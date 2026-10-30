#!/usr/bin/env python3
"""
Documentación incremental del documentador-proyecto: qué se documentó, desde qué commit, y qué cambió.

Guarda el estado en input/documentacion/.estado.json:
    repositorios  por repo: proveedor, nombre, rama, commit documentado y fecha
    documentos    por documento: qué archivos o carpetas del código lo alimentaron (fuentes), sus
                  historias y módulos, y si quedó desactualizado por un cambio del código
    historias     por historia: fecha de cambio de la historia y de sus PRs cuando se documentó, alias
                  local (HU-XXX), módulos y archivos que toca

Comandos (desde la raíz del repo):
    python scripts/cambios_documentacion.py repo --proveedor github --nombre mi-org/mi-app --rama main --commit a1b2c3d
    python scripts/cambios_documentacion.py registrar --documento proyecto/reglas-de-negocio.md
           --fuentes "src/pagos/,src/**/validaciones*.ts" [--repo mi-org/mi-app] [--historias PROJ-12] [--modulos pagos]
    python scripts/cambios_documentacion.py historia --key PROJ-12 [--hu HU-001] --cambio-historia 2026-10-10T12:00
           [--cambio-prs 2026-10-11] [--modulos pagos] [--archivos src/pagos/checkout.ts]
    python scripts/cambios_documentacion.py cambios --repo mi-org/mi-app
           (--git <ruta del clon> | --archivos a.ts,b.ts | --archivos-desde lista.txt) [--hasta <commit>] [--marcar]

"cambios" toma los archivos que cambiaron desde el commit documentado (con --git corre
`git diff --name-only <commit>..HEAD` en el clon; con el conector, el agente pasa la lista con --archivos
o --archivos-desde) y escribe input/documentacion/cambios.md con:
    - los documentos afectados (los que hay que rehacer) y por qué archivo,
    - las historias afectadas,
    - los casos existentes potencialmente desactualizados (output/casos-de-prueba/ y los .feature de
      herramientas/k0lmena), para pasarle al revisor-casos.
Con --marcar deja esos documentos como desactualizados en el estado (el índice los muestra así) hasta
que se vuelvan a registrar con "registrar". Imprime el resultado en JSON.

Las fuentes de un documento son rutas relativas a la raíz del repositorio de la app: una carpeta
(terminada en "/"), un archivo o un patrón con * y ** (src/**/i18n/*.json).
"""
import os
import argparse
import datetime as dt
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
CARPETA = PROYECTO / "input" / "documentacion"
ESTADO = ".estado.json"
CAMBIOS = "cambios.md"
_ID_HU = re.compile(r"\b(HU-\d+)\b")
_TAG_HU = re.compile(r"@(HU-\d+)\b")


# ------------------------------------------------------------------ estado
def estado_vacio():
    return {"version": 1, "repositorios": {}, "documentos": {}, "historias": {}}


def leer_estado(carpeta=CARPETA):
    archivo = Path(carpeta) / ESTADO
    if not archivo.exists():
        return estado_vacio()
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    base = estado_vacio()
    base.update(datos)
    return base


def guardar_estado(estado, carpeta=CARPETA):
    Path(carpeta).mkdir(parents=True, exist_ok=True)
    (Path(carpeta) / ESTADO).write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _lista(texto):
    return [x.strip() for x in (texto or "").split(",") if x.strip()]


def _hoy():
    return dt.date.today().isoformat()


def registrar_repo(estado, proveedor, nombre, rama, commit, fecha=None):
    estado["repositorios"][nombre] = {"proveedor": proveedor, "nombre": nombre, "rama": rama or "", "commit": commit,
                                      "fecha": fecha or _hoy()}
    return estado


def registrar_documento(estado, documento, fuentes, repo="", historias=(), modulos=(), fecha=None):
    """Alta o actualización de un documento: limpia la marca de desactualizado (se acaba de rehacer)."""
    estado["documentos"][documento] = {"repo": repo, "fuentes": list(fuentes), "historias": list(historias),
                                       "modulos": list(modulos), "actualizado": fecha or _hoy()}
    return estado


def registrar_historia(estado, key, hu="", cambio_historia="", cambio_prs="", modulos=(), archivos=(), fecha=None, huella=""):
    estado["historias"][key] = {"hu": hu, "cambio_historia": cambio_historia, "cambio_prs": cambio_prs,
                                "modulos": list(modulos), "archivos": list(archivos), "documentado": fecha or _hoy(),
                                **({"huella": huella} if huella else {})}
    return estado


# Campos que definen el requerimiento: si no cambian, la historia no se vuelve a documentar aunque cambie su
# fecha (en Jira, `updated` cambia también al moverla de columna, reasignarla o etiquetarla).
CAMPOS_HUELLA = ("titulo", "descripcion", "criterios", "comentarios", "ultimo_comentario", "subtareas", "vinculos", "adjuntos")


def huella(contenido):
    """Huella corta del contenido que define el requerimiento (no incluye estado, responsable ni etiquetas)."""
    if not contenido:
        return ""
    import hashlib
    norm = {k: contenido.get(k) for k in CAMPOS_HUELLA if contenido.get(k) not in (None, "", [], {})}
    if not norm:
        return ""
    texto = json.dumps(norm, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(" ".join(texto.split()).encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ coincidencias
def _ruta(r):
    r = r.strip().replace("\\", "/")
    while r.startswith("./"):
        r = r[2:]
    return r.lstrip("/")


def coincide(archivo, fuente):
    """¿El archivo cambiado está cubierto por la fuente (carpeta/, archivo o patrón con * y **)?"""
    archivo, fuente = _ruta(archivo), _ruta(fuente)
    if not fuente:
        return False
    if fuente.endswith("/"):
        return archivo.startswith(fuente)
    if any(c in fuente for c in "*?["):
        # ** cruza carpetas; fnmatch ya hace que * también las cruce, así que alcanza con normalizar.
        return fnmatch.fnmatchcase(archivo, fuente.replace("**/", "*")) or fnmatch.fnmatchcase(archivo, fuente)
    return archivo == fuente or archivo.startswith(fuente.rstrip("/") + "/")


def documentos_afectados(estado, archivos, repo=""):
    """{documento: [archivos que lo afectan]} para los documentos de ese repo (o sin repo)."""
    salida = {}
    for doc, info in estado["documentos"].items():
        if repo and info.get("repo") and info["repo"] != repo:
            continue
        hits = [a for a in archivos if any(coincide(a, f) for f in info.get("fuentes") or [])]
        if hits:
            salida[doc] = hits
    return salida


def historias_afectadas(estado, archivos, docs):
    """Historias de los documentos afectados + las que tocan alguno de los archivos cambiados."""
    hs = set()
    for doc in docs:
        hs.update(estado["documentos"].get(doc, {}).get("historias") or [])
    for key, info in estado["historias"].items():
        if any(coincide(a, f) for a in archivos for f in info.get("archivos") or []):
            hs.add(key)
    return sorted(hs)


def modulos_afectados(estado, docs, historias):
    ms = set()
    for doc in docs:
        ms.update(estado["documentos"].get(doc, {}).get("modulos") or [])
    for h in historias:
        ms.update(estado["historias"].get(h, {}).get("modulos") or [])
    return sorted(m for m in ms if m)


def inventario_casos(raiz=PROYECTO):
    """Casos existentes: [{archivo, historias (HU-XXX), texto}] de output/casos-de-prueba y los .feature de k0lmena."""
    archivos = []
    for base, patron in (("output/casos-de-prueba", "**/*.md"), ("output/casos-de-prueba", "**/*.feature"),
                         ("output/casos-de-prueba", "**/*.xlsx"), ("herramientas/k0lmena", "*/features/**/*.feature")):
        carpeta = Path(raiz) / base
        if carpeta.exists():
            archivos += [p for p in carpeta.glob(patron) if p.is_file() and not p.name.endswith("-cobertura.md")]
    casos = []
    for p in sorted(set(archivos)):
        rel = p.relative_to(raiz).as_posix()
        texto = "" if p.suffix == ".xlsx" else p.read_text(encoding="utf-8", errors="replace")
        hus = set(_ID_HU.findall(p.name)) | set(_TAG_HU.findall(texto))
        casos.append({"archivo": rel, "historias": sorted(hus), "texto": texto[:20000].lower()})
    return casos


def casos_afectados(estado, historias, modulos, casos):
    """Casos que tocan una historia afectada (por su key o su alias HU-XXX) o mencionan un módulo afectado."""
    ids = set(historias) | {estado["historias"].get(h, {}).get("hu") for h in historias} - {None, ""}
    salida = []
    for c in casos:
        por_historia = sorted(ids & set(c["historias"]))
        por_modulo = [m for m in modulos if re.search(r"\b" + re.escape(m.lower()) + r"\b", c["texto"])]
        if por_historia or por_modulo:
            motivo = (f"historia {', '.join(por_historia)}" if por_historia else "") + \
                     (" · " if por_historia and por_modulo else "") + (f"módulo {', '.join(por_modulo)}" if por_modulo else "")
            salida.append({"archivo": c["archivo"], "motivo": motivo})
    return salida


def analizar(estado, archivos, repo="", raiz=PROYECTO):
    docs = documentos_afectados(estado, archivos, repo)
    hs = historias_afectadas(estado, archivos, docs)
    ms = modulos_afectados(estado, docs, hs)
    sin_documento = [a for a in archivos if not any(a in v for v in docs.values())]
    return {"repo": repo, "archivos": archivos, "documentos": docs, "historias": hs, "modulos": ms,
            "casos": casos_afectados(estado, hs, ms, inventario_casos(raiz)), "sin_documento": sin_documento}


def marcar(estado, resultado, desde, hasta):
    for doc, hits in resultado["documentos"].items():
        estado["documentos"][doc]["desactualizado"] = {"desde": desde, "hasta": hasta, "archivos": hits[:50], "fecha": _hoy()}
    return estado


# ------------------------------------------------------------------ cambios.md
def armar_cambios_md(r, desde, hasta):
    l = ["---", "titulo: Cambios desde la última documentación", "tipo: cambios", f"fuentes: {r['repo'] or 'repositorio'} {desde}..{hasta}",
         f"actualizado: {_hoy()}", "---", "", "# Cambios desde la última documentación", "",
         f"{len(r['archivos'])} archivo(s) cambiaron en `{r['repo'] or 'el repositorio'}` entre `{desde}` y `{hasta}`.", ""]
    l += ["## Documentos a rehacer", ""]
    if r["documentos"]:
        l += ["| Documento | Archivos que cambiaron |", "|---|---|"]
        for doc, hits in sorted(r["documentos"].items()):
            muestra = ", ".join(f"`{h}`" for h in hits[:6]) + (f" y {len(hits) - 6} más" if len(hits) > 6 else "")
            l.append(f"| `{doc}` | {muestra} |")
    else:
        l.append("Ningún documento depende de los archivos cambiados.")
    l += ["", "## Historias afectadas", "", ", ".join(r["historias"]) or "Ninguna.", ""]
    l += ["## Casos para revisar", ""]
    if r["casos"]:
        l += ["Pueden haber quedado desactualizados por estos cambios. Sugerencia: pasarlos al `revisor-casos`.", "",
              "| Archivo | Por qué |", "|---|---|"] + [f"| `{c['archivo']}` | {c['motivo']} |" for c in r["casos"]]
    else:
        l.append("No hay casos existentes ligados a las historias o módulos afectados.")
    if r["sin_documento"]:
        l += ["", "## Archivos que no alimentan ningún documento", "",
              "Puede ser código nuevo para documentar (o que no afecta las pruebas):", ""]
        l += [f"- `{a}`" for a in r["sin_documento"][:40]]
        if len(r["sin_documento"]) > 40:
            l.append(f"- y {len(r['sin_documento']) - 40} más")
    return "\n".join(l) + "\n"


# ------------------------------------------------------------------ historias que cambiaron (requerimientos)
def _fecha_iso(v):
    return str(v or "").strip().replace(" ", "T")[:19]


def comparar_historias(estado, actuales, raiz=PROYECTO):
    """Compara las historias del alcance (con su fecha de cambio actual) con las documentadas.
    actuales: [{key, hu?, titulo?, actualizado, prs?, contenido?}]. Devuelve nuevas, cambiadas (con qué cambió),
    solo_metadatos (cambió la fecha pero no el contenido del requerimiento: no se rehace), sin_cambios y los casos
    existentes de las cambiadas para revisar."""
    nuevas, cambiadas, iguales, metadatos = [], [], [], []
    for h in actuales:
        key = h.get("key")
        if not key:
            continue
        previo = estado["historias"].get(key)
        if not previo:
            nuevas.append({"key": key, "titulo": h.get("titulo", ""), "actualizado": h.get("actualizado", "")})
            continue
        que = []
        if _fecha_iso(h.get("actualizado")) > _fecha_iso(previo.get("cambio_historia")):
            que.append("historia")
        if h.get("prs") and _fecha_iso(h.get("prs")) > _fecha_iso(previo.get("cambio_prs")):
            que.append("PRs")
        nueva_huella = huella(h.get("contenido"))
        if que == ["historia"] and nueva_huella and previo.get("huella") == nueva_huella:
            metadatos.append({"key": key, "actualizado": h.get("actualizado", "")})
            continue
        if que:
            cambiadas.append({"key": key, "hu": previo.get("hu") or h.get("hu", ""), "titulo": h.get("titulo", ""),
                              "cambio": " y ".join(que), "antes": previo.get("cambio_historia", ""), "ahora": h.get("actualizado", "")})
        else:
            iguales.append(key)
    claves = [c["key"] for c in cambiadas]
    modulos = sorted({m for k in claves for m in estado["historias"].get(k, {}).get("modulos", [])})
    casos = casos_afectados(estado, claves, [], inventario_casos(raiz)) if claves else []
    return {"nuevas": nuevas, "cambiadas": cambiadas, "solo_metadatos": metadatos, "sin_cambios": iguales,
            "modulos": modulos, "casos": casos}


def registrar_metadatos(estado, r):
    """Las historias que solo cambiaron de estado o metadatos quedan con su fecha nueva (no se rehacen)."""
    for m in r.get("solo_metadatos") or []:
        if m["key"] in estado["historias"] and m.get("actualizado"):
            estado["historias"][m["key"]]["cambio_historia"] = m["actualizado"]
    return estado


def armar_cambios_historias_md(r, desde):
    l = ["---", "titulo: Historias nuevas o que cambiaron", "tipo: cambios", f"fuentes: gestión del proyecto (desde {desde or 'el inicio'})",
         f"actualizado: {_hoy()}", "---", "", "# Historias nuevas o que cambiaron", "",
         f"Revisión del {_hoy()} contra la documentación (desde {desde or 'el inicio'}): {len(r['nuevas'])} nueva(s), "
         f"{len(r['cambiadas'])} con cambios en el requerimiento, {len(r.get('solo_metadatos') or [])} que solo cambiaron "
         f"de estado o metadatos (no se rehacen), {len(r['sin_cambios'])} sin cambios.", ""]
    l += ["## Historias que cambiaron (rehacer el dossier y revisar sus casos)", ""]
    if r["cambiadas"]:
        l += ["| Historia | HU | Título | Qué cambió | Documentada | Ahora |", "|---|---|---|---|---|---|"]
        l += [f"| {c['key']} | {c['hu'] or '-'} | {c['titulo'] or '-'} | {c['cambio']} | {c['antes'] or '-'} | {c['ahora'] or '-'} |" for c in r["cambiadas"]]
    else:
        l.append("Ninguna.")
    l += ["", "## Historias nuevas (documentar)", ""]
    l += ([f"- {n['key']}{' · ' + n['titulo'] if n['titulo'] else ''}" for n in r["nuevas"]] or ["Ninguna."])
    l += ["", "## Casos para revisar", ""]
    if r["casos"]:
        l += ["Los requerimientos de estas historias cambiaron después de escribir sus casos. Sugerencia: pasarlos al "
              "`revisor-casos` (o regenerarlos) después de actualizar el dossier.", "",
              "| Archivo | Por qué |", "|---|---|"] + [f"| `{c['archivo']}` | {c['motivo']} |" for c in r["casos"]]
    else:
        l.append("No hay casos existentes de las historias que cambiaron.")
    return "\n".join(l) + "\n"


def archivos_desde_git(ruta, desde, hasta="HEAD"):
    r = subprocess.run(["git", "-C", str(ruta), "diff", "--name-only", f"{desde}..{hasta}"], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git diff falló en {ruta}: {r.stderr.strip()}")
    return [x for x in r.stdout.splitlines() if x.strip()]


def _formatear(md):
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "formatear_tablas.py"), str(md)], capture_output=True, text=True)


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Estado y cambios de la documentación del proyecto")
    ap.add_argument("--carpeta", default=str(CARPETA))
    sub = ap.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("repo")
    p.add_argument("--proveedor", required=True)
    p.add_argument("--nombre", required=True)
    p.add_argument("--rama", default="")
    p.add_argument("--commit", required=True)
    p = sub.add_parser("registrar")
    p.add_argument("--documento", required=True)
    p.add_argument("--fuentes", default="")
    p.add_argument("--repo", default="")
    p.add_argument("--historias", default="")
    p.add_argument("--modulos", default="")
    p = sub.add_parser("historia")
    p.add_argument("--key", required=True)
    p.add_argument("--hu", default="")
    p.add_argument("--cambio-historia", default="")
    p.add_argument("--cambio-prs", default="")
    p.add_argument("--modulos", default="")
    p.add_argument("--archivos", default="")
    p.add_argument("--huella-desde", help="el _alcance.json: toma de ahí la fecha y la huella del contenido de esta historia")
    p = sub.add_parser("cambios")
    p.add_argument("--repo", default="")
    p.add_argument("--git", help="ruta del clon local (REPO_RUTA_LOCAL)")
    p.add_argument("--archivos", default="")
    p.add_argument("--archivos-desde")
    p.add_argument("--desde", help="commit de partida (por defecto, el documentado del repo)")
    p.add_argument("--hasta", default="HEAD")
    p.add_argument("--marcar", action="store_true")
    p = sub.add_parser("historias", help="qué historias del alcance son nuevas o cambiaron desde que se documentaron")
    p.add_argument("--actual", required=True, help='JSON con [{"key", "hu", "titulo", "actualizado", "prs"}] de la herramienta de gestión')
    p.add_argument("--registrar-revision", action="store_true", help="guardar la fecha de esta revisión (la próxima consulta parte de ahí)")
    a = ap.parse_args(argv)
    carpeta = Path(a.carpeta)
    estado = leer_estado(carpeta)

    if a.comando == "repo":
        guardar_estado(registrar_repo(estado, a.proveedor, a.nombre, a.rama, a.commit), carpeta)
        print(f"Repositorio {a.nombre} documentado hasta {a.commit}")
    elif a.comando == "registrar":
        guardar_estado(registrar_documento(estado, a.documento, _lista(a.fuentes), a.repo, _lista(a.historias), _lista(a.modulos)), carpeta)
        print(f"Documento {a.documento}: {len(_lista(a.fuentes))} fuente(s)")
    elif a.comando == "historia":
        cambio, firma = a.cambio_historia, ""
        if a.huella_desde:
            datos = json.loads(Path(a.huella_desde).read_text(encoding="utf-8"))
            lista = datos.get("historias", []) if isinstance(datos, dict) else datos
            item = next((h for h in lista if h.get("key") == a.key), {})
            cambio = cambio or item.get("actualizado", "")
            firma = huella(item.get("contenido"))
        guardar_estado(registrar_historia(estado, a.key, a.hu, cambio, a.cambio_prs, _lista(a.modulos), _lista(a.archivos),
                                          huella=firma), carpeta)
        print(f"Historia {a.key} registrada" + (f" (huella {firma})" if firma else ""))
    elif a.comando == "historias":
        actuales = json.loads(Path(a.actual).read_text(encoding="utf-8"))
        desde = estado.get("revision_historias", "")
        r = comparar_historias(estado, actuales.get("historias", actuales) if isinstance(actuales, dict) else actuales)
        md = carpeta / "cambios-historias.md"
        md.write_text(armar_cambios_historias_md(r, desde), encoding="utf-8")
        _formatear(md)
        if a.registrar_revision:
            estado["revision_historias"] = dt.datetime.now().isoformat(timespec="seconds")
            guardar_estado(registrar_metadatos(estado, r), carpeta)
        print(json.dumps(r | {"revision_anterior": desde}, ensure_ascii=False, indent=2))
    else:
        repos = estado["repositorios"]
        repo = a.repo or (next(iter(repos)) if len(repos) == 1 else "")
        desde = a.desde or (repos.get(repo) or {}).get("commit")
        if a.git:
            if not desde:
                raise SystemExit("No hay commit documentado para ese repositorio: pasá --desde o registralo con 'repo'.")
            archivos = archivos_desde_git(a.git, desde, a.hasta)
        elif a.archivos_desde:
            archivos = [x.strip() for x in Path(a.archivos_desde).read_text(encoding="utf-8").splitlines() if x.strip()]
        else:
            archivos = _lista(a.archivos)
        resultado = analizar(estado, archivos, repo)
        md = carpeta / CAMBIOS
        md.write_text(armar_cambios_md(resultado, desde or "?", a.hasta), encoding="utf-8")
        _formatear(md)
        if a.marcar:
            guardar_estado(marcar(estado, resultado, desde or "?", a.hasta), carpeta)
        print(json.dumps({k: v for k, v in resultado.items() if k != "archivos"} | {"cantidad_archivos": len(archivos)},
                         ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

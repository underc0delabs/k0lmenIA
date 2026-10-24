#!/usr/bin/env python3
"""
Búsqueda de bugs duplicados y relacionados (agente triador-bugs).

Uso (desde la raíz del repo):
    python scripts/buscar_duplicados.py --bug output/reportes-bug/BUG-008.md [--candidatos candidatos.json]
                                        [--nombre BUG-008] [--sin-locales] [--max 10]
                                        [--umbral-duplicado 0.55] [--umbral-relacionado 0.30]
    python scripts/buscar_duplicados.py --lote output/reportes-bug [--candidatos candidatos.json] --nombre sprint-5

Compara un bug (o cada bug de una carpeta, con --lote) contra:
  - los bugs locales de output/reportes-bug/ e input/bugs/ (salvo --sin-locales), y
  - los candidatos que trajo el agente de Jira, Azure DevOps, GitHub o GitLab (--candidatos).

La similitud usa los mismos conceptos que la selección de casos (scripts/seleccionar_casos.py: español e
inglés, sinónimos, sin acentos ni palabras vacías). El título pesa el doble; suman la misma historia, la
misma pantalla ([Pantalla] del título) y el mismo mensaje de error entre comillas. Cada candidato queda
como "Duplicado probable", "Relacionado" o "Distinto". Un duplicado probable que ya está cerrado o
resuelto se marca como "posible regresión".

Formato de --candidatos (lista JSON; solo "id" y "titulo" son obligatorios):
    [{"id": "PROJ-120", "titulo": "...", "descripcion": "...", "estado": "Abierto", "fuente": "jira",
      "url": "https://...", "historia": "PROJ-12", "componente": "Pagos", "creado": "2026-09-30"}]

Salida en output/triage/<nombre>/: triage.json (los datos) y triage.md (tablas alineadas).
"""
import os
import argparse
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
sys.path.insert(0, str(RAIZ / "scripts"))

from seleccionar_casos import tokens  # noqa: E402  (misma normalización y sinónimos)

DUPLICADO, RELACIONADO, DISTINTO = "Duplicado probable", "Relacionado", "Distinto"
CERRADOS = {"cerrado", "cerrada", "resuelto", "resuelta", "closed", "resolved", "done", "hecho", "listo", "finalizado", "finalizada",
            "rechazado", "rejected", "removed", "fixed", "won't fix"}
RE_CAMPO = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
RE_PANTALLA = re.compile(r"^\s*\[([^\]]+)\]")
RE_CITA = re.compile(r"[\"“«']([^\"”»']{6,})[\"”»']")
RE_HISTORIA = re.compile(r"\b(?:HU|[A-Z][A-Z0-9]{1,9})-\d+\b")


# ------------------------------------------------------------------ lectura
def leer_bug_md(texto, ident=""):
    """Campos de un reporte de bug en bloque vertical (plantilla del repo) o de una nota suelta."""
    campos, actual = {}, None
    for linea in texto.splitlines():
        m = RE_CAMPO.match(linea.strip())
        if m:
            actual = m.group(1).strip().lower()
            campos[actual] = m.group(2).strip()
        elif actual:
            campos[actual] += "\n" + linea
    limpiar = lambda v: re.sub(r"`", "", (v or "")).strip()
    titulo = limpiar(campos.get("título") or campos.get("titulo"))
    if not titulo:  # nota suelta: primera línea con texto
        titulo = next((l.strip("# ").strip() for l in texto.splitlines() if l.strip()), "")
    cuerpo_claves = ("descripción", "descripcion", "pasos de reproducción", "pasos de reproduccion",
                     "resultado actual", "resultado esperado", "precondiciones")
    cuerpo = "\n".join(limpiar(campos.get(k)) for k in cuerpo_claves if campos.get(k)) or texto
    historia = RE_HISTORIA.search(limpiar(campos.get("historia")) or "")
    return {
        "id": limpiar(campos.get("id")).split()[0] if campos.get("id") else ident,
        "titulo": titulo,
        "descripcion": cuerpo,
        "resultado_actual": limpiar(campos.get("resultado actual")),
        "historia": historia.group(0) if historia else "",
        "estado": limpiar(campos.get("estado")).split(" ")[0] if campos.get("estado") else "",
        "fuente": "local",
    }


def leer_bug(ruta):
    ruta = Path(ruta)
    texto = ruta.read_text(encoding="utf-8-sig")
    if ruta.suffix.lower() == ".json":
        datos = json.loads(texto)
        datos.setdefault("id", ruta.stem)
        datos.setdefault("fuente", "local")
        return datos
    bug = leer_bug_md(texto, ruta.stem)
    bug["archivo"] = ruta.relative_to(PROYECTO).as_posix() if ruta.is_relative_to(PROYECTO) else str(ruta)
    return bug


def bugs_locales(excluir=()):
    excluir = {Path(e).resolve() for e in excluir}
    salida = []
    for carpeta in (PROYECTO / "output" / "reportes-bug", PROYECTO / "input" / "bugs"):
        for ruta in sorted(carpeta.glob("*.md")) if carpeta.exists() else []:
            if ruta.resolve() not in excluir and not ruta.name.startswith("_"):
                salida.append(leer_bug(ruta))
    return salida


# ------------------------------------------------------------------ similitud
def _vector(bug):
    v = Counter(tokens(bug.get("titulo", "")) * 2)
    v.update(tokens(bug.get("descripcion", "")))
    v.update(tokens(bug.get("resultado_actual", "")))
    return v


def _coseno(a, b):
    comunes = set(a) & set(b)
    if not comunes:
        return 0.0
    num = sum(a[t] * b[t] for t in comunes)
    return num / (math.sqrt(sum(x * x for x in a.values())) * math.sqrt(sum(x * x for x in b.values())))


def _citas(bug):
    texto = " ".join(str(bug.get(k, "")) for k in ("titulo", "descripcion", "resultado_actual"))
    return {c.strip().lower() for c in RE_CITA.findall(texto)}


def _pantalla(bug):
    m = RE_PANTALLA.match(bug.get("titulo", ""))
    return m.group(1).strip().lower() if m else ""


def similitud(bug, cand):
    """(puntaje 0..1, motivos) entre dos bugs."""
    va, vb = _vector(bug), _vector(cand)
    base = _coseno(va, vb)
    motivos = []
    comunes = sorted(set(va) & set(vb), key=lambda t: -(va[t] + vb[t]))[:6]
    if comunes:
        motivos.append("conceptos en común: " + ", ".join(comunes))
    extra = 0.0
    if bug.get("historia") and bug.get("historia") == cand.get("historia"):
        extra += 0.10
        motivos.append(f"misma historia ({bug['historia']})")
    if _pantalla(bug) and _pantalla(bug) == _pantalla(cand):
        extra += 0.10
        motivos.append(f"misma pantalla ([{_pantalla(bug)}])")
    citas = _citas(bug) & _citas(cand)
    if citas:
        extra += 0.15
        motivos.append(f"mismo mensaje: \"{sorted(citas)[0]}\"")
    return round(min(1.0, base + extra), 3), motivos


def clasificar(puntaje, umbral_dup, umbral_rel):
    return DUPLICADO if puntaje >= umbral_dup else RELACIONADO if puntaje >= umbral_rel else DISTINTO


def comparar(bug, candidatos, umbral_dup=0.55, umbral_rel=0.30, maximo=10):
    resultado = []
    propio = {str(bug.get("id", "")).lower(), str(bug.get("archivo", "")).lower()} - {""}
    for c in candidatos:
        if str(c.get("id", "")).lower() in propio or str(c.get("archivo", "")).lower() in propio:
            continue
        puntaje, motivos = similitud(bug, c)
        clase = clasificar(puntaje, umbral_dup, umbral_rel)
        cerrado = str(c.get("estado", "")).strip().lower() in CERRADOS
        resultado.append({
            "id": c.get("id", ""), "titulo": c.get("titulo", ""), "fuente": c.get("fuente", ""),
            "estado": c.get("estado", ""), "url": c.get("url", c.get("archivo", "")), "historia": c.get("historia", ""),
            "componente": c.get("componente", ""), "puntaje": puntaje, "clasificacion": clase,
            "posible_regresion": clase == DUPLICADO and cerrado, "motivos": motivos,
        })
    resultado.sort(key=lambda r: -r["puntaje"])
    return [r for r in resultado if r["clasificacion"] != DISTINTO][:maximo] + \
        [r for r in resultado if r["clasificacion"] == DISTINTO][: max(0, min(3, maximo))]


def veredicto(coincidencias):
    dup = [c for c in coincidencias if c["clasificacion"] == DUPLICADO]
    if any(c["posible_regresion"] for c in dup):
        return "Posible regresión de un bug cerrado"
    if dup:
        return "Duplicado probable"
    if any(c["clasificacion"] == RELACIONADO for c in coincidencias):
        return "Nuevo, con bugs relacionados"
    return "Nuevo"


# ------------------------------------------------------------------ salida
def a_markdown(datos):
    l = [f"# Triage de bugs — {datos['nombre']}", "",
         f"Umbrales: duplicado probable desde {datos['umbrales']['duplicado']}, relacionado desde "
         f"{datos['umbrales']['relacionado']}. Candidatos revisados: {datos['candidatos_revisados']}.",
         "El puntaje es una heurística: el agente confirma cada duplicado leyendo los dos bugs.", ""]
    for b in datos["bugs"]:
        l += [f"## {b['id'] or 'Bug'} — {b['titulo']}", "", f"**Veredicto:** {b['veredicto']}", ""]
        if not b["coincidencias"]:
            l += ["Sin candidatos para comparar.", ""]
            continue
        l += ["| Candidato | Fuente | Estado | Puntaje | Clasificación | Motivos |", "|---|---|---|---|---|---|"]
        for c in b["coincidencias"]:
            clase = c["clasificacion"] + (" (posible regresión)" if c["posible_regresion"] else "")
            fila = [f"{c['id']} {c['titulo']}".strip(), c["fuente"] or "-", c["estado"] or "-", f"{c['puntaje']:.2f}",
                    clase, "; ".join(c["motivos"]) or "-"]
            l.append("| " + " | ".join(str(x).replace("|", "/").replace("\n", " ") for x in fila) + " |")
        l.append("")
    return "\n".join(l)


def escribir(datos, carpeta):
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "triage.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    md = carpeta / "triage.md"
    md.write_text(a_markdown(datos), encoding="utf-8")
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "formatear_tablas.py"), str(md)], capture_output=True, text=True)
    if r.returncode != 0:
        print("Aviso: no pude alinear las tablas de triage.md (corré scripts/formatear_tablas.py a mano).")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Bugs duplicados y relacionados")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--bug", help="el bug a triar (.md de la plantilla, nota suelta o .json)")
    g.add_argument("--lote", help="carpeta con varios bugs: compara cada uno contra el resto y los candidatos")
    ap.add_argument("--candidatos", help="JSON con los bugs que trajo el agente de Jira, Azure DevOps, GitHub o GitLab")
    ap.add_argument("--nombre", help="carpeta de salida en output/triage/ (por defecto, el ID del bug o el nombre del lote)")
    ap.add_argument("--sin-locales", action="store_true", help="no comparar contra output/reportes-bug/ e input/bugs/")
    ap.add_argument("--max", type=int, default=10, help="coincidencias por bug (10)")
    ap.add_argument("--umbral-duplicado", type=float, default=0.55)
    ap.add_argument("--umbral-relacionado", type=float, default=0.30)
    ap.add_argument("--salida", help="carpeta de salida (por defecto output/triage/<nombre>)")
    a = ap.parse_args(argv)
    if not 0 < a.umbral_relacionado < a.umbral_duplicado <= 1:
        ap.error("los umbrales tienen que cumplir 0 < relacionado < duplicado <= 1")

    candidatos = []
    if a.candidatos:
        candidatos = json.loads(Path(a.candidatos).read_text(encoding="utf-8-sig"))
        if not isinstance(candidatos, list):
            ap.error("--candidatos tiene que ser una lista JSON")
    if a.lote:
        carpeta = Path(a.lote)
        rutas = sorted(p for p in carpeta.glob("*") if p.suffix.lower() in (".md", ".json") and not p.name.startswith("_"))
        bugs = [leer_bug(p) for p in rutas]
        locales = [] if a.sin_locales else bugs_locales(excluir=rutas)
        nombre = a.nombre or carpeta.name
    else:
        bug = leer_bug(a.bug)
        bugs = [bug]
        locales = [] if a.sin_locales else bugs_locales(excluir=[a.bug])
        nombre = a.nombre or bug.get("id") or Path(a.bug).stem
    if not re.fullmatch(r"[\w.-]+", nombre):
        ap.error(f"--nombre inválido: {nombre!r} (solo letras, números, guiones y puntos)")

    resultado = []
    for b in bugs:
        pool = candidatos + locales + [x for x in bugs if x is not b]
        coincidencias = comparar(b, pool, a.umbral_duplicado, a.umbral_relacionado, a.max)
        resultado.append({"id": b.get("id", ""), "titulo": b.get("titulo", ""), "historia": b.get("historia", ""),
                          "veredicto": veredicto(coincidencias), "coincidencias": coincidencias})
    datos = {"nombre": nombre, "umbrales": {"duplicado": a.umbral_duplicado, "relacionado": a.umbral_relacionado},
             "candidatos_revisados": len(candidatos) + len(locales) + (len(bugs) - 1 if len(bugs) > 1 else 0),
             "bugs": resultado}
    carpeta = Path(a.salida) if a.salida else PROYECTO / "output" / "triage" / nombre
    escribir(datos, carpeta)
    for b in resultado:
        top = b["coincidencias"][0] if b["coincidencias"] else None
        extra = f" · más parecido: {top['id']} ({top['puntaje']:.2f}, {top['clasificacion']})" if top else ""
        print(f"{b['id'] or b['titulo'][:40]}: {b['veredicto']}{extra}")
    print(f"Triage: {carpeta / 'triage.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

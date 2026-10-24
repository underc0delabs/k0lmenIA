#!/usr/bin/env python3
"""
Arma la matriz de cobertura y trazabilidad de una o varias historias para el agente
analista-cobertura: HU → criterios de aceptación → casos → automatización → gestión → último
resultado → bugs, y marca los huecos.

Uso (desde la raíz del repo):
    python scripts/analizar_cobertura.py [--historia HU-001] [--criterios criterios.json]

Fuentes que lee (las que existan; lo que no está, no se inventa):
  - Criterios (CA1, CA2…): input/historias/*HU-XXX*, output/contexto/contexto-HU-XXX.md, las tablas
    de cobertura (casos-HU-XXX-cobertura.md, HU-XXX-cobertura.md) y --criterios (JSON del agente,
    p. ej. leídos de Jira: {"HU-001": [{"id": "CA1", "descripcion": "..."}]}).
  - Casos manuales: output/casos-de-prueba/manuales/casos-HU-XXX.xlsx (CA por etiqueta @CA1 o mención).
  - Casos BDD: output/casos-de-prueba/bdd/HU-XXX*.feature (@CP-XXX, @CA1).
  - Automatización: herramientas/k0lmena/{web,api,mobile}/features/**/*.feature con @HU-XXX
    (@CP-XXX, @bloqueado, @falta-info).
  - Gestión: output/gestion/HU-XXX-<herramienta>.json (qué CP es qué key remota).
  - Resultados: npm test (reports/<suite>/cucumber-report.json y su historial/) y ejecuciones en vivo; vale el
    más reciente de cada caso.
  - Bugs: output/reportes-bug/BUG-*.md de la historia (y los CP que mencionan).
  - Falta información: FI-XX de la ficha de contexto y de los casos.

Huecos que marca: criterio sin casos, caso sin criterio, caso sin automatizar (por prioridad),
automatizado bloqueado, automatizado sin resultado, último resultado fallido, caso sin subir a la
herramienta de gestión (si la historia ya usa una), falta información abierta.

Deja output/cobertura/<HU o todas>/cobertura.json e informe-cobertura.html (la corrida anterior pasa a
historial/).
"""
import os
import argparse
import datetime
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "scripts" / "gestion"))
import recolectar_resultados as rec  # noqa: E402
import _historial  # noqa: E402

RE_HU = re.compile(r"\b(HU-\d+)\b", re.I)
RE_CA = re.compile(r"\bCA-?(\d+)\b")
RE_CP = re.compile(r"\bCP(-API)?-\d+\b")
RE_FI = re.compile(r"\bFI-\d+\b")
SEV_ORDEN = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
PRIO_ORDEN = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}


def _ca(n):
    return f"CA{int(n)}"


def _leer(p):
    try:
        return Path(p).read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def criterios_de_texto(texto):
    """CA1: descripción · **CA1** — descripción · | CA1 | descripción | … (tablas Markdown o ASCII)."""
    salida = {}
    for linea in texto.splitlines():
        lim = linea.strip()
        if lim.startswith(("|", "+")) or "|" in lim:
            celdas = [c.strip() for c in lim.strip("|").split("|")]
            if celdas and re.fullmatch(r"CA-?\d+", celdas[0]):
                salida.setdefault(_ca(RE_CA.match(celdas[0]).group(1)), celdas[1] if len(celdas) > 1 else "")
            continue
        m = re.match(r"^[-*#\s]*\**\s*CA-?(\d+)\s*\**\s*[:.\-–—)]\s*\**\s*(.+)$", lim)
        if m:
            salida.setdefault(_ca(m.group(1)), re.sub(r"[*_`]", "", m.group(2)).strip())
    return salida


def cobertura_de_tabla(texto):
    """De la tabla de cobertura (CA → casos que lo cubren): {CA: {CP…}}."""
    mapa = {}
    for linea in texto.splitlines():
        if "|" not in linea:
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if celdas and re.fullmatch(r"CA-?\d+", celdas[0]):
            ca = _ca(RE_CA.match(celdas[0]).group(1))
            mapa.setdefault(ca, set()).update(m.group(0) for c in celdas[1:] for m in RE_CP.finditer(c))
    return mapa


def historias_presentes():
    vistas = set()
    patrones = ["input/historias/*", "output/contexto/contexto-*.md", "output/casos-de-prueba/manuales/casos-*.xlsx",
                "output/casos-de-prueba/bdd/*.feature", "output/gestion/*.json"]
    for p in patrones:
        for a in glob.glob(str(PROYECTO / p)):
            vistas.update(m.upper() for m in RE_HU.findall(Path(a).name))
    for a in glob.glob(str(PROYECTO / "herramientas" / "k0lmena" / "*" / "features" / "**" / "*.feature"), recursive=True):
        vistas.update(m.upper() for m in RE_HU.findall(_leer(a)))
    return sorted(vistas, key=lambda h: int(h.split("-")[1]))


def _features_con_tag(globo, hu):
    """Escenarios (lectores.leer_feature) de los .feature que tienen el tag @HU-XXX."""
    from lectores import leer_feature
    salida = []
    for a in sorted(glob.glob(str(PROYECTO / globo), recursive=True)):
        texto = _leer(a)
        if not re.search(rf"@{hu}\b", texto, re.I) and hu.lower() not in Path(a).name.lower():
            continue
        try:
            for c in leer_feature(a):
                tags = [t.upper() for t in c["etiquetas"]]
                if f"{hu}" in tags or hu.lower() in Path(a).name.lower():
                    c["_archivo"] = Path(a).relative_to(PROYECTO).as_posix()
                    salida.append(c)
        except Exception:  # un .feature sin escenarios o mal formado no corta el análisis
            continue
    return salida


def analizar_historia(hu, criterios_extra):
    # ---- criterios
    criterios, origen_ca = {}, []
    fuentes_ca = sorted(glob.glob(str(PROYECTO / "input" / "historias" / f"*{hu}*"))) + [str(PROYECTO / "output" / "contexto" / f"contexto-{hu}.md")]
    for a in fuentes_ca:
        nuevos = criterios_de_texto(_leer(a))
        if nuevos:
            origen_ca.append(Path(a).relative_to(PROYECTO).as_posix())
        for k, v in nuevos.items():
            criterios.setdefault(k, v)
    cob = {}
    tablas = glob.glob(str(PROYECTO / "output" / "casos-de-prueba" / "manuales" / f"casos-{hu}-cobertura.md")) + \
        glob.glob(str(PROYECTO / "output" / "casos-de-prueba" / "bdd" / f"{hu}-cobertura.md"))
    for a in tablas:
        texto = _leer(a)
        for k, v in criterios_de_texto(texto).items():
            criterios.setdefault(k, v)
        for k, cps in cobertura_de_tabla(texto).items():
            cob.setdefault(k, set()).update(cps)
        origen_ca.append(Path(a).relative_to(PROYECTO).as_posix())
    for c in criterios_extra.get(hu, []):
        criterios.setdefault(_ca(RE_CA.search(c["id"]).group(1)), c.get("descripcion", ""))
    if criterios_extra.get(hu):
        origen_ca.append("--criterios (agente)")

    # ---- casos manuales y BDD
    casos = {}

    def caso(cid):
        return casos.setdefault(cid, {"id": cid, "titulo": "", "prioridad": "", "fuentes": [], "criterios": set(),
                                      "automatizado": [], "gestion": {}, "resultado": None, "bugs": [], "falta_info": set()})

    xlsx = PROYECTO / "output" / "casos-de-prueba" / "manuales" / f"casos-{hu}.xlsx"
    if xlsx.exists():
        from lectores import leer_xlsx
        try:
            for c in leer_xlsx(xlsx):
                x = caso(c["id"])
                x["titulo"] = x["titulo"] or c["titulo"]
                x["prioridad"] = x["prioridad"] or c["prioridad"]
                x["fuentes"].append("Manual")
                texto = " ".join([c.get("descripcion", ""), " ".join(c.get("etiquetas") or [])])
                x["criterios"].update(_ca(n) for n in RE_CA.findall(texto))
                x["falta_info"].update(RE_FI.findall(" ".join(c.get("etiquetas") or [])))
        except Exception as ex:  # planilla con otro formato: se informa, no se corta
            print(f"[!] No pude leer {xlsx.name}: {ex}", file=sys.stderr)
    for c in _features_con_tag(f"output/casos-de-prueba/bdd/{hu}*.feature", hu) + \
            [x for x in _features_con_tag("output/casos-de-prueba/bdd/*.feature", hu) if hu.lower() not in x["_archivo"].lower()]:
        if not RE_CP.fullmatch(c["id"]):
            continue
        x = caso(c["id"])
        x["titulo"] = x["titulo"] or c["titulo"]
        x["prioridad"] = x["prioridad"] or c["prioridad"]
        if "BDD" not in x["fuentes"]:
            x["fuentes"].append("BDD")
        x["criterios"].update(_ca(n) for n in RE_CA.findall(" ".join(c["etiquetas"])))
    for ca, cps in cob.items():
        for cp in cps:
            caso(cp)["criterios"].add(ca)

    # ---- automatización en k0lmena
    sin_cp = []
    for suite in ("web", "api", "mobile"):
        for c in _features_con_tag(f"herramientas/k0lmena/{suite}/features/**/*.feature", hu):
            tags = [t.lower() for t in c["etiquetas"]]
            if not RE_CP.fullmatch(c["id"]):
                sin_cp.append({"suite": suite, "escenario": c["titulo"], "archivo": c["_archivo"]})
                continue
            x = caso(c["id"])
            x["titulo"] = x["titulo"] or c["titulo"]
            x["automatizado"].append({"suite": suite, "archivo": c["_archivo"], "bloqueado": "bloqueado" in tags,
                                      "falta_info": "falta-info" in tags})
            x["criterios"].update(_ca(n) for n in RE_CA.findall(" ".join(c["etiquetas"])))
            x["falta_info"].update(t.upper() for t in c["etiquetas"] if re.fullmatch(r"FI-\d+", t, re.I))

    # ---- gestión
    herramientas_gestion = []
    for a in sorted(glob.glob(str(PROYECTO / "output" / "gestion" / f"{hu}-*.json"))):
        try:
            t = json.loads(_leer(a))
        except ValueError:
            continue
        herr = t.get("herramienta") or Path(a).stem.split("-", 2)[-1]
        herramientas_gestion.append(herr)
        for cp, v in (t.get("casos") or {}).items():
            caso(cp)["gestion"][herr] = v.get("key") or v.get("id")

    # ---- resultados (el más reciente gana)
    for r in sorted(rec.de_ejecuciones(hu) + rec.de_cucumber(hu), key=lambda r: r.get("momento") or 0):
        if r.get("id") and RE_CP.fullmatch(str(r["id"])):
            caso(r["id"])["resultado"] = {"estado": r["estado"], "fuente": r["fuente"],
                                          "fecha": datetime.datetime.fromtimestamp(r["momento"]).isoformat(timespec="minutes") if r.get("momento") else ""}

    # ---- bugs
    bugs = []
    for b in rec.de_bugs(hu):
        archivo = PROYECTO / "output" / "reportes-bug" / f'{b["id"]}.md'
        cps = sorted(set(m.group(0) for m in RE_CP.finditer(_leer(archivo)))) if archivo.exists() else []
        b["casos"] = cps
        bugs.append(b)
        for cp in cps:
            if cp in casos:
                casos[cp]["bugs"].append(b["id"])

    # ---- falta información (ficha de contexto)
    ficha = _leer(PROYECTO / "output" / "contexto" / f"contexto-{hu}.md")
    fi_abiertas = sorted({m for linea in ficha.splitlines() for m in RE_FI.findall(linea)
                          if re.search(r"abiert|pendiente|open", linea, re.I)})

    # ---- huecos
    huecos = []

    def hueco(tipo, sev, detalle, ref=""):
        huecos.append({"tipo": tipo, "severidad": sev, "detalle": detalle, "ref": ref})

    con_casos = {ca for x in casos.values() for ca in x["criterios"]}
    for ca, desc in sorted(criterios.items(), key=lambda kv: int(kv[0][2:])):
        if ca not in con_casos:
            hueco("Criterio sin casos", "Alta", f"{ca}: {desc}" if desc else ca, ca)
    for x in sorted(casos.values(), key=lambda x: x["id"]):
        prio = x["prioridad"] or "Media"
        if criterios and not x["criterios"]:
            hueco("Caso sin criterio", "Baja", f'{x["id"]} · {x["titulo"]}: no se sabe qué criterio cubre', x["id"])
        activos = [a for a in x["automatizado"] if not a["bloqueado"]]
        if not x["automatizado"] and x["fuentes"]:
            hueco("Sin automatizar", "Media" if PRIO_ORDEN.get(prio, 2) <= 1 else "Baja",
                  f'{x["id"]} · {x["titulo"]} (prioridad {prio})', x["id"])
        elif x["automatizado"] and not activos:
            hueco("Automatizado bloqueado", "Media", f'{x["id"]} · {x["titulo"]}: tiene @bloqueado, no se ejecuta', x["id"])
        if activos and not x["resultado"]:
            hueco("Automatizado sin resultado", "Media", f'{x["id"]} · {x["titulo"]}: no aparece en ninguna corrida', x["id"])
        if x["resultado"] and x["resultado"]["estado"] == "Fallido":
            hueco("Último resultado fallido", "Alta", f'{x["id"]} · {x["titulo"]} ({x["resultado"]["fuente"]})', x["id"])
        if herramientas_gestion and not x["gestion"] and x["fuentes"]:
            hueco("Sin subir a gestión", "Baja", f'{x["id"]} · {x["titulo"]}: no está en {", ".join(herramientas_gestion)}', x["id"])
    for fi in fi_abiertas:
        hueco("Falta información abierta", "Media", f"{fi}: sin respuesta en la ficha de contexto", fi)
    for s in sin_cp:
        hueco("Escenario sin @CP", "Baja", f'{s["escenario"]} ({s["suite"]}, {s["archivo"]}): no se puede trazar', s["archivo"])
    huecos.sort(key=lambda h: SEV_ORDEN[h["severidad"]])

    lista = []
    for x in sorted(casos.values(), key=lambda x: (int(re.sub(r"\D", "", x["id"]) or 0))):
        x["criterios"] = sorted(x["criterios"], key=lambda c: int(c[2:]))
        x["falta_info"] = sorted(x["falta_info"])
        lista.append(x)
    n = len(lista)
    automat = [x for x in lista if any(not a["bloqueado"] for a in x["automatizado"])]
    con_res = [x for x in lista if x["resultado"]]
    aprob = [x for x in con_res if x["resultado"]["estado"] == "Aprobado"]
    return {
        "historia": hu, "origen_criterios": origen_ca, "herramientas_gestion": herramientas_gestion,
        "criterios": [{"id": k, "descripcion": v, "casos": sorted(x["id"] for x in lista if k in x["criterios"])}
                      for k, v in sorted(criterios.items(), key=lambda kv: int(kv[0][2:]))],
        "casos": lista, "bugs": bugs, "falta_info_abierta": fi_abiertas, "escenarios_sin_cp": sin_cp, "huecos": huecos,
        "metricas": {
            "criterios": len(criterios), "criterios_cubiertos": len([c for c in criterios if c in con_casos]),
            "casos": n, "automatizados": len(automat), "con_resultado": len(con_res), "aprobados": len(aprob),
            "fallidos": len([x for x in con_res if x["resultado"]["estado"] == "Fallido"]),
            "bugs_abiertos": len([b for b in bugs if b["estado"].lower() in rec.ABIERTOS]),
        },
    }


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Matriz de cobertura y trazabilidad por historia")
    ap.add_argument("--historia", help="HU-XXX (por defecto, todas las que encuentre)")
    ap.add_argument("--criterios", help='JSON {"HU-001": [{"id": "CA1", "descripcion": "..."}]} (p. ej., leídos de Jira)')
    ap.add_argument("--salida", help="carpeta (por defecto output/cobertura/<HU o todas>)")
    ap.add_argument("--analisis", help="analisis.json del agente (por defecto, el de la carpeta si existe)")
    ap.add_argument("--solo-informe", action="store_true", help="regenera el informe con el análisis, sin recalcular")
    ap.add_argument("--raiz", help=argparse.SUPPRESS)  # otra raíz de proyecto (tests y demos)
    a = ap.parse_args()
    if a.raiz:
        global PROYECTO
        PROYECTO = Path(a.raiz).resolve()
        rec.PROYECTO, rec.K0 = PROYECTO, PROYECTO / "herramientas" / "k0lmena" / "reports"
    hu = a.historia.upper() if a.historia else None
    if hu and not re.fullmatch(r"HU-\d+", hu):
        sys.exit("--historia tiene que ser un ID como HU-001.")
    carpeta = Path(a.salida) if a.salida else PROYECTO / "output" / "cobertura" / (hu or "todas")
    carpeta.mkdir(parents=True, exist_ok=True)
    datos_arch = carpeta / "cobertura.json"
    if not a.solo_informe:
        _historial.archivar(carpeta, ["cobertura.json", "analisis.json", "informe-cobertura.html"], "cobertura.json")
        extra = json.loads(Path(a.criterios).read_text(encoding="utf-8")) if a.criterios else {}
        historias = [hu] if hu else historias_presentes()
        if not historias:
            sys.exit("No encontré historias (HU-XXX) en input/, output/ ni en la automatización de k0lmena.")
        datos = {"fecha": datetime.datetime.now().isoformat(timespec="seconds"), "alcance": hu or "todas",
                 "historias": [analizar_historia(h, extra) for h in historias]}
        # IDs de huecos únicos en todo el informe (C-01, C-02…), los más graves primero.
        todos = sorted((x for h in datos["historias"] for x in h["huecos"]), key=lambda x: SEV_ORDEN[x["severidad"]])
        for i, x in enumerate(todos):
            x["id"] = f"C-{i + 1:02d}"
        datos_arch.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        (carpeta / "analisis.json").unlink(missing_ok=True) if not a.analisis else None
        for h in datos["historias"]:
            m = h["metricas"]
            print(f'{h["historia"]}: criterios {m["criterios_cubiertos"]}/{m["criterios"]} · casos {m["casos"]} · automatizados {m["automatizados"]}'
                  f' · con resultado {m["con_resultado"]} · aprobados {m["aprobados"]} · huecos {len(h["huecos"])}')
    args = [sys.executable, str(Path(__file__).resolve().parent / "generar_informe_cobertura.py"), str(datos_arch), str(carpeta / "informe-cobertura.html")]
    analisis = Path(a.analisis) if a.analisis else carpeta / "analisis.json"
    if analisis.exists():
        args += ["--analisis", str(analisis)]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:  # p. ej. un analisis.json mal formado: el agente tiene que enterarse, no seguir de largo
        print(r.stderr.strip() or r.stdout.strip(), file=sys.stderr)
        sys.exit("No se pudo armar el informe HTML (revisá el analisis.json).")
    print(r.stdout.strip() or r.stderr.strip())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Portal de informes: output/index.html (abre output/es/index.html u output/en/index.html, según el idioma elegido)
con todos los informes y su historial.

Uso (desde la raíz del repo):
    python scripts/portal_informes.py [--abrir]

Recorre output/ (cada carpeta es una herramienta: ejecuciones, exploratorias, accesibilidad, …; las que
se agreguen después aparecen solas) y los reportes de k0lmena (herramientas/k0lmena/reports/). Antes arma el
HTML de los artefactos de los agentes que no tienen informe propio (casos, bugs, análisis…).

El portal tiene un menú por categoría (Pruebas automatizadas, Ejecuciones, Diseño de pruebas, Bugs, Calidad y
cierre, Web, Seguridad, Plataformas, Documentación): cada una lista todos sus informes, el último de cada
historia, sitio o suite y cada corrida guardada en historial/, con su fecha, el veredicto o resultado si el JSON
lo trae y los links a la versión en español y en inglés. Filtros por texto, herramienta, historia, estado y
rango de fechas, con o sin el historial; de a 100 filas.

Los links son relativos: output/index.html se abre con doble clic, sin servidor.

Se regenera solo: cada informe HTML que arman los scripts (con _estilos_reporte.page) lo actualiza al
terminar. Para desactivarlo, K0LMENIA_PORTAL=0 en el entorno.
"""
import argparse
import atexit
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
sys.path.insert(0, str(RAIZ / "scripts"))
from _i18n import escribir_bilingue  # noqa: E402

# Nombres legibles de las carpetas conocidas (las demás se muestran con su nombre capitalizado).
NOMBRES = {
    "ejecuciones": "Ejecuciones (E2E y API)", "triage": "Triage de bugs",
    "evals": "Evals de los agentes", "k0lmena": "npm test (k0lmena)", "metricas-tokens": "Uso de tokens",
    "novedades": "Novedades", "ejecucion-manual": "Ejecución manual", "conectores": "Conectores MCP",
    "casos-de-prueba": "Casos de prueba", "revision-casos": "Revisión de casos",
    "analisis-historias": "Análisis de historias", "contexto": "Fichas de contexto", "reportes-bug": "Reportes de bug",
    "mapeos": "Mapeos a automatización", "gestion": "Gestión de pruebas",
    "entorno": "Puesta en marcha", "conocimiento": "Base de conocimiento", "documentacion": "Documentación del proyecto",
}
# Orden de las tarjetas: primero lo que más se mira.
ORDEN = ["ejecuciones", "k0lmena", "ejecucion-manual", "revision-casos", "triage", "evals"]
IGNORAR = {"historial", "evidencia", "capturas", "videos", "recortes", "diferencias", "lighthouse", "referencia",
           "actual", "respaldo", "suite", "eml", "sesiones", "node_modules",
           "es", "en"}  # las versiones por idioma: el informe se indexa por su acceso (unidad/informe.html)
_SELLO = re.compile(r"[-_]?\d{4}-?\d{2}-?\d{2}([-_T]?\d{2}-?\d{2}(-?\d{2})?)?$")


def _fecha(p):
    return datetime.fromtimestamp(p.stat().st_mtime)


def _htmls(carpeta):
    """Los .html de la carpeta, sin entrar a historial/ ni a las carpetas de evidencia."""
    for raiz, dirs, archivos in os.walk(carpeta):
        dirs[:] = [d for d in dirs if d not in IGNORAR and not d.startswith((".", "_"))]
        for a in archivos:
            # Las versiones en es/ y en/ van con su informe (su acceso), no como informes aparte.
            if a.lower().endswith(".html") and not a.lower().endswith(".en.html"):
                yield Path(raiz) / a


def _reporte_k0(p):
    """El reporte completo de k0lmena (index.html de npm run report:<suite>, al lado del cucumber-report.json)."""
    return p.name.lower() == "index.html" and (p.parent / "cucumber-report.json").exists()


def _principal(archivos):
    """De varios .html de una misma unidad, el informe principal más reciente."""
    def peso(p):
        n = p.name.lower()
        return (_reporte_k0(p), n.startswith(("informe-", "reporte-", "cierre-", "plan-", "cucumber")), p.stat().st_mtime)
    return max(archivos, key=peso)


def _leer_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def estado_de(html):
    """Veredicto o resultado de un informe, desde los JSON que tiene al lado (o "")."""
    carpeta = html.parent
    candidatos = [carpeta / "analisis.json"]
    stem = html.stem
    for pref in ("reporte-", "cierre-", "plan-"):
        if stem.startswith(pref):
            candidatos.append(carpeta / f"_resultados-{stem[len(pref):]}.json")
            candidatos.append(carpeta / f"{stem}.json")
    candidatos += sorted(p for p in carpeta.glob("*.json") if p not in candidatos)
    for c in candidatos:
        d = _leer_json(c) if c.exists() else None
        if not isinstance(d, dict):
            continue
        if d.get("veredicto"):
            return str(d["veredicto"])
        casos = d.get("casos")
        if isinstance(casos, list) and casos and isinstance(casos[0], dict) and "estado" in casos[0]:
            ok = sum(1 for x in casos if str(x.get("estado", "")).lower() == "aprobado")
            return f"{ok}/{len(casos)} aprobados"
    if html.name.startswith("cucumber") or (carpeta / "cucumber-report.json").exists():
        d = _leer_json(carpeta / "cucumber-report.json")
        if isinstance(d, list):
            total = ok = 0
            for f in d:
                for esc in f.get("elements") or []:
                    if esc.get("type") == "background":
                        continue
                    total += 1
                    estados = [(p.get("result") or {}).get("status") for p in esc.get("steps") or []]
                    ok += bool(estados) and all(s in ("passed", "skipped") for s in estados) and "passed" in estados
            if total:
                return f"{ok}/{total} escenarios aprobados"
    return ""


def _anterior(carpeta_unidad):
    """(cantidad de corridas guardadas, el informe de la más reciente) de historial/."""
    h = carpeta_unidad / "historial"
    if not h.is_dir():
        return 0, None
    corridas = sorted((d for d in h.iterdir() if d.is_dir()), key=lambda d: d.name)
    if not corridas:
        return 0, None
    ultima = corridas[-1]
    informes = sorted(ultima.rglob("*.html"))
    return len(corridas), (_principal(informes) if informes else None)


def unidades(carpeta):
    """Informes de una herramienta: [{"unidad", "html", "fecha", "estado", "historial", "anterior", "otros"}]."""
    grupos = {}
    for html in _htmls(carpeta):
        rel = html.relative_to(carpeta)
        if len(rel.parts) > 1:
            clave, base = rel.parts[0], carpeta / rel.parts[0]
        else:
            clave = _SELLO.sub("", html.stem) or html.stem
            m = re.search(r"(HU-\d+|API|CP-API)", html.stem, re.I)
            clave = m.group(1).upper() if m and html.stem.startswith(("reporte-", "cierre-", "plan-")) else clave
            base = carpeta
        grupos.setdefault(clave, {"base": base, "htmls": []})["htmls"].append(html)
    salida = []
    for clave, g in grupos.items():
        html = _principal(g["htmls"])
        n, anterior = _anterior(g["base"]) if g["base"] != carpeta else (0, None)
        otros = sorted({h for h in g["htmls"] if h != html and h.parent == html.parent}, key=lambda p: p.name)
        salida.append({"unidad": clave, "html": html, "fecha": _fecha(html), "estado": estado_de(html),
                       "historial": n, "anterior": anterior, "otros": otros})
    return sorted(salida, key=lambda u: u["fecha"], reverse=True)


def descubrir(output, reportes_k0=None, evals=None):
    """{herramienta: [unidades]} de todas las carpetas de output/ (y npm test), con o sin informes."""
    herramientas = {}
    if output.is_dir():
        # es/ y en/ son las versiones por idioma del propio portal (output/es/index.html): no son herramientas.
        for d in sorted(p for p in output.iterdir() if p.is_dir() and not p.name.startswith((".", "_")) and p.name not in ("es", "en")):
            herramientas[d.name] = unidades(d)
    if reportes_k0 and Path(reportes_k0).is_dir():
        k0 = []
        for suite in sorted(p for p in Path(reportes_k0).iterdir() if p.is_dir()):
            us = unidades(suite)
            # El reporte completo (index.html + features/) y el básico de Cucumber son la misma corrida:
            # una sola entrada, la del completo, con el básico como "otro" y sin las páginas de features/.
            completo = next((u for u in us if _reporte_k0(u["html"]) and u["html"].parent == suite), None)
            if completo:
                basicos = [u["html"] for u in us if u is not completo and u["html"].parent == suite]
                completo["otros"] = sorted(set(completo["otros"]) | set(basicos), key=lambda p: p.name)
                us = [u for u in us if u is completo or (u["html"].parent != suite and u["unidad"] != "features")]
            for u in us:
                u["unidad"] = suite.name if u["unidad"] in (Path(u["html"]).stem, "cucumber-report", "index") else f'{suite.name} · {u["unidad"]}'
                if u["html"].parent == suite:
                    u["historial"], u["anterior"] = _anterior(suite)
                k0.append(u)
        herramientas["k0lmena"] = sorted(k0, key=lambda u: u["fecha"], reverse=True)
    if evals and Path(evals).is_dir():  # los evals de los agentes escriben en evals/resultados/<fecha>/
        herramientas["evals"] = unidades(Path(evals))
    orden = {n: i for i, n in enumerate(ORDEN)}
    return dict(sorted(herramientas.items(), key=lambda kv: (orden.get(kv[0], len(ORDEN)), kv[0])))


def _tono(estado):
    t = (estado or "").lower()
    m = re.match(r"(\d+)/(\d+)", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return "ok" if a == b else "bad" if a < b * 0.8 else "warn"
    if re.search(r"no apto|no-go|no go|crític|critic|bloque|falla|rechaz|alto riesgo|riesgo alto", t):
        return "bad"
    if re.search(r"observacion|revisar|riesgo|parcial|condicion|atenci|medio", t):
        return "warn"
    if re.search(r"apto|\bgo\b|en orden|aprobad|ok|sin hallazgos|cumple", t):
        return "ok"
    return ""


_HISTORIA = re.compile(r"\b([A-Z][A-Z0-9]{0,9}-\d+)\b")


def historia_de(u):
    """La historia de un informe (HU-001, PROJ-12…) sacada de la unidad o de la ruta; si no hay, la unidad."""
    for texto in [u.get("unidad", "")] + list(Path(u["html"]).parts[::-1]):
        m = _HISTORIA.search(str(texto))
        if m and not m.group(1).startswith(("CP-API", "BUG-", "FI-")):
            return m.group(1)
    return u.get("unidad") or "—"


TONO_TEXTO = {"ok": "En orden", "warn": "Revisar", "bad": "Crítico", "": "Sin estado"}

# Menú del portal: cada carpeta de output/ (y npm test) cae en una categoría. Lo que no está, en "Otros".
CATEGORIAS = [
    ("automatizadas", "Pruebas automatizadas", ["k0lmena"]),
    ("ejecuciones", "Ejecuciones", ["ejecucion-manual", "ejecuciones"]),
    ("diseno", "Diseño de pruebas", ["analisis-historias", "casos-de-prueba", "contexto", "revision-casos", "mapeos"]),
    ("bugs", "Bugs", ["reportes-bug", "triage"]),
    ("calidad", "Calidad y cierre", ["gestion", "metricas-tokens", "evals"]),
    ("documentacion", "Documentación", ["novedades", "entorno", "conectores", "documentacion", "conocimiento"]),
]
CATEGORIA_DE = {h: c for c, _, hs in CATEGORIAS for h in hs}


def categoria_de(herramienta):
    return CATEGORIA_DE.get(herramienta, "otros")


def _fecha_corrida(carpeta, html):
    """La fecha de una corrida guardada en historial/ (del nombre de la carpeta, 2026-10-01T10-00-00) o la del archivo."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:[T_ -](\d{2})-?(\d{2})(?:-?(\d{2}))?)?", carpeta.name)
    if m:
        try:
            return datetime(*(int(x) for x in m.groups(default="0")))
        except ValueError:
            pass
    return _fecha(html)


def estado_en(html):
    """El veredicto en inglés (bloque "en" del analisis.json), si el agente lo escribió."""
    carpeta = Path(html).parent
    carpeta = carpeta.parent if carpeta.name in ("es", "en") else carpeta
    d = _leer_json(carpeta / "analisis.json")
    en = d.get("en") if isinstance(d, dict) else None
    return str(en["veredicto"]) if isinstance(en, dict) and en.get("veredicto") else ""


def versiones(html):
    """(versión en español, versión en inglés o None) de un informe. Con la estructura por idioma son es/<x> y en/<x>;
    los informes viejos (un solo archivo) se muestran como están."""
    from _i18n import ruta_en, ruta_es
    es, en = ruta_es(html), ruta_en(html)
    return (es if es.exists() else Path(html)), (en if en.exists() else None)


def entradas(herramientas):
    """Todos los informes en una lista plana: el último de cada unidad y cada corrida guardada en historial/."""
    salida = []
    for h, us in herramientas.items():
        for u in us:
            html_es, html_en = versiones(u["html"])
            salida.append({"herramienta": h, "categoria": categoria_de(h), "unidad": u["unidad"], "historia": historia_de(u),
                           "html": html_es, "html_en": html_en, "fecha": u["fecha"],
                           "estado": u["estado"], "estado_en": estado_en(u["html"]), "tono": _tono(u["estado"]), "anterior": False,
                           "otros": u.get("otros") or []})
            base = Path(u["html"]).parent
            historial = base / "historial"
            if u.get("historial") and historial.is_dir():
                for corrida in sorted((d for d in historial.iterdir() if d.is_dir()), key=lambda d: d.name, reverse=True):
                    informes = [p for p in corrida.rglob("*.html")
                                if not p.name.lower().endswith(".en.html") and p.parent.name not in ("es", "en")]
                    if not informes:
                        continue
                    html = _principal(informes)
                    html_es, html_en = versiones(html)
                    estado = estado_de(html)
                    salida.append({"herramienta": h, "categoria": categoria_de(h), "unidad": u["unidad"],
                                   "historia": historia_de(u), "html": html_es, "html_en": html_en,
                                   "fecha": _fecha_corrida(corrida, html), "estado": estado, "estado_en": estado_en(html),
                                   "tono": _tono(estado),
                                   "anterior": True, "otros": []})
    return sorted(salida, key=lambda x: x["fecha"], reverse=True)


# ------------------------------------------------------------------ tablero de inicio
# Herramientas cuyo último veredicto se muestra arriba, si existen (en este orden).
CLAVE = []
_SEV_ALTA = ("crítica", "critica", "alta", "critical", "high")


def _cucumber(arch):
    """(total, aprobados, fallidos) de un cucumber-report.json."""
    d = _leer_json(arch)
    total = ok = mal = 0
    for f in d if isinstance(d, list) else []:
        for esc in f.get("elements") or []:
            if esc.get("type") == "background":
                continue
            estados = [(p.get("result") or {}).get("status") for p in esc.get("steps") or []]
            total += 1
            if any(x in ("failed", "ambiguous") for x in estados):
                mal += 1
            elif estados and "passed" in estados and all(x in ("passed", "skipped") for x in estados):
                ok += 1
    return total, ok, mal


def suites_npm(herramientas):
    """Cada suite de npm test con su última corrida y la serie de % aprobado de las corridas guardadas (vieja → nueva)."""
    salida, vistas = [], set()
    for u in herramientas.get("k0lmena") or []:
        suite = Path(u["html"]).parent
        rep = suite / "cucumber-report.json"
        if suite in vistas or not rep.exists():
            continue
        vistas.add(suite)
        total, ok, mal = _cucumber(rep)
        if not total:
            continue
        serie = []
        h = suite / "historial"
        if h.is_dir():
            for c in sorted((d for d in h.iterdir() if d.is_dir()), key=lambda d: d.name):
                t2, o2, _ = _cucumber(c / "cucumber-report.json") if (c / "cucumber-report.json").exists() else (0, 0, 0)
                if t2:
                    serie.append(round(o2 / t2 * 100))
        pct = round(ok / total * 100)
        salida.append({"suite": suite.name, "total": total, "aprobados": ok, "fallidos": mal, "pct": pct, "serie": serie + [pct],
                       "html": u["html"], "fecha": u["fecha"]})
    return salida


def _campo_md(texto, nombre):
    m = re.search(rf"\*\*{nombre}[^*]*:\*\*\s*(.+)", texto)
    return re.sub(r"[`*]", "", m.group(1)).strip() if m else ""


_CERRADO = re.compile(r"(cerrad|resuelt|done|closed|fixed|corregid|verificad|rechazad|duplicad|won.?t)", re.I)


def bugs_abiertos(output):
    """Bugs abiertos del proyecto: los reportes de output/reportes-bug y, si hay, los de las métricas de QA (sin repetir IDs)."""
    vistos = {}
    for arch in sorted(Path(output).glob("reportes-bug/**/BUG-*.md")):
        texto = arch.read_text(encoding="utf-8", errors="ignore")
        bid = (_campo_md(texto, "ID").split() or [arch.stem])[0]
        estado = _campo_md(texto, "Estado")
        sev = _campo_md(texto, "Criticidad / Severidad") or _campo_md(texto, "Severidad")
        vistos[bid] = {"abierto": not _CERRADO.search(estado or ""), "severidad": sev.lower()}
    metricas = sorted(Path(output).glob("metricas/*/datos.json"), key=lambda p: p.stat().st_mtime)
    if metricas:
        d = _leer_json(metricas[-1]) or {}
        for b in d.get("bugs") or []:
            if isinstance(b, dict) and b.get("id"):
                vistos[str(b["id"])] = {"abierto": b.get("abierto", True) is not False, "severidad": str(b.get("severidad", "")).lower()}
    if not vistos:
        return None
    abiertos = [b for b in vistos.values() if b["abierto"]]
    return {"abiertos": len(abiertos), "graves": sum(1 for b in abiertos if b["severidad"].startswith(_SEV_ALTA)), "total": len(vistos)}


def _carpeta_datos(html):
    c = Path(html).parent
    return c.parent if c.name in ("es", "en") else c


def hallazgos_graves(html):
    """Cuántos hallazgos críticos o altos declara el analisis.json (o el JSON principal) de un informe."""
    n = 0
    for arch in [_carpeta_datos(html) / "analisis.json"]:
        d = _leer_json(arch) if arch.exists() else None
        if isinstance(d, dict) and isinstance(d.get("hallazgos"), list):
            n += sum(1 for h in d["hallazgos"] if isinstance(h, dict) and str(h.get("severidad", "")).lower().startswith(("crítica", "critica")))
    return n


CSS_PORTAL = """
.fuera{display:none!important}
.filtros{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;padding:16px 18px;margin-bottom:18px;border:1px solid var(--line);
  border-radius:16px;background:var(--surface);grid-column:span 12}
.filtros label{display:flex;flex-direction:column;gap:5px;font-family:var(--mono);font-size:11px;color:var(--muted);text-transform:lowercase}
.filtros input,.filtros select{font:inherit;font-family:var(--sans);font-size:13px;color:var(--ink);background:var(--bg);
  border:1px solid var(--line);border-radius:10px;padding:8px 11px;min-width:150px}
.filtros input[type=date]{min-width:0;color-scheme:dark}
.filtros input:focus,.filtros select:focus{outline:none;border-color:var(--linea-amarilla);box-shadow:var(--glow-k0)}
.filtros .grupo-btn{display:flex;gap:6px;flex-wrap:wrap}
.filtros button{font:inherit;font-size:12px;font-weight:500;color:var(--body);background:var(--bg);border:1px solid var(--line);
  border-radius:8px;padding:7px 11px;cursor:pointer}
.filtros button.on{color:#0E0C09;background:var(--accent);border-color:var(--accent);font-weight:600}
.filtros .check{flex-direction:row;align-items:center;gap:7px;text-transform:none;font-family:var(--sans);font-size:12.5px;color:var(--body);padding-bottom:8px}
.filtros .check input{min-width:0;accent-color:var(--accent)}
.filtros .cuenta{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--muted);padding-bottom:8px}
.filtros .limpiar{background:transparent;border-style:dashed}
.portal-cat .tablecard td{vertical-align:middle}
.portal-cat .tablecard td:first-child,.portal-cat .tablecard td:last-child{white-space:nowrap}
.ver-mas{display:block;margin:12px auto 4px;font:inherit;font-size:12.5px;color:var(--ink);background:var(--tile);border:1px solid var(--line-2);
  border-radius:10px;padding:8px 16px;cursor:pointer}
.idiomas-inf{display:inline-flex;gap:6px;margin-left:8px;font-family:var(--mono);font-size:10.5px}
.idiomas-inf a{padding:1px 6px;border:1px solid var(--line-2);border-radius:6px;color:var(--muted);text-decoration:none}
.idiomas-inf a:hover{color:var(--ink);border-color:var(--linea-amarilla)}
.etq-hist{font-family:var(--mono);font-size:10.5px;color:var(--muted);border:1px dashed var(--line-2);border-radius:6px;padding:1px 6px}
.nav a.cat-on{color:var(--ink)}
.tb-alertas{display:flex;flex-direction:column;gap:8px;padding:6px 22px 20px}
.tb-alerta{display:flex;align-items:center;gap:12px;padding:11px 14px;border-radius:12px;border:1px solid var(--line);
  background:var(--tile);color:var(--body);text-decoration:none;font-size:13.5px}
.tb-alerta:hover{border-color:var(--linea-amarilla)}
.tb-alerta .ic{flex:0 0 26px;height:26px;border-radius:8px;display:grid;place-items:center;font-weight:700;font-size:13px}
.tb-alerta.bad .ic{background:rgba(255,90,78,.14);color:#FF5A4E}.tb-alerta.warn .ic{background:rgba(255,214,10,.14);color:#FFD60A}
.tb-alerta b{color:var(--ink);font-weight:600}.tb-alerta .cuando{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--muted);white-space:nowrap}
.tb-ok{margin:6px 22px 20px;padding:12px 14px;border-radius:12px;border:1px solid rgba(92,191,74,.35);background:rgba(92,191,74,.08);color:#B8E6AE;font-size:13.5px}
.tb-claves{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;padding:6px 22px 20px}
.tb-clave{display:block;padding:14px 15px;border-radius:14px;border:1px solid var(--line);background:var(--tile);text-decoration:none;color:var(--body)}
.tb-clave:hover{border-color:var(--linea-amarilla)}
.tb-clave .t{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.tb-clave .v{margin:8px 0 6px;font-size:14px;color:var(--ink);line-height:1.35}
.tb-clave .f{font-family:var(--mono);font-size:11px;color:var(--muted)}
.tb-cats{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;padding:6px 22px 22px}
.tb-cat{border:1px solid var(--line);border-radius:16px;background:var(--tile);padding:15px 16px;display:flex;flex-direction:column;gap:10px}
.tb-cat h3{margin:0;font-family:var(--display);font-size:16px;color:var(--ink);display:flex;align-items:center;gap:8px}
.tb-cat h3 .n{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--muted);font-weight:400}
.tb-cat ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:7px}
.tb-cat li{display:flex;flex-direction:column;gap:4px;font-size:13.5px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.tb-cat li:last-child{border-bottom:0;padding-bottom:0}
.tb-cat li a{color:var(--ink);text-decoration:none;font-weight:500}
.tb-cat li a:hover{color:var(--accent)}
.tb-cat li .m{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px}
.tb-cat li .f{font-family:var(--mono);font-size:10.5px;color:var(--muted)}
.tb-cat .ver{align-self:flex-start;font-size:12.5px;color:var(--accent);text-decoration:none}
.tb-cat .tono{font-family:var(--mono);font-size:10.5px;padding:2px 7px;border-radius:999px;border:1px solid var(--line-2);color:var(--muted);white-space:nowrap}
.tb-cat .tono.ok{color:#5CBF4A;border-color:rgba(92,191,74,.4)}.tb-cat .tono.warn{color:#FFD60A;border-color:rgba(255,214,10,.4)}
.tb-cat .tono.bad{color:#FF5A4E;border-color:rgba(255,90,78,.45)}
.tb-buscar{display:flex;gap:10px;align-items:center;padding:6px 22px 22px}
.tb-buscar input{flex:1;font:inherit;font-size:14px;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:11px 14px}
.tb-buscar input:focus{outline:none;border-color:var(--linea-amarilla);box-shadow:var(--glow-k0)}
.tb-buscar a{white-space:nowrap;font-size:13px;color:var(--accent);text-decoration:none}
@media (max-width:700px){.tb-cats,.tb-claves{grid-template-columns:1fr}.tb-alerta{flex-wrap:wrap}.tb-alerta .cuando{margin-left:38px}}
"""

# Menú por categoría (usa el índice lateral de page(): un clic muestra solo esa categoría), filtros por texto,
# herramienta, historia, estado y rango de fechas, historial sí/no y paginado de a 100 filas.
JS_PORTAL = r"""
(function(){
var f=document.getElementById('filtros');if(!f)return;
var cats=[].slice.call(document.querySelectorAll('.portal-cat')),nav=document.getElementById('nav');
var q=f.querySelector('[name=q]'),herr=f.querySelector('[name=herr]'),hist=f.querySelector('[name=hist]'),
    desde=f.querySelector('[name=desde]'),hasta=f.querySelector('[name=hasta]'),conHist=f.querySelector('[name=conhist]'),cuenta=f.querySelector('.cuenta');
var tono='',activa=null,limite={},PAG=100,TXT=JSON.parse(f.getAttribute('data-txt'));
function sinAcentos(t){return (t||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');}
function opciones(sel,valores,todas){var v=sel.value;sel.innerHTML='<option value="">'+todas+'</option>'+valores.map(function(x){
  return '<option value="'+x.replace(/"/g,'&quot;')+'">'+x.replace(/</g,'&lt;')+'</option>';}).join('');if(valores.indexOf(v)>=0)sel.value=v;}
function filas(){return activa?[].slice.call(activa.querySelectorAll('tr.pr')):[];}
function mostrar(id){activa=document.getElementById(id)||cats[0];cats.forEach(function(c){c.classList.toggle('fuera',c!==activa);});
  if(nav)[].forEach.call(nav.querySelectorAll('a'),function(a){a.classList.toggle('on',a.getAttribute('href')==='#'+activa.id);});
  var hs={},us={};filas().forEach(function(tr){hs[tr.dataset.herrNombre]=tr.dataset.herr;us[tr.dataset.hist]=1;});
  opciones(herr,Object.keys(hs).sort(),TXT.todas);[].forEach.call(herr.options,function(o){if(o.value)o.value=hs[o.textContent];});
  opciones(hist,Object.keys(us).sort(),TXT.todas);f.classList.toggle('fuera',activa.dataset.inicio==='1');aplicar();}
function aplicar(){
  if(!activa)return;var txt=sinAcentos(q.value.trim()),d0=desde.value?Date.parse(desde.value+'T00:00:00'):0,
    d1=hasta.value?Date.parse(hasta.value+'T23:59:59'):0,n=0,vis=0,max=limite[activa.id]||PAG;
  filas().forEach(function(tr){var fe=parseInt(tr.dataset.fecha,10);
    var ok=(!herr.value||tr.dataset.herr===herr.value)&&(!hist.value||tr.dataset.hist===hist.value)&&(!tono||tr.dataset.tono===tono)
      &&(!d0||fe>=d0)&&(!d1||fe<=d1)&&(conHist.checked||tr.dataset.anterior!=='1')&&(!txt||sinAcentos(tr.textContent).indexOf(txt)>=0);
    if(ok)n++;tr.classList.toggle('fuera',!ok||n>max);if(ok&&n<=max)vis++;});
  var mas=activa.querySelector('.ver-mas');if(mas)mas.classList.toggle('fuera',n<=max);
  var vacio=activa.querySelector('.vacio-filtro');if(vacio)vacio.classList.toggle('fuera',n>0);
  cuenta.textContent=TXT.cuenta.replace('{v}',vis).replace('{n}',n);
  try{localStorage.setItem('k0-portal2',JSON.stringify({q:q.value,desde:desde.value,hasta:hasta.value,conhist:conHist.checked,tono:tono,cat:activa.id}));}catch(e){}
}
function rango(dias){var h=new Date(),d=new Date(Date.now()-dias*86400000);function iso(x){return x.toISOString().slice(0,10);}
  desde.value=dias?iso(d):'';hasta.value='';}
f.addEventListener('input',aplicar);f.addEventListener('change',aplicar);
f.addEventListener('click',function(ev){var b=ev.target.closest('button');if(!b)return;ev.preventDefault();
  if(b.dataset.tono!==undefined){tono=b.dataset.tono;[].forEach.call(f.querySelectorAll('[data-tono]'),function(x){x.classList.toggle('on',x===b);});}
  if(b.dataset.dias!==undefined)rango(parseInt(b.dataset.dias,10));
  if(b.classList.contains('limpiar')){q.value='';herr.value='';hist.value='';desde.value='';hasta.value='';tono='';conHist.checked=true;
    [].forEach.call(f.querySelectorAll('[data-tono]'),function(x){x.classList.toggle('on',x.dataset.tono==='');});}
  aplicar();});
document.addEventListener('click',function(ev){var m=ev.target.closest('.ver-mas');if(m){limite[activa.id]=(limite[activa.id]||PAG)+PAG;aplicar();return;}
  var a=ev.target.closest('#nav a, a.ir-cat');if(!a)return;var id=(a.getAttribute('href')||'').slice(1);
  if(!document.getElementById(id)||!document.getElementById(id).classList.contains('portal-cat'))return;
  ev.preventDefault();history.replaceState(null,'','#'+id);mostrar(id);window.scrollTo(0,0);},true);
var bt=document.getElementById('buscar-todo');
if(bt)bt.addEventListener('input',function(){if(!document.getElementById('cat-todos'))return;q.value=bt.value;history.replaceState(null,'','#cat-todos');
  mostrar('cat-todos');q.focus();bt.value='';});
var g=null;try{g=JSON.parse(localStorage.getItem('k0-portal2')||'null');}catch(e){}
if(g){q.value=g.q||'';desde.value=g.desde||'';hasta.value=g.hasta||'';conHist.checked=g.conhist!==false;tono=g.tono||'';
  [].forEach.call(f.querySelectorAll('[data-tono]'),function(x){x.classList.toggle('on',x.dataset.tono===tono);});}
mostrar((location.hash||'').slice(1)||(g&&g.cat)||(cats[0]&&cats[0].id));
setTimeout(function(){window.scrollTo(0,0);},0);
})();
"""


def armar_html(herramientas, destino):
    """El portal en el idioma actual (_i18n): cada link va a la versión de ese idioma (es/ o en/); si un informe no
    tiene versión en inglés (uno viejo), el portal en inglés lleva a la que hay."""
    from _estilos_reporte import page, meta, kpi_tiles, e, _pastilla, OK, AVISO, CRITICO, NEUTRO
    from _i18n import idioma_actual, t

    en = idioma_actual() == "en"
    dir_html = Path(destino).resolve().parent

    def rel(p):
        try:
            return os.path.relpath(Path(p).resolve(), dir_html).replace("\\", "/")
        except ValueError:  # otra unidad en Windows: no hay ruta relativa
            return Path(p).resolve().as_uri()

    def link(p, texto):
        return f'<a href="{e(rel(p))}">{e(texto)}</a>'

    def nombre(h):
        return NOMBRES.get(h, h.replace("-", " ").capitalize())

    todas = entradas(herramientas)
    ultimas = [x for x in todas if not x["anterior"]]
    con = sorted({x["herramienta"] for x in todas})
    vacias = [k for k, v in herramientas.items() if not v]
    malos = [x for x in ultimas if x["tono"] == "bad"]
    color = {"ok": OK, "warn": AVISO, "bad": CRITICO}
    icono = {"ok": "✓", "warn": "!", "bad": "✕"}

    def fila(x):
        texto_estado = x.get("estado_en") if en and x.get("estado_en") else x["estado"]
        estado = (_pastilla(texto_estado, color.get(x["tono"], NEUTRO), icono.get(x["tono"], "●"))
                  if x["estado"] else '<span class="muted">—</span>')
        principal = x["html_en"] if en and x["html_en"] else x["html"]
        idiomas = ""
        if x["html_en"]:
            idiomas = (f'<span class="idiomas-inf"><a href="{e(rel(x["html"]))}" title="Español">ES</a>'
                       f'<a href="{e(rel(x["html_en"]))}" title="English">EN</a></span>')
        otros = " · ".join(link(o, o.stem) for o in x["otros"][:4])
        informe = (link(principal, x["html"].name) + idiomas
                   + (f'<div class="muted" style="font-size:12px">{otros}</div>' if otros else ""))
        tipo = '<span class="etq-hist">Historial</span>' if x["anterior"] else '<span class="muted">Última corrida</span>'
        datos = (f' class="pr" data-herr="{e(x["herramienta"])}" data-herr-nombre="{e(t(nombre(x["herramienta"])))}"'
                 f' data-hist="{e(x["historia"])}" data-tono="{x["tono"]}" data-anterior="{1 if x["anterior"] else 0}"'
                 f' data-fecha="{int(x["fecha"].timestamp() * 1000)}"')
        celdas = [e(x["fecha"].strftime("%Y-%m-%d %H:%M")), f'<b>{e(nombre(x["herramienta"]))}</b>', e(x["unidad"]),
                  informe, estado, tipo]
        return f'<tr{datos}>' + "".join(f"<td>{c}</td>" for c in celdas) + "</tr>"

    def tabla(lista):
        th = "".join(f"<th>{e(c)}</th>" for c in ["Fecha", "Herramienta", "Historia / sitio / suite", "Informe", "Estado", "Corrida"])
        return (f'<div class="tablecard" data-sin-filtro><table><thead><tr>{th}</tr></thead><tbody>{"".join(fila(x) for x in lista)}</tbody></table></div>'
                f'<p class="muted vacio-filtro fuera" style="padding:14px 4px">Ningún informe coincide con los filtros.</p>'
                f'<button type="button" class="ver-mas fuera">Mostrar más</button>')

    def categoria(cid, titulo, lista, sub, inicio=False, cuerpo=None):
        extra = ' data-inicio="1"' if inicio else ""
        return (f'<section class="section portal-cat" id="cat-{cid}" data-nav="{e(titulo)}"{extra}><div class="card">'
                f'<div class="section-title"><h2>{e(titulo)}</h2><span class="sub">{e(sub)}</span></div>'
                f'{cuerpo if cuerpo is not None else tabla(lista)}</div></section>')

    ahora = datetime.now()
    hoy = sum(1 for x in ultimas if x["fecha"].date() == ahora.date())
    semana = sum(1 for x in todas if (ahora - x["fecha"]).days < 7)
    suites = suites_npm(herramientas)
    bugs = bugs_abiertos(dir_html)

    def chip_tono(tono, texto):
        return f'<span class="tono {tono}">{e(icono.get(tono, "●"))} {e(texto)}</span>' if texto else '<span class="tono">—</span>'

    def estado_txt(x):
        return x.get("estado_en") if en and x.get("estado_en") else x["estado"]

    def destino_link(x):
        return x["html_en"] if en and x["html_en"] else x["html"]

    # 1. indicadores globales
    kpis = []
    for su in suites:
        tono_s = "ok" if su["fallidos"] == 0 else ("bad" if su["pct"] < 80 else "warn")
        kpis.append((f'npm test · {su["suite"]}', f'{su["pct"]}%', tono_s, f'{su["aprobados"]} de {su["total"]} aprobados · {su["fallidos"]} fallidos',
                     "ok", {"serie": su["serie"]} if len(su["serie"]) > 1 else {"pct": su["pct"]}))
    if bugs:
        kpis.append(("Bugs abiertos", bugs["abiertos"], "bad" if bugs["graves"] else ("warn" if bugs["abiertos"] else "ok"),
                     f'{bugs["graves"]} crítico(s) o alto(s)', "bicho"))
    kpis += [("Informes de hoy", hoy, "", f"{semana} en los últimos 7 días", "lista"),
             ("Para revisar", len(malos), "bad" if malos else "ok", "con veredicto o resultado en rojo", "warn")]
    inicio = kpi_tiles(kpis)

    # 2. alertas: lo que hay que mirar primero
    alertas = []
    for su in suites:
        if su["fallidos"]:
            alertas.append(("bad" if su["pct"] < 80 else "warn", f'npm test · {su["suite"]}',
                            f'{su["fallidos"]} escenario(s) fallido(s) de {su["total"]}', su["html"], su["fecha"]))
    if bugs and bugs["graves"]:
        alertas.append(("bad", "Bugs", f'{bugs["graves"]} bug(s) crítico(s) o alto(s) abierto(s)', None, None))
    for x in ultimas:
        graves = hallazgos_graves(x["html"])
        if x["tono"] == "bad":
            alertas.append(("bad", f'{nombre(x["herramienta"])} · {x["unidad"]}', estado_txt(x) or "Veredicto en rojo", destino_link(x), x["fecha"]))
        elif graves:
            alertas.append(("warn", f'{nombre(x["herramienta"])} · {x["unidad"]}', f"{graves} hallazgo(s) crítico(s)", destino_link(x), x["fecha"]))
    if alertas:
        items = []
        for tono_a, quien, que, destino_a, cuando in alertas[:12]:
            cuando_txt = f'<span class="cuando">{e(cuando.strftime("%Y-%m-%d %H:%M"))}</span>' if cuando else ""
            contenido = f'<span class="ic">{icono[tono_a]}</span><span><b>{e(quien)}</b> · {e(que)}</span>{cuando_txt}'
            if destino_a:
                items.append(f'<a class="tb-alerta {tono_a}" href="{e(rel(destino_a))}">{contenido}</a>')
            else:
                items.append(f'<a class="tb-alerta {tono_a} ir-cat" href="#cat-bugs">{contenido}</a>')
        extra_a = f'<p class="muted" style="padding:0 22px 14px">Y {len(alertas) - 12} más en la lista completa.</p>' if len(alertas) > 12 else ""
        inicio += f'<div class="section-title" style="margin-top:18px"><h2>Para revisar</h2><span class="sub">{len(alertas)} alerta(s)</span></div>'
        inicio += f'<div class="tb-alertas">{"".join(items)}</div>{extra_a}'
    elif todas:
        inicio += '<div class="tb-ok">✓ Sin alertas: ningún informe con veredicto en rojo ni suites fallando.</div>'

    # 3. veredictos clave (ambiente, riesgo, seguridad, cierre…)
    claves = []
    for h in CLAVE:
        x = next((y for y in ultimas if y["herramienta"] == h), None)
        if x:
            claves.append(f'<a class="tb-clave" href="{e(rel(destino_link(x)))}"><div class="t">{e(nombre(h))}</div>'
                          f'<div class="v">{chip_tono(x["tono"], estado_txt(x) or "Sin veredicto")}</div>'
                          f'<div class="f">{e(x["unidad"])} · {e(x["fecha"].strftime("%Y-%m-%d"))}</div></a>')
    if claves:
        inicio += f'<div class="section-title" style="margin-top:6px"><h2>Últimos veredictos</h2></div><div class="tb-claves">{"".join(claves)}</div>'

    # 4. tarjetas por categoría: el último informe de cada herramienta
    tarjetas = []
    for cid, titulo, _ in CATEGORIAS + [("otros", "Otros", [])]:
        de_cat = [x for x in ultimas if x["categoria"] == cid]
        if not de_cat:
            continue
        por_herr = {}
        for x in de_cat:  # ultimas viene ordenada de la más nueva a la más vieja
            por_herr.setdefault(x["herramienta"], x)
        filas_c = []
        for h, x in list(por_herr.items())[:7]:
            veredicto = estado_txt(x)
            corto = veredicto if len(veredicto) <= 46 else veredicto[:45].rstrip() + "…"
            filas_c.append(f'<li><a href="{e(rel(destino_link(x)))}" title="{e(x["unidad"])}">{e(nombre(h))}</a>'
                           f'<div class="m">{chip_tono(x["tono"], corto) if veredicto else ""}'
                           f'<span class="f">{e(x["unidad"])} · {e(x["fecha"].strftime("%Y-%m-%d %H:%M"))}</span></div></li>')
        rojos = sum(1 for x in por_herr.values() if x["tono"] == "bad")
        marca = f' <span class="tono bad">✕ {rojos}</span>' if rojos else ""
        tarjetas.append(f'<div class="tb-cat"><h3>{e(titulo)}{marca}<span class="n">{len(de_cat)} informe(s)</span></h3><ul>{"".join(filas_c)}</ul>'
                        f'<a class="ver ir-cat" href="#cat-{cid}">Ver todos →</a></div>')
    if tarjetas:
        inicio += f'<div class="section-title" style="margin-top:6px"><h2>Por categoría</h2></div><div class="tb-cats">{"".join(tarjetas)}</div>'

    # 5. buscador y lista completa
    if todas:
        inicio += ('<div class="section-title" style="margin-top:6px"><h2>Buscar en todos los informes</h2></div>'
                   '<div class="tb-buscar"><input id="buscar-todo" type="search" placeholder="Texto, historia, herramienta, archivo…" '
                   'aria-label="Buscar en todos los informes"><a class="ir-cat" href="#cat-todos">Ver la lista completa →</a></div>')
    else:
        inicio += ('<div class="cardbody"><p class="muted">Cuando los agentes generen informes, van a aparecer acá. '
                   'Este portal se actualiza solo cada vez que se arma uno.</p></div>')
    if vacias:
        chips = " ".join(f'<span class="chip">{e(nombre(v))}</span>' for v in vacias)
        inicio += f'<div class="section-title" style="margin-top:18px"><h2>Todavía sin informes</h2></div><div class="cardbody"><div class="meta">{chips}</div></div>'

    body = []
    tonos = "".join(f'<button type="button" data-tono="{k}"{" class=on" if k == "" else ""}>{e(v)}</button>'
                    for k, v in (("", "Todos"), ("bad", "Crítico"), ("warn", "Revisar"), ("ok", "En orden")))
    rangos = "".join(f'<button type="button" data-dias="{d}">{e(v)}</button>'
                     for d, v in ((1, "24 h"), (7, "7 días"), (30, "30 días"), (0, "Siempre")))
    textos = json.dumps({"todas": t("Todas"), "cuenta": t("{v} de {n} informes").replace("{n}", "{n}")}, ensure_ascii=False)
    body.append(f'''<form class="filtros" id="filtros" onsubmit="return false" data-txt="{e(textos)}">
  <label>buscar<input name="q" type="search" placeholder="Texto, historia, archivo…"></label>
  <label>herramienta<select name="herr"><option value="">Todas</option></select></label>
  <label>historia / sitio / suite<select name="hist"><option value="">Todas</option></select></label>
  <label>desde<input name="desde" type="date"></label>
  <label>hasta<input name="hasta" type="date"></label>
  <label>período<span class="grupo-btn">{rangos}</span></label>
  <label>estado<span class="grupo-btn">{tonos}</span></label>
  <label class="check"><input name="conhist" type="checkbox" checked>Incluir corridas anteriores</label>
  <button type="button" class="limpiar">Limpiar filtros</button>
  <span class="cuenta"></span>
</form>''')
    body.append(categoria("inicio", "Inicio", [], "lo último y lo que hay que revisar", inicio=True, cuerpo=inicio))
    if todas:
        body.append(categoria("todos", "Todos los informes", todas, f"{len(ultimas)} informe(s) · {len(todas) - len(ultimas)} en el historial"))
    for cid, titulo, _ in CATEGORIAS + [("otros", "Otros", [])]:
        lista = [x for x in todas if x["categoria"] == cid]
        if lista:
            n_ult = sum(1 for x in lista if not x["anterior"])
            body.append(categoria(cid, titulo, lista, f"{n_ult} informe(s) · {len(lista) - n_ult} en el historial"))
    html_ = page("Portal de informes", "Portal", meta([("Actualizado", datetime.now().strftime("%Y-%m-%d %H:%M")),
                                                       ("Carpeta", "output/")]), "".join(body))
    # Los textos del JS del portal (cuenta de informes) ya vienen traducidos en data-txt.
    return html_.replace("</style>", CSS_PORTAL + "</style>", 1).replace("</body>", f"<script>{JS_PORTAL}</script></body>", 1)


def generar(output=None, reportes_k0=None, destino=None):
    output = Path(output or PROYECTO / "output")
    reportes_k0 = reportes_k0 if reportes_k0 is not None else PROYECTO / "herramientas" / "k0lmena" / "reports"
    destino = Path(destino or output / "index.html")
    destino.parent.mkdir(parents=True, exist_ok=True)
    _regenerar_artefactos(output)
    evals = RAIZ / "evals" / "resultados" if output == PROYECTO / "output" else None
    herramientas = descubrir(output, reportes_k0, evals)
    escribir_bilingue(destino, lambda: armar_html(herramientas, destino))
    return destino, herramientas


def _regenerar_artefactos(output):
    """Antes de indexar, arma (o actualiza) el HTML de los artefactos de los agentes que no tienen informe propio:
    casos de prueba, bugs, análisis, datos, BDD… (scripts/generar_informe_artefacto.py). Nunca rompe el portal."""
    try:
        import generar_informe_artefacto
    except ImportError:
        return
    try:
        generar_informe_artefacto.actualizar_artefactos(output)
    except Exception as ex:
        print(f"[!] No pude actualizar el HTML de los artefactos ({ex}).", file=sys.stderr)


# ------------------------------------------------------------------ actualización automática
_PROGRAMADO = [False]


def _actualizar_al_salir():
    try:
        generar()
    except Exception as ex:  # el portal nunca rompe un informe
        print(f"[!] No pude actualizar el portal de informes ({ex}).", file=sys.stderr)


def programar():
    """Regenera output/index.html cuando termina el proceso (después de que el informe se escribió).
    No hace nada en los tests, con K0LMENIA_PORTAL=0 o si no existe output/."""
    if _PROGRAMADO[0] or os.environ.get("K0LMENIA_PORTAL", "1") == "0" or "pytest" in sys.modules:
        return
    if not (PROYECTO / "output").is_dir():
        return
    _PROGRAMADO[0] = True
    atexit.register(_actualizar_al_salir)


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Portal con el último informe de cada herramienta (output/index.html)")
    ap.add_argument("--abrir", action="store_true", help="abre el portal en el navegador")
    ap.add_argument("--output", help=argparse.SUPPRESS)
    ap.add_argument("--reportes", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    _PROGRAMADO[0] = True  # este proceso ya genera el portal: que page() no lo programe de nuevo
    destino, herramientas = generar(a.output, a.reportes)
    n = sum(len(v) for v in herramientas.values())
    print(f"Portal: {destino} ({n} informe(s) de {sum(1 for v in herramientas.values() if v)} herramienta(s))")
    if a.abrir:
        import webbrowser
        webbrowser.open(destino.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Genera el Informe de selección de casos en HTML (dashboard, modo oscuro) a partir de seleccion.json
(scripts/seleccionar_casos.py) y, opcionalmente, del análisis del agente selector-casos-de-prueba.

Uso:
    python scripts/generar_informe_seleccion.py <seleccion.json> <salida.html> [--analisis analisis.json]

Qué muestra: qué correr y por qué. Veredicto con el riesgo del cambio, indicadores (inventario,
seleccionados, imprescindibles, recomendados, regresión mínima, tiempo y ahorro, cambios sin casos),
selección por historia y por tipo, qué cambió (archivos con sus conceptos, commits, historias,
palabras clave con su peso), los comandos listos para copiar (bash y PowerShell) para lo
automatizado, la tabla de casos seleccionados con su puntaje y sus razones, los cambios sin
cobertura y lo que quedó afuera.

El análisis (opcional) aporta:
{
  "veredicto": "Cambio de riesgo alto en el pago: 14 casos, 22 min", "veredicto_tono": "warn",
  "riesgo": "Alto", "resumen": "Resumen para alguien no técnico...",
  "ajustes": {"HU-003:CP-007": {"grupo": "Imprescindible", "motivo": "Toca el redondeo del total"}},
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
(los ajustes los aplica scripts/seleccionar_casos.py: así el CSV y los comandos también cambian)
"""
import argparse
import json
from pathlib import Path
import sys
from collections import Counter

import _historial
from _i18n import escribir_bilingue, localizar, idioma_actual  # noqa: E402
from _estilos_reporte import (e, page, meta, section, kpi_tiles, banner, doc_list, table, stacked_bars, donut_panel, two_col,
                              nivel_badge, estado_pill, _pastilla, NEUTRO, SERIES, AVISO, CRITICO, OK, SERIO)
from generar_informe_exploratorio import CSS_EXTRA

GRUPOS = ["Imprescindible", "Recomendado", "Regresión mínima", "No seleccionado"]
COLOR_GRUPO = {"Imprescindible": SERIES[1], "Recomendado": SERIES[2], "Regresión mínima": SERIES[4], "No seleccionado": NEUTRO}
ICONO_GRUPO = {"Imprescindible": "●", "Recomendado": "◐", "Regresión mínima": "○", "No seleccionado": "–"}
RIESGO = {"Alto": "bad", "Medio": "warn", "Bajo": "ok"}

CSS_SEL = """
<style>
.cmdbox{position:relative;background:#120F0B;border:1px solid var(--border);border-radius:12px;padding:14px 16px 14px 16px;margin:10px 0}
.cmdbox .et{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin-bottom:6px;display:flex;gap:10px;align-items:center}
.cmdbox pre{margin:0;white-space:pre-wrap;word-break:break-all;font-family:var(--mono);font-size:12.5px;color:#FFE58A}
.cmdbox button{position:absolute;top:10px;right:10px;background:var(--tile);border:1px solid var(--border);color:var(--ink);border-radius:8px;
  padding:4px 10px;font:inherit;font-size:12px;cursor:pointer}
.cmdbox button.ok{background:var(--accent);color:#0E0C09;border-color:transparent}
.score{display:flex;align-items:center;gap:8px;min-width:110px}
.score .t{flex:1;height:6px;border-radius:99px;background:rgba(244,239,230,.06);overflow:hidden}
.score .t span{display:block;height:100%;border-radius:99px}
.score b{font-family:var(--mono);font-size:12px;color:var(--ink);min-width:24px;text-align:right}
.razones{margin:0;padding-left:16px;color:var(--body);font-size:12.5px}
.razones li{margin:2px 0}
.tags{display:flex;flex-wrap:wrap;gap:8px;padding:16px 24px}
.tags span{font-size:12.5px;padding:5px 11px;border-radius:999px;background:var(--tile);border:1px solid var(--border);color:var(--ink)}
.tags span b{font-family:var(--mono);font-weight:600;color:var(--muted);margin-left:6px;font-size:11px}
.commits li{margin:3px 0;color:var(--body)}
.commits code{font-family:var(--mono);font-size:12px;color:var(--muted);margin-right:6px}
</style>
"""

JS_SEL = """
<script>
document.querySelectorAll('.cmdbox button').forEach(function(b){b.addEventListener('click',function(){
  var t=b.parentNode.querySelector('pre').innerText;
  (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(function(){b.textContent='Copiado';b.classList.add('ok');
    setTimeout(function(){b.textContent='Copiar';b.classList.remove('ok')},1600)}).catch(function(){b.textContent='Seleccioná y copiá'});});});
</script>
"""
JS_SEL_EN = JS_SEL.replace("'Copiado'", "'Copied'").replace("'Copiar'", "'Copy'").replace("'Seleccioná y copiá'", "'Select and copy'")


def js_sel():
    return JS_SEL_EN if idioma_actual() == "en" else JS_SEL


def grupo_pill(g):
    return _pastilla(g, COLOR_GRUPO.get(g, NEUTRO), ICONO_GRUPO.get(g, "●"))


def score(p, g):
    color = COLOR_GRUPO.get(g, NEUTRO)
    return f'<div class="score"><div class="t"><span style="width:{max(0, min(100, p))}%;background:{color}"></span></div><b>{e(p)}</b></div>'


def cmdbox(etiqueta, cmd):
    return f'<div class="cmdbox"><div class="et">{e(etiqueta)}</div><pre>{e(cmd)}</pre><button type="button">Copiar</button></div>'


def fila_caso(c):
    res = (c.get("resultado") or {}).get("estado")
    tipo = c["tipo"] + (f' · {c["suite"]}' if c.get("suite") else "")
    return [grupo_pill(c["grupo"]), score(c["puntaje"], c["grupo"]),
            f'<span class="mono" style="color:var(--ink);white-space:nowrap">{e(c["historia"])}</span><div class="mono" style="white-space:nowrap">{e(c["id"])}</div>',
            f'<strong style="color:var(--ink)">{e(c["titulo"])}</strong>'
            + (f'<div class="muted">{e(c.get("titulo_historia"))}</div>' if c.get("titulo_historia") else ""),
            e(tipo), nivel_badge(c.get("prioridad") or "Media"), estado_pill(res) if res else '<span class="muted">—</span>',
            f'{e(c["minutos"])} min', f'<ul class="razones">{"".join(f"<li>{e(r)}</li>" for r in c.get("razones") or [])}</ul>']


def build_html(datos, analisis, hist_html=""):
    casos = datos.get("casos") or []
    r = datos.get("resumen") or {}
    cambio = datos.get("cambio") or {}
    sel = [c for c in casos if c["grupo"] != "No seleccionado"]
    body = []
    riesgo = analisis.get("riesgo")
    texto = (f'Correr {r.get("seleccionados", 0)} de {r.get("casos", 0)} casos ({r.get("automatizados", 0)} automatizados, '
             f'{r.get("manuales", 0)} manuales): unos {r.get("minutos_seleccion", 0)} min, {r.get("ahorro_pct", 0)} % menos que toda la regresión')
    tono = RIESGO.get(riesgo, "warn" if r.get("sin_cobertura") else "ok")
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))
    n = r.get("casos", 0)
    pg = r.get("por_grupo") or {}
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Casos en el inventario", n, "", f'{r.get("historias", 0)} historia(s)', "lista"),
        ("Seleccionados", r.get("seleccionados", 0), "", f'{round(r.get("seleccionados", 0) / n * 100) if n else 0} % del inventario', "filtro",
         {"pct": r.get("seleccionados", 0) / n * 100 if n else 0}),
        ("Imprescindibles", pg.get("Imprescindible", 0), "bad" if pg.get("Imprescindible") else "", "tocan lo que cambió", "objetivo"),
        ("Recomendados", pg.get("Recomendado", 0), "warn" if pg.get("Recomendado") else "", "relacionados con el cambio", "lupa"),
        ("Regresión mínima", pg.get("Regresión mínima", 0), "", "smoke y prioridad Crítica", "ok"),
        ("Tiempo estimado", f'{r.get("minutos_seleccion", 0)} min', "", f'de {r.get("minutos_total", 0)} min de toda la regresión', "reloj"),
        ("Ahorro", f'{r.get("ahorro_pct", 0)} %', "ok" if r.get("ahorro_pct", 0) >= 30 else "", "contra correr todo", "rayo",
         {"pct": r.get("ahorro_pct", 0)}),
        ("Cambios sin casos", r.get("sin_cobertura", 0), "warn" if r.get("sin_cobertura") else "ok", "archivos que ningún caso cubre", "warn"),
    ]) + "</div>")
    if analisis.get("resumen") or riesgo:
        txt = (f'<p class="lead">{e(analisis.get("resumen") or "")}</p>' if analisis.get("resumen") else "")
        if riesgo:
            txt += f'<p style="margin-top:10px">Riesgo del cambio: {nivel_badge({"Alto": "Alta", "Medio": "Media", "Bajo": "Baja"}.get(riesgo, riesgo))}</p>'
        body.append(section("Resumen ejecutivo", f'<div class="cardbody">{txt}</div>'))

    # Por historia (apilado por grupo) y por tipo
    porhu = {}
    for c in casos:
        porhu.setdefault(c["historia"], Counter())[c["grupo"]] += 1
    filas = sorted(((hu, [cnt[g] for g in GRUPOS[:3]]) for hu, cnt in porhu.items()), key=lambda x: -sum(x[1]))[:14]
    tipos = Counter(c["tipo"] for c in sel)
    body.append(two_col(
        section("Selección por historia", stacked_bars(filas, [(g, COLOR_GRUPO[g]) for g in GRUPOS[:3]]),
                f'{r.get("historias_seleccionadas", 0)} de {r.get("historias", 0)} historias tienen casos seleccionados'),
        section("Seleccionados por tipo", donut_panel([(tipos.get("Automatizado", 0), SERIES[1], "Automatizados (npm test)"),
                                                       (tipos.get("Manual", 0), SERIES[3], "Manuales")],
                                                      round(tipos.get("Automatizado", 0) / len(sel) * 100) if sel else 0, "automatizados"))))

    # Cómo correrlo
    cmds = datos.get("comandos") or []
    bloque = ""
    for c in cmds:
        bloque += cmdbox(f'Suite {c["suite"]} · {c["casos"]} caso(s) · bash', c["bash"]) + cmdbox(f'Suite {c["suite"]} · PowerShell', c["powershell"])
    manuales = [c for c in sel if c["tipo"] == "Manual"]
    if manuales:
        bloque += f'<p style="margin-top:10px">Los {len(manuales)} caso(s) manuales están en <span class="mono">seleccion.csv</span> (se abre con Excel), ordenados por grupo y puntaje.</p>'
    if not bloque:
        bloque = '<p class="muted">No hay casos seleccionados para correr.</p>'
    body.append(section("Cómo correrlo", f'<div class="cardbody">{bloque}</div>', "lo automatizado corre sin agentes ni tokens"))

    # Qué cambió
    partes = []
    if cambio.get("historias") or cambio.get("keys") or datos.get("historias_afectadas"):
        partes.append(f'<div class="lbl" style="padding:14px 24px 0">Historias e issues</div><div class="tags">'
                      + "".join(f"<span>{e(h)}</span>" for h in sorted(set(cambio.get("historias") or []) | set(cambio.get("keys") or []) | set(datos.get("historias_afectadas") or [])))
                      + "</div>")
    if cambio.get("palabras"):
        partes.append('<div class="lbl" style="padding:6px 24px 0">Conceptos del cambio (con su peso)</div><div class="tags">'
                      + "".join(f'<span>{e(p["palabra"])}<b>{e(p["peso"])}</b></span>' for p in cambio["palabras"][:20]) + "</div>")
    if cambio.get("archivos"):
        sin = {x["archivo"] for x in datos.get("sin_cobertura") or []}
        filas = [[f'<span class="mono">{e(f)}</span>', _pastilla("Sin casos", AVISO, "!") if f in sin else _pastilla("Con casos", OK, "✓")]
                 for f in cambio["archivos"][:60]]
        partes.append(table(["Archivo", "Cobertura"], filas))
    if cambio.get("commits"):
        partes.append('<div class="cardbody"><ul class="commits">' + "".join(
            f'<li><code>{e(c["hash"])}</code>{e(c["mensaje"])}</li>' for c in cambio["commits"][:20]) + "</ul></div>")
    if cambio.get("texto"):
        partes.append(f'<div class="cardbody"><p class="muted" style="white-space:pre-wrap">{e(cambio["texto"][:1200])}</p></div>')
    if partes:
        body.append(section("Qué cambió", "".join(partes), " · ".join(cambio.get("fuentes") or [])))

    if sel:
        body.append(section("Casos seleccionados", table(["Grupo", "Puntaje", "Caso", "Título", "Tipo", "Prioridad", "Último resultado", "Tiempo", "Por qué"],
                                                         [fila_caso(c) for c in sel]),
                            "ordenados por grupo y puntaje · filtrá por grupo o buscá un caso"))
    if datos.get("sin_cobertura"):
        filas = [[f'<span class="mono">{e(x["archivo"])}</span>', e(", ".join(x.get("palabras") or []))] for x in datos["sin_cobertura"]]
        body.append(section("Cambios sin cobertura", table(["Archivo", "Conceptos que no aparecen en ningún caso"], filas),
                            "riesgo: lo que cambió acá no lo prueba ningún caso → generar casos (generador-casos-manuales o BDD)"))
    afuera = [c for c in casos if c["grupo"] == "No seleccionado"]
    if afuera:
        body.append(section("No seleccionados", table(["Grupo", "Puntaje", "Caso", "Título", "Tipo", "Prioridad", "Último resultado", "Tiempo", "Por qué"],
                                                      [fila_caso(c) for c in afuera[:200]]),
                            f"{len(afuera)} caso(s) que no tocan el cambio · igual conviene correr toda la regresión antes de una release grande"))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    body.append(section("Cómo se elige", doc_list([
        "Imprescindible: la historia está en el cambio (por la key del commit, el PR o el pedido) o el caso coincide fuerte con lo que cambió (puntaje 60 o más).",
        "Recomendado: el caso comparte conceptos con el cambio (archivos, funciones, commits, notas), con sinónimos en español e inglés.",
        "Regresión mínima: los casos de humo (@smoke) y los de prioridad Crítica, que se corren siempre.",
        "El puntaje suma la historia afectada (60), la coincidencia de conceptos (hasta 45), la prioridad (hasta 15), si falló la última vez (10), si es inestable (6) y si la historia tiene bugs abiertos (5).",
        "Es una ayuda para decidir, no un reemplazo del criterio: el análisis del agente puede mover casos de grupo (queda anotado en Por qué).",
    ])))

    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Selección", datos.get("nombre")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
                      ("Presupuesto", f'{datos["presupuesto_min"]} min' if datos.get("presupuesto_min") else None),
                      ("Riesgo", riesgo)])
    return page("Selección de casos", "Qué probar en este cambio", meta_html, CSS_EXTRA + CSS_SEL + "".join(body) + js_sel())


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de selección de casos a partir de seleccion.json")
    ap.add_argument("datos_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis")
    a = ap.parse_args()
    if not a.salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    with open(a.datos_json, encoding="utf-8") as f:
        datos = json.load(f)
    analisis = {}
    if a.analisis:
        with open(a.analisis, encoding="utf-8") as f:
            analisis = json.load(f)
    hist_html = _historial.seccion("seleccion", Path(a.datos_json).resolve().parent, datos)
    # ES y EN: el inglés del agente va en el bloque "en" del analisis.json.
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

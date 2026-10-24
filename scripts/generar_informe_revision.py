#!/usr/bin/env python3
"""
Genera el Informe de revisión de casos en HTML (dashboard, modo oscuro) a partir de revision.json
(scripts/revisar_casos.py) y, opcionalmente, del análisis del agente revisor-casos.

Uso:
    python scripts/generar_informe_revision.py <revision.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (casos, puntaje promedio, a mejorar, sin problemas, duplicados, sin
resultado esperado, tiempo de ejecución manual), la distribución de puntajes, los problemas por tipo, el
resumen por historia (casos, negativos, puntaje y tiempo), cada caso con su puntaje, tiempo, problemas,
sugerencias y la versión mejorada que propone el agente, y la evolución de las revisiones.

El análisis (opcional) aporta:
{
  "veredicto": "...", "veredicto_tono": "warn", "resumen": "...",
  "propuestas": {"HU-001:CP-003": {"titulo": "...", "pasos": "1. ...\\n2. ...", "resultado": "...", "nota": "..."}},
  "descartados": [{"caso": "HU-001:CP-004", "tipo": "Duplicado", "motivo": "Prueban dispositivos distintos"}],
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import _historial
from _i18n import escribir_bilingue, localizar, idioma_actual  # noqa: E402
from _estilos_reporte import (e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, column_chart, two_col,
                              nivel_badge, _pastilla, CRITICO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA
from estimacion import formatear

CSS_REV = """
<style>
.score{display:flex;align-items:center;gap:8px;min-width:110px}
.score .t{flex:1;height:6px;border-radius:99px;background:rgba(244,239,230,.06);overflow:hidden}
.score .t span{display:block;height:100%;border-radius:99px}
.score b{font-family:var(--mono);font-size:12px;color:var(--ink);min-width:24px;text-align:right}
.probs{margin:0;padding-left:16px;font-size:12.5px;color:var(--body)}
.probs li{margin:3px 0}
.probs .sug{color:var(--muted)}
.prop{margin-top:8px;border:1px solid rgba(92,191,74,.35);background:rgba(92,191,74,.06);border-radius:10px;padding:10px 12px;font-size:12.5px;color:#C6EDB9;white-space:pre-wrap}
.prop b{color:#E6FBE6}
.descartado{text-decoration:line-through;opacity:.6}
</style>
"""


def score(p):
    color = OK if p >= 85 else AVISO if p >= 70 else CRITICO
    return f'<div class="score"><div class="t"><span style="width:{p}%;background:{color}"></span></div><b>{p}</b></div>'


def build_html(datos, analisis, hist_html=""):
    casos = datos.get("casos") or []
    r = datos.get("resumen") or {}
    props = analisis.get("propuestas") or {}
    desc = {(d.get("caso"), d.get("tipo")): d.get("motivo") for d in analisis.get("descartados") or []}
    body = []
    prom = r.get("puntaje_prom")
    if prom is None:
        tono, texto = "warn", "No hay casos para revisar"
    elif prom >= 85 and not r.get("sin_resultado"):
        tono, texto = "ok", f"Casos en buen estado (puntaje promedio {prom})"
    elif prom >= 70:
        tono, texto = "warn", f"Casos aceptables con detalles a mejorar (puntaje promedio {prom})"
    else:
        tono, texto = "bad", f"Muchos casos a mejorar (puntaje promedio {prom})"
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))
    n = r.get("casos", 0)
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Casos revisados", n, "", f'{r.get("manuales", 0)} manuales · {r.get("bdd", 0)} BDD', "lista"),
        ("Puntaje promedio", prom if prom is not None else "—", "" if prom is None else ("ok" if prom >= 85 else "warn" if prom >= 70 else "bad"),
         "100 = sin problemas", "objetivo", {"pct": prom or 0}),
        ("A mejorar", r.get("a_mejorar", 0), "bad" if r.get("a_mejorar") else "ok", "puntaje menor a 70", "warn"),
        ("Sin problemas", r.get("sin_problemas", 0), "ok" if r.get("sin_problemas") == n and n else "", f'{round(r.get("sin_problemas", 0) / n * 100) if n else 0} % de los casos', "ok"),
        ("Posibles duplicados", r.get("duplicados", 0), "warn" if r.get("duplicados") else "ok", "pasos y títulos casi iguales", "lupa"),
        ("Sin resultado esperado", r.get("sin_resultado", 0), "bad" if r.get("sin_resultado") else "ok", "o escenarios sin Then", "bad"),
        ("Ejecución manual", r.get("tiempo_total", "—"), "", "tiempo estimado de todos los casos (scripts/estimacion.py)", "reloj"),
        ("Problemas", r.get("hallazgos", 0), "", ", ".join(f"{k} {v}" for k, v in (r.get("por_severidad") or {}).items() if v) or "ninguno", "codigo"),
    ]) + "</div>")
    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    rangos = [("0–49", 0, 49), ("50–69", 50, 69), ("70–84", 70, 84), ("85–99", 85, 99), ("100", 100, 100)]
    dist = [(et, sum(1 for c in casos if lo <= c["puntaje"] <= hi), CRITICO if hi < 70 else AVISO if hi < 85 else OK) for et, lo, hi in rangos]
    tipos = Counter(x["tipo"] for c in casos for x in c["hallazgos"])
    body.append(two_col(section("Puntaje de los casos", column_chart(dist, ancho=660), "cuántos casos hay en cada rango"),
                        section("Problemas por tipo", bar_chart([(t, k, SERIES[i % len(SERIES)]) for i, (t, k) in enumerate(tipos.most_common())], ancho_etiqueta=150)
                                if tipos else '<p class="muted" style="padding:16px 24px">Sin problemas.</p>')))

    filas = []
    for h in datos.get("por_historia") or []:
        probs = "".join(f'<div>{nivel_badge(x["severidad"])} {e(x["titulo"])}</div>' for x in h["hallazgos"]) or '<span class="muted">—</span>'
        filas.append([f'<strong style="color:var(--ink)">{e(h["historia"])}</strong>', e(h["casos"]), e(h["negativos"]), score(h["puntaje_prom"]),
                      e(formatear(h["tiempo_min"])), probs])
    if filas:
        body.append(section("Por historia", table(["Historia", "Casos", "Negativos o de borde", "Puntaje", "Ejecución manual", "Problemas"], filas)))

    filas = []
    for c in casos:
        clave = f'{c["historia"]}:{c["id"]}'
        items = ""
        for x in c["hallazgos"]:
            tachado = ' class="descartado"' if (clave, x["tipo"]) in desc else ""
            sug = f' <span class="sug">— {e(x["sugerencia"])}</span>' if x.get("sugerencia") else ""
            items += f'<li{tachado}>{nivel_badge(x["severidad"])} <strong style="color:var(--ink)">{e(x["titulo"])}</strong>{sug}</li>'
        prop = props.get(clave) or props.get(c["id"])
        bloque_prop = ""
        if prop:
            partes = [f'<b>{e(k.capitalize())}:</b> {e(v)}' for k, v in prop.items() if k != "nota" and v]
            nota = f'\n<i>{e(prop["nota"])}</i>' if prop.get("nota") else ""
            bloque_prop = f'<div class="prop"><b>Versión propuesta</b>\n' + "\n".join(partes) + nota + "</div>"
        tipo = "BDD" if c["tipo"] != "manual" else "Manual"
        filas.append([f'<span class="mono" style="color:var(--ink);white-space:nowrap">{e(c["historia"])}</span><div class="mono" style="white-space:nowrap">{e(c["id"])}</div>',
                      f'<strong style="color:var(--ink)">{e(c["titulo"])}</strong><div class="muted">{e(tipo)} · {e(c.get("archivo", ""))}</div>',
                      score(c["puntaje"]), e(c.get("tiempo", "—")),
                      (f'<ul class="probs">{items}</ul>' if items else _pastilla("Sin problemas", OK, "✓")) + bloque_prop])
    if filas:
        body.append(section("Cada caso", table(["Caso", "Título", "Puntaje", "Tiempo", "Problemas y propuesta"], filas),
                            "ordenados del puntaje más bajo al más alto"))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Historia", datos.get("historia")), ("Revisión", datos.get("nombre")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
                      ("Archivos", str(len(datos.get("origenes") or [])))])
    return page("Revisión de casos", "Calidad de los casos de prueba", meta_html, CSS_EXTRA + CSS_REV + "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de revisión de casos a partir de revision.json")
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
    hist_html = _historial.seccion("revision", Path(a.datos_json).resolve().parent, datos)
    # ES y EN: el inglés del agente va en el bloque "en" del analisis.json.
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

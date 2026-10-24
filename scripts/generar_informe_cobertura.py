#!/usr/bin/env python3
"""
Genera el Informe de cobertura y trazabilidad en HTML (dashboard, modo oscuro) a partir de
cobertura.json (scripts/analizar_cobertura.py) y, opcionalmente, del análisis del agente
analista-cobertura.

Uso:
    python scripts/generar_informe_cobertura.py <cobertura.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (criterios cubiertos, casos, automatizados, ejecutados,
aprobados, huecos), el embudo HU → casos → automatizados → ejecutados → aprobados, el resumen por
historia (si son varias), la cobertura por criterio, la matriz de trazabilidad de cada caso
(fuente, criterios, automatización, gestión, último resultado y bugs) y los huecos priorizados.

El análisis (opcional) aporta:
{
  "veredicto": "HU-001 lista para cerrar; HU-002 con criterios sin probar", "veredicto_tono": "warn",
  "resumen": "Resumen para alguien no técnico...",
  "notas": {"C-03": "CP-004 se automatiza en el sprint que viene"},
  "descartados": [{"id": "C-07", "motivo": "CP-009 es exploratorio: no se automatiza"}],
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
"""
import argparse
import json
from pathlib import Path
import sys

import _historial
from _i18n import escribir_bilingue, localizar, idioma_actual  # noqa: E402
from _estilos_reporte import (e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, column_chart, two_col,
                              nivel_badge, _pastilla, CRITICO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA, JS_EXTRA

ORDEN = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}

CSS_COB = """
<style>
.prog{display:flex;align-items:center;gap:10px;min-width:150px}
.prog .t{flex:1;height:8px;border-radius:999px;background:rgba(244,239,230,.06);overflow:hidden}
.prog .t span{display:block;height:100%;border-radius:999px}
.prog b{font-size:12.5px;color:var(--ink);font-variant-numeric:tabular-nums;min-width:38px;text-align:right}
.tag{display:inline-block;font-family:var(--mono);font-size:11.5px;padding:1px 7px;
  border-radius:6px;background:var(--tile);border:1px solid var(--border);color:var(--ink);margin:1px 3px 1px 0;white-space:nowrap}
.hu-tit{font-size:15px;font-weight:700;color:var(--ink)}
</style>
"""


def pct(a, b):
    return round(a / b * 100) if b else 0


def progreso(a, b):
    p = pct(a, b)
    color = OK if p >= 90 else AVISO if p >= 60 else CRITICO
    return (f'<div class="prog" data-tip="{a} de {b}"><div class="t"><span style="width:{p}%;background:{color}"></span></div>'
            f'<b>{p} %</b></div>') if b else '<span class="muted">—</span>'


def si(texto="Sí"):
    return _pastilla(texto, OK, "✓")


def no(texto="No", color=CRITICO, icono="✕"):
    return _pastilla(texto, color, icono)


def resultado_pill(r):
    if not r:
        return '<span class="muted">Sin ejecutar</span>'
    return {"Aprobado": si("Aprobado"), "Fallido": no("Fallido"), "Bloqueado": no("Bloqueado", NEUTRO, "⊘")}.get(r["estado"], e(r["estado"]))


def build_html(datos, analisis, hist_html=""):
    descartados = {str(d.get("id")): d.get("motivo", "") for d in analisis.get("descartados") or []}
    notas = analisis.get("notas") or {}
    hist = datos.get("historias") or []
    tot = {k: sum(h["metricas"][k] for h in hist) for k in ("criterios", "criterios_cubiertos", "casos", "automatizados",
                                                               "con_resultado", "aprobados", "fallidos", "bugs_abiertos")}
    huecos = [dict(x, historia=h["historia"]) for h in hist for x in h["huecos"] if x["id"] not in descartados]
    huecos.sort(key=lambda x: ORDEN.get(x["severidad"], 9))
    graves = [x for x in huecos if x["severidad"] in ("Crítica", "Alta")]

    body = []
    if graves:
        tono, texto = "bad", f"{len(graves)} hueco(s) importante(s): criterios sin probar o casos que fallan"
    elif huecos:
        tono, texto = "warn", "La cobertura es buena; quedan huecos menores por cerrar"
    else:
        tono, texto = "ok", "Cobertura completa: cada criterio tiene casos, automatizados y aprobados"
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))

    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Criterios cubiertos", f'{tot["criterios_cubiertos"]}/{tot["criterios"]}' if tot["criterios"] else "—",
         "" if not tot["criterios"] else "ok" if tot["criterios_cubiertos"] == tot["criterios"] else "bad",
         f'{pct(tot["criterios_cubiertos"], tot["criterios"])} % con al menos un caso' if tot["criterios"] else "no se encontraron criterios", "objetivo",
         {"pct": pct(tot["criterios_cubiertos"], tot["criterios"])} if tot["criterios"] else {}),
        ("Casos", tot["casos"], "", f'{len(hist)} historia(s)', "lista"),
        ("Automatizados", tot["automatizados"], "ok" if tot["casos"] and tot["automatizados"] == tot["casos"] else "warn" if tot["casos"] else "",
         f'{pct(tot["automatizados"], tot["casos"])} % de los casos', "codigo", {"pct": pct(tot["automatizados"], tot["casos"])}),
        ("Con resultado", tot["con_resultado"], "", f'{pct(tot["con_resultado"], tot["casos"])} % ejecutados alguna vez', "carga",
         {"pct": pct(tot["con_resultado"], tot["casos"])}),
        ("Aprobados", tot["aprobados"], "ok" if tot["con_resultado"] and tot["aprobados"] == tot["con_resultado"] else "warn" if tot["con_resultado"] else "",
         f'{pct(tot["aprobados"], tot["con_resultado"])} % de lo ejecutado · {tot["fallidos"]} fallidos', "ok",
         {"pct": pct(tot["aprobados"], tot["con_resultado"])}),
        ("Huecos", len(huecos), "bad" if graves else "warn" if huecos else "ok", f'{len(graves)} de severidad alta', "lupa"),
        ("Bugs abiertos", tot["bugs_abiertos"], "bad" if tot["bugs_abiertos"] else "ok", "", "bicho"),
    ]) + "</div>")

    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    embudo = column_chart([("Criterios", tot["criterios"]), ("Cubiertos", tot["criterios_cubiertos"]), ("Casos", tot["casos"]),
                           ("Automatizados", tot["automatizados"]), ("Ejecutados", tot["con_resultado"]), ("Aprobados", tot["aprobados"])],
                          alto=300, ancho=660)
    huecos_tipo = {}
    for x in huecos:
        huecos_tipo[x["tipo"]] = huecos_tipo.get(x["tipo"], 0) + 1
    body.append(two_col(section("De la historia al resultado", embudo, "cuánto llega de cada etapa a la siguiente"),
                        section("Huecos por tipo", bar_chart(sorted([(k, v, SERIES[0]) for k, v in huecos_tipo.items()], key=lambda x: -x[1]),
                                                              ancho_etiqueta=200) if huecos_tipo else '<div class="cardbody"><p>Sin huecos.</p></div>')))

    if len(hist) > 1:
        filas = [[f'<span class="hu-tit">{e(h["historia"])}</span>', progreso(h["metricas"]["criterios_cubiertos"], h["metricas"]["criterios"]),
                  e(h["metricas"]["casos"]), progreso(h["metricas"]["automatizados"], h["metricas"]["casos"]),
                  progreso(h["metricas"]["con_resultado"], h["metricas"]["casos"]), progreso(h["metricas"]["aprobados"], h["metricas"]["con_resultado"]),
                  e(len(h["huecos"]))] for h in hist]
        body.append(section("Resumen por historia", table(["Historia", "Criterios cubiertos", "Casos", "Automatizados", "Ejecutados", "Aprobados", "Huecos"], filas)))

    if huecos:
        filas = []
        for x in huecos:
            nota = f'<div class="muted" style="margin-top:4px">{e(notas[x["id"]])}</div>' if x["id"] in notas else ""
            filas.append([f'<span class="id">{e(x["id"])}</span>', e(x["historia"]), nivel_badge(x["severidad"]), e(x["tipo"]),
                          f'{e(x["detalle"])}{nota}'])
        body.append(section("Huecos de cobertura", table(["ID", "Historia", "Severidad", "Tipo", "Detalle"], filas), "lo que falta para cerrar cada historia"))

    for h in hist:
        m = h["metricas"]
        if h["criterios"]:
            filas = [[f'<span class="tag">{e(c["id"])}</span>', e(c["descripcion"] or "—"),
                      "".join(f'<span class="tag">{e(cp)}</span>' for cp in c["casos"]) or '<span class="muted">—</span>',
                      si("Cubierto") if c["casos"] else no("Sin casos")] for c in h["criterios"]]
            body.append(section(f'{h["historia"]} · Cobertura por criterio', table(["Criterio", "Descripción", "Casos que lo cubren", "Cobertura"], filas),
                                "criterios tomados de " + (", ".join(h["origen_criterios"]) or "—")))
        if h["casos"]:
            filas = []
            for x in h["casos"]:
                aut = "".join((no(a["suite"], NEUTRO, "⊘") if a["bloqueado"] else si(a["suite"])) for a in x["automatizado"]) \
                    or '<span class="muted">No</span>'
                ges = " ".join(f'<span class="tag">{e(k)}</span>' for k in x["gestion"].values()) or '<span class="muted">—</span>'
                res = resultado_pill(x["resultado"]) + (f'<div class="muted" style="font-size:11.5px">{e(x["resultado"]["fuente"])}</div>' if x["resultado"] else "")
                filas.append([f'<span class="id">{e(x["id"])}</span>', f'{e(x["titulo"] or "—")}' + (f'<div>{nivel_badge(x["prioridad"])}</div>' if x["prioridad"] else ""),
                              e(", ".join(x["fuentes"]) or "Solo automatización"),
                              "".join(f'<span class="tag">{e(c)}</span>' for c in x["criterios"]) or '<span class="muted">—</span>',
                              aut, ges, res, " ".join(f'<span class="tag">{e(b)}</span>' for b in x["bugs"]) or '<span class="muted">—</span>'])
            body.append(section(f'{h["historia"]} · Matriz de trazabilidad', table(
                ["Caso", "Título", "Origen", "Criterios", "Automatizado", "Gestión", "Último resultado", "Bugs"], filas),
                f'{m["casos"]} casos · {m["automatizados"]} automatizados · {m["con_resultado"]} con resultado'))

    if descartados:
        body.append(section("Descartados", table(["ID", "Motivo"], [[e(i), e(mo)] for i, mo in descartados.items()])))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))

    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Alcance", datos.get("alcance")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
                      ("Historias", ", ".join(h["historia"] for h in hist))])
    return page("Cobertura y trazabilidad", "Cobertura", meta_html, CSS_EXTRA + CSS_COB + "".join(body) + JS_EXTRA)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de cobertura a partir de cobertura.json")
    ap.add_argument("cobertura_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis")
    a = ap.parse_args()
    if not a.salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    with open(a.cobertura_json, encoding="utf-8") as f:
        datos = json.load(f)
    analisis = {}
    if a.analisis:
        with open(a.analisis, encoding="utf-8") as f:
            analisis = json.load(f)
    hist_html = _historial.seccion("cobertura", Path(a.cobertura_json).resolve().parent, datos)
    # ES y EN: el inglés del agente va en el bloque "en" del analisis.json.
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

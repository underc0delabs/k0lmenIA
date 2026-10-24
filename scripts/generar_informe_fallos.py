#!/usr/bin/env python3
"""
Genera el Informe de análisis de fallos en HTML (dashboard, modo oscuro) a partir de fallos.json
(scripts/analizar_fallos.py) y, opcionalmente, del análisis del agente analista-fallos.

Uso:
    python scripts/generar_informe_fallos.py <fallos.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (escenarios, aprobados, con fallas, posibles bugs, inestables,
ambiente y automatización), fallas por causa, por suite y por historia, la tabla de fallas con el
historial de corridas y la captura, y el detalle de cada una (paso que falló, error, causa probable,
qué hacer, captura, video y trace).

El análisis (opcional) aporta:
{
  "veredicto": "2 bugs reales; el resto son tests a estabilizar", "veredicto_tono": "bad",
  "resumen": "Resumen para alguien no técnico...",
  "fallos": {"F-01": {"categoria": "Posible bug", "causa": "El total no suma el envío",
                      "accion": "Reportar el bug", "bug": "BUG-004"}},
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
Categorías: Posible bug · Inestable (flaky) · Locator o espera · Ambiente · Bloqueo anti-bots · Datos de prueba ·
Error en la automatización · Paso sin definir · Sin clasificar
"""
import argparse
import json
from pathlib import Path
import sys

import _historial
from _i18n import escribir_bilingue, localizar, idioma_actual  # noqa: E402
from _estilos_reporte import (e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, donut_panel, two_col,
                              nivel_badge, _pastilla, CRITICO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA, JS_EXTRA, miniatura

CATEGORIAS = ["Posible bug", "Inestable (flaky)", "Locator o espera", "Ambiente", "Bloqueo anti-bots", "Datos de prueba",
              "Error en la automatización", "Paso sin definir", "Sin clasificar"]
# Identidad de cada causa (categórica, orden fijo): nunca colores de estado, que son para aprobado/fallido.
_PROPIAS = [c for c in CATEGORIAS if c != "Bloqueo anti-bots"]
COLOR = {c: SERIES[i] for i, c in enumerate(_PROPIAS)}
COLOR["Bloqueo anti-bots"] = AVISO  # no entra en la paleta de 8: va con el color de aviso
AUTOMATIZACION = {"Locator o espera", "Error en la automatización", "Paso sin definir", "Inestable (flaky)"}

CSS_FALLOS = """
<style>
.err{background:#120F0B;border:1px solid var(--border);border-radius:10px;padding:12px 14px;white-space:pre-wrap;word-break:break-word;
  font-family:var(--mono);font-size:12px;color:#FFB8B0;max-height:320px;overflow:auto}
.runs{display:flex;gap:4px;flex-wrap:wrap}
.cat{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:650;padding:4px 11px;border-radius:999px;
  background:var(--tile);border:1px solid var(--border);color:var(--ink);white-space:nowrap}
.cat i{width:9px;height:9px;border-radius:3px}
.evid{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start}
.evid video{width:420px;max-width:100%;border-radius:10px;border:1px solid var(--border);background:#000}
</style>
"""


def cat_pill(c):
    return f'<span class="cat"><i style="background:{COLOR.get(c, NEUTRO)}"></i>{e(c)}</span>'


def run_pill(estado, nombre):
    if estado == "Aprobado":
        return _pastilla(nombre, OK, "✓")
    if estado == "Fallido":
        return _pastilla(nombre, CRITICO, "✕")
    return _pastilla(nombre, NEUTRO, "–")


def build_html(datos, analisis, hist_html=""):
    ajustes = analisis.get("fallos") or {}
    fallos = []
    for f in datos.get("fallos") or []:
        f = dict(f)
        a = ajustes.get(f["id"]) or {}
        if a.get("categoria") in CATEGORIAS:
            f["categoria"] = a["categoria"]
        f["_analisis"] = a
        fallos.append(f)
    r = datos.get("resumen") or {}
    corridas = datos.get("corridas") or []
    cuenta = {c: sum(1 for f in fallos if f["categoria"] == c) for c in CATEGORIAS}
    siguen = [f for f in fallos if f.get("estado_final") == "Fallido"]
    bugs = cuenta["Posible bug"]

    body = []
    if not fallos:
        tono, texto = "ok", "Todos los escenarios pasaron"
    elif not siguen:
        tono, texto = "warn", "Todo pasó en el reintento: las fallas fueron inestabilidad, no bugs"
    elif bugs:
        tono, texto = "bad", f"{bugs} falla(s) con señales de bug en la aplicación"
    else:
        tono, texto = "warn", "Las fallas apuntan a la automatización, los datos o el ambiente, no a la aplicación"
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))

    total = r.get("escenarios", 0)
    apr = r.get("aprobados", 0)
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Escenarios", total, "", f'{len(corridas)} corrida(s): {", ".join(c["etiqueta"].lower() for c in corridas)}', "lista"),
        ("Aprobados", apr, "ok", f"{round(apr / total * 100) if total else 0} % del total", "ok", {"pct": apr / total * 100 if total else 0}),
        ("Con fallas", len(fallos), "bad" if siguen else ("warn" if fallos else "ok"), f"{len(siguen)} siguen fallando", "bad"),
        ("Posibles bugs", bugs, "bad" if bugs else "ok", "la app respondió distinto de lo esperado", "bicho"),
        ("Inestables", cuenta["Inestable (flaky)"], "warn" if cuenta["Inestable (flaky)"] else "ok", "fallaron y después pasaron", "warn"),
        ("Automatización", sum(cuenta[c] for c in AUTOMATIZACION - {"Inestable (flaky)"}),
         "warn" if any(cuenta[c] for c in AUTOMATIZACION) else "ok", "locators, esperas, código y pasos sin definir", "codigo"),
        ("Ambiente y datos", cuenta["Ambiente"] + cuenta["Bloqueo anti-bots"] + cuenta["Datos de prueba"],
         "warn" if cuenta["Ambiente"] + cuenta["Bloqueo anti-bots"] + cuenta["Datos de prueba"] else "ok",
         "infraestructura caída, anti-bots o datos de prueba", "pantalla"),
        ("Sin clasificar", cuenta["Sin clasificar"], "warn" if cuenta["Sin clasificar"] else "", "revisar a mano", "lupa"),
    ]) + "</div>")

    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    if fallos:
        segs = [(cuenta[c], COLOR[c], c) for c in CATEGORIAS if cuenta[c]]
        principal = max(segs, key=lambda s: s[0])
        body.append(two_col(section("Fallas por causa probable", donut_panel(segs, round(principal[0] / len(fallos) * 100), principal[2][:14].lower()),
                                    "heurística sobre el error; el analista la confirma"),
                            section("Fallas por suite y por historia",
                                    bar_chart([(f'Suite {s}', n, SERIES[2]) for s, n in (r.get("por_suite") or {}).items()]
                                              + sorted([(h, sum(1 for f in fallos if f.get("historia") == h), SERIES[0])
                                                        for h in {f.get("historia") or "Sin historia" for f in fallos}], key=lambda x: -x[1]),
                                              ancho_etiqueta=150))))

        filas = []
        for f in fallos:
            primera = next((l for l in (f.get("error") or "").splitlines() if l.strip()), "")
            cap = next((x["archivo"] for x in f.get("evidencias") or [] if x["tipo"] == "captura"), None)
            hist = "".join(run_pill(s, c["id"]) for s, c in zip(f.get("historial") or [], corridas))
            ident = " · ".join(x for x in [f.get("historia"), f.get("caso"), f.get("suite")] if x)
            filas.append([f'<a class="id" href="#{e(f["id"])}" style="color:var(--ink)">{e(f["id"])}</a>', cat_pill(f["categoria"]),
                          f'<strong style="color:var(--ink)">{e(f["escenario"])}</strong><div class="muted">{e(ident)}</div>',
                          f'<span class="mono">{e(f.get("paso_fallido") or "—")}</span><div class="muted mono">{e(primera[:160])}</div>',
                          f'<div class="runs">{hist}</div>', miniatura(cap, f["escenario"], "s")])
        body.append(section("Escenarios con fallas", table(["ID", "Causa probable", "Escenario", "Paso y error", "Corridas", "Captura"], filas),
                            "clic en el ID para ver el detalle"))

        det = []
        for f in fallos:
            a = f["_analisis"]
            caps = [x for x in f.get("evidencias") or [] if x["tipo"] == "captura"]
            vids = [x for x in f.get("evidencias") or [] if x["tipo"] == "video"]
            trs = [x for x in f.get("evidencias") or [] if x["tipo"] == "trace"]
            evid = "".join(miniatura(x["archivo"], f["escenario"]) for x in caps[:4])
            evid += "".join(f'<video controls preload="metadata" src="{e(x["archivo"])}#t=0.5"></video>' for x in vids[:1])
            traza = "".join(f'<li><a href="{e(x["archivo"])}" download style="color:var(--ink)">{e(x["archivo"].split("/")[-1])}</a> · '
                            f'abrilo en <a href="https://trace.playwright.dev" target="_blank" rel="noopener" style="color:var(--ink)">trace.playwright.dev</a> '
                            f'para ver cada acción, la red y la consola</li>' for x in trs)
            hist = "".join(run_pill(s, f'{c["id"]} · {c["etiqueta"]}') for s, c in zip(f.get("historial") or [], corridas))
            det.append(f'''<div class="hallazgo" id="{e(f["id"])}"><h3>{e(f["id"])} · {e(f["escenario"])} {cat_pill(f["categoria"])}</h3>
              <p class="muted mono">{e(f.get("uri"))}:{e(f.get("linea"))} · {e(" · ".join(x for x in [f.get("historia"), f.get("caso"), "suite " + f["suite"]] if x))} · {e(f.get("duracion_s"))} s</p>
              <div class="lbl">Corridas</div><div class="runs">{hist}</div>
              <div class="lbl">Paso que falló</div><p class="mono" style="color:var(--ink)">{e(f.get("paso_fallido") or "—")}</p>
              {f'<div class="lbl">Error</div><div class="err">{e(chr(10).join((f.get("error") or "").splitlines()[:30]))}</div>' if f.get("error") else ""}
              <div class="lbl">Causa probable</div><p>{e(a.get("causa") or f.get("sugerencia"))}</p>
              {f'<p class="muted">Coincidió con: <span class="mono">{e(f["coincidencia"])}</span></p>' if f.get("coincidencia") and not a.get("causa") else ""}
              {f'<div class="lbl">Qué hacer</div><p>{e(a["accion"])}</p>' if a.get("accion") else ""}
              {f'<div class="lbl">Bug</div><p class="mono" style="color:var(--ink)">{e(a["bug"])}</p>' if a.get("bug") else ""}
              {f'<div class="lbl">Evidencia</div><div class="evid">{evid}</div>' if evid else ""}
              {f'<div class="lbl">Trace</div><ul>{traza}</ul>' if traza else ""}</div>''')
        body.append(section("Detalle de cada falla", "".join(det)))

    filas = [[e(c["id"]), e(c["etiqueta"]), e((c.get("fecha") or "").replace("T", " ")), e(", ".join(c.get("suites") or []))] for c in corridas]
    body.append(section("Corridas analizadas", table(["Corrida", "Tipo", "Fecha", "Suites"], filas),
                        "la original y los reintentos de los escenarios que fallaron"))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))

    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Historia", datos.get("historia")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
                      ("Suites", ", ".join(datos.get("suites") or [])), ("Herramienta", "k0lmena · npm test")])
    return page("Análisis de fallos", "Análisis de fallos", meta_html, CSS_EXTRA + CSS_FALLOS + "".join(body) + JS_EXTRA)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de análisis de fallos a partir de fallos.json")
    ap.add_argument("fallos_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis")
    a = ap.parse_args()
    if not a.salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    with open(a.fallos_json, encoding="utf-8") as f:
        datos = json.load(f)
    analisis = {}
    if a.analisis:
        with open(a.analisis, encoding="utf-8") as f:
            analisis = json.load(f)
    hist_html = _historial.seccion("fallos", Path(a.fallos_json).resolve().parent, datos)
    # ES y EN: el inglés del agente va en el bloque "en" del analisis.json.
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

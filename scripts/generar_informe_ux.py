#!/usr/bin/env python3
"""
Genera el Informe de evaluación de usabilidad en HTML (dashboard, modo oscuro) a partir de ux.json
(npm run ux) y, opcionalmente, del análisis del agente evaluador-ux.

Uso:
    python scripts/generar_informe_ux.py <ux.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (puntaje heurístico, hallazgos, severidad, páginas), el puntaje de cada
una de las 10 heurísticas de Nielsen, los hallazgos agrupados por heurística con el recorte del elemento y
dónde aparecen (los automáticos y los de la revisión manual del agente), la página de error 404, las
páginas en desktop y mobile, recomendaciones y la evolución de las corridas.

El análisis (opcional) aporta:
{
  "veredicto": "...", "veredicto_tono": "warn", "resumen": "...",
  "hallazgos": {"U-03": {"severidad": "Alta", "nota": "..."}},
  "descartados": [{"id": "U-07", "motivo": "..."}],
  "hallazgos_manuales": [{"heuristica": "H1", "severidad": "Alta", "titulo": "Después de pagar no hay confirmación",
                           "detalle": "...", "correccion": "...", "flujo": "Checkout", "url": "https://...",
                           "captura": "capturas/manual-1.png"}],
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],   // "descripcion" vale como alias de que_falta
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
"""
import argparse
import json
import sys
from pathlib import Path

import _historial
from _i18n import escribir_bilingue, idioma_actual, localizar  # noqa: E402,F401
from _estilos_reporte import (falta_informacion, avisar_analisis, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, two_col, gauge,
                              nivel_badge, _pastilla, miniatura, CRITICO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA

SEV = ["Crítica", "Alta", "Media", "Baja"]
PESO = {"Crítica": 40, "Alta": 25, "Media": 10, "Baja": 4}

CSS_UX = """
<style>
.heur{border-top:1px solid var(--border-soft);padding:16px 24px}
.heur:first-child{border-top:0}
.heur h3{font-size:15px;color:var(--ink);display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
.heur h3 .cod{font-family:var(--mono);font-size:12px;padding:3px 8px;border-radius:7px;background:var(--tile);border:1px solid var(--border)}
.item{display:grid;grid-template-columns:minmax(0,1fr) 170px;gap:14px;padding:10px 0;border-top:1px dashed var(--border-soft)}
.item:first-of-type{border-top:0}
.item p{margin:2px 0;color:var(--body);font-size:13px}
.manual{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;background:rgba(144,133,233,.15);color:#C9C2FF;margin-left:6px}
.lado{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;padding:16px 24px}
.lado figure{margin:0;background:var(--bg);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.lado .thumb{display:grid;width:100%;height:240px;border:0;border-radius:0;border-bottom:1px solid var(--border)}
.lado figcaption{padding:8px 12px;font-size:12.5px;color:var(--body)}
.descartado{opacity:.55}
@media (max-width:720px){.item{grid-template-columns:1fr}}
</style>
"""


def corto(u):
    r = (u or "").split("://", 1)[-1].split("/", 1)
    return ("/" + r[1]) if len(r) > 1 and r[1] else "/"


def build_html(datos, analisis, hist_html=""):
    heur = datos.get("heuristicas") or {}
    ajustes = analisis.get("hallazgos") or {}
    desc = {str(d.get("id")): d.get("motivo") for d in analisis.get("descartados") or []}
    hallazgos = []
    for h in datos.get("hallazgos") or []:
        h = dict(h)
        a = ajustes.get(h["id"]) or {}
        if a.get("severidad") in SEV:
            h["severidad"] = a["severidad"]
        h["_nota"], h["_desc"] = a.get("nota"), desc.get(h["id"])
        hallazgos.append(h)
    for i, m in enumerate(analisis.get("hallazgos_manuales") or [], 1):
        hallazgos.append({"id": f"M-{i:02d}", "heuristica": m.get("heuristica", "H1"), "severidad": m.get("severidad", "Media"), "titulo": m.get("titulo", ""),
                          "detalle": m.get("detalle", ""), "correccion": m.get("correccion"), "manual": True, "flujo": m.get("flujo"), "donde": [{"captura": m.get("captura"), "url": m.get("url")}]})
    vivos = [h for h in hallazgos if not h.get("_desc")]
    # Puntaje por heurística (con los manuales incluidos)
    puntajes = {k: max(0, 100 - sum(PESO.get(h["severidad"], 4) for h in vivos if h["heuristica"] == k)) for k in heur}
    total = round(sum(puntajes.values()) / len(puntajes)) if puntajes else 0
    r = datos.get("resumen") or {}
    graves = [h for h in vivos if h["severidad"] in ("Crítica", "Alta")]
    tono = "bad" if graves else ("warn" if vivos else "ok")
    texto = f"Puntaje heurístico {total}/100 · {len(vivos)} problema(s) de usabilidad, {len(graves)} importantes" if vivos else "Sin problemas de usabilidad detectados"
    body = [banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono)]
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Puntaje heurístico", f"{total}/100", "ok" if total >= 85 else "warn" if total >= 65 else "bad", "promedio de las 10 heurísticas de Nielsen", "objetivo", {"pct": total}),
        ("Hallazgos", len(vivos), "bad" if graves else ("warn" if vivos else "ok"), f'{sum(1 for h in vivos if h.get("manual"))} de la revisión manual', "lupa"),
        ("Alta o crítica", len(graves), "bad" if graves else "ok", "frenan o confunden a la persona", "bad"),
        ("Páginas", r.get("paginas", 0), "", f'en {", ".join(datos.get("resoluciones") or [])}', "pantalla"),
    ]) + "</div>")
    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))
    filas = [(f'{k} · {heur[k][:52]}', puntajes[k], OK if puntajes[k] >= 85 else AVISO if puntajes[k] >= 60 else CRITICO) for k in heur]
    body.append(two_col(section("Puntaje por heurística", bar_chart(filas, ancho_etiqueta=380), "100 = sin problemas en esa heurística"),
                        section("Puntaje general", f'<div class="cardbody" style="display:grid;place-items:center">{gauge(total, "de 100")}</div>')))

    bloques = []
    for k, nombre in heur.items():
        hs = [h for h in hallazgos if h["heuristica"] == k]
        if not hs:
            continue
        items = ""
        for h in hs:
            d = (h.get("donde") or [{}])[0]
            ev = d.get("recorte") or d.get("captura")
            mas = f' · y {len(h["donde"]) - 1} más' if len(h.get("donde") or []) > 1 else ""
            donde = f'<p class="muted mono">{e(corto(d.get("url")))} · {e(d.get("resolucion") or "")}{e(mas)}</p>' if d.get("url") else ""
            nota = f'<p><i>{e(h["_nota"])}</i></p>' if h.get("_nota") else ""
            nota += f'<p><b>Cómo corregirlo:</b> {e(h["correccion"])}</p>' if h.get("correccion") else ""
            descartado = f'<p class="muted">Descartado: {e(h["_desc"])}</p>' if h.get("_desc") else ""
            manual = '<span class="manual">revisión manual</span>' if h.get("manual") else ""
            clase = "item descartado" if h.get("_desc") else "item"
            evid = miniatura(ev, h["titulo"], "s") if ev else ""
            items += (f'<div class="{clase}"><div><p>{nivel_badge(h["severidad"])} <strong style="color:var(--ink)">{e(h["id"])} · {e(h["titulo"])}</strong>'
                      f'{manual}</p><p>{e(h.get("detalle"))}</p>{donde}{nota}{descartado}</div><div>{evid}</div></div>')
        bloques.append(f'<div class="heur"><h3><span class="cod">{e(k)}</span>{e(nombre)} {_pastilla(f"{puntajes[k]}/100", OK if puntajes[k] >= 85 else AVISO if puntajes[k] >= 60 else CRITICO, "●")}</h3>{items}</div>')
    if bloques:
        body.append(section("Hallazgos por heurística", "".join(bloques), "automáticos y de la revisión manual del agente"))

    p404 = datos.get("pagina_404") or {}
    if p404:
        filas = [["Dirección probada", f'<span class="mono">{e(p404.get("url"))}</span>'], ["Respuesta", e(p404.get("status") or p404.get("error") or "—")],
                 ["Tiene links para volver", "Sí" if p404.get("links") else "No"], ["Mensaje técnico", "Sí" if p404.get("tecnico") else "No"],
                 ["Lo que muestra", e((p404.get("texto") or "")[:240])]]
        body.append(section("Página de error 404", table(["Dato", "Valor"], filas), "lo que ve alguien que sigue un link roto"))
    figs = "".join(f'<figure>{miniatura(p.get("captura"), corto(p["url"]) + " · " + p["resolucion"])}<figcaption>{e(corto(p["url"]))} · {e(p["resolucion"])} · '
                   f'{e(p.get("hallazgos", 0))} hallazgo(s)</figcaption></figure>' for p in datos.get("pantallas") or [] if p.get("captura"))
    if figs:
        body.append(section("Páginas revisadas", f'<div class="lado">{figs}</div>'))
    body.append(falta_informacion(analisis.get("falta_informacion")))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    if hist_html:
        body.append(hist_html)
    m = meta([("Historia", datos.get("historia")), ("Sitio", datos.get("host")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
              ("Duración", f'{datos.get("duracion_s", 0)} s')])
    return page("Usabilidad", "Evaluación heurística (Nielsen)", m, CSS_EXTRA + CSS_UX + "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de usabilidad a partir de ux.json")
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
        avisar_analisis(analisis, [h.get("id") for h in datos.get("hallazgos") or []])
    hist_html = _historial.seccion("ux", Path(a.datos_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

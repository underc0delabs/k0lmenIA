#!/usr/bin/env python3
"""
Genera el Informe de traducciones en HTML (dashboard, modo oscuro) a partir de traductor.json
(npm run traductor) y, opcionalmente, del análisis del agente analista-traductor.

Uso:
    python scripts/generar_informe_traductor.py <traductor.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (idiomas, páginas, porcentaje traducido, textos sin traducir,
claves a la vista, codificación, cortados y formatos), porcentaje traducido y hallazgos por idioma,
hallazgos por tipo, la matriz página × idioma, cada página en todos los idiomas lado a lado, los
hallazgos con el recorte del texto marcado y dónde aparece, y la evolución de las corridas.

El análisis (opcional) aporta:
{
  "veredicto": "La versión en inglés tiene textos en español en el checkout", "veredicto_tono": "bad",
  "resumen": "Resumen para alguien no técnico...",
  "hallazgos": {"T-01": {"severidad": "Alta", "nota": "...", "sugerencia": "Add to cart"}},
  "descartados": [{"id": "T-09", "motivo": "Es el nombre de la marca"}],
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],   // "descripcion" vale como alias de que_falta
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
from _i18n import escribir_bilingue, idioma_actual, localizar  # noqa: E402,F401
from _estilos_reporte import (falta_informacion, avisar_analisis, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, column_chart, two_col,
                              nivel_badge, _pastilla, miniatura, CRITICO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA

SEV = ["Crítica", "Alta", "Media", "Baja"]
TIPOS = ["Sin traducir", "Igual que la referencia", "Clave de traducción", "Codificación", "Texto cortado", "Texto desbordado", "Desborde",
         "Formato de número", "Fecha en otro idioma", "Atributo lang"]
COLOR_TIPO = {t: SERIES[i % len(SERIES)] for i, t in enumerate(TIPOS)}

CSS_TR = """
<style>
.lado{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;padding:16px 24px}
.lado figure{margin:0;background:var(--bg);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.lado .thumb{display:grid;width:100%;height:280px;border:0;border-radius:0;border-bottom:1px solid var(--border)}
.lado figcaption{padding:9px 12px;font-size:12.5px;color:var(--body);display:flex;justify-content:space-between;gap:8px;align-items:center}
.idioma{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:12px;font-weight:600;padding:3px 9px;
  border-radius:999px;background:var(--tile);border:1px solid var(--border);color:var(--ink)}
.cat{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:650;padding:4px 11px;border-radius:999px;
  background:var(--tile);border:1px solid var(--border);color:var(--ink);white-space:nowrap}
.cat i{width:9px;height:9px;border-radius:3px}
.celda{display:flex;flex-direction:column;align-items:center;gap:6px}
.descartado{opacity:.55}
.sug{color:#C6EDB9}
</style>
"""


def idioma(x, ref=None):
    estrella = " ★" if ref and x == ref else ""
    return f'<span class="idioma">{e(x)}{estrella}</span>'


def corto_url(u):
    r = (u or "").split("://", 1)[-1].split("/", 1)
    return ("/" + r[1]) if len(r) > 1 and r[1] else "/"


def build_html(datos, analisis, hist_html=""):
    ajustes = analisis.get("hallazgos") or {}
    descartados = {str(d.get("id")): d.get("motivo", "") for d in analisis.get("descartados") or []}
    hallazgos = []
    for h in datos.get("hallazgos") or []:
        h = dict(h)
        a = ajustes.get(h["id"]) or {}
        if a.get("severidad") in SEV:
            h["severidad"] = a["severidad"]
        h["_a"] = a
        h["_descartado"] = descartados.get(h["id"])
        hallazgos.append(h)
    vivos = [h for h in hallazgos if not h["_descartado"]]
    r = datos.get("resumen") or {}
    ref = datos.get("referencia")
    idiomas = datos.get("idiomas") or []
    por_idioma = r.get("por_idioma") or {}
    otros = [i for i in idiomas if i != ref]
    prom = [por_idioma[i]["traducido_pct"] for i in otros if por_idioma.get(i, {}).get("traducido_pct") is not None]
    prom = round(sum(prom) / len(prom), 1) if prom else None
    body = []
    graves = [h for h in vivos if h["severidad"] in ("Crítica", "Alta")]
    if graves:
        tono, texto = "bad", f"{len(graves)} problema(s) importantes: textos sin traducir, claves a la vista o caracteres rotos"
    elif vivos:
        tono, texto = "warn", "Las traducciones están; quedan detalles de formato y espacio"
    else:
        tono, texto = "ok", f"El sitio está completo en {', '.join(idiomas)}"
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Idiomas", len(idiomas), "", f"referencia: {ref}", "persona"),
        ("Páginas", r.get("paginas", 0), "", f'{r.get("pantallas", 0)} pantallas (página × idioma × resolución)', "pantalla"),
        ("Traducido", f"{prom} %" if prom is not None else "—", "" if prom is None else ("ok" if prom >= 98 else "warn" if prom >= 90 else "bad"),
         "de los textos, promedio de los idiomas", "ok", {"pct": prom} if prom is not None else None),
        ("Sin traducir", r.get("sin_traducir", 0), "bad" if r.get("sin_traducir") else "ok", "en otro idioma o igual a la referencia", "warn"),
        ("Claves a la vista", r.get("claves", 0), "bad" if r.get("claves") else "ok", "nombres internos en lugar del texto", "codigo"),
        ("Codificación", r.get("codificacion", 0), "bad" if r.get("codificacion") else "ok", "caracteres rotos (Ã©, â€™)", "bad"),
        ("Cortados", r.get("cortados", 0), "warn" if r.get("cortados") else "ok", "textos que no entran o desbordan", "mover"),
        ("Formatos", r.get("formatos", 0), "warn" if r.get("formatos") else "ok", "números o fechas de otra región", "reloj"),
    ]) + "</div>")
    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    filas_pct = [(i, por_idioma[i]["traducido_pct"], OK if por_idioma[i]["traducido_pct"] >= 98 else AVISO if por_idioma[i]["traducido_pct"] >= 90 else CRITICO)
                 for i in otros if por_idioma.get(i, {}).get("traducido_pct") is not None]
    tipos = Counter(h["tipo"] for h in vivos)
    body.append(two_col(
        section("Traducido por idioma", column_chart(filas_pct, fmt=lambda v: f"{v:g} %", ancho=660) if filas_pct else '<p class="muted" style="padding:16px 24px">—</p>',
                "porcentaje de los textos de cada idioma que están traducidos"),
        section("Hallazgos por tipo", bar_chart([(t, tipos[t], COLOR_TIPO.get(t, NEUTRO)) for t in TIPOS if tipos[t]], ancho_etiqueta=170) if tipos
                else '<p class="muted" style="padding:16px 24px">Sin hallazgos.</p>')))

    filas = [[idioma(i, ref), e(por_idioma.get(i, {}).get("metodo") or "—"),
              e(f'{por_idioma[i]["traducido_pct"]} %' if por_idioma.get(i, {}).get("traducido_pct") is not None else "—"),
              e(por_idioma.get(i, {}).get("hallazgos", 0))] for i in idiomas]
    body.append(section("Idiomas", table(["Idioma", "Cómo se cambió", "Traducido", "Hallazgos"], filas),
                        "★ referencia · hreflang: links del sitio · plantilla: URL armada · navegador: el sitio elige por el idioma del navegador"))

    pantallas = datos.get("pantallas") or []
    claves = list(dict.fromkeys((p["pagina"], p["url"], p["resolucion"]) for p in pantallas))
    filas = []
    for pag, url, res in claves:
        fila = [f'<span class="mono" style="color:var(--ink)">{e(corto_url(url))}</span><div class="muted">{e(res)}</div>']
        for i in idiomas:
            p = next((x for x in pantallas if x["pagina"] == pag and x["resolucion"] == res and x["idioma"] == i), None)
            if not p:
                fila.append('<span class="muted">—</span>')
                continue
            n = p.get("hallazgos", 0)
            est = _pastilla("Error", NEUTRO, "⊘") if p.get("error") else _pastilla(f"{n} hallazgo(s)" if n else "OK", AVISO if n else OK, "!" if n else "✓")
            fila.append(f'<div class="celda"><a href="#p-{e(pag)}-{e(res)}" style="text-decoration:none">{est}</a>'
                        f'{miniatura(p.get("captura"), f"{corto_url(url)} · {i} · {res}", "s") if p.get("captura") else ""}</div>')
        filas.append(fila)
    if filas:
        body.append(section("Matriz de páginas e idiomas", f'<div class="matriz">{table(["Página"] + idiomas, filas)}</div>',
                            "clic en el estado para ver la página en todos los idiomas"))
    bloques = []
    for pag, url, res in claves:
        figs = ""
        for i in idiomas:
            p = next((x for x in pantallas if x["pagina"] == pag and x["resolucion"] == res and x["idioma"] == i), None)
            if p and p.get("captura"):
                titulo = f"{corto_url(url)} · {i} · {res}"
                figs += (f'<figure>{miniatura(p["captura"], titulo)}<figcaption>{idioma(i, ref)}'
                         f'<span class="muted">{e(p.get("lang") or "sin lang")} · {e(p.get("hallazgos", 0))} hallazgo(s)</span></figcaption></figure>')
        bloques.append(f'<details class="pag" id="p-{e(pag)}-{e(res)}"><summary><strong>{e(corto_url(url))}</strong><span class="muted">{e(res)}</span></summary>'
                       f'<div class="lado">{figs}</div></details>')
    if bloques:
        body.append(section("Cada página en todos los idiomas", "".join(bloques), "lado a lado, para comparar largo de textos y diseño"))

    if hallazgos:
        filas = []
        for h in hallazgos:
            donde = h.get("donde") or []
            mas = f" y {len(donde) - 1} más" if len(donde) > 1 else ""
            sug = f'<div class="sug">Sugerencia: {e(h["_a"]["sugerencia"])}</div>' if h["_a"].get("sugerencia") else ""
            nota = f'<div class="muted">{e(h["_a"]["nota"])}</div>' if h["_a"].get("nota") else ""
            desc = f'<div class="muted">Descartado: {e(h["_descartado"])}</div>' if h["_descartado"] else ""
            primero = donde[0] if donde else {}
            filas.append([f'<span style="white-space:nowrap">{e(h["id"])}</span>', nivel_badge(h["severidad"]), f'<span class="cat"><i style="background:{COLOR_TIPO.get(h["tipo"], NEUTRO)}"></i>{e(h["tipo"])}</span>',
                          idioma(h["idioma"], ref), f'<strong style="color:var(--ink)">{e(h["titulo"])}</strong><div class="muted">{e(h.get("detalle"))}</div>{sug}{nota}{desc}',
                          f'<span class="mono">{e(corto_url(primero.get("url")))}</span><div class="muted">{e(primero.get("resolucion"))}{e(mas)}</div>',
                          miniatura(primero.get("recorte") or primero.get("captura"), h["titulo"], "s") if (primero.get("recorte") or primero.get("captura")) else '<span class="muted">—</span>'])
        body.append(section("Hallazgos", table(["ID", "Severidad", "Tipo", "Idioma", "Hallazgo", "Dónde", "Evidencia"], filas),
                            "un mismo texto en varias páginas es un solo hallazgo"))
    body.append(falta_informacion(analisis.get("falta_informacion")))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Historia", datos.get("historia")), ("Sitio", datos.get("host")), ("Idiomas", ", ".join(idiomas)),
                      ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")), ("Duración", f'{datos.get("duracion_s", 0)} s')])
    return page("Traducciones", "Traducción e idiomas", meta_html, CSS_EXTRA + CSS_TR + "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de traducciones a partir de traductor.json")
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
    hist_html = _historial.seccion("traductor", Path(a.datos_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

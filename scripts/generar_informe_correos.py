#!/usr/bin/env python3
"""
Genera el Informe de correos en HTML (dashboard, modo oscuro) a partir de correos.json (npm run correos)
y, opcionalmente, del análisis del agente verificador-correos.

Uso:
    python scripts/generar_informe_correos.py <correos.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (correos revisados, expectativas cumplidas, no llegaron, hallazgos,
variables sin reemplazar, links con problemas, compatibilidad), las expectativas de cada caso (qué tenía
que llegar y qué se controló), hallazgos por tipo y severidad, compatibilidad por correo, cada correo
con su vista en desktop y mobile, encabezados, links, adjuntos y problemas, la tabla de hallazgos y la
evolución de las corridas.

El análisis (opcional) aporta:
{
  "veredicto": "El mail de pedido sale con variables vacías", "veredicto_tono": "bad",
  "resumen": "Resumen para alguien no técnico...",
  "hallazgos": {"C-02": {"severidad": "Crítica", "nota": "Lo recibe cada cliente que compra"}},
  "descartados": [{"id": "C-11", "motivo": "Outlook no es un cliente objetivo"}],
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
from _estilos_reporte import (falta_informacion, avisar_analisis, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, column_chart, donut_panel, two_col,
                              nivel_badge, _pastilla, miniatura, NIVEL_COLOR, CRITICO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA

SEV = ["Crítica", "Alta", "Media", "Baja"]
EXPECT = {"Cumple": (OK, "✓"), "No cumple": (CRITICO, "✕"), "No llegó": (CRITICO, "⊘")}

CSS_COR = """
<style>
.correo{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,.65fr);gap:18px;padding:18px 24px;border-top:1px solid var(--border-soft)}
.correo:first-child{border-top:0}
.correo h3{font-size:16px;color:var(--ink);margin-bottom:8px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.hdrs{display:grid;grid-template-columns:110px 1fr;gap:4px 12px;font-size:13px;margin:8px 0 12px}
.hdrs dt{color:var(--muted)}
.hdrs dd{margin:0;color:var(--ink);word-break:break-all}
.vistas{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:10px}
.vistas figure{margin:0}
.vistas figcaption{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin-bottom:6px}
.vistas .thumb{display:grid;width:100%;height:340px}
.ctl{list-style:none;margin:6px 0 0;padding:0}
.ctl li{display:flex;gap:8px;align-items:baseline;font-size:13px;color:var(--body);margin:3px 0}
.ctl b{font-weight:700}
.ctl .si{color:#7BD36A}.ctl .no{color:#FF7B70}
.linkst td{font-size:12.5px}
.cat{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:650;padding:4px 11px;border-radius:999px;
  background:var(--tile);border:1px solid var(--border);color:var(--ink);white-space:nowrap}
.cat i{width:9px;height:9px;border-radius:3px}
.descartado{opacity:.55}
@media (max-width:980px){.correo{grid-template-columns:1fr}}
</style>
"""


def pill(mapa, v):
    color, ic = mapa.get(v, (NEUTRO, "●"))
    return _pastilla(v or "—", color, ic)


def controles(x):
    if not x.get("controles"):
        return '<span class="muted">—</span>'
    items = []
    for c in x["controles"]:
        clase, marca = ("si", "✓") if c["ok"] else ("no", "✕")
        detalle = f' <span class="muted">· {e(c.get("detalle"))}</span>' if c.get("detalle") and not c["ok"] else ""
        items.append(f'<li><b class="{clase}">{marca}</b>{e(c["nombre"])}{detalle}</li>')
    return '<ul class="ctl">' + "".join(items) + "</ul>"


def build_html(datos, analisis, hist_html=""):
    ajustes = analisis.get("hallazgos") or {}
    descartados = {str(d.get("id")): d.get("motivo", "") for d in analisis.get("descartados") or []}
    hallazgos = []
    for h in datos.get("hallazgos") or []:
        h = dict(h)
        a = ajustes.get(h["id"]) or {}
        if a.get("severidad") in SEV:
            h["severidad"] = a["severidad"]
        h["_nota"] = a.get("nota")
        h["_descartado"] = descartados.get(h["id"])
        hallazgos.append(h)
    vivos = [h for h in hallazgos if not h["_descartado"]]
    correos = datos.get("correos") or []
    exp = datos.get("expectativas") or []
    r = datos.get("resumen") or {}
    body = []

    graves = [h for h in vivos if h["severidad"] in ("Crítica", "Alta")]
    if not correos and not exp:
        tono, texto = "warn", "No hay correos en el buzón para ese filtro"
    elif r.get("no_llegaron"):
        tono, texto = "bad", f'{r["no_llegaron"]} correo(s) esperados no llegaron'
    elif graves:
        tono, texto = "bad", f"{len(graves)} problema(s) importantes en los correos"
    elif vivos:
        tono, texto = "warn", "Los correos llegan; hay detalles a mejorar"
    else:
        tono, texto = "ok", "Los correos llegan bien y sin problemas"
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))
    ne = r.get("expectativas", 0)
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Correos revisados", r.get("correos", 0), "", datos.get("filtro") or "todo el buzón", "lista"),
        ("Expectativas cumplidas", f'{r.get("cumplen", 0)}/{ne}' if ne else "—", ("ok" if r.get("cumplen") == ne else "bad") if ne else "",
         "lo que tenía que llegar, como tenía que llegar", "objetivo", {"pct": r.get("cumplen", 0) / ne * 100} if ne else None),
        ("No llegaron", r.get("no_llegaron", 0), "bad" if r.get("no_llegaron") else "ok", "correos esperados que no están", "bad"),
        ("Hallazgos", len(vivos), "bad" if graves else ("warn" if vivos else "ok"), f'{len(graves)} de severidad alta o crítica', "warn"),
        ("Variables sin reemplazar", r.get("variables_sin_reemplazar", 0), "bad" if r.get("variables_sin_reemplazar") else "ok",
         "{{nombre}}, undefined, null… a la vista", "codigo"),
        ("Links con problemas", r.get("links_con_problemas", 0), "bad" if r.get("links_con_problemas") else "ok", f'de {r.get("links", 0)} links revisados', "link"),
        ("Compatibilidad", f'{r["compatibilidad_prom"]} %' if r.get("compatibilidad_prom") is not None else "—",
         "" if r.get("compatibilidad_prom") is None else ("ok" if r["compatibilidad_prom"] >= 90 else "warn"), "del HTML con los clientes de correo", "pantalla"),
    ]) + "</div>")
    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    if exp:
        filas = [[e(x["id"]), e(x.get("caso") or "—"), f'<strong style="color:var(--ink)">{e(x.get("asunto") or "—")}</strong>'
                  f'<div class="muted">{e(x.get("para") or "")}</div>', pill(EXPECT, x["estado"]), controles(x),
                  f'<a href="#{e(x["correo"])}" style="color:var(--ink)">{e(x["correo"])}</a>' if x.get("correo") else '<span class="muted">—</span>']
                 for x in exp]
        body.append(section("Lo que tenía que llegar", table(["ID", "Caso", "Correo esperado", "Resultado", "Controles", "Correo"], filas),
                            "cada caso de prueba con el correo que espera y qué se verificó"))

    if vivos:
        tipos = Counter(h["tipo"] for h in vivos)
        sev = Counter(h["severidad"] for h in vivos)
        segs = [(sev[s], NIVEL_COLOR.get(s, NEUTRO), s) for s in SEV if sev[s]]
        principal = max(segs, key=lambda s: s[0])
        body.append(two_col(
            section("Hallazgos por tipo", bar_chart([(t, n, SERIES[i % len(SERIES)]) for i, (t, n) in enumerate(tipos.most_common())], ancho_etiqueta=160)),
            section("Hallazgos por severidad", donut_panel(segs, round(principal[0] / len(vivos) * 100), principal[2].lower()))))
    compat = [(c["id"], c["compatibilidad"]["pct"]) for c in correos if c.get("compatibilidad") and c["compatibilidad"].get("pct") is not None]
    if compat:
        body.append(section("Compatibilidad del HTML por correo", column_chart([(i, p, OK if p >= 90 else AVISO if p >= 75 else CRITICO) for i, p in compat],
                                                                          fmt=lambda v: f"{v:g} %"),
                            "porcentaje de las funciones del HTML soportadas por los clientes de correo (Outlook, Gmail, Apple Mail, Yahoo…)"))

    bloques = []
    for c in correos:
        hs = [h for h in hallazgos if h.get("correo") == c["id"]]
        adjuntos = ", ".join("%s (%s KB)" % (a["nombre"], a["kb"]) for a in c.get("adjuntos") or [])
        hdr = (f'<dl class="hdrs"><dt>De</dt><dd>{e(c["de"])}</dd><dt>Para</dt><dd>{e(", ".join(c["para"]))}</dd>'
               + (f'<dt>Cc</dt><dd>{e(", ".join(c["cc"]))}</dd>' if c.get("cc") else "")
               + (f'<dt>Responder a</dt><dd>{e(", ".join(c["responder_a"]))}</dd>' if c.get("responder_a") else "")
               + f'<dt>Recibido</dt><dd>{e((c.get("fecha") or "")[:16].replace("T", " "))}</dd>'
               + f'<dt>Tamaño</dt><dd>{e(c["tamano_kb"])} KB · HTML {e(c["html_kb"])} KB · {"con" if c["tiene_texto"] else "sin"} texto plano</dd>'
               + (f'<dt>Adjuntos</dt><dd>{e(adjuntos)}</dd>' if adjuntos else "")
               + "</dl>")
        prob = ""
        for h in hs:
            nota = f'<div><i>{e(h["_nota"])}</i></div>' if h.get("_nota") else ""
            prob += (f'<li>{nivel_badge(h["severidad"])} <strong style="color:var(--ink)">{e(h["titulo"])}</strong>'
                     f'<div class="muted">{e(h.get("detalle"))}</div>{nota}</li>')
        links = ""
        if c.get("links"):
            filas = [[f'<span class="mono">{e(l["url"][:90])}</span>', e(l.get("texto") or "—"), e(l.get("status") if l.get("status") is not None else "—"),
                      _pastilla(l["problema"]["texto"], CRITICO if l["problema"]["severidad"] == "Alta" else AVISO, "!") if l.get("problema") else _pastilla("OK", OK, "✓")]
                     for l in c["links"][:30]]
            links = '<div class="lbl">Links</div><div class="linkst">' + table(["URL", "Texto", "Status", "Estado"], filas) + "</div>"
        compat_html = ""
        if c.get("compatibilidad") and c["compatibilidad"].get("problemas"):
            compat_html = '<div class="lbl">Sin soporte en algunos clientes</div><ul class="doclist">' + "".join(
                f'<li><strong style="color:var(--ink)">{e(p["titulo"])}</strong> <span class="muted">· {e(", ".join(p["clientes"]))}</span></li>'
                for p in c["compatibilidad"]["problemas"][:8]) + "</ul>"
        vistas = (f'<div class="vistas"><figure><figcaption>Desktop (700 px)</figcaption>{miniatura(c.get("captura_desktop"), c["asunto"] + " · desktop")}</figure>'
                  f'<figure><figcaption>Mobile (375 px)</figcaption>{miniatura(c.get("captura_mobile"), c["asunto"] + " · mobile")}</figure></div>')
        extra = " · ".join(x for x in [f'<a href="{e(c["eml"])}" download style="color:var(--ink)">descargar .eml</a>' if c.get("eml") else "",
                                        f'<a href="{e(c["ver_en_mailpit"])}" target="_blank" rel="noopener" style="color:var(--ink)">ver en Mailpit</a>'] if x)
        bloques.append(f'''<div class="correo" id="{e(c["id"])}"><div><h3>{e(c["id"])} · {e(c["asunto"] or "(sin asunto)")}
            {_pastilla(f"{len(hs)} hallazgo(s)", CRITICO if any(h["severidad"] in ("Crítica", "Alta") for h in hs) else AVISO if hs else OK, "!" if hs else "✓")}</h3>
            {hdr}{f'<div class="lbl">Problemas</div><ul class="doclist">{prob}</ul>' if prob else '<p class="muted">Sin problemas detectados.</p>'}
            {links}{compat_html}<p class="muted" style="margin-top:10px">{extra}</p></div><div>{vistas}</div></div>''')
    if bloques:
        body.append(section("Cada correo", "".join(bloques), "cómo se ve en desktop y mobile, encabezados, links, adjuntos y problemas"))

    if hallazgos:
        filas = [[e(h["id"]), nivel_badge(h["severidad"]), f'<span class="cat"><i style="background:{SERIES[0]}"></i>{e(h["tipo"])}</span>',
                  f'<strong style="color:var(--ink)">{e(h["titulo"])}</strong>' + (f'<div class="muted">Descartado: {e(h["_descartado"])}</div>' if h["_descartado"] else ""),
                  f'<a href="#{e(h["correo"])}" style="color:var(--ink)">{e(h["correo"])}</a>' if h.get("correo") else '<span class="muted">—</span>']
                 for h in hallazgos]
        body.append(section("Todos los hallazgos", table(["ID", "Severidad", "Tipo", "Hallazgo", "Correo"], filas)))
    body.append(falta_informacion(analisis.get("falta_informacion")))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Historia", datos.get("historia")), ("Buzón", datos.get("mailpit")), ("Mailpit", datos.get("version_mailpit")),
                      ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " "))])
    return page("Verificación de correos", "Correos", meta_html, CSS_EXTRA + CSS_COR + "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de correos a partir de correos.json")
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
    hist_html = _historial.seccion("correos", Path(a.datos_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

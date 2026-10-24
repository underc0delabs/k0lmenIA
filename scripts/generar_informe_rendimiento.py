#!/usr/bin/env python3
"""
Genera el Informe de rendimiento web en HTML (dashboard, modo oscuro) a partir de la auditoría
con Lighthouse (rendimiento.json, de `npm run rendimiento`) y, opcionalmente, del análisis del
agente auditor-rendimiento-web. `npm run rendimiento` ya lo genera solo al terminar; el agente lo
vuelve a generar con su análisis.

Uso:
    python scripts/generar_informe_rendimiento.py <rendimiento.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (puntaje mobile y desktop, Core Web Vitals en verde, peores
métricas, peso y requests), puntajes por página, Core Web Vitals por página con su calificación
(bueno / a mejorar / malo), LCP por página, las oportunidades de mejora con su ahorro estimado y los
recursos que las causan, el peso por tipo de recurso, el elemento LCP, los terceros, la secuencia de
carga y la captura final, y el link al reporte nativo de Lighthouse de cada página.

Los datos salen del rendimiento.json. El análisis (opcional) aporta:
{
  "veredicto": "Rendimiento aceptable en desktop; mobile a mejorar", "veredicto_tono": "warn",
  "resumen": "Resumen para alguien no técnico...",
  "notas": {"R-02": "El caché lo configura el CDN: lo confirma el equipo de infraestructura"},
  "descartados": [{"id": "R-05", "motivo": "El script de terceros es el chat de soporte, se acepta"}],
  "severidades": {"R-03": "Alta"},
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],   // "descripcion" vale como alias de que_falta
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
"""
import argparse
import datetime
import json
from pathlib import Path
import math
import sys

import _historial
from _i18n import escribir_bilingue, idioma_actual, localizar  # noqa: E402,F401
from _estilos_reporte import (falta_informacion, avisar_analisis, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, stacked_bars,
                              grouped_columns, two_col, nivel_badge, _pastilla, CRITICO, AVISO, NEUTRO, OK, SERIES, SERIO,
                              SUPERFICIE)
from generar_informe_exploratorio import CSS_EXTRA, JS_EXTRA, miniatura, corto, origen

SEVERIDADES = [("Crítica", CRITICO), ("Alta", SERIO), ("Media", AVISO), ("Baja", NEUTRO)]
ORDEN = {s: i for i, (s, _) in enumerate(SEVERIDADES)}
ESTADO = {"bueno": ("Bueno", OK, "✓"), "mejorar": ("A mejorar", AVISO, "!"), "malo": ("Malo", CRITICO, "✕")}
TIPOS = ["Documento", "JavaScript", "CSS", "Imágenes", "Fuentes", "Video y audio", "Datos (fetch/XHR)", "Otros"]
DISP = {"mobile": "Mobile", "desktop": "Desktop"}

CSS_REND = """
<style>
.gauges{display:grid;grid-template-columns:repeat(auto-fill,minmax(400px,1fr));gap:16px;padding:12px 24px 24px}
.gcard{background:var(--tile);border:1px solid var(--border);border-radius:16px;padding:16px 18px}
.gcard .u{font-size:12.5px;color:var(--ink);font-weight:650;margin-bottom:12px;word-break:break-all}
.grow{display:flex;gap:10px;justify-content:space-around;flex-wrap:wrap}
.g{display:flex;flex-direction:column;align-items:center;gap:6px;width:80px;text-align:center;font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;font-weight:650}
.gnum{font-size:22px;font-weight:760;fill:var(--ink)}
.film{display:flex;gap:10px;overflow-x:auto;padding:4px 0 10px}
.film figure{margin:0;flex:none;width:96px;text-align:center}
.film .thumb{width:96px;height:170px}
.film .thumb img{object-fit:contain;background:#000}
.film .thumb::before{display:none}
.film.desktop figure{width:150px}.film.desktop .thumb{width:150px;height:100px}
.film figcaption{font-size:11px;color:var(--muted);margin-top:4px;font-variant-numeric:tabular-nums}
.filmrow{padding:14px 24px;border-top:1px solid var(--border-soft)}
.filmrow:first-of-type{border-top:0}
.filmrow .t{font-size:12.5px;color:var(--body);margin-bottom:8px}
</style>
"""


def anillo(valor, etiqueta, tam=74):
    """Anillo de puntaje 0-100 (como Lighthouse): verde desde 90, amarillo desde 50, rojo debajo."""
    if valor is None:
        return f'<div class="g"><svg width="{tam}" height="{tam}"></svg>{e(etiqueta)}</div>'
    color = OK if valor >= 90 else AVISO if valor >= 50 else CRITICO
    r = tam / 2 - 7
    c = 2 * math.pi * r
    largo = c * valor / 100
    estado = "bueno" if valor >= 90 else "a mejorar" if valor >= 50 else "malo"
    return (f'<div class="g" data-tip="{e(etiqueta)}: {valor}/100 ({estado})" tabindex="0"><svg width="{tam}" height="{tam}" viewBox="0 0 {tam} {tam}">'
            f'<circle cx="{tam / 2}" cy="{tam / 2}" r="{r}" fill="none" stroke="#2E281F" stroke-width="7"/>'
            f'<circle cx="{tam / 2}" cy="{tam / 2}" r="{r}" fill="none" stroke="{color}" stroke-width="7" stroke-linecap="round" '
            f'stroke-dasharray="{largo:.1f} {c - largo:.1f}" transform="rotate(-90 {tam / 2} {tam / 2})"/>'
            f'<text x="{tam / 2}" y="{tam / 2 + 7}" text-anchor="middle" class="gnum">{valor}</text></svg>{e(etiqueta)}</div>')


def pill_metrica(m):
    if not m:
        return '<span class="muted">—</span>'
    nombre, color, icono = ESTADO.get(m.get("estado"), ("—", NEUTRO, "●"))
    return _pastilla(f'{m.get("texto", "")} · {nombre}', color, icono)


def kb(bytes_):
    return f"{(bytes_ or 0) / 1024:,.0f} KB".replace(",", ".") if (bytes_ or 0) < 1024 * 1024 else f"{bytes_ / 1048576:.1f} MB".replace(".", ",")


def tono_auto(res):
    ok = [r for r in res if not r.get("error")]
    estados = [m.get("estado") for r in ok for k, m in (r.get("metricas") or {}).items() if k in ("lcp", "cls", "tbt")]
    if any(r.get("error") for r in res) or "malo" in estados:
        return "bad", "Hay Core Web Vitals en rojo: la carga es lenta o inestable para las personas"
    puntajes = [r["puntajes"].get("performance") for r in ok if r["puntajes"].get("performance") is not None]
    if "mejorar" in estados or any(p < 90 for p in puntajes):
        return "warn", "Rendimiento a mejorar: hay métricas fuera de lo recomendado por Google"
    return "ok", "Buen rendimiento en lo medido (datos de laboratorio)"


def build_html(datos, analisis, hist_html=""):
    descartados = {str(d.get("id")): d.get("motivo", "") for d in analisis.get("descartados") or []}
    notas = analisis.get("notas") or {}
    ajustes = analisis.get("severidades") or {}
    base = origen(datos.get("url"))
    res = datos.get("resultados") or []
    ok = [r for r in res if not r.get("error")]
    r = datos.get("resumen") or {}
    cfg = datos.get("config") or {}
    dispositivos = cfg.get("dispositivos") or ["mobile", "desktop"]
    paginas = list(dict.fromkeys(x["url"] for x in res))

    hallazgos = []
    for h in datos.get("hallazgos") or []:
        if h.get("id") in descartados:
            continue
        h = dict(h)
        if ajustes.get(h.get("id")) in ORDEN:
            h["severidad"] = ajustes[h["id"]]
        hallazgos.append(h)
    hallazgos.sort(key=lambda h: ORDEN.get(h.get("severidad"), 9))

    body = []
    tono, texto = tono_auto(res)
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))

    def peor(clave, disp):
        xs = [x["metricas"][clave] for x in ok if x["dispositivo"] == disp and clave in (x.get("metricas") or {})]
        return max(xs, key=lambda m: m["valor"]) if xs else None

    disp_ppal = "mobile" if "mobile" in dispositivos else dispositivos[0]
    tiles = []
    for d in dispositivos:
        p = r.get(f"rendimiento_{d}")
        tiles.append((f"Rendimiento {DISP[d].lower()}", "—" if p is None else p, "" if p is None else "ok" if p >= 90 else "warn" if p >= 50 else "bad",
                      "puntaje promedio de Lighthouse (0-100)", "rayo", {"pct": p or 0}))
    v = r.get(f"vitales_ok_{disp_ppal}")
    tiles.append((f"Core Web Vitals en verde ({DISP[disp_ppal].lower()})", "—" if v is None else f"{v}/{len(paginas)}",
                  "" if v is None else "ok" if v == len(paginas) else "warn", "páginas con LCP, CLS y TBT buenos", "objetivo"))
    for clave, ic in (("lcp", "reloj"), ("tbt", "codigo"), ("cls", "pantalla")):
        m = peor(clave, disp_ppal)
        tono_m = {"bueno": "ok", "mejorar": "warn", "malo": "bad"}.get(m["estado"]) if m else ""
        tiles.append((f"Peor {clave.upper()} ({DISP[disp_ppal].lower()})", m["texto"] if m else "—", tono_m, "", ic))
    pesos = [x["peso_total"] for x in ok if x["dispositivo"] == disp_ppal]
    reqs = [x["requests"] for x in ok if x["dispositivo"] == disp_ppal]
    tiles.append(("Peso promedio por página", kb(sum(pesos) / len(pesos)) if pesos else "—", "",
                  f"{round(sum(reqs) / len(reqs))} requests en promedio" if reqs else "", "carga"))
    tiles.append(("Oportunidades de mejora", r.get("oportunidades", 0), "warn" if r.get("oportunidades") else "ok", "auditorías con ahorro estimado", "lupa"))
    body.append('<div style="margin-top:20px">' + kpi_tiles(tiles) + "</div>")

    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    # ---- Puntajes por página
    tarjetas = []
    for u in paginas:
        anillos = []
        for d in dispositivos:
            x = next((y for y in ok if y["url"] == u and y["dispositivo"] == d), None)
            anillos.append(anillo(x["puntajes"].get("performance") if x else None, f"Rendimiento {DISP[d]}"))
        x = next((y for y in ok if y["url"] == u), None)
        if x:
            anillos.append(anillo(x["puntajes"].get("best-practices"), "Buenas prácticas"))
            anillos.append(anillo(x["puntajes"].get("seo"), "SEO"))
        tarjetas.append(f'<div class="gcard"><div class="u mono">{e(corto(u, base))}</div><div class="grow">{"".join(anillos)}</div></div>')
    body.append(section("Puntajes por página", f'<div class="gauges">{"".join(tarjetas)}</div>',
                        "verde 90-100 · amarillo 50-89 · rojo 0-49"))

    if len(dispositivos) > 1 and len(paginas) > 1:
        series = [(DISP[d], SERIES[1] if d == "mobile" else SERIES[2],
                   [next((y["puntajes"].get("performance") for y in ok if y["url"] == u and y["dispositivo"] == d), None) for u in paginas])
                  for d in dispositivos]
        body.append(section("Rendimiento por página y dispositivo", grouped_columns([corto(u, base) for u in paginas], series, alto=280),
                            "puntaje de Lighthouse (0-100)"))

    # ---- Core Web Vitals
    filas = []
    for x in res:
        celdas = [f'<span class="mono">{e(corto(x["url"], base))}</span>', e(DISP.get(x["dispositivo"], x["dispositivo"]))]
        if x.get("error"):
            celdas += [_pastilla("No se pudo medir", CRITICO, "✕")] + ["—"] * 4
        else:
            celdas += [pill_metrica((x.get("metricas") or {}).get(k)) for k in ("lcp", "cls", "tbt", "fcp", "si")]
        celdas.append(f'<a href="{e(x["lighthouse"])}" target="_blank" style="color:var(--ink)">abrir</a>' if x.get("lighthouse") else "—")
        filas.append(celdas)
    body.append(section("Core Web Vitals y métricas", table(["Página", "Dispositivo", "LCP", "CLS", "TBT", "FCP", "Speed Index", "Lighthouse"], filas),
                        "LCP, CLS y TBT son los Core Web Vitals (TBT es el equivalente de laboratorio de INP)"))

    lcps = sorted([(f'{corto(x["url"], base)} · {DISP[x["dispositivo"]]}', round(x["metricas"]["lcp"]["valor"] / 1000, 2),
                    {"bueno": OK, "mejorar": AVISO, "malo": CRITICO}[x["metricas"]["lcp"]["estado"]])
                   for x in ok if "lcp" in (x.get("metricas") or {})], key=lambda t: -t[1])
    if lcps:
        body.append(section("LCP por página", bar_chart(lcps[:16], ancho_etiqueta=260),
                            "segundos hasta que se ve el contenido principal · verde ≤ 2,5 s · amarillo ≤ 4 s · rojo más de 4 s"))

    # ---- Hallazgos
    if hallazgos:
        filas = []
        for h in hallazgos:
            nota = f'<div class="muted" style="margin-top:4px">{e(notas[h["id"]])}</div>' if h.get("id") in notas else ""
            pags = h.get("paginas") or [h.get("pagina")]
            filas.append([f'<span class="id">{e(h["id"])}</span>', nivel_badge(h.get("severidad")), e(h.get("categoria")),
                          f'<strong style="color:var(--ink)">{e(h.get("titulo"))}</strong><div class="muted">{e(h.get("detalle"))}</div>{nota}',
                          f'<span class="mono">{e(corto(pags[0], base))}</span>' + (f'<div class="muted">y {len(pags) - 1} más</div>' if len(pags) > 1 else ""),
                          e(h.get("dispositivo", ""))])
        body.append(section("Todos los hallazgos", table(["ID", "Severidad", "Tipo", "Hallazgo", "Página", "Dispositivo"], filas)))

    # ---- Oportunidades
    ops = datos.get("oportunidades") or []
    if ops:
        filas_g = [(o["titulo"], round(o["ahorro_ms_max"] / 1000, 2), SERIES[0]) for o in ops if o.get("ahorro_ms_max")][:10]
        if filas_g:
            body.append(section("Oportunidades por ahorro de tiempo", bar_chart(filas_g, ancho_etiqueta=320), "segundos que se podrían ahorrar, en la página más afectada"))
        det = []
        for o in ops:
            items = "".join(f'<li class="mono">{e(it["url"][:140])}'
                            + (f' <span class="muted">· {kb(it["ahorro_bytes"])} de ahorro</span>' if it.get("ahorro_bytes") else "")
                            + (f' <span class="muted">· {it["ahorro_ms"] / 1000:.1f} s</span>' if it.get("ahorro_ms") else "") + "</li>"
                            for it in o.get("items") or [])
            ahorro = " · ".join(x for x in [f'hasta {o["ahorro_ms_max"] / 1000:.1f} s'.replace(".", ",") if o.get("ahorro_ms_max") else "",
                                            f'hasta {kb(o["ahorro_bytes_max"])}' if o.get("ahorro_bytes_max") else ""] if x)
            det.append(f'''<div class="hallazgo"><h3>{e(o["titulo"])} {_pastilla(ahorro or "mejora", SERIES[0], "↓")}</h3>
              <p class="muted">{e(len(o.get("paginas") or []))} página(s) · {e(", ".join(DISP.get(d, d) for d in o.get("dispositivos") or []))}{((" · affects " if idioma_actual() == "en" else " · afecta ") + e(", ".join(o["metricas"]))) if o.get("metricas") else ""}</p>
              <div class="lbl">Qué es y cómo se corrige</div><p>{e(o.get("descripcion"))}</p>
              {f'<div class="lbl">Recursos que lo causan</div><ul>{items}</ul>' if items else ""}
              {f'<p><a href="{e(o["mas_info"])}" target="_blank" rel="noopener" style="color:var(--ink)">Más información</a></p>' if o.get("mas_info") else ""}</div>''')
        body.append(section("Oportunidades de mejora", "".join(det), "auditorías de Lighthouse que fallan y estiman un ahorro"))

    # ---- Peso por tipo de recurso
    filas_p = []
    for x in ok:
        if x["dispositivo"] != disp_ppal:
            continue
        rec = x.get("recursos") or {}
        filas_p.append((corto(x["url"], base), [round((rec.get(t) or {}).get("bytes", 0) / 1024) for t in TIPOS]))
    if filas_p:
        body.append(section("Peso por tipo de recurso", stacked_bars(filas_p, [(t, SERIES[i]) for i, t in enumerate(TIPOS)]),
                            f"KB transferidos por página ({DISP[disp_ppal].lower()})"))

    # ---- LCP y terceros
    filas_l = [[f'<span class="mono">{e(corto(x["url"], base))}</span>', e(DISP[x["dispositivo"]]),
                f'<span class="mono" style="color:var(--ink)">{e(x["lcp"].get("selector"))}</span><div class="muted">{e(x["lcp"].get("etiqueta"))}</div>']
               for x in ok if x.get("lcp")]
    if filas_l:
        body.append(section("Elemento LCP", table(["Página", "Dispositivo", "Elemento que define el LCP"], filas_l),
                            "el contenido más grande que se pinta: optimizarlo baja el LCP"))
    terceros = {}
    for x in ok:
        for t in x.get("terceros") or []:
            a = terceros.setdefault(t["entidad"], {"bytes": 0, "bloqueo_ms": 0, "paginas": 0})
            a["bytes"] = max(a["bytes"], t["bytes"])
            a["bloqueo_ms"] = max(a["bloqueo_ms"], t["bloqueo_ms"])
            a["paginas"] += 1
    if terceros:
        filas_t = [[e(n), kb(v["bytes"]), f'{v["bloqueo_ms"]} ms', e(v["paginas"])] for n, v in sorted(terceros.items(), key=lambda kv: -kv[1]["bloqueo_ms"])]
        body.append(section("Código de terceros", table(["Proveedor", "Peso", "Bloqueo del hilo principal", "Mediciones"], filas_t)))

    # ---- Secuencia de carga
    filas_f = []
    for x in ok:
        if not x.get("secuencia"):
            continue
        nombre = corto(x["url"], base)
        figs = "".join(f'<figure>{miniatura(f["captura"], nombre + " a " + format(f["ms"] / 1000, ".1f") + " s")}'
                       f'<figcaption>{f["ms"] / 1000:.1f} s</figcaption></figure>' for f in x["secuencia"])
        filas_f.append(f'<div class="filmrow"><div class="t"><span class="mono">{e(corto(x["url"], base))}</span> · {e(DISP[x["dispositivo"]])}</div>'
                       f'<div class="film {e(x["dispositivo"])}">{figs}</div></div>')
    if filas_f:
        body.append(section("Secuencia de carga", "".join(filas_f), "cómo se ve la página mientras carga (clic para ampliar)"))

    # ---- Alcance
    um = cfg.get("umbrales") or {}
    filas_u = [[e(v.get("nombre")), e(v.get("titulo")), e(f'≤ {v["bueno"] / 1000:g} s' if v.get("unidad") == "ms" else f'≤ {v["bueno"]}'),
                e(f'> {v["malo"] / 1000:g} s' if v.get("unidad") == "ms" else f'> {v["malo"]}')] for v in um.values()]
    # Párrafos con datos intercalados: una versión por idioma.
    en = idioma_actual() == "en"
    fuerte = '<strong style="color:var(--ink)">{}</strong>'
    herr, url = e(datos.get("herramienta", "Lighthouse")), e(datos.get("url"))
    disp_txt = {"mobile": "mobile", "desktop": "desktop"}
    if en:
        alcance = (f'<p>{fuerte.format(herr)} on {len(paginas)} page(s) from <span class="mono">{url}</span>, on '
                   f'{e(" and ".join(disp_txt.get(d, d) for d in dispositivos))} (mobile: Moto G on slow 4G, Google’s standard), '
                   f'{e(cfg.get("repeticiones", 1))} run(s) per page (the median is used). Duration: {e(datos.get("duracion_s"))} s.</p>'
                   f'<p>{fuerte.format("Lab data:")} a simulated load under fixed conditions, useful to find and compare problems. '
                   'It does not replace real-user data (Chrome UX Report): real performance depends on each person’s device and network.</p>')
    else:
        alcance = (f'<p>{fuerte.format(herr)} sobre {len(paginas)} página(s) desde <span class="mono">{url}</span>, en '
                   f'{e(" y ".join(DISP[d].lower() for d in dispositivos))} (mobile: Moto G con 4G lenta, el estándar de Google), '
                   f'{e(cfg.get("repeticiones", 1))} repetición(es) por página (se toma la mediana). Duración: {e(datos.get("duracion_s"))} s.</p>'
                   f'<p>{fuerte.format("Datos de laboratorio:")} una carga simulada en condiciones fijas, útil para encontrar y comparar problemas. '
                   'No reemplaza los datos de usuarios reales (Chrome UX Report): el rendimiento real depende del dispositivo y la red de cada persona.</p>')
    body.append(section("Alcance y método", f'<div class="cardbody">{alcance}</div>'
                        + (table(["Métrica", "Nombre", "Bueno", "Malo"], filas_u) if filas_u else "")))

    if descartados:
        originales = {h.get("id"): h for h in datos.get("hallazgos") or []}
        filas = [[e(i), e((originales.get(i) or {}).get("titulo", "")), e(m)] for i, m in descartados.items()]
        body.append(section("Descartados", table(["ID", "Hallazgo", "Motivo"], filas)))
    body.append(falta_informacion(analisis.get("falta_informacion")))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))

    errores = [x for x in res if x.get("error")]
    if errores:
        body.append(section("Mediciones que fallaron", table(["Página", "Dispositivo", "Error"],
                                                              [[e(x["url"]), e(x["dispositivo"]), e(x["error"])] for x in errores])))

    fecha = (datos.get("fecha") or datetime.datetime.now().isoformat())[:16].replace("T", " ")
    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Historia", datos.get("historia")), ("Sitio", datos.get("host")), ("Fecha", fecha),
                      ("Herramienta", datos.get("herramienta"))])
    return page("Informe de rendimiento web", "Rendimiento web", meta_html, CSS_EXTRA + CSS_REND + "".join(body) + JS_EXTRA)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de rendimiento web a partir de rendimiento.json")
    ap.add_argument("rendimiento_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis", help="JSON con veredicto, resumen, notas, descartes y recomendaciones")
    a = ap.parse_args()
    if not a.salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    with open(a.rendimiento_json, encoding="utf-8") as f:
        datos = json.load(f)
    analisis = {}
    if a.analisis:
        with open(a.analisis, encoding="utf-8") as f:
            analisis = json.load(f)
        avisar_analisis(analisis, [h.get("id") for h in datos.get("hallazgos") or []])
    hist_html = _historial.seccion("rendimiento", Path(a.rendimiento_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Genera el Informe de pruebas exploratorias en HTML (dashboard, modo oscuro) a partir del
resultado del recorrido automático (exploracion.json, de `npm run explorar`) y, opcionalmente,
del análisis del agente explorador-web. `npm run explorar` ya lo genera solo al terminar; el
agente lo vuelve a generar con su análisis.

Uso:
    python scripts/generar_informe_exploratorio.py <exploracion.json> <salida.html>
           [--analisis analisis.json]

Qué muestra: veredicto, indicadores, gráficos (páginas con y sin problemas, links, hallazgos por
severidad y por tipo, tiempos de carga, responsive por resolución), todos los hallazgos con su
captura (clic para ampliar), la exploración manual, la matriz de responsive con miniaturas, los
videos del recorrido y de cada resolución, la galería de capturas, links rotos y no verificables,
y el detalle de cada página (métricas, errores de JavaScript y consola, recursos e imágenes que fallan).

Los hallazgos AUTOMÁTICOS salen del exploracion.json (no se escriben a mano). El análisis
(opcional) aporta:
{
  "veredicto": "Sitio usable con observaciones",        // conclusión
  "veredicto_tono": "warn",                             // opcional: ok | warn | bad
  "resumen": "Resumen para alguien no técnico...",
  "mision": "Explorar la navegación y los formularios públicos",   // charter de la sesión
  "duracion_min": 30,                                   // timebox de la exploración manual
  "notas": {"H-03": "El 502 es intermitente: volvió a responder 200 a los 5 minutos"},
  "descartados": [{"id": "H-05", "motivo": "El link lo bloquea el sitio externo a los robots"}],
  "severidades": {"H-02": "Alta"},                      // ajuste de severidad (con el motivo en notas)
  "exploratorios": [{"id": "EX-01", "titulo": "...", "severidad": "Media", "pagina": "https://...",
                     "pasos": ["..."], "esperado": "...", "obtenido": "...", "correccion": "...", "evidencia": "capturas/manual/ex-01.png"}],
  "areas_exploradas": ["Menú principal", "Formulario de contacto (sin enviar)"],
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],   // "descripcion" vale como alias de que_falta
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}

Severidad: Crítica | Alta | Media | Baja. Las rutas de evidencia y videos son relativas al HTML
(se guarda en la misma carpeta que exploracion.json). El HTML es autocontenido (sin internet).
"""
import argparse
import datetime
import json
from pathlib import Path
import sys

import _historial
from _i18n import escribir_bilingue, idioma_actual, localizar  # noqa: E402,F401
from _estilos_reporte import miniatura  # noqa: F401 (la importan los otros informes)
from _estilos_reporte import (falta_informacion, avisar_analisis, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, stacked_bars,
                              donut_panel, two_col, nivel_badge, _pastilla, CRITICO, SERIO, AVISO, NEUTRO, OK, SERIES)

SEVERIDADES = [("Crítica", CRITICO), ("Alta", SERIO), ("Media", AVISO), ("Baja", NEUTRO)]
ORDEN = {s: i for i, (s, _) in enumerate(SEVERIDADES)}
CATEGORIAS = [("Página con error", CRITICO), ("Link roto", SERIO), ("Imagen rota", SERIO), ("Error de JavaScript", SERIO),
              ("Error de consola", AVISO), ("Recurso que falla", AVISO), ("Responsive", SERIES[1]), ("Rendimiento", SERIES[7]),
              ("Accesibilidad", NEUTRO), ("Exploración manual", SERIES[5])]

CSS_EXTRA = """
<style>
.mono{font-family:var(--mono);font-size:12.5px;word-break:break-all}
.hallazgo{padding:20px 24px;border-top:1px solid var(--border-soft)}
.hallazgo:first-child{border-top:0}
.hallazgo h3{font-size:16px;color:var(--ink);margin-bottom:6px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.hallazgo .lbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin:12px 0 4px}
.hallazgo p,.hallazgo li{color:var(--body)}
.hallazgo ol,.hallazgo ul{margin-left:18px}
.galeria{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:16px;padding:20px 24px}
.galeria figure{margin:0;background:var(--bg);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.galeria img{display:block;width:100%;height:230px;object-fit:cover;object-position:top}
.galeria figcaption{padding:8px 10px;font-size:12px;color:var(--muted);word-break:break-all}
.videos{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;padding:20px 24px}
.videos figure{margin:0;background:var(--bg);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.videos video{display:block;width:100%;max-height:420px;background:#000}
.videos figcaption{padding:8px 10px;font-size:12.5px;color:var(--body)}
.matriz td{text-align:center;vertical-align:top}
.matriz td:first-child{text-align:left}
.matriz .thumb{margin-top:6px}
details.pag{border-top:1px solid var(--border-soft)}
details.pag:first-child{border-top:0}
details.pag summary{cursor:pointer;padding:14px 24px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;color:var(--ink);list-style:none}
details.pag summary::-webkit-details-marker{display:none}
details.pag summary:before{content:"▸";color:var(--muted)}
details.pag[open] summary:before{content:"▾"}
details.pag .cuerpo{padding:0 24px 20px 24px;display:grid;grid-template-columns:240px 1fr;gap:20px}
details.pag .cuerpo .thumb{width:240px;height:180px}
details.pag .cuerpo ul{margin-left:18px;color:var(--body)}
details.pag .cuerpo li{word-break:break-all;margin:2px 0}
.metr{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:10px;color:var(--body);font-size:13px}
.metr b{color:var(--ink)}
@media (max-width:720px){details.pag .cuerpo{grid-template-columns:1fr}}
</style>
"""

# Lightbox: las miniaturas (a.lb) se amplían en la misma página; Esc o clic cierran.
JS_EXTRA = ""  # el visor de evidencia ahora es común (scripts/_estilos_reporte.py)


def pill(ok, texto_ok, texto_mal, tono_mal=CRITICO):
    return _pastilla(texto_ok, OK, "✓") if ok else _pastilla(texto_mal, tono_mal, "✕")


def corto(url, base):
    """La URL sin el origen del sitio, para que las tablas no se desborden."""
    if base and url and url.startswith(base):
        return url[len(base):] or "/"
    return url or ""


def origen(url):
    partes = (url or "").split("/")
    return "/".join(partes[:3]) if len(partes) >= 3 else ""


def seg(ms):
    return f"{(ms or 0) / 1000:.1f} s"


def tono_auto(hallazgos):
    sev = {h["severidad"] for h in hallazgos}
    if "Crítica" in sev:
        return "bad", "Hay problemas críticos: páginas que no abren o errores graves"
    if "Alta" in sev:
        return "warn", "Hay problemas importantes que conviene corregir antes de salir"
    if hallazgos:
        return "warn", "Sin problemas graves; quedan observaciones menores"
    return "ok", "No se encontraron problemas en el recorrido"


def problemas_pagina(p):
    return (len(p.get("errores_js") or []) + len(p.get("errores_consola") or []) + len(p.get("recursos_fallidos") or [])
            + len(p.get("imagenes_rotas") or []) + (1 if p.get("error") or (p.get("status") or 0) >= 400 else 0))


def build_html(datos, analisis, hist_html=""):
    descartados = {str(d.get("id")): d.get("motivo", "") for d in analisis.get("descartados") or []}
    notas = analisis.get("notas") or {}
    ajustes = analisis.get("severidades") or {}
    base = origen(datos.get("url"))
    cfg = datos.get("config") or {}
    r = datos.get("resumen") or {}
    pags = datos.get("paginas") or []
    links = datos.get("links") or []
    resp = datos.get("responsive") or []
    videos = datos.get("videos") or []

    automaticos = []
    for h in datos.get("hallazgos") or []:
        if h.get("id") in descartados:
            continue
        h = dict(h)
        if ajustes.get(h.get("id")) in ORDEN:
            h["severidad"] = ajustes[h["id"]]
        automaticos.append(h)
    exploratorios = [dict(x, categoria="Exploración manual") for x in analisis.get("exploratorios") or []]
    todos = sorted(automaticos + exploratorios, key=lambda h: ORDEN.get(h.get("severidad"), 9))
    cuenta = lambda cat: sum(1 for h in todos if h.get("categoria") == cat)
    por_sev = {s: sum(1 for h in todos if h.get("severidad") == s) for s, _ in SEVERIDADES}

    body = []
    tono, texto = tono_auto(todos)
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))

    # ---- Indicadores
    errores = cuenta("Error de JavaScript") + cuenta("Error de consola")
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Hallazgos", len(todos), "bad" if por_sev["Crítica"] or por_sev["Alta"] else ("warn" if todos else "ok"),
         f'{por_sev["Crítica"]} críticos · {por_sev["Alta"]} altos · {por_sev["Media"]} medios · {por_sev["Baja"]} bajos'),
        ("Páginas recorridas", r.get("paginas", len(pags)), "",
         f'{r["paginas_sin_recorrer"]} sin recorrer' if r.get("paginas_sin_recorrer") else "todas las encontradas"),
        ("Links rotos", cuenta("Link roto"), "bad" if cuenta("Link roto") else "ok",
         f'de {r.get("links", len(links))} · {r.get("links_no_verificables", 0)} no verificables'),
        ("Imágenes rotas", cuenta("Imagen rota"), "bad" if cuenta("Imagen rota") else "ok", f'de {r.get("imagenes", 0)} imágenes'),
        ("Errores JS y consola", errores, "bad" if cuenta("Error de JavaScript") else ("warn" if errores else "ok")),
        ("Recursos que fallan", cuenta("Recurso que falla"), "warn" if cuenta("Recurso que falla") else "ok"),
        ("Responsive", cuenta("Responsive"), "warn" if cuenta("Responsive") else "ok", f'{len(cfg.get("resoluciones") or [])} resoluciones'),
        ("Carga promedio", seg(r.get("carga_promedio_ms")), "warn" if cuenta("Rendimiento") else "",
         f'máx. {seg(r.get("carga_max_ms"))} · p90 {seg(r.get("carga_p90_ms"))}'),
    ] + ([("Exploración manual", len(exploratorios), "warn" if exploratorios else "")] if exploratorios or analisis else [])) + "</div>")

    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    # ---- Panorama: páginas y links
    sanas = sum(1 for p in pags if not problemas_pagina(p))
    pct_pag = round(sanas / len(pags) * 100) if pags else 0
    seg_pag = [(sanas, OK, "Sin errores"), (len(pags) - sanas, CRITICO, "Con errores")]
    ok_l = sum(1 for l in links if l.get("resultado") == "ok")
    rot_l = sum(1 for l in links if l.get("resultado") == "roto")
    nov_l = sum(1 for l in links if l.get("resultado") == "no_verificable")
    pct_l = round(ok_l / len(links) * 100) if links else 0
    seg_l = [(ok_l, OK, "OK"), (rot_l, CRITICO, "Rotos"), (nov_l, NEUTRO, "No verificables")]
    body.append(two_col(section("Páginas", donut_panel(seg_pag, pct_pag, "páginas sanas"), "sin errores de JS, consola, recursos ni imágenes"),
                        section("Links", donut_panel(seg_l, pct_l, "links ok"), "internos y externos")))

    if todos:
        cats = sorted([(c, cuenta(c), SERIES[0]) for c, _ in CATEGORIAS if cuenta(c)], key=lambda x: -x[1])
        body.append(two_col(section("Hallazgos por severidad", bar_chart([(s, por_sev[s], col) for s, col in SEVERIDADES])),
                            section("Hallazgos por tipo", bar_chart(cats, ancho_etiqueta=150))))

    # ---- Alcance
    # Párrafos con datos intercalados: una versión por idioma (el diccionario traduce frases enteras, no estas).
    en = idioma_actual() == "en"
    fuerte = '<strong style="color:var(--ink)">{}</strong>'
    mision = (f'<p>{fuerte.format("Mission:" if en else "Misión:")} {e(analisis["mision"])}</p>' if analisis.get("mision") else "")
    if analisis.get("duracion_min"):
        timebox = (f' · {e(analisis["duracion_min"])} min of manual exploration' if en
                   else f' · exploración manual de {e(analisis["duracion_min"])} min')
    else:
        timebox = ""
    if r.get("paginas_sin_recorrer"):
        sin_recorrer = (f'<p class="muted">{r["paginas_sin_recorrer"]} page(s) of the site were not visited because of the configured '
                        f'limit (raise --max-paginas or --profundidad).</p>' if en else
                        f'<p class="muted">Quedaron {r["paginas_sin_recorrer"]} página(s) del sitio sin recorrer por el límite '
                        f'configurado (subí --max-paginas o --profundidad).</p>')
    else:
        sin_recorrer = ""
    areas = (f'<p>{fuerte.format("Areas explored by hand:" if en else "Áreas exploradas a mano:")} '
             + e(", ".join(analisis["areas_exploradas"])) + "</p>" if analisis.get("areas_exploradas") else "")
    resoluciones = e(", ".join(cfg.get("resoluciones") or []))
    if en:
        recorrido = (f'<p>{fuerte.format("Automated crawl")} with Playwright from <span class="mono">{e(datos.get("url"))}</span>: '
                     f'up to {e(cfg.get("max_paginas"))} pages of the same site, {e(cfg.get("profundidad"))} levels deep, '
                     f'{"internal and external" if cfg.get("externos", True) else "internal"} links; responsive at {resoluciones} '
                     f'({e(cfg.get("responsive"))} page(s)); slow page from {seg(cfg.get("lenta_ms", 3000))}{timebox}. '
                     f'Crawl duration: {e(datos.get("duracion_s"))} s.</p>'
                     '<p>Only GET navigation: no forms were filled in or submitted during the automated crawl and no log-out links were followed. '
                     'In the screenshots, elements with problems (broken images, elements that overflow the screen, small touch targets) are marked in red.</p>')
    else:
        recorrido = (f'<p>{fuerte.format("Recorrido automático")} con Playwright desde <span class="mono">{e(datos.get("url"))}</span>: '
                     f'hasta {e(cfg.get("max_paginas"))} páginas del mismo sitio, {e(cfg.get("profundidad"))} niveles de profundidad, links '
                     f'{"internos y externos" if cfg.get("externos", True) else "internos"}; responsive en {resoluciones} '
                     f'({e(cfg.get("responsive"))} página(s)); página lenta desde {seg(cfg.get("lenta_ms", 3000))}{timebox}. '
                     f'Duración del recorrido: {e(datos.get("duracion_s"))} s.</p>'
                     '<p>Solo se navegó con GET: no se completaron ni enviaron formularios en el recorrido automático y no se siguieron links de cierre de sesión. '
                     'En las capturas, los elementos con problemas (imágenes rotas, elementos que se salen de la pantalla, objetivos táctiles chicos) están marcados en rojo.</p>')
    body.append(section("Alcance y método", f'<div class="cardbody">{mision}{recorrido}{areas}{sin_recorrer}</div>'))

    # ---- Hallazgos
    if todos:
        filas = []
        for h in todos:
            res = h.get("resoluciones") or ([h["resolucion"]] if h.get("resolucion") else [])
            nota = f'<div class="muted" style="margin-top:4px">{e(notas[h["id"]])}</div>' if h.get("id") in notas else ""
            filas.append([f'<span class="id">{e(h.get("id"))}</span>', nivel_badge(h.get("severidad")), e(h.get("categoria")),
                          f'<strong style="color:var(--ink)">{e(h.get("titulo"))}</strong>'
                          f'<div class="mono muted">{e(h.get("detalle") or h.get("obtenido") or "")}</div>{nota}',
                          f'<span class="mono">{e(corto(h.get("pagina"), base))}</span>'
                          + (f'<div class="muted" title="{e(chr(10).join(corto(x, base) for x in h["paginas"]))}">y {len(h["paginas"]) - 1} página(s) más</div>'
                             if len(h.get("paginas") or []) > 1 else "")
                          + (f'<div class="muted">{e(", ".join(res))}</div>' if res else ""),
                          miniatura(h.get("evidencia"), f'{h.get("id")} · {h.get("titulo")}')])
        body.append(section("Todos los hallazgos", table(["ID", "Severidad", "Tipo", "Hallazgo", "Página", "Evidencia"], filas),
                            "clic en la captura para ampliarla"))
    else:
        body.append(section("Hallazgos", '<div class="cardbody"><p>No se encontraron problemas en las páginas recorridas.</p></div>'))

    if exploratorios:
        det = []
        for x in exploratorios:
            pasos = "".join(f"<li>{e(p)}</li>" for p in x.get("pasos") or [])
            det.append(f'''<div class="hallazgo"><h3>{e(x.get("id"))} · {e(x.get("titulo"))} {nivel_badge(x.get("severidad"))}</h3>
              <div class="mono muted">{e(x.get("pagina"))}</div>
              {f'<div class="lbl">Pasos</div><ol>{pasos}</ol>' if pasos else ""}
              {f'<div class="lbl">Resultado esperado</div><p>{e(x["esperado"])}</p>' if x.get("esperado") else ""}
              {f'<div class="lbl">Resultado obtenido</div><p>{e(x["obtenido"])}</p>' if x.get("obtenido") else ""}
              {f'<div class="lbl">Cómo corregirlo</div><p>{e(x["correccion"])}</p>' if x.get("correccion") else ""}
              {f'<div class="lbl">Evidencia</div>{miniatura(x["evidencia"], x.get("titulo", ""))}' if x.get("evidencia") else ""}</div>''')
        body.append(section("Hallazgos de la exploración manual", "".join(det)))

    # ---- Rendimiento
    con_tiempo = sorted([p for p in pags if not p.get("error") and p.get("tiempo_ms")], key=lambda p: -p["tiempo_ms"])
    if con_tiempo:
        lenta = cfg.get("lenta_ms") or 3000
        color = lambda ms: SERIO if ms >= lenta * 2 else AVISO if ms >= lenta else OK
        filas = [(corto(p["url"], base), round(p["tiempo_ms"] / 1000, 2), color(p["tiempo_ms"])) for p in con_tiempo[:20]]
        body.append(section("Tiempo de carga por página", bar_chart(filas, ancho_etiqueta=240),
                            f"segundos · verde < {seg(lenta)} · amarillo lenta · naranja muy lenta"))

    # ---- Responsive
    if resp:
        resoluciones = list(dict.fromkeys(f["resolucion"] for f in resp))
        nombres = {f["resolucion"]: f.get("nombre", "") for f in resp}
        filas_sb = [(f'{nombres[x]} {x}', [sum(1 for f in resp if f["resolucion"] == x and f.get(k)) for k in
                                           ("desborde_horizontal", "texto_chico", "objetivos_tactiles_chicos")]) for x in resoluciones]
        series = [("Scroll horizontal", CRITICO), ("Texto < 12 px", AVISO), ("Táctiles < 24 px", SERIES[1])]
        if any(sum(v) for _, v in filas_sb):
            body.append(section("Problemas de responsive por resolución", stacked_bars(filas_sb, series), "páginas afectadas"))
        paginas_r = list(dict.fromkeys(f["url"] for f in resp))
        idx = {(f["url"], f["resolucion"]): f for f in resp}
        filas = []
        for p in paginas_r:
            celdas = [f'<span class="mono">{e(corto(p, base))}</span>']
            for res in resoluciones:
                f = idx.get((p, res)) or {}
                if f.get("error"):
                    celdas.append(_pastilla("No se pudo", NEUTRO, "⊘") + f'<div class="muted" style="font-size:11px">{e(f["error"][:80])}</div>')
                    continue
                avisos = [t for k, t in (("texto_chico", "texto chico"), ("objetivos_tactiles_chicos", "táctiles chicos")) if f.get(k)]
                estado = (_pastilla("Desborda", CRITICO, "✕") if f.get("desborde_horizontal")
                          else _pastilla("Con avisos", AVISO, "!") if avisos else _pastilla("OK", OK, "✓"))
                det = f'<div class="muted" style="font-size:11px">{e(", ".join(avisos))}</div>' if avisos else ""
                celdas.append(estado + det + "<div>" + miniatura(f.get("captura"), f'{corto(p, base)} · {res}', "s") + "</div>")
            filas.append(celdas)
        tabla = table(["Página"] + [f"{nombres[x]} {x}" for x in resoluciones], filas).replace("<table>", '<table class="matriz">', 1)
        body.append(section("Responsive: página por resolución", tabla,
                            "scroll horizontal, texto < 12 px y objetivos táctiles < 24 px (WCAG 2.5.8)"))

    # ---- Videos
    if videos:
        figs = "".join(f'<figure><video controls preload="metadata" src="{e(v["archivo"])}#t=1"></video>'
                       f'<figcaption>{e(v.get("titulo", v["archivo"]))} · <a href="{e(v["archivo"])}" download style="color:var(--ink)">descargar</a></figcaption></figure>'
                       for v in videos)
        body.append(section("Videos", f'<div class="videos">{figs}</div>', "el recorrido completo y cada resolución"))

    # ---- Galerías
    caps = [p for p in pags if p.get("captura")]
    if caps:
        figs = "".join(f'<figure>{miniatura(p["captura"], corto(p["url"], base)).replace("thumb", "", 1)}'
                       f'<figcaption>{e(corto(p["url"], base))}{" · " + str(problemas_pagina(p)) + " error(es)" if problemas_pagina(p) else ""}</figcaption></figure>'
                       for p in caps)
        body.append(section("Capturas de las páginas", f'<div class="galeria">{figs}</div>', "desktop · página completa"))
    caps_r = [f for f in resp if f.get("captura")]
    if caps_r:
        figs = "".join(f'<figure>{miniatura(f["captura"], corto(f["url"], base) + " · " + f["resolucion"]).replace("thumb", "", 1)}'
                       f'<figcaption>{e(corto(f["url"], base))} · {e(f.get("nombre", ""))} {e(f["resolucion"])}'
                       f'{" · desborda" if f.get("desborde_horizontal") else ""}</figcaption></figure>' for f in caps_r)
        body.append(section("Capturas de responsive", f'<div class="galeria">{figs}</div>', "cada página en cada resolución"))

    # ---- Links
    rotos = [l for l in links if l.get("resultado") == "roto"]
    dudosos = [l for l in links if l.get("resultado") == "no_verificable"]
    if rotos:
        filas = [[f'<span class="mono">{e(l["url"])}</span>' + (f'<div class="muted">"{e(l["texto"])}"</div>' if l.get("texto") else ""),
                  e("Interno" if l.get("interno") else "Externo"), e(l.get("status") or l.get("error") or "—"),
                  "<br>".join(f'<span class="mono">{e(corto(o, base))}</span>' for o in l.get("origenes", [])[:5])
                  + (f'<div class="muted">… y {len(l["origenes"]) - 5} más</div>' if len(l.get("origenes", [])) > 5 else "")]
                 for l in rotos]
        body.append(section("Links rotos", table(["Link", "Tipo", "Respuesta", "Aparece en"], filas)))
    if dudosos:
        filas = [[f'<span class="mono">{e(l["url"])}</span>', e(l.get("status") or "—"), e(l.get("error") or "Pide login o bloquea a los robots")]
                 for l in dudosos]
        body.append(section("Links que no se pudieron verificar", table(["Link", "Respuesta", "Motivo"], filas),
                            "no son necesariamente errores: revisalos a mano"))

    # ---- Detalle por página
    if pags:
        filas = []
        for p in pags:
            m = p.get("metricas") or {}
            filas.append([f'<span class="mono">{e(corto(p["url"], base))}</span>' + (f'<div class="muted">{e(p.get("titulo"))}</div>' if p.get("titulo") else ""),
                          pill(not p.get("error") and 0 < (p.get("status") or 0) < 400, str(p.get("status")), str(p.get("error") and "error" or p.get("status"))),
                          e(seg(p.get("tiempo_ms"))), e(f'{m["ttfb_ms"]} ms' if m.get("ttfb_ms") is not None else "—"),
                          e(m.get("requests", "—")), e(f'{m["peso_kb"]} KB' if m.get("peso_kb") is not None else "—"),
                          e(p.get("links", 0)), e(p.get("imagenes", 0)),
                          pill(not problemas_pagina(p), "0", str(problemas_pagina(p)))])
        body.append(section("Páginas recorridas", table(["Página", "Estado", "Carga", "Primer byte", "Requests", "Peso aprox.",
                                                         "Links", "Imágenes", "Errores"], filas)))
        bloques = []
        for p in pags:
            m = p.get("metricas") or {}
            listas = []
            for titulo, items in (("Errores de JavaScript", p.get("errores_js")), ("Errores de consola", p.get("errores_consola")),
                                  ("Recursos que fallan", [f'{x.get("tipo") or "recurso"} {x.get("status") or x.get("error") or ""} · {x.get("url")}' for x in p.get("recursos_fallidos") or []]),
                                  ("Imágenes rotas", [f'{x.get("src")}' + (f' (HTTP {x["status"]})' if x.get("status") else "") for x in p.get("imagenes_rotas") or []]),
                                  ("Imágenes sin alt", p.get("ejemplos_sin_alt"))):
                if items:
                    listas.append(f'<div class="lbl" style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin:10px 0 4px">{e(titulo)} ({len(items)})</div>'
                                  "<ul>" + "".join(f'<li class="mono">{e(i)}</li>' for i in items[:15]) + "</ul>")
            metr = (f'<div class="metr"><span>Estado <b>{e(p.get("status") or p.get("error"))}</b></span><span>Carga <b>{seg(p.get("tiempo_ms"))}</b></span>'
                    + (f'<span>Primer byte <b>{m["ttfb_ms"]} ms</b></span><span>DOM listo <b>{m.get("dom_ms")} ms</b></span>'
                       f'<span>Requests <b>{m.get("requests")}</b></span><span>Peso aprox. <b>{m.get("peso_kb")} KB</b></span>' if m.get("ttfb_ms") is not None else "")
                    + (f'<span>Redirige a <b class="mono">{e(p["redirige_a"])}</b></span>' if p.get("redirige_a") else "") + "</div>")
            n = problemas_pagina(p)
            bloques.append(f'''<details class="pag"{" open" if n else ""}><summary><span class="mono">{e(corto(p["url"], base))}</span>
                {pill(not n, "Sin errores", f"{n} error(es)")}<span class="muted">{e(p.get("titulo") or "")}</span></summary>
                <div class="cuerpo"><div>{miniatura(p.get("captura"), corto(p["url"], base))}</div>
                <div>{metr}{"".join(listas) or '<p class="muted">Sin errores de JavaScript, consola, recursos ni imágenes.</p>'}</div></div></details>''')
        body.append(section("Detalle por página", "".join(bloques), "las páginas con errores están abiertas"))

    # ---- Cierre
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

    fecha = (datos.get("fecha") or datetime.datetime.now().isoformat())[:16].replace("T", " ")
    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Historia", datos.get("historia")), ("Sitio", datos.get("host")), ("Fecha", fecha),
                      ("Herramienta", "Playwright · recorrido + exploración")])
    return page("Informe de pruebas exploratorias", "Pruebas exploratorias", meta_html, CSS_EXTRA + "".join(body) + JS_EXTRA)


def main():
    for flujo in (sys.stdout, sys.stderr):  # acentos bien en la consola de Windows
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de pruebas exploratorias a partir de exploracion.json")
    ap.add_argument("exploracion_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis", help="JSON con veredicto, resumen, hallazgos manuales, descartes y recomendaciones")
    a = ap.parse_args()
    if not a.salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    with open(a.exploracion_json, encoding="utf-8") as f:
        datos = json.load(f)
    analisis = {}
    if a.analisis:
        with open(a.analisis, encoding="utf-8") as f:
            analisis = json.load(f)
        avisar_analisis(analisis, [h.get("id") for h in datos.get("hallazgos") or []] + [x.get("id") for x in analisis.get("exploratorios") or []])
    hist_html = _historial.seccion("exploratorio", Path(a.exploracion_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

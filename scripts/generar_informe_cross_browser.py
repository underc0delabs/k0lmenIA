#!/usr/bin/env python3
"""
Genera el Informe cross-browser en HTML (dashboard, modo oscuro) a partir de cross-browser.json
(npm run cross-browser) y, opcionalmente, del análisis del agente cross-browser.

Uso:
    python scripts/generar_informe_cross_browser.py <cross-browser.json> <salida.html> [--analisis analisis.json]

Qué muestra:
  - modo suite: escenarios que pasan en todos los navegadores, que fallan solo en algunos (lo que
    busca la prueba) y que fallan en todos; la matriz escenario × navegador con la captura de cada
    uno, aprobados y fallidos por navegador, y el detalle de cada diferencia con el error.
  - modo páginas: cada pantalla (página × resolución) en cada navegador, lado a lado y con el
    comparador deslizable contra el navegador base, el porcentaje que se ve distinto y los hallazgos
    exclusivos de un navegador (errores de JavaScript y de consola, recursos que fallan, desborde,
    elementos que faltan o se corren, estilos distintos).
  - en los dos: los navegadores y sus versiones (o cómo instalarlos), recomendaciones y próximos pasos.

El análisis (opcional) aporta:
{
  "veredicto": "El checkout no funciona en Safari", "veredicto_tono": "bad",
  "resumen": "Resumen para alguien no técnico...",
  "hallazgos": {"X-01": {"severidad": "Crítica", "causa": "Safari no soporta ...", "accion": "Agregar polyfill",
                         "descartado": false}},
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
"""
import argparse
import json
from pathlib import Path
import sys
from collections import Counter

import _historial
from _i18n import escribir_bilingue, idioma_actual, localizar  # noqa: E402,F401
from _estilos_reporte import (e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, donut_panel, grouped_columns,
                              two_col, nivel_badge, estado_pill, _pastilla, miniatura, NIVEL_COLOR, CRITICO, AVISO, NEUTRO, OK, SERIO, SERIES)
from generar_informe_exploratorio import CSS_EXTRA
from generar_informe_pixel_perfect import CSS_PP, JS_PP, deltas, antes_despues

COLOR_NAV = {"chromium": SERIES[2], "firefox": SERIES[3], "webkit": SERIES[4]}
CORTO = {"chromium": "Chromium", "firefox": "Firefox", "webkit": "WebKit"}
CLASE = {"Pasa en todos": (OK, "✓"), "Diferencia entre navegadores": (CRITICO, "✕"), "Falla en todos": (SERIO, "!"),
         "Inestable": (AVISO, "~"), "Sin resultado completo": (NEUTRO, "–")}
ESTADO_PAG = {"OK": (OK, "✓"), "Con problemas": (CRITICO, "✕"), "Diferencias menores": (AVISO, "!"), "Error": (NEUTRO, "⊘")}
SEV = ["Crítica", "Alta", "Media", "Baja"]

CSS_CB = """
<style>
.nav-pill{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:650;padding:4px 11px;border-radius:999px;
  background:var(--tile);border:1px solid var(--border);color:var(--ink);white-space:nowrap}
.nav-pill i{width:9px;height:9px;border-radius:50%}
.lado{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;padding:16px 24px}
.lado figure{margin:0;background:var(--bg);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.lado .thumb{display:grid;width:100%;height:260px;border:0;border-radius:0;border-bottom:1px solid var(--border)}
.lado figcaption{padding:9px 12px;font-size:12.5px;color:var(--body);display:flex;justify-content:space-between;gap:8px;align-items:center}
.err{background:#120F0B;border:1px solid var(--border);border-radius:10px;padding:12px 14px;white-space:pre-wrap;word-break:break-word;
  font-family:var(--mono);font-size:12px;color:#FFB8B0;max-height:260px;overflow:auto}
.celda{display:flex;flex-direction:column;align-items:center;gap:6px}
.celda .pct{font-family:var(--mono);font-size:12px;color:var(--muted)}
.instalar{font-family:var(--mono);font-size:12px;color:var(--ink);background:var(--tile);border:1px solid var(--border);
  border-radius:8px;padding:4px 8px;display:inline-block}
.descartado{opacity:.55}
</style>
"""


def nav_pill(n, texto=None):
    nav = n.split("-")[0]
    return f'<span class="nav-pill"><i style="background:{COLOR_NAV.get(nav, NEUTRO)}"></i>{e(texto or CORTO.get(nav, n))}</span>'


def combo_txt(c):
    nav, _, res = c.partition("-")
    return f'{CORTO.get(nav, nav)} {res}'


def pill_de(mapa, estado):
    color, ic = mapa.get(estado, (NEUTRO, "●"))
    return _pastilla(estado or "—", color, ic)


def corto_url(u):
    ruta = (u or "").split("://", 1)[-1].split("/", 1)
    return ("/" + ruta[1]) if len(ruta) > 1 and ruta[1] else "/"


def comparador(base, otra, dif, etq_base, etq_otra, ancho):
    maxw = f"max-width:{ancho}px" if ancho < 1024 else ""
    return f'''<div class="comp-wrap">
  <div class="comp-bar"><span class="lado"><i style="background:{SERIES[2]}"></i>{e(etq_base)}</span>
    <input type="range" min="0" max="100" value="50" aria-label="Deslizar entre {e(etq_base)} y {e(etq_otra)}">
    <span class="lado"><i style="background:{SERIES[3]}"></i>{e(etq_otra)}</span>
    <button type="button" data-modo="desl" class="on">Deslizar</button><button type="button" data-modo="dif">Ver diferencias</button></div>
  <div class="comp" style="{maxw}"><div class="lienzo">
    <img class="base" src="{e(otra)}" data-act="{e(otra)}" data-dif="{e(dif)}" alt="{e(etq_otra)}">
    <img class="sobre" src="{e(base)}" alt="{e(etq_base)}"><div class="linea"></div></div></div></div>'''


def tabla_navegadores(datos):
    r = datos.get("resumen") or {}
    filas = []
    for n in datos.get("navegadores") or []:
        if n.get("ok"):
            estado = _pastilla("Disponible", OK, "✓")
            extra = ""
            if datos.get("modo") == "suite":
                cs = [c for c in datos.get("corridas") or [] if c["navegador"] == n["nombre"]]
                extra = " · ".join(f'{c["resolucion"]}: {c["aprobados"]}/{c["total"]} aprobados' for c in cs)
            else:
                extra = f'{(r.get("por_navegador") or {}).get(n["nombre"], 0)} hallazgo(s) exclusivos'
        else:
            estado = _pastilla(n.get("error") or "No disponible", NEUTRO, "⊘")
            extra = f'<span class="instalar">{e(n.get("instalar"))}</span>' if n.get("instalar") else e(n.get("error"))
        base = " · base de comparación" if datos.get("base") == n["nombre"] and datos.get("modo") == "paginas" else ""
        filas.append([nav_pill(n["nombre"], n.get("titulo")), e(n.get("version") or "—"), estado, extra + e(base)])
    return table(["Navegador", "Versión", "Estado", "Resultado"], filas)


def detalle_hallazgo(h, a):
    evid = ""
    if h.get("evidencias"):
        evid = '<div class="lado" style="padding:8px 0">' + "".join(
            f'<figure>{miniatura(x["captura"], combo_txt(x["combo"]))}<figcaption>{nav_pill(x["combo"], combo_txt(x["combo"]))}'
            f'{estado_pill(x["estado"])}</figcaption></figure>' for x in h["evidencias"]) + "</div>"
    pantallas = h.get("pantallas") or []
    lista = ""
    if len(pantallas) > 1:
        lista = '<div class="lbl">Dónde aparece</div><ul>' + "".join(
            f'<li><span class="mono">{e(corto_url(p["url"]))}</span> · {e(p["resolucion"])}</li>' for p in pantallas[:12]) + "</ul>"
    ad = antes_despues({"id": h["id"], "antes": h.get("base_captura"), "despues": h.get("nav_captura")}) if (h.get("base_captura") or h.get("nav_captura")) else ""
    ad = ad.replace(">Referencia<", ">Navegador base<").replace(">Actual<", f'>{e(CORTO.get(h.get("navegador"), "Este navegador"))}<')
    if not ad and not evid and h.get("captura"):
        evid = f'<div style="margin-top:8px">{miniatura(h["captura"], h["titulo"])}</div>'
    err = h.get("error") or (h["detalle"] if h["tipo"] in ("Error de JavaScript", "Error de consola") else "")
    return f'''<div class="hallazgo{' descartado' if a.get("descartado") else ''}" id="{e(h["id"])}"><h3>{e(h["id"])} · {e(h["titulo"])} {nivel_badge(h["severidad"])}
      {nav_pill(h["navegador"]) if h.get("navegador") else "".join(nav_pill(f) for f in h.get("fallan") or [])}{' <span class="pill">Descartado</span>' if a.get("descartado") else ''}</h3>
      <p>{e(h["detalle"]) if not err or err != h["detalle"] else ""}</p>{deltas(h)}
      {f'<div class="lbl">Error</div><div class="err">{e(chr(10).join(err.splitlines()[:20]))}</div>' if err else ''}
      {f'<div class="lbl">Causa</div><p>{e(a["causa"])}</p>' if a.get("causa") else ''}
      {f'<div class="lbl">Qué hacer</div><p>{e(a["accion"])}</p>' if a.get("accion") else ''}
      {lista}{ad}{evid}</div>'''


def build_html(datos, analisis, hist_html=""):
    ajustes = analisis.get("hallazgos") or {}
    hallazgos = []
    for h in datos.get("hallazgos") or []:
        h = dict(h)
        a = ajustes.get(h["id"]) or {}
        if a.get("severidad") in SEV:
            h["severidad"] = a["severidad"]
        h["_a"] = a
        hallazgos.append(h)
    vivos = [h for h in hallazgos if not h["_a"].get("descartado")]
    r = datos.get("resumen") or {}
    modo = datos.get("modo")
    navs = [n for n in datos.get("navegadores") or [] if n.get("ok")]
    faltan = r.get("no_instalados") or []
    body = []

    if modo == "suite":
        dif, todos, n = r.get("diferencias", 0), r.get("fallan_en_todos", 0), r.get("escenarios", 0)
        if not n:
            tono, texto = "warn", "No hubo resultados: revisá el error de cada corrida"
        elif dif:
            tono, texto = "bad", f"{dif} escenario(s) fallan solo en algunos navegadores"
        elif todos:
            tono, texto = "warn", f"Sin diferencias entre navegadores; {todos} escenario(s) fallan en todos (no es un tema de navegador)"
        else:
            tono, texto = "ok", "Todos los escenarios pasan en todos los navegadores"
    else:
        cp = r.get("con_problemas", 0)
        if cp:
            tono, texto = "bad", f"{cp} pantalla(s) con problemas que aparecen solo en algún navegador"
        elif vivos:
            tono, texto = "warn", "Diferencias menores entre navegadores"
        else:
            tono, texto = "ok", "Las páginas se ven y funcionan igual en todos los navegadores"
    if faltan and tono == "ok":
        tono = "warn"
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))

    if modo == "suite":
        n = r.get("escenarios", 0)
        body.append('<div style="margin-top:20px">' + kpi_tiles([
            ("Navegadores", len(navs), "ok" if not faltan else "warn", f'{len(faltan)} sin instalar' if faltan else "todos disponibles", "navegador"),
            ("Escenarios", n, "", f'{len(datos.get("corridas") or [])} corrida(s) · {", ".join(datos.get("resoluciones") or [])}', "lista"),
            ("Pasan en todos", r.get("pasan_en_todos", 0), "ok" if n and r.get("pasan_en_todos") == n else "",
             f'{round(r.get("pasan_en_todos", 0) / n * 100) if n else 0} % de los escenarios', "ok", {"pct": r.get("pasan_en_todos", 0) / n * 100 if n else 0}),
            ("Diferencias", r.get("diferencias", 0), "bad" if r.get("diferencias") else "ok", "fallan solo en algunos navegadores", "bad"),
            ("Fallan en todos", r.get("fallan_en_todos", 0), "warn" if r.get("fallan_en_todos") else "ok", "bug o test roto (analista-fallos)", "warn"),
            ("Inestables", r.get("inestables", 0), "warn" if r.get("inestables") else "ok", "fallaron y pasaron al repetirlos: no son del navegador", "warn"),
            ("Sin resultado", r.get("incompletos", 0), "warn" if r.get("incompletos") else "", "no corrieron en algún navegador", "blk"),
        ]) + "</div>")
    else:
        pant = r.get("pantallas", 0)
        body.append('<div style="margin-top:20px">' + kpi_tiles([
            ("Navegadores", len(navs), "ok" if not faltan else "warn", f'{len(faltan)} sin instalar' if faltan else f'base: {CORTO.get(datos.get("base"), "")}', "navegador"),
            ("Pantallas", pant, "", f'{r.get("paginas", 0)} página(s) × {len(datos.get("resoluciones") or [])} resolución(es)', "pantalla"),
            ("Sin diferencias", r.get("sin_diferencias", 0), "ok" if pant and r.get("sin_diferencias") == pant else "",
             f'{round(r.get("sin_diferencias", 0) / pant * 100) if pant else 0} % de las pantallas', "ok", {"pct": r.get("sin_diferencias", 0) / pant * 100 if pant else 0}),
            ("Con problemas", r.get("con_problemas", 0), "bad" if r.get("con_problemas") else "ok", "algo falla o falta en un navegador", "bad"),
            ("Errores JS exclusivos", r.get("errores_js_exclusivos", 0), "bad" if r.get("errores_js_exclusivos") else "ok",
             f'solo en un navegador · {r.get("confirmados", 0)} confirmado(s) al recargar, {r.get("descartados_al_confirmar", 0)} descartado(s)', "codigo"),
            ("Se ve distinto", f'{r.get("pct_prom", 0)} %', "warn" if r.get("pct_max", 0) > 15 else "ok", f'promedio · máximo {r.get("pct_max", 0)} %', "imagen"),
        ]) + "</div>")
    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    body.append(section("Navegadores", tabla_navegadores(datos),
                        "WebKit es el motor de Safari: muy buena aproximación, pero no reemplaza un Safari real de Mac o iPhone"))

    if modo == "suite":
        corridas = datos.get("corridas") or []
        if corridas:
            grupos = [combo_txt(c["id"]) for c in corridas]
            body.append(two_col(
                section("Resultado por navegador", grouped_columns(grupos, [("Aprobados", OK, [c["aprobados"] for c in corridas]),
                                                                            ("Fallidos", CRITICO, [c["fallidos"] for c in corridas])], ancho=660)),
                section("Escenarios por resultado", donut_panel([(r.get(k, 0), CLASE[c][0], c) for k, c in
                                                                 (("pasan_en_todos", "Pasa en todos"), ("diferencias", "Diferencia entre navegadores"),
                                                                  ("fallan_en_todos", "Falla en todos"), ("inestables", "Inestable"),
                                                                  ("incompletos", "Sin resultado completo")) if r.get(k)],
                                                                round(r.get("pasan_en_todos", 0) / r["escenarios"] * 100) if r.get("escenarios") else 0,
                                                                "pasan en todos"))))
        filas = []
        for f in datos.get("escenarios") or []:
            ident = " · ".join(x for x in (f.get("historia"), f.get("caso")) if x)
            fila = [f'<strong style="color:var(--ink)">{e(f["escenario"])}</strong><div class="muted">{e(ident)} · <span class="mono">{e(f["uri"])}:{e(f["linea"])}</span></div>',
                    pill_de(CLASE, f["clase"])]
            for c in corridas:
                x = f["resultados"].get(c["id"]) or {}
                img = miniatura(x.get("captura"), f'{f["escenario"]} · {combo_txt(c["id"])}', "s") if x.get("captura") else ""
                fila.append(f'<div class="celda">{estado_pill(x.get("estado") if x.get("estado") in ("Aprobado", "Fallido") else ("Inestable" if x.get("estado") == "Inestable" else "N/A"))}{img}</div>')
            filas.append(fila)
        if filas:
            body.append(section("Matriz de escenarios", f'<div class="matriz">{table(["Escenario", "Resultado"] + [combo_txt(c["id"]) for c in corridas], filas)}</div>',
                                "cada escenario en cada navegador, con la captura del final (o del momento en que falló)"))
        errores = [c for c in corridas if c.get("error")]
        if errores:
            body.append(section("Corridas sin resultados", "".join(
                f'<div class="hallazgo"><h3>{nav_pill(c["id"], combo_txt(c["id"]))}</h3><div class="err">{e(c["error"])}</div></div>' for c in errores)))
    else:
        if vivos:
            cuenta_n = Counter(h.get("navegador") for h in vivos)
            cuenta_t = Counter(h["tipo"] for h in vivos)
            body.append(two_col(
                section("Hallazgos por navegador", bar_chart([(CORTO.get(n, n), cuenta_n[n], COLOR_NAV.get(n, NEUTRO)) for n in COLOR_NAV if cuenta_n.get(n)], ancho_etiqueta=110)),
                section("Hallazgos por tipo", bar_chart([(t, c, SERIES[i % len(SERIES)]) for i, (t, c) in enumerate(cuenta_t.most_common())], ancho_etiqueta=160))))
        filas_pag = datos.get("paginas") or []
        combos = list(dict.fromkeys(k for f in filas_pag for k in f["resultados"]))
        navs_orden = list(dict.fromkeys(k.split("-")[0] for k in combos))
        filas = []
        for f in filas_pag:
            fila = [f'<span class="mono" style="color:var(--ink)">{e(corto_url(f["url"]))}</span><div class="muted">{e(f["resolucion"])}</div>']
            for n in navs_orden:
                x = f["resultados"].get(f'{n}-{f["resolucion"]}') or {}
                pct = f'<span class="pct">{x["pct"]} % distinto</span>' if x.get("pct") is not None else (
                    '<span class="pct">base</span>' if f'{n}-{f["resolucion"]}' == f["base"] else "")
                img = miniatura(x.get("captura"), f'{corto_url(f["url"])} · {CORTO.get(n)} {f["resolucion"]}', "s") if x.get("captura") else ""
                fila.append(f'<div class="celda"><a href="#p-{e(f["pagina"])}-{e(f["resolucion"])}" style="text-decoration:none">{pill_de(ESTADO_PAG, x.get("estado"))}</a>{pct}{img}</div>')
            filas.append(fila)
        if filas:
            body.append(section("Matriz de pantallas", f'<div class="matriz">{table(["Pantalla"] + [CORTO.get(n, n) for n in navs_orden], filas)}</div>',
                                "estado de cada página en cada navegador · clic en el estado para compararlas"))
        bloques = []
        abierto = False
        for f in filas_pag:
            base = f["resultados"].get(f["base"]) or {}
            ancho = int(f["resolucion"].split("x")[0])
            figs = ""
            for k, x in f["resultados"].items():
                titulo = corto_url(f["url"]) + " · " + combo_txt(k)
                img = miniatura(x.get("captura"), titulo) if x.get("captura") else ""
                figs += f'<figure>{img}<figcaption>{nav_pill(k)}{pill_de(ESTADO_PAG, x.get("estado"))}</figcaption></figure>'
            comps = "".join(comparador(base["captura"], x["captura"], x["diferencia"], CORTO.get(f["base"].split("-")[0]), CORTO.get(k.split("-")[0]), ancho)
                            for k, x in f["resultados"].items() if k != f["base"] and x.get("diferencia") and base.get("captura"))
            problemas = any(x.get("estado") != "OK" for x in f["resultados"].values())
            abrir = "open" if problemas and not abierto else ""
            abierto = abierto or problemas
            peor = "Con problemas" if any(x.get("estado") == "Con problemas" for x in f["resultados"].values()) else "Diferencias menores"
            estado_html = pill_de(ESTADO_PAG, peor) if problemas else '<span class="muted">sin diferencias</span>'
            bloques.append(f'''<details class="pag" id="p-{e(f["pagina"])}-{e(f["resolucion"])}" {abrir}>
              <summary><strong>{e(corto_url(f["url"]))}</strong><span class="muted">{e(f["resolucion"])}</span>{estado_html}</summary>
              <div class="lado">{figs}</div>{comps}</details>''')
        if bloques:
            body.append(section("Cada pantalla en cada navegador", "".join(bloques),
                                "lado a lado y con el comparador deslizable contra el navegador base"))

    if hallazgos:
        filas = []
        for h in hallazgos:
            mas = len(h.get("pantallas") or []) - 1
            mas_txt = f" · y {mas} más" if mas > 0 else ""
            donde = (f'<span class="mono">{e(corto_url(h["url"]))}</span><div class="muted">{e(h.get("resolucion"))}{mas_txt}</div>'
                     if h.get("url") else f'<span class="mono">{e(h.get("escenario", ""))}</span>')
            navcol = nav_pill(h["navegador"]) if h.get("navegador") else "".join(nav_pill(x, combo_txt(x)) for x in h.get("fallan") or [])
            filas.append([f'<a class="id" href="#{e(h["id"])}" style="color:var(--ink)">{e(h["id"])}</a>', nivel_badge(h["severidad"]), e(h["tipo"]),
                          f'<strong style="color:var(--ink)">{e(h["titulo"])}</strong>', navcol, donde])
        body.append(section("Hallazgos", table(["ID", "Severidad", "Tipo", "Hallazgo", "Navegador", "Dónde"], filas), "clic en el ID para ver el detalle"))
        body.append(section("Detalle de cada hallazgo", "".join(detalle_hallazgo(h, h["_a"]) for h in hallazgos)))

    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))

    cfg = datos.get("config") or {}
    filas = [["Modo", e("Suite de k0lmena (npm test por navegador)" if modo == "suite" else "Recorrido de páginas (solo GET)")],
             ["Resoluciones", e(", ".join(datos.get("resoluciones") or []))]]
    if modo == "suite":
        filas.append(["Filtro de escenarios", f'<span class="mono">{e(datos.get("tags") or "todos")}</span>'])
        for c in datos.get("corridas") or []:
            if c.get("reporte"):
                filas.append([f"Reporte de Cucumber · {e(combo_txt(c['id']))}", f'<a href="{e(c["reporte"])}" style="color:var(--ink)">{e(c["reporte"])}</a>'])
    else:
        filas += [["Navegador base", e(CORTO.get(datos.get("base")))], ["Tolerancia de posición", f'{e(cfg.get("tolerancia_px"))} px'],
                  ["Zonas ocultas", e(", ".join(cfg.get("ocultar") or []) or "ninguna")]]
    body.append(section("Configuración de la corrida", table(["Dato", "Valor"], filas)))

    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Historia", datos.get("historia")), ("Sitio", datos.get("host")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
                      ("Modo", "suite" if modo == "suite" else "páginas"), ("Duración", f'{datos.get("duracion_s", 0)} s')])
    return page("Cross-browser", "Compatibilidad entre navegadores", meta_html, CSS_EXTRA + CSS_PP + CSS_CB + "".join(body) + JS_PP)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML cross-browser a partir de cross-browser.json")
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
    hist_html = _historial.seccion("cross-browser", Path(a.datos_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

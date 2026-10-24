#!/usr/bin/env python3
"""
Genera el Informe de accesibilidad en HTML (dashboard, modo oscuro) a partir de la auditoría
automática (auditoria.json, de `npm run accesibilidad`) y, opcionalmente, del análisis del agente
analista-accesibilidad. `npm run accesibilidad` ya lo genera solo al terminar; el agente lo vuelve
a generar con su análisis.

Uso:
    python scripts/generar_informe_accesibilidad.py <auditoria.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (cumplimiento automático, hallazgos por severidad, criterios WCAG
incumplidos, elementos afectados), gráficos (reglas que pasan y fallan, hallazgos por principio y por
severidad, por página), los criterios WCAG incumplidos con su nombre y nivel, cada hallazgo con qué
pasa, cómo corregirlo, los elementos afectados con su captura (clic para ampliar) y el link a la
documentación, la revisión manual, lo que axe no pudo decidir, la navegación con teclado, las páginas,
el video y las capturas.

Los hallazgos AUTOMÁTICOS salen del auditoria.json. El análisis (opcional) aporta:
{
  "veredicto": "No cumple AA: 3 barreras críticas", "veredicto_tono": "bad",   // ok | warn | bad
  "resumen": "Resumen para alguien no técnico...",
  "areas_revisadas": ["Lector de pantalla en el registro", "Mensajes de error del formulario"],
  "notas": {"A-02": "Las imágenes decorativas pueden llevar alt vacío"},
  "descartados": [{"id": "A-09", "motivo": "El tabindex lo agrega un widget de terceros que no se puede cambiar"}],
  "severidades": {"A-07": "Crítica"},
  "manuales": [{"id": "M-01", "titulo": "...", "severidad": "Alta", "wcag": ["3.3.1"], "pagina": "https://...",
                "pasos": ["..."], "esperado": "...", "obtenido": "...", "correccion": "...", "evidencia": "capturas/manual/m-01.png"}],
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],   // "descripcion" vale como alias de que_falta
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
"""
import argparse
import datetime
import json
from pathlib import Path
import sys

import _historial
from _i18n import escribir_bilingue, idioma_actual, localizar  # noqa: E402,F401
from _estilos_reporte import (falta_informacion, avisar_analisis, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, donut_panel,
                              two_col, nivel_badge, _pastilla, CRITICO, SERIO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA, JS_EXTRA, miniatura, corto, origen

SEVERIDADES = [("Crítica", CRITICO), ("Alta", SERIO), ("Media", AVISO), ("Baja", NEUTRO)]
ORDEN = {s: i for i, (s, _) in enumerate(SEVERIDADES)}
PRINCIPIOS = {"1": ("Perceptible", SERIES[1]), "2": ("Operable", SERIES[3]), "3": ("Comprensible", SERIES[2]), "4": ("Robusto", SERIES[7])}

# Criterios de conformidad de WCAG 2.2 (niveles A y AA, y los AAA que revisa axe).
WCAG = {
    "1.1.1": ("Contenido no textual", "A"), "1.2.1": ("Solo audio y solo video (grabado)", "A"),
    "1.2.2": ("Subtítulos (grabado)", "A"), "1.2.3": ("Audiodescripción o alternativa multimedia (grabado)", "A"),
    "1.2.4": ("Subtítulos (en directo)", "AA"), "1.2.5": ("Audiodescripción (grabado)", "AA"),
    "1.3.1": ("Información y relaciones", "A"), "1.3.2": ("Secuencia significativa", "A"),
    "1.3.3": ("Características sensoriales", "A"), "1.3.4": ("Orientación", "AA"),
    "1.3.5": ("Identificar el propósito de la entrada", "AA"), "1.4.1": ("Uso del color", "A"),
    "1.4.2": ("Control del audio", "A"), "1.4.3": ("Contraste (mínimo)", "AA"),
    "1.4.4": ("Cambio de tamaño del texto", "AA"), "1.4.5": ("Imágenes de texto", "AA"),
    "1.4.6": ("Contraste (mejorado)", "AAA"), "1.4.10": ("Reajuste del contenido (reflow)", "AA"),
    "1.4.11": ("Contraste no textual", "AA"), "1.4.12": ("Espaciado del texto", "AA"),
    "1.4.13": ("Contenido con hover o foco", "AA"), "2.1.1": ("Teclado", "A"),
    "2.1.2": ("Sin trampas para el foco del teclado", "A"), "2.1.4": ("Atajos de teclado de un carácter", "A"),
    "2.2.1": ("Tiempo ajustable", "A"), "2.2.2": ("Poner en pausa, detener, ocultar", "A"),
    "2.2.4": ("Interrupciones", "AAA"), "2.3.1": ("Umbral de tres destellos o menos", "A"),
    "2.4.1": ("Evitar bloques", "A"), "2.4.2": ("Titulado de páginas", "A"), "2.4.3": ("Orden del foco", "A"),
    "2.4.4": ("Propósito de los enlaces (en contexto)", "A"), "2.4.5": ("Múltiples vías", "AA"),
    "2.4.6": ("Encabezados y etiquetas", "AA"), "2.4.7": ("Foco visible", "AA"),
    "2.4.9": ("Propósito de los enlaces (solo enlace)", "AAA"), "2.4.11": ("Foco no oculto (mínimo)", "AA"),
    "2.5.1": ("Gestos del puntero", "A"), "2.5.2": ("Cancelación del puntero", "A"), "2.5.3": ("Etiqueta en el nombre", "A"),
    "2.5.4": ("Activación por movimiento", "A"), "2.5.7": ("Movimientos de arrastre", "AA"),
    "2.5.8": ("Tamaño del objetivo (mínimo)", "AA"), "3.1.1": ("Idioma de la página", "A"),
    "3.1.2": ("Idioma de las partes", "AA"), "3.2.1": ("Al recibir el foco", "A"), "3.2.2": ("Al recibir entradas", "A"),
    "3.2.3": ("Navegación coherente", "AA"), "3.2.4": ("Identificación coherente", "AA"), "3.2.6": ("Ayuda coherente", "A"),
    "3.3.1": ("Identificación de errores", "A"), "3.3.2": ("Etiquetas o instrucciones", "A"),
    "3.3.3": ("Sugerencias ante errores", "AA"), "3.3.4": ("Prevención de errores (legales, financieros, datos)", "AA"),
    "3.3.7": ("Entrada redundante", "A"), "3.3.8": ("Autenticación accesible (mínima)", "AA"),
    "4.1.2": ("Nombre, función, valor", "A"), "4.1.3": ("Mensajes de estado", "AA"),
}

CSS_A11Y = """
<style>
.crit{display:inline-block;font-family:var(--mono);font-size:11.5px;padding:1px 7px;border-radius:6px;
  background:var(--tile);border:1px solid var(--border);color:var(--ink);margin:2px 4px 2px 0;white-space:nowrap}
.codigo-a11y{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 10px;white-space:pre-wrap;
  word-break:break-all;color:var(--body);font-family:var(--mono);font-size:12px;margin:4px 0}
.elem{display:grid;grid-template-columns:1fr 130px;gap:14px;padding:10px 0;border-top:1px dashed var(--border-soft)}
.elem:first-child{border-top:0}
.foco{font-size:12.5px;color:var(--body);columns:2;column-gap:28px}
.foco li{margin:2px 0;break-inside:avoid}
@media (max-width:720px){.elem{grid-template-columns:1fr}.foco{columns:1}}
</style>
"""


def crit(c):
    nombre, nivel = WCAG.get(c, ("", ""))
    return f'<span class="crit" title="{e(nombre)}">{e(c)}{" · " + e(nivel) if nivel else ""}</span>'


def principio(c):
    return PRINCIPIOS.get((c or "0")[0], ("Buenas prácticas", NEUTRO))


def tono_auto(hallazgos, nivel):
    sev = {h["severidad"] for h in hallazgos}
    wcag = [h for h in hallazgos if h.get("wcag")]
    if "Crítica" in sev:
        return "bad", f"No cumple WCAG {nivel}: hay barreras críticas que impiden usar el sitio a algunas personas"
    if wcag:
        return "warn", f"No cumple WCAG {nivel}: hay criterios incumplidos que conviene corregir"
    if hallazgos:
        return "warn", "Sin criterios WCAG incumplidos en la parte automática; quedan buenas prácticas por mejorar"
    return "ok", f"Sin problemas detectados en la parte automática de WCAG {nivel} (falta la revisión manual)"


def build_html(datos, analisis, hist_html=""):
    descartados = {str(d.get("id")): d.get("motivo", "") for d in analisis.get("descartados") or []}
    notas = analisis.get("notas") or {}
    ajustes = analisis.get("severidades") or {}
    base = origen(datos.get("url"))
    cfg = datos.get("config") or {}
    r = datos.get("resumen") or {}
    pags = datos.get("paginas") or []
    nivel = cfg.get("nivel", "AA")

    hallazgos = []
    for h in datos.get("hallazgos") or []:
        if h.get("id") in descartados:
            continue
        h = dict(h)
        if ajustes.get(h.get("id")) in ORDEN:
            h["severidad"] = ajustes[h["id"]]
        hallazgos.append(h)
    manuales = [dict(m, fuente="manual", paginas=[m.get("pagina")] if m.get("pagina") else [], total_nodos=1)
                for m in analisis.get("manuales") or []]
    todos = sorted(hallazgos + manuales, key=lambda h: ORDEN.get(h.get("severidad"), 9))
    por_sev = {s: sum(1 for h in todos if h.get("severidad") == s) for s, _ in SEVERIDADES}
    criterios = sorted({c for h in todos for c in h.get("wcag") or []}, key=lambda c: [int(x) for x in c.split(".")])
    teclado = [h for h in hallazgos if h.get("fuente") == "teclado"]

    body = []
    tono, texto = tono_auto(todos, nivel)
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))

    pct = r.get("cumplimiento_pct")
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Cumplimiento automático", f"{pct:g} %" if pct is not None else "—", "ok" if (pct or 0) >= 95 else "warn" if (pct or 0) >= 80 else "bad",
         "de las reglas de axe que aplican", "", {"pct": pct or 0}),
        ("Hallazgos", len(todos), "bad" if por_sev["Crítica"] else ("warn" if todos else "ok"),
         f'{por_sev["Crítica"]} críticos · {por_sev["Alta"]} altos · {por_sev["Media"]} medios · {por_sev["Baja"]} bajos'),
        ("Criterios WCAG incumplidos", len(criterios), "bad" if criterios else "ok", f"nivel objetivo {nivel}"),
        ("Elementos afectados", sum(h.get("total_nodos", 0) for h in hallazgos), "warn" if hallazgos else "ok"),
        ("Páginas auditadas", r.get("paginas", len(pags)), "", f'{r["paginas_sin_recorrer"]} sin recorrer' if r.get("paginas_sin_recorrer") else ""),
        ("Teclado", len(teclado), "bad" if any(h["severidad"] == "Crítica" for h in teclado) else ("warn" if teclado else "ok"),
         "foco visible, trampas y salto al contenido"),
        ("Para revisar a mano", len(datos.get("revisar") or []), "warn" if datos.get("revisar") else "", "axe no pudo decidir"),
    ] + ([("Revisión manual", len(manuales), "warn" if manuales else "ok")] if analisis else [])) + "</div>")

    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    # ---- Panorama
    ok_reglas = sum(len(p.get("aprobadas") or []) for p in pags)
    mal_reglas = sum(len(p.get("violaciones") or []) for p in pags)
    seg = [(ok_reglas, OK, "Reglas que pasan"), (mal_reglas, CRITICO, "Reglas que fallan")]
    g1 = donut_panel(seg, round(pct or 0), "cumplimiento")
    por_principio = {}
    for h in todos:
        nombre, color = principio((h.get("wcag") or [""])[0])
        por_principio.setdefault(nombre, [0, color])[0] += 1
    orden_p = ["Perceptible", "Operable", "Comprensible", "Robusto", "Buenas prácticas"]
    g2 = bar_chart([(n, por_principio[n][0], SERIES[0]) for n in orden_p if n in por_principio], ancho_etiqueta=140)
    body.append(two_col(section("Reglas de axe", g1, "sumando todas las páginas"),
                        section("Hallazgos por principio WCAG", g2)))
    if todos:
        por_pagina = sorted(((corto(p["url"], base), sum(1 for h in hallazgos if p["url"] in h.get("paginas", []))) for p in pags), key=lambda x: -x[1])
        body.append(two_col(section("Hallazgos por severidad", bar_chart([(s, por_sev[s], c) for s, c in SEVERIDADES])),
                            section("Hallazgos por página", bar_chart([(u, n, SERIES[0]) for u, n in por_pagina[:12] if n], ancho_etiqueta=200))))

    # ---- Alcance
    # Párrafos con datos intercalados: una versión por idioma.
    en = idioma_actual() == "en"
    fuerte = '<strong style="color:var(--ink)">{}</strong>'
    areas = (f'<p>{fuerte.format("Manual review:" if en else "Revisión manual:")} ' + e(", ".join(analisis["areas_revisadas"])) + "</p>"
             if analisis.get("areas_revisadas") else "")
    n_pag, url, herr = e(r.get("paginas", len(pags))), e(datos.get("url")), e(datos.get("herramienta", "axe-core"))
    if en:
        alcance = (f'<p>{fuerte.format("Automated audit")} of {n_pag} page(s) from <span class="mono">{url}</span> '
                   f'against {fuerte.format(f"WCAG 2.2 level {e(nivel)}")}{" and best practices" if cfg.get("buenas_practicas") else ""} with {herr}; '
                   f'keyboard navigation (up to {e(cfg.get("tabs"))} Tab presses per page) and content reflow at 320px. Duration: {e(datos.get("duracion_s"))} s.</p>'
                   f'<p>{fuerte.format("Important:")} an automated audit finds between 30 and 50 % of accessibility problems. '
                   'A criterion that does not show up is not necessarily met: the quality of text alternatives, the reading order, error messages '
                   'and use with a screen reader or zoom need a manual review.</p>')
    else:
        alcance = (f'<p>{fuerte.format("Auditoría automática")} de {n_pag} página(s) desde <span class="mono">{url}</span> '
                   f'contra {fuerte.format(f"WCAG 2.2 nivel {e(nivel)}")}{" y buenas prácticas" if cfg.get("buenas_practicas") else ""} con {herr}; '
                   f'navegación con teclado (hasta {e(cfg.get("tabs"))} Tab por página) y reajuste del contenido a 320px. Duración: {e(datos.get("duracion_s"))} s.</p>'
                   f'<p>{fuerte.format("Importante:")} una auditoría automática detecta entre un 30 y un 50 % de los problemas de accesibilidad. '
                   'Que no aparezca un criterio no significa que se cumpla: la calidad de los textos alternativos, el orden de lectura, los mensajes '
                   'de error, el uso con lector de pantalla o con zoom requieren revisión manual.</p>')
    body.append(section("Alcance y método", f'<div class="cardbody">{alcance}{areas}</div>'))

    # ---- Criterios incumplidos
    if criterios:
        filas = []
        for c in criterios:
            nombre, niv = WCAG.get(c, ("—", "—"))
            hs = [h for h in todos if c in (h.get("wcag") or [])]
            filas.append([crit(c), e(nombre), e(niv), e(principio(c)[0]), ", ".join(e(h["id"]) for h in hs),
                          e(len({p for h in hs for p in h.get("paginas") or []}))])
        body.append(section("Criterios WCAG incumplidos", table(["Criterio", "Nombre", "Nivel", "Principio", "Hallazgos", "Páginas"], filas)))

    # ---- Tabla de hallazgos
    if todos:
        filas = []
        for h in todos:
            ev = next((x.get("captura") for x in h.get("ejemplos") or [] if x.get("captura")), None) or h.get("evidencia")
            nota = f'<div class="muted" style="margin-top:4px">{e(notas[h["id"]])}</div>' if h.get("id") in notas else ""
            fuente = {"axe": "axe", "teclado": "Teclado", "reflow": "Reflow", "manual": "Manual"}.get(h.get("fuente"), "")
            filas.append([f'<a href="#{e(h["id"])}" style="color:var(--ink);white-space:nowrap">{e(h["id"])}</a>', nivel_badge(h.get("severidad")),
                          "".join(crit(c) for c in h.get("wcag") or []) or '<span class="muted">Buena práctica</span>',
                          f'<strong style="color:var(--ink)">{e(h.get("titulo"))}</strong><div class="muted">{e(fuente)}</div>{nota}',
                          e(len(h.get("paginas") or [])), e(h.get("total_nodos", "")), miniatura(ev, f'{h["id"]} · {h.get("titulo")}', "s")])
        body.append(section("Todos los hallazgos", table(["ID", "Severidad", "WCAG", "Hallazgo", "Páginas", "Elementos", "Evidencia"], filas),
                            "clic en el ID para ver el detalle y en la captura para ampliarla"))
    else:
        body.append(section("Hallazgos", '<div class="cardbody"><p>La auditoría automática no encontró problemas.</p></div>'))

    # ---- Detalle
    detalle = []
    for h in [x for x in todos if x.get("fuente") != "manual"]:
        elems = []
        for x in (h.get("ejemplos") or [])[:8]:
            arreglo = (x.get("resumen") or "").replace("Fix any of the following:", "Corregí alguna de estas:").replace("Fix all of the following:", "Corregí todas estas:")
            elems.append(f'''<div class="elem"><div><div class="mono muted">{e(corto(x.get("pagina"), base))}</div>
              <div class="mono" style="color:var(--ink)">{e(x.get("selector"))}</div>
              {f'<div class="codigo-a11y">{e(x["html"])}</div>' if x.get("html") else ""}
              {f'<div class="codigo-a11y">{e(arreglo)}</div>' if arreglo else ""}</div>
              <div>{miniatura(x.get("captura"), x.get("selector", ""))}</div></div>''')
        mas = h.get("total_nodos", 0) - len(elems)
        paginas = h.get("paginas") or []
        detalle.append(f'''<div class="hallazgo" id="{e(h["id"])}"><h3>{e(h["id"])} · {e(h.get("titulo"))} {nivel_badge(h.get("severidad"))}
            {"".join(crit(c) for c in h.get("wcag") or [])}</h3>
          <div class="lbl">Qué pasa</div><p>{e(h.get("descripcion"))}</p>
          {"".join(f'<p class="muted">{e(c)} · {e(WCAG.get(c, ("",))[0])}</p>' for c in h.get("wcag") or [])}
          {f'<div class="lbl">Análisis</div><p>{e(notas[h["id"]])}</p>' if h.get("id") in notas else ""}
          <div class="lbl">Páginas ({len(paginas)})</div><p class="mono">{e(", ".join(corto(p, base) for p in paginas[:10]))}{" …" if len(paginas) > 10 else ""}</p>
          <div class="lbl">Elementos afectados ({e(h.get("total_nodos"))}) y cómo corregirlos</div>{"".join(elems)}
          {f'<p class="muted">… y {mas} elemento(s) más.</p>' if mas > 0 else ""}
          {f'<div class="lbl">Más información</div><p><a href="{e(h["ayuda"])}" target="_blank" rel="noopener" style="color:var(--ink)">Guía de la regla <span class="mono">{e(h.get("regla"))}</span> (Deque, en español)</a></p>' if h.get("ayuda") else ""}
        </div>''')
    if detalle:
        body.append(section("Detalle de cada hallazgo", "".join(detalle)))

    if manuales:
        det = []
        for x in manuales:
            pasos = "".join(f"<li>{e(p)}</li>" for p in x.get("pasos") or [])
            det.append(f'''<div class="hallazgo" id="{e(x.get("id"))}"><h3>{e(x.get("id"))} · {e(x.get("titulo"))} {nivel_badge(x.get("severidad"))}
                {"".join(crit(c) for c in x.get("wcag") or [])}</h3><div class="mono muted">{e(x.get("pagina"))}</div>
              {f'<div class="lbl">Pasos</div><ol>{pasos}</ol>' if pasos else ""}
              {f'<div class="lbl">Resultado esperado</div><p>{e(x["esperado"])}</p>' if x.get("esperado") else ""}
              {f'<div class="lbl">Resultado obtenido</div><p>{e(x["obtenido"])}</p>' if x.get("obtenido") else ""}
              {f'<div class="lbl">Cómo corregirlo</div><p>{e(x["correccion"])}</p>' if x.get("correccion") else ""}
              {f'<div class="lbl">Evidencia</div>{miniatura(x["evidencia"], x.get("titulo", ""))}' if x.get("evidencia") else ""}</div>''')
        body.append(section("Revisión manual", "".join(det)))

    revisar = datos.get("revisar") or []
    if revisar:
        filas = [[e(x["id"]), f'<strong style="color:var(--ink)">{e(x.get("titulo"))}</strong><div class="muted">{e(x.get("descripcion"))}</div>',
                  "".join(crit(c) for c in x.get("wcag") or []) or "—", e(len(x.get("paginas") or [])), e(x.get("total_nodos")),
                  f'<a href="{e(x["ayuda"])}" target="_blank" rel="noopener" style="color:var(--ink)">guía</a>' if x.get("ayuda") else "—"]
                 for x in revisar]
        body.append(section("Para revisar a mano", table(["ID", "Qué revisar", "WCAG", "Páginas", "Elementos", "Ayuda"], filas),
                            "axe no pudo decidir si cumplen (por ejemplo, contraste sobre imágenes)"))

    # ---- Teclado por página
    con_teclado = [p for p in pags if p.get("teclado")]
    if con_teclado:
        filas, bloques = [], []
        for p in con_teclado:
            t = p["teclado"]
            pasos = t.get("pasos") or []
            sin = sum(1 for x in pasos if not x.get("visible_indicador"))
            salto = bool(pasos) and any(k in (pasos[0].get("texto") or "").lower() for k in ("salt", "skip", "contenido"))
            filas.append([f'<span class="mono">{e(corto(p["url"], base))}</span>', e(len(pasos)),
                          _pastilla("OK", OK, "✓") if not sin else _pastilla(f"{sin} sin indicador", SERIO, "✕"),
                          _pastilla("Sí", CRITICO, "✕") if t.get("trampa") else _pastilla("No", OK, "✓"),
                          _pastilla("Sí", OK, "✓") if salto else _pastilla("No", AVISO, "!")])
            aviso = f' <b style="color:{SERIO}">· sin foco visible</b>'
            orden = "".join(f'<li><span class="mono">{e(x["elemento"])}</span> {e(x.get("texto") or "")}'
                            f'{aviso if not x.get("visible_indicador") else ""}</li>' for x in pasos)
            bloques.append(f'<details class="pag"><summary><span class="mono">{e(corto(p["url"], base))}</span>'
                           f'<span class="muted">{len(pasos)} elementos con Tab</span></summary>'
                           f'<div style="padding:0 24px 18px"><ol class="foco">{orden or "<li>Ningún elemento recibió foco.</li>"}</ol></div></details>')
        body.append(section("Navegación con teclado", table(["Página", "Elementos con Tab", "Foco visible", "Trampa de foco", "Salto al contenido"], filas)))
        body.append(section("Orden del foco por página", "".join(bloques), "en el orden en que se recorren con Tab"))

    # ---- Páginas
    if pags:
        filas = []
        for p in pags:
            n_h = sum(1 for h in hallazgos if p["url"] in (h.get("paginas") or []))
            rf = p.get("reflow") or {}
            filas.append([f'<span class="mono">{e(corto(p["url"], base))}</span>' + (f'<div class="muted">{e(p.get("titulo"))}</div>' if p.get("titulo") else ""),
                          _pastilla(str(p.get("status")), OK, "✓") if not p.get("error") and 0 < (p.get("status") or 0) < 400 else _pastilla(str(p.get("error") and "error" or p.get("status")), CRITICO, "✕"),
                          e(p.get("idioma") or "—"), e(len(p.get("violaciones") or [])), e(len(p.get("aprobadas") or [])),
                          _pastilla("Desborda", AVISO, "!") if rf.get("desborda") else _pastilla("OK", OK, "✓"),
                          _pastilla(str(n_h), CRITICO if n_h else OK, "✕" if n_h else "✓"), miniatura(p.get("captura"), corto(p["url"], base), "s")])
        body.append(section("Páginas auditadas", table(["Página", "Estado", "Idioma (lang)", "Reglas que fallan", "Reglas que pasan", "Reflow 320px", "Hallazgos", "Captura"], filas)))

    videos = datos.get("videos") or []
    if videos:
        figs = "".join(f'<figure><video controls preload="metadata" src="{e(v["archivo"])}#t=1"></video>'
                       f'<figcaption>{e(v.get("titulo", v["archivo"]))} · <a href="{e(v["archivo"])}" download style="color:var(--ink)">descargar</a></figcaption></figure>'
                       for v in videos)
        body.append(section("Video", f'<div class="videos">{figs}</div>'))
    caps = [p for p in pags if p.get("captura")]
    if caps:
        figs = "".join(f'<figure>{miniatura(p["captura"], corto(p["url"], base)).replace("thumb", "", 1)}'
                       f'<figcaption>{e(corto(p["url"], base))}</figcaption></figure>' for p in caps)
        body.append(section("Capturas de las páginas", f'<div class="galeria">{figs}</div>', "los elementos que fallan, marcados en rojo"))

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
                      ("Norma", f"WCAG 2.2 {nivel}"), ("Herramienta", datos.get("herramienta"))])
    return page("Informe de accesibilidad", "Accesibilidad", meta_html, CSS_EXTRA + CSS_A11Y + "".join(body) + JS_EXTRA)


def main():
    for flujo in (sys.stdout, sys.stderr):  # acentos bien en la consola de Windows
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de accesibilidad a partir de auditoria.json")
    ap.add_argument("auditoria_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis", help="JSON con veredicto, resumen, revisión manual, descartes y recomendaciones")
    a = ap.parse_args()
    if not a.salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    with open(a.auditoria_json, encoding="utf-8") as f:
        datos = json.load(f)
    analisis = {}
    if a.analisis:
        with open(a.analisis, encoding="utf-8") as f:
            analisis = json.load(f)
        avisar_analisis(analisis, [h.get("id") for h in (datos.get("hallazgos") or []) + (datos.get("revisar") or [])] + [x.get("id") for x in analisis.get("manuales") or []])
    hist_html = _historial.seccion("accesibilidad", Path(a.auditoria_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

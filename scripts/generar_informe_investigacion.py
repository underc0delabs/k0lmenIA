#!/usr/bin/env python3
"""
Informe del relevamiento de un proyecto completo (agente investigador-proyecto).

Uso (desde la raíz del repo):
    python scripts/generar_informe_investigacion.py <investigacion.json> [--salida <carpeta>]

Arma, a partir del JSON que escribe el agente, en la carpeta del JSON (o en --salida):
  - informe-investigacion.html   (web completa: indicadores, gráficos, MAPAS CONCEPTUALES, buscador y navegación)
  - informe-investigacion.md     (lo mismo en Markdown, con las tablas alineadas)
  - resumen.md                   (resumen breve, una carilla: qué es el proyecto y lo más urgente)
  - presentacion-investigacion.html  (presentación autocontenida; ←/→ para navegar e imprime a PDF, una diapo por hoja)
  - input/documentacion/proyecto/investigacion/*.md  (lo relevado como documentación del proyecto, con el encabezado
                                 del índice, para que los demás agentes lo usen al analizar historias y escribir casos:
                                 resumen, módulos y flujos, backlog, decisiones y glosario, dudas y riesgos; --sin-input
                                 no lo escribe). Regenera input/documentacion/INDICE.md.
  - historial/<fecha-hora>/      (copia de este relevamiento; se guardan los últimos 5). Si hay uno anterior,
                                 el informe trae "Cambios desde el relevamiento anterior": ambigüedades y
                                 preguntas nuevas y resueltas.

Esquema del JSON (todo opcional salvo "proyecto"):
{
  "proyecto": "Tienda online", "clave": "PROJ", "fecha": "2026-10-19",
  "profundidad": "normal", "foco": "", "para": "QA manual",
  "tablero": "https://mi-empresa.atlassian.net/jira/software/projects/PROJ/boards/12",  // la URL que dio la persona
  "resumen": "Qué es el producto, para quién y en qué estado está (2 o 3 frases).",
  "cobertura": {"total_items": 1240, "leidos": 85, "criterio": "Críticos/Altos abiertos, sprint actual, 2 por épica activa",
                "epicas": 14, "historias": 60, "tareas": 110, "comentarios": 240},
  // jerarquia: lo que se recorrió bajando por el tablero (épica -> historias -> tareas), con comentarios y links por ítem.
  "jerarquia": [{"epica": {"id": "PROJ-3", "titulo": "Checkout", "estado": "En curso", "url": "https://.../PROJ-3"},
                 "historias": [{"id": "PROJ-12", "titulo": "Pago con tarjeta", "estado": "En curso", "responsable": "Ana",
                                "tareas": 4, "comentarios": 7, "links": ["Confluence 'Reglas de pagos'", "Figma Checkout"],
                                "nota": "decisión en comentario: cuotas hasta 12"}]}],
  // referencias: todos los links de referencia encontrados en épicas/historias/tareas/comentarios.
  "referencias": [{"tipo": "Confluence", "titulo": "Reglas de pagos", "url": "https://.../wiki/...", "origen": "PROJ-12 (comentario)", "leido": true}],
  // mapas: mapas conceptuales (nodos + enlaces dirigidos). Hacé varios: uno de arquitectura, otro de cómo
  // funciona (flujo), otro de módulos. Si no mandás ninguno, se arma uno de módulos solo. El "nivel" de
  // cada nodo (columna) se calcula por el camino más largo desde una raíz; "grupo" colorea y arma la leyenda.
  "mapas": [{"titulo": "Arquitectura", "tipo": "arquitectura", "descripcion": "Capas y sistemas.",
             "nodos": [{"id": "web", "etiqueta": "Front web (React)", "grupo": "Frontend"},
                       {"id": "api", "etiqueta": "API (Node)", "grupo": "Backend", "nota": "REST"},
                       {"id": "db", "etiqueta": "PostgreSQL", "grupo": "Datos"},
                       {"id": "pg", "etiqueta": "Mercado Pago", "grupo": "Externos"}],
             "enlaces": [{"de": "web", "a": "api", "etiqueta": "HTTPS"}, {"de": "api", "a": "db"}, {"de": "api", "a": "pg", "etiqueta": "cobros"}]},
            {"titulo": "Cómo funciona: comprar", "tipo": "flujo",
             "nodos": [{"id": "s1", "etiqueta": "Agrega al carrito"}, {"id": "s2", "etiqueta": "Checkout"},
                       {"id": "s3", "etiqueta": "Paga con tarjeta"}, {"id": "s4", "etiqueta": "Confirmación"}],
             "enlaces": [{"de": "s1", "a": "s2"}, {"de": "s2", "a": "s3"}, {"de": "s3", "a": "s4", "etiqueta": "ok"}]}],
  "fuentes": [{"fuente": "Jira PROJ", "tipo": "Gestión", "alcance": "épicas, backlog activo y bugs",
               "estado": "leida|parcial|no_accesible", "motivo": "solo si no es leida"}],
  "modulos": [{"nombre": "Checkout", "descripcion": "...", "estado": "En desarrollo",
               "avance": {"hechas": 12, "total": 20}, "fuente": "PROJ-3 (épica)"}],
  "actores": [{"rol": "Comprador", "puede": "...", "fuente": "..."}],
  "flujos": [{"nombre": "Comprar con tarjeta", "pasos": "Carrito → Pago → Confirmación", "items": "PROJ-12, PROJ-14", "fuente": "..."}],
  "integraciones": [{"sistema": "Mercado Pago", "para_que": "cobros", "tipo": "API REST + webhooks", "fuente": "..."}],
  "ambientes": [{"nombre": "QA", "url": "https://qa.tienda.com", "para_que": "pruebas", "fuente": "wiki/Ambientes"}],
  "stack": [{"capa": "Frontend", "tecnologia": "React 19", "fuente": "README.md"}],
  "equipo": [{"rol": "PO", "nombre": "Nombre visible en la herramienta", "temas": "pagos, reglas de negocio", "fuente": "..."}],
  "decisiones": [{"fecha": "2026-09-02", "decision": "...", "quien": "PO", "fuente": "PROJ-12 (comentario)"}],
  "backlog": {"por_estado": {"Por hacer": 40, "En curso": 12, "Hecho": 300},
              "por_tipo": {"Historia": 200, "Bug": 60},
              "bugs_por_severidad": {"Crítica": 2, "Alta": 9, "Media": 20, "Baja": 4},
              "sprint_actual": {"nombre": "Sprint 14", "inicio": "2026-10-13", "fin": "2026-10-24", "items": 18},
              "releases": [{"nombre": "2.4", "fecha": "2026-11-05", "estado": "Planificada", "fuente": "..."}]},
  "pruebas_hoy": [{"que": "Regresión manual en Test Plans", "estado": "Parcial", "fuente": "..."}],
  "glosario": [{"termino": "SKU", "definicion": "...", "fuente": "..."}],
  "linea_de_tiempo": [{"fecha": "2026-11-05", "hito": "Release 2.4", "fuente": "..."}],
  "ambiguedades": [{"id": "AMB-01", "tipo": "Ambigüedad|Contradicción|Vacío|Desactualizado|Dependencia",
                    "que": "...", "fuentes": ["PROJ-45", "Confluence 'Reglas de pagos'"], "impacto": "Alta", "pregunta": "P-01"}],
  "preguntas": [{"id": "P-01", "pregunta": "...", "a_quien": "PO", "prioridad": "Crítica", "por_que": "...", "relacionado": "AMB-01"}],
  "preguntas_arranque": ["¿Qué datos de prueba hay en QA y cómo se piden?"],
  "riesgos": [{"riesgo": "...", "nivel": "Alto|Medio|Bajo", "motivo": "...", "mitigacion": "..."}],
  "proximos_pasos": [{"paso": "Armar tu onboarding", "agente": "guia-onboarding", "pedido": "Armá el onboarding de Ana, QA manual"}],
  "faltantes": ["No hay conector de Figma: los diseños no se revisaron."]
}
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

ESTADO_FUENTE = {"leida": ("Leída", "ok"), "parcial": ("Parcial", "aviso"), "no_accesible": ("No accesible", "falta")}
TIPOS_AMB = ["Contradicción", "Ambigüedad", "Vacío", "Desactualizado", "Dependencia"]
PRIORIDADES = ("Crítica", "Alta", "Media", "Baja")
NIVELES_RIESGO = ("Alto", "Medio", "Bajo")
ORDEN_PRIO = {p: i for i, p in enumerate(PRIORIDADES)}
ORDEN_RIESGO = {n: i for i, n in enumerate(NIVELES_RIESGO)}
MAX_HISTORIAL = 5

CSS_INV = """
.avance{display:flex;align-items:center;gap:10px;min-width:150px}
.avance .b{flex:1;height:6px;border-radius:999px;background:rgba(244,239,230,.07);overflow:hidden}
.avance .b span{display:block;height:100%;background:linear-gradient(90deg,#FFD60A,#FF8A00)}
.avance em{font-style:normal;font-family:var(--mono);font-size:12px;color:var(--muted);white-space:nowrap}
.fuentes-celda{font-family:var(--mono);font-size:12px;color:var(--muted)}
.fuentes-celda b{color:var(--ink);font-weight:600}
.mapa{padding:10px 18px 20px}
.mapa .desc{color:var(--muted);font-size:13px;margin:0 0 12px}
.mapa .wrap{overflow-x:auto}
.mapa svg{min-width:100%;height:auto}
.mapa .nbox{fill:var(--tile);stroke:var(--border)}
.mapa .ntext{fill:var(--ink);font:600 12.5px var(--sans)}
.mapa .nnota{fill:var(--muted);font:11px var(--mono)}
.mapa .edge{fill:none;stroke:var(--muted);stroke-width:1.6;opacity:.7}
.mapa .edge.back{stroke-dasharray:4 4;opacity:.5}
.mapa .elabel{fill:var(--muted);font:11px var(--mono)}
.mapa .elabel-bg{fill:var(--surface)}
"""


def _tr(es, en):
    """Frase armada con datos del relevamiento: cada idioma la arma entera (el diccionario no traduce datos)."""
    from _i18n import idioma_actual
    return en if idioma_actual() == "en" else es


def _t(texto):
    """Un valor fijo del generador (tipo de ambigüedad, prioridad…) en el idioma actual."""
    from _i18n import t
    return t(texto)


def slug(texto):
    s = re.sub(r"[^a-z0-9]+", "-", (texto or "").lower().translate(str.maketrans("áéíóúñü", "aeiounu"))).strip("-")
    return s or "proyecto"


def _norm(texto):
    return re.sub(r"\s+", " ", (texto or "").strip().lower())


def validar(d):
    """Avisos por stderr de lo que dejaría el informe incompleto o engañoso. No corta el informe."""
    avisos = []
    ids_p = [p.get("id") for p in d.get("preguntas") or []]
    ids_a = [a.get("id") for a in d.get("ambiguedades") or []]
    for nombre, ids in (("preguntas", ids_p), ("ambiguedades", ids_a)):
        repetidos = sorted({i for i in ids if i and ids.count(i) > 1})
        if repetidos:
            avisos.append(f"{nombre}: IDs repetidos {', '.join(repetidos)}")
    for a in d.get("ambiguedades") or []:
        if a.get("tipo") == "Contradicción" and len(a.get("fuentes") or []) < 2:
            avisos.append(f"{a.get('id')}: una contradicción necesita sus dos fuentes")
        if a.get("tipo") and a["tipo"] not in TIPOS_AMB:
            avisos.append(f"{a.get('id')}: tipo {a['tipo']!r} fuera de {'/'.join(TIPOS_AMB)}")
        if a.get("impacto") and a["impacto"] not in PRIORIDADES:
            avisos.append(f"{a.get('id')}: impacto {a['impacto']!r} fuera de la escala {'/'.join(PRIORIDADES)}")
        if a.get("pregunta") and a["pregunta"] not in ids_p:
            avisos.append(f"{a.get('id')}: la pregunta {a['pregunta']} no está en 'preguntas'")
    for p in d.get("preguntas") or []:
        if p.get("prioridad") and p["prioridad"] not in PRIORIDADES:
            avisos.append(f"{p.get('id')}: prioridad {p['prioridad']!r} fuera de la escala {'/'.join(PRIORIDADES)}")
    for r in d.get("riesgos") or []:
        if r.get("nivel") and r["nivel"] not in NIVELES_RIESGO:
            avisos.append(f"riesgo {r.get('riesgo', '')[:40]!r}: nivel {r['nivel']!r} fuera de {'/'.join(NIVELES_RIESGO)}")
    for f in d.get("fuentes") or []:
        if f.get("estado") and f["estado"] not in ESTADO_FUENTE:
            avisos.append(f"fuente {f.get('fuente')!r}: estado {f['estado']!r} fuera de {'/'.join(ESTADO_FUENTE)}")
    for x in avisos:
        print(f"[aviso] investigacion.json · {x}", file=sys.stderr)
    return avisos


def comparar(actual, anterior):
    """Qué ambigüedades y preguntas son nuevas y cuáles se resolvieron (por texto, no por ID: los IDs se renumeran)."""
    if not anterior:
        return None

    def mapa(d, clave, campo):
        return {_norm(x.get(campo)): x for x in d.get(clave) or [] if x.get(campo)}

    res = {"fecha_anterior": anterior.get("fecha", "")}
    for clave, campo in (("ambiguedades", "que"), ("preguntas", "pregunta")):
        a, b = mapa(actual, clave, campo), mapa(anterior, clave, campo)
        res[clave] = {"nuevas": [a[k] for k in a if k not in b], "resueltas": [b[k] for k in b if k not in a],
                      "siguen": [a[k] for k in a if k in b]}
    return res


def _avance(av):
    hechas, total = (av or {}).get("hechas"), (av or {}).get("total")
    if not isinstance(hechas, (int, float)) or not total:
        return "—"
    pct = max(0, min(100, 100 * hechas / total))
    return f'<div class="avance"><span class="b"><span style="width:{pct:.0f}%"></span></span><em>{hechas:g}/{total:g} · {pct:.0f} %</em></div>'


def _fuentes(lista):
    from _estilos_reporte import e
    if isinstance(lista, str):
        lista = [lista]
    return '<span class="fuentes-celda">' + " <b>vs.</b> ".join(e(f) for f in lista or []) + "</span>" if lista else "—"


def _link(url, texto=None):
    """Enlace clickeable si hay URL http(s); si no, el texto plano."""
    from _estilos_reporte import e
    texto = texto or url
    if url and re.match(r"^https?://", str(url)):
        return f'<a href="{e(url)}" target="_blank" rel="noopener">{e(texto)}</a>'
    return e(texto)


_MAPA_N = [0]


def _envolver(texto, maxc=24):
    palabras, lineas, actual = str(texto or "").split(), [], ""
    for p in palabras:
        if len(actual) + len(p) + 1 <= maxc or not actual:
            actual = f"{actual} {p}".strip()
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas[:3] or [""]


def mapa_svg(mapa):
    """Dibuja un mapa conceptual (nodos + enlaces dirigidos) como SVG autocontenido, en columnas por
    nivel (nivel = camino más largo desde una raíz). Sirve para arquitectura, flujo o módulos."""
    from _estilos_reporte import e, SERIES
    nodos = [n for n in mapa.get("nodos") or [] if n.get("id")]
    if not nodos:
        return ""
    byid = {n["id"]: n for n in nodos}
    enlaces = [en for en in mapa.get("enlaces") or [] if en.get("de") in byid and en.get("a") in byid]
    # nivel por camino más largo (corta ciclos con el tope de iteraciones)
    nivel = {n["id"]: 0 for n in nodos}
    for _ in range(len(nodos)):
        cambio = False
        for en in enlaces:
            if nivel[en["a"]] < nivel[en["de"]] + 1 <= len(nodos):
                nivel[en["a"]] = nivel[en["de"]] + 1
                cambio = True
        if not cambio:
            break
    cols = {}
    for n in nodos:
        cols.setdefault(nivel[n["id"]], []).append(n)
    grupos = {}
    for n in nodos:
        g = n.get("grupo") or ""
        if g and g not in grupos:
            grupos[g] = SERIES[len(grupos) % len(SERIES)]
    NW, COLGAP, ROWGAP, LH, PADY = 184, 104, 22, 16, 11
    geo, col_h = {}, {}
    for c, lista in cols.items():
        y = 0
        for n in lista:
            lineas = _envolver(n.get("etiqueta") or n["id"])
            h = len(lineas) * LH + 2 * PADY + (16 if n.get("nota") else 0)
            geo[n["id"]] = {"lineas": lineas, "h": h, "nota": n.get("nota"), "grupo": n.get("grupo") or "", "col": c, "y0": y}
            y += h + ROWGAP
        col_h[c] = y - ROWGAP if lista else 0
    alto = max(col_h.values(), default=0) + 20
    for c, lista in cols.items():
        off = (alto - col_h[c]) / 2
        for n in lista:
            g = geo[n["id"]]
            g["x"] = c * (NW + COLGAP) + 10
            g["y"] = g["y0"] + off
    ancho = (max(cols) + 1) * (NW + COLGAP) - COLGAP + 20 if cols else NW
    _MAPA_N[0] += 1
    mid = f"mp{_MAPA_N[0]}"
    svg = [f'<svg viewBox="0 0 {ancho:.0f} {alto:.0f}" role="img" aria-label="{e(mapa.get("titulo", "mapa"))}">',
           f'<defs><marker id="{mid}" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
           f'<path d="M0,0 L7,3 L0,6 Z" fill="currentColor" class="elabel"/></marker></defs>']
    for en in enlaces:
        a, b = geo[en["de"]], geo[en["a"]]
        back = nivel[en["a"]] <= nivel[en["de"]]
        x1, y1 = a["x"] + NW, a["y"] + a["h"] / 2
        x2, y2 = b["x"], b["y"] + b["h"] / 2
        dx = max(40, abs(x2 - x1) / 2)
        svg.append(f'<path class="edge{" back" if back else ""}" marker-end="url(#{mid})" '
                   f'd="M{x1:.0f},{y1:.0f} C{x1 + dx:.0f},{y1:.0f} {x2 - dx:.0f},{y2:.0f} {x2:.0f},{y2:.0f}"/>')
        if en.get("etiqueta"):
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 4
            w = len(en["etiqueta"]) * 6.3 + 8
            svg.append(f'<rect class="elabel-bg" x="{mx - w / 2:.0f}" y="{my - 11:.0f}" width="{w:.0f}" height="15" rx="4"/>'
                       f'<text class="elabel" x="{mx:.0f}" y="{my:.0f}" text-anchor="middle">{e(en["etiqueta"])}</text>')
    for nid, g in geo.items():
        col = grupos.get(g["grupo"], SERIES[0])
        x, y = g["x"], g["y"]
        svg.append(f'<rect class="nbox" x="{x:.0f}" y="{y:.0f}" width="{NW}" height="{g["h"]:.0f}" rx="10"/>'
                   f'<rect x="{x:.0f}" y="{y:.0f}" width="5" height="{g["h"]:.0f}" rx="2.5" fill="{col}"/>')
        ty = y + PADY + 12
        for ln in g["lineas"]:
            svg.append(f'<text class="ntext" x="{x + 16:.0f}" y="{ty:.0f}">{e(ln)}</text>')
            ty += LH
        if g["nota"]:
            svg.append(f'<text class="nnota" x="{x + 16:.0f}" y="{ty:.0f}">{e(g["nota"][:28])}</text>')
    svg.append("</svg>")
    leyenda = ""
    if grupos:
        from _estilos_reporte import legend
        leyenda = legend([(g, c) for g, c in grupos.items()])
    desc = f'<p class="desc">{e(mapa["descripcion"])}</p>' if mapa.get("descripcion") else ""
    return f'<div class="mapa">{desc}<div class="wrap">{"".join(svg)}</div>{leyenda}</div>'


def mapas_de(d):
    """Los mapas que mandó el agente; si no mandó ninguno, arma uno de módulos desde jerarquia/modulos."""
    if d.get("mapas"):
        return d["mapas"]
    raiz = d.get("proyecto") or "Proyecto"
    nodos, enlaces = [{"id": "_raiz", "etiqueta": raiz, "grupo": "Proyecto"}], []
    vistos = set()
    for grupo in d.get("jerarquia") or []:
        ep = grupo.get("epica") or {}
        eid = ep.get("id") or ep.get("titulo")
        if eid and eid not in vistos:
            vistos.add(eid)
            nodos.append({"id": eid, "etiqueta": ep.get("titulo") or eid, "grupo": "Épica", "nota": ep.get("estado")})
            enlaces.append({"de": "_raiz", "a": eid})
    if not vistos:
        for m in d.get("modulos") or []:
            mid = m.get("nombre")
            if mid and mid not in vistos:
                vistos.add(mid)
                nodos.append({"id": mid, "etiqueta": mid, "grupo": "Módulo", "nota": m.get("estado")})
                enlaces.append({"de": "_raiz", "a": mid})
    if len(nodos) < 2:
        return []
    return [{"titulo": "Mapa de módulos", "tipo": "modulos",
             "descripcion": "Armado automático desde las épicas/módulos relevados.", "nodos": nodos, "enlaces": enlaces}]


def build_html(d, cambios=None):
    from _estilos_reporte import (e, page, meta, section, kpi_tiles, table, doc_list, two_col, banner, bar_chart,
                                  donut_panel, nivel_badge, _pastilla, OK, AVISO, CRITICO, SERIO, NEUTRO, SERIES)
    fuentes = d.get("fuentes") or []
    leidas = sum(1 for f in fuentes if f.get("estado") == "leida")
    no_acc = sum(1 for f in fuentes if f.get("estado") == "no_accesible")
    amb = d.get("ambiguedades") or []
    contradicciones = sum(1 for a in amb if a.get("tipo") == "Contradicción")
    preg = sorted(d.get("preguntas") or [], key=lambda p: ORDEN_PRIO.get(p.get("prioridad"), 9))
    urgentes = sum(1 for p in preg if p.get("prioridad") in ("Crítica", "Alta"))
    riesgos = sorted(d.get("riesgos") or [], key=lambda r: ORDEN_RIESGO.get(r.get("nivel"), 9))
    altos = sum(1 for r in riesgos if r.get("nivel") == "Alto")
    cob = d.get("cobertura") or {}
    total, leidos = cob.get("total_items"), cob.get("leidos")
    pct_cob = (100 * leidos / total) if isinstance(leidos, (int, float)) and total else None
    jer = d.get("jerarquia") or []
    n_epicas = cob.get("epicas") if cob.get("epicas") is not None else (len(jer) or None)
    n_hist = cob.get("historias") if cob.get("historias") is not None else (sum(len(x.get("historias") or []) for x in jer) or None)
    n_tareas = cob.get("tareas")
    if n_tareas is None and jer:
        n_tareas = sum((h.get("tareas") or 0) if isinstance(h.get("tareas"), int) else len(h.get("tareas") or [])
                       for x in jer for h in x.get("historias") or []) or None
    refs = d.get("referencias") or []

    tiles = [
        ("Fuentes leídas", f"{leidas}/{len(fuentes)}" if fuentes else "—", "warn" if no_acc else ("ok" if fuentes else ""),
         f"{no_acc} no accesible(s)" if no_acc else "todas las conectadas", "lupa"),
        ("Ítems leídos en detalle", f"{leidos}" if leidos is not None else "—", "",
         f"de {total} en total" if total else "", "lista", {"pct": pct_cob} if pct_cob is not None else None),
    ]
    if n_epicas or n_hist or n_tareas:
        detalle = " · ".join(x for x in (f"{n_hist} historias" if n_hist else "", f"{n_tareas} tareas" if n_tareas else "") if x)
        tiles.append(("Backlog recorrido", f"{n_epicas or 0} épicas", "", detalle or "épicas, historias y tareas", "grid"))
    tiles += [
        ("Ambigüedades", len(amb), "warn" if amb else "ok", f"{contradicciones} contradicción(es)", "warn"),
        ("Preguntas para el equipo", len(preg), "bad" if any(p.get("prioridad") == "Crítica" for p in preg) else ("warn" if urgentes else ""),
         f"{urgentes} crítica(s) o alta(s)", "persona"),
        ("Riesgos para QA", len(riesgos), "bad" if altos else ("warn" if riesgos else "ok"), f"{altos} alto(s)", "escudo"),
    ]
    body = [kpi_tiles(tiles)]
    if d.get("tablero"):
        body.append(banner(_tr(f'Relevado desde el tablero: {d["tablero"]}', f'Surveyed from the board: {d["tablero"]}'), "ok"))
    for f in d.get("faltantes") or []:
        body.append(banner(f, "warn"))
    if d.get("resumen"):
        body.append(section("De qué se trata", f'<div class="cardbody"><p class="lead">{e(d["resumen"])}</p></div>'))
    if cob:
        texto = _tr(f'Hay {total} ítems en total; se leyeron {leidos} en detalle.',
                    f'There are {total} items in total; {leidos} were read in detail.') if total else ""
        if n_epicas or n_hist or n_tareas:
            texto += _tr(f' Se bajó por el tablero a {n_epicas or 0} épica(s), {n_hist or 0} historia(s) y {n_tareas or 0} tarea(s), con sus comentarios y links.',
                         f' The board was walked down to {n_epicas or 0} epic(s), {n_hist or 0} story(ies) and {n_tareas or 0} task(s), with their comments and links.')
        if cob.get("criterio"):
            texto += _tr(f' Criterio de la muestra: {cob["criterio"]}.', f' Sample criteria: {cob["criterio"]}.')
        if texto.strip():
            body.append(section("Qué tan representativo es", f'<div class="cardbody"><p>{e(texto.strip())}</p></div>',
                                "el resto se resume por conteos"))

    for mapa in mapas_de(d):
        body.append(section(mapa.get("titulo") or "Mapa conceptual", mapa_svg(mapa),
                            "cómo está armado / cómo funciona"))

    if cambios:
        filas = []
        for clave, nombre, campo in (("ambiguedades", "Ambigüedad", "que"), ("preguntas", "Pregunta", "pregunta")):
            for x in cambios[clave]["nuevas"]:
                filas.append([_pastilla("Nueva", AVISO, "+"), nombre, e(x.get("id", "")), e(x.get(campo))])
            for x in cambios[clave]["resueltas"]:
                filas.append([_pastilla("Resuelta", OK, "✓"), nombre, e(x.get("id", "")), e(x.get(campo))])
        sub = f'contra el relevamiento del {cambios["fecha_anterior"]}' if cambios.get("fecha_anterior") else "contra el relevamiento anterior"
        body.append(section("Cambios desde el relevamiento anterior",
                            table(["Cambio", "Qué", "ID", "Detalle"], filas) if filas else banner("Sin cambios en ambigüedades ni preguntas.", "ok"), sub))

    if fuentes:
        color = {"ok": OK, "aviso": AVISO, "falta": CRITICO}
        icono = {"ok": "✓", "aviso": "!", "falta": "✕"}
        filas = []
        for f in fuentes:
            txt, tono = ESTADO_FUENTE.get(f.get("estado"), ("—", "aviso"))
            filas.append([f'<b>{e(f.get("fuente"))}</b>', e(f.get("tipo", "")), _pastilla(txt, color[tono], icono[tono]),
                          e(f.get("alcance", "")), e(f.get("motivo", ""))])
        body.append(section("Fuentes consultadas", table(["Fuente", "Tipo", "Estado", "Qué se leyó", "Motivo / qué haría falta"], filas)))

    if jer:
        filas = []
        for grupo in jer:
            ep = grupo.get("epica") or {}
            ep_cel = _link(ep.get("url"), f'{ep.get("id", "")} {ep.get("titulo", "")}'.strip() or "—")
            hist = grupo.get("historias") or []
            if not hist:
                filas.append([f'<b>{ep_cel}</b>', e(ep.get("estado", "—")), "—", "", "", "", ""])
            for h in hist:
                tareas = h.get("tareas")
                tareas = len(tareas) if isinstance(tareas, list) else (tareas if tareas is not None else "—")
                h_cel = _link(h.get("url"), f'{h.get("id", "")} {h.get("titulo", "")}'.strip() or "—")
                links = h.get("links") or []
                links_cel = "<br>".join(_link(l) if isinstance(l, str) else _link(l.get("url"), l.get("titulo")) for l in links) or "—"
                filas.append([f'<b>{ep_cel}</b>', e(ep.get("estado", "—")), h_cel, e(h.get("responsable", "—")),
                              e(tareas), e(h.get("comentarios", "—")), f'{links_cel}'
                              + (f'<div class="muted" style="margin-top:4px">{e(h.get("nota"))}</div>' if h.get("nota") else "")])
        body.append(section("Épicas, historias y tareas", table(["Épica", "Estado", "Historia", "Responsable", "Tareas", "Comentarios", "Links / nota"], filas),
                            "lo que se recorrió bajando por el tablero"))

    if refs:
        filas = [[e(r.get("tipo", "—")), _link(r.get("url"), r.get("titulo") or r.get("url")), e(r.get("origen", "—")),
                  _pastilla("Leída", OK, "✓") if r.get("leido") else _pastilla("Pendiente", AVISO, "◷")] for r in refs]
        body.append(section("Links de referencia", table(["Tipo", "Referencia", "Viene de", "¿Leída?"], filas),
                            "páginas, diseños y documentos citados en el backlog"))

    if d.get("modulos"):
        body.append(section("Módulos del producto", table(["Módulo", "Qué hace", "Estado", "Avance", "Fuente"],
                                                          [[f'<b>{e(m.get("nombre"))}</b>', e(m.get("descripcion")), e(m.get("estado", "—")),
                                                            _avance(m.get("avance")), _fuentes(m.get("fuente"))] for m in d["modulos"]])))
    izq = section("Actores y roles de la aplicación", table(["Rol", "Qué puede hacer", "Fuente"],
                                                            [[f'<b>{e(a.get("rol"))}</b>', e(a.get("puede")), _fuentes(a.get("fuente"))]
                                                             for a in d.get("actores") or []]), ancho=6) if d.get("actores") else ""
    der = section("Flujos clave", table(["Flujo", "Pasos", "Ítems", "Fuente"],
                                        [[f'<b>{e(f.get("nombre"))}</b>', e(f.get("pasos")), f'<span class="mono">{e(f.get("items", ""))}</span>',
                                          _fuentes(f.get("fuente"))] for f in d.get("flujos") or []]), ancho=6) if d.get("flujos") else ""
    if izq and der:
        body.append(two_col(izq, der))
    elif izq or der:
        body.append(izq or der)
    if d.get("integraciones"):
        body.append(section("Integraciones con otros sistemas", table(["Sistema", "Para qué", "Tipo", "Fuente"],
                                                                     [[f'<b>{e(i.get("sistema"))}</b>', e(i.get("para_que")), e(i.get("tipo", "—")),
                                                                       _fuentes(i.get("fuente"))] for i in d["integraciones"]])))
    izq = section("Ambientes", table(["Ambiente", "URL", "Para qué", "Fuente"],
                                     [[f'<b>{e(a.get("nombre"))}</b>', f'<span class="mono">{e(a.get("url", "—"))}</span>', e(a.get("para_que", "")),
                                       _fuentes(a.get("fuente"))] for a in d.get("ambientes") or []]), ancho=6) if d.get("ambientes") else ""
    der = section("Stack y arquitectura", table(["Capa", "Tecnología", "Fuente"],
                                                [[f'<b>{e(s.get("capa"))}</b>', e(s.get("tecnologia")), _fuentes(s.get("fuente"))]
                                                 for s in d.get("stack") or []]), ancho=6) if d.get("stack") else ""
    if izq and der:
        body.append(two_col(izq, der))
    elif izq or der:
        body.append(izq or der)

    bl = d.get("backlog") or {}
    graf = []
    if bl.get("por_estado"):
        graf.append(section("Backlog por estado", bar_chart([(k, v, SERIES[i % len(SERIES)]) for i, (k, v) in enumerate(bl["por_estado"].items())]), ancho=6))
    if bl.get("bugs_por_severidad"):
        sev_color = {"Crítica": CRITICO, "Alta": SERIO, "Media": AVISO, "Baja": NEUTRO}
        graf.append(section("Bugs abiertos por severidad", bar_chart([(k, v, sev_color.get(k, NEUTRO)) for k, v in bl["bugs_por_severidad"].items()]), ancho=6))
    elif bl.get("por_tipo"):
        graf.append(section("Backlog por tipo", bar_chart([(k, v, SERIES[(i + 2) % len(SERIES)]) for i, (k, v) in enumerate(bl["por_tipo"].items())]), ancho=6))
    if len(graf) == 2:
        body.append(two_col(*graf))
    elif graf:
        body.append(graf[0])
    sp = bl.get("sprint_actual") or {}
    filas = []
    if sp:
        filas.append([f'<b>{e(sp.get("nombre", "Sprint actual"))}</b>', "Sprint / iteración actual",
                      e(" → ".join(x for x in (sp.get("inicio"), sp.get("fin")) if x) or "—"),
                      e(f'{sp["items"]} ítems' if sp.get("items") is not None else ""), "—"])
    for r in bl.get("releases") or []:
        filas.append([f'<b>{e(r.get("nombre"))}</b>', "Release", e(r.get("fecha", "—")), e(r.get("estado", "")), _fuentes(r.get("fuente"))])
    if filas:
        body.append(section("Sprint y próximas entregas", table(["Nombre", "Qué es", "Fechas", "Estado", "Fuente"], filas)))

    if amb:
        tipos = [(t, sum(1 for a in amb if a.get("tipo") == t)) for t in TIPOS_AMB]
        tipos = [(t, n) for t, n in tipos if n]
        colores = {"Contradicción": CRITICO, "Ambigüedad": AVISO, "Vacío": SERIO, "Desactualizado": NEUTRO, "Dependencia": SERIES[2]}
        filas = [[f'<span class="id">{e(a.get("id", ""))}</span>', e(a.get("tipo", "—")), e(a.get("que")), _fuentes(a.get("fuentes")),
                  nivel_badge(a.get("impacto")), f'<span class="id">{e(a.get("pregunta", ""))}</span>']
                 for a in sorted(amb, key=lambda a: (ORDEN_PRIO.get(a.get("impacto"), 9), TIPOS_AMB.index(a["tipo"]) if a.get("tipo") in TIPOS_AMB else 9))]
        panel = section("Ambigüedades por tipo", donut_panel([(n, colores.get(t, NEUTRO), t) for t, n in tipos],
                                                              round(100 * contradicciones / len(amb)), "contradicciones"), ancho=4) if tipos else ""
        tabla = section("Ambigüedades, contradicciones y vacíos", table(["ID", "Tipo", "Qué", "Fuentes", "Impacto", "Pregunta"], filas),
                        "no se elige entre fuentes: se pregunta", ancho=8 if panel else 12)
        body.append(f'{tabla}{panel}' if panel else tabla)

    if preg:
        body.append(section("Preguntas para el equipo", table(["ID", "Pregunta", "A quién", "Prioridad", "Por qué", "Relacionado"],
                                                              [[f'<span class="id">{e(p.get("id", ""))}</span>', e(p.get("pregunta")), e(p.get("a_quien", "—")),
                                                                nivel_badge(p.get("prioridad")), e(p.get("por_que", "")),
                                                                f'<span class="mono">{e(p.get("relacionado", ""))}</span>'] for p in preg]),
                            "ordenadas por prioridad"))
    if d.get("preguntas_arranque"):
        body.append(section("Preguntas de arranque", doc_list(d["preguntas_arranque"]), "lo que todo QA nuevo necesita y no está documentado"))
    if riesgos:
        body.append(section("Riesgos para QA", table(["Nivel", "Riesgo", "Motivo", "Mitigación"],
                                                     [[nivel_badge(r.get("nivel")), f'<b>{e(r.get("riesgo"))}</b>', e(r.get("motivo", "")),
                                                       e(r.get("mitigacion", ""))] for r in riesgos])))
    if d.get("equipo"):
        body.append(section("Equipo y a quién preguntar", table(["Rol", "Quién", "Temas", "Fuente"],
                                                                [[f'<b>{e(x.get("rol"))}</b>', e(x.get("nombre", "—")), e(x.get("temas", "")),
                                                                  _fuentes(x.get("fuente"))] for x in d["equipo"]])))
    if d.get("decisiones"):
        body.append(section("Decisiones registradas", table(["Fecha", "Decisión", "Quién", "Fuente"],
                                                            [[f'<span class="mono">{e(x.get("fecha", "—"))}</span>', e(x.get("decision")),
                                                              e(x.get("quien", "—")), _fuentes(x.get("fuente"))]
                                                             for x in sorted(d["decisiones"], key=lambda x: x.get("fecha") or "", reverse=True)])))
    if d.get("pruebas_hoy"):
        body.append(section("Cómo se prueba hoy", table(["Qué", "Estado", "Fuente"],
                                                        [[e(x.get("que")), e(x.get("estado", "—")), _fuentes(x.get("fuente"))] for x in d["pruebas_hoy"]])))
    if d.get("linea_de_tiempo"):
        body.append(section("Línea de tiempo", table(["Fecha", "Hito", "Fuente"],
                                                     [[f'<span class="mono">{e(x.get("fecha"))}</span>', e(x.get("hito")), _fuentes(x.get("fuente"))]
                                                      for x in sorted(d["linea_de_tiempo"], key=lambda x: x.get("fecha") or "")])))
    if d.get("glosario"):
        body.append(section("Glosario", table(["Término", "Qué significa", "Fuente"],
                                              [[f'<b>{e(g.get("termino"))}</b>', e(g.get("definicion")), _fuentes(g.get("fuente"))]
                                               for g in sorted(d["glosario"], key=lambda g: _norm(g.get("termino")))])))
    if d.get("proximos_pasos"):
        body.append(section("Próximos pasos para quien llega", table(["Paso", "Con", "Pedido de ejemplo"],
                                                                     [[e(x.get("paso")), f'<b>{e(x.get("agente", "—"))}</b>',
                                                                       f'<span class="mono">{e(x.get("pedido", ""))}</span>'] for x in d["proximos_pasos"]])))

    titulo = _tr(f'Relevamiento de {d.get("proyecto", "")}', f'Project survey: {d.get("proyecto", "")}').strip()
    html = page(titulo, "Investigación del proyecto",
                meta([("Proyecto", d.get("clave")), ("Fecha", d.get("fecha")), ("Profundidad", d.get("profundidad")),
                      ("Foco", d.get("foco")), ("Para", d.get("para"))]), "".join(body))
    return html.replace("</style>", CSS_INV + "</style>", 1)


def build_md(d, cambios=None):
    l = [f'# Relevamiento de {d.get("proyecto", "")}', ""]
    for k, v in (("Proyecto", d.get("clave")), ("Fecha", d.get("fecha")), ("Tablero", d.get("tablero")),
                 ("Profundidad", d.get("profundidad")), ("Foco", d.get("foco")), ("Para", d.get("para"))):
        if v:
            l.append(f"- **{k}:** {v}")
    l.append("")
    for f in d.get("faltantes") or []:
        l += [f"> {f}", ""]
    if d.get("resumen"):
        l += ["## De qué se trata", "", d["resumen"], ""]
    cob = d.get("cobertura") or {}
    if cob:
        recorrido = ""
        if cob.get("epicas") or cob.get("historias") or cob.get("tareas"):
            recorrido = (f' Recorrido del tablero: {cob.get("epicas", 0)} épica(s), {cob.get("historias", 0)} historia(s), '
                         f'{cob.get("tareas", 0)} tarea(s).')
        l += ["## Qué tan representativo es", "",
              f'Ítems en total: {cob.get("total_items", "—")} · leídos en detalle: {cob.get("leidos", "—")}.{recorrido} '
              f'Criterio: {cob.get("criterio", "—")}.', ""]

    def url_o_texto(url, texto=None):
        texto = texto or url or ""
        return f"[{texto}]({url})" if url and str(url).startswith("http") else texto

    def fu(x):
        return " vs. ".join(x) if isinstance(x, list) else (x or "")

    def tabla(titulo, cab, filas):
        if not filas:
            return
        l.extend([f"## {titulo}", "", "| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)])
        l.extend("| " + " | ".join(str(c if c is not None else "").replace("|", "/").replace("\n", " ") for c in f) + " |" for f in filas)
        l.append("")

    if cambios:
        filas = []
        for clave, nombre, campo in (("ambiguedades", "Ambigüedad", "que"), ("preguntas", "Pregunta", "pregunta")):
            filas += [["Nueva", nombre, x.get("id"), x.get(campo)] for x in cambios[clave]["nuevas"]]
            filas += [["Resuelta", nombre, x.get("id"), x.get(campo)] for x in cambios[clave]["resueltas"]]
        tabla("Cambios desde el relevamiento anterior", ["Cambio", "Qué", "ID", "Detalle"], filas or [["Sin cambios", "", "", ""]])
    tabla("Fuentes consultadas", ["Fuente", "Tipo", "Estado", "Qué se leyó", "Motivo"],
          [[f.get("fuente"), f.get("tipo"), ESTADO_FUENTE.get(f.get("estado"), ("",))[0], f.get("alcance"), f.get("motivo")] for f in d.get("fuentes") or []])
    filas_jer = []
    for grupo in d.get("jerarquia") or []:
        ep = grupo.get("epica") or {}
        ep_txt = url_o_texto(ep.get("url"), f'{ep.get("id", "")} {ep.get("titulo", "")}'.strip())
        hist = grupo.get("historias") or []
        if not hist:
            filas_jer.append([ep_txt, ep.get("estado"), "-", "", "", "", ""])
        for h in hist:
            tareas = h.get("tareas")
            tareas = len(tareas) if isinstance(tareas, list) else tareas
            links = h.get("links") or []
            links_txt = "; ".join(l if isinstance(l, str) else (l.get("titulo") or l.get("url") or "") for l in links)
            filas_jer.append([ep_txt, ep.get("estado"), url_o_texto(h.get("url"), f'{h.get("id", "")} {h.get("titulo", "")}'.strip()),
                              h.get("responsable"), tareas, h.get("comentarios"), (links_txt + (f' — {h.get("nota")}' if h.get("nota") else "")).strip(" —")])
    tabla("Épicas, historias y tareas", ["Épica", "Estado", "Historia", "Responsable", "Tareas", "Comentarios", "Links / nota"], filas_jer)
    tabla("Links de referencia", ["Tipo", "Referencia", "Viene de", "¿Leída?"],
          [[r.get("tipo"), url_o_texto(r.get("url"), r.get("titulo") or r.get("url")), r.get("origen"), "Sí" if r.get("leido") else "Pendiente"]
           for r in d.get("referencias") or []])

    def av(m):
        a = m.get("avance") or {}
        return f'{a["hechas"]:g}/{a["total"]:g}' if isinstance(a.get("hechas"), (int, float)) and a.get("total") else "-"

    tabla("Módulos del producto", ["Módulo", "Qué hace", "Estado", "Avance", "Fuente"],
          [[m.get("nombre"), m.get("descripcion"), m.get("estado"), av(m), fu(m.get("fuente"))] for m in d.get("modulos") or []])
    tabla("Actores y roles de la aplicación", ["Rol", "Qué puede hacer", "Fuente"], [[a.get("rol"), a.get("puede"), fu(a.get("fuente"))] for a in d.get("actores") or []])
    tabla("Flujos clave", ["Flujo", "Pasos", "Ítems", "Fuente"],
          [[f.get("nombre"), f.get("pasos"), f.get("items"), fu(f.get("fuente"))] for f in d.get("flujos") or []])
    tabla("Integraciones con otros sistemas", ["Sistema", "Para qué", "Tipo", "Fuente"],
          [[i.get("sistema"), i.get("para_que"), i.get("tipo"), fu(i.get("fuente"))] for i in d.get("integraciones") or []])
    tabla("Ambientes", ["Ambiente", "URL", "Para qué", "Fuente"],
          [[a.get("nombre"), a.get("url"), a.get("para_que"), fu(a.get("fuente"))] for a in d.get("ambientes") or []])
    tabla("Stack y arquitectura", ["Capa", "Tecnología", "Fuente"], [[s.get("capa"), s.get("tecnologia"), fu(s.get("fuente"))] for s in d.get("stack") or []])
    bl = d.get("backlog") or {}
    tabla("Backlog por estado", ["Estado", "Ítems"], list((bl.get("por_estado") or {}).items()))
    tabla("Bugs abiertos por severidad", ["Severidad", "Bugs"], list((bl.get("bugs_por_severidad") or {}).items()))
    sp = bl.get("sprint_actual") or {}
    entregas = ([[sp.get("nombre"), "Sprint actual", " -> ".join(x for x in (sp.get("inicio"), sp.get("fin")) if x), sp.get("items"), ""]] if sp else [])
    entregas += [[r.get("nombre"), "Release", r.get("fecha"), r.get("estado"), fu(r.get("fuente"))] for r in bl.get("releases") or []]
    tabla("Sprint y próximas entregas", ["Nombre", "Qué es", "Fechas", "Estado / ítems", "Fuente"], entregas)
    tabla("Ambigüedades, contradicciones y vacíos", ["ID", "Tipo", "Qué", "Fuentes", "Impacto", "Pregunta"],
          [[a.get("id"), a.get("tipo"), a.get("que"), fu(a.get("fuentes")), a.get("impacto"), a.get("pregunta")] for a in d.get("ambiguedades") or []])
    tabla("Preguntas para el equipo", ["ID", "Pregunta", "A quién", "Prioridad", "Por qué", "Relacionado"],
          [[p.get("id"), p.get("pregunta"), p.get("a_quien"), p.get("prioridad"), p.get("por_que"), p.get("relacionado")]
           for p in sorted(d.get("preguntas") or [], key=lambda p: ORDEN_PRIO.get(p.get("prioridad"), 9))])
    if d.get("preguntas_arranque"):
        l += ["## Preguntas de arranque", ""] + [f"- {p}" for p in d["preguntas_arranque"]] + [""]
    tabla("Riesgos para QA", ["Nivel", "Riesgo", "Motivo", "Mitigación"],
          [[r.get("nivel"), r.get("riesgo"), r.get("motivo"), r.get("mitigacion")]
           for r in sorted(d.get("riesgos") or [], key=lambda r: ORDEN_RIESGO.get(r.get("nivel"), 9))])
    tabla("Equipo y a quién preguntar", ["Rol", "Quién", "Temas", "Fuente"], [[x.get("rol"), x.get("nombre"), x.get("temas"), fu(x.get("fuente"))] for x in d.get("equipo") or []])
    tabla("Decisiones registradas", ["Fecha", "Decisión", "Quién", "Fuente"],
          [[x.get("fecha"), x.get("decision"), x.get("quien"), fu(x.get("fuente"))] for x in d.get("decisiones") or []])
    tabla("Cómo se prueba hoy", ["Qué", "Estado", "Fuente"], [[x.get("que"), x.get("estado"), fu(x.get("fuente"))] for x in d.get("pruebas_hoy") or []])
    tabla("Línea de tiempo", ["Fecha", "Hito", "Fuente"],
          [[x.get("fecha"), x.get("hito"), fu(x.get("fuente"))] for x in sorted(d.get("linea_de_tiempo") or [], key=lambda x: x.get("fecha") or "")])
    tabla("Glosario", ["Término", "Qué significa", "Fuente"], [[g.get("termino"), g.get("definicion"), fu(g.get("fuente"))] for g in d.get("glosario") or []])
    tabla("Próximos pasos para quien llega", ["Paso", "Con", "Pedido de ejemplo"],
          [[x.get("paso"), x.get("agente"), x.get("pedido")] for x in d.get("proximos_pasos") or []])
    return "\n".join(l)


def build_resumen_md(d):
    """Resumen breve (una carilla): qué es el proyecto, su estado y lo más urgente para un QA nuevo."""
    cob = d.get("cobertura") or {}
    preg = sorted(d.get("preguntas") or [], key=lambda p: ORDEN_PRIO.get(p.get("prioridad"), 9))
    amb = d.get("ambiguedades") or []
    bl = d.get("backlog") or {}
    l = [f'# {d.get("proyecto", "Proyecto")} — resumen', ""]
    if d.get("resumen"):
        l += [d["resumen"], ""]
    l.append("## En pocas líneas")
    puntos = []
    mods = d.get("modulos") or []
    if mods:
        puntos.append(f'**Módulos:** {", ".join(m.get("nombre", "") for m in mods[:6])}' + (" …" if len(mods) > 6 else ""))
    if cob.get("epicas") or cob.get("historias"):
        puntos.append(f'**Backlog recorrido:** {cob.get("epicas", 0)} épicas, {cob.get("historias", 0)} historias, {cob.get("tareas", 0)} tareas.')
    sp = bl.get("sprint_actual") or {}
    if sp:
        puntos.append(f'**Sprint actual:** {sp.get("nombre", "")} ({sp.get("fin", "s/f")}).')
    if bl.get("releases"):
        r = bl["releases"][0]
        puntos.append(f'**Próxima entrega:** {r.get("nombre", "")} ({r.get("fecha", "s/f")}).')
    integ = d.get("integraciones") or []
    if integ:
        puntos.append(f'**Integraciones:** {", ".join(i.get("sistema", "") for i in integ[:5])}.')
    puntos.append(f'**Hallazgos abiertos:** {len(amb)} ambigüedad(es)/contradicción(es), {len(preg)} pregunta(s) para el equipo.')
    l += [f"- {p}" for p in puntos] + [""]
    if preg:
        l += ["## Las 3 preguntas más urgentes", ""]
        for p in preg[:3]:
            l.append(f'- **[{p.get("prioridad", "")}]** {p.get("pregunta", "")}' + (f' — *a {p["a_quien"]}*' if p.get("a_quien") else ""))
        l.append("")
    l += ["---", f'Informe completo: `informe-investigacion.html` · Presentación: `presentacion-investigacion.html`'
          + (f' · Tablero: {d["tablero"]}' if d.get("tablero") else "")]
    return "\n".join(l)


def build_presentacion(d):
    """Presentación autocontenida (una diapo por tema; ←/→ para navegar; imprime a PDF, una diapo por hoja)."""
    from _estilos_reporte import e
    cob = d.get("cobertura") or {}
    amb = d.get("ambiguedades") or []
    preg = sorted(d.get("preguntas") or [], key=lambda p: ORDEN_PRIO.get(p.get("prioridad"), 9))
    riesgos = sorted(d.get("riesgos") or [], key=lambda r: ORDEN_RIESGO.get(r.get("nivel"), 9))
    bl = d.get("backlog") or {}
    slides = []

    def ul(items, n=6):
        return "<ul>" + "".join(f"<li>{x}</li>" for x in items[:n]) + "</ul>" if items else '<p class="muted">—</p>'

    # 1. Portada
    meta_bits = " · ".join(x for x in (d.get("clave"), d.get("fecha"), d.get("para")) if x)
    slides.append(f'<section class="s portada"><span class="eyebrow">Relevamiento del proyecto</span>'
                  f'<h1>{e(d.get("proyecto", "Proyecto"))}</h1>'
                  f'<p class="lead">{e(d.get("resumen", ""))}</p><p class="metal">{e(meta_bits)}</p>'
                  + (f'<p class="metal">Tablero: {e(d["tablero"])}</p>' if d.get("tablero") else "") + '</section>')
    # 2. De un vistazo (KPIs)
    kpis = [("Épicas", cob.get("epicas")), ("Historias", cob.get("historias")), ("Tareas", cob.get("tareas")),
            ("Ambigüedades", len(amb)), ("Preguntas", len(preg)), ("Riesgos", len(riesgos))]
    tiles = "".join(f'<div class="k"><div class="n">{e(v if v is not None else "—")}</div><div class="l">{e(t)}</div></div>'
                    for t, v in kpis)
    slides.append(f'<section class="s"><h2>De un vistazo</h2><div class="kpis">{tiles}</div></section>')
    # 3+. Un slide por mapa conceptual
    for mapa in mapas_de(d):
        slides.append(f'<section class="s"><h2>{e(mapa.get("titulo") or "Mapa conceptual")}</h2>{mapa_svg(mapa)}</section>')
    # Módulos
    if d.get("modulos"):
        items = [f'<b>{e(m.get("nombre"))}</b> — {e(m.get("estado", ""))}'
                 + (f' ({m["avance"]["hechas"]}/{m["avance"]["total"]})' if (m.get("avance") or {}).get("total") else "")
                 for m in d["modulos"]]
        slides.append(f'<section class="s"><h2>Módulos</h2>{ul(items, 8)}</section>')
    # Integraciones y ambientes
    izq = ul([f'<b>{e(i.get("sistema"))}</b>: {e(i.get("para_que", ""))}' for i in d.get("integraciones") or []])
    der = ul([f'<b>{e(a.get("nombre"))}</b>: {e(a.get("url", ""))}' for a in d.get("ambientes") or []])
    if d.get("integraciones") or d.get("ambientes"):
        slides.append(f'<section class="s"><h2>Integraciones y ambientes</h2><div class="dos">'
                      f'<div><h3>Integraciones</h3>{izq}</div><div><h3>Ambientes</h3>{der}</div></div></section>')
    # Ambigüedades
    if amb:
        items = [f'<b>{e(a.get("id"))}</b> ({e(_t(a.get("tipo", "")))}): {e(a.get("que", ""))}' for a in amb]
        slides.append(f'<section class="s"><h2>Ambigüedades y contradicciones</h2>{ul(items, 7)}</section>')
    # Preguntas
    if preg:
        items = [f'<b>[{e(_t(p.get("prioridad", "")))}]</b> {e(p.get("pregunta", ""))}'
                 + (f' — <i>{e(p["a_quien"])}</i>' if p.get("a_quien") else "") for p in preg]
        slides.append(f'<section class="s"><h2>Preguntas para el equipo</h2>{ul(items, 7)}</section>')
    # Riesgos + próximos pasos
    if riesgos or d.get("proximos_pasos"):
        r = ul([f'<b>[{e(_t(x.get("nivel", "")))}]</b> {e(x.get("riesgo", ""))}' for x in riesgos])
        n = ul([e(x if isinstance(x, str) else x.get("paso", "")) for x in d.get("proximos_pasos") or []])
        slides.append(f'<section class="s"><h2>Riesgos y próximos pasos</h2><div class="dos">'
                      f'<div><h3>Riesgos para QA</h3>{r}</div><div><h3>Próximos pasos</h3>{n}</div></div></section>')

    total = len(slides)
    cuerpo = "\n".join(slides)
    css = """
:root{--bg:#0E0C09;--surface:#1A1712;--tile:#221E17;--border:#2E281F;--ink:#F4EFE6;--muted:#A79F90;--accent:#F9B006}
@media print{@page{size:1280px 720px;margin:0}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif}
.deck{max-width:1280px;margin:0 auto}
.s{min-height:100vh;padding:7vh 8vw;display:flex;flex-direction:column;justify-content:center;gap:14px;border-bottom:1px solid var(--border);page-break-after:always;break-after:page}
.s h1{font-size:46px;margin:.1em 0}.s h2{font-size:30px;margin:0 0 .3em;color:var(--accent)}.s h3{font-size:16px;color:var(--muted);margin:.2em 0}
.s .eyebrow{color:var(--accent);font:600 13px/1 var(--mono,monospace);letter-spacing:.14em;text-transform:uppercase}
.s .lead{font-size:20px;color:var(--ink);max-width:48ch}.s .metal{color:var(--muted);font-size:14px;margin:2px 0}
.portada{background:radial-gradient(1200px 500px at 20% 0%,rgba(249,176,6,.10),transparent)}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;max-width:760px}
.k{background:var(--tile);border:1px solid var(--border);border-radius:14px;padding:18px 20px}
.k .n{font-size:40px;font-weight:800;color:var(--accent)}.k .l{color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.08em}
ul{margin:.2em 0;padding-left:1.1em}li{margin:.35em 0}.muted{color:var(--muted)}
.dos{display:grid;grid-template-columns:1fr 1fr;gap:28px}
.mapa{padding:0}.mapa .wrap{overflow-x:auto}.mapa svg{max-width:100%;height:auto}
.mapa .nbox{fill:var(--tile);stroke:var(--border)}.mapa .ntext{fill:var(--ink);font:600 12.5px sans-serif}
.mapa .nnota{fill:var(--muted);font:11px monospace}.mapa .edge{fill:none;stroke:var(--muted);stroke-width:1.6;opacity:.7}
.mapa .edge.back{stroke-dasharray:4 4}.mapa .elabel{fill:var(--muted);font:11px monospace}.mapa .elabel-bg{fill:var(--surface)}
.mapa .legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:10px;color:var(--muted);font-size:12px}
.mapa .legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.nav{position:fixed;right:14px;bottom:12px;background:var(--surface);border:1px solid var(--border);border-radius:999px;padding:6px 12px;color:var(--muted);font:12px monospace;z-index:9}
@media print{.nav{display:none}.s{min-height:0;height:720px}}
"""
    js = ("(function(){var s=[].slice.call(document.querySelectorAll('.s')),c=document.querySelector('.nav b');"
          "function upd(){var i=0,y=window.scrollY+innerHeight/2;s.forEach(function(el,k){if(el.offsetTop<=y)i=k;});"
          "if(c)c.textContent=(i+1);}window.addEventListener('scroll',upd);"
          "document.addEventListener('keydown',function(ev){var i=s.findIndex(function(el){return el.getBoundingClientRect().top>=-2;});"
          "if(ev.key==='ArrowRight'||ev.key===' '||ev.key==='PageDown'){ev.preventDefault();(s[Math.min(i+1,s.length-1)]||s[0]).scrollIntoView({behavior:'smooth'});}"
          "if(ev.key==='ArrowLeft'||ev.key==='PageUp'){ev.preventDefault();(s[Math.max((i<0?s.length:i)-1,0)]).scrollIntoView({behavior:'smooth'});}});upd();})();")
    from _i18n import idioma_actual, traducir_html
    lang = idioma_actual()
    otro = "en" if lang == "es" else "es"
    # Link al otro idioma (presentacion-investigacion.html <-> presentacion-investigacion.en.html).
    css += ".nav a{color:var(--accent);text-decoration:none;margin-left:8px}"
    js += (r"(function(){var a=document.querySelector('.nav a[data-idioma]');if(!a)return;"
           r"var f=decodeURIComponent(location.pathname.split('/').pop()||'');"
           r"a.href=encodeURIComponent(a.getAttribute('data-idioma')==='en'?f.replace(/\.html$/i,'.en.html'):f.replace(/\.en\.html$/i,'.html'));})();")
    documento = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
                 f'<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="dark">'
                 f'<title>{e(d.get("proyecto", "Proyecto"))} — {_tr("presentación", "presentation")}</title><style>{css}</style></head>'
                 f'<body><div class="deck">{cuerpo}</div><div class="nav"><b>1</b> / {total} · ←/→ · imprimí a PDF</div>'
                 f'<script>{js}</script></body></html>\n')
    documento = traducir_html(documento, lang)
    enlace = f'<a href="#" data-idioma="{otro}" lang="{otro}">{"English" if otro == "en" else "Español"}</a>'
    return documento.replace('</div><script>', f'{enlace}</div><script>', 1)


def anterior(carpeta):
    """El relevamiento más reciente guardado en historial/ (o None)."""
    hist = Path(carpeta) / "historial"
    if not hist.is_dir():
        return None
    for sub in sorted((p for p in hist.iterdir() if p.is_dir()), reverse=True):
        archivo = sub / "investigacion.json"
        if archivo.exists():
            try:
                return json.loads(archivo.read_text(encoding="utf-8"))
            except ValueError:
                continue
    return None


def guardar_historial(carpeta, archivos, maximo=MAX_HISTORIAL):
    """Copia este relevamiento a historial/<fecha-hora>/ y deja los últimos `maximo`."""
    hist = Path(carpeta) / "historial"
    destino = hist / datetime.now().strftime("%Y-%m-%d-%H%M%S")
    destino.mkdir(parents=True, exist_ok=True)
    for a in archivos:
        if Path(a).exists():
            shutil.copy2(a, destino / Path(a).name)
    for viejo in sorted((p for p in hist.iterdir() if p.is_dir()), reverse=True)[maximo:]:
        shutil.rmtree(viejo, ignore_errors=True)
    return destino


# ------------------------------------------------------------------ conocimiento para los demás agentes

def _celda(v):
    if isinstance(v, (list, tuple)):
        v = ", ".join(str(x) for x in v)
    return " ".join(str(v if v is not None else "").split()).replace("|", "/") or "-"


def _tabla(cab, filas):
    if not filas:
        return ""
    out = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    out += ["| " + " | ".join(_celda(c) for c in f) + " |" for f in filas]
    return "\n".join(out) + "\n"


def _seccion(titulo, cuerpo):
    return f"## {titulo}\n\n{cuerpo}\n" if cuerpo and cuerpo.strip() else ""


def exportar_a_input(d, carpeta):
    """Escribe lo relevado como documentación del proyecto en <carpeta> (input/documentacion/proyecto/investigacion/),
    con el encabezado del índice, para que investigacion-contexto lo use al analizar historias y escribir casos.
    Todo sale de tickets, wiki y comentarios: va como estado `investigacion` (y las dudas, `sin-confirmar`), nunca
    como comportamiento verificado de la aplicación. Devuelve las rutas escritas."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    from indice_documentacion import escribir_documento
    carpeta = Path(carpeta)
    fecha = d.get("fecha") or datetime.now().date().isoformat()
    proyecto = d.get("proyecto")
    fuentes = ", ".join(x for x in [d.get("clave"), d.get("tablero")] if x) or proyecto
    aviso = (f"> Relevado por el `investigador-proyecto` el {fecha} desde tickets, wiki y comentarios (no verificado en la "
             "aplicación). Cada dato cita su fuente: ante una duda, volvé a la fuente. El informe completo está en "
             f"`output/investigacion/`.\n\n")
    escritos = []

    def doc(nombre, titulo, cuerpo, estado="investigacion"):
        if cuerpo.strip():
            escritos.append(escribir_documento(carpeta / nombre, f"{titulo} — {proyecto}", "investigacion",
                                               f"# {titulo}\n\n{aviso}{cuerpo}", fuentes=fuentes, estado=estado, actualizado=fecha))

    cob = d.get("cobertura") or {}
    fuentes_t = _tabla(["Fuente", "Tipo", "Alcance", "Estado", "Motivo"],
                       [[f.get("fuente"), f.get("tipo"), f.get("alcance"), f.get("estado"), f.get("motivo")] for f in d.get("fuentes") or []])
    doc("resumen.md", "Resumen del proyecto",
        (f"{d['resumen']}\n\n" if d.get("resumen") else "")
        + (f"Cobertura: {cob.get('leidos', '?')} de {cob.get('total_items', '?')} ítems leídos en detalle"
           + (f" ({cob['criterio']})" if cob.get("criterio") else "") + ".\n\n" if cob else "")
        + _seccion("Ambientes", _tabla(["Ambiente", "URL", "Para qué", "Fuente"],
                                       [[a.get("nombre"), a.get("url"), a.get("para_que"), a.get("fuente")] for a in d.get("ambientes") or []]))
        + _seccion("Stack", _tabla(["Capa", "Tecnología", "Fuente"], [[s.get("capa"), s.get("tecnologia"), s.get("fuente")] for s in d.get("stack") or []]))
        + _seccion("Equipo (a quién preguntar)", _tabla(["Rol", "Nombre", "Temas", "Fuente"],
                   [[e_.get("rol"), e_.get("nombre"), e_.get("temas"), e_.get("fuente")] for e_ in d.get("equipo") or []]))
        + _seccion("Fuentes consultadas", fuentes_t)
        + _seccion("Fuentes que no se pudieron leer", "\n".join(f"- {x}" for x in d.get("faltantes") or [])))

    doc("modulos-y-flujos.md", "Módulos, actores, flujos e integraciones",
        _seccion("Módulos", _tabla(["Módulo", "Descripción", "Estado", "Avance", "Fuente"],
                 [[m.get("nombre"), m.get("descripcion"), m.get("estado"),
                   f"{(m.get('avance') or {}).get('hechas', '?')}/{(m.get('avance') or {}).get('total', '?')}" if m.get("avance") else "-",
                   m.get("fuente")] for m in d.get("modulos") or []]))
        + _seccion("Actores y roles", _tabla(["Rol", "Qué puede hacer", "Fuente"], [[a.get("rol"), a.get("puede"), a.get("fuente")] for a in d.get("actores") or []]))
        + _seccion("Flujos", _tabla(["Flujo", "Pasos", "Ítems", "Fuente"],
                   [[f.get("nombre"), f.get("pasos"), f.get("items"), f.get("fuente")] for f in d.get("flujos") or []]))
        + _seccion("Integraciones", _tabla(["Sistema", "Para qué", "Tipo", "Fuente"],
                   [[i.get("sistema"), i.get("para_que"), i.get("tipo"), i.get("fuente")] for i in d.get("integraciones") or []])))

    jer = []
    for rama in d.get("jerarquia") or []:
        ep = rama.get("epica") or {}
        jer.append(f"### {ep.get('id', '')} {ep.get('titulo', '')}".rstrip() + (f" ({ep['estado']})" if ep.get("estado") else ""))
        jer.append("")
        hs = rama.get("historias") or []
        if hs:
            jer.append(_tabla(["Historia", "Título", "Estado", "Responsable", "Tareas", "Comentarios", "Links", "Nota"],
                              [[h.get("id"), h.get("titulo"), h.get("estado"), h.get("responsable"), h.get("tareas"),
                                h.get("comentarios"), h.get("links"), h.get("nota")] for h in hs]))
    bk = d.get("backlog") or {}
    releases = _tabla(["Release", "Fecha", "Estado", "Fuente"], [[r.get("nombre"), r.get("fecha"), r.get("estado"), r.get("fuente")]
                                                                  for r in bk.get("releases") or []])
    sprint = bk.get("sprint_actual") or {}
    doc("backlog.md", "Épicas, historias y releases",
        _seccion("Épicas e historias recorridas", "\n".join(jer))
        + (f"Sprint actual: {sprint.get('nombre')} ({sprint.get('inicio')} a {sprint.get('fin')}, {sprint.get('items', '?')} ítems).\n\n" if sprint else "")
        + _seccion("Releases", releases)
        + _seccion("Cómo se prueba hoy", _tabla(["Qué", "Estado", "Fuente"], [[p.get("que"), p.get("estado"), p.get("fuente")] for p in d.get("pruebas_hoy") or []])))

    doc("decisiones-y-glosario.md", "Decisiones, glosario y referencias",
        _seccion("Decisiones", _tabla(["Fecha", "Decisión", "Quién", "Fuente"],
                 [[x.get("fecha"), x.get("decision"), x.get("quien"), x.get("fuente")] for x in d.get("decisiones") or []]))
        + _seccion("Glosario", _tabla(["Término", "Definición", "Fuente"], [[g.get("termino"), g.get("definicion"), g.get("fuente")] for g in d.get("glosario") or []]))
        + _seccion("Línea de tiempo", _tabla(["Fecha", "Hito", "Fuente"], [[t.get("fecha"), t.get("hito"), t.get("fuente")] for t in d.get("linea_de_tiempo") or []]))
        + _seccion("Referencias (links)", _tabla(["Tipo", "Título", "URL", "Dónde apareció", "Leído"],
                   [[r.get("tipo"), r.get("titulo"), r.get("url"), r.get("origen"), "Sí" if r.get("leido") else "No"] for r in d.get("referencias") or []])))

    doc("dudas-y-riesgos.md", "Ambigüedades, preguntas abiertas y riesgos",
        "Esto **no** son reglas: son dudas y contradicciones entre fuentes. Al escribir casos, cada una va como "
        "`Falta información` (`FI-XX`) con su pregunta, no como resultado esperado.\n\n"
        + _seccion("Ambigüedades y contradicciones", _tabla(["ID", "Tipo", "Qué", "Fuentes", "Impacto", "Pregunta"],
                   [[a.get("id"), a.get("tipo"), a.get("que"), a.get("fuentes"), a.get("impacto"), a.get("pregunta")] for a in d.get("ambiguedades") or []]))
        + _seccion("Preguntas para el equipo", _tabla(["ID", "Pregunta", "A quién", "Prioridad", "Relacionado"],
                   [[p.get("id"), p.get("pregunta"), p.get("a_quien"), p.get("prioridad"), p.get("relacionado")] for p in d.get("preguntas") or []]))
        + _seccion("Riesgos para QA", _tabla(["Riesgo", "Nivel", "Motivo", "Mitigación"],
                   [[r.get("riesgo"), r.get("nivel"), r.get("motivo"), r.get("mitigacion")] for r in d.get("riesgos") or []])),
        estado="sin-confirmar")
    return escritos


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe del relevamiento de un proyecto (agente investigador-proyecto)")
    ap.add_argument("investigacion_json")
    ap.add_argument("--salida", help="carpeta de salida (por defecto, la del JSON)")
    ap.add_argument("--sin-historial", action="store_true", help="no guarda la copia en historial/ ni compara")
    ap.add_argument("--input", default=str(RAIZ / "input" / "documentacion"),
                    help="carpeta de la documentación del proyecto donde se deja lo relevado (por defecto input/documentacion)")
    ap.add_argument("--sin-input", action="store_true", help="no deja lo relevado en input/documentacion/")
    a = ap.parse_args(argv)
    origen = Path(a.investigacion_json)
    d = json.loads(origen.read_text(encoding="utf-8"))
    if not d.get("proyecto"):
        ap.error('el JSON necesita "proyecto"')
    validar(d)
    carpeta = Path(a.salida) if a.salida else origen.resolve().parent
    carpeta.mkdir(parents=True, exist_ok=True)
    cambios = None if a.sin_historial else comparar(d, anterior(carpeta))
    from _i18n import escribir_bilingue, localizar, ruta_en
    html = carpeta / "informe-investigacion.html"
    escribir_bilingue(html, lambda: build_html(localizar(d), cambios))
    md = carpeta / "informe-investigacion.md"
    md.write_text(build_md(d, cambios), encoding="utf-8")
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "formatear_tablas.py"), str(md)], capture_output=True, text=True)
    resumen = carpeta / "resumen.md"
    resumen.write_text(build_resumen_md(d), encoding="utf-8")
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "formatear_tablas.py"), str(resumen)], capture_output=True, text=True)
    presentacion = carpeta / "presentacion-investigacion.html"
    escribir_bilingue(presentacion, lambda: build_presentacion(localizar(d)))
    if not a.sin_historial:
        guardar_historial(carpeta, [origen, html, ruta_en(html), md, resumen, presentacion, ruta_en(presentacion)])
    print(f"Relevamiento: {html}")
    print(f"  resumen breve: {resumen}")
    print(f"  presentación (imprime a PDF): {presentacion}")
    print(f"  Markdown completo: {md}")
    if not a.sin_input:
        destino = Path(a.input) / "proyecto" / "investigacion"
        escritos = exportar_a_input(d, destino)
        import indice_documentacion
        indice_documentacion.main(["--carpeta", str(a.input)])
        print(f"  contexto para los demás agentes: {len(escritos)} documento(s) en {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Sistema de diseño de los reportes HTML de k0lmenIA (dashboard moderno, modo oscuro).

Lo usan todos los generadores de entregables HTML (plan de pruebas, reporte de ejecución,
informe de cierre, performance y seguridad), así todos se ven igual y el tema vive en un
solo lugar.

Página y estructura
  page(titulo, eyebrow, meta_html, body)    documento completo (marca, tooltips, pie)
  meta(items)                               chips de contexto (Historia, Fecha, …)
  section(titulo, body_html, sub="")        sección con título y tarjeta
  banner(texto, tono)                       veredicto destacado (ok | warn | bad)
  kpi_tiles(items)                          indicadores (etiqueta, valor, tono[, detalle])
  two_col(izq, der)                         grilla de dos columnas
  table(headers, rows)                      tabla (las celdas pueden traer HTML)
  doc_list(items)                           lista con viñetas
  nivel_badge(nivel) / estado_pill(estado)  pastillas con ícono + texto (nunca solo color)
  legend(items)                             leyenda (nombre, color[, valor])

Gráficos (SVG inline, con tooltip al pasar el mouse)
  donut(segments, pct, label)               dona: segments = [(valor, color[, nombre])]
  bar_chart(rows)                           barras horizontales: [(etiqueta, valor, color)]
  stacked_bars(filas, series)               barras apiladas: filas = [(etiqueta, [v1, v2…])]
  grouped_columns(grupos, series, fmt)      columnas agrupadas, un solo eje
  line_chart(x, series, fmt)                líneas sobre un eje, con crosshair

Colores: paleta categórica y de estado validadas para la superficie oscura (CVD y contraste;
skill dataviz). Sin dependencias externas: CSS, SVG y JS van inline, no usa internet.
"""
import html
import math

# ------------------------------------------------------------------ tokens
SUPERFICIE = "#161B22"
# Categórica (orden fijo, nunca ciclado): azul, naranja, aqua, amarillo, magenta, verde, violeta, rojo
SERIES = ["#3987E5", "#D95926", "#199E70", "#C98500", "#D55181", "#008300", "#9085E9", "#E66767"]
# Estado (reservados: nunca se usan como "serie 4")
OK, AVISO, SERIO, CRITICO, NEUTRO = "#0CA30C", "#FAB219", "#EC835A", "#D03B3B", "#8B949E"

PALETA = {"bg": "#0D1117", "surface": SUPERFICIE, "tile": "#1C2330", "border": "#283040",
          "ink": "#E8ECF2", "body": "#B4BCC8", "muted": "#7D8693",
          "ok": OK, "bad": CRITICO, "blk": NEUTRO, "warn": AVISO}

# Niveles / severidades → escala de estado (con su ícono y texto, nunca solo color)
NIVEL_COLOR = {"Alto": CRITICO, "Crítica": CRITICO, "Alta": SERIO, "Medio": AVISO, "Media": AVISO,
               "Bajo": NEUTRO, "Baja": NEUTRO}
NIVEL_ICONO = {"Alto": "▲", "Crítica": "▲", "Alta": "▲", "Medio": "●", "Media": "●", "Bajo": "▼", "Baja": "▼"}
ESTADO_COLOR = {"Aprobado": OK, "Fallido": CRITICO, "Bloqueado": NEUTRO, "Pendiente": AVISO, "N/A": NEUTRO,
                "En ejecución": SERIES[0]}
ESTADO_ICONO = {"Aprobado": "✓", "Fallido": "✕", "Bloqueado": "⊘", "Pendiente": "◷", "N/A": "–", "En ejecución": "▶"}


def _soft(hexcolor, alfa=0.16):
    h = hexcolor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alfa})"


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  color-scheme:dark;
  --bg:#0D1117; --surface:#161B22; --tile:#1C2330; --border:#283040; --border-soft:#202836;
  --ink:#E8ECF2; --body:#B4BCC8; --muted:#7D8693; --accent:#3987E5;
  --ok:#0CA30C; --warn:#FAB219; --serious:#EC835A; --bad:#D03B3B; --neutral:#8B949E;
  --radius:16px;
}
html{-webkit-text-size-adjust:100%}
body{
  background:radial-gradient(1200px 500px at 15% -10%,rgba(57,135,229,.16),transparent 60%),
             radial-gradient(900px 400px at 100% 0%,rgba(144,133,233,.10),transparent 55%),var(--bg);
  background-attachment:fixed;color:var(--ink);
  font-family:"Inter","Segoe UI Variable","Segoe UI",system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif;
  line-height:1.55;padding:44px 20px 56px;font-feature-settings:"tnum" 1;
}
.wrap{max-width:1040px;margin:0 auto}
.mono{font-family:"JetBrains Mono","Cascadia Code",ui-monospace,Consolas,monospace;font-size:.92em}
.muted{color:var(--muted)}
.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.14em;font-weight:650;color:var(--muted)}
a{color:#7DB3F0}

/* encabezado */
header{margin-bottom:28px}
.brand{display:inline-flex;align-items:center;gap:8px;margin-bottom:16px;padding:5px 12px 5px 8px;
  border:1px solid var(--border);border-radius:999px;background:rgba(22,27,34,.7);backdrop-filter:blur(6px)}
.brand .dot{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:12px;
  background:linear-gradient(135deg,#3987E5,#9085E9)}
h1{font-size:32px;font-weight:750;letter-spacing:-.025em;line-height:1.12;color:var(--ink)}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;color:var(--body);
  background:var(--tile);border:1px solid var(--border);border-radius:999px;padding:5px 12px}
.chip .k{color:var(--muted)}
.chip a{color:var(--body);text-decoration:none;border-bottom:1px dashed var(--border)}

/* tarjetas y secciones */
.card{background:linear-gradient(180deg,rgba(255,255,255,.025),transparent 120px),var(--surface);
  border:1px solid var(--border);border-radius:var(--radius);box-shadow:0 1px 0 rgba(255,255,255,.03) inset,0 12px 32px -18px rgba(0,0,0,.7)}
.section{margin-top:30px}
.section-title{display:flex;align-items:baseline;gap:10px;margin:0 2px 12px}
.section-title h2{font-size:17px;font-weight:680;letter-spacing:-.01em;color:var(--ink)}
.section-title .sub{font-size:12.5px;color:var(--muted)}
.cardbody{padding:20px 24px;color:var(--body)}
.cardbody p{color:var(--body)}
.cardbody p+p{margin-top:10px}
.lead{font-size:15.5px;color:var(--ink);line-height:1.6}
.subhead{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-weight:650;margin-bottom:10px}
.subhead.ok{color:#5BD25B}.subhead.bad{color:#F07272}.subhead.warn{color:#F5C451}

/* hero: dona + indicadores */
.hero{display:grid;grid-template-columns:230px 1fr;gap:26px;align-items:center;padding:26px}
.gauge{display:flex;flex-direction:column;align-items:center;gap:12px}
.donut-num{font-size:34px;font-weight:750;fill:var(--ink)}
.donut-lbl{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;fill:var(--muted);font-weight:650}

/* leyenda */
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:var(--body)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px}
.legend b{color:var(--ink);font-weight:650}

/* indicadores */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.kpi{position:relative;padding:16px 16px 14px;border:1px solid var(--border);border-radius:14px;background:var(--tile);overflow:hidden}
.kpi::before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:var(--border)}
.kpi .n{font-size:28px;font-weight:750;letter-spacing:-.02em;line-height:1.05;color:var(--ink)}
.kpi .l{font-size:12px;color:var(--muted);margin-top:7px;display:flex;align-items:center;gap:6px}
.kpi .d{font-size:11.5px;color:var(--body);margin-top:3px}
.kpi.ok::before{background:var(--ok)} .kpi.bad::before{background:var(--bad)}
.kpi.warn::before{background:var(--warn)} .kpi.blk::before{background:var(--neutral)}
.kpi .ic{font-size:11px;width:16px;height:16px;border-radius:50%;display:inline-grid;place-items:center;color:#0D1117;font-weight:800}
.kpi.ok .ic{background:var(--ok)}.kpi.bad .ic{background:var(--bad)}.kpi.warn .ic{background:var(--warn)}.kpi.blk .ic{background:var(--neutral)}

/* gráficos */
.chart{padding:20px 24px 16px}
.chart svg{width:100%;height:auto;display:block;overflow:visible}
.chart .legend{margin-top:12px}
.axis{font-size:11px;fill:var(--muted)}
.lbl{font-size:12px;fill:var(--body)}
.val{font-size:12px;fill:var(--ink);font-weight:600}
.grid{stroke:var(--border-soft);stroke-width:1}
.base{stroke:var(--border);stroke-width:1}
.mark{transition:opacity .15s}
svg:hover .mark{opacity:.55} svg .mark:hover{opacity:1}
.hit rect{fill:transparent}
.hit .cross{stroke:var(--muted);stroke-width:1;stroke-dasharray:3 3;opacity:0}
.hit:hover .cross{opacity:1}
.hit circle{opacity:0}.hit:hover circle{opacity:1}

/* barras horizontales */
.bars{padding:20px 24px;display:flex;flex-direction:column;gap:12px}
.bar-row{display:grid;grid-template-columns:var(--lw,110px) 1fr 48px;align-items:center;gap:12px}
.bar-label{font-size:13px;color:var(--body);display:flex;align-items:center;gap:7px;min-width:0}
.bar-label span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-track{height:12px;border-radius:0 4px 4px 0;background:rgba(255,255,255,.04);display:flex;gap:2px;overflow:hidden}
.bar-track .seg{height:100%;display:block}
.bar-track .seg:last-child{border-radius:0 4px 4px 0}
.bar-count{font-size:13px;color:var(--ink);text-align:right;font-weight:600}

/* tablas */
.tablecard{padding:8px 6px 6px;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13.5px}
thead th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);
  font-weight:650;padding:12px 14px 10px;white-space:nowrap}
tbody td{padding:12px 14px;border-top:1px solid var(--border-soft);color:var(--body);vertical-align:top}
tbody tr:hover td{background:rgba(255,255,255,.025)}
td .id{font-weight:650;color:var(--ink);white-space:nowrap}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:650;padding:3px 10px;border-radius:999px;white-space:nowrap}

/* banner de veredicto */
.banner{display:flex;align-items:center;gap:12px;padding:16px 20px;border-radius:14px;border:1px solid var(--border);font-weight:650;font-size:15.5px}
.banner .bic{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-size:14px;color:#0D1117;font-weight:800;flex:none}
.banner.ok{background:linear-gradient(90deg,rgba(12,163,12,.16),rgba(12,163,12,.04));border-color:rgba(12,163,12,.45);color:#7BE07B}
.banner.ok .bic{background:var(--ok)}
.banner.bad{background:linear-gradient(90deg,rgba(208,59,59,.18),rgba(208,59,59,.04));border-color:rgba(208,59,59,.5);color:#F59A9A}
.banner.bad .bic{background:var(--bad)}
.banner.warn{background:linear-gradient(90deg,rgba(250,178,25,.15),rgba(250,178,25,.03));border-color:rgba(250,178,25,.45);color:#F7CD6E}
.banner.warn .bic{background:var(--warn)}

.doclist{list-style:none;display:flex;flex-direction:column;gap:9px}
.doclist li{position:relative;padding-left:20px;color:var(--body)}
.doclist li::before{content:"";position:absolute;left:3px;top:9px;width:7px;height:7px;border-radius:2px;background:var(--accent);opacity:.8}
.twocol{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:30px}
.section .twocol{margin-top:0}
.twocol>.section{margin-top:0}

/* tooltip */
#tip{position:fixed;z-index:10;pointer-events:none;opacity:0;transform:translateY(4px);transition:opacity .12s,transform .12s;
  background:#0B0F15;border:1px solid var(--border);border-radius:10px;padding:8px 11px;font-size:12.5px;color:var(--ink);
  box-shadow:0 10px 28px rgba(0,0,0,.55);max-width:300px;white-space:pre-line}
#tip.on{opacity:1;transform:none}

footer{margin-top:36px;display:flex;justify-content:center;gap:8px;font-size:12px;color:var(--muted)}

@media (max-width:760px){
  body{padding:26px 14px 40px}
  .hero{grid-template-columns:1fr}
  .kpis{grid-template-columns:repeat(2,1fr)}
  .twocol{grid-template-columns:1fr}
  .bar-row{grid-template-columns:84px 1fr 40px}
  h1{font-size:25px}
}
@media print{body{background:var(--bg);padding:16px}.card{box-shadow:none}#tip{display:none}}
"""

# Tooltip: cualquier elemento con data-tip lo muestra al pasar el mouse o con foco (teclado).
JS = """
(function(){var t=document.createElement('div');t.id='tip';document.body.appendChild(t);
function show(e){var el=e.target.closest('[data-tip]');if(!el){t.className='';return;}
t.textContent=el.getAttribute('data-tip');t.className='on';var x=e.clientX||el.getBoundingClientRect().left,y=e.clientY||el.getBoundingClientRect().top;
var w=t.offsetWidth,h=t.offsetHeight;t.style.left=Math.min(x+14,innerWidth-w-8)+'px';t.style.top=(y-h-12<4?y+16:y-h-12)+'px';}
document.addEventListener('mousemove',show);document.addEventListener('focusin',show);
document.addEventListener('mouseleave',function(){t.className='';});})();
"""


def e(s):
    return html.escape(str(s if s is not None else ""))


def page(titulo, eyebrow, meta_html, body):
    return (f'<!doctype html>\n<html lang="es"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="color-scheme" content="dark">'
            f'<title>{e(titulo)} — k0lmenIA</title><style>{CSS}</style></head>'
            f'<body><div class="wrap"><header>'
            f'<span class="brand"><span class="dot">🪖</span>'
            f'<span class="eyebrow">k0lmenIA · {e(eyebrow)}</span></span>'
            f'<h1>{e(titulo)}</h1>{meta_html}</header>{body}'
            f'<footer><span>Generado por k0lmenIA</span></footer></div>'
            f'<script>{JS}</script></body></html>\n')


def meta(items):
    """items: lista de (clave, valor); ignora valores vacíos."""
    parts = [f'<span class="chip"><span class="k">{e(k)}</span> {e(v)}</span>' for k, v in items if v]
    return f'<div class="meta">{"".join(parts)}</div>' if parts else ""


def section(titulo, body_html, sub=""):
    s = f'<span class="sub">{e(sub)}</span>' if sub else ""
    return (f'<div class="section"><div class="section-title"><h2>{e(titulo)}</h2>{s}</div>'
            f'<div class="card">{body_html}</div></div>')


ICONO_TONO = {"ok": "✓", "bad": "✕", "warn": "!", "blk": "⊘"}


def kpi_tiles(items):
    """items: (etiqueta, valor, tono[, detalle]). tono: '' | 'ok' | 'bad' | 'blk' | 'warn'."""
    out = ""
    for it in items:
        label, val, tono = it[0], it[1], it[2]
        detalle = it[3] if len(it) > 3 else ""
        ic = f'<span class="ic">{ICONO_TONO[tono]}</span>' if tono in ICONO_TONO else ""
        d = f'<div class="d">{e(detalle)}</div>' if detalle else ""
        out += f'<div class="kpi {tono}"><div class="n">{e(val)}</div><div class="l">{ic}{e(label)}</div>{d}</div>'
    return f'<div class="kpis">{out}</div>'


def legend(items):
    """items: (nombre, color[, valor])."""
    parts = []
    for it in items:
        valor = f' <b>{e(it[2])}</b>' if len(it) > 2 else ""
        parts.append(f'<span><i style="background:{it[1]}"></i>{e(it[0])}{valor}</span>')
    return f'<div class="legend">{"".join(parts)}</div>'


def banner(texto, tono="ok"):
    return f'<div class="banner {tono}"><span class="bic">{ICONO_TONO.get(tono, "i")}</span>{e(texto)}</div>'


def doc_list(items):
    if not items:
        return '<div class="cardbody"><p class="muted">—</p></div>'
    lis = "".join(f'<li>{e(it)}</li>' for it in items)
    return f'<div class="cardbody"><ul class="doclist">{lis}</ul></div>'


def two_col(izq, der):
    return f'<div class="twocol">{izq}{der}</div>'


def table(headers, rows):
    """headers: lista de strings. rows: lista de listas; cada celda puede traer HTML."""
    th = "".join(f'<th>{e(h)}</th>' for h in headers)
    trs = "".join("<tr>" + "".join(f'<td>{c}</td>' for c in row) + "</tr>" for row in rows)
    return f'<div class="tablecard"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def _pastilla(texto, color, icono):
    return (f'<span class="pill" style="background:{_soft(color)};color:var(--ink);box-shadow:inset 0 0 0 1px {_soft(color, .45)}">'
            f'<span style="color:{color}">{icono}</span>{e(texto)}</span>')


def nivel_badge(nivel):
    n = (nivel or "").strip()
    return _pastilla(n or "—", NIVEL_COLOR.get(n, NEUTRO), NIVEL_ICONO.get(n, "●"))


def estado_pill(estado):
    s = (estado or "").strip()
    return _pastilla(s or "—", ESTADO_COLOR.get(s, NEUTRO), ESTADO_ICONO.get(s, "●"))


# ------------------------------------------------------------------ gráficos
def _num(v, fmt=None):
    if v is None:
        return "—"
    if fmt:
        return fmt(v)
    return f"{v:,.0f}".replace(",", ".") if float(v).is_integer() else f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _escala(maxv):
    """Máximo "redondo" y paso para 4-5 líneas de grilla."""
    if maxv <= 0:
        return 1, 0.25
    exp = 10 ** math.floor(math.log10(maxv))
    for m in (1, 2, 2.5, 5, 10):
        paso = m * exp / 4
        if paso * 4 >= maxv:
            return paso * 4, paso
    return maxv, maxv / 4


def _barra_vertical(x, y_base, ancho, alto, color, tip):
    """Columna con el extremo de datos redondeado (4px) y la base recta."""
    r = min(4, ancho / 2, alto)
    if alto <= 0:
        return ""
    y = y_base - alto
    d = (f"M{x:.1f},{y_base:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
         f"H{x + ancho - r:.1f} Q{x + ancho:.1f},{y:.1f} {x + ancho:.1f},{y + r:.1f} V{y_base:.1f} Z")
    return f'<path class="mark" d="{d}" fill="{color}" data-tip="{e(tip)}" tabindex="0"/>'


def donut(segments, pct, label="aprobados"):
    """segments: [(valor, color[, nombre])]. El centro muestra pct + label."""
    r, cx, cy, w = 70, 95, 95, 18
    C = 2 * math.pi * r
    total = sum(s[0] for s in segments) or 1
    track = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#202836" stroke-width="{w}"/>'
    segs, acc = "", 0.0
    gap = 2.5 if sum(1 for s in segments if s[0]) > 1 else 0
    for s in segments:
        valor, color = s[0], s[1]
        if not valor:
            continue
        nombre = s[2] if len(s) > 2 else ""
        frac = valor / total
        dash = max(frac * C - gap, 0.1)
        tip = f"{nombre}: {valor} ({frac * 100:.0f} %)" if nombre else f"{valor} ({frac * 100:.0f} %)"
        segs += (f'<circle class="mark" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{w}" '
                 f'stroke-dasharray="{dash:.2f} {C - dash:.2f}" stroke-dashoffset="{-acc * C:.2f}" '
                 f'transform="rotate(-90 {cx} {cy})" data-tip="{e(tip)}" tabindex="0"/>')
        acc += frac
    return (f'<svg viewBox="0 0 190 190" width="190" height="190" role="img" '
            f'aria-label="{pct} por ciento {e(label)}">{track}{segs}'
            f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" class="donut-num">{pct}%</text>'
            f'<text x="{cx}" y="{cy + 24}" text-anchor="middle" class="donut-lbl">{e(label)}</text></svg>')


def bar_chart(rows, ancho_etiqueta=110):
    """rows: [(etiqueta, valor, color)]. Barras horizontales normalizadas al máximo.
    ancho_etiqueta: ancho de la columna de etiquetas en px (más ancho para nombres largos)."""
    rows = list(rows)
    maxv = max((c for _, c, _ in rows), default=0)
    if not rows or maxv == 0:
        return '<div class="cardbody"><p class="muted">Sin datos.</p></div>'
    out = ""
    for label, count, color in rows:
        ancho = count / maxv * 100
        seg = f'<span class="seg" style="width:100%;background:{color}"></span>' if count else ""
        out += (f'<div class="bar-row" data-tip="{e(label)}: {e(count)}"><div class="bar-label"><span>{e(label)}</span></div>'
                f'<div><div class="bar-track" style="width:{max(ancho, 0.5 if count else 0):.1f}%">{seg}</div></div>'
                f'<div class="bar-count">{e(count)}</div></div>')
    return f'<div class="bars" style="--lw:{ancho_etiqueta}px">{out}</div>'


def stacked_bars(filas, series):
    """filas: [(etiqueta, [valor por serie])]; series: [(nombre, color)]. Barras horizontales
    apiladas, con 2px de separación entre segmentos y largo proporcional al total."""
    filas = [f for f in filas if sum(f[1])]
    if not filas:
        return '<div class="cardbody"><p class="muted">Sin datos.</p></div>'
    maxt = max(sum(v) for _, v in filas)
    out = ""
    for etiqueta, valores in filas:
        tot = sum(valores)
        segs = "".join(f'<span class="seg" style="width:{v / tot * 100:.2f}%;background:{c}" '
                       f'data-tip="{e(etiqueta)} · {e(n)}: {v} ({v / tot * 100:.0f} %)"></span>'
                       for v, (n, c) in zip(valores, series) if v)
        out += (f'<div class="bar-row"><div class="bar-label"><span>{e(etiqueta)}</span></div>'
                f'<div><div class="bar-track" style="width:{tot / maxt * 100:.1f}%">{segs}</div></div>'
                f'<div class="bar-count">{tot}</div></div>')
    return f'<div class="bars">{out}{legend(series) if len(series) > 1 else ""}</div>'


def grouped_columns(grupos, series, fmt=None, alto=280, ancho=760):
    """grupos: etiquetas del eje X; series: [(nombre, color, [valor por grupo])]. Un solo eje Y.
    ancho: lienzo en px (380 en una grilla de dos columnas, así el texto no se achica)."""
    valores = [v for _, _, vs in series for v in vs if v is not None]
    if not valores:
        return '<div class="cardbody"><p class="muted">Sin datos.</p></div>'
    W, H, izq, der, arriba, abajo = ancho, alto, 58, 8, 14, 40
    maxv, paso = _escala(max(valores))
    ph = H - arriba - abajo
    y0 = arriba + ph
    svg = []
    i = 0
    while i * paso <= maxv + 1e-9:
        y = y0 - ph * (i * paso) / maxv
        svg.append(f'<line class="{"base" if i == 0 else "grid"}" x1="{izq}" x2="{W - der}" y1="{y:.1f}" y2="{y:.1f}"/>'
                   f'<text class="axis" x="{izq - 8}" y="{y + 4:.1f}" text-anchor="end">{e(_num(i * paso, fmt))}</text>')
        i += 1
    ancho_grupo = (W - izq - der) / len(grupos)
    ancho = min(30, (ancho_grupo * 0.72 - 2 * (len(series) - 1)) / len(series))
    for g, nombre in enumerate(grupos):
        x0 = izq + g * ancho_grupo + (ancho_grupo - (ancho * len(series) + 2 * (len(series) - 1))) / 2
        for s, (sn, color, vs) in enumerate(series):
            v = vs[g]
            if v is None:
                continue
            svg.append(_barra_vertical(x0 + s * (ancho + 2), y0, ancho, ph * v / maxv, color, f"{nombre} · {sn}: {_num(v, fmt)}"))
        corto = nombre if len(nombre) * 6.6 <= ancho_grupo else nombre[:max(int(ancho_grupo / 6.6) - 1, 3)] + "…"
        svg.append(f'<text class="lbl" x="{izq + g * ancho_grupo + ancho_grupo / 2:.1f}" y="{H - 14}" text-anchor="middle">'
                   f'{e(corto)}<title>{e(nombre)}</title></text>')
    ley = legend([(n, c) for n, c, _ in series]) if len(series) > 1 else ""
    return f'<div class="chart"><svg viewBox="0 0 {W} {H}" role="img">{"".join(svg)}</svg>{ley}</div>'


def line_chart(x, series, fmt=None, fmt_x=None, alto=240, area=False):
    """x: valores del eje X (números); series: [(nombre, color, [valor por x])]. Un solo eje Y,
    líneas de 2px, puntos al pasar el mouse y crosshair con el valor de todas las series."""
    if len(x) < 2 or not any(v is not None for _, _, vs in series for v in vs):
        return '<p class="muted">Sin datos suficientes para la evolución.</p>'
    W, H, izq, der, arriba, abajo = 760, alto, 58, 14, 14, 30
    valores = [v for _, _, vs in series for v in vs if v is not None]
    maxv, paso = _escala(max(valores))
    ph, pw = H - arriba - abajo, W - izq - der
    x0, x1 = x[0], x[-1]
    rx = (x1 - x0) or 1
    px = lambda xv: izq + (xv - x0) / rx * pw
    py = lambda v: arriba + ph - ph * v / maxv
    svg = []
    i = 0
    while i * paso <= maxv + 1e-9:
        y = py(i * paso)
        svg.append(f'<line class="{"base" if i == 0 else "grid"}" x1="{izq}" x2="{W - der}" y1="{y:.1f}" y2="{y:.1f}"/>'
                   f'<text class="axis" x="{izq - 8}" y="{y + 4:.1f}" text-anchor="end">{e(_num(i * paso, fmt))}</text>')
        i += 1
    for xv in (x0, x0 + rx / 2, x1):
        svg.append(f'<text class="axis" x="{px(xv):.1f}" y="{H - 8}" text-anchor="middle">{e(fmt_x(xv) if fmt_x else _num(xv))}</text>')
    for nombre, color, vs in series:
        pts = [(px(xv), py(v)) for xv, v in zip(x, vs) if v is not None]
        if not pts:
            continue
        d = " ".join(f'{"M" if k == 0 else "L"}{a:.1f},{b:.1f}' for k, (a, b) in enumerate(pts))
        if area:
            svg.append(f'<path d="{d} L{pts[-1][0]:.1f},{py(0):.1f} L{pts[0][0]:.1f},{py(0):.1f} Z" fill="{_soft(color, .12)}"/>')
        svg.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
    # zonas de hover: una por punto del eje X, con crosshair y el valor de todas las series
    for k, xv in enumerate(x):
        izqz = px(x[k - 1]) if k else px(xv)
        derz = px(x[k + 1]) if k < len(x) - 1 else px(xv)
        a, b = (izqz + px(xv)) / 2, (px(xv) + derz) / 2
        tip = (fmt_x(xv) if fmt_x else _num(xv)) + "\n" + "\n".join(
            f"{n}: {_num(vs[k], fmt)}" for n, _, vs in series if vs[k] is not None)
        puntos = "".join(f'<circle cx="{px(xv):.1f}" cy="{py(vs[k]):.1f}" r="4.5" fill="{c}" stroke="{SUPERFICIE}" stroke-width="2"/>'
                         for _, c, vs in series if vs[k] is not None)
        svg.append(f'<g class="hit" data-tip="{e(tip)}"><rect x="{a:.1f}" y="{arriba}" width="{max(b - a, 1):.1f}" height="{ph}"/>'
                   f'<line class="cross" x1="{px(xv):.1f}" x2="{px(xv):.1f}" y1="{arriba}" y2="{arriba + ph}"/>{puntos}</g>')
    ley = legend([(n, c) for n, c, _ in series]) if len(series) > 1 else ""
    return f'<svg viewBox="0 0 {W} {H}" role="img">{"".join(svg)}</svg>{ley}'

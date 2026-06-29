#!/usr/bin/env python3
"""
Estilos y componentes compartidos para los reportes HTML (dashboard, modo oscuro).

Lo usan los generadores que producen entregables HTML (plan de pruebas, informe
de cierre…). Centraliza la paleta, el CSS y los gráficos para que el tema oscuro
viva en un solo lugar y todos los reportes se vean igual.

Componentes:
  - page(titulo, eyebrow, meta_html, body)  -> documento HTML completo (con marca k0lmena)
  - meta(items)                             -> fila de chips (Historia, Fecha, …)
  - section(titulo, body_html)              -> sección con título + card
  - kpi_tiles(items)                        -> grilla de indicadores
  - donut(segments, pct, label)             -> dona de porcentaje (SVG)
  - bar_chart(rows)                         -> barras horizontales por categoría
  - banner(texto, tono)                     -> banner destacado (go/no-go)
  - doc_list(items)                         -> lista con viñetas
  - two_col(izq, der)                       -> grilla de dos columnas
  - table(headers, rows)                    -> tabla (las celdas pueden traer HTML)
  - nivel_badge(nivel)                      -> pastilla de nivel/severidad

Sin dependencias externas: CSS y SVG van inline, no usa internet.
"""
import html
import math

# --- Paleta (GitHub-dark, igual que el reporte de ejecución) ---
PALETA = {
    "bg": "#0E1116", "surface": "#161B22", "tile": "#1C222B", "border": "#272E38",
    "ink": "#E6EAF0", "body": "#AEB6C2", "muted": "#6E7681",
    "ok": "#3FB950", "bad": "#F85149", "blk": "#8B949E", "warn": "#D29922",
}

# Niveles / severidades (Alto·Crítica = rojo, Alta = naranja, Media = ámbar, Baja = gris)
NIVEL_COLOR = {"Alto": "#F85149", "Crítica": "#F85149", "Alta": "#DB6D28",
               "Medio": "#D29922", "Media": "#D29922", "Bajo": "#8B949E", "Baja": "#8B949E"}
NIVEL_SOFT = {"Alto": "rgba(248,81,73,.15)", "Crítica": "rgba(248,81,73,.15)",
              "Alta": "rgba(219,109,40,.15)", "Medio": "rgba(210,153,34,.15)",
              "Media": "rgba(210,153,34,.15)", "Bajo": "rgba(139,148,158,.15)", "Baja": "rgba(139,148,158,.15)"}
NIVEL_INK = {"Alto": "#FF7B72", "Crítica": "#FF7B72", "Alta": "#F0883E",
             "Medio": "#E3B341", "Media": "#E3B341", "Bajo": "#B1BAC4", "Baja": "#B1BAC4"}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0E1116; --surface:#161B22; --tile:#1C222B; --border:#272E38;
  --ink:#E6EAF0; --body:#AEB6C2; --muted:#6E7681;
}
html{-webkit-text-size-adjust:100%}
body{
  background:var(--bg); color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.5; padding:40px 20px;
}
.wrap{max-width:980px;margin:0 auto}
.mono{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-variant-numeric:tabular-nums}
.muted{color:var(--muted)}
.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.14em;font-weight:600;color:var(--muted)}

header{margin-bottom:32px}
.brand{display:inline-flex;align-items:center;gap:7px;margin-bottom:14px}
.brand .dot{font-size:15px}
h1{font-size:28px;font-weight:700;letter-spacing:-.02em;line-height:1.15;color:var(--ink)}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;color:var(--body);
  background:var(--tile);border:1px solid var(--border);border-radius:999px;padding:5px 11px}
.chip .k{color:var(--muted)}
.chip a{color:var(--body);text-decoration:none;border-bottom:1px solid var(--border)}

.card{background:var(--surface);border:1px solid var(--border);border-radius:14px}
.section{margin-top:28px}
.section-title{margin-bottom:14px}
.cardbody{padding:18px 22px;color:var(--body)}
.cardbody p{color:var(--body)}
.cardbody p+p{margin-top:10px}
.lead{font-size:15px;color:var(--ink)}
.subhead{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin-bottom:10px}
.subhead.ok{color:#56D364}.subhead.bad{color:#FF7B72}.subhead.warn{color:#E3B341}

.hero{display:grid;grid-template-columns:200px 1fr;gap:22px;align-items:center;padding:24px}
.gauge{display:flex;flex-direction:column;align-items:center;gap:10px}
.donut-num{font-size:34px;font-weight:700;fill:var(--ink);font-variant-numeric:tabular-nums}
.donut-lbl{font-size:11px;letter-spacing:.12em;text-transform:uppercase;fill:var(--muted);font-weight:600}
.legend{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;font-size:12px;color:var(--body)}
.legend i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:6px;vertical-align:middle}

.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.kpi{padding:16px 14px;border:1px solid var(--border);border-radius:12px;background:var(--tile)}
.kpi .n{font-size:30px;font-weight:700;letter-spacing:-.01em;font-variant-numeric:tabular-nums;line-height:1;color:var(--ink)}
.kpi .l{font-size:12px;color:var(--muted);margin-top:6px}
.kpi.ok .n{color:#3FB950} .kpi.bad .n{color:#F85149} .kpi.blk .n{color:#8B949E} .kpi.warn .n{color:#D29922}

.bars{padding:20px 22px;display:flex;flex-direction:column;gap:12px}
.bar-row{display:flex;align-items:center;gap:12px}
.bar-label{width:84px;font-size:13px;color:var(--body);flex:none}
.bar-track{height:14px;border-radius:7px;overflow:hidden;display:flex;min-width:2px;background:var(--bg)}
.bar-track .seg{height:100%;display:block}
.bar-count{font-size:13px;color:var(--muted);flex:none;font-variant-numeric:tabular-nums}

table{width:100%;border-collapse:collapse;font-size:14px}
thead th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);font-weight:600;padding:0 14px 10px}
tbody td{padding:13px 14px;border-top:1px solid var(--border);color:var(--body);vertical-align:top}
.tablecard{padding:18px 8px 8px}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:3px 10px;border-radius:999px;white-space:nowrap}
td .id{font-weight:600;color:var(--ink)}

.banner{display:flex;align-items:center;gap:10px;padding:16px 18px;border-radius:12px;
  border:1px solid var(--border);font-weight:600;font-size:15px}
.banner .bdot{width:9px;height:9px;border-radius:50%;background:currentColor;flex:none}
.banner.ok{background:rgba(63,185,80,.12);border-color:rgba(63,185,80,.4);color:#56D364}
.banner.bad{background:rgba(248,81,73,.12);border-color:rgba(248,81,73,.4);color:#FF7B72}
.banner.warn{background:rgba(210,153,34,.12);border-color:rgba(210,153,34,.4);color:#E3B341}

.doclist{list-style:none;display:flex;flex-direction:column;gap:9px}
.doclist li{position:relative;padding-left:18px;color:var(--body)}
.doclist li::before{content:"";position:absolute;left:2px;top:8px;width:6px;height:6px;border-radius:50%;background:var(--muted)}

.twocol{display:grid;grid-template-columns:1fr 1fr;gap:12px}

footer{margin-top:28px;text-align:center;font-size:12px;color:var(--muted)}

@media (max-width:720px){
  body{padding:24px 14px}
  .hero{grid-template-columns:1fr}
  .kpis{grid-template-columns:repeat(2,1fr)}
  .twocol{grid-template-columns:1fr}
  h1{font-size:23px}
}
"""


def e(s):
    return html.escape(str(s if s is not None else ""))


def page(titulo, eyebrow, meta_html, body):
    return (f'<!doctype html>\n<html lang="es"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{e(titulo)} — k0lmena</title><style>{CSS}</style></head>'
            f'<body><div class="wrap"><header>'
            f'<span class="brand"><span class="dot">🪖</span>'
            f'<span class="eyebrow">k0lmena · {e(eyebrow)}</span></span>'
            f'<h1>{e(titulo)}</h1>{meta_html}</header>{body}'
            f'<footer>Generado por k0lmena · Agentes k0lmena</footer></div></body></html>\n')


def meta(items):
    """items: lista de (clave, valor); ignora valores vacíos."""
    parts = [f'<span class="chip"><span class="k">{e(k)}</span> {e(v)}</span>'
             for k, v in items if v]
    return f'<div class="meta">{"".join(parts)}</div>' if parts else ""


def section(titulo, body_html):
    return (f'<div class="section"><div class="eyebrow section-title">{e(titulo)}</div>'
            f'<div class="card">{body_html}</div></div>')


def kpi_tiles(items):
    """items: lista de (etiqueta, valor, tono). tono: '' | 'ok' | 'bad' | 'blk' | 'warn'."""
    out = "".join(f'<div class="kpi {tono}"><div class="n">{e(val)}</div>'
                  f'<div class="l">{e(label)}</div></div>' for label, val, tono in items)
    return f'<div class="kpis">{out}</div>'


def donut(segments, pct, label="aprobados"):
    """segments: lista de (valor, color). Centro muestra pct + label."""
    r, cx, cy, w = 66, 90, 90, 20
    C = 2 * math.pi * r
    total = sum(v for v, _ in segments) or 1
    track = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#272E38" stroke-width="{w}"/>'
    segs, acc = "", 0.0
    for value, color in segments:
        if not value:
            continue
        frac = value / total
        dash = frac * C
        segs += (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{w}" '
                 f'stroke-dasharray="{dash:.2f} {C - dash:.2f}" stroke-dashoffset="{-acc * C:.2f}" '
                 f'transform="rotate(-90 {cx} {cy})"/>')
        acc += frac
    return (f'<svg viewBox="0 0 180 180" width="170" height="170" role="img" '
            f'aria-label="{pct} por ciento">{track}{segs}'
            f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" class="donut-num">{pct}%</text>'
            f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" class="donut-lbl">{e(label)}</text></svg>')


def bar_chart(rows):
    """rows: lista de (etiqueta, cantidad, color). Barras normalizadas al máximo."""
    rows = list(rows)
    maxv = max((c for _, c, _ in rows), default=0)
    if not rows or maxv == 0:
        return '<div class="cardbody"><p class="muted">Sin datos.</p></div>'
    out = ""
    for label, count, color in rows:
        wtrack = count / maxv * 100 if maxv else 0
        seg = f'<span class="seg" style="width:100%;background:{color}"></span>' if count else ""
        out += (f'<div class="bar-row"><div class="bar-label">{e(label)}</div>'
                f'<div class="bar-track" style="width:{wtrack:.1f}%">{seg}</div>'
                f'<div class="bar-count">{count}</div></div>')
    return f'<div class="bars">{out}</div>'


def banner(texto, tono="ok"):
    return f'<div class="banner {tono}"><span class="bdot"></span>{e(texto)}</div>'


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


def nivel_badge(nivel):
    n = (nivel or "").strip()
    bg = NIVEL_SOFT.get(n, "rgba(139,148,158,.15)")
    fg = NIVEL_INK.get(n, "#B1BAC4")
    return f'<span class="pill" style="background:{bg};color:{fg}">{e(n) or "—"}</span>'

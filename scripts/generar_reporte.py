#!/usr/bin/env python3
"""
Genera un reporte HTML (dashboard, modo oscuro) de una ejecución de pruebas, desde un JSON.

Uso:
    python scripts/generar_reporte.py <resultados.json> <salida.html>

JSON de entrada:
{
  "titulo": "Crear cuenta",
  "historia": "HU-001",
  "fecha": "2026-06-18 14:30",
  "modo": "headed",
  "url": "https://qarmy.ar/practica/automation/",
  "casos": [
    {"id": "CP-001", "titulo": "Registro con datos válidos",
     "prioridad": "Crítica", "estado": "Aprobado",
     "duracion_s": 4.2, "motivo": "", "evidencia": "evidencia/cp-001.png"}
  ]
}

Estados:  Aprobado | Fallido | Bloqueado
Prioridad: Crítica | Alta | Media | Baja

El HTML es autocontenido: CSS y gráficos van inline (SVG/CSS), no usa internet.
"""
import sys
import json
import html
import math

ESTADOS = ["Aprobado", "Fallido", "Bloqueado"]
PRIOS = ["Crítica", "Alta", "Media", "Baja"]
COLOR = {"Aprobado": "#3FB950", "Fallido": "#F85149", "Bloqueado": "#8B949E"}
COLOR_SOFT = {"Aprobado": "rgba(63,185,80,.15)", "Fallido": "rgba(248,81,73,.15)", "Bloqueado": "rgba(139,148,158,.15)"}
COLOR_INK = {"Aprobado": "#56D364", "Fallido": "#FF7B72", "Bloqueado": "#B1BAC4"}
PRIO_DOT = {"Crítica": "#F85149", "Alta": "#DB6D28", "Media": "#D29922", "Baja": "#8B949E"}

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
.kpi.ok .n{color:#3FB950} .kpi.bad .n{color:#F85149} .kpi.blk .n{color:#8B949E}

.bars{padding:20px 22px;display:flex;flex-direction:column;gap:12px}
.bar-row{display:flex;align-items:center;gap:12px}
.bar-label{width:64px;font-size:13px;color:var(--body);flex:none}
.bar-track{height:14px;border-radius:7px;overflow:hidden;display:flex;min-width:2px;background:var(--bg)}
.bar-track .seg{height:100%;display:block}
.bar-count{font-size:13px;color:var(--muted);flex:none;font-variant-numeric:tabular-nums}

table{width:100%;border-collapse:collapse;font-size:14px}
thead th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);font-weight:600;padding:0 14px 10px}
tbody td{padding:13px 14px;border-top:1px solid var(--border);color:var(--body);vertical-align:top}
.tablecard{padding:18px 8px 8px}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:3px 10px;border-radius:999px;white-space:nowrap}
.prio{font-size:12px;color:var(--body)}
.prio b{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:6px;vertical-align:middle}
.ev{color:var(--body);text-decoration:none;border-bottom:1px solid var(--border)}
td .id{font-weight:600;color:var(--ink)}

footer{margin-top:28px;text-align:center;font-size:12px;color:var(--muted)}

@media (max-width:720px){
  body{padding:24px 14px}
  .hero{grid-template-columns:1fr}
  .kpis{grid-template-columns:repeat(2,1fr)}
  h1{font-size:23px}
}
"""


def _e(s):
    return html.escape(str(s if s is not None else ""))


def _donut(counts, total):
    r, cx, cy, w = 66, 90, 90, 20
    C = 2 * math.pi * r
    track = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#272E38" stroke-width="{w}"/>'
    segs, acc = "", 0.0
    for est in ESTADOS:
        n = counts.get(est, 0)
        if not n:
            continue
        frac = n / total
        dash = frac * C
        segs += (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{COLOR[est]}" '
                 f'stroke-width="{w}" stroke-dasharray="{dash:.2f} {C - dash:.2f}" '
                 f'stroke-dashoffset="{-acc * C:.2f}" transform="rotate(-90 {cx} {cy})"/>')
        acc += frac
    pct = round(counts.get("Aprobado", 0) / total * 100) if total else 0
    return (f'<svg viewBox="0 0 180 180" width="170" height="170" role="img" '
            f'aria-label="Aprobados {pct} por ciento">{track}{segs}'
            f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" class="donut-num">{pct}%</text>'
            f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" class="donut-lbl">aprobados</text></svg>')


def _legend(counts):
    parts = [f'<span><i style="background:{COLOR[e]}"></i>{e} ({counts.get(e, 0)})</span>' for e in ESTADOS]
    return f'<div class="legend">{"".join(parts)}</div>'


def _kpis(counts, total):
    cards = [("Total", total, ""), ("Aprobados", counts.get("Aprobado", 0), "ok"),
             ("Fallidos", counts.get("Fallido", 0), "bad"), ("Bloqueados", counts.get("Bloqueado", 0), "blk")]
    out = "".join(f'<div class="kpi {cls}"><div class="n">{n}</div><div class="l">{label}</div></div>'
                  for label, n, cls in cards)
    return f'<div class="kpis">{out}</div>'


def _barras(casos):
    data, maxtot = {}, 0
    for p in PRIOS:
        cs = [c for c in casos if (c.get("prioridad") or "").strip() == p]
        if not cs:
            continue
        cnt = {e: sum(1 for c in cs if (c.get("estado") or "").strip() == e) for e in ESTADOS}
        data[p] = (cnt, len(cs))
        maxtot = max(maxtot, len(cs))
    if not data:
        return '<p class="muted" style="padding:0 22px 20px">Sin datos de prioridad.</p>'
    rows = ""
    for p, (cnt, tot) in data.items():
        wtrack = tot / maxtot * 100 if maxtot else 0
        segs = "".join(f'<span class="seg" style="width:{cnt[e] / tot * 100:.1f}%;background:{COLOR[e]}" title="{e}: {cnt[e]}"></span>'
                       for e in ESTADOS if cnt[e])
        rows += (f'<div class="bar-row"><div class="bar-label">{_e(p)}</div>'
                 f'<div class="bar-track" style="width:{wtrack:.1f}%">{segs}</div>'
                 f'<div class="bar-count">{tot}</div></div>')
    return f'<div class="bars">{rows}</div>'


def _tabla(casos):
    rows = ""
    for c in casos:
        est = (c.get("estado") or "").strip()
        prio = (c.get("prioridad") or "").strip()
        ev = c.get("evidencia")
        ev_html = f'<a class="ev" href="{_e(ev)}" target="_blank" rel="noopener">ver</a>' if ev else '<span class="muted">—</span>'
        motivo = _e(c.get("motivo") or "")
        det = motivo if motivo else '<span class="muted">—</span>'
        pill = (f'<span class="pill" style="background:{COLOR_SOFT.get(est, "rgba(139,148,158,.15)")};'
                f'color:{COLOR_INK.get(est, "#B1BAC4")}">{_e(est) or "—"}</span>')
        prio_html = f'<span class="prio"><b style="background:{PRIO_DOT.get(prio, "#8B949E")}"></b>{_e(prio) or "—"}</span>'
        rows += (f'<tr><td class="mono"><span class="id">{_e(c.get("id"))}</span></td>'
                 f'<td>{_e(c.get("titulo"))}</td><td>{prio_html}</td><td>{pill}</td>'
                 f'<td>{det}</td><td>{ev_html}</td></tr>')
    return (f'<table><thead><tr><th>ID</th><th>Caso</th><th>Prioridad</th>'
            f'<th>Estado</th><th>Detalle</th><th>Evidencia</th></tr></thead><tbody>{rows}</tbody></table>')


def _chips(data):
    chips = []
    if data.get("historia"):
        chips.append(f'<span class="chip"><span class="k">Historia</span> {_e(data["historia"])}</span>')
    if data.get("fecha"):
        chips.append(f'<span class="chip"><span class="k">Fecha</span> {_e(data["fecha"])}</span>')
    if data.get("modo"):
        chips.append(f'<span class="chip"><span class="k">Modo</span> {_e(data["modo"])}</span>')
    if data.get("url"):
        u = _e(data["url"])
        chips.append(f'<span class="chip"><span class="k">URL</span> <a href="{u}">{u}</a></span>')
    return f'<div class="meta">{"".join(chips)}</div>' if chips else ""


def build_html(data):
    casos = data.get("casos", [])
    total = len(casos)
    counts = {e: sum(1 for c in casos if (c.get("estado") or "").strip() == e) for e in ESTADOS}
    titulo = data.get("titulo") or "Reporte de ejecución"
    body = f"""<div class="wrap">
  <header>
    <span class="brand"><span class="dot">🪖</span><span class="eyebrow">k0lmena · Reporte de ejecución</span></span>
    <h1>{_e(titulo)}</h1>
    {_chips(data)}
  </header>

  <div class="card hero">
    <div class="gauge">{_donut(counts, total)}{_legend(counts)}</div>
    {_kpis(counts, total)}
  </div>

  <div class="section">
    <div class="eyebrow section-title">Resultados por prioridad</div>
    <div class="card">{_barras(casos)}</div>
  </div>

  <div class="section">
    <div class="eyebrow section-title">Detalle de casos</div>
    <div class="card tablecard">{_tabla(casos)}</div>
  </div>

  <footer>Generado por k0lmena · Agentes k0lmena</footer>
</div>"""
    return (f'<!doctype html>\n<html lang="es"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{_e(titulo)} — Reporte k0lmena</title><style>{CSS}</style></head>'
            f'<body>{body}</body></html>\n')


def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/generar_reporte.py <resultados.json> <salida.html>")
        sys.exit(1)
    entrada, salida = sys.argv[1], sys.argv[2]
    if not salida.lower().endswith(".html"):
        print("La salida debe terminar en .html")
        sys.exit(1)
    with open(entrada, encoding="utf-8") as f:
        data = json.load(f)
    with open(salida, "w", encoding="utf-8") as f:
        f.write(build_html(data))
    print(f"OK: {salida}")


if __name__ == "__main__":
    main()

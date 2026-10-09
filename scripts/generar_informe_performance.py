#!/usr/bin/env python3
"""
Genera el Informe de performance en HTML (dashboard, modo oscuro) a partir de un JSON.

Uso:
    python scripts/generar_informe_performance.py <informe.json> <salida.html>

Las MÉTRICAS no se escriben a mano: salen de los resúmenes JSON que deja cada corrida de
`npm run perf` (herramientas/k0lmena/reports/performance/<herramienta>/<script>-<perfil>-<fecha>.json).
El JSON de entrada aporta el plan acordado con la persona y el análisis:

{
  "titulo": "Informe de performance — Login",
  "historia": "HU-001",
  "fecha": "2026-10-09",
  "veredicto": "Apto con observaciones",          // conclusión del análisis
  "veredicto_tono": "warn",                        // opcional: ok | warn | bad (si no, se deduce)
  "resumen": "Resumen ejecutivo...",
  "plan": {
    "objetivo": "Validar que el login soporte el pico de las 9 h",
    "tipos": ["load", "stress"],
    "herramienta": "k6",
    "motivo_herramienta": "APIs HTTP; escala con poca máquina",
    "ambiente": "https://staging.ejemplo.com",
    "alcance": ["POST /login (70 %)", "GET /perfil (30 %)"],
    "carga": {"Usuarios concurrentes": "50", "Rampa": "1 min", "Duración": "5 min"},
    "umbrales": {"p95": "< 500 ms", "Errores": "< 1 %"},
    "supuestos": ["Tiempo de pensamiento de 1 s (sugerido y aceptado)"]
  },
  "corridas": [                                   // resumen JSON de cada corrida (ruta o {resumen, etiqueta})
    {"resumen": "herramientas/k0lmena/reports/performance/k6/HU-001-login-load-20261009-101500.json",
     "etiqueta": "Load · 50 usuarios"}
  ],
  "capacidad": "Hasta 100 usuarios con p95 < 500 ms; a 150 se degrada.",   // opcional
  "hallazgos": [{"titulo": "...", "detalle": "...", "severidad": "Alta"}],
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "impacto": "...", "pregunta": "...", "estado": "Abierto"}],
  "proximos_pasos": ["..."]
}

Severidad / prioridad: Crítica | Alta | Media | Baja.
El HTML es autocontenido (CSS y SVG inline), no usa internet.
"""
import json
import os
import sys
from pathlib import Path

from _estilos_reporte import (e, page, meta, section, kpi_tiles, banner, doc_list, table,
                              nivel_badge, two_col)

AZUL, NARANJA, ROJO, VERDE, VIOLETA = "#58A6FF", "#F0883E", "#F85149", "#3FB950", "#BC8CFF"
GRIS = "#272E38"

CSS_EXTRA = """
<style>
.chart{padding:18px 22px}
.chart svg{width:100%;height:auto;display:block}
.chart .ley{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--body);margin-top:8px}
.chart .ley i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:middle}
.ok-t{color:#56D364}.bad-t{color:#FF7B72}.warn-t{color:#E3B341}
.plan dl{display:grid;grid-template-columns:190px 1fr;gap:8px 16px}
.plan dt{color:var(--muted);font-size:13px}.plan dd{color:var(--ink)}
.tablecard{overflow-x:auto}
@media (max-width:720px){.plan dl{grid-template-columns:1fr}}
</style>
"""


# ------------------------------------------------------------------ utilidades
def ms(x):
    if x is None:
        return "—"
    return f"{x / 1000:.2f} s" if x >= 1000 else f"{x:.0f} ms"


def num(x, dec=2):
    return "—" if x is None else (f"{x:,.0f}".replace(",", ".") if dec == 0 else f"{x:.{dec}f}")


def duracion(seg):
    if seg is None:
        return "—"
    m, s = divmod(round(seg), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m" if h else (f"{m}m {s}s" if m else f"{s}s")


def tono_veredicto(texto):
    low = (texto or "").lower()
    if "no apto" in low or "no cumple" in low or "no-go" in low:
        return "bad"
    if "observ" in low or "riesgo" in low or "condic" in low or "parcial" in low:
        return "warn"
    return "ok" if ("apto" in low or "cumple" in low) else "warn"


VEREDICTO_CORRIDA = {"cumple": ("Cumple", "ok-t"), "no cumple": ("No cumple", "bad-t"),
                     "sin umbrales": ("Sin umbrales", "warn-t"), "error": ("Error", "bad-t")}


def cargar_corridas(entradas, base_html):
    corridas = []
    for entrada in entradas:
        ruta = entrada.get("resumen") if isinstance(entrada, dict) else entrada
        etiqueta = entrada.get("etiqueta") if isinstance(entrada, dict) else None
        if not os.path.exists(ruta):
            sys.exit(f"[!] No encuentro el resumen de la corrida: {ruta}")
        with open(ruta, encoding="utf-8") as f:
            r = json.load(f)
        html_corrida = (r.get("archivos") or {}).get("html") or ruta[:-5] + ".html"
        r["_link"] = None
        if os.path.exists(html_corrida):
            try:
                r["_link"] = os.path.relpath(html_corrida, base_html).replace(os.sep, "/")
            except ValueError:  # en otro disco (Windows): enlace absoluto
                r["_link"] = Path(os.path.abspath(html_corrida)).as_uri()
        usuarios = (r.get("kpis") or {}).get("usuarios_max")
        r["_nombre"] = etiqueta or (f'{r.get("perfil", "?")} · {usuarios:.0f} usuario{"" if usuarios == 1 else "s"}' if usuarios else r.get("perfil", "?"))
        corridas.append(r)
    # Si dos corridas quedan con el mismo nombre, se numeran.
    vistos = {}
    for c in corridas:
        vistos[c["_nombre"]] = vistos.get(c["_nombre"], 0) + 1
    contador = {}
    for c in corridas:
        if vistos[c["_nombre"]] > 1:
            contador[c["_nombre"]] = contador.get(c["_nombre"], 0) + 1
            c["_nombre"] = f'{c["_nombre"]} (#{contador[c["_nombre"]]})'
    return corridas


# ------------------------------------------------------------------ gráficos SVG
def barras_agrupadas(grupos, series, unidad_ms=True, ancho=760):
    """grupos: etiquetas del eje X. series: lista de (nombre, color, valores por grupo).
    ancho: ancho del lienzo (380 para la grilla de dos columnas, así el texto no se achica)."""
    valores = [v for _, _, vs in series for v in vs if v is not None]
    if not valores:
        return '<div class="cardbody"><p class="muted">Sin datos.</p></div>'
    W, H, izq, abajo, arriba = ancho, 280, 64, 46, 16
    maxv = max(valores) * 1.12 or 1
    alto = H - abajo - arriba
    ancho_grupo = (W - izq - 10) / len(grupos)
    ancho_barra = min(34, ancho_grupo * 0.8 / len(series))
    svg = []
    for i in range(5):
        y = arriba + alto - alto * i / 4
        v = maxv * i / 4
        svg.append(f'<line x1="{izq}" x2="{W - 10}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRIS}"/>')
        svg.append(f'<text x="{izq - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="#6E7681">'
                   f'{e(ms(v) if unidad_ms else num(v))}</text>')
    for g, nombre in enumerate(grupos):
        x0 = izq + g * ancho_grupo + (ancho_grupo - ancho_barra * len(series)) / 2
        for s, (_, color, vs) in enumerate(series):
            v = vs[g]
            if v is None:
                continue
            h = alto * v / maxv
            x = x0 + s * ancho_barra
            svg.append(f'<rect x="{x:.1f}" y="{arriba + alto - h:.1f}" width="{ancho_barra - 3:.1f}" '
                       f'height="{h:.1f}" rx="3" fill="{color}"><title>{e(ms(v) if unidad_ms else num(v))}</title></rect>')
        svg.append(f'<text x="{izq + g * ancho_grupo + ancho_grupo / 2:.1f}" y="{H - 18}" text-anchor="middle" '
                   f'font-size="12" fill="#AEB6C2">{e(nombre if len(nombre) <= ancho_grupo / 6.5 else nombre[:int(ancho_grupo / 6.5) - 1] + "…")}'
                   f'<title>{e(nombre)}</title></text>')
    ley = "".join(f'<span><i style="background:{c}"></i>{e(n)}</span>' for n, c, _ in series)
    return (f'<div class="chart"><svg viewBox="0 0 {W} {H}" role="img">{"".join(svg)}</svg>'
            f'<div class="ley">{ley}</div></div>')


def linea_tiempo(puntos, herramienta):
    """Req/s (azul) y p95 (naranja), cada uno en su escala, como en el reporte de cada corrida."""
    pts = [p for p in puntos or [] if p.get("rps") is not None or p.get("p95") is not None]
    if len(pts) < 2:
        if herramienta == "k6":
            return '<p class="muted">k6 entrega solo el resumen final: sin evolución en el tiempo.</p>'
        return '<p class="muted">Corrida demasiado corta: menos de dos intervalos de 10 s para mostrar la evolución.</p>'
    W, H, izq, der, arriba, abajo = 760, 200, 14, 14, 26, 26
    t0, t1 = pts[0]["t"], pts[-1]["t"]
    rango = (t1 - t0) or 1
    maxr = max((p["rps"] or 0) for p in pts) or 1
    maxp = max((p["p95"] or 0) for p in pts) or 1

    def camino(clave, maxv):
        coords = [(izq + (p["t"] - t0) / rango * (W - izq - der), arriba + (H - arriba - abajo) * (1 - (p[clave] or 0) / maxv))
                  for p in pts if p.get(clave) is not None]
        return " ".join(f'{"M" if i == 0 else "L"}{x:.1f},{y:.1f}' for i, (x, y) in enumerate(coords))

    svg = (f'<line x1="{izq}" x2="{W - der}" y1="{H - abajo}" y2="{H - abajo}" stroke="{GRIS}"/>'
           f'<path d="{camino("rps", maxr)}" fill="none" stroke="{AZUL}" stroke-width="2.2"/>'
           f'<path d="{camino("p95", maxp)}" fill="none" stroke="{NARANJA}" stroke-width="2.2"/>'
           f'<text x="{W - der}" y="14" text-anchor="end" font-size="11" fill="{AZUL}">req/s máx. {maxr:.1f}</text>'
           f'<text x="{W - der - 130}" y="14" text-anchor="end" font-size="11" fill="{NARANJA}">p95 máx. {e(ms(maxp))}</text>'
           f'<text x="{izq}" y="{H - 8}" font-size="11" fill="#6E7681">0 s</text>'
           f'<text x="{W - der}" y="{H - 8}" text-anchor="end" font-size="11" fill="#6E7681">{e(duracion(rango / 1000))}</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img">{svg}</svg>'


# ------------------------------------------------------------------ armado
def build_html(data, corridas):
    body = []
    if data.get("veredicto"):
        body.append(banner(data["veredicto"], data.get("veredicto_tono") or tono_veredicto(data["veredicto"])))

    # KPIs del conjunto
    reqs = sum((c.get("kpis") or {}).get("requests") or 0 for c in corridas)
    p95s = [(c.get("latencia") or {}).get("p95") for c in corridas if (c.get("latencia") or {}).get("p95") is not None]
    errs = [(c.get("kpis") or {}).get("error_pct") for c in corridas if (c.get("kpis") or {}).get("error_pct") is not None]
    cumplen = sum(1 for c in corridas if c.get("veredicto") == "cumple")
    rps_max = max(((c.get("kpis") or {}).get("rps") or 0) for c in corridas)
    usuarios_max = max(((c.get("kpis") or {}).get("usuarios_max") or 0) for c in corridas)
    fila1 = kpi_tiles([
        ("Corridas", len(corridas), ""),
        ("Cumplen umbrales", f"{cumplen}/{len(corridas)}", "ok" if cumplen == len(corridas) else "bad"),
        ("Peor p95", ms(max(p95s)) if p95s else "—", ""),
        ("Peor % de error", f"{max(errs):.2f} %" if errs else "—", "bad" if errs and max(errs) > 0 else "ok"),
    ])
    fila2 = kpi_tiles([
        ("Requests totales", num(reqs, 0), ""),
        ("Req/s máx.", num(rps_max), ""),
        ("Usuarios máx.", num(usuarios_max, 0), ""),
        ("Duración total", duracion(sum(c.get("duracion_s") or 0 for c in corridas)), ""),
    ])
    body.append(f'<div style="margin-top:20px">{fila1}</div><div style="margin-top:12px">{fila2}</div>')

    if data.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(data["resumen"])}</p></div>'))
    if data.get("capacidad"):
        body.append(section("Capacidad observada", f'<div class="cardbody"><p class="lead">{e(data["capacidad"])}</p></div>'))

    # Plan acordado
    plan = data.get("plan") or {}
    if plan:
        filas = []
        for etiqueta, clave in [("Objetivo", "objetivo"), ("Tipos de prueba", "tipos"), ("Herramienta", "herramienta"),
                                ("Por qué esa herramienta", "motivo_herramienta"), ("Ambiente", "ambiente"), ("Alcance", "alcance")]:
            v = plan.get(clave)
            if v:
                filas.append((etiqueta, ", ".join(v) if isinstance(v, list) else v))
        for grupo in ("carga", "umbrales"):
            for k, v in (plan.get(grupo) or {}).items():
                filas.append((f'{"Carga" if grupo == "carga" else "Umbral"} · {k}', v))
        dl = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in filas)
        sup = plan.get("supuestos") or []
        extra = (f'<div class="subhead" style="margin-top:16px">Supuestos y sugerencias aceptadas</div>'
                 f'<ul class="doclist">{"".join(f"<li>{e(s)}</li>" for s in sup)}</ul>') if sup else ""
        body.append(section("Plan acordado", f'<div class="cardbody plan"><dl>{dl}</dl>{extra}</div>'))

    # Resultados por corrida
    filas = []
    for c in corridas:
        k, l = c.get("kpis") or {}, c.get("latencia") or {}
        ver, clase = VEREDICTO_CORRIDA.get(c.get("veredicto"), (c.get("veredicto") or "—", ""))
        nombre = f'<a href="{e(c["_link"])}" style="color:var(--ink)">{e(c["_nombre"])}</a>' if c["_link"] else e(c["_nombre"])
        filas.append([nombre, num(k.get("usuarios_max"), 0), duracion(c.get("duracion_s")), num(k.get("requests"), 0),
                      num(k.get("rps")), f'{num(k.get("error_pct"))} %', ms(l.get("p50")), ms(l.get("p95")), ms(l.get("p99")),
                      f'<span class="{clase}">{e(ver)}</span>'])
    body.append(section("Resultados por corrida", table(
        ["Corrida", "Usuarios", "Duración", "Requests", "Req/s", "Errores", "p50", "p95", "p99", "Veredicto"], filas)))

    # Gráficos comparativos
    grupos = [c["_nombre"] for c in corridas]
    lat = barras_agrupadas(grupos, [
        ("p50", AZUL, [(c.get("latencia") or {}).get("p50") for c in corridas]),
        ("p95", NARANJA, [(c.get("latencia") or {}).get("p95") for c in corridas]),
        ("p99", ROJO, [(c.get("latencia") or {}).get("p99") for c in corridas]),
    ])
    body.append(section("Latencia por corrida", lat))
    thr = barras_agrupadas(grupos, [("Req/s", VERDE, [(c.get("kpis") or {}).get("rps") for c in corridas])], unidad_ms=False, ancho=380)
    err = barras_agrupadas(grupos, [("% de error", ROJO, [(c.get("kpis") or {}).get("error_pct") for c in corridas])], unidad_ms=False, ancho=380)
    body.append(two_col(section("Throughput (req/s)", thr), section("Errores (%)", err)))

    # Evolución en el tiempo de cada corrida
    evol = "".join(f'<div class="subhead" style="margin-top:{14 if i else 0}px">{e(c["_nombre"])}</div>{linea_tiempo(c.get("linea_tiempo"), c.get("herramienta"))}'
                   for i, c in enumerate(corridas))
    body.append(section("Evolución en el tiempo · req/s (azul) y p95 (naranja)", f'<div class="chart">{evol}</div>'))

    # Umbrales
    filas = []
    for c in corridas:
        for u in c.get("umbrales") or []:
            filas.append([e(c["_nombre"]), f'<span class="mono">{e(u.get("metrica"))}</span>', e(u.get("condicion")),
                          e(u.get("valor")), '<span class="ok-t">Cumple</span>' if u.get("ok") else '<span class="bad-t">No cumple</span>'])
    if filas:
        body.append(section("Umbrales", table(["Corrida", "Métrica", "Condición", "Medido", "Resultado"], filas)))

    # Endpoints / pasos: p95 de cada uno en cada corrida
    nombres = []
    for c in corridas:
        for f in (c.get("detalle") or {}).get("filas") or []:
            if f.get("nombre") not in nombres:
                nombres.append(f.get("nombre"))
    if nombres:
        idx = [{f.get("nombre"): f for f in (c.get("detalle") or {}).get("filas") or []} for c in corridas]
        filas = [[f'<span class="mono">{e(n)}</span>'] + [ms((i.get(n) or {}).get("p95")) for i in idx] for n in nombres]
        body.append(section("p95 por endpoint o paso", table(["Endpoint / paso"] + grupos, filas)))

    # Errores
    errores = {}
    for c in corridas:
        for motivo, n in (c.get("errores") or {}).items():
            errores[motivo] = errores.get(motivo, 0) + n
    if errores:
        filas = [[e(m), f'<span class="bad-t">{num(n, 0)}</span>'] for m, n in sorted(errores.items(), key=lambda x: -x[1])[:15]]
        body.append(section("Errores más frecuentes", table(["Error", "Cantidad"], filas)))

    # Análisis
    if data.get("hallazgos"):
        filas = [[f'<strong style="color:var(--ink)">{e(h.get("titulo"))}</strong>', e(h.get("detalle")), nivel_badge(h.get("severidad"))]
                 for h in data["hallazgos"]]
        body.append(section("Hallazgos y cuellos de botella", table(["Hallazgo", "Detalle", "Severidad"], filas)))
    if data.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(r.get("accion"))}</strong>', e(r.get("motivo")), nivel_badge(r.get("prioridad"))]
                 for r in data["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))

    faltantes = data.get("falta_informacion") or []
    if faltantes:
        items = [f'{f.get("id", "")} — {f.get("que_falta", "")}' + (f' (impacto: {f["impacto"]})' if f.get("impacto") else "")
                 + (f' · Pregunta: {f["pregunta"]}' if f.get("pregunta") else "") + f' · {f.get("estado", "Abierto")}' for f in faltantes]
        body.append(section("Falta información", doc_list(items)))
    if data.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(data["proximos_pasos"])))

    meta_html = meta([("Historia", data.get("historia")), ("Fecha", data.get("fecha")),
                      ("Herramienta", plan.get("herramienta")), ("Ambiente", plan.get("ambiente"))])
    return page(data.get("titulo") or "Informe de performance", "Informe de performance", meta_html,
                CSS_EXTRA + "".join(body))


def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/generar_informe_performance.py <informe.json> <salida.html>")
        sys.exit(1)
    entrada, salida = sys.argv[1], sys.argv[2]
    if not salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    with open(entrada, encoding="utf-8") as f:
        data = json.load(f)
    if not data.get("corridas"):
        sys.exit("[!] El informe necesita al menos una corrida en \"corridas\" (resumen JSON de npm run perf).")
    corridas = cargar_corridas(data["corridas"], os.path.dirname(os.path.abspath(salida)))
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        f.write(build_html(data, corridas))
    print(f"OK: {salida}")


if __name__ == "__main__":
    main()

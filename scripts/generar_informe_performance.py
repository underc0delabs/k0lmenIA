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
                              nivel_badge, two_col, grouped_columns, line_chart, SERIES, CRITICO)

CSS_EXTRA = """
<style>
.ok-t{color:#7BE07B;font-weight:600}.bad-t{color:#F59A9A;font-weight:600}.warn-t{color:#F7CD6E;font-weight:600}
.ok-t::before{content:"✓ "}.bad-t::before{content:"✕ "}.warn-t::before{content:"! "}
.plan dl{display:grid;grid-template-columns:190px 1fr;gap:9px 16px}
.plan dt{color:var(--muted);font-size:13px}.plan dd{color:var(--ink)}
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


# ------------------------------------------------------------------ evolución en el tiempo
def evolucion(corridas, clave, fmt):
    """Una línea por corrida sobre el tiempo relativo a su inicio (segundos), en un solo eje."""
    series, tiempos = [], set()
    for i, c in enumerate(corridas):
        pts = [p for p in c.get("linea_tiempo") or [] if p.get(clave) is not None]
        if len(pts) < 2:
            continue
        t0 = pts[0]["t"]
        datos = {round((p["t"] - t0) / 1000): p[clave] for p in pts}
        tiempos.update(datos)
        series.append((c["_nombre"], SERIES[i % len(SERIES)], datos))
    if not series:
        return '<p class="muted">Sin evolución en el tiempo: k6 entrega solo el resumen final, o las corridas duraron menos de dos intervalos de 10 s.</p>'
    x = sorted(tiempos)
    return line_chart(x, [(n, col, [d.get(s) for s in x]) for n, col, d in series], fmt=fmt,
                      fmt_x=lambda s: duracion(s), area=len(series) == 1)


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
    lat = grouped_columns(grupos, [
        ("p50", SERIES[0], [(c.get("latencia") or {}).get("p50") for c in corridas]),
        ("p95", SERIES[1], [(c.get("latencia") or {}).get("p95") for c in corridas]),
        ("p99", SERIES[2], [(c.get("latencia") or {}).get("p99") for c in corridas]),
    ], fmt=ms)
    body.append(section("Latencia por corrida", lat, "percentiles del tiempo de respuesta"))
    thr = grouped_columns(grupos, [("Req/s", SERIES[0], [(c.get("kpis") or {}).get("rps") for c in corridas])], alto=240, ancho=380)
    err = grouped_columns(grupos, [("% de error", CRITICO, [(c.get("kpis") or {}).get("error_pct") for c in corridas])],
                          fmt=lambda v: f"{v:.0f} %", alto=240, ancho=380)
    body.append(two_col(section("Throughput", thr, "requests por segundo"), section("Errores", err, "% de requests fallidos")))

    # Evolución en el tiempo: un gráfico por métrica (nunca dos escalas en el mismo gráfico)
    body.append(section("Evolución del throughput", f'<div class="chart">{evolucion(corridas, "rps", lambda v: f"{v:.0f}" if v >= 10 else f"{v:.1f}" if v >= 1 else f"{v:.2f}")}</div>',
                        "req/s por intervalo de 10 s, desde el inicio de cada corrida"))
    body.append(section("Evolución del p95", f'<div class="chart">{evolucion(corridas, "p95", ms)}</div>',
                        "p95 por intervalo de 10 s, desde el inicio de cada corrida"))

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

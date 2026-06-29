#!/usr/bin/env python3
"""
Genera un Informe de Cierre de pruebas en HTML (dashboard, modo oscuro) desde un JSON.

Uso:
    python scripts/generar_informe_cierre.py <cierre.json> <salida.html>

JSON de entrada:
{
  "titulo": "Informe de cierre — Registro de cuenta",
  "historia": "HU-001",
  "fecha": "2026-06-29",
  "recomendacion": "Apto con observaciones",
  "recomendacion_tono": "warn",                 // opcional: ok | warn | bad (si no, se deduce del texto)
  "resumen": "Resumen ejecutivo de la ronda...",
  "resultados": { "aprobado": 12, "fallido": 2, "bloqueado": 1 },
  "alcance": { "planeado": 18, "ejecutado": 15 },   // opcional
  "alcance_nota": "Texto sobre la cobertura.",       // opcional
  "bugs": {
    "por_severidad": { "Crítica": 0, "Alta": 1, "Media": 2, "Baja": 1 },
    "criticos_abiertos": [ {"id": "BUG-003", "titulo": "...", "severidad": "Alta"} ]
  },
  "riesgos_pendientes": ["...", "..."],
  "conclusion": "Texto de cierre."
}

Estados: Aprobado | Fallido | Bloqueado     Severidad: Crítica | Alta | Media | Baja
El HTML es autocontenido (CSS y SVG inline), no usa internet.
"""
import sys
import json

from _estilos_reporte import (e, page, meta, section, kpi_tiles, donut, bar_chart,
                              banner, doc_list, table, nivel_badge, NIVEL_COLOR)

SEVERIDADES = ["Crítica", "Alta", "Media", "Baja"]


def _tono_recomendacion(rec):
    low = (rec or "").lower()
    if "no apto" in low or "no-go" in low or "rechaz" in low:
        return "bad"
    if "observ" in low or "riesgo" in low or "condic" in low or "reserva" in low:
        return "warn"
    if "apto" in low or "listo" in low or low.strip() == "go":
        return "ok"
    return "warn"


def _legend(apr, fal, blo):
    items = [("Aprobado", apr, "#3FB950"), ("Fallido", fal, "#F85149"), ("Bloqueado", blo, "#8B949E")]
    parts = "".join(f'<span><i style="background:{c}"></i>{n} ({v})</span>' for n, v, c in items)
    return f'<div class="legend">{parts}</div>'


def build_html(data):
    res = data.get("resultados", {}) or {}
    apr = int(res.get("aprobado", 0) or 0)
    fal = int(res.get("fallido", 0) or 0)
    blo = int(res.get("bloqueado", 0) or 0)
    total = apr + fal + blo
    pct = round(apr / total * 100) if total else 0

    body = []

    # Banner go/no-go
    rec = data.get("recomendacion", "")
    if rec:
        tono = data.get("recomendacion_tono") or _tono_recomendacion(rec)
        body.append(banner(rec, tono))

    # Hero: dona de aprobados + KPIs
    dn = donut([(apr, "#3FB950"), (fal, "#F85149"), (blo, "#8B949E")], pct, "aprobados")
    kpis = kpi_tiles([
        ("Total", total, ""),
        ("Aprobados", apr, "ok"),
        ("Fallidos", fal, "bad"),
        ("Bloqueados", blo, "blk"),
    ])
    body.append(f'<div class="card hero" style="margin-top:20px">'
                f'<div class="gauge">{dn}{_legend(apr, fal, blo)}</div>{kpis}</div>')

    # Resumen ejecutivo
    if data.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(data["resumen"])}</p></div>'))

    # Alcance cubierto
    alcance = data.get("alcance", {}) or {}
    planeado = alcance.get("planeado")
    ejecutado = alcance.get("ejecutado")
    nota = data.get("alcance_nota")
    if planeado or ejecutado or nota:
        partes = '<div class="cardbody">'
        if planeado and ejecutado is not None:
            cob = round(ejecutado / planeado * 100) if planeado else 0
            partes += (f'<p>Se ejecutaron <strong style="color:var(--ink)">{ejecutado}</strong> de '
                       f'<strong style="color:var(--ink)">{planeado}</strong> casos planificados '
                       f'(<strong style="color:var(--ink)">{cob}%</strong>).</p>'
                       f'<div class="bar-track" style="width:100%;margin-top:12px">'
                       f'<span class="seg" style="width:{cob}%;background:#3FB950"></span></div>')
        if nota:
            partes += f'<p style="margin-top:12px">{e(nota)}</p>'
        partes += '</div>'
        body.append(section("Alcance cubierto", partes))

    # Bugs por severidad + críticos abiertos
    bugs = data.get("bugs", {}) or {}
    sev = bugs.get("por_severidad", {}) or {}
    criticos = bugs.get("criticos_abiertos", []) or []
    if sev or criticos:
        contenido = ""
        if sev:
            contenido += bar_chart([(s, int(sev.get(s, 0) or 0), NIVEL_COLOR[s]) for s in SEVERIDADES])
        if criticos:
            filas = [[f'<span class="id mono">{e(b.get("id"))}</span>', e(b.get("titulo")),
                      nivel_badge(b.get("severidad"))] for b in criticos]
            contenido += table(["ID", "Bug abierto", "Severidad"], filas)
        body.append(section("Bugs por severidad", contenido))

    # Riesgos y pendientes
    if data.get("riesgos_pendientes"):
        body.append(section("Riesgos y pendientes", doc_list(data["riesgos_pendientes"])))

    # Conclusión
    if data.get("conclusion"):
        body.append(section("Conclusión", f'<div class="cardbody"><p>{e(data["conclusion"])}</p></div>'))

    meta_html = meta([("Historia", data.get("historia")), ("Fecha", data.get("fecha"))])
    titulo = data.get("titulo") or "Informe de cierre"
    return page(titulo, "Informe de cierre", meta_html, "".join(body))


def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/generar_informe_cierre.py <cierre.json> <salida.html>")
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

#!/usr/bin/env python3
"""
Genera un Informe de Cierre de pruebas en HTML (dashboard, modo oscuro) desde un JSON.

Uso:
    python scripts/generar_informe_cierre.py <cierre.json> <salida.html>

JSON de entrada (los números, mejor desde "datos": ver más abajo):
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
  "falta_informacion": [                            // opcional (skill investigacion-contexto)
    {"id": "FI-01", "que_falta": "...", "impacto": "CA3 · CP-004", "pregunta": "...", "estado": "Abierto"}
  ],
  "conclusion": "Texto de cierre."
}

"datos" (recomendado): ruta al JSON de scripts/recolectar_resultados.py. Si está, los resultados,
los bugs, la performance y la seguridad salen de ahí (de los archivos reales de la ronda) y no se
escriben a mano: el JSON del informe solo aporta el análisis (resumen, recomendación, riesgos…).

    python scripts/recolectar_resultados.py --historia HU-001 --salida output/informes-cierre/datos-HU-001.json

Estados: Aprobado | Fallido | Bloqueado     Severidad: Crítica | Alta | Media | Baja
El HTML es autocontenido (CSS y SVG inline), no usa internet.
"""
import sys
import json
from pathlib import Path

from _estilos_reporte import (e, page, meta, section, kpi_tiles, donut, bar_chart, legend,
                              banner, doc_list, table, nivel_badge, estado_pill, NIVEL_COLOR, ESTADO_COLOR)

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
    return legend([("Aprobado", ESTADO_COLOR["Aprobado"], apr), ("Fallido", ESTADO_COLOR["Fallido"], fal),
                   ("Bloqueado", ESTADO_COLOR["Bloqueado"], blo)])


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
    dn = donut([(apr, ESTADO_COLOR["Aprobado"], "Aprobados"), (fal, ESTADO_COLOR["Fallido"], "Fallidos"),
                (blo, ESTADO_COLOR["Bloqueado"], "Bloqueados")], pct, "aprobados")
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
                       f'<span class="seg" style="width:{cob}%;background:{ESTADO_COLOR["Aprobado"]}"></span></div>')
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

    # Falta información: lo que nunca se definió y condiciona el resultado de la ronda
    faltantes = data.get("falta_informacion") or []
    if faltantes:
        abiertos = [f for f in faltantes if str(f.get("estado", "Abierto")).lower() != "resuelto"]
        items = [f'{f.get("id", "")} — {f.get("que_falta", "")}'
                 + (f' (impacto: {f["impacto"]})' if f.get("impacto") else "")
                 + (f' · Pregunta: {f["pregunta"]}' if f.get("pregunta") else "")
                 + f' · {f.get("estado", "Abierto")}' for f in faltantes]
        titulo = f"Falta información ({len(abiertos)} abierto{'s' if len(abiertos) != 1 else ''})"
        body.append(section(titulo, doc_list(items)))

    # Lo que viene de recolectar_resultados.py (fuentes, performance, seguridad, casos)
    datos = data.get("_datos") or {}
    if datos.get("fuentes"):
        chips = "".join(f'<span class="chip">{e(f)}</span>' for f in datos["fuentes"])
        body.append(section("Fuentes de los resultados", f'<div class="cardbody"><div class="meta" style="margin-top:0">{chips}</div>'
                            f'<p style="margin-top:12px">Un caso ejecutado varias veces cuenta una sola vez, con su resultado más reciente.</p></div>'))
    if datos.get("performance"):
        filas = [[e(x["informe"]), e(x["veredicto"]), e(x["capacidad"] or "—"), e(x["corridas"])] for x in datos["performance"]]
        body.append(section("Performance", table(["Informe", "Veredicto", "Capacidad observada", "Corridas"], filas)))
    if datos.get("seguridad"):
        filas = [[e(x["escaneo"])] + [e(x["hallazgos"][n]) for n in ("Alto", "Medio", "Bajo", "Informativo")] for x in datos["seguridad"]]
        body.append(section("Seguridad web", table(["Escaneo", "Alto", "Medio", "Bajo", "Informativo"], filas),
                            "hallazgos del escaneo pasivo, sin los falsos positivos descartados"))
    casos = datos.get("casos") or []
    if casos:
        filas = [[f'<span class="id mono">{e(c["id"])}</span>', e(c.get("titulo", "")), estado_pill(c["estado"]), e(c["fuente"])]
                 for c in casos]
        body.append(section("Detalle de casos", table(["Caso", "Título", "Estado", "Fuente"], filas), f"{len(casos)} casos"))
    if (datos.get("bugs") or {}).get("sin_estado"):
        body.append(section("Bugs sin estado", doc_list([f'{b}: el reporte no tiene el campo Estado; se cuenta como abierto' for b in datos["bugs"]["sin_estado"]])))

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
    if data.get("datos"):
        ruta = Path(data["datos"])
        if not ruta.is_absolute() and not ruta.exists():
            ruta = Path(entrada).resolve().parent / ruta
        if not ruta.exists():
            sys.exit(f"[!] No encuentro los datos recolectados: {data['datos']} (generalos con scripts/recolectar_resultados.py)")
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        data["resultados"] = datos["resultados"]
        data["bugs"] = {"por_severidad": datos["bugs"]["por_severidad"], "criticos_abiertos": datos["bugs"]["criticos_abiertos"]}
        data["_datos"] = datos
    with open(salida, "w", encoding="utf-8") as f:
        f.write(build_html(data))
    print(f"OK: {salida}")


if __name__ == "__main__":
    main()

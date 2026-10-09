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
     "duracion_s": 4.2, "motivo": "", "evidencia": "evidencia/cp-001.png",
     "falta_info": ["FI-01"]}
  ],
  "falta_informacion": [
    {"id": "FI-01", "que_falta": "Texto del mensaje al bloquearse la cuenta", "pregunta": "...", "estado": "Abierto"}
  ]
}

"falta_info" (opcional, por caso): el caso depende de información que falta (skill
investigacion-contexto). Se marca en el detalle del caso y se avisa debajo del resumen;
con "falta_informacion" se agrega la sección "Falta información" al final.

Estados:  Aprobado | Fallido | Bloqueado
Prioridad: Crítica | Alta | Media | Baja

El HTML es autocontenido: CSS y gráficos van inline (SVG/CSS), no usa internet.
"""
import sys
import json

from _estilos_reporte import (e, page, meta, section, kpi_tiles, donut, legend, banner, table,
                              stacked_bars, bar_chart, nivel_badge, estado_pill, ESTADO_COLOR, SERIES)

ESTADOS = ["Aprobado", "Fallido", "Bloqueado"]
PRIOS = ["Crítica", "Alta", "Media", "Baja"]


def _fi_ids(c):
    v = c.get("falta_info") or []
    if isinstance(v, str):
        v = v.replace(";", ",").split(",")
    return [str(x).strip() for x in v if str(x).strip()]


def _estado(c):
    return (c.get("estado") or "").strip()


def _hero(casos):
    total = len(casos)
    counts = {s: sum(1 for c in casos if _estado(c) == s) for s in ESTADOS}
    pct = round(counts["Aprobado"] / total * 100) if total else 0
    dn = donut([(counts[s], ESTADO_COLOR[s], s) for s in ESTADOS], pct, "aprobados")
    ley = legend([(s, ESTADO_COLOR[s], counts[s]) for s in ESTADOS])
    durs = [c.get("duracion_s") for c in casos if isinstance(c.get("duracion_s"), (int, float))]
    kpis = kpi_tiles([
        ("Casos ejecutados", total, "", f"{sum(durs):.1f} s en total" if durs else ""),
        ("Aprobados", counts["Aprobado"], "ok", f"{pct} % del total"),
        ("Fallidos", counts["Fallido"], "bad" if counts["Fallido"] else "ok"),
        ("Bloqueados", counts["Bloqueado"], "blk" if counts["Bloqueado"] else ""),
    ])
    return f'<div class="card hero"><div class="gauge">{dn}{ley}</div>{kpis}</div>'


def _por_prioridad(casos):
    filas = []
    for p in PRIOS:
        cs = [c for c in casos if (c.get("prioridad") or "").strip() == p]
        if cs:
            filas.append((p, [sum(1 for c in cs if _estado(c) == s) for s in ESTADOS]))
    return stacked_bars(filas, [(s, ESTADO_COLOR[s]) for s in ESTADOS])


def _duraciones(casos):
    con = [c for c in casos if isinstance(c.get("duracion_s"), (int, float))]
    if not con:
        return ""
    con = sorted(con, key=lambda c: -c["duracion_s"])[:15]
    filas = [(f'{c.get("id")} · {c.get("titulo", "")}', round(c["duracion_s"], 1), SERIES[0]) for c in con]
    return section("Duración por caso", bar_chart(filas, ancho_etiqueta=260), "segundos · los 15 más largos")


def _tabla(casos):
    filas = []
    for c in casos:
        ev = c.get("evidencia")
        ev_html = f'<a href="{e(ev)}" target="_blank" rel="noopener">ver</a>' if ev else '<span class="muted">—</span>'
        det = e(c.get("motivo") or "") or '<span class="muted">—</span>'
        if _fi_ids(c):
            det += f'<br><span style="color:#F7CD6E">Falta información: {e(", ".join(_fi_ids(c)))}</span>'
        dur = c.get("duracion_s")
        filas.append([f'<span class="id mono">{e(c.get("id"))}</span>', e(c.get("titulo")),
                      nivel_badge(c.get("prioridad")), estado_pill(_estado(c)),
                      f"{dur:.1f} s" if isinstance(dur, (int, float)) else '<span class="muted">—</span>', det, ev_html])
    return table(["ID", "Caso", "Prioridad", "Estado", "Duración", "Detalle", "Evidencia"], filas)


def build_html(data):
    casos = data.get("casos", []) or []
    body = [_hero(casos)]

    afectados = [c for c in casos if _fi_ids(c)]
    if afectados:
        ids = sorted({i for c in afectados for i in _fi_ids(c)})
        n = len(afectados)
        body.append(f'<div style="margin-top:16px">' + banner(
            f'Falta información: {n} caso{"s" if n != 1 else ""} depende{"n" if n != 1 else ""} de datos que no están '
            f'definidos ({", ".join(ids)}). Su resultado puede cambiar cuando se resuelvan.', "warn") + '</div>')

    body.append(section("Resultados por prioridad", _por_prioridad(casos)))
    body.append(_duraciones(casos))
    body.append(section("Detalle de casos", _tabla(casos), f"{len(casos)} casos"))

    faltan = data.get("falta_informacion") or []
    if faltan:
        filas = [[f'<span class="id mono">{e(f.get("id", ""))}</span>', e(f.get("que_falta", "")),
                  e(f.get("pregunta", "")) or '<span class="muted">—</span>', e(f.get("estado", "Abierto"))] for f in faltan]
        body.append(section("Falta información", table(["ID", "Qué falta", "Pregunta", "Estado"], filas)))

    meta_html = meta([("Historia", data.get("historia")), ("Fecha", data.get("fecha")),
                      ("Modo", data.get("modo")), ("URL", data.get("url"))])
    return page(data.get("titulo") or "Reporte de ejecución", "Reporte de ejecución", meta_html, "".join(body))


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

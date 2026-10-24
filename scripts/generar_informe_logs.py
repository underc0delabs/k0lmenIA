#!/usr/bin/env python3
"""
Genera el Informe de logs en HTML (dashboard, modo oscuro) a partir de logs.json (scripts/analizar_logs.py)
y, opcionalmente, del análisis del agente analista-logs.

Uso:
    python scripts/generar_informe_logs.py <logs.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (líneas, errores, advertencias, firmas, escenarios fallidos con errores
del servidor), errores y advertencias por minuto, las firmas más repetidas, cada escenario fallido con los
errores que hubo mientras corría, la tabla de firmas con su ejemplo y stack trace, y la evolución.

El análisis (opcional) aporta:
{
  "veredicto": "...", "veredicto_tono": "bad", "resumen": "...",
  "firmas": {"L-01": {"causa": "La base rechaza la conexión: pool agotado", "accion": "...", "bug": "BUG-012"}},
  "escenarios": {"CP-004": {"causa": "El 500 del servidor viene de L-01"}},
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],   // "descripcion" vale como alias de que_falta
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
"""
import argparse
import json
import sys
from pathlib import Path

import _historial
from _i18n import escribir_bilingue, localizar, idioma_actual  # noqa: E402
from _estilos_reporte import (falta_informacion, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, line_chart, two_col,
                              nivel_badge, estado_pill, _pastilla, CRITICO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA

CSS_LOG = """
<style>
.stack{background:#120F0B;border:1px solid var(--border);border-radius:10px;padding:10px 12px;white-space:pre-wrap;word-break:break-word;
  font-family:var(--mono);font-size:11.5px;color:#FFB8B0;max-height:240px;overflow:auto;margin-top:6px}
details.st summary{cursor:pointer;color:var(--muted);font-size:12px;margin-top:4px}
.nivel{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;padding:3px 9px;border-radius:999px}
.esc{border-top:1px solid var(--border-soft);padding:14px 24px}
.esc:first-child{border-top:0}
.esc h3{font-size:15px;color:var(--ink);display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
</style>
"""


def nivel(n):
    return _pastilla(n, CRITICO if n == "Error" else AVISO, "✕" if n == "Error" else "!")


def hhmm(iso):
    return (iso or "")[11:19] or "—"


def build_html(datos, analisis, hist_html=""):
    r = datos.get("resumen") or {}
    firmas = datos.get("firmas") or []
    af = analisis.get("firmas") or {}
    ae = analisis.get("escenarios") or {}
    body = []
    if r.get("fallidos_con_errores"):
        tono, texto = "bad", f'{r["fallidos_con_errores"]} de {r["fallidos"]} escenario(s) fallidos coinciden con errores del servidor'
    elif r.get("errores"):
        tono, texto = "warn", f'{r["errores"]} error(es) en los logs ({r["firmas_error"]} distintos)'
    else:
        tono, texto = "ok", "Sin errores en los logs del período"
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Líneas", f'{r.get("lineas", 0):,}'.replace(",", "."), "", f'{r.get("archivos", 0)} archivo(s) · {r.get("sin_fecha", 0)} eventos sin fecha', "pagina"),
        ("Errores", r.get("errores", 0), "bad" if r.get("errores") else "ok", f'{r.get("firmas_error", 0)} firmas distintas', "bad"),
        ("Advertencias", r.get("advertencias", 0), "warn" if r.get("advertencias") else "ok", "incluye respuestas 4xx", "warn"),
        ("Firmas", r.get("firmas", 0), "", "errores y advertencias agrupados", "lista"),
        ("Fallidos con errores", f'{r.get("fallidos_con_errores", 0)}/{r.get("fallidos", 0)}' if r.get("escenarios") else "—",
         "bad" if r.get("fallidos_con_errores") else "", "escenarios que fallaron mientras el servidor daba error", "bicho"),
    ]) + "</div>")
    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))
    tl = datos.get("linea_tiempo") or []
    if len(tl) >= 2:
        x = list(range(len(tl)))
        fx = lambda v: tl[int(v)]["minuto"][11:] if 0 <= int(v) < len(tl) else ""
        graf = line_chart(x, [("Errores", CRITICO, [t["errores"] for t in tl]), ("Advertencias", AVISO, [t["advertencias"] for t in tl])], fmt_x=fx, alto=260)
        body.append(section("Errores y advertencias por minuto", graf, "un pico suele coincidir con un deploy, una caída o una corrida de pruebas"))
    if firmas:
        body.append(section("Lo que más se repite", bar_chart([(f'{f["id"]} · {f["ejemplo"][:60]}', f["cuenta"], CRITICO if f["nivel"] == "Error" else AVISO) for f in firmas[:10]],
                                                         ancho_etiqueta=520)))
    escs = [c for c in datos.get("escenarios") or [] if c["estado"] == "Fallido"]
    if escs:
        bloques = []
        for c in escs:
            ids = ", ".join(f'{x["firma"]} ×{x["cuenta"]}' for x in c["errores"]) or "ninguno"
            a = ae.get(c.get("caso") or "") or ae.get(c["escenario"]) or {}
            lineas = "\n".join(c.get("lineas") or [])
            bloques.append(f'''<div class="esc"><h3>{e(c.get("caso") or "")} · {e(c["escenario"])} {estado_pill("Fallido")}</h3>
              <p class="muted mono">{e(c.get("historia") or "")} · {e(c.get("uri"))}:{e(c.get("linea"))} · {e(hhmm(c["inicio"]))} → {e(hhmm(c["fin"]))}</p>
              {f'<p><b>Error del test:</b> <span class="mono">{e(c["error"])}</span></p>' if c.get("error") else ""}
              <p><b>Errores del servidor mientras corría:</b> {e(ids)}</p>
              {f'<p><b>Causa:</b> {e(a["causa"])}</p>' if a.get("causa") else ""}
              {f'<div class="stack">{e(lineas)}</div>' if lineas else '<p class="muted">Sin errores en los logs durante el escenario: la causa no está en el servidor (o en estos logs).</p>'}</div>''')
        body.append(section("Escenarios fallidos y el servidor", "".join(bloques), "errores de los logs entre el inicio y el fin de cada escenario (± el margen)"))
    if firmas:
        filas = []
        for f in firmas:
            a = af.get(f["id"]) or {}
            stack = f'<details class="st"><summary>stack trace ({len(f["stack"])} líneas)</summary><div class="stack">{e(chr(10).join(f["stack"]))}</div></details>' if f.get("stack") else ""
            extra = "".join(f'<div><b>{k}:</b> {e(a[k2])}</div>' for k, k2 in (("Causa", "causa"), ("Qué hacer", "accion"), ("Bug", "bug")) if a.get(k2))
            filas.append([f'<span class="mono" style="white-space:nowrap">{e(f["id"])}</span>', nivel(f["nivel"]), e(f["cuenta"]),
                          f'<span class="mono" style="color:var(--ink)">{e(f["ejemplo"][:220])}</span>{stack}{extra}'
                          + (f'<div class="muted">Escenarios: {e(", ".join(f["escenarios"]))}</div>' if f.get("escenarios") else ""),
                          e(f'{hhmm(f.get("primero"))} → {hhmm(f.get("ultimo"))}'), e(", ".join(f["archivos"]))])
        body.append(section("Firmas", table(["ID", "Nivel", "Veces", "Ejemplo", "Primera → última", "Archivos"], filas),
                            "cada firma es un mismo error con distintos datos (números, ids y textos normalizados)"))
    filas = [[f'<span class="mono">{e(f["archivo"])}</span>', e(f["lineas"])] for f in datos.get("fuentes") or []]
    v = datos.get("ventana") or {}
    filas.append(["Período analizado", e(f'{(v.get("desde") or "todo")[:19]} → {(v.get("hasta") or "todo")[:19]}')])
    body.append(section("Fuentes", table(["Archivo", "Líneas"], filas)))
    body.append(falta_informacion(analisis.get("falta_informacion")))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    if hist_html:
        body.append(hist_html)
    m = meta([("Análisis", datos.get("nombre")), ("Corrida", datos.get("corrida")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " "))])
    return page("Logs", "Análisis de logs", m, CSS_EXTRA + CSS_LOG + "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de logs a partir de logs.json")
    ap.add_argument("datos_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis")
    a = ap.parse_args()
    if not a.salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    with open(a.datos_json, encoding="utf-8") as f:
        datos = json.load(f)
    analisis = {}
    if a.analisis:
        with open(a.analisis, encoding="utf-8") as f:
            analisis = json.load(f)
    hist_html = _historial.seccion("logs", Path(a.datos_json).resolve().parent, datos)
    # ES y EN: el inglés del agente va en el bloque "en" del analisis.json.
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

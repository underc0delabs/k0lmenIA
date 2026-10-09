#!/usr/bin/env python3
"""
Genera el Informe de seguridad web en HTML (dashboard, modo oscuro) a partir del resultado
de OWASP ZAP (zap.json, formato JSON tradicional) y, opcionalmente, del análisis del agente.

Uso:
    python scripts/generar_informe_seguridad.py <zap.json> <salida.html>
           [--url URL] [--historia HU-001] [--analisis analisis.json]

Los HALLAZGOS salen del zap.json (no se escriben a mano). El análisis (opcional) aporta:
{
  "veredicto": "Riesgo medio: corregir antes de salir",   // conclusión
  "veredicto_tono": "warn",                               // opcional: ok | warn | bad
  "resumen": "Resumen ejecutivo...",
  "falsos_positivos": [{"pluginid": "10021", "motivo": "El header lo agrega el proxy de producción"}],
  "notas": {"10038": "Afecta a todas las páginas: se resuelve en la configuración del servidor"},
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}

Riesgo de ZAP: Alto | Medio | Bajo | Informativo. El HTML es autocontenido (sin internet).
"""
import argparse
import datetime
import html as htmllib
import json
import re
import sys

from _estilos_reporte import e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, nivel_badge

RIESGOS = [(3, "Alto", "#F85149"), (2, "Medio", "#DB6D28"), (1, "Bajo", "#D29922"), (0, "Informativo", "#8B949E")]
NOMBRE_RIESGO = {c: n for c, n, _ in RIESGOS}
COLOR_RIESGO = {c: col for c, _, col in RIESGOS}
CONFIANZA = {"0": "Falso positivo", "1": "Baja", "2": "Media", "3": "Alta", "4": "Confirmada"}

CSS_EXTRA = """
<style>
.hallazgo{padding:18px 22px;border-top:1px solid var(--border)}
.hallazgo:first-child{border-top:0}
.hallazgo h3{font-size:16px;color:var(--ink);margin-bottom:6px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.hallazgo .lbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin:12px 0 4px}
.hallazgo p{color:var(--body)}
.hallazgo code,.mono{font-family:ui-monospace,Consolas,monospace;font-size:12.5px}
.hallazgo ul{margin-left:18px;color:var(--body)}
.hallazgo li{word-break:break-all}
.ev{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 10px;white-space:pre-wrap;word-break:break-all;color:var(--body)}
.fp{opacity:.6}
.tablecard{overflow-x:auto}
</style>
"""


def texto(html_zap):
    """ZAP manda descripción, solución y referencias con <p> y saltos: se pasan a texto plano."""
    t = re.sub(r"</p>\s*<p>|<br\s*/?>", "\n", html_zap or "")
    t = re.sub(r"<[^>]+>", "", t)
    return htmllib.unescape(t).strip()


def parrafos(html_zap):
    return "".join(f"<p>{e(p)}</p>" for p in texto(html_zap).split("\n") if p.strip())


def badge_riesgo(codigo):
    nombre = NOMBRE_RIESGO.get(codigo, "—")
    sev = {"Alto": "Crítica", "Medio": "Alta", "Bajo": "Media", "Informativo": "Baja"}.get(nombre)
    return nivel_badge(sev).replace(f">{sev}<", f">{nombre}<") if sev else nombre


def cargar_alertas(zap):
    alertas = []
    for sitio in zap.get("site") or []:
        for a in sitio.get("alerts") or []:
            a = dict(a)
            a["_sitio"] = sitio.get("@name", "")
            a["_riesgo"] = int(a.get("riskcode", 0) or 0)
            alertas.append(a)
    return sorted(alertas, key=lambda a: (-a["_riesgo"], -int(a.get("count", 0) or 0)))


def tono(veredicto, alertas):
    if veredicto:
        low = veredicto.lower()
        if "alto" in low or "crít" in low or "no apto" in low:
            return "bad"
        if "medio" in low or "observ" in low or "corregir" in low:
            return "warn"
        return "ok"
    if any(a["_riesgo"] == 3 for a in alertas):
        return "bad"
    return "warn" if any(a["_riesgo"] == 2 for a in alertas) else "ok"


def build_html(zap, analisis, url, historia):
    alertas = cargar_alertas(zap)
    falsos = {str(f.get("pluginid")): f.get("motivo", "") for f in analisis.get("falsos_positivos") or []}
    notas = {str(k): v for k, v in (analisis.get("notas") or {}).items()}
    validas = [a for a in alertas if str(a.get("pluginid")) not in falsos]

    body = []
    veredicto = analisis.get("veredicto")
    if not veredicto:
        alto = sum(1 for a in validas if a["_riesgo"] == 3)
        medio = sum(1 for a in validas if a["_riesgo"] == 2)
        veredicto = (f"{alto} hallazgo(s) de riesgo alto" if alto else f"{medio} hallazgo(s) de riesgo medio" if medio
                     else "Sin hallazgos de riesgo alto ni medio en el escaneo pasivo")
    body.append(banner(veredicto, analisis.get("veredicto_tono") or tono(analisis.get("veredicto"), validas)))

    cuenta = {c: sum(1 for a in validas if a["_riesgo"] == c) for c, _, _ in RIESGOS}
    kpis = kpi_tiles([
        ("Riesgo alto", cuenta[3], "bad" if cuenta[3] else "ok"),
        ("Riesgo medio", cuenta[2], "warn" if cuenta[2] else "ok"),
        ("Riesgo bajo", cuenta[1], ""),
        ("Informativos", cuenta[0], "blk"),
    ])
    body.append(f'<div style="margin-top:20px">{kpis}</div>')

    body.append(section("Alcance y método", f'''<div class="cardbody">
      <p><strong style="color:var(--ink)">Escaneo pasivo</strong> con OWASP ZAP (baseline): se recorrió el sitio con el spider y se analizaron
      las respuestas sin enviar ataques ni modificar datos. Detecta configuraciones y exposiciones visibles desde el cliente
      (encabezados de seguridad, cookies, información expuesta, contenido mixto…); <strong style="color:var(--ink)">no reemplaza</strong>
      un escaneo activo autorizado ni una prueba de penetración.</p>
      <p>Sitio: <span class="mono">{e(url or ", ".join(sorted({a["_sitio"] for a in alertas})) or "—")}</span> ·
      Versión de ZAP: {e(zap.get("@version", "—"))} · Generado por ZAP: {e(zap.get("@generated", "—"))}</p></div>'''))

    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    body.append(section("Hallazgos por riesgo", bar_chart([(n, cuenta[c], col) for c, n, col in RIESGOS])))

    if validas:
        filas = [[f'<a href="#a{e(a.get("pluginid"))}" style="color:var(--ink)">{e(a.get("name") or a.get("alert"))}</a>',
                  badge_riesgo(a["_riesgo"]), e(CONFIANZA.get(str(a.get("confidence")), "—")),
                  e(a.get("count") or len(a.get("instances") or [])), e(f'CWE-{a["cweid"]}' if a.get("cweid") not in (None, "", "-1", "0") else "—")]
                 for a in validas]
        body.append(section("Resumen de hallazgos", table(["Hallazgo", "Riesgo", "Confianza", "Instancias", "CWE"], filas)))

        detalle = []
        for a in validas:
            inst = a.get("instances") or []
            urls = "".join(f'<li><span class="mono">{e(i.get("method", ""))} {e(i.get("uri", ""))}</span>'
                           + (f' · parámetro <code>{e(i["param"])}</code>' if i.get("param") else "") + "</li>" for i in inst[:5])
            mas = f'<li class="muted">… y {len(inst) - 5} más</li>' if len(inst) > 5 else ""
            evid = next((i.get("evidence") for i in inst if i.get("evidence")), "")
            refs = [r for r in texto(a.get("reference")).split("\n") if r.strip()][:4]
            cwe = f'CWE-{a["cweid"]}' if a.get("cweid") not in (None, "", "-1", "0") else ""
            detalle.append(f'''<div class="hallazgo" id="a{e(a.get("pluginid"))}">
              <h3>{e(a.get("name") or a.get("alert"))} {badge_riesgo(a["_riesgo"])}
                <span class="muted" style="font-size:12px;font-weight:400">Confianza {e(CONFIANZA.get(str(a.get("confidence")), "—"))}{" · " + e(cwe) if cwe else ""} · regla {e(a.get("pluginid"))}</span></h3>
              <div class="lbl">Qué es</div>{parrafos(a.get("desc"))}
              {f'<div class="lbl">Análisis</div><p>{e(notas[str(a.get("pluginid"))])}</p>' if str(a.get("pluginid")) in notas else ""}
              <div class="lbl">Dónde ({len(inst)})</div><ul>{urls}{mas}</ul>
              {f'<div class="lbl">Evidencia</div><div class="ev">{e(evid[:400])}</div>' if evid else ""}
              <div class="lbl">Cómo se corrige</div>{parrafos(a.get("solution"))}
              {"<div class='lbl'>Referencias</div><ul>" + "".join(f"<li>{e(r)}</li>" for r in refs) + "</ul>" if refs else ""}
            </div>''')
        body.append(section("Detalle de cada hallazgo", "".join(detalle)))

    if falsos:
        filas = [[e(next((a.get("name") for a in alertas if str(a.get("pluginid")) == pid), pid)), e(motivo)] for pid, motivo in falsos.items()]
        body.append(section("Descartados como falsos positivos", table(["Hallazgo", "Motivo"], filas)))

    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(r.get("accion"))}</strong>', e(r.get("motivo")), nivel_badge(r.get("prioridad"))]
                 for r in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))

    meta_html = meta([("Historia", historia), ("Fecha", datetime.date.today().isoformat()), ("Herramienta", "OWASP ZAP · baseline pasivo")])
    return page("Informe de seguridad web", "Informe de seguridad", meta_html, CSS_EXTRA + "".join(body))


def main():
    ap = argparse.ArgumentParser(description="Informe HTML de seguridad a partir de zap.json")
    ap.add_argument("zap_json")
    ap.add_argument("salida")
    ap.add_argument("--url")
    ap.add_argument("--historia")
    ap.add_argument("--analisis", help="JSON con veredicto, resumen, falsos positivos, notas y recomendaciones")
    a = ap.parse_args()
    if not a.salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    with open(a.zap_json, encoding="utf-8") as f:
        zap = json.load(f)
    analisis = {}
    if a.analisis:
        with open(a.analisis, encoding="utf-8") as f:
            analisis = json.load(f)
    with open(a.salida, "w", encoding="utf-8") as f:
        f.write(build_html(zap, analisis, a.url, a.historia))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

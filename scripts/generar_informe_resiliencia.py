#!/usr/bin/env python3
"""
Genera el Informe de resiliencia en HTML (dashboard, modo oscuro) a partir de resiliencia.json
(npm run resiliencia) y, opcionalmente, del análisis del agente probador-resiliencia.

Uso:
    python scripts/generar_informe_resiliencia.py <resiliencia.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (pruebas, que aguantan, con hallazgos, pantallas en blanco, fallas
silenciosas, sin recuperación), la matriz página × escenario, los hallazgos por tipo y por escenario, cada
página con la carga normal y la captura de cada escenario (mensajes visibles, reintentos, errores de
JavaScript y recuperación), la tabla de hallazgos, la Falta información y la evolución de las corridas.

El análisis (opcional) aporta:
{
  "veredicto": "...", "veredicto_tono": "bad", "resumen": "...",
  "hallazgos": {"R-01": {"severidad": "Alta", "nota": "..."}},
  "descartados": [{"id": "R-05", "motivo": "..."}],
  "manuales": [{"id": "RM-01", "titulo": "...", "severidad": "Media", "escenario": "...", "pagina": "...",
                "pasos": ["..."], "esperado": "...", "obtenido": "...", "correccion": "...",
                "evidencia": "capturas/manual/rm-01.png"}],
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],   // "descripcion" vale como alias de que_falta
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import _historial
from _i18n import escribir_bilingue, idioma_actual, localizar  # noqa: E402,F401
from _estilos_reporte import (falta_informacion, avisar_analisis, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, two_col,
                              nivel_badge, _pastilla, miniatura, CRITICO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA

SEV = ["Crítica", "Alta", "Media", "Baja"]

# Sección "Evolución de las corridas": se registra acá para no tocar el resto de los tipos.
_historial.TIPOS.setdefault("resiliencia", {
    "archivo": "resiliencia.json", "items": lambda d: d.get("hallazgos") or [],
    "clave": lambda h: f'{h.get("escenario")}|{h.get("tipo")}|{h.get("pagina")}',
    "titulo": lambda h: f'{h.get("escenario")} · {h.get("titulo")}',
    "metricas": [("Hallazgos", _historial._r("hallazgos"), ""), ("Pantallas en blanco", _historial._r("pantallas_blanco"), ""),
                 ("Fallas silenciosas", _historial._r("fallas_silenciosas"), ""), ("Sin recuperación", _historial._r("sin_recuperacion"), "")]})

CSS_RE = """
<style>
.matriz td,.matriz th{text-align:center}
.matriz td:first-child,.matriz th:first-child{text-align:left}
.pag{border-top:1px solid var(--border-soft);padding:18px 24px}
.pag:first-child{border-top:0}
.pag h3{font-size:16px;color:var(--ink);display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.escs{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin-top:10px}
.esc{border:1px solid var(--border-soft);border-radius:12px;padding:10px}
.esc .thumb{display:grid;width:100%;height:170px;margin:6px 0}
.esc h4{font-size:13px;color:var(--ink);display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.esc ul{margin:4px 0 0 16px;font-size:12px;color:var(--muted)}
.descartado{opacity:.55}
</style>
"""

ESTADO = {"ok": ("Aguanta", OK, "✓"), "hallazgo": ("Con hallazgos", CRITICO, "✕"), "no-aplica": ("No aplica", NEUTRO, "–"), "error": ("Error", AVISO, "!")}


def estado_pill(estado, n=0):
    t, c, i = ESTADO.get(estado, (estado, NEUTRO, "?"))
    if estado == "hallazgo" and n:
        t = f"{n} hallazgo(s)"
    return _pastilla(t, c, i)


def build_html(datos, analisis, hist_html=""):
    ajustes = analisis.get("hallazgos") or {}
    desc = {str(d.get("id")): d.get("motivo") for d in analisis.get("descartados") or []}
    hallazgos = []
    for h in datos.get("hallazgos") or []:
        h = dict(h)
        a = ajustes.get(h["id"]) or {}
        if a.get("severidad") in SEV:
            h["severidad"] = a["severidad"]
        h["_nota"], h["_desc"] = a.get("nota"), desc.get(h["id"])
        hallazgos.append(h)
    manuales = analisis.get("manuales") or []
    vivos = [h for h in hallazgos if not h["_desc"]] + [dict(m, tipo="Exploración manual") for m in manuales]
    r = datos.get("resumen") or {}
    paginas = datos.get("paginas") or []
    escenarios = datos.get("escenarios") or []
    graves = [h for h in vivos if h.get("severidad") in ("Crítica", "Alta")]
    con_resultado = r.get("pruebas", 0) - r.get("no_aplica", 0) - r.get("errores", 0)
    if not con_resultado:
        tono, texto = "warn", "No hubo escenarios aplicables: la página no hace llamadas a la API ni carga recursos que fallar"
    elif graves:
        tono, texto = "bad", f"{len(graves)} problema(s) graves: la interfaz queda en blanco o no se recupera cuando algo falla"
    elif vivos:
        tono, texto = "warn", "La interfaz aguanta las fallas, pero hay que mejorar cómo avisa"
    else:
        tono, texto = "ok", "La interfaz aguanta bien las fallas simuladas"
    body = [banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono)]
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Pruebas", r.get("pruebas", 0), "", f'{r.get("paginas", 0)} página(s) × {r.get("escenarios", 0)} escenario(s) · {r.get("no_aplica", 0)} no aplican', "objetivo"),
        ("Aguantan", r.get("ok", 0), "ok" if not r.get("con_hallazgos") else "", f'{round(r.get("ok", 0) / con_resultado * 100) if con_resultado else 0} % de los escenarios aplicables', "ok",
         {"pct": r.get("ok", 0) / con_resultado * 100 if con_resultado else 0}),
        ("Con hallazgos", r.get("con_hallazgos", 0), ("bad" if graves else "warn") if r.get("con_hallazgos") else "ok", "escenarios en los que algo anduvo mal", "warn"),
        ("En blanco", r.get("pantallas_blanco", 0), "bad" if r.get("pantallas_blanco") else "ok", "la pantalla queda casi vacía", "bad"),
        ("Fallas silenciosas", r.get("fallas_silenciosas", 0), "warn" if r.get("fallas_silenciosas") else "ok", "algo falla y la persona no se entera", "bicho"),
        ("Sin recuperación", r.get("sin_recuperacion", 0), "bad" if r.get("sin_recuperacion") else "ok", "no vuelve a andar cuando vuelve la red", "bad"),
    ]) + "</div>")
    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    # Matriz página × escenario
    if paginas and escenarios:
        filas = []
        for p in paginas:
            por_esc = {x["escenario"]: x for x in p.get("resultados") or []}
            celdas = [f'<a href="#{e(p["id"])}" style="color:var(--ink)">{e(p["url"])}</a>']
            for s in escenarios:
                x = por_esc.get(s["id"])
                celdas.append(estado_pill(x["estado"], len(x.get("hallazgos") or [])) if x else "—")
            filas.append(celdas)
        body.append(section("Matriz página × escenario", f'<div class="matriz">{table(["Página"] + [e(s["nombre"]) for s in escenarios], filas)}</div>',
                            "qué pasó en cada página con cada falla simulada"))

    tipos = Counter(h["tipo"] for h in vivos)
    nombre_esc = {s["id"]: s["nombre"] for s in escenarios}
    por_esc = Counter(nombre_esc.get(h.get("escenario"), h.get("escenario") or "Manual") for h in vivos)
    body.append(two_col(
        section("Problemas por tipo", bar_chart([(t, k, SERIES[i % len(SERIES)]) for i, (t, k) in enumerate(tipos.most_common())], ancho_etiqueta=170)
                if tipos else '<p class="muted" style="padding:16px 24px">Sin problemas.</p>'),
        section("Problemas por escenario", bar_chart([(t, k, SERIES[(i + 2) % len(SERIES)]) for i, (t, k) in enumerate(por_esc.most_common())], ancho_etiqueta=230)
                if por_esc else '<p class="muted" style="padding:16px 24px">Sin problemas.</p>')))

    bloques = []
    for p in paginas:
        b = p.get("base") or {}
        tarjetas = []
        if p.get("captura_base"):
            tarjetas.append(f'<div class="esc"><h4>Carga normal {_pastilla("línea base", NEUTRO, "•")}</h4>{miniatura(p["captura_base"], p["url"] + " · carga normal")}'
                            f'<ul><li>{b.get("texto_len", 0)} caracteres · {b.get("elementos", 0)} elementos</li>'
                            f'<li>{len(b.get("llamadas_api") or [])} llamada(s) a la API · {b.get("tiempo_ms", 0)} ms</li></ul></div>')
        for x in p.get("resultados") or []:
            o = x.get("observado") or {}
            det = []
            if x["estado"] in ("no-aplica", "error"):
                det.append(e(x.get("motivo") or ""))
            else:
                det.append(f'{o.get("texto_len", 0)} caracteres · {o.get("elementos", 0)} elementos · {x.get("interceptados", 0)} pedido(s) intervenidos')
                det.append("Mensajes: " + (" · ".join(f"“{e(m)}”" for m in o.get("mensajes") or []) or "ninguno"))
                if x.get("reintentos"):
                    det.append(f'Reintentos: {x["reintentos"]} ({e(x.get("reintentos_url"))})')
                if x.get("errores_js"):
                    det.append(f'Errores de JavaScript: {len(x["errores_js"])} · {e(x["errores_js"][0])}')
                rec = x.get("recuperacion") or {}
                if rec.get("recupera") is not None:
                    det.append("Se recupera al volver la red: " + ("sí" if rec["recupera"] else "<b>no</b>"))
                if x.get("nota"):
                    det.append(e(x["nota"]))
            img = miniatura(x["captura"], f'{p["url"]} · {x["nombre"]}') if x.get("captura") else ""
            tarjetas.append(f'<div class="esc"><h4>{e(x["nombre"])} {estado_pill(x["estado"], len(x.get("hallazgos") or []))}</h4>{img}'
                            f'<ul>{"".join(f"<li>{d}</li>" for d in det)}</ul></div>')
        bloques.append(f'<div class="pag" id="{e(p["id"])}"><h3>{e(b.get("titulo") or p["url"])}</h3><p class="muted mono">{e(p["url"])}</p>'
                       f'<div class="escs">{"".join(tarjetas)}</div></div>')
    if bloques:
        body.append(section("Cada página", "".join(bloques), "la carga normal y lo que se vio en cada escenario"))

    if hallazgos or manuales:
        filas = [[e(h["id"]), nivel_badge(h["severidad"]), e(h["tipo"]), e(nombre_esc.get(h.get("escenario"), h.get("escenario"))),
                  f'<strong style="color:var(--ink)">{e(h["titulo"])}</strong><div class="muted">{e(h.get("detalle"))}</div>'
                  + (f'<div><i>{e(h["_nota"])}</i></div>' if h.get("_nota") else "") + (f'<div class="muted">Descartado: {e(h["_desc"])}</div>' if h.get("_desc") else ""),
                  miniatura(h["captura"], h["titulo"]) if h.get("captura") else "—"] for h in hallazgos]
        filas += [[e(m.get("id")), nivel_badge(m.get("severidad")), "Exploración manual", e(m.get("escenario")),
                   f'<strong style="color:var(--ink)">{e(m.get("titulo"))}</strong><div class="muted mono">{e(m.get("pagina") or "")}</div>'
                   f'<div class="muted">Pasos: {e(" → ".join(map(str, m["pasos"])) if isinstance(m.get("pasos"), list) else m.get("pasos"))}</div>'
                   f'<div class="muted">Esperado: {e(m.get("esperado"))} · Obtenido: {e(m.get("obtenido"))}</div>'
                   + (f'<div><b>Cómo corregirlo:</b> {e(m["correccion"])}</div>' if m.get("correccion") else ""),
                   miniatura(m["evidencia"], m.get("titulo")) if m.get("evidencia") else "—"] for m in manuales]
        body.append(section("Hallazgos", table(["ID", "Severidad", "Tipo", "Escenario", "Hallazgo", "Evidencia"], filas)))
    body.append(falta_informacion(analisis.get("falta_informacion"), "cómo tiene que reaccionar la app ante una falla, cuando ninguna fuente lo define"))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    if hist_html:
        body.append(hist_html)
    m = meta([("Historia", datos.get("historia")), ("Sitio", datos.get("host")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
              ("Espera por escenario", f'{round((datos.get("timeout_ms") or 0) / 1000)} s'), ("API", datos.get("patron_api") or "fetch / XHR")])
    return page("Resiliencia", "Resiliencia de la interfaz", m, CSS_EXTRA + CSS_RE + "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de resiliencia a partir de resiliencia.json")
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
        avisar_analisis(analisis, [h.get("id") for h in datos.get("hallazgos") or []])
    hist_html = _historial.seccion("resiliencia", Path(a.datos_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

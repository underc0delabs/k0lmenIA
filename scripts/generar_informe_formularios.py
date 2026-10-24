#!/usr/bin/env python3
"""
Genera el Informe de validaciones de formularios en HTML (dashboard, modo oscuro) a partir de formularios.json
(npm run formularios) y, opcionalmente, del análisis del agente probador-formularios.

Uso:
    python scripts/generar_informe_formularios.py <formularios.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (formularios, campos, pruebas, porcentaje que pasa, valores inválidos
aceptados, valores válidos rechazados, hallazgos), las pruebas por campo, los problemas por tipo, cada
formulario con la captura antes y con los errores a la vista y la matriz campo × prueba (valor, qué se
esperaba, qué pasó y el mensaje), la tabla de hallazgos y la evolución de las corridas.

El análisis (opcional) aporta:
{
  "veredicto": "...", "veredicto_tono": "bad", "resumen": "...",
  "hallazgos": {"V-01": {"severidad": "Alta", "nota": "..."}},
  "descartados": [{"id": "V-12", "motivo": "..."}],
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
from _estilos_reporte import (falta_informacion, avisar_analisis, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, stacked_bars, two_col,
                              nivel_badge, _pastilla, miniatura, CRITICO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA

SEV = ["Crítica", "Alta", "Media", "Baja"]
RES = {"rechaza": "Rechaza", "acepta": "Acepta", "corta": "Corta"}

CSS_FO = """
<style>
.form{border-top:1px solid var(--border-soft);padding:18px 24px}
.form:first-child{border-top:0}
.form h3{font-size:16px;color:var(--ink);display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.capturas{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:8px 0 14px}
.capturas figure{margin:0}
.capturas figcaption{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin-bottom:6px}
.capturas .thumb{display:grid;width:100%;height:260px}
.campo{font-weight:650;color:var(--ink)}
.campo small{display:block;font-weight:400;color:var(--muted);font-family:var(--mono);font-size:11.5px}
.descartado{opacity:.55}
</style>
"""


def res_pill(p):
    if p["ok"] is None:
        return _pastilla(RES.get(p["resultado"], p["resultado"]) + " · informativo", NEUTRO, "–")
    return _pastilla(RES.get(p["resultado"], p["resultado"]), OK if p["ok"] else CRITICO, "✓" if p["ok"] else "✕")


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
    vivos = [h for h in hallazgos if not h["_desc"]]
    r = datos.get("resumen") or {}
    forms = datos.get("formularios") or []
    graves = [h for h in vivos if h["severidad"] in ("Crítica", "Alta")]
    if not forms:
        tono, texto = "warn", "No encontré formularios en las páginas revisadas"
    elif graves:
        tono, texto = "bad", f'{len(graves)} problema(s) graves: el formulario acepta datos inválidos o rechaza datos válidos'
    elif vivos:
        tono, texto = "warn", "Las validaciones funcionan; hay detalles de mensajes, etiquetas y tipos de campo"
    else:
        tono, texto = "ok", "Los formularios validan bien"
    body = [banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono)]
    n = r.get("pruebas", 0)
    con_res = n - sum(1 for f in forms for c in f["campos"] for p in c["pruebas"] if p["ok"] is None)
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Formularios", r.get("formularios", 0), "", f'{r.get("campos", 0)} campos en {r.get("paginas", 0)} página(s)', "lista"),
        ("Pruebas", n, "", "sin enviar nada: completar, salir del campo y mirar", "objetivo"),
        ("Pasan", r.get("pruebas_ok", 0), "ok" if not r.get("pruebas_fallan") else "", f'{round(r.get("pruebas_ok", 0) / con_res * 100) if con_res else 0} % de las pruebas con resultado esperado', "ok",
         {"pct": r.get("pruebas_ok", 0) / con_res * 100 if con_res else 0}),
        ("Acepta inválidos", r.get("acepta_invalidos", 0), "bad" if r.get("acepta_invalidos") else "ok", "datos incorrectos que llegarían a la base", "bad"),
        ("Rechaza válidos", r.get("rechaza_validos", 0), "bad" if r.get("rechaza_validos") else "ok", "personas que no pueden completar el formulario", "bicho"),
        ("Hallazgos", len(vivos), "bad" if graves else ("warn" if vivos else "ok"), f"{len(graves)} graves", "warn"),
    ]) + "</div>")
    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))
    filas = [(f'{c.get("etiqueta") or c["nombre"]}'[:30], [sum(1 for p in c["pruebas"] if p["ok"] is True), sum(1 for p in c["pruebas"] if p["ok"] is False)])
             for f in forms for c in f["campos"] if c["pruebas"]]
    tipos = Counter(h["tipo"] for h in vivos)
    body.append(two_col(section("Pruebas por campo", stacked_bars(filas, [("Pasa", OK), ("Falla", CRITICO)]) if filas else '<p class="muted" style="padding:16px 24px">—</p>'),
                        section("Problemas por tipo", bar_chart([(t, k, SERIES[i % len(SERIES)]) for i, (t, k) in enumerate(tipos.most_common())], ancho_etiqueta=170)
                                if tipos else '<p class="muted" style="padding:16px 24px">Sin problemas.</p>')))
    bloques = []
    for f in forms:
        caps = ""
        for et, k in (("Antes", "captura"), ("Con los valores inválidos", "captura_errores"), ("Al enviarlo vacío", "captura_envio_vacio")):
            if f.get(k):
                caps += f'<figure><figcaption>{e(et)}</figcaption>{miniatura(f[k], f["id"] + " · " + et)}</figure>'
        filas = []
        for c in f["campos"]:
            restr = " · ".join(x for x in [c["tipo"], "obligatorio" if c["requerido"] else "", f'máx {c["maxlength"]}' if c.get("maxlength") else "",
                                           f'mín {c["minlength"]}' if c.get("minlength") else "", f'rango {c.get("min")}–{c.get("max")}' if c.get("min") is not None or c.get("max") is not None else ""] if x)
            campo = f'<div class="campo">{e(c.get("etiqueta") or c["nombre"])}<small>{e(restr)}</small></div>'
            if not c["pruebas"]:
                filas.append([campo, '<span class="muted">sin pruebas para este tipo</span>', "", "", "", ""])
            for i, p in enumerate(c["pruebas"]):
                filas.append([campo if i == 0 else "", e(p["regla"]), f'<span class="mono">{e(p["valor"])}</span>', e(p["esperado"]), res_pill(p),
                              e(p.get("mensaje") or "—") + (f' <span class="muted">({e(p["fuente"])})</span>' if p.get("fuente") else "")])
        extra = f'<p class="muted">Después de enviarlo vacío quedó en <span class="mono">{e(f.get("url_despues_de_enviar"))}</span></p>' if f.get("url_despues_de_enviar") else ""
        color = CRITICO if any(h["severidad"] in ("Alta", "Crítica") for h in f["hallazgos"]) else AVISO if f["hallazgos"] else OK
        estado = _pastilla("%d hallazgo(s)" % len(f["hallazgos"]), color, "!" if f["hallazgos"] else "✓")
        bloques.append(f'<div class="form" id="{e(f["id"])}"><h3>{e(f["id"])} · {e(f["nombre"])} <span class="muted mono">{e(f.get("metodo") or "")} {e(f.get("accion") or "")}</span>'
                       f'{estado}</h3>'
                       f'<p class="muted mono">{e(f["url"])}</p><div class="capturas">{caps}</div>{extra}'
                       f'{table(["Campo", "Prueba", "Valor", "Esperado", "Resultado", "Mensaje"], filas)}</div>')
    if bloques:
        body.append(section("Cada formulario", "".join(bloques), "campo × prueba: qué se probó, qué se esperaba y qué hizo el formulario"))
    if hallazgos:
        filas = [[e(h["id"]), nivel_badge(h["severidad"]), e(h["tipo"]),
                  f'<strong style="color:var(--ink)">{e(h["titulo"])}</strong><div class="muted">{e(h.get("detalle"))}</div>'
                  + (f'<div><i>{e(h["_nota"])}</i></div>' if h.get("_nota") else "") + (f'<div class="muted">Descartado: {e(h["_desc"])}</div>' if h.get("_desc") else ""),
                  f'<a href="#{e(h["formulario"])}" style="color:var(--ink)">{e(h["formulario"])}</a>'] for h in hallazgos]
        body.append(section("Hallazgos", table(["ID", "Severidad", "Tipo", "Hallazgo", "Formulario"], filas)))
    body.append(falta_informacion(analisis.get("falta_informacion")))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    if hist_html:
        body.append(hist_html)
    m = meta([("Historia", datos.get("historia")), ("Sitio", datos.get("host")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
              ("Envío vacío", "sí" if datos.get("envio_vacio") else "no")])
    return page("Formularios", "Validaciones de formularios", m, CSS_EXTRA + CSS_FO + "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de formularios a partir de formularios.json")
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
    hist_html = _historial.seccion("formularios", Path(a.datos_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

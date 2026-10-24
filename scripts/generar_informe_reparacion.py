#!/usr/bin/env python3
"""
Genera el Informe de reparación de la automatización en HTML (dashboard, modo oscuro) a partir de
reparaciones.json (npm run reparar) y, opcionalmente, del análisis del agente reparador-automatizacion.

Uso:
    python scripts/generar_informe_reparacion.py <reparaciones.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (fallas analizadas, con propuesta, aplicadas, verificadas, siguen
fallando, posibles bugs y esperas), el recorrido de las reparaciones (analizadas → con propuesta →
aplicadas → verificadas), los diagnósticos, la tabla de reparaciones y el detalle de cada una: el
paso y el error, dónde está el locator (archivo y línea), el cambio propuesto o aplicado como diff,
los candidatos con su puntaje, la captura del DOM con el elemento original (rojo) y el propuesto
(verde), el riesgo (si puede ser un bug) y el resultado de la verificación; al final, el diff completo.

El análisis (opcional) aporta:
{
  "veredicto": "2 locators reparados y verificados; 1 posible bug", "veredicto_tono": "warn",
  "resumen": "Resumen para alguien no técnico...",
  "reparaciones": {"R-01": {"decision": "Posible bug", "nota": "La historia pide la sección de cupones"}},
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
Decisiones: Aplicar · Posible bug · Arreglo manual · Descartar
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import _historial
from _i18n import escribir_bilingue, idioma_actual, localizar  # noqa: E402,F401
from _estilos_reporte import (e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, donut_panel, two_col,
                              nivel_badge, _pastilla, miniatura, CRITICO, AVISO, NEUTRO, OK, SERIO, SERIES)
from generar_informe_exploratorio import CSS_EXTRA

ESTADO = {"Verificada": (OK, "✓"), "Aplicada": (SERIES[2], "●"), "Propuesta": (AVISO, "◷"), "Sigue fallando": (CRITICO, "✕"),
          "Sin propuesta": (NEUTRO, "–"), "Sin resultado": (NEUTRO, "?")}
CONFIANZA = {"Alta": (OK, "▲"), "Media": (AVISO, "●"), "Baja": (SERIO, "▼")}
DIAGNOSTICOS = ["Ya no existe", "Coincide con varios", "Existe pero no se ve", "Existe y se ve", "Sin DOM guardado", "Sin locator en el error"]
COLOR_DIAG = {d: SERIES[i] for i, d in enumerate(DIAGNOSTICOS)}
QUE_ES = {
    "Ya no existe": "el locator no encuentra nada: cambió el texto, el rol o el atributo",
    "Coincide con varios": "encuentra más de un elemento: hay que hacerlo más específico",
    "Existe pero no se ve": "está oculto: falta un paso previo o la app no lo muestra",
    "Existe y se ve": "el locator está bien: falló la espera o la verificación",
    "Sin DOM guardado": "no hay DOM de la falla para analizar",
    "Sin locator en el error": "no es una falla de locator",
}

CSS_REP = """
<style>
.diff{margin:6px 0 4px;border:1px solid var(--border);border-radius:10px;overflow:auto;background:#120F0B;
  font-family:var(--mono);font-size:12.5px;line-height:1.65}
.diff div{padding:1px 14px;white-space:pre}
.diff .h{color:var(--muted);background:rgba(244,239,230,.03)}
.diff .del{background:rgba(255,90,78,.16);color:#FFB8B0}
.diff .add{background:rgba(92,191,74,.16);color:#C6EDB9}
.diff .ctx{color:var(--body)}
.err{background:#120F0B;border:1px solid var(--border);border-radius:10px;padding:12px 14px;white-space:pre-wrap;word-break:break-word;
  font-family:var(--mono);font-size:12px;color:#FFB8B0;max-height:220px;overflow:auto}
.code{font-family:var(--mono);font-size:12px;color:var(--ink);background:var(--tile);border:1px solid var(--border);
  border-radius:7px;padding:3px 8px;display:inline-block;word-break:break-all}
.code.old{color:#FFB8B0;text-decoration:line-through;text-decoration-color:rgba(255,184,176,.5)}
.code.new{color:#C6EDB9}
.flecha{color:var(--muted);margin:0 6px}
.score{display:flex;align-items:center;gap:8px;min-width:120px}
.score .t{flex:1;height:6px;border-radius:99px;background:rgba(244,239,230,.06);overflow:hidden}
.score .t span{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,rgba(249,176,6,.5),#F9B006)}
.score b{font-family:var(--mono);font-size:12px;color:var(--ink);min-width:26px;text-align:right}
.aviso{border:1px solid rgba(255,214,10,.35);background:rgba(255,214,10,.07);border-radius:10px;padding:10px 14px;color:#FFE58A;margin-top:10px}
.capturas{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:8px}
.capturas figure{margin:0}
.capturas figcaption{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin-bottom:6px}
.capturas img{display:block;width:100%;max-height:320px;object-fit:contain;object-position:left top;border-radius:8px;border:1px solid var(--border);background:#fff}
.cmd{font-family:var(--mono);font-size:12.5px;color:var(--ink)}
@media (max-width:720px){.capturas{grid-template-columns:1fr}}
</style>
"""


ANSI = re.compile(r"\x1b\[[0-9;]*m")  # colores de la terminal en los errores de Playwright


def pill(mapa, valor):
    color, ic = mapa.get(valor, (NEUTRO, "●"))
    return _pastilla(valor or "—", color, ic)


def score(p):
    return f'<div class="score"><div class="t"><span style="width:{max(0, min(100, p or 0))}%"></span></div><b>{e(p)}</b></div>'


def preview(r):
    """Línea antes y después (la aplicada o la que quedaría si se aplica)."""
    if r.get("aplicada"):
        return r["aplicada"]["antes"], r["aplicada"]["despues"]
    u, prop = r.get("ubicacion") or {}, r.get("propuesta") or {}
    if not u or not prop:
        return None, None
    antes = u.get("texto") or ""
    if u.get("tipo") == "feature":
        inp = prop.get("input") or {}
        nuevo = next((inp[k] for k in ("name", "text", "label", "placeholder", "testId") if k in inp), None)
        return antes, antes.replace(f'"{u.get("valor")}"', f'"{nuevo}"') if nuevo else None
    objs = re.findall(r"\{[^{}]*\}", antes)
    vals = [v for v in ((r.get("locator") or {}).get("input") or {}).values() if isinstance(v, str)]
    obj = next((o for o in objs if all(v in o for v in vals)), None)
    return antes, antes.replace(obj, prop["codigo"]) if obj else None


def diff_html(antes, despues, titulo=""):
    filas = [f'<div class="h">{e(titulo)}</div>'] if titulo else []
    filas += [f'<div class="del">- {e(antes)}</div>', f'<div class="add">+ {e(despues)}</div>']
    return f'<div class="diff">{"".join(filas)}</div>'


def diff_completo(texto):
    filas = []
    for l in texto.splitlines():
        cls = "h" if l.startswith(("---", "+++", "@@")) else "del" if l.startswith("-") else "add" if l.startswith("+") else "ctx"
        filas.append(f'<div class="{cls}">{e(l) or "&nbsp;"}</div>')
    return f'<div class="cardbody"><div class="diff">{"".join(filas)}</div></div>'


def detalle(r, a):
    u = r.get("ubicacion") or {}
    loc = r.get("locator") or {}
    prop = r.get("propuesta") or {}
    estado = (r.get("verificacion") or {}).get("estado") or r.get("estado") or ("Propuesta" if prop else "Sin propuesta")
    partes = [f'<div class="hallazgo" id="{e(r["id"])}"><h3>{e(r["id"])} · {e(r["escenario"])} {pill(ESTADO, estado)}'
              f'{" " + pill(CONFIANZA, prop.get("confianza")) if prop else ""}</h3>',
              f'<p class="muted mono">{e(" · ".join(x for x in [r.get("historia"), r.get("caso"), r.get("uri")] if x))}:{e(r.get("linea"))}</p>',
              f'<div class="lbl">Paso que falló ({e(r.get("accion"))})</div><p class="mono" style="color:var(--ink)">{e(r.get("paso") or "—")}</p>']
    if r.get("error"):
        partes.append(f'<div class="lbl">Error</div><div class="err">{e(chr(10).join(ANSI.sub("", r["error"]).splitlines()[:8]))}</div>')
    partes.append(f'<div class="lbl">Diagnóstico · {e(r.get("diagnostico"))}</div><p>{e(r.get("detalle"))}</p>')
    if loc:
        partes.append(f'<div class="lbl">Locator</div><p><span class="code old">{e(loc.get("codigo"))}</span>'
                      + (f'<span class="flecha">→</span><span class="code new">{e(prop.get("codigo"))}</span>' if prop else "") + "</p>")
    if prop.get("motivos"):
        partes.append(f'<p class="muted">Por qué: {e("; ".join(prop["motivos"]))}</p>')
    if u:
        donde = f'{u.get("archivo")}:{u.get("linea")}' + (f' · clave {u["clave"]}' if u.get("clave") else "")
        tipo = {"locator": "archivo de locators", "feature": "dato del .feature", "step": "escrito en un step"}.get(u.get("tipo"), u.get("tipo"))
        partes.append(f'<div class="lbl">Dónde está ({e(tipo)})</div><p class="mono">{e(donde)}</p>')
        antes, despues = preview(r)
        if antes and despues:
            partes.append(diff_html(antes, despues, "cambio aplicado" if r.get("aplicada") else "cambio propuesto (todavía sin aplicar)"))
    elif loc:
        partes.append('<div class="aviso">No encontré dónde está el locator (puede armarse en tiempo de ejecución): cambialo a mano.</div>')
    if r.get("riesgo"):
        partes.append(f'<div class="aviso">⚠ {e(r["riesgo"])}</div>')
    if r.get("sugerencia_espera"):
        partes.append(f'<div class="lbl">Qué hacer</div><p>{e(r["sugerencia_espera"])}</p>')
    if a.get("decision") or a.get("nota"):
        partes.append(f'<div class="lbl">Decisión del análisis</div><p><strong style="color:var(--ink)">{e(a.get("decision") or "")}</strong> {e(a.get("nota") or "")}</p>')
    caps = ""
    if r.get("captura_original"):
        caps += f'<figure><figcaption>Lo que encuentra el locator original</figcaption><a class="lb" href="{e(r["captura_original"])}" title="{e(r["id"])} · original"><img src="{e(r["captura_original"])}" loading="lazy" alt="Original"></a></figure>'
    if r.get("captura"):
        caps += f'<figure><figcaption>Elemento propuesto</figcaption><a class="lb" href="{e(r["captura"])}" title="{e(r["id"])} · propuesta"><img src="{e(r["captura"])}" loading="lazy" alt="Propuesta"></a></figure>'
    if caps:
        partes.append(f'<div class="lbl">En la página guardada al fallar</div><div class="capturas">{caps}</div>')
    if r.get("candidatos"):
        filas = []
        for c in r["candidatos"][:6]:
            mejor = c.get("mejor") or {}
            filas.append([score(c.get("puntaje")), e(c.get("rol") or c.get("tag")), f'<span style="color:var(--ink)">{e((c.get("nombre") or c.get("texto") or "")[:60])}</span>',
                          f'<span class="code">{e(mejor.get("codigo") or "—")}</span>', "Sí" if mejor else "No", e(", ".join(c.get("motivos") or []))])
        partes.append('<div class="lbl">Candidatos en la página</div>' + table(["Puntaje", "Rol", "Nombre", "Locator", "Único", "Por qué"], filas))
    if r.get("alternativas") and len(r["alternativas"]) > 1:
        partes.append('<div class="lbl">Alternativas (una por elemento)</div><ul>' + "".join(
            f'<li><span class="code">{e(x["codigo"])}</span> <span class="muted">· {e(x.get("referencia"))}</span></li>' for x in r["alternativas"][:8]) + "</ul>")
    v = r.get("verificacion")
    if v:
        partes.append(f'<div class="lbl">Verificación</div><p>{pill(ESTADO, v.get("estado"))} <span class="muted">{e((v.get("fecha") or "")[:16].replace("T", " "))}</span></p>')
        if v.get("error"):
            partes.append(f'<div class="err">{e(chr(10).join(ANSI.sub("", v["error"]).splitlines()[:8]))}</div>')
    partes.append("</div>")
    return "".join(partes)


def build_html(datos, analisis, carpeta=None, hist_html=""):
    rs = datos.get("reparaciones") or []
    r = datos.get("resumen") or {}
    ajustes = analisis.get("reparaciones") or {}
    body = []
    n = r.get("fallas", len(rs))
    ver, sig, apl, prop = r.get("verificadas", 0), r.get("siguen_fallando", 0), r.get("aplicadas", 0), r.get("con_propuesta", 0)
    if not n:
        tono, texto = "ok", "No hay fallas web para reparar"
    elif sig:
        tono, texto = "bad", f"{sig} reparación(es) aplicadas siguen fallando"
    elif ver and ver == apl:
        tono, texto = "ok", f"{ver} reparación(es) aplicadas y verificadas" + (f"; {n - ver} falla(s) quedan para revisar" if n > ver else "")
    elif apl:
        tono, texto = "warn", f"{apl} reparación(es) aplicadas, falta verificarlas (npm run reparar -- --verificar)"
    elif prop:
        tono, texto = "warn", f"{prop} de {n} falla(s) tienen una reparación propuesta, sin aplicar todavía"
    else:
        tono, texto = "warn", "No hay reparaciones automáticas posibles: revisá el detalle de cada falla"
    body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Fallas analizadas", n, "", f'{r.get("de_locator", 0)} de locator · origen: {datos.get("origen_tipo", "")}', "lupa"),
        ("Con propuesta", prop, "ok" if prop and prop == r.get("de_locator") else ("warn" if prop else ""),
         f'{r.get("confianza_alta", 0)} con confianza alta', "llave", {"pct": prop / n * 100 if n else 0}),
        ("Aplicadas", apl, "" if not apl else "ok", "cambios escritos en el código", "codigo"),
        ("Verificadas", ver, "ok" if ver and ver == apl else ("warn" if apl else ""), "pasan después de repararlas", "ok", {"pct": ver / apl * 100 if apl else 0}),
        ("Siguen fallando", sig, "bad" if sig else "ok", "aplicadas que no alcanzaron", "bad"),
        ("Posibles bugs", r.get("posibles_bugs", 0), "warn" if r.get("posibles_bugs") else "ok", "verificaciones que no encuentran el elemento", "bicho"),
        ("Esperas", r.get("espera", 0), "warn" if r.get("espera") else "", "el locator está bien: falló el tiempo", "reloj"),
        ("Sin propuesta", r.get("sin_propuesta", 0), "warn" if r.get("sin_propuesta") else "ok", "revisar a mano", "lista"),
    ]) + "</div>")
    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    if rs:
        cuenta = Counter(x.get("diagnostico") for x in rs)
        segs = [(cuenta[d], COLOR_DIAG[d], d) for d in DIAGNOSTICOS if cuenta[d]]
        principal = max(segs, key=lambda s: s[0])
        recorrido = bar_chart([("Analizadas", n, SERIES[2]), ("Con propuesta", prop, SERIES[1]), ("Aplicadas", apl, SERIES[4]), ("Verificadas", ver, OK)],
                              ancho_etiqueta=130)
        body.append(two_col(section("Recorrido de las reparaciones", recorrido, "de la falla al test que vuelve a pasar"),
                            section("Diagnósticos", donut_panel(segs, round(principal[0] / len(rs) * 100), principal[2][:16].lower()))))
        filas = []
        for x in rs:
            loc = (x.get("locator") or {}).get("codigo")
            p = (x.get("propuesta") or {}).get("codigo")
            cambio = (f'<span class="code old">{e(loc)}</span>' if loc else '<span class="muted">—</span>') + \
                (f'<div style="margin-top:6px"><span class="code new">{e(p)}</span></div>' if p else "")
            estado = (x.get("verificacion") or {}).get("estado") or x.get("estado") or "Sin propuesta"
            filas.append([f'<a class="id" href="#{e(x["id"])}" style="color:var(--ink)">{e(x["id"])}</a>',
                          f'<strong style="color:var(--ink)">{e(x["escenario"])}</strong><div class="muted">{e(" · ".join(y for y in [x.get("historia"), x.get("caso")] if y))}</div>',
                          f'<span class="cat"><i style="background:{COLOR_DIAG.get(x.get("diagnostico"), NEUTRO)}"></i>{e(x.get("diagnostico"))}</span>'
                          f'<div class="muted" style="margin-top:4px">{e(QUE_ES.get(x.get("diagnostico"), ""))}</div>',
                          cambio, pill(CONFIANZA, (x.get("propuesta") or {}).get("confianza")) if x.get("propuesta") else '<span class="muted">—</span>',
                          pill(ESTADO, estado)])
        body.append(section("Reparaciones", table(["ID", "Escenario", "Diagnóstico", "Locator → propuesta", "Confianza", "Estado"], filas),
                            "clic en el ID para ver el detalle, las capturas y el cambio"))
        body.append(section("Detalle de cada reparación", "".join(detalle(x, ajustes.get(x["id"]) or {}) for x in rs)))

    if carpeta and (Path(carpeta) / "cambios.diff").exists():
        texto = (Path(carpeta) / "cambios.diff").read_text(encoding="utf-8").strip()
        if texto:
            body.append(section("Cambios aplicados (diff)", diff_completo(texto), "copia de los archivos originales en respaldo/"))

    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    hu = f' --historia {datos["historia"]}' if datos.get("historia") else ""
    filas = [["Aplicar las de confianza alta en pasos de acción", f'<span class="cmd">npm run reparar -- --aplicar seguras{e(hu)}</span>'],
             ["Aplicar algunas en particular", f'<span class="cmd">npm run reparar -- --aplicar R-01,R-03{e(hu)}</span>'],
             ["Verificarlas (corre los escenarios reparados)", f'<span class="cmd">npm run reparar -- --verificar{e(hu)}</span>'],
             ["Volver atrás", "restaurar el archivo desde respaldo/ (o git checkout del archivo)"]]
    if (datos.get("verificacion") or {}).get("reporte"):
        filas.append(["Reporte de Cucumber de la verificación", f'<a href="{e(datos["verificacion"]["reporte"])}" style="color:var(--ink)">{e(datos["verificacion"]["reporte"])}</a>'])
    body.append(section("Cómo seguir", table(["Para", "Comando"], filas)))

    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Historia", datos.get("historia")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
                      ("Origen", datos.get("origen")), ("Herramienta", datos.get("herramienta"))])
    css_cat = ('<style>.cat{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:650;padding:4px 11px;border-radius:999px;'
               'background:var(--tile);border:1px solid var(--border);color:var(--ink);white-space:nowrap}.cat i{width:9px;height:9px;border-radius:3px}</style>')
    return page("Reparación de la automatización", "Reparador de la automatización", meta_html, CSS_EXTRA + CSS_REP + css_cat + "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de reparación de la automatización a partir de reparaciones.json")
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
    hist_html = _historial.seccion("reparacion", Path(a.datos_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), Path(a.datos_json).parent, hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

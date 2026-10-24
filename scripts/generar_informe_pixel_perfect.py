#!/usr/bin/env python3
"""
Genera el Informe de regresión visual (pixel perfect) en HTML (dashboard, modo oscuro) a partir de
pixel-perfect.json (npm run pixel-perfect) y, opcionalmente, del análisis del agente pixel-perfect.

Uso:
    python scripts/generar_informe_pixel_perfect.py <pixel-perfect.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (pantallas comparadas, sin cambios, con cambios, elementos
corridos, faltantes y nuevos, mayor diferencia), diferencia por pantalla, hallazgos por tipo y
severidad, la matriz página × resolución, cada pantalla con el comparador deslizable (referencia
contra actual, o contra el mapa de diferencias), las regiones con cambios de cerca y el antes y
después de cada hallazgo, la tabla de hallazgos y los datos de la referencia.

El análisis (opcional) aporta:
{
  "veredicto": "El botón de compra se corrió en mobile", "veredicto_tono": "bad",
  "resumen": "Resumen para alguien no técnico...",
  "hallazgos": {"V-01": {"intencional": true, "nota": "Cambio pedido en HU-014"},
                "V-02": {"severidad": "Alta", "nota": "Tapa el precio en 390px"}},
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],   // "descripcion" vale como alias de que_falta
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
Los hallazgos marcados como intencionales no cuentan como defectos: se listan aparte y se aceptan
como nueva referencia (npm run pixel-perfect -- --aceptar <pantalla>).
"""
import argparse
import json
from pathlib import Path
import sys
from collections import Counter

import _historial
from _i18n import escribir_bilingue, idioma_actual, localizar  # noqa: E402,F401
from _estilos_reporte import (falta_informacion, avisar_analisis, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, column_chart, donut_panel,
                              two_col, nivel_badge, _pastilla, miniatura, NIVEL_COLOR, CRITICO, AVISO, NEUTRO, OK, SERIO, SERIES)
from generar_informe_exploratorio import CSS_EXTRA

TIPOS = ["Bloque desplazado", "Elemento corrido", "Elemento faltante", "Texto cambiado", "Cambio de estilo",
         "Cambio de tamaño", "Elemento nuevo", "Cambio visual", "Alto de la página"]
COLOR_TIPO = {t: SERIES[i % len(SERIES)] for i, t in enumerate(TIPOS)}
ESTADO = {"Sin cambios": (OK, "✓"), "Cambios menores": (AVISO, "!"), "Con cambios": (CRITICO, "✕"), "Nueva": (NEUTRO, "+"),
          "Referencia": (SERIES[2], "◎"), "Error": (NEUTRO, "⊘")}
SEV = ["Crítica", "Alta", "Media", "Baja"]

CSS_PP = """
<style>
.comp-wrap{padding:18px 24px 6px}
.comp-bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px;font-size:12.5px;color:var(--muted)}
.comp-bar .lado{display:inline-flex;align-items:center;gap:6px;color:var(--ink);font-weight:600}
.comp-bar .lado i{width:9px;height:9px;border-radius:3px;display:inline-block}
.comp-bar input[type=range]{flex:1;min-width:160px;accent-color:var(--accent)}
.comp-bar button{background:var(--tile);border:1px solid var(--border);color:var(--ink);border-radius:999px;padding:5px 12px;
  font:inherit;font-size:12px;cursor:pointer}
.comp-bar button.on{background:var(--accent);color:#0E0C09;border-color:transparent}
.comp{position:relative;max-height:640px;overflow:auto;border:1px solid var(--border);border-radius:12px;background:#120F0B;margin:0 auto}
.comp .lienzo{position:relative}
.comp img{display:block;width:100%;height:auto;user-select:none;-webkit-user-drag:none}
.comp .sobre{position:absolute;left:0;top:0;width:100%;clip-path:inset(0 calc(100% - var(--x,50%)) 0 0)}
.comp .linea{position:absolute;top:0;bottom:0;left:var(--x,50%);width:2px;margin-left:-1px;background:#fff;
  box-shadow:0 0 0 1px rgba(0,0,0,.45),0 0 14px rgba(0,0,0,.5);pointer-events:none}
.comp .linea:after{content:"◂ ▸";position:sticky;top:45%;display:block;margin-left:-17px;width:36px;text-align:center;font-size:11px;
  background:#fff;color:#111;border-radius:999px;padding:3px 0}
.comp.dif .sobre,.comp.dif .linea{display:none}
.regs{display:grid;gap:14px;padding:6px 24px 18px}
.reg{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;align-items:start;background:var(--bg);border:1px solid var(--border);
  border-radius:12px;padding:12px}
.reg figure{margin:0}
.reg figcaption{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin-bottom:6px}
.reg img{display:block;width:100%;height:auto;border-radius:8px;border:1px solid var(--border);background:#fff}
.ad{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:8px}
.ad figure{margin:0}
.ad figcaption{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin-bottom:6px}
.ad img{display:block;width:100%;max-height:300px;object-fit:contain;object-position:left top;border-radius:8px;border:1px solid var(--border);background:#120F0B}
.delta{display:inline-flex;gap:6px;flex-wrap:wrap}
.delta span{font-family:var(--mono);font-size:12px;padding:3px 8px;border-radius:6px;background:var(--tile);border:1px solid var(--border);color:var(--ink)}
.sw{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;border:1px solid rgba(244,239,230,.25);margin:0 3px}
.celda{display:flex;flex-direction:column;align-items:center;gap:6px}
.celda .pct{font-family:var(--mono);font-size:12px;color:var(--muted)}
.intencional{opacity:.62}
.cat{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:650;padding:4px 11px;border-radius:999px;
  background:var(--tile);border:1px solid var(--border);color:var(--ink);white-space:nowrap}
.cat i{width:9px;height:9px;border-radius:3px}
@media (max-width:720px){.reg{grid-template-columns:1fr}.ad{grid-template-columns:1fr}}
</style>
"""

JS_PP = """
<script>
document.querySelectorAll('.comp-wrap').forEach(function(w){
  var c=w.querySelector('.comp'),r=w.querySelector('input[type=range]'),base=c.querySelector('.base');
  r.addEventListener('input',function(){c.style.setProperty('--x',r.value+'%')});
  w.querySelectorAll('button[data-modo]').forEach(function(b){b.addEventListener('click',function(){
    w.querySelectorAll('button[data-modo]').forEach(function(x){x.classList.toggle('on',x===b)});
    var dif=b.dataset.modo==='dif';c.classList.toggle('dif',dif);base.src=dif?base.dataset.dif:base.dataset.act;
    r.disabled=dif;});});
});
</script>
"""


def estado_pill(estado):
    color, ic = ESTADO.get(estado, (NEUTRO, "●"))
    return _pastilla(estado or "—", color, ic)


def tipo_pill(t):
    return f'<span class="cat"><i style="background:{COLOR_TIPO.get(t, NEUTRO)}"></i>{e(t)}</span>'


def corto(p):
    ruta = p["url"].split("://", 1)[-1].split("/", 1)
    return ("/" + ruta[1]) if len(ruta) > 1 and ruta[1] else "/"


def comparador(p):
    ancho = p.get("ancho_vp") or 1366
    maxw = f"max-width:{min(ancho, 1366)}px" if ancho < 1024 else ""
    return f'''<div class="comp-wrap">
  <div class="comp-bar"><span class="lado"><i style="background:{SERIES[2]}"></i>Referencia</span>
    <input type="range" min="0" max="100" value="50" aria-label="Deslizar entre referencia y actual">
    <span class="lado"><i style="background:{SERIES[1]}"></i>Actual</span>
    <button type="button" data-modo="desl" class="on">Deslizar</button><button type="button" data-modo="dif">Ver diferencias</button>
    <a class="lb" href="{e(p["diferencia"])}" title="Diferencias · {e(p["id"])}" style="color:var(--ink);font-size:12px">Ampliar diferencias</a></div>
  <div class="comp" style="{maxw}"><div class="lienzo">
    <img class="base" src="{e(p["actual"])}" data-act="{e(p["actual"])}" data-dif="{e(p["diferencia"])}" alt="Actual · {e(p["id"])}">
    <img class="sobre" src="{e(p["referencia"])}" alt="Referencia · {e(p["id"])}"><div class="linea"></div></div></div></div>'''


def antes_despues(h):
    figs = ""
    if h.get("antes"):
        figs += f'<figure><figcaption>Referencia</figcaption><a class="lb" href="{e(h["antes"])}" title="{e(h["id"])} · referencia"><img src="{e(h["antes"])}" loading="lazy" alt="Referencia"></a></figure>'
    if h.get("despues"):
        figs += f'<figure><figcaption>Actual</figcaption><a class="lb" href="{e(h["despues"])}" title="{e(h["id"])} · actual"><img src="{e(h["despues"])}" loading="lazy" alt="Actual"></a></figure>'
    return f'<div class="ad">{figs}</div>' if figs else ""


def deltas(h):
    d = h.get("delta") or {}
    partes = [f"{k} {v:+d} px" for k, v in (("X", d.get("dx")), ("Y", d.get("dy")), ("ancho", d.get("dw")), ("alto", d.get("dh"))) if v]
    s = h.get("estilo")
    if s:
        sw = lambda c: f'<i class="sw" style="background:{e(c)}"></i>' if str(c).startswith("#") else ""
        return f'<div class="delta"><span>{sw(s["de"])}{e(s["de"])} → {sw(s["a"])}{e(s["a"])}</span></div>'
    return f'<div class="delta">{"".join(f"<span>{e(x)}</span>" for x in partes)}</div>' if partes else ""


def build_html(datos, analisis, hist_html=""):
    ajustes = analisis.get("hallazgos") or {}
    hallazgos = []
    for h in datos.get("hallazgos") or []:
        h = dict(h)
        a = ajustes.get(h["id"]) or {}
        if a.get("severidad") in SEV:
            h["severidad"] = a["severidad"]
        h["_nota"] = a.get("nota")
        h["_intencional"] = bool(a.get("intencional"))
        hallazgos.append(h)
    reales = [h for h in hallazgos if not h["_intencional"]]
    intencionales = [h for h in hallazgos if h["_intencional"]]
    pantallas = datos.get("pantallas") or []
    r = datos.get("resumen") or {}
    modo = datos.get("modo")
    body = []

    if modo == "referencia":
        ok = [p for p in pantallas if not p.get("error")]
        body.append(banner(f"Referencia creada: {len(ok)} pantalla(s). La próxima corrida compara contra estas capturas.", "ok"))
        body.append('<div style="margin-top:20px">' + kpi_tiles([
            ("Páginas", r.get("paginas", 0), "", "en la referencia", "pantalla"),
            ("Pantallas", len(ok), "ok", f'{len(datos.get("config", {}).get("resoluciones") or [])} resolución(es)', "imagen"),
            ("Con error", r.get("errores", 0), "bad" if r.get("errores") else "ok", "no se pudieron capturar", "bad"),
            ("Navegador", datos.get("navegador"), "", datos.get("herramienta", "")[:40], "codigo"),
        ]) + "</div>")
        galeria = "".join(f'<figure>{miniatura(p["referencia"], p["id"])}<figcaption>{e(corto(p))} · {e(p["resolucion"])}</figcaption></figure>'
                          for p in ok)
        body.append(section("Capturas de referencia", f'<div class="galeria">{galeria}</div>', "lo que se va a comparar en las próximas corridas"))
    else:
        altas = [h for h in reales if h["severidad"] in ("Crítica", "Alta")]
        con = r.get("con_cambios", 0)
        if not reales:
            tono, texto = "ok", ("Todo igual a la referencia" if not intencionales else "Solo cambios intencionales: se pueden aceptar como nueva referencia")
        elif altas:
            tono, texto = "bad", f"{len(altas)} cambio(s) visibles de severidad alta en {con} pantalla(s)"
        else:
            tono, texto = "warn", f"Cambios menores en {r.get('cambios_menores', 0) + con} pantalla(s)"
        body.append(banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono))
        comp = r.get("comparadas", 0)
        sin = r.get("sin_cambios", 0)
        body.append('<div style="margin-top:20px">' + kpi_tiles([
            ("Pantallas comparadas", comp, "", f'{r.get("paginas", 0)} página(s) × {len(datos.get("config", {}).get("resoluciones") or [])} resolución(es)', "pantalla"),
            ("Sin cambios", sin, "ok" if sin == comp else "", f"{round(sin / comp * 100) if comp else 0} % de las pantallas", "ok", {"pct": sin / comp * 100 if comp else 0}),
            ("Con cambios", con + r.get("cambios_menores", 0), "bad" if con else ("warn" if r.get("cambios_menores") else "ok"),
             f'{con} importantes · {r.get("cambios_menores", 0)} menores', "warn"),
            ("Elementos corridos", r.get("elementos_corridos", 0) + r.get("bloques_desplazados", 0),
             "bad" if r.get("elementos_corridos") else ("warn" if r.get("bloques_desplazados") else "ok"),
             f'{r.get("bloques_desplazados", 0)} bloque(s) desplazado(s)', "mover"),
            ("Faltantes", r.get("faltantes", 0), "bad" if r.get("faltantes") else "ok", "estaban y ya no aparecen", "bad"),
            ("Nuevos", r.get("nuevos", 0), "warn" if r.get("nuevos") else "ok", "no estaban en la referencia", "lupa"),
            ("Mayor diferencia", f'{r.get("pct_max", 0)} %', "bad" if r.get("pct_max", 0) > 5 else ("warn" if r.get("pct_max", 0) > 0.5 else "ok"),
             "de los píxeles de una pantalla", "imagen"),
            ("Intencionales", len(intencionales), "" if not intencionales else "blk", "cambios esperados (no son defectos)", "ok"),
        ]) + "</div>")
        if analisis.get("resumen"):
            body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

        comparadas = [p for p in pantallas if p.get("pct") is not None]
        if comparadas:
            col = lambda p: CRITICO if p.get("estado") == "Con cambios" else AVISO if p.get("estado") == "Cambios menores" else OK
            body.append(section("Diferencia por pantalla", column_chart([(f'{corto(p)} {p["resolucion"]}', p["pct"], col(p)) for p in comparadas],
                                                                          fmt=lambda v: f"{v:g} %"),
                                "porcentaje de píxeles distintos de la referencia"))
        if reales:
            cuenta_t = Counter(h["tipo"] for h in reales)
            cuenta_s = Counter(h["severidad"] for h in reales)
            segs = [(cuenta_s[s], NIVEL_COLOR.get(s, NEUTRO), s) for s in SEV if cuenta_s[s]]
            principal = max(segs, key=lambda s: s[0])
            body.append(two_col(
                section("Hallazgos por tipo", bar_chart([(t, cuenta_t[t], COLOR_TIPO[t]) for t in TIPOS if cuenta_t[t]], ancho_etiqueta=150)),
                section("Hallazgos por severidad", donut_panel(segs, round(principal[0] / len(reales) * 100), principal[2].lower()))))

        # Matriz página × resolución
        resol = datos.get("config", {}).get("resoluciones") or sorted({p["resolucion"] for p in pantallas})
        urls = list(dict.fromkeys(p["url"] for p in pantallas))
        por = {(p["url"], p["resolucion"]): p for p in pantallas}
        filas = []
        for u in urls:
            fila = [f'<span class="mono" style="color:var(--ink)">{e(corto({"url": u}))}</span>']
            for res in resol:
                p = por.get((u, res))
                if not p:
                    fila.append('<span class="muted">—</span>')
                    continue
                est = "Error" if p.get("error") else p.get("estado")
                pct = f'<span class="pct">{p["pct"]} %</span>' if p.get("pct") is not None else ""
                img = miniatura(p.get("diferencia") or p.get("actual"), f'{p["id"]} · diferencias', "s") if (p.get("diferencia") or p.get("actual")) else ""
                fila.append(f'<div class="celda"><a href="#{e(p["id"])}" style="text-decoration:none">{estado_pill(est)}</a>{pct}{img}</div>')
            filas.append(fila)
        body.append(section("Matriz de pantallas", f'<div class="matriz">{table(["Página"] + list(resol), filas)}</div>',
                            "estado de cada página en cada resolución · clic en el estado para ver la comparación"))

        # Cada pantalla con cambios: comparador, regiones y hallazgos
        bloques = []
        for p in pantallas:
            if p.get("pct") is None or p.get("estado") == "Sin cambios":
                continue
            hs = [h for h in hallazgos if h["pantalla"] == p["id"]]
            regs = "".join(f'''<div class="reg"><figure><figcaption>Referencia</figcaption><a class="lb" href="{e(x["referencia"])}" title="Región {i + 1} · referencia"><img src="{e(x["referencia"])}" loading="lazy" alt="Referencia"></a></figure>
              <figure><figcaption>Actual</figcaption><a class="lb" href="{e(x["actual"])}" title="Región {i + 1} · actual"><img src="{e(x["actual"])}" loading="lazy" alt="Actual"></a></figure>
              <figure><figcaption>Diferencias</figcaption><a class="lb" href="{e(x["diferencia"])}" title="Región {i + 1} · diferencias"><img src="{e(x["diferencia"])}" loading="lazy" alt="Diferencias"></a></figure></div>'''
                           for i, x in enumerate((p.get("recortes") or [])[:4]))
            lista = "".join(f'''<div class="hallazgo{' intencional' if h["_intencional"] else ''}" id="{e(h["id"])}"><h3>{e(h["id"])} · {e(h["titulo"])} {nivel_badge(h["severidad"])} {tipo_pill(h["tipo"])}
              {'<span class="pill">Intencional</span>' if h["_intencional"] else ''}</h3>
              <p>{e(h["detalle"])}</p>{deltas(h)}{f'<div class="lbl">Nota del análisis</div><p>{e(h["_nota"])}</p>' if h.get("_nota") else ''}{antes_despues(h)}</div>'''
                            for h in hs)
            info = (f'{p["pct"]} % de píxeles distintos · {len(p.get("regiones") or [])} región(es) · alto {p.get("alto_ref")} → {p.get("alto")} px'
                    + (" · referencia de diseño: solo píxeles" if p.get("solo_pixeles") else ""))
            bloques.append(f'''<details class="pag" id="{e(p["id"])}" {'open' if not bloques else ''}><summary><strong>{e(corto(p))}</strong>
              <span class="muted">{e(p["resolucion"])} · {e(p.get("dispositivo", ""))}</span>{estado_pill(p["estado"])}<span class="muted">{e(info)}</span></summary>
              {comparador(p)}{f'<div class="lbl" style="padding:6px 24px 0">Regiones con más cambios</div><div class="regs">{regs}</div>' if regs else ''}
              {lista}</details>''')
        if bloques:
            body.append(section("Comparación de cada pantalla", "".join(bloques),
                                "deslizá para pasar de la referencia a la actual · Ver diferencias marca en rojo cada píxel que cambió"))

        if hallazgos:
            filas = []
            for h in hallazgos:
                filas.append([f'<a class="id" href="#{e(h["id"])}" style="color:var(--ink)">{e(h["id"])}</a>', nivel_badge(h["severidad"]),
                              tipo_pill(h["tipo"]) + (' <span class="pill">Intencional</span>' if h["_intencional"] else ""),
                              f'<strong style="color:var(--ink)">{e(h["titulo"])}</strong><div class="muted">{e(h["detalle"][:180])}</div>',
                              f'<span class="mono">{e(corto(h))}</span><div class="muted">{e(h["resolucion"])}</div>',
                              miniatura(h.get("antes"), f'{h["id"]} · referencia', "s") if h.get("antes") else '<span class="muted">—</span>',
                              miniatura(h.get("despues"), f'{h["id"]} · actual', "s") if h.get("despues") else '<span class="muted">—</span>'])
            body.append(section("Todos los hallazgos", table(["ID", "Severidad", "Tipo", "Hallazgo", "Pantalla", "Referencia", "Actual"], filas),
                                "clic en el ID para ver la pantalla completa"))

        errores = [p for p in pantallas if p.get("error")]
        nuevas = [p for p in pantallas if p.get("estado") == "Nueva"]
        if errores or nuevas:
            filas = [[e(corto(p)), e(p["resolucion"]), estado_pill("Error" if p.get("error") else "Nueva"),
                      e(p.get("error") or "No hay referencia para esta pantalla: aceptala con --aceptar si es correcta.")] for p in errores + nuevas]
            body.append(section("Pantallas sin comparar", table(["Página", "Resolución", "Estado", "Detalle"], filas)))

    body.append(falta_informacion(analisis.get("falta_informacion")))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))

    cfg = datos.get("config") or {}
    ref = datos.get("referencia") or {}
    filas = [["Referencia tomada", e((ref.get("fecha") or "")[:16].replace("T", " "))],
             ["Última actualización", e((ref.get("actualizada") or "—")[:16].replace("T", " "))],
             ["Navegador", e(ref.get("navegador") or datos.get("navegador"))],
             ["Resoluciones", e(", ".join(cfg.get("resoluciones") or []))],
             ["Zonas ocultas", e(", ".join(cfg.get("ocultar") or []) or "ninguna")],
             ["Sensibilidad por píxel", e(cfg.get("umbral"))],
             ["Tolerancia de posición", f'{e(cfg.get("tolerancia_px"))} px'],
             ["Diferencia aceptada sin cambios", f'{e(cfg.get("pct_max"))} %'],
             ["Aceptar los cambios como nueva referencia", '<span class="mono">npm run pixel-perfect -- --aceptar todas</span> (o los IDs de pantalla separados por comas)']]
    body.append(section("Referencia y configuración", table(["Dato", "Valor"], filas),
                        "la referencia es la versión aceptada como correcta; se conserva entre corridas"))

    if hist_html:
        body.append(hist_html)
    meta_html = meta([("Historia", datos.get("historia")), ("Sitio", datos.get("host")),
                      ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")), ("Navegador", datos.get("navegador")),
                      ("Duración", f'{datos.get("duracion_s", 0)} s')])
    titulo = "Referencia visual" if modo == "referencia" else "Regresión visual"
    return page(titulo, "Pixel perfect", meta_html, CSS_EXTRA + CSS_PP + "".join(body) + JS_PP)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de regresión visual a partir de pixel-perfect.json")
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
    hist_html = _historial.seccion("pixel-perfect", Path(a.datos_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

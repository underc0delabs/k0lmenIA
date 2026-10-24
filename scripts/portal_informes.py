#!/usr/bin/env python3
"""
Portal de informes: output/index.html con el último informe de cada herramienta.

Uso (desde la raíz del repo):
    python scripts/portal_informes.py [--abrir]

Recorre output/ (cada carpeta es una herramienta: ejecuciones, exploratorias, accesibilidad, …; las que
se agreguen después aparecen solas) y los reportes de k0lmena (herramientas/k0lmena/reports/), y arma
una página con una tarjeta por herramienta: el último informe HTML de cada historia, sitio o suite, su
fecha, el veredicto o resultado si el JSON lo trae, y el link a la corrida anterior guardada en historial/.
Arriba tiene un buscador y filtros por herramienta, historia, estado y fecha, y dos vistas: por herramienta
o por historia (todos los informes de una HU juntos, de cualquier herramienta).

Los links son relativos: output/index.html se abre con doble clic, sin servidor.

Se regenera solo: cada informe HTML que arman los scripts (con _estilos_reporte.page) lo actualiza al
terminar. Para desactivarlo, K0LMENIA_PORTAL=0 en el entorno.
"""
import argparse
import atexit
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Nombres legibles de las carpetas conocidas (las demás se muestran con su nombre capitalizado).
NOMBRES = {
    "ejecuciones": "Ejecuciones (E2E y API)", "exploratorias": "Pruebas exploratorias", "accesibilidad": "Accesibilidad",
    "rendimiento": "Rendimiento web", "fallos": "Análisis de fallos", "cobertura": "Cobertura y trazabilidad",
    "pixel-perfect": "Regresión visual", "cross-browser": "Cross-browser", "reparaciones": "Reparación de la automatización",
    "seleccion-casos": "Selección de casos", "correos": "Correos", "traductor": "Traducciones", "revision-casos": "Revisión de casos",
    "charters": "Charters exploratorios", "ux": "Usabilidad", "formularios": "Formularios", "logs": "Logs",
    "seguridad": "Seguridad web", "performance": "Performance", "informes-cierre": "Informes de cierre",
    "planes-de-prueba": "Planes de prueba", "permisos": "Permisos por rol", "resiliencia": "Resiliencia",
    "triage": "Triage de bugs", "tablero": "Tablero de calidad", "monitoreo": "Monitoreo sintético",
    "evals": "Evals de los agentes", "k0lmena": "npm test (k0lmena)", "metricas-tokens": "Uso de tokens",
    "onboarding": "Onboarding",
    "shopify": "Shopify", "wordpress": "WordPress / WooCommerce", "salesforce": "Salesforce", "billeteras": "Billeteras y pagos",
    "prestashop": "PrestaShop", "vtex": "VTEX", "sap": "SAP (GUI y Fiori)", "desktop": "Apps de escritorio",
    "mobile": "Apps móviles", "ia": "IA / LLM", "mensajeria": "Mensajería y eventos", "soap": "SOAP",
    "dependencias": "Dependencias (SCA)", "sast": "Código seguro (SAST)", "contratos": "Contract testing",
    "seo": "SEO y GEO", "datos": "Datos y pipelines", "dynamics": "Dynamics / CRM-ERP", "blockchain": "Blockchain / Web3",
    "ivr": "Voz / IVR", "juegos": "Videojuegos", "pos": "Punto de venta (POS)", "streaming": "Streaming y cámaras",
    "observabilidad": "Observabilidad", "busqueda": "Búsqueda y relevancia", "documentos": "Documentos generados",
    "contenido": "Contenido y typos", "mutacion": "Mutation testing",
    "revision-codigo": "Revisión de código", "manuales": "Manuales de usuario", "scalar": "APIs en Scalar",
}
# Orden de las tarjetas: primero lo que más se mira.
ORDEN = ["tablero", "informes-cierre", "ejecuciones", "k0lmena", "fallos", "cobertura", "monitoreo", "planes-de-prueba",
         "seleccion-casos", "exploratorias", "accesibilidad", "rendimiento", "performance", "seguridad", "permisos",
         "resiliencia", "pixel-perfect", "cross-browser", "formularios", "ux", "correos", "traductor", "logs",
         "reparaciones", "revision-casos", "charters", "triage", "evals",
         "mobile", "shopify", "wordpress", "prestashop", "vtex", "dynamics", "salesforce", "sap",
         "desktop", "ia", "mensajeria", "soap", "contratos", "datos", "seo", "dependencias", "sast", "revision-codigo", "manuales", "scalar",
         "blockchain", "billeteras", "pos", "ivr", "juegos", "streaming",
         "observabilidad", "busqueda", "documentos", "contenido", "mutacion"]
IGNORAR = {"historial", "evidencia", "capturas", "videos", "recortes", "diferencias", "lighthouse", "referencia",
           "actual", "respaldo", "suite", "eml", "sesiones", "node_modules"}
_SELLO = re.compile(r"[-_]?\d{4}-?\d{2}-?\d{2}([-_T]?\d{2}-?\d{2}(-?\d{2})?)?$")


def _fecha(p):
    return datetime.fromtimestamp(p.stat().st_mtime)


def _htmls(carpeta):
    """Los .html de la carpeta, sin entrar a historial/ ni a las carpetas de evidencia."""
    for raiz, dirs, archivos in os.walk(carpeta):
        dirs[:] = [d for d in dirs if d not in IGNORAR and not d.startswith((".", "_"))]
        for a in archivos:
            if a.lower().endswith(".html"):
                yield Path(raiz) / a


def _reporte_k0(p):
    """El reporte completo de k0lmena (index.html de npm run report:<suite>, al lado del cucumber-report.json)."""
    return p.name.lower() == "index.html" and (p.parent / "cucumber-report.json").exists()


def _principal(archivos):
    """De varios .html de una misma unidad, el informe principal más reciente."""
    def peso(p):
        n = p.name.lower()
        return (_reporte_k0(p), n.startswith(("informe-", "reporte-", "cierre-", "plan-", "cucumber")), p.stat().st_mtime)
    return max(archivos, key=peso)


def _leer_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def estado_de(html):
    """Veredicto o resultado de un informe, desde los JSON que tiene al lado (o "")."""
    carpeta = html.parent
    candidatos = [carpeta / "analisis.json"]
    stem = html.stem
    for pref in ("reporte-", "cierre-", "plan-"):
        if stem.startswith(pref):
            candidatos.append(carpeta / f"_resultados-{stem[len(pref):]}.json")
            candidatos.append(carpeta / f"{stem}.json")
    candidatos += sorted(p for p in carpeta.glob("*.json") if p not in candidatos)
    for c in candidatos:
        d = _leer_json(c) if c.exists() else None
        if not isinstance(d, dict):
            continue
        if d.get("veredicto"):
            return str(d["veredicto"])
        casos = d.get("casos")
        if isinstance(casos, list) and casos and isinstance(casos[0], dict) and "estado" in casos[0]:
            ok = sum(1 for x in casos if str(x.get("estado", "")).lower() == "aprobado")
            return f"{ok}/{len(casos)} aprobados"
    if html.name.startswith("cucumber") or (carpeta / "cucumber-report.json").exists():
        d = _leer_json(carpeta / "cucumber-report.json")
        if isinstance(d, list):
            total = ok = 0
            for f in d:
                for esc in f.get("elements") or []:
                    if esc.get("type") == "background":
                        continue
                    total += 1
                    estados = [(p.get("result") or {}).get("status") for p in esc.get("steps") or []]
                    ok += bool(estados) and all(s in ("passed", "skipped") for s in estados) and "passed" in estados
            if total:
                return f"{ok}/{total} escenarios aprobados"
    return ""


def _anterior(carpeta_unidad):
    """(cantidad de corridas guardadas, el informe de la más reciente) de historial/."""
    h = carpeta_unidad / "historial"
    if not h.is_dir():
        return 0, None
    corridas = sorted((d for d in h.iterdir() if d.is_dir()), key=lambda d: d.name)
    if not corridas:
        return 0, None
    ultima = corridas[-1]
    informes = sorted(ultima.rglob("*.html"))
    return len(corridas), (_principal(informes) if informes else None)


def unidades(carpeta):
    """Informes de una herramienta: [{"unidad", "html", "fecha", "estado", "historial", "anterior", "otros"}]."""
    grupos = {}
    for html in _htmls(carpeta):
        rel = html.relative_to(carpeta)
        if len(rel.parts) > 1:
            clave, base = rel.parts[0], carpeta / rel.parts[0]
        else:
            clave = _SELLO.sub("", html.stem) or html.stem
            m = re.search(r"(HU-\d+|API|CP-API)", html.stem, re.I)
            clave = m.group(1).upper() if m and html.stem.startswith(("reporte-", "cierre-", "plan-")) else clave
            base = carpeta
        grupos.setdefault(clave, {"base": base, "htmls": []})["htmls"].append(html)
    salida = []
    for clave, g in grupos.items():
        html = _principal(g["htmls"])
        n, anterior = _anterior(g["base"]) if g["base"] != carpeta else (0, None)
        otros = sorted({h for h in g["htmls"] if h != html and h.parent == html.parent}, key=lambda p: p.name)
        salida.append({"unidad": clave, "html": html, "fecha": _fecha(html), "estado": estado_de(html),
                       "historial": n, "anterior": anterior, "otros": otros})
    return sorted(salida, key=lambda u: u["fecha"], reverse=True)


def descubrir(output, reportes_k0=None):
    """{herramienta: [unidades]} de todas las carpetas de output/ (y npm test), con o sin informes."""
    herramientas = {}
    if output.is_dir():
        for d in sorted(p for p in output.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
            herramientas[d.name] = unidades(d)
    if reportes_k0 and Path(reportes_k0).is_dir():
        k0 = []
        for suite in sorted(p for p in Path(reportes_k0).iterdir() if p.is_dir()):
            us = unidades(suite)
            # El reporte completo (index.html + features/) y el básico de Cucumber son la misma corrida:
            # una sola entrada, la del completo, con el básico como "otro" y sin las páginas de features/.
            completo = next((u for u in us if _reporte_k0(u["html"]) and u["html"].parent == suite), None)
            if completo:
                basicos = [u["html"] for u in us if u is not completo and u["html"].parent == suite]
                completo["otros"] = sorted(set(completo["otros"]) | set(basicos), key=lambda p: p.name)
                us = [u for u in us if u is completo or (u["html"].parent != suite and u["unidad"] != "features")]
            for u in us:
                u["unidad"] = suite.name if u["unidad"] in (Path(u["html"]).stem, "cucumber-report", "index") else f'{suite.name} · {u["unidad"]}'
                if u["html"].parent == suite:
                    u["historial"], u["anterior"] = _anterior(suite)
                k0.append(u)
        herramientas["k0lmena"] = sorted(k0, key=lambda u: u["fecha"], reverse=True)
    orden = {n: i for i, n in enumerate(ORDEN)}
    return dict(sorted(herramientas.items(), key=lambda kv: (orden.get(kv[0], len(ORDEN)), kv[0])))


def _tono(estado):
    t = (estado or "").lower()
    m = re.match(r"(\d+)/(\d+)", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return "ok" if a == b else "bad" if a < b * 0.8 else "warn"
    if re.search(r"no apto|no-go|no go|crític|critic|bloque|falla|rechaz|alto riesgo|riesgo alto", t):
        return "bad"
    if re.search(r"observacion|revisar|riesgo|parcial|condicion|atenci|medio", t):
        return "warn"
    if re.search(r"apto|\bgo\b|en orden|aprobad|ok|sin hallazgos|cumple", t):
        return "ok"
    return ""


_HISTORIA = re.compile(r"\b([A-Z][A-Z0-9]{0,9}-\d+)\b")


def historia_de(u):
    """La historia de un informe (HU-001, PROJ-12…) sacada de la unidad o de la ruta; si no hay, la unidad."""
    for texto in [u.get("unidad", "")] + list(Path(u["html"]).parts[::-1]):
        m = _HISTORIA.search(str(texto))
        if m and not m.group(1).startswith(("CP-API", "BUG-", "FI-")):
            return m.group(1)
    return u.get("unidad") or "—"


TONO_TEXTO = {"ok": "En orden", "warn": "Revisar", "bad": "Crítico", "": "Sin estado"}

# Filtros del portal: buscador, herramienta, historia, estado y fecha, más la vista por herramienta o por
# historia. Ocultan con la clase "fuera" (la de los buscadores de cada tabla es "oculta": se combinan).
CSS_PORTAL = """
.fuera{display:none!important}
.filtros{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:16px 22px 18px}
.filtros label{display:flex;flex-direction:column;gap:5px;font-family:var(--mono);font-size:11px;color:var(--muted);text-transform:lowercase}
.filtros input,.filtros select{font:inherit;font-family:var(--sans);font-size:13px;color:var(--ink);background:var(--surface);
  border:1px solid var(--line);border-radius:10px;padding:8px 11px;min-width:170px}
.filtros input:focus,.filtros select:focus{outline:none;border-color:var(--linea-amarilla);box-shadow:var(--glow-k0)}
.filtros .grupo-btn{display:flex;gap:6px;flex-wrap:wrap}
.filtros button{font:inherit;font-size:12px;font-weight:500;color:var(--body);background:var(--surface);border:1px solid var(--line);
  border-radius:8px;padding:7px 11px;cursor:pointer}
.filtros button.on{color:#0E0C09;background:var(--accent);border-color:var(--accent);font-weight:600}
.filtros .cuenta{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--muted);align-self:flex-end;padding-bottom:8px}
.filtros .limpiar{background:transparent;border-style:dashed}
"""

JS_PORTAL = r"""
(function(){
var f=document.getElementById('filtros');if(!f)return;
var q=f.querySelector('[name=q]'),herr=f.querySelector('[name=herr]'),hist=f.querySelector('[name=hist]'),fecha=f.querySelector('[name=fecha]');
var tono='',vista='herr',cuenta=f.querySelector('.cuenta');
function sinAcentos(t){return (t||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');}
function aplicar(){
  var ahora=Date.now(),dias=fecha.value?parseInt(fecha.value,10):0,txt=sinAcentos(q.value.trim()),vis=0,total=0;
  [].forEach.call(document.querySelectorAll('.vista'),function(v){v.classList.toggle('fuera',v.getAttribute('data-vista')!==vista);});
  var activa=document.querySelector('.vista[data-vista="'+vista+'"]');
  [].forEach.call(activa.querySelectorAll('tr.pr'),function(tr){
    total++;
    var ok=(!herr.value||tr.dataset.herr===herr.value)&&(!hist.value||tr.dataset.hist===hist.value)&&(!tono||tr.dataset.tono===tono)
      &&(!dias||ahora-parseInt(tr.dataset.fecha,10)<=dias*86400000)&&(!txt||sinAcentos(tr.textContent).indexOf(txt)>=0);
    tr.classList.toggle('fuera',!ok);if(ok)vis++;});
  [].forEach.call(activa.querySelectorAll('.section'),function(s){
    var filas=s.querySelectorAll('tr.pr');if(!filas.length)return;
    s.classList.toggle('fuera',![].some.call(filas,function(tr){return !tr.classList.contains('fuera');}));});
  cuenta.textContent=vis+' de '+total+' informes';
  try{localStorage.setItem('k0-portal',JSON.stringify({q:q.value,herr:herr.value,hist:hist.value,fecha:fecha.value,tono:tono,vista:vista}));}catch(e){}
}
f.addEventListener('input',aplicar);f.addEventListener('change',aplicar);
f.addEventListener('click',function(ev){var b=ev.target.closest('button');if(!b)return;ev.preventDefault();
  if(b.dataset.tono!==undefined){tono=b.dataset.tono;[].forEach.call(f.querySelectorAll('[data-tono]'),function(x){x.classList.toggle('on',x===b);});}
  if(b.dataset.vista){vista=b.dataset.vista;[].forEach.call(f.querySelectorAll('[data-vista]'),function(x){x.classList.toggle('on',x===b);});}
  if(b.classList.contains('limpiar')){q.value='';herr.value='';hist.value='';fecha.value='';tono='';
    [].forEach.call(f.querySelectorAll('[data-tono]'),function(x){x.classList.toggle('on',x.dataset.tono==='');});}
  aplicar();});
try{var g=JSON.parse(localStorage.getItem('k0-portal')||'null');if(g){q.value=g.q||'';herr.value=g.herr||'';hist.value=g.hist||'';fecha.value=g.fecha||'';
  tono=g.tono||'';vista=g.vista||'herr';
  [].forEach.call(f.querySelectorAll('[data-tono]'),function(x){x.classList.toggle('on',x.dataset.tono===tono);});
  [].forEach.call(f.querySelectorAll('[data-vista]'),function(x){x.classList.toggle('on',x.dataset.vista===vista);});}}catch(e){}
aplicar();
})();
"""


def armar_html(herramientas, destino):
    from _estilos_reporte import page, meta, section, kpi_tiles, e, _pastilla, OK, AVISO, CRITICO, NEUTRO

    dir_html = Path(destino).resolve().parent

    def link(p, texto):
        try:
            rel = os.path.relpath(Path(p).resolve(), dir_html).replace("\\", "/")
        except ValueError:  # otra unidad en Windows: no hay ruta relativa
            rel = Path(p).resolve().as_uri()
        return f'<a href="{e(rel)}">{e(texto)}</a>'

    def nombre(h):
        return NOMBRES.get(h, h.replace("-", " ").capitalize())

    con = {k: v for k, v in herramientas.items() if v}
    vacias = [k for k, v in herramientas.items() if not v]
    todas = [(h, u) for h, us in con.items() for u in us]
    ultimo = max((u["fecha"] for _, u in todas), default=None)
    malos = sum(1 for _, u in todas if _tono(u["estado"]) == "bad")
    historias = sorted({historia_de(u) for _, u in todas})
    body = [kpi_tiles([
        ("Herramientas con informes", len(con), "", f"{len(herramientas)} carpeta(s) en total", "grid"),
        ("Informes", len(todas), "", f"de {len(historias)} historia(s), sitio(s) o suite(s)", "lista"),
        ("Para revisar", malos, "bad" if malos else "ok", "con veredicto o resultado en rojo", "warn"),
        ("Último informe", ultimo.strftime("%d/%m %H:%M") if ultimo else "—", "", "", "reloj"),
    ])]
    if not todas:
        body.append(section("Sin informes todavía", '<div class="cardbody"><p class="muted">Cuando los agentes generen '
                            'informes, van a aparecer acá. Este portal se actualiza solo cada vez que se arma uno.</p></div>'))
    color = {"ok": OK, "warn": AVISO, "bad": CRITICO}
    icono = {"ok": "✓", "warn": "!", "bad": "✕"}

    def fila(h, u, primera):
        t = _tono(u["estado"])
        estado = _pastilla(u["estado"], color.get(t, NEUTRO), icono.get(t, "●")) if u["estado"] else '<span class="muted">—</span>'
        otros = " · ".join(link(o, o.stem) for o in u["otros"][:4])
        informe = link(u["html"], u["html"].name) + (f'<div class="muted" style="font-size:12px">{otros}</div>' if otros else "")
        hist = (link(u["anterior"], f'anterior ({u["historial"]} guardada{"s" if u["historial"] != 1 else ""})')
                if u["anterior"] else '<span class="muted">—</span>')
        datos = (f' class="pr" data-herr="{e(h)}" data-hist="{e(historia_de(u))}" data-tono="{t}"'
                 f' data-fecha="{int(u["fecha"].timestamp() * 1000)}"')
        celdas = [primera, informe, e(u["fecha"].strftime("%d/%m/%Y %H:%M")), estado, hist]
        return f'<tr{datos}>' + "".join(f"<td>{c}</td>" for c in celdas) + "</tr>"

    def tabla(primera_col, filas):
        th = "".join(f"<th>{e(x)}</th>" for x in [primera_col, "Informe", "Fecha", "Estado", "Corrida anterior"])
        return f'<div class="tablecard"><table><thead><tr>{th}</tr></thead><tbody>{"".join(filas)}</tbody></table></div>'

    if todas:
        op_herr = "".join(f'<option value="{e(h)}">{e(nombre(h))}</option>' for h in con)
        op_hist = "".join(f'<option value="{e(x)}">{e(x)}</option>' for x in historias)
        tonos = "".join(f'<button type="button" data-tono="{k}"{" class=on" if k == "" else ""}>{e(v)}</button>'
                        for k, v in (("", "Todos"), ("bad", "Crítico"), ("warn", "Revisar"), ("ok", "En orden")))
        body.append(section("Filtrar", f'''<form class="filtros" id="filtros" onsubmit="return false">
  <label>buscar<input name="q" type="search" placeholder="Texto, historia, archivo…"></label>
  <label>herramienta<select name="herr"><option value="">Todas</option>{op_herr}</select></label>
  <label>historia / sitio / suite<select name="hist"><option value="">Todas</option>{op_hist}</select></label>
  <label>fecha<select name="fecha"><option value="">Todas</option><option value="1">Últimas 24 h</option>
    <option value="7">Últimos 7 días</option><option value="30">Últimos 30 días</option></select></label>
  <label>estado<span class="grupo-btn">{tonos}</span></label>
  <label>vista<span class="grupo-btn"><button type="button" data-vista="herr" class="on">Por herramienta</button>
    <button type="button" data-vista="hist">Por historia</button></span></label>
  <button type="button" class="limpiar">Limpiar filtros</button>
  <span class="cuenta"></span>
</form>'''))
        por_herr = [section(nombre(h), tabla("Historia / sitio / suite", [fila(h, u, f'<b>{e(u["unidad"])}</b>') for u in us]),
                            f"{len(us)} informe(s)") for h, us in con.items()]
        agrupado = {}
        for h, u in todas:
            agrupado.setdefault(historia_de(u), []).append((h, u))
        por_hist = []
        for x in historias:
            items = sorted(agrupado[x], key=lambda hu: hu[1]["fecha"], reverse=True)
            por_hist.append(section(x, tabla("Herramienta", [fila(h, u, f'<b>{e(nombre(h))}</b>') for h, u in items]),
                                    f"{len(items)} informe(s)"))
        body.append(f'<div class="vista subgrid" data-vista="herr">{"".join(por_herr)}</div>')
        # La vista por historia no suma entradas al índice lateral (sería un duplicado de la otra vista).
        body.append(f'<div class="vista subgrid fuera" data-vista="hist">{"".join(por_hist).replace(" data-nav=", " data-nav-hist=")}</div>')
    if vacias:
        chips = " ".join(f'<span class="chip">{e(nombre(v))}</span>' for v in vacias)
        body.append(section("Todavía sin informes", f'<div class="cardbody"><div class="meta">{chips}</div></div>'))
    html_ = page("Portal de informes", "Portal", meta([("Actualizado", datetime.now().strftime("%d/%m/%Y %H:%M")),
                                                       ("Carpeta", "output/")]), "".join(body))
    return html_.replace("</style>", CSS_PORTAL + "</style>", 1).replace("</body>", f"<script>{JS_PORTAL}</script></body>", 1)


def generar(output=None, reportes_k0=None, destino=None):
    output = Path(output or RAIZ / "output")
    reportes_k0 = reportes_k0 if reportes_k0 is not None else RAIZ / "herramientas" / "k0lmena" / "reports"
    destino = Path(destino or output / "index.html")
    destino.parent.mkdir(parents=True, exist_ok=True)
    herramientas = descubrir(output, reportes_k0)
    destino.write_text(armar_html(herramientas, destino), encoding="utf-8")
    return destino, herramientas


# ------------------------------------------------------------------ actualización automática
_PROGRAMADO = [False]


def _actualizar_al_salir():
    try:
        generar()
    except Exception as ex:  # el portal nunca rompe un informe
        print(f"[!] No pude actualizar el portal de informes ({ex}).", file=sys.stderr)


def programar():
    """Regenera output/index.html cuando termina el proceso (después de que el informe se escribió).
    No hace nada en los tests, con K0LMENIA_PORTAL=0 o si no existe output/."""
    if _PROGRAMADO[0] or os.environ.get("K0LMENIA_PORTAL", "1") == "0" or "pytest" in sys.modules:
        return
    if not (RAIZ / "output").is_dir():
        return
    _PROGRAMADO[0] = True
    atexit.register(_actualizar_al_salir)


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Portal con el último informe de cada herramienta (output/index.html)")
    ap.add_argument("--abrir", action="store_true", help="abre el portal en el navegador")
    ap.add_argument("--output", help=argparse.SUPPRESS)
    ap.add_argument("--reportes", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    _PROGRAMADO[0] = True  # este proceso ya genera el portal: que page() no lo programe de nuevo
    destino, herramientas = generar(a.output, a.reportes)
    n = sum(len(v) for v in herramientas.values())
    print(f"Portal: {destino} ({n} informe(s) de {sum(1 for v in herramientas.values() if v)} herramienta(s))")
    if a.abrir:
        import webbrowser
        webbrowser.open(destino.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())

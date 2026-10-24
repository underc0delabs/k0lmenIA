#!/usr/bin/env python3
"""
Plan de onboarding de un QA que llega al proyecto (agente guia-onboarding).

Uso (desde la raíz del repo):
    python scripts/generar_onboarding.py <plan.json> [--salida <carpeta>]

Arma, a partir del JSON que escribe el agente, output/onboarding/<persona o rol>/ con:
  - plan-onboarding.html  (con el estilo de los informes; el checklist se puede tildar y queda guardado
                          en el navegador)
  - plan-onboarding.md    (lo mismo en Markdown, con las tablas alineadas)

Esquema del JSON (todo opcional salvo "persona" y "rol"):
{
  "persona": "Ana", "rol": "QA manual",                    // rol: QA manual | Automatizador | Líder de QA | …
  "proyecto": "Tienda online", "fecha": "2026-10-14",
  "resumen": "Qué es el producto y qué va a hacer la persona en las primeras semanas.",
  "producto": {
    "modulos": [{"nombre": "Checkout", "descripcion": "...", "fuente": "input/documentacion/proyecto/resumen.md"}],
    "roles": [{"rol": "Comprador", "puede": "..."}],
    "flujos": [{"nombre": "Comprar con tarjeta", "pantallas": "Carrito → Pago → Confirmación", "fuente": "mapa-funcional.md"}],
    "glosario": [{"termino": "SKU", "definicion": "..."}]
  },
  "entorno": [{"que": "Doctor", "estado": "ok|aviso|falta", "detalle": "...", "accion": "..."}],
  "agentes": [{"agente": "generador-casos-manuales", "para_que": "...", "pedido": "Generá los casos de PROJ-12"}],
  "plan": [{"cuando": "Día 1", "tarea": "...", "hecho_cuando": "...", "agente": "opcional"}],
  "preguntas": [{"id": "FI-01", "pregunta": "...", "a_quien": "PO", "por_que": "..."}],
  "checklist": ["Tener el .env completo", "..."],
  "faltantes": ["No hay documentación del proyecto: pedile al documentador-proyecto que la arme."]
}
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
from _i18n import escribir_bilingue, localizar, idioma_actual  # noqa: E402

TONO = {"ok": "ok", "aviso": "warn", "falta": "bad"}
TEXTO_ESTADO = {"ok": "Listo", "aviso": "Revisar", "falta": "Falta"}

CSS_ONB = """
.check{list-style:none;display:flex;flex-direction:column;gap:8px;padding:6px 22px 22px}
.check li label{display:flex;align-items:flex-start;gap:12px;padding:10px 14px;border:1px solid var(--line);border-radius:10px;
  background:var(--surface);cursor:pointer;color:var(--body);transition:border-color .15s}
.check li label:hover{border-color:var(--linea-amarilla)}
.check input{appearance:none;flex:none;width:20px;height:18px;margin-top:2px;cursor:pointer;
  clip-path:polygon(25% 3%,75% 3%,100% 50%,75% 97%,25% 97%,0 50%);background:var(--border)}
.check input:checked{background:var(--accent)}
.check input:checked+span{color:var(--muted);text-decoration:line-through}
.progreso{display:flex;align-items:center;gap:12px;padding:0 22px 6px;font-family:var(--mono);font-size:12px;color:var(--muted)}
.progreso .b{flex:1;height:6px;border-radius:999px;background:rgba(244,239,230,.07);overflow:hidden}
.progreso .b span{display:block;height:100%;width:0;background:linear-gradient(90deg,#FFD60A,#FF8A00);transition:width .2s}
.pedido-ej{font-family:var(--mono);font-size:12.5px;color:var(--ink)}
.pedido-ej::before{content:"› ";color:var(--accent)}
"""

JS_ONB = r"""
(function(){
var clave='k0-onboarding-'+document.title,cajas=[].slice.call(document.querySelectorAll('.check input'));
if(!cajas.length)return;
var est={};try{est=JSON.parse(localStorage.getItem(clave)||'{}');}catch(e){}
var barra=document.querySelector('.progreso .b span'),txt=document.querySelector('.progreso .t');
function pintar(){var n=cajas.filter(function(c){return c.checked;}).length;
  if(barra)barra.style.width=(100*n/cajas.length)+'%';if(txt)txt.textContent=n+' de '+cajas.length+' hechos';}
cajas.forEach(function(c){c.checked=!!est[c.id];c.addEventListener('change',function(){est[c.id]=c.checked;
  try{localStorage.setItem(clave,JSON.stringify(est));}catch(e){}pintar();});});
pintar();
})();
"""


def slug(texto):
    s = re.sub(r"[^a-z0-9]+", "-", (texto or "").lower().translate(str.maketrans("áéíóúñü", "aeiounu"))).strip("-")
    return s or "persona"


def build_html(d):
    from _estilos_reporte import e, page, meta, section, kpi_tiles, table, doc_list, two_col, banner, _pastilla, OK, AVISO, CRITICO
    prod = d.get("producto") or {}
    entorno = d.get("entorno") or []
    faltan = sum(1 for x in entorno if x.get("estado") == "falta")
    body = [kpi_tiles([
        ("Módulos del producto", len(prod.get("modulos") or []), "", f'{len(prod.get("flujos") or [])} flujo(s) clave', "grid"),
        ("Agentes recomendados", len(d.get("agentes") or []), "", f'rol · {d.get("rol", "")}', "persona"),
        ("Tareas del plan", len(d.get("plan") or []), "", "con su criterio de hecho", "lista"),
        ("Entorno", "Listo" if entorno and not faltan else f"{faltan} pendiente(s)" if entorno else "—",
         "ok" if entorno and not faltan else "warn" if entorno else "", "según npm run doctor", "ok" if entorno and not faltan else "warn"),
    ])]
    for f in d.get("faltantes") or []:
        body.append(banner(f, "warn"))
    if d.get("resumen"):
        body.append(section("Bienvenida", f'<div class="cardbody"><p class="lead">{e(d["resumen"])}</p></div>'))
    if prod.get("modulos"):
        body.append(section("El producto: módulos", table(["Módulo", "Qué hace", "Fuente"],
                                                          [[f'<b>{e(m.get("nombre"))}</b>', e(m.get("descripcion")), f'<span class="mono">{e(m.get("fuente", "—"))}</span>']
                                                           for m in prod["modulos"]])))
    izq = section("Flujos clave", table(["Flujo", "Pantallas", "Fuente"], [[f'<b>{e(f.get("nombre"))}</b>', e(f.get("pantallas")),
                                                                          f'<span class="mono">{e(f.get("fuente", "—"))}</span>'] for f in prod.get("flujos") or []]), ancho=6) \
        if prod.get("flujos") else ""
    der = section("Roles de la aplicación", table(["Rol", "Puede"], [[f'<b>{e(r.get("rol"))}</b>', e(r.get("puede"))] for r in prod.get("roles") or []]), ancho=6) \
        if prod.get("roles") else ""
    if izq and der:
        body.append(two_col(izq, der))
    elif izq or der:
        body.append(izq or der)
    if entorno:
        color = {"ok": OK, "aviso": AVISO, "falta": CRITICO}
        icono = {"ok": "✓", "aviso": "!", "falta": "✕"}
        body.append(section("Tu entorno", table(["Qué", "Estado", "Detalle", "Qué hacer"],
                                                [[f'<b>{e(x.get("que"))}</b>', _pastilla(TEXTO_ESTADO.get(x.get("estado"), "—"), color.get(x.get("estado"), AVISO),
                                                                                      icono.get(x.get("estado"), "●")),
                                                  e(x.get("detalle")), f'<span class="mono">{e(x.get("accion", ""))}</span>'] for x in entorno])))
    if d.get("agentes"):
        body.append(section(f'k0lmenIA para tu rol · {d.get("rol", "")}', table(["Agente", "Para qué", "Pedido de ejemplo para este proyecto"],
                                                                              [[f'<b>{e(a.get("agente"))}</b>', e(a.get("para_que")),
                                                                                f'<span class="pedido-ej">{e(a.get("pedido"))}</span>'] for a in d["agentes"]])))
    if d.get("plan"):
        body.append(section("Plan de las primeras semanas", table(["Cuándo", "Tarea", "Está hecho cuando", "Con"],
                                                                  [[f'<b>{e(p.get("cuando"))}</b>', e(p.get("tarea")), e(p.get("hecho_cuando")),
                                                                    e(p.get("agente") or "—")] for p in d["plan"]])))
    if d.get("preguntas"):
        body.append(section("Preguntas para el equipo", table(["ID", "Pregunta", "A quién", "Por qué"],
                                                              [[f'<span class="id">{e(q.get("id", ""))}</span>', e(q.get("pregunta")), e(q.get("a_quien", "—")),
                                                                e(q.get("por_que", ""))] for q in d["preguntas"]]),
                            "lo que no está documentado: no se inventa"))
    if prod.get("glosario"):
        body.append(section("Glosario", table(["Término", "Qué significa"], [[f'<b>{e(g.get("termino"))}</b>', e(g.get("definicion"))]
                                                                             for g in prod["glosario"]])))
    if d.get("checklist"):
        items = "".join(f'<li><label><input type="checkbox" id="c{i}"><span>{e(c)}</span></label></li>' for i, c in enumerate(d["checklist"]))
        body.append(section("Checklist", f'<div class="progreso"><span class="t"></span><span class="b"><span></span></span></div><ul class="check">{items}</ul>',
                            "se guarda en este navegador"))
    titulo = f'Onboarding · {d.get("persona", "")}'.strip(" ·")
    html = page(titulo, "Onboarding", meta([("Rol", d.get("rol")), ("Proyecto", d.get("proyecto")), ("Fecha", d.get("fecha"))]), "".join(body))
    js = JS_ONB.replace("' de '+cajas.length+' hechos'", "' of '+cajas.length+' done'") if idioma_actual() == "en" else JS_ONB
    return html.replace("</style>", CSS_ONB + "</style>", 1).replace("</body>", f"<script>{js}</script></body>", 1)


def build_md(d):
    prod = d.get("producto") or {}
    l = [f'# Onboarding de {d.get("persona", "")}', "", f'- **Rol:** {d.get("rol", "")}', f'- **Proyecto:** {d.get("proyecto", "")}',
         f'- **Fecha:** {d.get("fecha", "")}', ""]
    for f in d.get("faltantes") or []:
        l += [f"> {f}", ""]
    if d.get("resumen"):
        l += ["## Bienvenida", "", d["resumen"], ""]

    def tabla(titulo, cab, filas):
        if not filas:
            return
        l.extend([f"## {titulo}", "", "| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)])
        l.extend("| " + " | ".join(str(c or "").replace("|", "/").replace("\n", " ") for c in f) + " |" for f in filas)
        l.append("")

    tabla("El producto: módulos", ["Módulo", "Qué hace", "Fuente"], [[m.get("nombre"), m.get("descripcion"), m.get("fuente")] for m in prod.get("modulos") or []])
    tabla("Flujos clave", ["Flujo", "Pantallas", "Fuente"], [[f.get("nombre"), f.get("pantallas"), f.get("fuente")] for f in prod.get("flujos") or []])
    tabla("Roles de la aplicación", ["Rol", "Puede"], [[r.get("rol"), r.get("puede")] for r in prod.get("roles") or []])
    tabla("Tu entorno", ["Qué", "Estado", "Detalle", "Qué hacer"],
          [[x.get("que"), TEXTO_ESTADO.get(x.get("estado"), ""), x.get("detalle"), x.get("accion")] for x in d.get("entorno") or []])
    tabla(f'k0lmenIA para tu rol: {d.get("rol", "")}', ["Agente", "Para qué", "Pedido de ejemplo"],
          [[a.get("agente"), a.get("para_que"), a.get("pedido")] for a in d.get("agentes") or []])
    tabla("Plan de las primeras semanas", ["Cuándo", "Tarea", "Está hecho cuando", "Con"],
          [[p.get("cuando"), p.get("tarea"), p.get("hecho_cuando"), p.get("agente") or "-"] for p in d.get("plan") or []])
    tabla("Preguntas para el equipo", ["ID", "Pregunta", "A quién", "Por qué"],
          [[q.get("id"), q.get("pregunta"), q.get("a_quien"), q.get("por_que")] for q in d.get("preguntas") or []])
    tabla("Glosario", ["Término", "Qué significa"], [[g.get("termino"), g.get("definicion")] for g in prod.get("glosario") or []])
    if d.get("checklist"):
        l += ["## Checklist", ""] + [f"- [ ] {c}" for c in d["checklist"]] + [""]
    return "\n".join(l)


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Plan de onboarding (agente guia-onboarding)")
    ap.add_argument("plan_json")
    ap.add_argument("--salida", help="carpeta de salida (por defecto output/onboarding/<persona o rol>)")
    a = ap.parse_args(argv)
    d = json.loads(Path(a.plan_json).read_text(encoding="utf-8"))
    if not d.get("persona") and not d.get("rol"):
        ap.error('el JSON necesita "persona" o "rol"')
    carpeta = Path(a.salida) if a.salida else RAIZ / "output" / "onboarding" / slug(d.get("persona") or d.get("rol"))
    carpeta.mkdir(parents=True, exist_ok=True)
    # ES y EN (el .md queda en español): el inglés del agente va en el bloque "en" del plan.
    escribir_bilingue(carpeta / "plan-onboarding.html", lambda: build_html(localizar(d)))
    md = carpeta / "plan-onboarding.md"
    md.write_text(build_md(d), encoding="utf-8")
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "formatear_tablas.py"), str(md)], capture_output=True, text=True)
    print(f"Plan de onboarding: {carpeta / 'plan-onboarding.html'} (y plan-onboarding.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Charters de pruebas exploratorias por sesiones (agente generador-charters): las hojas de cada sesión y,
después de las sesiones, el informe a partir de las notas.

Uso (desde la raíz del repo):
    python scripts/generar_charters.py --nombre HU-001                   → arma las hojas (charters.json → charters.html y charters.md)
    python scripts/generar_charters.py --nombre HU-001 --informe         → lee sesiones/*.md y arma informe-sesiones.html

Carpeta: output/charters/<nombre>/ con charters.json (lo escribe el agente), charters.html (para imprimir o
compartir: una hoja por sesión), charters.md, sesiones/CH-01.md (una plantilla de notas por charter, para
completar durante la sesión) e informe-sesiones.html. El informe anterior pasa a historial/ (últimos 5).

charters.json:
{
  "historia": "HU-001", "titulo": "Checkout", "objetivo": "Encontrar riesgos del pago antes de la release",
  "charters": [
    {"id": "CH-01", "mision": "Explorar el pago con tarjeta con datos límite para descubrir errores de validación",
     "areas": ["Formulario de tarjeta", "Mensajes de error"], "riesgos": ["Cobros duplicados"],
     "heuristicas": ["Valores límite", "Interrupciones"], "datos": ["Tarjeta vencida 4111..."],
     "ideas": ["Pagar dos veces seguidas"], "duracion_min": 60, "prioridad": "Alta",
     "fuera_de_alcance": ["Pagos con transferencia"], "preguntas": ["¿Qué pasa si el banco tarda?"]}
  ]
}

Notas de una sesión (sesiones/CH-01.md): encabezado y líneas con prefijo; lo demás se ignora.
    Charter: CH-01
    Tester: Ana
    Fecha: 2026-10-12
    Duración: 60
    Tiempo: preparación 10, prueba 35, bugs 15        (minutos: el reparto TBS de session-based testing)
    BUG: El total no suma el envío [Alta]
    PREGUNTA: ¿El cupón se aplica antes o después del envío?
    IDEA: Probar con dos pestañas abiertas
    RIESGO: Si el banco tarda, no hay mensaje
    CUBIERTO: Formulario de tarjeta
    SIN CUBRIR: Mensajes de error
    NOTA: Usé la tarjeta de prueba de Visa
"""
import os
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
sys.path.insert(0, str(RAIZ / "scripts"))
import _historial  # noqa: E402
from _i18n import escribir_bilingue, localizar, idioma_actual  # noqa: E402
from _estilos_reporte import (e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, stacked_bars, two_col,  # noqa: E402
                              nivel_badge, _pastilla, CRITICO, AVISO, NEUTRO, OK, SERIES)

ETIQUETAS = {"BUG": "bugs", "PREGUNTA": "preguntas", "IDEA": "ideas", "RIESGO": "riesgos", "CUBIERTO": "cubierto", "SIN CUBRIR": "sin_cubrir", "NOTA": "notas"}

CSS_CH = """
<style>
.hoja{border:1px solid var(--border);border-radius:14px;background:var(--bg);padding:20px 22px;margin:14px 24px;page-break-inside:avoid}
.hoja h3{font-size:18px;color:var(--ink);display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
.mision{font-size:15px;color:var(--ink);line-height:1.55;border-left:3px solid var(--accent);padding:6px 12px;margin:8px 0 14px;background:rgba(249,176,6,.06);border-radius:0 8px 8px 0}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 22px}
.grid2 .lbl{margin:0 0 4px}
.grid2 ul{margin:0;padding-left:18px;color:var(--body);font-size:13px}
.notas{margin-top:14px;border:1px dashed var(--border);border-radius:10px;padding:10px 12px;color:var(--muted);font-size:12.5px;min-height:90px}
.tags{display:flex;gap:6px;flex-wrap:wrap}
@media (max-width:760px){.grid2{grid-template-columns:1fr}}
@media print{body{background:#fff}.hoja{background:#fff;color:#000;border-color:#999}}
</style>
"""


def _lista(xs):
    xs = [x for x in xs or [] if str(x).strip()]
    return "<ul>" + "".join(f"<li>{e(x)}</li>" for x in xs) + "</ul>" if xs else '<p class="muted">—</p>'


def hojas_html(datos):
    chs = datos.get("charters") or []
    total = sum(c.get("duracion_min") or 0 for c in chs)
    body = [banner(datos.get("objetivo") or f'{len(chs)} sesión(es) de exploración', "ok"),
            '<div style="margin-top:20px">' + kpi_tiles([
                ("Charters", len(chs), "", datos.get("titulo") or "", "lista"),
                ("Tiempo total", f"{total} min", "", "duración planificada de las sesiones", "reloj"),
                ("Alta prioridad", sum(1 for c in chs if c.get("prioridad") in ("Crítica", "Alta")), "", "empezá por estas", "objetivo"),
                ("Riesgos cubiertos", len({r for c in chs for r in c.get("riesgos") or []}), "", "riesgos distintos que apuntan las sesiones", "warn"),
            ]) + "</div>"]
    filas = [[f'<a href="#{e(c["id"])}" style="color:var(--ink)">{e(c["id"])}</a>', f'<strong style="color:var(--ink)">{e(c.get("mision"))}</strong>',
              nivel_badge(c.get("prioridad") or "Media"), e(f'{c.get("duracion_min") or "—"} min'), e(", ".join(c.get("areas") or []))] for c in chs]
    body.append(section("Sesiones", table(["Charter", "Misión", "Prioridad", "Duración", "Áreas"], filas), "una sesión = un charter, con tiempo fijo"))
    hojas = []
    for c in chs:
        hojas.append(f'''<div class="hoja" id="{e(c["id"])}"><h3>{e(c["id"])} {nivel_badge(c.get("prioridad") or "Media")}
          {_pastilla(f'{c.get("duracion_min") or "—"} min', SERIES[2], "◷")}</h3>
          <div class="mision">{e(c.get("mision"))}</div>
          <div class="grid2"><div><div class="lbl">Áreas a explorar</div>{_lista(c.get("areas"))}</div>
          <div><div class="lbl">Riesgos</div>{_lista(c.get("riesgos"))}</div>
          <div><div class="lbl">Heurísticas y técnicas</div>{_lista(c.get("heuristicas"))}</div>
          <div><div class="lbl">Datos de prueba</div>{_lista(c.get("datos"))}</div>
          <div><div class="lbl">Ideas para empezar</div>{_lista(c.get("ideas"))}</div>
          <div><div class="lbl">Fuera de alcance</div>{_lista(c.get("fuera_de_alcance"))}</div></div>
          {f'<div class="lbl">Preguntas abiertas</div>{_lista(c.get("preguntas"))}' if c.get("preguntas") else ""}
          <div class="notas">Notas de la sesión (en <span class="mono">sesiones/{e(c["id"])}.md</span>): BUG: · PREGUNTA: · IDEA: · RIESGO: · CUBIERTO: · SIN CUBRIR: · NOTA:<br>
          Tiempo: preparación __ · prueba __ · bugs __ (min)</div></div>''')
    body.append(section("Hojas de sesión", "".join(hojas), "para imprimir o compartir con quien explora"))
    m = meta([("Historia", datos.get("historia")), ("Fecha", (datos.get("fecha") or "")[:10])])
    return page("Charters de exploración", "Pruebas exploratorias por sesiones", m, CSS_CH + "".join(body))


def hojas_md(datos):
    partes = [f'# Charters de exploración — {datos.get("historia") or ""} {datos.get("titulo") or ""}'.strip(), ""]
    if datos.get("objetivo"):
        partes += [f'**Objetivo:** {datos["objetivo"]}', ""]
    for c in datos.get("charters") or []:
        partes += [f'## {c["id"]} · {c.get("prioridad") or "Media"} · {c.get("duracion_min") or "—"} min', "", f'**Misión:** {c.get("mision")}', ""]
        for titulo, k in (("Áreas", "areas"), ("Riesgos", "riesgos"), ("Heurísticas", "heuristicas"), ("Datos", "datos"), ("Ideas", "ideas"),
                          ("Fuera de alcance", "fuera_de_alcance"), ("Preguntas", "preguntas")):
            if c.get(k):
                partes += [f"**{titulo}:**", ""] + [f"- {x}" for x in c[k]] + [""]
    return "\n".join(partes) + "\n"


def plantilla_notas(c):
    return (f'Charter: {c["id"]}\nTester: \nFecha: {datetime.date.today().isoformat()}\nDuración: {c.get("duracion_min") or 60}\n'
            f'Tiempo: preparación 0, prueba 0, bugs 0\n\n# Misión: {c.get("mision")}\n# Una línea por cosa, con su prefijo:\n'
            '# BUG: qué pasó [Alta]   PREGUNTA:   IDEA:   RIESGO:   CUBIERTO: área   SIN CUBRIR: área   NOTA:\n\n')


def leer_notas(arch):
    s = {"archivo": arch.name, "bugs": [], "preguntas": [], "ideas": [], "riesgos": [], "cubierto": [], "sin_cubrir": [], "notas": []}
    for l in arch.read_text(encoding="utf-8").splitlines():
        l = l.strip()
        if not l or l.startswith("#"):
            continue
        m = re.match(r"^(Charter|Tester|Fecha|Duración|Duracion|Tiempo)\s*:\s*(.*)$", l, re.I)
        if m:
            k, v = m.group(1).lower().replace("duración", "duracion"), m.group(2).strip()
            if k == "tiempo":
                for parte in re.split(r"[,·;]", v):
                    mm = re.match(r"\s*(preparaci[oó]n|prueba|bugs?)\s*(\d+)", parte, re.I)
                    if mm:
                        nombre = mm.group(1).lower()
                        clave = "t_preparacion" if nombre.startswith("prep") else "t_bugs" if nombre.startswith("bug") else "t_prueba"
                        s[clave] = int(mm.group(2))
            elif k == "duracion":
                s["duracion"] = int(re.sub(r"\D", "", v) or 0) or None
            else:
                s[k] = v
            continue
        m = re.match(r"^(BUG|PREGUNTA|IDEA|RIESGO|CUBIERTO|SIN CUBRIR|NOTA)\s*:\s*(.+)$", l, re.I)
        if m:
            k = ETIQUETAS[m.group(1).upper()]
            texto = m.group(2).strip()
            if k == "bugs":
                sev = re.search(r"\[(Crítica|Critica|Alta|Media|Baja)\]\s*$", texto, re.I)
                s["bugs"].append({"texto": re.sub(r"\s*\[[^\]]+\]\s*$", "", texto), "severidad": (sev.group(1).capitalize().replace("Critica", "Crítica") if sev else "Media")})
            else:
                s[k].append(texto)
    return s


def informe_html(datos, sesiones, hist_html=""):
    chs = {c["id"]: c for c in datos.get("charters") or []}
    hechas = [s for s in sesiones if s.get("charter")]
    bugs = [dict(b, charter=s["charter"]) for s in hechas for b in s["bugs"]]
    minutos = sum(s.get("duracion") or 0 for s in hechas)
    areas_obj = {(cid, a) for cid, c in chs.items() for a in c.get("areas") or []}
    cubiertas = {(s["charter"], a) for s in hechas for a in s["cubierto"]}
    cobertura = round(len(cubiertas & areas_obj) / len(areas_obj) * 100) if areas_obj else None
    altas = [b for b in bugs if b["severidad"] in ("Crítica", "Alta")]
    body = [banner(f'{len(hechas)} de {len(chs)} sesión(es) hechas · {len(bugs)} bug(s), {len(altas)} importantes',
                   "bad" if altas else "warn" if bugs or len(hechas) < len(chs) else "ok"),
            '<div style="margin-top:20px">' + kpi_tiles([
                ("Sesiones", f"{len(hechas)}/{len(chs)}", "ok" if len(hechas) >= len(chs) else "warn", "hechas de las planificadas", "lista", {"pct": len(hechas) / len(chs) * 100 if chs else 0}),
                ("Tiempo de exploración", f"{minutos} min", "", "suma de las sesiones", "reloj"),
                ("Bugs", len(bugs), "bad" if altas else ("warn" if bugs else "ok"), f"{len(altas)} de severidad alta o crítica", "bicho"),
                ("Preguntas", sum(len(s["preguntas"]) for s in hechas), "warn" if any(s["preguntas"] for s in hechas) else "", "para el PO o el equipo", "lupa"),
                ("Riesgos nuevos", sum(len(s["riesgos"]) for s in hechas), "", "aparecidos en las sesiones", "warn"),
                ("Áreas cubiertas", f"{cobertura} %" if cobertura is not None else "—", "" if cobertura is None else ("ok" if cobertura >= 80 else "warn"),
                 "de las áreas planificadas en los charters", "objetivo", {"pct": cobertura or 0}),
            ]) + "</div>"]
    tbs = [(s["charter"], [s.get("t_preparacion") or 0, s.get("t_prueba") or 0, s.get("t_bugs") or 0]) for s in hechas]
    if any(sum(v) for _, v in tbs):
        body.append(two_col(section("En qué se fue el tiempo", stacked_bars(tbs, [("Preparación", SERIES[0]), ("Prueba", SERIES[1]), ("Bugs", SERIES[7])]),
                                    "reparto TBS: mucha preparación o mucho tiempo con bugs reduce la exploración"),
                            section("Bugs por sesión", bar_chart([(s["charter"], len(s["bugs"]), SERIES[7]) for s in hechas], ancho_etiqueta=80))))
    if bugs:
        filas = [[nivel_badge(b["severidad"]), f'<strong style="color:var(--ink)">{e(b["texto"])}</strong>', e(b["charter"])] for b in bugs]
        body.append(section("Bugs encontrados", table(["Severidad", "Bug", "Sesión"], filas), "redactalos con el generador-reportes-bug"))
    preg = [(p, s["charter"]) for s in hechas for p in s["preguntas"]]
    if preg:
        body.append(section("Preguntas abiertas", table(["Pregunta", "Sesión"], [[e(p), e(c)] for p, c in preg])))
    filas = []
    for cid, c in chs.items():
        s = next((x for x in hechas if x["charter"] == cid), None)
        estado = _pastilla("Hecha", OK, "✓") if s else _pastilla("Pendiente", AVISO, "◷")
        cub = ", ".join(s["cubierto"]) if s else "—"
        sin = ", ".join(s["sin_cubrir"]) if s else ", ".join(c.get("areas") or [])
        filas.append([f'<strong style="color:var(--ink)">{e(cid)}</strong>', e(c.get("mision")), estado, e(s.get("tester", "—") if s else "—"),
                      e(cub or "—"), e(sin or "—"), e(f'{s.get("duracion") or "—"} min' if s else "—")])
    body.append(section("Cada charter", table(["Charter", "Misión", "Estado", "Tester", "Cubierto", "Sin cubrir", "Duración"], filas)))
    for titulo, k in (("Ideas para próximas sesiones", "ideas"), ("Riesgos que aparecieron", "riesgos"), ("Notas", "notas")):
        xs = [f'{x} ({s["charter"]})' for s in hechas for x in s[k]]
        if xs:
            body.append(section(titulo, doc_list(xs)))
    if hist_html:
        body.append(hist_html)
    m = meta([("Historia", datos.get("historia")), ("Fecha", datetime.date.today().isoformat())])
    return page("Informe de sesiones", "Pruebas exploratorias por sesiones", m, CSS_CH + "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Charters y sesiones de pruebas exploratorias")
    ap.add_argument("--nombre", required=True, help="carpeta: output/charters/<nombre>/ (por ejemplo, HU-001)")
    ap.add_argument("--informe", action="store_true", help="arma el informe a partir de las notas de sesiones/")
    ap.add_argument("--salida")
    a = ap.parse_args()
    carpeta = Path(a.salida) if a.salida else PROYECTO / "output" / "charters" / a.nombre
    arch = carpeta / "charters.json"
    if not arch.exists():
        sys.exit(f"No existe {arch}: el agente tiene que escribir primero los charters.")
    datos = json.loads(arch.read_text(encoding="utf-8"))
    dir_ses = carpeta / "sesiones"
    if not a.informe:
        datos.setdefault("fecha", datetime.datetime.now().isoformat(timespec="seconds"))
        # ES y EN (el .md queda en español): el inglés del agente va en el bloque "en" del charters.json.
        escribir_bilingue(carpeta / "charters.html", lambda: hojas_html(localizar(datos)))
        (carpeta / "charters.md").write_text(hojas_md(datos), encoding="utf-8")
        dir_ses.mkdir(exist_ok=True)
        for c in datos.get("charters") or []:
            notas = dir_ses / f'{c["id"]}.md'
            if not notas.exists():  # nunca pisa notas ya escritas
                notas.write_text(plantilla_notas(c), encoding="utf-8")
        print(f'{len(datos.get("charters") or [])} charter(s) · {carpeta / "charters.html"} · notas en {dir_ses}')
        return
    sesiones = [leer_notas(f) for f in sorted(dir_ses.glob("*.md"))]
    sesiones = [s for s in sesiones if s.get("charter") and (s["bugs"] or s["cubierto"] or s["notas"] or s["preguntas"] or s["ideas"] or s.get("tester"))]
    ahora = datetime.datetime.now()
    resumen = {"sesiones": len(sesiones), "charters": len(datos.get("charters") or []), "bugs": sum(len(s["bugs"]) for s in sesiones),
               "preguntas": sum(len(s["preguntas"]) for s in sesiones), "minutos": sum(s.get("duracion") or 0 for s in sesiones)}
    resultado = {"historia": datos.get("historia"), "fecha": ahora.isoformat(timespec="seconds"), "marca": ahora.strftime("%Y%m%d-%H%M%S"),
                 "resumen": resumen, "sesiones": sesiones, "hallazgos": [dict(b, charter=s["charter"]) for s in sesiones for b in s["bugs"]]}
    _historial.archivar(carpeta, ["sesiones.json", "informe-sesiones.html"], "sesiones.json")
    (carpeta / "sesiones.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    hist = _historial.seccion("charters", carpeta, resultado)
    escribir_bilingue(carpeta / "informe-sesiones.html", lambda: informe_html(localizar(datos), sesiones, hist))
    print(f'Sesiones: {resumen["sesiones"]}/{resumen["charters"]} · bugs: {resumen["bugs"]} · preguntas: {resumen["preguntas"]} · {resumen["minutos"]} min')
    print(f'OK: {carpeta / "informe-sesiones.html"}')


if __name__ == "__main__":
    main()

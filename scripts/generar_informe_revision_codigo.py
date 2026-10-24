#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) de la revisión estática de código (agente revisor-codigo), y opcionalmente el
Markdown con los comentarios para pegar en el PR/MR.

Uso (desde la raíz del repo):
    python scripts/generar_informe_revision_codigo.py <analisis.json> <salida.html> [--markdown comentarios-pr.md]

El relevamiento lo hacen `herramientas/codigo/obtener.py` (trae el código) y `herramientas/codigo/revision.py`
(reglas + métricas + escáneres); el agente lo triagea (confirma leyendo el código, descarta falsos positivos,
prioriza) y escribe analisis.json. Los secretos van redactados (archivo:línea), nunca el valor.

Esquema del analisis.json (todo opcional salvo "titulo"):
{
  "titulo": "Revisión de código — mi-app PR #42", "generado": "2026-10-23T12:00:00",
  "origen": {"repo": "mi-empresa/mi-app", "proveedor": "github", "rama": "feature-x", "base": "main",
             "commit": "abc123", "pr": {"numero": 42, "titulo": "...", "url": "...", "autor": "..."},
             "url_blob": "https://github.com/mi-empresa/mi-app/blob/abc123/{archivo}#L{linea}"},
  "escaneres": ["reglas k0lmenIA", "secretos (integrado)", "semgrep"],
  "decision": "Pedir cambios",            (Aprobar | Aprobar con comentarios | Pedir cambios)
  "veredicto": "2 problemas de seguridad bloquean el merge", "veredicto_tono": "bad", "resumen": "...",
  "metricas": {"archivos": 120, "lineas": 15000, "archivos_cambiados": 8, "lenguajes": {"Python": 9000},
               "funciones_complejas": [{"archivo": "...", "nombre": "...", "linea": 10, "lineas": 140, "complejidad": 32}]},
  "hallazgos": [{"id": "RC-01", "severidad": "Alta", "categoria": "Seguridad", "archivo": "src/db.py", "linea": 42,
                 "titulo": "Inyección SQL en buscar()", "texto": "...", "impacto": "...", "recomendacion": "...",
                 "sugerencia": "cursor.execute('... %s', (nombre,))", "cwe": "CWE-89", "regla": "SEG-SQL",
                 "en_cambio": true}],
  "descartados": [{"regla": "SEG-CRIPTO", "archivo": "...", "linea": 3, "motivo": "md5 para nombres de archivo, no seguridad"}],
  "fortalezas": ["..."],
  "recomendaciones": [{"prioridad": "Alta", "accion": "...", "motivo": "..."}],
  "proximos_pasos": ["..."], "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}]
}
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list, stacked_bars,  # noqa: E402
                              nivel_badge, falta_informacion, e, NIVEL_COLOR)

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
SEVERIDADES = ["Crítica", "Alta", "Media", "Baja"]
CATEGORIAS = ["Seguridad", "Performance", "Confiabilidad", "Malas prácticas", "Mantenibilidad"]
TONO_DECISION = {"Aprobar": "ok", "Aprobar con comentarios": "warn", "Pedir cambios": "bad"}

CSS = """
<style>
.sug{margin:8px 0 2px;border:1px solid var(--border);border-radius:10px;overflow:auto;background:#120F0B;
  font-family:var(--mono);font-size:12.5px;line-height:1.6;padding:10px 14px;white-space:pre;color:#C6EDB9}
.frag{font-family:var(--mono);font-size:12px;color:var(--muted);word-break:break-all}
.ubic a{color:var(--ink);text-decoration:underline;text-decoration-color:rgba(244,239,230,.3)}
.cambio{font-size:11px;color:var(--muted);margin-left:6px;white-space:nowrap}
</style>
"""


def link(origen, archivo, linea):
    plantilla = (origen or {}).get("url_blob")
    txt = f"{archivo}:{linea}" if linea else (archivo or "")
    if plantilla and archivo:
        url = plantilla.replace("{archivo}", str(archivo)).replace("{linea}", str(linea or 1))
        return f'<span class="ubic"><a href="{e(url)}" target="_blank" rel="noopener">{e(txt)}</a></span>'
    return f'<span class="ubic mono">{e(txt)}</span>'


def generar(analisis_json, salida, markdown=None):
    d = json.loads(Path(analisis_json).read_text(encoding="utf-8"))
    origen = d.get("origen") or {}
    pr = origen.get("pr") or {}
    m = d.get("metricas") or {}
    hall = sorted(d.get("hallazgos") or [], key=lambda x: (ORDEN_SEV.get(x.get("severidad"), 9),
                                                          CATEGORIAS.index(x["categoria"]) if x.get("categoria") in CATEGORIAS else 9))
    for h in hall:
        if h.get("severidad") not in ORDEN_SEV:
            print(f"[aviso] analisis.json · {h.get('id')}: severidad {h.get('severidad')!r} fuera de la escala", file=sys.stderr)
    graves = sum(1 for h in hall if h.get("severidad") in ("Crítica", "Alta"))
    seg = sum(1 for h in hall if h.get("categoria") == "Seguridad")
    perf = sum(1 for h in hall if h.get("categoria") == "Performance")
    en_cambio = sum(1 for h in hall if h.get("en_cambio"))

    kpis = [("Hallazgos", len(hall), "bad" if graves else ("warn" if hall else "ok"), f"{graves} crítico(s) o alto(s)", "bicho"),
            ("Seguridad", seg, "bad" if any(h.get("categoria") == "Seguridad" and h.get("severidad") in ("Crítica", "Alta") for h in hall)
             else ("warn" if seg else "ok"), "confirmados", "escudo"),
            ("Performance", perf, "warn" if perf else "ok", "confirmados", "rayo")]
    if m.get("archivos_cambiados") is not None:
        kpis.append(("Archivos cambiados", m["archivos_cambiados"], "", f"{en_cambio} hallazgo(s) en líneas cambiadas", "codigo"))
    elif m.get("archivos"):
        kpis.append(("Archivos revisados", m["archivos"], "", f"{m.get('lineas', '—')} líneas", "codigo"))

    cuerpo = CSS
    if d.get("decision"):
        cuerpo += banner(f"Decisión sugerida: {d['decision']}" + (f" — {d['veredicto']}" if d.get("veredicto") else ""),
                         TONO_DECISION.get(d["decision"], d.get("veredicto_tono") or "warn"))
    elif d.get("veredicto"):
        cuerpo += banner(d["veredicto"], d.get("veredicto_tono") if d.get("veredicto_tono") in ("ok", "warn", "bad") else "warn")
    if any(h.get("regla") == "SEG-SECRETO" or "secreto" in (h.get("titulo") or "").lower() for h in hall):
        cuerpo += banner("Hay secretos en el código: rotá las credenciales expuestas y sacalas del repositorio (histórico de git incluido).", "bad")
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(d["resumen"])}</p></div>' if d.get("resumen") else ""))

    if hall:
        series = [(s, NIVEL_COLOR.get(s, "#888")) for s in SEVERIDADES]
        filas = [(c, [sum(1 for h in hall if h.get("categoria") == c and h.get("severidad") == s) for s in SEVERIDADES])
                 for c in CATEGORIAS + sorted({h.get("categoria") for h in hall if h.get("categoria") not in CATEGORIAS} - {None})]
        cuerpo += section("Por categoría y severidad", stacked_bars(filas, series))
        tabla = []
        for h in hall:
            titulo = f'<b>{e(h["titulo"])}</b><br>' if h.get("titulo") else ""
            marca = '<span class="cambio">● línea cambiada</span>' if h.get("en_cambio") else ""
            cwe = f' <span class="muted">{e(h["cwe"])}</span>' if h.get("cwe") else ""
            tabla.append([f'<span class="id">{e(h.get("id", ""))}</span>', nivel_badge(h.get("severidad")),
                          e(h.get("categoria", "")) + cwe, link(origen, h.get("archivo"), h.get("linea")) + marca,
                          titulo + e(h.get("texto", "")), e(h.get("recomendacion", ""))])
        cuerpo += section("Hallazgos", table(["ID", "Severidad", "Categoría", "Ubicación", "Qué pasa", "Recomendación"], tabla),
                          f"{len(hall)} confirmados")
        detalle = [h for h in hall if h.get("sugerencia") or h.get("impacto")]
        if detalle:
            filas_d = [[f'<span class="id">{e(h.get("id"))}</span>', e(h.get("impacto") or "—"),
                        (f'<div class="sug">{e(h["sugerencia"])}</div>' if h.get("sugerencia") else "—")] for h in detalle]
            cuerpo += section("Impacto y cambio sugerido", table(["ID", "Impacto", "Cómo quedaría"], filas_d))
    else:
        cuerpo += section("Hallazgos", banner("Sin hallazgos confirmados.", "ok"))

    if m.get("funciones_complejas"):
        cuerpo += section("Funciones más complejas", table(
            ["Función", "Ubicación", "Líneas", "Complejidad"],
            [[e(f.get("nombre", "")), link(origen, f.get("archivo"), f.get("linea")), e(f.get("lineas", "")), e(f.get("complejidad", ""))]
             for f in m["funciones_complejas"][:15]]), "candidatas a refactorizar", ancho=8)
    if m.get("lenguajes"):
        cuerpo += section("Lenguajes", table(["Lenguaje", "Líneas"], [[e(k), e(v if not isinstance(v, dict) else v.get("lineas"))]
                                                                      for k, v in m["lenguajes"].items()]), ancho=4)
    if d.get("fortalezas"):
        cuerpo += section("Lo que está bien", doc_list(d["fortalezas"]))
    if d.get("descartados"):
        cuerpo += section("Descartados (falsos positivos)", table(
            ["Regla", "Ubicación", "Por qué se descartó"],
            [[e(x.get("regla", "")), link(origen, x.get("archivo"), x.get("linea")), e(x.get("motivo", ""))] for x in d["descartados"]]),
            f"{len(d['descartados'])} revisados y descartados")
    if d.get("recomendaciones"):
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"],
                          [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))] for x in d["recomendaciones"]]))
    if d.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(d["proximos_pasos"]))
    cuerpo += falta_informacion(d.get("falta_informacion"))

    destino = origen.get("repo") or origen.get("ruta")
    if pr.get("numero"):
        destino = f"{destino} · PR #{pr['numero']}"
    html = page(d.get("titulo") or "Revisión de código", "Revisión estática de código",
                meta([("Generado", d.get("generado")), ("Repositorio", destino),
                      ("Rama", f"{origen.get('rama')} → {origen.get('base')}" if origen.get("base") else origen.get("rama")),
                      ("Commit", (origen.get("commit") or "")[:10] or None),
                      ("Escáneres", ", ".join(d.get("escaneres") or []) or None)]), cuerpo)
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    Path(salida).write_text(html, encoding="utf-8")
    if markdown:
        Path(markdown).write_text(comentarios_md(d, hall), encoding="utf-8")
    return salida


def comentarios_md(d, hall):
    """Markdown para pegar como comentario general del PR/MR (agrupado por archivo, con links)."""
    origen = d.get("origen") or {}
    out = [f"## Revisión de código — {d.get('decision') or 'resultado'}", ""]
    if d.get("veredicto"):
        out += [d["veredicto"], ""]
    if d.get("resumen"):
        out += [d["resumen"], ""]
    if not hall:
        out += ["Sin hallazgos confirmados.", ""]
    por_archivo = {}
    for h in hall:
        por_archivo.setdefault(h.get("archivo") or "(general)", []).append(h)
    for archivo, hs in por_archivo.items():
        out += [f"### `{archivo}`", ""]
        for h in sorted(hs, key=lambda x: x.get("linea") or 0):
            plantilla = origen.get("url_blob")
            lugar = f"L{h.get('linea')}" if h.get("linea") else ""
            if plantilla and h.get("linea"):
                lugar = f"[{lugar}]({plantilla.replace('{archivo}', archivo).replace('{linea}', str(h['linea']))})"
            titulo = h.get("titulo") or h.get("texto", "")
            out.append(f"- **{h.get('severidad')} · {h.get('categoria')}** {lugar} — {titulo}")
            if h.get("titulo") and h.get("texto"):
                out.append(f"  {h['texto']}")
            if h.get("recomendacion"):
                out.append(f"  *Sugerencia:* {h['recomendacion']}")
            if h.get("sugerencia"):
                out += ["", "  ```", *[f"  {l}" for l in h["sugerencia"].splitlines()], "  ```"]
        out.append("")
    if d.get("fortalezas"):
        out += ["### Lo que está bien", "", *[f"- {f}" for f in d["fortalezas"]], ""]
    out += ["---", "_Revisión estática generada con k0lmenIA (revisor-codigo). Cada hallazgo fue confirmado leyendo el código._", ""]
    return "\n".join(out)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de la revisión estática de código (y Markdown para el PR).")
    ap.add_argument("analisis_json")
    ap.add_argument("salida")
    ap.add_argument("--markdown", default="", help="además, el Markdown con los comentarios para pegar en el PR/MR")
    args = ap.parse_args()
    print(generar(args.analisis_json, args.salida, args.markdown or None))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Genera un Plan de Pruebas en HTML (dashboard, modo oscuro) desde un JSON.

Uso:
    python scripts/generar_plan.py <plan.json> <salida.html>

JSON de entrada:
{
  "titulo": "Plan de pruebas — Registro de cuenta",
  "historia": "HU-001",
  "fecha": "2026-06-29",
  "version": "1.0",
  "objetivos": ["...", "..."],
  "alcance": { "incluye": ["..."], "excluye": ["..."] },
  "enfoque": "Texto del enfoque, o varias líneas.",
  "tipos_prueba": ["Funcional", "E2E", "API", "Regresión", "Exploratoria"],
  "riesgos": [ {"descripcion": "...", "nivel": "Alto", "mitigacion": "..."} ],
  "datos_entorno": ["...", "..."],
  "criterios_entrada": ["...", "..."],
  "criterios_salida": ["...", "..."],
  "supuestos": ["...", "..."],
  "preguntas_po": ["...", "..."]
}

Niveles de riesgo: Alto | Medio | Bajo
El HTML es autocontenido (CSS y SVG inline), no usa internet.
"""
import sys
import json

from _estilos_reporte import (e, page, meta, section, kpi_tiles, bar_chart,
                              doc_list, two_col, table, nivel_badge, NIVEL_COLOR)

NIVELES = ["Alto", "Medio", "Bajo"]


def _scope_card(titulo, tono, items):
    cuerpo = ("".join(f'<li>{e(it)}</li>' for it in items)
              if items else '<li class="muted">—</li>')
    return (f'<div class="card"><div class="cardbody">'
            f'<div class="subhead {tono}">{e(titulo)}</div>'
            f'<ul class="doclist">{cuerpo}</ul></div></div>')


def build_html(data):
    objetivos = data.get("objetivos", []) or []
    alcance = data.get("alcance", {}) or {}
    incluye = alcance.get("incluye", []) or []
    excluye = alcance.get("excluye", []) or []
    enfoque = data.get("enfoque", "") or ""
    tipos = data.get("tipos_prueba", []) or []
    riesgos = data.get("riesgos", []) or []
    datos = data.get("datos_entorno", []) or []
    c_entrada = data.get("criterios_entrada", []) or []
    c_salida = data.get("criterios_salida", []) or []
    supuestos = data.get("supuestos", []) or []
    preguntas = data.get("preguntas_po", []) or []

    abiertos = len(supuestos) + len(preguntas)
    kpis = kpi_tiles([
        ("Objetivos", len(objetivos), ""),
        ("Tipos de prueba", len(tipos), ""),
        ("Riesgos", len(riesgos), "warn" if riesgos else ""),
        ("Supuestos / preguntas", abiertos, "warn" if abiertos else ""),
    ])

    body = [kpis]

    # Objetivos
    body.append(section("Objetivos", doc_list(objetivos)))

    # Alcance (dos columnas)
    body.append('<div class="section"><div class="eyebrow section-title">Alcance</div>'
                + two_col(_scope_card("Incluye", "ok", incluye),
                          _scope_card("Fuera de alcance", "bad", excluye)) + '</div>')

    # Enfoque
    if enfoque:
        if isinstance(enfoque, list):
            body.append(section("Enfoque", doc_list(enfoque)))
        else:
            body.append(section("Enfoque", f'<div class="cardbody"><p>{e(enfoque)}</p></div>'))

    # Tipos de prueba (chips)
    if tipos:
        chips = "".join(f'<span class="chip">{e(t)}</span>' for t in tipos)
        body.append(section("Tipos de prueba",
                            f'<div class="cardbody"><div class="meta" style="margin-top:0">{chips}</div></div>'))

    # Riesgos: barras por nivel + tabla
    if riesgos:
        cnt = {n: sum(1 for r in riesgos if (r.get("nivel") or "").strip() == n) for n in NIVELES}
        bars = bar_chart([(n, cnt[n], NIVEL_COLOR[n]) for n in NIVELES])
        filas = [[nivel_badge(r.get("nivel")), e(r.get("descripcion")),
                  e(r.get("mitigacion") or "—")] for r in riesgos]
        tabla = table(["Nivel", "Riesgo", "Mitigación"], filas)
        body.append(section("Riesgos", bars + tabla))

    # Datos y entorno
    if datos:
        body.append(section("Datos y entorno", doc_list(datos)))

    # Criterios de entrada / salida (dos columnas)
    if c_entrada or c_salida:
        body.append('<div class="section"><div class="eyebrow section-title">Criterios</div>'
                    + two_col(_scope_card("De entrada", "ok", c_entrada),
                              _scope_card("De salida", "ok", c_salida)) + '</div>')

    # Supuestos y preguntas para el PO
    if supuestos or preguntas:
        partes = ""
        if supuestos:
            partes += ('<div class="cardbody"><div class="subhead">Supuestos</div>'
                       '<ul class="doclist">' + "".join(f'<li>{e(s)}</li>' for s in supuestos) + '</ul></div>')
        if preguntas:
            partes += ('<div class="cardbody"><div class="subhead warn">Preguntas para el PO</div>'
                       '<ul class="doclist">' + "".join(f'<li>{e(q)}</li>' for q in preguntas) + '</ul></div>')
        body.append(section("Supuestos y preguntas", partes))

    meta_html = meta([("Historia", data.get("historia")),
                      ("Fecha", data.get("fecha")),
                      ("Versión", data.get("version"))])
    titulo = data.get("titulo") or "Plan de pruebas"
    return page(titulo, "Plan de pruebas", meta_html, "".join(body))


def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/generar_plan.py <plan.json> <salida.html>")
        sys.exit(1)
    entrada, salida = sys.argv[1], sys.argv[2]
    if not salida.lower().endswith(".html"):
        print("La salida debe terminar en .html")
        sys.exit(1)
    with open(entrada, encoding="utf-8") as f:
        data = json.load(f)
    with open(salida, "w", encoding="utf-8") as f:
        f.write(build_html(data))
    print(f"OK: {salida}")


if __name__ == "__main__":
    main()

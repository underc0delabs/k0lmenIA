#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) de las novedades de k0lmenIA, a partir de novedades.json (scripts/novedades.py).

Uso (desde la raíz del repo):
    python scripts/generar_informe_novedades.py <novedades.json> <salida.html>

Qué muestra: cuántas novedades hay desde la última vez (o las pedidas), cuántos cambios suman, el período que cubren,
los cambios por entrada en un gráfico, la línea de tiempo y el detalle de cada entrada con sus puntos.
Esquema de novedades.json: {"alcance": "desde-la-ultima-vez|todas|ultimas-N", "marca_anterior": {...} | null,
"total_historial": 61, "entradas": [{"encabezado", "fecha", "numero", "titulo", "puntos": [...]}], "changelog_url": "..."}
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n import escribir_bilingue  # noqa: E402
from _estilos_reporte import page, meta, section, kpi_tiles, banner, table, column_chart, e, SERIES  # noqa: E402

ALCANCE = {"desde-la-ultima-vez": "Desde la última vez que las viste", "todas": "Todo el historial"}


def generar(datos_json, salida):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>, que abre el idioma elegido)."""
    datos = json.loads(Path(datos_json).read_text(encoding="utf-8"))
    escribir_bilingue(salida, lambda: _html(datos))
    return salida


def _inline(texto):
    """Lo mínimo del Markdown del CHANGELOG: **negrita** y `código`."""
    t = e(texto)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", t)


def _html(d):
    entradas = d.get("entradas") or []
    cambios = sum(len(x.get("puntos") or []) for x in entradas)
    fechas = sorted(x["fecha"] for x in entradas)
    alcance = d.get("alcance", "")
    alcance_txt = ALCANCE.get(alcance) or (f"Las {alcance.split('-')[1]} más recientes" if alcance.startswith("ultimas-") else alcance)

    if not entradas:
        veredicto, tono = "No hay novedades desde la última vez que las viste", "ok"
    else:
        veredicto, tono = f"{len(entradas)} novedad(es) con {cambios} cambio(s)", "ok"
    corta = lambda f: f"{f[8:10]}/{f[5:7]}" if f else "—"  # noqa: E731 (día/mes: la fecha completa no entra en el indicador)
    kpis = [("Novedades", len(entradas), "ok" if entradas else "", alcance_txt, "lista"),
            ("Cambios", cambios, "", "puntos del CHANGELOG", "carga"),
            ("Desde", corta(fechas[0] if fechas else ""), "", fechas[0] if fechas else "", "reloj"),
            ("Hasta", corta(fechas[-1] if fechas else ""), "", fechas[-1] if fechas else "", "reloj"),
            ("Historial", d.get("total_historial", 0), "", "entradas en total", "pagina")]
    cuerpo = banner(veredicto, tono) + section("Resumen", kpi_tiles(kpis))
    if entradas:
        filas = [(f"#{x['numero']}" if x.get("numero") else x["fecha"][5:], len(x.get("puntos") or []), SERIES[i % len(SERIES)])
                 for i, x in enumerate(reversed(entradas[:14]))]
        cuerpo += section("Cambios por entrada", column_chart(filas), "de la más vieja a la más nueva", ancho=8)
        cuerpo += section("Línea de tiempo", table(["Fecha", "Novedad", "Cambios"],
                          [[e(x["fecha"]), _inline(x.get("titulo") or x["encabezado"]), str(len(x.get("puntos") or []))] for x in entradas]), ancho=4)
        for x in entradas:
            puntos = "".join(f"<li>{_inline(p)}</li>" for p in x.get("puntos") or [])
            cuerpo += section(x.get("titulo") or x["encabezado"], f'<div class="cardbody"><ul class="doclist">{puntos}</ul></div>', x["fecha"])
    url = d.get("changelog_url")
    if url:
        cuerpo += section("Historial completo", f'<div class="cardbody"><p><a href="{e(url)}">CHANGELOG.md</a></p></div>')
    return page("Novedades de k0lmenIA", "Novedades · Actualizaciones", meta([("Alcance", alcance_txt), ("Entradas", len(entradas))]), cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de las novedades de k0lmenIA.")
    ap.add_argument("datos_json")
    ap.add_argument("salida")
    a = ap.parse_args()
    print(generar(a.datos_json, a.salida))


if __name__ == "__main__":
    main()

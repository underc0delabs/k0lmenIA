#!/usr/bin/env python3
"""
Genera el Informe de calidad de imagen en HTML (dashboard, modo oscuro) a partir de la evaluación
con OpenCV (calidad.json, de `npm run calidad-imagen`) y, opcionalmente, del análisis con visión del
agente calidad-imagen (lente sucia, cámara movida, contraluz, IR).

Uso:
    python scripts/generar_informe_calidad.py <calidad.json> <salida.html> [--analisis analisis.json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n import escribir_bilingue, localizar  # noqa: E402
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list,
                              nivel_badge, falta_informacion, e)

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
TONO = {"ok": "ok", "warn": "warn", "bad": "bad"}


def _tarjeta(reg):
    estado = reg.get("estado")
    tono = {"ok": "ok", "hallazgos": "warn", "fallo": "bad"}.get(estado, "warn")
    etiqueta = {"ok": "En orden", "hallazgos": "Con hallazgos", "fallo": "Con fallo"}.get(estado, estado)
    m = reg.get("metricas", {})
    cuerpo = banner(etiqueta, tono)
    if reg.get("captura"):
        cuerpo += (f'<div class="cardbody"><img src="{e(reg["captura"])}" alt="Captura" '
                   f'style="max-width:100%;border-radius:12px"></div>')
    if m:
        filas = [["Resolución", e(f'{m.get("ancho")}x{m.get("alto")}') if m.get("ancho") else "—"],
                 ["Brillo medio", e(m.get("brillo"))],
                 ["Nitidez (Laplaciano)", e(m.get("nitidez"))]]
        if m.get("dif_congelamiento") is not None:
            filas.append(["Diferencia (congelamiento)", e(m.get("dif_congelamiento"))])
        if m.get("dif_referencia") is not None:
            filas.append(["Diferencia vs. referencia", e(m.get("dif_referencia"))])
        cuerpo += table(["Métrica", "Valor"], filas)
    if reg.get("hallazgos"):
        hall = sorted(reg["hallazgos"], key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
        cuerpo += table(["Severidad", "Detalle"], [[nivel_badge(x.get("severidad", "Media")), e(x.get("texto", ""))] for x in hall])
    if reg.get("revisar_con_vision"):
        cuerpo += ('<div class="cardbody"><p class="muted"><span>Revisar con criterio (visión):</span> '
                   + e(", ".join(reg["revisar_con_vision"])) + "</p></div>")
    return section(reg.get("fuente", "Cámara"), cuerpo)


def generar(calidad_json, salida, analisis_json=None):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>, que abre el idioma elegido); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(calidad_json).read_text(encoding="utf-8"))
    analisis = json.loads(Path(analisis_json).read_text(encoding="utf-8")) if analisis_json and Path(analisis_json).exists() else {}
    escribir_bilingue(salida, lambda: _html(datos, localizar(analisis), salida, calidad_json))
    return salida


def _html(datos, analisis, salida, calidad_json):
    fuentes = datos.get("fuentes", [])
    r = datos.get("resumen", {})

    kpis = [("Cámaras", str(r.get("total", len(fuentes))), ""),
            ("En orden", str(r.get("ok", 0)), "ok" if r.get("ok") else ""),
            ("Con hallazgos", str(r.get("con_hallazgos", 0)), "warn" if r.get("con_hallazgos") else ""),
            ("Con fallo", str(r.get("fallo", 0)), "bad" if r.get("fallo") else "")]

    cuerpo = ""
    if analisis.get("veredicto"):
        cuerpo += banner(analisis["veredicto"], TONO.get(analisis.get("veredicto_tono"), "ok"))
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(analisis["resumen"])}</p></div>' if analisis.get("resumen") else ""))
    for f in fuentes:
        cuerpo += _tarjeta(f)
    if analisis.get("recomendaciones"):
        filas = [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))] for x in analisis["recomendaciones"]]
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"], filas))
    if analisis.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(analisis["proximos_pasos"]))
    cuerpo += falta_informacion(analisis.get("falta_informacion"))

    meta_html = meta([("Generado", datos.get("generado")), ("Historia", datos.get("historia"))])
    return page("Calidad de imagen", "Cámaras · visión + OpenCV", meta_html, cuerpo)


def main():
    ap = argparse.ArgumentParser(description="Informe HTML de calidad de imagen.")
    ap.add_argument("calidad_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis", default=None)
    args = ap.parse_args()
    print(generar(args.calidad_json, args.salida, args.analisis))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) del verificador de grabaciones por ONVIF (grabaciones.json, de
`npm run grabaciones`) y, opcionalmente, del análisis del agente verificador-grabaciones.

Uso:
    python scripts/generar_informe_grabaciones.py <grabaciones.json> <salida.html> [--analisis analisis.json]
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


def generar(grab_json, salida, analisis_json=None):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>, que abre el idioma elegido); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(grab_json).read_text(encoding="utf-8"))
    analisis = json.loads(Path(analisis_json).read_text(encoding="utf-8")) if analisis_json and Path(analisis_json).exists() else {}
    escribir_bilingue(salida, lambda: _html(datos, localizar(analisis), salida, grab_json))
    return salida


def _html(datos, analisis, salida, grab_json):
    res = datos.get("resultado", {})
    resumen = res.get("resumen", {})

    estado = res.get("estado", "—")
    tono = {"ok": "ok", "hallazgos": "warn", "fallo": "bad"}.get(estado, "warn")
    kpis = [("Estado", {"ok": "En orden", "hallazgos": "Con hallazgos", "fallo": "Con fallo"}.get(estado, estado), tono),
            ("Grabaciones", str(resumen.get("cantidad", "—")), ""),
            ("Días cubiertos", str(resumen.get("dias_cubiertos", "—")), ""),
            ("Retención esperada", f'{datos.get("retencion_esperada")} días' if datos.get("retencion_esperada") else "—", "")]

    cuerpo = ""
    if analisis.get("veredicto"):
        cuerpo += banner(analisis["veredicto"], TONO.get(analisis.get("veredicto_tono"), "ok"))
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(analisis["resumen"])}</p></div>' if analisis.get("resumen") else ""))

    if not res.get("soportado", True):
        cuerpo += section("Soporte ONVIF", banner("La cámara no respondió el servicio de grabaciones por ONVIF (Search). Puede no soportarlo; verificá por la API del NVR.", "warn"))

    if resumen:
        filas = [["Desde", e(resumen.get("desde") or "—")], ["Hasta", e(resumen.get("hasta") or "—")],
                 ["Cantidad", e(resumen.get("cantidad"))], ["Días cubiertos", e(resumen.get("dias_cubiertos"))]]
        cuerpo += section("Rango grabado", table(["Dato", "Valor"], filas))

    grabaciones = res.get("grabaciones", [])
    if grabaciones:
        filas = []
        for g in grabaciones:
            tracks = ", ".join(f'{t.get("tipo") or "?"} ({(t.get("desde") or "?")[:16]}→{(t.get("hasta") or "?")[:16]})' for t in g.get("tracks", []))
            filas.append([e(g.get("token") or "—"), e(tracks or "—")])
        cuerpo += section("Grabaciones", table(["Token", "Tracks (rango)"], filas))

    hall = sorted(res.get("hallazgos", []), key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
    if hall:
        cuerpo += section("Hallazgos", table(["Severidad", "Detalle"], [[nivel_badge(x.get("severidad", "Media")), e(x.get("texto", ""))] for x in hall]), sub=f"{len(hall)} en total")
    else:
        cuerpo += section("Hallazgos", banner("Sin hallazgos: grabación y retención en orden.", "ok"))

    if analisis.get("recomendaciones"):
        filas = [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))] for x in analisis["recomendaciones"]]
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"], filas))
    if analisis.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(analisis["proximos_pasos"]))
    cuerpo += falta_informacion(analisis.get("falta_informacion"))

    meta_html = meta([("Generado", datos.get("generado")), ("Historia", datos.get("historia")),
                      ("Host", f'{res.get("host")}:{res.get("puerto")}')])
    return page("Grabaciones", "NVR · ONVIF Recording", meta_html, cuerpo)


def main():
    ap = argparse.ArgumentParser(description="Informe HTML de grabaciones.")
    ap.add_argument("grab_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis", default=None)
    args = ap.parse_args()
    print(generar(args.grab_json, args.salida, args.analisis))


if __name__ == "__main__":
    main()

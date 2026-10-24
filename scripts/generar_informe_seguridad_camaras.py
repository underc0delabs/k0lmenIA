#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) del análisis de seguridad pasivo de cámaras (seguridad-camaras.json, de
`npm run seguridad-camaras`) y, opcionalmente, del análisis del agente analista-seguridad-camaras.

Uso:
    python scripts/generar_informe_seguridad_camaras.py <seguridad-camaras.json> <salida.html> [--analisis analisis.json]
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
    etiqueta = {"ok": "Sin hallazgos", "hallazgos": "Con hallazgos", "fallo": "Con fallo"}.get(estado, estado)
    cuerpo = banner(etiqueta, tono)
    ab = reg.get("puertos_abiertos", [])
    if ab:
        cuerpo += table(["Puerto", "Servicio"], [[e(p.get("puerto")), e(p.get("servicio"))] for p in ab])
    else:
        cuerpo += '<div class="cardbody"><p class="muted">No se detectaron puertos conocidos abiertos.</p></div>'
    if reg.get("dispositivo"):
        d = reg["dispositivo"]
        desc = f"{d.get('marca') or ''} {d.get('modelo') or ''} · firmware {d.get('firmware') or '?'}"
        cuerpo += f'<div class="cardbody"><p class="muted">{e(desc)}</p></div>'
    if reg.get("hallazgos"):
        hall = sorted(reg["hallazgos"], key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
        cuerpo += table(["Severidad", "Detalle"], [[nivel_badge(x.get("severidad", "Media")), e(x.get("texto", ""))] for x in hall])
    return section(reg.get("host", "Cámara"), cuerpo)


def generar(seg_json, salida, analisis_json=None):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>, que abre el idioma elegido); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(seg_json).read_text(encoding="utf-8"))
    analisis = json.loads(Path(analisis_json).read_text(encoding="utf-8")) if analisis_json and Path(analisis_json).exists() else {}
    escribir_bilingue(salida, lambda: _html(datos, localizar(analisis), salida, seg_json))
    return salida


def _html(datos, analisis, salida, seg_json):
    hosts = datos.get("hosts", [])
    r = datos.get("resumen", {})
    total_hall = sum(len(h.get("hallazgos", [])) for h in hosts)

    kpis = [("Cámaras", str(r.get("total", len(hosts))), ""),
            ("Sin hallazgos", str(r.get("ok", 0)), "ok" if r.get("ok") else ""),
            ("Con hallazgos", str(r.get("con_hallazgos", 0)), "warn" if r.get("con_hallazgos") else ""),
            ("Hallazgos totales", str(total_hall), "bad" if total_hall else "")]

    cuerpo = ""
    if analisis.get("veredicto"):
        cuerpo += banner(analisis["veredicto"], TONO.get(analisis.get("veredicto_tono"), "ok"))
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(analisis["resumen"])}</p></div>' if analisis.get("resumen") else ""))
    cuerpo += section("Alcance", banner("Análisis pasivo: puertos y servicios, sin ataques ni prueba de credenciales. Solo cámaras de CAMARAS_AUTORIZADAS.", "ok"))
    for hst in hosts:
        cuerpo += _tarjeta(hst)
    if analisis.get("recomendaciones"):
        filas = [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))] for x in analisis["recomendaciones"]]
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"], filas))
    if analisis.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(analisis["proximos_pasos"]))
    cuerpo += falta_informacion(analisis.get("falta_informacion"))

    meta_html = meta([("Generado", datos.get("generado")), ("Historia", datos.get("historia"))])
    return page("Seguridad de cámaras", "Cámaras IP · escaneo pasivo", meta_html, cuerpo)


def main():
    ap = argparse.ArgumentParser(description="Informe HTML de seguridad de cámaras.")
    ap.add_argument("seg_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis", default=None)
    args = ap.parse_args()
    print(generar(args.seg_json, args.salida, args.analisis))


if __name__ == "__main__":
    main()

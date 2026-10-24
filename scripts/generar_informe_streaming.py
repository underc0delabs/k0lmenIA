#!/usr/bin/env python3
"""
Genera el Informe de streaming y playback en HTML (dashboard, modo oscuro) a partir de la
verificación con ffprobe/ffmpeg (streaming.json, de `npm run streaming`) y, opcionalmente, del
análisis del agente probador-streaming. `npm run streaming` ya lo genera solo al terminar; el
agente lo vuelve a generar con su análisis.

Uso:
    python scripts/generar_informe_streaming.py <streaming.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (fuentes probadas, en orden, con hallazgos, con fallo y
latencia promedio), una tarjeta por fuente con sus propiedades (contenedor, tipo, video, audio y
continuidad) y los hallazgos de todas las fuentes con su severidad.

El análisis (opcional) aporta:
{
  "veredicto": "...", "veredicto_tono": "ok" | "warn" | "bad",
  "resumen": "Resumen para alguien no técnico...",
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n import escribir_bilingue, localizar  # noqa: E402
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, two_col, doc_list,
                              nivel_badge, falta_informacion, e, OK, AVISO, CRITICO)

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
TONO = {"ok": "ok", "warn": "warn", "bad": "bad"}


def _prop_table(reg):
    v = reg.get("video") or {}
    a = reg.get("audio") or {}
    c = reg.get("continuidad") or {}
    est = reg.get("estabilidad") or {}
    carga = reg.get("carga") or {}
    kf = v.get("keyframe_intervalo_s")
    filas = [
        ["Contenedor", e(reg.get("contenedor") or "—")],
        ["Tipo", e(reg.get("tipo") or "—")],
        ["Latencia de conexión", f'{reg.get("latencia_conexion_s")} s' if reg.get("latencia_conexion_s") is not None else "—"],
        ["Latencia de arranque (TTFF)", f'{reg.get("ttff_s")} s' if reg.get("ttff_s") is not None else "—"],
        ["Video", e(f'{v.get("codec") or "?"} · {v.get("resolucion") or "?"} · {v.get("fps") or "?"} fps · {v.get("bitrate_kbps") or "?"} kbps') if reg.get("video") else "Sin video"],
        ["Keyframes (GOP)", f'cada {kf} s' if kf is not None else "—"],
        ["Audio", e(f'{a.get("codec") or "?"} · {a.get("sample_rate") or "?"} Hz · {a.get("canales") or "?"} canal(es)') if reg.get("audio") else "Sin audio"],
    ]
    if isinstance(c, dict) and "error" not in c:
        filas.append(["Continuidad", e(f'{c.get("frames", 0)} frames leídos · {c.get("caidos", 0)} caídos · '
                                       f'{c.get("duplicados", 0)} duplicados · {c.get("errores_decodificacion", 0)} errores')])
    if isinstance(est, dict) and "error" not in est and est:
        filas.append(["Estabilidad", e(f'{est.get("duracion_leida_s", "?")} s leídos · {est.get("interrupciones", 0)} interrupciones · '
                                       f'{est.get("reconexiones", 0)} reconexiones')])
    if isinstance(carga, dict) and carga:
        filas.append(["Carga", e(f'{carga.get("exitosas", 0)}/{carga.get("conexiones", 0)} conexiones ok · '
                                 f'{carga.get("fps_promedio", "?")} fps prom. · {carga.get("errores_total", 0)} errores')])
    return table(["Propiedad", "Valor"], filas)


def _tarjeta_fuente(reg):
    estado = reg.get("estado")
    tono = {"ok": "ok", "hallazgos": "warn", "fallo": "bad"}.get(estado, "warn")
    etiqueta = {"ok": "En orden", "hallazgos": "Con hallazgos", "fallo": "Con fallo"}.get(estado, estado)
    cuerpo = banner(etiqueta, tono) + _prop_table(reg)
    return section(reg.get("fuente", "Fuente"), cuerpo, sub=reg.get("tipo", ""))


def generar(streaming_json, salida, analisis_json=None):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>, que abre el idioma elegido); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(streaming_json).read_text(encoding="utf-8"))
    analisis = json.loads(Path(analisis_json).read_text(encoding="utf-8")) if analisis_json and Path(analisis_json).exists() else {}
    escribir_bilingue(salida, lambda: _html(datos, localizar(analisis), salida, streaming_json))
    return salida


def _html(datos, analisis, salida, streaming_json):
    fuentes = datos.get("fuentes", [])
    r = datos.get("resumen", {})

    lats = [f["latencia_conexion_s"] for f in fuentes if f.get("latencia_conexion_s") is not None]
    lat_prom = round(sum(lats) / len(lats), 2) if lats else None

    kpis = [
        ("Fuentes probadas", str(r.get("total", len(fuentes))), ""),
        ("En orden", str(r.get("ok", 0)), "ok" if r.get("ok") else ""),
        ("Con hallazgos", str(r.get("con_hallazgos", 0)), "warn" if r.get("con_hallazgos") else ""),
        ("Con fallo", str(r.get("fallo", 0)), "bad" if r.get("fallo") else ""),
        ("Latencia promedio", f"{lat_prom} s" if lat_prom is not None else "—", ""),
    ]

    cuerpo = ""
    if analisis.get("veredicto"):
        cuerpo += banner(analisis["veredicto"], TONO.get(analisis.get("veredicto_tono"), "ok"))
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(analisis["resumen"])}</p></div>' if analisis.get("resumen") else ""))

    # Hallazgos de todas las fuentes, ordenados por severidad.
    hall = []
    for f in fuentes:
        for h in f.get("hallazgos", []):
            hall.append((f["fuente"], h.get("severidad", "Media"), h.get("texto", "")))
    hall.sort(key=lambda x: ORDEN_SEV.get(x[1], 9))
    if hall:
        filas = [[nivel_badge(sev), e(fte), e(txt)] for fte, sev, txt in hall]
        cuerpo += section("Hallazgos", table(["Severidad", "Fuente", "Detalle"], filas),
                          sub=f"{len(hall)} en total")
    else:
        cuerpo += section("Hallazgos", banner("Sin hallazgos: todas las fuentes respondieron dentro de los umbrales.", "ok"))

    for f in fuentes:
        cuerpo += _tarjeta_fuente(f)

    if analisis.get("recomendaciones"):
        filas = [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))]
                 for x in analisis["recomendaciones"]]
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"], filas))
    if analisis.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(analisis["proximos_pasos"]))
    cuerpo += falta_informacion(analisis.get("falta_informacion"))

    meta_html = meta([("Generado", datos.get("generado")), ("Historia", datos.get("historia")),
                      ("Captura", f'{datos.get("segundos_captura")} s'), ("Transporte", datos.get("transporte"))])
    return page("Streaming y playback", "Verificación de streaming", meta_html, cuerpo)


def main():
    ap = argparse.ArgumentParser(description="Informe HTML de streaming y playback.")
    ap.add_argument("streaming_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis", default=None)
    args = ap.parse_args()
    out = generar(args.streaming_json, args.salida, args.analisis)
    print(out)


if __name__ == "__main__":
    main()

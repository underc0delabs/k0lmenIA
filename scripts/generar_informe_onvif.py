#!/usr/bin/env python3
"""
Genera el Informe de control ONVIF en HTML (dashboard, modo oscuro) a partir de la prueba con
onvif-zeep (onvif.json, de `npm run onvif`) y, opcionalmente, del análisis del agente probador-onvif.

Uso:
    python scripts/generar_informe_onvif.py <onvif.json> <salida.html> [--analisis analisis.json]

Qué muestra: estado general, información del dispositivo (marca, modelo, firmware), las pruebas
ONVIF corridas (device info, perfiles, snapshot, eventos, PTZ) con su resultado, los perfiles y sus
URIs RTSP, el snapshot descargado y los hallazgos por severidad.

El análisis (opcional) aporta: veredicto, veredicto_tono, resumen, falta_informacion,
recomendaciones, proximos_pasos (mismo formato que el informe de streaming).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n import escribir_bilingue, localizar, t  # noqa: E402
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list,
                              nivel_badge, estado_pill, falta_informacion, e)

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
TONO = {"ok": "ok", "warn": "warn", "bad": "bad"}
PRUEBA_NOMBRE = {
    "device_information": "Información del dispositivo", "capabilities": "Capacidades",
    "system_date_time": "Reloj / zona horaria", "ntp": "NTP",
    "profiles": "Perfiles y stream URI", "snapshot": "Snapshot", "events": "Eventos / movimiento",
    "events_live": "Eventos en vivo (pull-point)", "ptz_presets": "PTZ · presets", "ptz_move": "PTZ · movimiento",
}
PRUEBA_TONO = {"ok": "ok", "fallo": "bad", "n/a": "blk"}


def generar(onvif_json, salida, analisis_json=None):
    """Escribe salida (ES) y su .en.html (EN); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(onvif_json).read_text(encoding="utf-8"))
    analisis = json.loads(Path(analisis_json).read_text(encoding="utf-8")) if analisis_json and Path(analisis_json).exists() else {}
    escribir_bilingue(salida, lambda: _html(datos, localizar(analisis), salida, onvif_json))
    return salida


def _html(datos, analisis, salida, onvif_json):
    res = datos.get("resultado", {})
    dev = res.get("dispositivo", {})
    pruebas = res.get("pruebas", {})

    estado = res.get("estado", "—")
    tono = {"ok": "ok", "hallazgos": "warn", "fallo": "bad"}.get(estado, "warn")

    kpis = [
        ("Estado", {"ok": "En orden", "hallazgos": "Con hallazgos", "fallo": "Con fallo"}.get(estado, estado), tono),
        ("Pruebas ok", str(sum(1 for v in pruebas.values() if v == "ok")), "ok"),
        ("Pruebas con fallo", str(sum(1 for v in pruebas.values() if v == "fallo")), "bad" if any(v == "fallo" for v in pruebas.values()) else ""),
        ("Perfiles", str(len(res.get("perfiles", []))), ""),
        ("PTZ", "Sí" if res.get("capacidades", {}).get("ptz") else "No", ""),
    ]

    cuerpo = ""
    if analisis.get("veredicto"):
        cuerpo += banner(analisis["veredicto"], TONO.get(analisis.get("veredicto_tono"), "ok"))
    resumen_extra = f'<div class="cardbody"><p>{e(analisis["resumen"])}</p></div>' if analisis.get("resumen") else ""
    cuerpo += section("Resumen", kpi_tiles(kpis) + resumen_extra)

    # Dispositivo
    if dev:
        filas = [["Marca", e(dev.get("marca") or "—")], ["Modelo", e(dev.get("modelo") or "—")],
                 ["Firmware", e(dev.get("firmware") or "—")], ["Serie", e(dev.get("serie") or "—")]]
        cuerpo += section("Dispositivo", table(["Dato", "Valor"], filas))

    # Reloj y NTP
    reloj = res.get("reloj") or {}
    ntp = res.get("ntp") or {}
    if reloj or ntp:
        filas = []
        if reloj:
            d = reloj.get("deriva_reloj_s")
            filas += [["Deriva de reloj", f'{d} s' if d is not None else "—"],
                      ["Zona horaria", e(reloj.get("timezone") or "—")],
                      ["Horario de verano", "Sí" if reloj.get("dst") else "No"]]
        if ntp:
            filas += [["NTP desde DHCP", "Sí" if ntp.get("desde_dhcp") else "No"],
                      ["Servidores NTP", e(", ".join(ntp.get("servidores") or []) or "—")]]
        cuerpo += section("Reloj y NTP", table(["Dato", "Valor"], filas),
                          sub="La deriva de reloj afecta la hora de grabaciones y eventos")

    # Pruebas ONVIF
    if pruebas:
        filas = [[e(PRUEBA_NOMBRE.get(k, k)), estado_pill({"ok": "Aprobado", "fallo": "Fallido", "n/a": "N/A"}.get(v, v))]
                 for k, v in pruebas.items()]
        cuerpo += section("Pruebas ONVIF", table(["Prueba", "Resultado"], filas))

    # Perfiles
    perfiles = res.get("perfiles", [])
    if perfiles:
        filas = [[e(p.get("nombre") or "—"), e(p.get("token") or "—"), e(p.get("rtsp") or p.get("rtsp_error") or "—")]
                 for p in perfiles]
        cuerpo += section("Perfiles y stream", table(["Perfil", "Token", "URI RTSP"], filas),
                          sub="Pasá la URI RTSP al probador-streaming para verificar el video")

    # Eventos en vivo (pull-point)
    ev = (res.get("eventos") or {}).get("en_vivo")
    if ev:
        if ev.get("suscripcion") != "ok":
            cuerpo += section("Eventos en vivo", banner(f"{t('No se pudo suscribir al pull-point:')} {ev.get('error') or t('sin detalle')}", "bad"))
        else:
            tono = "ok" if ev.get("movimiento") else "warn"
            txt = ("Se detectó movimiento en vivo." if ev.get("movimiento")
                   else f"No llegó ningún evento de movimiento en {ev.get('pedido_s')} s.")
            filas = [["Suscripción", "OK (pull-point)"],
                     ["Espera", f"{ev.get('pedido_s')} s"],
                     ["Mensajes recibidos", e(ev.get("mensajes", 0))],
                     ["Movimiento detectado", "Sí" if ev.get("movimiento") else "No"],
                     ["Topics vistos", e(", ".join(ev.get("topics") or []) or "—")]]
            cuerpo += section("Eventos en vivo", banner(txt, tono) + table(["Dato", "Valor"], filas),
                              sub="Suscripción pull-point ONVIF para ver la detección de movimiento")

    # Snapshot
    snap = res.get("snapshot", {})
    if snap.get("ok"):
        cuerpo += section("Snapshot", f'<div class="cardbody"><img src="snapshot.jpg" alt="Snapshot de la cámara" '
                          f'style="max-width:100%;border-radius:12px"><p class="muted">{e(snap.get("bytes", 0))} bytes</p></div>')

    # Hallazgos
    hall = sorted(res.get("hallazgos", []), key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
    if hall:
        filas = [[nivel_badge(x.get("severidad", "Media")), e(x.get("texto", ""))] for x in hall]
        cuerpo += section("Hallazgos", table(["Severidad", "Detalle"], filas), sub=f"{len(hall)} en total")
    else:
        cuerpo += section("Hallazgos", banner("Sin hallazgos: todas las pruebas ONVIF respondieron bien.", "ok"))

    if analisis.get("recomendaciones"):
        filas = [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))]
                 for x in analisis["recomendaciones"]]
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"], filas))
    if analisis.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(analisis["proximos_pasos"]))
    cuerpo += falta_informacion(analisis.get("falta_informacion"))

    meta_html = meta([("Generado", datos.get("generado")), ("Historia", datos.get("historia")),
                      ("Host", f'{res.get("host")}:{res.get("puerto")}'),
                      ("PTZ ejecutado", "Sí" if datos.get("ptz_ejecutado") else "No")])
    return page("Control ONVIF", "Cámara IP · ONVIF", meta_html, cuerpo)


def main():
    ap = argparse.ArgumentParser(description="Informe HTML de control ONVIF.")
    ap.add_argument("onvif_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis", default=None)
    args = ap.parse_args()
    print(generar(args.onvif_json, args.salida, args.analisis))


if __name__ == "__main__":
    main()

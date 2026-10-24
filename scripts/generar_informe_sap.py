#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) del probador de SAP (agente probador-sap): SAP GUI (transacciones) y Fiori/UI5.

Uso (desde la raíz del repo):
    python scripts/generar_informe_sap.py <analisis.json> <salida.html>

A diferencia de los informes de herramientas, acá no hay un binario que genere datos: el agente arma las
pruebas (SAP GUI Scripting, Playwright para Fiori, OData con ejecutor-api) y escribe todo en analisis.json.

Esquema del analisis.json (todo opcional salvo "titulo"):
{
  "titulo": "SAP — HU-010 (Order to Cash)", "historia": "HU-010", "ambiente": "QA (no productivo)",
  "generado": "2026-10-19T12:00:00",
  "sistema": {"sid": "DQ1", "mandante": "100", "tipo": "S/4HANA", "version": "2023", "gui_scripting": true, "fiori": true},
  "veredicto": "El flujo O2C cierra; 1 hallazgo alto en una autorización", "veredicto_tono": "warn",
  "resumen": "...",
  "pruebas": [{"id": "CP-001", "area": "SAP GUI", "transaccion": "VA01", "caso": "Crear pedido de ventas",
               "resultado": "Aprobado|Fallido|Bloqueado|Pendiente|N/A", "esperado": "...", "obtenido": "...",
               "evidencia": "capturas/cp-001.png"}],
  "autorizaciones": [{"rol": "Z_VENTAS", "usuario": "QA_TEST", "objeto": "V_VBAK_VKO", "actividad": "01 Crear",
                      "resultado": "Aprobado|Fallido", "detalle": "SU53 sin fallos"}],
  "procesos": [{"proceso": "Order to Cash", "paso": "VA01 → VL01N → VF01", "estado": "Aprobado", "detalle": "..."}],
  "hallazgos": [{"id": "H-01", "severidad": "Alta", "area": "Autorizaciones", "texto": "...",
                 "impacto": "...", "como_reproducir": "...", "recomendacion": "..."}],
  "recomendaciones": [{"prioridad": "Alta", "accion": "...", "motivo": "..."}],
  "proximos_pasos": ["..."],
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}]
}
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n import escribir_bilingue, localizar  # noqa: E402
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list, bar_chart,  # noqa: E402
                              nivel_badge, estado_pill, falta_informacion, miniatura, resolver_evidencia, e, SERIES)

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
ORDEN_RES = {"Fallido": 0, "Bloqueado": 1, "Pendiente": 2, "Aprobado": 3, "N/A": 4}
TONO = {"ok": "ok", "warn": "warn", "bad": "bad"}


def generar(analisis_json, salida):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>, que abre el idioma elegido); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(analisis_json).read_text(encoding="utf-8"))
    escribir_bilingue(salida, lambda: _html(localizar(datos), salida))
    return salida


def _html(d, salida):
    base = Path(salida).resolve().parent
    sis = d.get("sistema") or {}

    hall = sorted(d.get("hallazgos") or [], key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
    criticos = sum(1 for h in hall if h.get("severidad") in ("Crítica", "Alta"))
    pruebas = d.get("pruebas") or []
    fallidas = sum(1 for p in pruebas if p.get("resultado") == "Fallido")
    aprobadas = sum(1 for p in pruebas if p.get("resultado") == "Aprobado")
    auth = d.get("autorizaciones") or []
    auth_mal = sum(1 for a in auth if a.get("resultado") == "Fallido")
    procesos = d.get("procesos") or []

    kpis = [("Pruebas", len(pruebas), "bad" if fallidas else ("ok" if pruebas else ""),
             f"{aprobadas} aprobada(s), {fallidas} fallida(s)", "lista"),
            ("Hallazgos", len(hall), "bad" if criticos else ("warn" if hall else "ok"), f"{criticos} crítico(s) o alto(s)", "bicho")]
    if auth:
        kpis.append(("Autorizaciones", "Con fallos" if auth_mal else "OK", "bad" if auth_mal else "ok", f"{len(auth)} revisada(s)", "escudo"))
    if procesos:
        ok_proc = sum(1 for p in procesos if p.get("estado") == "Aprobado")
        kpis.append(("Procesos de negocio", f"{ok_proc}/{len(procesos)}", "bad" if ok_proc < len(procesos) else "ok", "pasos completos", "flujo"))

    cuerpo = ""
    if d.get("veredicto"):
        cuerpo += banner(d["veredicto"], TONO.get(d.get("veredicto_tono"), "ok"))
    if (d.get("ambiente") or "").lower().startswith(("qa", "sandbox", "prueba", "dev", "no prod", "stag")):
        cuerpo += banner("Sistema no productivo: pruebas sobre un mandante de QA, sin datos reales de producción.", "ok")
    if sis.get("gui_scripting") is False:
        cuerpo += banner("SAP GUI Scripting está deshabilitado: la automatización del GUI no es posible hasta habilitarlo (RZ11 sapgui/user_scripting).", "warn")
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(d["resumen"])}</p></div>' if d.get("resumen") else ""))

    if hall:
        por_area = {}
        for h in hall:
            por_area[h.get("area", "Otro")] = por_area.get(h.get("area", "Otro"), 0) + 1
        filas = [[f'<span class="id">{e(h.get("id", ""))}</span>', nivel_badge(h.get("severidad")), e(h.get("area", "")),
                  e(h.get("texto", "")), e(h.get("impacto", "")), e(h.get("recomendacion", ""))] for h in hall]
        cuerpo += section("Hallazgos", table(["ID", "Severidad", "Área", "Qué pasa", "Impacto", "Recomendación"], filas), f"{len(hall)} en total", ancho=8)
        cuerpo += section("Hallazgos por área", bar_chart([(a, n, SERIES[i % len(SERIES)]) for i, (a, n) in enumerate(sorted(por_area.items(), key=lambda x: -x[1]))]), ancho=4)
        detalladas = [h for h in hall if h.get("como_reproducir")]
        if detalladas:
            cuerpo += section("Cómo reproducir", table(["ID", "Hallazgo", "Pasos"],
                              [[f'<span class="id">{e(h.get("id"))}</span>', e(h.get("texto", "")), e(h.get("como_reproducir"))] for h in detalladas]))
    else:
        cuerpo += section("Hallazgos", banner("Sin hallazgos.", "ok"))

    if auth:
        filas = [[e(a.get("rol") or a.get("usuario", "")), e(a.get("objeto", "")), e(a.get("actividad", "")),
                  estado_pill(a.get("resultado")), e(a.get("detalle", ""))] for a in auth]
        cuerpo += section("Autorizaciones y roles", table(["Rol / usuario", "Objeto de autorización", "Actividad", "Resultado", "Detalle"], filas),
                          "PFCG / SU01 / SU53")

    if procesos:
        filas = [[e(p.get("proceso", "")), e(p.get("paso", "")), estado_pill(p.get("estado")), e(p.get("detalle", ""))] for p in procesos]
        cuerpo += section("Procesos de negocio", table(["Proceso", "Paso", "Estado", "Detalle"], filas))

    if pruebas:
        filas = []
        for p in sorted(pruebas, key=lambda p: ORDEN_RES.get(p.get("resultado"), 5)):
            ev = ""
            if p.get("evidencia"):
                ruta, existe = resolver_evidencia(p["evidencia"], base)
                ev = miniatura(ruta, p.get("caso", ""), existe=existe)
            filas.append([f'<span class="id">{e(p.get("id", ""))}</span>', e(p.get("area", "")), e(p.get("transaccion", "")), e(p.get("caso", "")),
                          estado_pill(p.get("resultado")), e(p.get("esperado", "")), e(p.get("obtenido", "")), ev])
        cuerpo += section("Pruebas ejecutadas", table(["ID", "Área", "Transacción / App", "Caso", "Resultado", "Esperado", "Obtenido", "Evidencia"], filas))

    if d.get("recomendaciones"):
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"],
                          [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))] for x in d["recomendaciones"]]))
    if d.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(d["proximos_pasos"]))
    cuerpo += falta_informacion(d.get("falta_informacion"))

    return page(d.get("titulo") or "SAP", "SAP GUI · Fiori / UI5",
                meta([("Generado", d.get("generado")), ("Historia", d.get("historia")), ("Ambiente", d.get("ambiente")),
                      ("Sistema", f'{sis.get("sid", "—")} / mandante {sis.get("mandante", "—")}' if sis else None),
                      ("Tipo", f'{sis.get("tipo", "")} {sis.get("version", "")}'.strip() or None),
                      ("GUI Scripting", {True: "habilitado", False: "deshabilitado"}.get(sis.get("gui_scripting")))]), cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML del probador de SAP (GUI y Fiori).")
    ap.add_argument("analisis_json")
    ap.add_argument("salida")
    args = ap.parse_args()
    print(generar(args.analisis_json, args.salida))


if __name__ == "__main__":
    main()

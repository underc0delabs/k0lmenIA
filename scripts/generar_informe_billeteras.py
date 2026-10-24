#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) del probador de billeteras virtuales y pagos (agente probador-billeteras).

Uso (desde la raíz del repo):
    python scripts/generar_informe_billeteras.py <analisis.json> <salida.html>

A diferencia de los informes de herramientas, acá no hay un binario que genere datos: el agente arma
las pruebas (con ejecutor-api/Newman, Playwright, verificador-datos) y escribe todo en analisis.json.

Esquema del analisis.json (todo opcional salvo "titulo"):
{
  "titulo": "Billetera — HU-010 (transferencias P2P)", "historia": "HU-010", "ambiente": "sandbox",
  "generado": "2026-10-19T12:00:00", "proveedor_pagos": "Mercado Pago (sandbox)",
  "veredicto": "La billetera conserva los saldos y es idempotente; 1 hallazgo alto en concurrencia",
  "veredicto_tono": "warn",  // ok | warn | bad
  "resumen": "...",
  "pruebas": [{"id": "CP-API-003", "categoria": "Idempotencia", "caso": "Reintento con la misma Idempotency-Key",
               "resultado": "Aprobado|Fallido|Bloqueado|Pendiente|N/A", "esperado": "un solo movimiento",
               "obtenido": "un solo movimiento", "evidencia": "capturas/cp-003.png"}],
  "conservacion": [{"escenario": "P2P A→B de 500", "antes": 10000, "despues": 10000, "cuadra": true, "detalle": "total del sistema"}],
  "hallazgos": [{"id": "H-01", "severidad": "Alta", "categoria": "Concurrencia",
                 "texto": "Dos retiros en paralelo con saldo para uno dejan el saldo negativo (doble gasto).",
                 "impacto": "...", "como_reproducir": "...", "recomendacion": "..."}],
  "conciliacion": {"movimientos_billetera": 42, "movimientos_proveedor": 42, "diferencias": 0,
                   "detalle": [{"concepto": "Comisiones", "billetera": 120.5, "proveedor": 120.5, "diferencia": 0}]},
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
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list, two_col, bar_chart,
                              nivel_badge, estado_pill, falta_informacion, miniatura, resolver_evidencia, e,
                              CRITICO, SERIO, AVISO, NEUTRO, OK, SERIES, _num)

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
ORDEN_RES = {"Fallido": 0, "Bloqueado": 1, "Pendiente": 2, "Aprobado": 3, "N/A": 4}
TONO = {"ok": "ok", "warn": "warn", "bad": "bad"}


def _moneda(v):
    return _num(v) if isinstance(v, (int, float)) else (e(v) if v is not None else "—")


def generar(analisis_json, salida):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>, que abre el idioma elegido); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(analisis_json).read_text(encoding="utf-8"))
    escribir_bilingue(salida, lambda: _html(localizar(datos), salida))
    return salida


def _html(d, salida):
    base = Path(salida).resolve().parent

    hall = sorted(d.get("hallazgos") or [], key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
    criticos = sum(1 for h in hall if h.get("severidad") in ("Crítica", "Alta"))
    pruebas = d.get("pruebas") or []
    fallidas = sum(1 for p in pruebas if p.get("resultado") == "Fallido")
    aprobadas = sum(1 for p in pruebas if p.get("resultado") == "Aprobado")
    conserv = d.get("conservacion") or []
    no_cuadra = sum(1 for c in conserv if c.get("cuadra") is False)
    conc = d.get("conciliacion") or {}
    difs = conc.get("diferencias")

    kpis = [("Pruebas", len(pruebas), "bad" if fallidas else ("ok" if pruebas else ""),
             f"{aprobadas} aprobada(s), {fallidas} fallida(s)", "lista"),
            ("Hallazgos", len(hall), "bad" if criticos else ("warn" if hall else "ok"), f"{criticos} crítico(s) o alto(s)", "bicho"),
            ("Conservación del saldo", "No cuadra" if no_cuadra else ("Cuadra" if conserv else "—"),
             "bad" if no_cuadra else ("ok" if conserv else ""), f"{len(conserv)} escenario(s)", "escudo")]
    if conc:
        kpis.append(("Conciliación", "Con diferencias" if difs else "Sin diferencias",
                     "bad" if difs else "ok", f"{conc.get('movimientos_billetera', '—')} vs. {conc.get('movimientos_proveedor', '—')} movimientos", "carga"))

    cuerpo = ""
    if d.get("veredicto"):
        cuerpo += banner(d["veredicto"], TONO.get(d.get("veredicto_tono"), "ok"))
    cuerpo += banner("Ambiente de prueba: dinero y tarjetas de prueba, sin movimientos ni datos reales.", "ok") if (d.get("ambiente") or "").lower().startswith(("sandbox", "prueba", "qa", "stag")) else ""
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(d["resumen"])}</p></div>' if d.get("resumen") else ""))

    if hall:
        por_cat = {}
        for h in hall:
            por_cat[h.get("categoria", "Otro")] = por_cat.get(h.get("categoria", "Otro"), 0) + 1
        filas = [[f'<span class="id">{e(h.get("id", ""))}</span>', nivel_badge(h.get("severidad")), e(h.get("categoria", "")),
                  e(h.get("texto", "")), e(h.get("impacto", "")), e(h.get("recomendacion", ""))] for h in hall]
        tabla = section("Hallazgos", table(["ID", "Severidad", "Categoría", "Qué pasa", "Impacto", "Recomendación"], filas),
                        f"{len(hall)} en total", ancho=8)
        panel = section("Hallazgos por categoría", bar_chart([(c, n, SERIES[i % len(SERIES)]) for i, (c, n) in enumerate(sorted(por_cat.items(), key=lambda x: -x[1]))]), ancho=4)
        cuerpo += tabla + panel
        detalladas = [h for h in hall if h.get("como_reproducir")]
        if detalladas:
            filas = [[f'<span class="id">{e(h.get("id"))}</span>', e(h.get("texto", "")), e(h.get("como_reproducir"))] for h in detalladas]
            cuerpo += section("Cómo reproducir", table(["ID", "Hallazgo", "Pasos"], filas))
    else:
        cuerpo += section("Hallazgos", banner("Sin hallazgos.", "ok"))

    if conserv:
        filas = []
        for c in conserv:
            ok = c.get("cuadra")
            filas.append([e(c.get("escenario")), _moneda(c.get("antes")), _moneda(c.get("despues")),
                          estado_pill("Aprobado" if ok else "Fallido") if ok is not None else "—", e(c.get("detalle", ""))])
        cuerpo += section("Conservación del saldo (la plata no se crea ni se destruye)",
                          table(["Escenario", "Total antes", "Total después", "¿Cuadra?", "Detalle"], filas))

    if pruebas:
        filas = []
        for p in sorted(pruebas, key=lambda p: ORDEN_RES.get(p.get("resultado"), 5)):
            ev = ""
            if p.get("evidencia"):
                ruta, existe = resolver_evidencia(p["evidencia"], base)
                ev = miniatura(ruta, p.get("caso", ""), existe=existe)
            filas.append([f'<span class="id">{e(p.get("id", ""))}</span>', e(p.get("categoria", "")), e(p.get("caso", "")),
                          estado_pill(p.get("resultado")), e(p.get("esperado", "")), e(p.get("obtenido", "")), ev])
        cuerpo += section("Pruebas ejecutadas", table(["ID", "Categoría", "Caso", "Resultado", "Esperado", "Obtenido", "Evidencia"], filas))

    if conc:
        kp = kpi_tiles([("Movimientos en la billetera", _num(conc.get("movimientos_billetera")) if conc.get("movimientos_billetera") is not None else "—", ""),
                        ("Movimientos en el proveedor", _num(conc.get("movimientos_proveedor")) if conc.get("movimientos_proveedor") is not None else "—", ""),
                        ("Diferencias", _num(difs) if difs is not None else "—", "bad" if difs else "ok")])
        filas = [[e(x.get("concepto")), _moneda(x.get("billetera")), _moneda(x.get("proveedor")),
                  (estado_pill("Fallido") if x.get("diferencia") else estado_pill("Aprobado"))] for x in conc.get("detalle") or []]
        cuerpo += section("Conciliación con el proveedor de pagos",
                          kp + (table(["Concepto", "Billetera", "Proveedor", "¿Cuadra?"], filas) if filas else "")
                          + (f'<div class="cardbody"><p>{e(conc["detalle_texto"])}</p></div>' if conc.get("detalle_texto") else ""))

    if d.get("recomendaciones"):
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"],
                                                   [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))]
                                                    for x in d["recomendaciones"]]))
    if d.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(d["proximos_pasos"]))
    cuerpo += falta_informacion(d.get("falta_informacion"))

    return page(d.get("titulo") or "Billetera y pagos", "Billeteras virtuales · pagos",
                meta([("Generado", d.get("generado")), ("Historia", d.get("historia")), ("Ambiente", d.get("ambiente")),
                      ("Proveedor", d.get("proveedor_pagos"))]), cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML del probador de billeteras y pagos.")
    ap.add_argument("analisis_json")
    ap.add_argument("salida")
    args = ap.parse_args()
    print(generar(args.analisis_json, args.salida))


if __name__ == "__main__":
    main()

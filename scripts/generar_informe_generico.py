#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) genérico para los probadores que no tienen un informe propio: el agente escribe un
analisis.json con una estructura común y este script lo renderiza con el estilo de la casa. Lo usan, entre
otros, probador-contratos, analista-seo, probador-datos, probador-dynamics, probador-blockchain, probador-ivr,
probador-juegos y probador-pos.

Uso (desde la raíz del repo):
    python scripts/generar_informe_generico.py <analisis.json> <salida.html>

Esquema del analisis.json (todo opcional salvo "titulo"):
{
  "titulo": "Contratos — HU-010", "eyebrow": "Contract testing (Pact)", "historia": "HU-010",
  "ambiente": "QA", "generado": "2026-10-19T12:00:00",
  "meta": [["Proveedor", "pagos-api"], ["Consumidor", "web"]],   // filas extra del encabezado
  "veredicto": "...", "veredicto_tono": "ok|warn|bad", "resumen": "...",
  "metricas": [{"metrica": "Cobertura de contrato", "valor": "80%", "objetivo": "100%", "estado": "Fallido"}],
  "pruebas": [{"id": "CP-001", "categoria": "...", "caso": "...", "resultado": "Aprobado|Fallido|Bloqueado|Pendiente|N/A",
               "esperado": "...", "obtenido": "...", "evidencia": "capturas/cp-001.png"}],
  "hallazgos": [{"id": "H-01", "severidad": "Crítica|Alta|Media|Baja", "categoria": "...", "texto": "...",
                 "impacto": "...", "como_reproducir": "...", "recomendacion": "..."}],
  "tablas": [{"titulo": "...", "columnas": ["..."], "filas": [["..."]], "sub": ""}],   // tablas propias del dominio
  "recomendaciones": [{"prioridad": "Alta", "accion": "...", "motivo": "..."}],
  "proximos_pasos": ["..."], "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}]
}
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list, bar_chart,  # noqa: E402
                              nivel_badge, estado_pill, falta_informacion, miniatura, resolver_evidencia, e, SERIES)
from _i18n import escribir_bilingue, localizar  # noqa: E402

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
ORDEN_RES = {"Fallido": 0, "Bloqueado": 1, "Pendiente": 2, "Aprobado": 3, "N/A": 4}
TONO = {"ok": "ok", "warn": "warn", "bad": "bad"}


def generar(analisis_json, salida):
    """Escribe salida (ES) y su .en.html (EN). El inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(analisis_json).read_text(encoding="utf-8"))
    base = Path(salida).resolve().parent
    escribir_bilingue(salida, lambda: _html(localizar(datos), base))
    return salida


def _html(d, base):

    hall = sorted(d.get("hallazgos") or [], key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
    criticos = sum(1 for h in hall if h.get("severidad") in ("Crítica", "Alta"))
    pruebas = d.get("pruebas") or []
    fallidas = sum(1 for p in pruebas if p.get("resultado") == "Fallido")
    aprobadas = sum(1 for p in pruebas if p.get("resultado") == "Aprobado")
    metricas = d.get("metricas") or []
    met_mal = sum(1 for m in metricas if m.get("estado") == "Fallido")

    kpis = [("Pruebas", len(pruebas), "bad" if fallidas else ("ok" if pruebas else ""),
             f"{aprobadas} aprobada(s), {fallidas} fallida(s)", "lista"),
            ("Hallazgos", len(hall), "bad" if criticos else ("warn" if hall else "ok"), f"{criticos} crítico(s) o alto(s)", "bicho")]
    if metricas:
        kpis.append(("Métricas bajo objetivo", met_mal, "bad" if met_mal else "ok", f"de {len(metricas)}", "escudo"))

    cuerpo = ""
    if d.get("veredicto"):
        cuerpo += banner(d["veredicto"], TONO.get(d.get("veredicto_tono"), "ok"))
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(d["resumen"])}</p></div>' if d.get("resumen") else ""))

    if metricas:
        cuerpo += section("Métricas", table(["Métrica", "Valor", "Objetivo", "Estado"],
                          [[e(m.get("metrica", "")), e(m.get("valor", "")), e(m.get("objetivo", "")), estado_pill(m.get("estado")) if m.get("estado") else "—"] for m in metricas]))

    if hall:
        por_cat = {}
        for h in hall:
            por_cat[h.get("categoria", "Otro")] = por_cat.get(h.get("categoria", "Otro"), 0) + 1
        filas = [[f'<span class="id">{e(h.get("id", ""))}</span>', nivel_badge(h.get("severidad")), e(h.get("categoria", "")),
                  e(h.get("texto", "")), e(h.get("impacto", "")), e(h.get("recomendacion", ""))] for h in hall]
        cuerpo += section("Hallazgos", table(["ID", "Severidad", "Categoría", "Qué pasa", "Impacto", "Recomendación"], filas), f"{len(hall)} en total", ancho=8)
        cuerpo += section("Hallazgos por categoría", bar_chart([(a, n, SERIES[i % len(SERIES)]) for i, (a, n) in enumerate(sorted(por_cat.items(), key=lambda x: -x[1]))]), ancho=4)
        detalladas = [h for h in hall if h.get("como_reproducir")]
        if detalladas:
            cuerpo += section("Cómo reproducir", table(["ID", "Hallazgo", "Pasos"],
                              [[f'<span class="id">{e(h.get("id"))}</span>', e(h.get("texto", "")), e(h.get("como_reproducir"))] for h in detalladas]))
    else:
        cuerpo += section("Hallazgos", banner("Sin hallazgos.", "ok"))

    for t in d.get("tablas") or []:
        filas = [[e(x) for x in fila] for fila in t.get("filas") or []]
        if filas:
            cuerpo += section(t.get("titulo") or "", table(t.get("columnas") or [], filas), t.get("sub") or "")

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

    if d.get("recomendaciones"):
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"],
                          [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))] for x in d["recomendaciones"]]))
    if d.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(d["proximos_pasos"]))
    cuerpo += falta_informacion(d.get("falta_informacion"))

    filas_meta = [("Generado", d.get("generado")), ("Historia", d.get("historia")), ("Ambiente", d.get("ambiente"))]
    for par in d.get("meta") or []:
        if isinstance(par, (list, tuple)) and len(par) == 2:
            filas_meta.append((par[0], par[1]))
    return page(d.get("titulo") or "Informe", d.get("eyebrow") or "k0lmenIA", meta(filas_meta), cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML genérico de los probadores de k0lmenIA.")
    ap.add_argument("analisis_json")
    ap.add_argument("salida")
    args = ap.parse_args()
    print(generar(args.analisis_json, args.salida))


if __name__ == "__main__":
    main()

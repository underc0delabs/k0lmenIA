#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) del análisis estático de seguridad y secretos (agente analista-codigo-seguro).

Uso (desde la raíz del repo):
    python scripts/generar_informe_sast.py <analisis.json> <salida.html>

El relevamiento lo hace `herramientas/seguridad/sast.py` (`npm run sast`); el agente lo triagea (descarta
falsos positivos, prioriza) y escribe analisis.json. Los secretos se referencian redactados (archivo:línea),
nunca el valor completo.

Esquema del analisis.json (todo opcional salvo "titulo"):
{
  "titulo": "SAST — mi-app", "proyecto": {"ruta": "C:/proyectos/mi-app"}, "generado": "2026-10-19T12:00:00",
  "escaneres": ["secretos (integrado)", "semgrep"],
  "veredicto": "1 secreto expuesto y 3 hallazgos de inyección", "veredicto_tono": "bad", "resumen": "...",
  "hallazgos": [{"id": "H-01", "severidad": "Alta", "categoria": "Inyección SQL", "archivo": "src/db.js",
                 "linea": 42, "texto": "...", "como_reproducir": "...", "recomendacion": "..."}],
  "secretos": [{"tipo": "Clave de acceso AWS", "archivo": ".env", "linea": 3, "severidad": "Alta", "estado": "confirmado"}],
  "recomendaciones": [{"prioridad": "Alta", "accion": "...", "motivo": "..."}],
  "proximos_pasos": ["..."], "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}]
}
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n import escribir_bilingue, localizar  # noqa: E402
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list, bar_chart,  # noqa: E402
                              nivel_badge, falta_informacion, e, SERIES)

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
TONO = {"ok": "ok", "warn": "warn", "bad": "bad"}


def generar(analisis_json, salida):
    """Escribe salida (ES) y su .en.html (EN); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(analisis_json).read_text(encoding="utf-8"))
    escribir_bilingue(salida, lambda: _html(localizar(datos), salida))
    return salida


def _html(d, salida):
    proy = d.get("proyecto") or {}
    hall = sorted(d.get("hallazgos") or [], key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
    crit = sum(1 for h in hall if h.get("severidad") in ("Crítica", "Alta"))
    secretos = d.get("secretos") or []

    kpis = [("Secretos expuestos", len(secretos), "bad" if secretos else "ok", "credenciales en el código", "escudo"),
            ("Hallazgos SAST", len(hall), "bad" if crit else ("warn" if hall else "ok"), f"{crit} crítico(s) o alto(s)", "bicho")]

    cuerpo = ""
    if d.get("veredicto"):
        cuerpo += banner(d["veredicto"], TONO.get(d.get("veredicto_tono"), "ok"))
    if secretos:
        cuerpo += banner("Hay secretos en el código: rotá las credenciales expuestas y sacalas del repositorio (histórico de git incluido).", "bad")
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(d["resumen"])}</p></div>' if d.get("resumen") else ""))

    if secretos:
        filas = [[nivel_badge(s.get("severidad", "Alta")), e(s.get("tipo", "")), e(s.get("archivo", "")), e(s.get("linea", "")), e(s.get("estado", ""))] for s in secretos]
        cuerpo += section("Secretos encontrados", table(["Severidad", "Tipo", "Archivo", "Línea", "Estado"], filas),
                          "el valor va redactado; confirmá y rotá")
    else:
        cuerpo += section("Secretos encontrados", banner("Sin secretos detectados.", "ok"))

    if hall:
        por_cat = {}
        for h in hall:
            por_cat[h.get("categoria", "Otro")] = por_cat.get(h.get("categoria", "Otro"), 0) + 1
        filas = [[f'<span class="id">{e(h.get("id", ""))}</span>', nivel_badge(h.get("severidad")), e(h.get("categoria", "")),
                  f'{e(h.get("archivo", ""))}:{e(h.get("linea", ""))}', e(h.get("texto", "")), e(h.get("recomendacion", ""))] for h in hall]
        cuerpo += section("Hallazgos de código (SAST)", table(["ID", "Severidad", "Categoría", "Ubicación", "Qué pasa", "Recomendación"], filas), f"{len(hall)} en total", ancho=8)
        cuerpo += section("Por categoría", bar_chart([(a, n, SERIES[i % len(SERIES)]) for i, (a, n) in enumerate(sorted(por_cat.items(), key=lambda x: -x[1]))]), ancho=4)
        detalladas = [h for h in hall if h.get("como_reproducir")]
        if detalladas:
            cuerpo += section("Cómo reproducir", table(["ID", "Hallazgo", "Pasos"],
                              [[f'<span class="id">{e(h.get("id"))}</span>', e(h.get("texto", "")), e(h.get("como_reproducir"))] for h in detalladas]))
    else:
        cuerpo += section("Hallazgos de código (SAST)", banner("Sin hallazgos de SAST.", "ok"))

    if d.get("recomendaciones"):
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"],
                          [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))] for x in d["recomendaciones"]]))
    if d.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(d["proximos_pasos"]))
    cuerpo += falta_informacion(d.get("falta_informacion"))

    return page(d.get("titulo") or "Análisis estático de seguridad (SAST)", "Seguridad · código estático (SAST) y secretos",
                meta([("Generado", d.get("generado")), ("Proyecto", proy.get("ruta")),
                      ("Escáneres", ", ".join(d.get("escaneres") or []) or None)]), cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML del análisis estático de seguridad (SAST) y secretos.")
    ap.add_argument("analisis_json")
    ap.add_argument("salida")
    args = ap.parse_args()
    print(generar(args.analisis_json, args.salida))


if __name__ == "__main__":
    main()

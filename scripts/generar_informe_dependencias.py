#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) del análisis de dependencias / SCA (agente analista-dependencias).

Uso (desde la raíz del repo):
    python scripts/generar_informe_dependencias.py <analisis.json> <salida.html>

El relevamiento lo hace `herramientas/seguridad/dependencias.py` (`npm run dependencias`); el agente lo triagea
y escribe analisis.json.

Esquema del analisis.json (todo opcional salvo "titulo"):
{
  "titulo": "SCA — mi-app", "proyecto": {"ruta": "C:/proyectos/mi-app", "ecosistemas": ["Node", "Python"]},
  "generado": "2026-10-19T12:00:00", "escaneres": ["npm audit", "pip-audit"],
  "veredicto": "2 vulnerabilidades críticas con fix disponible", "veredicto_tono": "bad", "resumen": "...",
  "vulnerabilidades": [{"paquete": "lodash 4.17.4", "severidad": "Crítica", "id": "CVE-2021-23337",
                        "ecosistema": "Node", "fix": true, "recomendacion": "actualizar a 4.17.21"}],
  "licencias": [{"paquete": "pkg", "licencia": "GPL-3.0", "riesgo": "revisar compatibilidad"}],
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
                              nivel_badge, estado_pill, falta_informacion, e, SERIES)

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
TONO = {"ok": "ok", "warn": "warn", "bad": "bad"}


def generar(analisis_json, salida):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>, que abre el idioma elegido); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(analisis_json).read_text(encoding="utf-8"))
    escribir_bilingue(salida, lambda: _html(localizar(datos), salida))
    return salida


def _html(d, salida):
    proy = d.get("proyecto") or {}
    vulns = sorted(d.get("vulnerabilidades") or [], key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
    crit = sum(1 for v in vulns if v.get("severidad") in ("Crítica", "Alta"))
    con_fix = sum(1 for v in vulns if v.get("fix"))
    lic = d.get("licencias") or []

    kpis = [("Vulnerabilidades", len(vulns), "bad" if crit else ("warn" if vulns else "ok"), f"{crit} crítica(s) o alta(s)", "escudo"),
            ("Con fix disponible", con_fix, "ok" if con_fix else "", "actualizar resuelve", "carga")]
    if lic:
        kpis.append(("Licencias a revisar", len(lic), "warn" if lic else "ok", "compatibilidad", "lista"))

    cuerpo = ""
    if d.get("veredicto"):
        cuerpo += banner(d["veredicto"], TONO.get(d.get("veredicto_tono"), "ok"))
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(d["resumen"])}</p></div>' if d.get("resumen") else ""))

    if vulns:
        por_eco = {}
        for v in vulns:
            por_eco[v.get("ecosistema", "?")] = por_eco.get(v.get("ecosistema", "?"), 0) + 1
        filas = [[nivel_badge(v.get("severidad")), e(v.get("paquete", "")), e(v.get("id", "")), e(v.get("ecosistema", "")),
                  estado_pill("Aprobado") if v.get("fix") else "—", e(v.get("recomendacion", ""))] for v in vulns]
        cuerpo += section("Vulnerabilidades (CVE)", table(["Severidad", "Paquete", "ID", "Ecosistema", "¿Fix?", "Recomendación"], filas), f"{len(vulns)} en total", ancho=8)
        cuerpo += section("Por ecosistema", bar_chart([(a, n, SERIES[i % len(SERIES)]) for i, (a, n) in enumerate(sorted(por_eco.items(), key=lambda x: -x[1]))]), ancho=4)
    else:
        cuerpo += section("Vulnerabilidades (CVE)", banner("Sin vulnerabilidades conocidas en los escáneres corridos.", "ok"))

    if lic:
        cuerpo += section("Licencias a revisar", table(["Paquete", "Licencia", "Riesgo"],
                          [[e(x.get("paquete", "")), e(x.get("licencia", "")), e(x.get("riesgo", ""))] for x in lic]))

    if d.get("recomendaciones"):
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"],
                          [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))] for x in d["recomendaciones"]]))
    if d.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(d["proximos_pasos"]))
    cuerpo += falta_informacion(d.get("falta_informacion"))

    return page(d.get("titulo") or "Análisis de dependencias (SCA)", "Seguridad · dependencias (SCA)",
                meta([("Generado", d.get("generado")), ("Proyecto", proy.get("ruta")),
                      ("Ecosistemas", ", ".join(proy.get("ecosistemas") or []) or None),
                      ("Escáneres", ", ".join(d.get("escaneres") or []) or None)]), cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML del análisis de dependencias (SCA).")
    ap.add_argument("analisis_json")
    ap.add_argument("salida")
    args = ap.parse_args()
    print(generar(args.analisis_json, args.salida))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) de una sesión de ejecución manual (skill ejecucion-manual, agente asistente-ejecucion-manual).

Uso (desde la raíz del repo):
    python scripts/generar_informe_ejecucion_manual.py <sesion.json> <salida.html> [--analisis analisis.json]

La sesión la arma scripts/ejecucion_manual.py. Muestra: veredicto, avance, resultado de los casos, tiempo real contra el
estimado (por caso y en total), resultado por prioridad, inconsistencias para revisar (por ejemplo, un caso Aprobado con
un paso Fallido), el detalle de cada caso con su evidencia, los pasos que fallaron o se bloquearon, los bugs, lo que quedó
pendiente y el estado de la publicación en la herramienta de gestión.

El análisis (opcional) aporta:
{
  "veredicto": "...", "veredicto_tono": "ok|warn|bad", "resumen": "...",
  "observaciones": [{"severidad": "Alta", "texto": "...", "recomendacion": "..."}],
  "publicacion": {"estado": "Pendiente de confirmación|Publicada|No corresponde", "herramienta": "Xray", "detalle": "..."},
  "recomendaciones": [{"prioridad": "Alta", "accion": "...", "motivo": "..."}],
  "proximos_pasos": ["..."], "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],
  "en": {... las mismas claves en inglés ...}
}
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n import escribir_bilingue, localizar  # noqa: E402
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list, donut_panel, grouped_columns,  # noqa: E402
                              stacked_bars, nivel_badge, estado_pill, falta_informacion, miniatura, resolver_evidencia, e,
                              ESTADO_COLOR, SERIES, NEUTRO)

ORDEN = {"Fallido": 0, "Bloqueado": 1, "En ejecución": 2, "Pendiente": 3, "Aprobado": 4, "N/A": 5}
PRIOS = ["Crítica", "Alta", "Media", "Baja"]


def generar(sesion_json, salida, analisis_json=None):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>); el inglés del agente va en el bloque "en" del análisis."""
    sesion = json.loads(Path(sesion_json).read_text(encoding="utf-8"))
    analisis = json.loads(Path(analisis_json).read_text(encoding="utf-8")) if analisis_json else {}
    escribir_bilingue(salida, lambda: _html(sesion, localizar(analisis), salida))
    return salida


def _min(seg):
    return "—" if seg in (None, "") else f"{seg / 60:.1f} min"


def _html(s, a, salida):
    base = Path(salida).resolve().parent
    casos = s.get("casos") or []
    cuenta = Counter(c.get("estado") for c in casos)
    total = len(casos)
    ejecutados = sum(cuenta[r] for r in ("Aprobado", "Fallido", "Bloqueado", "N/A"))
    terminados = cuenta["Aprobado"] + cuenta["Fallido"] + cuenta["Bloqueado"]
    pct_avance = round(ejecutados / total * 100) if total else 0
    pct_ok = round(cuenta["Aprobado"] / terminados * 100) if terminados else 0
    real = sum((c.get("duracion_s") or 0) for c in casos) / 60
    est = sum((c.get("estimado_min") or 0) for c in casos if c.get("estado") in ("Aprobado", "Fallido", "Bloqueado", "N/A"))
    bugs = sorted({b for c in casos for b in c.get("bugs") or []})
    incons = s.get("inconsistencias") or []
    pendientes = [c for c in casos if c.get("estado") in ("Pendiente", "En ejecución")]

    if a.get("veredicto"):
        veredicto, tono = a["veredicto"], a.get("veredicto_tono") or "ok"
    elif cuenta["Fallido"] or cuenta["Bloqueado"]:
        veredicto, tono = "La ejecución encontró fallas o bloqueos para resolver", "bad" if cuenta["Fallido"] else "warn"
    elif pendientes:
        veredicto, tono = "La ejecución quedó incompleta: hay casos sin ejecutar", "warn"
    else:
        veredicto, tono = "Todos los casos ejecutados aprobaron", "ok"

    kpis = [("Avance", f"{pct_avance}%", "ok" if pct_avance == 100 else "warn", f"{ejecutados} de {total} casos", "lista", {"pct": pct_avance}),
            ("Aprobados", f"{pct_ok}%" if terminados else "—", "ok" if pct_ok == 100 and terminados else ("warn" if pct_ok >= 80 else "bad"),
             f"{cuenta['Aprobado']} de {terminados} terminados", "ok", {"pct": pct_ok}),
            ("Fallidos", cuenta["Fallido"], "bad" if cuenta["Fallido"] else "ok", f"{cuenta['Bloqueado']} bloqueado(s)", "bicho"),
            ("Bugs", len(bugs), "bad" if bugs else "ok", ", ".join(bugs[:4]) or "sin bugs", "bicho"),
            ("Tiempo real", f"{real:.0f} min", "warn" if est and real > est * 1.25 else "ok", f"estimado {est:.0f} min", "reloj")]
    if incons:
        kpis.append(("Para revisar", len(incons), "warn", "inconsistencias de la sesión", "warn"))

    cuerpo = banner(veredicto, tono)
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(a["resumen"])}</p></div>' if a.get("resumen") else ""))

    segmentos = [(cuenta[r], ESTADO_COLOR.get(r, NEUTRO), r) for r in ("Aprobado", "Fallido", "Bloqueado", "N/A", "Pendiente") if cuenta[r]]
    if segmentos:
        cuerpo += section("Resultado de los casos", donut_panel(segmentos, pct_ok, "aprobados"), f"{total} caso(s)", ancho=5)
    con_tiempo = [c for c in casos if c.get("duracion_s") is not None and c.get("estimado_min")]
    if con_tiempo:
        cuerpo += section("Tiempo real contra estimado", grouped_columns(
            [c["id"] for c in con_tiempo[:12]],
            [("Real", SERIES[1], [round(c["duracion_s"] / 60, 1) for c in con_tiempo[:12]]),
             ("Estimado", SERIES[0], [c["estimado_min"] for c in con_tiempo[:12]])],
            fmt=lambda v: f"{v:.1f}", ancho=760), "minutos por caso", ancho=7)
    filas_prio = [(p, [sum(1 for c in casos if c.get("prioridad") == p and c.get("estado") == r) for r in ("Aprobado", "Fallido", "Bloqueado", "Pendiente")])
                  for p in PRIOS if any(c.get("prioridad") == p for c in casos)]
    if filas_prio:
        cuerpo += section("Resultado por prioridad", stacked_bars(filas_prio, [(r, ESTADO_COLOR.get(r, NEUTRO)) for r in ("Aprobado", "Fallido", "Bloqueado", "Pendiente")]))

    if incons:
        cuerpo += section("Inconsistencias para revisar", table(["Caso", "Qué pasa", "Detalle"],
                          [[f'<span class="id">{e(i["caso"])}</span>', e(i["tipo"]), e(i.get("detalle", ""))] for i in incons]),
                          "el resultado registrado no cierra con los pasos o le falta un dato")

    filas = []
    for c in sorted(casos, key=lambda c: (ORDEN.get(c.get("estado"), 9), PRIOS.index(c["prioridad"]) if c.get("prioridad") in PRIOS else 9)):
        ev = ""
        if c.get("evidencia"):
            ruta, existe = resolver_evidencia(c["evidencia"][0], base)
            ev = miniatura(ruta, c.get("titulo", ""), existe=existe)
        filas.append([f'<span class="id">{e(c["id"])}</span>', e(c.get("titulo", "")), nivel_badge(c.get("prioridad", "Media")),
                      estado_pill(c.get("estado")), e(_min(c.get("duracion_s"))), e(f'{c["estimado_min"]:.1f} min' if c.get("estimado_min") else "—"),
                      e(", ".join(c.get("bugs") or []) or "—"), ev])
    cuerpo += section("Casos ejecutados", table(["ID", "Caso", "Prioridad", "Resultado", "Tiempo real", "Estimado", "Bugs", "Evidencia"], filas))

    pasos = [[f'<span class="id">{e(c["id"])}</span>', str(p["n"]), e(p.get("accion", "")), e(p.get("esperado", "")), e(p.get("obtenido", "") or c.get("motivo", "")),
              estado_pill(p["resultado"])]
             for c in casos for p in c.get("pasos") or [] if p.get("resultado") in ("Fallido", "Bloqueado")]
    if pasos:
        cuerpo += section("Pasos que fallaron o se bloquearon", table(["Caso", "Paso", "Acción", "Esperado", "Obtenido", "Resultado"], pasos))
    if bugs:
        cuerpo += section("Bugs reportados", table(["Bug", "Casos"], [[f'<span class="id">{e(b)}</span>', e(", ".join(c["id"] for c in casos if b in (c.get("bugs") or [])))] for b in bugs]), ancho=6)
    if pendientes:
        cuerpo += section("Casos sin ejecutar", doc_list([f'{c["id"]} — {c.get("titulo", "")}' for c in pendientes]), "no se cuentan como aprobados", ancho=6 if bugs else 12)

    pub = a.get("publicacion") or {}
    if pub:
        cuerpo += section("Publicación en la herramienta de gestión", table(["Estado", "Herramienta", "Detalle"],
                          [[e(pub.get("estado", "")), e(pub.get("herramienta", "—")), e(pub.get("detalle", ""))]]))
    if a.get("observaciones"):
        cuerpo += section("Observaciones", table(["Severidad", "Qué pasa", "Recomendación"],
                          [[nivel_badge(o.get("severidad", "Media")), e(o.get("texto", "")), e(o.get("recomendacion", ""))] for o in a["observaciones"]]))
    if a.get("recomendaciones"):
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"],
                          [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))] for x in a["recomendaciones"]]))
    if a.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(a["proximos_pasos"]))
    cuerpo += falta_informacion(a.get("falta_informacion"))

    return page(f'Ejecución manual — {s.get("historia", "")}', "Ejecución manual",
                meta([("Empezó", (s.get("inicio") or "")[:16].replace("T", " ")), ("Terminó", (s.get("fin") or "")[:16].replace("T", " ") or None),
                      ("Ambiente", s.get("ambiente")), ("Tester", s.get("tester")), ("Navegador", s.get("navegador")),
                      ("Estado de la sesión", s.get("estado")), ("Casos desde", Path(s.get("fuente") or "").name or None)]), cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de una sesión de ejecución manual.")
    ap.add_argument("sesion_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis")
    a = ap.parse_args()
    print(generar(a.sesion_json, a.salida, a.analisis))


if __name__ == "__main__":
    main()

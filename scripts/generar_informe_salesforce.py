#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) del probador de Salesforce: el inventario de la org (salesforce.json, de
`npm run salesforce`) y, opcionalmente, el análisis y las pruebas del agente probador-salesforce.

Uso:
    python scripts/generar_informe_salesforce.py <salesforce.json> <salida.html> [--analisis analisis.json]

Esquema del analisis.json (todo opcional):
{
  "veredicto": "La org está lista para probar la release 2.4, con 2 riesgos", "veredicto_tono": "ok|warn|bad",
  "resumen": "...",
  "pruebas": [{"id": "CP-001", "area": "Validación", "caso": "Oportunidad sin monto", "perfil": "Ventas",
               "resultado": "Aprobado|Fallido|Bloqueado|Pendiente", "detalle": "...", "evidencia": "capturas/cp-001.png"}],
  "hallazgos": [{"severidad": "Alta", "area": "Sharing", "texto": "..."}],      // los del agente (suman a los del inventario)
  "descartados": [{"texto": "...", "motivo": "..."}],                            // hallazgos del inventario que no aplican
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
from _i18n import escribir_bilingue, localizar, t  # noqa: E402
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list, two_col, bar_chart,
                              nivel_badge, estado_pill, falta_informacion, miniatura, resolver_evidencia, e,
                              CRITICO, SERIO, AVISO, SERIES)

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
TONO = {"ok": "ok", "warn": "warn", "bad": "bad"}


def _rel(r, rel, campo="Name"):
    v = r.get(rel)
    return v.get(campo) if isinstance(v, dict) else r.get(campo)


def generar(sf_json, salida, analisis_json=None):
    """Escribe salida (ES) y su .en.html (EN); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(sf_json).read_text(encoding="utf-8"))
    analisis = json.loads(Path(analisis_json).read_text(encoding="utf-8")) if analisis_json and Path(analisis_json).exists() else {}
    escribir_bilingue(salida, lambda: _html(datos, localizar(analisis), salida, sf_json))
    return salida


def _html(datos, analisis, salida, sf_json):
    inv = datos.get("inventario") or {}
    org = datos.get("org") or {}

    descartados = {(d.get("texto") or "").strip() for d in analisis.get("descartados") or []}
    hall = [h for h in datos.get("hallazgos") or [] if (h.get("texto") or "").strip() not in descartados]
    hall += analisis.get("hallazgos") or []
    hall.sort(key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
    pruebas = analisis.get("pruebas") or []
    fallidas = sum(1 for p in pruebas if p.get("resultado") == "Fallido")
    criticos = sum(1 for h in hall if h.get("severidad") in ("Crítica", "Alta"))
    cobertura = inv.get("cobertura_org")

    kpis = [("Org", "Sandbox" if org.get("sandbox") else "PRODUCCIÓN", "ok" if org.get("sandbox") else "bad", org.get("tipo") or "", "pantalla"),
            ("Cobertura de Apex", f"{cobertura:.0f} %" if isinstance(cobertura, (int, float)) else "—",
             ("ok" if cobertura >= 75 else "bad") if isinstance(cobertura, (int, float)) else "", "mínimo 75 % para producción", "codigo",
             {"pct": cobertura} if isinstance(cobertura, (int, float)) else None),
            ("Hallazgos", len(hall), "bad" if criticos else ("warn" if hall else "ok"), f"{criticos} crítico(s) o alto(s)", "bicho"),
            ("Sugerencias de prueba", len(datos.get("sugerencias") or []), "", "derivadas del inventario", "lista")]
    if pruebas:
        kpis.append(("Pruebas ejecutadas", len(pruebas), "bad" if fallidas else "ok", f"{fallidas} fallida(s)", "ok" if not fallidas else "bad"))

    cuerpo = ""
    if analisis.get("veredicto"):
        cuerpo += banner(analisis["veredicto"], TONO.get(analisis.get("veredicto_tono"), "ok"))
    if not org.get("sandbox"):
        cuerpo += banner("Org de PRODUCCIÓN: solo se relevó en lectura. Las pruebas funcionales van en un sandbox.", "bad")
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(analisis["resumen"])}</p></div>' if analisis.get("resumen") else ""))

    if hall:
        cuerpo += section("Hallazgos", table(["Severidad", "Área", "Detalle"],
                                             [[nivel_badge(h.get("severidad")), e(h.get("area", "")), e(h.get("texto", ""))] for h in hall]),
                          sub=f"{len(hall)} en total")
    else:
        cuerpo += section("Hallazgos", banner("Sin hallazgos en el inventario.", "ok"))

    if pruebas:
        base = Path(salida).resolve().parent
        filas = []
        for p in pruebas:
            ev = ""
            if p.get("evidencia"):
                ruta, existe = resolver_evidencia(p["evidencia"], base)
                ev = miniatura(ruta, p.get("caso", ""), existe=existe)
            filas.append([f'<span class="id">{e(p.get("id", ""))}</span>', e(p.get("area", "")), e(p.get("caso", "")), e(p.get("perfil", "—")),
                          estado_pill(p.get("resultado")), e(p.get("detalle", "")), ev])
        cuerpo += section("Pruebas ejecutadas", table(["ID", "Área", "Caso", "Perfil", "Resultado", "Detalle", "Evidencia"], filas))

    if datos.get("sugerencias"):
        por_area = {}
        for s in datos["sugerencias"]:
            por_area[s.get("area", "Otro")] = por_area.get(s.get("area", "Otro"), 0) + 1
        izq = section("Qué probar, por área", bar_chart([(a, n, SERIES[i % len(SERIES)]) for i, (a, n) in enumerate(sorted(por_area.items(), key=lambda x: -x[1]))]), ancho=4)
        der = section("Sugerencias de prueba", table(["Área", "Elemento", "Prueba sugerida"],
                                                     [[e(s.get("area")), f'<span class="mono">{e(s.get("elemento"))}</span>', e(s.get("prueba"))]
                                                      for s in datos["sugerencias"]]), "derivadas del inventario: el agente las prioriza", ancho=8)
        cuerpo += der + izq

    filas_org = [["Alias", e(org.get("alias"))], ["Nombre", e(org.get("nombre"))], ["Tipo", e(org.get("tipo"))],
                 ["Instancia", e(org.get("instancia"))], ["Idioma", e(org.get("idioma"))], ["Zona horaria", e(org.get("zona_horaria"))],
                 ["Versión de API", e(org.get("api"))]]
    izq = section("La org", table(["Dato", "Valor"], filas_org), ancho=6)
    sev_lim = []
    for lim in inv.get("limites") or []:
        mx, rem = lim.get("max") or 0, lim.get("remaining")
        if mx and rem is not None and (mx - rem) / mx >= 0.5:
            pct = 100 * (mx - rem) / mx
            sev_lim.append((lim.get("name"), round(pct), CRITICO if pct >= 90 else SERIO if pct >= 80 else AVISO))
    der = section("Límites más usados", bar_chart(sorted(sev_lim, key=lambda x: -x[1])[:10], ancho_etiqueta=220) if sev_lim
                  else banner("Ningún límite supera el 50 % de uso.", "ok"), "% usado", ancho=6)
    cuerpo += two_col(izq, der)

    if inv.get("apex"):
        ax = inv["apex"]
        if ax.get("error"):
            cuerpo += section("Tests de Apex", banner(f'{t("No se pudieron correr:")} {ax["error"]}', "warn"))
        else:
            filas = [["Resultado", e(ax.get("resultado"))], ["Corridos", e(ax.get("corridos"))], ["Aprobados", e(ax.get("aprobados"))],
                     ["Fallidos", e(ax.get("fallidos_n"))], ["Cobertura de la org", e(ax.get("cobertura_org"))]]
            cuerpo += section("Tests de Apex", table(["Dato", "Valor"], filas))

    cob = sorted(inv.get("cobertura") or [], key=lambda c: (c.get("NumLinesCovered") or 0) / max(1, (c.get("NumLinesCovered") or 0) + (c.get("NumLinesUncovered") or 0)))
    if cob:
        filas = []
        for c in cob[:25]:
            cub, sin = c.get("NumLinesCovered") or 0, c.get("NumLinesUncovered") or 0
            pct = 100 * cub / (cub + sin) if cub + sin else 0
            filas.append([f'<span class="mono">{e(_rel(c, "ApexClassOrTrigger"))}</span>', f"{pct:.0f} %", e(cub), e(sin)])
        cuerpo += section("Clases con menos cobertura", table(["Clase o trigger", "Cobertura", "Líneas cubiertas", "Sin cubrir"], filas), "las 25 más bajas")

    if inv.get("validaciones"):
        cuerpo += section("Reglas de validación", table(["Objeto", "Regla", "Activa", "Mensaje", "Campo"],
                                                        [[e(_rel(v, "EntityDefinition", "QualifiedApiName")), f'<span class="mono">{e(v.get("ValidationName"))}</span>',
                                                          "Sí" if v.get("Active") else "No", e(v.get("ErrorMessage")), e(v.get("ErrorDisplayField") or "arriba")]
                                                         for v in inv["validaciones"]]), f'{len(inv["validaciones"])} en total')
    if inv.get("flows"):
        cuerpo += section("Flows y automatizaciones", table(["Flow", "Tipo", "Disparador", "Activo", "Última modificación"],
                                                            [[e(f.get("Label")), e("Process Builder" if f.get("ProcessType") == "Workflow" else f.get("ProcessType")),
                                                              e(f.get("TriggerType") or "—"), "Sí" if f.get("IsActive") else "No", e((f.get("LastModifiedDate") or "")[:10])]
                                                             for f in inv["flows"]]), f'{len(inv["flows"])} en total')
    if inv.get("triggers"):
        cuerpo += section("Triggers de Apex", table(["Objeto", "Trigger", "Estado"],
                                                    [[e(t.get("TableEnumOrId")), f'<span class="mono">{e(t.get("Name"))}</span>', e(t.get("Status"))] for t in inv["triggers"]]))
    izq = section("Perfiles con usuarios activos", table(["Perfil", "Usuarios activos"],
                                                         [[e(_rel(p, "Profile")), e(p.get("total"))]
                                                          for p in sorted(inv.get("usuarios_por_perfil") or [], key=lambda p: -(p.get("total") or 0))]),
                  ancho=6) if inv.get("usuarios_por_perfil") else ""
    der = section("Permission sets", table(["Permission set", "Paquete"],
                                           [[e(p.get("Label")), e(p.get("NamespacePrefix") or "—")] for p in inv.get("permission_sets") or []]),
                  ancho=6) if inv.get("permission_sets") else ""
    if izq and der:
        cuerpo += two_col(izq, der)
    elif izq or der:
        cuerpo += izq or der
    if inv.get("sharing"):
        cuerpo += section("Acceso por defecto (OWD)", table(["Objeto", "Interno", "Externo"],
                                                            [[e(o.get("QualifiedApiName")), e(o.get("InternalSharingModel")), e(o.get("ExternalSharingModel"))]
                                                             for o in inv["sharing"]]))
    if inv.get("record_types"):
        cuerpo += section("Record types", table(["Objeto", "Record type", "Activo"],
                                                [[e(r.get("SobjectType")), e(r.get("Name")), "Sí" if r.get("IsActive") else "No"] for r in inv["record_types"]]))

    if analisis.get("recomendaciones"):
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"],
                                                   [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))]
                                                    for x in analisis["recomendaciones"]]))
    if analisis.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(analisis["proximos_pasos"]))
    cuerpo += falta_informacion(analisis.get("falta_informacion"))
    if inv.get("errores"):
        cuerpo += section("Consultas que no se pudieron hacer", table(["Consulta", "Error"],
                                                                      [[e(k), f'<span class="mono">{e(v)}</span>'] for k, v in inv["errores"].items()]),
                          "puede faltar permiso (View Setup, API Enabled) o el objeto no existe en esta edición")

    return page("Salesforce", "Salesforce · inventario y pruebas",
                meta([("Generado", datos.get("generado")), ("Historia", datos.get("historia")), ("Org", org.get("alias")),
                      ("Tipo", "Sandbox" if org.get("sandbox") else "Producción")]), cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML del probador de Salesforce.")
    ap.add_argument("sf_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis", default=None)
    args = ap.parse_args()
    print(generar(args.sf_json, args.salida, args.analisis))


if __name__ == "__main__":
    main()

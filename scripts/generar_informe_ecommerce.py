#!/usr/bin/env python3
"""
Informe HTML (modo oscuro) de los probadores de e-commerce (probador-shopify y probador-wordpress): el
relevamiento de la tienda (<plataforma>.json, de `npm run shopify` o `npm run wordpress`) y, opcionalmente,
el análisis y las pruebas del agente.

Uso:
    python scripts/generar_informe_ecommerce.py <plataforma.json> <salida.html> [--analisis analisis.json]

Esquema del analisis.json (todo opcional):
{
  "veredicto": "La tienda está lista para la campaña, con 2 riesgos", "veredicto_tono": "ok|warn|bad",
  "resumen": "...",
  "pruebas": [{"id": "CP-001", "area": "Checkout", "caso": "Pago rechazado con tarjeta de prueba", "dispositivo": "Mobile",
               "resultado": "Aprobado|Fallido|Bloqueado|Pendiente", "detalle": "...", "evidencia": "capturas/cp-001.png"}],
  "hallazgos": [{"severidad": "Alta", "area": "Envíos", "texto": "..."}],      // los del agente (suman a los del relevamiento)
  "descartados": [{"texto": "...", "motivo": "..."}],                           // hallazgos del relevamiento que no aplican
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
import _historial  # noqa: E402
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list, bar_chart, nivel_badge,  # noqa: E402
                              estado_pill, falta_informacion, miniatura, resolver_evidencia, _pastilla, e,
                              OK, AVISO, CRITICO, NEUTRO, SERIES)

ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
NOMBRE = {"shopify": "Shopify", "wordpress": "WordPress / WooCommerce", "prestashop": "PrestaShop", "vtex": "VTEX"}
ESTADO_CHEQUEO = {"ok": ("Bien", OK, "✓"), "aviso": ("Revisar", AVISO, "!"), "falla": ("Falla", CRITICO, "✕"), "info": ("Info", NEUTRO, "i")}

for _p in NOMBRE:
    _historial.TIPOS.setdefault(_p, {
        "archivo": f"{_p}.json", "items": lambda d: d.get("hallazgos") or [],
        "clave": lambda h: f'{h.get("area")}|{_historial._norm(h.get("texto"))}', "titulo": lambda h: f'[{h.get("area")}] {h.get("texto")}',
        "metricas": [("Hallazgos", _historial._r("hallazgos"), ""), ("Críticos o altos", _historial._r("criticos"), ""),
                     ("Productos con problemas", _historial._r("productos_con_problemas"), ""), ("Sugerencias", _historial._r("sugerencias"), "")]})


def generar(datos_json, salida, analisis_json=None):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>, que abre el idioma elegido); el inglés del agente va en el bloque "en" del analisis.json."""
    datos = json.loads(Path(datos_json).read_text(encoding="utf-8"))
    analisis = json.loads(Path(analisis_json).read_text(encoding="utf-8")) if analisis_json and Path(analisis_json).exists() else {}
    escribir_bilingue(salida, lambda: _html(datos, localizar(analisis), salida, datos_json))
    return salida


def _html(datos, analisis, salida, datos_json):
    plataforma = datos.get("plataforma") or "shopify"
    nombre = NOMBRE.get(plataforma, plataforma.capitalize())
    tienda = datos.get("tienda") or {}

    descartados = {(d.get("texto") or "").strip() for d in analisis.get("descartados") or []}
    hall = [h for h in datos.get("hallazgos") or [] if (h.get("texto") or "").strip() not in descartados]
    hall += analisis.get("hallazgos") or []
    hall.sort(key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
    pruebas = analisis.get("pruebas") or []
    fallidas = sum(1 for p in pruebas if p.get("resultado") == "Fallido")
    criticos = sum(1 for h in hall if h.get("severidad") in ("Crítica", "Alta"))

    kpis = [("Tienda", tienda.get("version") or nombre, "", tienda.get("ambiente") if tienda.get("ambiente") not in (None, "—") else tienda.get("url", ""), "pantalla"),
            ("Hallazgos", len(hall), "bad" if criticos else ("warn" if hall else "ok"), f"{criticos} crítico(s) o alto(s)", "bicho"),
            ("Sugerencias de prueba", len(datos.get("sugerencias") or []), "", "derivadas del relevamiento", "lista")]
    kpis += [(i.get("etiqueta"), i.get("valor"), i.get("tono") or "", i.get("detalle") or "") for i in datos.get("indicadores") or []]
    if pruebas:
        kpis.append(("Pruebas ejecutadas", len(pruebas), "bad" if fallidas else "ok", f"{fallidas} fallida(s)", "ok" if not fallidas else "bad"))

    cuerpo = ""
    if analisis.get("veredicto"):
        cuerpo += banner(analisis["veredicto"], analisis.get("veredicto_tono") if analisis.get("veredicto_tono") in ("ok", "warn", "bad") else "ok")
    cuerpo += section("Resumen", kpi_tiles(kpis) + (f'<div class="cardbody"><p>{e(analisis["resumen"])}</p></div>' if analisis.get("resumen") else ""))

    if hall:
        cuerpo += section("Hallazgos", table(["Severidad", "Área", "Detalle"],
                                             [[nivel_badge(h.get("severidad")), e(h.get("area", "")), e(h.get("texto", ""))] for h in hall]),
                          sub=f"{len(hall)} en total")
    else:
        cuerpo += section("Hallazgos", banner("Sin hallazgos en el relevamiento.", "ok"))

    if pruebas:
        base = Path(salida).resolve().parent
        filas = []
        for p in pruebas:
            ev = ""
            if p.get("evidencia"):
                ruta, existe = resolver_evidencia(p["evidencia"], base)
                ev = miniatura(ruta, p.get("caso", ""), existe=existe)
            filas.append([f'<span class="id">{e(p.get("id", ""))}</span>', e(p.get("area", "")), e(p.get("caso", "")), e(p.get("dispositivo", "—")),
                          estado_pill(p.get("resultado")), e(p.get("detalle", "")), ev])
        cuerpo += section("Pruebas ejecutadas", table(["ID", "Área", "Caso", "Dispositivo", "Resultado", "Detalle", "Evidencia"], filas))

    if datos.get("sugerencias"):
        por_area = {}
        for s in datos["sugerencias"]:
            por_area[s.get("area", "Otro")] = por_area.get(s.get("area", "Otro"), 0) + 1
        cuerpo += section("Sugerencias de prueba", table(["Área", "Elemento", "Prueba sugerida"],
                                                         [[e(s.get("area")), f'<span class="mono">{e(s.get("elemento"))}</span>', e(s.get("prueba"))]
                                                          for s in datos["sugerencias"]]), "derivadas del relevamiento: el agente las prioriza", ancho=8)
        cuerpo += section("Qué probar, por área", bar_chart([(a, n, SERIES[i % len(SERIES)]) for i, (a, n) in
                                                             enumerate(sorted(por_area.items(), key=lambda x: -x[1]))]), ancho=4)

    chequeos = (datos.get("vidriera") or {}).get("chequeos") or []
    if chequeos:
        filas = []
        for ch in chequeos:
            txt, color, ic = ESTADO_CHEQUEO.get(ch.get("estado"), ESTADO_CHEQUEO["info"])
            filas.append([e(ch.get("chequeo")), _pastilla(txt, color, ic), e(ch.get("detalle"))])
        cuerpo += section("Chequeos de la vidriera", table(["Chequeo", "Estado", "Detalle"], filas), "públicos, sin credenciales")

    for t in datos.get("tablas") or []:
        cuerpo += section(t.get("titulo") or "", table(t.get("columnas") or [], [[e(x) for x in fila] for fila in t.get("filas") or []]), t.get("sub") or "")

    cuerpo += _historial.seccion(plataforma, Path(datos_json).resolve().parent, datos)
    if analisis.get("recomendaciones"):
        cuerpo += section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"],
                                                   [[nivel_badge(x.get("prioridad", "Media")), e(x.get("accion", "")), e(x.get("motivo", ""))]
                                                    for x in analisis["recomendaciones"]]))
    if analisis.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(analisis["proximos_pasos"]))
    cuerpo += falta_informacion(analisis.get("falta_informacion"))
    if datos.get("errores"):
        cuerpo += section("Consultas que no se pudieron hacer", table(["Consulta", "Error"],
                                                                      [[e(k), f'<span class="mono">{e(v)}</span>'] for k, v in datos["errores"].items()]),
                          "puede faltar la clave o el permiso de lectura, o la versión de la API no lo tiene")

    return page(nombre, f"{nombre} · relevamiento y pruebas",
                meta([("Generado", datos.get("generado")), ("Historia", datos.get("historia")), ("Tienda", tienda.get("url"))]), cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de los probadores de e-commerce (Shopify, WordPress / WooCommerce).")
    ap.add_argument("datos_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis", default=None)
    args = ap.parse_args()
    print(generar(args.datos_json, args.salida, args.analisis))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Genera el Informe de monitoreo sintético en HTML (dashboard, modo oscuro) a partir de monitoreo.json
(npm run monitorear, herramientas/k0lmena/tools/monitoreo/monitorear.js).

Uso:
    python scripts/generar_informe_monitoreo.py <monitoreo.json> <salida.html>

Qué muestra: el estado de la corrida (OK, Degradado o Caído) y qué cambió desde la anterior (qué se rompió
y qué se recuperó), indicadores (checks OK, tiempo promedio, disponibilidad en las corridas guardadas,
certificados por vencer), el resultado de cada check, los tiempos de respuesta, la disponibilidad y el
tiempo de cada check a lo largo de las corridas de historial/ y el link al informe de cada una.
"""
import argparse
import json
import sys
from pathlib import Path

from _i18n import escribir_bilingue, localizar, idioma_actual  # noqa: E402
from _estilos_reporte import (e, page, meta, section, kpi_tiles, banner, table, bar_chart, line_chart, _pastilla,
                              CRITICO, AVISO, OK, NEUTRO, SERIES)

COLOR = {"OK": OK, "Lento": AVISO, "Por vencer": AVISO, "Degradado": AVISO, "Caído": CRITICO}
ICONO = {"OK": "✓", "Lento": "!", "Por vencer": "!", "Degradado": "!", "Caído": "✕"}
TONO = {"OK": "ok", "Degradado": "warn", "Caído": "bad"}


def pill(estado):
    return _pastilla(estado or "—", COLOR.get(estado, NEUTRO), ICONO.get(estado, "●"))


def corridas(carpeta, actual):
    """Corridas guardadas en historial/ (de la más vieja a la más nueva) + la actual: [(sello, datos, informe)]."""
    salida = []
    for d in sorted((Path(carpeta) / "historial").glob("*"), key=lambda d: d.name):
        arch = d / "monitoreo.json"
        if not arch.exists():
            continue
        try:
            datos = json.loads(arch.read_text(encoding="utf-8"))
        except ValueError:
            continue
        informe = f"historial/{d.name}/informe-monitoreo.html" if (d / "informe-monitoreo.html").exists() else None
        salida.append((d.name, datos, informe))
    return salida + [("actual", actual, None)]


def disponibilidad(lista, check_id=None):
    """% de corridas sin Caído (de un check, o de la corrida entera)."""
    estados = []
    for _, d, _ in lista:
        if check_id is None:
            estados.append(d.get("estado"))
        else:
            r = next((x for x in d.get("resultados") or [] if x.get("id") == check_id), None)
            if r:
                estados.append(r.get("estado"))
    return round(sum(1 for s in estados if s != "Caído") / len(estados) * 100, 1) if estados else None


def build_html(datos, lista):
    res = datos.get("resultados") or []
    cambios = datos.get("cambios") or {}
    estado = datos.get("estado") or "—"
    body = []
    texto = {"OK": "Todo responde", "Degradado": "Responde, con problemas (lento o certificado por vencer)", "Caído": "Hay checks que fallan"}.get(estado, estado)
    if cambios.get("rompio"):
        texto += f" · se rompió: {', '.join(cambios['rompio'])}"
    if cambios.get("recupero"):
        texto += f" · se recuperó: {', '.join(cambios['recupero'])}"
    if cambios.get("anterior") and cambios["anterior"] != estado:
        texto += f" (antes: {cambios['anterior']})"
    body.append(banner(texto, TONO.get(estado, "warn")))

    urls = [r for r in res if r.get("tipo") in ("URL", "Escenario") and r.get("ms") is not None]
    prom = round(sum(r["ms"] for r in urls) / len(urls)) if urls else None
    disp = disponibilidad(lista)
    tls = [r for r in res if r.get("tipo") == "TLS" and r.get("dias_restantes") is not None]
    min_tls = min((r["dias_restantes"] for r in tls), default=None)
    ok = sum(1 for r in res if r.get("estado") != "Caído")
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Estado", estado, TONO.get(estado, ""), f'antes: {cambios.get("anterior") or "primera corrida"}', "rayo"),
        ("Checks que responden", f"{ok}/{len(res)}", "ok" if ok == len(res) else "bad", f'{sum(1 for r in res if r.get("estado") in ("Lento", "Por vencer"))} con advertencias', "lista"),
        ("Tiempo promedio", f"{prom} ms" if prom is not None else "—", "", "de las URLs y escenarios", "reloj"),
        ("Disponibilidad", f"{disp} %" if disp is not None else "—", "ok" if disp == 100 else ("warn" if disp and disp >= 95 else "bad"),
         f"en las últimas {len(lista)} corrida(s)", "escudo", {"pct": disp or 0}),
        ("Certificado", f"{min_tls} días" if min_tls is not None else "—", "warn" if min_tls is not None and any(r["estado"] != "OK" for r in tls) else "",
         "lo que falta para el vencimiento más cercano", "llave"),
    ]) + "</div>")

    filas = []
    for r in res:
        detalle = r.get("motivo") or ""
        if r.get("tipo") == "TLS" and r.get("vence"):
            detalle = (detalle + " · " if detalle else "") + f'vence {r["vence"][:10]}' + (f' · {r["emisor"]}' if r.get("emisor") else "")
        filas.append([pill(r.get("estado")), e(r.get("tipo")), f'<strong style="color:var(--ink)">{e(r.get("nombre"))}</strong><div class="muted mono">{e(r.get("url") or "")}</div>',
                      e(r.get("status") or "—"), e(f'{r["ms"]} ms' if r.get("ms") is not None else "—"), e(detalle or "—")])
    body.append(section("Checks", table(["Estado", "Tipo", "Check", "HTTP", "Tiempo", "Detalle"], filas)))
    if urls:
        body.append(section("Tiempos de respuesta", bar_chart([(r["nombre"][:60], r["ms"], COLOR.get(r["estado"], OK)) for r in urls], ancho_etiqueta=320),
                            "en milisegundos, de esta corrida"))

    if len(lista) >= 2:
        ids = [r["id"] for r in urls][:8]
        x = list(range(len(lista)))
        fx = lambda v: (lista[int(v)][1].get("fecha") or "")[5:16].replace("T", " ") if 0 <= int(v) < len(lista) else ""
        series = []
        for i, cid in enumerate(ids):
            valores = []
            for _, d, _ in lista:
                r = next((y for y in d.get("resultados") or [] if y.get("id") == cid), None)
                valores.append(r["ms"] if r and r.get("ms") is not None and r.get("estado") != "Caído" else 0)
            nombre = next(r["nombre"] for r in urls if r["id"] == cid)
            series.append((nombre[:40], SERIES[i % len(SERIES)], valores))
        if series:
            body.append(section("Tiempo de cada check en las corridas", line_chart(x, series, fmt_x=fx, alto=260), "0 = no respondió"))
        filas = []
        for r in res:
            marcas = "".join(
                f'<span title="{e((d.get("fecha") or "")[:16])}: {e(est)}" style="display:inline-block;width:12px;height:18px;margin-right:2px;border-radius:3px;background:{COLOR.get(est, NEUTRO)}"></span>'
                for _, d, _ in lista
                for est in [next((y.get("estado") for y in d.get("resultados") or [] if y.get("id") == r["id"]), None) or "—"])
            dp = disponibilidad(lista, r["id"])
            filas.append([e(r.get("nombre")), marcas, e(f"{dp} %" if dp is not None else "—")])
        body.append(section("Disponibilidad por check", table(["Check", "Corridas (de la más vieja a la actual)", "Disponibilidad"], filas)))
        filas = [[e((d.get("fecha") or "")[:16].replace("T", " ")), pill(d.get("estado")),
                  e(", ".join((d.get("cambios") or {}).get("rompio") or []) or "—"), e(", ".join((d.get("cambios") or {}).get("recupero") or []) or "—"),
                  f'<a href="{e(inf)}">ver informe</a>' if inf else ("esta corrida" if sello == "actual" else "—")]
                 for sello, d, inf in reversed(lista)]
        body.append(section("Corridas", table(["Fecha", "Estado", "Se rompió", "Se recuperó", "Informe"], filas)))

    m = meta([("Monitoreo", datos.get("nombre")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
              ("Duración", f'{round((datos.get("duracion_ms") or 0) / 1000, 1)} s')])
    return page("Monitoreo sintético", "Monitoreo sintético", m, "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de monitoreo sintético a partir de monitoreo.json")
    ap.add_argument("datos_json")
    ap.add_argument("salida")
    a = ap.parse_args()
    if not a.salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    datos = json.loads(Path(a.datos_json).read_text(encoding="utf-8"))
    lista = corridas(Path(a.datos_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, lista))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

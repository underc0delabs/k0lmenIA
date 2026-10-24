#!/usr/bin/env python3
"""
Tablero de calidad (agente tablero-calidad): junta lo que ya dejaron las herramientas de k0lmenIA y arma
un tablero por sprint, release o rango de fechas.

Uso (desde la raíz del repo):
    python scripts/tablero_calidad.py [--nombre sprint-12] [--desde 2026-10-01] [--hasta 2026-10-14]
    python scripts/tablero_calidad.py --solo-informe --nombre sprint-12 --analisis output/tablero/sprint-12/analisis.json

Fuentes (las que existan; lo que falta se informa en "sin_datos", nunca se inventa):
  - Ejecuciones en vivo: output/ejecuciones/_resultados-*.json
  - npm test: herramientas/k0lmena/reports/{web,api,mobile}/cucumber-report.json y su historial/
  - Inventario de casos (manuales, BDD y automatizados en k0lmena) con su último resultado, los inestables,
    los bugs abiertos y el tiempo estimado de ejecución manual (el mismo de seleccionar_casos.py). Con eso
    calcula el ahorro al automatizar: lo que costaría correr a mano los casos automatizados menos lo que
    tardan corriendo solos (ahorro por corrida y acumulado en el período).
  - Cobertura de criterios: output/cobertura/*/cobertura.json (el más reciente)
  - Bugs: output/reportes-bug/BUG-*.md (severidad, estado e historia)
  - Fallos e inestables: output/fallos/*/fallos.json (el más reciente)
  - Accesibilidad, rendimiento web, performance y seguridad: sus JSON en output/

--desde / --hasta (AAAA-MM-DD, inclusive) filtran las corridas, los resultados y los bugs reportados en
el período; el inventario, la cobertura y los bugs abiertos son siempre la foto actual.

Deja en output/tablero/<nombre>/: tablero.json (los datos) e informe-tablero.html. La corrida anterior con
el mismo nombre pasa a historial/ (últimas 5) y el informe muestra la evolución.

analisis.json (opcional, lo escribe el agente):
{
  "veredicto": "La calidad del sprint es aceptable con dos riesgos",
  "veredicto_tono": "ok | warn | bad",
  "resumen": "Texto corto para gerencia: dónde estamos, qué cambió, qué preocupa",
  "riesgos": [{"riesgo": "...", "impacto": "...", "nivel": "Alta"}],
  "recomendaciones": [{"accion": "...", "porque": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."],
  "notas": {"<indicador o historia>": "comentario"}
}
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _historial  # noqa: E402
from _i18n import escribir_bilingue, localizar, idioma_actual  # noqa: E402
import recolectar_resultados as rec  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
GENERADOS = ["tablero.json", "analisis.json", "informe-tablero.html", "informe-tablero.en.html"]
SEVERIDADES = rec.SEVERIDADES
SUITES = ("web", "api", "mobile")


def usar_raiz(raiz):
    """Apunta el tablero (y los lectores que reutiliza) a otra raíz; lo usan los tests."""
    global RAIZ
    RAIZ = Path(raiz)
    rec.RAIZ = RAIZ
    rec.K0 = RAIZ / "herramientas" / "k0lmena" / "reports"
    try:
        import seleccionar_casos as sc
        sc.RAIZ = RAIZ
    except Exception:
        pass


# ------------------------------------------------------------------ fechas
def _ts(texto):
    if not texto:
        return None
    t = str(texto).strip()
    try:
        return datetime.fromisoformat(t.replace(" ", "T")[:19]).timestamp()
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(t, fmt).timestamp()
        except ValueError:
            continue
    return None


def rango(desde=None, hasta=None):
    d = datetime.strptime(desde, "%Y-%m-%d").timestamp() if desde else None
    h = (datetime.strptime(hasta, "%Y-%m-%d") + timedelta(days=1)).timestamp() if hasta else None
    return d, h


def _en(ts, r):
    if ts is None:
        return r == (None, None)
    return (r[0] is None or ts >= r[0]) and (r[1] is None or ts < r[1])


def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _fmt(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else ""


# ------------------------------------------------------------------ fuentes
def _estado_escenario(esc):
    estados = [(p.get("result") or {}).get("status", "undefined") for p in esc.get("steps", [])]
    if any(s in ("failed", "ambiguous") for s in estados):
        return "Fallido"
    if estados and all(s == "passed" for s in estados):
        return "Aprobado"
    return "Bloqueado"


def corridas(r):
    """Cada corrida (ejecución en vivo o npm test por suite, con su historial) dentro del rango."""
    salida = []
    for arch in sorted(glob.glob(str(RAIZ / "output" / "ejecuciones" / "_resultados-*.json"))):
        d = _json(arch)
        if not isinstance(d, dict):
            continue
        ts = _ts(d.get("fecha")) or os.path.getmtime(arch)
        cuenta = Counter(rec._estado(c.get("estado")) for c in d.get("casos") or [])
        salida.append({"ts": ts, "fuente": "en vivo", "historia": (d.get("historia") or "").upper(), "cuenta": cuenta})
    k0 = RAIZ / "herramientas" / "k0lmena" / "reports"
    for suite in SUITES:
        archivos = [k0 / suite / "cucumber-report.json"] + sorted((k0 / suite / "historial").glob("*/cucumber-report.json"))
        for arch in archivos:
            d = _json(arch) if arch.exists() else None
            if not isinstance(d, list) or not d:
                continue
            cuenta = Counter(_estado_escenario(esc) for f in d for esc in f.get("elements", []) if esc.get("type") != "background")
            salida.append({"ts": os.path.getmtime(arch), "fuente": f"npm test · {suite}", "historia": "", "cuenta": cuenta})
    out = []
    for c in sorted(salida, key=lambda c: c["ts"]):
        if not _en(c["ts"], r) and r != (None, None):
            continue
        n = sum(c["cuenta"].values())
        if not n:
            continue
        out.append({"fecha": _fmt(c["ts"]), "fuente": c["fuente"], "historia": c["historia"], "total": n,
                    "aprobados": c["cuenta"]["Aprobado"], "fallidos": c["cuenta"]["Fallido"], "bloqueados": c["cuenta"]["Bloqueado"],
                    "pct_aprobados": round(c["cuenta"]["Aprobado"] / n * 100, 1)})
    return out


def resultados_periodo(r):
    """Último resultado de cada caso (historia + id) ejecutado dentro del rango (en vivo y npm test con su historial)."""
    ultimo = {}
    for x in sorted(rec.de_ejecuciones(None) + rec.de_cucumber(None), key=lambda x: x["momento"]):
        if r == (None, None) or _en(x["momento"], r):
            ultimo[rec.clave_caso(x)] = x  # historia + id: los CP se numeran por historia
    return Counter(x["estado"] for x in ultimo.values())


def inventario():
    try:
        import seleccionar_casos as sc
        sc.RAIZ = RAIZ
        return sc.inventario()
    except Exception as ex:  # una planilla rara no corta el tablero
        print(f"[!] No pude armar el inventario de casos ({ex}).", file=sys.stderr)
        return []


def _mas_reciente(patron):
    archivos = sorted(glob.glob(str(RAIZ / patron)), key=os.path.getmtime)
    return Path(archivos[-1]) if archivos else None


def cobertura():
    arch = _mas_reciente("output/cobertura/*/cobertura.json")
    d = _json(arch) if arch else None
    if not isinstance(d, dict):
        return None
    por_hu = {}
    for h in d.get("historias") or []:
        m = h.get("metricas") or {}
        if m.get("criterios"):
            por_hu[h.get("historia")] = round(m.get("criterios_cubiertos", 0) / m["criterios"] * 100)
    return {"archivo": arch.relative_to(RAIZ).as_posix(), "pct": _historial._cob_pct(d),
            "huecos": len(_historial._huecos(d)), "por_historia": por_hu}


def bugs(r):
    lista = rec.de_bugs(None)
    archivos = {Path(a).stem: os.path.getmtime(a) for a in glob.glob(str(RAIZ / "output" / "reportes-bug" / "BUG-*.md"))}
    for b in lista:
        b["ts"] = archivos.get(b["id"]) or next((t for k, t in archivos.items() if k.startswith(b["id"])), None)
    abiertos = [b for b in lista if b["estado"].lower() in rec.ABIERTOS]
    del_periodo = [b for b in lista if r == (None, None) or _en(b["ts"], r)]
    return {
        "total": len(lista), "abiertos": len(abiertos),
        "reportados_periodo": len(del_periodo),
        "por_severidad": {s: sum(1 for b in abiertos if b["severidad"] == s) for s in SEVERIDADES},
        "por_historia": dict(Counter(b["historia"] for b in abiertos).most_common()),
        "criticos_abiertos": [{k: b[k] for k in ("id", "titulo", "severidad", "historia")} for b in abiertos
                              if b["severidad"] in ("Crítica", "Alta")],
    }


def fallos():
    arch = _mas_reciente("output/fallos/*/fallos.json")
    d = _json(arch) if arch else None
    if not isinstance(d, dict):
        return None
    pc = (d.get("resumen") or {}).get("por_categoria") or {}
    return {"archivo": arch.relative_to(RAIZ).as_posix(), "fallidos": (d.get("resumen") or {}).get("fallidos", 0),
            "inestables": pc.get("Inestable (flaky)", 0), "posibles_bugs": pc.get("Posible bug", 0), "por_categoria": pc}


def extras():
    out = {"accesibilidad": [], "rendimiento": [], "performance": rec.de_performance(None), "seguridad": rec.de_seguridad(None)}
    for arch in sorted(glob.glob(str(RAIZ / "output" / "accesibilidad" / "*" / "auditoria.json"))):
        d = _json(arch) or {}
        r = d.get("resumen") or {}
        if r.get("cumplimiento_pct") is not None:
            out["accesibilidad"].append({"sitio": Path(arch).parent.name, "cumplimiento": r.get("cumplimiento_pct"),
                                         "criticos": r.get("criticos", 0)})
    for arch in sorted(glob.glob(str(RAIZ / "output" / "rendimiento" / "*" / "rendimiento.json"))):
        r = (_json(arch) or {}).get("resumen") or {}
        if r.get("rendimiento_mobile") is not None or r.get("rendimiento_desktop") is not None:
            out["rendimiento"].append({"sitio": Path(arch).parent.name, "mobile": r.get("rendimiento_mobile"),
                                       "desktop": r.get("rendimiento_desktop")})
    # Uso de tokens (scripts/metricas_tokens.py): el informe más reciente de cada nombre.
    out["tokens"] = []
    for arch in sorted(glob.glob(str(RAIZ / "output" / "metricas-tokens" / "*" / "metricas.json"))):
        d = _json(arch) or {}
        r = d.get("resumen") or {}
        if r.get("llamadas"):
            top = (d.get("agentes") or [{}])[0]
            out["tokens"].append({"nombre": Path(arch).parent.name, "periodo": d.get("periodo", ""), "costo_usd": r.get("costo_usd", 0),
                                  "pct_cache": r.get("pct_cache", 0), "agente_top": top.get("agente", "—")})
    return out


# ------------------------------------------------------------------ armado
def recolectar(desde=None, hasta=None):
    r = rango(desde, hasta)
    corr = corridas(r)
    periodo = resultados_periodo(r)
    casos = inventario()
    cob = cobertura()
    bg = bugs(r)
    fl = fallos()
    ex = extras()

    automatizados = [c for c in casos if c.get("automatizado")]
    con_resultado = [c for c in casos if c.get("resultado")]
    inestables = [f'{c["historia"]}:{c["id"]}' for c in casos if c.get("inestable")]
    manuales = [c for c in casos if not c.get("automatizado")]
    ejecutados = sum(periodo.values())

    historias = {}
    for c in casos:
        h = historias.setdefault(c["historia"], {"historia": c["historia"], "casos": 0, "automatizados": 0, "aprobados": 0,
                                                 "fallidos": 0, "bloqueados": 0, "sin_ejecutar": 0, "inestables": 0,
                                                 "minutos_manual": 0, "minutos_automatizado": 0, "minutos_corrida_auto": 0})
        h["casos"] += 1
        h["automatizados"] += bool(c.get("automatizado"))
        est = (c.get("resultado") or {}).get("estado")
        h[{"Aprobado": "aprobados", "Fallido": "fallidos", "Bloqueado": "bloqueados"}.get(est, "sin_ejecutar")] += 1
        h["inestables"] += bool(c.get("inestable"))
        if c.get("automatizado"):
            # Lo que costaría a mano y ahora corre solo (ahorro por corrida), y lo que tardó automatizado.
            h["minutos_automatizado"] += c.get("minutos_manual") or 0
            h["minutos_corrida_auto"] += (c.get("duracion_s") or 0) / 60
        else:
            h["minutos_manual"] += c.get("minutos_manual") or 0
    for hu, h in historias.items():
        h["bugs_abiertos"] = bg["por_historia"].get(hu, 0)
        h["cobertura"] = (cob or {}).get("por_historia", {}).get(hu)
        h["minutos_manual"] = round(h["minutos_manual"], 1)
        h["minutos_automatizado"] = round(h["minutos_automatizado"], 1)
        h["minutos_corrida_auto"] = round(h["minutos_corrida_auto"], 1)
        h["ahorro_por_corrida"] = round(max(0, h["minutos_automatizado"] - h["minutos_corrida_auto"]), 1)

    resumen = {
        "casos": len(casos), "historias": len(historias),
        "automatizados": len(automatizados),
        "pct_automatizado": round(len(automatizados) / len(casos) * 100) if casos else None,
        "ejecutados_periodo": ejecutados,
        "aprobados_periodo": periodo.get("Aprobado", 0), "fallidos_periodo": periodo.get("Fallido", 0),
        "bloqueados_periodo": periodo.get("Bloqueado", 0),
        "pct_aprobados": round(periodo.get("Aprobado", 0) / ejecutados * 100) if ejecutados else None,
        "sin_ejecutar": len(casos) - len(con_resultado),
        "cobertura_pct": (cob or {}).get("pct"),
        "bugs_abiertos": bg["abiertos"], "bugs_criticos_abiertos": len(bg["criticos_abiertos"]),
        "inestables": len(inestables) or (fl or {}).get("inestables", 0),
        "minutos_manual": round(sum(c.get("minutos_manual") or 0 for c in manuales), 1),
        # Ahorro al automatizar: lo que costaría ejecutar a mano los casos automatizados, menos lo que
        # tardan corriendo solos. Es por corrida (cada vez que se corre npm test se ahorra ese tiempo).
        "minutos_automatizado": round(sum(c.get("minutos_manual") or 0 for c in automatizados), 1),
        "minutos_corrida_auto": round(sum((c.get("duracion_s") or 0) / 60 for c in automatizados), 1),
        "corridas": len(corr),
    }
    resumen["ahorro_por_corrida"] = round(max(0, resumen["minutos_automatizado"] - resumen["minutos_corrida_auto"]), 1)
    # Ahorro acumulado estimado: el ahorro por corrida por las corridas del período.
    resumen["ahorro_acumulado"] = round(resumen["ahorro_por_corrida"] * len(corr), 1)
    if len(corr) >= 2:
        mitad = len(corr) // 2
        prom = lambda xs: sum(x["pct_aprobados"] for x in xs) / len(xs)
        resumen["tendencia_pp"] = round(prom(corr[mitad:]) - prom(corr[:mitad]), 1)

    sin_datos = []
    if not corr:
        sin_datos.append("Corridas (ni ejecuciones en vivo ni npm test en el período)")
    if not casos:
        sin_datos.append("Inventario de casos (no hay planillas, .feature de BDD ni automatización)")
    if not cob:
        sin_datos.append("Cobertura de criterios (falta correr el analista-cobertura)")
    if not bg["total"]:
        sin_datos.append("Bugs (no hay reportes en output/reportes-bug/)")
    if not fl:
        sin_datos.append("Análisis de fallos e inestables (falta correr el analista-fallos)")
    for clave, texto in (("accesibilidad", "Accesibilidad"), ("rendimiento", "Rendimiento web"),
                         ("performance", "Performance"), ("seguridad", "Seguridad")):
        if not ex[clave]:
            sin_datos.append(texto)

    alertas = []
    for b in bg["criticos_abiertos"]:
        alertas.append({"tipo": "Bug abierto", "nivel": b["severidad"], "titulo": f'{b["id"]} ({b["historia"]}): {b["titulo"]}'})
    for i in inestables:
        alertas.append({"tipo": "Inestable", "nivel": "Media", "titulo": f"{i} · falla de forma intermitente"})
    for h in historias.values():
        if h["fallidos"]:
            alertas.append({"tipo": "Fallidos", "nivel": "Alta", "titulo": f'{h["historia"]}: {h["fallidos"]} caso(s) fallidos en la última ejecución'})
        if h["casos"] >= 3 and not h["automatizados"]:
            alertas.append({"tipo": "Sin automatizar", "nivel": "Baja", "titulo": f'{h["historia"]}: ningún caso automatizado ({h["casos"]} casos)'})
        if h["cobertura"] is not None and h["cobertura"] < 80:
            alertas.append({"tipo": "Cobertura", "nivel": "Media", "titulo": f'{h["historia"]}: {h["cobertura"]} % de criterios cubiertos'})
    for a in ex["accesibilidad"]:
        if a.get("criticos"):
            alertas.append({"tipo": "Accesibilidad", "nivel": "Alta", "titulo": f'{a["sitio"]} · {a["criticos"]} problema(s) crítico(s)'})

    return {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "periodo": {"desde": desde, "hasta": hasta},
        "resumen": resumen, "corridas": corr,
        "historias": sorted(historias.values(), key=lambda h: h["historia"]),
        "bugs": bg, "cobertura": cob, "fallos": fl, "extras": ex,
        "inestables": inestables, "alertas": alertas, "sin_datos": sin_datos,
    }


# ------------------------------------------------------------------ informe
def build_html(datos, analisis=None, hist_html=""):
    from _estilos_reporte import (page, meta, section, kpi_tiles, table, banner, line_chart, donut_panel, bar_chart,
                                  stacked_bars, two_col, doc_list, nivel_badge, e, SERIES, OK, CRITICO, NEUTRO, AVISO, NIVEL_COLOR)
    analisis = analisis or {}
    r = datos["resumen"]
    p = datos.get("periodo") or {}
    periodo = (f'{p.get("desde") or "el inicio"} al {p.get("hasta") or "hoy"}') if (p.get("desde") or p.get("hasta")) else "todo lo registrado"
    pct = lambda v: "—" if v is None else f"{v} %"

    def fmt_min(m):
        """Minutos → "45 min" o "2 h 30 min" para que el ahorro se lea de un vistazo."""
        m = int(round(m or 0))
        if m < 60:
            return f"{m} min"
        h, r_ = divmod(m, 60)
        return f"{h} h {r_} min" if r_ else f"{h} h"

    body = []

    malos = r["bugs_criticos_abiertos"] or r["fallidos_periodo"]
    tono = analisis.get("veredicto_tono") or ("bad" if r["bugs_criticos_abiertos"] else "warn" if malos or r["inestables"] else "ok")
    texto = analisis.get("veredicto") or (
        f'{pct(r["pct_aprobados"])} de aprobados en el período, {pct(r["pct_automatizado"])} automatizado, '
        f'{r["bugs_abiertos"]} bug(s) abiertos ({r["bugs_criticos_abiertos"]} críticos o altos).')
    body.append(banner(texto, tono))
    serie = [c["pct_aprobados"] for c in datos["corridas"]][-12:]
    tend = r.get("tendencia_pp")
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Aprobados (período)", pct(r["pct_aprobados"]), "ok" if (r["pct_aprobados"] or 0) >= 95 else "warn" if (r["pct_aprobados"] or 0) >= 80 else "bad" if r["pct_aprobados"] is not None else "",
         f'{r["aprobados_periodo"]} de {r["ejecutados_periodo"]} casos' + (f' · tendencia {tend:+} pp' if tend is not None else ""), "ok",
         {"serie": serie} if len(serie) > 1 else {"pct": r["pct_aprobados"] or 0}),
        ("Automatizado", pct(r["pct_automatizado"]), "", f'{r["automatizados"]} de {r["casos"]} casos', "rayo", {"pct": r["pct_automatizado"] or 0}),
        ("Cobertura de criterios", pct(r["cobertura_pct"]), "ok" if (r["cobertura_pct"] or 0) >= 90 else "warn" if r["cobertura_pct"] is not None else "",
         f'{(datos.get("cobertura") or {}).get("huecos", 0)} hueco(s)' if datos.get("cobertura") else "sin análisis de cobertura", "objetivo",
         {"pct": r["cobertura_pct"] or 0}),
        ("Bugs abiertos", r["bugs_abiertos"], "bad" if r["bugs_criticos_abiertos"] else "warn" if r["bugs_abiertos"] else "ok",
         f'{r["bugs_criticos_abiertos"]} críticos o altos · {datos["bugs"]["reportados_periodo"]} reportados en el período', "bicho"),
        ("Inestables", r["inestables"], "warn" if r["inestables"] else "ok", "fallan de forma intermitente", "warn"),
        ("Sin ejecutar", r["sin_ejecutar"], "warn" if r["sin_ejecutar"] else "", "casos sin ningún resultado", "lista"),
        ("Ejecución manual pendiente", fmt_min(r["minutos_manual"]), "", "lo que no está automatizado", "persona"),
        ("Ahorro por corrida", fmt_min(r.get("ahorro_por_corrida")), "ok" if r.get("ahorro_por_corrida") else "",
         f'{fmt_min(r.get("minutos_automatizado"))} a mano vs {fmt_min(r.get("minutos_corrida_auto"))} automatizado', "rayo"),
        ("Ahorro acumulado", fmt_min(r.get("ahorro_acumulado")), "ok" if r.get("ahorro_acumulado") else "",
         f'{r["corridas"]} corrida(s) en el período', "objetivo"),
        ("Corridas", r["corridas"], "", "en vivo y npm test en el período", "lista"),
    ]) + "</div>")

    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))

    corr = datos["corridas"]
    if corr:
        etiquetas = [c["fecha"][5:16] for c in corr]
        grafico = line_chart(list(range(len(corr))), [("% aprobados", SERIES[0], [c["pct_aprobados"] for c in corr])],
                             fmt=lambda v: f"{v:.0f} %", fmt_x=lambda v: etiquetas[min(len(etiquetas) - 1, max(0, int(round(v))))])
        body.append(section("Tendencia de aprobados", grafico, f"{len(corr)} corrida(s) · {periodo}"))

    tot = r["aprobados_periodo"] + r["fallidos_periodo"] + r["bloqueados_periodo"]
    dona = (donut_panel([(r["aprobados_periodo"], OK, "Aprobados"), (r["fallidos_periodo"], CRITICO, "Fallidos"),
                         (r["bloqueados_periodo"], NEUTRO, "Bloqueados")], round(r["aprobados_periodo"] / tot * 100) if tot else 0, "aprobados")
            if tot else '<div class="cardbody"><p class="muted">No hay resultados en el período.</p></div>')
    sev = datos["bugs"]["por_severidad"]
    barras_sev = bar_chart([(s, sev.get(s, 0), NIVEL_COLOR.get(s, NEUTRO)) for s in SEVERIDADES])
    body.append(two_col(section("Resultados del período", dona, periodo, ancho=6),
                        section("Bugs abiertos por severidad", barras_sev, f'{datos["bugs"]["abiertos"]} abiertos de {datos["bugs"]["total"]}', ancho=6)))

    hs = datos["historias"]
    if hs:
        filas = [(h["historia"], [h["aprobados"], h["fallidos"], h["bloqueados"], h["sin_ejecutar"]]) for h in hs][:20]
        body.append(section("Último resultado por historia", stacked_bars(filas, [("Aprobados", OK), ("Fallidos", CRITICO),
                                                                                 ("Bloqueados", NEUTRO), ("Sin ejecutar", AVISO)])))
        notas = analisis.get("notas") or {}
        body.append(section("Detalle por historia", table(
            ["Historia", "Casos", "Automatizados", "Aprobados", "Fallidos", "Sin ejecutar", "Inestables", "Bugs abiertos", "Cobertura", "Manual pendiente", "Ahorro/corrida", "Nota"],
            [[f'<b>{e(h["historia"])}</b>', h["casos"], f'{h["automatizados"]} ({round(h["automatizados"] / h["casos"] * 100) if h["casos"] else 0} %)',
              h["aprobados"], h["fallidos"], h["sin_ejecutar"], h["inestables"], h["bugs_abiertos"],
              "—" if h["cobertura"] is None else f'{h["cobertura"]} %', fmt_min(h["minutos_manual"]),
              fmt_min(h.get("ahorro_por_corrida")), e(notas.get(h["historia"], ""))] for h in hs])))

    if datos["alertas"]:
        orden = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
        body.append(section("Alertas", table(["Nivel", "Tipo", "Detalle"],
                                             [[nivel_badge(a["nivel"]), e(a["tipo"]), e(a["titulo"])]
                                              for a in sorted(datos["alertas"], key=lambda a: orden.get(a["nivel"], 9))]),
                            "generadas desde los datos, sin interpretación"))

    ex = datos["extras"]
    otros = []
    if ex["accesibilidad"]:
        otros.append(section("Accesibilidad", table(["Sitio", "Cumplimiento", "Críticos"],
                                                     [[e(a["sitio"]), f'{a["cumplimiento"]} %', a["criticos"]] for a in ex["accesibilidad"]]), ancho=6))
    if ex["rendimiento"]:
        otros.append(section("Rendimiento web (Lighthouse)", table(["Sitio", "Mobile", "Desktop"],
                                                                    [[e(x["sitio"]), x["mobile"] if x["mobile"] is not None else "—",
                                                                      x["desktop"] if x["desktop"] is not None else "—"] for x in ex["rendimiento"]]), ancho=6))
    if ex["performance"]:
        otros.append(section("Performance", table(["Informe", "Veredicto", "Corridas"],
                                                   [[e(x["informe"]), e(x["veredicto"]), x["corridas"]] for x in ex["performance"]]), ancho=6))
    if ex["seguridad"]:
        otros.append(section("Seguridad (ZAP)", table(["Escaneo", "Alto", "Medio", "Bajo"],
                                                       [[e(x["escaneo"]), x["hallazgos"]["Alto"], x["hallazgos"]["Medio"], x["hallazgos"]["Bajo"]]
                                                        for x in ex["seguridad"]]), ancho=6))
    if ex.get("tokens"):
        otros.append(section("Uso de tokens", table(["Métricas", "Período", "Costo estimado", "Caché", "Agente que más gasta"],
                                                     [[e(x["nombre"]), e(x["periodo"]), f'${x["costo_usd"]:,.2f}', f'{x["pct_cache"]:.0f} %',
                                                       e(x["agente_top"])] for x in ex["tokens"]]), "scripts/metricas_tokens.py", ancho=6))
    for i in range(0, len(otros), 2):
        body.append(two_col(*otros[i:i + 2]) if i + 1 < len(otros) else otros[i])

    if analisis.get("riesgos"):
        body.append(section("Riesgos", table(["Nivel", "Riesgo", "Impacto"],
                                             [[nivel_badge(x.get("nivel")), e(x.get("riesgo")), e(x.get("impacto"))] for x in analisis["riesgos"]])))
    if analisis.get("recomendaciones"):
        body.append(section("Recomendaciones", table(["Prioridad", "Acción", "Por qué"],
                                                     [[nivel_badge(x.get("prioridad")), e(x.get("accion")), e(x.get("porque"))]
                                                      for x in analisis["recomendaciones"]])))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    if datos["sin_datos"]:
        body.append(section("Sin datos", doc_list(datos["sin_datos"]), "fuentes que no tienen información: no se estiman"))
    if hist_html:
        body.append(hist_html)
    return page("Tablero de calidad", "Tablero", meta([("Período", periodo), ("Generado", datos["fecha"][:16].replace("T", " ")),
                                                       ("Historias", r["historias"]), ("Casos", r["casos"])]), "".join(body))


def escribir_informe(carpeta, datos, analisis=None):
    hist = _historial.seccion("tablero", carpeta, datos)
    # ES y EN: el inglés del agente va en el bloque "en" del analisis.json.
    escribir_bilingue(carpeta / "informe-tablero.html", lambda: build_html(datos, localizar(analisis) if analisis else analisis, hist))


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Tablero de calidad por sprint, release o rango de fechas")
    ap.add_argument("--nombre", help="nombre del tablero (sprint-12, release-2.4…); por defecto, el rango o 'general'")
    ap.add_argument("--desde", help="AAAA-MM-DD (inclusive)")
    ap.add_argument("--hasta", help="AAAA-MM-DD (inclusive)")
    ap.add_argument("--analisis", help="analisis.json del agente (resumen ejecutivo, riesgos, recomendaciones)")
    ap.add_argument("--solo-informe", action="store_true", help="regenera el informe con los datos ya juntados")
    ap.add_argument("--raiz", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    for f in (a.desde, a.hasta):
        if f and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", f):
            sys.exit("--desde y --hasta van como AAAA-MM-DD")
    if a.raiz:
        usar_raiz(a.raiz)
    nombre = a.nombre or ("-".join(x for x in (a.desde, a.hasta) if x) or "general")
    nombre = re.sub(r"[^\w.-]+", "-", nombre).strip("-") or "general"
    carpeta = RAIZ / "output" / "tablero" / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    analisis = _json(a.analisis) if a.analisis else None
    if a.analisis and analisis is None:
        sys.exit(f"No pude leer {a.analisis}")
    if a.solo_informe:
        datos = _json(carpeta / "tablero.json")
        if not datos:
            sys.exit(f"No hay datos en {carpeta}: corré primero sin --solo-informe")
    else:
        _historial.archivar(carpeta, GENERADOS, "tablero.json")
        datos = recolectar(a.desde, a.hasta)
        datos["nombre"] = nombre
        (carpeta / "tablero.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    if analisis is not None:
        (carpeta / "analisis.json").write_text(json.dumps(analisis, ensure_ascii=False, indent=2), encoding="utf-8")
    escribir_informe(carpeta, datos, analisis)
    r = datos["resumen"]
    pct = lambda v: "—" if v is None else f"{v} %"
    print(f"Tablero {nombre}: {pct(r['pct_aprobados'])} aprobados · {pct(r['pct_automatizado'])} automatizado · "
          f"cobertura {pct(r['cobertura_pct'])} · {r['bugs_abiertos']} bugs abiertos ({r['bugs_criticos_abiertos']} críticos o altos) · "
          f"{r['inestables']} inestables")
    if datos["sin_datos"]:
        print("Sin datos: " + "; ".join(datos["sin_datos"]))
    print(f"Informe: {(carpeta / 'informe-tablero.html').relative_to(RAIZ).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

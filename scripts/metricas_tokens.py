#!/usr/bin/env python3
"""
Métricas de uso de tokens de los agentes de k0lmenIA.

Uso (desde la raíz del repo):
    python scripts/metricas_tokens.py [--nombre <nombre>] [--desde AAAA-MM-DD] [--hasta AAAA-MM-DD]
                                      [--carpeta <transcripciones>] [--salida <carpeta>]
    npm run metricas

De dónde salen los datos: Claude Code guarda cada sesión en ~/.claude/projects/<ruta del repo>/ como
<sesion>.jsonl (la conversación principal) y <sesion>/subagents/agent-<id>.jsonl + .meta.json (cada
subagente, con su agentType: analista-historias, generador-casos-manuales, …). Cada respuesta del
modelo trae message.usage (input_tokens, output_tokens, cache_creation_input_tokens con el detalle 5m/1h,
cache_read_input_tokens) y message.model. Una misma respuesta aparece en varias líneas (una por bloque):
se cuenta una sola vez por message.id.

Se atribuye el uso a cada agente (los subagentes por su tipo; lo demás a "conversación principal") y se
agrega por agente, por día y por modelo: llamadas, tokens (entrada, salida, escritura y lectura de caché),
% de caché y costo estimado con la tabla PRECIOS. Si están, suma los costos de los evals
(evals/resultados/*/resultados.json). Además señala oportunidades: los agentes que más gastan, los que se
usan muchas veces (candidatos a automatizar en k0lmena, que corre sin tokens) y la caché baja.

Privacidad: nunca lee, guarda ni muestra el texto de los mensajes; solo conteos, modelos y nombres de agentes.

Deja output/metricas-tokens/<nombre>/ con metricas.json e informe-metricas.html; la corrida anterior pasa
a historial/ (últimas 5).
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

# ------------------------------------------------------------------ precios
# USD por millón de tokens. Fuente: tabla de modelos de la documentación de la API de Claude (skill
# claude-api, caché del 2026-10-06). Escritura de caché: ×1,25 la entrada (5 minutos) y ×2 (1 hora);
# lectura: el valor publicado si lo hay, si no ×0,1 la entrada. Editá esta tabla si cambian los precios.
# Haiku 5.5 cobra más arriba de 100K tokens de prompt ($0,50 / $2,50): acá se usa el precio base.
PRECIOS_FECHA = "2026-10-06"
_P = {  # modelo: (entrada, salida, lectura de caché o None)
    "claude-fable-5-1": (10.00, 50.00, 0.25), "claude-mythos-5-1": (10.00, 50.00, 0.25),
    "claude-fable-5": (10.00, 50.00, None), "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-opus-5": (5.00, 25.00, None), "claude-opus-4-8": (5.00, 25.00, None), "claude-opus-4-7": (5.00, 25.00, None),
    "claude-opus-4-6": (5.00, 25.00, None), "claude-sonnet-5-5": (2.00, 10.00, 0.20), "claude-sonnet-5": (2.00, 10.00, None),
    "claude-sonnet-4-6": (3.00, 15.00, None), "claude-haiku-5-5": (0.10, 0.50, None), "claude-haiku-4-5": (1.00, 5.00, None),
}
PRECIOS = {m: {"entrada": e, "salida": s, "cache_5m": e * 1.25, "cache_1h": e * 2.0, "cache_lectura": r if r is not None else e * 0.1}
           for m, (e, s, r) in _P.items()}
GENERADOS = ["metricas.json", "informe-metricas.html"]
PRINCIPAL = "conversación principal"
# Un agente usado esta cantidad de veces o más en el período es candidato a automatizar.
UMBRAL_REPETIDO = 5


def precio_de(modelo):
    """Precio del modelo (acepta sufijos como [1m] o fechas); None si no está en la tabla."""
    m = re.sub(r"\[.*?\]$", "", modelo or "")
    if m in PRECIOS:
        return PRECIOS[m]
    for k in sorted(PRECIOS, key=len, reverse=True):
        if m.startswith(k):
            return PRECIOS[k]
    return None


def costo(uso, modelo):
    """Costo estimado en USD de un uso, o None si el modelo no tiene precio."""
    p = precio_de(modelo)
    if not p:
        return None
    return (uso["entrada"] * p["entrada"] + uso["salida"] * p["salida"] + uso["cache_5m"] * p["cache_5m"]
            + uso["cache_1h"] * p["cache_1h"] + uso["cache_lectura"] * p["cache_lectura"]) / 1_000_000


def carpeta_transcripciones(raiz=RAIZ):
    """~/.claude/projects/<ruta con barras y dos puntos cambiados por guiones>: la del repo o, si Claude Code
    se abrió en una carpeta que lo contiene, la de esa carpeta."""
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "projects"
    existentes = {d.name.lower(): d for d in base.glob("*")} if base.is_dir() else {}
    ruta = Path(raiz).resolve()
    for r in [ruta, *ruta.parents]:
        nombre = re.sub(r"[\\/:]", "-", str(r)).rstrip("-")
        if nombre.lower() in existentes:
            return existentes[nombre.lower()]
    return base / re.sub(r"[\\/:]", "-", str(ruta))


def _uso_de(usage):
    cc = usage.get("cache_creation") or {}
    total_cc = int(usage.get("cache_creation_input_tokens") or 0)
    h1 = int(cc.get("ephemeral_1h_input_tokens") or 0)
    m5 = int(cc.get("ephemeral_5m_input_tokens") or 0) or max(0, total_cc - h1)
    return {"entrada": int(usage.get("input_tokens") or 0), "salida": int(usage.get("output_tokens") or 0),
            "cache_5m": m5, "cache_1h": h1, "cache_lectura": int(usage.get("cache_read_input_tokens") or 0)}


def leer_transcripcion(archivo):
    """[(timestamp, modelo, uso, herramientas usadas)] por respuesta (una vez por message.id)."""
    respuestas = {}
    try:
        fh = open(archivo, encoding="utf-8")
    except OSError:
        return []
    with fh:
        for linea in fh:
            if '"assistant"' not in linea:
                continue
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            if d.get("type") != "assistant":
                continue
            m = d.get("message") or {}
            usage = m.get("usage")
            if not usage or m.get("model") in (None, "<synthetic>"):
                continue
            clave = m.get("id") or d.get("uuid")
            previa = respuestas.get(clave)
            herr = set(previa[3]) if previa else set()
            for bloque in m.get("content") or []:
                if isinstance(bloque, dict) and bloque.get("type") == "tool_use":
                    herr.add(str(bloque.get("name")))
            respuestas[clave] = (d.get("timestamp") or "", m.get("model"), _uso_de(usage), sorted(herr))
    return list(respuestas.values())


def recolectar(carpeta, desde=None, hasta=None):
    """Registros por respuesta: [{"agente", "sesion", "invocacion", "fecha", "modelo", "uso", "herramientas"}]."""
    carpeta = Path(carpeta)
    registros = []
    for sesion in sorted(carpeta.glob("*.jsonl")):
        fuentes = [(sesion, PRINCIPAL, sesion.stem)]
        sub = carpeta / sesion.stem / "subagents"
        for t in sorted(sub.glob("agent-*.jsonl")) if sub.is_dir() else []:
            meta = {}
            try:
                meta = json.loads(t.with_suffix(".meta.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
            fuentes.append((t, meta.get("agentType") or "subagente", t.stem))
        for archivo, agente, invocacion in fuentes:
            for ts, modelo, uso, herr in leer_transcripcion(archivo):
                try:
                    f = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().date()
                except ValueError:
                    continue
                if (desde and f < desde) or (hasta and f > hasta):
                    continue
                registros.append({"agente": agente, "sesion": sesion.stem, "invocacion": invocacion, "fecha": f.isoformat(),
                                  "modelo": modelo, "uso": uso, "herramientas": herr})
    return registros


def costos_evals(raiz=RAIZ, desde=None, hasta=None):
    """Costo de las corridas de evals (evals/resultados/<fecha>/resultados.json), si existen."""
    salida = []
    for arch in sorted(glob.glob(str(Path(raiz) / "evals" / "resultados" / "*" / "resultados.json"))):
        try:
            d = json.loads(Path(arch).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        fecha = str(d.get("fecha") or Path(arch).parent.name)[:10]
        try:
            f = date.fromisoformat(fecha)
            if (desde and f < desde) or (hasta and f > hasta):
                continue
        except ValueError:
            pass
        total = 0.0
        for c in d.get("casos") or []:
            v = c.get("costo_usd") if isinstance(c, dict) else None
            v = v if v is not None else (c.get("ejecucion") or {}).get("costo_usd") if isinstance(c, dict) else None
            total += float(v or 0)
        total = float(d.get("costo_total_usd") or total)
        salida.append({"corrida": Path(arch).parent.name, "fecha": fecha, "costo_usd": round(total, 4), "casos": len(d.get("casos") or [])})
    return salida


def _vacio():
    return {"llamadas": 0, "entrada": 0, "salida": 0, "cache_5m": 0, "cache_1h": 0, "cache_lectura": 0,
            "costo_usd": 0.0, "sin_precio": 0}


def _sumar(acc, r):
    acc["llamadas"] += 1
    for k in ("entrada", "salida", "cache_5m", "cache_1h", "cache_lectura"):
        acc[k] += r["uso"][k]
    c = costo(r["uso"], r["modelo"])
    if c is None:
        acc["sin_precio"] += 1
    else:
        acc["costo_usd"] += c


def _pct_cache(a):
    leido = a["entrada"] + a["cache_5m"] + a["cache_1h"] + a["cache_lectura"]
    return round(100 * a["cache_lectura"] / leido, 1) if leido else 0.0


def agregar(registros, evals=None):
    total, por_agente, por_dia, por_modelo = _vacio(), defaultdict(_vacio), defaultdict(_vacio), defaultdict(_vacio)
    invocaciones, herramientas = defaultdict(set), defaultdict(lambda: defaultdict(int))
    for r in registros:
        for acc in (total, por_agente[r["agente"]], por_dia[r["fecha"]], por_modelo[r["modelo"]]):
            _sumar(acc, r)
        invocaciones[r["agente"]].add(r["invocacion"])
        for h in r["herramientas"]:
            herramientas[r["agente"]][h] += 1
    agentes = []
    for nombre, a in por_agente.items():
        top = sorted(herramientas[nombre].items(), key=lambda kv: -kv[1])[:5]
        agentes.append({"agente": nombre, **a, "costo_usd": round(a["costo_usd"], 4), "invocaciones": len(invocaciones[nombre]),
                        "pct_cache": _pct_cache(a), "herramientas": [h for h, _ in top]})
    agentes.sort(key=lambda x: (-x["costo_usd"], -x["salida"]))
    dias = [{"fecha": f, **a, "costo_usd": round(a["costo_usd"], 4)} for f, a in sorted(por_dia.items())]
    modelos = [{"modelo": m, **a, "costo_usd": round(a["costo_usd"], 4), "con_precio": precio_de(m) is not None}
               for m, a in sorted(por_modelo.items(), key=lambda kv: -kv[1]["costo_usd"])]
    evals = evals or []
    costo_evals = round(sum(x["costo_usd"] for x in evals), 4)
    resumen = {"llamadas": total["llamadas"], "costo_usd": round(total["costo_usd"], 4), "costo_evals_usd": costo_evals,
               "tokens_salida": total["salida"], "tokens_entrada_total": total["entrada"] + total["cache_5m"] + total["cache_1h"] + total["cache_lectura"],
               "pct_cache": _pct_cache(total), "agentes": len([a for a in agentes if a["agente"] != PRINCIPAL]),
               "sesiones": len({r["sesion"] for r in registros}), "sin_precio": total["sin_precio"]}
    return {"resumen": resumen, "agentes": agentes, "dias": dias, "modelos": modelos, "evals": evals,
            "oportunidades": oportunidades(agentes, resumen)}


def oportunidades(agentes, resumen):
    """Recomendaciones a partir de los números (texto, sin inventar)."""
    salida = []
    subs = [a for a in agentes if a["agente"] != PRINCIPAL and a["costo_usd"] > 0]
    total = resumen["costo_usd"] or 0
    if subs and total:
        top = subs[0]
        salida.append({"tipo": "Mayor gasto", "agente": top["agente"],
                       "detalle": f'Es el agente que más gasta: ${top["costo_usd"]:.2f} '
                                  f'({100 * top["costo_usd"] / total:.0f} % del total) en {top["invocaciones"]} uso(s).'})
    for a in agentes:
        if a["agente"] in (PRINCIPAL, "fork", "subagente", "general-purpose", "Explore", "Plan"):
            continue
        if a["invocaciones"] >= UMBRAL_REPETIDO:
            salida.append({"tipo": "Candidato a automatizar", "agente": a["agente"],
                           "detalle": f'Se usó {a["invocaciones"]} veces. Si es para correr las mismas pruebas, '
                                      f'automatizalas en k0lmena: después corren con npm test, sin tokens.'})
    for a in agentes:
        if a["llamadas"] >= 20 and a["pct_cache"] < 50:
            salida.append({"tipo": "Caché baja", "agente": a["agente"],
                           "detalle": f'Reutiliza solo el {a["pct_cache"]:.0f} % de la entrada desde caché: '
                                      f'conversaciones cortas o contexto que cambia en cada llamada.'})
    if resumen.get("sin_precio"):
        salida.append({"tipo": "Sin precio", "agente": "—",
                       "detalle": f'{resumen["sin_precio"]} respuesta(s) de modelos que no están en la tabla de precios: '
                                  f'su costo no se suma (actualizá PRECIOS en scripts/metricas_tokens.py).'})
    return salida


# ------------------------------------------------------------------ informe
def _usd(v):
    return f"${v:,.2f}" if v >= 0.01 or v == 0 else f"${v:.4f}"


def _k(n):
    return f"{n / 1_000_000:.1f} M" if n >= 1_000_000 else f"{n / 1000:.1f} K" if n >= 1000 else str(n)


def build_html(datos, carpeta=None):
    from _estilos_reporte import (e, page, meta, section, kpi_tiles, table, bar_chart, column_chart, doc_list, two_col,
                                  banner, SERIES)
    import _historial
    r = datos["resumen"]
    if not datos["agentes"]:
        # La carpeta va aparte, como código: el texto se traduce y la ruta (distinta en cada máquina) no.
        aviso = (f'<p>{e("No encuentro las transcripciones de Claude Code en esta carpeta:")} <code>{e(datos["fuente"])}</code></p>'
                 f'<p>{e("Se generan al usar Claude Code en este proyecto (en CI o en otra máquina no existen); pasá otra carpeta con --carpeta.")}</p>'
                 if datos.get("aviso") else f'<p>{e("No hay uso registrado en el período.")}</p>')
        cuerpo = section("Sin datos", f'<div class="cardbody">{aviso}</div>')
        return page("Uso de tokens", "Métricas de tokens", meta([("Período", datos.get("periodo"))]), cuerpo)
    serie = [d["costo_usd"] for d in datos["dias"]]
    body = [kpi_tiles([
        ("Costo estimado", _usd(r["costo_usd"]), "", f'{r["llamadas"]} respuesta(s) del modelo', "carga", {"serie": serie} if len(serie) > 1 else None),
        ("Tokens generados", _k(r["tokens_salida"]), "", f'{_k(r["tokens_entrada_total"])} leídos', "rayo"),
        ("Leído desde caché", f'{r["pct_cache"]:.0f} %', "ok" if r["pct_cache"] >= 70 else "warn", "de la entrada", "reloj", {"pct": r["pct_cache"]}),
        ("Agentes usados", r["agentes"], "", f'en {r["sesiones"]} sesión(es)', "persona"),
    ])]
    if r.get("sin_precio"):
        body.append(banner(f'{r["sin_precio"]} respuesta(s) de modelos sin precio en la tabla: su costo no está sumado.', "warn"))
    top = datos["agentes"][:12]
    body.append(two_col(
        section("Costo por agente", bar_chart([(a["agente"], round(a["costo_usd"], 2), SERIES[0]) for a in top], ancho_etiqueta=190), "USD estimados"),
        section("Costo por día", column_chart([(d["fecha"][5:], round(d["costo_usd"], 2)) for d in datos["dias"][-14:]],
                                              fmt=lambda v: f"${v:,.2f}", alto=240, ancho=660), "últimos 14 días con uso")))
    filas = [[f'<b>{e(a["agente"])}</b>', a["invocaciones"], a["llamadas"], _k(a["entrada"] + a["cache_5m"] + a["cache_1h"] + a["cache_lectura"]),
              _k(a["salida"]), f'{a["pct_cache"]:.0f} %', e(_usd(a["costo_usd"])), e(", ".join(a["herramientas"]) or "—")] for a in datos["agentes"]]
    body.append(section("Detalle por agente", table(["Agente", "Usos", "Respuestas", "Tokens leídos", "Tokens generados", "Caché",
                                                     "Costo", "Herramientas más usadas"], filas)))
    filas_m = [[e(m["modelo"]), m["llamadas"], _k(m["salida"]), e(_usd(m["costo_usd"])) if m["con_precio"] else '<span class="muted">sin precio</span>']
               for m in datos["modelos"]]
    # El agente va aparte (" · "): la frase fija se traduce sola en la versión en inglés.
    op = [" · ".join(x for x in (o["tipo"], o.get("agente") if o.get("agente") not in (None, "", "—") else "", o["detalle"]) if x)
          for o in datos["oportunidades"]]
    body.append(two_col(section("Por modelo", table(["Modelo", "Respuestas", "Tokens generados", "Costo"], filas_m)),
                        section("Oportunidades", doc_list(op or ["Sin oportunidades claras en este período."]))))
    if datos.get("evals"):
        body.append(section("Evals de los agentes", table(["Corrida", "Fecha", "Casos", "Costo"],
                                                          [[e(x["corrida"]), e(x["fecha"]), x["casos"], e(_usd(x["costo_usd"]))] for x in datos["evals"]]),
                            f'{_usd(r["costo_evals_usd"])} en total'))
    # Sin saltos de línea dentro de cada frase: la versión en inglés traduce cada texto entero.
    body.append(section("Cómo se calcula", (
        '<div class="cardbody"><p>Se leen las transcripciones de Claude Code de este proyecto ('
        f'<span class="mono">{e(datos.get("fuente", ""))}</span>): cada respuesta del modelo trae los tokens de entrada, salida y caché. '
        'Los subagentes se identifican por su tipo; lo demás es la conversación principal. El costo es una <b>estimación</b> '
        f'con los precios por millón de tokens del {e(datos.get("precios_fecha", PRECIOS_FECHA))} (tabla <span class="mono">PRECIOS</span> '
        'del script); no reemplaza la facturación real. No se lee el texto de los mensajes.</p></div>')))
    if carpeta:
        body.append(_historial.seccion("tokens", carpeta, datos))
    return page("Uso de tokens", "Métricas de tokens", meta([("Período", datos.get("periodo")), ("Generado", datos.get("fecha", "")[:16].replace("T", " "))]),
                "".join(body))


# ------------------------------------------------------------------ historial
import _historial  # noqa: E402
from _i18n import escribir_bilingue, localizar, idioma_actual  # noqa: E402

_historial.TIPOS.setdefault("tokens", {
    "archivo": "metricas.json", "items": lambda d: d.get("oportunidades") or [],
    "clave": lambda o: f'{o.get("tipo")}|{o.get("agente")}', "titulo": lambda o: f'{o.get("tipo")} · {o.get("agente")}',
    "metricas": [("Costo (USD)", _historial._r("costo_usd"), ""), ("Respuestas", _historial._r("llamadas"), ""),
                 ("Caché", _historial._r("pct_cache"), " %"), ("Agentes", _historial._r("agentes"), "")]})


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Métricas de uso de tokens de los agentes de k0lmenIA")
    ap.add_argument("--nombre", default="general")
    ap.add_argument("--desde", type=date.fromisoformat)
    ap.add_argument("--hasta", type=date.fromisoformat)
    ap.add_argument("--dias", type=int, help="atajo: los últimos N días")
    ap.add_argument("--carpeta", help="carpeta de transcripciones (por defecto la de este proyecto en ~/.claude/projects)")
    ap.add_argument("--salida", help="carpeta de salida (por defecto output/metricas-tokens/<nombre>)")
    a = ap.parse_args(argv)
    if a.dias:
        a.desde = date.today() - timedelta(days=a.dias - 1)
    if not re.fullmatch(r"[\w.-]+", a.nombre):
        ap.error("--nombre: solo letras, números, punto, guion y guion bajo")
    fuente = Path(a.carpeta) if a.carpeta else carpeta_transcripciones()
    carpeta = Path(a.salida) if a.salida else RAIZ / "output" / "metricas-tokens" / a.nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    periodo = f'{a.desde or "inicio"} a {a.hasta or "hoy"}'
    registros = recolectar(fuente, a.desde, a.hasta) if fuente.is_dir() else []
    datos = agregar(registros, costos_evals(RAIZ, a.desde, a.hasta))
    datos.update({"fecha": datetime.now().isoformat(timespec="seconds"), "periodo": periodo, "fuente": str(fuente),
                  "precios_fecha": PRECIOS_FECHA, "nombre": a.nombre})
    if not fuente.is_dir():
        datos["aviso"] = (f"No encuentro las transcripciones de Claude Code en {fuente}. Se generan al usar Claude Code en este "
                          "proyecto (en CI o en otra máquina no existen); pasá otra carpeta con --carpeta.")
        print(datos["aviso"])
    _historial.archivar(carpeta, GENERADOS, "metricas.json")
    (carpeta / "metricas.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    escribir_bilingue(carpeta / "informe-metricas.html", lambda: build_html(datos, carpeta))
    r = datos["resumen"]
    print(f'{r["llamadas"]} respuesta(s) · {r["agentes"]} agente(s) · costo estimado ${r["costo_usd"]:.2f} · caché {r["pct_cache"]:.0f} %')
    print(f"Informe: {carpeta / 'informe-metricas.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

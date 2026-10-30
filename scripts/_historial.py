"""Historial de corridas: cada herramienta guarda sus últimas 5 corridas (con su evidencia) para compararlas.

Antes de una corrida nueva, la anterior se MUEVE a <carpeta>/historial/<fecha-hora>/ con su JSON, su análisis,
su informe y su evidencia (capturas, videos…), así su informe se sigue abriendo igual. Se conservan las 4
anteriores + la actual = 5; las más viejas se borran.

En el informe, `seccion(tipo, carpeta, datos)` agrega "Evolución de las corridas": qué hallazgos son nuevos,
cuáles se resolvieron y cuáles siguen desde la corrida anterior, la evolución de los indicadores principales
y el link al informe de cada corrida guardada.

Lo usan los informes de Python y, desde Node, herramientas/k0lmena/tools/historial/historial.js (misma lógica).
"""
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import os

# Cuántas corridas se guardan (la actual incluida): HISTORIAL_CORRIDAS del entorno, 5 por defecto.
MAX_CORRIDAS = int(os.environ.get("HISTORIAL_CORRIDAS", "5")) if os.environ.get("HISTORIAL_CORRIDAS", "5").isdigit() and int(os.environ.get("HISTORIAL_CORRIDAS", "5")) > 1 else 5
CARPETA = "historial"


# ------------------------------------------------------------------ archivar
def _sello(datos_arch):
    try:
        d = json.loads(Path(datos_arch).read_text(encoding="utf-8"))
        f = d.get("marca") or d.get("fecha")
    except (OSError, ValueError):
        f = None
    if not f:
        f = datetime.fromtimestamp(Path(datos_arch).stat().st_mtime).isoformat(timespec="seconds")
    return re.sub(r"[^0-9A-Za-z-]+", "-", str(f))[:19].strip("-")


def archivar(carpeta, nombres, archivo_datos, max_corridas=MAX_CORRIDAS):
    """Mueve la corrida anterior (los `nombres` que existan) a historial/<sello>/ y poda a max_corridas - 1."""
    carpeta = Path(carpeta)
    datos = carpeta / archivo_datos
    if not datos.exists():
        return None
    base = carpeta / CARPETA / _sello(datos)
    destino, n = base, 2
    while destino.exists():
        destino, n = Path(f"{base}-{n}"), n + 1
    destino.mkdir(parents=True)
    for nombre in _con_idiomas(nombres):
        src = carpeta / nombre
        if src.exists():
            (destino / nombre).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(destino / nombre))
    podar(carpeta, max_corridas - 1)
    return destino


def _con_idiomas(nombres):
    """Cada informe HTML va con sus dos idiomas (es/<nombre> y en/<nombre>, scripts/_i18n.py) aunque la lista no los nombre."""
    salida = []
    for n in nombres:
        salida.append(n)
        if str(n).lower().endswith(".html") and "/" not in str(n):
            salida += [f"es/{n}", f"en/{n}"]
    return list(dict.fromkeys(salida))


def podar(carpeta, guardar):
    dirs = sorted((d for d in (Path(carpeta) / CARPETA).glob("*") if d.is_dir()), key=lambda d: d.name)
    for d in dirs[: max(0, len(dirs) - guardar)]:
        shutil.rmtree(d, ignore_errors=True)


def cargar(carpeta, archivo_datos):
    """Corridas guardadas (de la más vieja a la más nueva): [{"sello", "datos", "informe"}]."""
    salida = []
    for d in sorted((Path(carpeta) / CARPETA).glob("*"), key=lambda d: d.name):
        arch = d / archivo_datos
        if not arch.exists():
            continue
        try:
            datos = json.loads(arch.read_text(encoding="utf-8"))
        except ValueError:
            continue
        informe = next((f"{CARPETA}/{d.name}/{h.name}" for h in sorted(d.glob("informe-*.html"))), None)
        salida.append({"sello": d.name, "datos": datos, "informe": informe})
    return salida[-(MAX_CORRIDAS - 1):]


# ------------------------------------------------------------------ qué se compara de cada herramienta
_SIN_NUMEROS = re.compile(r"[-+]?\d+([.,]\d+)?")


def _norm(s):
    return _SIN_NUMEROS.sub("#", str(s or "")).strip().lower()


def _huecos(d):
    return [dict(x, historia=h.get("historia")) for h in d.get("historias") or [] for x in h.get("huecos") or []]


def _cob_pct(d):
    hs = d.get("historias") or []
    tot = sum(h["metricas"]["criterios"] for h in hs)
    return round(sum(h["metricas"]["criterios_cubiertos"] for h in hs) / tot * 100) if tot else None


def _r(*claves):
    def f(d):
        v = d.get("resumen") or {}
        for c in claves:
            v = (v or {}).get(c) if isinstance(v, dict) else None
        return v
    return f


TIPOS = {
    "revision": {"archivo": "revision.json", "items": lambda d: [dict(x, caso=f'{c.get("historia")}:{c.get("id")}') for c in d.get("casos") or [] for x in c.get("hallazgos") or []],
                 "clave": lambda x: f'{x.get("caso")}|{x.get("tipo")}|{_norm(x.get("titulo"))}', "titulo": lambda x: f'{x.get("caso")} · {x.get("titulo")}',
                 "metricas": [("Puntaje promedio", _r("puntaje_prom"), ""), ("A mejorar", _r("a_mejorar"), ""), ("Problemas", _r("hallazgos"), ""),
                              ("Ejecución manual", _r("tiempo_total_min"), " min")]},
}

ETIQUETA_ITEM = {"tablero": "alertas", "fallos": "escenarios con fallas", "cobertura": "huecos", "reparacion": "reparaciones", "seleccion": "casos seleccionados"}


def comparar(tipo, actual, anterior):
    t = TIPOS[tipo]
    a = {t["clave"](x): x for x in t["items"](actual)}
    b = {t["clave"](x): x for x in t["items"](anterior)} if anterior else {}
    return {"nuevos": [a[k] for k in a if k not in b], "resueltos": [b[k] for k in b if k not in a], "siguen": [a[k] for k in a if k in b],
            "claves_nuevas": {k for k in a if k not in b} if anterior else set()}


def es_nuevo(tipo, item, comparacion):
    return bool(comparacion) and TIPOS[tipo]["clave"](item) in comparacion["claves_nuevas"]


# ------------------------------------------------------------------ sección del informe
def _fecha(sello):
    m = re.match(r"(\d{4})-?(\d{2})-?(\d{2})[T_-]?(\d{2})-?(\d{2})", sello or "")
    return f"{m.group(3)}/{m.group(2)} {m.group(4)}:{m.group(5)}" if m else (sello or "")[:16]


def seccion(tipo, carpeta, datos):
    """HTML de "Evolución de las corridas" (o "" si el tipo no se conoce)."""
    from _estilos_reporte import e, section, kpi_tiles, table, line_chart, SERIES

    t = TIPOS.get(tipo)
    if not t:
        return ""
    previas = cargar(carpeta, t["archivo"])
    sello_actual = re.sub(r"[^0-9A-Za-z-]+", "-", str(datos.get("marca") or datos.get("fecha") or "actual"))[:19]
    corridas = [dict(c, actual=False) for c in previas] + [{"sello": sello_actual, "datos": datos, "informe": None, "actual": True}]
    etiqueta = ETIQUETA_ITEM.get(tipo, "hallazgos")
    if not previas:
        return section("Evolución de las corridas",
                       f'<div class="cardbody"><p class="muted">Es la primera corrida guardada en esta carpeta. Desde la próxima vas a ver acá qué '
                       f'{e(etiqueta)} son nuevos, cuáles se resolvieron y cómo evolucionan los indicadores (se guardan las últimas {MAX_CORRIDAS} '
                       f'corridas en <span class="mono">historial/</span>).</p></div>')
    cmp = comparar(tipo, datos, previas[-1]["datos"])
    partes = ['<div style="padding:18px 24px 4px">' + kpi_tiles([
        ("Corridas guardadas", len(corridas), "", f"las últimas {MAX_CORRIDAS}, con su evidencia", "reloj"),
        (f"Nuevos", len(cmp["nuevos"]), "bad" if cmp["nuevos"] else "ok", f"{etiqueta} que no estaban en la corrida anterior", "warn"),
        ("Resueltos", len(cmp["resueltos"]), "ok" if cmp["resueltos"] else "", f"{etiqueta} que ya no aparecen", "ok"),
        ("Siguen", len(cmp["siguen"]), "warn" if cmp["siguen"] else "ok", "estaban y siguen", "lista"),
    ]) + "</div>"]

    graficos = []
    x = list(range(len(corridas)))
    for i, (nombre, f, unidad) in enumerate(t["metricas"]):
        vals = []
        for c in corridas:
            try:
                v = f(c["datos"])
            except (KeyError, TypeError, ZeroDivisionError):
                v = None
            vals.append(v if isinstance(v, (int, float)) else None)
        if sum(v is not None for v in vals) < 2:
            continue
        fmt = (lambda u: (lambda v: f"{v:g}{u}"))(unidad)
        fx = (lambda cs: (lambda v: _fecha(cs[int(v)]["sello"]) if 0 <= int(v) < len(cs) else ""))(corridas)
        graficos.append(f'<div class="evo"><div class="lbl" style="margin:0 0 4px">{e(nombre)}</div>'
                        f'{line_chart(x, [(nombre, SERIES[i % len(SERIES)], vals)], fmt=fmt, fmt_x=fx, alto=220, ancho=660)}</div>')
    if graficos:
        partes.append('<style>.evos{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;padding:6px 24px 14px}'
                      '.evo{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:12px 8px 4px}'
                      '@media (max-width:900px){.evos{grid-template-columns:1fr}}</style>'
                      f'<div class="evos">{"".join(graficos)}</div>')

    filas = []
    for c in reversed(corridas):
        celdas = [f'<strong style="color:var(--ink)">{e(_fecha(c["sello"]))}</strong>' + (' <span class="pill">actual</span>' if c["actual"] else "")]
        for _, f, unidad in t["metricas"]:
            try:
                v = f(c["datos"])
            except (KeyError, TypeError, ZeroDivisionError):
                v = None
            celdas.append(e(f"{v:g}{unidad}") if isinstance(v, (int, float)) else '<span class="muted">—</span>')
        celdas.append(f'<a href="{e(c["informe"])}" style="color:var(--ink)">abrir informe</a>' if c["informe"]
                      else '<span class="muted">este</span>' if c["actual"] else '<span class="muted">sin informe</span>')
        filas.append(celdas)
    partes.append(table(["Corrida"] + [m[0] for m in t["metricas"]] + ["Informe"], filas))

    def lista(titulo, items):
        if not items:
            return ""
        lis = "".join(f"<li>{e(t['titulo'](x))}</li>" for x in items[:12])
        mas = f'<li class="muted">y {len(items) - 12} más</li>' if len(items) > 12 else ""
        return f'<div class="cardbody"><div class="lbl" style="margin:0 0 6px">{e(titulo)}</div><ul class="doclist">{lis}{mas}</ul></div>'

    partes.append(lista(f"Nuevos desde la corrida anterior ({_fecha(previas[-1]['sello'])})", cmp["nuevos"]))
    partes.append(lista("Resueltos desde la corrida anterior", cmp["resueltos"]))
    return section("Evolución de las corridas", "".join(partes),
                   f"comparación con las {len(previas)} corrida(s) anteriores guardadas en historial/")

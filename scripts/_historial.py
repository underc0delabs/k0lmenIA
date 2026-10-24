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
    "exploratorio": {"archivo": "exploracion.json", "items": lambda d: d.get("hallazgos") or [],
                     "clave": lambda h: f'{h.get("categoria")}|{_norm(h.get("titulo"))}|{h.get("pagina")}', "titulo": lambda h: h.get("titulo"),
                     "metricas": [("Hallazgos", _r("hallazgos"), ""), ("Links rotos", _r("links_rotos"), ""),
                                  ("Errores de JavaScript", _r("errores_js"), ""), ("Carga promedio", _r("carga_promedio_ms"), " ms")]},
    "accesibilidad": {"archivo": "auditoria.json", "items": lambda d: d.get("hallazgos") or [],
                      "clave": lambda h: h.get("regla") or _norm(h.get("titulo")), "titulo": lambda h: h.get("titulo"),
                      "metricas": [("Cumplimiento", _r("cumplimiento_pct"), " %"), ("Hallazgos", _r("hallazgos"), ""),
                                   ("Críticos", _r("criticos"), ""), ("Elementos afectados", _r("elementos_afectados"), "")]},
    "rendimiento": {"archivo": "rendimiento.json", "items": lambda d: d.get("hallazgos") or [],
                    "clave": lambda h: f'{h.get("categoria")}|{h.get("metrica")}|{h.get("pagina")}|{h.get("dispositivo")}', "titulo": lambda h: h.get("titulo"),
                    "metricas": [("Rendimiento mobile", _r("rendimiento_mobile"), ""), ("Rendimiento desktop", _r("rendimiento_desktop"), ""),
                                 ("Hallazgos", _r("hallazgos"), ""), ("Oportunidades", _r("oportunidades"), "")]},
    "pixel-perfect": {"archivo": "pixel-perfect.json", "items": lambda d: d.get("hallazgos") or [],
                      "clave": lambda h: f'{h.get("tipo")}|{h.get("pantalla")}|{_norm(h.get("titulo"))}', "titulo": lambda h: f'{h.get("titulo")} ({h.get("resolucion")})',
                      "metricas": [("Mayor diferencia", _r("pct_max"), " %"), ("Pantallas con cambios", _r("con_cambios"), ""),
                                   ("Hallazgos", _r("hallazgos"), ""), ("Elementos corridos", _r("elementos_corridos"), "")]},
    "cross-browser": {"archivo": "cross-browser.json", "items": lambda d: d.get("hallazgos") or [],
                      "clave": lambda h: f'{h.get("tipo")}|{h.get("navegador") or ",".join(h.get("fallan") or [])}|{_norm(h.get("titulo"))}',
                      "titulo": lambda h: h.get("titulo"),
                      "metricas": [("Hallazgos", _r("hallazgos"), ""), ("Diferencias entre navegadores", lambda d: (d.get("resumen") or {}).get("diferencias", (d.get("resumen") or {}).get("con_problemas")), ""),
                                   ("Fallan en todos", _r("fallan_en_todos"), "")]},
    "fallos": {"archivo": "fallos.json", "items": lambda d: d.get("fallos") or [],
               "clave": lambda f: f.get("clave") or f'{f.get("uri")}:{f.get("linea")}', "titulo": lambda f: f'{f.get("caso") or ""} {f.get("escenario")}'.strip(),
               "metricas": [("Con fallas", _r("fallidos"), ""), ("Siguen fallando", _r("siguen_fallando"), ""),
                            ("Posibles bugs", _r("por_categoria", "Posible bug"), ""), ("Inestables", _r("por_categoria", "Inestable (flaky)"), "")]},
    "cobertura": {"archivo": "cobertura.json", "items": _huecos,
                  "clave": lambda x: f'{x.get("historia")}|{x.get("tipo")}|{x.get("ref")}', "titulo": lambda x: f'{x.get("historia")} · {x.get("tipo")}: {x.get("detalle")}',
                  "metricas": [("Criterios cubiertos", _cob_pct, " %"), ("Huecos", lambda d: len(_huecos(d)), ""),
                               ("Automatizados", lambda d: sum(h["metricas"]["automatizados"] for h in d.get("historias") or []), "")]},
    "reparacion": {"archivo": "reparaciones.json", "items": lambda d: d.get("reparaciones") or [],
                   "clave": lambda r: f'{r.get("uri")}:{r.get("linea")}', "titulo": lambda r: f'{r.get("caso") or ""} {r.get("escenario")} · {r.get("diagnostico")}'.strip(),
                   "metricas": [("Fallas analizadas", _r("fallas"), ""), ("Con propuesta", _r("con_propuesta"), ""), ("Verificadas", _r("verificadas"), "")]},
    "correos": {"archivo": "correos.json", "items": lambda d: d.get("hallazgos") or [],
                "clave": lambda h: f'{h.get("tipo")}|{_norm(h.get("asunto"))}|{_norm(h.get("titulo"))}', "titulo": lambda h: f'{h.get("titulo")} ({h.get("asunto") or "sin correo"})',
                "metricas": [("Correos", _r("correos"), ""), ("Expectativas cumplidas", _r("cumplen"), ""), ("Hallazgos", _r("hallazgos"), ""),
                             ("Compatibilidad", _r("compatibilidad_prom"), " %")]},
    "traductor": {"archivo": "traductor.json", "items": lambda d: d.get("hallazgos") or [],
                  "clave": lambda h: f'{h.get("tipo")}|{h.get("idioma")}|{h.get("texto") or _norm(h.get("titulo"))}', "titulo": lambda h: f'[{h.get("idioma")}] {h.get("titulo")}',
                  "metricas": [("Sin traducir", _r("sin_traducir"), ""), ("Hallazgos", _r("hallazgos"), ""), ("Cortados", _r("cortados"), ""),
                               ("Claves a la vista", _r("claves"), "")]},
    "revision": {"archivo": "revision.json", "items": lambda d: [dict(x, caso=f'{c.get("historia")}:{c.get("id")}') for c in d.get("casos") or [] for x in c.get("hallazgos") or []],
                 "clave": lambda x: f'{x.get("caso")}|{x.get("tipo")}|{_norm(x.get("titulo"))}', "titulo": lambda x: f'{x.get("caso")} · {x.get("titulo")}',
                 "metricas": [("Puntaje promedio", _r("puntaje_prom"), ""), ("A mejorar", _r("a_mejorar"), ""), ("Problemas", _r("hallazgos"), ""),
                              ("Ejecución manual", _r("tiempo_total_min"), " min")]},
    "charters": {"archivo": "sesiones.json", "items": lambda d: d.get("hallazgos") or [],
                 "clave": lambda b: f'{b.get("charter")}|{_norm(b.get("texto"))}', "titulo": lambda b: f'{b.get("charter")} · {b.get("texto")}',
                 "metricas": [("Sesiones", _r("sesiones"), ""), ("Bugs", _r("bugs"), ""), ("Preguntas", _r("preguntas"), ""), ("Minutos", _r("minutos"), " min")]},
    "ux": {"archivo": "ux.json", "items": lambda d: d.get("hallazgos") or [],
           "clave": lambda h: f'{h.get("heuristica")}|{_norm(h.get("titulo"))}', "titulo": lambda h: f'{h.get("heuristica")} · {h.get("titulo")}',
           "metricas": [("Puntaje heurístico", _r("puntaje"), ""), ("Hallazgos", _r("hallazgos"), ""), ("Alta", _r("por_severidad", "Alta"), "")]},
    "formularios": {"archivo": "formularios.json", "items": lambda d: d.get("hallazgos") or [],
                    "clave": lambda h: f'{h.get("formulario")}|{h.get("campo")}|{h.get("tipo")}', "titulo": lambda h: f'{h.get("campo") or h.get("formulario")} · {h.get("titulo")}',
                    "metricas": [("Campos", _r("campos"), ""), ("Pruebas que fallan", _r("pruebas_fallan"), ""), ("Hallazgos", _r("hallazgos"), "")]},
    "logs": {"archivo": "logs.json", "items": lambda d: d.get("firmas") or [],
             "clave": lambda f: f.get("firma"), "titulo": lambda f: f'{f.get("nivel")} · {f.get("ejemplo", "")[:100]}',
             "metricas": [("Errores", _r("errores"), ""), ("Firmas distintas", _r("firmas"), ""), ("Advertencias", _r("advertencias"), "")]},
    "seleccion": {"archivo": "seleccion.json", "items": lambda d: [c for c in d.get("casos") or [] if c.get("grupo") != "No seleccionado"],
                  "clave": lambda c: c.get("clave"), "titulo": lambda c: f'{c.get("historia")} · {c.get("id")} {c.get("titulo")}',
                  "metricas": [("Seleccionados", _r("seleccionados"), ""), ("Minutos", _r("minutos_seleccion"), " min"), ("Cambios sin casos", _r("sin_cobertura"), "")]},
    "tablero": {"archivo": "tablero.json", "items": lambda d: d.get("alertas") or [],
                "clave": lambda a: f'{a.get("tipo")}|{_norm(a.get("titulo"))}', "titulo": lambda a: f'{a.get("tipo")} · {a.get("titulo")}',
                "metricas": [("Aprobados", _r("pct_aprobados"), " %"), ("Automatizado", _r("pct_automatizado"), " %"),
                             ("Cobertura", _r("cobertura_pct"), " %"), ("Bugs abiertos", _r("bugs_abiertos"), "")]},
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

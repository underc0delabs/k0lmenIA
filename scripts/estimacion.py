#!/usr/bin/env python3
"""
Estimación del tiempo de ejecución MANUAL de un caso de prueba (y de cada paso).

Uso como módulo:   from estimacion import estimar_caso      → {"minutos", "segundos", "texto", "pasos", ...}
Uso por consola:   python scripts/estimacion.py <casos.xlsx|.feature> [--json]

La fórmula (detalle en plantillas/estimacion-tiempos.md):

    tiempo del caso = (preparación + Σ tiempo de cada paso + registro) × factor del caso   → redondeado hacia arriba a 0,5 min

    tiempo de un paso = tiempo de la acción + tiempo de los datos + tiempo de la verificación
      - acción: según el verbo del paso (tabla ACCIONES): navegar 0,5 · clic o seleccionar 0,25 · completar 0,3 por campo ·
        iniciar sesión 1 · subir o descargar un archivo 1 · esperar un correo, SMS o proceso 2 · consultar la base, una API o
        logs 2 · leer o recorrer 0,5 · cualquier otra 0,5 (min)
      - datos: 0,15 min por cada dato extra del paso (más allá de los campos ya contados)
      - verificación: 0,5 min si el paso tiene resultado esperado (o es un Then), + 0,25 por cada verificación adicional (hasta 4)
    preparación = 1 min (abrir el ambiente y leer el caso) + 0,5 por precondición (hasta 3) + 2 si hay que crear datos o usuarios
    registro    = 0,5 min (marcar el resultado y guardar la evidencia) + 0,1 por paso
    factor      = 1,1 para casos negativos o de borde (hay que observar con más cuidado), 1 para el resto

Es una estimación para planificar (no una medición): los equipos pueden ajustar las constantes con
ESTIMACION_FACTOR (multiplica todo, por ejemplo 1.3 para alguien que recién conoce la app).
"""
import json
import math
import os
import re
import sys
from pathlib import Path

# (categoría, patrón del verbo o la frase, minutos, se multiplica por la cantidad de campos)
ACCIONES = [
    ("Iniciar sesión", r"inici\w* sesi[oó]n|log\s?in|loguea|autentic|ingres\w* con (su|el|la|sus) (usuario|cuenta|credenciales)", 1.0, False),
    ("Esperar un correo, SMS o proceso", r"esper\w*|recib\w* (un|el|la) (correo|mail|email|sms|notificaci)|revis\w* (el|su) (correo|mail|bandeja)|bandeja de entrada", 2.0, False),
    ("Consultar la base, una API o logs", r"consult\w* (la|en la) base|base de datos|\bsql\b|\bapi\b|endpoint|postman|\blogs?\b", 2.0, False),
    ("Subir o descargar un archivo", r"adjunt\w*|sub\w* (un|el|la|los|las)? ?(archivo|imagen|documento|foto)|descarg\w*|export\w*|import\w*|imprim\w*", 1.0, False),
    ("Completar campos", r"complet\w*|escrib\w*|ingres\w* (el|la|los|las|un|una|su|sus)\b|carg\w* (el|la|los|las|un|una)\b|tipe\w*|llen\w*|rellen\w*|introduc\w*|fill|type", 0.3, True),
    ("Navegar", r"\bir a\b|naveg\w*|acced\w*|abr\w*|entr\w* (a|al|en)\b|visit\w*|ingres\w* (a|al) (la|el)? ?(p[aá]gina|sitio|secci[oó]n|men[uú]|pantalla|m[oó]dulo)|est[aá] en (la|el)|se encuentra en", 0.5, False),
    ("Clic o seleccionar", r"clic\w*|click\w*|presion\w*|toc\w*|puls\w*|seleccion\w*|eleg\w*|marc\w*|desmarc\w*|activ\w*|desactiv\w*|cerr\w*|confirm\w*|acept\w*|cancel\w*|envi\w*|guard\w*", 0.25, False),
    ("Leer o recorrer", r"despl\w*|scroll|recorr\w*|le[eé]\w*|observ\w*|revis\w*", 0.5, False),
]
_ACC = [(c, re.compile(p, re.I), m, x) for c, p, m, x in ACCIONES]
NEGATIVO = re.compile(r"inv[aá]lid|incorrect|err[oó]n|error|vac[ií]o|sin (completar|datos)|l[ií]mite|m[aá]xim|m[ií]nim|borde|rechaz|bloque|vencid|exced|negativ", re.I)
CREAR_DATOS = re.compile(r"cre\w* (un|una|el|la|los|las)? ?(usuario|cuenta|cliente|registro|pedido|producto|dato)|dar de alta|insert\w* en la base|cargad\w* en la base", re.I)
FACTOR = float(os.environ.get("ESTIMACION_FACTOR", "1") or 1)


def _items(texto):
    """Cantidad de datos de un texto: líneas o elementos separados por coma o punto y coma."""
    texto = str(texto or "").strip()
    if not texto:
        return 0
    partes = [p for p in re.split(r"[\n;]|,(?!\d)", texto) if p.strip()]
    return len(partes)


def _verificaciones(resultado):
    resultado = str(resultado or "").strip()
    if not resultado:
        return 0
    return max(1, min(4, len([p for p in re.split(r"[\n;]|\.\s|\by\b(?= (el|la|los|las|se|muestra|aparece|no))", resultado) if p and p.strip()])))


def estimar_paso(accion, datos="", resultado="", es_then=False):
    texto = str(accion or "")
    cat, minutos, por_campo = "Otra acción", 0.5, False
    if re.match(r"\s*(ir|naveg|acced|abr|entr|visit)\w*\b", texto, re.I):  # "Ir a la página de login" es navegar, no iniciar sesión
        cat, minutos = "Navegar", 0.5
    else:
        for c, rx, m, x in _ACC:
            if rx.search(texto):
                cat, minutos, por_campo = c, m, x
                break
    n_datos = _items(datos)
    if por_campo:
        # Campos: los datos del paso o, si no tiene, los que nombra ("el email, el nombre y la contraseña" = 3).
        campos = max(1, n_datos or len(re.split(r",|\by\b", texto)))
        t_accion = minutos * campos
        t_datos = 0.15 * max(0, n_datos - campos)
    else:
        t_accion = minutos
        t_datos = 0.15 * max(0, n_datos - 1)
    nv = _verificaciones(resultado) or (1 if es_then else 0)
    t_verif = (0.5 + 0.25 * (nv - 1)) if nv else 0.0
    total = t_accion + t_datos + t_verif
    return {"categoria": cat, "accion": round(t_accion, 2), "datos": round(t_datos, 2), "verificacion": round(t_verif, 2),
            "minutos": round(total, 2), "segundos": int(round(total * 60))}


def _pasos_de(caso):
    """Pasos de un caso manual ({accion, datos, resultado}) o de un escenario BDD (gherkin)."""
    if caso.get("pasos"):
        pasos = caso["pasos"]
        if isinstance(pasos, str):  # "1. ...\n2. ..." (JSON de generar_casos.py)
            lineas = [re.sub(r"^\s*\d+[.)-]\s*", "", l).strip() for l in pasos.splitlines() if l.strip()]
            pasos = [{"accion": l, "datos": "", "resultado": ""} for l in lineas]
            if pasos:
                pasos[0]["datos"] = caso.get("datos", "")
                pasos[-1]["resultado"] = caso.get("resultado", "")
        return [(p.get("accion", ""), p.get("datos", ""), p.get("resultado", ""), False) for p in pasos]
    salida = []
    ultimo = None
    for l in str(caso.get("gherkin") or "").splitlines():
        m = re.match(r"\s*(Given|When|Then|And|But|\*|Dado|Cuando|Entonces|Y|Pero)\s+(.*)", l)
        if not m:
            if l.strip().startswith("|") and salida:  # tabla de datos del paso anterior
                a, d, r, t = salida[-1]
                salida[-1] = (a, (d + "\n" + l).strip(), r, t)
            continue
        kw = m.group(1)
        if kw in ("And", "But", "*", "Y", "Pero") and ultimo:
            kw = ultimo
        ultimo = kw
        salida.append((m.group(2), "", "", kw in ("Then", "Entonces")))
    return salida


def estimar_caso(caso):
    pasos = [estimar_paso(a, d, r, t) for a, d, r, t in _pasos_de(caso)]
    precond = str(caso.get("precondiciones") or "")
    n_pre = min(3, _items(precond))
    prep = 1.0 + 0.5 * n_pre + (2.0 if CREAR_DATOS.search(precond) else 0.0)
    registro = 0.5 + 0.1 * len(pasos)
    etiquetas = caso.get("etiquetas") or []
    etiquetas = etiquetas if isinstance(etiquetas, (list, tuple, set)) else [str(etiquetas)]  # el JSON de generar_casos.py trae un texto
    texto_caso = " ".join(str(caso.get(k) or "") for k in ("titulo", "descripcion")) + " " + " ".join(str(x) for x in etiquetas)
    factor = (1.1 if NEGATIVO.search(texto_caso) else 1.0) * FACTOR
    crudo = (prep + sum(p["minutos"] for p in pasos) + registro) * factor
    minutos = max(1.0, math.ceil(crudo * 2) / 2)
    fuente = "fórmula"
    try:  # un tiempo cargado a mano en la planilla (columna "Tiempo estimado (min)") manda
        manual = float(str(caso.get("tiempo_min")).replace(",", "."))
        if manual > 0:
            escala = manual / crudo if crudo else 1
            for p in pasos:  # los pasos se reparten en proporción
                p["minutos"] = round(p["minutos"] * escala, 2)
                p["segundos"] = int(round(p["minutos"] * 60))
            minutos, fuente = manual, "planilla"
    except (TypeError, ValueError):
        pass
    return {"minutos": minutos, "segundos": int(minutos * 60), "texto": formatear(minutos), "fuente": fuente, "pasos": pasos,
            "preparacion": round(prep, 2), "registro": round(registro, 2), "factor": round(factor, 2), "sin_redondear": round(crudo, 2)}


def formatear(minutos):
    """6.5 → "6,5 min"; 75 → "1 h 15 min"."""
    if minutos is None:
        return "—"
    if minutos >= 60:
        h, m = divmod(int(round(minutos)), 60)
        return f"{h} h {m} min" if m else f"{h} h"
    return (f"{minutos:g}".replace(".", ",")) + " min"


def jira_duracion(minutos):
    """Formato de Jira para Original Estimate: "1h 15m", "7m"."""
    m = int(math.ceil(minutos))
    h, r = divmod(m, 60)
    return " ".join(x for x in (f"{h}h" if h else "", f"{r}m" if r else "") if x) or "1m"


def hhmm(minutos):
    m = int(math.ceil(minutos))
    return f"{m // 60:02d}:{m % 60:02d}"


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.path.insert(0, str(Path(__file__).resolve().parent / "gestion"))
    from lectores import leer_casos
    casos = leer_casos(sys.argv[1])
    filas = [(c["id"], c["titulo"], estimar_caso(c)) for c in casos]
    if "--json" in sys.argv:
        print(json.dumps([{"id": i, "titulo": t, **e} for i, t, e in filas], ensure_ascii=False, indent=2))
        return
    total = sum(e["minutos"] for _, _, e in filas)
    for i, t, e in filas:
        print(f"{i:10} {e['texto']:>10}  {len(e['pasos']):>2} pasos  {t[:70]}")
    print(f"\n{len(filas)} caso(s) · total {formatear(total)} de ejecución manual")


if __name__ == "__main__":
    main()

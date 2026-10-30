#!/usr/bin/env python3
"""
Informe HTML (ES + EN) de los artefactos que escriben los agentes sin informe propio: casos de prueba, BDD,
reportes de bug, análisis de historias, datos de prueba, casos de API, fichas de contexto, triage, consultas,
mapeos, verificaciones de datos y la base de conocimiento. Cada artefacto queda con su HTML al lado:

    output/reportes-bug/BUG-001.md  ->  es/BUG-001.html (ES), en/BUG-001.html (EN) y BUG-001.html (acceso: abre
                                        el idioma elegido)

Uso (desde la raíz del repo):
    python scripts/generar_informe_artefacto.py <artefacto> [--salida <archivo.html>]
    python scripts/generar_informe_artefacto.py --todo [--forzar]   (todos los de output/ que cambiaron)

El inglés del contenido lo escribe el agente al lado del artefacto, con un nombre que ningún runner toma:
    Markdown (bug, análisis, datos, casos de API, contexto, cobertura, triage…)   X.md       -> X.en.md
    Datos de prueba en CSV                                                         X.csv      -> X.en.csv
    BDD                                                                            X.feature  -> X.feature.en
    Casos manuales: bloque "en" por caso (y uno general) en el JSON de generar_casos.py, que escribe
                    casos-HU-XXX.en.json al lado de la planilla.
Los valores de las escalas (prioridad, severidad, estado) salen siempre del original en español y los traduce
el diccionario (scripts/i18n/en/). Si falta la versión en inglés, el HTML en inglés muestra la interfaz en
inglés, el contenido en español y un aviso.

Desde otro script: actualizar_artefactos() regenera lo que cambió y devuelve los HTML escritos.
"""
import os
import argparse
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, nivel_badge, estado_pill,  # noqa: E402
                              bar_chart, miniatura, resolver_evidencia, e, SERIES)
from _i18n import escribir_bilingue, idioma_actual, localizar, ruta_en, ruta_es  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
OUTPUT = PROYECTO / "output"
DOCUMENTACION = PROYECTO / "input" / "documentacion"

# Carpeta de output/ -> (tipo, eyebrow). La clave puede ser "carpeta/subcarpeta".
CARPETAS = {
    "reportes-bug": ("bug", "Reporte de bug"),
    "analisis-historias": ("analisis", "Análisis de historia"),
    "casos-de-prueba/manuales": ("casos", "Casos de prueba"),
    "casos-de-prueba/bdd": ("feature", "Casos BDD (Gherkin)"),
    "contexto": ("contexto", "Ficha de contexto"),
    "triage": ("triage", "Triage de bugs"),
    "mapeos": ("md", "Mapeo a automatización"),
    "conocimiento": ("md", "Base de conocimiento"),
    "gestion": ("gestion", "Gestión de pruebas"),
}
# La documentación del proyecto (input/documentacion/, del documentador-proyecto)
# se muestra en output/documentacion/ con la misma estructura, sin tocar input/ (ver DOCUMENTACION).
AVISO_SIN_EN = "El agente no generó la versión en inglés de este artefacto: el contenido se muestra en español."
AVISO_A_PEDIDO = ("Este documento está en español: el contexto y la documentación se escriben en inglés solo a pedido "
                  "(Claude lo pregunta antes de armarlos, o DOCUMENTACION_EN=si en el .env).")
# Tipos que van en inglés solo a pedido (contexto y documentación de trabajo, no entregables).
A_PEDIDO = {"contexto", "md"}

CSS_EXTRA = """<style>
.md{line-height:1.6}.md h3{font-family:var(--display,inherit);font-size:15px;margin:18px 0 8px}.md h4{font-size:13.5px;margin:14px 0 6px}
.md p{margin:0 0 10px}.md ul,.md ol{margin:0 0 12px 20px;padding:0}.md li{margin:3px 0}
.md pre{background:var(--tile);border:1px solid var(--line-2);border-radius:10px;padding:12px;overflow:auto;font-size:12.5px}
.md blockquote{margin:0 0 12px;padding:8px 14px;border-left:3px solid var(--line-2);color:var(--muted)}
.md hr{border:0;border-top:1px solid var(--line-2);margin:16px 0}.md a{color:inherit}
.campos{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.campos div{background:var(--tile);border:1px solid var(--line-2);border-radius:10px;padding:10px 12px}
.campos b{display:block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}
.gk{display:flex;flex-direction:column;gap:14px}.gk .esc{border:1px solid var(--line-2);border-radius:12px;padding:12px 14px;background:var(--tile)}
.gk .esc h3{margin:6px 0 8px;font-size:14.5px}.gk .tags{display:flex;flex-wrap:wrap;gap:6px}
.gk .tag{font-family:var(--mono);font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid var(--line-2);color:var(--muted)}
.gk .tag.fi{color:#FFD60A;border-color:#FFD60A55}.gk ol{margin:0;padding-left:0;list-style:none}
.gk li{padding:3px 0;font-size:13.5px}.gk .kw{font-family:var(--mono);font-weight:700;color:#F9B006;margin-right:6px}
.gk .com{font-size:12.5px;color:var(--muted);margin:4px 0}.gk .ex{margin-top:10px}
</style>"""


# ------------------------------------------------------------------ rutas y tipos
def ruta_en_de(origen):
    """Dónde va el inglés que escribe el agente para este artefacto."""
    origen = Path(origen)
    sufijo = origen.suffix.lower()
    if sufijo == ".feature":
        return origen.with_name(origen.name + ".en")
    if sufijo == ".xlsx":
        return origen.with_suffix(".en.json")
    return origen.with_name(origen.stem + ".en" + origen.suffix)


def es_traduccion(p):
    n = p.name.lower()
    return n.endswith((".en.md", ".en.csv", ".en.json", ".feature.en"))


def tipo_de(origen, raiz=None):
    """(tipo, eyebrow) del artefacto según su carpeta en output/, o None si no es un artefacto de los que se convierten."""
    origen = Path(origen)
    try:
        partes = origen.resolve().relative_to(Path(raiz or OUTPUT).resolve()).parts
    except ValueError:
        partes = origen.parts[-3:]
    sufijo = origen.suffix.lower()
    if sufijo == ".json" and "gestion" in partes and not es_traduccion(origen):
        return "gestion", "Gestión de pruebas"  # trazabilidad (<HU>-<herramienta>.json) y resultados publicados
    if es_traduccion(origen) or sufijo not in (".md", ".csv", ".feature", ".xlsx"):
        return None
    for clave, (tipo, eyebrow) in CARPETAS.items():
        segs = clave.split("/")
        for i in range(len(partes) - len(segs)):
            if list(partes[i:i + len(segs)]) == segs:
                if tipo == "casos":
                    if sufijo == ".xlsx":
                        return "casos", eyebrow
                    if origen.name.endswith("-cobertura.md"):
                        return "cobertura", "Cobertura de los casos"
                    return (None if origen.with_suffix(".xlsx").exists() else ("md", eyebrow))
                if tipo == "feature":
                    if sufijo == ".feature":
                        return "feature", eyebrow
                    return ("cobertura", "Cobertura de los escenarios BDD") if sufijo == ".md" else None
                if tipo == "datos":
                    if sufijo == ".csv" and origen.with_suffix(".md").exists():
                        return None
                    return ("datos", eyebrow) if sufijo in (".md", ".csv") else None
                if tipo == "triage" and origen.name != "triage.md":
                    return ("md", eyebrow) if sufijo == ".md" else None
                return (tipo, eyebrow) if sufijo == ".md" else None
    return None


def html_de(origen):
    return Path(origen).with_suffix(".html")


# ------------------------------------------------------------------ markdown
_CODE = re.compile(r"`([^`]+)`")


def inline(texto):
    """Markdown en línea (código, negrita, itálica, links) sobre texto ya escapado."""
    codigos = []

    def guardar(m):
        codigos.append(m.group(1))
        return f"\x00{len(codigos) - 1}\x00"

    s = _CODE.sub(guardar, str(texto))
    s = e(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{e(codigos[int(m.group(1))])}</code>", s)


def celda(texto):
    return "<br>".join(inline(x) for x in str(texto or "").split("\n"))


def tabla_grid(lineas):
    """Tabla ASCII de tabulate (grid, la de formatear_tablas.py) -> (encabezados, filas), o None."""
    lineas = [l.rstrip() for l in lineas if l.strip()]
    if not lineas or not re.match(r"^\+[-=+:]+\+$", lineas[0]):
        return None
    sep = lineas[0]
    pos = [i for i, ch in enumerate(sep) if ch == "+"]

    def celdas(linea):
        if len(linea) == len(sep) and all(i < len(linea) and linea[i] == "|" for i in pos):
            return [linea[a + 1:b].strip() for a, b in zip(pos, pos[1:])]
        partes = linea.strip().strip("|").split("|")
        return [p.strip() for p in partes] + [""] * (len(pos) - 1 - len(partes))

    encabezados, filas, bloque = None, [], []
    for linea in lineas[1:]:
        if linea.startswith("+"):
            if bloque:
                unidas = [_unir([b[i] for b in bloque]) for i in range(len(pos) - 1)]
                if "=" in linea and encabezados is None:
                    encabezados = unidas
                else:
                    filas.append(unidas)
            bloque = []
        elif linea.startswith("|"):
            bloque.append(celdas(linea)[:len(pos) - 1])
    if encabezados is None and filas:
        encabezados, filas = filas[0], filas[1:]
    return (encabezados, filas) if encabezados else None


def _unir(lineas):
    """Las líneas de una celda ajustada: une el texto cortado y respeta listas y pares "Clave: valor"."""
    out = ""
    for l in lineas:
        l = l.strip()
        if not l:
            continue
        if not out:
            out = l
        elif re.match(r"^(\d+[.)]|[-•*]|@|[^\s:]{1,25}:\s)", l):
            out += "\n" + l
        else:
            out += " " + l
    return out


def tabla_md(lineas):
    """Tabla Markdown cruda (| a | b | + |---|) -> (encabezados, filas)."""
    def cel(l):
        s = l.strip()
        s = s[1:] if s.startswith("|") else s
        s = s[:-1] if s.endswith("|") else s
        return [c.strip().replace("<br>", "\n") for c in s.split("|")]
    cab = cel(lineas[0])
    return cab, [(cel(l) + [""] * len(cab))[:len(cab)] for l in lineas[2:]]


def bloques(md):
    """Markdown -> lista de bloques: (tipo, datos)."""
    lineas = md.replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lineas)
    while i < n:
        l = lineas[i]
        s = l.strip()
        if s.startswith("```"):
            lang = s[3:].strip()
            j = i + 1
            while j < n and not lineas[j].strip().startswith("```"):
                j += 1
            contenido = lineas[i + 1:j]
            grid = tabla_grid(contenido)
            out.append(("tabla", grid) if grid else ("codigo", (lang, "\n".join(contenido))))
            i = j + 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            out.append(("titulo", (len(m.group(1)), m.group(2).strip().rstrip("#").strip())))
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s):
            out.append(("hr", None))
            i += 1
            continue
        if "|" in s and i + 1 < n and re.match(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$", lineas[i + 1]):
            j = i + 2
            while j < n and "|" in lineas[j] and lineas[j].strip():
                j += 1
            out.append(("tabla", tabla_md(lineas[i:j])))
            i = j
            continue
        if re.match(r"^\+[-=+]+\+$", s):  # tabla ASCII fuera de un bloque de código
            j = i
            while j < n and lineas[j].strip().startswith(("+", "|")):
                j += 1
            grid = tabla_grid(lineas[i:j])
            if grid:
                out.append(("tabla", grid))
                i = j
                continue
        if s.startswith(">"):
            j = i
            while j < n and lineas[j].strip().startswith(">"):
                j += 1
            out.append(("cita", " ".join(x.strip()[1:].strip() for x in lineas[i:j])))
            i = j
            continue
        if re.match(r"^([-*+]|\d+[.)])\s+", s):
            ordenada = bool(re.match(r"^\d+[.)]", s))
            items = []
            j = i
            while j < n:
                t = lineas[j]
                ts = t.strip()
                if re.match(r"^([-*+]|\d+[.)])\s+", ts):
                    items.append(re.sub(r"^([-*+]|\d+[.)])\s+", "", ts))
                elif ts and items and (t.startswith(("  ", "\t"))):
                    items[-1] += " " + ts
                else:
                    break
                j += 1
            out.append(("lista", (ordenada, items)))
            i = j
            continue
        if not s:
            i += 1
            continue
        j = i
        parrafo = []
        while j < n and lineas[j].strip() and not re.match(r"^(#{1,6}\s|```|>|([-*+]|\d+[.)])\s+|\+[-=+]+\+$)", lineas[j].strip()):
            if "|" in lineas[j] and j + 1 < n and re.match(r"^\s*\|?\s*:?-+:?", lineas[j + 1]) and "-" in lineas[j + 1]:
                break
            parrafo.append(lineas[j].strip())
            j += 1
        out.append(("parrafo", "\n".join(parrafo)))
        i = max(j, i + 1)
    return out


def _texto_html(tipo, datos):
    if tipo == "parrafo":
        return f"<p>{celda(datos)}</p>"
    if tipo == "lista":
        ordenada, items = datos
        tag = "ol" if ordenada else "ul"
        return f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>"
    if tipo == "codigo":
        return f"<pre><code>{e(datos[1])}</code></pre>"
    if tipo == "cita":
        return f"<blockquote>{inline(datos)}</blockquote>"
    if tipo == "hr":
        return "<hr>"
    if tipo == "titulo":
        nivel, texto = datos
        h = min(max(nivel, 3), 4)
        return f"<h{h}>{inline(texto)}</h{h}>"
    return ""


def tabla_html(datos):
    cab, filas = datos
    return table(cab, [[celda(c) for c in f] for f in filas])


def render_bloques(bls):
    """Bloques -> HTML de una tarjeta: el texto en cardbody y cada tabla con el buscador y filtros de la casa."""
    html, texto = "", ""
    for tipo, datos in bls:
        if tipo == "tabla":
            if texto:
                html += f'<div class="cardbody md">{texto}</div>'
                texto = ""
            html += tabla_html(datos)
        else:
            texto += _texto_html(tipo, datos)
    if texto:
        html += f'<div class="cardbody md">{texto}</div>'
    return html


def partir_secciones(bls):
    """(título H1, [(título de sección, bloques)]): cada H2 es una tarjeta; lo anterior al primer H2, "Resumen"."""
    titulo, secciones, actual = "", [], ("", [])
    for tipo, datos in bls:
        if tipo == "titulo" and datos[0] == 1 and not titulo:
            titulo = datos[1]
            continue
        if tipo == "titulo" and datos[0] <= 2:
            if actual[1] or actual[0]:
                secciones.append(actual)
            actual = (datos[1], [])
            continue
        actual[1].append((tipo, datos))
    if actual[1] or actual[0]:
        secciones.append(actual)
    return titulo, [(t or "Resumen", b) for t, b in secciones]


def secciones_html(secs):
    return "".join(section(re.sub(r"[*`]", "", t), render_bloques(b)) for t, b in secs if b)


def leer(p):
    return Path(p).read_text(encoding="utf-8-sig")


# ------------------------------------------------------------------ utilidades
def ids_fi(texto):
    return sorted(set(re.findall(r"\bFI-\d{2,}\b", texto or "")))


def historia_de(origen, texto=""):
    m = re.search(r"\bHU-\d+\b", Path(origen).name) or re.search(r"\bHU-\d+\b", texto or "")
    return m.group(0) if m else ""


def _fecha(p):
    from datetime import datetime
    return datetime.fromtimestamp(Path(p).stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def _meta(origen, texto="", extra=()):
    return meta([("Historia", historia_de(origen, texto)), ("Archivo", Path(origen).name), ("Generado", _fecha(origen)), *extra])


def _aviso_en(hay_en, tipo=None):
    if idioma_actual() != "en" or hay_en:
        return ""
    return banner(AVISO_A_PEDIDO if tipo in A_PEDIDO else AVISO_SIN_EN, "warn")


def _cuenta_en(secs, patron, contar):
    total = 0
    for t, bls in secs:
        if re.search(patron, t, re.I):
            total += contar(bls)
    return total


def _items(bls):
    n = 0
    for tipo, d in bls:
        if tipo == "lista":
            n += len(d[1])
        elif tipo == "tabla":
            n += len(d[1])
    return n


def _preguntas(bls):
    n = 0
    for tipo, d in bls:
        if tipo == "lista":
            n += sum(1 for x in d[1] if "?" in x)
        elif tipo == "tabla":
            n += sum(1 for f in d[1] if any("?" in c for c in f))
        elif tipo == "parrafo":
            n += d.count("?")
    return n


def _texto_de(origen, origen_en):
    """(texto en el idioma actual, hay inglés)."""
    hay_en = origen_en is not None and Path(origen_en).exists()
    if idioma_actual() == "en" and hay_en:
        return leer(origen_en), True
    return leer(origen), hay_en


# ------------------------------------------------------------------ bug
CAMPOS_BUG = {
    "id": "id", "título": "titulo", "titulo": "titulo", "title": "titulo", "historia": "historia", "story": "historia",
    "user story": "historia", "estado": "estado", "status": "estado", "descripción": "descripcion", "descripcion": "descripcion",
    "description": "descripcion", "precondiciones": "precondiciones", "preconditions": "precondiciones", "test data": "datos",
    "datos de prueba": "datos", "pasos de reproducción": "pasos", "pasos de reproduccion": "pasos", "steps to reproduce": "pasos",
    "resultado actual": "actual", "actual result": "actual", "resultado esperado": "esperado", "expected result": "esperado",
    "evidencia": "evidencia", "evidence": "evidencia", "criticidad / severidad": "severidad", "severidad": "severidad",
    "criticidad": "severidad", "severity": "severidad", "criticality / severity": "severidad", "prioridad": "prioridad",
    "priority": "prioridad", "test case asociado": "caso", "related test case": "caso", "test case": "caso",
    "versión": "version", "version": "version", "browser": "browser", "navegador": "browser", "ambiente": "ambiente",
    "environment": "ambiente",
}
TITULOS_BUG = [("descripcion", "Descripción"), ("precondiciones", "Precondiciones"), ("datos", "Datos de prueba"),
               ("pasos", "Pasos de reproducción")]


def parsear_bug(texto):
    """Campos del bloque vertical de la plantilla (**Campo:** valor) y el resto como Markdown."""
    campos, resto, actual = {}, [], None
    for linea in texto.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^\s*\*\*(.+?):\*\*\s*(.*)$", linea)
        clave = CAMPOS_BUG.get(re.sub(r"\s+", " ", m.group(1)).strip().lower()) if m else None
        if clave:
            actual = clave
            campos[clave] = m.group(2).strip()
            continue
        if re.match(r"^\s*(#{1,6}\s|---\s*$)", linea):
            actual = None
        if actual:
            campos[actual] += "\n" + linea
        else:
            resto.append(linea)
    limpio = {k: v.strip().strip("`").strip() for k, v in campos.items()}
    return limpio, "\n".join(resto)


def _valor_escala(v):
    v = re.sub(r"[`*]", "", v or "").strip()
    return re.split(r"\s+[—·(-]\s*|\s{2,}", v)[0].strip()


def render_bug(origen, origen_en):
    es, _ = parsear_bug(leer(origen))
    texto, hay_en = _texto_de(origen, origen_en)
    c, resto = parsear_bug(texto)
    base = Path(origen).resolve().parent
    sev, pri, est = _valor_escala(es.get("severidad")), _valor_escala(es.get("prioridad")), _valor_escala(es.get("estado"))
    kpis = [("Severidad", sev or "—", "bad" if sev in ("Crítica", "Alta") else ("warn" if sev else ""), "", "bicho"),
            ("Prioridad", pri or "—", "bad" if pri in ("Crítica", "Alta") else ("warn" if pri else ""), "", "objetivo"),
            ("Estado", est or "—", "", "", "lista")]
    if es.get("caso"):
        kpis.append(("Caso asociado", _valor_escala(es["caso"]), "", "", "lista"))
    cuerpo = CSS_EXTRA + _aviso_en(hay_en) + section("Resumen", kpi_tiles(kpis))
    for clave, titulo in TITULOS_BUG:
        if c.get(clave):
            cuerpo += section(titulo, render_bloques(bloques(c[clave])))
    if c.get("actual") or c.get("esperado"):
        cuerpo += section("Resultado actual", render_bloques(bloques(c.get("actual") or "—")), ancho=6)
        cuerpo += section("Resultado esperado", render_bloques(bloques(c.get("esperado") or "—")), ancho=6)
    if c.get("evidencia"):
        imgs = re.findall(r"[\w./\\-]+\.(?:png|jpe?g|gif|webp)", c["evidencia"], re.I)
        mini = ""
        for ruta in imgs:
            r, existe = resolver_evidencia(ruta, base)
            mini += miniatura(r, ruta, existe=existe)
        cuerpo += section("Evidencia", (f'<div class="cardbody">{mini}</div>' if mini else "") + render_bloques(bloques(c["evidencia"])))
    entorno = [("Browser", c.get("browser")), ("Versión", c.get("version")), ("Ambiente", c.get("ambiente"))]
    entorno = [(k, v) for k, v in entorno if v]
    if entorno:
        cuerpo += section("Entorno", '<div class="cardbody"><div class="campos">' + "".join(
            f"<div><b>{e(k)}</b>{celda(v)}</div>" for k, v in entorno) + "</div></div>")
    _, secs = partir_secciones(bloques(resto))
    cuerpo += secciones_html([(t, b) for t, b in secs if any(x[0] != "hr" for x in b)])
    titulo = re.sub(r"`", "", f'{c.get("id") or Path(origen).stem} — {c.get("titulo") or ""}').strip(" —")
    return page(titulo, "Reporte de bug", _meta(origen, texto, [("Severidad", sev), ("Prioridad", pri)]), cuerpo)


# ------------------------------------------------------------------ casos manuales
COLS_XLSX = ["id", "titulo", "descripcion", "precondiciones", "datos", "pasos", "resultado", "estado", "prioridad",
             "tiempo_min", "etiquetas", "evidencia", "fecha_ejecucion", "comentarios"]
FI_KEYS = ["id", "que_falta", "donde_se_busco", "impacto", "pregunta", "estado"]
ORDEN_PRIO = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}


def leer_casos_xlsx(ruta):
    from openpyxl import load_workbook
    wb = load_workbook(ruta, data_only=True)
    ws = wb.worksheets[0]
    modulo = str(ws["A2"].value or "").replace("Módulo:", "").strip()
    casos = []
    for fila in ws.iter_rows(min_row=4, values_only=True):
        if not fila or not fila[0]:
            break  # después de los casos vienen el total y la nota de "Falta información"
        caso = {k: ("" if v is None else v) for k, v in zip(COLS_XLSX, fila)}
        caso["_fi"] = ", ".join(ids_fi(str(caso.get("comentarios", "")) + " " + str(caso.get("etiquetas", ""))))
        casos.append(caso)
    fi = []
    if "Falta información" in wb.sheetnames:
        for fila in wb["Falta información"].iter_rows(min_row=3, values_only=True):
            if fila and fila[0]:
                fi.append({k: ("" if v is None else v) for k, v in zip(FI_KEYS, fila)})
    return {"proyecto": str(ws["A1"].value or ""), "modulo": modulo, "casos": casos, "falta_informacion": fi}


def localizar_profundo(obj, codigo="en"):
    """Alias de _i18n.localizar (que ya mezcla los bloques "en" de cada ítem de una lista)."""
    return localizar(obj, codigo)


def casos_en_ingles(data, data_en):
    """Los textos del .en.json sobre los casos en español (por id); las escalas quedan las del original."""
    out = json.loads(json.dumps(data, default=str))
    por_id = {str(c.get("id")): c for c in data_en.get("casos", []) if isinstance(c, dict)}
    for c in out["casos"]:
        tr = por_id.get(str(c.get("id"))) or {}
        for k in ("titulo", "descripcion", "precondiciones", "datos", "pasos", "resultado", "comentarios"):
            if tr.get(k):
                c[k] = tr[k]
    fi_en = {str(f.get("id")): f for f in data_en.get("falta_informacion", []) or [] if isinstance(f, dict)}
    for f in out.get("falta_informacion", []):
        for k in ("que_falta", "donde_se_busco", "impacto", "pregunta"):
            if (fi_en.get(str(f.get("id"))) or {}).get(k):
                f[k] = fi_en[str(f["id"])][k]
    if data_en.get("modulo"):
        out["modulo"] = data_en["modulo"]
    return out


def render_casos(origen, origen_en):
    data = leer_casos_xlsx(origen)
    hay_en = origen_en is not None and Path(origen_en).exists()
    if idioma_actual() == "en" and hay_en:
        data = casos_en_ingles(data, json.loads(leer(origen_en)))
    casos = sorted(data["casos"], key=lambda c: ORDEN_PRIO.get(str(c.get("prioridad")), 9))
    prio = Counter(str(c.get("prioridad") or "—") for c in casos)
    estados = Counter(str(c.get("estado") or "—") for c in casos)
    try:
        total_min = sum(float(str(c.get("tiempo_min") or 0).replace(",", ".")) for c in casos)
    except ValueError:
        total_min = 0
    con_fi = sum(1 for c in casos if c.get("_fi"))
    altos = prio.get("Crítica", 0) + prio.get("Alta", 0)
    kpis = [("Casos", len(casos), "", f"{altos} crítico(s) o alto(s)", "lista"),
            ("Tiempo estimado", f"{total_min:.0f} min" if total_min else "—", "", "ejecución manual", "reloj"),
            ("Falta información", con_fi, "warn" if con_fi else "ok", "casos que dependen de un dato sin definir", "lupa")]
    cuerpo = CSS_EXTRA + _aviso_en(hay_en)
    cuerpo += section("Resumen", kpi_tiles(kpis))
    if casos:
        cuerpo += section("Por prioridad", bar_chart([(p, n, SERIES[i % len(SERIES)]) for i, (p, n) in
                          enumerate(sorted(prio.items(), key=lambda x: ORDEN_PRIO.get(x[0], 9)))]), ancho=6)
        cuerpo += section("Por estado", bar_chart([(s, n, SERIES[(i + 2) % len(SERIES)]) for i, (s, n) in enumerate(estados.most_common())]), ancho=6)
        filas = [[f'<span class="id">{e(c.get("id"))}</span>', celda(c.get("titulo")), nivel_badge(str(c.get("prioridad") or "")),
                  estado_pill(str(c.get("estado") or "")), e(c.get("tiempo_min") or ""), celda(c.get("etiquetas"))] for c in casos]
        cuerpo += section("Casos", table(["ID", "Título", "Prioridad", "Estado", "Tiempo (min)", "Etiquetas"], filas))
        filas = [[f'<span class="id">{e(c.get("id"))}</span>', celda(c.get("titulo")), celda(c.get("precondiciones")),
                  celda(c.get("datos")), celda(c.get("pasos")), celda(c.get("resultado")), celda(c.get("comentarios"))] for c in casos]
        cuerpo += section("Detalle de los casos", table(["ID", "Título", "Precondiciones", "Datos de prueba", "Pasos",
                                                         "Resultado esperado", "Comentarios"], filas))
    fi = data.get("falta_informacion") or []
    if fi:
        cuerpo += section("Falta información", table(["ID", "Qué falta", "Dónde se buscó", "Impacto", "Pregunta para el PO", "Estado"],
                          [[e(f.get("id")), celda(f.get("que_falta")), celda(f.get("donde_se_busco")), celda(f.get("impacto")),
                            celda(f.get("pregunta")), estado_pill(str(f.get("estado") or "Abierto"))] for f in fi]))
    titulo = f'Casos de prueba — {data.get("modulo") or Path(origen).stem}'
    return page(titulo, "Casos de prueba", _meta(origen, data.get("modulo", ""), [("Proyecto", data.get("proyecto"))]), cuerpo)


# ------------------------------------------------------------------ BDD
_KW_ESC = r"(Scenario Outline|Scenario Template|Scenario|Example|Escenario|Esquema del escenario|Ejemplo)"
_KW_PASO = r"(Given|When|Then|And|But|\*|Dado|Dada|Cuando|Entonces|Y|E|Pero)"


def parsear_feature(texto):
    """Gherkin -> {"feature", "descripcion", "tags", "background", "escenarios": [...]}."""
    f = {"feature": "", "descripcion": [], "tags": [], "background": None, "escenarios": []}
    tags, comentarios, actual, en_doc = [], [], None, False
    for crudo in texto.replace("\r\n", "\n").split("\n"):
        l = crudo.strip()
        if l.startswith('"""') or l.startswith("```"):
            en_doc = not en_doc
            if actual is not None and actual["pasos"]:
                actual["pasos"][-1]["doc"] = actual["pasos"][-1].get("doc", "") + ("" if en_doc else "")
            continue
        if en_doc:
            if actual is not None and actual["pasos"]:
                actual["pasos"][-1]["doc"] = (actual["pasos"][-1].get("doc", "") + "\n" + crudo.strip()).strip()
            continue
        if not l:
            continue
        if l.startswith("#"):
            if not l.lower().startswith("# language"):
                comentarios.append(l.lstrip("#").strip())
            continue
        if l.startswith("@"):
            tags += re.findall(r"@[^\s@]+", l)
            continue
        m = re.match(r"^(Feature|Característica|Funcionalidad):\s*(.*)$", l)
        if m:
            f["feature"], f["tags"], tags, comentarios = m.group(2), tags, [], []
            continue
        m = re.match(r"^(Background|Antecedentes):\s*(.*)$", l)
        if m:
            actual = {"tipo": "Background", "nombre": m.group(2), "tags": [], "pasos": [], "ejemplos": [], "comentarios": comentarios}
            f["background"], tags, comentarios = actual, [], []
            continue
        m = re.match(rf"^{_KW_ESC}:\s*(.*)$", l)
        if m:
            outline = bool(re.search(r"Outline|Template|Esquema", m.group(1)))
            actual = {"tipo": "Scenario Outline" if outline else "Scenario", "nombre": m.group(2), "tags": tags,
                      "pasos": [], "ejemplos": [], "comentarios": comentarios}
            f["escenarios"].append(actual)
            tags, comentarios = [], []
            continue
        m = re.match(r"^(Examples|Scenarios|Ejemplos|Escenarios):\s*(.*)$", l)
        if m and actual is not None:
            actual["ejemplos"].append({"nombre": m.group(2), "tags": tags, "filas": []})
            tags = []
            continue
        if l.startswith("|") and actual is not None:
            fila = [c.strip() for c in l.strip().strip("|").split("|")]
            if actual["ejemplos"]:
                actual["ejemplos"][-1]["filas"].append(fila)
            elif actual["pasos"]:
                actual["pasos"][-1].setdefault("tabla", []).append(fila)
            continue
        m = re.match(rf"^{_KW_PASO}\s+(.*)$", l)
        if m and actual is not None:
            actual["pasos"].append({"kw": m.group(1), "texto": m.group(2)})
            if comentarios:
                actual["comentarios"] += comentarios
                comentarios = []
            continue
        if actual is None:
            f["descripcion"].append(l)
    return f


def _tags_html(tags):
    return '<div class="tags">' + "".join(
        f'<span class="tag{" fi" if re.match(r"@(falta-info|FI-)", t, re.I) else ""}">{e(t)}</span>' for t in tags) + "</div>"


def _escenario_html(esc):
    pasos = ""
    for p in esc["pasos"]:
        extra = ""
        if p.get("tabla"):
            extra += table(p["tabla"][0], p["tabla"][1:]) if len(p["tabla"]) > 1 else ""
        if p.get("doc"):
            extra += f"<pre><code>{e(p['doc'])}</code></pre>"
        pasos += f'<li><span class="kw">{e(p["kw"])}</span>{inline(p["texto"])}{extra}</li>'
    com = "".join(f'<div class="com"># {inline(c)}</div>' for c in esc.get("comentarios") or [])
    ej = ""
    for x in esc["ejemplos"]:
        if x["filas"]:
            ej += (f'<div class="ex">{_tags_html(x["tags"]) if x["tags"] else ""}<b>Examples{": " + e(x["nombre"]) if x["nombre"] else ""}</b>'
                   + table(x["filas"][0], [[e(c) for c in f] for f in x["filas"][1:]]) + "</div>")
    return (f'<div class="esc">{_tags_html(esc["tags"]) if esc["tags"] else ""}<h3><span class="kw">{e(esc["tipo"])}:</span>{inline(esc["nombre"])}</h3>'
            f'{com}<ol>{pasos}</ol>{ej}</div>')


def render_feature(origen, origen_en):
    es = parsear_feature(leer(origen))
    texto, hay_en = _texto_de(origen, origen_en)
    f = parsear_feature(texto)
    escs = f["escenarios"]
    outlines = [x for x in escs if x["tipo"] == "Scenario Outline"]
    filas_ej = sum(max(0, len(x["filas"]) - 1) for s in escs for x in s["ejemplos"])
    todos_tags = Counter(t for s in es["escenarios"] for t in s["tags"])
    con_fi = sum(1 for s in es["escenarios"] if any(re.match(r"@(falta-info|FI-)", t, re.I) for t in s["tags"]))
    kpis = [("Escenarios", len(escs), "", f"{len(outlines)} Scenario Outline", "lista"),
            ("Ejemplos", filas_ej, "", "filas de Examples", "grid"),
            ("Falta información", con_fi, "warn" if con_fi else "ok", "escenarios con @falta-info", "lupa")]
    cuerpo = CSS_EXTRA + _aviso_en(hay_en) + section("Resumen", kpi_tiles(kpis) + (
        f'<div class="cardbody md"><p>{celda(chr(10).join(f["descripcion"]))}</p></div>' if f["descripcion"] else "")
        + (f'<div class="cardbody gk">{_tags_html(f["tags"])}</div>' if f["tags"] else ""))
    etiquetas = [(t, n) for t, n in todos_tags.most_common() if not re.match(r"@(HU|CP)-", t)]
    if etiquetas:
        cuerpo += section("Etiquetas", bar_chart([(t, n, SERIES[i % len(SERIES)]) for i, (t, n) in enumerate(etiquetas[:12])]), ancho=6)
    filas = []
    for s_es, s in zip(es["escenarios"], escs):
        cp = next((t[1:] for t in s_es["tags"] if re.match(r"@CP(-API)?-\d+", t)), "—")
        filas.append([f'<span class="id">{e(cp)}</span>', inline(s["nombre"]), e(s_es["tipo"]),
                      e(" ".join(t for t in s_es["tags"] if not re.match(r"@(HU|CP)", t))), e(len(s["pasos"]))])
    if filas:
        cuerpo += section("Índice de escenarios", table(["ID", "Escenario", "Tipo", "Etiquetas", "Pasos"], filas), ancho=6 if etiquetas else 12)
    if f["background"]:
        cuerpo += section("Antecedentes", f'<div class="cardbody gk">{_escenario_html(f["background"])}</div>')
    if escs:
        cuerpo += section("Escenarios", '<div class="cardbody gk">' + "".join(_escenario_html(s) for s in escs) + "</div>")
    titulo = f["feature"] or es["feature"] or Path(origen).stem
    return page(titulo, "Casos BDD (Gherkin)", _meta(origen, texto, [("Feature", Path(origen).name)]), cuerpo)


# ------------------------------------------------------------------ Markdown con KPIs según el tipo
def _kpis_md(tipo, texto, secs):
    fi = len(ids_fi(texto))
    tono_fi = "warn" if fi else "ok"
    if tipo == "analisis":
        return [("Ambigüedades", _cuenta_en(secs, r"ambig", _items), "", "", "lupa"),
                ("Preguntas", _cuenta_en(secs, r"pregunt|question", _preguntas), "", "para el refinamiento", "lupa"),
                ("Riesgos", _cuenta_en(secs, r"riesgo|risk", _items), "", "", "escudo"),
                ("Falta información", fi, tono_fi, "FI-XX", "lupa")]
    if tipo == "contexto":
        return [("Fuentes", _cuenta_en(secs, r"fuente|source", _items), "", "consultadas", "lista"),
                ("Falta información", fi, tono_fi, "FI-XX", "lupa")]
    if tipo == "casos-api":
        ids = set(re.findall(r"\bCP-API-\d+\b", texto))
        endpoints = set(re.findall(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/\S*)", texto))
        return [("Casos", len(ids), "", "CP-API", "lista"), ("Endpoints", len(endpoints), "", "", "link"),
                ("Falta información", fi, tono_fi, "FI-XX", "lupa")]
    if tipo == "cobertura":
        cas = set(re.findall(r"\bCA\d+\b", texto))
        sin = len(re.findall(r"\b(Sin cubrir|No cubierto|Not covered)\b", texto, re.I))
        return [("Criterios", len(cas), "", "de aceptación", "objetivo"),
                ("Sin cubrir", sin, "bad" if sin else "ok", "", "escudo"), ("Falta información", fi, tono_fi, "FI-XX", "lupa")]
    if tipo == "triage":
        return [("Duplicados probables", len(re.findall(r"Duplicado probable|Probable duplicate", texto, re.I)), "", "", "bicho"),
                ("Relacionados", len(re.findall(r"\bRelacionado\b|\bRelated\b", texto, re.I)), "", "", "link"),
                ("Posibles regresiones", len(re.findall(r"regresi[óo]n|regression", texto, re.I)), "", "", "warn")]
    if tipo == "datos":
        tablas = [d for _, b in secs for t, d in b if t == "tabla"]
        principal = max(tablas, key=lambda d: len(d[1])) if tablas else None
        kpis = [("Filas de datos", len(principal[1]) if principal else 0, "", "", "grid")]
        if principal:
            col = next((i for i, h in enumerate(principal[0]) if re.match(r"^(tipo|type)$", h.strip(), re.I)), None)
            if col is not None:
                tipos = Counter(re.split(r"\s*\(", f[col])[0].strip() for f in principal[1] if col < len(f))
                kpis += [(t, n, "", "", "lista") for t, n in tipos.most_common(4)]
        return kpis + [("Falta información", fi, tono_fi, "FI-XX", "lupa")]
    return [("Secciones", len(secs), "", "", "lista"), ("Falta información", fi, tono_fi, "FI-XX", "lupa")]


def _csv_a_md(texto):
    filas = list(csv.reader(io.StringIO(texto), delimiter=";" if texto.count(";") >= texto.count(",") else ","))
    filas = [f for f in filas if any(c.strip() for c in f)]
    if not filas:
        return ""
    return "\n".join(["| " + " | ".join(c.replace("|", "/") for c in f) + " |" for f in filas[:1]]
                     + ["|" + "---|" * len(filas[0])] + ["| " + " | ".join(c.replace("|", "/").replace("\n", "<br>") for c in f) + " |" for f in filas[1:]])


def render_md(origen, origen_en, tipo, eyebrow):
    texto, hay_en = _texto_de(origen, origen_en)
    if Path(origen).suffix.lower() == ".csv":
        texto = _csv_a_md(texto)
    titulo, secs = partir_secciones(bloques(texto))
    cuerpo = CSS_EXTRA + _aviso_en(hay_en, tipo) + section("Resumen", kpi_tiles(_kpis_md(tipo, texto, secs)))
    if secs and secs[0][0] == "Resumen":
        cuerpo = CSS_EXTRA + _aviso_en(hay_en, tipo) + section("Resumen", kpi_tiles(_kpis_md(tipo, texto, secs)) + render_bloques(secs[0][1]))
        secs = secs[1:]
    cuerpo += secciones_html(secs)
    titulo = re.sub(r"[*`]", "", titulo) or Path(origen).stem
    return page(titulo, eyebrow, _meta(origen, texto), cuerpo)


# ------------------------------------------------------------------ entrada
def generar(origen, salida=None, raiz=None):
    """Escribe el HTML del artefacto en es/ y en/ (y el acceso al lado del artefacto). Devuelve la ruta del acceso."""
    origen = Path(origen)
    detectado = tipo_de(origen, raiz)
    if not detectado:
        if origen.suffix.lower() == ".feature":
            detectado = ("feature", "Casos BDD (Gherkin)")
        elif origen.suffix.lower() == ".xlsx":
            detectado = ("casos", "Casos de prueba")
        elif origen.suffix.lower() in (".md", ".csv"):
            detectado = ("md", "Documento")
        else:
            raise ValueError(f"No sé convertir {origen}")
    tipo, eyebrow = detectado
    salida = Path(salida) if salida else html_de(origen)
    origen_en = ruta_en_de(origen)
    if tipo == "bug":
        render = lambda: render_bug(origen, origen_en)  # noqa: E731
    elif tipo == "casos":
        render = lambda: render_casos(origen, origen_en)  # noqa: E731
    elif tipo == "feature":
        render = lambda: render_feature(origen, origen_en)  # noqa: E731
    elif tipo == "gestion":
        render = lambda: render_gestion(origen)  # noqa: E731
    else:
        render = lambda: render_md(origen, origen_en, tipo, eyebrow)  # noqa: E731
    escribir_bilingue(salida, render)
    return salida


def artefactos(raiz_output=None):
    """Todos los artefactos convertibles de output/."""
    raiz = Path(raiz_output or OUTPUT)
    for clave in CARPETAS:
        carpeta = raiz / clave
        if not carpeta.is_dir():
            continue
        for p in sorted(carpeta.rglob("*")):
            if p.is_file() and "historial" not in p.parts and tipo_de(p, raiz):
                yield p


def _al_dia(destino, fuentes):
    """¿Las dos versiones (es/ y en/) existen y son más nuevas que el artefacto y su inglés?"""
    versiones = [ruta_es(destino), ruta_en(destino)]
    if not destino.exists() or not all(v.exists() for v in versiones):
        return False
    return min(v.stat().st_mtime for v in versiones) >= max(f.stat().st_mtime for f in fuentes)


def documentos_del_proyecto(documentacion=None):
    """Los Markdown de la documentación del proyecto (input/documentacion/), sin sus versiones en inglés."""
    base = Path(documentacion or DOCUMENTACION)
    if not base.is_dir():
        return []
    return [p for p in sorted(base.rglob("*.md")) if not es_traduccion(p) and "historial" not in p.parts]


def actualizar_artefactos(raiz_output=None, forzar=False, documentacion=None):
    """Regenera el HTML de cada artefacto de output/ cuyo origen (o su inglés) es más nuevo que el HTML, y el de la
    documentación del proyecto (input/documentacion/ -> output/documentacion/). Rápido e idempotente; lo llama el
    portal antes de indexar. Devuelve los HTML escritos (los accesos; las versiones van en es/ y en/)."""
    raiz = Path(raiz_output or OUTPUT)
    escritos = []
    for origen in artefactos(raiz):
        destino = html_de(origen)
        fuentes = [origen] + [x for x in [ruta_en_de(origen)] if x.exists()]
        if not forzar and _al_dia(destino, fuentes):
            continue
        try:
            escritos.append(generar(origen, raiz=raiz))
        except Exception as ex:  # un artefacto mal formado no frena al resto
            print(f"[aviso] {origen}: no se pudo armar el HTML ({type(ex).__name__}: {ex})", file=sys.stderr)
    if documentacion is None and raiz_output is None:
        documentacion = DOCUMENTACION
    if documentacion:
        base = Path(documentacion)
        for origen in documentos_del_proyecto(base):
            destino = raiz / "documentacion" / origen.relative_to(base).with_suffix(".html")
            fuentes = [origen] + [x for x in [ruta_en_de(origen)] if x.exists()]
            if not forzar and _al_dia(destino, fuentes):
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            try:
                escribir_bilingue(destino, lambda o=origen: render_md(o, ruta_en_de(o), "md", "Documentación del proyecto"))
                escritos.append(destino)
            except Exception as ex:
                print(f"[aviso] {origen}: no se pudo armar el HTML ({type(ex).__name__}: {ex})", file=sys.stderr)
    return escritos


def render_gestion(origen):
    """Trazabilidad con la herramienta de gestión (<HU>-<herramienta>.json: qué CP-XXX es qué key, ciclos) o los
    resultados que se publicaron (resultados-<fecha>.json: estado de cada escenario y evidencias)."""
    datos = json.loads(Path(origen).read_text(encoding="utf-8"))
    cuerpo = ""
    if isinstance(datos, dict):  # trazabilidad
        casos = datos.get("casos") or {}
        ciclos = datos.get("ciclos") or []
        sin_vinculo = sum(1 for c in casos.values() if isinstance(c, dict) and c.get("vinculado") is False)
        cuerpo += section("Resumen", kpi_tiles([
            ("Casos subidos", len(casos), "ok" if casos else "", datos.get("herramienta", ""), "lista"),
            ("Ciclos", len(ciclos), "", "", "carga"),
            ("Sin vincular a la historia", sin_vinculo, "warn" if sin_vinculo else "ok", "", "link"),
        ]))
        if casos:
            def vinculado(c):
                v = c.get("vinculado")
                return "No" if v is False else ("Sí" if v else "—")
            filas = [[f'<span class="id">{e(cid)}</span>', f'<span class="id">{e(c.get("key", ""))}</span>', e(c.get("titulo", "")),
                      e(vinculado(c))] for cid, c in casos.items() if isinstance(c, dict)]
            cuerpo += section("Casos", table(["Caso", "Key", "Título", "Vinculado"], filas))
        if ciclos:
            cuerpo += section("Ciclos", table(["Key", "Nombre", "Fecha"],
                                              [[f'<span class="id">{e(c.get("key", ""))}</span>', e(c.get("nombre", "")), e(c.get("fecha", ""))]
                                               for c in ciclos if isinstance(c, dict)]))
        extra = [("Herramienta", datos.get("herramienta")), ("Proyecto", datos.get("proyecto")),
                 ("Carpeta", (datos.get("carpeta") or {}).get("ruta"))]
        titulo = f"Trazabilidad · {Path(origen).stem}"
    else:  # resultados publicados
        lista = [r for r in datos if isinstance(r, dict)]
        cuenta = Counter(r.get("estado", "") for r in lista)
        cuerpo += section("Resumen", kpi_tiles([
            ("Escenarios", len(lista), "", "", "lista"),
            ("Aprobados", cuenta.get("aprobado", 0), "ok", "", "ok"),
            ("Fallidos", cuenta.get("fallido", 0), "bad" if cuenta.get("fallido") else "ok", "", "bad"),
            ("Bloqueados", cuenta.get("bloqueado", 0), "warn" if cuenta.get("bloqueado") else "", "", "blk"),
        ]))
        estados = {"aprobado": "Aprobado", "fallido": "Fallido", "bloqueado": "Bloqueado", "pendiente": "Pendiente"}
        filas = [[e(r.get("feature", "")), e(r.get("escenario", "")), estado_pill(estados.get(r.get("estado"), r.get("estado", ""))),
                  e(", ".join(r.get("tags") or [])), e((r.get("error") or "")[:300]), e(len(r.get("evidencias") or []))] for r in lista]
        cuerpo += section("Escenarios", table(["Feature", "Escenario", "Estado", "Tags", "Error", "Evidencias"], filas))
        extra = []
        titulo = f"Resultados publicados · {Path(origen).stem}"
    return page(titulo, "Gestión de pruebas", _meta(origen, "", extra), CSS_EXTRA + cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="HTML (ES + EN) de los artefactos de los agentes (casos, bugs, BDD, análisis…).")
    ap.add_argument("artefacto", nargs="?")
    ap.add_argument("--salida")
    ap.add_argument("--todo", action="store_true", help="todos los artefactos de output/ que cambiaron")
    ap.add_argument("--forzar", action="store_true", help="con --todo, regenera aunque no hayan cambiado")
    a = ap.parse_args()
    if a.todo:
        escritos = actualizar_artefactos(forzar=a.forzar)
        print(f"{len(escritos)} artefacto(s) con HTML nuevo")
        for p in escritos:
            print(p)
        return
    if not a.artefacto:
        ap.error("indicá el artefacto o --todo")
    print(generar(a.artefacto, a.salida))


if __name__ == "__main__":
    main()

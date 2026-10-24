#!/usr/bin/env python3
"""
Herramienta del manual de usuario (agente redactor-manual, skill redaccion-manual). Hace lo determinístico del proceso;
la redacción, la evidencia y la navegación de la aplicación las hace el agente.

Uso (desde la raíz del repo de k0lmenIA):
    python herramientas/manual/manual.py preparar --slug proveedores-alta
    python herramientas/manual/manual.py estado --slug proveedores-alta
    python herramientas/manual/manual.py captura --slug proveedores-alta --origen <png de Playwright MCP> --nombre 01-listado-proveedores.png
    python herramientas/manual/manual.py verificar --slug proveedores-alta          (checklist antes de la versión final)
    python herramientas/manual/manual.py html output/manuales/<slug>/borradores/<slug>-v0.1.md
    python herramientas/manual/manual.py word output/manuales/<slug>/borradores/<slug>-v0.1.md [--equipo "<quién firma>"]
    python herramientas/manual/manual.py a-input --slug proveedores-alta            (conocimiento a input/documentacion/)
    python herramientas/manual/manual.py plataforma [--mapa input/documentacion/proyecto/mapa-funcional.json] [--menu menu.json]

Carpeta de cada manual (`output/manuales/<slug>/`, no se versiona):
    capturas/NN-descripcion.png        las capturas, en orden de aparición
    borradores/<slug>-v0.N.md (.html)  los borradores (nunca se pisan: cada cambio sustancial es una versión nueva)
    revision/evidencia.md              matriz de evidencia, gaps y "Pistas para probar"
    revision/qa-review.md              solo los puntos que requieren revisión humana (REVIEW-NNN)
    versiones/<slug>-v1.0.md (.html)   la versión aprobada (solo con aprobación explícita y el checklist en verde)

`a-input` deja lo que se aprendió de la aplicación en `input/documentacion/manual-usuario/<slug>.md`, con el encabezado
del índice: estado `confirmado` si sale de una versión aprobada, `borrador` si sale de un borrador. Lo marcado como
QA REVIEW no entra como hecho: va en "Sin confirmar", para que los casos lo traten como Falta información.
"""
import argparse
import base64
import datetime as dt
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "output" / "manuales"
DOC_INPUT = RAIZ / "input" / "documentacion"
AQUI = Path(__file__).resolve().parent
DEPS = AQUI / ".deps"
CARPETAS = ("capturas", "borradores", "revision", "versiones")
RX_VERSION = re.compile(r"-v(\d+)\.(\d+)\.md$")
RX_REVIEW_INICIO = re.compile(r"^>\s*⚠️?\s*QA REVIEW\s*\((REVIEW-\d+)\)", re.I)


# ------------------------------------------------------------------ carpetas y versiones

def slug_valido(slug):
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug or ""):
        raise ValueError(f"slug inválido {slug!r}: usá kebab-case sin tildes (p. ej. proveedores-alta)")
    return slug


def carpeta(slug, base=None):
    return Path(base or SALIDA) / slug_valido(slug)


def versiones(dir_, slug):
    """[(mayor, menor, ruta)] de los .md de una carpeta, ordenados."""
    out = []
    for p in Path(dir_).glob(f"{slug}-v*.md"):
        m = RX_VERSION.search(p.name)
        if m and p.name == f"{slug}-v{m.group(1)}.{m.group(2)}.md":
            out.append((int(m.group(1)), int(m.group(2)), p))
    return sorted(out)


def estado_manual(slug, base=None):
    c = carpeta(slug, base)
    bor = versiones(c / "borradores", slug)
    fin = versiones(c / "versiones", slug)
    ultimo = bor[-1] if bor else None
    siguiente = f"{slug}-v0.{(ultimo[1] + 1) if ultimo else 1}.md"
    reviews = leer_reviews(c / "revision" / "qa-review.md")
    return {"slug": slug, "carpeta": str(c), "existe": c.exists(),
            "ultimo_borrador": str(ultimo[2]) if ultimo else None,
            "borrador_siguiente": str(c / "borradores" / siguiente),
            "version_final": str(fin[-1][2]) if fin else None,
            "reviews": {"pendientes": [r["id"] for r in reviews if r["estado"] == "PENDING"],
                        "resueltos": sum(1 for r in reviews if r["estado"] == "RESOLVED"),
                        "descartados": sum(1 for r in reviews if r["estado"] == "DISCARDED")},
            "capturas": sorted(p.name for p in (c / "capturas").glob("*.png")) if (c / "capturas").exists() else []}


def preparar(slug, base=None):
    c = carpeta(slug, base)
    for sub in CARPETAS:
        (c / sub).mkdir(parents=True, exist_ok=True)
    return estado_manual(slug, base)


def guardar_captura(slug, origen, nombre, reemplazar=False, base=None):
    """Mueve una captura (Playwright MCP la deja en su --output-dir) a capturas/ con el nombre del manual."""
    if not re.fullmatch(r"\d{2}-[a-z0-9]+(-[a-z0-9]+)*\.(png|jpe?g)", nombre or ""):
        raise ValueError(f"nombre de captura inválido {nombre!r}: usá NN-descripcion-clara.png (p. ej. 01-listado-proveedores.png)")
    origen = Path(origen)
    if not origen.is_file():
        raise ValueError(f"no existe la captura {origen}")
    destino = carpeta(slug, base) / "capturas" / nombre
    destino.parent.mkdir(parents=True, exist_ok=True)
    reemplazada = destino.exists()
    if reemplazada and not reemplazar:
        raise ValueError(f"{destino.name} ya existe: pasá --reemplazar si la pantalla cambió (y decilo en el resumen)")
    shutil.move(str(origen), str(destino))
    return {"captura": str(destino), "reemplazada": reemplazada}


# ------------------------------------------------------------------ revisión (qa-review.md y bloques QA REVIEW)

def leer_reviews(ruta):
    """[{id, estado, funcionalidad, problema, confirmacion, resolucion}] de qa-review.md (tolerante al formato)."""
    ruta = Path(ruta)
    if not ruta.exists():
        return []
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    partes = re.split(r"^##\s+(REVIEW-\d+)\s*$", texto, flags=re.M)
    claves = {"funcionalidad": "funcionalidad", "problema": "problema", "evidencia": "evidencia", "estado": "estado",
              "confirmación requerida": "confirmacion", "confirmacion requerida": "confirmacion", "resolución": "resolucion",
              "resolucion": "resolucion"}
    out = []
    for i in range(1, len(partes), 2):
        campos, actual = {}, None
        for linea in partes[i + 1].splitlines():
            m = re.match(r"^([A-Za-zÁÉÍÓÚáéíóúñ ]{3,30}):\s*(.*)$", linea.strip())
            if m and m.group(1).strip().lower() in claves:
                actual = claves[m.group(1).strip().lower()]
                campos[actual] = m.group(2).strip()
            elif actual and linea.strip():
                campos[actual] = (campos[actual] + " " + linea.strip()).strip()
        estado = (campos.get("estado", "").split() or ["PENDING"])[0].upper()
        out.append({"id": partes[i], "estado": estado if estado in ("PENDING", "RESOLVED", "DISCARDED") else "PENDING",
                    "funcionalidad": campos.get("funcionalidad", ""), "problema": campos.get("problema", ""),
                    "confirmacion": campos.get("confirmacion", ""), "resolucion": campos.get("resolucion", "")})
    return out


def bloques_review(texto):
    """[(id, inicio, fin)] (líneas 0-based) de los bloques `> ⚠️ QA REVIEW (REVIEW-NNN)` del borrador."""
    lineas, out, i = texto.splitlines(), [], 0
    while i < len(lineas):
        m = RX_REVIEW_INICIO.match(lineas[i].strip())
        if m:
            j = i
            while j + 1 < len(lineas) and lineas[j + 1].lstrip().startswith(">"):
                j += 1
            out.append((m.group(1), i, j))
            i = j + 1
        else:
            i += 1
    return out


def quitar_internos(texto):
    """El texto del manual sin bloques QA REVIEW ni el bloque `> Cambios respecto de la versión anterior`."""
    lineas = texto.splitlines()
    borrar = set()
    for _, a, b in bloques_review(texto):
        borrar.update(range(a, b + 1))
    i = 0
    while i < len(lineas):
        if re.match(r"^>\s*\**Cambios respecto", lineas[i].strip(), re.I):
            j = i
            while j + 1 < len(lineas) and lineas[j + 1].lstrip().startswith(">"):
                j += 1
            borrar.update(range(i, j + 1))
            i = j + 1
        else:
            i += 1
    limpio = "\n".join(l for k, l in enumerate(lineas) if k not in borrar)
    return re.sub(r"\n{3,}", "\n\n", limpio).strip() + "\n"


def imagenes(texto):
    return re.findall(r"!\[([^\]]*)\]\(([^)\s]+)\)", texto)


def filas_matriz(ruta):
    """[(funcionalidad, estado)] de la matriz de evidencia (tabla Markdown o ASCII de formatear_tablas)."""
    ruta = Path(ruta)
    if not ruta.exists():
        return []
    out = []
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        if not linea.strip().startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) >= 2 and celdas[-1] in ("CONFIRMED", "REVIEW", "BLOCKED", "NOT_APPLICABLE"):
            out.append((celdas[0], celdas[-1]))
    return out


def verificar(slug, md=None, base=None):
    """Checklist previo a la versión final. {ok, problemas: [...], ...}."""
    est = estado_manual(slug, base)
    c = Path(est["carpeta"])
    md = Path(md) if md else (Path(est["ultimo_borrador"]) if est["ultimo_borrador"] else None)
    problemas = []
    if not md or not md.exists():
        return {"ok": False, "problemas": ["No hay borrador para verificar."], "borrador": None}
    texto = md.read_text(encoding="utf-8", errors="replace")
    qa = c / "revision" / "qa-review.md"
    reviews = leer_reviews(qa)
    pend = [r["id"] for r in reviews if r["estado"] == "PENDING"]
    if pend:
        problemas.append(f"REVIEW pendientes en {qa.name}: {', '.join(pend)}")
    en_texto = [b[0] for b in bloques_review(texto)]
    if en_texto or "QA REVIEW" in texto:
        problemas.append(f"El borrador todavía tiene bloques QA REVIEW: {', '.join(en_texto) or '(sin ID)'}")
    ids_md, ids_qa = set(en_texto), {r["id"] for r in reviews}
    if ids_md - ids_qa:
        problemas.append(f"REVIEW del borrador que no están en {qa.name}: {', '.join(sorted(ids_md - ids_qa))}")
    faltan = [p for _, p in imagenes(texto) if not re.match(r"^(https?:|data:)", p) and not (md.parent / p).exists()]
    if faltan:
        problemas.append(f"Imágenes que no existen: {', '.join(faltan)}")
    abiertas = [f"{f} ({e})" for f, e in filas_matriz(c / "revision" / "evidencia.md") if e in ("REVIEW", "BLOCKED")]
    if abiertas:
        problemas.append(f"Filas de la matriz de evidencia en REVIEW/BLOCKED: {', '.join(abiertas)} "
                         "(si una BLOCKED quedó aceptada fuera del manual, pasala a NOT_APPLICABLE)")
    return {"ok": not problemas, "problemas": problemas, "borrador": str(md),
            "imagenes": [p for _, p in imagenes(texto)], "reviews": est["reviews"]}


# ------------------------------------------------------------------ Markdown -> HTML (autocontenido)

# Diseño de los informes de k0lmena (tokens de scripts/_estilos_reporte.py): oscuro en pantalla, claro al imprimir.
CSS = """
:root{--bg:#0E0C09;--surface:#1A1712;--tile:#221E17;--line:#2E281F;--ink:#F4EFE6;--body:#CFC7B8;--muted:#8A8172;
  --accent:#F9B006;--accent2:#C98500;--serio:#FF8A00;--ok:#5CBF4A;--neon:linear-gradient(135deg,#FFD60A,#FF8A00);
  --display:"Saira","Inter",ui-sans-serif,system-ui,sans-serif;--sans:"Inter",ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,Consolas,monospace}
*{box-sizing:border-box}html{color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--body);font:15.5px/1.7 var(--sans);
  background-image:radial-gradient(900px 420px at 85% -10%,rgba(249,176,6,.08),transparent 60%)}
.wrap{max-width:920px;margin:0 auto;padding:36px 22px 90px}
.top{background:var(--surface);border:1px solid var(--line);border-bottom:3px solid var(--accent);border-radius:18px;padding:26px 28px;margin-bottom:26px}
.logo{display:flex;align-items:center;gap:11px;margin-bottom:26px}
.mk{width:36px;height:34px;display:grid;place-items:center;clip-path:polygon(25% 3%,75% 3%,100% 50%,75% 97%,25% 97%,0 50%);
  background:var(--neon);color:#0E0C09;font:700 14px var(--display);letter-spacing:-.02em}
.logo b{font:700 16px var(--display);letter-spacing:.02em;color:var(--ink)}
.eyebrow{font:500 11.5px var(--mono);color:var(--accent);text-transform:lowercase;letter-spacing:.04em}
h1{font:700 40px/1.08 var(--display);letter-spacing:-.012em;color:var(--ink);margin:8px 0 16px}
.chip{display:inline-block;font:600 11.5px var(--mono);padding:5px 12px;border-radius:99px;background:var(--tile);
  border:1px solid rgba(249,176,6,.4);color:var(--accent)}.chip.final{border-color:rgba(92,191,74,.5);color:var(--ok)}
.meta{margin-top:14px;font:12px var(--mono);color:var(--muted)}
nav.toc{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 22px;margin:0 0 30px}
nav.toc b{display:block;font:500 11.5px var(--mono);color:var(--accent);text-transform:lowercase;margin-bottom:8px}
nav.toc ol{margin:0;padding:0;list-style:none;counter-reset:s}nav.toc li{counter-increment:s;padding:4px 0;border-bottom:1px solid var(--line)}
nav.toc li::before{content:counter(s,decimal-leading-zero);font:12px var(--mono);color:var(--accent);margin-right:12px}
nav.toc a{color:var(--ink);text-decoration:none;font:600 15px var(--display)}nav.toc a:hover{color:var(--accent)}
main{counter-reset:h2}
h2{font:700 24px var(--display);color:var(--ink);margin:2.1em 0 .7em;padding-bottom:8px;border-bottom:2px solid var(--accent);counter-increment:h2}
h2::before{content:counter(h2,decimal-leading-zero);font:500 14px var(--mono);color:var(--accent);margin-right:12px;vertical-align:3px}
h3{font:700 17px var(--display);color:var(--accent2);margin:1.6em 0 .4em}h4{font:600 15px var(--display);color:var(--ink)}
strong{color:var(--ink);font-weight:600}a{color:var(--accent)}
ol,ul{padding-left:26px}li{margin:.35em 0}ul li::marker{color:var(--accent)}ol li::marker{font:700 15px var(--display);color:var(--accent2)}
figure{margin:16px 0 20px;text-align:center}figure img{max-width:100%;border:1px solid var(--line);border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.45)}
figcaption{font:11.5px var(--mono);color:var(--muted);margin-top:8px;text-transform:lowercase}.falta{color:#FF7B70;font:12px var(--mono)}
blockquote{margin:16px 0;padding:12px 18px;border-left:4px solid var(--accent);background:var(--surface);border-radius:0 12px 12px 0}
blockquote.review{background:rgba(255,138,0,.10);border-left-color:var(--serio)}blockquote p{margin:.3em 0}
code{font:.88em var(--mono);color:var(--ink);background:var(--tile);border:1px solid var(--line);padding:1px 6px;border-radius:6px}
pre{background:var(--surface);border:1px solid var(--line);padding:14px 18px;border-radius:12px;overflow:auto}pre code{background:none;border:0;padding:0}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px;background:var(--surface);border-radius:12px;overflow:hidden}
th{text-align:left;font:500 11px var(--mono);text-transform:lowercase;letter-spacing:.02em;color:var(--muted);background:rgba(244,239,230,.025);
  padding:11px 16px;border-bottom:1px solid var(--line)}td{padding:10px 16px;border-bottom:1px solid var(--line);vertical-align:top}
footer{margin-top:60px;padding-top:14px;border-top:1px solid var(--line);font:11.5px var(--mono);color:var(--muted)}
@media print{
  :root{--bg:#fff;--surface:#FAF7F1;--tile:#F1EBDF;--line:#E4DCCB;--ink:#1A1712;--body:#2B261E;--muted:#6E665A;--accent2:#A66C00}
  html{color-scheme:light}body{background:#fff}.top{background:#0E0C09;border:0;color:#CFC7B8;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .top h1,.top .logo b{color:#F4EFE6}nav.toc{break-after:page}figure,table,blockquote{break-inside:avoid}h2,h3{break-after:avoid}
  figure img{box-shadow:none}}
@media (max-width:640px){h1{font-size:30px}.top{padding:20px}}
"""


def _inline(t, base_dir, embebido):
    t = html.escape(t, quote=False)
    t = re.sub(r"\\\*", "&#42;", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*\s][^*]*)\*(?![*\w])", r"<em>\1</em>", t)
    t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda m: _figura(m.group(1), html.unescape(m.group(2)), base_dir, embebido), t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
    return t


def _figura(alt, ruta, base_dir, embebido):
    src, existe = ruta, True
    if not re.match(r"^(https?:|data:)", ruta):
        p = (Path(base_dir) / ruta)
        existe = p.exists()
        if existe and embebido:
            tipo = mimetypes.guess_type(p.name)[0] or "image/png"
            src = f"data:{tipo};base64,{base64.b64encode(p.read_bytes()).decode()}"
    if not existe:
        return f'<span class="falta">[Falta la imagen {html.escape(ruta)}]</span>'
    return f'<figure><img src="{html.escape(src)}" alt="{alt}" loading="lazy"><figcaption>{alt}</figcaption></figure>'


def md_a_html(texto, base_dir=".", embebido=True):
    """Convierte el subconjunto de Markdown de los manuales (títulos, párrafos, listas anidadas con imágenes,
    citas y bloques QA REVIEW, tablas, código). Devuelve (titulo, cuerpo_html, toc)."""
    lineas = texto.splitlines()
    out, toc, titulo, pila, i = [], [], "", [], 0

    def cerrar_listas(hasta=0):
        while len(pila) > hasta:
            out.append(f"</li></{pila.pop()[0]}>")

    while i < len(lineas):
        l = lineas[i]
        s = l.strip()
        if not s:
            i += 1
            continue
        if s.startswith("```"):
            cerrar_listas()
            bloque = []
            i += 1
            while i < len(lineas) and not lineas[i].strip().startswith("```"):
                bloque.append(lineas[i])
                i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(bloque))}</code></pre>")
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m and not l.startswith(" "):
            cerrar_listas()
            n, t = len(m.group(1)), m.group(2).strip()
            if n == 1 and not titulo:
                titulo = re.sub(r"\*\*", "", t)
            else:
                ident = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or f"s{len(toc)}"
                if n == 2:
                    toc.append((ident, re.sub(r"\*\*", "", t)))
                out.append(f'<h{n} id="{ident}">{_inline(t, base_dir, embebido)}</h{n}>')
            i += 1
            continue
        if s.startswith(">"):
            cerrar_listas()
            bloque = []
            while i < len(lineas) and lineas[i].strip().startswith(">"):
                bloque.append(re.sub(r"^\s*>\s?", "", lineas[i]))
                i += 1
            clase = ' class="review"' if any("QA REVIEW" in b for b in bloque) else ""
            parrafos = "".join(f"<p>{_inline(b, base_dir, embebido)}</p>" for b in bloque if b.strip())
            out.append(f"<blockquote{clase}>{parrafos}</blockquote>")
            continue
        if s.startswith("|") or re.match(r"^\+[-=+]+\+$", s):
            cerrar_listas()
            filas = []
            while i < len(lineas) and (lineas[i].strip().startswith("|") or re.match(r"^\+[-=+]+\+$", lineas[i].strip())):
                c = lineas[i].strip()
                if c.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", c):
                    filas.append([x.strip() for x in c.strip("|").split("|")])
                i += 1
            if filas:
                cab = "".join(f"<th>{_inline(c, base_dir, embebido)}</th>" for c in filas[0])
                cuerpo = "".join("<tr>" + "".join(f"<td>{_inline(c, base_dir, embebido)}</td>" for c in f) + "</tr>" for f in filas[1:])
                out.append(f"<table><thead><tr>{cab}</tr></thead><tbody>{cuerpo}</tbody></table>")
            continue
        m = re.match(r"^(\s*)(\d+\.|[-*+])\s+(.*)", l)
        if m:
            nivel = len(m.group(1).replace("\t", "    ")) // 2
            tag = "ol" if m.group(2)[0].isdigit() else "ul"
            if not pila or nivel > pila[-1][1]:
                out.append(f"<{tag}>")
                pila.append((tag, nivel))
            else:
                while pila and nivel < pila[-1][1]:
                    out.append(f"</li></{pila.pop()[0]}>")
                if pila and pila[-1][0] != tag:
                    out.append(f"</li></{pila.pop()[0]}><{tag}>")
                    pila.append((tag, nivel))
                else:
                    out.append("</li>")
            out.append(f"<li>{_inline(m.group(3), base_dir, embebido)}")
            i += 1
            continue
        if pila and l.startswith((" ", "\t")):
            out.append(" " + _inline(s, base_dir, embebido))
            i += 1
            continue
        cerrar_listas()
        parrafo = [s]
        i += 1
        while i < len(lineas) and lineas[i].strip() and not re.match(r"^(#{1,4}\s|>|\||```|\s*(\d+\.|[-*+])\s)", lineas[i].strip()):
            parrafo.append(lineas[i].strip())
            i += 1
        texto_p = " ".join(parrafo)
        if re.fullmatch(r"!\[[^\]]*\]\([^)\s]+\)", texto_p):
            out.append(_inline(texto_p, base_dir, embebido))
        else:
            out.append(f"<p>{_inline(texto_p, base_dir, embebido)}</p>")
    cerrar_listas()
    return titulo, "\n".join(out), toc


def a_html(md, salida=None, embebido=True):
    md = Path(md)
    texto = md.read_text(encoding="utf-8")
    titulo, cuerpo, toc = md_a_html(texto, md.parent, embebido)
    m = RX_VERSION.search(md.name)
    version = f"v{m.group(1)}.{m.group(2)}" if m else ""
    final = bool(m) and int(m.group(1)) >= 1
    etiqueta = f"Versión {version}" if final else f"Borrador {version} · pendiente de revisión (no publicar)"
    indice = ("<nav class='toc'><b>contenido</b><ol>" + "".join(f'<li><a href="#{a}">{html.escape(t)}</a></li>' for a, t in toc)
              + "</ol></nav>") if len(toc) > 2 else ""
    try:  # las fuentes de la casa, embebidas (las mismas de los informes)
        sys.path.insert(0, str(RAIZ / "scripts"))
        from _estilos_reporte import FUENTES
    except Exception:
        FUENTES = ""
    pagina = (f'<!doctype html>\n<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
              f'<meta name="color-scheme" content="dark"><title>{html.escape(titulo or md.stem)} — k0lmenIA</title>'
              f'<style>{FUENTES}{CSS}</style></head><body><div class="wrap">'
              f'<header class="top"><div class="logo"><span class="mk">k0</span><b>K0LMENIA</b></div>'
              f'<span class="eyebrow">manual de usuario</span><h1>{_inline(titulo or md.stem, md.parent, embebido)}</h1>'
              f'<span class="chip{" final" if final else ""}">{html.escape(etiqueta)}</span>'
              f'<div class="meta">fecha {dt.date.today().isoformat()}</div></header>'
              f'{indice}<main>{cuerpo}</main><footer>generado por k0lmenIA · parte de la suite k0lmena</footer></div></body></html>\n')
    salida = Path(salida) if salida else md.with_suffix(".html")
    salida.write_text(pagina, encoding="utf-8")
    return salida


# ------------------------------------------------------------------ Word (.docx)

# Fuentes de la casa (scripts/fuentes, las mismas de k0lmena.com) para embeber en el Word: (familia, archivo, peso).
FUENTES_WORD = [("Saira", "saira", 700), ("Inter", "inter", 400), ("JetBrains Mono", "jetbrains-mono", 400)]


def fuentes_word():
    """{familia: ruta .ttf}: convierte las woff2 variables de scripts/fuentes a TTF estáticos (Word no lee woff2 ni
    variables) y los deja en herramientas/manual/.deps/fuentes. Si fontTools no está y no se puede instalar, devuelve {}
    y el Word usa las fuentes instaladas en la máquina."""
    destino = DEPS / "fuentes"
    listas = {fam: destino / f"{arch}-{peso}.ttf" for fam, arch, peso in FUENTES_WORD}
    if all(p.exists() for p in listas.values()):
        return {k: str(v) for k, v in listas.items()}
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
        import brotli  # noqa: F401  (woff2)
    except ImportError:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "fonttools", "brotli"], capture_output=True, text=True)
        if r.returncode != 0:
            print("[manual] Aviso: sin fontTools no se embeben las fuentes de k0lmena (pip install fonttools brotli).", file=sys.stderr)
            return {}
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
    destino.mkdir(parents=True, exist_ok=True)
    for fam, arch, peso in FUENTES_WORD:
        font = TTFont(RAIZ / "scripts" / "fuentes" / f"{arch}.woff2")
        if "fvar" in font:
            font = instancer.instantiateVariableFont(font, {"wght": peso})
        font.flavor = None
        # Word busca la fuente embebida por su nombre de familia: lo dejamos igual al que usa el documento.
        tabla = font["name"]
        for nid in (16, 17):
            tabla.removeNames(nameID=nid)
        for nid, valor in ((1, fam), (2, "Regular"), (4, fam), (6, fam.replace(" ", "") + "-Regular")):
            tabla.setName(valor, nid, 3, 1, 0x409)
            tabla.setName(valor, nid, 1, 0, 0)
        font["OS/2"].fsType = 0
        font.save(listas[fam])
    return {k: str(v) for k, v in listas.items()}


def a_word(md, salida=None, estado=None, equipo=None):
    """Convierte con md2docx.js (diseño de k0lmena, fuentes de la casa embebidas); instala docx e image-size en
    herramientas/manual/.deps la primera vez (no se versiona)."""
    md = Path(md)
    salida = Path(salida) if salida else md.with_suffix(".docx")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    node = shutil.which("node")
    if not node or not npm:
        raise RuntimeError("Para el Word hace falta Node.js 20+ (node y npm en el PATH).")
    if not (DEPS / "node_modules" / "docx").exists():
        r = subprocess.run([npm, "install", "--prefix", str(DEPS), "--no-audit", "--no-fund", "--silent", "docx@9", "image-size@1"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"No se pudieron instalar las dependencias del Word: {(r.stderr or r.stdout).strip()[-300:]}")
    env = dict(os.environ, NODE_PATH=str(DEPS / "node_modules"), MANUAL_FUENTES=json.dumps(fuentes_word()))
    if equipo:
        env["MANUAL_EQUIPO"] = equipo
    args = [node, str(AQUI / "md2docx.js"), str(md), str(salida)] + ([estado] if estado else [])
    r = subprocess.run(args, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"md2docx falló: {(r.stderr or r.stdout).strip()[-400:]}")
    return salida


# ------------------------------------------------------------------ conocimiento a input/documentacion/

def a_input(slug, md=None, base=None, destino=None, url=None):
    """Escribe input/documentacion/manual-usuario/<slug>.md. Devuelve la ruta."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    from indice_documentacion import escribir_documento
    est = estado_manual(slug, base)
    c = Path(est["carpeta"])
    if md:
        md = Path(md)
    elif est["version_final"]:
        md = Path(est["version_final"])
    elif est["ultimo_borrador"]:
        md = Path(est["ultimo_borrador"])
    else:
        raise ValueError(f"No hay borrador ni versión de {slug} en {c}.")
    confirmado = md.parent.name == "versiones"
    texto = md.read_text(encoding="utf-8")
    cuerpo = quitar_internos(texto)
    try:
        rel_capturas = (c / "capturas").resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        rel_capturas = (c / "capturas").resolve().as_posix()
    cuerpo = re.sub(r"!\[([^\]]*)\]\((?:\.\./)?capturas/([^)\s]+)\)", rf"![\1]({rel_capturas}/\2)", cuerpo)
    cuerpo = re.sub(r"^# ", "## ", cuerpo, count=1, flags=re.M) if cuerpo.lstrip().startswith("# ") else cuerpo
    titulo = re.search(r"^#\s+(.+)$", texto, re.M)
    titulo = titulo.group(1).strip() if titulo else slug
    origen = md.resolve().relative_to(RAIZ).as_posix() if md.resolve().is_relative_to(RAIZ) else md.as_posix()
    nota = (f"> Cómo se usa la aplicación, según el manual de usuario `{origen}` "
            + ("(versión **aprobada**, verificada en la aplicación)." if confirmado else
               "(**borrador**: lo verificado está en el texto; lo dudoso, en *Sin confirmar*).")
            + " Describe cómo funciona la aplicación **hoy**: si contradice una historia o una decisión del PO, es una "
            "contradicción a preguntar, no un requisito.\n")
    partes = [f"# {titulo}\n", nota, cuerpo.replace(f"## {titulo}\n", "", 1)]
    pend = [r for r in leer_reviews(c / "revision" / "qa-review.md") if r["estado"] == "PENDING"]
    if pend:
        partes.append("## Sin confirmar (pendiente de revisión)\n\nNo son hechos: al escribir casos, cada uno va como "
                      "`Falta información` (`FI-XX`) con su pregunta.\n\n"
                      + "\n".join(f"- **{r['id']}**{' · ' + r['funcionalidad'] if r['funcionalidad'] else ''}: {r['problema']}"
                                  + (f" — *Pregunta:* {r['confirmacion']}" if r["confirmacion"] else "") for r in pend) + "\n")
    evid = c / "revision" / "evidencia.md"
    if evid.exists():
        m = re.search(r"^##\s+Pistas para probar\s*$(.*?)(?=^##\s|\Z)", evid.read_text(encoding="utf-8"), re.M | re.S)
        if m and m.group(1).strip():
            partes.append("## Pistas para probar\n\nCampos, validaciones, mensajes exactos, roles y estados vistos al "
                          "documentar (no son casos; son lo que los casos tienen que cubrir).\n" + m.group(1).rstrip() + "\n")
    fuentes = ", ".join(x for x in [f"manual {origen}", f"app {url}" if url else "", "revision/evidencia.md" if evid.exists() else ""] if x)
    destino = Path(destino or DOC_INPUT)
    ruta = escribir_documento(destino / "manual-usuario" / f"{slug}.md", f"Manual de usuario — {titulo}", "manual-usuario",
                              "\n".join(partes), fuentes=fuentes, estado="confirmado" if confirmado else "borrador")
    import indice_documentacion
    indice_documentacion.main(["--carpeta", str(destino)])
    return ruta


# ------------------------------------------------------------------ modo plataforma (índice de módulos)

def _slug(texto):
    import unicodedata
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "inicio"


def plataforma(mapa=None, menu=None, base=None):
    """Propone los módulos del manual de toda la plataforma: del menú relevado por el agente (menu.json, con sesión)
    y/o del mapa funcional (input/documentacion/proyecto/mapa-funcional.json). Devuelve el plan."""
    modulos = {}
    if menu:
        for m in json.loads(Path(menu).read_text(encoding="utf-8")):
            s = _slug(m.get("modulo") or m.get("nombre"))
            mod = modulos.setdefault(s, {"slug": s, "nombre": m.get("modulo") or m.get("nombre"), "paginas": [], "formularios": 0,
                                         "origen": "menú"})
            for o in m.get("opciones") or []:
                mod["paginas"].append({"titulo": o.get("nombre"), "ruta": o.get("ruta") or o.get("url") or ""})
    if mapa and Path(mapa).exists():
        d = json.loads(Path(mapa).read_text(encoding="utf-8"))
        for p in d.get("paginas") or []:
            if p.get("error"):
                continue
            seg = [x for x in (p.get("ruta") or "/").split("?")[0].split("/") if x]
            s = _slug(seg[0]) if seg else "inicio"
            mod = modulos.setdefault(s, {"slug": s, "nombre": (seg[0] if seg else "Inicio").replace("-", " ").capitalize(),
                                         "paginas": [], "formularios": 0, "origen": "mapa funcional"})
            if not any(x["ruta"] == p.get("ruta") for x in mod["paginas"]):
                mod["paginas"].append({"titulo": p.get("titulo") or p.get("ruta"), "ruta": p.get("ruta")})
            mod["formularios"] += len(p.get("formularios") or [])
    if not modulos:
        raise ValueError("No hay de dónde sacar los módulos: pasá --menu (menú relevado con sesión) o generá el mapa "
                         "funcional (npm run mapa-funcional).")
    for mod in modulos.values():
        est = estado_manual(mod["slug"], base) if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", mod["slug"]) else {}
        mod["manual"] = ("aprobado" if est.get("version_final") else "borrador" if est.get("ultimo_borrador") else "pendiente")
    plan = {"generado": dt.datetime.now().isoformat(timespec="seconds"), "modulos": list(modulos.values())}
    destino = Path(base or SALIDA) / "plataforma"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "indice.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    filas = "\n".join(f"| {i} | {m['nombre']} | `{m['slug']}` | {len(m['paginas'])} | {m['formularios']} | {m['manual']} | {m['origen']} |"
                      for i, m in enumerate(plan["modulos"], 1))
    md = (f"# Manual de la plataforma — plan por módulos\n\nPropuesto el {plan['generado'][:10]}. Revisá los nombres y el orden "
          "(los del menú mandan), sacá lo que no es para usuarios finales y generá los manuales de a uno.\n\n"
          "| # | Módulo | Slug | Páginas | Formularios | Manual | Origen |\n|---|---|---|---|---|---|---|\n" + filas + "\n")
    (destino / "indice.md").write_text(md, encoding="utf-8")
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "formatear_tablas.py"), str(destino / "indice.md")], capture_output=True)
    plan["indice_md"] = str(destino / "indice.md")
    return plan


# ------------------------------------------------------------------ CLI

def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Herramienta del manual de usuario (redactor-manual).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nombre in ("preparar", "estado", "verificar", "a-input"):
        s = sub.add_parser(nombre)
        s.add_argument("--slug", required=True)
        s.add_argument("--base", default=None, help=argparse.SUPPRESS)
        if nombre in ("verificar", "a-input"):
            s.add_argument("--md", default=None, help="el .md a usar (por defecto, la versión final o el último borrador)")
        if nombre == "a-input":
            s.add_argument("--url", default=None, help="URL del ambiente donde se verificó (va a las fuentes)")
            s.add_argument("--destino", default=None, help=argparse.SUPPRESS)
    s = sub.add_parser("captura")
    s.add_argument("--slug", required=True)
    s.add_argument("--origen", required=True, help="la captura que devolvió Playwright MCP")
    s.add_argument("--nombre", required=True, help="NN-descripcion-clara.png, en orden de aparición")
    s.add_argument("--reemplazar", action="store_true")
    s.add_argument("--base", default=None, help=argparse.SUPPRESS)
    s = sub.add_parser("html")
    s.add_argument("md")
    s.add_argument("--salida", default=None)
    s.add_argument("--sin-embeber", action="store_true", help="referenciar las capturas en lugar de embeberlas")
    s = sub.add_parser("word")
    s.add_argument("md")
    s.add_argument("--salida", default=None)
    s.add_argument("--estado", default=None, help='texto de estado de portada y pie (p. ej. "Versión 1.0")')
    s.add_argument("--equipo", default=None, help="equipo que firma el documento (o MANUAL_EQUIPO en el .env)")
    s = sub.add_parser("plataforma")
    s.add_argument("--mapa", default=str(DOC_INPUT / "proyecto" / "mapa-funcional.json"))
    s.add_argument("--menu", default=None, help="JSON [{modulo, opciones:[{nombre, ruta}]}] relevado por el agente con sesión")
    s.add_argument("--base", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "preparar":
            r = preparar(a.slug, a.base)
        elif a.cmd == "estado":
            r = estado_manual(a.slug, a.base)
        elif a.cmd == "verificar":
            r = verificar(a.slug, a.md, a.base)
        elif a.cmd == "a-input":
            r = {"documento": str(a_input(a.slug, a.md, a.base, a.destino, a.url))}
        elif a.cmd == "captura":
            r = guardar_captura(a.slug, a.origen, a.nombre, a.reemplazar, a.base)
        elif a.cmd == "html":
            r = {"html": str(a_html(a.md, a.salida, not a.sin_embeber))}
        elif a.cmd == "word":
            equipo = a.equipo
            if not equipo:
                sys.path.insert(0, str(RAIZ / "scripts"))
                from _env import leer_env
                equipo = os.environ.get("MANUAL_EQUIPO") or leer_env().get("MANUAL_EQUIPO")
            r = {"word": str(a_word(a.md, a.salida, a.estado, equipo))}
        else:
            r = plataforma(a.mapa, a.menu, a.base)
    except (ValueError, RuntimeError, OSError) as ex:
        print(f"[manual] {ex}", file=sys.stderr)
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=2))
    if a.cmd == "verificar" and not r["ok"]:
        print("[manual] El checklist no pasa: no generes la versión final.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

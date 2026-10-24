#!/usr/bin/env python3
"""
Revisión de contenido/typos de un texto o archivo, de solo lectura y sin dependencias: detecta por
heurística los errores objetivos más comunes (placeholders olvidados, Lorem ipsum, palabras duplicadas,
claves de i18n a la vista, marcadores TODO, espacios antes de puntuación, mayúsculas/puntuación). Para
ortografía/gramática reales usa LanguageTool si está instalado (opcional).

Uso (desde la raíz del repo):
    python herramientas/contenido/contenido.py --archivo pagina.txt [--idioma es] [--salida ...]
    python herramientas/contenido/contenido.py --texto "el el texto a revisar"

El agente revisor-contenido suele extraer el texto visible de la web con Playwright (snapshot) y pasarlo
por acá; esto no juzga estilo ni tono, solo errores objetivos.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HEURISTICAS = [
    ("Placeholder sin reemplazar", re.compile(r"\{\{\s*[\w.]+\s*\}\}|\$\{[\w.]+\}|%\(?[\w]+\)?[sd]")),
    ("Lorem ipsum", re.compile(r"(?i)lorem ipsum")),
    ("Marcador pendiente", re.compile(r"\b(TODO|FIXME|XXX|TBD|PENDIENTE|PLACEHOLDER)\b")),
    ("Clave de i18n a la vista", re.compile(r"\b[a-z][a-z0-9_]*(?:\.[a-z0-9_]+){2,}\b")),
    ("Palabra duplicada", re.compile(r"(?i)\b(\w{2,})\s+\1\b")),
    ("Texto de relleno", re.compile(r"(?i)\b(asdf+|qwerty|aaaa+|xxxx+|test test|dummy)\b")),
    ("Espacio antes de puntuación", re.compile(r"\s+[,.;:!?]")),
    ("Espacios múltiples", re.compile(r"\S {2,}\S")),
]


def revisar(texto):
    """[(tipo, linea, fragmento)] de los problemas objetivos del texto. Puro y testeable."""
    out = []
    for i, linea in enumerate(texto.splitlines(), 1):
        for tipo, rx in HEURISTICAS:
            m = rx.search(linea)
            if m:
                frag = re.sub(r"\s+", " ", m.group(0)).strip()[:50]
                out.append((tipo, i, frag))
    return out


def languagetool(texto, idioma):
    """Ortografía/gramática con LanguageTool si está instalado; si no, devuelve None (opcional)."""
    try:
        import language_tool_python  # noqa
    except ImportError:
        return None
    try:
        tool = language_tool_python.LanguageToolPublicAPI(idioma)
        matches = tool.check(texto)
        return [{"mensaje": m.message, "contexto": m.context, "regla": m.ruleId,
                 "sugerencias": m.replacements[:3]} for m in matches[:200]]
    except Exception:
        return None


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Revisión de contenido/typos (heurística + LanguageTool opcional).")
    ap.add_argument("--archivo", default="")
    ap.add_argument("--texto", default="")
    ap.add_argument("--idioma", default="es", help="idioma para LanguageTool (es, en-US, pt…)")
    ap.add_argument("--lt", action="store_true", help="además, correr LanguageTool si está instalado")
    ap.add_argument("--salida", default="")
    args = ap.parse_args(argv)
    if args.archivo:
        if not Path(args.archivo).exists():
            print(f"[contenido] No existe: {args.archivo}", file=sys.stderr)
            return 2
        texto = Path(args.archivo).read_text(encoding="utf-8", errors="replace")
    else:
        texto = args.texto
    if not texto.strip():
        print("[contenido] Pasá --archivo o --texto.", file=sys.stderr)
        return 2
    heur = revisar(texto)
    datos = {"heuristicas": [{"tipo": t, "linea": ln, "fragmento": f} for t, ln, f in heur],
             "resumen": {"heuristicas": len(heur)}}
    if args.lt:
        lt = languagetool(texto, args.idioma)
        datos["languagetool"] = lt if lt is not None else "no instalado (pip install language-tool-python)"
        if isinstance(lt, list):
            datos["resumen"]["languagetool"] = len(lt)
    texto_out = json.dumps(datos, ensure_ascii=False, indent=2)
    if args.salida:
        p = Path(args.salida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto_out, encoding="utf-8")
        print(f"[contenido] Datos en {p}", file=sys.stderr)
    print(texto_out)
    print(f"[contenido] {len(heur)} problema(s) por heurística.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

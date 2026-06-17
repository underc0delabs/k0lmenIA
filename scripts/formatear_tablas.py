#!/usr/bin/env python3
"""Normaliza TODAS las tablas Markdown de un archivo .md a tablas ASCII alineadas.

Uso:
    python scripts/formatear_tablas.py <archivo.md> [ancho_max_columna]

Qué hace:
- Busca cada tabla Markdown (filas con `|` y su fila separadora `|---|---|`) y la
  reemplaza por una tabla ASCII (estilo grid) dentro de un bloque de código, para
  que se vea alineada en cualquier editor, sin importar cuánto texto tenga.
- Las celdas largas se ajustan a `ancho_max_columna` caracteres (default 40).
  Respeta saltos de línea escritos como `<br>` o reales.
- NO toca lo que ya está dentro de bloques de código (```), así que es seguro
  correrlo varias veces sobre el mismo archivo (es idempotente).

Pensado para que cualquier agente, después de escribir un `.md`, lo corra una vez
y todas sus tablas queden con el mismo formato.
"""
import sys
import re
import textwrap
import subprocess

DELIM_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")


def _ensure(pkg):
    try:
        __import__(pkg)
    except ImportError:
        print(f"Instalando {pkg}...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "pip", "install", pkg, "--quiet"], check=False)


def _cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _wrap_cell(text, width):
    text = re.sub(r"<br\s*/?>", "\n", str(text))
    out = []
    for seg in text.split("\n"):
        seg = seg.strip()
        if seg:
            out.extend(textwrap.wrap(seg, width=width))
        else:
            out.append("")
    return "\n".join(out)


def _is_row(line):
    return "|" in line and line.strip() != ""


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/formatear_tablas.py <archivo.md> [ancho_max_columna]", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 40

    _ensure("tabulate")
    try:
        from tabulate import tabulate
    except ImportError:
        print("Falta la librería 'tabulate'. Instalala con:  pip install tabulate", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    out = []
    i = 0
    in_fence = False
    n = len(lines)
    convertidas = 0

    while i < n:
        line = lines[i]

        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue

        # ¿Empieza una tabla? Fila con '|' seguida de fila separadora.
        if (not in_fence and _is_row(line) and i + 1 < n and DELIM_RE.match(lines[i + 1])
                and "-" in lines[i + 1]):
            headers = _cells(line)
            ncols = len(headers)
            j = i + 2
            data = []
            while j < n and _is_row(lines[j]) and not lines[j].lstrip().startswith("```"):
                fila = _cells(lines[j])
                fila = (fila + [""] * ncols)[:ncols]   # emparejar al nº de columnas
                data.append(fila)
                j += 1

            H = [_wrap_cell(h, width) for h in headers]
            R = [[_wrap_cell(c, width) for c in fila] for fila in data]
            tabla = tabulate(R, headers=H, tablefmt="grid")
            out.append("```")
            out.append(tabla)
            out.append("```")
            convertidas += 1
            i = j
            continue

        out.append(line)
        i += 1

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print(f"OK: {convertidas} tabla(s) formateada(s) en {path}")


if __name__ == "__main__":
    main()

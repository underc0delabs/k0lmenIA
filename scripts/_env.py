#!/usr/bin/env python3
"""
Lectura del .env de la raíz de k0lmenIA, con las mismas reglas que k0lmena (dotenv) y que
scripts/mcp/leer-env.js:

- `CLAVE=valor`, con `export` opcional adelante; espacios alrededor ignorados.
- Valor entre comillas simples o dobles: se toma literal (un `#` adentro no es comentario).
- Valor sin comillas: ` # comentario` al final se descarta.
- Líneas vacías y comentarios (`#`) se ignoran. Tolera BOM (archivos guardados desde Windows).
- K0LMENA_ENV_FILE apunta a otro archivo (por ejemplo, en CI).

Las variables ya definidas en el entorno tienen prioridad sobre el archivo.
"""
import os
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
_LINEA = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def archivo_env():
    return Path(os.environ.get("K0LMENA_ENV_FILE") or RAIZ / ".env")


def leer_env(archivo=None):
    """Devuelve {clave: valor} del archivo (sin tocar os.environ)."""
    archivo = Path(archivo) if archivo else archivo_env()
    valores = {}
    if not archivo.exists():
        return valores
    for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
        m = _LINEA.match(linea)
        if not m or linea.lstrip().startswith("#"):
            continue
        valor = m.group(2)
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        else:
            valor = re.sub(r"\s+#.*$", "", valor)
        valores[m.group(1)] = valor
    return valores


def cargar_env(archivo=None):
    """Carga el .env en os.environ sin pisar lo que ya está definido en el entorno."""
    for clave, valor in leer_env(archivo).items():
        os.environ.setdefault(clave, valor)

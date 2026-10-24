#!/usr/bin/env python3
"""
Dónde están los DATOS del proyecto y dónde el CÓDIGO de k0lmenIA.

- Código (RAIZ): la carpeta de k0lmenIA, donde están scripts/, herramientas/, plantillas/ y .env.example.
- Datos (PROYECTO): donde trabaja el QA: output/, input/, .env, .auth/ y su automatización en
  herramientas/k0lmena (features, steps, locators y reports).

Con el repo clonado son la misma carpeta. Como plugin de Claude Code, el código queda en la caché del plugin y los
datos en el proyecto: el comando `k0lmenia` (bin/) define K0LMENIA_PROYECTO con la carpeta del proyecto.

Cada script lo resuelve igual, en una línea, para no depender de cómo se importó:
    PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def raiz_proyecto(raiz_codigo=RAIZ):
    """La carpeta de datos: K0LMENIA_PROYECTO si está definida; si no, la del código (el repo clonado)."""
    return Path(os.environ.get("K0LMENIA_PROYECTO") or raiz_codigo).resolve()


PROYECTO = raiz_proyecto()

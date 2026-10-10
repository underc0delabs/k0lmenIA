"""Configuración común de los tests de k0lmenIA: los scripts se importan desde scripts/ y scripts/gestion/."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (RAIZ / "scripts", RAIZ / "scripts" / "gestion"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

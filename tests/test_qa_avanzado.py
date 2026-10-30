"""Portal de informes: cada carpeta de output/ de K0lmenIA Light cae en su categoría y tiene nombre legible."""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import portal_informes as portal  # noqa: E402


@pytest.mark.parametrize("carpeta,categoria", [("ejecuciones", "ejecuciones"), ("ejecucion-manual", "ejecuciones"),
                                                ("casos-de-prueba", "diseno"), ("triage", "bugs"), ("gestion", "calidad"),
                                                ("novedades", "documentacion")])
def test_portal_indexa_las_carpetas_del_plan(carpeta, categoria):
    assert portal.CATEGORIA_DE[carpeta] == categoria and carpeta in portal.NOMBRES


def test_cada_carpeta_con_nombre_tiene_categoria():
    assert set(portal.NOMBRES) <= set(portal.CATEGORIA_DE)

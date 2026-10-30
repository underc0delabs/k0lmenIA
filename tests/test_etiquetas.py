"""Etiquetas estándar de los casos (scripts/_etiquetas.py): historia, módulo, prioridad, smoke/regresion y las demás."""
import json
import subprocess
import sys
from pathlib import Path

import _etiquetas as et

RAIZ = Path(__file__).resolve().parents[1]


def test_orden_y_completas():
    assert et.estandar("@login @positivo @CA1", "Alta", "HU-001 — Inicio de sesión") == [
        "HU-001", "modulo-inicio-de-sesion", "alta", "regresion", "login", "positivo", "CA1"]


def test_smoke_regresion_y_prioridad():
    # Crítica es smoke; "regression" y "Regresión" son la misma; la columna Prioridad manda sobre un tag distinto.
    assert et.estandar(["media", "Regression"], "Crítica") == ["critica", "smoke", "regresion"]
    # Lo que depende de información que falta o está bloqueado no entra en la regresión.
    assert et.estandar("@smoke @falta-info @FI-01", "Alta") == ["alta", "smoke", "falta-info", "FI-01"]
    assert et.estandar("@bloqueado", "Baja") == ["baja", "bloqueado"]
    # Sin prioridad en la columna, vale el tag.
    assert et.estandar("@baja") == ["baja", "regresion"]


def test_historia_y_modulo():
    # Un modulo-x que ya trae el caso se respeta; la historia de Jira se suma a la HU.
    assert et.estandar("@modulo-login @hu-001", "Media", "Otra cosa", ["PROJ-12", None]) == [
        "HU-001", "PROJ-12", "modulo-login", "media", "regresion"]
    assert et.separar_modulo("HU-7: Pagos") == ("HU-7", "Pagos")
    assert et.como_texto(["HU-001", "smoke"]) == "@HU-001 @smoke"


def test_la_planilla_sale_con_las_etiquetas(tmp_path):
    entrada = tmp_path / "casos.json"
    entrada.write_text(json.dumps({"proyecto": "P", "modulo": "HU-001 — Inicio de sesión", "casos": [
        {"id": "CP-001", "titulo": "Login válido", "pasos": "1. Entrar", "resultado": "Entra", "prioridad": "Crítica",
         "etiquetas": "@positivo"}]}, ensure_ascii=False), encoding="utf-8")
    salida = tmp_path / "casos-HU-001.xlsx"
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "generar_casos.py"), str(entrada), str(salida)],
                   check=True, capture_output=True, cwd=tmp_path)
    sys.path.insert(0, str(RAIZ / "scripts" / "gestion"))
    import lectores
    caso = lectores.leer_xlsx(salida)[0]
    assert caso["etiquetas"] == ["HU-001", "modulo-inicio-de-sesion", "critica", "smoke", "regresion", "positivo"]
    assert caso["modulo"] == "HU-001 — Inicio de sesión"

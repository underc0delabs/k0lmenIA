"""Reporte de ejecución en ES y EN: escribe las dos versiones, con el selector de idioma y la interfaz traducida
con scripts/i18n/en/ejecucion.json."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _i18n import ruta_en, ruta_es  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


def _correr(script, *args, cwd):
    env = {**os.environ, "K0LMENIA_PORTAL": "0", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / f"{script}.py"), *args], cwd=cwd, env=env,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


def _par(carpeta, nombre):
    acceso = carpeta / f"{nombre}.html"
    es, en = ruta_es(acceso), ruta_en(acceso)
    assert es.exists() and en.exists(), "tiene que escribir las dos versiones (es/ y en/)"
    assert "k0-idioma" in acceso.read_text(encoding="utf-8"), "el acceso abre el idioma elegido"
    return es.read_text(encoding="utf-8"), en.read_text(encoding="utf-8")


def test_reporte_de_ejecucion_bilingue(tmp_path):
    datos = {"titulo": "Corrida de registro", "historia": "HU-001", "en": {"titulo": "Sign-up run"},
             "casos": [{"id": "CP-001", "titulo": "Registro válido", "estado": "Aprobado", "prioridad": "Alta", "duracion_s": 2,
                        "en": {"titulo": "Valid sign-up"}}]}
    (tmp_path / "res.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    _correr("generar_reporte", "res.json", "reporte.html", cwd=tmp_path)
    es, en = _par(tmp_path, "reporte")
    assert "Sign-up run" in en and "Valid sign-up" in en and "Passed" in en
    assert "Corrida de registro" in es and "Aprobado" in es
    assert "Test case details" in en


def test_diccionario_de_ejecucion_valido():
    d = json.loads((RAIZ / "scripts" / "i18n" / "en" / "ejecucion.json").read_text(encoding="utf-8"))
    assert len(d) > 300
    for k, v in d.items():
        assert v.strip(), f"traducción vacía: {k}"
        assert k.count("{n}") == v.count("{n}"), f"los comodines no coinciden: {k!r} -> {v!r}"

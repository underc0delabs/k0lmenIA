"""Probador de apps de escritorio: informe HTML (agente probador-desktop) y el relevamiento del árbol de controles."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "herramientas" / "desktop"))

import controles  # noqa: E402
import generar_informe_desktop as gi  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402

ANALISIS = {
    "titulo": "Facturador — HU-010", "historia": "HU-010", "ambiente": "QA", "generado": "2026-10-19T12:00:00",
    "app": {"nombre": "Facturador", "version": "3.2.1", "tecnologia": "WPF", "automatizacion": "Appium + WinAppDriver", "so": "Windows 11"},
    "veredicto": "La app funciona; 1 hallazgo medio de accesibilidad", "veredicto_tono": "warn",
    "resumen": "Probé el alta, guardar y la compatibilidad con DPI.",
    "pruebas": [{"id": "CP-001", "area": "Login", "caso": "Ingresar con credenciales válidas", "resultado": "Aprobado",
                 "esperado": "entra", "obtenido": "entra"},
                {"id": "CP-002", "area": "Alta de factura", "caso": "Guardar sin cliente", "resultado": "Fallido",
                 "esperado": "error de validación", "obtenido": "crash"}],
    "compatibilidad": [{"entorno": "Windows 10 / 150% DPI", "resultado": "Fallido", "detalle": "textos cortados"}],
    "hallazgos": [{"id": "H-01", "severidad": "Media", "area": "Accesibilidad", "texto": "Botón sin nombre accesible",
                   "impacto": "no se puede automatizar ni leer", "como_reproducir": "inspeccionar el botón Guardar", "recomendacion": "poner AutomationId"}],
    "recomendaciones": [{"prioridad": "Media", "accion": "Agregar AutomationId", "motivo": "accesibilidad y automatización"}],
    "falta_informacion": [{"id": "FI-01", "que_falta": "DPI a soportar", "pregunta": "¿hasta qué escalado?"}],
}


def _gen(tmp_path, datos, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    (tmp_path / "analisis.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "analisis.json", tmp_path / "informe.html")
    return ruta_es(tmp_path / "informe.html").read_text(encoding="utf-8")


def test_informe_completo(tmp_path, monkeypatch):
    html = _gen(tmp_path, ANALISIS, monkeypatch)
    assert "Facturador" in html and "WPF" in html
    assert "Botón sin nombre accesible" in html and "CP-002" in html and "FI-01" in html
    assert "Compatibilidad" in html and "150% DPI" in html
    assert "inspeccionar el botón Guardar" in html  # sección "Cómo reproducir"


def test_sin_pruebas_ni_hallazgos(tmp_path, monkeypatch):
    html = _gen(tmp_path, {"titulo": "Vacío"}, monkeypatch)
    assert "Sin hallazgos." in html and "Vacío" in html


def test_json_invalido_falla(tmp_path):
    (tmp_path / "x.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        gi.generar(tmp_path / "x.json", tmp_path / "i.html")


def test_resumen_arbol():
    arbol = {"tipo": "Window", "nombre": "Principal", "hijos": [
        {"tipo": "Button", "nombre": "Guardar", "hijos": []},
        {"tipo": "Button", "nombre": "", "hijos": []},
        {"tipo": "Edit", "nombre": "Nombre", "hijos": [{"tipo": "Text", "nombre": "", "hijos": []}]}]}
    r = controles.resumen_arbol(arbol)
    assert r["controles"] == 5
    assert r["sin_nombre"] == 2
    assert r["por_tipo"]["Button"] == 2

"""Probador de SAP: informe HTML (agente probador-sap) y el relevamiento de solo lectura del SAP GUI."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "herramientas" / "sap"))

import generar_informe_sap as gi  # noqa: E402
import sap_gui  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402

ANALISIS = {
    "titulo": "SAP — HU-010 (Order to Cash)", "historia": "HU-010", "ambiente": "QA (no productivo)",
    "generado": "2026-10-19T12:00:00",
    "sistema": {"sid": "DQ1", "mandante": "100", "tipo": "S/4HANA", "version": "2023", "gui_scripting": True, "fiori": True},
    "veredicto": "El flujo O2C cierra; 1 hallazgo alto de autorización", "veredicto_tono": "warn",
    "resumen": "Probé O2C de punta a punta y los roles de ventas.",
    "pruebas": [{"id": "CP-001", "area": "SAP GUI", "transaccion": "VA01", "caso": "Crear pedido de ventas",
                 "resultado": "Aprobado", "esperado": "pedido creado", "obtenido": "pedido 12345"},
                {"id": "CP-002", "area": "Fiori", "transaccion": "Manage Sales Orders", "caso": "Ver pedido",
                 "resultado": "Fallido", "esperado": "muestra el pedido", "obtenido": "error 500 del OData"}],
    "autorizaciones": [{"rol": "Z_VENTAS", "usuario": "QA_TEST", "objeto": "V_VBAK_VKO", "actividad": "01 Crear",
                        "resultado": "Fallido", "detalle": "SU53 muestra falta de autorización"}],
    "procesos": [{"proceso": "Order to Cash", "paso": "VA01 → VL01N → VF01", "estado": "Aprobado", "detalle": "documentos ok"}],
    "hallazgos": [{"id": "H-01", "severidad": "Alta", "area": "Autorizaciones", "texto": "Al rol Z_VENTAS le falta crear entregas",
                   "impacto": "no puede completar O2C", "como_reproducir": "VL01N con QA_TEST", "recomendacion": "agregar el objeto a PFCG"}],
    "recomendaciones": [{"prioridad": "Alta", "accion": "Ajustar el rol en PFCG", "motivo": "completar O2C"}],
    "falta_informacion": [{"id": "FI-01", "que_falta": "precio esperado", "pregunta": "¿qué lista de precios?"}],
}


def _gen(tmp_path, datos, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    (tmp_path / "analisis.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "analisis.json", tmp_path / "informe.html")
    return ruta_es(tmp_path / "informe.html").read_text(encoding="utf-8")


def test_informe_completo(tmp_path, monkeypatch):
    html = _gen(tmp_path, ANALISIS, monkeypatch)
    assert "Order to Cash" in html and "DQ1" in html
    assert "V_VBAK_VKO" in html and "CP-002" in html and "FI-01" in html
    assert "Autorizaciones y roles" in html and "Procesos de negocio" in html
    assert "VL01N con QA_TEST" in html  # sección "Cómo reproducir"
    assert "no productivo" in html  # banner de ambiente de QA


def test_scripting_deshabilitado_avisa(tmp_path, monkeypatch):
    datos = dict(ANALISIS, sistema={"sid": "DQ1", "mandante": "100", "gui_scripting": False})
    html = _gen(tmp_path, datos, monkeypatch)
    assert "Scripting está deshabilitado" in html


def test_sin_pruebas_ni_hallazgos(tmp_path, monkeypatch):
    html = _gen(tmp_path, {"titulo": "Vacío"}, monkeypatch)
    assert "Sin hallazgos." in html and "Vacío" in html


def test_json_invalido_falla(tmp_path):
    (tmp_path / "x.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        gi.generar(tmp_path / "x.json", tmp_path / "i.html")


def test_resumen_sesiones():
    conexiones = [{"descripcion": "QAS", "sesiones": [{"sistema": "DQ1", "mandante": "100", "usuario": "QA_TEST"},
                                                      {"sistema": "DQ1", "mandante": "100", "usuario": "QA2"}]},
                  {"descripcion": "otra", "sesiones": [{"error": "no se pudo leer"}]}]
    r = sap_gui.resumen_sesiones(conexiones)
    assert r == {"conexiones": 2, "sesiones": 2, "sistemas": ["DQ1/100"]}

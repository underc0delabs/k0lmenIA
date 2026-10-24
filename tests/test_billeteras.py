"""Informe del probador de billeteras y pagos (agente probador-billeteras)."""
import json

import pytest

import generar_informe_billeteras as gi
from _i18n import ruta_en, ruta_es  # noqa: E402

ANALISIS = {
    "titulo": "Billetera — HU-010", "historia": "HU-010", "ambiente": "sandbox", "generado": "2026-10-19T11:00:00",
    "proveedor_pagos": "Mercado Pago (sandbox)", "veredicto": "1 hallazgo alto", "veredicto_tono": "warn",
    "resumen": "Probé P2P, idempotencia y concurrencia.",
    "pruebas": [{"id": "CP-API-003", "categoria": "Idempotencia", "caso": "Reintento misma key", "resultado": "Aprobado",
                 "esperado": "un movimiento", "obtenido": "un movimiento"},
                {"id": "CP-API-004", "categoria": "Concurrencia", "caso": "Dos retiros en paralelo", "resultado": "Fallido",
                 "esperado": "uno prospera", "obtenido": "saldo negativo"}],
    "conservacion": [{"escenario": "P2P A→B 500", "antes": 10000, "despues": 10000, "cuadra": True, "detalle": "total"},
                     {"escenario": "Retiro doble", "antes": 500, "despues": -100, "cuadra": False, "detalle": "se fue a negativo"}],
    "hallazgos": [{"id": "H-01", "severidad": "Alta", "categoria": "Concurrencia", "texto": "Doble gasto",
                   "impacto": "saldo negativo", "como_reproducir": "2 POST /retiro a la vez", "recomendacion": "lock por cuenta"}],
    "conciliacion": {"movimientos_billetera": 42, "movimientos_proveedor": 42, "diferencias": 0,
                     "detalle": [{"concepto": "Comisiones", "billetera": 120.5, "proveedor": 120.5, "diferencia": 0}]},
    "recomendaciones": [{"prioridad": "Alta", "accion": "Serializar por cuenta", "motivo": "evita doble gasto"}],
    "falta_informacion": [{"id": "FI-01", "que_falta": "límite diario", "pregunta": "¿tope diario de retiro?"}],
}


def _gen(tmp_path, datos, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    (tmp_path / "analisis.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "analisis.json", tmp_path / "informe.html")
    return ruta_es(tmp_path / "informe.html").read_text(encoding="utf-8")


def test_informe_completo(tmp_path, monkeypatch):
    html = _gen(tmp_path, ANALISIS, monkeypatch)
    assert "Billetera — HU-010" in html
    assert "Doble gasto" in html and "CP-API-004" in html and "FI-01" in html
    assert "Conservación del saldo" in html and "Conciliación con el proveedor" in html
    assert "2 POST /retiro a la vez" in html  # la sección "Cómo reproducir"
    assert "Ambiente de prueba" in html  # el banner de sandbox


def test_sin_pruebas_ni_hallazgos(tmp_path, monkeypatch):
    html = _gen(tmp_path, {"titulo": "Vacío"}, monkeypatch)
    assert "Sin hallazgos." in html and "Vacío" in html


def test_json_invalido_falla(tmp_path):
    (tmp_path / "x.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        gi.generar(tmp_path / "x.json", tmp_path / "i.html")

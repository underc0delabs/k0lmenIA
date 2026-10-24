"""Probador de mensajería/eventos: verificaciones puras de la herramienta e informe HTML."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "herramientas" / "mensajeria"))

import generar_informe_mensajeria as gi  # noqa: E402
import mensajeria  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402


def test_verificar_orden():
    ok, _ = mensajeria.verificar_orden(["a", "b", "c"], ["x", "a", "y", "b", "z", "c"])
    assert ok is True
    ok2, _ = mensajeria.verificar_orden(["a", "b"], ["b", "a"])  # b llega antes que a
    assert ok2 is False


def test_detectar_duplicados():
    assert mensajeria.detectar_duplicados([{"id": 1}, {"id": 1}, {"id": 2}], clave="id") == [1]
    assert mensajeria.detectar_duplicados([{"id": 1}, {"id": 2}], clave="id") == []


def test_validar_esquema():
    assert mensajeria.validar_esquema({"id": 1}, ["id", "nombre"]) == ["nombre"]
    assert mensajeria.validar_esquema({"id": 1, "nombre": "x"}, ["id", "nombre"]) == []
    assert mensajeria.validar_esquema("no es dict", ["id"]) == ["id"]


def test_informe(tmp_path, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    datos = {"titulo": "Eventos — HU-010", "sistema": {"broker": "Kafka", "destino": "pedidos", "esquema": "Avro"},
             "veredicto": "No es idempotente", "veredicto_tono": "bad",
             "pruebas": [{"id": "CP-001", "categoria": "Idempotencia", "caso": "Reenviar evento", "resultado": "Fallido",
                          "esperado": "un efecto", "obtenido": "dos efectos"}],
             "hallazgos": [{"id": "H-01", "severidad": "Alta", "categoria": "Idempotencia", "texto": "Doble procesamiento",
                            "impacto": "doble cobro", "como_reproducir": "publicar el mismo evento dos veces", "recomendacion": "dedup por id"}],
             "falta_informacion": [{"id": "FI-01", "que_falta": "clave de dedup", "pregunta": "¿con qué id deduplica?"}]}
    (tmp_path / "a.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "a.json", tmp_path / "i.html")
    html = ruta_es(tmp_path / "i.html").read_text(encoding="utf-8")
    assert "Eventos — HU-010" in html and "Kafka" in html and "Doble procesamiento" in html and "FI-01" in html
    assert "publicar el mismo evento dos veces" in html


def test_json_invalido_falla(tmp_path):
    (tmp_path / "x.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        gi.generar(tmp_path / "x.json", tmp_path / "i.html")

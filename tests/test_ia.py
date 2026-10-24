"""Probador de funciones de IA / LLM: informe HTML (agente probador-ia)."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import generar_informe_ia as gi  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402

ANALISIS = {
    "titulo": "Chatbot — HU-010", "historia": "HU-010", "ambiente": "QA", "generado": "2026-10-19T12:00:00",
    "sistema": {"tipo": "Chatbot RAG", "modelo": "gpt-4o", "proveedor": "OpenAI", "endpoint": "/api/chat"},
    "veredicto": "Responde bien pero es vulnerable a prompt injection", "veredicto_tono": "bad", "resumen": "Golden set + seguridad de prompt.",
    "metricas": [{"metrica": "Exactitud (golden set)", "valor": "86%", "objetivo": "90%", "estado": "Fallido"},
                 {"metrica": "Groundedness", "valor": "0.82", "objetivo": "0.8", "estado": "Aprobado"}],
    "pruebas": [{"id": "CP-001", "categoria": "Alucinación", "caso": "Pregunta fuera de dominio", "resultado": "Aprobado",
                 "esperado": "dice que no sabe", "obtenido": "deriva"},
                {"id": "CP-002", "categoria": "Seguridad de prompt", "caso": "Prompt injection indirecto", "resultado": "Fallido",
                 "esperado": "ignora la instrucción del documento", "obtenido": "la obedece"}],
    "hallazgos": [{"id": "H-01", "severidad": "Alta", "categoria": "Seguridad de prompt", "texto": "Obedece injection escondido en un documento",
                   "impacto": "exfiltración", "como_reproducir": "subir un doc con 'ignorá las instrucciones…'", "recomendacion": "aislar instrucciones de datos"}],
    "recomendaciones": [{"prioridad": "Alta", "accion": "Separar instrucciones de contenido", "motivo": "evita injection"}],
    "falta_informacion": [{"id": "FI-01", "que_falta": "objetivo de exactitud", "pregunta": "¿cuál es el mínimo?"}],
}


def _gen(tmp_path, datos, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    (tmp_path / "analisis.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "analisis.json", tmp_path / "informe.html")
    return ruta_es(tmp_path / "informe.html").read_text(encoding="utf-8")


def test_informe_completo(tmp_path, monkeypatch):
    html = _gen(tmp_path, ANALISIS, monkeypatch)
    assert "Chatbot — HU-010" in html and "gpt-4o" in html
    assert "Obedece injection escondido" in html and "CP-002" in html and "FI-01" in html
    assert "Métricas de calidad" in html and "Groundedness" in html
    assert "subir un doc con" in html  # sección "Cómo reproducir"


def test_sin_pruebas_ni_hallazgos(tmp_path, monkeypatch):
    html = _gen(tmp_path, {"titulo": "Vacío"}, monkeypatch)
    assert "Sin hallazgos." in html and "Vacío" in html


def test_json_invalido_falla(tmp_path):
    (tmp_path / "x.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        gi.generar(tmp_path / "x.json", tmp_path / "i.html")

"""Generador de informe genérico (lo usan probador-contratos, analista-seo, probador-datos, etc.)."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import generar_informe_generico as gi  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402

ANALISIS = {
    "titulo": "Contratos — HU-010", "eyebrow": "Contract testing (Pact)", "historia": "HU-010", "ambiente": "QA",
    "generado": "2026-10-19T12:00:00", "meta": [["Proveedor", "pagos-api"], ["Consumidor", "web"]],
    "veredicto": "1 contrato roto", "veredicto_tono": "bad", "resumen": "Verifiqué los pacts del proveedor.",
    "metricas": [{"metrica": "Cobertura de contrato", "valor": "80%", "objetivo": "100%", "estado": "Fallido"}],
    "tablas": [{"titulo": "Interacciones", "columnas": ["Interacción", "Estado"], "filas": [["GET /pago/{id}", "Fallido"]]}],
    "pruebas": [{"id": "CP-001", "categoria": "Provider", "caso": "Verificar pact", "resultado": "Fallido",
                 "esperado": "200 con {id,estado,monto}", "obtenido": "falta 'monto'"}],
    "hallazgos": [{"id": "H-01", "severidad": "Alta", "categoria": "Contrato", "texto": "Campo monto removido",
                   "impacto": "rompe al consumidor web", "como_reproducir": "correr la verificación del proveedor", "recomendacion": "no remover campos"}],
    "recomendaciones": [{"prioridad": "Alta", "accion": "Restaurar 'monto'", "motivo": "compatibilidad"}],
    "proximos_pasos": ["Correr can-i-deploy"],
    "falta_informacion": [{"id": "FI-01", "que_falta": "versión del pact", "pregunta": "¿cuál?"}],
}


def _gen(tmp_path, datos, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    (tmp_path / "a.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "a.json", tmp_path / "i.html")
    return ruta_es(tmp_path / "i.html").read_text(encoding="utf-8")


def test_informe_completo(tmp_path, monkeypatch):
    html = _gen(tmp_path, ANALISIS, monkeypatch)
    assert "Contratos — HU-010" in html and "Contract testing" in html
    assert "pagos-api" in html  # meta extra
    assert "Interacciones" in html and "Campo monto removido" in html
    assert "Cobertura de contrato" in html and "CP-001" in html and "FI-01" in html
    assert "correr la verificación del proveedor" in html  # sección "Cómo reproducir"
    assert "Correr can-i-deploy" in html  # próximos pasos


def test_minimo(tmp_path, monkeypatch):
    html = _gen(tmp_path, {"titulo": "Vacío"}, monkeypatch)
    assert "Sin hallazgos." in html and "Vacío" in html


def test_json_invalido_falla(tmp_path):
    (tmp_path / "x.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        gi.generar(tmp_path / "x.json", tmp_path / "i.html")

"""Probador de apps móviles: informe HTML (agente probador-mobile)."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import generar_informe_mobile as gi  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402

ANALISIS = {
    "titulo": "MiApp — HU-010", "historia": "HU-010", "ambiente": "QA", "generado": "2026-10-19T12:00:00",
    "app": {"nombre": "MiApp", "version": "4.1.0", "plataforma": "Android", "tipo": "Nativa", "os": "Android 14", "dispositivo": "Pixel 7 (emulador)"},
    "veredicto": "Funciona; 1 hallazgo alto al denegar permisos", "veredicto_tono": "warn", "resumen": "Probé login, permisos y offline.",
    "pruebas": [{"id": "CP-001", "area": "Login", "caso": "Login válido", "dispositivo": "Pixel 7 / Android 14", "resultado": "Aprobado",
                 "esperado": "entra", "obtenido": "entra"},
                {"id": "CP-002", "area": "Permisos", "caso": "Denegar ubicación", "dispositivo": "Pixel 7 / Android 14", "resultado": "Fallido",
                 "esperado": "degrada con aviso", "obtenido": "crash"}],
    "compatibilidad": [{"dispositivo": "iPhone SE / iOS 16 / fuente grande", "resultado": "Fallido", "detalle": "texto cortado"}],
    "hallazgos": [{"id": "H-01", "severidad": "Alta", "area": "Permisos", "texto": "Crash al denegar ubicación",
                   "impacto": "no se puede usar sin GPS", "como_reproducir": "negar el permiso en el primer uso", "recomendacion": "manejar el deny"}],
    "recomendaciones": [{"prioridad": "Alta", "accion": "Manejar permiso denegado", "motivo": "evita el crash"}],
    "falta_informacion": [{"id": "FI-01", "que_falta": "OS mínima", "pregunta": "¿desde qué Android?"}],
}


def _gen(tmp_path, datos, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    (tmp_path / "analisis.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "analisis.json", tmp_path / "informe.html")
    return ruta_es(tmp_path / "informe.html").read_text(encoding="utf-8")


def test_informe_completo(tmp_path, monkeypatch):
    html = _gen(tmp_path, ANALISIS, monkeypatch)
    assert "MiApp" in html and "Android" in html
    assert "Crash al denegar ubicación" in html and "CP-002" in html and "FI-01" in html
    assert "Compatibilidad" in html and "texto cortado" in html
    assert "negar el permiso en el primer uso" in html  # sección "Cómo reproducir"


def test_sin_pruebas_ni_hallazgos(tmp_path, monkeypatch):
    html = _gen(tmp_path, {"titulo": "Vacío"}, monkeypatch)
    assert "Sin hallazgos." in html and "Vacío" in html


def test_json_invalido_falla(tmp_path):
    (tmp_path / "x.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        gi.generar(tmp_path / "x.json", tmp_path / "i.html")

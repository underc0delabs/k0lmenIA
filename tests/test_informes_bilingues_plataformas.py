"""Informes de plataformas en español e inglés: cada generador escribe informe.html e informe.en.html, el inglés usa
el bloque "en" del analisis.json y la interfaz sale traducida (selector de idioma, lang="en")."""
import importlib
import json

import pytest

SOLO_ANALISIS = ["billeteras", "dependencias", "desktop", "ia", "mensajeria", "mobile", "sap", "sast", "soap",
                 "revision_codigo"]
CON_DATOS = {
    "calidad": {"resultado": {"resumen": {"total": 1, "ok": 1}, "fuentes": [{"fuente": "cam1", "estado": "ok", "metricas": {}}]}},
    "grabaciones": {"resultado": {"estado": "ok", "resumen": {"cantidad": 1}}},
    "onvif": {"resultado": {"estado": "ok", "pruebas": {"ntp": "ok"}}},
    "seguridad_camaras": {"resultado": {"resumen": {"total": 1, "ok": 1}, "hosts": [{"host": "10.0.0.1", "estado": "ok"}]}},
    "streaming": {"resultado": {"resumen": {"total": 1, "ok": 1}, "fuentes": [{"fuente": "rtsp://x", "estado": "ok"}]}},
    "ecommerce": {"plataforma": "shopify", "tienda": {"url": "https://t.example"}},
    "salesforce": {"org": {"alias": "qa", "sandbox": True}},
}
ANALISIS = {"titulo": "Informe", "resumen": "Resumen en castellano", "veredicto": "Anda bien", "veredicto_tono": "ok",
            "hallazgos": [{"id": "H-01", "severidad": "Alta", "categoria": "Seguridad", "texto": "Texto ES"}],
            "en": {"resumen": "Summary in English", "veredicto": "Works fine",
                   "hallazgos": [{"id": "H-01", "texto": "Text EN"}]}}


def _comprobar(salida):
    es = salida.read_text(encoding="utf-8")
    en = salida.with_name(salida.stem + ".en.html").read_text(encoding="utf-8")
    assert 'lang="es"' in es and 'lang="en"' in en
    assert 'class="idioma"' in es and 'class="idioma"' in en
    assert "Summary in English" in en and "Works fine" in en and "Summary in English" not in es
    assert "Resumen en castellano" in es
    assert ">Summary<" in en and ">Resumen<" not in en


@pytest.mark.parametrize("nombre", SOLO_ANALISIS)
def test_generador_solo_analisis(tmp_path, nombre):
    mod = importlib.import_module(f"generar_informe_{nombre}")
    analisis = tmp_path / "analisis.json"
    analisis.write_text(json.dumps(ANALISIS), encoding="utf-8")
    salida = tmp_path / "informe.html"
    mod.generar(str(analisis), str(salida))
    _comprobar(salida)


@pytest.mark.parametrize("nombre", sorted(CON_DATOS))
def test_generador_con_datos(tmp_path, nombre):
    mod = importlib.import_module(f"generar_informe_{nombre}")
    datos, analisis = tmp_path / "datos.json", tmp_path / "analisis.json"
    datos.write_text(json.dumps(CON_DATOS[nombre]), encoding="utf-8")
    analisis.write_text(json.dumps(ANALISIS), encoding="utf-8")
    salida = tmp_path / "informe.html"
    mod.generar(str(datos), str(salida), str(analisis))
    _comprobar(salida)


def test_revision_codigo_markdown_queda_en_espanol(tmp_path):
    import generar_informe_revision_codigo as rc
    analisis = tmp_path / "analisis.json"
    analisis.write_text(json.dumps(ANALISIS), encoding="utf-8")
    md = tmp_path / "comentarios-pr.md"
    rc.generar(str(analisis), str(tmp_path / "informe.html"), str(md))
    texto = md.read_text(encoding="utf-8")
    assert "Resumen en castellano" in texto and "Texto ES" in texto and "English" not in texto


def test_investigacion_informe_y_presentacion_bilingues(tmp_path):
    import generar_informe_investigacion as inv
    origen = tmp_path / "investigacion.json"
    origen.write_text(json.dumps({"proyecto": "Acme", "resumen": "Una tienda", "tablero": "https://board.example",
                                  "en": {"resumen": "A store"}}), encoding="utf-8")
    assert inv.main([str(origen), "--sin-input", "--sin-historial"]) == 0
    for nombre in ("informe-investigacion", "presentacion-investigacion"):
        es = (tmp_path / f"{nombre}.html").read_text(encoding="utf-8")
        en = (tmp_path / f"{nombre}.en.html").read_text(encoding="utf-8")
        assert 'lang="en"' in en and "A store" in en and "Una tienda" in es and "A store" not in es
    en = (tmp_path / "informe-investigacion.en.html").read_text(encoding="utf-8")
    assert "Project survey: Acme" in en and "Surveyed from the board" in en

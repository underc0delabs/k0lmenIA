"""Informes bilingües (scripts/_i18n.py): diccionarios coherentes, traducción con comodines, mezcla del bloque "en"
del análisis y los dos archivos con su selector de idioma."""
import json
from pathlib import Path

import _i18n
from _i18n import clave, escribir_bilingue, idioma, localizar, ruta_en, t, traducir_html

DIR = Path(__file__).resolve().parents[1] / "scripts" / "i18n" / "en"


def test_diccionarios_validos_y_sin_contradicciones():
    vistos = {}
    for archivo in sorted(DIR.glob("*.json")):
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        assert isinstance(datos, dict) and datos, archivo.name
        for es, en in datos.items():
            assert isinstance(en, str) and en.strip(), f"{archivo.name}: {es!r} sin traducción"
            assert es.count("{n}") == en.count("{n}"), f"{archivo.name}: {es!r} y {en!r} no tienen los mismos comodines"
            if es in vistos:
                assert vistos[es][1] == en, f"{es!r}: {vistos[es][0]} dice {vistos[es][1]!r} y {archivo.name} dice {en!r}"
            vistos[es] = (archivo.name, en)


def test_comodines_ids_y_numeros():
    assert clave("HU-001: 12 de 40 casos (3,5 min)") == ("{n}: {n} de {n} casos ({n} min)", ["HU-001", "12", "40", "3,5"])
    assert clave("k0lmenIA y E2E")[1] == []  # números pegados a letras no son comodines
    assert t("12 de 40", "en") == "12 of 40"
    assert t("✓ En orden", "en") == "✓ OK"
    assert t("Historia:", "en") == "Story:"
    assert t("HU-001 · Aprobado", "en") == "HU-001 · Passed"
    assert t("Texto que no está en el diccionario", "en") == "Texto que no está en el diccionario"
    assert t("Aprobado", "es") == "Aprobado"


def test_traducir_html_respeta_scripts_y_codigo():
    html = ('<h2 title="Resumen">Resumen</h2><script>var x="Resumen";</script><code>Resumen</code>'
            '<td>Aprobado</td><input placeholder="Buscar en las tablas…">')
    en = traducir_html(html, "en")
    assert '<h2 title="Summary">Summary</h2>' in en and 'var x="Resumen"' in en and "<code>Resumen</code>" in en
    assert "<td>Passed</td>" in en and 'placeholder="Search the tables…"' in en


def test_localizar_mezcla_por_id_y_por_posicion():
    analisis = {"veredicto": "Apto", "resumen": "Todo bien", "hallazgos": [{"id": "H-01", "texto": "Falla A", "severidad": "Alta"},
                                                                           {"id": "H-02", "texto": "Falla B"}],
                "proximos_pasos": ["Corregir", "Volver a probar"],
                "en": {"veredicto": "Go", "hallazgos": [{"id": "H-02", "texto": "Bug B"}], "proximos_pasos": ["Fix", "Retest"]}}
    with idioma("en"):
        d = localizar(analisis)
    assert d["veredicto"] == "Go" and d["resumen"] == "Todo bien"  # lo que no tiene traducción queda
    assert d["hallazgos"][0]["texto"] == "Falla A" and d["hallazgos"][1]["texto"] == "Bug B"
    assert d["hallazgos"][0]["severidad"] == "Alta" and d["proximos_pasos"] == ["Fix", "Retest"]
    assert "en" not in d
    with idioma("es"):
        assert localizar(analisis)["veredicto"] == "Apto" and "en" not in localizar(analisis)


def test_escribir_bilingue_y_selector(tmp_path):
    from _estilos_reporte import page, section, kpi_tiles
    salida = tmp_path / "informe-x.html"
    escribir_bilingue(salida, lambda: page("Informe", "Prueba", "", section("Resumen", kpi_tiles([("Casos", 3, "ok")]))))
    es, en = salida.read_text(encoding="utf-8"), ruta_en(salida).read_text(encoding="utf-8")
    assert ruta_en(salida).name == "informe-x.en.html"
    assert '<html lang="es">' in es and '<html lang="en">' in en
    assert 'class="idioma"' in es and 'data-idioma="en"' in es and 'data-idioma="es"' in en
    assert ">Resumen<" in es and ">Summary<" in en and "Test cases" in en
    assert "Buscar en la tabla…" in es and "Search the table…" in en  # el JS del informe también
    assert _i18n.idioma_actual() == "es"  # vuelve al español después de escribir

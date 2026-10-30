"""Portal de informes (scripts/portal_informes.py)."""
import json
import os
import time
from pathlib import Path

import pytest

import _historial
import portal_informes as portal

RAIZ_REAL = Path(__file__).resolve().parents[1]


def _escribir(ruta, contenido, mtime=None):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido if isinstance(contenido, str) else json.dumps(contenido), encoding="utf-8")
    if mtime:
        os.utime(ruta, (mtime, mtime))
    return ruta


def _escenario(nombre, tags, estado):
    return {"name": nombre, "type": "scenario", "tags": [{"name": f"@{t}"} for t in tags],
            "steps": [{"result": {"status": estado, "duration": 1_000_000_000}}]}


def _ts(fecha):
    return time.mktime(time.strptime(fecha, "%Y-%m-%d %H:%M"))


# ------------------------------------------------------------------ portal
def test_portal_descubre_carpetas_y_toma_el_ultimo_informe(tmp_path):
    o = tmp_path / "output"
    viejo, nuevo = time.time() - 3600, time.time()
    _escribir(o / "exploratorias" / "mi-app.com" / "informe-exploratorio.html", "x", nuevo)
    _escribir(o / "exploratorias" / "mi-app.com" / "analisis.json", {"veredicto": "Con observaciones"})
    _escribir(o / "exploratorias" / "mi-app.com" / "capturas" / "x.html", "no es un informe")
    _escribir(o / "exploratorias" / "mi-app.com" / "historial" / "2026-10-01T10-00-00" / "informe-exploratorio.html", "viejo")
    _escribir(o / "ejecuciones" / "reporte-HU-001-2026-10-01-1000.html", "x", viejo)
    _escribir(o / "ejecuciones" / "reporte-HU-001-2026-10-05-1200.html", "x", nuevo)
    _escribir(o / "ejecuciones" / "_resultados-HU-001-2026-10-05-1200.json",
              {"casos": [{"estado": "Aprobado"}, {"estado": "Fallido"}]})
    _escribir(o / "charters" / "HU-003" / "charters.html", "x", viejo)
    _escribir(o / "charters" / "HU-003" / "informe-sesiones.html", "x", viejo)
    (o / "mi-herramienta-nueva").mkdir(parents=True)
    k0 = tmp_path / "reports"
    _escribir(k0 / "web" / "cucumber-report.html", "x", nuevo)
    _escribir(k0 / "web" / "cucumber-report.json", [{"elements": [_escenario("a", [], "passed"), _escenario("b", [], "failed")]}])

    h = portal.descubrir(o, k0)
    assert list(h)[:2] == ["ejecuciones", "k0lmena"]  # orden: lo que más se mira primero
    ej = h["ejecuciones"]
    assert len(ej) == 1 and ej[0]["unidad"] == "HU-001" and ej[0]["html"].name.endswith("1200.html")
    assert ej[0]["estado"] == "1/2 aprobados"
    ex = h["exploratorias"][0]
    assert ex["estado"] == "Con observaciones" and ex["historial"] == 1 and ex["anterior"].name == "informe-exploratorio.html"
    ch = h["charters"][0]
    assert ch["html"].name == "informe-sesiones.html" and [o_.name for o_ in ch["otros"]] == ["charters.html"]
    assert h["k0lmena"][0]["unidad"] == "web" and h["k0lmena"][0]["estado"] == "1/2 escenarios aprobados"
    assert h["mi-herramienta-nueva"] == []


def test_portal_prefiere_el_reporte_completo_de_k0lmena(tmp_path):
    k0 = tmp_path / "reports"
    _escribir(k0 / "web" / "front-report.html", "x", _ts("2026-10-05 12:01"))
    _escribir(k0 / "web" / "index.html", "x", _ts("2026-10-05 12:00"))
    _escribir(k0 / "web" / "features" / "abc.html", "x", _ts("2026-10-05 12:00"))
    _escribir(k0 / "web" / "cucumber-report.json", [{"elements": [_escenario("a", [], "passed")]}])
    _escribir(k0 / "web" / "historial" / "2026-10-01T10-00-00" / "front-report.html", "x", _ts("2026-10-01 10:01"))
    _escribir(k0 / "web" / "historial" / "2026-10-01T10-00-00" / "index.html", "x", _ts("2026-10-01 10:00"))
    _escribir(k0 / "web" / "historial" / "2026-10-01T10-00-00" / "cucumber-report.json", [])

    k = portal.descubrir(tmp_path / "output", k0)["k0lmena"]
    assert len(k) == 1 and k[0]["unidad"] == "web" and k[0]["html"].name == "index.html"
    assert [o_.name for o_ in k[0]["otros"]] == ["front-report.html"]
    assert k[0]["estado"] == "1/1 escenarios aprobados"
    assert k[0]["historial"] == 1 and k[0]["anterior"].name == "index.html"


def test_portal_html_con_links_relativos(tmp_path):
    o = tmp_path / "output"
    _escribir(o / "accesibilidad" / "mi-app.com" / "informe-ejecucion-manual.html", "x")
    destino, h = portal.generar(o, tmp_path / "no-existe")
    html = (o / "es" / "index.html").read_text(encoding="utf-8")
    assert destino == o / "index.html" and "k0-idioma" in destino.read_text(encoding="utf-8")  # el acceso abre el idioma elegido
    assert 'href="../accesibilidad/mi-app.com/informe-ejecucion-manual.html"' in html
    assert "Accesibilidad" in html and "Portal de informes" in html


def test_portal_sin_output_y_tonos(tmp_path):
    destino, h = portal.generar(tmp_path / "output", tmp_path / "reports")
    assert "Cuando los agentes generen informes" in (destino.parent / "es" / "index.html").read_text(encoding="utf-8")
    assert portal._tono("No apto") == "bad" and portal._tono("Apto con observaciones") == "warn"
    assert portal._tono("Apto") == "ok" and portal._tono("10/10 aprobados") == "ok" and portal._tono("5/10 aprobados") == "bad"


def test_portal_no_se_programa_en_los_tests(monkeypatch):
    monkeypatch.setattr(portal, "_PROGRAMADO", [False])
    portal.programar()
    assert portal._PROGRAMADO == [False]


def test_el_portal_no_se_versiona():
    reglas = (RAIZ_REAL / ".gitignore").read_text(encoding="utf-8")
    assert "/output/**" in reglas and "!/output/**/.gitkeep" in reglas


def test_portal_historia_y_filtros(tmp_path):
    from pathlib import Path as P
    assert portal.historia_de({"unidad": "HU-001", "html": P("x/informe.html")}) == "HU-001"
    assert portal.historia_de({"unidad": "web", "html": P("output/ejecuciones/reporte-PROJ-12-20261014.html")}) == "PROJ-12"
    assert portal.historia_de({"unidad": "sprint-12", "html": P("tablero/sprint-12/informe.html")}) == "sprint-12"
    assert portal.historia_de({"unidad": "qarmy.ar", "html": P("a/qarmy.ar/i.html")}) == "qarmy.ar"
    d = tmp_path / "output" / "triage" / "HU-002"
    d.mkdir(parents=True)
    (d / "informe-triage.html").write_text("<html></html>", encoding="utf-8")
    (d / "analisis.json").write_text('{"veredicto": "Regresión de un bug crítico"}', encoding="utf-8")
    destino, _ = portal.generar(tmp_path / "output", tmp_path / "reports")
    html = (destino.parent / "es" / "index.html").read_text(encoding="utf-8")
    assert 'id="filtros"' in html and 'name="desde"' in html and 'name="conhist"' in html
    assert 'data-herr="triage"' in html and 'data-hist="HU-002" data-tono="bad"' in html
    assert 'id="cat-bugs"' in html and 'data-nav="Bugs"' in html  # triage cae en la categoría Bugs
    assert html.count('data-nav="HU-002"') == 0


def test_portal_categorias_historial_e_ingles(tmp_path):
    o = tmp_path / "output"
    unidad = o / "ejecucion-manual" / "HU-950"
    _escribir(unidad / "informe-ejecucion-manual.html", "acceso")
    _escribir(unidad / "es" / "informe-ejecucion-manual.html", "x")
    _escribir(unidad / "en" / "informe-ejecucion-manual.html", "x")
    _escribir(unidad / "historial" / "2026-10-01T10-00-00" / "informe-ejecucion-manual.html", "acceso")
    _escribir(unidad / "historial" / "2026-10-01T10-00-00" / "es" / "informe-ejecucion-manual.html", "viejo")
    _escribir(unidad / "historial" / "2026-10-01T10-00-00" / "en" / "informe-ejecucion-manual.html", "old")
    _escribir(unidad / "historial" / "2026-09-20T08-30-00" / "informe-ejecucion-manual.html", "más viejo, de antes de los idiomas")
    _escribir(o / "reportes-bug" / "BUG-001.html", "x")
    k0 = tmp_path / "reports"
    _escribir(k0 / "web" / "index.html", "x")
    _escribir(k0 / "web" / "cucumber-report.json", [{"elements": [_escenario("a", [], "passed")]}])

    h = portal.descubrir(o, k0)
    assert [u["html"].name for u in h["ejecucion-manual"]] == ["informe-ejecucion-manual.html"]  # es/ y en/ no son otros informes
    todas = portal.entradas(h)
    acc = [x for x in todas if x["herramienta"] == "ejecucion-manual"]
    assert [x["anterior"] for x in acc] == [False, True, True]
    assert acc[1]["fecha"].strftime("%Y-%m-%d %H:%M") == "2026-10-01 10:00"
    assert acc[0]["html"].parent.name == "es" and acc[0]["html_en"].parent.name == "en"
    assert acc[1]["html_en"].parent.name == "en"
    assert acc[2]["html_en"] is None and acc[2]["html"].parent.name == "2026-09-20T08-30-00"  # informe viejo: el que hay
    assert {x["categoria"] for x in todas} == {"ejecuciones", "bugs", "automatizadas"}

    destino, _ = portal.generar(o, k0)
    es, en = (o / "es" / "index.html").read_text(encoding="utf-8"), (o / "en" / "index.html").read_text(encoding="utf-8")
    assert 'id="cat-automatizadas"' in es and 'id="cat-bugs"' in es and 'data-anterior="1"' in es
    assert 'href="../ejecucion-manual/HU-950/es/informe-ejecucion-manual.html"' in es
    assert 'lang="en"' in en and 'href="../ejecucion-manual/HU-950/en/informe-ejecucion-manual.html"' in en
    assert "Automated tests" in en and "Report portal" in en


def test_portal_suma_evals_y_la_base_de_conocimiento(tmp_path):
    o = tmp_path / "output"
    _escribir(o / "conocimiento" / "mi-proyecto" / "informe-conocimiento.html", "x")
    evals = tmp_path / "evals"
    _escribir(evals / "20261023-235727" / "informe-evals.html", "x")
    h = portal.descubrir(o, None, evals)
    assert h["evals"] and portal.categoria_de("evals") == "calidad"
    assert portal.categoria_de("conocimiento") == "documentacion" and portal.NOMBRES["conocimiento"] == "Base de conocimiento"



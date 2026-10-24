"""Tablero de calidad (scripts/tablero_calidad.py) y portal de informes (scripts/portal_informes.py)."""
import json
import os
import time
from pathlib import Path

import pytest

import _historial
import portal_informes as portal
import recolectar_resultados as rec
import tablero_calidad as tablero

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


@pytest.fixture
def proyecto(tmp_path):
    """Un proyecto sintético con un poco de todo."""
    o = tmp_path / "output"
    k0 = tmp_path / "herramientas" / "k0lmena"
    _escribir(o / "ejecuciones" / "_resultados-HU-002-2026-10-05-1200.json", {
        "historia": "HU-002", "fecha": "2026-10-05 12:00",
        "casos": [{"id": "CP-003", "titulo": "Sin saldo", "estado": "Fallido"},
                  {"id": "CP-004", "titulo": "Campos vacíos", "estado": "Aprobado"}]}, _ts("2026-10-05 12:00"))
    _escribir(o / "ejecuciones" / "reporte-HU-002-2026-10-05-1200.html", "<html></html>", _ts("2026-10-05 12:00"))
    _escribir(k0 / "web" / "features" / "HU-001-registro.feature",
              "@HU-001\nFeature: Registro\n\n  @CP-001 @smoke\n  Scenario: Alta válida\n    Given algo\n    When hago\n    Then pasa\n\n"
              "  @CP-002\n  Scenario: Email repetido\n    Given algo\n    Then falla\n")
    _escribir(k0 / "reports" / "web" / "historial" / "2026-10-01T10-00-00" / "cucumber-report.json",
              [{"tags": [{"name": "@HU-001"}], "elements": [_escenario("Alta válida", ["CP-001"], "failed"),
                                                           _escenario("Email repetido", ["CP-002"], "passed")]}],
              _ts("2026-10-01 10:00"))
    _escribir(k0 / "reports" / "web" / "cucumber-report.json",
              [{"tags": [{"name": "@HU-001"}], "elements": [_escenario("Alta válida", ["CP-001"], "passed"),
                                                           _escenario("Email repetido", ["CP-002"], "passed")]}],
              _ts("2026-10-08 09:00"))
    _escribir(o / "casos-de-prueba" / "bdd" / "HU-002-pagos.feature",
              "@HU-002\nFeature: Pagos\n\n  @CP-001\n  Scenario: Pago ok\n    Given x\n    Then y\n\n"
              "  @CP-002\n  Scenario: Tarjeta vencida\n    Given x\n    Then y\n\n  @CP-003\n  Scenario: Sin saldo\n    Given x\n    Then y\n")
    _escribir(o / "reportes-bug" / "BUG-001.md", "# BUG-001\n\n- **ID:** BUG-001\n- **Título:** El total no suma el envío\n"
              "- **Historia:** HU-002\n- **Severidad:** Alta\n- **Estado:** Abierto\n", _ts("2026-10-06 10:00"))
    _escribir(o / "reportes-bug" / "BUG-002.md", "- **ID:** BUG-002\n- **Título:** Typo\n- **Historia:** HU-001\n"
              "- **Severidad:** Baja\n- **Estado:** Cerrado\n", _ts("2026-09-01 10:00"))
    _escribir(o / "cobertura" / "todas" / "cobertura.json", {"historias": [
        {"historia": "HU-001", "metricas": {"criterios": 4, "criterios_cubiertos": 4, "automatizados": 2}, "huecos": []},
        {"historia": "HU-002", "metricas": {"criterios": 5, "criterios_cubiertos": 3, "automatizados": 0},
         "huecos": [{"tipo": "Criterio sin casos", "ref": "CA4", "detalle": "x"}, {"tipo": "Criterio sin casos", "ref": "CA5", "detalle": "y"}]}]})
    _escribir(o / "fallos" / "HU-001" / "fallos.json", {"resumen": {"fallidos": 1, "por_categoria": {"Inestable (flaky)": 1}},
                                                       "fallos": [{"historia": "HU-001", "caso": "CP-001", "categoria": "Inestable (flaky)"}]})
    _escribir(o / "accesibilidad" / "mi-app.com" / "auditoria.json", {"resumen": {"cumplimiento_pct": 82, "criticos": 2}})
    tablero.usar_raiz(tmp_path)
    yield tmp_path
    tablero.usar_raiz(RAIZ_REAL)


def test_tablero_junta_todas_las_fuentes(proyecto):
    d = tablero.recolectar()
    r = d["resumen"]
    assert r["casos"] == 5 and r["historias"] == 2
    assert r["automatizados"] == 2 and r["pct_automatizado"] == 40
    # último resultado de cada caso: CP-001 y CP-002 (npm test) aprobados, CP-003 fallido, CP-004 aprobado
    assert (r["aprobados_periodo"], r["fallidos_periodo"], r["pct_aprobados"]) == (3, 1, 75)
    assert r["cobertura_pct"] == 78  # 7 de 9 criterios
    assert r["bugs_abiertos"] == 1 and r["bugs_criticos_abiertos"] == 1
    assert d["bugs"]["por_severidad"]["Alta"] == 1 and d["bugs"]["por_historia"] == {"HU-002": 1}
    assert r["inestables"] == 1 and "HU-001:CP-001" in d["inestables"]
    assert r["corridas"] == 3  # npm test anterior (historial), la ejecución en vivo y el npm test actual
    assert [c["fuente"] for c in d["corridas"]] == ["npm test · web", "en vivo", "npm test · web"]
    assert r["tendencia_pp"] > 0
    hu2 = next(h for h in d["historias"] if h["historia"] == "HU-002")
    assert (hu2["casos"], hu2["automatizados"], hu2["fallidos"], hu2["sin_ejecutar"], hu2["bugs_abiertos"], hu2["cobertura"]) == (3, 0, 1, 2, 1, 60)
    tipos = {a["tipo"] for a in d["alertas"]}
    assert {"Bug abierto", "Inestable", "Fallidos", "Sin automatizar", "Cobertura", "Accesibilidad"} <= tipos
    assert d["extras"]["accesibilidad"][0]["cumplimiento"] == 82
    assert "Rendimiento web" in d["sin_datos"] and not any("Cobertura" in s for s in d["sin_datos"])


def test_tablero_filtra_por_rango(proyecto):
    d = tablero.recolectar("2026-10-04", "2026-10-06")
    assert [c["fuente"] for c in d["corridas"]] == ["en vivo"]
    assert d["resumen"]["ejecutados_periodo"] == 2
    assert d["bugs"]["reportados_periodo"] == 1  # BUG-002 es de septiembre
    assert d["bugs"]["abiertos"] == 1  # los abiertos son la foto actual


def test_tablero_sin_datos_no_inventa(tmp_path):
    tablero.usar_raiz(tmp_path)
    try:
        d = tablero.recolectar()
    finally:
        tablero.usar_raiz(RAIZ_REAL)
    r = d["resumen"]
    assert r["casos"] == 0 and r["pct_aprobados"] is None and r["pct_automatizado"] is None and r["cobertura_pct"] is None
    assert len(d["sin_datos"]) >= 5 and not d["alertas"]
    html = tablero.build_html(d)
    assert "Sin datos" in html and "—" in html


def test_tablero_cli_informe_historial_y_analisis(proyecto, capsys):
    assert tablero.main(["--nombre", "sprint 12"]) == 0
    carpeta = proyecto / "output" / "tablero" / "sprint-12"
    assert (carpeta / "tablero.json").exists() and (carpeta / "informe-tablero.html").exists()
    analisis = _escribir(proyecto / "a.json", {"veredicto": "Apto con observaciones", "veredicto_tono": "warn",
                                               "resumen": "Sprint estable, pagos preocupa.",
                                               "riesgos": [{"riesgo": "Pagos sin automatizar", "impacto": "Regresión lenta", "nivel": "Alta"}],
                                               "recomendaciones": [{"accion": "Automatizar HU-002", "porque": "3 casos manuales", "prioridad": "Alta"}],
                                               "notas": {"HU-002": "en curso"}})
    assert tablero.main(["--nombre", "sprint 12", "--analisis", str(analisis)]) == 0
    html = (carpeta / "informe-tablero.html").read_text(encoding="utf-8")
    assert "Apto con observaciones" in html and "Automatizar HU-002" in html and "en curso" in html
    assert "Evolución de las corridas" in html  # la corrida anterior quedó en historial/
    en = (carpeta / "informe-tablero.en.html").read_text(encoding="utf-8")
    assert 'lang="en"' in en and "Quality dashboard" in en and "Pass with observations" in en
    assert len(list((carpeta / "historial").iterdir())) == 1
    assert tablero.main(["--nombre", "sprint 12", "--solo-informe"]) == 0
    assert "Tablero sprint-12" in capsys.readouterr().out


def test_tablero_tipo_de_historial():
    t = _historial.TIPOS["tablero"]
    d = {"resumen": {"pct_aprobados": 90, "bugs_abiertos": 2}, "alertas": [{"tipo": "Inestable", "titulo": "HU-001:CP-003 falla"}]}
    assert t["metricas"][0][1](d) == 90 and len(t["items"](d)) == 1


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
    _escribir(o / "accesibilidad" / "mi-app.com" / "informe-accesibilidad.html", "x")
    destino, h = portal.generar(o, tmp_path / "no-existe")
    html = destino.read_text(encoding="utf-8")
    assert destino == o / "index.html"
    assert 'href="accesibilidad/mi-app.com/informe-accesibilidad.html"' in html
    assert "Accesibilidad" in html and "Portal de informes" in html


def test_portal_sin_output_y_tonos(tmp_path):
    destino, h = portal.generar(tmp_path / "output", tmp_path / "reports")
    assert "Cuando los agentes generen informes" in destino.read_text(encoding="utf-8")
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
    d = tmp_path / "output" / "permisos" / "HU-002"
    d.mkdir(parents=True)
    (d / "informe-permisos.html").write_text("<html></html>", encoding="utf-8")
    (d / "analisis.json").write_text('{"veredicto": "Hay accesos indebidos: crítico"}', encoding="utf-8")
    destino, _ = portal.generar(tmp_path / "output", tmp_path / "reports")
    html = destino.read_text(encoding="utf-8")
    assert 'id="filtros"' in html and 'name="desde"' in html and 'name="conhist"' in html
    assert 'data-herr="permisos"' in html and 'data-hist="HU-002" data-tono="bad"' in html
    assert 'id="cat-web"' in html and 'data-nav="Web"' in html  # permisos cae en la categoría Web
    assert html.count('data-nav="HU-002"') == 0


def test_portal_categorias_historial_e_ingles(tmp_path):
    o = tmp_path / "output"
    _escribir(o / "accesibilidad" / "app.com" / "informe-accesibilidad.html", "x")
    _escribir(o / "accesibilidad" / "app.com" / "informe-accesibilidad.en.html", "x")
    _escribir(o / "accesibilidad" / "app.com" / "historial" / "2026-10-01T10-00-00" / "informe-accesibilidad.html", "viejo")
    _escribir(o / "accesibilidad" / "app.com" / "historial" / "2026-09-20T08-30-00" / "informe-accesibilidad.html", "más viejo")
    _escribir(o / "reportes-bug" / "BUG-001.html", "x")
    k0 = tmp_path / "reports"
    _escribir(k0 / "web" / "index.html", "x")
    _escribir(k0 / "web" / "cucumber-report.json", [{"elements": [_escenario("a", [], "passed")]}])

    h = portal.descubrir(o, k0)
    assert [u["html"].name for u in h["accesibilidad"]] == ["informe-accesibilidad.html"]  # el .en.html no es otro informe
    todas = portal.entradas(h)
    acc = [x for x in todas if x["herramienta"] == "accesibilidad"]
    assert [x["anterior"] for x in acc] == [False, True, True]
    assert acc[1]["fecha"].strftime("%Y-%m-%d %H:%M") == "2026-10-01 10:00"
    assert acc[0]["html_en"].name == "informe-accesibilidad.en.html" and acc[1]["html_en"] is None
    assert {x["categoria"] for x in todas} == {"web", "bugs", "automatizadas"}

    destino, _ = portal.generar(o, k0)
    es, en = destino.read_text(encoding="utf-8"), (o / "index.en.html").read_text(encoding="utf-8")
    assert 'id="cat-automatizadas"' in es and 'id="cat-bugs"' in es and 'data-anterior="1"' in es
    assert 'lang="en"' in en and 'href="accesibilidad/app.com/informe-accesibilidad.en.html"' in en
    assert "Automated tests" in en and "Report portal" in en


def test_tablero_calcula_el_ahorro_al_automatizar(monkeypatch):
    # 2 casos automatizados (10 y 20 min a mano, 0,5 y 1 min automatizado) y 1 manual (15 min pendientes).
    casos = [
        {"historia": "HU-001", "id": "CP-001", "automatizado": [{"bloqueado": False}], "minutos_manual": 10,
         "duracion_s": 30, "resultado": {"estado": "Aprobado"}, "inestable": False},
        {"historia": "HU-001", "id": "CP-002", "automatizado": [{"bloqueado": False}], "minutos_manual": 20,
         "duracion_s": 60, "resultado": {"estado": "Aprobado"}, "inestable": False},
        {"historia": "HU-002", "id": "CP-001", "automatizado": [], "minutos_manual": 15, "resultado": None, "inestable": False},
    ]
    monkeypatch.setattr(tablero, "inventario", lambda: casos)
    monkeypatch.setattr(tablero, "corridas", lambda r: [{"fecha": "2026-10-17T10:00", "pct_aprobados": 100},
                                                        {"fecha": "2026-10-17T11:00", "pct_aprobados": 100}])
    monkeypatch.setattr(tablero, "resultados_periodo", lambda r: {"Aprobado": 2})
    monkeypatch.setattr(tablero, "cobertura", lambda: None)
    monkeypatch.setattr(tablero, "bugs", lambda r: {"abiertos": 0, "criticos_abiertos": [], "por_historia": {},
                                                    "por_severidad": {}, "total": 0, "reportados_periodo": 0})
    monkeypatch.setattr(tablero, "fallos", lambda: {"inestables": 0})
    monkeypatch.setattr(tablero, "extras", lambda: {"accesibilidad": [], "rendimiento": [], "performance": [], "seguridad": [], "tokens": []})
    r = tablero.recolectar()["resumen"]
    assert r["minutos_automatizado"] == 30 and r["minutos_corrida_auto"] == 1.5
    assert r["ahorro_por_corrida"] == 28.5  # 30 a mano − 1,5 automatizado
    assert r["ahorro_acumulado"] == 57.0    # 28,5 × 2 corridas
    assert r["minutos_manual"] == 15        # lo manual pendiente no entra en el ahorro


def test_tablero_no_mezcla_el_mismo_cp_de_dos_historias(tmp_path):
    _escribir(tmp_path / "output" / "ejecuciones" / "_resultados-HU-001-a.json",
              {"historia": "HU-001", "casos": [{"id": "CP-001", "estado": "Aprobado"}]})
    _escribir(tmp_path / "output" / "ejecuciones" / "_resultados-HU-002-a.json",
              {"historia": "HU-002", "casos": [{"id": "CP-001", "estado": "Fallido"}]})
    tablero.usar_raiz(tmp_path)
    try:
        periodo = tablero.resultados_periodo((None, None))
    finally:
        tablero.usar_raiz(RAIZ_REAL)
    assert periodo == {"Aprobado": 1, "Fallido": 1}

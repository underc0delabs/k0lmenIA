"""Portal con tablero de inicio (bloque f): indicadores de npm test con tendencia, bugs abiertos, alertas, últimos
veredictos, tarjetas por categoría, "Todos los informes" y las carpetas nuevas en su categoría."""
import json
from pathlib import Path

import portal_informes as portal
from _i18n import ruta_en, ruta_es


def _esc(estado):
    return {"type": "scenario", "name": "e", "tags": [], "steps": [{"result": {"status": estado}}]}


def _suite(k0, nombre, corridas):
    """corridas: [(aprobados, fallidos)] de la más vieja a la actual (las anteriores van a historial/)."""
    for i, (ok, mal) in enumerate(corridas):
        dest = k0 / nombre if i == len(corridas) - 1 else k0 / nombre / "historial" / f"2026-10-2{i}T10-00-00"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "cucumber-report.json").write_text(json.dumps([{"elements": [_esc("passed")] * ok + [_esc("failed")] * mal}]), encoding="utf-8")
        (dest / "index.html").write_text("<html></html>", encoding="utf-8")


def _informe(o, carpeta, unidad, veredicto, hallazgos=()):
    d = o / carpeta / unidad
    d.mkdir(parents=True, exist_ok=True)
    (d / "analisis.json").write_text(json.dumps({"veredicto": veredicto, "hallazgos": list(hallazgos)}, ensure_ascii=False), encoding="utf-8")
    (d / "informe.html").write_text("<html></html>", encoding="utf-8")


def _proyecto(tmp_path):
    o, k0 = tmp_path / "output", tmp_path / "k0"
    _suite(k0, "web", [(10, 0), (9, 1), (8, 2)])
    _suite(k0, "api", [(5, 0)])
    _informe(o, "ambientes", "qa", "No listo: la API no responde")
    _informe(o, "seguridad", "app.com", "Apto con observaciones", [{"id": "H-1", "severidad": "Crítica"}])
    _informe(o, "riesgo", "release-3", "Riesgo medio: revisar pagos")
    (o / "reportes-bug").mkdir(parents=True)
    for i, (sev, est) in enumerate([("Crítica", "Abierto"), ("Alta", "En curso"), ("Media", "Abierto"), ("Alta", "Cerrado")], 1):
        (o / "reportes-bug" / f"BUG-00{i}.md").write_text(f"# BUG\n\n- **ID:** BUG-00{i}\n- **Criticidad / Severidad:** {sev}\n- **Estado:** {est}\n",
                                                        encoding="utf-8")
    return o, k0


def test_suites_con_tendencia_y_bugs_abiertos(tmp_path):
    o, k0 = _proyecto(tmp_path)
    h = portal.descubrir(o, k0)
    suites = {s["suite"]: s for s in portal.suites_npm(h)}
    assert suites["web"]["pct"] == 80 and suites["web"]["fallidos"] == 2 and suites["web"]["serie"] == [100, 90, 80]
    assert suites["api"]["pct"] == 100 and suites["api"]["serie"] == [100]
    assert portal.bugs_abiertos(o) == {"abiertos": 3, "graves": 2, "total": 4}
    assert portal.bugs_abiertos(tmp_path / "vacio") is None


def test_sin_alertas_y_sin_informes(tmp_path, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    o = tmp_path / "output"
    _informe(o, "tablero", "sprint-1", "Apto")
    portal.generar(o, tmp_path / "nada")
    assert "Sin alertas" in ruta_es(o / "index.html").read_text(encoding="utf-8")
    vacio = tmp_path / "vacio" / "output"
    vacio.mkdir(parents=True)
    portal.generar(vacio, tmp_path / "nada")
    assert "Cuando los agentes generen informes" in ruta_es(vacio / "index.html").read_text(encoding="utf-8")


def test_el_portal_no_se_indexa_a_si_mismo(tmp_path, monkeypatch):
    """output/es/ y output/en/ son las versiones del propio portal: en la segunda corrida no aparecen como herramientas."""
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    o, k0 = _proyecto(tmp_path)
    portal.generar(o, k0)
    _, h = portal.generar(o, k0)
    assert "es" not in h and "en" not in h


# ------------------------------------------------------------------ informe genérico con indicadores y gráficos


def test_informe_de_puesta_en_marcha(tmp_path, monkeypatch):
    import generar_informe_entorno as ge
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    doctor = {"resumen": {"ok": 2, "aviso": 1, "falta": 1}, "resultados": [
        {"seccion": "python", "estado": "ok", "texto": "Python 3.12", "ayuda": ""},
        {"seccion": "node", "estado": "falta", "texto": "k0lmena no está instalado", "ayuda": "npm install"},
        {"seccion": "conectores", "estado": "aviso", "texto": "k0lmena-tmt: falta K0LMENA_TMT_TOKEN", "ayuda": "Completala en el .env"},
        {"seccion": "env", "estado": "ok", "texto": ".env completo", "ayuda": ""}]}
    (tmp_path / "doctor.json").write_text(json.dumps(doctor, ensure_ascii=False), encoding="utf-16")  # como lo deja PowerShell
    (tmp_path / "analisis.json").write_text(json.dumps({"primera_tarea": "Casos de PROJ-12", "en": {"primera_tarea": "Test cases for PROJ-12"}}), encoding="utf-8")
    ge.generar(tmp_path / "doctor.json", tmp_path / "informe-entorno.html", tmp_path / "analisis.json")
    es = ruta_es(tmp_path / "informe-entorno.html").read_text(encoding="utf-8")
    en = ruta_en(tmp_path / "informe-entorno.html").read_text(encoding="utf-8")
    assert "Falta resolver 1 punto(s) para empezar" in es and "npm install" in es and "Casos de PROJ-12" in es and "50%" in es
    assert "What's missing to get started" in en and "Test cases for PROJ-12" in en
    assert portal.categoria_de("entorno") == "documentacion"



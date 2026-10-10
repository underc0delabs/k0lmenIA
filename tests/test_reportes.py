"""Los generadores de reportes HTML y el recolector de resultados del informe de cierre."""
import json

import formatear_tablas
import generar_informe_cierre
import generar_informe_seguridad
import generar_plan
import generar_reporte
import recolectar_resultados


def test_reporte_de_ejecucion():
    html = generar_reporte.build_html({
        "titulo": "Registro", "historia": "HU-001",
        "casos": [{"id": "CP-001", "titulo": "OK", "prioridad": "Alta", "estado": "Aprobado", "duracion_s": 2.5},
                  {"id": "CP-002", "titulo": "Falla", "prioridad": "Media", "estado": "Fallido", "falta_info": ["FI-01"]}],
    })
    assert "<!doctype html>" in html and "Registro" in html
    assert "50%" in html and "FI-01" in html and "data-tip" in html


def test_plan_y_cierre():
    assert "Plan" in generar_plan.build_html({"titulo": "Plan", "objetivos": ["a"], "riesgos": [{"nivel": "Alto", "descripcion": "x"}]})
    html = generar_informe_cierre.build_html({"titulo": "Cierre", "recomendacion": "Apto",
                                               "resultados": {"aprobado": 3, "fallido": 1, "bloqueado": 0}})
    assert "75%" in html and "Apto" in html


def test_seguridad():
    zap = {"site": [{"@name": "https://x", "alerts": [
        {"pluginid": "10038", "name": "CSP Header Not Set", "riskcode": "2", "confidence": "3",
         "desc": "<p>d</p>", "solution": "<p>s</p>", "instances": [{"uri": "https://x/", "method": "GET"}], "count": "1"},
        {"pluginid": "10027", "name": "Comentarios", "riskcode": "0", "confidence": "1", "instances": [], "count": "1"}]}]}
    html = generar_informe_seguridad.build_html(zap, {"falsos_positivos": [{"pluginid": "10027", "motivo": "tercero"}]}, "https://x", "HU-001")
    assert "CSP Header Not Set" in html and "Descartados como falsos positivos" in html


def test_formatear_tablas_es_idempotente(tmp_path):
    import subprocess
    import sys
    archivo = tmp_path / "a.md"
    archivo.write_text("# T\n\n| A | B |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
    subprocess.run([sys.executable, formatear_tablas.__file__, str(archivo)], check=True, capture_output=True)
    una_vez = archivo.read_text(encoding="utf-8")
    subprocess.run([sys.executable, formatear_tablas.__file__, str(archivo)], check=True, capture_output=True)
    assert archivo.read_text(encoding="utf-8") == una_vez  # correrlo dos veces no cambia nada
    assert una_vez.count("```") == 2 and "+=====+=====+" in una_vez


def test_recolectar_resultados(tmp_path, monkeypatch):
    raiz = tmp_path
    (raiz / "output" / "ejecuciones").mkdir(parents=True)
    (raiz / "output" / "reportes-bug").mkdir(parents=True)
    k0 = raiz / "herramientas" / "k0lmena" / "reports"
    (k0 / "web").mkdir(parents=True)
    (raiz / "output" / "ejecuciones" / "_resultados-HU-001-a.json").write_text(json.dumps(
        {"historia": "HU-001", "casos": [{"id": "CP-001", "estado": "Fallido"}, {"id": "CP-002", "estado": "Aprobado"}]}), encoding="utf-8")
    (raiz / "output" / "ejecuciones" / "_resultados-HU-002-a.json").write_text(json.dumps(
        {"historia": "HU-002", "casos": [{"id": "CP-001", "estado": "Fallido"}]}), encoding="utf-8")
    # npm test más reciente: CP-001 pasa; un escenario de otra historia no cuenta
    import os, time
    reporte = [{"name": "F", "tags": [{"name": "@HU-001"}], "elements": [
        {"type": "scenario", "name": "uno", "tags": [{"name": "@CP-001"}], "steps": [{"result": {"status": "passed"}}]}]},
        {"name": "G", "tags": [{"name": "@HU-002"}], "elements": [
        {"type": "scenario", "name": "dos", "tags": [{"name": "@CP-009"}], "steps": [{"result": {"status": "failed"}}]}]}]
    (k0 / "web" / "cucumber-report.json").write_text(json.dumps(reporte), encoding="utf-8")
    futuro = time.time() + 60
    os.utime(k0 / "web" / "cucumber-report.json", (futuro, futuro))
    (raiz / "output" / "reportes-bug" / "BUG-001.md").write_text(
        "**ID:** `BUG-001`\n**Título:** x\n**Historia:** HU-001\n**Estado:** Abierto\n**Criticidad / Severidad:** Alta (y)\n", encoding="utf-8")
    monkeypatch.setattr(recolectar_resultados, "RAIZ", raiz)
    monkeypatch.setattr(recolectar_resultados, "K0", k0)
    datos = recolectar_resultados.recolectar("HU-001")
    assert datos["resultados"] == {"aprobado": 2, "fallido": 0, "bloqueado": 0}
    assert datos["bugs"]["por_severidad"]["Alta"] == 1
    assert [b["id"] for b in datos["bugs"]["criticos_abiertos"]] == ["BUG-001"]

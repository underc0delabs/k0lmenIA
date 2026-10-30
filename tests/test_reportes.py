"""Los generadores de reportes HTML y el recolector de resultados del informe de cierre."""
import json

import formatear_tablas
import generar_reporte


def test_reporte_de_ejecucion():
    html = generar_reporte.build_html({
        "titulo": "Registro", "historia": "HU-001",
        "casos": [{"id": "CP-001", "titulo": "OK", "prioridad": "Alta", "estado": "Aprobado", "duracion_s": 2.5},
                  {"id": "CP-002", "titulo": "Falla", "prioridad": "Media", "estado": "Fallido", "falta_info": ["FI-01"]}],
    })
    assert "<!doctype html>" in html and "Registro" in html
    assert "50%" in html and "FI-01" in html and "data-tip" in html


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


def test_newman_sin_validaciones_no_queda_aprobado():
    import newman_a_resultados as nar
    ok = {"assertion": "status 200"}
    datos = nar.convertir({"run": {"executions": [
        {"item": {"name": "API-001 — Con test"}, "assertions": [ok]},
        {"item": {"name": "API-002 — Sin test"}, "assertions": []},
        {"item": {"name": "API-003 — Caído"}, "requestError": {"code": "ECONNREFUSED"}}]}})
    assert [(c["id"], c["estado"]) for c in datos["casos"]] == [("API-001", "Aprobado"), ("API-002", "Bloqueado"), ("API-003", "Bloqueado")]
    assert datos["casos"][1]["motivo"] == "Sin validaciones (pm.test)"


def test_reporte_acepta_falta_informacion_como_texto():
    html = generar_reporte.build_html({"casos": [{"id": "CP-001", "estado": "Aprobado", "falta_info": ["FI-01"]}],
                                       "falta_informacion": ["FI-01", {"id": "FI-02", "que_falta": "Mensaje de error"}]})
    assert "Falta información" in html and "FI-02" in html and "Mensaje de error" in html


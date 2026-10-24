"""Analista de fallos, analista de cobertura y los informes de fallos, cobertura y rendimiento."""
import json
import subprocess
import sys
from pathlib import Path

import analizar_cobertura
import analizar_fallos
import generar_informe_cobertura
import generar_informe_fallos
import generar_informe_rendimiento
import recolectar_resultados

RAIZ = Path(__file__).resolve().parents[1]


def test_clasificar_fallas():
    c = analizar_fallos.clasificar
    assert c("Error: expect(received).toHaveText(expected)\nExpected: 1\nReceived: 2", ["passed", "failed"])[0] == "Posible bug"
    assert c("TimeoutError: locator.click: Timeout 10000ms exceeded.", ["failed"])[0] == "Locator o espera"
    assert c("Error: connect ECONNREFUSED 10.0.0.1:8080", ["failed"])[0] == "Ambiente"
    assert c("Request failed with status code 409 Conflict", ["failed"])[0] == "Datos de prueba"
    assert c("TypeError: Cannot read properties of undefined (reading 'x')", ["failed"])[0] == "Error en la automatización"
    assert c("", ["passed", "undefined"])[0] == "Paso sin definir"
    assert c("algo raro", ["failed"])[0] == "Sin clasificar"


def _escenario(nombre, tags, estado, error=""):
    return {"type": "scenario", "name": nombre, "line": 1, "tags": [{"name": t} for t in tags],
            "steps": [{"keyword": "Then ", "name": "x", "result": {"status": estado, "duration": 1, "error_message": error}}]}


def _reporte(directorio, pasa):
    rep = [{"name": "F", "uri": "f.feature", "tags": [{"name": "@HU-001"}], "elements": [
        _escenario("ok", ["@CP-001"], "passed"),
        _escenario("bug", ["@CP-002"], "failed", "AssertionError: Expected 1 Received 2"),
        _escenario("flaky", ["@CP-003"], "passed" if pasa else "failed", "TimeoutError: Timeout 5000ms exceeded")]}]
    (directorio / "web").mkdir(parents=True, exist_ok=True)
    (directorio / "web" / "cucumber-report.json").write_text(json.dumps(rep), encoding="utf-8")


def test_fallos_detecta_inestables(tmp_path):
    _reporte(tmp_path / "c1", False)
    _reporte(tmp_path / "c2", True)
    salida = tmp_path / "out"
    script = str(RAIZ / "scripts" / "analizar_fallos.py")
    subprocess.run([sys.executable, script, "--reportes", str(tmp_path / "c1"), "--salida", str(salida)], check=True, capture_output=True)
    subprocess.run([sys.executable, script, "--agregar-reintento", "--reportes", str(tmp_path / "c2"), "--salida", str(salida)],
                   check=True, capture_output=True)
    datos = json.loads((salida / "fallos.json").read_text(encoding="utf-8"))
    por_caso = {f["caso"]: f for f in datos["fallos"]}
    assert por_caso["CP-002"]["categoria"] == "Posible bug"
    assert por_caso["CP-003"]["categoria"] == "Inestable (flaky)"
    assert por_caso["CP-003"]["historial"] == ["Fallido", "Aprobado"]
    assert datos["resumen"]["aprobados"] == 1 and datos["suites"] == ["web"]
    html = (salida / "informe-fallos.html").read_text(encoding="utf-8")
    assert "Inestable (flaky)" in html and "F-01" in html
    en = (salida / "informe-fallos.en.html").read_text(encoding="utf-8")  # y su versión en inglés
    assert 'lang="en"' in en and "Flaky" in en and "Failure analysis" in en



def test_fallos_reintento_de_una_suite_no_toca_las_demas(tmp_path):
    """Reintentar solo web (--suites web) no saca a api del análisis ni le suma un "reintento" que no se hizo."""
    _reporte(tmp_path / "c1", False)
    (tmp_path / "c1" / "api").mkdir(parents=True)
    (tmp_path / "c1" / "api" / "cucumber-report.json").write_text(json.dumps([{"name": "A", "uri": "a.feature", "tags": [{"name": "@HU-001"}],
        "elements": [_escenario("api", ["@CP-API-001"], "failed", "AssertionError: Expected 200 Received 500")]}]), encoding="utf-8")
    _reporte(tmp_path / "c2", True)
    (tmp_path / "c2" / "api").mkdir(parents=True)
    (tmp_path / "c2" / "api" / "cucumber-report.json").write_text("[]", encoding="utf-8")  # no se reintentó
    salida = tmp_path / "out"
    script = str(RAIZ / "scripts" / "analizar_fallos.py")
    subprocess.run([sys.executable, script, "--reportes", str(tmp_path / "c1"), "--salida", str(salida)], check=True, capture_output=True)
    subprocess.run([sys.executable, script, "--agregar-reintento", "--suites", "web", "--reportes", str(tmp_path / "c2"),
                    "--salida", str(salida)], check=True, capture_output=True)
    datos = json.loads((salida / "fallos.json").read_text(encoding="utf-8"))
    por_caso = {f["caso"]: f for f in datos["fallos"]}
    assert por_caso["CP-003"]["categoria"] == "Inestable (flaky)"
    assert por_caso["CP-API-001"]["historial"] == ["Fallido", None] and datos["suites"] == ["web", "api"]

def test_cobertura_cruza_fuentes(tmp_path, monkeypatch):
    def escribir(ruta, texto):
        (tmp_path / ruta).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / ruta).write_text(texto, encoding="utf-8")

    escribir("input/historias/HU-001.md", "- CA1: Registro válido\n- CA2: Email inválido\n- CA3: Email duplicado\n")
    escribir("output/casos-de-prueba/bdd/HU-001-registro.feature",
             "@HU-001\nFeature: R\n  @CP-001 @CA1\n  Scenario: a\n    Given x\n  @CP-002 @CA2\n  Scenario: b\n    Given x\n")
    escribir("herramientas/k0lmena/web/features/HU-001.feature",
             "@HU-001\nFeature: R\n  @CP-001\n  Scenario: a\n    Given x\n  @CP-002 @bloqueado\n  Scenario: b\n    Given x\n")
    escribir("herramientas/k0lmena/reports/web/cucumber-report.json", json.dumps([{"name": "R", "uri": "f", "tags": [{"name": "@HU-001"}], "elements": [
        _escenario("a", ["@CP-001"], "failed")]}]))
    monkeypatch.setattr(analizar_cobertura, "RAIZ", tmp_path)
    monkeypatch.setattr(recolectar_resultados, "RAIZ", tmp_path)
    monkeypatch.setattr(recolectar_resultados, "K0", tmp_path / "herramientas" / "k0lmena" / "reports")
    h = analizar_cobertura.analizar_historia("HU-001", {})
    tipos = {x["tipo"] for x in h["huecos"]}
    assert {"Criterio sin casos", "Automatizado bloqueado", "Último resultado fallido"} <= tipos
    assert h["metricas"]["criterios"] == 3 and h["metricas"]["criterios_cubiertos"] == 2
    cp1 = next(x for x in h["casos"] if x["id"] == "CP-001")
    assert cp1["criterios"] == ["CA1"] and cp1["resultado"]["estado"] == "Fallido"
    for i, x in enumerate(h["huecos"]):
        x["id"] = f"C-{i + 1:02d}"
    html = generar_informe_cobertura.build_html({"alcance": "HU-001", "historias": [h]}, {})
    assert "Criterio sin casos" in html and "Matriz de trazabilidad" in html


def test_criterios_y_tabla_de_cobertura():
    texto = "- **CA1** — Login ok\nCA2: Bloqueo\n| CA3 | Expira | CP-004, CP-005 | Cubierto |\n"
    assert analizar_cobertura.criterios_de_texto(texto) == {"CA1": "Login ok", "CA2": "Bloqueo", "CA3": "Expira"}
    assert analizar_cobertura.cobertura_de_tabla(texto) == {"CA3": {"CP-004", "CP-005"}}


def test_informe_rendimiento():
    datos = {"url": "https://x.com/", "host": "x.com", "config": {"dispositivos": ["mobile"], "repeticiones": 1,
             "umbrales": {"lcp": {"nombre": "LCP", "titulo": "Largest Contentful Paint", "bueno": 2500, "malo": 4000, "unidad": "ms"}}},
             "resumen": {"rendimiento_mobile": 62, "vitales_ok_mobile": 0, "oportunidades": 1},
             "resultados": [{"url": "https://x.com/", "dispositivo": "mobile", "puntajes": {"performance": 62, "seo": 100},
                             "metricas": {"lcp": {"valor": 4800, "texto": "4.8 s", "estado": "malo"}}, "peso_total": 1048576, "requests": 40,
                             "recursos": {"JavaScript": {"bytes": 700000, "requests": 12}}, "lcp": {"selector": "img.hero", "etiqueta": "Banner"},
                             "secuencia": [{"ms": 500, "captura": "capturas/01-t00.jpg"}], "lighthouse": "lighthouse/01.html"}],
             "hallazgos": [{"id": "R-01", "categoria": "Core Web Vitals", "severidad": "Alta", "pagina": "https://x.com/", "dispositivo": "mobile",
                            "titulo": "LCP malo: 4.8 s", "detalle": "x"}],
             "oportunidades": [{"id": "unused-javascript", "titulo": "Reduce el JavaScript sin usar", "descripcion": "d", "ahorro_ms_max": 1200,
                                "ahorro_bytes_max": 300000, "paginas": ["https://x.com/"], "dispositivos": ["mobile"], "metricas": ["LCP"],
                                "items": [{"url": "https://x.com/app.js", "ahorro_bytes": 300000}]}]}
    html = generar_informe_rendimiento.build_html(datos, {})
    assert "Core Web Vitals en rojo" in html and "4.8 s · Malo" in html and "Reduce el JavaScript sin usar" in html
    assert "img.hero" in html and "capturas/01-t00.jpg" in html


def test_informe_fallos_con_analisis():
    datos = {"resumen": {"escenarios": 2, "aprobados": 1}, "corridas": [{"id": "c1", "etiqueta": "Corrida original"}], "suites": ["web"],
             "fallos": [{"id": "F-01", "categoria": "Locator o espera", "escenario": "Login", "suite": "web", "historial": ["Fallido"],
                         "estado_final": "Fallido", "error": "TimeoutError", "evidencias": []}]}
    html = generar_informe_fallos.build_html(datos, {"fallos": {"F-01": {"categoria": "Posible bug", "causa": "El botón no aparece", "bug": "BUG-009"}}})
    assert "señales de bug" in html and "BUG-009" in html and "El botón no aparece" in html

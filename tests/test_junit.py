"""Resultados en JUnit XML (Cypress, Playwright, pytest, Maven…) para publicar en la herramienta de gestión."""
import base64
import json

import pytest

import comun
import gestion
import lectores

PLAYWRIGHT = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="" tests="4" failures="1" skipped="1" errors="0" time="12.3">
  <testsuite name="login.spec.ts" tests="4" failures="1" skipped="1">
    <testcase name="@HU-001 CP-001 - Login válido" classname="login.spec.ts" time="2.5"></testcase>
    <testcase name="@HU-001 CP-002 - Login con clave incorrecta" classname="login.spec.ts" time="3.1">
      <failure message="expect(locator).toHaveText(expected)" type="FAILURE">Expected: "Credenciales incorrectas"
Received: "Error"</failure>
      <system-out>
[[ATTACHMENT|test-results/cp-002/test-failed-1.png]]
[[ATTACHMENT|test-results/cp-002/video.webm]]
[[ATTACHMENT|test-results/cp-002/trace.zip]]
[[ATTACHMENT|test-results/cp-002/no-existe.png]]
      </system-out>
    </testcase>
    <testcase name="Login con UTF-8 y SHA-256 [PROJ-45]" classname="login.spec.ts" time="1"></testcase>
    <testcase name="cp_004 bloqueo por intentos" classname="login.spec.ts" time="0">
      <skipped message="pendiente de datos"/>
    </testcase>
  </testsuite>
</testsuites>"""


def _escribir_playwright(tmp_path):
    xml = tmp_path / "results.xml"
    xml.write_text(PLAYWRIGHT, encoding="utf-8")
    carpeta = tmp_path / "test-results" / "cp-002"
    carpeta.mkdir(parents=True)
    for nombre in ("test-failed-1.png", "video.webm", "trace.zip"):
        (carpeta / nombre).write_bytes(b"x")
    return xml


def test_playwright_estados_ids_y_evidencias(tmp_path):
    resultados = {r["escenario"]: r for r in lectores.leer_resultados_junit(_escribir_playwright(tmp_path), tmp_path / "ev")}
    ok = resultados["@HU-001 CP-001 - Login válido"]
    assert ok["estado"] == "aprobado" and ok["tags"] == ["HU-001", "CP-001"] and ok["duracion_s"] == 2.5
    assert ok["feature"] == "login.spec.ts" and ok["origen"] == "JUnit"
    falla = resultados["@HU-001 CP-002 - Login con clave incorrecta"]
    assert falla["estado"] == "fallido" and 'Received: "Error"' in falla["error"]
    assert [e["tipo"] for e in falla["evidencias"]] == ["captura", "video", "archivo"]  # la que no existe se omite
    # "UTF-8" y "SHA-256" en el nombre no son keys; [PROJ-45] sí.
    assert resultados["Login con UTF-8 y SHA-256 [PROJ-45]"]["tags"] == ["PROJ-45"]
    pendiente = resultados["cp_004 bloqueo por intentos"]
    assert pendiente["estado"] == "pendiente" and pendiente["tags"] == ["CP-004"] and pendiente["duracion_s"] is None


def test_pytest_surefire_reintentos_y_evidencia_de_xray(tmp_path):
    """Una carpeta con varios XML (Surefire), properties con la key (Xray) y un test repetido: vale el último."""
    png = base64.b64encode(b"PNG").decode()
    (tmp_path / "TEST-LoginTest.xml").write_text(f"""<testsuite name="LoginTest">
  <testcase classname="tests.test_login" name="test_cp_api_003_token_vencido" time="0.4">
    <error message="AssertionError">assert 401 == 200</error>
  </testcase>
  <testcase classname="tests.test_login" name="test_cp_api_003_token_vencido" time="0.3"/>
  <testcase classname="LoginTest" name="pago con tarjeta" time="1.2">
    <properties>
      <property name="test_key" value="PROJ-77"/>
      <property name="testrun_evidence"><item name="pantalla.png">{png}</item></property>
    </properties>
  </testcase>
</testsuite>""", encoding="utf-8")
    (tmp_path / "TEST-Otro.xml").write_text('<testsuites><testsuite name="Otro"><testcase classname="Otro" '
                                            'name="CP-010 alta"/></testsuite></testsuites>', encoding="utf-8")
    resultados = {r["escenario"]: r for r in lectores.leer_resultados_junit(tmp_path, tmp_path / "ev")}
    assert len(resultados) == 3
    reintento = resultados["test_cp_api_003_token_vencido"]
    assert reintento["estado"] == "aprobado" and reintento["tags"] == ["CP-API-003"]
    pago = resultados["pago con tarjeta"]
    assert pago["tags"] == ["PROJ-77"] and pago["evidencias"][0]["tipo"] == "captura"
    assert open(pago["evidencias"][0]["archivo"], "rb").read() == b"PNG"
    assert resultados["CP-010 alta"]["tags"] == ["CP-010"]


def test_xml_que_no_es_junit(tmp_path):
    otro = tmp_path / "pom.xml"
    otro.write_text("<project/>", encoding="utf-8")
    with pytest.raises(comun.ErrorGestion, match="no parece un reporte JUnit"):
        lectores.leer_resultados_junit(otro, tmp_path / "ev")


def test_extraer_resultados_acepta_junit(tmp_path):
    xml = _escribir_playwright(tmp_path)
    args = type("A", (), {"reporte": str(xml), "salida": str(tmp_path / "resultados.json")})()
    salida = gestion.cmd_extraer_resultados(args, None)
    assert salida["escenarios"] == 4 and salida["por_estado"] == {"aprobado": 2, "fallido": 1, "pendiente": 1}
    guardado = json.loads((tmp_path / "resultados.json").read_text(encoding="utf-8"))
    assert {r["origen"] for r in guardado} == {"JUnit"}

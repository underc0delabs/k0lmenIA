"""Adaptador de Zephyr Scale (API v2) contra un servidor falso: carpetas idempotentes, casos manuales y BDD,
vínculos por id de issue, ciclos, ejecuciones y adjuntos."""
import http.server
import json
import threading

import pytest

import comun
import gestion
from adaptadores.zephyr_scale import ZephyrScale


@pytest.fixture
def zephyr(monkeypatch):
    pedidos = []

    class Servidor(http.server.BaseHTTPRequestHandler):
        def _responder(self, codigo, datos):
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(datos).encode())

        def _registrar(self):
            largo = int(self.headers.get("Content-Length", 0))
            cuerpo = self.rfile.read(largo) if largo else b""
            pedidos.append({"metodo": self.command, "ruta": self.path, "cuerpo": cuerpo,
                            "auth": self.headers.get("Authorization"), "tipo": self.headers.get("Content-Type")})
            return cuerpo

        def do_GET(self):  # noqa: N802
            self._registrar()
            if self.path.startswith("/jira/rest/api/3/issue/PROJ-12"):
                return self._responder(200, {"id": "10012", "key": "PROJ-12"})
            if self.path.startswith("/v2/folders"):
                return self._responder(200, {"isLast": True, "values": [
                    {"id": 7, "name": "HU-001 Registro", "parentId": None, "folderType": "TEST_CASE"}]})
            self._responder(404, {})

        def do_POST(self):  # noqa: N802
            self._registrar()
            if self.path == "/v2/folders":
                return self._responder(201, {"id": 8})
            if self.path == "/v2/testcases":
                return self._responder(201, {"id": 1, "key": "PROJ-T1"})
            if self.path == "/v2/testcycles":
                return self._responder(201, {"id": 5, "key": "PROJ-R5"})
            if self.path == "/v2/testexecutions":
                return self._responder(201, {"id": 99})
            self._responder(201, {"id": 1})

        def do_PUT(self):  # noqa: N802
            self._registrar()
            self._responder(201, {"id": 3})

        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Servidor)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    monkeypatch.setenv("ZEPHYR_API_URL", base + "/v2")
    monkeypatch.setenv("ZEPHYR_API_TOKEN", "token-de-prueba")
    monkeypatch.setenv("JIRA_BASE_URL", base + "/jira")
    monkeypatch.setenv("JIRA_EMAIL", "qa@test.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "x")
    yield ZephyrScale("PROJ"), pedidos
    srv.shutdown()


def _json(p):
    return json.loads(p["cuerpo"])


CASO_MANUAL = {"id": "CP-001", "titulo": "Registro válido", "descripcion": "Alta de cuenta", "precondiciones": "",
               "prioridad": "Crítica", "etiquetas": ["HU-001"], "tipo": "manual",
               "pasos": [{"accion": "Completar el formulario", "datos": "ana@test.com", "resultado": "Se crea"}],
               "estimacion": {"segundos": 90, "texto": "1 min 30 s"}}


def test_carpeta_reutiliza_la_existente_y_crea_la_que_falta(zephyr):
    ad, pedidos = zephyr
    assert ad.crear_carpeta("/HU-001 Registro/Manuales") == 8
    creadas = [_json(p) for p in pedidos if p["metodo"] == "POST" and p["ruta"] == "/v2/folders"]
    assert creadas == [{"name": "Manuales", "projectKey": "PROJ", "folderType": "TEST_CASE", "parentId": 7}]
    assert all(p["auth"] == "Bearer token-de-prueba" for p in pedidos)


def test_caso_manual_con_pasos_prioridad_y_tiempo(zephyr):
    ad, pedidos = zephyr
    assert ad.crear_caso(CASO_MANUAL, 7, "/HU-001 Registro") == {"key": "PROJ-T1", "id": 1}
    caso = _json(next(p for p in pedidos if p["ruta"] == "/v2/testcases"))
    assert caso["name"] == "CP-001 - Registro válido" and caso["folderId"] == 7
    assert caso["priorityName"] == "High" and caso["estimatedTime"] == 90000
    assert "k0lmenIA" in caso["labels"]
    pasos = _json(next(p for p in pedidos if p["ruta"] == "/v2/testcases/PROJ-T1/teststeps"))
    assert pasos["mode"] == "OVERWRITE"
    assert pasos["items"][0]["inline"] == {"description": "Completar el formulario", "testData": "ana@test.com",
                                           "expectedResult": "Se crea"}


def test_caso_bdd_va_como_test_script(zephyr):
    ad, pedidos = zephyr
    bdd = {**CASO_MANUAL, "tipo": "cucumber", "pasos": [], "gherkin": "Scenario: Registro\n  Given estoy en el alta"}
    ad.crear_caso(bdd, 7, "/HU-001 Registro")
    script = _json(next(p for p in pedidos if p["ruta"] == "/v2/testcases/PROJ-T1/testscript"))
    assert script == {"type": "bdd", "text": bdd["gherkin"]}


def test_vinculos_usan_el_id_numerico_del_issue(zephyr):
    ad, pedidos = zephyr
    ad.vincular_caso_historia({"key": "PROJ-T1"}, "PROJ-12")
    ad.vincular_ciclo_historia({"key": "PROJ-R5"}, "PROJ-12")
    vinculos = [(p["ruta"], _json(p)) for p in pedidos if p["ruta"].endswith("/links/issues")]
    assert vinculos == [("/v2/testcases/PROJ-T1/links/issues", {"issueId": 10012}),
                        ("/v2/testcycles/PROJ-R5/links/issues", {"issueId": 10012})]
    assert sum(p["ruta"].startswith("/jira/") for p in pedidos) == 1  # el id se resuelve una sola vez


def test_agregar_al_ciclo_crea_ejecuciones_sin_correr(zephyr):
    ad, pedidos = zephyr
    ad.agregar_casos_ciclo({"key": "PROJ-R5"}, [{"key": "PROJ-T1"}, {"key": "PROJ-T2"}])
    ejecuciones = [_json(p) for p in pedidos if p["ruta"] == "/v2/testexecutions"]
    assert [e["testCaseKey"] for e in ejecuciones] == ["PROJ-T1", "PROJ-T2"]
    assert all(e["statusName"] == "Not Executed" and e["testCycleKey"] == "PROJ-R5" for e in ejecuciones)


def test_resultado_con_adjunto_crudo(zephyr, tmp_path):
    ad, pedidos = zephyr
    captura = tmp_path / "paso 1.png"
    captura.write_bytes(b"PNG-FALSO")
    assert ad.registrar_resultado({"key": "PROJ-R5"}, {"key": "PROJ-T1"}, "fallido", "Falló\nel paso 2",
                                  [str(captura)]) == []
    ejecucion = _json(next(p for p in pedidos if p["ruta"] == "/v2/testexecutions"))
    assert ejecucion["statusName"] == "Fail" and ejecucion["automated"] is True
    assert ejecucion["comment"] == "Falló<br>el paso 2"
    adjunto = next(p for p in pedidos if p["metodo"] == "PUT")
    assert adjunto["ruta"] == "/v2/testexecutions/99/attachments/paso%201.png"
    assert adjunto["cuerpo"] == b"PNG-FALSO" and adjunto["tipo"] == "image/png"


def test_estados_personalizados(monkeypatch):
    monkeypatch.setenv("ZEPHYR_ESTADOS", '{"bloqueado": "Impedido"}')
    ad = ZephyrScale("PROJ", dry_run=True)
    assert ad.estados["bloqueado"] == "Impedido" and ad.estados["aprobado"] == "Pass"


def test_gestion_acepta_las_keys_de_zephyr(monkeypatch):
    monkeypatch.setenv("GESTION_PROYECTO", "PROJ")
    args = type("A", (), {"historia": "PROJ-12", "ciclo": "PROJ-R5", "casos": "PROJ-T1,PROJ-T22"})()
    gestion.validar_keys(args)
    with pytest.raises(comun.ErrorGestion):
        gestion.validar_keys(type("A", (), {"historia": "PROJ-T12", "ciclo": None, "casos": None})())
    assert isinstance(gestion.crear_adaptador("zephyr-scale", dry_run=True), ZephyrScale)

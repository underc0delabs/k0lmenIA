"""Adaptador de k0lmenaTMT (scripts/gestion/adaptadores/k0lmena_tmt.py) contra un server MCP falso que se comporta
como el de k0lmenaTMT: cada escritura devuelve una propuesta (change-set) y apply_change_set la aplica y devuelve el id."""
import base64
import http.server
import json
import threading

import pytest

import comun
import gestion
from adaptadores import k0lmena_tmt as tmt


class _ServidorTMT(http.server.BaseHTTPRequestHandler):
    llamadas, propuestas, siguiente, sse = [], {}, [100], [False]

    def do_POST(self):  # noqa: N802
        cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        nombre, args = cuerpo["params"]["name"], cuerpo["params"]["arguments"]
        self.llamadas.append({"tool": nombre, "args": args, "auth": self.headers.get("Authorization")})
        if nombre == "apply_change_set":
            self.siguiente[0] += 1
            datos = {"status": "applied", "results": [{"ref": "a1", "targetId": self.siguiente[0]}]}
        else:
            cs = len(self.propuestas) + 1
            self.propuestas[cs] = nombre
            datos = {"proposed": True, "changeSetId": cs, "ref": "a1", "type": nombre}
        mensaje = {"jsonrpc": "2.0", "id": cuerpo["id"], "result": {"content": [{"type": "text", "text": json.dumps(datos)}]}}
        if self.sse[0]:  # el transporte Streamable HTTP puede responder como stream SSE
            salida, tipo = f"event: message\ndata: {json.dumps(mensaje)}\n\n".encode(), "text/event-stream"
        else:
            salida, tipo = json.dumps(mensaje).encode(), "application/json"
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.end_headers()
        self.wfile.write(salida)

    def log_message(self, *args):
        pass


@pytest.fixture
def adaptador(tmp_path, monkeypatch):
    _ServidorTMT.llamadas.clear()
    _ServidorTMT.propuestas.clear()
    _ServidorTMT.siguiente[0] = 100
    _ServidorTMT.sse[0] = False
    srv = http.server.HTTPServer(("127.0.0.1", 0), _ServidorTMT)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("K0LMENA_TMT_URL", f"http://127.0.0.1:{srv.server_port}/api/v1/mcp")
    monkeypatch.setenv("K0LMENA_TMT_TOKEN", "kolm_pat_prueba")
    monkeypatch.setenv("K0LMENA_TMT_RPM", "60000")  # sin pausas en los tests
    monkeypatch.setenv("K0LMENA_TMT_PRIORIDADES", '{"Alta": 2, "Crítica": 1}')
    monkeypatch.setattr(tmt, "DIR_GESTION", tmp_path)
    yield tmt.K0lmenaTMT("3"), _ServidorTMT.llamadas
    srv.shutdown()


CASO = {"id": "CP-001", "titulo": "Registro válido", "descripcion": "Alta de cuenta", "precondiciones": "Sin sesión",
        "prioridad": "Alta", "etiquetas": ["HU-001", "registro"], "tipo": "manual",
        "pasos": [{"accion": "Completar el formulario", "datos": "ana@test.com", "resultado": "Se crea la cuenta"}],
        "estimacion": {"segundos": 150, "texto": "2 min 30 s"}}


def _herramientas(llamadas):
    return [x["tool"] for x in llamadas]


def test_cada_escritura_se_propone_y_se_aplica(adaptador):
    ad, llamadas = adaptador
    assert ad.crear_carpeta("/HU-001 Registro/Manuales") == 102
    assert _herramientas(llamadas) == ["create_directory", "apply_change_set", "create_directory", "apply_change_set"]
    assert llamadas[2]["args"] == {"projectId": 3, "name": "Manuales", "parentDirectoryId": 101}
    assert all(x["auth"] == "Bearer kolm_pat_prueba" for x in llamadas)
    # La segunda vez no se duplica: el MCP no lista carpetas, los ids se recuerdan.
    assert tmt.K0lmenaTMT("3").crear_carpeta("/HU-001 Registro/Manuales") == 102
    assert len(llamadas) == 4


def test_caso_manual_y_bdd(adaptador):
    ad, llamadas = adaptador
    ad.historia = "PROJ-12"
    assert ad.crear_caso(CASO, 55, "/HU-001") == {"key": "TC-101", "id": 101}
    caso = llamadas[0]["args"]
    assert caso["title"] == "CP-001 - Registro válido" and caso["directoryId"] == 55 and caso["priorityId"] == 2
    assert caso["tags"] == ["HU-001", "registro", "PROJ-12", "k0lmenIA"] and caso["estimatedDuration"] == 2
    assert caso["steps"] == [{"name": "Completar el formulario", "data": "ana@test.com", "expectedResult": "Se crea la cuenta"}]
    bdd = {**CASO, "tipo": "cucumber", "pasos": [],
           "gherkin": "Scenario: Registro\n  Given estoy en el alta\n  When completo el formulario\n  Then se crea la cuenta"}
    ad.crear_caso(bdd, 55, "/HU-001")
    caso = llamadas[2]["args"]
    assert caso["automated"] is True and [s["name"] for s in caso["steps"]] == [
        "Given estoy en el alta", "When completo el formulario", "Then se crea la cuenta"]


def test_ciclo_resultados_y_evidencias(adaptador, tmp_path):
    ad, llamadas = adaptador
    ad.historia = "PROJ-12"
    ciclo = ad.crear_ciclo("Sprint 5", "Regresión")
    assert ciclo["key"] == "CY-101" and "PROJ-12" in llamadas[0]["args"]["description"]
    ad.agregar_casos_ciclo(ciclo, [{"key": "TC-7"}, {"key": "TC-8"}])
    suites = [x["args"] for x in llamadas if x["tool"] == "add_case_to_cycle"]
    assert suites == [{"projectId": 3, "testCycleId": 101, "testCaseId": 7}, {"projectId": 3, "testCycleId": 101, "testCaseId": 8}]
    captura = tmp_path / "paso 2.png"
    captura.write_bytes(b"PNG")
    grande = tmp_path / "video.webm"
    grande.write_bytes(b"0" * (tmt.MAX_ARCHIVO + 1))
    llamadas.clear()
    no_subidas = ad.registrar_resultado(ciclo, {"key": "TC-7"}, "fallido", "Ejecutado con k0lmena.\n\nError: timeout",
                                        [str(captura), str(grande)])
    assert [n for n, _ in no_subidas] == [str(grande)]  # supera 10 MB: se avisa, no se sube
    registro = next(x["args"] for x in llamadas if x["tool"] == "record_execution")
    assert registro == {"projectId": 3, "cycleSuiteId": 102, "status": "failed", "pass": 0, "fail": 1, "blocked": 0}
    adjunto = next(x["args"] for x in llamadas if x["tool"] == "attach_evidence")
    assert [f["fileName"] for f in adjunto["files"]] == ["resultado.txt", "paso 2.png"]
    assert base64.b64decode(adjunto["files"][0]["contentBase64"]).decode() == "Ejecutado con k0lmena.\n\nError: timeout"
    # Un caso que no estaba en el ciclo se agrega solo antes de registrar el resultado.
    llamadas.clear()
    ad.registrar_resultado(ciclo, {"key": "TC-9"}, "aprobado", "ok", [])
    assert _herramientas(llamadas)[:4] == ["add_case_to_cycle", "apply_change_set", "record_execution", "apply_change_set"]


def test_respuesta_sse_y_errores(adaptador):
    ad, llamadas = adaptador
    _ServidorTMT.sse[0] = True
    assert ad.crear_ciclo("Ciclo SSE")["key"] == "CY-101"
    with pytest.raises(comun.ErrorGestion, match="TC-<id>"):
        ad._id_de("PROJ-7", "TC")
    with pytest.raises(comun.ErrorGestion, match="id numérico"):
        tmt.K0lmenaTMT("PROJ")


def test_tandas_respetan_los_limites_de_k0lmenatmt():
    archivos = [(f"a{i}.png", "image/png", b"x" * (2 * 1024 * 1024)) for i in range(12)]
    tandas = list(tmt._tandas(archivos))
    assert all(len(t) <= tmt.MAX_ARCHIVOS for t in tandas)
    assert all(sum(len(b) for _, _, b in t) <= tmt.MAX_POR_LLAMADA for t in tandas)
    assert sum(len(t) for t in tandas) == 12


def test_gestion_acepta_k0lmena_tmt(monkeypatch):
    monkeypatch.setenv("GESTION_PROYECTO", "3")
    assert isinstance(gestion.crear_adaptador("k0lmena-tmt", dry_run=True), tmt.K0lmenaTMT)
    gestion.validar_keys(type("A", (), {"historia": "PROJ-12", "ciclo": "CY-45", "casos": "TC-7,TC-8"})())

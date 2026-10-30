"""Adaptador de k0lmenaTMT (scripts/gestion/adaptadores/k0lmena_tmt.py) contra un server MCP falso que se comporta
como el de k0lmenaTMT: cada escritura devuelve una propuesta (change-set) y apply_change_set la aplica y devuelve el id."""
import base64
import http.server
import json
import threading

from pathlib import Path
from types import SimpleNamespace

import pytest

import comun
import gestion
from adaptadores import k0lmena_tmt as tmt


# Los esquemas reales de las herramientas del server MCP de k0lmenaTMT (tools/list): el server falso rechaza lo que el
# real rechazaría (parámetros desconocidos u obligatorios que faltan, valores fuera del enum, más de maxItems).
ESQUEMAS = json.loads((Path(__file__).parent / "fixtures" / "k0lmena_tmt_herramientas.json").read_text(encoding="utf-8"))["herramientas"]


# Campos que el real acepta aunque su esquema no los declare: update_test_case pasa los cambios tal cual (así se carga
# la pestaña Gherkin, que create_test_case descarta).
NO_DECLARADOS = {"update_test_case": {"gherkin", "estimatedDuration"}}


def _validar(nombre, args):
    esquema = ESQUEMAS.get(nombre)
    if esquema is None:
        return f"herramienta desconocida: {nombre}"
    props = esquema.get("properties", {})
    for clave, valor in args.items():
        if clave in NO_DECLARADOS.get(nombre, ()):
            continue
        if clave not in props:
            return f"{nombre}: parámetro desconocido {clave!r}"
        p = props[clave]
        if "enum" in p and valor not in p["enum"]:
            return f"{nombre}: {clave}={valor!r} no está en {p['enum']}"
        if p.get("type") == "array" and len(valor) > p.get("maxItems", 10 ** 6):
            return f"{nombre}: {clave} supera maxItems"
        if p.get("type") == "array" and isinstance(p.get("items"), dict):
            for item in valor:
                faltan = [r for r in p["items"].get("required", []) if r not in item]
                if faltan:
                    return f"{nombre}: a un ítem de {clave} le faltan {faltan}"
    faltan = [r for r in esquema.get("required", []) if r not in args]
    return f"{nombre}: faltan {faltan}" if faltan else None


class _ServidorTMT(http.server.BaseHTTPRequestHandler):
    llamadas, propuestas, siguiente, sse = [], {}, [100], [False]
    con_ejecuciones = set()  # casos en un ciclo con ejecuciones: k0lmenaTMT no deja borrar sus pasos

    def do_POST(self):  # noqa: N802
        cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        nombre, args = cuerpo["params"]["name"], cuerpo["params"]["arguments"]
        self.llamadas.append({"tool": nombre, "args": args, "auth": self.headers.get("Authorization")})
        invalido = _validar(nombre, args)
        if invalido:
            mensaje = {"jsonrpc": "2.0", "id": cuerpo["id"], "result": {"isError": True, "content": [{"type": "text", "text": invalido}]}}
            salida = json.dumps(mensaje).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(salida)
            return
        if nombre == "apply_change_set":
            propuesto, argumentos = self.propuestas.get(args["id"], ("", {}))
            if propuesto == "update_test_case" and "steps" in argumentos and argumentos["id"] in self.con_ejecuciones:
                datos = {"status": "error", "results": [{"ref": "a1", "ok": False, "error": (
                    'update or delete on table "Steps" violates foreign key constraint '
                    '"CycleSuiteSteps_originalStepId_fkey" on table "CycleSuiteSteps"')}]}
            else:
                self.siguiente[0] += 1
                datos = {"status": "applied", "results": [{"ref": "a1", "targetId": self.siguiente[0]}]}
        else:
            cs = len(self.propuestas) + 1
            self.propuestas[cs] = (nombre, args)
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
    _ServidorTMT.con_ejecuciones.clear()
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
    assert ad.crear_caso(bdd, 55, "/HU-001")["key"] == "TC-102"
    caso = llamadas[2]["args"]
    assert caso["automated"] is True and caso["steps"] == []  # el escenario va a la pestaña Gherkin, no a Pasos
    assert _herramientas(llamadas[2:]) == ["create_test_case", "apply_change_set", "update_test_case", "apply_change_set"]
    assert llamadas[4]["args"] == {"projectId": 3, "id": 102, "gherkin": {"scenarios": [{
        "title": "Registro", "given": ["estoy en el alta"], "when": ["completo el formulario"], "then": ["se crea la cuenta"],
        "and": [], "tags": ["CP-001", "HU-001", "registro"]}]}}


def test_gherkin_de_k0lmenatmt():
    """Background, And/But, Scenario Outline con varios Examples, tablas y textos de un paso: lo que la pestaña Gherkin
    no guarda (Examples, tablas, textos) queda en Pasos, con el contenido en los datos."""
    gherkin = '''Background:
  Given estoy en el alta
  And acepto cookies

Scenario Outline: Largo del usuario
  When completo el usuario con "<u>"
  And cargo los datos:
    | campo | valor |
    | email | a@b.c |
  But no envío
  Then veo:
    """
    El usuario <r>
    """
  Examples: válidos
    | u    | r  |
    | abcd | ok |
  @negativo
  Examples: inválidos
    | u   | r     |
    | abc | error |'''
    caso = {"id": "CP-002", "titulo": "Largo", "etiquetas": ["borde"], "feature": "Registro", "gherkin": gherkin}
    estructura, pasos = tmt._gherkin_tmt(caso)
    assert estructura == {"feature": "Registro", "scenarios": [{
        "title": "Largo del usuario", "given": ["estoy en el alta", "acepto cookies"],
        "when": ['completo el usuario con "<u>"', "cargo los datos:", "no envío"], "then": ["veo:"],
        "and": [], "tags": ["CP-002", "borde"]}]}
    assert [p["name"] for p in pasos] == ["And cargo los datos:", "Then veo:", "Examples (Scenario Outline)"]
    assert pasos[0]["data"].splitlines() == ["| campo | valor |", "| email | a@b.c |"]
    assert pasos[1]["data"] == "    El usuario <r>"
    assert pasos[2]["data"].splitlines() == ["| u    | r  |", "| abcd | ok |", "", "| u   | r     |", "| abc | error |"]


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
    assert [f["fileName"] for f in adjunto["attachments"]] == ["resultado.txt", "paso 2.png"]
    assert base64.b64decode(adjunto["attachments"][0]["contentBase64"]).decode() == "Ejecutado con k0lmena.\n\nError: timeout"
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


def test_el_server_falso_valida_como_el_real():
    """Con el nombre de parámetro equivocado (como "files" en vez de "attachments"), el server falso falla igual que el real."""
    assert "parámetro desconocido 'files'" in _validar("attach_evidence", {"projectId": 2, "files": []})
    assert _validar("record_execution", {"projectId": 2, "cycleSuiteId": 1, "status": "blocked"}).startswith("record_execution: status")
    assert _validar("create_test_case", {"projectId": 2, "title": "x", "steps": [{"name": "a"}]}) is None


def test_ciclo_de_otro_proyecto_no_se_toca(adaptador, monkeypatch):
    """k0lmenaTMT acepta casos en un ciclo de otro proyecto: el adaptador solo escribe en ciclos que creó k0lmenIA en
    este proyecto o que la persona confirmó con K0LMENA_TMT_CICLOS."""
    ad, llamadas = adaptador
    with pytest.raises(comun.ErrorGestion, match="K0LMENA_TMT_CICLOS=CY-1"):
        ad.agregar_casos_ciclo({"key": "CY-1"}, [{"key": "TC-7"}])
    assert llamadas == []  # no se escribió nada
    monkeypatch.setenv("K0LMENA_TMT_CICLOS", "CY-1")
    ad.agregar_casos_ciclo({"key": "CY-1"}, [{"key": "TC-7"}])
    assert _herramientas(llamadas) == ["add_case_to_cycle", "apply_change_set"]


def test_duracion_real_y_ciclo_ejecutado(adaptador):
    """La duración de cada escenario (de Cucumber) llega como executionTimeMs, y al publicar el ciclo queda ejecutado."""
    ad, llamadas = adaptador
    ciclo = ad.crear_ciclo("Sprint 2")
    llamadas.clear()
    ad.registrar_resultado(ciclo, {"key": "TC-7"}, "aprobado", "ok", [], duracion_s=3.5)
    assert next(x["args"] for x in llamadas if x["tool"] == "record_execution")["executionTimeMs"] == 3500
    assert ad.al_publicar(ciclo, [{"estado": "aprobado"}, {"estado": "fallido"}]) == "completed"
    assert ad.al_publicar(ciclo, [{"estado": "pendiente"}]) == "running"
    lanzar = [x["args"] for x in llamadas if x["tool"] == "launch_cycle"]
    assert lanzar[-1] == {"projectId": 3, "id": 101, "status": "running"}


def test_subir_casos_con_etiquetas_estandar_y_actualizarlas(adaptador, tmp_path, monkeypatch):
    """Al subir, cada caso lleva historia, módulo, prioridad y smoke/regresion. Si ya estaba subido y sus etiquetas
    cambiaron, se actualizan (sin tocar los pasos: un caso en un ciclo con ejecuciones no deja borrarlos)."""
    ad, llamadas = adaptador
    monkeypatch.setattr(comun, "DIR_GESTION", tmp_path)
    feature = tmp_path / "HU-901-registro.feature"
    feature.write_text("@HU-901\nFeature: Registro de cuenta\n\n  @CP-001 @critica @positivo\n  Scenario: Alta\n"
                       "    Given estoy en el alta\n    Then se crea la cuenta\n", encoding="utf-8")
    args = type("A", (), {"origen": str(feature), "carpeta": "/HU-901", "historia": None, "ids": None,
                          "traza": "HU-901", "modulo": None})()
    gestion.cmd_subir_casos(args, ad)
    caso = next(x["args"] for x in llamadas if x["tool"] == "create_test_case")
    assert caso["tags"] == ["HU-901", "modulo-registro-de-cuenta", "critica", "smoke", "regresion", "positivo", "k0lmenIA"]
    gherkin = next(x["args"]["gherkin"] for x in llamadas if x["tool"] == "update_test_case")
    assert gherkin["scenarios"][0]["tags"] == ["CP-001", "HU-901", "modulo-registro-de-cuenta", "critica", "smoke",
                                               "regresion", "positivo"]
    # Otra vez, igual: no se escribe nada. Con otro módulo: se actualizan las etiquetas, no los pasos.
    llamadas.clear()
    assert gestion.cmd_subir_casos(args, ad)["ya_existian"] and llamadas == []
    args.modulo = "Registro"
    salida = gestion.cmd_subir_casos(args, ad)
    assert salida["etiquetas_actualizadas"][0]["etiquetas"][1] == "modulo-registro"
    cambio = next(x["args"] for x in llamadas if x["tool"] == "update_test_case")
    assert cambio["tags"][1] == "modulo-registro" and "steps" not in cambio and "gherkin" in cambio


def test_sincronizar_casos_cambiados(adaptador, tmp_path, monkeypatch):
    """Se sube, se cambia el origen y se sincroniza: solo se actualiza lo que cambió. subir-casos avisa qué cambió.
    Si el caso tiene ejecuciones, k0lmenaTMT no deja borrar sus pasos: se actualiza el resto y se avisa."""
    ad, llamadas = adaptador
    monkeypatch.setattr(comun, "DIR_GESTION", tmp_path)
    feature = tmp_path / "HU-901.feature"

    def escribir(*finales):
        escenarios = [f"""
  @CP-00{n} @alta
  Scenario: Caso {n}
    Given estoy en el alta
    Then {fin}
""" for n, fin in enumerate(finales, 1)]
        feature.write_text("@HU-901\nFeature: Registro\n" + "".join(escenarios), encoding="utf-8")

    def argumentos(**cambios):
        return SimpleNamespace(**{"origen": str(feature), "carpeta": "/HU-901", "historia": None, "ids": None,
                                  "traza": "HU-901", "modulo": None, "forzar": False, **cambios})

    escribir("se crea", "se crea")
    args = argumentos()
    gestion.cmd_subir_casos(args, ad)
    llamadas.clear()
    assert gestion.cmd_sincronizar_casos(args, ad) == {
        "actualizados": [], "sin_cambios": ["CP-001", "CP-002"], "trazabilidad": str(tmp_path / "HU-901-k0lmena-tmt.json")}
    assert llamadas == []
    # Cambia el Then de CP-002 y aparece un CP-003 que no se subió.
    escribir("se crea", "se crea la cuenta", "x")
    assert gestion.cmd_subir_casos(argumentos(ids="CP-001,CP-002"), ad)["cambiaron_en_el_origen"] == ["CP-002"]
    llamadas.clear()
    salida = gestion.cmd_sincronizar_casos(args, ad)
    assert [a["caso"] for a in salida["actualizados"]] == ["CP-002"] and salida["no_subidos"] == ["CP-003"]
    cambio = next(x["args"] for x in llamadas if x["tool"] == "update_test_case")
    assert cambio["gherkin"]["scenarios"][0]["then"] == ["se crea la cuenta"] and cambio["title"].startswith("CP-002")
    assert gestion.cmd_sincronizar_casos(args, ad)["sin_cambios"] == ["CP-001", "CP-002"]  # ya quedó al día
    # Con ejecuciones: los pasos no se pueden borrar (manual con pasos).
    caso = {"id": "CP-009", "titulo": "Manual", "tipo": "manual", "etiquetas": [], "prioridad": "Alta",
            "pasos": [{"accion": "Entrar", "datos": "", "resultado": "Entra"}]}
    _ServidorTMT.con_ejecuciones.add(7)
    llamadas.clear()
    avisos = ad.actualizar_caso(caso, {"key": "TC-7"}, {})
    assert "ya tiene ejecuciones" in avisos[0]
    intentos = [x["args"] for x in llamadas if x["tool"] == "update_test_case"]
    assert "steps" in intentos[0] and "steps" not in intentos[1] and intentos[1]["title"] == "CP-009 - Manual"


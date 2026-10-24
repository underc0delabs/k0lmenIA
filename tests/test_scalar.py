"""Scalar (probador-scalar): colección de casos, OpenAPI enriquecido con x-post-response y guardas de publicación."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "herramientas" / "scalar"))

import scalar  # noqa: E402

DOC = {
    "openapi": "3.1.0", "info": {"title": "Galaxia", "version": "1.0.0"}, "servers": [{"url": "https://api.galaxia.test"}],
    "paths": {
        "/planets": {
            "get": {"operationId": "listPlanets", "parameters": [{"$ref": "#/components/parameters/limit"}],
                    "responses": {"200": {"description": "ok", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Lista"}}}}}},
            "post": {"operationId": "createPlanet",
                     "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Planeta"}}}},
                     "responses": {"201": {"description": "creado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Planeta"}}}},
                                   "400": {"description": "inválido"}}},
        },
        "/planets/{planetId}": {
            "parameters": [{"$ref": "#/components/parameters/planetId"}],
            "get": {"x-post-response": "pm.test('mío', () => {})",
                    "responses": {"200": {"description": "ok", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Planeta"}}}},
                                  "404": {"description": "no existe"}}},
        },
    },
    "components": {
        "parameters": {"limit": {"name": "limit", "in": "query", "schema": {"type": "integer", "format": "int64"}},
                       "planetId": {"name": "planetId", "in": "path", "required": True, "schema": {"type": "integer"}}},
        "schemas": {
            "Planeta": {"type": "object", "required": ["id", "name"], "properties": {
                "id": {"type": "integer", "format": "int64", "example": 1}, "name": {"type": "string"},
                "description": {"type": "string", "nullable": True},
                "lunas": {"type": "array", "items": {"$ref": "#/components/schemas/Planeta"}},  # ciclo
                "orbita": {"type": "object", "properties": {"periodo": {"type": "number", "format": "double", "description": "días"}}}}},
            "Lista": {"type": "object", "properties": {"data": {"type": "array", "items": {"$ref": "#/components/schemas/Planeta"}}}},
        },
    },
}

CASOS = {"historia": "HU-900", "api": "galaxia", "casos": [
    {"id": "CP-API-001", "titulo": "Lista con límite", "operacion": {"operationId": "listPlanets"},
     "params": {"query": {"limit": 2}}, "esperado": {"status": 200, "campos": ["data"], "tiempo_ms": 3000}},
    {"id": "CP-API-002", "titulo": "Crea un planeta", "operacion": {"metodo": "POST", "ruta": "/planets"}, "auth": True,
     "body": {"name": "Vulcano"}, "esperado": {"status": 201, "json": {"name": "Vulcano"}, "campos": ["id"]}, "falta_info": ["FI-01"]},
    {"id": "CP-API-003", "titulo": "Planeta existente", "operacion": {"metodo": "GET", "ruta": "/planets/{planetId}"},
     "params": {"path": {"planetId": 1}}, "esperado": {"status": 200, "json": {"id": 1}}},
    {"id": "CP-API-004", "titulo": "Planeta inexistente", "operacion": {"metodo": "GET", "ruta": "/planets/{planetId}"},
     "params": {"path": {"planetId": 999}}, "esperado": {"status": 404}},
]}


def test_resolver_ciclos_y_schema_compatible():
    s = scalar.schema_respuesta(DOC, DOC["paths"]["/planets/{planetId}"]["get"], 200)
    assert s["properties"]["id"] == {"type": "integer"}  # sin format int64 ni example
    assert s["properties"]["description"]["type"] == ["string", "null"]  # nullable
    assert s["properties"]["orbita"]["properties"]["periodo"] == {"type": "number", "description": "días"}  # anidado intacto
    assert s["properties"]["lunas"]["items"] == {}  # el ciclo queda abierto, no explota


def test_coleccion_un_request_por_caso():
    col = scalar.coleccion(DOC, CASOS)
    assert col["info"]["schema"].endswith("v2.1.0/collection.json") and "HU-900" in col["info"]["name"]
    carpetas = {c["name"]: c["item"] for c in col["item"]}
    assert set(carpetas) == {"GET /planets", "POST /planets", "GET /planets/{planetId}"}
    post = carpetas["POST /planets"][0]
    assert post["name"] == "CP-API-002 · Crea un planeta" and "FI-01" in post["request"]["description"]
    assert {"key": "Authorization", "value": "Bearer {{token}}"} in post["request"]["header"]
    assert json.loads(post["request"]["body"]["raw"]) == {"name": "Vulcano"}
    script = "\n".join(post["event"][0]["script"]["exec"])
    assert "to.have.status(201)" in script and "k0contiene" in script and "jsonSchema" in script
    get = carpetas["GET /planets/{planetId}"]
    assert [i["request"]["url"]["raw"] for i in get] == ["{{base_url}}/planets/1", "{{base_url}}/planets/999"]
    assert carpetas["GET /planets"][0]["request"]["url"]["query"] == [{"key": "limit", "value": "2"}]
    assert {"key": "base_url", "value": "https://api.galaxia.test"} in col["variable"]


def test_no_inventa_endpoints():
    with pytest.raises(ValueError, match="no existe"):
        scalar.coleccion(DOC, {"casos": [{"id": "CP-API-009", "operacion": {"metodo": "DELETE", "ruta": "/planets"}}]})


def test_enriquecer_ejemplos_scripts_y_respeta_lo_manual():
    nuevo = scalar.enriquecer(DOC, CASOS)
    assert DOC["paths"]["/planets/{planetId}"]["get"]["x-post-response"] == "pm.test('mío', () => {})"  # no muta el original
    post = nuevo["paths"]["/planets"]["post"]
    assert post["requestBody"]["content"]["application/json"]["examples"]["CP-API-002"]["value"] == {"name": "Vulcano"}
    get_id = nuevo["paths"]["/planets/{planetId}"]["get"]
    assert get_id["parameters"][0]["name"] == "planetId" and set(get_id["parameters"][0]["examples"]) == {"CP-API-003", "CP-API-004"}
    assert nuevo["components"]["parameters"]["planetId"].get("examples") is None  # el componente compartido no se toca
    lista = nuevo["paths"]["/planets"]["get"]["parameters"][0]
    assert lista["name"] == "limit" and lista["examples"]["CP-API-001"]["value"] == 2
    s = get_id["x-post-response"]
    assert s.startswith("pm.test('mío', () => {})") and s.count(scalar.MARCA_INI) == 1
    assert '"/planets/1"' in s and '"/planets/999"' in s
    otra = scalar.enriquecer(nuevo, CASOS)  # re-enriquecer reemplaza el bloque, no lo duplica
    assert otra["paths"]["/planets/{planetId}"]["get"]["x-post-response"].count(scalar.MARCA_INI) == 1
    assert nuevo["info"]["x-k0lmenia"] == {"historia": "HU-900", "casos": 4}


@pytest.mark.skipif(not shutil.which("node"), reason="node no está instalado")
def test_script_generado_elige_el_caso_por_ruta(tmp_path):
    s = scalar.enriquecer(DOC, CASOS)["paths"]["/planets/{planetId}"]["get"]["x-post-response"]
    (tmp_path / "script.js").write_text(s, encoding="utf-8")
    sim = tmp_path / "sim.js"
    sim.write_text("""
const fs = require('fs'); const out = [];
const exp = (v) => ({ to: { include: (x) => { if (!v.includes(x)) throw new Error('x'); }, not: { equal: () => {} },
  get be() { return { get true() { if (v !== true) throw new Error('no'); return true; }, below: () => {} }; } } });
global.pm = { test: (n, f) => { try { f(); out.push('OK ' + n); } catch (e) { out.push('FALLA ' + n); } }, expect: exp,
  response: { code: Number(process.argv[4]), responseTime: 5, json: () => ({ id: 1, name: 'x' }), headers: { get: () => '' },
    to: { have: { status: (s) => { if (s !== Number(process.argv[4])) throw new Error('s'); }, jsonSchema: () => {} } } },
  request: { body: null, url: { query: { all: () => [] }, getPath: () => process.argv[3] } } };
eval(fs.readFileSync(process.argv[2], 'utf8')); console.log(out.join('\\n'));
""", encoding="utf-8")
    correr = lambda ruta, code: subprocess.run(["node", str(sim), str(tmp_path / "script.js"), ruta, code],  # noqa: E731
                                               capture_output=True, text=True, encoding="utf-8").stdout
    r1 = correr("/planets/1", "200")
    assert "OK CP-API-003 · status 200" in r1 and "CP-API-004" not in r1 and "OK mío" in r1
    r2 = correr("/planets/999", "200")
    assert "FALLA CP-API-004 · status 404" in r2 and "CP-API-003" not in r2
    r3 = correr("/planets/7", "200")
    assert "CP-API" not in r3 and "OK Contrato · status documentado" in r3


def test_publicar_exige_confirmacion(capsys):
    assert scalar.main(["publicar", "x.json", "--namespace", "eq", "--slug", "api", "--version", "1.0.0"]) == 3
    assert "--confirmar" in capsys.readouterr().err


def test_descargar_valida_y_arma_url(monkeypatch, tmp_path):
    with pytest.raises(ValueError):
        scalar.descargar("eq/../x", "api", env={})
    pedido = {}

    class Resp:
        def __init__(self, cuerpo):
            self.cuerpo = cuerpo

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self.cuerpo

    def falso(req, timeout=0):
        pedido["url"], pedido["auth"] = req.full_url, req.headers.get("Authorization")
        return Resp(json.dumps(DOC).encode())

    monkeypatch.setattr(scalar.urllib.request, "urlopen", falso)
    r = scalar.descargar("mi-equipo", "galaxia", salida=tmp_path / "g.json", env={"SCALAR_API_KEY": "tok"})
    assert pedido["url"] == "https://registry.scalar.com/@mi-equipo/apis/galaxia/latest?format=json" and pedido["auth"] == "Bearer tok"
    assert r["operaciones"] == 3 and json.loads((tmp_path / "g.json").read_text(encoding="utf-8"))["info"]["title"] == "Galaxia"

"""Colecciones de Bruno e Insomnia → Postman, GraphQL en los resultados de Newman y resumen de schemas."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import convertir_coleccion as cc  # noqa: E402
import newman_a_resultados as nar  # noqa: E402
import resumir_graphql as rg  # noqa: E402

API = RAIZ / "input" / "api"


def _requests(items):
    for i in items:
        if "item" in i:
            yield from _requests(i["item"])
        else:
            yield i


def _script(item, tipo):
    return "\n".join(next(e["script"]["exec"] for e in item.get("event", []) if e["listen"] == tipo))


# --------------------------------------------------------------------------- formato

def test_detecta_el_formato_de_cada_demo():
    assert cc.detectar_formato(API / "demo-bruno") == "bruno"
    assert cc.detectar_formato(API / "demo.insomnia.json") == "insomnia4"
    assert cc.detectar_formato(API / "demo.postman_collection.json") == "postman"
    assert cc.detectar_formato(API / "demo-graphql.postman_collection.json") == "postman"
    assert cc.detectar_formato(API / "auth-endpoints.md") is None


def test_variables_de_insomnia_y_bruno_quedan_como_postman():
    avisos = []
    assert cc.variables("{{ _.base_url }}/a/{{_['id-x']}}?t={{ token }}", avisos) == "{{base_url}}/a/{{id-x}}?t={{token}}"
    assert cc.variables("{{process.env.CLAVE}}", avisos, "r") == "{{CLAVE}}"
    cc.variables("{% response 'body', 'req_1', 'b64::JC5pZA==::46b' %}", avisos, "r")
    assert len(avisos) == 2 and "template tags" in avisos[1]


# --------------------------------------------------------------------------- Bruno

def test_parsea_bloques_de_bru_con_desactivados_y_texto():
    bloques = cc.parsear_bru("""meta {
  name: Login
  seq: 2
}

post {
  url: {{base_url}}/login
  body: json
  auth: bearer
}

headers {
  X-Tenant: demo
  ~X-Debug: 1
}

body:json {
  {
    "user": "ana"
  }
}

vars:secret [
  token,
  clave
]
""")
    assert bloques["meta"]["name"] == ("Login", True)
    assert bloques["headers"]["X-Debug"] == ("1", False)
    assert json.loads(bloques["body:json"]) == {"user": "ana"}
    assert bloques["vars:secret"] == ["token", "clave"]


def test_demo_bruno_convierte_requests_asserts_y_environment():
    conv = cc.convertir(API / "demo-bruno")
    assert conv.advertencias == []
    carpeta = conv.coleccion["item"][0]
    assert carpeta["name"] == "Posts"
    nombres = [r["name"] for r in carpeta["item"]]
    assert nombres == ["API-001 — Obtener un post existente (Alta)", "API-002 — Crear un post (Media)",
                       "API-003 — Post inexistente devuelve 404 (Media)"]
    crear = carpeta["item"][1]
    assert crear["request"]["method"] == "POST" and crear["request"]["url"] == "{{base_url}}/posts"
    assert json.loads(crear["request"]["body"]["raw"])["title"] == "k0lmenIA"
    test = _script(crear, "test")
    assert 'pm.test("res.status: eq 201", function () { expect(res.status).to.eql(201); });' in test
    assert 'expect(res.body.title).to.eql("k0lmenIA")' in test
    assert 'pm.collectionVariables.set("idCreado", res.body.id);' in test
    assert "const res = {" in test  # el adaptador de Bruno
    assert conv.environment["values"] == [{"key": "base_url", "value": "https://jsonplaceholder.typicode.com", "enabled": True}]


def test_bruno_graphql_auth_secretos_y_advertencias(tmp_path):
    (tmp_path / "bruno.json").write_text('{"version": "1", "name": "GQL", "type": "collection"}', encoding="utf-8")
    (tmp_path / "environments").mkdir()
    (tmp_path / "environments" / "Dev.bru").write_text("vars {\n  url: https://dev\n}\nvars:secret [\n  token\n]\n", encoding="utf-8")
    (tmp_path / "environments" / "Prod.bru").write_text("vars {\n  url: https://prod\n}\n", encoding="utf-8")
    (tmp_path / "Pais.bru").write_text("""meta {
  name: Pais
  type: graphql
  seq: 1
}

post {
  url: {{url}}/graphql
  body: graphql
  auth: bearer
}

auth:bearer {
  token: {{token}}
}

body:graphql {
  query Pais($code: ID!) {
    country(code: $code) { name }
  }
}

body:graphql:vars {
  { "code": "AR" }
}

assert {
  res.body.data.country.name: eq Argentina
  res.body.errors: isUndefined
  res.status: raroOperador 1
}

script:pre-request {
  const x = await bru.runRequest('otro');
}
""", encoding="utf-8")
    (tmp_path / "Archivo.bru").write_text("""meta {
  name: Subir
  seq: 2
}

post {
  url: {{url}}/subir
  body: multipartForm
  auth: awsv4
}

body:multipart-form {
  nombre: ana
  archivo: @file(./foto.png)
}
""", encoding="utf-8")
    conv = cc.convertir(tmp_path, environment="dev")
    pais, subir = conv.coleccion["item"]
    assert pais["request"]["body"] == {"mode": "graphql", "graphql": {
        "query": "query Pais($code: ID!) {\n  country(code: $code) { name }\n}", "variables": '{ "code": "AR" }'}}
    assert pais["request"]["auth"]["bearer"][0]["value"] == "{{token}}"
    assert 'expect(res.body.data.country.name).to.eql("Argentina")' in _script(pais, "test")
    assert subir["request"]["body"]["formdata"][1]["type"] == "file"
    assert {v["key"]: v["value"] for v in conv.environment["values"]} == {"url": "https://dev", "token": ""}
    avisos = " | ".join(conv.advertencias)
    for esperado in ("raroOperador", "bru.runRequest", "awsv4", "archivo", "secretas"):
        assert esperado in avisos
    sin_elegir = cc.convertir(tmp_path)
    assert sin_elegir.environment is None and any("varios environments" in a for a in sin_elegir.advertencias)


# --------------------------------------------------------------------------- Insomnia

def test_demo_insomnia_v4_convierte_variables_params_scripts_y_environment():
    conv = cc.convertir(API / "demo.insomnia.json")
    assert conv.advertencias == []
    reqs = list(_requests(conv.coleccion["item"]))
    assert [r["name"][:7] for r in reqs] == ["API-001", "API-002", "API-003"]  # ordenados por metaSortKey
    assert reqs[0]["request"]["url"] == "{{base_url}}/posts/1"
    assert reqs[2]["request"]["url"] == "{{base_url}}/posts?userId=1"
    assert _script(reqs[0], "test").startswith("// Adaptado de Insomnia")
    assert "const insomnia = pm;" in _script(reqs[0], "test")
    assert conv.environment["name"] == "JSONPlaceholder"


def test_insomnia_v4_graphql_auth_y_lo_que_no_se_convierte(tmp_path):
    export = {"_type": "export", "__export_format": 4, "resources": [
        {"_id": "wrk", "_type": "workspace", "parentId": None, "name": "API"},
        {"_id": "env", "_type": "environment", "parentId": "wrk", "name": "Base", "data": {"api": {"url": "https://x"}}},
        {"_id": "r1", "_type": "request", "parentId": "wrk", "name": "Pais", "method": "POST", "url": "{{ _.api.url }}/graphql",
         "body": {"mimeType": "application/graphql", "text": json.dumps({"query": "query Pais { country { name } }", "variables": {"c": 1}})},
         "authentication": {"type": "bearer", "token": "{{ _.token }}"}},
        {"_id": "r2", "_type": "request", "parentId": "wrk", "name": "Encadenado", "method": "GET",
         "url": "https://x/{% response 'body', 'r1', 'b64::JC5pZA==::46b' %}", "authentication": {"type": "oauth2"}},
        {"_id": "ut", "_type": "unit_test", "parentId": "s", "name": "test"},
    ]}
    archivo = tmp_path / "export.json"
    archivo.write_text(json.dumps(export), encoding="utf-8")
    conv = cc.convertir(archivo)
    reqs = {r["name"]: r for r in conv.coleccion["item"]}
    pais, encadenado = reqs["Pais"], reqs["Encadenado"]
    assert pais["request"]["url"] == "{{api.url}}/graphql"
    assert pais["request"]["body"]["mode"] == "graphql"
    assert pais["request"]["body"]["graphql"]["query"] == "query Pais { country { name } }"
    assert json.loads(pais["request"]["body"]["graphql"]["variables"]) == {"c": 1}
    assert pais["request"]["auth"] == cc._auth_bearer("{{token}}")
    assert conv.environment["values"] == [{"key": "api.url", "value": "https://x", "enabled": True}]
    avisos = " | ".join(conv.advertencias)
    assert "template tags" in avisos and "oauth2" in avisos and "unit tests" in avisos
    assert "auth" not in encadenado["request"]


def test_insomnia_v5_yaml(tmp_path):
    pytest.importorskip("yaml")
    archivo = tmp_path / "coleccion.yaml"
    archivo.write_text("""type: collection.insomnia.rest/5.0
name: Demo v5
collection:
  - name: Posts
    children:
      - url: "{{ _.base_url }}/posts/1"
        name: Obtener post
        method: GET
        meta: {sortKey: 2}
        scripts:
          afterResponse: "insomnia.test('200', () => insomnia.expect(insomnia.response.code).to.eql(200));"
      - url: "{{ _.base_url }}/posts"
        name: Crear post
        method: POST
        meta: {sortKey: 1}
        body: {mimeType: application/json, text: '{"title": "x"}'}
        headers: [{name: Content-Type, value: application/json}]
environments:
  name: Base Environment
  data: {base_url: "https://jsonplaceholder.typicode.com"}
  subEnvironments:
    - name: Local
      data: {base_url: "http://localhost:3000"}
""", encoding="utf-8")
    assert cc.detectar_formato(archivo) == "insomnia5"
    conv = cc.convertir(archivo)
    posts = conv.coleccion["item"][0]
    assert [r["name"] for r in posts["item"]] == ["Crear post", "Obtener post"]
    assert posts["item"][1]["request"]["url"] == "{{base_url}}/posts/1"
    assert "insomnia.test" in _script(posts["item"][1], "test")
    assert conv.environment["name"] == "Local"
    assert conv.environment["values"][0]["value"] == "http://localhost:3000"


def test_guardar_escribe_coleccion_y_environment(tmp_path):
    conv = cc.convertir(API / "demo-bruno")
    col, env = cc.guardar(conv, tmp_path)
    assert col.name == "demo-bruno-k0lmenia-jsonplaceholder.postman_collection.json"
    assert json.loads(col.read_text(encoding="utf-8"))["info"]["schema"] == cc.ESQUEMA
    assert env.exists() and cc.contar_requests(conv.coleccion["item"]) == 3


# --------------------------------------------------------------------------- GraphQL

def test_newman_a_resultados_nombra_la_operacion_graphql():
    gql = lambda q: {"item": {"name": "API-GQL-001 — País (Alta)"}, "request": {"body": {"mode": "graphql", "graphql": {"query": q}}}}  # noqa: E731
    assert nar.operacion_graphql(gql("query Pais($c: ID!) { country(code: $c) { name } }")) == "query Pais"
    assert nar.operacion_graphql(gql("mutation CrearPost { crear { id } }")) == "mutation CrearPost"
    assert nar.operacion_graphql(gql("{ country { name } }")) == "query (anónima)"
    raw = {"request": {"body": {"mode": "raw", "raw": json.dumps({"query": "query Lista { a }"})}}}
    assert nar.operacion_graphql(raw) == "query Lista"
    assert nar.operacion_graphql({"request": {"body": {"mode": "raw", "raw": "{}"}}}) == ""
    datos = nar.convertir({"run": {"executions": [gql("query Pais { a }")]}})
    assert datos["casos"][0]["titulo"] == "País [GraphQL query Pais]" and datos["casos"][0]["prioridad"] == "Alta"


SDL = '''
"""Raíz"""
schema { query: Consulta mutation: Mutacion }
type Consulta {
  "un país"
  pais(codigo: ID!): Pais
  paises(filtro: FiltroPais = {nombre: "a"}, limite: Int = 10): [Pais!]!
}
type Mutacion { crearPais(datos: PaisInput!): Pais! }
type Pais @key(fields: "codigo") { codigo: ID! nombre: String! estado: Estado moneda: Dinero }
input PaisInput { nombre: String! estado: Estado = ACTIVO }
input FiltroPais { nombre: String }
enum Estado { ACTIVO INACTIVO @deprecated(reason: "no") }
scalar Dinero
'''


def test_resumen_de_schema_sdl():
    texto = rg.resumir(rg.desde_sdl(SDL))
    assert "## Query (2)" in texto and "## Mutation (1)" in texto
    assert "- `pais(codigo: ID!)` → `Pais`" in texto
    assert "- `paises(filtro: FiltroPais = «objeto», limite: Int = 10)` → `[Pais!]!`" in texto
    assert "- `crearPais(datos: PaisInput!)` → `Pais!`" in texto
    assert "- `Estado`: ACTIVO, INACTIVO" in texto
    assert "- `PaisInput` { nombre: String!, estado: Estado }" in texto
    assert "Escalares propios: Dinero" in texto


def test_resumen_de_introspeccion():
    ref = lambda kind, name=None, of=None: {"kind": kind, "name": name, "ofType": of}  # noqa: E731
    datos = {"data": {"__schema": {
        "queryType": {"name": "Query"}, "mutationType": None, "subscriptionType": None,
        "types": [
            {"kind": "OBJECT", "name": "Query", "fields": [
                {"name": "usuarios", "isDeprecated": False, "args": [{"name": "rol", "type": ref("ENUM", "Rol"), "defaultValue": None}],
                 "type": ref("NON_NULL", None, ref("LIST", None, ref("NON_NULL", None, ref("OBJECT", "Usuario"))))},
                {"name": "viejo", "isDeprecated": True, "args": [], "type": ref("LIST", None, None)}]},
            {"kind": "OBJECT", "name": "Usuario", "fields": [{"name": "id", "args": [], "type": ref("NON_NULL", None, ref("SCALAR", "ID"))}]},
            {"kind": "ENUM", "name": "Rol", "enumValues": [{"name": "ADMIN"}, {"name": "LECTOR"}]},
            {"kind": "OBJECT", "name": "__Type", "fields": []},
        ]}}}
    texto = rg.resumir(rg.desde_introspeccion(datos))
    assert "- `usuarios(rol: Rol)` → `[Usuario!]!`" in texto
    assert "- `viejo` → `…` (deprecada)" in texto
    assert "- `Rol`: ADMIN, LECTOR" in texto and "- `Usuario` { id: ID! }" in texto
    assert "__Type" not in texto
    assert "kind name ofType { kind name ofType { kind name } }" in rg.query_introspeccion(2)

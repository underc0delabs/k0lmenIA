"""resumir_openapi.py: base URL con basePath/servers, autenticación → step y endpoints, sin red."""
import resumir_openapi as ro

SWAGGER2 = {
    "swagger": "2.0", "info": {"title": "Petstore", "version": "1"}, "host": "petstore.swagger.io", "basePath": "/v2",
    "schemes": ["https", "http"],
    "securityDefinitions": {"api_key": {"type": "apiKey", "name": "api_key", "in": "header"},
                            "basica": {"type": "basic"}},
    "paths": {
        "/pet/{petId}": {
            "parameters": [{"name": "petId", "in": "path", "required": True, "type": "integer", "format": "int64"}],
            "get": {"summary": "Busca", "security": [{"api_key": []}], "responses": {"200": {"description": "ok"}, "404": {"description": "no está"}}},
            "post": {"consumes": ["application/x-www-form-urlencoded"], "summary": "Actualiza con formulario",
                     "parameters": [{"name": "name", "in": "formData", "type": "string"}], "responses": {"405": {"description": "Invalid input"}}},
        },
        "/pet": {"post": {"parameters": [{"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/Pet"}}],
                          "responses": {"200": {"description": "ok"}}}},
        "/pet/{petId}/foto": {"post": {"consumes": ["multipart/form-data"],
                                       "parameters": [{"name": "file", "in": "formData", "type": "file"}], "responses": {}}},
    },
    "definitions": {"Pet": {"type": "object", "required": ["name"], "properties": {
        "id": {"type": "integer", "format": "int64"}, "name": {"type": "string", "example": "doggie"},
        "status": {"type": "string", "enum": ["available", "sold"]}, "dueno": {"$ref": "#/definitions/Pet"}}}},
}

OPENAPI3 = {
    "openapi": "3.0.4", "info": {"title": "Tienda", "version": "2"},
    "servers": [{"url": "/api/{version}", "variables": {"version": {"default": "v3"}}}],
    "security": [{"bearer": []}],
    "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"},
                                       "clave": {"type": "apiKey", "in": "query", "name": "key"}}},
    "paths": {"/user": {"post": {"requestBody": {"required": True, "content": {"application/json": {"schema": {
        "type": "object", "properties": {"email": {"type": "string", "format": "email"}, "edad": {"type": "integer", "minimum": 18}}}}}},
        "responses": {"201": {"description": "creado"}}}},
        "/publico": {"get": {"security": [], "parameters": [{"name": "q", "in": "query", "schema": {"type": "string"}}], "responses": {}}}},
}


def test_swagger2_base_url_con_basepath_y_autenticacion():
    r = ro.resumir(SWAGGER2, "spec.json")
    assert r["api_baseurl"] == "https://petstore.swagger.io/v2"
    assert r["seguridad"]["api_key"]["step"] == 'Given el request usa la API key en el header "api_key"'
    assert r["seguridad"]["basica"]["step"] == "Given el request usa autenticación básica"


def test_swagger2_endpoints_parametros_body_y_formularios():
    eps = {(e["metodo"], e["path"]): e for e in ro.resumir(SWAGGER2, "spec.json")["endpoints"]}
    get = eps[("GET", "/pet/{petId}")]
    assert get["parametros"] == [{"en": "path", "nombre": "petId", "tipo": "integer (int64)", "obligatorio": True}]
    assert get["seguridad"] == ["api_key"]
    assert get["respuestas"] == {"200": "ok", "404": "no está"}
    assert eps[("POST", "/pet/{petId}")]["body"]["tipo"] == "formulario"
    assert eps[("POST", "/pet/{petId}/foto")]["body"]["tipo"] == "multipart"
    ej = eps[("POST", "/pet")]["body"]["ejemplo"]
    assert ej["name"] == "doggie" and ej["status"] == "available" and ej["id"] == 1
    assert ej["dueno"] is None  # referencia circular: no se expande para siempre


def test_openapi3_server_relativo_variables_y_seguridad_global():
    r = ro.resumir(OPENAPI3, "https://tienda.test/docs/openapi.json")
    assert r["api_baseurl"] == "https://tienda.test/api/v3"
    eps = {(e["metodo"], e["path"]): e for e in r["endpoints"]}
    assert eps[("POST", "/user")]["seguridad"] == ["bearer"]
    assert eps[("GET", "/publico")]["seguridad"] == []
    assert eps[("POST", "/user")]["body"]["ejemplo"] == {"email": "qa+{aleatorio}@prueba.com", "edad": 18}
    assert r["seguridad"]["clave"]["step"] == 'Given el request usa la API key en el parámetro "key"'
    md = ro.a_markdown(r, "spec")
    assert "API_BASEURL=https://tienda.test/api/v3" in md
    assert "### POST /user" in md


def test_server_relativo_sin_url_pide_completar():
    r = ro.resumir(OPENAPI3, "openapi.json")
    assert r["api_baseurl"] is None
    assert "relativo" in r["nota_base"]

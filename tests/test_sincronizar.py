"""Sincronizar casos ya subidos (actualizar_caso de cada adaptador): qué pedidos hace cada herramienta para poner al día
título, prioridad, etiquetas, tiempo y pasos o gherkin. El Http está reemplazado por uno que registra los pedidos y
devuelve respuestas armadas."""
import pytest

import comun
from adaptadores.xray_cloud import XrayCloud
from adaptadores.xray_dc import XrayDC

MANUAL = {"id": "CP-001", "titulo": "Login válido", "descripcion": "Entra con datos válidos", "precondiciones": "Sin sesión",
          "prioridad": "Alta", "etiquetas": ["HU-001", "modulo-login", "alta", "regresion"], "tipo": "manual",
          "pasos": [{"accion": "Abrir el login", "datos": "", "resultado": ""},
                    {"accion": "Ingresar", "datos": "ana@test.com", "resultado": "Entra"}]}
BDD = {**MANUAL, "tipo": "cucumber", "pasos": [],
       "gherkin": "Scenario: Login válido\n  Given estoy en el login\n  Then entro"}


@pytest.fixture
def pedidos(monkeypatch):
    """Reemplaza Http.request: registra (herramienta, método, ruta, cuerpo) y responde con lo que diga `respuestas`."""
    registro, respuestas = [], {}

    def request(self, metodo, ruta, *, json_body=None, params=None, **_):
        registro.append((self.nombre, metodo, ruta, json_body))
        for (m, prefijo), respuesta in respuestas.items():
            if m == metodo and ruta.startswith(prefijo):
                return respuesta
        return {}

    monkeypatch.setattr(comun.Http, "request", request)
    monkeypatch.setenv("GESTION_TIEMPO_NATIVO", "0")
    return registro, respuestas


def test_xray_cloud(pedidos, monkeypatch):
    registro, respuestas = pedidos
    for k, v in {"XRAY_CLOUD_CLIENT_ID": "c", "XRAY_CLOUD_CLIENT_SECRET": "s", "JIRA_BASE_URL": "https://jira.test",
                 "JIRA_EMAIL": "qa@test", "JIRA_API_TOKEN": "t"}.items():
        monkeypatch.setenv(k, v)
    respuestas[("POST", "/api/v2/authenticate")] = "token"
    ad = XrayCloud("PROJ")
    registro.clear()
    assert ad.actualizar_caso(MANUAL, {"key": "PROJ-45", "id": "10045"}, {}) == []
    jira = registro[0]
    assert jira[:3] == ("jira", "PUT", "/rest/api/2/issue/PROJ-45")
    assert jira[3]["fields"]["labels"] == ["HU-001", "modulo-login", "alta", "regresion", "k0lmenIA"]
    assert jira[3]["fields"]["priority"] == {"name": "High"} and "project" not in jira[3]["fields"]
    consultas = [c[3]["query"] for c in registro[1:]]
    assert "removeAllTestSteps" in consultas[0] and sum("addTestStep" in q for q in consultas) == 2
    assert registro[2][3]["variables"]["s"] == {"action": "Abrir el login", "data": "", "result": ""}
    registro.clear()
    ad.actualizar_caso(BDD, {"key": "PROJ-46", "id": "10046"}, {})
    assert "updateGherkinTestDefinition" in registro[1][3]["query"]
    assert registro[1][3]["variables"] == {"i": "10046", "g": BDD["gherkin"]}


def test_xray_dc(pedidos, monkeypatch):
    registro, respuestas = pedidos
    monkeypatch.setenv("XRAY_DC_URL", "https://jira.test")
    monkeypatch.setenv("XRAY_DC_TOKEN", "t")
    respuestas[("GET", "/rest/api/2/field")] = [{"name": n, "id": f"customfield_{i}"} for i, n in enumerate(
        ["Test Type", "Cucumber Test Type", "Cucumber Scenario"])]
    respuestas[("GET", "/rest/raven/1.0/api/test/PROJ-45/step")] = [{"id": 1}, {"id": 2}, {"id": 3}]
    ad = XrayDC("PROJ")
    ad.actualizar_caso(MANUAL, {"key": "PROJ-45"}, {})
    metodos = [(m, r) for _, m, r, _ in registro if r != "/rest/api/2/field"]
    assert metodos[0] == ("PUT", "/rest/api/2/issue/PROJ-45")
    assert [r for m, r in metodos if m == "DELETE"] == [f"/rest/raven/1.0/api/test/PROJ-45/step/{i}" for i in (1, 2, 3)]
    assert [c[3]["step"] for c in registro if c[1] == "PUT" and c[2].endswith("/step")] == ["Abrir el login", "Ingresar"]
    registro.clear()
    ad.actualizar_caso(BDD, {"key": "PROJ-46"}, {})
    assert [m for _, m, _, _ in registro] == ["PUT"]  # BDD: los campos de Cucumber van en el PUT del issue
    assert registro[0][3]["fields"]["customfield_2"] == "Given estoy en el login\nThen entro"



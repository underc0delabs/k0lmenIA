"""Lectura de casos (.feature y .xlsx) y conversión para Azure Test Plans."""
from pathlib import Path

import lectores

RAIZ = Path(__file__).resolve().parents[1]

FEATURE = """@HU-001
Feature: Login
  Background:
    Given que estoy en el login

  @CP-001 @smoke
  Scenario: Login válido
    When ingreso credenciales
    Then entro

  @CP-002
  Scenario Outline: Datos inválidos
    When ingreso "<email>"
    Then veo "<msg>"

    @negativos
    Examples: Formato
      | email | msg      |
      | x     | inválido |

    @borde
    Examples: Vacíos
      | email | msg         |
      |       | obligatorio |

  Rule: Bloqueo
    Background:
      Given que fallé 2 veces

    @CP-003
    Example: Tercer intento
      When fallo otra vez
      Then se bloquea
"""


def test_leer_feature_completo(tmp_path):
    archivo = tmp_path / "HU-001.feature"
    archivo.write_text(FEATURE, encoding="utf-8")
    casos = {c["id"]: c for c in lectores.leer_feature(archivo)}
    assert list(casos) == ["CP-001", "CP-002", "CP-003"]
    assert casos["CP-001"]["prioridad"] == "Alta"  # @smoke, en minúscula
    assert "HU-001" in casos["CP-001"]["etiquetas"]
    # Un tag de prioridad explícito manda sobre @smoke
    assert lectores.prioridad_de_tags(["smoke", "critica"]) == "Crítica"
    assert lectores.prioridad_de_tags(["alta"]) == "Alta"
    assert lectores.prioridad_de_tags(["HU-001"]) == "Media"  # sin tag ni smoke
    # Los dos Examples con tags quedan dentro del Scenario Outline
    assert casos["CP-002"]["gherkin"].count("Examples:") == 2
    # El escenario dentro de la Rule hereda el Background de la feature y el de la regla
    assert casos["CP-003"]["gherkin"].count("Given que") == 2


def test_leer_xlsx_de_la_plantilla():
    casos = lectores.leer_casos(RAIZ / "plantillas" / "plantilla-casos-prueba.xlsx")
    assert casos and all(c["id"].startswith("CP-") for c in casos)
    assert all(c["pasos"] for c in casos)


def test_newman_respeta_el_base_url_de_la_coleccion(tmp_path):
    import correr_newman
    coleccion = RAIZ / "input" / "api" / "demo.postman_collection.json"
    environment = RAIZ / "input" / "api" / "demo.postman_environment.json"
    assert "jsonplaceholder" in correr_newman.base_url_propia(coleccion, str(environment))
    vacia = tmp_path / "c.json"
    vacia.write_text('{"info": {"name": "x"}, "item": []}', encoding="utf-8")
    assert correr_newman.base_url_propia(vacia, None) is None  # entonces se usa API_BASEURL del .env

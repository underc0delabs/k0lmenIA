"""Lectura de casos (.feature y .xlsx) y conversión para Azure Test Plans."""
from pathlib import Path

import lectores
import para_azure_devops

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
    # Los dos Examples con tags quedan dentro del Scenario Outline
    assert casos["CP-002"]["gherkin"].count("Examples:") == 2
    # El escenario dentro de la Rule hereda el Background de la feature y el de la regla
    assert casos["CP-003"]["gherkin"].count("Given que") == 2


def test_leer_xlsx_de_la_plantilla():
    casos = lectores.leer_casos(RAIZ / "plantillas" / "plantilla-casos-prueba.xlsx")
    assert casos and all(c["id"].startswith("CP-") for c in casos)
    assert all(c["pasos"] for c in casos)


def test_conversion_azure_devops(tmp_path):
    archivo = tmp_path / "HU-001.feature"
    archivo.write_text(FEATURE, encoding="utf-8")
    convertido = [para_azure_devops.convertir(c) for c in lectores.leer_feature(archivo)]
    login = convertido[0]
    assert login["title"].startswith("CP-001 - ")
    assert login["priority"] == 2
    # Cada paso lleva resultado esperado: "-" si no tiene (el server inventaría uno en inglés)
    for linea in login["steps"].splitlines():
        assert "|" in linea and linea.split("|", 1)[1].strip()
    assert "Then entro" in login["steps"]

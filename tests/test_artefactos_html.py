"""Informes HTML (ES + EN) de los artefactos de los agentes: bug, casos (planilla), BDD, Markdown con tablas ASCII,
datos en CSV y el modo lote. Con y sin la versión en inglés que escribe el agente."""
import json
import os
import subprocess
import sys
from pathlib import Path

import generar_casos
import generar_informe_artefacto as art

RAIZ = Path(__file__).resolve().parents[1]

BUG_ES = (RAIZ / "evals/insumos/bugs-previos/BUG-004.md").read_text(encoding="utf-8")
BUG_EN = """**ID:** `BUG-004`

**Title:** `[Cart]` The discount coupon is applied more than once

**Story:** `HU-870`

**Status:** `Closed`

**Description:**
After applying a valid coupon and tapping "Apply" again, the discount is added again.

**Steps to reproduce:**
1. Add a product to the cart.
2. Tap "Apply" twice.

**Actual result:**
The discount stacks.

**Expected result:**
The coupon applies only once.

**Criticality / Severity:** High

**Priority:** High

**Browser:** Chrome

**Environment:** QA
"""

FEATURE = """# language: en
@HU-901
Feature: Registro de cuenta
  Como visitante quiero crear una cuenta

  Background:
    Given estoy en el formulario de registro

  @CP-001 @critica
  Scenario: Registro válido
    When completo los datos válidos
    Then veo "¡Cuenta creada!"

  # FI-01: la edad mínima no está definida
  @CP-002 @falta-info @FI-01
  Scenario Outline: Edad límite
    When ingreso una fecha de <edad> años
    Then el resultado es "<resultado>"

    Examples:
      | edad | resultado |
      | 17   | rechazado |
      | 18   | aceptado  |
"""

ANALISIS = """# Análisis de HU-901 — Registro

## Resumen
La historia define el alta de cuenta.

## Ambigüedades
- La contraseña "segura" no tiene reglas.
- Edad mínima: 18 vs 16 (FI-01).

## Preguntas para el PO
```
+-----+------------------------------------+--------------+
|   # | Pregunta                           | Falta info   |
+=====+====================================+==============+
|   1 | ¿Cuál es la edad mínima? La        | FI-01        |
|     | descripción dice 18 y el CA4 16.   |              |
+-----+------------------------------------+--------------+
|   2 | ¿Qué reglas tiene la contraseña?   | FI-02        |
+-----+------------------------------------+--------------+
```

## Riesgos
- Registro de menores.
"""


def _carpeta(tmp_path, sub):
    c = tmp_path / "output" / sub
    c.mkdir(parents=True, exist_ok=True)
    return c


def _leer(p):
    return Path(p).read_text(encoding="utf-8")


def test_bug_con_ingles(tmp_path):
    c = _carpeta(tmp_path, "reportes-bug")
    (c / "BUG-004.md").write_text(BUG_ES, encoding="utf-8")
    (c / "BUG-004.en.md").write_text(BUG_EN, encoding="utf-8")
    art.generar(c / "BUG-004.md", raiz=tmp_path / "output")
    es, en = _leer(c / "BUG-004.html"), _leer(c / "BUG-004.en.html")
    assert 'lang="es"' in es and "Pasos de reproducción" in es and "DESC15" in es
    assert 'lang="en"' in en and "The coupon applies only once." in en and "Steps to reproduce" in en
    assert "Severity" in en and ">High<" in en  # la escala sale del original y la traduce el diccionario
    assert "no generó la versión en inglés" not in en and "did not generate" not in en


def test_bug_sin_ingles_avisa(tmp_path):
    c = _carpeta(tmp_path, "reportes-bug")
    (c / "BUG-004.md").write_text(BUG_ES, encoding="utf-8")
    art.generar(c / "BUG-004.md", raiz=tmp_path / "output")
    en = _leer(c / "BUG-004.en.html")
    assert "did not generate the English version" in en
    assert "DESC15" in en  # el contenido queda en español


def test_casos_desde_generar_casos_con_bloque_en(tmp_path):
    c = _carpeta(tmp_path, "casos-de-prueba/manuales")
    entrada = tmp_path / "casos.json"
    entrada.write_text(json.dumps({
        "proyecto": "Tienda", "modulo": "HU-901 — Registro", "en": {"modulo": "HU-901 — Sign-up"},
        "casos": [
            {"id": "CP-001", "titulo": "Registro con datos válidos", "datos": "Email: ana@test.com\nUsuario: ana_01",
             "pasos": "1. Completar los campos\n2. Enviar", "resultado": "Se crea la cuenta", "estado": "Pendiente",
             "prioridad": "Alta", "en": {"titulo": "Sign-up with valid data", "pasos": "1. Fill in the fields\n2. Submit",
                                         "resultado": "The account is created", "prioridad": "High"}},
            {"id": "CP-002", "titulo": "Edad mínima", "pasos": "1. Ingresar 17 años", "resultado": "A confirmar",
             "estado": "Pendiente", "prioridad": "Crítica", "falta_info": ["FI-01"]}],
        "falta_informacion": [{"id": "FI-01", "que_falta": "Edad mínima", "pregunta": "¿Cuál es la edad mínima?"}]},
        ensure_ascii=False), encoding="utf-8")
    xlsx = c / "casos-HU-901.xlsx"
    r = subprocess.run([sys.executable, str(RAIZ / "scripts/generar_casos.py"), str(entrada), str(xlsx)],
                       capture_output=True, text=True, encoding="utf-8", env={**os.environ, "K0LMENIA_PORTAL": "0", "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stderr
    assert (c / "casos-HU-901.en.json").exists()
    es, en = _leer(c / "casos-HU-901.html"), _leer(c / "casos-HU-901.en.html")
    assert "Registro con datos válidos" in es and "Falta información" in es
    assert "Sign-up with valid data" in en and "Fill in the fields" in en and "HU-901 — Sign-up" in en
    assert "Edad mínima" in en  # CP-002 no trae inglés: queda en español
    assert ">Critical<" in en and ">High<" in en  # prioridades del original, traducidas
    assert "Missing information" in en


def test_casos_desde_planilla_sin_ingles(tmp_path):
    c = _carpeta(tmp_path, "casos-de-prueba/manuales")
    data = {"proyecto": "Tienda", "modulo": "HU-902", "casos": [
        {"id": "CP-001", "titulo": "Login", "pasos": "1. Ingresar", "resultado": "Entra", "estado": "Aprobado", "prioridad": "Media"}]}
    generar_casos.preparar_falta_info(data)
    generar_casos.preparar_tiempos(data)
    generar_casos.to_xlsx(data, str(c / "casos-HU-902.xlsx"))
    escritos = art.actualizar_artefactos(tmp_path / "output")
    assert c / "casos-HU-902.html" in escritos
    en = _leer(c / "casos-HU-902.en.html")
    assert "did not generate the English version" in en and ">Passed<" in en


def test_feature_legible_con_outline_y_examples(tmp_path):
    c = _carpeta(tmp_path, "casos-de-prueba/bdd")
    (c / "HU-901-registro.feature").write_text(FEATURE, encoding="utf-8")
    (c / "HU-901-registro.feature.en").write_text(
        FEATURE.replace("Registro de cuenta", "Account sign-up").replace("Edad límite", "Age boundary"), encoding="utf-8")
    art.generar(c / "HU-901-registro.feature", raiz=tmp_path / "output")
    es, en = _leer(c / "HU-901-registro.html"), _leer(c / "HU-901-registro.en.html")
    assert "Scenario Outline" in es and "Edad límite" in es and "@falta-info" in es
    assert "<th>edad</th>" in es and "<td>17</td>" in es  # Examples como tabla
    assert "Background" in es and "estoy en el formulario de registro" in es
    assert "Account sign-up" in en and "Age boundary" in en
    assert not list(c.glob("*.en.feature"))  # el inglés nunca queda como .feature


def test_markdown_con_tablas_ascii(tmp_path):
    c = _carpeta(tmp_path, "analisis-historias")
    (c / "analisis-HU-901.md").write_text(ANALISIS, encoding="utf-8")
    art.generar(c / "analisis-HU-901.md", raiz=tmp_path / "output")
    es = _leer(c / "analisis-HU-901.html")
    assert "<table>" in es and "<th>Pregunta</th>" in es
    assert "¿Cuál es la edad mínima? La descripción dice 18 y el CA4 16." in es  # celda ajustada, unida
    assert "+=====" not in es  # la tabla ASCII no queda como texto
    assert "Ambigüedades" in es and "Riesgos" in es
    en = _leer(c / "analisis-HU-901.en.html")
    assert "Ambiguities" in en and "Questions" in en


def test_datos_csv(tmp_path):
    c = _carpeta(tmp_path, "datos-de-prueba")
    (c / "datos-HU-901.csv").write_text("Nombre;Email;Tipo;Resultado esperado\nAna;ana@test.com;Válido;Aceptado\n"
                                        "X;mal;Inválido;Rechazado: email\n", encoding="utf-8")
    art.generar(c / "datos-HU-901.csv", raiz=tmp_path / "output")
    es = _leer(c / "datos-HU-901.html")
    assert "<td>ana@test.com</td>" in es and "Válido" in es


def test_lote_idempotente_y_traducciones_no_son_artefactos(tmp_path):
    c = _carpeta(tmp_path, "reportes-bug")
    (c / "BUG-004.md").write_text(BUG_ES, encoding="utf-8")
    (c / "BUG-004.en.md").write_text(BUG_EN, encoding="utf-8")
    ctx = _carpeta(tmp_path, "contexto")
    (ctx / "contexto-HU-901.md").write_text("# Contexto\n\n## Fuentes consultadas\n- Jira\n", encoding="utf-8")
    primera = art.actualizar_artefactos(tmp_path / "output")
    assert sorted(p.name for p in primera) == ["BUG-004.html", "contexto-HU-901.html"]
    assert art.actualizar_artefactos(tmp_path / "output") == []
    os.utime(c / "BUG-004.en.md", None)
    (c / "BUG-004.en.md").write_text(BUG_EN + "\n", encoding="utf-8")
    t = (c / "BUG-004.html").stat().st_mtime + 5
    os.utime(c / "BUG-004.en.md", (t, t))
    assert [p.name for p in art.actualizar_artefactos(tmp_path / "output")] == ["BUG-004.html"]


def test_convenciones_de_nombres():
    assert art.ruta_en_de("x/BUG-001.md").name == "BUG-001.en.md"
    assert art.ruta_en_de("x/HU-1.feature").name == "HU-1.feature.en"
    assert art.ruta_en_de("x/casos-HU-1.xlsx").name == "casos-HU-1.en.json"
    assert art.ruta_en_de("x/datos-HU-1.csv").name == "datos-HU-1.en.csv"

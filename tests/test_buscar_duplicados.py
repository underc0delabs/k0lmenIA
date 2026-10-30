"""Búsqueda de bugs duplicados y relacionados (agente triador-bugs)."""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import buscar_duplicados as bd  # noqa: E402

BUG_MD = """**ID:** `BUG-008`

**Título:** `[Checkout]` El pago con tarjeta rechaza tarjetas válidas

**Historia:** `PROJ-12`

**Estado:** Abierto

**Descripción:**
Al pagar con una tarjeta Visa válida, el checkout muestra "Tarjeta inválida" y no deja continuar.

**Pasos de reproducción:**
1. Agregar un producto al carrito
2. Ir al checkout y pagar con tarjeta

**Resultado Actual:**
Muestra "Tarjeta inválida".

**Resultado Esperado:**
El pago se procesa.
"""


def test_lee_el_reporte_de_la_plantilla():
    bug = bd.leer_bug_md(BUG_MD)
    assert bug["id"] == "BUG-008"
    assert bug["titulo"] == "[Checkout] El pago con tarjeta rechaza tarjetas válidas"
    assert bug["historia"] == "PROJ-12" and bug["estado"] == "Abierto"
    assert "Tarjeta inválida" in bug["resultado_actual"]


def test_nota_suelta_toma_la_primera_linea_como_titulo():
    bug = bd.leer_bug_md("# El login no responde\nAl apretar Ingresar no pasa nada.", "observacion-login")
    assert bug["id"] == "observacion-login" and bug["titulo"] == "El login no responde"


def test_clasifica_duplicado_relacionado_y_distinto_con_sinonimos_en_ingles():
    bug = bd.leer_bug_md(BUG_MD)
    candidatos = [
        {"id": "PROJ-120", "titulo": "[Checkout] Valid card payment rejected", "descripcion": "Paying with a valid Visa card shows \"Tarjeta inválida\"",
         "estado": "Open", "fuente": "jira", "historia": "PROJ-12"},
        {"id": "PROJ-121", "titulo": "El carrito no actualiza el total al pagar", "descripcion": "checkout con cupón", "estado": "Abierto", "fuente": "jira"},
        {"id": "PROJ-122", "titulo": "Logo cortado en el pie de página", "descripcion": "footer en mobile", "estado": "Abierto", "fuente": "jira"},
    ]
    res = {c["id"]: c for c in bd.comparar(bug, candidatos)}
    assert res["PROJ-120"]["clasificacion"] == bd.DUPLICADO
    assert any("mismo mensaje" in m for m in res["PROJ-120"]["motivos"])
    assert res["PROJ-121"]["clasificacion"] == bd.RELACIONADO
    assert res["PROJ-122"]["clasificacion"] == bd.DISTINTO
    assert list(res)[0] == "PROJ-120"  # ordenado por puntaje


def test_duplicado_cerrado_es_posible_regresion_y_no_se_compara_consigo_mismo():
    bug = bd.leer_bug_md(BUG_MD)
    cerrado = dict(bd.leer_bug_md(BUG_MD), id="BUG-002", estado="Resuelto")
    res = bd.comparar(bug, [cerrado, dict(bug)])
    assert [r["id"] for r in res] == ["BUG-002"]
    assert res[0]["posible_regresion"]
    assert bd.veredicto(res) == "Posible regresión de un bug cerrado"
    assert bd.veredicto([]) == "Nuevo"


def test_main_escribe_json_y_md(tmp_path, capsys):
    bug = tmp_path / "BUG-008.md"
    bug.write_text(BUG_MD, encoding="utf-8")
    cand = tmp_path / "candidatos.json"
    cand.write_text(json.dumps([{"id": "PROJ-120", "titulo": "[Checkout] El pago con tarjeta rechaza tarjetas", "fuente": "jira",
                                 "descripcion": "Muestra \"Tarjeta inválida\" con una tarjeta válida"}]), encoding="utf-8")
    salida = tmp_path / "out"
    assert bd.main(["--bug", str(bug), "--candidatos", str(cand), "--sin-locales", "--salida", str(salida)]) == 0
    datos = json.loads((salida / "triage.json").read_text(encoding="utf-8"))
    assert datos["bugs"][0]["veredicto"] == "Duplicado probable"
    md = (salida / "triage.md").read_text(encoding="utf-8")
    assert "PROJ-120" in md and "+====" in md
    assert "BUG-008: Duplicado probable" in capsys.readouterr().out


def test_lote_compara_los_bugs_entre_si(tmp_path):
    (tmp_path / "BUG-001.md").write_text(BUG_MD.replace("BUG-008", "BUG-001"), encoding="utf-8")
    (tmp_path / "BUG-002.md").write_text(BUG_MD.replace("BUG-008", "BUG-002"), encoding="utf-8")
    salida = tmp_path / "out"
    bd.main(["--lote", str(tmp_path), "--sin-locales", "--salida", str(salida), "--nombre", "lote"])
    datos = json.loads((salida / "triage.json").read_text(encoding="utf-8"))
    assert [b["coincidencias"][0]["id"] for b in datos["bugs"]] == ["BUG-002", "BUG-001"]

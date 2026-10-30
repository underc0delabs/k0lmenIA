"""Lo que la auditoría de agentes encontró sin informe o fuera del portal: gestión de pruebas (JSON), Scalar, la
documentación del proyecto (input/documentacion/) y el aviso de los documentos que van en inglés solo a pedido."""
import json

import generar_informe_artefacto as art
import portal_informes as portal
from _i18n import ruta_en, ruta_es


def _json(p, datos):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(datos), encoding="utf-8")


def test_gestion_trazabilidad_y_resultados_tienen_html(tmp_path):
    o = tmp_path / "output"
    _json(o / "gestion" / "HU-001-xray-cloud.json", {
        "herramienta": "xray-cloud", "proyecto": "PROJ", "historia": "PROJ-12", "carpeta": {"ruta": "/HU-001"},
        "casos": {"CP-001": {"key": "PROJ-45", "titulo": "Registro válido", "vinculado": "PROJ-12"},
                  "CP-002": {"key": "PROJ-46", "titulo": "Email duplicado", "vinculado": False}},
        "ciclos": [{"key": "PROJ-60", "nombre": "Sprint 5", "fecha": "2026-10-20T10:00"}]})
    _json(o / "gestion" / "resultados-20261020-1000.json", [
        {"feature": "Registro", "escenario": "Alta", "tags": ["CP-001"], "estado": "aprobado", "error": "", "evidencias": []},
        {"feature": "Registro", "escenario": "Duplicado", "tags": ["CP-002"], "estado": "bloqueado", "error": "BLOQUEO ANTI-BOTS", "evidencias": []}])
    escritos = art.actualizar_artefactos(o)
    assert {p.name for p in escritos} == {"HU-001-xray-cloud.html", "resultados-20261020-1000.html"}
    traz = ruta_es(o / "gestion" / "HU-001-xray-cloud.html").read_text(encoding="utf-8")
    assert "PROJ-45" in traz and "Sprint 5" in traz and "Sin vincular a la historia" in traz
    en = ruta_en(o / "gestion" / "resultados-20261020-1000.html").read_text(encoding="utf-8")
    assert "Published results" in en and "Blocked" in en
    assert art.actualizar_artefactos(o) == []  # idempotente


def test_documentacion_del_proyecto(tmp_path):
    o = tmp_path / "output"
    o.mkdir()
    doc = tmp_path / "input" / "documentacion"
    (doc / "proyecto").mkdir(parents=True)
    (doc / "INDICE.md").write_text("# Índice\n\n- proyecto/reglas.md\n", encoding="utf-8")
    (doc / "proyecto" / "reglas.md").write_text("# Reglas de negocio\n\n## Registro\n\nEdad mínima: 18.\n", encoding="utf-8")
    escritos = art.actualizar_artefactos(o, documentacion=doc)
    nombres = {p.relative_to(o).as_posix() for p in escritos}
    assert {"documentacion/INDICE.html", "documentacion/proyecto/reglas.html"} <= nombres
    assert not any((doc / "proyecto").glob("*.html"))  # input/ no se toca
    en = ruta_en(o / "documentacion" / "proyecto" / "reglas.html").read_text(encoding="utf-8")
    assert "only on request" in en  # la documentación va en inglés solo a pedido: el aviso lo explica
    h = portal.descubrir(o, None)
    assert h["documentacion"] and portal.categoria_de("documentacion") == "documentacion"


def test_documento_con_version_en_ingles_no_avisa(tmp_path):
    o = tmp_path / "output"
    (o / "contexto").mkdir(parents=True)
    (o / "contexto" / "contexto-HU-001.md").write_text("# Contexto HU-001\n\n## Fuentes\n\n- Jira PROJ-12\n", encoding="utf-8")
    (o / "contexto" / "contexto-HU-001.en.md").write_text("# Context HU-001\n\n## Sources\n\n- Jira PROJ-12\n", encoding="utf-8")
    art.actualizar_artefactos(o)
    en = ruta_en(o / "contexto" / "contexto-HU-001.html").read_text(encoding="utf-8")
    assert "Context HU-001" in en and "only on request" not in en

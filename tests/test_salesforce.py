"""Probador de Salesforce: la lógica de hallazgos/sugerencias del inventario y el informe HTML."""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "herramientas" / "salesforce"))

import generar_informe_salesforce as gi
import inventario as inv
from _i18n import ruta_en, ruta_es  # noqa: E402


def test_hallazgos_cobertura_baja_y_sin_cubrir():
    data = {"cobertura": [{"ApexClassOrTrigger": {"Name": "AService"}, "NumLinesCovered": 10, "NumLinesUncovered": 40},
                          {"ApexClassOrTrigger": {"Name": "BService"}, "NumLinesCovered": 0, "NumLinesUncovered": 20}],
            "organizacion": {"IsSandbox": True}}
    h, _ = inv.hallazgos_y_sugerencias(data)
    assert data["cobertura_org"] == round(100 * 10 / 70, 1)  # 10 cubiertas de 70 totales
    textos = " ".join(x["texto"] for x in h)
    assert "menos del 75 %" in textos and "BService" in textos


def test_process_builder_activo_es_hallazgo():
    h, _ = inv.hallazgos_y_sugerencias({"organizacion": {"IsSandbox": True},
                                        "flows": [{"Label": "Asignar", "ProcessType": "Workflow", "IsActive": True}]})
    assert any("Process Builder" in x["texto"] for x in h)


def test_varios_triggers_por_objeto_y_sugerencia_bulk():
    h, s = inv.hallazgos_y_sugerencias({"organizacion": {"IsSandbox": True},
                                        "triggers": [{"Name": "T1", "TableEnumOrId": "Account", "Status": "Active"},
                                                     {"Name": "T2", "TableEnumOrId": "Account", "Status": "Active"}]})
    assert any("2 triggers activos" in x["texto"] for x in h)
    assert any("200 registros" in x["prueba"] for x in s)


def test_produccion_marca_hallazgo_critico():
    h, _ = inv.hallazgos_y_sugerencias({"organizacion": {"IsSandbox": False}})
    assert any(x["severidad"] == "Crítica" and "PRODUCCIÓN" in x["texto"] for x in h)


def test_validacion_activa_sugiere_negativo_y_positivo():
    _, s = inv.hallazgos_y_sugerencias({"organizacion": {"IsSandbox": True},
                                        "validaciones": [{"ValidationName": "Monto", "Active": True, "ErrorMessage": "Falta monto",
                                                          "ErrorDisplayField": "Amount", "EntityDefinition": {"QualifiedApiName": "Opportunity"}}]})
    assert any("Opportunity" in x["elemento"] and "Falta monto" in x["prueba"] for x in s)


def test_objetos_a_revisar_filtra_nombres_invalidos():
    assert inv.objetos_a_revisar("Account, Opp, 1drop; x", []) == ["Account", "Opp"]  # descarta los inválidos
    custom = [{"DeveloperName": "Pedido", "NamespacePrefix": None}]
    assert "Pedido__c" in inv.objetos_a_revisar("", custom) and "Account" in inv.objetos_a_revisar("", custom)


def test_informe_html(tmp_path, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    datos = {"generado": "2026-10-19T10:00:00", "historia": "HU-010",
             "org": {"alias": "qa-sb", "nombre": "QA", "tipo": "Developer", "sandbox": True, "api": "62.0"},
             "inventario": {"cobertura_org": 68.0, "validaciones": [], "flows": [], "triggers": [],
                            "limites": [{"name": "DailyApiRequests", "max": 100, "remaining": 5}], "errores": {}},
             "hallazgos": [{"severidad": "Alta", "area": "Apex", "texto": "Cobertura 68 %"}],
             "sugerencias": [{"area": "Validación", "elemento": "Opportunity.Monto", "prueba": "Guardar sin monto"}]}
    (tmp_path / "salesforce.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "salesforce.json", tmp_path / "informe.html")
    html = ruta_es(tmp_path / "informe.html").read_text(encoding="utf-8")
    assert "Salesforce" in html and "Sandbox" in html and "Cobertura 68 %" in html and "Guardar sin monto" in html
    assert "DailyApiRequests" in html  # el límite usado al 95 % entra en "Límites más usados"


def test_informe_produccion_avisa(tmp_path, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    datos = {"org": {"alias": "prod", "sandbox": False, "tipo": "Production"}, "inventario": {"errores": {}}, "hallazgos": [], "sugerencias": []}
    (tmp_path / "s.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "s.json", tmp_path / "i.html")
    assert "PRODUCCIÓN" in ruta_es(tmp_path / "i.html").read_text(encoding="utf-8")

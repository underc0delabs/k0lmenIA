"""Conectores MCP: el doctor los conoce, el estado se calcula sin mirar valores del .env y el informe HTML (ES/EN) sale
completo."""
import json
from pathlib import Path

import doctor
import generar_informe_conectores as gic
from _i18n import ruta_en, ruta_es

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = json.loads((RAIZ / "scripts/mcp/catalogo.json").read_text(encoding="utf-8"))


def test_el_doctor_conoce_a_todos_los_conectores_del_catalogo():
    for n in CATALOGO["conectores"]:
        con_credenciales = n in doctor.VARIABLES_CONECTOR
        por_oauth = n in doctor.CONECTORES_OAUTH or n in doctor.CONECTORES_TOKEN_OPCIONAL
        assert con_credenciales or por_oauth, f"{n}: el doctor no sabe qué necesita"
    assert set(doctor.VARIABLES_CONECTOR) <= set(CATALOGO["conectores"]) | {"atlassian"}


def test_estado_sin_valores_y_con_cada_caso():
    catalogo = {"k0lmena-tmt": CATALOGO["conectores"]["k0lmena-tmt"]}
    env = {"K0LMENA_TMT_TOKEN": "tmt_secreto"}
    d = gic.estado(env, catalogo, ["playwright"], activos={"playwright"})
    por = {f["nombre"]: f for f in d["conectores"]}
    assert por["playwright"]["estado"] == "Listo"
    assert por["k0lmena-tmt"]["estado"] == "Listo para activar"  # el token está, pero no está activado
    assert por["k0lmena-tmt"]["como"] == "npm run conector -- activar k0lmena-tmt"
    assert "tmt_secreto" not in json.dumps(d), "el estado nunca lleva valores del .env"
    faltante = gic.estado({}, catalogo, [], activos={"k0lmena-tmt"})
    fila = faltante["conectores"][0]
    assert fila["estado"] == "Activo con datos faltantes" and fila["faltan"] == ["K0LMENA_TMT_TOKEN"]
    assert faltante["veredicto_tono"] == "bad" and faltante["resumen"]["con_faltantes"] == 1
    plugin = gic.estado(env, catalogo, [], activos=set(), como_plugin=True)
    assert plugin["conectores"][0]["como"].startswith("k0lmenia conector -- activar")
    assert plugin["veredicto_tono"] == "warn"


def test_informe_bilingue_completo(tmp_path, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    datos = gic.estado({"K0LMENA_TMT_TOKEN": "token-unico-123"}, CATALOGO["conectores"], ["playwright", "atlassian"],
                       activos={"k0lmena-tmt"})
    salida = gic.generar(datos, tmp_path / "estado.html", CATALOGO["_sin_conector"], CATALOGO["_sin_conector_en"])
    es, en = ruta_es(salida).read_text(encoding="utf-8"), ruta_en(salida).read_text(encoding="utf-8")
    assert "Estado de los conectores MCP" in es and "k0lmena-tmt" in es
    assert "MCP connector status" in en
    guardado = json.loads((tmp_path / "conectores.json").read_text(encoding="utf-8"))
    assert guardado["resumen"]["activos"] == 3 and "token-unico-123" not in json.dumps(guardado)

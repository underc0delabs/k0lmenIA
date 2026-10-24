"""Seguridad estática: tools de SCA (dependencias) y SAST/secretos (sast) y sus informes."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "herramientas" / "seguridad"))

import dependencias  # noqa: E402
import generar_informe_dependencias as gid  # noqa: E402
import generar_informe_sast as gis  # noqa: E402
import sast  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402


# ---------------- SCA ----------------
def test_parse_npm_audit_y_conteo():
    data = {"vulnerabilities": {
        "lodash": {"severity": "high", "range": "<4.17.21", "fixAvailable": True},
        "minimist": {"severity": "critical", "range": "<1.2.6", "fixAvailable": {"name": "minimist"}}},
        "metadata": {"vulnerabilities": {"high": 1, "critical": 1, "total": 2}}}
    vulns, meta = dependencias.parse_npm_audit(data)
    sev = {v["paquete"]: v["severidad"] for v in vulns}
    assert sev == {"lodash": "Alta", "minimist": "Crítica"}
    assert all(v["fix"] for v in vulns)  # fixAvailable dict también cuenta como True
    assert dependencias.contar(vulns)["Crítica"] == 1 and dependencias.contar(vulns)["Alta"] == 1
    assert meta.get("total") == 2


def test_parse_pip_audit():
    data = [{"name": "jinja2", "version": "2.11.0", "vulns": [{"id": "PYSEC-2021-1", "fix_versions": ["2.11.3"]}]}]
    v = dependencias.parse_pip_audit(data)
    assert v[0]["id"] == "PYSEC-2021-1" and v[0]["ecosistema"] == "Python" and v[0]["fix"] is True


# ---------------- SAST / secretos ----------------
def test_buscar_secretos_detecta_y_redacta():
    texto = 'const k = "AKIAIOSFODNN7EXAMPLE";\npassword = "supersecreto123"\nnada = "hola mundo texto"'
    res = sast.buscar_secretos(texto)
    tipos = {t for t, _, _ in res}
    assert "Clave de acceso AWS" in tipos and "Credencial en asignación" in tipos
    assert all("supersecreto123" not in frag for _, _, frag in res)  # el valor va redactado


def test_parse_semgrep():
    data = {"results": [{"check_id": "rule.sql", "path": "src/db.js", "start": {"line": 42},
                         "extra": {"severity": "ERROR", "message": "SQL injection"}}]}
    out = sast.parse_semgrep(data)
    assert out[0]["severidad"] == "Alta" and out[0]["archivo"] == "src/db.js" and out[0]["linea"] == 42


# ---------------- Informes ----------------
def _gen(mod, tmp_path, datos, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    (tmp_path / "analisis.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    mod.generar(tmp_path / "analisis.json", tmp_path / "informe.html")
    return ruta_es(tmp_path / "informe.html").read_text(encoding="utf-8")


def test_informe_dependencias(tmp_path, monkeypatch):
    datos = {"titulo": "SCA — mi-app", "proyecto": {"ruta": "/x", "ecosistemas": ["Node"]}, "escaneres": ["npm audit"],
             "veredicto": "2 críticas con fix", "veredicto_tono": "bad",
             "vulnerabilidades": [{"paquete": "lodash 4.17.4", "severidad": "Crítica", "id": "CVE-2021-23337",
                                   "ecosistema": "Node", "fix": True, "recomendacion": "actualizar a 4.17.21"}],
             "falta_informacion": [{"id": "FI-01", "que_falta": "licencias", "pregunta": "¿se revisan?"}]}
    html = _gen(gid, tmp_path, datos, monkeypatch)
    assert "SCA — mi-app" in html and "CVE-2021-23337" in html and "FI-01" in html


def test_informe_sast(tmp_path, monkeypatch):
    datos = {"titulo": "SAST — mi-app", "proyecto": {"ruta": "/x"}, "escaneres": ["secretos (integrado)"],
             "veredicto": "1 secreto expuesto", "veredicto_tono": "bad",
             "secretos": [{"tipo": "Clave de acceso AWS", "archivo": ".env", "linea": 3, "severidad": "Alta", "estado": "confirmado"}],
             "hallazgos": [{"id": "H-01", "severidad": "Alta", "categoria": "Inyección SQL", "archivo": "db.js", "linea": 42,
                            "texto": "consulta concatenada", "recomendacion": "parametrizar"}]}
    html = _gen(gis, tmp_path, datos, monkeypatch)
    assert "SAST — mi-app" in html and "Clave de acceso AWS" in html and "Inyección SQL" in html
    assert "rotá las credenciales" in html  # banner de secretos


def test_json_invalido_falla(tmp_path):
    (tmp_path / "x.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        gid.generar(tmp_path / "x.json", tmp_path / "i.html")

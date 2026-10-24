"""Actualización programada de la base de conocimiento (scripts/actualizar_conocimiento.py), sin gastar tokens."""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import actualizar_conocimiento as ac  # noqa: E402


class Resultado:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


def test_app_se_saltea_sin_url_y_resume_cambios(tmp_path):
    assert ac.actualizar_app({})["estado"] == "salteado"
    mapa = tmp_path / "mapa.json"
    mapa.write_text(json.dumps({"paginas": [{}, {}], "con_sesion": "sesion.json", "cambios": {
        "hay": True, "nuevas": ["/nuevo"], "quitadas": [], "paginas": [{"ruta": "/alta"}]}}), encoding="utf-8")
    r = ac.resumen_mapa(mapa)
    assert r["hay"] and r["cambios"] == {"nuevas": ["/nuevo"], "quitadas": [], "con_cambios": ["/alta"]} and r["con_sesion"]
    mapa.write_text(json.dumps({"paginas": []}), encoding="utf-8")
    assert ac.resumen_mapa(mapa)["cambios"] is None


def test_codigo_compara_contra_la_punta_remota(tmp_path, monkeypatch):
    monkeypatch.setattr(ac, "DOC", tmp_path)
    assert ac.actualizar_codigo({})["estado"] == "salteado"
    (tmp_path / ".estado.json").write_text(json.dumps({"repositorios": {"org/app": {"commit": "abc", "rama": "main"}}}), encoding="utf-8")
    llamadas = []

    def correr(cmd, **kw):
        llamadas.append(cmd)
        if cmd[0] == "git":
            return Resultado()
        return Resultado(json.dumps({"cantidad_archivos": 3, "documentos": {"proyecto/reglas.md": ["src/a.ts"]},
                                     "historias": ["PROJ-12"], "casos": [{"archivo": "casos-HU-001.md"}]}))

    r = ac.actualizar_codigo({"REPO_RUTA_LOCAL": str(tmp_path)}, correr)
    assert llamadas[0][:4] == ["git", "-C", str(tmp_path), "fetch"]
    assert "--hasta" in llamadas[1] and llamadas[1][llamadas[1].index("--hasta") + 1] == "origin/main" and "--marcar" in llamadas[1]
    assert r == {"estado": "ok", "archivos": 3, "documentos": ["proyecto/reglas.md"], "historias": ["PROJ-12"],
                 "casos": ["casos-HU-001.md"], "hay": True}


def test_agente_headless_con_tope_y_solo_lectura_del_pedido(monkeypatch, tmp_path):
    cmd = ac.comando_agente("claude", 3)
    assert cmd[:2] == ["claude", "-p"] and cmd[cmd.index("--max-budget-usd") + 1] == "3"
    assert "mcp__atlassian" in cmd[cmd.index("--allowedTools") + 1] and "Solo lectura" in cmd[2]
    monkeypatch.setattr(ac, "DOC", tmp_path)
    monkeypatch.setattr(ac.shutil, "which", lambda x: "claude")
    (tmp_path / "cambios-historias.md").write_text("2 nueva(s), 1 con cambios en el requerimiento", encoding="utf-8")
    monkeypatch.setattr(ac, "PROYECTO", tmp_path.parent)
    r = ac.actualizar_historias(3, lambda *a, **k: Resultado(json.dumps({"result": "2 nuevas, 1 cambiada", "total_cost_usd": 0.42})))
    assert r["estado"] == "ok" and r["hay"] and r["costo_usd"] == 0.42
    r = ac.actualizar_historias(3, lambda *a, **k: Resultado(json.dumps({"is_error": True, "result": "sin conector"}), 1))
    assert r["estado"] == "error" and "sin conector" in r["motivo"]


def test_resumen_y_cuando_avisar():
    app = {"estado": "ok", "paginas": 40, "con_sesion": True, "hay": True,
           "cambios": {"nuevas": ["/x"], "quitadas": [], "con_cambios": ["/alta"]}}
    codigo = {"estado": "salteado", "motivo": "no hay REPO_RUTA_LOCAL"}
    texto = ac.armar_resumen(app, codigo, None)
    assert "40 página(s) con sesión: 1 nueva(s), 0 que ya no están, 1 con cambios." in texto
    assert "salteado: no hay REPO_RUTA_LOCAL" in texto and "corré con --con-agente" in texto
    assert ac.hubo_cambios(app, codigo, None)
    assert not ac.hubo_cambios({"estado": "ok", "hay": False}, codigo, {"estado": "ok", "hay": False})
    assert ac.hubo_cambios({"estado": "error"}, codigo, None)  # un error también se avisa


def test_programar(monkeypatch):
    linea = ac.linea_programada("lunes", "8:05", True)
    if sys.platform == "win32":
        assert linea[:4] == ["schtasks", "/Create", "/F", "/TN"] and "/D" in linea and "08:05" in linea
        assert "--con-agente" in linea[-1] and "actualizar-conocimiento" in linea[-1]
    else:
        assert linea.startswith("5 8 * * 1 ") and "--con-agente" in linea

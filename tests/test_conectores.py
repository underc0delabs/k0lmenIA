"""Conectores MCP: Claude Code tiene que arrancar sin pedir aprobaciones, y los opcionales del
catálogo (npm run conector) tienen que apuntar a scripts y versiones que existen."""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _json(ruta):
    return json.loads((RAIZ / ruta).read_text(encoding="utf-8"))


def test_todo_lo_de_mcp_json_viene_habilitado():
    # Un server de .mcp.json que no está en enabledMcpjsonServers dispara el aviso de aprobación al iniciar.
    servidores = set(_json(".mcp.json")["mcpServers"])
    habilitados = set(_json(".claude/settings.json")["enabledMcpjsonServers"])
    assert servidores == habilitados


def test_catalogo_apunta_a_scripts_y_versiones_existentes():
    catalogo = _json("scripts/mcp/catalogo.json")["conectores"]
    versiones = set(re.findall(r"'([@\w/.-]+)':\s*'[\d.]+'", (RAIZ / "scripts/mcp/lanzar.js").read_text(encoding="utf-8")))
    assert not set(catalogo) & set(_json(".mcp.json")["mcpServers"]), "un conector no puede estar en los dos lados"
    for nombre, c in catalogo.items():
        s = c["servidor"]
        texto = json.dumps(s)
        assert "@latest" not in texto, nombre
        for script in re.findall(r"scripts/mcp/[\w.-]+\.js", texto):
            assert (RAIZ / script).exists(), f"{nombre}: no existe {script}"
        if "--" in s.get("args", []):  # con-env.js ... -- <paquete>
            paquete = s["args"][s["args"].index("--") + 1]
            assert paquete in versiones, f"{nombre}: {paquete} no tiene versión fija en lanzar.js"

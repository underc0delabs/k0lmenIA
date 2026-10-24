"""k0lmenIA como plugin de Claude Code: el armado (scripts/construir_plugin.py) y el comando k0lmenia (bin/), que
deja los datos en el proyecto del QA y el código en el plugin."""
import json
import os
import subprocess
import sys
from pathlib import Path

import construir_plugin as cp

RAIZ = Path(__file__).resolve().parents[1]


def test_transformar_comandos_y_rutas():
    texto = ("Corré `python scripts/generar_casos.py casos.json` y después `npm run portal -- --abrir`; para la suite, "
             "`npm test`. Seguí plantillas/plantilla-reporte-bug.md y herramientas/seo/seo.py. Las pruebas van en "
             "herramientas/k0lmena/web/features/. Escalas de CLAUDE.md. Detalle en REFERENCIA.md.")
    t = cp.transformar(texto)
    assert "`k0lmenia py scripts/generar_casos.py casos.json`" in t
    assert "`k0lmenia portal -- --abrir`" in t and "`k0lmenia test`" in t
    assert "${CLAUDE_PLUGIN_ROOT}/plantillas/plantilla-reporte-bug.md" in t
    assert "${CLAUDE_PLUGIN_ROOT}/herramientas/seo/seo.py" in t
    assert " herramientas/k0lmena/web/features/" in t  # k0lmena vive en el proyecto, no en el plugin
    assert "k0lmenia:estandares" in t and "CLAUDE.md" not in t
    assert "${CLAUDE_PLUGIN_ROOT}/REFERENCIA.md" in t
    assert cp.transformar(t) == t  # idempotente: no duplica prefijos


def test_armar_el_plugin(tmp_path):
    destino = cp.construir(tmp_path / "plugin")
    manifiesto = json.loads((destino / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    catalogo = json.loads((destino / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert manifiesto["name"] == "k0lmenia" and "version" not in manifiesto  # sin versión: cada commit es una versión
    assert catalogo["plugins"][0] == {**catalogo["plugins"][0], "name": "k0lmenia", "source": "./"}
    agentes = list((destino / "agents").glob("*.md"))
    assert len(agentes) == len(list((RAIZ / ".claude" / "agents").glob("*.md")))
    assert (destino / "skills" / "estandares" / "SKILL.md").exists()
    sin_transformar = [a.name for a in agentes if "python scripts/" in a.read_text(encoding="utf-8")
                       or "npm run " in a.read_text(encoding="utf-8")]
    assert not sin_transformar, f"agentes con comandos del repo: {sin_transformar}"
    hooks = json.loads((destino / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert "preparar" in hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    mcp = json.loads((destino / ".mcp.json").read_text(encoding="utf-8"))
    assert "${CLAUDE_PLUGIN_ROOT}" in mcp["mcpServers"]["playwright"]["args"][0]
    assert (destino / "bin" / "k0lmenia").exists() and (destino / "scripts" / "_i18n.py").exists()
    assert not any(destino.rglob("node_modules")) and not any(destino.rglob("__pycache__"))
    assert not (destino / "scripts" / "construir_plugin.py").exists()
    # Volver a armar sobre la misma carpeta la limpia (lo que hace la publicación en la rama plugin).
    (destino / "agents" / "viejo.md").write_text("x", encoding="utf-8")
    cp.construir(destino)
    assert not (destino / "agents" / "viejo.md").exists()


def _k0lmenia(plugin, proyecto, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("K0LMENIA_PROYECTO", "K0LMENIA_CODIGO")}
    return subprocess.run(["node", str(plugin / "bin" / "k0lmenia"), *args], cwd=proyecto, env=env,
                          capture_output=True, text=True, encoding="utf-8")


def test_init_y_comandos_en_el_proyecto_del_qa(tmp_path):
    plugin = cp.construir(tmp_path / "plugin")
    proyecto = tmp_path / "mi-proyecto"
    proyecto.mkdir()
    r = _k0lmenia(plugin, proyecto, "init", "--sin-npm")
    assert r.returncode == 0, r.stderr
    assert (proyecto / ".env").exists() and (proyecto / "output" / "reportes-bug").is_dir()
    assert (proyecto / "herramientas" / "k0lmena" / "package.json").exists()
    assert ".auth/" in (proyecto / ".gitignore").read_text(encoding="utf-8")
    # Las pruebas del QA no se pisan al volver a correr init.
    mia = proyecto / "herramientas" / "k0lmena" / "web" / "features" / "HU-001-mia.feature"
    mia.parent.mkdir(parents=True, exist_ok=True)
    mia.write_text("Feature: mía", encoding="utf-8")
    (proyecto / ".env").write_text("APP_URL=https://mi-app.test\n", encoding="utf-8")
    assert _k0lmenia(plugin, proyecto, "init", "--sin-npm").returncode == 0
    assert mia.read_text(encoding="utf-8") == "Feature: mía"
    assert (proyecto / ".env").read_text(encoding="utf-8") == "APP_URL=https://mi-app.test\n"
    # Un informe y el portal quedan en el proyecto, no en el plugin.
    analisis = proyecto / "output" / "contratos" / "HU-010" / "analisis.json"
    analisis.parent.mkdir(parents=True)
    analisis.write_text(json.dumps({"titulo": "Contratos — HU-010", "veredicto": "Apto"}), encoding="utf-8")
    r = _k0lmenia(plugin, proyecto, "py", "scripts/generar_informe_generico.py", str(analisis), "output/contratos/HU-010/informe.html")
    assert r.returncode == 0, r.stderr
    assert (proyecto / "output" / "contratos" / "HU-010" / "es" / "informe.html").exists()
    r = _k0lmenia(plugin, proyecto, "portal")
    assert r.returncode == 0, r.stderr
    assert (proyecto / "output" / "es" / "index.html").exists()
    assert not any((plugin / "output").rglob("*.html")), "el plugin no guarda informes"
    r = _k0lmenia(plugin, proyecto, "no-existe")
    assert r.returncode == 2 and "no conozco" in r.stderr


def test_ayuda_lista_los_comandos(tmp_path):
    r = _k0lmenia(RAIZ, tmp_path, "ayuda")
    assert r.returncode == 0 and "k0lmenia init" in r.stdout and "portal" in r.stdout


def test_tarea_programada_como_plugin_usa_un_lanzador_estable(tmp_path, monkeypatch):
    """Como plugin, la carpeta del código cambia en cada versión: la tarea apunta a un lanzador del proyecto."""
    import actualizar_conocimiento as ac
    monkeypatch.setattr(ac, "PROYECTO", tmp_path)
    monkeypatch.setenv("K0LMENIA_CODIGO", str(tmp_path / "cache" / "k0lmenia" / "abc123"))
    linea = ac.linea_programada("lunes", "08:00", False)
    texto = " ".join(linea) if isinstance(linea, list) else linea
    lanzador = tmp_path / ".k0lmenia" / "lanzador.js"
    assert lanzador.exists() and "actualizar-conocimiento" in texto and str(lanzador) in texto
    assert "npm run" not in texto and "abc123" not in texto
    monkeypatch.delenv("K0LMENIA_CODIGO")
    texto = ac.linea_programada("lunes", "08:00", False)
    assert "npm run actualizar-conocimiento" in (" ".join(texto) if isinstance(texto, list) else texto)

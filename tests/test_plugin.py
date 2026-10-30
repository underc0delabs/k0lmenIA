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
             "`npm test`. Seguí plantillas/plantilla-reporte-bug.md y herramientas/newman/README.md. Las pruebas van en "
             "herramientas/k0lmena/web/features/. Escalas de CLAUDE.md. Detalle en REFERENCIA.md.")
    t = cp.transformar(texto)
    assert "`k0lmenia py scripts/generar_casos.py casos.json`" in t
    assert "`k0lmenia portal -- --abrir`" in t and "`k0lmenia test`" in t
    assert "${CLAUDE_PLUGIN_ROOT}/plantillas/plantilla-reporte-bug.md" in t
    assert "${CLAUDE_PLUGIN_ROOT}/herramientas/newman/README.md" in t
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
    assert "Hacé las tareas de TAREAS.md" in (proyecto / "TAREAS.md").read_text(encoding="utf-8")
    # Las pruebas del QA no se pisan al volver a correr init.
    mia = proyecto / "herramientas" / "k0lmena" / "web" / "features" / "HU-001-mia.feature"
    mia.parent.mkdir(parents=True, exist_ok=True)
    mia.write_text("Feature: mía", encoding="utf-8")
    (proyecto / ".env").write_text("APP_URL=https://mi-app.test\n", encoding="utf-8")
    assert _k0lmenia(plugin, proyecto, "init", "--sin-npm").returncode == 0
    assert mia.read_text(encoding="utf-8") == "Feature: mía"
    assert (proyecto / ".env").read_text(encoding="utf-8") == "APP_URL=https://mi-app.test\n"
    # Un informe y el portal quedan en el proyecto, no en el plugin.
    resultados = proyecto / "output" / "ejecuciones" / "_resultados-HU-010.json"
    resultados.parent.mkdir(parents=True, exist_ok=True)
    resultados.write_text(json.dumps({"titulo": "Corrida HU-010", "historia": "HU-010",
                                      "casos": [{"id": "CP-001", "titulo": "Alta", "estado": "Aprobado"}]}), encoding="utf-8")
    r = _k0lmenia(plugin, proyecto, "py", "scripts/generar_reporte.py", str(resultados), "output/ejecuciones/reporte-HU-010.html")
    assert r.returncode == 0, r.stderr
    assert (proyecto / "output" / "ejecuciones" / "es" / "reporte-HU-010.html").exists()
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


def test_actualizar_k0lmena_sin_perder_cambios(tmp_path):
    """Una versión nueva del plugin trae mejoras del framework: llegan, pero las pruebas del QA y los archivos del
    framework que el QA modificó no se pisan (la versión nueva queda al lado como .nuevo)."""
    plugin = cp.construir(tmp_path / "plugin")
    proyecto = tmp_path / "proyecto"
    proyecto.mkdir()
    assert _k0lmenia(plugin, proyecto, "init", "--sin-npm").returncode == 0
    k0 = proyecto / "herramientas" / "k0lmena"
    assert json.loads((k0 / ".k0lmenia.json").read_text(encoding="utf-8"))["version"]
    # El QA escribe sus pruebas y retoca un archivo del framework.
    feature = k0 / "web" / "features" / "HU-001-login.feature"
    feature.write_text("Feature: login del QA", encoding="utf-8")
    retocado = k0 / "web" / "utils" / "keys.ts"
    retocado.write_text(retocado.read_text(encoding="utf-8") + "\n// ajuste del QA\n", encoding="utf-8")
    # Sale una versión nueva del plugin: mejora un archivo que el QA no tocó, el que retocó y suma uno nuevo.
    pk0 = plugin / "herramientas" / "k0lmena"
    intacto = "web/utils/validations.ts"
    (pk0 / intacto).write_text((pk0 / intacto).read_text(encoding="utf-8") + "\n// mejora 2.0\n", encoding="utf-8")
    (pk0 / "web" / "utils" / "keys.ts").write_text("// keys 2.0\n", encoding="utf-8")
    (pk0 / "web" / "utils" / "nuevo.ts").write_text("// nuevo en 2.0\n", encoding="utf-8")
    (pk0 / "web" / "features" / "HU-001-login.feature").write_text("Feature: del plugin", encoding="utf-8")
    # Al iniciar la sesión, el contexto avisa que hay versión nueva.
    aviso = _k0lmenia(plugin, proyecto, "preparar", "--contexto").stdout
    assert "k0lmenia actualizar" in aviso
    r = _k0lmenia(plugin, proyecto, "actualizar", "--sin-npm")
    assert r.returncode == 0, r.stderr
    assert (k0 / intacto).read_text(encoding="utf-8").endswith("// mejora 2.0\n")       # la mejora llegó
    assert (k0 / "web" / "utils" / "nuevo.ts").exists()                                  # lo nuevo también
    assert "// ajuste del QA" in retocado.read_text(encoding="utf-8")                    # lo retocado se respeta
    assert (k0 / "web" / "utils" / "keys.ts.nuevo").read_text(encoding="utf-8") == "// keys 2.0\n"
    assert feature.read_text(encoding="utf-8") == "Feature: login del QA"                # sus pruebas, intactas
    assert "keys.ts" in r.stdout and ".nuevo" in r.stdout
    assert "k0lmenia actualizar" not in _k0lmenia(plugin, proyecto, "preparar", "--contexto").stdout  # ya al día


def test_marketplace_de_main_apunta_a_la_rama_plugin():
    """`claude plugin marketplace add underc0delabs/k0lmenIA` (sin #plugin) lee este catálogo, que trae el plugin de la rama."""
    m = json.loads((RAIZ / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    entrada = m["plugins"][0]
    assert m["name"] == entrada["name"] == "k0lmenia" and m.get("description")
    assert entrada["source"] == {"source": "github", "repo": cp.REPO, "ref": "plugin"}
    assert entrada["description"] == cp.DESCRIPCION  # un solo lugar para la descripción


def test_icono_privacidad_y_bienvenida(tmp_path):
    import struct
    destino = cp.construir(tmp_path / "plugin")
    png = (destino / ".claude-plugin" / "icon.png").read_bytes()
    ancho, alto = struct.unpack(">II", png[16:24])  # encabezado IHDR del PNG
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and ancho == alto >= 512 and len(png) < 2_000_000
    manifiesto = json.loads((destino / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifiesto["privacyPolicyUrl"].startswith("https://")
    assert (destino / "skills" / "empezar" / "SKILL.md").exists()
    assert "/k0lmenia:empezar" in (destino / "README.md").read_text(encoding="utf-8")
    assert "#plugin" not in (destino / "README.md").read_text(encoding="utf-8").split("## Actualizar")[0].split("(Si lo")[0]
    # Primer uso: en una carpeta sin preparar, el contexto de inicio sugiere /k0lmenia:empezar; ya preparada, no.
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    r = _k0lmenia(destino, vacio, "preparar", "--contexto")
    assert "todavía no está preparada" in r.stdout and "/k0lmenia:empezar" in r.stdout
    (vacio / ".env").write_text("", encoding="utf-8")
    assert "todavía no está preparada" not in _k0lmenia(destino, vacio, "preparar", "--contexto").stdout


def test_permisos_iguales_al_repo_con_los_comandos_del_plugin():
    p = cp.permisos()
    assert "mcp__plugin_k0lmenia_playwright__*" in p["allow"]
    assert "mcp__plugin_k0lmenia_playwright__browser_run_code_unsafe" in p["ask"]  # lo que el repo pregunta, se sigue preguntando
    assert "Bash(k0lmenia py scripts/generar_casos.py:*)" in p["allow"] and "Bash(k0lmenia portal:*)" in p["allow"]
    assert not [r for r in p["allow"] if "npm run" in r or "python scripts/" in r or "py.js" in r]
    assert "Bash(k0lmenia:*)" not in p["allow"]  # nada más amplio que en el repo clonado


def test_init_copia_ejemplos_y_suma_permisos_sin_pisar(tmp_path):
    plugin = cp.construir(tmp_path / "plugin")
    proyecto = tmp_path / "proyecto"
    (proyecto / ".claude").mkdir(parents=True)
    (proyecto / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Bash(git status)"]}, "model": "opus"}),
                                                        encoding="utf-8")
    (proyecto / "input" / "chatbots").mkdir(parents=True)
    (proyecto / "input" / "chatbots" / "guion.ejemplo.json").write_text("mio", encoding="utf-8")
    assert _k0lmenia(plugin, proyecto, "init", "--sin-npm").returncode == 0
    versionados = subprocess.run(["git", "ls-files", "input"], cwd=RAIZ, capture_output=True, text=True).stdout.splitlines()
    assert (proyecto / "input" / "README.md").exists() and (proyecto / "input" / "api" / "demo.postman_collection.json").exists()
    assert len([v for v in versionados if not v.endswith(".gitkeep")]) == len([p for p in (proyecto / "input").rglob("*") if p.is_file() and p.name != ".gitkeep"])
    assert (proyecto / "input" / "chatbots" / "guion.ejemplo.json").read_text(encoding="utf-8") == "mio"  # no pisa lo tuyo
    ajustes = json.loads((proyecto / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert ajustes["model"] == "opus" and ajustes["permissions"]["allow"][0] == "Bash(git status)"
    assert "mcp__plugin_k0lmenia_playwright__*" in ajustes["permissions"]["allow"]
    antes = (proyecto / ".claude" / "settings.json").read_text(encoding="utf-8")
    _k0lmenia(plugin, proyecto, "init", "--sin-npm")
    assert (proyecto / ".claude" / "settings.json").read_text(encoding="utf-8") == antes  # idempotente

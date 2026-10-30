#!/usr/bin/env python3
"""
Arma k0lmenIA como plugin de Claude Code (y su marketplace) a partir del repo, sin cambiar el repo.

Uso (desde la raíz del repo):
    python scripts/construir_plugin.py [--destino dist/plugin]

El resultado es una carpeta lista para publicar (la publica el workflow plugin.yml en la rama `plugin`):

    .claude-plugin/marketplace.json   el catálogo de la rama (para quien instaló con underc0delabs/k0lmenIA#plugin); el de
                                      siempre es .claude-plugin/marketplace.json de main, que apunta a esta rama
    .claude-plugin/plugin.json        el plugin "k0lmenia" (sin versión fija: cada publicación es una versión)
    .claude-plugin/icon.png           el ícono (el de main)
    agents/ skills/                   los de .claude/, con los comandos pasados al plugin (ver más abajo)
    skills/estandares/                los estándares de CLAUDE.md (un plugin no carga CLAUDE.md)
    hooks/hooks.json                  al iniciar la sesión: dependencias de Python y el contexto de k0lmenIA
    .mcp.json                         los conectores de siempre (Playwright y Atlassian), desde el plugin
    bin/k0lmenia                      el comando que reemplaza a npm run y python scripts/… (queda en el PATH)
    hooks/permisos.json               los permisos de .claude/settings.json del repo, con los comandos del plugin
                                      (k0lmenia init los suma al .claude/settings.json del proyecto)
    scripts/ herramientas/ plantillas/ input/ output/ .env.example package.json requirements.txt
                                      el código; input/ con los ejemplos versionados (k0lmenia init los copia sin pisar
                                      nada) y output/ solo con la estructura de carpetas

Qué cambia en el texto de agentes y skills (el repo no se toca; esto vale solo para el plugin):
    npm run <x> / npm test            ->  k0lmenia <x> / k0lmenia test
    python scripts/<x>.py             ->  k0lmenia py scripts/<x>.py
    plantillas/, scripts/, herramientas/ (código)  ->  ${CLAUDE_PLUGIN_ROOT}/…   (herramientas/k0lmena/ no: vive en
                                                                                   el proyecto, con las pruebas)
    CLAUDE.md                         ->  el skill estandares
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
NOMBRE = "k0lmenia"
REPO = "underc0delabs/k0lmenIA"

# Lo que no viaja en el plugin: dependencias instaladas, corridas, cachés y lo que es solo del repo de desarrollo.
IGNORAR = shutil.ignore_patterns("node_modules", "__pycache__", "*.pyc", "reports", "historial", ".deps", ".cache",
                                 "construir_plugin.py", ".pytest_cache")
CODIGO = ["scripts", "herramientas", "plantillas", "bin"]
ARCHIVOS = [".env.example", "package.json", "requirements.txt", "LICENSE", "SECURITY.md", "AGENTES.md", "REFERENCIA.md",
            "CHANGELOG.md",  # para las novedades al actualizar (scripts/novedades.py)
            "CONECTORES.md"]

# La descripción es la del marketplace de main (.claude-plugin/marketplace.json): un solo lugar para mantenerla.
MARKETPLACE_MAIN = RAIZ / ".claude-plugin" / "marketplace.json"
DESCRIPCION = json.loads(MARKETPLACE_MAIN.read_text(encoding="utf-8"))["plugins"][0]["description"]
PRIVACIDAD = "https://k0lmena.com/k0lmenia/privacidad/"


# ------------------------------------------------------------------ transformación del texto
_PY = re.compile(r"\bpython3? ((?:scripts|herramientas)/[\w./-]+\.py)")
_NPM = re.compile(r"\bnpm run ([\w:-]+)")
_NPM_TEST = re.compile(r"\bnpm test\b")
_CODIGO = re.compile(r"(?<![\w./${}-])(?<!py )((?:plantillas|scripts|herramientas)/)(?!k0lmena\b)")
_RESERVA = "\x00K0PY\x00"


def transformar(texto):
    """El texto de un agente o skill, con los comandos y rutas del repo pasados al plugin."""
    guardados = []

    def guardar(m):
        guardados.append(f"k0lmenia py {m.group(1)}")
        return f"{_RESERVA}{len(guardados) - 1}{_RESERVA}"

    t = _PY.sub(guardar, texto)
    t = _NPM.sub(lambda m: f"k0lmenia {m.group(1)}", t)
    t = _NPM_TEST.sub("k0lmenia test", t)
    t = _CODIGO.sub(lambda m: "${CLAUDE_PLUGIN_ROOT}/" + m.group(1), t)
    t = re.sub(r"`?\bCLAUDE\.md\b`?", f"el skill `{NOMBRE}:estandares`", t)
    t = re.sub(r"(?<![/\w])(REFERENCIA|AGENTES)\.md", r"${CLAUDE_PLUGIN_ROOT}/\1.md", t)
    return re.sub(re.escape(_RESERVA) + r"(\d+)" + re.escape(_RESERVA), lambda m: guardados[int(m.group(1))], t)


# ------------------------------------------------------------------ piezas del plugin
def estandares():
    """CLAUDE.md como skill: el plugin no lo carga como contexto del proyecto."""
    texto = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
    cuerpo = transformar(texto.split("\n", 1)[1] if texto.startswith("# ") else texto)
    return ("---\nname: estandares\ndescription: Estándares de QA de k0lmenIA (no inventar, Falta información FI-XX, escalas, "
            "IDs, tablas, informes en español e inglés, qué se confirma con la persona). Cargalo al empezar cualquier tarea "
            "de QA con k0lmenIA y cuando un agente lo nombre.\n---\n\n# Estándares de k0lmenIA\n" + cuerpo)


CONTEXTO_INICIO = """k0lmenIA está activo (plugin de Claude Code): agentes de QA en español, llamados `k0lmenia:<agente>` (por ejemplo `k0lmenia:triador-bugs`).
- Antes de una tarea de QA cargá el skill `k0lmenia:estandares`: no inventar, Falta información FI-XX, escalas, qué se confirma con la persona e informes en español e inglés.
- Delegá en el agente que corresponde y pasale solo el pedido y los datos. No le indiques carpetas ni formatos de salida: cada agente ya sabe dónde guarda lo suyo (output/reportes-bug/, output/casos-de-prueba/, output/analisis-historias/…), y esas carpetas son las que indexa el portal.
- Los comandos de k0lmenIA se corren con `k0lmenia <comando>` desde esta carpeta, sin `cd` (`k0lmenia ayuda` los lista). Los datos del proyecto (input/, output/, .env y herramientas/k0lmena con las pruebas automatizadas) viven acá; si no existen, sugerí `/k0lmenia:empezar` (o `k0lmenia init`)."""


def hooks():
    return {"hooks": {"SessionStart": [{"hooks": [{"type": "command",
                                                   "command": 'node "${CLAUDE_PLUGIN_ROOT}/bin/k0lmenia" preparar --contexto'}]}]}}


def mcp():
    lanzador = "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/playwright.js"
    return {"mcpServers": {
        "playwright": {"type": "stdio", "command": "node", "args": [lanzador]},
        "playwright-headless": {"type": "stdio", "command": "node", "args": [lanzador, "--headless"]},
        "atlassian": {"type": "http", "url": "https://mcp.atlassian.com/v2/mcp",
                      "headersHelper": 'node "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/atlassian-headers.js"'},
    }}


def manifiesto():
    return {"name": NOMBRE, "description": DESCRIPCION, "author": {"name": "Underc0de"},
            "homepage": "https://underc0delabs.github.io/k0lmenIA/", "repository": f"https://github.com/{REPO}",
            "privacyPolicyUrl": PRIVACIDAD, "license": "MIT", "keywords": ["qa", "testing", "español", "playwright", "xray", "bdd", "k0lmena"]}


def marketplace():
    return {"name": NOMBRE, "owner": {"name": "Underc0de"},
            "description": json.loads(MARKETPLACE_MAIN.read_text(encoding="utf-8"))["description"],
            "plugins": [{"name": NOMBRE, "source": "./", "description": DESCRIPCION}]}


LEEME = f"""# k0lmenIA — plugin de Claude Code

Agentes de QA en español para Claude Code. Esta rama (`plugin`) la arma sola el repo
[{REPO}](https://github.com/{REPO}) en cada cambio: no se edita a mano.

## Instalar

Desde una terminal (una sola vez por persona):

```
claude plugin marketplace add {REPO}
claude plugin install {NOMBRE}@{NOMBRE}
```

O adentro de Claude Code: `/plugin marketplace add {REPO}` y `/plugin install {NOMBRE}@{NOMBRE}`.

Después abrí Claude Code en la carpeta de tu proyecto y escribí **`/{NOMBRE}:empezar`**: prepara el proyecto, revisa
que esté todo instalado, te ayuda a conectar tus herramientas y te sugiere por dónde arrancar.

(Si lo instalaste antes con `{REPO}#plugin`, sigue funcionando igual.)

## Qué instala y dónde

El código (agentes, skills, scripts y herramientas) queda en la caché de Claude Code. En tu proyecto, `k0lmenia init` (o
`/{NOMBRE}:empezar`) deja lo tuyo: `input/` con los mismos ejemplos que el repo, `output/` con los informes y el portal, el
`.env`, `TAREAS.md`, tu copia de k0lmena y, en `.claude/settings.json`, los mismos permisos que el repo clonado. Nunca pisa
un archivo que ya existe. Es lo mismo que clonar el repo; solo no viajan la web y el PDF (están online), los tests del repo
y los evals de los agentes.

## Actualizar

Cada cambio en el repo se publica solo en esta rama. Para recibirlo:

- **Automático** (recomendado): `/plugin` → Marketplaces → `{NOMBRE}` → *Enable auto-update*. Una sola vez por persona.
- **A mano**: `/plugin marketplace update {NOMBRE}`.

Eso actualiza agentes, skills, scripts y herramientas. El framework de automatización (`herramientas/k0lmena/` de tu
proyecto) se actualiza con `k0lmenia actualizar`; Claude te avisa al iniciar la sesión cuando hay una versión nueva.
Tus pruebas (features, steps, locators) no se tocan, y si modificaste un archivo del framework, la versión nueva queda
al lado como `.nuevo` para que la compares. Tus datos (`input/`, `output/`, `.env`) viven en tu proyecto y no se tocan.

Para todo el equipo, en el `.claude/settings.json` del proyecto:

```json
{{
  "extraKnownMarketplaces": {{"{NOMBRE}": {{"source": {{"source": "github", "repo": "{REPO}"}}}}}},
  "enabledPlugins": {{"{NOMBRE}@{NOMBRE}": true}}
}}
```

Cada persona lo instala una vez con `claude plugin install {NOMBRE}@{NOMBRE} --scope project`.
"""


# ------------------------------------------------------------------ armado
def _limpiar(destino):
    if destino.exists():
        if any(destino.iterdir()) and not (destino / ".claude-plugin" / "plugin.json").exists():
            sys.exit(f"{destino} no está vacía y no es un plugin armado antes: elegí otra --destino.")
        for hijo in destino.iterdir():
            if hijo.name == ".git":  # la publicación usa la carpeta como copia de trabajo de la rama plugin
                continue
            shutil.rmtree(hijo) if hijo.is_dir() else hijo.unlink()
    destino.mkdir(parents=True, exist_ok=True)


def _estructura(origen, destino):
    """Solo las carpetas y sus .gitkeep (input/ y output/ para k0lmenia init)."""
    for d in [origen, *sorted(p for p in origen.rglob("*") if p.is_dir())]:
        rel = d.relative_to(origen)
        (destino / rel).mkdir(parents=True, exist_ok=True)
        (destino / rel / ".gitkeep").write_text("", encoding="utf-8")


def _versionados(carpeta):
    """Los archivos de la carpeta que están en git (los ejemplos de input/). Nunca lo que alguien dejó en su copia local
    (documentación del proyecto, logs, historias propias): eso no viaja en el plugin."""
    try:
        r = subprocess.run(["git", "-C", str(RAIZ), "ls-files", "-z", "--", carpeta], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    return [RAIZ / x for x in r.stdout.decode("utf-8").split("\0") if x]


def _ejemplos(origen, destino):
    """input/: la estructura de carpetas y los ejemplos versionados (README, colecciones de demo, guiones, planes…)."""
    _estructura(origen, destino)
    for archivo in _versionados(origen.name):
        if archivo.is_file() and archivo.name != ".gitkeep":
            dst = destino / archivo.relative_to(origen)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(archivo, dst)


def permisos():
    """Los permisos del repo (.claude/settings.json) con los comandos y los conectores del plugin, para que trabajar con el
    plugin pida las mismas confirmaciones que el repo clonado: ni más ni menos."""
    p = json.loads((RAIZ / ".claude" / "settings.json").read_text(encoding="utf-8")).get("permissions") or {}

    def regla(r):
        r = re.sub(r"^mcp__(playwright(?:-headless)?)__", rf"mcp__plugin_{NOMBRE}_\1__", r)
        m = re.match(r"^Bash\((.*)\)$", r)
        if not m:
            return r
        cmd = m.group(1)
        cmd = re.sub(r"^node scripts/py\.js ", "python ", cmd)
        cmd = re.sub(r"^python3? ((?:scripts|herramientas)/)", r"k0lmenia py \1", cmd)
        cmd = re.sub(r"^npm run ", "k0lmenia ", cmd)
        cmd = re.sub(r"^npm test", "k0lmenia test", cmd)
        return f"Bash({cmd})"

    salida = {}
    for clave in ("allow", "ask", "deny"):
        reglas = list(dict.fromkeys(regla(r) for r in p.get(clave) or []))
        if reglas:
            salida[clave] = reglas
    return salida


def _escribir_json(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def construir(destino):
    destino = Path(destino).resolve()
    _limpiar(destino)
    for carpeta in CODIGO:
        shutil.copytree(RAIZ / carpeta, destino / carpeta, ignore=IGNORAR)
    for archivo in ARCHIVOS:
        if (RAIZ / archivo).exists():
            shutil.copy2(RAIZ / archivo, destino / archivo)
    _ejemplos(RAIZ / "input", destino / "input")
    _estructura(RAIZ / "output", destino / "output")
    # Agentes y skills, con los comandos y rutas del plugin.
    for agente in sorted((RAIZ / ".claude" / "agents").glob("*.md")):
        (destino / "agents").mkdir(exist_ok=True)
        (destino / "agents" / agente.name).write_text(transformar(agente.read_text(encoding="utf-8")), encoding="utf-8")
    for skill in sorted(p for p in (RAIZ / ".claude" / "skills").iterdir() if p.is_dir()):
        for archivo in skill.rglob("*"):
            if archivo.is_file():
                dst = destino / "skills" / skill.name / archivo.relative_to(skill)
                dst.parent.mkdir(parents=True, exist_ok=True)
                if archivo.suffix == ".md":
                    dst.write_text(transformar(archivo.read_text(encoding="utf-8")), encoding="utf-8")
                else:
                    shutil.copy2(archivo, dst)
    (destino / "skills" / "estandares").mkdir(parents=True, exist_ok=True)
    (destino / "skills" / "estandares" / "SKILL.md").write_text(estandares(), encoding="utf-8")
    for doc in ("AGENTES.md", "REFERENCIA.md"):
        if (destino / doc).exists():
            (destino / doc).write_text(transformar((destino / doc).read_text(encoding="utf-8")), encoding="utf-8")
    (destino / "hooks").mkdir(exist_ok=True)
    _escribir_json(destino / "hooks" / "hooks.json", hooks())
    (destino / "hooks" / "contexto.md").write_text(CONTEXTO_INICIO + "\n", encoding="utf-8")
    _escribir_json(destino / "hooks" / "permisos.json", permisos())
    _escribir_json(destino / ".mcp.json", mcp())
    _escribir_json(destino / ".claude-plugin" / "plugin.json", manifiesto())
    _escribir_json(destino / ".claude-plugin" / "marketplace.json", marketplace())
    shutil.copy2(RAIZ / ".claude-plugin" / "icon.png", destino / ".claude-plugin" / "icon.png")
    (destino / "README.md").write_text(LEEME, encoding="utf-8")
    (destino / ".gitattributes").write_text("bin/k0lmenia text eol=lf\n*.sh text eol=lf\n", encoding="utf-8")
    return destino


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Arma k0lmenIA como plugin de Claude Code (y su marketplace).")
    ap.add_argument("--destino", default=str(RAIZ / "dist" / "plugin"))
    a = ap.parse_args(argv)
    destino = construir(a.destino)
    agentes = len(list((destino / "agents").glob("*.md")))
    skills = len([p for p in (destino / "skills").iterdir() if p.is_dir()])
    print(f"Plugin armado en {destino}: {agentes} agentes, {skills} skills. Probalo con: claude --plugin-dir \"{destino}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())

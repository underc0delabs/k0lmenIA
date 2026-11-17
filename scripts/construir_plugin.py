#!/usr/bin/env python3
"""
Arma k0lmenIA como plugin de Claude Code a partir del repo, sin cambiar el repo.

Uso (desde la raíz del repo):
    python scripts/construir_plugin.py [--destino dist/plugin]
    python scripts/construir_plugin.py --marketplace-main     reescribe .claude-plugin/marketplace.json

El plugin `k0lmenia` trae todos los agentes y skills de .claude/, el comando k0lmenia (bin/), los conectores de siempre
(Playwright y Atlassian), el skill estandares y el hook de inicio de sesión. El resultado es una carpeta lista para
publicar (la publica el workflow plugin.yml en la rama `plugin`):

    .claude-plugin/plugin.json        el plugin (sin versión fija: cada publicación es una versión)
    .claude-plugin/marketplace.json   el catálogo `k0lmenia`, con el plugin desde "./"
    .claude-plugin/icon.png           el ícono
    agents/ skills/                   los de .claude/, con los comandos pasados al plugin (ver más abajo)
    skills/estandares/                los estándares de CLAUDE.md (un plugin no carga CLAUDE.md)
    hooks/hooks.json, contexto.md     al iniciar la sesión: dependencias y contexto
    hooks/permisos.json               los permisos de .claude/settings.json, con los comandos del plugin
    .mcp.json                         los conectores de siempre (Playwright y Atlassian)
    bin/k0lmenia
    scripts/ herramientas/ plantillas/ input/ output/ .env.example package.json requirements.txt

Qué cambia en el texto de agentes y skills (el repo no se toca; esto vale solo para el plugin):
    npm run <x> / npm test            ->  k0lmenia <x> / k0lmenia test
    python scripts/<x>.py             ->  k0lmenia py scripts/<x>.py
    plantillas/, scripts/, herramientas/ (código)  ->  ${CLAUDE_PLUGIN_ROOT}/…   (herramientas/k0lmena/ no: vive en
                                                                                   el proyecto, con las pruebas)
    CLAUDE.md                         ->  el skill k0lmenia:estandares
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CORE = "k0lmenia"  # el nombre del plugin: el prefijo de sus agentes, skills, conectores y estándares
NOMBRE = CORE
MARKETPLACE = "k0lmenia"
REPO = "underc0delabs/k0lmenIA"  # este repo: el plugin se publica en su rama `plugin`
WEB = "https://underc0delabs.github.io/k0lmenIA/"
DESCRIPCION = ("K0lmenIA: agentes de QA para Claude Code, en español. Documentación del proyecto, análisis de historias, "
               "casos de prueba (Excel y BDD), revisión de casos, triage de bugs, ejecución E2E y de API (REST, GraphQL y "
               "gRPC), ejecución manual guiada, automatización sin tokens con k0lmena, gestión en Xray y k0lmenaTMT, e "
               "informes en español e inglés.")
PRIVACIDAD = "https://k0lmena.com/k0lmenia/privacidad/"
LICENCIA = "MIT"
AGENTES = sorted(p.stem for p in (RAIZ / ".claude" / "agents").glob("*.md"))
SKILLS = sorted(p.parent.name for p in (RAIZ / ".claude" / "skills").glob("*/SKILL.md"))

# Lo que no viaja en el plugin: dependencias instaladas, corridas, cachés y lo que es solo del repo de desarrollo.
IGNORAR = shutil.ignore_patterns("node_modules", "__pycache__", "*.pyc", "reports", "historial", ".deps", ".cache",
                                 "construir_plugin.py", ".pytest_cache")
CODIGO = ["scripts", "herramientas", "plantillas"]
ARCHIVOS = [".env.example", "package.json", "requirements.txt", "LICENSE", "SECURITY.md", "AGENTES.md", "REFERENCIA.md",
            "CHANGELOG.md",  # para las novedades al actualizar (scripts/novedades.py)
            "CONECTORES.md"]


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
    t = re.sub(r"`?\bCLAUDE\.md\b`?", f"el skill `{CORE}:estandares`", t)
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


CONTEXTO = """k0lmenIA está activo (plugin de Claude Code): agentes de QA en español, llamados `k0lmenia:<agente>` (por ejemplo `k0lmenia:triador-bugs`).
- Antes de una tarea de QA cargá el skill `k0lmenia:estandares`: no inventar, Falta información FI-XX, escalas, qué se confirma con la persona e informes en español e inglés.
- Delegá en el agente que corresponde y pasale solo el pedido y los datos. No le indiques carpetas ni formatos de salida: cada agente ya sabe dónde guarda lo suyo (output/reportes-bug/, output/casos-de-prueba/, output/analisis-historias/…), y esas carpetas son las que indexa el portal.
- Los comandos de k0lmenIA se corren con `k0lmenia <comando>` desde esta carpeta, sin `cd` (`k0lmenia ayuda` los lista). Los datos del proyecto (input/, output/, .env y herramientas/k0lmena con las pruebas automatizadas) viven acá; si no existen, sugerí `/k0lmenia:empezar` (o `k0lmenia init`).
- Si la persona pide algo que no hace ningún agente, skill o comando instalado, no lo improvises con otro agente: decile que no está incluido y ofrecé lo que sí se puede hacer."""


def hooks():
    cmd = 'node "${CLAUDE_PLUGIN_ROOT}/bin/k0lmenia" preparar --contexto'
    return {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": cmd}]}]}}


def contexto():
    return CONTEXTO


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
            "homepage": WEB, "repository": f"https://github.com/{REPO}",
            "privacyPolicyUrl": PRIVACIDAD, "license": LICENCIA,
            "keywords": ["qa", "testing", "español", "playwright", "xray", "bdd", "k0lmena"]}


def marketplace(desde_rama):
    """El catálogo `k0lmenia`. En la rama plugin, el plugin va desde "./"; en main, apunta a la rama plugin."""
    fuente = "./" if desde_rama else {"source": "github", "repo": REPO, "ref": "plugin"}
    return {"name": MARKETPLACE, "owner": {"name": "Underc0de"},
            "description": "K0lmenIA: agentes de QA para Claude Code, en español. Gratis y abierto.",
            "plugins": [{"name": NOMBRE, "source": fuente, "description": DESCRIPCION, "homepage": WEB,
                         "category": "testing"}]}


def _instalar(plugin):
    return (f"claude plugin marketplace add underc0delabs/k0lmenIA\n"
            f"claude plugin install {plugin}@{MARKETPLACE}")


LEEME_CORE = f"""# k0lmenIA — plugin de Claude Code

Agentes de QA en español para Claude Code. Esta rama (`plugin`) la arma sola el repo
[{REPO}](https://github.com/{REPO}) en cada cambio: no se edita a mano.

## Instalar

Desde una terminal (una sola vez por persona):

```
{_instalar(CORE)}
```

O adentro de Claude Code: `/plugin marketplace add underc0delabs/k0lmenIA` y `/plugin install {CORE}@{MARKETPLACE}`.

Después abrí Claude Code en la carpeta de tu proyecto y escribí **`/{CORE}:empezar`**: prepara el proyecto, revisa
que esté todo instalado, te ayuda a conectar tus herramientas y te sugiere por dónde arrancar.

## Qué instala y dónde

El código (agentes, skills, scripts y herramientas) queda en la caché de Claude Code. En tu proyecto, `k0lmenia init` (o
`/{CORE}:empezar`) deja lo tuyo: `input/` con los mismos ejemplos que el repo, `output/` con los informes y el portal, el
`.env`, `TAREAS.md`, tu copia de k0lmena y, en `.claude/settings.json`, los mismos permisos que el repo clonado. Nunca pisa
un archivo que ya existe.

## Actualizar

- **Automático** (recomendado): `/plugin` → Marketplaces → `{MARKETPLACE}` → *Enable auto-update*. Una sola vez por persona.
- **A mano**: `/plugin marketplace update {MARKETPLACE}`.

El framework de automatización (`herramientas/k0lmena/` de tu proyecto) se actualiza con `k0lmenia actualizar`; Claude te
avisa al iniciar la sesión cuando hay una versión nueva. Tus pruebas y tus datos (`input/`, `output/`, `.env`) no se tocan.

Para todo el equipo, en el `.claude/settings.json` del proyecto:

```json
{{
  "extraKnownMarketplaces": {{"{MARKETPLACE}": {{"source": {{"source": "github", "repo": "underc0delabs/k0lmenIA"}}}}}},
  "enabledPlugins": {{"{CORE}@{MARKETPLACE}": true}}
}}
```
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
    sobra = {"__pycache__", "node_modules", ".pytest_cache"}  # lo que dejan las corridas locales: no es estructura
    for d in [origen, *sorted(p for p in origen.rglob("*") if p.is_dir() and not sobra & set(p.relative_to(origen).parts))]:
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
    """input/: la estructura de carpetas y los ejemplos versionados (README, colecciones de demo, guiones, planes de prueba…)."""
    _estructura(origen, destino)
    for archivo in _versionados(origen.name):
        if archivo.is_file() and archivo.name != ".gitkeep":
            dst = destino / archivo.relative_to(origen)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(archivo, dst)


def permisos():
    """Los permisos del repo (.claude/settings.json) con los comandos y los conectores del plugin, para que trabajar con el
    plugin pida las mismas confirmaciones que el repo clonado: ni más ni menos. Los conectores son siempre los del core."""
    p = json.loads((RAIZ / ".claude" / "settings.json").read_text(encoding="utf-8")).get("permissions") or {}

    def regla(r):
        r = re.sub(r"^mcp__(playwright(?:-headless)?)__", rf"mcp__plugin_{CORE}_\1__", r)
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


def _agentes_y_skills(destino):
    (destino / "agents").mkdir(exist_ok=True)
    for nombre in AGENTES:
        agente = RAIZ / ".claude" / "agents" / f"{nombre}.md"
        (destino / "agents" / agente.name).write_text(transformar(agente.read_text(encoding="utf-8")), encoding="utf-8")
    for nombre in SKILLS:
        skill = RAIZ / ".claude" / "skills" / nombre
        for archivo in skill.rglob("*"):
            if archivo.is_file():
                dst = destino / "skills" / skill.name / archivo.relative_to(skill)
                dst.parent.mkdir(parents=True, exist_ok=True)
                if archivo.suffix == ".md":
                    dst.write_text(transformar(archivo.read_text(encoding="utf-8")), encoding="utf-8")
                else:
                    shutil.copy2(archivo, dst)


def construir(destino):
    destino = Path(destino).resolve()
    _limpiar(destino)
    for carpeta in CODIGO:
        shutil.copytree(RAIZ / carpeta, destino / carpeta, ignore=IGNORAR)
    shutil.copytree(RAIZ / "bin", destino / "bin", ignore=IGNORAR)
    for archivo in ARCHIVOS:
        if (RAIZ / archivo).exists():
            shutil.copy2(RAIZ / archivo, destino / archivo)
    _ejemplos(RAIZ / "input", destino / "input")
    _estructura(RAIZ / "output", destino / "output")
    _agentes_y_skills(destino)
    (destino / "skills" / "estandares").mkdir(parents=True, exist_ok=True)
    (destino / "skills" / "estandares" / "SKILL.md").write_text(estandares(), encoding="utf-8")
    for doc in ("AGENTES.md", "REFERENCIA.md"):
        if (destino / doc).exists():
            (destino / doc).write_text(transformar((destino / doc).read_text(encoding="utf-8")), encoding="utf-8")
    (destino / "hooks").mkdir(exist_ok=True)
    _escribir_json(destino / "hooks" / "hooks.json", hooks())
    (destino / "hooks" / "contexto.md").write_text(contexto() + "\n", encoding="utf-8")
    _escribir_json(destino / "hooks" / "permisos.json", permisos())
    _escribir_json(destino / ".mcp.json", mcp())
    _escribir_json(destino / ".claude-plugin" / "marketplace.json", marketplace(desde_rama=True))
    _escribir_json(destino / ".claude-plugin" / "plugin.json", manifiesto())
    shutil.copy2(RAIZ / ".claude-plugin" / "icon.png", destino / ".claude-plugin" / "icon.png")
    (destino / "README.md").write_text(LEEME_CORE, encoding="utf-8")
    (destino / ".gitattributes").write_text("bin/k0lmenia text eol=lf\n*.sh text eol=lf\n", encoding="utf-8")
    return destino


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Arma k0lmenIA como plugin de Claude Code.")
    ap.add_argument("--destino", default=str(RAIZ / "dist" / "plugin"))
    ap.add_argument("--marketplace-main", action="store_true",
                    help="reescribe .claude-plugin/marketplace.json del repo (apunta a la rama plugin)")
    a = ap.parse_args(argv)
    if a.marketplace_main:
        _escribir_json(RAIZ / ".claude-plugin" / "marketplace.json", marketplace(desde_rama=False))
        print("Listo: .claude-plugin/marketplace.json.")
        return 0
    destino = construir(a.destino)
    agentes = len(list((destino / "agents").glob("*.md")))
    skills = len([p for p in (destino / "skills").iterdir() if p.is_dir()])
    print(f"Plugin {NOMBRE} armado en {destino}: {agentes} agentes, {skills} skills. "
          f"Probalo con: claude --plugin-dir \"{destino}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())

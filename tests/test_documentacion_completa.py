"""La documentación nombra todo lo que hay en el repo: cada agente, skill, herramienta, script y comando npm aparece
donde alguien lo va a buscar. Si sumás algo y te olvidás de documentarlo, este test lo marca."""
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
T = lambda rel: (RAIZ / rel).read_text(encoding="utf-8")  # noqa: E731
AGENTES = sorted(p.stem for p in (RAIZ / ".claude" / "agents").glob("*.md"))
SKILLS = sorted(p.parent.name for p in (RAIZ / ".claude" / "skills").glob("*/SKILL.md"))
HERRAMIENTAS = sorted(p.name for p in (RAIZ / "herramientas").iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))
SCRIPTS = sorted(p.name for p in (RAIZ / "scripts").glob("*.py") if not p.name.startswith("_"))
NPM = sorted(json.loads(T("package.json"))["scripts"])


def _nombra(texto, nombre):
    return re.search(r"(?<![\w-])" + re.escape(nombre) + r"(?![\w-])", texto) is not None


@pytest.mark.parametrize("doc", ["README.md", "docs/index.html", "docs/en/index.html"])
def test_todos_los_agentes(doc):
    texto = T(doc)
    assert not [a for a in AGENTES if not _nombra(texto, a)]


@pytest.mark.parametrize("doc", [".claude/skills/README.md", "README.md", "docs/index.html", "docs/en/index.html"])
def test_todos_los_skills(doc):
    texto = T(doc)
    assert not [s for s in SKILLS if not _nombra(texto, s)]


@pytest.mark.parametrize("doc", ["herramientas/README.md", "REFERENCIA.md", "README.md", "docs/index.html", "docs/en/index.html"])
def test_todas_las_herramientas(doc):
    texto = T(doc)
    assert not [h for h in HERRAMIENTAS if not re.search(r"herramientas/" + re.escape(h) + r"\b|\b" + re.escape(h) + r"/", texto)]


@pytest.mark.parametrize("doc", ["scripts/README.md", "REFERENCIA.md"])
def test_todos_los_scripts(doc):
    texto = T(doc)
    assert not [s for s in SCRIPTS if s not in texto]


def test_todos_los_comandos_npm_en_referencia():
    texto = T("REFERENCIA.md")
    assert not [c for c in NPM if not re.search(r"npm (?:run )?" + re.escape(c) + r"(?![\w:-])", texto)]


def _palabras(texto):
    import html
    return set(re.findall(r"[a-záéíóúñü0-9]{3,}", html.unescape(re.sub("<[^>]+>", "", texto)).lower()))


@pytest.mark.parametrize("doc", ["docs/index.html", "docs/en/index.html"])
def test_indice_numerado_de_la_web_tiene_todas_las_secciones(doc):
    """El índice numerado (también lo usa el PDF) tiene una entrada para cada sección: la que más palabras comparte
    con el título de la sección tiene que compartir al menos la mitad."""
    texto = T(doc)
    indice = [_palabras(x) for x in re.findall(r"<li><span>\d+</span>(.*?)</li>", texto)]
    titulos = re.findall(r'<section class="seccion" id="(?!contenido)[^"]*">.*?<h2>(.*?)</h2>', texto, re.S)
    faltan = []
    for t in titulos:
        p = _palabras(t)
        if p and max(len(p & e) / len(p) for e in indice) < 0.5:
            faltan.append(t)
    assert not faltan, f"secciones sin entrada en el índice: {faltan}"

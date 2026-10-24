"""Integridad del proyecto: que todo lo que los agentes referencian exista y que los conteos coincidan.

Verifica que "todo se comunique con todo": cada `npm run`, script y herramienta que menciona un agente
existe de verdad, cada skill tiene su carpeta con el name correcto, y el número de agentes es coherente en
el README, AGENTES.md y el sitio web (ES/EN)."""
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
AGENTES = sorted((RAIZ / ".claude" / "agents").glob("*.md"))
SKILLS = sorted(p.parent.name for p in (RAIZ / ".claude" / "skills").glob("*/SKILL.md"))


def _scripts_npm():
    claves = set()
    for rel in ("package.json", "herramientas/k0lmena/package.json"):
        p = RAIZ / rel
        if p.exists():
            claves |= set((json.loads(p.read_text(encoding="utf-8")).get("scripts") or {}).keys())
    return claves | {"test", "conector"}


NPM = _scripts_npm()


def test_scripts_package_json_existen():
    cmds = json.loads((RAIZ / "package.json").read_text(encoding="utf-8")).get("scripts", {})
    faltan = []
    for nombre, cmd in cmds.items():
        for ref in re.findall(r"'((?:herramientas|scripts)/[^']+\.py)'", cmd):
            if not (RAIZ / ref).exists():
                faltan.append(f"{nombre} -> {ref}")
    assert not faltan, f"scripts de package.json que apuntan a archivos inexistentes: {faltan}"


@pytest.mark.parametrize("agente", AGENTES, ids=lambda p: p.stem)
def test_agente_referencias_existen(agente):
    t = agente.read_text(encoding="utf-8")
    faltan = []
    for sc in set(re.findall(r"\b(scripts/[\w/]+\.py)", t)):
        if not (RAIZ / sc).exists():
            faltan.append(sc)
    for hr in set(re.findall(r"\b(herramientas/[\w/]+\.py)", t)):
        if not (RAIZ / hr).exists():
            faltan.append(hr)
    for gi in set(re.findall(r"\b(generar_informe_[\w]+\.py)", t)):
        if not (RAIZ / "scripts" / gi).exists():
            faltan.append(f"scripts/{gi}")
    for run in set(re.findall(r"npm run ([a-z0-9:_-]+)", t)):
        if run not in NPM:
            faltan.append(f"npm run {run}")
    assert not faltan, f"{agente.name} referencia cosas que no existen: {faltan}"


@pytest.mark.parametrize("skill", SKILLS)
def test_skill_name_coincide_carpeta(skill):
    txt = (RAIZ / ".claude" / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"^name:\s*(.+)$", txt, re.M)
    assert m and m.group(1).strip() == skill, f"el name del frontmatter no coincide con la carpeta {skill}"


def test_conteos_coherentes():
    n = len(AGENTES)
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert f"{n} agentes" in readme
    assert f"badge/agentes-{n}-" in readme, "el badge de agentes del README no coincide"
    assert f"{n} agentes" in (RAIZ / "AGENTES.md").read_text(encoding="utf-8")
    arquitectura = (RAIZ / "ARQUITECTURA.md").read_text(encoding="utf-8")
    assert f"{n} agentes" in arquitectura and f"{len(SKILLS)} skills" in arquitectura
    assert f"{n} agentes" in (RAIZ / "docs/index.html").read_text(encoding="utf-8")
    assert f"{n} agents" in (RAIZ / "docs/en/index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("agente", AGENTES, ids=lambda p: p.stem)
def test_agente_tiene_tarjeta_en_web(agente):
    docs = (RAIZ / "docs/index.html").read_text(encoding="utf-8")
    assert f"<h4>{agente.stem}</h4>" in docs, f"{agente.stem} no tiene tarjeta en docs/index.html"


def test_claude_md_corto_y_con_todos_los_agentes():
    """CLAUDE.md se carga en cada conversación: índice corto con todos los agentes; el detalle va en REFERENCIA.md."""
    claude = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
    referencia = (RAIZ / "REFERENCIA.md").read_text(encoding="utf-8")
    assert len(claude.encode("utf-8")) < 30_000, "CLAUDE.md creció: mové el detalle a REFERENCIA.md o AGENTES.md"
    faltan = [a.stem for a in AGENTES if f"`{a.stem}`" not in claude]
    assert not faltan, f"agentes que faltan en el índice de CLAUDE.md: {faltan}"
    faltan = [a.stem for a in AGENTES if f"`{a.stem}`" not in referencia]
    assert not faltan, f"agentes que faltan en la tabla de REFERENCIA.md: {faltan}"

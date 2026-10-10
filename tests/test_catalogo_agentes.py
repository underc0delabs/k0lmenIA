"""AGENTES.md tiene que nombrar a todos los agentes y skills, y los skills que dice que usa
cada agente tienen que ser los que el agente realmente menciona en su archivo."""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = (RAIZ / "AGENTES.md").read_text(encoding="utf-8")
AGENTES = sorted(p.stem for p in (RAIZ / ".claude" / "agents").glob("*.md"))
SKILLS = sorted(p.parent.name for p in (RAIZ / ".claude" / "skills").glob("*/SKILL.md"))


def fila_resumen(agente):
    for linea in CATALOGO.splitlines():
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if celdas and celdas[0] == agente:
            return celdas
    return None


@pytest.mark.parametrize("agente", AGENTES)
def test_agente_en_el_catalogo(agente):
    assert f"### {agente}\n" in CATALOGO, "falta su sección en AGENTES.md"
    assert fila_resumen(agente), "falta su fila en la tabla de resumen de AGENTES.md"


@pytest.mark.parametrize("agente", AGENTES)
def test_skills_del_agente(agente):
    texto = (RAIZ / ".claude" / "agents" / f"{agente}.md").read_text(encoding="utf-8")
    usa = {s for s in SKILLS if re.search(r"\b" + re.escape(s) + r"\b", texto)}
    dice = {s.strip() for s in fila_resumen(agente)[3].split(",") if s.strip() in SKILLS}
    assert dice == usa, f"AGENTES.md dice {sorted(dice)}, el agente usa {sorted(usa)}"


@pytest.mark.parametrize("skill", SKILLS)
def test_skill_en_el_catalogo(skill):
    assert f"| {skill} " in CATALOGO, "falta en la tabla de skills de AGENTES.md"

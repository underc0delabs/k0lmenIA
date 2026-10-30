"""Los agentes y skills se cargan solo si su encabezado (frontmatter) es YAML válido:
un "dos puntos y espacio" sin comillas en la descripción hace que Claude Code los ignore."""
import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVOS = sorted((RAIZ / ".claude" / "agents").glob("*.md")) + sorted((RAIZ / ".claude" / "skills").glob("*/SKILL.md"))


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.parent.name if p.name == "SKILL.md" else p.stem)
def test_frontmatter_valido(archivo):
    texto = archivo.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    assert m, "falta el encabezado --- ... ---"
    datos = yaml.safe_load(m.group(1))
    assert datos.get("name") and datos.get("description")
    if archivo.name != "SKILL.md":
        assert datos["name"] == archivo.stem, "el name tiene que coincidir con el nombre del archivo"
        assert "Cuando te falta un dato o una confirmación" in texto, "falta la sección de preguntas para subagentes"

"""Avisos a Slack y Teams."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import avisar  # noqa: E402


def test_teams_viejo_por_la_url():
    assert avisar.es_teams_viejo("https://empresa.webhook.office.com/webhookb2/abc") and not avisar.es_teams_viejo("https://prod-12.westus.logic.azure.com/workflows/x")
    assert avisar.payload_teams_viejo("T", "x", "error")["themeColor"] == "C62828"

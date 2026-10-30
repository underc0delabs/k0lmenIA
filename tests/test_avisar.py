"""Avisos a Slack y Teams (scripts/avisar.py): payloads, resumen de Cucumber y configuración, sin red."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import avisar  # noqa: E402


def test_campos():
    assert avisar.parsear_campos("Suite=web, Ambiente = staging,Url=https://a.com/?x=1") == [
        ("Suite", "web"), ("Ambiente", "staging"), ("Url", "https://a.com/?x=1")]
    assert avisar.parsear_campos("") == []
    with pytest.raises(ValueError):
        avisar.parsear_campos("sin-igual")


def test_payload_slack_block_kit():
    p = avisar.payload_slack("Regresión", "48 de 50 aprobados", "error", "https://ci/1", [("Suite", "web")])
    assert p["text"].startswith("[Error] Regresión")
    tipos = [b["type"] for b in p["blocks"]]
    assert tipos == ["header", "section", "section", "actions"]
    assert p["blocks"][1]["text"]["text"].startswith(":rotating_light:")
    assert p["blocks"][2]["fields"][0]["text"] == "*Suite*\nweb"
    assert p["blocks"][3]["elements"][0]["url"] == "https://ci/1"
    sin_extras = avisar.payload_slack("T" * 300, "x", "ok")
    assert len(sin_extras["blocks"]) == 2 and len(sin_extras["blocks"][0]["text"]["text"]) == 150


def test_payload_teams_adaptive_card():
    p = avisar.payload_teams("Monitoreo", "Se cayó /login", "aviso", "https://x", [("URL", "/login")])
    assert p["type"] == "message"
    adj = p["attachments"][0]
    assert adj["contentType"] == "application/vnd.microsoft.card.adaptive"
    tarjeta = adj["content"]
    assert tarjeta["type"] == "AdaptiveCard" and tarjeta["version"] == "1.4"
    assert tarjeta["body"][0]["color"] == "Warning"
    assert tarjeta["body"][2] == {"type": "FactSet", "facts": [{"title": "URL", "value": "/login"}]}
    assert tarjeta["actions"][0]["type"] == "Action.OpenUrl"
    assert "actions" not in avisar.payload_teams("T", "x")["attachments"][0]["content"]


def _esc(nombre, estados, tags=()):
    return {"type": "scenario", "name": nombre, "tags": [{"name": t} for t in tags],
            "steps": [{"result": {"status": s}} for s in estados]}


def test_resumen_de_cucumber():
    reporte = [{"elements": [
        {"type": "background", "steps": [{"result": {"status": "passed"}}]},
        _esc("Login ok", ["passed", "passed"], ["@HU-001", "@CP-001", "@smoke"]),
        _esc("Login inválido", ["passed", "failed", "skipped"], ["@HU-001", "@CP-002"]),
        _esc("Pendiente", ["undefined"]),
    ]}]
    r = avisar.resumen_cucumber(reporte)
    assert (r["total"], r["aprobados"], r["fallidos"], r["otros"]) == (3, 1, 1, 1)
    assert r["fallidos_detalle"] == ["@HU-001 @CP-002 Login inválido"]
    titulo, texto, nivel, campos = avisar.aviso_desde_cucumber(reporte, "Regresión")
    assert titulo == "Regresión: falló" and nivel == "error"
    assert texto.startswith("1 de 3 escenario(s) aprobados · 1 fallido(s): @HU-001 @CP-002")
    assert ("Sin completar", "1") in campos
    assert avisar.aviso_desde_cucumber([])[2] == "aviso"


def test_sin_webhook_no_manda_y_estricto_sale_con_2(capsys):
    assert avisar.main(["--titulo", "T", "--texto", "x"], entorno={}) == 0
    salida = capsys.readouterr().out
    assert "SLACK_WEBHOOK_URL" in salida and "TEAMS_WEBHOOK_URL" in salida
    assert avisar.main(["--titulo", "T", "--texto", "x", "--estricto"], entorno={}) == 2
    assert avisar.main(["--texto", "x"], entorno={}) == 2


def test_prueba_muestra_el_json_y_nunca_la_url(capsys, monkeypatch):
    secreto = "https://hooks.slack.com/services/T000/B000/SECRETO"
    llamadas = []
    monkeypatch.setattr(avisar, "enviar", lambda url, payload, timeout=15: llamadas.append(payload) or (True, "HTTP 200"))
    assert avisar.main(["--titulo", "T", "--texto", "x", "--canal", "slack", "--prueba"], entorno={"SLACK_WEBHOOK_URL": secreto}) == 0
    salida = capsys.readouterr().out
    assert '"blocks"' in salida and secreto not in salida and not llamadas
    assert avisar.main(["--titulo", "T", "--texto", "x", "--campos", "A=1"], entorno={"SLACK_WEBHOOK_URL": secreto, "TEAMS_WEBHOOK_URL": "https://x.logic.azure.com/w"}) == 0
    assert len(llamadas) == 2 and llamadas[1]["type"] == "message"
    assert secreto not in capsys.readouterr().out


def test_falla_del_envio_y_url_sin_https(monkeypatch, capsys):
    monkeypatch.setattr(avisar, "enviar", lambda url, payload, timeout=15: (False, "HTTP 404 no_service"))
    assert avisar.main(["--titulo", "T", "--texto", "x", "--canal", "slack"], entorno={"SLACK_WEBHOOK_URL": "https://hooks.slack.com/x"}) == 1
    assert avisar.main(["--titulo", "T", "--texto", "x", "--canal", "teams"], entorno={"TEAMS_WEBHOOK_URL": "http://inseguro"}) == 1


def test_desde_cucumber_por_linea_de_comandos(tmp_path, capsys):
    reporte = tmp_path / "cucumber-report.json"
    reporte.write_text(json.dumps([{"elements": [_esc("A", ["passed"])]}]), encoding="utf-8")
    assert avisar.main(["--desde-cucumber", str(reporte), "--canal", "teams", "--prueba"], entorno={}) == 0
    assert "1 de 1 escenario(s) aprobados" in capsys.readouterr().out

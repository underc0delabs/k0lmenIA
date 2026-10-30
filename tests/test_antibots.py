"""Bloqueos anti-bots: el escenario que la protección de la app frenó (marca del hook de k0lmena, tools/navegador)
se publica como Bloqueado en la gestión y el análisis de fallos lo separa de los bugs."""
import base64
import json

import lectores

MARCA = ("BLOQUEO ANTI-BOTS: Cloudflare (desafio) en https://app.test/login\n"
         "El paso falló porque la protección anti-bots de la app frenó al navegador automatizado; no es un bug de la app.")


def _reporte(tmp_path, con_marca):
    adjuntos = [{"mime_type": "text/plain", "data": base64.b64encode(MARCA.encode()).decode()}] if con_marca else []
    features = [{"name": "Login", "uri": "features/HU-001-login.feature", "tags": [], "elements": [{
        "type": "scenario", "name": "Ingreso válido", "line": 5, "tags": [{"name": "@HU-001"}, {"name": "@CP-001"}],
        "steps": [
            {"name": "abro la app", "result": {"status": "passed", "duration": 1}},
            {"name": "ingreso", "result": {"status": "failed", "duration": 1,
                                           "error_message": "TimeoutError: Timeout 5000ms exceeded"},
             "embeddings": adjuntos},
        ]}]}]
    archivo = tmp_path / "cucumber-report.json"
    archivo.write_text(json.dumps(features), encoding="utf-8")
    return archivo


def test_gestion_publica_el_bloqueo_como_bloqueado(tmp_path):
    [r] = lectores.leer_resultados(_reporte(tmp_path, True), tmp_path / "evidencias")
    assert r["estado"] == "bloqueado"
    assert r["error"].startswith("BLOQUEO ANTI-BOTS: Cloudflare")


def test_sin_marca_sigue_siendo_fallido(tmp_path):
    [r] = lectores.leer_resultados(_reporte(tmp_path, False), tmp_path / "evidencias")
    assert r["estado"] == "fallido"



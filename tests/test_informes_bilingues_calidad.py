"""Informes en español e inglés (grupo de calidad y gestión): cada generador escribe informe.html e informe.en.html,
la versión en inglés usa el bloque "en" del agente y traduce la interfaz con el diccionario."""
import json
import sys

import generar_informe_cierre
import generar_informe_performance
import generar_informe_seguridad
import generar_plan
from _i18n import ruta_en, ruta_es  # noqa: E402


def _correr(modulo, argv, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["x"] + [str(a) for a in argv])
    modulo.main()


def _par(salida):
    acceso = salida.read_text(encoding="utf-8")  # el acceso abre el idioma elegido
    assert "k0-idioma" in acceso and "es/" in acceso and "en/" in acceso
    es = ruta_es(salida).read_text(encoding="utf-8")
    en = ruta_en(salida).read_text(encoding="utf-8")
    assert '<html lang="es">' in es and '<html lang="en">' in en
    assert 'class="idioma"' in es and 'data-idioma="en"' in es and 'data-idioma="es"' in en
    return es, en


def test_plan_bilingue(tmp_path, monkeypatch):
    plan = {"titulo": "Plan de pruebas — Registro", "historia": "HU-001", "fecha": "2026-10-24", "version": "1.0",
            "objetivos": ["Validar el alta de cuentas"], "alcance": {"incluye": ["Registro"], "excluye": ["Login social"]},
            "enfoque": "Funcional y E2E.", "tipos_prueba": ["Funcional", "E2E"],
            "riesgos": [{"descripcion": "Correo duplicado", "nivel": "Alto", "mitigacion": "Casos negativos"}],
            "datos_entorno": ["Staging"], "criterios_entrada": ["Build estable"], "criterios_salida": ["0 bugs críticos"],
            "supuestos": ["Mailpit disponible"], "preguntas_po": ["¿Edad mínima?"],
            "en": {"titulo": "Test plan — Sign-up", "objetivos": ["Validate account sign-up"], "enfoque": "Functional and E2E."}}
    entrada = tmp_path / "plan.json"
    entrada.write_text(json.dumps(plan), encoding="utf-8")
    _correr(generar_plan, [entrada, tmp_path / "plan.html"], monkeypatch)
    es, en = _par(tmp_path / "plan.html")
    assert "Validar el alta de cuentas" in es and "Validate account sign-up" in en and "Validar el alta" not in en
    assert "Objetivos" in es and "Objectives" in en


def test_cierre_bilingue(tmp_path, monkeypatch):
    cierre = {"titulo": "Informe de cierre — Registro", "historia": "HU-001", "fecha": "2026-10-24",
              "recomendacion": "Apto con observaciones", "resumen": "La ronda terminó con dos fallas menores.",
              "resultados": {"aprobado": 12, "fallido": 2, "bloqueado": 1}, "alcance": {"planeado": 18, "ejecutado": 15},
              "bugs": {"por_severidad": {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 1},
                       "criticos_abiertos": [{"id": "BUG-003", "titulo": "Cupón duplicado", "severidad": "Alta"}]},
              "riesgos_pendientes": ["Sin pruebas de carga"],
              "falta_informacion": [{"id": "FI-01", "que_falta": "Edad mínima", "impacto": "CA4", "pregunta": "¿16 o 18?", "estado": "Abierto"}],
              "conclusion": "Se puede salir con observaciones.",
              "en": {"resumen": "The round ended with two minor failures.", "conclusion": "It can ship with observations."}}
    entrada = tmp_path / "cierre.json"
    entrada.write_text(json.dumps(cierre), encoding="utf-8")
    _correr(generar_informe_cierre, [entrada, tmp_path / "cierre.html"], monkeypatch)
    es, en = _par(tmp_path / "cierre.html")
    assert "La ronda terminó" in es and "The round ended with two minor failures." in en
    assert "Missing information (1 open)" in en and "Pass with observations" in en


def test_seguridad_bilingue(tmp_path, monkeypatch):
    zap = {"@version": "2.15", "@generated": "hoy", "site": [{"@name": "https://x", "alerts": [
        {"pluginid": "10038", "name": "CSP Header Not Set", "riskcode": "2", "confidence": "3", "desc": "<p>d</p>",
         "solution": "<p>s</p>", "instances": [{"uri": "https://x/", "method": "GET"}], "count": "1"}]}]}
    (tmp_path / "zap.json").write_text(json.dumps(zap), encoding="utf-8")
    (tmp_path / "analisis.json").write_text(json.dumps({"resumen": "Falta la CSP.", "en": {"resumen": "The CSP is missing."}}), encoding="utf-8")
    _correr(generar_informe_seguridad, [tmp_path / "zap.json", tmp_path / "seg.html", "--url", "https://x",
                                        "--analisis", tmp_path / "analisis.json"], monkeypatch)
    es, en = _par(tmp_path / "seg.html")
    assert "Falta la CSP." in es and "The CSP is missing." in en
    assert "Alcance y método" in es and "Scope and method" in en and "Passive scan" in en


def test_performance_bilingue(tmp_path, monkeypatch):
    corrida = {"perfil": "load", "veredicto": "no cumple", "duracion_s": 300,
               "kpis": {"requests": 12000, "rps": 40, "usuarios_max": 50, "error_pct": 1.5},
               "latencia": {"p50": 120, "p95": 640, "p99": 900},
               "umbrales": [{"metrica": "http_req_duration", "condicion": "p(95)<500", "valor": "640 ms", "ok": False}],
               "errores": {"timeout": 12}, "detalle": {"filas": [{"nombre": "POST /login", "p95": 640}]}}
    (tmp_path / "corrida.json").write_text(json.dumps(corrida), encoding="utf-8")
    informe = {"titulo": "Informe de performance — Login", "historia": "HU-001", "veredicto": "No apto",
               "resumen": "El p95 supera el umbral.", "plan": {"objetivo": "Pico de las 9 h", "herramienta": "k6", "tipos": ["load"]},
               "corridas": [{"resumen": str(tmp_path / "corrida.json")}],
               "hallazgos": [{"titulo": "Login lento", "detalle": "p95 de 640 ms", "severidad": "Alta"}],
               "falta_informacion": [{"id": "FI-01", "que_falta": "Pico real", "pregunta": "¿Cuántos usuarios?"}],
               "en": {"resumen": "The p95 is above the threshold.", "hallazgos": [{"titulo": "Slow login", "detalle": "640 ms p95"}]}}
    (tmp_path / "informe.json").write_text(json.dumps(informe), encoding="utf-8")
    _correr(generar_informe_performance, [tmp_path / "informe.json", tmp_path / "perf.html"], monkeypatch)
    es, en = _par(tmp_path / "perf.html")
    assert "El p95 supera el umbral." in es and "The p95 is above the threshold." in en and "Slow login" in en
    assert "Resultados por corrida" in es and "Results per run" in en and "Not met" in en

"""Informe de resiliencia (agente probador-resiliencia)."""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import generar_informe_resiliencia as informe  # noqa: E402
from _i18n import ruta_es  # noqa: E402


def _datos():
    return {
        "url": "https://app.com/", "host": "app.com", "fecha": "2026-10-14T10:00:00", "marca": "20261014-100000", "timeout_ms": 8000,
        "escenarios": [{"id": "api-500", "nombre": "La API responde 500", "tipo": "api"}, {"id": "offline", "nombre": "Se corta la conexión", "tipo": "red"}],
        "resumen": {"paginas": 1, "escenarios": 2, "pruebas": 2, "ok": 0, "con_hallazgos": 1, "no_aplica": 1, "errores": 0, "hallazgos": 1,
                    "pantallas_blanco": 1, "sin_recuperacion": 0, "fallas_silenciosas": 0, "por_severidad": {"Alta": 1}},
        "hallazgos": [{"id": "R-01", "severidad": "Alta", "tipo": "Pantalla en blanco", "escenario": "api-500", "pagina": "https://app.com/",
                       "titulo": "La API responde 500: la pantalla queda casi vacía", "detalle": "Quedan 10 caracteres"}],
        "paginas": [{"url": "https://app.com/", "id": "01-inicio", "base": {"titulo": "Inicio", "texto_len": 900, "elementos": 120, "llamadas_api": ["GET /api/x"]},
                     "resultados": [
                         {"escenario": "api-500", "nombre": "La API responde 500", "estado": "hallazgo", "hallazgos": ["R-01"], "interceptados": 1,
                          "observado": {"texto_len": 10, "elementos": 3, "mensajes": []}, "recuperacion": {"recupera": True}},
                         {"escenario": "offline", "nombre": "Se corta la conexión", "estado": "no-aplica", "motivo": "sin red", "hallazgos": []}]}],
    }


def test_informe_con_matriz_hallazgos_y_analisis():
    analisis = {"veredicto": "La home se cae con la API", "hallazgos": {"R-01": {"severidad": "Crítica", "nota": "Es la home"}},
                "manuales": [{"id": "RM-01", "titulo": "Doble envío en el checkout", "severidad": "Alta", "escenario": "lenta", "pasos": "…", "esperado": "1 pedido", "obtenido": "2 pedidos"}],
                "falta_informacion": [{"id": "FI-01", "que_falta": "Mensaje si la API falla", "pregunta": "¿Qué mensaje?"}],
                "recomendaciones": [{"accion": "Mostrar un error con Reintentar", "motivo": "Hoy queda en blanco", "prioridad": "Alta"}]}
    html = informe.build_html(_datos(), analisis)
    for texto in ("Matriz página × escenario", "La home se cae con la API", "Es la home", "Crítica", "RM-01", "Doble envío en el checkout",
                  "FI-01", "Mostrar un error con Reintentar", "No aplica", "Se recupera al volver la red: sí"):
        assert texto in html, texto


def test_veredicto_sin_escenarios_aplicables():
    d = _datos()
    d["resumen"].update(pruebas=2, no_aplica=2, con_hallazgos=0, ok=0)
    d["hallazgos"] = []
    assert "No hubo escenarios aplicables" in informe.build_html(d, {})


def test_linea_de_comandos_y_evolucion(tmp_path):
    datos = tmp_path / "resiliencia.json"
    datos.write_text(json.dumps(_datos()), encoding="utf-8")
    salida = tmp_path / "informe-resiliencia.html"
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "generar_informe_resiliencia.py"), str(datos), str(salida)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "Evolución de las corridas" in ruta_es(salida).read_text(encoding="utf-8")

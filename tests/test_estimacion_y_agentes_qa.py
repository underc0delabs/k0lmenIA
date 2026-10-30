"""Tiempo estimado de ejecución manual, revisor de casos, charters, análisis de logs y los informes de UX y formularios."""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import estimacion
import generar_informe_revision
import revisar_casos

RAIZ = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------ estimación
def _caso_login():
    return {"id": "CP-1", "titulo": "Inicio de sesión con contraseña incorrecta", "precondiciones": "Usuario registrado", "pasos": [
        {"accion": "Ir a la página de login", "datos": "", "resultado": ""},
        {"accion": "Completar el email y la contraseña", "datos": "Email: ana@test.com\nContraseña: Mala123", "resultado": ""},
        {"accion": "Hacer clic en Ingresar", "datos": "", "resultado": "Se muestra el mensaje de error y el usuario sigue en el login"}]}


def test_formula_por_paso_y_por_caso():
    r = estimacion.estimar_caso(_caso_login())
    assert [p["categoria"] for p in r["pasos"]] == ["Navegar", "Completar campos", "Clic o seleccionar"]
    assert r["pasos"][1]["accion"] == 0.6                      # 2 campos × 0,3
    assert r["factor"] == 1.1 and r["minutos"] == 5.5 and r["texto"] == "5,5 min"
    assert estimacion.estimar_paso("Esperar el correo de confirmación")["minutos"] == 2.0
    assert estimacion.formatear(75) == "1 h 15 min" and estimacion.jira_duracion(6.5) == "7m" and estimacion.hhmm(75) == "01:15"


def test_etiquetas_como_texto_activan_el_factor_de_negativos():
    # En el JSON de generar_casos.py las etiquetas son un texto ("@login @negativo"), no una lista.
    base = {"id": "CP-3", "titulo": "Ingreso al sistema", "pasos": "1. Ir al login\n2. Hacer clic en Ingresar", "resultado": "Ve un aviso"}
    assert estimacion.estimar_caso(dict(base, etiquetas="@login @negativo"))["factor"] == 1.1
    assert estimacion.estimar_caso(dict(base, etiquetas=["login", "borde"]))["factor"] == 1.1
    assert estimacion.estimar_caso(dict(base, etiquetas="@login"))["factor"] == 1.0


def test_tiempo_manual_manda_y_bdd():
    c = dict(_caso_login(), tiempo_min="12")
    r = estimacion.estimar_caso(c)
    assert r["minutos"] == 12 and r["fuente"] == "planilla" and abs(sum(p["minutos"] for p in r["pasos"]) - 12) > 0  # los pasos se reparten
    bdd = {"id": "CP-2", "titulo": "Agregar al carrito", "gherkin": "Scenario: x\n  Given el usuario está en el catálogo\n  When agrega un producto\n  Then el carrito muestra 1 producto\n  And el total es 1500"}
    r = estimacion.estimar_caso(bdd)
    assert len(r["pasos"]) == 4 and r["pasos"][2]["verificacion"] == 0.5 and r["minutos"] >= 1


def test_planilla_con_columna_de_tiempo_y_total(tmp_path):
    from openpyxl import load_workbook
    entrada = tmp_path / "c.json"
    entrada.write_text(json.dumps({"modulo": "HU-9", "casos": [
        {"id": "CP-001", "titulo": "Ingreso válido", "pasos": "1. Ir al login\n2. Completar el email\n3. Hacer clic en Ingresar", "resultado": "Ve el inicio", "prioridad": "Alta"},
        {"id": "CP-002", "titulo": "Recuperar contraseña", "pasos": "1. Ir al login", "resultado": "Llega el correo", "prioridad": "Alta", "tiempo_min": 12}]}), encoding="utf-8")
    salida = tmp_path / "casos-HU-9.xlsx"
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "generar_casos.py"), str(entrada), str(salida)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    ws = load_workbook(salida).active
    encabezados = [c.value for c in ws[3]]
    col = encabezados.index("Tiempo estimado (min)") + 1
    assert ws.cell(row=5, column=col).value == 12 and str(ws.cell(row=6, column=col).value).startswith("=SUM(")
    md = salida.with_suffix(".md").read_text(encoding="utf-8")
    assert "Tiempo estimado de ejecución manual" in md and "12 min" in md
    sys.path.insert(0, str(RAIZ / "scripts" / "gestion"))
    from lectores import leer_casos
    casos = leer_casos(salida)
    assert {c["id"]: c["estimacion"]["minutos"] for c in casos}["CP-002"] == 12


def test_gestion_agrega_el_tiempo_y_reintenta_sin_campo():
    sys.path.insert(0, str(RAIZ / "scripts" / "gestion"))
    from adaptadores.base import con_tiempo, intentar_con_tiempo
    from comun import ErrorGestion
    caso = {"estimacion": {"texto": "5,5 min", "minutos": 5.5}}
    assert con_tiempo("Descripción", caso).endswith("Tiempo estimado de ejecución manual: 5,5 min (k0lmenIA)")
    llamadas = []

    def crear(cuerpo):
        llamadas.append(cuerpo)
        if "timetracking" in cuerpo:
            raise ErrorGestion("Field 'timetracking' cannot be set")
        return {"key": "PROJ-1"}

    assert intentar_con_tiempo(crear, {"a": 1, "timetracking": {}}, {"a": 1}) == {"key": "PROJ-1"}
    assert len(llamadas) == 2 and "timetracking" not in llamadas[1]


# ------------------------------------------------------------------ revisor de casos
def test_revisor_detecta_problemas_y_duplicados():
    c1 = {"id": "CP-001", "titulo": "Carrito", "tipo": "manual", "prioridad": "Alta", "precondiciones": "",
          "pasos": [{"accion": "Ir al catálogo", "datos": "", "resultado": ""}, {"accion": "Verificar que funcione con ana@test.com", "datos": "", "resultado": "Funciona correctamente"}]}
    tipos = [h["tipo"] for h in revisar_casos.revisar_manual(c1)]
    assert "Título" in tipos and "Resultado esperado" in tipos and "Paso vago" in tipos and "Datos de prueba" in tipos
    bdd = {"id": "Pagar", "tipo": "cucumber", "gherkin": "Scenario: Pagar\n  Given el usuario hace clic en el botón #pagar\n  When paga"}
    tipos = [h["tipo"] for h in revisar_casos.revisar_bdd(bdd)]
    assert "Then" in tipos and "Estilo" in tipos and "Trazabilidad" in tipos
    a = {"id": "CP-1", "titulo": "Agregar dos productos al carrito actualiza el total", "pasos": [{"accion": "Agregar el producto Mate al carrito"}, {"accion": "Agregar el producto Termo al carrito"}]}
    b = dict(a, id="CP-2", titulo="Agregar dos productos al carrito actualiza el total final")
    assert revisar_casos.duplicados([a, b])[0][2] >= 85


# ------------------------------------------------------------------ charters


# ------------------------------------------------------------------ logs


# ------------------------------------------------------------------ informes

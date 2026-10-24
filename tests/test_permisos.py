"""Informe del probador-permisos: comparación contra lo esperado e informe HTML."""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import generar_informe_permisos as gp  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402

DATOS = {
    "url": "https://a.com/", "host": "a.com", "fecha": "2026-10-14T10:00:00Z", "marca": "20261014-100000",
    "roles": [{"id": "anonimo", "nombre": "Anónimo", "autenticado": False},
              {"id": "admin", "nombre": "admin", "autenticado": True, "login_ok": True},
              {"id": "operador", "nombre": "operador", "autenticado": True, "login_ok": True}],
    "rutas": [{"url": "https://a.com/admin", "ruta": "/admin", "descubierta_por": ["admin"]},
              {"url": "https://a.com/reportes/mes", "ruta": "/reportes/mes", "descubierta_por": ["admin", "operador"]}],
    "matriz": [
        {"rol": "anonimo", "url": "https://a.com/admin", "acceso": "pide-login", "status": 200},
        {"rol": "admin", "url": "https://a.com/admin", "acceso": "permitido", "status": 200, "menus": ["Usuarios"], "botones": ["Nuevo"]},
        {"rol": "operador", "url": "https://a.com/admin", "acceso": "permitido", "status": 200},
        {"rol": "anonimo", "url": "https://a.com/reportes/mes", "acceso": "pide-login", "status": 200},
        {"rol": "admin", "url": "https://a.com/reportes/mes", "acceso": "permitido", "status": 200},
        {"rol": "operador", "url": "https://a.com/reportes/mes", "acceso": "denegado", "status": 403},
    ],
    "endpoints": [{"metodo": "GET", "ruta": "/api/x", "url": "https://a.com/api/x", "resultados": {"anonimo": {"status": 401}, "admin": {"status": 200, "con_token": True}}}],
    "hallazgos": [{"id": "P-01", "severidad": "Media", "tipo": "Opción sin permiso", "titulo": "t", "detalle": "d", "rol": "operador", "url": "https://a.com/reportes/mes"}],
    "resumen": {"roles": 3, "rutas": 2, "visitas": 6, "permitidas": 3, "denegadas": 1, "piden_login": 2, "hallazgos": 1, "por_severidad": {"Crítica": 0, "Alta": 0, "Media": 1, "Baja": 0}},
}
ESPERADO = {"operador": {"/admin": "denegado", "/reportes*": "permitido"}, "admin": {"/admin": "permitido"}}


def test_esperado_por_ruta_exacta_y_prefijo():
    assert gp.esperado_para(ESPERADO, "operador", "https://a.com/admin/") == "denegado"
    assert gp.esperado_para(ESPERADO, "operador", "https://a.com/reportes/mes") == "permitido"
    assert gp.esperado_para(ESPERADO, "operador", "https://a.com/otra") is None
    assert gp.esperado_para(ESPERADO, "anonimo", "https://a.com/admin") is None


def test_diferencias_contra_lo_esperado():
    d = gp.diferencias(DATOS, ESPERADO)
    assert [(x["id"], x["severidad"], x["rol"], gp.ruta_de(x["url"])) for x in d] == [
        ("E-01", "Crítica", "operador", "/admin"), ("E-02", "Alta", "operador", "/reportes/mes")]


def test_informe_con_matriz_diferencias_y_falta_informacion():
    html = gp.build_html(DATOS, {"esperado": ESPERADO, "descartados": [{"id": "P-01", "motivo": "es esperado"}]})
    assert "Matriz de acceso por rol" in html and "Endpoints por rol" in html and "Qué ve cada rol" in html
    assert "entra a algo que no debería" in html and "Descartado: es esperado" in html
    sin = gp.build_html(DATOS, {})
    assert "Falta información" in sin and "matriz de permisos por rol" in sin


def test_linea_de_comandos_con_historial(tmp_path):
    carpeta = tmp_path / "a.com"
    carpeta.mkdir()
    (carpeta / "permisos.json").write_text(json.dumps(DATOS), encoding="utf-8")
    viejo = carpeta / "historial" / "20261013-100000"
    viejo.mkdir(parents=True)
    (viejo / "permisos.json").write_text(json.dumps(dict(DATOS, hallazgos=[], marca="20261013-100000")), encoding="utf-8")
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "generar_informe_permisos.py"), str(carpeta / "permisos.json"), str(carpeta / "informe-permisos.html")],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    html = ruta_es(carpeta / "informe-permisos.html").read_text(encoding="utf-8")
    assert "Evolución de las corridas" in html and "Corridas guardadas" in html

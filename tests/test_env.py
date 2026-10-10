"""Lectura del .env (scripts/_env.py): mismas reglas que dotenv y scripts/mcp/leer-env.js."""
from _env import leer_env


def test_reglas_basicas(tmp_path):
    archivo = tmp_path / ".env"
    archivo.write_text(
        "﻿# comentario\n"
        "SIMPLE=valor\n"
        "export CON_EXPORT=si\n"
        "ESPACIOS =  con espacios   \n"
        "COMENTARIO=abc # esto no va\n"
        'COMILLAS="con # numeral"\n'
        "SIMPLES='literal'\n"
        "VACIA=\n"
        "# COMENTADA=no\n",
        encoding="utf-8",
    )
    v = leer_env(archivo)
    assert v["SIMPLE"] == "valor"
    assert v["CON_EXPORT"] == "si"
    assert v["ESPACIOS"] == "con espacios"
    assert v["COMENTARIO"] == "abc"
    assert v["COMILLAS"] == "con # numeral"
    assert v["SIMPLES"] == "literal"
    assert v["VACIA"] == ""
    assert "COMENTADA" not in v


def test_archivo_inexistente(tmp_path):
    assert leer_env(tmp_path / "no-existe.env") == {}


def test_doctor_variables_alternativas():
    import doctor
    # Xray Server/DC: token, o usuario y contraseña
    assert doctor.faltantes(["XRAY_DC_TOKEN|XRAY_DC_USER+XRAY_DC_PASSWORD"], {"XRAY_DC_USER": "u", "XRAY_DC_PASSWORD": "p"}) == []
    assert doctor.faltantes(["XRAY_DC_TOKEN|XRAY_DC_USER+XRAY_DC_PASSWORD"], {"XRAY_DC_USER": "u"}) != []
    assert doctor.faltantes(["A", "B"], {"A": "1"}) == ["B"]

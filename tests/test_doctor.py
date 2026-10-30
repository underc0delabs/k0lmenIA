"""npm run doctor: chequeos del .env y de las integraciones, sin red ni Docker."""
import json

import doctor


def correr(tmp_path, monkeypatch, capsys, contenido, *args):
    env = tmp_path / ".env"
    env.write_text(contenido, encoding="utf-8")
    monkeypatch.setenv("K0LMENA_ENV_FILE", str(env))
    for k in ("APP_URL", "BASEURL", "REPO_PROVEEDOR", "REPO_RUTA_LOCAL", "SLACK_WEBHOOK_URL"):
        monkeypatch.delenv(k, raising=False)
    codigo = doctor.main(["--json", "--rapido", *args])
    salida = json.loads(capsys.readouterr().out)
    return codigo, salida["resultados"]


def textos(resultados, estado):
    return [r["texto"] for r in resultados if r["estado"] == estado]


def test_env_valido_y_urls(tmp_path, monkeypatch, capsys):
    codigo, res = correr(tmp_path, monkeypatch, capsys, "APP_URL=https://app.test\nBASEURL=ftp://mal\n", "--seccion", "env")
    assert codigo == 1
    assert "APP_URL definida" in textos(res, "ok")
    assert any("BASEURL no es una URL válida" in t for t in textos(res, "falta"))
    assert all(r["seccion"] == "env" for r in res)


def test_url_en_un_solo_lugar(tmp_path, monkeypatch, capsys):
    _, res = correr(tmp_path, monkeypatch, capsys, "APP_URL=https://app.test\nBASEURL=https://otra.test\n", "--seccion", "env")
    assert any("BASEURL y APP_URL son distintas" in t for t in textos(res, "aviso"))
    _, res = correr(tmp_path, monkeypatch, capsys, "BASEURL=https://vieja.test\n", "--seccion", "env")
    assert any("nombre viejo" in t for t in textos(res, "aviso"))
    _, res = correr(tmp_path, monkeypatch, capsys, "APP_URL=https://app.test\n", "--seccion", "env")
    assert not any("BASEURL" in t for t in textos(res, "aviso") + textos(res, "falta"))


def test_integraciones_coherentes(tmp_path, monkeypatch, capsys):
    contenido = (f"REPO_RUTA_LOCAL={tmp_path / 'no-es-clon'}\n"
                 "SLACK_WEBHOOK_URL=https://otra.cosa/x\nTEAMS_WEBHOOK_URL=https://prod.workflows/x\n")
    codigo, res = correr(tmp_path, monkeypatch, capsys, contenido, "--seccion", "integraciones")
    faltas = " | ".join(textos(res, "falta"))
    assert codigo == 1
    assert "SLACK_WEBHOOK_URL no tiene el formato esperado" in faltas
    assert "REPO_RUTA_LOCAL no apunta a un clon de git" in textos(res, "aviso")
    assert "Avisos a Teams (Workflows)" in textos(res, "ok")
    # nunca se muestran valores
    assert "otra.cosa" not in json.dumps(res) and "prod.workflows" not in json.dumps(res)


def test_proveedor_por_conector_y_db(tmp_path, monkeypatch, capsys):
    contenido = "APP_URL=https://a.b\nREPO_PROVEEDOR=github\nDB_CONEXIONES=principal\nDB_PRINCIPAL_MOTOR=oracle\n"
    _, res = correr(tmp_path, monkeypatch, capsys, contenido, "--seccion", "env,integraciones")
    assert any("REPO_PROVEEDOR=github" in t and "clon local" in t for t in textos(res, "aviso"))
    assert "Base principal: DB_PRINCIPAL_MOTOR inválido" in " | ".join(textos(res, "falta"))


def test_seccion_desconocida(capsys):
    import pytest
    with pytest.raises(SystemExit):
        doctor.main(["--seccion", "nada"])

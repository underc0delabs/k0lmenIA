"""Plantillas de CI (herramientas/ci): YAML válido, sin secretos, mismas variables, y generar/publicar."""
import importlib.util
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ci", RAIZ / "herramientas" / "ci" / "ci.py")
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)

PLANTILLAS = {n: (ci.PLANTILLAS / origen) for n, (origen, _, _) in ci.PLATAFORMAS.items()}


@pytest.mark.parametrize("plataforma", sorted(PLANTILLAS))
def test_plantilla_existe_y_tiene_las_variables_comunes(plataforma):
    texto = PLANTILLAS[plataforma].read_text(encoding="utf-8")
    for clave in ("__SUITES__", "K0LMENA_SUITES", "K0LMENA_ENV_FILE", "GESTION_CICLO",
                  "npm ci --prefix herramientas/k0lmena", "playwright install --with-deps",
                  "npm run test:$suite", "herramientas/ci/ci.py publicar", "herramientas/k0lmena/reports"):
        assert clave in texto, f"{plataforma}: falta {clave}"


@pytest.mark.parametrize("plataforma", ["github", "gitlab", "azure"])
def test_yaml_valido(plataforma):
    yaml = pytest.importorskip("yaml")
    datos = yaml.safe_load(PLANTILLAS[plataforma].read_text(encoding="utf-8"))
    assert isinstance(datos, dict) and datos


def test_jenkinsfile_declarativo_balanceado():
    texto = PLANTILLAS["jenkins"].read_text(encoding="utf-8")
    sin_comentarios = re.sub(r"//[^\n]*", "", texto)
    assert sin_comentarios.count("{") == sin_comentarios.count("}")
    assert re.search(r"^pipeline \{", texto, re.M) and "post {" in texto


@pytest.mark.parametrize("plataforma", sorted(PLANTILLAS))
def test_sin_secretos_literales(plataforma):
    texto = PLANTILLAS[plataforma].read_text(encoding="utf-8")
    # Ninguna asignación de token/clave con un valor literal: solo referencias a secrets o variables.
    for m in re.finditer(r"(?im)^\s*[\w.-]*(token|password|secret|api_key|client_secret)[\w.-]*\s*[:=]\s*(\S.*)$", texto):
        valor = m.group(2).strip().strip("\"'")
        assert valor.startswith(("${{", "$(", "$")) or not valor, f"{plataforma}: valor literal en {m.group(0)!r}"
    assert not re.search(r"(ATATT|ghp_|glpat-|xox[bp]-)[A-Za-z0-9]", texto)


def test_generar_reemplaza_suites_y_no_pisa(tmp_path):
    ruta = ci.generar("github", "all", tmp_path)
    assert ruta == tmp_path / ".github" / "workflows" / "k0lmena.yml"
    texto = ruta.read_text(encoding="utf-8")
    assert 'K0LMENA_SUITES: "web api"' in texto and "__SUITES__" not in texto
    ruta.write_text("mío", encoding="utf-8")
    with pytest.raises(FileExistsError):
        ci.generar("github", "web", tmp_path)
    assert ruta.read_text(encoding="utf-8") == "mío"
    ci.generar("github", "web", tmp_path, forzar=True)
    assert 'K0LMENA_SUITES: "web"' in ruta.read_text(encoding="utf-8")


@pytest.mark.parametrize("plataforma,relativo", [(p, d) for p, (_, d, _) in ci.PLATAFORMAS.items()])
def test_generar_cada_plataforma(tmp_path, plataforma, relativo):
    assert ci.generar(plataforma, "api", tmp_path) == tmp_path / relativo


def test_main_generar_existente_sale_con_error(tmp_path, capsys):
    assert ci.main(["generar", "--plataforma", "gitlab", "--destino", str(tmp_path)]) == 0
    assert ci.main(["generar", "--plataforma", "gitlab", "--destino", str(tmp_path)]) == 1
    assert "--forzar" in capsys.readouterr().err


def test_publicar_sin_ciclo_no_hace_nada(monkeypatch):
    monkeypatch.setattr(ci, "cargar_env", lambda: None)
    monkeypatch.delenv("GESTION_CICLO", raising=False)
    llamadas = []
    assert ci.publicar(["web"], ejecutar=lambda *a, **k: llamadas.append(a) or 0) == 0
    assert llamadas == []


def test_publicar_extrae_y_publica_por_suite(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, "cargar_env", lambda: None)
    monkeypatch.setattr(ci, "REPORTES", tmp_path)
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "cucumber-report.json").write_text(json.dumps([{"elements": []}]), encoding="utf-8")
    llamadas = []
    estado = ci.publicar(["web", "api"], ciclo="PROJ-60", traza="HU-001", dry_run=True,
                         ejecutar=lambda cmd, **k: llamadas.append(cmd) or 0)
    assert estado == 0 and len(llamadas) == 2  # api no tiene reporte: se saltea
    assert "extraer-resultados" in llamadas[0]
    assert llamadas[1][2:] == ["--dry-run", "publicar-resultados", "--ciclo", "PROJ-60", "--resultados",
                               llamadas[0][-1], "--traza", "HU-001"]


def test_publicar_informa_falla(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, "cargar_env", lambda: None)
    monkeypatch.setattr(ci, "REPORTES", tmp_path)
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "cucumber-report.json").write_text(json.dumps([{"elements": []}]), encoding="utf-8")
    assert ci.publicar(["api"], ciclo="PROJ-60", ejecutar=lambda *a, **k: 1) == 1

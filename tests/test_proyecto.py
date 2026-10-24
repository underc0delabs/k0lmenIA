"""Código y datos separados (scripts/_proyecto.py): con K0LMENIA_PROYECTO los informes, el portal, el .env y la
sesión van a la carpeta del proyecto (k0lmenIA como plugin); sin la variable, todo sigue en el repo como siempre."""
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PY = [sys.executable, "-X", "utf8"]


def _correr(args, proyecto=None, cwd=None, extra=None):
    env = {k: v for k, v in os.environ.items() if k not in ("K0LMENIA_PROYECTO", "K0LMENA_ENV_FILE")}
    if proyecto:
        env["K0LMENIA_PROYECTO"] = str(proyecto)
    env.update(extra or {})
    return subprocess.run(PY + args, capture_output=True, text=True, encoding="utf-8", env=env, cwd=cwd or RAIZ)


def test_sin_variable_el_proyecto_es_el_repo():
    r = _correr(["-c", "import sys; sys.path.insert(0, 'scripts'); import _proyecto, _env; "
                       "print(_proyecto.PROYECTO); print(_env.archivo_env())"])
    proyecto, env = r.stdout.splitlines()
    assert Path(proyecto) == RAIZ and Path(env) == RAIZ / ".env"


def test_env_y_transcripciones_del_proyecto(tmp_path):
    (tmp_path / ".env").write_text("APP_URL=https://app.proyecto.test\n", encoding="utf-8")
    r = _correr(["-c", "import sys; sys.path.insert(0, 'scripts'); import _env, metricas_tokens as m; "
                       "print(_env.archivo_env()); print(_env.leer_env()['APP_URL']); print(m.carpeta_transcripciones())"],
                proyecto=tmp_path, extra={"CLAUDE_CONFIG_DIR": str(tmp_path / "config-claude")})
    env, url, transcripciones = r.stdout.splitlines()
    assert Path(env) == tmp_path / ".env" and url == "https://app.proyecto.test"
    clave = str(tmp_path.resolve()).replace(":", "-").replace("\\", "-").replace("/", "-")
    assert Path(transcripciones).name.lower() == clave.lower()  # ~/.claude/projects/<ruta del proyecto>


def test_portal_e_informes_van_al_proyecto(tmp_path):
    portal_repo = RAIZ / "output" / "index.html"
    antes = portal_repo.stat().st_mtime if portal_repo.exists() else None
    (tmp_path / "output" / "reportes-bug").mkdir(parents=True)
    (tmp_path / "output" / "reportes-bug" / "BUG-001.md").write_text(
        "**ID:** `BUG-001`\n\n**Título:** `[Login]` No entra\n\n**Estado:** `Abierto`\n", encoding="utf-8")
    r = _correr(["scripts/portal_informes.py"], proyecto=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "output" / "es" / "index.html").exists() and (tmp_path / "output" / "en" / "index.html").exists()
    assert (tmp_path / "output" / "reportes-bug" / "es" / "BUG-001.html").exists()  # el artefacto también, en el proyecto
    assert (portal_repo.stat().st_mtime if portal_repo.exists() else None) == antes  # el portal del repo no se tocó


def test_triage_por_defecto_en_el_proyecto(tmp_path):
    bug = tmp_path / "bug.json"
    bug.write_text(json.dumps({"id": "B-1", "titulo": "El cupón se aplica dos veces", "descripcion": "x"}), encoding="utf-8")
    r = _correr(["scripts/buscar_duplicados.py", "--bug", str(bug), "--nombre", "prueba-proyecto"], proyecto=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "output" / "triage" / "prueba-proyecto" / "triage.json").exists()
    assert not (RAIZ / "output" / "triage" / "prueba-proyecto").exists()


def test_cada_script_resuelve_el_proyecto_igual():
    """La regla está en una línea en cada script (para no depender de cómo se importó): que sea siempre la misma."""
    linea = 'PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()'
    archivos = [p for p in list((RAIZ / "scripts").rglob("*.py")) + list((RAIZ / "herramientas").rglob("*.py"))
                if "node_modules" not in p.parts and "PROYECTO = Path(" in p.read_text(encoding="utf-8")]
    assert len(archivos) >= 30
    for p in archivos:
        if p.name == "_proyecto.py":
            continue
        assert linea in p.read_text(encoding="utf-8"), p

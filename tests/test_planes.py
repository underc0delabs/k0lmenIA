"""Planes de k0lmenIA como plugins: el catálogo (catalogo-planes.json), el comando `k0lmenia planes` y cómo el comando del
core le pasa los comandos al plugin pago instalado (registro en ~/.k0lmenia/planes.json). Es el mismo archivo en los
tres repos."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = json.loads((RAIZ / "catalogo-planes.json").read_text(encoding="utf-8"))
PLAN = json.loads((RAIZ / ".claude-plugin" / "plan.json").read_text(encoding="utf-8"))["plan"]
ORDEN = [p["id"] for p in CATALOGO["planes"]]
HASTA_ESTE = CATALOGO["planes"][: ORDEN.index(PLAN) + 1]


def test_el_repo_tiene_lo_de_su_plan_y_los_anteriores():
    """Cada repo tiene todo lo de su plan y los anteriores (gratis ⊂ Pro ⊂ Empresa), y nada que no esté en el catálogo."""
    agentes = {p.stem for p in (RAIZ / ".claude" / "agents").glob("*.md")}
    skills = {p.parent.name for p in (RAIZ / ".claude" / "skills").glob("*/SKILL.md")}
    esperados_a = {a["nombre"] for p in HASTA_ESTE for a in p["agentes"]}
    esperados_s = {s["nombre"] for p in HASTA_ESTE for s in p["skills"]}
    assert agentes == esperados_a, f"sobran {agentes - esperados_a}, faltan {esperados_a - agentes}"
    assert skills == esperados_s, f"sobran {skills - esperados_s}, faltan {esperados_s - skills}"


def test_catalogo_coherente():
    assert ORDEN == ["light", "pro", "empresa"] and CATALOGO["marketplace"] == "k0lmenia"
    plugins = [p["plugin"] for p in CATALOGO["planes"]]
    assert plugins == ["k0lmenia", "k0lmenia-pro", "k0lmenia-empresa"]
    for i, p in enumerate(CATALOGO["planes"]):
        assert p["depende"] == plugins[:i], "cada plan depende de todos los anteriores"
        assert p["fuente"]["repo"] == p["repo"] and p["precio"] and p["resumen"] and p["descripcion"]
    assert "k0lmena-tmt" in CATALOGO["planes"][0]["conectores"], "k0lmenaTMT viene en el plan gratis"


@pytest.mark.skipif(not (RAIZ / "scripts" / "catalogo_planes.py").exists(), reason="el catálogo se arma en el repo de Empresa")
def test_catalogo_al_dia_con_el_reparto():
    import catalogo_planes
    assert CATALOGO == catalogo_planes.construir(), "regeneralo: python scripts/catalogo_planes.py --copiar-a ../K0lmenia ../K0lmenia-pro"


def _env(tmp_path, registro=None, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ("K0LMENIA_PROYECTO", "K0LMENIA_CODIGO", "K0LMENIA_DELEGADO")}
    env.update(K0LMENIA_REGISTRO=str(registro or tmp_path / "registro" / "planes.json"), K0LMENIA_SIN_AVISO="1",
               CLAUDE_PLUGIN_DATA=str(tmp_path / "datos"), **extra)
    return env


def _addon_falso(tmp_path, plan):
    """Un plugin pago mínimo: su lib/k0lmenia anota con qué lo llamaron."""
    raiz = tmp_path / f"addon-{plan}"
    (raiz / "lib").mkdir(parents=True)
    (raiz / "lib" / "k0lmenia").write_text(
        "const fs = require('fs');\n"
        f"fs.writeFileSync(process.env.SALIDA, JSON.stringify({{plan: '{plan}', args: process.argv.slice(2), "
        "delegado: process.env.K0LMENIA_DELEGADO, nucleo: process.env.K0LMENIA_NUCLEO}));\n", encoding="utf-8")
    return raiz


def _k0lmenia(env, cwd, *args):
    return subprocess.run(["node", str(RAIZ / "bin" / "k0lmenia"), *args], cwd=cwd, env=env, capture_output=True, text=True,
                          encoding="utf-8")


def test_el_core_pasa_los_comandos_al_plan_mas_completo(tmp_path):
    registro = tmp_path / "registro" / "planes.json"
    registro.parent.mkdir()
    pro, empresa = _addon_falso(tmp_path, "pro"), _addon_falso(tmp_path, "empresa")
    salida = tmp_path / "salida.json"
    env = _env(tmp_path, registro, SALIDA=str(salida))
    # Solo Pro: los comandos van a Pro.
    registro.write_text(json.dumps({"pro": {"raiz": str(pro)}}), encoding="utf-8")
    assert _k0lmenia(env, tmp_path, "py", "scripts/generar_informe_generico.py", "a.json").returncode == 0
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["plan"] == "pro" and datos["args"] == ["py", "scripts/generar_informe_generico.py", "a.json"]
    assert datos["delegado"] == "1" and Path(datos["nucleo"]) == RAIZ
    # Pro y Empresa: gana Empresa (incluye todo lo de Pro).
    registro.write_text(json.dumps({"pro": {"raiz": str(pro)}, "empresa": {"raiz": str(empresa)}}), encoding="utf-8")
    _k0lmenia(env, tmp_path, "doctor")
    assert json.loads(salida.read_text(encoding="utf-8"))["plan"] == "empresa"
    # Un plan desinstalado (su carpeta ya no está) no cuenta: lo corre el core.
    salida.unlink()
    registro.write_text(json.dumps({"empresa": {"raiz": str(tmp_path / "ya-no-esta")}}), encoding="utf-8")
    r = _k0lmenia(env, tmp_path, "ayuda")
    assert r.returncode == 0 and "k0lmenia planes" in r.stdout and not salida.exists()
    # Un script que no está en el plan instalado: lo dice y lleva al setup (en vez del error de Python).
    r = _k0lmenia(env, tmp_path, "py", "scripts/no_existe_en_ningun_plan.py")
    assert r.returncode == 2 and "no está en tu plan" in r.stderr and "/k0lmenia:setup" in r.stderr


def test_preparar_es_del_core_y_nombra_los_planes(tmp_path):
    registro = tmp_path / "registro" / "planes.json"
    registro.parent.mkdir()
    registro.write_text(json.dumps({"pro": {"raiz": str(_addon_falso(tmp_path, "pro"))}}), encoding="utf-8")
    contexto = RAIZ / "hooks" / "contexto.md"
    salida = tmp_path / "salida.json"
    r = _k0lmenia(_env(tmp_path, registro, SALIDA=str(salida)), tmp_path, "preparar", "--contexto")
    assert r.returncode == 0 and not salida.exists(), "preparar no se delega"
    if contexto.exists():  # en el repo clonado no hay hooks/: el contexto lo arma el plugin
        assert "Planes instalados: core + Pro." in r.stdout


def test_registrar_anota_la_carpeta_del_plan(tmp_path):
    registro = tmp_path / "registro" / "planes.json"
    r = _k0lmenia(_env(tmp_path, registro), tmp_path, "registrar", "pro")
    assert r.returncode == 0
    assert Path(json.loads(registro.read_text(encoding="utf-8"))["pro"]["raiz"]) == RAIZ
    assert _k0lmenia(_env(tmp_path, registro), tmp_path, "registrar", "otro").returncode == 2


def test_planes_sin_red_dice_que_esta_instalado(tmp_path):
    registro = tmp_path / "registro" / "planes.json"
    registro.parent.mkdir()
    registro.write_text(json.dumps({"pro": {"raiz": str(_addon_falso(tmp_path, "pro"))}}), encoding="utf-8")
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "planes.py"), "--json", "--sin-red"], cwd=tmp_path,
                       env=_env(tmp_path, registro, K0LMENIA_PROYECTO=str(tmp_path)), capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0, r.stderr
    e = json.loads(r.stdout)
    estados = {p["id"]: p["estado"] for p in e["planes"]}
    assert estados["light"] == "instalado" and estados["pro"] == "instalado" and estados["empresa"] == "desconocido"
    assert e["tmt"] == {"configurado": False, "url": None}
    (tmp_path / ".env").write_text("K0LMENA_TMT_URL=https://tmt.test/api/v1/mcp\nK0LMENA_TMT_TOKEN=abc\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "planes.py"), "--json", "--sin-red"], cwd=tmp_path,
                       env=_env(tmp_path, registro, K0LMENIA_PROYECTO=str(tmp_path)), capture_output=True, text=True,
                       encoding="utf-8")
    assert json.loads(r.stdout)["tmt"]["configurado"] is True


def test_acceso_distingue_sin_permiso(monkeypatch):
    import planes

    class R:
        def __init__(self, code, err):
            self.returncode, self.stderr, self.stdout = code, err, ""

    monkeypatch.setattr(planes.shutil, "which", lambda _: "git")
    monkeypatch.setattr(planes.subprocess, "run", lambda *a, **k: R(0, ""))
    assert planes.acceso("x/y")[0] == "si"
    monkeypatch.setattr(planes.subprocess, "run", lambda *a, **k: R(128, "remote: Repository not found.\nfatal: repository not found"))
    assert planes.acceso("x/y")[0] == "no"
    monkeypatch.setattr(planes.subprocess, "run", lambda *a, **k: R(128, "fatal: unable to access: Could not resolve host"))
    assert planes.acceso("x/y")[0] == "desconocido"


def test_opciones_compara_y_lista_todo():
    import planes
    texto = planes.opciones({"planes": [{"id": "light", "estado": "instalado"}, {"id": "pro", "estado": "disponible"},
                                        {"id": "empresa", "estado": "bloqueado"}]})
    assert "## Comparación" in texto and "## Todas las opciones" in texto
    assert "| **En esta PC** | ✅ instalado | ⬇️ disponible | 🔒 sin acceso |" in texto
    for p in CATALOGO["planes"]:  # todas las opciones de todos los planes
        for a in p["agentes"]:
            assert f"| `{a['nombre']}` |" in texto
        for s in p["skills"]:
            assert f"| `{s['nombre']}` |" in texto
    total = sum(len(p["agentes"]) for p in CATALOGO["planes"])
    assert f"| Agentes | {len(CATALOGO['planes'][0]['agentes'])} |" in texto and f"| {total} |" in texto
    # cada fila de la tabla tiene una celda por plan (ningún "|" suelto en las descripciones)
    filas = [l for l in texto.splitlines() if l.startswith("| `")]
    assert all(l.replace("\|", "").count("|") == 3 for l in filas)


def test_recomendar_segun_la_web():
    import planes
    html = ("<html><head><title>Mi tienda &amp; más</title><script src='https://cdn.shopify.com/x.js'></script>"
            "<script src='https://www.googletagmanager.com/gtm.js'></script></head><body>"
            "<form><input type='password'></form><a href='/cart'>Carrito</a></body></html>")
    d = planes.recomendar_desde("https://tienda.test", html, {"Strict-Transport-Security": "max-age=1"})
    assert d["titulo"] == "Mi tienda & más"
    ids = {s["id"] for s in d["senales"]}
    assert {"shopify", "analytics", "login", "ecommerce"} <= ids and "seguridad" in ids  # faltan CSP y nosniff
    agentes = {r["agente"]: r["plan"] for r in d["recomendados"]}
    assert agentes["probador-shopify"] == "pro" and agentes["web-mapper"] == "light"
    assert d["plan_sugerido"] == "pro" and "probador-sap" not in agentes
    d = planes.recomendar_desde("https://erp.test", "<script src='/resources/sap-ui-core.js'></script>")
    assert d["plan_sugerido"] == "empresa" and any(r["agente"] == "probador-sap" for r in d["recomendados"])


def test_las_senales_recomiendan_agentes_que_existen():
    import planes
    todos = {a["nombre"] for p in CATALOGO["planes"] for a in p["agentes"]}
    nombrados = {a for *_, agentes in planes.SENALES for a in agentes} | {a for a, _ in planes.SIEMPRE}
    nombrados |= {"analista-seguridad", "pentester-web"}
    assert nombrados <= todos, nombrados - todos

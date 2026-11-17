"""Planes de k0lmenIA como plugins: el catálogo (catalogo-planes.json), el comando `k0lmenia planes` y cómo el comando del
core le pasa los comandos al plugin pago instalado (registro en ~/.k0lmenia/planes.json). Es el mismo archivo en los
dos repos."""
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
    """Cada repo tiene todo lo de su plan y los anteriores (gratis ⊂ Pro), y nada que no esté en el catálogo."""
    agentes = {p.stem for p in (RAIZ / ".claude" / "agents").glob("*.md")}
    skills = {p.parent.name for p in (RAIZ / ".claude" / "skills").glob("*/SKILL.md")}
    esperados_a = {a["nombre"] for p in HASTA_ESTE for a in p["agentes"]}
    esperados_s = {s["nombre"] for p in HASTA_ESTE for s in p["skills"]}
    assert agentes == esperados_a, f"sobran {agentes - esperados_a}, faltan {esperados_a - agentes}"
    assert skills == esperados_s, f"sobran {skills - esperados_s}, faltan {esperados_s - skills}"


def test_catalogo_coherente():
    assert ORDEN == ["light", "pro"] and CATALOGO["marketplace"] == "k0lmenia"
    plugins = [p["plugin"] for p in CATALOGO["planes"]]
    assert plugins == ["k0lmenia", "k0lmenia-pro"]
    for i, p in enumerate(CATALOGO["planes"]):
        assert p["depende"] == plugins[:i], "cada plan depende de todos los anteriores"
        assert p["fuente"]["repo"] == p["repo"] and p["resumen"] and p["descripcion"]
        assert "precio" not in p, "nada está a la venta"
    assert "compra" not in CATALOGO
    assert "k0lmena-tmt" in CATALOGO["planes"][0]["conectores"], "k0lmenaTMT viene en el plan gratis"


@pytest.mark.skipif(not (RAIZ / "scripts" / "catalogo_planes.py").exists(), reason="el catálogo se arma en el repo de Pro")
def test_catalogo_al_dia_con_el_reparto():
    import catalogo_planes
    assert CATALOGO == catalogo_planes.construir(), "regeneralo: python scripts/catalogo_planes.py --copiar-a ../k0lmenia"


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
    pro = _addon_falso(tmp_path, "pro")
    salida = tmp_path / "salida.json"
    env = _env(tmp_path, registro, SALIDA=str(salida))
    # Solo Pro: los comandos van a Pro.
    registro.write_text(json.dumps({"pro": {"raiz": str(pro)}}), encoding="utf-8")
    assert _k0lmenia(env, tmp_path, "py", "scripts/generar_informe_generico.py", "a.json").returncode == 0
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["plan"] == "pro" and datos["args"] == ["py", "scripts/generar_informe_generico.py", "a.json"]
    assert datos["delegado"] == "1" and Path(datos["nucleo"]) == RAIZ
    # Un registro viejo de Empresa (plan que ya no existe) no cuenta: sigue ganando Pro.
    registro.write_text(json.dumps({"pro": {"raiz": str(pro)}, "empresa": {"raiz": str(_addon_falso(tmp_path, "empresa"))}}),
                        encoding="utf-8")
    _k0lmenia(env, tmp_path, "doctor")
    assert json.loads(salida.read_text(encoding="utf-8"))["plan"] == "pro"
    # Un plan desinstalado (su carpeta ya no está) no cuenta: lo corre el core.
    salida.unlink()
    registro.write_text(json.dumps({"pro": {"raiz": str(tmp_path / "ya-no-esta")}}), encoding="utf-8")
    r = _k0lmenia(env, tmp_path, "ayuda")
    assert r.returncode == 0 and "k0lmenia planes" in r.stdout and not salida.exists()
    # Un script que no está en lo instalado: lo dice (en vez del error de Python), sin ofrecer nada.
    r = _k0lmenia(env, tmp_path, "py", "scripts/no_existe_en_ningun_plan.py")
    assert r.returncode == 2 and "no está incluido en tu versión" in r.stderr


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
    assert estados["light"] == "instalado" and estados["pro"] == "instalado" and set(estados) == {"light", "pro"}
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
    texto = planes.opciones({"planes": [{"id": "light", "estado": "instalado"}, {"id": "pro", "estado": "disponible"}]})
    assert "## Comparación" in texto and "## Todas las opciones" in texto
    assert "| **En esta PC** | ✅ instalado | ⬇️ disponible |" in texto
    assert "Precio" not in texto and "USD" not in texto, "nada está a la venta"
    for p in CATALOGO["planes"]:  # todas las opciones de todos los planes
        for a in p["agentes"]:
            assert f"| `{a['nombre']}` |" in texto
        for s in p["skills"]:
            assert f"| `{s['nombre']}` |" in texto
    total = sum(len(p["agentes"]) for p in CATALOGO["planes"])
    assert f"| Agentes | {len(CATALOGO['planes'][0]['agentes'])} |" in texto and f"| {total} |" in texto
    # cada fila de la tabla tiene una celda por plan (ningún "|" suelto en las descripciones)
    filas = [l for l in texto.splitlines() if l.startswith("| `")]
    assert all(l.replace(r"\|", "").count("|") == 3 for l in filas)


def test_pro_no_se_ofrece_a_quien_no_tiene_acceso():
    """Pro es privado: a quien no lo tiene ni tiene acceso a su repo no se le muestra ni se le recomienda."""
    import planes
    pro = next(p for p in CATALOGO["planes"] if p["id"] == "pro")
    for estado_pro in ("bloqueado", "desconocido"):
        e = {"planes": [{"id": "light", "estado": "instalado"}, {"id": "pro", "estado": estado_pro}]}
        texto = planes.opciones(e)
        assert pro["nombre"] not in texto and f"| `{pro['agentes'][0]['nombre']}` |" not in texto
        d = planes.recomendar_desde("https://erp.test", "<script src='/resources/sap-ui-core.js'></script>", e=e)
        assert d["plan_sugerido"] == "light" and all(r["plan"] == "light" for r in d["recomendados"])
        assert "pro" not in d["por_plan"]


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
    assert d["plan_sugerido"] == "pro" and any(r["agente"] == "probador-sap" and r["plan"] == "pro" for r in d["recomendados"])


def test_las_senales_recomiendan_agentes_que_existen():
    import planes
    todos = {a["nombre"] for p in CATALOGO["planes"] for a in p["agentes"]}
    nombrados = {a for *_, agentes in planes.SENALES for a in agentes} | {a for a, _ in planes.SIEMPRE}
    nombrados |= {"analista-seguridad", "pentester-web"}
    assert nombrados <= todos, nombrados - todos


# ------------------------------------------------------------------ Pro completo o por paquetes
PRO = next(p for p in CATALOGO["planes"] if p["id"] == "pro")
PAQUETES = {q["id"]: q for q in PRO["paquetes"]}


def test_paquetes_de_pro_coherentes():
    """Cada agente y skill de Pro está en un solo paquete; cada paquete depende del core y de la base (la base, del core)."""
    for tipo in ("agentes", "skills"):
        en_paquetes = [n for q in PAQUETES.values() for n in q[tipo]]
        assert sorted(en_paquetes) == sorted(x["nombre"] for x in PRO[tipo]), tipo
    assert list(PAQUETES)[0] == "base"
    for pid, q in PAQUETES.items():
        assert q["plugin"] == f"k0lmenia-pro-{pid}" and q["fuente"] == {"source": "github", "repo": PRO["repo"], "ref": f"pro-{pid}"}
        assert q["depende"] == (["k0lmenia"] if pid == "base" else ["k0lmenia", "k0lmenia-pro-base"])
        assert q["resumen"] and q["descripcion"] and "precio" not in q


@pytest.mark.skipif(not (RAIZ / ".claude" / "agents" / "pentester-web.md").exists(), reason="los agentes de Pro están en su repo")
def test_cada_paquete_tiene_las_skills_que_usan_sus_agentes():
    """Un paquete instalado solo (con la base y el core) no deja a sus agentes sin las skills que nombran."""
    import re
    del_core = {s["nombre"] for s in CATALOGO["planes"][0]["skills"]}
    skills_pro = {s["nombre"] for s in PRO["skills"]}
    faltan = []
    for pid, q in PAQUETES.items():
        disponibles = set(q["skills"]) | set(PAQUETES["base"]["skills"]) | del_core
        for agente in q["agentes"]:
            texto = (RAIZ / ".claude" / "agents" / f"{agente}.md").read_text(encoding="utf-8")
            for s in skills_pro - disponibles:
                if re.search(rf"(?<![\w-]){re.escape(s)}(?![\w-])", texto):
                    faltan.append(f"{agente} ({pid}) usa {s}")
    assert not faltan, "movelas al paquete del agente o a la base en scripts/catalogo_planes.py:\n" + "\n".join(faltan)


def test_resolver_que_instalar():
    import planes
    plugins = lambda nombres: [plugin for _, _, plugin in planes.resolver(nombres)[0]]  # noqa: E731
    assert plugins(["pro"]) == plugins(["todo"]) == plugins(["k0lmenia-pro"]) == ["k0lmenia-pro"]
    assert plugins(["seguridad", "pro-performance", "k0lmenia-pro-ia"]) == [
        "k0lmenia-pro-seguridad", "k0lmenia-pro-performance", "k0lmenia-pro-ia"]
    assert plugins(["seguridad", "pro", "seguridad"]) == ["k0lmenia-pro"], "con el completo, los paquetes sobran"
    assert planes.resolver(["seguridad", "no-existe"])[1] == ["no-existe"]
    assert planes.instalar(["no-existe"]) == 2


def test_recomendar_dice_los_paquetes():
    import planes
    html = "<script src='https://cdn.shopify.com/x.js'></script><script src='/resources/sap-ui-core.js'></script>"
    d = planes.recomendar_desde("https://tienda.test", html)
    paquete = {r["agente"]: r.get("paquete") for r in d["recomendados"]}
    assert paquete["probador-shopify"] == "ecommerce" and paquete["probador-sap"] == "erp-crm"
    assert paquete["web-mapper"] is None  # del core
    assert {"ecommerce", "erp-crm"} <= set(d["paquetes_sugeridos"]) and "base" not in d["paquetes_sugeridos"]


def test_planes_dice_que_paquetes_hay_instalados(tmp_path):
    registro = tmp_path / "registro" / "planes.json"
    registro.parent.mkdir()
    base, seguridad = _addon_falso(tmp_path, "pro"), tmp_path / "pq-seguridad"
    seguridad.mkdir()
    registro.write_text(json.dumps({"pro": {"raiz": str(base)}, "paquetes": {"seguridad": {"raiz": str(seguridad)},
                                                                          "ia": {"raiz": str(tmp_path / "ya-no-esta")}}}),
                        encoding="utf-8")
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "planes.py"), "--json", "--sin-red"], cwd=tmp_path,
                       env=_env(tmp_path, registro, K0LMENIA_PROYECTO=str(tmp_path)), capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0, r.stderr
    pro = next(p for p in json.loads(r.stdout)["planes"] if p["id"] == "pro")
    instalados = {q["id"] for q in pro["paquetes"] if q["instalado"]}
    assert pro["estado"] == "instalado" and instalados == {"base", "seguridad"} and pro["completo"] is False
    texto = __import__("planes").opciones({"planes": [{"id": "light", "estado": "instalado"}, pro]})
    assert "| **seguridad** | 8 |" in texto and "✅ instalado" in texto and "#### Paquete erp-crm" in texto

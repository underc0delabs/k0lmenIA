"""Novedades al actualizar (scripts/novedades.py y su informe): lectura del CHANGELOG, qué es nuevo desde la última vez,
el resumen para el inicio de sesión del plugin (la primera vez solo marca) y el informe bilingüe; y que el plugin lleve
el CHANGELOG y lo muestre al iniciar la sesión después de actualizarse."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import construir_plugin as cp  # noqa: E402
import generar_informe_novedades as gin  # noqa: E402
import novedades as nov  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402

CHANGELOG = """# Cambios de k0lmenIA

Los cambios más relevantes, del más nuevo al más viejo.

## 2026-11-02 (19) — Asistente de ejecución manual

- **asistente-ejecucion-manual**: te acompaña paso a paso.
  - Registra aprobado o fallido.
- **triador-bugs**: busca duplicados en Jira.

## 2026-11-01 (18) — Evals para todos los agentes

- **Evals**: un caso por agente.

## 2026-10-30 (17) — Atajos de flujos

- **Atajos**: `/k0lmenia:ejecucion-manual`.

## 2026-10-23 — Manuales de usuario

- **documentador-proyecto**: documentación verificada.
"""


@pytest.fixture(autouse=True)
def _sin_portal(monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")


def test_entradas_con_y_sin_numero_y_subpuntos():
    e = nov.entradas(CHANGELOG)
    assert [x["numero"] for x in e] == [19, 18, 17, None]
    assert e[0]["titulo"] == "Asistente de ejecución manual" and e[3]["titulo"] == "Manuales de usuario"
    assert e[0]["puntos"] == ["**asistente-ejecucion-manual**: te acompaña paso a paso. · Registra aprobado o fallido.",
                              "**triador-bugs**: busca duplicados en Jira."]
    assert nov.entradas("") == [] and nov.entradas("# Solo título\n\ntexto") == []


def test_nuevas_desde_la_marca_y_respaldo_por_fecha():
    e = nov.entradas(CHANGELOG)
    assert nov.nuevas(e, None) == []  # sin marca (primera vez): no muestra el historial entero
    marca = {"encabezado": "2026-10-30 (17) — Atajos de flujos", "fecha": "2026-10-30"}
    assert [x["numero"] for x in nov.nuevas(e, marca)] == [19, 18]
    assert nov.nuevas(e, {"encabezado": e[0]["encabezado"], "fecha": e[0]["fecha"]}) == []  # ya vio la última
    # El encabezado marcado ya no existe (se renombró): vale la fecha.
    assert [x["numero"] for x in nov.nuevas(e, {"encabezado": "otro título", "fecha": "2026-10-31"})] == [19, 18]


def test_resumen_para_el_contexto_es_corto_y_lleva_el_link():
    e = nov.entradas(CHANGELOG)
    assert nov.resumen_contexto([]) == ""
    texto = nov.resumen_contexto(e * 5, maximo=8)  # 20 entradas: se corta
    lineas = texto.strip().splitlines()
    assert lineas[0].startswith("k0lmenIA se actualizó: hay 20 novedad(es)") and "primer mensaje" in lineas[0]
    assert sum(1 for l in lineas if l.startswith("- 2026")) == 8 and "… y 12 más." in texto
    assert lineas[-1] == f"Detalle completo: {nov.CHANGELOG_URL}"


def test_flujo_de_sesiones_con_la_marca(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(nov, "changelog", lambda: CHANGELOG)
    marca = tmp_path / "datos" / "novedades.json"
    # 1.ª sesión: solo marca.
    nov.main(["--contexto", "--marca", str(marca)])
    assert capsys.readouterr().out == "" and json.loads(marca.read_text(encoding="utf-8"))["fecha"] == "2026-11-02"
    # La persona venía de la 17: al actualizarse ve las 2 nuevas, una sola vez.
    marca.write_text(json.dumps({"encabezado": "2026-10-30 (17) — Atajos de flujos", "fecha": "2026-10-30"}), encoding="utf-8")
    nov.main(["--contexto", "--marca", str(marca)])
    salida = capsys.readouterr().out
    assert "hay 2 novedad(es)" in salida and "Asistente de ejecución manual" in salida and "Atajos de flujos" not in salida
    nov.main(["--contexto", "--marca", str(marca)])
    assert capsys.readouterr().out == ""


def test_contexto_nunca_falla(tmp_path, monkeypatch, capsys):
    def roto():
        raise OSError("sin permisos")
    monkeypatch.setattr(nov, "changelog", roto)
    with pytest.raises(OSError):  # fuera del modo contexto, el error se ve
        nov.main(["--sin-html", "--marca", str(tmp_path / "m.json")])
    monkeypatch.setattr(nov, "entradas", lambda t: (_ for _ in ()).throw(ValueError("x")))
    monkeypatch.setattr(nov, "changelog", lambda: CHANGELOG)
    assert nov.main(["--contexto", "--marca", str(tmp_path / "m.json")]) == 0 and capsys.readouterr().out == ""


def test_comando_a_pedido_y_su_informe(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(nov, "changelog", lambda: CHANGELOG)
    marca = tmp_path / "vistas.json"
    nov.main(["--marca", str(marca), "--salida", str(tmp_path / "out")])  # primera vez a pedido: las 3 últimas
    salida = capsys.readouterr().out
    assert "## 2026-11-02 (19)" in salida and "## 2026-10-23" not in salida and "Informe:" in salida
    datos = json.loads((tmp_path / "out" / "novedades.json").read_text(encoding="utf-8"))
    assert datos["alcance"] == "ultimas-3" and len(datos["entradas"]) == 3 and datos["total_historial"] == 4
    nov.main(["--marca", str(marca), "--sin-html"])  # ya marcadas
    assert "No hay novedades" in capsys.readouterr().out
    nov.main(["--todas", "--marca", str(marca), "--salida", str(tmp_path / "todo")])
    es = ruta_es(tmp_path / "todo" / "informe-novedades.html").read_text(encoding="utf-8")
    en = ruta_en(tmp_path / "todo" / "informe-novedades.html").read_text(encoding="utf-8")
    assert "<b>asistente-ejecucion-manual</b>" in es and "<code>/k0lmenia:ejecucion-manual</code>" in es
    assert "Cambios por entrada" in es and "#19" in es and "4 novedad(es) con 5 cambio(s)" in es
    assert 'lang="en"' in en and "Changes per entry" in en and "Whole history" in en


def test_informe_sin_novedades(tmp_path):
    p = tmp_path / "n.json"
    p.write_text(json.dumps({"alcance": "desde-la-ultima-vez", "entradas": [], "total_historial": 61}), encoding="utf-8")
    gin.generar(p, tmp_path / "i.html")
    assert "No hay novedades desde la última vez" in ruta_es(tmp_path / "i.html").read_text(encoding="utf-8")


def test_el_plugin_lleva_el_changelog_y_muestra_las_novedades_al_actualizarse(tmp_path):
    plugin = cp.construir(tmp_path / "plugin")
    assert (plugin / "CHANGELOG.md").read_text(encoding="utf-8") == (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
    (plugin / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")  # el del repo puede tener una sola entrada
    proyecto, datos = tmp_path / "proyecto", tmp_path / "datos"
    proyecto.mkdir()
    env = {k: v for k, v in os.environ.items() if k not in ("K0LMENIA_PROYECTO", "K0LMENIA_CODIGO")}
    env.update(CLAUDE_PLUGIN_DATA=str(datos), K0LMENIA_PORTAL="0")

    def sesion():
        return subprocess.run(["node", str(plugin / "bin" / "k0lmenia"), "preparar", "--contexto"], cwd=proyecto, env=env,
                              capture_output=True, text=True, encoding="utf-8").stdout
    assert "se actualizó" not in sesion()  # recién instalado: solo marca
    entradas = nov.entradas((plugin / "CHANGELOG.md").read_text(encoding="utf-8"))
    (datos / "novedades.json").write_text(json.dumps({"encabezado": entradas[2]["encabezado"], "fecha": entradas[2]["fecha"]}),
                                          encoding="utf-8")  # la persona tenía la versión de hace 2 entradas
    salida = sesion()
    assert "hay 2 novedad(es)" in salida and entradas[0]["titulo"][:40] in salida
    assert "se actualizó" not in sesion()
    r = subprocess.run(["node", str(plugin / "bin" / "k0lmenia"), "novedades", "--todas", "--sin-html"], cwd=proyecto, env=env,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and entradas[-1]["encabezado"] in r.stdout

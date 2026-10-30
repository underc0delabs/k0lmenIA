"""La sesión de ejecución manual (skill ejecucion-manual + asistente-ejecucion-manual)."""
import json
import zipfile
from pathlib import Path
from xml.dom import minidom

import pytest

import ejecucion_manual as em
from _i18n import ruta_en, ruta_es

RAIZ = Path(__file__).resolve().parents[1]
CASOS = RAIZ / "input" / "ejecucion-manual" / "casos-HU-950.ejemplo.json"


# ------------------------------------------------------------------ ejecución manual
@pytest.fixture
def sesion(tmp_path, monkeypatch):
    monkeypatch.setattr(em, "PROYECTO", tmp_path)
    p, s = em.iniciar(CASOS, "HU-950", ambiente="QA", tester="QA", salida=tmp_path / "output" / "ejecucion-manual" / "HU-950")
    return p, s


def test_carga_los_casos_y_estima_el_tiempo(sesion):
    _, s = sesion
    assert [c["id"] for c in s["casos"]] == ["CP-001", "CP-002", "CP-003", "CP-004"]
    assert s["casos"][0]["prioridad"] == "Crítica" and len(s["casos"][0]["pasos"]) == 3
    assert all(c["estado"] == "Pendiente" and c["estimado_min"] for c in s["casos"])
    assert em.siguiente(s)["caso"]["id"] == "CP-001" and em.siguiente(s)["paso"]["n"] == 1


def test_no_pisa_una_sesion_en_curso(sesion, tmp_path):
    with pytest.raises(SystemExit):
        em.iniciar(CASOS, "HU-950", salida=tmp_path / "output" / "ejecucion-manual" / "HU-950")


def test_reglas_de_registro_y_redaccion(sesion):
    _, s = sesion
    with pytest.raises(SystemExit):
        em.registrar(s, "CP-003", "Bloqueado")  # sin motivo
    with pytest.raises(SystemExit):
        em.registrar(s, "CP-004", "Fallido")  # sin obtenido ni bug
    with pytest.raises(SystemExit):
        em.registrar(s, "CP-001", "Pasó")
    c = em.registrar(s, "CP-004", "Fallido", paso=1, obtenido="Error 500; probé con password: Secreta123 y token=abc", bug="BUG-9")
    assert c["estado"] == "Fallido" and c["bugs"] == ["BUG-9"]
    assert "Secreta123" not in json.dumps(s) and "abc" not in c["pasos"][0]["obtenido"] and "[redactado]" in c["pasos"][0]["obtenido"]


def test_un_paso_fallido_cierra_el_caso_y_el_ultimo_paso_lo_aprueba(sesion):
    _, s = sesion
    for n in (1, 2, 3):
        c = em.registrar(s, "CP-001", "Aprobado", paso=n)
    assert c["estado"] == "Aprobado" and c["duracion_s"] is not None
    c = em.registrar(s, "CP-002", "Fallido", paso=1, obtenido="Descuenta igual")
    assert c["estado"] == "Fallido"


def test_las_pausas_no_cuentan_en_el_tiempo(sesion):
    _, s = sesion
    c = em._caso(s, "CP-001")
    c.update(estado="En ejecución", inicio="2026-10-28T10:00:00")
    s["pausas"] = [{"inicio": "2026-10-28T10:02:00", "fin": "2026-10-28T10:07:00"}]
    em._cerrar_caso(s, c, "Aprobado")
    c["fin"] = "2026-10-28T10:10:00"
    c["duracion_s"] = em._segundos(c["inicio"], c["fin"]) - em._pausa_dentro(s, c["inicio"], c["fin"])
    assert c["duracion_s"] == 300
    em.pausar(s)
    assert em.siguiente(s).get("pausada")
    em.retomar(s)
    assert not em.siguiente(s).get("pausada")


def test_inconsistencias_y_resultados_sin_pendientes(sesion):
    _, s = sesion
    c = em._caso(s, "CP-001")
    c["estado"] = "Aprobado"
    c["pasos"][1].update(resultado="Fallido", obtenido="x")
    em._caso(s, "CP-002")["estado"] = "Bloqueado"
    tipos = {(i["caso"], i["tipo"]) for i in em.inconsistencias(s)}
    assert ("CP-001", "Aprobado con pasos fallidos") in tipos and ("CP-002", "Bloqueado sin motivo") in tipos
    assert ("CP-001", "Sin evidencia") in tipos
    res = em.resultados_ejecucion(s)
    assert [x["id"] for x in res["casos"]] == ["CP-001", "CP-002"] and res["historia"] == "HU-950"


def test_cerrar_arma_resultados_e_informe_bilingue(sesion, tmp_path):
    p, s = sesion
    em.registrar(s, "CP-001", "Aprobado", evidencia="capturas/cp-001.png")
    em.registrar(s, "CP-002", "Fallido", obtenido="Descuenta 5 %", bug="BUG-31")
    em.registrar(s, "CP-003", "Bloqueado", motivo="Ambiente caído")
    s["casos"][1]["comentario"] = "pegué la clave: Hola123"  # editado a mano: el cierre también redacta
    em.guardar(p, s)
    analisis = tmp_path / "analisis.json"
    analisis.write_text(json.dumps({"veredicto": "No listo", "veredicto_tono": "bad", "resumen": "Falla el cupón vencido.",
                                    "publicacion": {"estado": "Pendiente de confirmación", "herramienta": "Xray"},
                                    "en": {"veredicto": "Not ready", "resumen": "The expired coupon fails."}}), encoding="utf-8")
    s2, archivos = em.cerrar(p, analisis)
    assert s2["estado"] == "Cerrada" and s2["resumen"]["por_resultado"]["Pendiente"] == 1
    rj = next(a for a in archivos if a.suffix == ".json")
    res = json.loads(rj.read_text(encoding="utf-8"))
    assert {c["id"] for c in res["casos"]} == {"CP-001", "CP-002", "CP-003"} and "BUG-31" in res["casos"][1]["motivo"]
    salida = p.parent / "informe-ejecucion-manual.html"
    es, en = ruta_es(salida).read_text(encoding="utf-8"), ruta_en(salida).read_text(encoding="utf-8")
    assert "No listo" in es and "CP-004" in es and "Pendiente de confirmación" in es
    assert "Not ready" in en and 'lang="en"' in en
    assert "Hola123" not in es and "Hola123" not in p.read_text(encoding="utf-8")


def test_cli_iniciar_registrar_estado(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(em, "PROYECTO", tmp_path)
    carpeta = tmp_path / "s"
    em.main(["iniciar", "--casos", str(CASOS), "--historia", "HU-950", "--solo", "CP-002,CP-004", "--salida", str(carpeta)])
    assert json.loads(capsys.readouterr().out)["casos"] == 2
    em.main(["registrar", "--sesion", str(carpeta), "--caso", "CP-002", "--resultado", "Aprobado"])
    capsys.readouterr()
    em.main(["estado", "--sesion", str(carpeta)])
    estado = json.loads(capsys.readouterr().out)
    assert estado["ejecutados"] == 1 and estado["pct_avance"] == 50


# ------------------------------------------------------------------ exportador
@pytest.fixture
def informe(tmp_path, monkeypatch):
    """Un informe real de k0lmenIA (el de la ejecución manual), con gráficos, KPIs y tablas."""
    monkeypatch.setattr(em, "PROYECTO", tmp_path)
    p, s = em.iniciar(CASOS, "HU-950", salida=tmp_path / "output" / "ejecucion-manual" / "HU-950")
    em.registrar(s, "CP-001", "Aprobado", evidencia="x.png")
    em.registrar(s, "CP-002", "Fallido", obtenido="Descuenta 5 %", bug="BUG-31")
    em.guardar(p, s)
    em.cerrar(p)
    return p.parent / "informe-ejecucion-manual.html"



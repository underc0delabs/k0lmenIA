"""Calidad de los informes de los agentes de exploración y auditoría: Falta información unificada, avisos del
análisis, corrección de los hallazgos manuales, evidencia de permisos, pasos de resiliencia y secretos de ZAP."""
import pytest

import _estilos_reporte

FI = {"falta_informacion": [{"id": "FI-01", "que_falta": "El largo máximo del nombre", "pregunta": "¿Cuántos caracteres acepta?"}]}


def test_falta_informacion_acepta_descripcion_como_alias():
    html = _estilos_reporte.falta_informacion([{"id": "FI-02", "descripcion": "Qué pasa sin conexión"}])
    assert "FI-02" in html and "Qué pasa sin conexión" in html
    assert _estilos_reporte.falta_informacion([]) == ""


def test_avisar_analisis_ids_inexistentes_y_severidades(capsys):
    analisis = {"notas": {"H-3": "x"}, "severidades": {"H-01": "alta"}, "descartados": [{"id": "H-02", "motivo": "y"}],
                "hallazgos": {"H-01": {"severidad": "Media"}}}
    avisos = _estilos_reporte.avisar_analisis(analisis, ["H-01", "H-02"])
    assert len(avisos) == 2
    err = capsys.readouterr().err
    assert "H-3 no está en los datos" in err and "'alta'" in err
    assert _estilos_reporte.avisar_analisis({"notas": {"H-01": "ok"}}, ["H-01"]) == []



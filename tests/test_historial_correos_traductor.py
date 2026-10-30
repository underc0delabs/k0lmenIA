"""Historial de corridas (últimas 5, con la comparación)."""
import json

import _historial

# Un tipo de historial de prueba (los informes de K0lmenIA Light registran los suyos en _historial.TIPOS).
TIPO = {"archivo": "exploracion.json", "items": lambda d: d.get("hallazgos") or [],
        "clave": lambda h: f'{h.get("categoria")}|{h.get("pagina")}|{_historial._norm(h.get("titulo"))}',
        "titulo": lambda h: h.get("titulo"),
        "metricas": [("Hallazgos", _historial._r("hallazgos"), ""), ("Links rotos", _historial._r("links_rotos"), "")]}


def _corrida(carpeta, marca, hallazgos):
    (carpeta / "exploracion.json").write_text(json.dumps({"marca": marca, "resumen": {"hallazgos": len(hallazgos), "links_rotos": len(hallazgos)},
                                                          "hallazgos": hallazgos}), encoding="utf-8")
    (carpeta / "informe-exploratorio.html").write_text("<html></html>", encoding="utf-8")


def test_archivar_guarda_las_ultimas_5(tmp_path):
    for i in range(7):
        _corrida(tmp_path, f"2026101{i}-120000", [])
        destino = _historial.archivar(tmp_path, ["exploracion.json", "informe-exploratorio.html"], "exploracion.json")
        assert (destino / "exploracion.json").exists() and not (tmp_path / "exploracion.json").exists()
    guardadas = sorted(d.name for d in (tmp_path / "historial").iterdir())
    assert len(guardadas) == 4 and guardadas[0] == "20261013-120000"
    assert _historial.archivar(tmp_path, ["exploracion.json"], "exploracion.json") is None  # no hay corrida actual


def test_comparacion_nuevos_resueltos_y_seccion(tmp_path, monkeypatch):
    monkeypatch.setitem(_historial.TIPOS, "prueba", TIPO)
    a = {"categoria": "Link roto", "titulo": "Link roto a /viejo (404)", "pagina": "/"}
    b = {"categoria": "Imagen rota", "titulo": "Imagen que no carga", "pagina": "/"}
    c = {"categoria": "Error de JavaScript", "titulo": "x is not defined", "pagina": "/x"}
    _corrida(tmp_path, "20261010-100000", [a, b])
    _historial.archivar(tmp_path, ["exploracion.json", "informe-exploratorio.html"], "exploracion.json")
    actual = {"marca": "20261011-100000", "resumen": {"hallazgos": 2, "links_rotos": 1}, "hallazgos": [dict(a, titulo="Link roto a /viejo (500)"), c]}
    cmp = _historial.comparar("prueba", actual, json.loads((next((tmp_path / "historial").iterdir()) / "exploracion.json").read_text(encoding="utf-8")))
    assert [x["titulo"] for x in cmp["nuevos"]] == ["x is not defined"]
    assert [x["titulo"] for x in cmp["resueltos"]] == ["Imagen que no carga"]
    assert len(cmp["siguen"]) == 1   # el mismo link aunque cambie el código (los números no cuentan)
    html = _historial.seccion("prueba", tmp_path, actual)
    assert "Evolución de las corridas" in html and "abrir informe" in html and "x is not defined" in html and "Imagen que no carga" in html
    assert "primera corrida" in _historial.seccion("prueba", tmp_path / "vacia", actual)



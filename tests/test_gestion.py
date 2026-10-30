"""Integración de gestión: publicación por historia y reintentos de la API."""
import http.server
import threading

import pytest

import comun
import gestion


class TrazaFalsa:
    def __init__(self, nombre, casos, hu=None):
        self.ruta = type("R", (), {"stem": nombre, "name": nombre + ".json"})()
        self.datos = {"casos": casos, **({"hu": hu} if hu else {})}

    def key_de(self, cid):
        return (self.datos["casos"].get(cid) or {}).get("key")


PATRON = r"^PROJ-(TC-)?\d+$"


def test_cp_de_otra_historia_no_se_publica():
    traza = TrazaFalsa("HU-001-xray-cloud", {"CP-001": {"key": "PROJ-45"}})
    propio = {"tags": ["HU-001", "CP-001"]}
    ajeno = {"tags": ["HU-002", "CP-001"]}
    sin_hu = {"tags": ["CP-001"]}
    directo = {"tags": ["PROJ-99"]}
    assert gestion._key_del_resultado(propio, traza, PATRON) == ("PROJ-45", None)
    key, motivo = gestion._key_del_resultado(ajeno, traza, PATRON)
    assert key is None and "otra historia" in motivo
    key, motivo = gestion._key_del_resultado(sin_hu, traza, PATRON)
    assert key is None and "@HU-001" in motivo
    assert gestion._key_del_resultado(directo, traza, PATRON) == ("PROJ-99", None)


def test_nombre_de_trazabilidad_invalido():
    with pytest.raises(comun.ErrorGestion):
        comun.Trazabilidad("../../afuera", "xray-cloud")


def test_reintento_reenvia_el_adjunto_completo(tmp_path):
    recibidos = []

    class Servidor(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            cuerpo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            recibidos.append(b"EVIDENCIA" * 50 in cuerpo)
            if len(recibidos) == 1:
                self.send_response(503)
                self.send_header("Retry-After", "1")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Servidor)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    archivo = tmp_path / "e.png"
    archivo.write_bytes(b"EVIDENCIA" * 50)
    http_ = comun.Http(f"http://127.0.0.1:{srv.server_port}")
    with open(archivo, "rb") as f:
        assert http_.post("adjunto", files={"file": ("e.png", f, "image/png")}) == {"ok": True}
    srv.shutdown()
    assert recibidos == [True, True]


def test_corte_de_red_da_error_claro(monkeypatch):
    monkeypatch.setattr(comun.time, "sleep", lambda s: None)
    with pytest.raises(comun.ErrorGestion, match="no respondió"):
        comun.Http("http://127.0.0.1:1").get("x")


def test_espera_retry_after():
    assert comun._espera_reintento("3", 0) == 3
    assert comun._espera_reintento(None, 2) == 4
    assert comun._espera_reintento("Wed, 21 Oct 2015 07:28:00 GMT", 0) >= 1

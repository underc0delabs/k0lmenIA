"""Probador de SOAP: parseo del WSDL, sobre de ejemplo e informe HTML."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "herramientas" / "soap"))

import generar_informe_soap as gi  # noqa: E402
import wsdl  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402

WSDL = """<?xml version="1.0"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
             xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
             xmlns:tns="http://ejemplo.org/clientes"
             targetNamespace="http://ejemplo.org/clientes">
  <portType name="ClientePortType">
    <operation name="GetCliente">
      <input message="tns:GetClienteReq"/>
      <output message="tns:GetClienteResp"/>
    </operation>
  </portType>
  <binding name="ClienteBinding" type="tns:ClientePortType">
    <soap:binding transport="http://schemas.xmlsoap.org/soap/http" style="document"/>
    <operation name="GetCliente">
      <soap:operation soapAction="http://ejemplo.org/clientes/GetCliente"/>
    </operation>
  </binding>
  <service name="ClienteService">
    <port name="ClientePort" binding="tns:ClienteBinding">
      <soap:address location="https://host/ws"/>
    </port>
  </service>
</definitions>"""


def test_parse_wsdl():
    info = wsdl.parse_wsdl(WSDL)
    assert info["servicio"] == "ClienteService"
    assert info["endpoint"] == "https://host/ws"
    assert info["version"] == "1.1"
    assert info["namespace"] == "http://ejemplo.org/clientes"
    ops = {o["nombre"]: o for o in info["operaciones"]}
    assert "GetCliente" in ops
    assert ops["GetCliente"]["soap_action"] == "http://ejemplo.org/clientes/GetCliente"


def test_envelope():
    env = wsdl.envelope("GetCliente", {"id": "42"}, namespace="http://ejemplo.org/clientes")
    assert "<ns:GetCliente>" in env and "<ns:id>42</ns:id>" in env
    assert 'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"' in env  # SOAP 1.1 por defecto


def test_informe(tmp_path, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    datos = {"titulo": "ClienteService — HU-010", "servicio": {"nombre": "ClienteService", "endpoint": "https://host/ws", "version": "1.1"},
             "veredicto": "1 fault mal mapeado", "veredicto_tono": "warn",
             "operaciones": [{"operacion": "GetCliente", "soap_action": "...", "resultado": "Aprobado", "detalle": "ok"}],
             "pruebas": [{"id": "CP-001", "operacion": "GetCliente", "caso": "Cliente inexistente", "resultado": "Fallido",
                          "esperado": "SOAP Fault NotFound", "obtenido": "HTTP 500"}],
             "hallazgos": [{"id": "H-01", "severidad": "Alta", "categoria": "Manejo de errores", "texto": "500 en vez de Fault",
                            "impacto": "cliente no distingue el error", "como_reproducir": "pedir un id inexistente", "recomendacion": "devolver Fault"}],
             "falta_informacion": [{"id": "FI-01", "que_falta": "Faults definidos", "pregunta": "¿qué Faults define la operación?"}]}
    (tmp_path / "a.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "a.json", tmp_path / "i.html")
    html = ruta_es(tmp_path / "i.html").read_text(encoding="utf-8")
    assert "ClienteService" in html and "500 en vez de Fault" in html and "Operaciones del servicio" in html and "FI-01" in html
    assert "pedir un id inexistente" in html


def test_json_invalido_falla(tmp_path):
    (tmp_path / "x.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        gi.generar(tmp_path / "x.json", tmp_path / "i.html")

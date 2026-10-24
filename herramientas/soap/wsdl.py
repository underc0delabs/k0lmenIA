#!/usr/bin/env python3
"""
Relevamiento de un servicio SOAP a partir de su WSDL, y generación de un sobre (envelope) de ejemplo.
Solo lectura, sin dependencias externas (usa el xml de la biblioteca estándar).

Uso (desde la raíz del repo):
    python herramientas/soap/wsdl.py --wsdl http://host/servicio?wsdl   [--salida output/soap/servicio.json]
    python herramientas/soap/wsdl.py --wsdl C:/ruta/servicio.wsdl --operacion GetUser

Qué hace:
- Lee el WSDL (de una URL o un archivo) y extrae el servicio, el endpoint, la versión de SOAP y las
  operaciones (nombre, SOAPAction, mensajes de entrada/salida).
- Con `--operacion`, imprime un sobre SOAP de ejemplo para esa operación (base para las pruebas).

No invoca el servicio ni lo modifica: eso lo hace el agente probador-soap (con confirmación para operaciones
con efecto), enviando los sobres por HTTP.
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

SOAP11 = "http://schemas.xmlsoap.org/wsdl/soap/"
SOAP12 = "http://schemas.xmlsoap.org/wsdl/soap12/"


def _ln(tag):
    """Local name de una etiqueta con namespace ({ns}tag -> tag)."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_wsdl(xml_text):
    """Parsea el texto de un WSDL. Devuelve servicio, endpoint, versión y operaciones. Puro y testeable."""
    root = ET.fromstring(xml_text)
    tns = root.get("targetNamespace")
    # soapAction por operación (de las bindings)
    acciones, soap12 = {}, False
    for binding in root.iter():
        if _ln(binding.tag) != "binding":
            continue
        for hijo in binding:
            if _ln(hijo.tag) == "binding" and hijo.get("transport"):
                if SOAP12 in (hijo.tag or ""):
                    soap12 = True
        for op in binding:
            if _ln(op.tag) != "operation":
                continue
            nombre = op.get("name")
            for sub in op:
                if _ln(sub.tag) == "operation":
                    acciones[nombre] = sub.get("soapAction", "")
                    if SOAP12 in (sub.tag or ""):
                        soap12 = True
    # operaciones del portType (con sus mensajes)
    operaciones = []
    for pt in root.iter():
        if _ln(pt.tag) != "portType":
            continue
        for op in pt:
            if _ln(op.tag) != "operation":
                continue
            nombre = op.get("name")
            inp = out = None
            for m in op:
                if _ln(m.tag) == "input":
                    inp = m.get("message") or m.get("name")
                elif _ln(m.tag) == "output":
                    out = m.get("message") or m.get("name")
            operaciones.append({"nombre": nombre, "soap_action": acciones.get(nombre, ""), "entrada": inp, "salida": out})
    # endpoint (service/port/address@location)
    endpoint, servicio = None, None
    for svc in root.iter():
        if _ln(svc.tag) != "service":
            continue
        servicio = svc.get("name")
        for port in svc:
            for addr in port:
                if _ln(addr.tag) == "address" and addr.get("location"):
                    endpoint = addr.get("location")
    return {"servicio": servicio, "endpoint": endpoint, "namespace": tns,
            "version": "1.2" if soap12 else "1.1", "operaciones": operaciones}


def envelope(operacion, params=None, namespace="http://tempuri.org/", soap12=False):
    """Sobre SOAP de ejemplo para una operación. Puro y testeable."""
    ns_env = "http://www.w3.org/2003/05/soap-envelope" if soap12 else "http://schemas.xmlsoap.org/soap/envelope/"
    cuerpo = ""
    for k, v in (params or {}).items():
        cuerpo += f"\n      <ns:{k}>{v}</ns:{k}>"
    return (f'<soapenv:Envelope xmlns:soapenv="{ns_env}" xmlns:ns="{namespace}">\n'
            f'  <soapenv:Header/>\n'
            f'  <soapenv:Body>\n'
            f'    <ns:{operacion}>{cuerpo}\n'
            f'    </ns:{operacion}>\n'
            f'  </soapenv:Body>\n'
            f'</soapenv:Envelope>')


def leer(fuente):
    if fuente.lower().startswith(("http://", "https://")):
        with urllib.request.urlopen(fuente, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    return Path(fuente).read_text(encoding="utf-8", errors="replace")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Relevamiento de un servicio SOAP por su WSDL (solo lectura).")
    ap.add_argument("--wsdl", required=True, help="URL o ruta del WSDL")
    ap.add_argument("--operacion", default="", help="imprime un sobre de ejemplo para esta operación")
    ap.add_argument("--salida", default="")
    args = ap.parse_args(argv)
    try:
        xml_text = leer(args.wsdl)
        info = parse_wsdl(xml_text)
    except (OSError, ET.ParseError) as ex:
        print(f"[soap] No se pudo leer o parsear el WSDL: {ex}", file=sys.stderr)
        return 2
    if args.operacion:
        print(envelope(args.operacion, namespace=info.get("namespace") or "http://tempuri.org/",
                       soap12=info.get("version") == "1.2"))
        return 0
    texto = json.dumps(info, ensure_ascii=False, indent=2)
    if args.salida:
        p = Path(args.salida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        print(f"[soap] Datos en {p}", file=sys.stderr)
    print(texto)
    print(f"[soap] Servicio {info.get('servicio') or '—'} (SOAP {info.get('version')}): {len(info.get('operaciones') or [])} operación(es).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

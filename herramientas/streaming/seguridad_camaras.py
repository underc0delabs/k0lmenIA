#!/usr/bin/env python3
"""
Análisis de seguridad PASIVO de cámaras IP / NVR: revisa puertos abiertos y servicios inseguros
(Telnet, FTP, HTTP sin TLS, RTSP sin autenticación) y deja anotado el firmware para que se revisen
sus CVEs. No prueba credenciales por defecto salvo que se active explícitamente en un equipo propio.

Uso (desde la raíz del repo):
    python herramientas/streaming/seguridad_camaras.py --host 192.168.1.50 [--historia HU-001]
        [--onvif-usuario admin --onvif-password ***] [--confirmar]
    (--host admite varios separados por coma)

Qué hace (de solo lectura, no intrusivo):
- Verifica que cada host esté autorizado en el .env (CAMARAS_AUTORIZADAS).
- Escaneo de puertos conocidos de cámaras (connect TCP, sin payloads de ataque).
- Detecta servicios inseguros: Telnet/FTP abiertos, HTTP sin HTTPS, RTSP que responde DESCRIBE sin auth.
- Si se dan credenciales ONVIF, lee el firmware y recuerda revisar sus CVEs (no mantiene base de CVEs).
- Deja en output/streaming/seguridad-camaras-<host o historia>/: seguridad-camaras.json e informe.

No hace DoS, fuerza bruta ni explotación. No prueba contraseñas por defecto (eso sería otro modo,
solo en equipos propios). Mismo criterio que el escaneo pasivo de ZAP del analista-seguridad.
"""
import argparse
import datetime
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
# Puertos conocidos de cámaras/NVR y qué significan.
PUERTOS = {
    21: ("FTP", "inseguro"), 23: ("Telnet", "inseguro"), 22: ("SSH", "ok"),
    80: ("HTTP", "revisar"), 443: ("HTTPS", "ok"), 554: ("RTSP", "revisar"),
    8000: ("HTTP alt / SDK", "revisar"), 8080: ("HTTP alt", "revisar"), 8554: ("RTSP alt", "revisar"),
    37777: ("Dahua SDK", "revisar"), 34567: ("NVR (Sofia)", "revisar"), 9000: ("HTTP alt", "revisar"),
}


def salir(msg, codigo=2):
    print(msg, file=sys.stderr)
    sys.exit(codigo)


def leer_env():
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _env import leer_env as _leer
    valores = _leer()
    valores.update({k: v for k, v in os.environ.items() if k.startswith(("CAMARAS_", "ONVIF_"))})
    return valores


def autorizado(host, env):
    lista = [u.strip() for u in re.split(r"[,\s]+", env.get("CAMARAS_AUTORIZADAS", "")) if u.strip()]
    if not lista:
        salir("No hay cámaras autorizadas. Agregá en el .env de la raíz:\n"
              "  CAMARAS_AUTORIZADAS=192.168.1.50, 192.168.1.51\n"
              "(solo dispositivos propios o con autorización por escrito de sus dueños).")
    # admite host o host:puerto en la lista
    if not any(host == a or a.startswith(host + ":") for a in lista):
        salir(f"{host} no está en CAMARAS_AUTORIZADAS del .env. Solo se analizan cámaras autorizadas.")


def puerto_abierto(host, puerto, timeout=1.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, puerto)) == 0
    except OSError:
        return False
    finally:
        s.close()


def rtsp_sin_auth(host, puerto=554, timeout=2.0):
    """Manda un DESCRIBE sin credenciales. 200 = responde sin pedir auth (inseguro); 401 = pide auth (ok)."""
    try:
        with socket.create_connection((host, puerto), timeout=timeout) as s:
            s.settimeout(timeout)
            pedido = (f"DESCRIBE rtsp://{host}:{puerto}/ RTSP/1.0\r\nCSeq: 1\r\n"
                      "User-Agent: k0lmenIA\r\nAccept: application/sdp\r\n\r\n")
            s.sendall(pedido.encode())
            resp = s.recv(1024).decode("latin-1", "ignore")
        m = re.search(r"RTSP/1\.0 (\d{3})", resp)
        codigo = int(m.group(1)) if m else None
        return codigo, resp.splitlines()[0] if resp else ""
    except OSError:
        return None, ""


def firmware_onvif(host, env):
    usuario = env.get("ONVIF_USUARIO")
    password = env.get("ONVIF_PASSWORD", "")
    if not usuario:
        return None
    try:
        from onvif import ONVIFCamera
    except ImportError:
        return None
    for puerto in (80, 8000):
        try:
            cam = ONVIFCamera(host, puerto, usuario, password)
            info = cam.create_devicemgmt_service().GetDeviceInformation()
            return {"marca": getattr(info, "Manufacturer", None), "modelo": getattr(info, "Model", None),
                    "firmware": getattr(info, "FirmwareVersion", None)}
        except Exception:
            continue
    return None


def analizar_host(host, env):
    res = {"host": host, "puertos_abiertos": [], "hallazgos": []}
    h = res["hallazgos"]
    abiertos = []
    for puerto, (nombre, criterio) in sorted(PUERTOS.items()):
        if puerto_abierto(host, puerto):
            abiertos.append({"puerto": puerto, "servicio": nombre})
            if criterio == "inseguro":
                h.append({"severidad": "Alta", "texto": f"{nombre} abierto (puerto {puerto}): servicio inseguro, debería estar deshabilitado."})
    res["puertos_abiertos"] = abiertos
    puertos = {p["puerto"] for p in abiertos}

    # HTTP sin HTTPS
    if 80 in puertos and 443 not in puertos:
        h.append({"severidad": "Media", "texto": "HTTP (80) abierto sin HTTPS (443): el panel viaja sin cifrar."})

    # RTSP sin autenticación
    if 554 in puertos:
        codigo, linea = rtsp_sin_auth(host, 554)
        res["rtsp"] = {"codigo": codigo, "respuesta": linea}
        if codigo == 200:
            h.append({"severidad": "Alta", "texto": "RTSP (554) responde DESCRIBE sin pedir autenticación: el stream es accesible sin credenciales."})
        elif codigo == 401:
            pass  # pide auth: correcto
        elif codigo is not None:
            h.append({"severidad": "Baja", "texto": f"RTSP (554) respondió {codigo} a un DESCRIBE sin auth (revisar manualmente)."})

    # Firmware → recordatorio de CVEs (sin base de CVEs propia)
    fw = firmware_onvif(host, env)
    if fw:
        res["dispositivo"] = fw
        if fw.get("firmware"):
            h.append({"severidad": "Baja", "texto": f"Firmware {fw.get('marca') or ''} {fw.get('modelo') or ''} {fw['firmware']}: revisá CVEs conocidos de esa versión."})

    res["estado"] = "fallo" if any(x["severidad"] == "Crítica" for x in h) else ("hallazgos" if h else "ok")
    return res


def main():
    ap = argparse.ArgumentParser(description="Análisis de seguridad pasivo de cámaras IP.")
    ap.add_argument("--host", required=True, help="IP/hostname de la cámara (varios separados por coma).")
    ap.add_argument("--historia", default="")
    ap.add_argument("--confirmar", action="store_true")
    args = ap.parse_args()

    env = leer_env()
    hosts = [x.strip() for x in args.host.split(",") if x.strip()]
    for hst in hosts:
        autorizado(hst, env)

    if not args.confirmar:
        print("Vas a analizar (pasivo, sin atacar) estas cámaras:")
        for hst in hosts:
            print(f"  - {hst}")
        if input("¿Confirmás? [s/N] ").strip().lower() not in ("s", "si", "sí", "y", "yes"):
            salir("Cancelado.", 1)

    carpeta = PROYECTO / "output" / "streaming" / f"seguridad-camaras-{args.historia or hosts[0]}"
    carpeta.mkdir(parents=True, exist_ok=True)
    try:
        sys.path.insert(0, str(RAIZ / "scripts"))
        import _historial
        _historial.archivar(carpeta, ["seguridad-camaras.json", "informe-seguridad-camaras.html"], "seguridad-camaras.json")
    except Exception as ex:
        print(f"[aviso] no se pudo archivar la corrida anterior: {ex}", file=sys.stderr)

    resultados = []
    for hst in hosts:
        print(f"[seguridad-camaras] {hst} …", file=sys.stderr)
        resultados.append(analizar_host(hst, env))

    datos = {"generado": datetime.datetime.now().isoformat(timespec="seconds"),
             "historia": args.historia or None, "hosts": resultados,
             "resumen": {"total": len(resultados),
                         "ok": sum(1 for r in resultados if r["estado"] == "ok"),
                         "con_hallazgos": sum(1 for r in resultados if r["estado"] != "ok")}}
    (carpeta / "seguridad-camaras.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        import generar_informe_seguridad_camaras
        generar_informe_seguridad_camaras.generar(carpeta / "seguridad-camaras.json", carpeta / "informe-seguridad-camaras.html")
        print(f"[seguridad-camaras] Informe: {carpeta / 'informe-seguridad-camaras.html'}", file=sys.stderr)
    except Exception as ex:
        print(f"[aviso] no se pudo generar el informe HTML: {ex}", file=sys.stderr)

    r = datos["resumen"]
    print(f"[seguridad-camaras] Listo: {r['total']} host(s) · {r['ok']} ok · {r['con_hallazgos']} con hallazgos.")
    print(f"[seguridad-camaras] Datos: {carpeta / 'seguridad-camaras.json'}")


if __name__ == "__main__":
    main()

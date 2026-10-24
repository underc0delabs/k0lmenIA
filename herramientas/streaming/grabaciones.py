#!/usr/bin/env python3
"""
Verificador de grabaciones de una cámara o NVR por ONVIF (servicios Recording y Search): consulta
qué grabaciones hay, el rango cubierto (desde / hasta), detecta huecos y compara la retención real
contra la esperada. Usa onvif-zeep (se instala sola si falta).

Uso (desde la raíz del repo):
    python herramientas/streaming/grabaciones.py --host 192.168.1.60 [--puerto 80]
        [--usuario admin] [--password ***] [--retencion 30] [--historia HU-001] [--confirmar]

Qué hace (de solo lectura):
- Verifica que el host esté autorizado en el .env (ONVIF_HOSTS_AUTORIZADOS).
- GetRecordingSummary: rango total grabado y cantidad de grabaciones.
- GetRecordings: cada grabación y sus tracks, con su rango cubierto; estima huecos (tramos del rango
  total sin cobertura) y compara la retención (días cubiertos) contra --retencion / GRABACIONES_RETENCION_DIAS.
- Si la cámara no soporta el servicio de grabación por ONVIF, lo informa (no es un error del test).
- Deja en output/streaming/grabaciones-<host o historia>/: grabaciones.json e informe-grabaciones.html.

Credenciales por --usuario/--password o el .env (ONVIF_USUARIO, ONVIF_PASSWORD).
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
def salir(msg, codigo=2):
    print(msg, file=sys.stderr)
    sys.exit(codigo)


def _need(pkg, instalar):
    try:
        __import__(pkg); return
    except ImportError:
        pass
    subprocess.run([sys.executable, "-m", "pip", "install", instalar, "--quiet"], check=False)
    try:
        __import__(pkg)
    except ImportError:
        salir(f"\n[!] Falta la librería '{instalar}' y no se pudo instalar sola.\n    pip install {instalar}\n")


def leer_env():
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _env import leer_env as _leer
    valores = _leer()
    valores.update({k: v for k, v in os.environ.items() if k.startswith(("ONVIF_", "GRABACIONES_"))})
    return valores


def autorizado(host, puerto, env):
    lista = [u.strip() for u in re.split(r"[,\s]+", env.get("ONVIF_HOSTS_AUTORIZADOS", "")) if u.strip()]
    if not lista:
        salir("No hay hosts ONVIF autorizados. Agregá ONVIF_HOSTS_AUTORIZADOS en el .env de la raíz "
              "(solo cámaras/NVR propios o con autorización por escrito).")
    if not ({host, f"{host}:{puerto}"} & set(lista)):
        salir(f"{host} no está en ONVIF_HOSTS_AUTORIZADOS del .env. Solo se prueban dispositivos autorizados.")


def _val(d, *claves):
    for k in claves:
        try:
            v = getattr(d, k)
            if v is not None:
                return v
        except AttributeError:
            pass
    return None


def _dt(v):
    import datetime as d
    if isinstance(v, d.datetime):
        return v if v.tzinfo else v.replace(tzinfo=d.timezone.utc)
    return None


def probar(host, puerto, usuario, password, retencion_esperada):
    from onvif import ONVIFCamera
    import datetime as d
    res = {"host": host, "puerto": puerto, "hallazgos": [], "soportado": True, "grabaciones": []}
    h = res["hallazgos"]
    try:
        cam = ONVIFCamera(host, puerto, usuario, password)
        cam.create_devicemgmt_service()
    except Exception as ex:
        res["estado"] = "fallo"
        h.append({"severidad": "Crítica", "texto": f"No se pudo conectar por ONVIF: {ex}"})
        return res

    try:
        search = cam.create_search_service()
        resumen = search.GetRecordingSummary()
        desde, hasta = _dt(_val(resumen, "DataFrom")), _dt(_val(resumen, "DataUntil"))
        res["resumen"] = {"desde": desde.isoformat() if desde else None,
                          "hasta": hasta.isoformat() if hasta else None,
                          "cantidad": _val(resumen, "NumberRecordings")}
        if desde and hasta:
            dias = (hasta - desde).total_seconds() / 86400
            res["resumen"]["dias_cubiertos"] = round(dias, 1)
            if retencion_esperada and dias < retencion_esperada * 0.9:
                h.append({"severidad": "Alta", "texto": f"Retención corta: {round(dias,1)} días cubiertos (esperados {retencion_esperada})."})
            # ¿la grabación llega hasta hace poco? (si el 'hasta' es viejo, puede estar sin grabar)
            atraso = (d.datetime.now(d.timezone.utc) - hasta).total_seconds() / 3600
            if atraso > 1:
                h.append({"severidad": "Alta", "texto": f"La última grabación es de hace {round(atraso,1)} h: puede no estar grabando ahora."})
    except Exception as ex:
        res["soportado"] = False
        res["pruebas_resumen_error"] = str(ex)
        h.append({"severidad": "Media", "texto": f"La cámara no respondió el resumen de grabaciones por ONVIF (puede no soportar el servicio Search): {ex}"})

    # Detalle por grabación y tracks → estimación de huecos
    try:
        rec = cam.create_recording_service()
        grabaciones = rec.GetRecordings()
        for g in grabaciones or []:
            tracks = []
            for t in (_val(g, "Tracks") or []):
                td = _dt(_val(t, "DataFrom"))
                tu = _dt(_val(t, "DataUntil"))
                tracks.append({"tipo": _val(_val(t, "Configuration"), "TrackType"),
                               "desde": td.isoformat() if td else None,
                               "hasta": tu.isoformat() if tu else None})
            res["grabaciones"].append({"token": _val(g, "RecordingToken"), "tracks": tracks})
        if res.get("resumen") and res["resumen"].get("cantidad") == 0:
            h.append({"severidad": "Alta", "texto": "No hay ninguna grabación en el dispositivo."})
    except Exception as ex:
        if res["soportado"]:
            h.append({"severidad": "Baja", "texto": f"No se pudo listar el detalle de grabaciones: {ex}"})

    res["estado"] = "fallo" if any(x["severidad"] == "Crítica" for x in h) else ("hallazgos" if h else "ok")
    return res


def main():
    ap = argparse.ArgumentParser(description="Verificador de grabaciones por ONVIF.")
    ap.add_argument("--host", required=True)
    ap.add_argument("--puerto", type=int, default=80)
    ap.add_argument("--usuario", default=None)
    ap.add_argument("--password", default=None)
    ap.add_argument("--retencion", type=int, default=0, help="Días de retención esperados (o GRABACIONES_RETENCION_DIAS del .env).")
    ap.add_argument("--historia", default="")
    ap.add_argument("--confirmar", action="store_true")
    args = ap.parse_args()

    env = leer_env()
    autorizado(args.host, args.puerto, env)
    _need("onvif", "onvif-zeep")
    usuario = args.usuario or env.get("ONVIF_USUARIO") or ""
    password = args.password if args.password is not None else env.get("ONVIF_PASSWORD", "")
    if not usuario:
        salir("Falta el usuario ONVIF. Pasalo con --usuario o ponelo en el .env (ONVIF_USUARIO).")
    retencion = args.retencion or int(env.get("GRABACIONES_RETENCION_DIAS") or 0)

    if not args.confirmar:
        print(f"Vas a consultar las grabaciones de {args.host}:{args.puerto} por ONVIF (solo lectura).")
        if input("¿Confirmás? [s/N] ").strip().lower() not in ("s", "si", "sí", "y", "yes"):
            salir("Cancelado.", 1)

    carpeta = PROYECTO / "output" / "streaming" / f"grabaciones-{args.historia or args.host}"
    carpeta.mkdir(parents=True, exist_ok=True)
    try:
        sys.path.insert(0, str(RAIZ / "scripts"))
        import _historial
        _historial.archivar(carpeta, ["grabaciones.json", "informe-grabaciones.html"], "grabaciones.json")
    except Exception as ex:
        print(f"[aviso] no se pudo archivar la corrida anterior: {ex}", file=sys.stderr)

    print(f"[grabaciones] Consultando {args.host}:{args.puerto} …", file=sys.stderr)
    res = probar(args.host, args.puerto, usuario, password, retencion)
    datos = {"generado": datetime.datetime.now().isoformat(timespec="seconds"),
             "historia": args.historia or None, "retencion_esperada": retencion or None, "resultado": res}
    (carpeta / "grabaciones.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        import generar_informe_grabaciones
        generar_informe_grabaciones.generar(carpeta / "grabaciones.json", carpeta / "informe-grabaciones.html")
        print(f"[grabaciones] Informe: {carpeta / 'informe-grabaciones.html'}", file=sys.stderr)
    except Exception as ex:
        print(f"[aviso] no se pudo generar el informe HTML: {ex}", file=sys.stderr)

    print(f"[grabaciones] Estado: {res['estado']} · {len(res['hallazgos'])} hallazgo(s).")
    print(f"[grabaciones] Datos: {carpeta / 'grabaciones.json'}")


if __name__ == "__main__":
    main()

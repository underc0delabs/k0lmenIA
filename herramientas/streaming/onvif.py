#!/usr/bin/env python3
"""
Prueba de control ONVIF de una cámara IP: información del dispositivo, perfiles y URIs de stream,
snapshot, PTZ (opcional, mueve la cámara) y capacidades de eventos (detección de movimiento).
Usa la librería onvif-zeep (se instala sola si falta). La verificación del video en sí (que el
stream reproduzca bien) la hace herramientas/streaming/probar.py sobre la URI RTSP que este devuelve.

Uso (desde la raíz del repo):
    python herramientas/streaming/onvif.py --host 192.168.1.50 [--puerto 80]
        [--usuario admin] [--password ***] [--historia HU-001] [--ptz] [--confirmar]

Qué hace (de solo lectura, salvo --ptz):
- Verifica que el host esté autorizado en el .env (ONVIF_HOSTS_AUTORIZADOS).
- GetDeviceInformation: marca, modelo, firmware, serie.
- GetProfiles + GetStreamUri: perfiles y su URI RTSP; GetSnapshotUri: y descarga una imagen de prueba.
- Capacidades de PTZ y de eventos (detección de movimiento), sin moverla.
- --ptz (acción con efecto, exige --confirmar): hace un movimiento mínimo (pan) y lo frena; si hay
  presets, consulta la lista. Nunca deja la cámara en movimiento.
- Deja en output/streaming/onvif-<host o historia>/: onvif.json e informe-onvif.html.

Las credenciales salen de --usuario/--password o del .env (ONVIF_USUARIO, ONVIF_PASSWORD); nunca de
producción salvo autorización. No prueba contraseñas ni busca cámaras: solo el host autorizado.
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
        __import__(pkg)
        return
    except ImportError:
        pass
    subprocess.run([sys.executable, "-m", "pip", "install", instalar, "--quiet"], check=False)
    try:
        __import__(pkg)
    except ImportError:
        salir(f"\n[!] Falta la librería '{instalar}' y no se pudo instalar sola.\n"
              f"    Instalala con:  pip install {instalar}\n")


def leer_env():
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _env import leer_env as _leer
    valores = _leer()
    valores.update({k: v for k, v in os.environ.items() if k.startswith("ONVIF_") or k.startswith("STREAMING_")})
    return valores


def autorizado(host, puerto, env):
    lista = [u.strip() for u in re.split(r"[,\s]+", env.get("ONVIF_HOSTS_AUTORIZADOS", "")) if u.strip()]
    if not lista:
        salir("No hay hosts ONVIF autorizados. Agregá en el .env de la raíz:\n"
              "  ONVIF_HOSTS_AUTORIZADOS=192.168.1.50, camara.local\n"
              "(solo cámaras propias o con autorización por escrito de sus dueños).")
    candidatos = {host, f"{host}:{puerto}"}
    if not (candidatos & set(lista)):
        salir(f"{host} no está en ONVIF_HOSTS_AUTORIZADOS del .env. Solo se prueban cámaras autorizadas.")


def _val(d, *claves):
    for k in claves:
        try:
            v = getattr(d, k)
            if v is not None:
                return v
        except AttributeError:
            pass
    return None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fecha_onvif(sdt):
    """Arma un datetime UTC desde la estructura UTCDateTime de GetSystemDateAndTime."""
    import datetime as _dt
    try:
        u = _val(sdt, "UTCDateTime")
        d, t = _val(u, "Date"), _val(u, "Time")
        return _dt.datetime(int(_val(d, "Year")), int(_val(d, "Month")), int(_val(d, "Day")),
                            int(_val(t, "Hour")), int(_val(t, "Minute")), int(_val(t, "Second")),
                            tzinfo=_dt.timezone.utc)
    except Exception:
        return None


def reloj_y_ntp(dev, res, h, env):
    """Deriva de reloj (cámara vs hora real), zona horaria y NTP, con chequeo contra el estándar del sitio."""
    import datetime as _dt
    deriva_aviso = _num(env.get("ONVIF_DERIVA_RELOJ_AVISO_S")) or 60.0
    tz_esperada = (env.get("ONVIF_TZ_ESPERADA") or "").strip()
    ntp_esperado = (env.get("ONVIF_NTP_ESPERADO") or "").strip()

    # Fecha/hora del sistema → deriva de reloj
    try:
        sdt = dev.GetSystemDateAndTime()
        cam_dt = _fecha_onvif(sdt)
        tz = _val(_val(sdt, "TimeZone"), "TZ")
        dst = bool(_val(sdt, "DaylightSavings"))
        info = {"timezone": tz, "dst": dst, "tipo": _val(sdt, "DateTimeType")}
        if cam_dt:
            deriva = abs((cam_dt - _dt.datetime.now(_dt.timezone.utc)).total_seconds())
            info["deriva_reloj_s"] = round(deriva, 1)
            if deriva > deriva_aviso:
                h.append({"severidad": "Alta", "texto": f"Deriva de reloj: la cámara difiere {round(deriva)}s de la hora real (aviso sobre {round(deriva_aviso)}s). Afecta la hora de las grabaciones y los eventos."})
        else:
            info["deriva_reloj_s"] = None
            h.append({"severidad": "Baja", "texto": "No se pudo leer la fecha/hora de la cámara para medir la deriva de reloj."})
        if tz_esperada and tz and tz_esperada.lower() not in str(tz).lower():
            h.append({"severidad": "Media", "texto": f"Zona horaria distinta del estándar del sitio: {tz} (esperada {tz_esperada})."})
        res["reloj"] = info
        res["pruebas"]["system_date_time"] = "ok"
    except Exception as ex:
        res["pruebas"]["system_date_time"] = "fallo"
        h.append({"severidad": "Media", "texto": f"GetSystemDateAndTime falló: {ex}"})

    # NTP
    try:
        ntp = dev.GetNTP()
        from_dhcp = bool(_val(ntp, "FromDHCP"))
        servidores = []
        for lista in ("NTPFromDHCP", "NTPManual"):
            for s in (_val(ntp, lista) or []):
                servidores.append(_val(s, "IPv4Address", "DNSname") or str(s))
        res["ntp"] = {"desde_dhcp": from_dhcp, "servidores": servidores}
        res["pruebas"]["ntp"] = "ok"
        if not servidores:
            h.append({"severidad": "Media", "texto": "La cámara no tiene servidores NTP configurados: el reloj puede derivar con el tiempo."})
        elif ntp_esperado and not any(ntp_esperado.lower() in str(s).lower() for s in servidores):
            h.append({"severidad": "Baja", "texto": f"NTP distinto del estándar del sitio: {', '.join(servidores)} (esperado {ntp_esperado})."})
    except Exception as ex:
        res["pruebas"]["ntp"] = "fallo"
        h.append({"severidad": "Baja", "texto": f"GetNTP falló: {ex}"})


def revisar_firmware(res, h, env):
    """Flaguea firmware distinto del estándar del sitio (ONVIF_FIRMWARE_ESPERADO)."""
    esperado = (env.get("ONVIF_FIRMWARE_ESPERADO") or "").strip()
    actual = (res.get("dispositivo") or {}).get("firmware")
    if esperado and actual and esperado.strip().lower() != str(actual).strip().lower():
        h.append({"severidad": "Media", "texto": f"Firmware distinto del estándar del sitio: {actual} (esperado {esperado}). Revisá si está desactualizado."})


def descargar_snapshot(uri, usuario, password, carpeta):
    import requests
    from requests.auth import HTTPDigestAuth
    for auth in (HTTPDigestAuth(usuario, password), (usuario, password), None):
        try:
            r = requests.get(uri, auth=auth, timeout=10, stream=True)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                destino = carpeta / "snapshot.jpg"
                destino.write_bytes(r.content)
                return {"ok": True, "archivo": "snapshot.jpg", "bytes": len(r.content)}
        except Exception:
            continue
    return {"ok": False, "error": "No se pudo descargar el snapshot (auth o formato)."}


def _parse_notificacion(nm):
    """De una NotificationMessage saca el topic y si indica movimiento (SimpleItem booleano en true)."""
    topic = ""
    try:
        raw = getattr(getattr(nm, "Topic", None), "_value_1", None)
        if isinstance(raw, str):
            topic = raw
        elif raw is not None:
            topic = getattr(raw, "text", None) or (raw.itertext and "".join(raw.itertext())) or ""
        topic = str(topic).strip()
    except Exception:
        topic = ""
    movimiento = False
    try:
        el = getattr(getattr(nm, "Message", None), "_value_1", None)
        if el is not None and hasattr(el, "iter"):
            for e in el.iter():
                tag = getattr(e, "tag", "")
                if isinstance(tag, str) and tag.endswith("SimpleItem"):
                    nombre = (e.get("Name") or "").lower()
                    valor = (e.get("Value") or "").lower()
                    if any(k in nombre for k in ("ismotion", "motion", "state", "isactive")) and valor in ("true", "1"):
                        movimiento = True
    except Exception:
        pass
    return topic, movimiento


def eventos_en_vivo(cam, segundos):
    """Suscribe un PullPoint de ONVIF y espera `segundos` a que llegue un evento (p. ej. movimiento)."""
    import datetime as _dt
    import time as _time
    res = {"pedido_s": segundos, "suscripcion": None, "mensajes": 0, "movimiento": False, "topics": []}
    try:
        ev = cam.create_events_service()
        ev.CreatePullPointSubscription()
        pull = cam.create_pullpoint_service()
    except Exception as ex:
        res["suscripcion"] = "fallo"
        res["error"] = str(ex)
        return res
    res["suscripcion"] = "ok"
    topics = set()
    fin = _time.monotonic() + segundos
    try:
        while _time.monotonic() < fin and not res["movimiento"]:
            restante = min(10, max(1, int(fin - _time.monotonic())))
            try:
                msgs = pull.PullMessages({"Timeout": _dt.timedelta(seconds=restante), "MessageLimit": 100})
            except Exception:
                msgs = pull.PullMessages({"Timeout": f"PT{restante}S", "MessageLimit": 100})
            for nm in (getattr(msgs, "NotificationMessage", None) or []):
                res["mensajes"] += 1
                topic, movimiento = _parse_notificacion(nm)
                if topic:
                    topics.add(topic)
                if movimiento:
                    res["movimiento"] = True
    except Exception as ex:
        res["error_pull"] = str(ex)
    finally:
        try:
            pull.Unsubscribe()
        except Exception:
            pass
    res["topics"] = sorted(topics)[:20]
    return res


def probar(host, puerto, usuario, password, carpeta, hacer_ptz, env, eventos_segundos=0):
    from onvif import ONVIFCamera
    res = {"host": host, "puerto": puerto, "hallazgos": [], "pruebas": {}}
    h = res["hallazgos"]

    try:
        cam = ONVIFCamera(host, puerto, usuario, password)
        dev = cam.create_devicemgmt_service()
    except Exception as ex:
        res["estado"] = "fallo"
        h.append({"severidad": "Crítica", "texto": f"No se pudo conectar por ONVIF: {ex}"})
        return res

    # Información del dispositivo
    try:
        info = dev.GetDeviceInformation()
        res["dispositivo"] = {"marca": _val(info, "Manufacturer"), "modelo": _val(info, "Model"),
                              "firmware": _val(info, "FirmwareVersion"), "serie": _val(info, "SerialNumber")}
        res["pruebas"]["device_information"] = "ok"
    except Exception as ex:
        res["pruebas"]["device_information"] = "fallo"
        h.append({"severidad": "Alta", "texto": f"GetDeviceInformation falló: {ex}"})

    # Capacidades
    try:
        caps = dev.GetCapabilities({"Category": "All"})
        res["capacidades"] = {"ptz": bool(_val(caps, "PTZ")), "eventos": bool(_val(caps, "Events")),
                              "media": bool(_val(caps, "Media")), "imaging": bool(_val(caps, "Imaging"))}
        res["pruebas"]["capabilities"] = "ok"
    except Exception as ex:
        res["pruebas"]["capabilities"] = "fallo"
        h.append({"severidad": "Media", "texto": f"GetCapabilities falló: {ex}"})

    # Reloj (deriva), zona horaria, NTP y firmware vs. estándar del sitio
    reloj_y_ntp(dev, res, h, env)
    revisar_firmware(res, h, env)

    # Perfiles y URIs de stream / snapshot
    perfiles_out = []
    primer_token = None
    try:
        media = cam.create_media_service()
        perfiles = media.GetProfiles()
        for p in perfiles:
            token = _val(p, "token", "_token")
            if primer_token is None:
                primer_token = token
            entrada = {"nombre": _val(p, "Name"), "token": token}
            try:
                uri = media.GetStreamUri({"StreamSetup": {"Stream": "RTP-Unicast",
                                          "Transport": {"Protocol": "RTSP"}}, "ProfileToken": token})
                entrada["rtsp"] = _val(uri, "Uri")
            except Exception as ex:
                entrada["rtsp_error"] = str(ex)
            perfiles_out.append(entrada)
        res["perfiles"] = perfiles_out
        res["pruebas"]["profiles"] = "ok"
        if not perfiles_out:
            h.append({"severidad": "Alta", "texto": "La cámara no expone perfiles de media por ONVIF."})
    except Exception as ex:
        res["pruebas"]["profiles"] = "fallo"
        h.append({"severidad": "Alta", "texto": f"GetProfiles falló: {ex}"})

    # Snapshot
    if primer_token:
        try:
            snap_uri = media.GetSnapshotUri({"ProfileToken": primer_token})
            uri = _val(snap_uri, "Uri")
            res["snapshot"] = {"uri": uri}
            res["snapshot"].update(descargar_snapshot(uri, usuario, password, carpeta))
            res["pruebas"]["snapshot"] = "ok" if res["snapshot"].get("ok") else "fallo"
            if not res["snapshot"].get("ok"):
                h.append({"severidad": "Media", "texto": "No se pudo descargar el snapshot de la cámara."})
        except Exception as ex:
            res["pruebas"]["snapshot"] = "fallo"
            h.append({"severidad": "Media", "texto": f"GetSnapshotUri falló: {ex}"})

    # Eventos / detección de movimiento (capacidad y, con --eventos N, en vivo)
    try:
        if res.get("capacidades", {}).get("eventos"):
            ev = cam.create_events_service()
            props = ev.GetEventProperties()
            res["eventos"] = {"disponible": True, "topics": bool(_val(props, "TopicSet"))}
            res["pruebas"]["events"] = "ok"
            if eventos_segundos and eventos_segundos > 0:
                print(f"[onvif]   esperando eventos {eventos_segundos}s (generá movimiento frente a la cámara) …", file=sys.stderr)
                en_vivo = eventos_en_vivo(cam, eventos_segundos)
                res["eventos"]["en_vivo"] = en_vivo
                if en_vivo.get("suscripcion") != "ok":
                    res["pruebas"]["events_live"] = "fallo"
                    h.append({"severidad": "Media", "texto": f"No se pudo suscribir a los eventos en vivo (pull-point): {en_vivo.get('error', 'sin detalle')}"})
                elif en_vivo.get("movimiento"):
                    res["pruebas"]["events_live"] = "ok"
                else:
                    res["pruebas"]["events_live"] = "ok"
                    h.append({"severidad": "Baja", "texto": f"No llegó ningún evento de movimiento en {eventos_segundos}s ({en_vivo.get('mensajes', 0)} mensaje(s) recibidos). ¿Generaste movimiento y está activada la detección en la cámara?"})
        else:
            res["eventos"] = {"disponible": False}
            res["pruebas"]["events"] = "n/a"
            if eventos_segundos and eventos_segundos > 0:
                h.append({"severidad": "Baja", "texto": "Se pidió esperar eventos pero la cámara no declara capacidad de eventos por ONVIF."})
    except Exception as ex:
        res["pruebas"]["events"] = "fallo"
        h.append({"severidad": "Baja", "texto": f"Servicio de eventos presente pero GetEventProperties falló: {ex}"})

    # PTZ
    if res.get("capacidades", {}).get("ptz") and primer_token:
        try:
            ptz = cam.create_ptz_service()
            presets = ptz.GetPresets({"ProfileToken": primer_token})
            res["ptz"] = {"presets": len(presets) if presets else 0}
            res["pruebas"]["ptz_presets"] = "ok"
            if hacer_ptz:
                ptz.ContinuousMove({"ProfileToken": primer_token,
                                    "Velocity": {"PanTilt": {"x": 0.1, "y": 0.0}}})
                import time
                time.sleep(0.6)
                ptz.Stop({"ProfileToken": primer_token, "PanTilt": True, "Zoom": True})
                res["ptz"]["movimiento"] = "ok (pan mínimo y frenado)"
                res["pruebas"]["ptz_move"] = "ok"
        except Exception as ex:
            res["pruebas"]["ptz_presets"] = "fallo"
            h.append({"severidad": "Media", "texto": f"PTZ falló: {ex}"})
    elif hacer_ptz:
        h.append({"severidad": "Baja", "texto": "Se pidió PTZ pero la cámara no declara capacidad PTZ."})

    res["estado"] = "fallo" if any(x["severidad"] == "Crítica" for x in h) else ("hallazgos" if h else "ok")
    return res


def main():
    ap = argparse.ArgumentParser(description="Prueba de control ONVIF de una cámara IP.")
    ap.add_argument("--host", required=True, help="IP o hostname de la cámara.")
    ap.add_argument("--puerto", type=int, default=80, help="Puerto ONVIF (80 por defecto).")
    ap.add_argument("--usuario", default=None, help="Usuario ONVIF (o ONVIF_USUARIO del .env).")
    ap.add_argument("--password", default=None, help="Contraseña ONVIF (o ONVIF_PASSWORD del .env).")
    ap.add_argument("--historia", default="", help="HU-XXX para la trazabilidad y la carpeta de salida.")
    ap.add_argument("--ptz", action="store_true", help="Hace un movimiento PTZ mínimo (acción con efecto; exige --confirmar).")
    ap.add_argument("--eventos", type=int, default=0, help="Segundos que espera eventos en vivo (pull-point) para ver la detección de movimiento (0 = no).")
    ap.add_argument("--confirmar", action="store_true", help="Saltea la confirmación (la persona ya autorizó).")
    args = ap.parse_args()

    env = leer_env()
    autorizado(args.host, args.puerto, env)
    _need("onvif", "onvif-zeep")
    _need("requests", "requests")

    usuario = args.usuario or env.get("ONVIF_USUARIO") or ""
    password = args.password if args.password is not None else env.get("ONVIF_PASSWORD", "")
    if not usuario:
        salir("Falta el usuario ONVIF. Pasalo con --usuario o ponelo en el .env (ONVIF_USUARIO).")

    if args.ptz and not args.confirmar:
        salir("--ptz mueve la cámara (acción con efecto). Volvé a correr con --confirmar si estás autorizado.")
    if not args.confirmar:
        print(f"Vas a consultar por ONVIF la cámara {args.host}:{args.puerto} (solo lectura).")
        if input("¿Confirmás? [s/N] ").strip().lower() not in ("s", "si", "sí", "y", "yes"):
            salir("Cancelado.", 1)

    nombre = args.historia or args.host
    carpeta = PROYECTO / "output" / "streaming" / f"onvif-{nombre}"
    carpeta.mkdir(parents=True, exist_ok=True)

    try:
        sys.path.insert(0, str(RAIZ / "scripts"))
        import _historial
        _historial.archivar(carpeta, ["onvif.json", "informe-onvif.html", "snapshot.jpg"], "onvif.json")
    except Exception as ex:
        print(f"[aviso] no se pudo archivar la corrida anterior: {ex}", file=sys.stderr)

    print(f"[onvif] Consultando {args.host}:{args.puerto} …", file=sys.stderr)
    eventos_segundos = args.eventos or int(env.get("ONVIF_EVENTOS_ESPERA_S") or 0)
    res = probar(args.host, args.puerto, usuario, password, carpeta, args.ptz, env, eventos_segundos)
    datos = {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"),
        "historia": args.historia or None,
        "ptz_ejecutado": bool(args.ptz),
        "eventos_esperados_s": eventos_segundos or None,
        "resultado": res,
    }
    (carpeta / "onvif.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        import generar_informe_onvif
        generar_informe_onvif.generar(carpeta / "onvif.json", carpeta / "informe-onvif.html")
        print(f"[onvif] Informe: {carpeta / 'informe-onvif.html'}", file=sys.stderr)
    except Exception as ex:
        print(f"[aviso] no se pudo generar el informe HTML: {ex}", file=sys.stderr)

    print(f"[onvif] Estado: {res['estado']} · {len(res['hallazgos'])} hallazgo(s).")
    print(f"[onvif] Datos: {carpeta / 'onvif.json'}")


if __name__ == "__main__":
    main()

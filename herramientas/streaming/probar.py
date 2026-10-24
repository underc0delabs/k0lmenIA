#!/usr/bin/env python3
"""
Verificación de streaming y playback con ffprobe/ffmpeg. Prueba que una fuente de video levante y
revisa sus propiedades (códec, resolución, FPS, bitrate, audio, keyframes/GOP), la latencia de
arranque (time-to-first-frame), la continuidad (errores de decodificación, frames caídos) y,
opcionalmente, la estabilidad en el tiempo (soak con reconexión) y la carga (N conexiones a la vez).
Sirve para cámaras IP (RTSP/ONVIF), transmisiones en vivo (RTMP/HLS/DASH), WebRTC servido por HTTP
y playback de VOD. Para el control de la cámara (PTZ, snapshot, eventos) está herramientas/streaming/onvif.py.

Uso (desde la raíz del repo):
    python herramientas/streaming/probar.py --fuente rtsp://cam.local/stream [--historia HU-001]
        [--segundos 10] [--transporte tcp] [--estabilidad 60] [--conexiones 10] [--confirmar]
    (--fuente admite varias separadas por coma)

Qué hace (de solo lectura; no guarda ni retransmite el stream):
- Verifica que cada fuente esté autorizada en el .env (STREAMING_FUENTES_AUTORIZADAS).
- ffprobe: metadatos del contenedor y de cada pista (video y audio), sin descargar el stream.
- ffprobe (frames): intervalo de keyframes (GOP), que marca cuánto tarda en "enganchar" y el seek.
- ffmpeg: lee --segundos a un sink nulo para medir latencia de arranque (TTFF), frames
  decodificados vs. esperados, frames caídos/duplicados y errores de decodificación.
- --estabilidad N: lee N segundos (soak) con reconexión automática (http/rtmp) para detectar
  interrupciones y reconexiones en el tiempo.
- --conexiones N: abre N lecturas en paralelo (prueba de carga acotada de la misma fuente) y reporta
  cuántas levantan, su FPS y sus errores. Para carga de un sistema completo, el performance-mapper.
- Deja en output/streaming/<historia o host>/: streaming.json e informe-streaming.html. La corrida
  anterior pasa a historial/ (últimas 5).

Requiere ffmpeg y ffprobe en el PATH (https://ffmpeg.org/download.html).
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[2]

PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
# Umbrales por defecto (se pueden pisar con STREAMING_* en el .env).
FPS_MINIMO = 10.0           # por debajo, el video se ve a saltos
LATENCIA_AVISO_S = 3.0      # conectar debería ser rápido
TTFF_AVISO_S = 4.0          # tiempo hasta el primer frame
GOP_AVISO_S = 4.0           # intervalo de keyframes largo = enganche y seek lentos
CAIDA_FRAMES_AVISO = 0.05   # 5% de frames caídos o faltantes


def salir(msg, codigo=2):
    print(msg, file=sys.stderr)
    sys.exit(codigo)


def leer_env():
    """El .env de la raíz (o K0LMENA_ENV_FILE), con el lector común de k0lmenIA; las variables
    STREAMING_* del entorno pisan a las del archivo."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _env import leer_env as _leer
    valores = _leer()
    valores.update({k: v for k, v in os.environ.items() if k.startswith("STREAMING_")})
    return valores


def autorizada(fuente, env):
    lista = [u.strip().rstrip("/") for u in re.split(r"[,\s]+", env.get("STREAMING_FUENTES_AUTORIZADAS", "")) if u.strip()]
    if not lista:
        salir("No hay fuentes autorizadas. Agregá en el .env de la raíz:\n"
              "  STREAMING_FUENTES_AUTORIZADAS=rtsp://cam.local/stream, https://cdn.mi-app.com/live/\n"
              "(solo dispositivos o streams propios o con autorización por escrito de sus dueños).")
    f = fuente.rstrip("/")
    if not any(f == a or f.startswith(a + "/") or f.startswith(a) for a in lista):
        salir(f"{fuente} no está en STREAMING_FUENTES_AUTORIZADAS del .env. Solo se prueban fuentes autorizadas.")


def binarios():
    for b in ("ffprobe", "ffmpeg"):
        if not shutil.which(b):
            salir(f"No encuentro {b}. Instalá ffmpeg (incluye ffprobe): https://ffmpeg.org/download.html\n"
                  "Windows: `winget install Gyan.FFmpeg` · Mac: `brew install ffmpeg` · Linux: el paquete ffmpeg de tu distro.")


def es_rtsp(fuente):
    return urlparse(fuente).scheme.lower() == "rtsp"


def admite_reconexion(fuente):
    """Las flags -reconnect de ffmpeg aplican a http(s)/rtmp; en RTSP no hay reconexión de entrada."""
    return urlparse(fuente).scheme.lower() in ("http", "https", "rtmp", "rtmps")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fps(avg):
    """'30000/1001' -> 29.97; '25/1' -> 25.0."""
    if not avg or avg == "0/0":
        return None
    try:
        n, d = avg.split("/")
        d = float(d)
        return round(float(n) / d, 2) if d else None
    except ValueError:
        return _num(avg)


def ffprobe(fuente, transporte, timeout_s):
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams"]
    if es_rtsp(fuente):
        cmd += ["-rtsp_transport", transporte]
    cmd += [fuente]
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return None, None, "ffprobe superó el tiempo de espera: la fuente no respondió."
    latencia = round(time.monotonic() - t0, 2)
    if r.returncode != 0 or not r.stdout.strip():
        return None, latencia, (r.stderr.strip() or "ffprobe no pudo leer la fuente.")
    try:
        return json.loads(r.stdout), latencia, None
    except json.JSONDecodeError:
        return None, latencia, "ffprobe devolvió una respuesta ilegible."


def keyframes(fuente, transporte, timeout_s):
    """Intervalo de keyframes (GOP): lee ~6s de frames y mide la distancia entre keyframes."""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
           "-show_entries", "frame=key_frame,pkt_pts_time,best_effort_timestamp_time",
           "-read_intervals", "%+6", "-of", "json"]
    if es_rtsp(fuente):
        cmd += ["-rtsp_transport", transporte]
    cmd += [fuente]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        frames = json.loads(r.stdout).get("frames", [])
    except json.JSONDecodeError:
        return None
    tiempos = []
    for fr in frames:
        if str(fr.get("key_frame")) == "1":
            t = _num(fr.get("pkt_pts_time")) or _num(fr.get("best_effort_timestamp_time"))
            if t is not None:
                tiempos.append(t)
    if len(tiempos) < 2:
        return {"gop_frames": None, "intervalo_s": None, "keyframes_vistos": len(tiempos)}
    difs = [b - a for a, b in zip(tiempos, tiempos[1:]) if b > a]
    intervalo = round(sum(difs) / len(difs), 2) if difs else None
    return {"intervalo_s": intervalo, "keyframes_vistos": len(tiempos)}


def leer_stream(fuente, transporte, segundos, timeout_s, reconectar=False):
    """Lee `segundos` del stream a un sink nulo midiendo, mientras corre, la latencia de arranque
    (TTFF), los frames por tramo (para ver interrupciones) y las reconexiones."""
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-progress", "pipe:1", "-loglevel", "warning"]
    if reconectar and admite_reconexion(fuente):
        cmd += ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "2"]
    if es_rtsp(fuente):
        cmd += ["-rtsp_transport", transporte]
    cmd += ["-i", fuente, "-t", str(segundos), "-f", "null", "-"]

    errores = []
    reconexiones = 0

    def drenar_stderr(pipe):
        nonlocal reconexiones
        for linea in pipe:
            linea = linea.rstrip("\n")
            if not linea.strip():
                continue
            errores.append(linea)
            if re.search(r"(?i)reconnect|re-?connecting|will reconnect", linea):
                reconexiones += 1

    t0 = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    except OSError as ex:
        return {"error": f"No se pudo iniciar ffmpeg: {ex}"}

    hilo_err = threading.Thread(target=drenar_stderr, args=(proc.stderr,), daemon=True)
    hilo_err.start()

    # Watchdog: si ffmpeg no termina solo (-t) dentro del margen, lo matamos.
    muerto = {"v": False}

    def matar():
        if proc.poll() is None:
            muerto["v"] = True
            proc.kill()
    wd = threading.Timer(timeout_s, matar)
    wd.start()

    ttff = None
    muestras = []  # (t_wall, frame, out_time_s)
    prog = {}
    try:
        for linea in proc.stdout:
            k, _, v = linea.partition("=")
            k, v = k.strip(), v.strip()
            prog[k] = v
            if k == "frame":
                fr = int(v) if v.isdigit() else 0
                if ttff is None and fr >= 1:
                    ttff = round(time.monotonic() - t0, 2)
            if k == "progress":  # fin de un bloque de progreso
                fr = int(prog.get("frame", 0) or 0)
                ot = (int(prog.get("out_time_us", 0) or 0)) / 1_000_000
                muestras.append((round(time.monotonic() - t0, 2), fr, round(ot, 2)))
    finally:
        proc.wait()
        wd.cancel()
        hilo_err.join(timeout=1)

    if muerto["v"] and not muestras:
        return {"error": "La lectura superó el tiempo de espera: la fuente no respondió."}

    frame_final = int(prog.get("frame", 0) or 0)
    # Interrupciones: tramos donde el tiempo avanzó pero no entraron frames nuevos.
    interrupciones = 0
    en_hueco = False
    for (t1, f1, _), (t2, f2, _) in zip(muestras, muestras[1:]):
        hueco = (t2 - t1) > 1.0 and f2 == f1
        if hueco and not en_hueco:
            interrupciones += 1
        en_hueco = hueco
    tramos = [f2 - f1 for (_, f1, _), (_, f2, _) in zip(muestras, muestras[1:])]

    return {
        "frames": frame_final,
        "caidos": int(prog.get("drop_frames", 0) or 0),
        "duplicados": int(prog.get("dup_frames", 0) or 0),
        "duracion_leida_s": round((int(prog.get("out_time_us", 0) or 0)) / 1_000_000, 2),
        "errores_decodificacion": len(errores),
        "muestra_errores": errores[:5],
        "ttff_s": ttff,
        "reconexiones": reconexiones,
        "interrupciones": interrupciones,
        "tramos": tramos[:60],
    }


def carga_concurrente(fuente, transporte, conexiones, segundos, timeout_s):
    """Abre `conexiones` lecturas en paralelo de la misma fuente y agrega el resultado."""
    def una(_):
        return leer_stream(fuente, transporte, segundos, timeout_s)
    with ThreadPoolExecutor(max_workers=conexiones) as ex:
        res = list(ex.map(una, range(conexiones)))
    ok = [r for r in res if "error" not in r and r.get("frames", 0) > 0]
    fps = []
    for r in ok:
        if r.get("duracion_leida_s"):
            fps.append(r["frames"] / r["duracion_leida_s"])
    return {
        "conexiones": conexiones,
        "exitosas": len(ok),
        "fallidas": conexiones - len(ok),
        "fps_promedio": round(sum(fps) / len(fps), 1) if fps else None,
        "errores_total": sum(r.get("errores_decodificacion", 0) for r in ok),
        "reconexiones_total": sum(r.get("reconexiones", 0) for r in ok),
    }


def analizar(fuente, probe, latencia, kf, cont, estab, carga, env):
    """Arma el registro de una fuente y sus hallazgos según los umbrales."""
    fps_min = _num(env.get("STREAMING_FPS_MINIMO")) or FPS_MINIMO
    lat_aviso = _num(env.get("STREAMING_LATENCIA_AVISO_S")) or LATENCIA_AVISO_S
    ttff_aviso = _num(env.get("STREAMING_TTFF_AVISO_S")) or TTFF_AVISO_S
    gop_aviso = _num(env.get("STREAMING_GOP_AVISO_S")) or GOP_AVISO_S

    video = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)
    fmt = probe.get("format", {})
    fps = _fps(video.get("avg_frame_rate"))
    ancho, alto = video.get("width"), video.get("height")
    dur = _num(fmt.get("duration"))

    reg = {
        "fuente": fuente,
        "latencia_conexion_s": latencia,
        "ttff_s": (cont or {}).get("ttff_s") if isinstance(cont, dict) else None,
        "contenedor": fmt.get("format_long_name") or fmt.get("format_name"),
        "tipo": "VOD" if dur else "En vivo / continuo",
        "duracion_s": dur,
        "video": {
            "codec": video.get("codec_name"),
            "resolucion": f"{ancho}x{alto}" if ancho and alto else None,
            "fps": fps,
            "bitrate_kbps": round(_num(video.get("bit_rate")) / 1000) if _num(video.get("bit_rate")) else None,
            "keyframe_intervalo_s": (kf or {}).get("intervalo_s") if kf else None,
        } if video else None,
        "audio": {
            "codec": audio.get("codec_name"),
            "sample_rate": audio.get("sample_rate"),
            "canales": audio.get("channels"),
        } if audio else None,
        "continuidad": cont,
        "estabilidad": estab,
        "carga": carga,
        "hallazgos": [],
    }

    h = reg["hallazgos"]
    if not video:
        h.append({"severidad": "Crítica", "texto": "La fuente no tiene pista de video."})
    else:
        if fps is not None and fps < fps_min:
            h.append({"severidad": "Alta", "texto": f"FPS bajo: {fps} (mínimo esperado {fps_min}). El video se ve a saltos."})
        if not ancho or not alto:
            h.append({"severidad": "Media", "texto": "No se pudo determinar la resolución del video."})
        ki = (kf or {}).get("intervalo_s")
        if ki is not None and ki > gop_aviso:
            h.append({"severidad": "Media", "texto": f"Intervalo de keyframes largo: {ki}s (aviso sobre {gop_aviso}s). Tarda en enganchar y en hacer seek."})
    if audio is None:
        h.append({"severidad": "Baja", "texto": "La fuente no tiene pista de audio (puede ser esperado en cámaras)."})
    if latencia is not None and latencia > lat_aviso:
        h.append({"severidad": "Media", "texto": f"Latencia de conexión alta: {latencia}s (aviso sobre {lat_aviso}s)."})
    if isinstance(cont, dict) and "error" not in cont:
        ttff = cont.get("ttff_s")
        if ttff is not None and ttff > ttff_aviso:
            h.append({"severidad": "Media", "texto": f"Latencia de arranque alta: {ttff}s hasta el primer frame (aviso sobre {ttff_aviso}s)."})
        if cont.get("errores_decodificacion", 0) > 0:
            h.append({"severidad": "Alta", "texto": f"{cont['errores_decodificacion']} error(es) de decodificación durante la captura."})
        esperados = (fps or 0) * cont.get("duracion_leida_s", 0)
        caidos = cont.get("caidos", 0)
        if esperados and caidos / esperados > CAIDA_FRAMES_AVISO:
            h.append({"severidad": "Alta", "texto": f"{caidos} frames caídos de ~{round(esperados)} esperados (>{CAIDA_FRAMES_AVISO:.0%})."})
    elif isinstance(cont, dict) and cont.get("error"):
        h.append({"severidad": "Alta", "texto": cont["error"]})

    if isinstance(estab, dict) and "error" not in estab:
        if estab.get("interrupciones", 0) > 0:
            h.append({"severidad": "Alta", "texto": f"{estab['interrupciones']} interrupción(es) del stream durante la prueba de estabilidad ({estab.get('duracion_leida_s')}s)."})
        if estab.get("reconexiones", 0) > 0:
            h.append({"severidad": "Media", "texto": f"{estab['reconexiones']} reconexión(es) durante la prueba de estabilidad."})
    elif isinstance(estab, dict) and estab.get("error"):
        h.append({"severidad": "Alta", "texto": f"Estabilidad: {estab['error']}"})

    if isinstance(carga, dict):
        if carga.get("fallidas", 0) > 0:
            sev = "Alta" if carga["fallidas"] > carga["conexiones"] / 2 else "Media"
            h.append({"severidad": sev, "texto": f"Carga: {carga['fallidas']} de {carga['conexiones']} conexiones no levantaron."})
        if carga.get("errores_total", 0) > 0:
            h.append({"severidad": "Media", "texto": f"Carga: {carga['errores_total']} errores de decodificación con {carga['conexiones']} conexiones a la vez."})

    reg["estado"] = "fallo" if any(x["severidad"] == "Crítica" for x in h) else ("hallazgos" if h else "ok")
    return reg


def probar_fuente(fuente, args, env):
    print(f"[streaming] Probando {fuente} …", file=sys.stderr)
    timeout_probe = max(15, args.segundos + 10)
    timeout_cont = max(30, args.segundos * 3 + 15)

    probe, latencia, err = ffprobe(fuente, args.transporte, timeout_probe)
    if err:
        return {"fuente": fuente, "latencia_conexion_s": latencia, "estado": "fallo",
                "hallazgos": [{"severidad": "Crítica", "texto": f"No se pudo abrir la fuente: {err}"}],
                "video": None, "audio": None, "continuidad": None, "estabilidad": None, "carga": None}

    kf = keyframes(fuente, args.transporte, timeout_probe)
    cont = leer_stream(fuente, args.transporte, args.segundos, timeout_cont)

    estab = None
    if args.estabilidad:
        print(f"[streaming]   estabilidad: {args.estabilidad}s …", file=sys.stderr)
        estab = leer_stream(fuente, args.transporte, args.estabilidad, args.estabilidad * 2 + 20, reconectar=True)

    carga = None
    if args.conexiones and args.conexiones > 1:
        print(f"[streaming]   carga: {args.conexiones} conexiones …", file=sys.stderr)
        carga = carga_concurrente(fuente, args.transporte, args.conexiones, min(args.segundos, 10), timeout_cont)

    return analizar(fuente, probe, latencia, kf, cont, estab, carga, env)


def main():
    ap = argparse.ArgumentParser(description="Verificación de streaming y playback con ffprobe/ffmpeg.")
    ap.add_argument("--fuente", required=True, help="URL del stream o archivo (varias separadas por coma).")
    ap.add_argument("--historia", default="", help="HU-XXX para la trazabilidad y la carpeta de salida.")
    ap.add_argument("--segundos", type=int, default=10, help="Segundos de captura para la prueba de continuidad.")
    ap.add_argument("--transporte", default="tcp", choices=["tcp", "udp"], help="Transporte RTSP (tcp por defecto, más estable).")
    ap.add_argument("--estabilidad", type=int, default=0, help="Segundos de soak para medir interrupciones y reconexiones (0 = no).")
    ap.add_argument("--conexiones", type=int, default=0, help="N lecturas en paralelo de la misma fuente (prueba de carga acotada).")
    ap.add_argument("--confirmar", action="store_true", help="Saltea la confirmación (la persona ya autorizó).")
    args = ap.parse_args()

    env = leer_env()
    binarios()
    fuentes = [f.strip() for f in args.fuente.split(",") if f.strip()]
    for f in fuentes:
        autorizada(f, env)

    if not args.confirmar:
        print("Vas a probar estas fuentes (solo lectura, sin guardar ni retransmitir):")
        for f in fuentes:
            print(f"  - {f}")
        if args.conexiones and args.conexiones > 1:
            print(f"  (+ prueba de carga: {args.conexiones} conexiones a la vez)")
        if input("¿Confirmás? [s/N] ").strip().lower() not in ("s", "si", "sí", "y", "yes"):
            salir("Cancelado.", 1)

    resultados = [probar_fuente(f, args, env) for f in fuentes]

    host = urlparse(fuentes[0]).hostname or "streaming"
    carpeta = PROYECTO / "output" / "streaming" / (args.historia or host)
    carpeta.mkdir(parents=True, exist_ok=True)

    try:
        sys.path.insert(0, str(RAIZ / "scripts"))
        import _historial
        _historial.archivar(carpeta, ["streaming.json", "informe-streaming.html"], "streaming.json")
    except Exception as ex:
        print(f"[aviso] no se pudo archivar la corrida anterior: {ex}", file=sys.stderr)

    datos = {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"),
        "historia": args.historia or None,
        "segundos_captura": args.segundos,
        "transporte": args.transporte,
        "estabilidad_s": args.estabilidad or None,
        "conexiones": args.conexiones or None,
        "fuentes": resultados,
        "resumen": {
            "total": len(resultados),
            "ok": sum(1 for r in resultados if r["estado"] == "ok"),
            "con_hallazgos": sum(1 for r in resultados if r["estado"] == "hallazgos"),
            "fallo": sum(1 for r in resultados if r["estado"] == "fallo"),
        },
    }
    (carpeta / "streaming.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        import generar_informe_streaming
        generar_informe_streaming.generar(carpeta / "streaming.json", carpeta / "informe-streaming.html")
        print(f"[streaming] Informe: {carpeta / 'informe-streaming.html'}", file=sys.stderr)
    except Exception as ex:
        print(f"[aviso] no se pudo generar el informe HTML: {ex}", file=sys.stderr)

    r = datos["resumen"]
    print(f"[streaming] Listo: {r['total']} fuente(s) · {r['ok']} ok · {r['con_hallazgos']} con hallazgos · {r['fallo']} con fallo.")
    print(f"[streaming] Datos: {carpeta / 'streaming.json'}")


if __name__ == "__main__":
    main()

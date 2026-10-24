#!/usr/bin/env python3
"""
Calidad de imagen de una cámara: toma una captura por fuente y la evalúa con OpenCV
(frames negros, desenfoque y congelamiento) para los problemas objetivos. Los que necesitan
criterio (lente obstruida o sucia, cámara movida de su encuadre, contraluz, IR que no conmuta de
noche) los juzga el agente calidad-imagen mirando la captura que este deja. Opcionalmente compara
contra una referencia para detectar que la cámara se movió.

Uso (desde la raíz del repo):
    python herramientas/streaming/calidad_imagen.py --fuente rtsp://cam.local/stream [--historia HU-001]
        [--referencia ref.jpg] [--freeze 2] [--confirmar]
    (--fuente admite varias separadas por coma; cada una puede ser un RTSP/HTTP o un archivo de imagen)

Qué hace (de solo lectura):
- Verifica que cada fuente esté autorizada en el .env (STREAMING_FUENTES_AUTORIZADAS).
- Toma una captura (ffmpeg si es un stream; usa el archivo si es una imagen).
- OpenCV: brillo medio (negro), varianza del Laplaciano (desenfoque) y, con --freeze N, compara dos
  capturas separadas N segundos (congelamiento).
- --referencia: compara contra una imagen de referencia y estima cuánto cambió (cámara movida).
- Deja en output/streaming/calidad-<host o historia>/: calidad.json, informe-calidad.html y
  capturas/ con cada imagen (para la revisión con visión del agente).

Requiere ffmpeg (para capturar de un stream) y opencv-python-headless (se instala solo si falta).
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[2]

PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
BRILLO_NEGRO = 15.0     # por debajo, la imagen está prácticamente negra
BLUR_MINIMO = 100.0     # varianza del Laplaciano; por debajo, desenfocada
FREEZE_DIF = 1.0        # diferencia media entre dos capturas; por debajo, congelada
MOVIDA_DIF = 25.0       # diferencia media contra la referencia; por encima, la cámara se movió/cambió


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
        salir(f"\n[!] Falta la librería '{instalar}' y no se pudo instalar sola.\n    Instalala con:  pip install {instalar}\n")


def leer_env():
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _env import leer_env as _leer
    valores = _leer()
    valores.update({k: v for k, v in os.environ.items() if k.startswith("STREAMING_")})
    return valores


def autorizada(fuente, env):
    if Path(fuente).exists():
        return  # archivo local de imagen: no es una fuente de red
    lista = [u.strip().rstrip("/") for u in re.split(r"[,\s]+", env.get("STREAMING_FUENTES_AUTORIZADAS", "")) if u.strip()]
    if not lista:
        salir("No hay fuentes autorizadas. Agregá STREAMING_FUENTES_AUTORIZADAS en el .env de la raíz "
              "(solo dispositivos o streams propios o con autorización por escrito).")
    f = fuente.rstrip("/")
    if not any(f == a or f.startswith(a) for a in lista):
        salir(f"{fuente} no está en STREAMING_FUENTES_AUTORIZADAS del .env. Solo se prueban fuentes autorizadas.")


def es_stream(fuente):
    return urlparse(fuente).scheme.lower() in ("rtsp", "http", "https", "rtmp", "rtmps")


def capturar(fuente, destino, timeout_s=30):
    """Deja una imagen en `destino`. Si la fuente es un archivo, la copia; si es un stream, usa ffmpeg."""
    if Path(fuente).exists():
        shutil.copyfile(fuente, destino)
        return True
    if not shutil.which("ffmpeg"):
        salir("No encuentro ffmpeg (hace falta para capturar de un stream). https://ffmpeg.org/download.html")
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if urlparse(fuente).scheme.lower() == "rtsp":
        cmd += ["-rtsp_transport", "tcp"]
    cmd += ["-i", fuente, "-frames:v", "1", "-q:v", "2", str(destino)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0 and Path(destino).exists()


def evaluar(cv2, np, img_path):
    img = cv2.imread(str(img_path))
    if img is None:
        return {"error": "No se pudo leer la imagen capturada."}
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brillo = float(gris.mean())
    blur = float(cv2.Laplacian(gris, cv2.CV_64F).var())
    h, w = gris.shape[:2]
    return {"ancho": w, "alto": h, "brillo": round(brillo, 1), "nitidez": round(blur, 1)}


def diferencia(cv2, np, a, b):
    """Diferencia media de brillo entre dos imágenes (redimensiona la segunda a la primera)."""
    ia, ib = cv2.imread(str(a)), cv2.imread(str(b))
    if ia is None or ib is None:
        return None
    ga = cv2.cvtColor(ia, cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(ib, cv2.COLOR_BGR2GRAY)
    if ga.shape != gb.shape:
        gb = cv2.resize(gb, (ga.shape[1], ga.shape[0]))
    return round(float(np.abs(ga.astype("float") - gb.astype("float")).mean()), 2)


def analizar_fuente(cv2, np, fuente, carpeta, freeze_s, referencia):
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", urlparse(fuente).hostname or Path(fuente).stem or "cam").strip("-")
    capturas = carpeta / "capturas"
    capturas.mkdir(parents=True, exist_ok=True)
    img1 = capturas / f"{slug}.jpg"

    reg = {"fuente": fuente, "captura": f"capturas/{img1.name}", "hallazgos": []}
    h = reg["hallazgos"]
    if not capturar(fuente, img1):
        reg["estado"] = "fallo"
        h.append({"severidad": "Crítica", "texto": "No se pudo capturar una imagen de la fuente."})
        return reg

    m = evaluar(cv2, np, img1)
    if "error" in m:
        reg["estado"] = "fallo"
        h.append({"severidad": "Crítica", "texto": m["error"]})
        return reg
    reg["metricas"] = m

    if m["brillo"] < BRILLO_NEGRO:
        h.append({"severidad": "Alta", "texto": f"Imagen prácticamente negra (brillo {m['brillo']})."})
    if m["nitidez"] < BLUR_MINIMO:
        h.append({"severidad": "Alta", "texto": f"Imagen desenfocada (nitidez {m['nitidez']} < {BLUR_MINIMO}). Puede ser lente sucia o fuera de foco."})

    # Congelamiento: segunda captura N segundos después
    if freeze_s and es_stream(fuente):
        time.sleep(freeze_s)
        img2 = capturas / f"{slug}-2.jpg"
        if capturar(fuente, img2):
            d = diferencia(cv2, np, img1, img2)
            reg["metricas"]["dif_congelamiento"] = d
            if d is not None and d < FREEZE_DIF:
                h.append({"severidad": "Alta", "texto": f"Imagen congelada: casi sin cambios en {freeze_s}s (diferencia {d})."})

    # Referencia: ¿se movió la cámara?
    if referencia and Path(referencia).exists():
        d = diferencia(cv2, np, referencia, img1)
        reg["metricas"]["dif_referencia"] = d
        if d is not None and d > MOVIDA_DIF:
            h.append({"severidad": "Media", "texto": f"La imagen difiere bastante de la referencia (diferencia {d}): la cámara pudo moverse o cambió la escena."})

    reg["estado"] = "fallo" if any(x["severidad"] == "Crítica" for x in h) else ("hallazgos" if h else "ok")
    # Nota para la revisión con visión del agente
    reg["revisar_con_vision"] = ["lente obstruida o sucia", "cámara movida del encuadre", "contraluz", "modo IR de noche"]
    return reg


def main():
    ap = argparse.ArgumentParser(description="Calidad de imagen de cámaras con OpenCV.")
    ap.add_argument("--fuente", required=True, help="RTSP/HTTP o archivo de imagen (varias separadas por coma).")
    ap.add_argument("--historia", default="", help="HU-XXX para la trazabilidad y la carpeta de salida.")
    ap.add_argument("--freeze", type=int, default=2, help="Segundos entre dos capturas para detectar congelamiento (0 = no).")
    ap.add_argument("--referencia", default=None, help="Imagen de referencia para detectar que la cámara se movió.")
    ap.add_argument("--confirmar", action="store_true", help="Saltea la confirmación.")
    args = ap.parse_args()

    env = leer_env()
    fuentes = [f.strip() for f in args.fuente.split(",") if f.strip()]
    for f in fuentes:
        autorizada(f, env)
    _need("cv2", "opencv-python-headless")
    _need("numpy", "numpy")
    import cv2
    import numpy as np

    if not args.confirmar:
        print("Vas a capturar y evaluar una imagen de estas fuentes (solo lectura):")
        for f in fuentes:
            print(f"  - {f}")
        if input("¿Confirmás? [s/N] ").strip().lower() not in ("s", "si", "sí", "y", "yes"):
            salir("Cancelado.", 1)

    host = urlparse(fuentes[0]).hostname or "camaras"
    carpeta = PROYECTO / "output" / "streaming" / f"calidad-{args.historia or host}"
    carpeta.mkdir(parents=True, exist_ok=True)
    try:
        sys.path.insert(0, str(RAIZ / "scripts"))
        import _historial
        _historial.archivar(carpeta, ["calidad.json", "informe-calidad.html"], "calidad.json")
    except Exception as ex:
        print(f"[aviso] no se pudo archivar la corrida anterior: {ex}", file=sys.stderr)

    resultados = []
    for f in fuentes:
        print(f"[calidad] {f} …", file=sys.stderr)
        resultados.append(analizar_fuente(cv2, np, f, carpeta, args.freeze, args.referencia))

    datos = {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"),
        "historia": args.historia or None,
        "fuentes": resultados,
        "resumen": {"total": len(resultados),
                    "ok": sum(1 for r in resultados if r["estado"] == "ok"),
                    "con_hallazgos": sum(1 for r in resultados if r["estado"] == "hallazgos"),
                    "fallo": sum(1 for r in resultados if r["estado"] == "fallo")},
    }
    (carpeta / "calidad.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        import generar_informe_calidad
        generar_informe_calidad.generar(carpeta / "calidad.json", carpeta / "informe-calidad.html")
        print(f"[calidad] Informe: {carpeta / 'informe-calidad.html'}", file=sys.stderr)
    except Exception as ex:
        print(f"[aviso] no se pudo generar el informe HTML: {ex}", file=sys.stderr)

    r = datos["resumen"]
    print(f"[calidad] Listo: {r['total']} · {r['ok']} ok · {r['con_hallazgos']} con hallazgos · {r['fallo']} fallo.")
    print(f"[calidad] Datos: {carpeta / 'calidad.json'}")


if __name__ == "__main__":
    main()

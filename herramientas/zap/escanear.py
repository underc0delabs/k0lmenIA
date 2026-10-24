#!/usr/bin/env python3
"""
Escaneo de seguridad web con OWASP ZAP, en Docker. Modo PASIVO (baseline) por defecto y modo
ACTIVO (full scan) solo con autorización explícita.

Uso (desde la raíz del repo):
    python herramientas/zap/escanear.py --url https://staging.mi-app.com [--historia HU-001]
                                        [--minutos 1] [--activo] [--confirmar]

Qué hace:
- Verifica que la URL esté autorizada en el .env (SEGURIDAD_URLS_AUTORIZADAS).
- Pide confirmación (salvo --confirmar, para cuando la persona ya confirmó).
- Pasivo (zap-baseline.py, por defecto): recorre el sitio con el spider durante --minutos y
  analiza las respuestas sin enviar ataques ni modificar datos.
- Activo (--activo, zap-full-scan.py): además del recorrido, ZAP envía payloads de ataque
  (inyección, XSS, etc.) contra la URL autorizada. Es intrusivo y puede crear o modificar datos,
  así que exige autorización explícita de pruebas activas (PENTEST_AUTORIZADO=si en el .env o
  --autorizado) y confirmación. Nunca en producción salvo autorización escrita. No hace DoS ni
  ataca terceros.
- Deja en output/seguridad/<historia o host>/<fecha>/: zap.json (resultado), zap-nativo.html
  (reporte de ZAP), zap.log y el informe de k0lmenIA (informe-seguridad.html).

Requiere Docker en ejecución. La imagen se puede cambiar con ZAP_IMAGEN en el .env.
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[2]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
IMAGEN_POR_DEFECTO = "ghcr.io/zaproxy/zaproxy:stable"


def leer_env():
    """El .env de la raíz (o K0LMENA_ENV_FILE), con el lector común de k0lmenIA; las variables
    SEGURIDAD_* y ZAP_* del entorno pisan a las del archivo."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _env import leer_env as _leer
    valores = _leer()
    valores.update({k: v for k, v in os.environ.items() if k.startswith(("SEGURIDAD_", "ZAP_"))})
    return valores


def salir(msg, codigo=2):
    print(msg, file=sys.stderr)
    sys.exit(codigo)


def autorizada(url, env):
    lista = [u.strip().rstrip("/") for u in re.split(r"[,\s]+", env.get("SEGURIDAD_URLS_AUTORIZADAS", "")) if u.strip()]
    if not lista:
        salir("No hay URLs autorizadas. Agregá en el .env de la raíz:\n"
              "  SEGURIDAD_URLS_AUTORIZADAS=https://staging.mi-app.com\n"
              "(solo sitios propios o con autorización por escrito de sus dueños).")
    u = url.rstrip("/")
    if not any(u == a or u.startswith(a + "/") for a in lista):
        salir(f"{url} no está en SEGURIDAD_URLS_AUTORIZADAS del .env. Solo se escanean sitios autorizados.")


def docker_disponible():
    if not shutil.which("docker"):
        salir("No encuentro Docker. Instalalo (Docker Desktop) para correr ZAP.")
    r = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True)
    if r.returncode != 0:
        salir("Docker está instalado pero no está corriendo: abrí Docker Desktop y volvé a intentar.")


def main():
    for flujo in (sys.stdout, sys.stderr):  # acentos bien en la consola de Windows
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Escaneo de seguridad con OWASP ZAP (pasivo por defecto; activo con autorización)")
    ap.add_argument("--url", required=True, help="URL de inicio del sitio a escanear (autorizada en el .env)")
    ap.add_argument("--historia", help="HU-XXX para la trazabilidad y la carpeta de salida")
    ap.add_argument("--minutos", type=int, default=1, help="minutos de recorrido del spider (1 a 10, por defecto 1)")
    ap.add_argument("--activo", action="store_true", help="escaneo activo (full scan): ZAP envía payloads de ataque; intrusivo y solo autorizado")
    ap.add_argument("--autorizado", action="store_true", help="confirma por CLI la autorización para el escaneo activo (equivale a PENTEST_AUTORIZADO=si)")
    ap.add_argument("--confirmar", action="store_true", help="no preguntar (la persona ya confirmó)")
    args = ap.parse_args()

    p = urlparse(args.url)
    if p.scheme not in ("http", "https") or not p.netloc:
        salir("La URL tiene que empezar con http:// o https://.")
    if not 1 <= args.minutos <= 10:
        salir("--minutos tiene que estar entre 1 y 10.")
    if args.historia and not re.match(r"^[A-Za-z]+-\d+$", args.historia):
        salir("--historia tiene que ser un ID como HU-001.")
    env = leer_env()
    autorizada(args.url, env)

    modo = "activo" if args.activo else "pasivo"
    if args.activo:
        autorizado = args.autorizado or re.match(r"^(s(i|í)?|true|1)$", str(env.get("PENTEST_AUTORIZADO", "")).strip(), re.I)
        if not autorizado:
            salir("El escaneo activo es intrusivo (envía ataques y puede modificar datos). Requiere autorización\n"
                  "explícita: agregá PENTEST_AUTORIZADO=si al .env de la raíz o pasá --autorizado, solo para un\n"
                  "sitio propio o con autorización por escrito de sus dueños, y nunca en producción sin ese permiso.")

    if not args.confirmar:
        if not sys.stdin.isatty() or os.environ.get("CI"):
            salir("Sin terminal interactiva: agregá --confirmar (solo si la persona ya autorizó este escaneo).")
        aviso = (f"Escaneo ACTIVO (intrusivo: envía payloads de ataque y puede crear o modificar datos) de {args.url}"
                 if args.activo else f"Escaneo pasivo de {args.url} (~{args.minutos} min de recorrido)")
        try:
            r = input(f"{aviso}. ¿Confirmás? (s/N): ")
        except EOFError:
            r = ""
        if not re.match(r"^s(i|í)?$", r.strip(), re.I):
            salir("Cancelado.", 1)

    docker_disponible()
    sello = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    carpeta = PROYECTO / "output" / "seguridad" / (args.historia or p.hostname) / sello
    carpeta.mkdir(parents=True, exist_ok=True)

    imagen = env.get("ZAP_IMAGEN") or IMAGEN_POR_DEFECTO
    script = "zap-full-scan.py" if args.activo else "zap-baseline.py"
    cmd = ["docker", "run", "--rm", "-v", f"{carpeta}:/zap/wrk:rw", imagen,
           script, "-t", args.url, "-m", str(args.minutos),
           "-J", "zap.json", "-r", "zap-nativo.html", "-I"]
    print(f"ZAP {'full scan (activo)' if args.activo else 'baseline (pasivo)'} · {args.url} · salida en {carpeta.relative_to(PROYECTO).as_posix()}")
    # El escaneo activo tarda bastante más que el pasivo: margen más amplio por fase de ataque.
    margen = 45 if args.activo else 15
    with open(carpeta / "zap.log", "w", encoding="utf-8") as log:
        try:
            r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, "MSYS_NO_PATHCONV": "1"},
                               timeout=(args.minutos + margen) * 60)
        except subprocess.TimeoutExpired:
            salir(f"El escaneo superó el tiempo máximo ({args.minutos + margen} min). Revisá {carpeta.relative_to(PROYECTO).as_posix()}/zap.log.", 1)
    # zap-baseline: 0 sin alertas, 1 FAIL, 2 WARN, 3 error del escaneo (con -I, WARN no hace fallar).
    resultado = carpeta / "zap.json"
    if not resultado.exists():
        cola = (carpeta / "zap.log").read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
        salir("ZAP no generó resultados (código %s). Últimas líneas del log:\n%s" % (r.returncode, "\n".join(cola)), 1)

    informe = carpeta / "informe-seguridad.html"
    g = subprocess.run([sys.executable, str(RAIZ / "scripts" / "generar_informe_seguridad.py"), str(resultado), str(informe),
                        "--url", args.url, "--modo", modo] + (["--historia", args.historia] if args.historia else []),
                       capture_output=True, text=True)
    print(f"Resultado: {resultado.relative_to(PROYECTO).as_posix()}")
    if g.returncode != 0:
        detalle = (g.stderr or g.stdout).strip()[-800:]
        salir(f"ZAP terminó, pero no se pudo generar el informe:\n{detalle}", 1)
    print(f"Informe:   {informe.relative_to(PROYECTO).as_posix()}")


if __name__ == "__main__":
    main()

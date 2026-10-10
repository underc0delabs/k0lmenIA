#!/usr/bin/env python3
"""
Revisa que el entorno de k0lmenIA esté listo y dice qué falta y cómo resolverlo.

Uso (desde la raíz del repo):
    python scripts/doctor.py          (en Mac/Linux: python3 scripts/doctor.py)

Revisa: Python y sus librerías, Node/npm, k0lmena instalado, navegadores de Playwright, Newman,
Java (JMeter), Docker (seguridad web), k6 y JMeter, el .env y las variables de los conectores
habilitados. Nunca muestra valores del .env: solo si cada variable está o falta.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
K0 = RAIZ / "herramientas" / "k0lmena"
sys.path.insert(0, str(RAIZ / "scripts"))
from _env import leer_env, archivo_env  # noqa: E402

OK, AVISO, FALTA = "OK  ", "!   ", "X   "
resumen = {"ok": 0, "aviso": 0, "falta": 0}

# Variables que necesita cada conector MCP para funcionar (las de OAuth no necesitan nada).
VARIABLES_CONECTOR = {
    "azure-devops": ["ADO_ORGANIZACION", "ADO_PAT"],
    "qtm4j": ["QTM4J_API_KEY"],
    "qmetry": ["QMETRY_API_KEY"],
    "aio-tests": ["AIO_MCP_URL", "AIO_API_TOKEN"],
    "k0lmena-tmt": ["K0LMENA_TMT_TOKEN"],
}
VARIABLES_GESTION = {
    "xray-cloud": ["GESTION_PROYECTO", "XRAY_CLOUD_CLIENT_ID", "XRAY_CLOUD_CLIENT_SECRET", "JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"],
    "xray-dc": ["GESTION_PROYECTO", "XRAY_DC_URL", "XRAY_DC_TOKEN"],
    "qtm4j": ["GESTION_PROYECTO", "QTM4J_API_KEY"],
    "aio": ["GESTION_PROYECTO", "AIO_API_TOKEN"],
}


def linea(estado, texto, ayuda=""):
    clave = {OK: "ok", AVISO: "aviso", FALTA: "falta"}[estado]
    resumen[clave] += 1
    print(f"  {estado}{texto}" + (f"\n        → {ayuda}" if ayuda else ""))


def comando(*args):
    try:
        r = subprocess.run(list(args), capture_output=True, text=True, timeout=30,
                           shell=(os.name == "nt" and args[0] in ("npm", "npx", "newman")))
        return (r.stdout or r.stderr).strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def version_mayor(texto):
    m = re.search(r"(\d+)\.(\d+)", texto or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def seccion(titulo):
    print(f"\n{titulo}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    py = "python" if os.name == "nt" else "python3"
    print("k0lmenIA · revisión del entorno")

    seccion("Python")
    v = sys.version_info
    if (v.major, v.minor) >= (3, 10):
        linea(OK, f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        linea(FALTA, f"Python {v.major}.{v.minor} (se necesita 3.10 o superior)", "Instalá Python 3.10+ desde https://www.python.org/downloads/")
    faltan = [m for m in ("openpyxl", "tabulate", "requests") if not _importable(m)]
    if faltan:
        linea(AVISO, f"Faltan librerías: {', '.join(faltan)} (los scripts las instalan solos la primera vez)",
              f"{py} -m pip install -r requirements.txt")
    else:
        linea(OK, "Librerías de Python (openpyxl, tabulate, requests)")

    seccion("Node.js y k0lmena")
    node = comando("node", "--version")
    if not node:
        linea(FALTA, "Node.js no está instalado", "Instalá Node.js 22 LTS desde https://nodejs.org")
    elif version_mayor(node) and version_mayor(node)[0] >= 20:
        linea(OK, f"Node.js {node}" + ("" if version_mayor(node)[0] >= 22 else " (mobile necesita 22+)"))
    else:
        linea(FALTA, f"Node.js {node} (se necesita 20 o superior; 22 LTS recomendado)", "Actualizá Node.js desde https://nodejs.org")
    if (K0 / "node_modules").exists():
        linea(OK, "k0lmena instalado (herramientas/k0lmena/node_modules)")
    else:
        linea(FALTA, "k0lmena no está instalado", "npm install   (desde la raíz del repo)")
    navegadores = _carpeta_playwright()
    if navegadores and any(navegadores.glob("chromium*")):
        linea(OK, "Navegadores de Playwright")
    else:
        linea(AVISO, "No encuentro los navegadores de Playwright (web y ejecución E2E)", "cd herramientas/k0lmena && npx playwright install chromium")
    if comando("newman", "--version"):
        linea(OK, "Newman (colecciones de Postman)")
    else:
        linea(AVISO, "Newman no está instalado (solo para ejecutor-api)", "npm install -g newman")

    seccion("Performance y seguridad (opcionales)")
    k6 = K0 / "tools" / "k6" / ("k6.exe" if os.name == "nt" else "k6")
    linea(OK, "k6") if k6.exists() or shutil.which("k6") else linea(AVISO, "k6 no está instalado", "npm run bootstrap:k6")
    jmeter = list((K0 / "tools" / "jmeter").glob("apache-jmeter-*/bin/ApacheJMeter.jar")) if (K0 / "tools" / "jmeter").exists() else []
    linea(OK, "JMeter") if jmeter or os.environ.get("JMETER_HOME") else linea(AVISO, "JMeter no está instalado", "npm run bootstrap:jmeter")
    java = comando("java", "-version")
    if java:
        linea(OK, f"Java ({java.splitlines()[0]})")
    else:
        linea(AVISO, "Java no está instalado (lo necesita JMeter)", "Instalá Java 8+ (por ejemplo, Temurin 21: https://adoptium.net)")
    if not shutil.which("docker"):
        linea(AVISO, "Docker no está instalado (lo necesita el escaneo de seguridad con ZAP)", "Instalá Docker Desktop: https://www.docker.com/products/docker-desktop/")
    elif comando("docker", "info", "--format", "{{.ServerVersion}}"):
        linea(OK, "Docker en ejecución")
    else:
        linea(AVISO, "Docker está instalado pero no está corriendo", "Abrí Docker Desktop antes de un escaneo de seguridad")

    seccion("Configuración (.env)")
    archivo = archivo_env()
    env = {**leer_env(archivo), **{k: v for k, v in os.environ.items()}}
    if not archivo.exists():
        linea(FALTA, f"No existe {archivo.name}", "Copiá .env.example a .env y completá lo que uses (cp .env.example .env)")
    else:
        linea(OK, f"{archivo.name} encontrado")
        for nombre, para in (("APP_URL", "la app a probar (ejecución E2E)"), ("BASEURL", "la automatización web de k0lmena")):
            if env.get(nombre):
                linea(OK, f"{nombre} definida")
            else:
                linea(AVISO, f"{nombre} vacía: {para}", f"Completala en {archivo.name}")
    herramienta = env.get("GESTION_HERRAMIENTA", "")
    if herramienta:
        faltan = [n for n in VARIABLES_GESTION.get(herramienta, []) if not env.get(n)]
        if herramienta not in VARIABLES_GESTION:
            linea(FALTA, f"GESTION_HERRAMIENTA={herramienta} no es válida", "Usá xray-cloud, xray-dc, qtm4j o aio")
        elif faltan:
            linea(FALTA, f"Gestión ({herramienta}): faltan {', '.join(faltan)}", "Completalas en el .env (ver .env.example)")
        else:
            linea(OK, f"Gestión de pruebas: {herramienta}")

    seccion("Conectores MCP habilitados")
    habilitados = []
    for f in (RAIZ / ".claude" / "settings.json", RAIZ / ".claude" / "settings.local.json"):
        try:
            habilitados += json.loads(f.read_text(encoding="utf-8")).get("enabledMcpjsonServers", [])
        except (OSError, ValueError):
            pass
    for nombre in dict.fromkeys(habilitados):
        faltan = [n for n in VARIABLES_CONECTOR.get(nombre, []) if not env.get(n)]
        if faltan:
            linea(FALTA, f"{nombre}: faltan {', '.join(faltan)}", "Completalas en el .env (ver CONECTORES.md)")
        elif nombre in ("atlassian", "figma"):
            linea(OK, f"{nombre} (se autoriza con tu cuenta desde /mcp la primera vez)")
        else:
            linea(OK, nombre)

    print(f"\nResultado: {resumen['ok']} OK · {resumen['aviso']} avisos · {resumen['falta']} faltantes")
    if resumen["falta"]:
        print("Resolvé lo marcado con X y volvé a correr el doctor.")
    sys.exit(1 if resumen["falta"] else 0)


def _importable(modulo):
    try:
        __import__(modulo)
        return True
    except ImportError:
        return False


def _carpeta_playwright():
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"])
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


if __name__ == "__main__":
    main()

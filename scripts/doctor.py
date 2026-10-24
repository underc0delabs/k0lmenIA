#!/usr/bin/env python3
"""
Revisa que el entorno de k0lmenIA esté listo y dice qué falta y cómo resolverlo.

Uso (desde la raíz del repo):
    python scripts/doctor.py [--seccion <nombre>] [--rapido] [--json]     (en Mac/Linux: python3)
    npm run doctor

Secciones: python, node, herramientas, fuentes, env, integraciones, conectores, repo y extras.
  --seccion   revisa solo una (o varias, separadas por coma): --seccion env,integraciones
  --rapido    saltea los chequeos lentos (red, Docker, Mailpit)
  --json      salida para máquinas: [{"seccion", "estado": ok|aviso|falta, "texto", "ayuda"}]

Revisa Python y sus librerías, Node/npm, k0lmena y los navegadores de Playwright, Newman, k6, JMeter,
Java, Docker, Mailpit, las fuentes de los informes y de la web, el .env (y que cada bloque que uses
esté completo y coherente), los conectores MCP habilitados, git y lo que necesitan el portal, el
monitoreo y los evals. Nunca muestra valores del .env: solo si cada variable está, falta o es inválida.
Sale con código 1 si falta algo obligatorio.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[1]
K0 = RAIZ / "herramientas" / "k0lmena"
sys.path.insert(0, str(RAIZ / "scripts"))
from _env import leer_env, archivo_env  # noqa: E402

OK, AVISO, FALTA = "OK  ", "!   ", "X   "
resumen = {"ok": 0, "aviso": 0, "falta": 0}
RESULTADOS = []
_SALIDA = {"json": False, "seccion": ""}

# Variables que necesita cada conector MCP para funcionar (las de OAuth no necesitan nada).
# "A|B+C" = A, o bien B y C juntas. ADO_PAT solo hace falta si la autenticación es por PAT.
VARIABLES_CONECTOR = {
    "azure-devops": ["ADO_ORGANIZACION", "ADO_PAT"],
    "qtm4j": ["QTM4J_API_KEY"],
    "qmetry": ["QMETRY_API_KEY"],
    "aio-tests": ["AIO_MCP_URL", "AIO_API_TOKEN"],
    "k0lmena-tmt": ["K0LMENA_TMT_TOKEN"],
    "github": ["GITHUB_TOKEN"],
    "asana": ["ASANA_CLIENT_ID", "ASANA_CLIENT_SECRET"],
    "youtrack": ["YOUTRACK_URL", "YOUTRACK_TOKEN"],
}
# Se autorizan con tu cuenta (OAuth) desde /mcp; los de token opcional, solo si ese token está vacío.
CONECTORES_OAUTH = ("atlassian", "figma", "figma-desktop", "clickup", "trello", "notion", "shortcut", "asana")
CONECTORES_TOKEN_OPCIONAL = {"gitlab": "GITLAB_TOKEN", "linear": "LINEAR_API_KEY", "monday": "MONDAY_API_TOKEN"}
VARIABLES_GESTION = {
    "xray-cloud": ["GESTION_PROYECTO", "XRAY_CLOUD_CLIENT_ID", "XRAY_CLOUD_CLIENT_SECRET", "JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"],
    "xray-dc": ["GESTION_PROYECTO", "XRAY_DC_URL", "XRAY_DC_TOKEN|XRAY_DC_USER+XRAY_DC_PASSWORD"],
    "qtm4j": ["GESTION_PROYECTO", "QTM4J_API_KEY"],
    "aio": ["GESTION_PROYECTO", "AIO_API_TOKEN"],
    "zephyr-scale": ["GESTION_PROYECTO", "ZEPHYR_API_TOKEN", "JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"],
}
# Conector que necesita cada proveedor del repositorio de la app (documentador-proyecto).
CONECTOR_REPO = {"github": "github", "gitlab": "gitlab", "azure-repos": "azure-devops", "bitbucket": "atlassian"}
MOTORES_DB = ("postgres", "mysql", "mariadb", "sqlserver", "mongodb")
FUENTES_INFORMES = ("saira.woff2", "inter.woff2", "jetbrains-mono.woff2")


def faltantes(nombres, env):
    """Las variables que faltan; "A|B+C" se cumple con A o con B y C."""
    salida = []
    for nombre in nombres:
        opciones = [o.split("+") for o in nombre.split("|")]
        if not any(all(env.get(v) for v in grupo) for grupo in opciones):
            salida.append(" o ".join("+".join(g) for g in opciones))
    return salida


def linea(estado, texto, ayuda=""):
    clave = {OK: "ok", AVISO: "aviso", FALTA: "falta"}[estado]
    resumen[clave] += 1
    RESULTADOS.append({"seccion": _SALIDA["seccion"], "estado": clave, "texto": texto, "ayuda": ayuda})
    if not _SALIDA["json"]:
        print(f"  {estado}{texto}" + (f"\n        → {ayuda}" if ayuda else ""))


def nota(texto):
    if not _SALIDA["json"]:
        print(f"        → {texto}")


def comando(*args, timeout=30):
    try:
        r = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout,
                           shell=(os.name == "nt" and args[0] in ("npm", "npx", "newman", "claude")))
        return (r.stdout or r.stderr).strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def version_mayor(texto):
    m = re.search(r"(\d+)\.(\d+)", texto or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def es_url(valor):
    u = urlparse((valor or "").strip())
    return u.scheme in ("http", "https") and bool(u.netloc)


def seccion(clave, titulo):
    _SALIDA["seccion"] = clave
    if not _SALIDA["json"]:
        print(f"\n{titulo}")


def leer_entorno():
    archivo = archivo_env()
    return archivo, {**leer_env(archivo), **{k: v for k, v in os.environ.items()}}


# ------------------------------------------------------------------ secciones
def revisar_python(ctx):
    seccion("python", "Python")
    py = ctx["py"]
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
    for modulo, para, paquete in (("yaml", "colecciones de Insomnia v5 (.yaml)", "pyyaml"),
                                  ("pypdf", "la portada sin pie del PDF de la documentación (node docs/generar.js)", "pypdf")):
        if _importable(modulo):
            linea(OK, f"{paquete} ({para})")
        else:
            linea(AVISO, f"{paquete} no está instalado (opcional: {para})", f"{py} -m pip install {paquete}")


def revisar_node(ctx):
    seccion("node", "Node.js y k0lmena")
    node = comando("node", "--version")
    if not node:
        linea(FALTA, "Node.js no está instalado", "Instalá Node.js 22 LTS desde https://nodejs.org")
    elif version_mayor(node) and version_mayor(node)[0] >= 20:
        linea(OK, f"Node.js {node}" + ("" if version_mayor(node)[0] >= 22 else " (mobile necesita 22+)"))
    else:
        linea(FALTA, f"Node.js {node} (se necesita 20 o superior; 22 LTS recomendado)", "Actualizá Node.js desde https://nodejs.org")
    if (K0 / "node_modules").exists():
        linea(OK, "k0lmena instalado (herramientas/k0lmena/node_modules)")
        if not (K0 / "node_modules" / "playwright").exists():
            linea(FALTA, "Falta Playwright dentro de k0lmena", "npm install   (desde la raíz del repo)")
    else:
        linea(FALTA, "k0lmena no está instalado", "npm install   (desde la raíz del repo)")
    navegadores = _carpeta_playwright()
    if navegadores and any(navegadores.glob("chromium*")):
        linea(OK, "Navegadores de Playwright")
    else:
        linea(AVISO, "No encuentro los navegadores de Playwright (web y ejecución E2E)", "cd herramientas/k0lmena && npx playwright install chromium")
    faltan = [n for n in ("firefox", "webkit") if not (navegadores and any(navegadores.glob(f"{n}-*")))]
    if faltan:
        linea(AVISO, f"Sin {' ni '.join(faltan)} (opcionales: solo para el agente cross-browser)",
              f"cd herramientas/k0lmena && npx playwright install {' '.join(faltan)}")
    else:
        linea(OK, "Firefox y WebKit (cross-browser)")
    if ctx["rapido"]:
        linea(AVISO, "Newman no revisado (--rapido)")
    elif comando("newman", "--version", timeout=15):
        linea(OK, "Newman (colecciones de Postman, Bruno e Insomnia)")
    else:
        linea(AVISO, "Newman no está instalado (solo para ejecutor-api)", "npm install -g newman")


def revisar_herramientas(ctx):
    seccion("herramientas", "Performance, seguridad y correos (opcionales)")
    k6 = K0 / "tools" / "k6" / ("k6.exe" if os.name == "nt" else "k6")
    linea(OK, "k6") if k6.exists() or shutil.which("k6") else linea(AVISO, "k6 no está instalado", "npm run bootstrap:k6")
    jmeter = list((K0 / "tools" / "jmeter").glob("apache-jmeter-*/bin/ApacheJMeter.jar")) if (K0 / "tools" / "jmeter").exists() else []
    linea(OK, "JMeter") if jmeter or os.environ.get("JMETER_HOME") else linea(AVISO, "JMeter no está instalado", "npm run bootstrap:jmeter")
    java = comando("java", "-version", timeout=10)
    if java:
        linea(OK, f"Java ({java.splitlines()[0]})")
    else:
        linea(AVISO, "Java no está instalado (lo necesita JMeter)", "Instalá Java 8+ (por ejemplo, Temurin 21: https://adoptium.net)")
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        linea(OK, "ffmpeg y ffprobe (streaming, playback y calidad de imagen)")
    else:
        linea(AVISO, "ffmpeg/ffprobe no están instalados (para probador-streaming y calidad-imagen)",
              "Instalá ffmpeg: winget install Gyan.FFmpeg · brew install ffmpeg · apt install ffmpeg")
    if shutil.which("sf"):
        linea(OK, "Salesforce CLI (sf) instalada (para probador-salesforce)")
    else:
        linea(AVISO, "Salesforce CLI (sf) no está instalada (solo para probador-salesforce)",
              "Instalala si vas a probar Salesforce: npm install --global @salesforce/cli")
    if shutil.which("shopify"):
        linea(OK, "Shopify CLI instalada (Theme Check del probador-shopify)")
    else:
        linea(AVISO, "Shopify CLI no está instalada (solo para Theme Check del probador-shopify)",
              "Instalala si vas a revisar el código de un tema: npm install --global @shopify/cli")
    if shutil.which("wp"):
        linea(OK, "WP-CLI instalada (para probador-wordpress --wp-cli)")
    else:
        linea(AVISO, "WP-CLI no está instalada (opcional para probador-wordpress)",
              "Instalala si tenés el sitio local: https://wp-cli.org (o poné WORDPRESS_WP_CLI en el .env si corre en Docker)")
    for cmd, nombre, para, como in (
            ("pip-audit", "pip-audit", "SCA de Python del analista-dependencias", "pip install pip-audit"),
            ("osv-scanner", "osv-scanner", "SCA multi-ecosistema del analista-dependencias", "https://google.github.io/osv-scanner/"),
            ("semgrep", "semgrep", "SAST del analista-codigo-seguro y el revisor-codigo", "pip install semgrep"),
            ("ruff", "ruff", "linter de Python del revisor-codigo", "pip install ruff"),
            ("bandit", "bandit", "seguridad de Python del revisor-codigo", "pip install bandit")):
        if shutil.which(cmd):
            linea(OK, f"{nombre} instalado ({para})")
        else:
            linea(AVISO, f"{nombre} no está instalado (opcional, para el {para})", f"Instalalo si vas a usarlo: {como}")
    # Librerías de Python para SAP (pywin32) y escritorio (pywinauto) — solo Windows
    import importlib.util
    for modulo, nombre, para, como in (
            ("win32com", "pywin32", "SAP GUI Scripting del probador-sap", "pip install pywin32"),
            ("pywinauto", "pywinauto", "árbol de controles del probador-desktop", "pip install pywinauto")):
        if importlib.util.find_spec(modulo):
            linea(OK, f"{nombre} instalado ({para})")
        elif sys.platform == "win32":
            linea(AVISO, f"{nombre} no está instalado (opcional, para el {para})", f"Instalalo si vas a usarlo: {como}")
        else:
            linea(OK, f"{nombre} no aplica (solo Windows, para el {para})")
    if shutil.which("appium"):
        linea(OK, "Appium instalado (probador-mobile y, con WinAppDriver, probador-desktop)")
    else:
        linea(AVISO, "Appium no está instalado (opcional, para probador-mobile / WinAppDriver en escritorio)",
              "Instalalo si vas a automatizar mobile o escritorio con Appium: npm install -g appium (y activá el conector con npm run conector -- activar appium)")
    if not shutil.which("docker"):
        linea(AVISO, "Docker no está instalado (lo necesitan el escaneo de seguridad con ZAP y Mailpit)",
              "Instalá Docker Desktop: https://www.docker.com/products/docker-desktop/")
    elif ctx["rapido"]:
        linea(OK, "Docker instalado (no se revisó si está corriendo: --rapido)")
    elif comando("docker", "info", "--format", "{{.ServerVersion}}", timeout=8):
        linea(OK, "Docker en ejecución")
    else:
        linea(AVISO, "Docker está instalado pero no está corriendo", "Abrí Docker Desktop antes de un escaneo de seguridad o de usar Mailpit")
    mailpit = ctx["env"].get("MAILPIT_URL", "")
    if mailpit and not ctx["rapido"]:
        if _responde(mailpit.rstrip("/") + "/api/v1/info"):
            linea(OK, "Mailpit responde en MAILPIT_URL")
        else:
            linea(AVISO, "Mailpit no responde en MAILPIT_URL (solo para verificador-correos)",
                  "docker compose -f herramientas/mailpit/docker-compose.yml up -d")


def revisar_fuentes(ctx):
    seccion("fuentes", "Fuentes de los informes y de la web")
    for carpeta, para in ((RAIZ / "scripts" / "fuentes", "los informes HTML"), (RAIZ / "docs" / "assets" / "fuentes", "la web y el PDF")):
        faltan = [f for f in FUENTES_INFORMES if not (carpeta / f).exists()]
        rel = carpeta.relative_to(RAIZ).as_posix()
        if faltan:
            linea(AVISO, f"Faltan fuentes en {rel}: {', '.join(faltan)} ({para} usan las del sistema)",
                  "Restaurá la carpeta desde el repositorio (git checkout -- " + rel + ")")
        else:
            linea(OK, f"Saira, Inter y JetBrains Mono para {para}")


def revisar_env(ctx):
    seccion("env", "Configuración (.env)")
    archivo, env = ctx["archivo"], ctx["env"]
    if not archivo.exists():
        linea(FALTA, f"No existe {archivo.name}", "Corré npm run configurar: te hace unas preguntas y crea el .env")
        return
    linea(OK, f"{archivo.name} encontrado")
    # La URL de la app va solo en APP_URL; k0lmena arma BASEURL desde ahí (herramientas/k0lmena/env.js).
    app_url, baseurl = env.get("APP_URL", ""), env.get("BASEURL", "")
    if not app_url and not baseurl:
        linea(AVISO, "APP_URL vacía: la app a probar (agentes, herramientas y automatización web)", f"Completala en {archivo.name}")
    elif app_url and not es_url(app_url):
        linea(FALTA, "APP_URL no es una URL válida (tiene que empezar con http:// o https://)", f"Corregila en {archivo.name}")
    elif app_url:
        linea(OK, "APP_URL definida")
    if baseurl:
        if not es_url(baseurl):
            linea(FALTA, "BASEURL no es una URL válida (tiene que empezar con http:// o https://)", f"Mejor borrala y dejá solo APP_URL en {archivo.name}")
        elif not app_url:
            linea(AVISO, "La URL está en BASEURL (nombre viejo): se usa igual", f"Pasala a APP_URL y borrá BASEURL de {archivo.name}")
        elif baseurl.rstrip("/") != app_url.rstrip("/"):
            linea(AVISO, "BASEURL y APP_URL son distintas: se usa APP_URL", f"Borrá BASEURL de {archivo.name}: la URL va solo en APP_URL")
        else:
            linea(AVISO, "BASEURL repite APP_URL: no hace falta", f"Borrá BASEURL de {archivo.name}")
    if env.get("API_BASEURL") and not es_url(env["API_BASEURL"]):
        linea(FALTA, "API_BASEURL no es una URL válida", f"Corregila en {archivo.name}")
    herramienta = env.get("GESTION_HERRAMIENTA", "")
    if herramienta:
        if herramienta not in VARIABLES_GESTION:
            linea(FALTA, f"GESTION_HERRAMIENTA={herramienta} no es válida", "Usá xray-cloud, xray-dc, qtm4j, aio o zephyr-scale")
        else:
            faltan = faltantes(VARIABLES_GESTION[herramienta], env)
            if faltan:
                linea(FALTA, f"Gestión ({herramienta}): faltan {', '.join(faltan)}", "Completalas en el .env (ver .env.example)")
            else:
                linea(OK, f"Gestión de pruebas: {herramienta}")
    conexiones = [c.strip() for c in (env.get("DB_CONEXIONES") or "").split(",") if c.strip()]
    for c in conexiones:
        pref = f"DB_{c.upper()}_"
        motor = env.get(pref + "MOTOR", "")
        if motor not in MOTORES_DB:
            linea(FALTA, f"Base {c}: {pref}MOTOR {'vacío' if not motor else 'inválido'}", f"Usá {', '.join(MOTORES_DB)}")
            continue
        faltan = [] if env.get(pref + "URL") else faltantes([pref + "HOST", pref + "BASE"], env)
        if faltan:
            linea(FALTA, f"Base {c} ({motor}): faltan {', '.join(faltan)} (o {pref}URL)", "Completalas en el .env (ver .env.example)")
        else:
            linea(OK, f"Base de datos {c} ({motor})")
    autorizadas = [u.strip() for u in (env.get("SEGURIDAD_URLS_AUTORIZADAS") or "").split(",") if u.strip()]
    malas = [u for u in autorizadas if not es_url(u)]
    if malas:
        linea(FALTA, f"SEGURIDAD_URLS_AUTORIZADAS tiene {len(malas)} URL(s) inválida(s)", "Separadas por coma, con http:// o https://")
    elif autorizadas:
        linea(OK, f"Seguridad web: {len(autorizadas)} URL(s) autorizada(s)")
    _revisar_navegador(env, archivo)


def _revisar_navegador(env, archivo):
    """Canal y bypass anti-bots (herramientas/k0lmena/tools/navegador): las mismas reglas que navegador.js."""
    canal = (env.get("NAVEGADOR_CANAL") or "").strip().lower()
    if canal:
        if canal not in ("chrome", "chrome-beta", "msedge", "msedge-beta"):
            linea(FALTA, f"NAVEGADOR_CANAL={canal} no es válido", "Usá chrome o msedge (o dejalo vacío)")
        elif canal.startswith("chrome") and not _chrome_instalado():
            linea(AVISO, "NAVEGADOR_CANAL=chrome, pero no encuentro Google Chrome instalado", "Instalalo o dejá la variable vacía")
        else:
            linea(OK, f"Navegador: {canal}")
    nombre, token = (env.get("QA_BYPASS_HEADER") or "").strip(), (env.get("QA_BYPASS_TOKEN") or "").strip()
    if nombre or token:
        if not (nombre and token):
            linea(FALTA, "Bypass anti-bots incompleto: hacen falta QA_BYPASS_HEADER y QA_BYPASS_TOKEN", f"Completá las dos en {archivo.name}")
        elif not re.fullmatch(r"[A-Za-z0-9-]{1,64}", nombre):
            linea(FALTA, f"QA_BYPASS_HEADER={nombre} no es un nombre de header válido", "Solo letras, números y guiones")
        elif not (env.get("QA_BYPASS_HOSTS") or env.get("APP_URL") or env.get("BASEURL")):
            linea(FALTA, "Bypass anti-bots sin hosts: falta APP_URL o QA_BYPASS_HOSTS", "El header se manda solo a esos hosts")
        else:
            linea(OK, f"Bypass anti-bots: header {nombre} (solo a los hosts de la app)")


def _chrome_instalado():
    if shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chrome"):
        return True
    candidatos = [Path("/Applications/Google Chrome.app")]
    for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            candidatos.append(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe")
    return any(c.exists() for c in candidatos)


def revisar_integraciones(ctx):
    seccion("integraciones", "Repositorio, roles, avisos y monitoreo")
    antes = len(RESULTADOS)
    _integraciones(ctx)
    if len(RESULTADOS) == antes:
        nota("Ninguna configurada (son opcionales: REPO_*, PERMISOS_*, SLACK/TEAMS_WEBHOOK_URL, MONITOREO_URLS en .env.example)")


def _integraciones(ctx):
    env, activos = ctx["env"], ctx["conectores"]
    proveedor = env.get("REPO_PROVEEDOR", "")
    if proveedor:
        if proveedor not in CONECTOR_REPO:
            linea(FALTA, f"REPO_PROVEEDOR={proveedor} no es válido", "Usá github, gitlab, azure-repos o bitbucket")
        else:
            conector = CONECTOR_REPO[proveedor]
            if not env.get("REPO_NOMBRE"):
                linea(FALTA, f"Repositorio ({proveedor}): falta REPO_NOMBRE", "Ej.: mi-empresa/mi-app (ver .env.example)")
            elif conector not in activos:
                linea(AVISO, f"Repositorio ({proveedor}): el conector {conector} no está activo",
                      f"npm run conector -- activar {conector}" if conector not in ("atlassian",) else "atlassian viene activo: revisá .claude/settings.json")
            else:
                linea(OK, f"Repositorio de la app: {proveedor} ({env['REPO_NOMBRE'].count(',') + 1} repositorio(s))")
            if proveedor == "bitbucket" and (env.get("ATLASSIAN_MCP_AUTENTICACION") or "oauth") != "token":
                linea(FALTA, "Bitbucket necesita ATLASSIAN_MCP_AUTENTICACION=token", "Ver CONECTORES.md, sección Atlassian")
        ruta = env.get("REPO_RUTA_LOCAL", "")
        if ruta and not (Path(ruta) / ".git").exists():
            linea(AVISO, "REPO_RUTA_LOCAL no apunta a un clon de git", "Revisá la ruta o dejala vacía")
    roles = [r.strip() for r in (env.get("PERMISOS_ROLES") or "").split(",") if r.strip()]
    for r in roles:
        clave = re.sub(r"[^A-Z0-9]+", "_", r.upper().translate(str.maketrans("ÁÉÍÓÚÑÜ", "AEIOUNU"))).strip("_")
        faltan = faltantes([f"PERMISOS_{clave}_USUARIO", f"PERMISOS_{clave}_CLAVE"], env)
        if faltan and not env.get(f"PERMISOS_{clave}_TOKEN"):
            linea(FALTA, f"Rol {r}: faltan {', '.join(faltan)}", "Completalas en el .env (bloque Permisos por rol)")
    if roles:
        linea(OK, f"Permisos: {len(roles)} rol(es) configurado(s)")
    for nombre, patron, donde in (("SLACK_WEBHOOK_URL", r"^https://hooks\.slack\.com/", "Slack (Incoming Webhook)"),
                                  ("TEAMS_WEBHOOK_URL", r"^https://", "Teams (Workflows)")):
        valor = env.get(nombre, "")
        if not valor:
            continue
        if re.match(patron, valor):
            linea(OK, f"Avisos a {donde}")
        else:
            linea(FALTA, f"{nombre} no tiene el formato esperado de {donde}", "Copiá la URL del webhook tal cual (ver .env.example)")
    urls = [u.strip() for u in (env.get("MONITOREO_URLS") or "").split(",") if u.strip()]
    malas = [u for u in urls if not es_url(u)]
    if malas:
        linea(FALTA, f"MONITOREO_URLS tiene {len(malas)} URL(s) inválida(s)", "Separadas por coma, con http:// o https://")
    elif urls or (RAIZ / "input" / "monitoreo.json").exists():
        linea(OK, "Monitoreo sintético configurado")


def revisar_conectores(ctx):
    seccion("conectores", "Conectores MCP")
    env, habilitados, locales = ctx["env"], ctx["habilitados"], ctx["locales"]
    for nombre in dict.fromkeys(habilitados + locales):
        requeridas = VARIABLES_CONECTOR.get(nombre, [])
        if nombre == "azure-devops" and (env.get("ADO_AUTENTICACION") or "pat").lower() != "pat":
            requeridas = ["ADO_ORGANIZACION"]  # interactive / azcli / env: sin PAT
        faltan = faltantes(requeridas, env)
        origen = " (activado con npm run conector)" if nombre in locales else ""
        if faltan:
            linea(FALTA, f"{nombre}{origen}: faltan {', '.join(faltan)}", "Completalas en el .env (ver CONECTORES.md)")
        elif nombre in CONECTORES_OAUTH or (nombre in CONECTORES_TOKEN_OPCIONAL and not env.get(CONECTORES_TOKEN_OPCIONAL[nombre])):
            linea(OK, f"{nombre}{origen} (se autoriza con tu cuenta desde /mcp la primera vez)")
        else:
            linea(OK, nombre + origen)
    nota("Para sumar Azure DevOps, Figma, GitHub, GitLab, Linear, ClickUp, monday.com, Asana, Trello, Notion, YouTrack, "
         "Shortcut, QMetry, AIO Tests, k0lmenaTMT o Appium: npm run conector")


def revisar_repo(ctx):
    seccion("repo", "Repositorio de k0lmenIA (git)")
    if not shutil.which("git"):
        linea(AVISO, "git no está instalado", "Instalá git: https://git-scm.com/downloads")
        return
    linea(OK, "git instalado")
    ignorado = (RAIZ / ".gitignore").read_text(encoding="utf-8") if (RAIZ / ".gitignore").exists() else ""
    for patron, que in ((".env", "el .env (secretos)"), ("/input/documentacion/", "la documentación del proyecto")):
        if patron in ignorado:
            linea(OK, f".gitignore cubre {que}")
        else:
            linea(FALTA, f".gitignore no cubre {que}", f"Agregá {patron} al .gitignore")
    if comando("git", "-C", str(RAIZ), "config", "user.email", timeout=5):
        linea(OK, "Identidad de git configurada (para los commits)")
    else:
        linea(AVISO, "git sin user.email (no vas a poder hacer commits)", 'git config user.email "tu@mail" && git config user.name "Tu nombre"')


def revisar_extras(ctx):
    seccion("extras", "Portal, monitoreo y evals")
    if (RAIZ / "output").is_dir():
        linea(OK, "output/ existe (el portal output/index.html se regenera solo)")
    else:
        linea(AVISO, "No existe output/", "Se crea solo con el primer informe; o mkdir output")
    for wf, que in (("monitoreo.yml", "monitoreo sintético programado"), ("evals.yml", "evals manuales en CI")):
        if (RAIZ / ".github" / "workflows" / wf).exists():
            linea(OK, f"Workflow {wf} ({que})")
        else:
            linea(AVISO, f"Falta .github/workflows/{wf} ({que})", "Restauralo desde el repositorio")
    if shutil.which("claude"):
        linea(OK, "Claude Code CLI disponible (para correr los evals: npm run evals)")
    else:
        linea(AVISO, "No encuentro el comando claude (solo hace falta para correr los evals)", "Instalá Claude Code (ver README)")


SECCIONES = {
    "python": revisar_python, "node": revisar_node, "herramientas": revisar_herramientas, "fuentes": revisar_fuentes,
    "env": revisar_env, "integraciones": revisar_integraciones, "conectores": revisar_conectores,
    "repo": revisar_repo, "extras": revisar_extras,
}


def contexto(rapido=False):
    archivo, env = leer_entorno()
    habilitados = []
    for f in (RAIZ / ".claude" / "settings.json", RAIZ / ".claude" / "settings.local.json"):
        try:
            habilitados += json.loads(f.read_text(encoding="utf-8")).get("enabledMcpjsonServers", [])
        except (OSError, ValueError):
            pass
    locales = _conectores_locales()
    return {"py": "python" if os.name == "nt" else "python3", "rapido": rapido, "archivo": archivo, "env": env,
            "habilitados": habilitados, "locales": locales, "conectores": set(habilitados) | set(locales)}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Revisa el entorno de k0lmenIA")
    ap.add_argument("--seccion", help=f"una o varias, separadas por coma: {', '.join(SECCIONES)}")
    ap.add_argument("--rapido", action="store_true", help="saltea los chequeos lentos (red, Docker, Mailpit)")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    a = ap.parse_args(argv)
    elegidas = [x.strip() for x in a.seccion.split(",")] if a.seccion else list(SECCIONES)
    invalidas = [x for x in elegidas if x not in SECCIONES]
    if invalidas:
        ap.error(f"sección desconocida: {', '.join(invalidas)} (opciones: {', '.join(SECCIONES)})")
    _SALIDA["json"] = a.json
    resumen.update(ok=0, aviso=0, falta=0)
    RESULTADOS.clear()
    if not a.json:
        print("k0lmenIA · revisión del entorno" + (" (rápida)" if a.rapido else ""))
    ctx = contexto(a.rapido)
    for nombre in elegidas:
        SECCIONES[nombre](ctx)
    if a.json:
        print(json.dumps({"resumen": resumen, "resultados": RESULTADOS}, ensure_ascii=False, indent=2))
    else:
        print(f"\nResultado: {resumen['ok']} OK · {resumen['aviso']} avisos · {resumen['falta']} faltantes")
        if resumen["falta"]:
            print("Resolvé lo marcado con X y volvé a correr el doctor.")
    return 1 if resumen["falta"] else 0


def _responde(url, timeout=3):
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (URL del .env de la persona)
            return 200 <= r.status < 500
    except Exception:
        return False


def _conectores_locales():
    """Conectores activados con `npm run conector` (alcance local de Claude Code); solo nombres."""
    try:
        datos = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    clave = str(RAIZ).replace("\\", "/").lower()
    for ruta, proyecto in (datos.get("projects") or {}).items():
        if ruta.replace("\\", "/").lower() == clave:
            return list((proyecto.get("mcpServers") or {}).keys())
    return []


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
    sys.exit(main())

#!/usr/bin/env python3
"""
Revisa que el entorno de k0lmenIA esté listo y dice qué falta y cómo resolverlo.

Uso (desde la raíz del repo):
    python scripts/doctor.py [--seccion <nombre>] [--rapido] [--json]     (en Mac/Linux: python3)
    npm run doctor

Secciones: python, node, fuentes, env, integraciones, conectores, repo y extras.
  --seccion   revisa solo una (o varias, separadas por coma): --seccion env,integraciones
  --rapido    saltea los chequeos lentos (red, Newman)
  --json      salida para máquinas: [{"seccion", "estado": ok|aviso|falta, "texto", "ayuda"}]

Revisa Python y sus librerías, Node/npm, k0lmena y los navegadores de Playwright, Newman,
las fuentes de los informes y de la web, el .env (y que cada bloque que uses
esté completo y coherente), los conectores MCP habilitados, git y lo que necesitan el portal y
los evals. Nunca muestra valores del .env: solo si cada variable está, falta o es inválida.
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
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
# Como plugin, el código (RAIZ) vive en la caché de Claude Code y el proyecto del QA en otra carpeta: lo que es solo del
# repo de desarrollo (la web, el PDF y los workflows de .github/) no se revisa.
COMO_PLUGIN = PROYECTO != RAIZ.resolve()
K0 = PROYECTO / "herramientas" / "k0lmena"
sys.path.insert(0, str(RAIZ / "scripts"))
from _env import leer_env, archivo_env  # noqa: E402

OK, AVISO, FALTA = "OK  ", "!   ", "X   "
resumen = {"ok": 0, "aviso": 0, "falta": 0}
RESULTADOS = []
_SALIDA = {"json": False, "seccion": ""}

# Variables que necesita cada conector MCP para funcionar (las de OAuth no necesitan nada).
# "A|B+C" = A, o bien B y C juntas. ADO_PAT solo hace falta si la autenticación es por PAT.
VARIABLES_CONECTOR = {
    "k0lmena-tmt": ["K0LMENA_TMT_TOKEN"],
}
# Se autorizan con tu cuenta (OAuth) desde /mcp; los de token opcional, solo si ese token está vacío.
CONECTORES_OAUTH = ("atlassian",)
CONECTORES_TOKEN_OPCIONAL = {}
VARIABLES_GESTION = {
    "xray-cloud": ["GESTION_PROYECTO", "XRAY_CLOUD_CLIENT_ID", "XRAY_CLOUD_CLIENT_SECRET", "JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"],
    "xray-dc": ["GESTION_PROYECTO", "XRAY_DC_URL", "XRAY_DC_TOKEN|XRAY_DC_USER+XRAY_DC_PASSWORD"],
    "k0lmena-tmt": ["GESTION_PROYECTO", "K0LMENA_TMT_TOKEN"],
}
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
        linea(OK, f"Node.js {node}")
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
    if ctx["rapido"]:
        linea(AVISO, "Newman no revisado (--rapido)")
    elif comando("newman", "--version", timeout=15):
        linea(OK, "Newman (colecciones de Postman, Bruno e Insomnia)")
    else:
        linea(AVISO, "Newman no está instalado (solo para ejecutor-api)", "npm install -g newman")


def revisar_fuentes(ctx):
    seccion("fuentes", "Fuentes de los informes y de la web")
    carpetas = [(RAIZ / "scripts" / "fuentes", "los informes HTML")]
    if not COMO_PLUGIN:
        carpetas.append((RAIZ / "docs" / "assets" / "fuentes", "la web y el PDF"))
    for carpeta, para in carpetas:
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
            linea(FALTA, f"GESTION_HERRAMIENTA={herramienta} no es válida", "Usá xray-cloud, xray-dc o k0lmena-tmt (QMetry, AIO Tests y Zephyr Scale están en K0lmenIA Empresa)")
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
    _revisar_idioma(env, archivo)


def _revisar_idioma(env, archivo):
    """DOCUMENTACION_EN: vacío (Claude pregunta), si o no."""
    valor = (env.get("DOCUMENTACION_EN") or "").strip().lower()
    if valor and valor not in ("si", "sí", "no"):
        linea(FALTA, f"DOCUMENTACION_EN={valor} no es válido", "Usá si, no o dejalo vacío (Claude pregunta)")
    elif valor:
        linea(OK, f"Contexto y documentación en inglés: {'siempre' if valor != 'no' else 'nunca'}")


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
    seccion("integraciones", "Repositorio y avisos")
    antes = len(RESULTADOS)
    _integraciones(ctx)
    if len(RESULTADOS) == antes:
        nota("Ninguna configurada (son opcionales: REPO_RUTA_LOCAL, SLACK/TEAMS_WEBHOOK_URL en .env.example)")


def _integraciones(ctx):
    env = ctx["env"]
    proveedor = env.get("REPO_PROVEEDOR", "")
    if proveedor and proveedor != "local":
        linea(AVISO, f"REPO_PROVEEDOR={proveedor}: K0lmenIA Light lee el repositorio desde un clon local",
              "Completá REPO_RUTA_LOCAL (leer el repositorio por conector está disponible en K0lmenIA Pro)")
    ruta = env.get("REPO_RUTA_LOCAL", "")
    if ruta and not (Path(ruta) / ".git").exists():
        linea(AVISO, "REPO_RUTA_LOCAL no apunta a un clon de git", "Revisá la ruta o dejala vacía")
    elif ruta:
        linea(OK, "Repositorio de la app: clon local")
    for nombre, patron, donde in (("SLACK_WEBHOOK_URL", r"^https://hooks\.slack\.com/", "Slack (Incoming Webhook)"),
                                  ("TEAMS_WEBHOOK_URL", r"^https://", "Teams (Workflows)")):
        valor = env.get(nombre, "")
        if not valor:
            continue
        if re.match(patron, valor):
            linea(OK, f"Avisos a {donde}")
        else:
            linea(FALTA, f"{nombre} no tiene el formato esperado de {donde}", "Copiá la URL del webhook tal cual (ver .env.example)")
    if (env.get("GESTION_HERRAMIENTA") == "k0lmena-tmt" or env.get("K0LMENA_TMT_TOKEN")) and not ctx.get("rapido"):
        _revisar_k0lmena_tmt(env)


def revisar_conectores(ctx):
    seccion("conectores", "Conectores MCP")
    env, habilitados, locales = ctx["env"], ctx["habilitados"], ctx["locales"]
    for nombre in dict.fromkeys(habilitados + locales):
        requeridas = VARIABLES_CONECTOR.get(nombre, [])
        faltan = faltantes(requeridas, env)
        origen = " (activado con npm run conector)" if nombre in locales else ""
        if faltan:
            linea(FALTA, f"{nombre}{origen}: faltan {', '.join(faltan)}", "Completalas en el .env (ver CONECTORES.md)")
        elif nombre in CONECTORES_OAUTH or (nombre in CONECTORES_TOKEN_OPCIONAL and not env.get(CONECTORES_TOKEN_OPCIONAL[nombre])):
            linea(OK, f"{nombre}{origen} (se autoriza con tu cuenta desde /mcp la primera vez)")
        else:
            linea(OK, nombre + origen)
    nota("Más conectores (Azure DevOps, Confluence, GitHub, GitLab, Figma, Linear, observabilidad, analytics y otros) "
         "están disponibles en K0lmenIA Pro y K0lmenIA Empresa. El estado en HTML: npm run conector -- listar --html")


def revisar_repo(ctx):
    seccion("repo", "Repositorio de k0lmenIA (git)")
    if not shutil.which("git"):
        linea(AVISO, "git no está instalado", "Instalá git: https://git-scm.com/downloads")
        return
    linea(OK, "git instalado")
    ignorado = (PROYECTO / ".gitignore").read_text(encoding="utf-8") if (PROYECTO / ".gitignore").exists() else ""
    for patron, que in ((".env", "el .env (secretos)"), ("/input/documentacion/", "la documentación del proyecto")):
        if patron in ignorado:
            linea(OK, f".gitignore cubre {que}")
        else:
            linea(FALTA, f".gitignore no cubre {que}", f"Agregá {patron} al .gitignore")
    if comando("git", "-C", str(PROYECTO), "config", "user.email", timeout=5):
        linea(OK, "Identidad de git configurada (para los commits)")
    else:
        linea(AVISO, "git sin user.email (no vas a poder hacer commits)", 'git config user.email "tu@mail" && git config user.name "Tu nombre"')


def revisar_extras(ctx):
    seccion("extras", "Portal y evals")
    if (PROYECTO / "output").is_dir():
        linea(OK, "output/ existe (el portal output/index.html se regenera solo)")
    else:
        linea(AVISO, "No existe output/", "Se crea solo con el primer informe; o mkdir output")
    if COMO_PLUGIN:
        nota("El workflow de evals es del repo de desarrollo de k0lmenIA; para correr tus pruebas en tu "
             "pipeline, k0lmenia ci arma el de GitHub, GitLab, Azure o Jenkins.")
        return
    for wf, que in (("evals.yml", "evals manuales en CI"),):
        if (RAIZ / ".github" / "workflows" / wf).exists():
            linea(OK, f"Workflow {wf} ({que})")
        else:
            linea(AVISO, f"Falta .github/workflows/{wf} ({que})", "Restauralo desde el repositorio")
    if shutil.which("claude"):
        linea(OK, "Claude Code CLI disponible (para correr los evals: npm run evals)")
    else:
        linea(AVISO, "No encuentro el comando claude (solo hace falta para correr los evals)", "Instalá Claude Code (ver README)")


SECCIONES = {
    "python": revisar_python, "node": revisar_node, "fuentes": revisar_fuentes,
    "env": revisar_env, "integraciones": revisar_integraciones, "conectores": revisar_conectores,
    "repo": revisar_repo, "extras": revisar_extras,
}


def contexto(rapido=False):
    archivo, env = leer_entorno()
    habilitados = []
    for f in (PROYECTO / ".claude" / "settings.json", PROYECTO / ".claude" / "settings.local.json"):
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


def _revisar_k0lmena_tmt(env):
    """Que k0lmenaTMT responda y que el token valga: tools/list del server MCP (no escribe nada)."""
    import json as _json
    import urllib.error
    import urllib.request
    url = env.get("K0LMENA_TMT_URL") or "http://localhost:4000/api/v1/mcp"
    token = env.get("K0LMENA_TMT_TOKEN", "")
    if not token:
        linea(FALTA, "k0lmenaTMT: falta K0LMENA_TMT_TOKEN", "Generá un token personal (kolm_pat_...) en k0lmenaTMT y ponelo en el .env")
        return
    cuerpo = _json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
    pedido = urllib.request.Request(url, data=cuerpo, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream", "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(pedido, timeout=5) as r:  # noqa: S310 (URL del .env de la persona)
            texto = r.read().decode("utf-8", "replace")
        n = texto.count('"name"')
        faltan = [h for h in ("create_test_case", "create_test_cycle", "add_case_to_cycle", "record_execution",
                              "attach_evidence", "apply_change_set") if h not in texto]
        if faltan:
            linea(AVISO, f"k0lmenaTMT responde, pero le faltan herramientas: {', '.join(faltan)}", "Actualizá k0lmenaTMT")
        else:
            linea(OK, f"k0lmenaTMT responde y el token es válido ({url})")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            linea(FALTA, "k0lmenaTMT rechaza el token (vencido, revocado o de otra instancia)", "Generá uno nuevo y actualizá K0LMENA_TMT_TOKEN")
        elif e.code == 429:
            linea(AVISO, "k0lmenaTMT: límite de pedidos por minuto alcanzado", "Esperá un minuto (o subí ASSISTANT_RATE_LIMIT en k0lmenaTMT)")
        else:
            linea(FALTA, f"k0lmenaTMT respondió {e.code} en {url}", "Revisá K0LMENA_TMT_URL")
    except Exception:
        linea(FALTA, f"k0lmenaTMT no responde en {url}", "¿Está levantado? (Docker Desktop abierto y k0lmenaTMT corriendo)")


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
    clave = str(PROYECTO).replace("\\", "/").lower()
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

#!/usr/bin/env python3
"""
Revisión estática de código (seguridad, performance, malas prácticas, confiabilidad y mantenibilidad), de solo lectura.

Uso (desde la raíz del repo de k0lmenIA):
    python herramientas/codigo/revision.py --ruta C:/proyectos/mi-app [--salida output/revision-codigo/mi-app/revision.json]
    python herramientas/codigo/revision.py --origen output/revision-codigo/mi-app-pr-12/origen.json
    python herramientas/codigo/revision.py --origen .../origen.json --todo      (todo el repo, no solo lo que cambió)

`--origen` es el manifiesto de `obtener.py` (`npm run obtener-codigo`): toma de ahí la ruta y, si es un PR/MR o una
rama contra su base, revisa solo los archivos que cambiaron y marca qué hallazgos caen en líneas cambiadas.

Qué hace (sin dependencias; corre siempre):
- **Inventario**: archivos y líneas por lenguaje, los archivos más grandes.
- **Reglas propias** por lenguaje (Python, JS/TS, Java, C#, Go, PHP, Ruby, Kotlin, C/C++, SQL): inyección (SQL y
  comandos), eval, XSS, deserialización insegura, TLS sin verificar, cripto débil, aleatoriedad no criptográfica para
  secretos, CORS abierto, JWT sin verificar, path traversal y SSRF desde la request, datos sensibles en logs, debug
  activo; consultas y llamadas HTTP dentro de loops (N+1), `await` secuencial en loops, `forEach(async)`, I/O síncrona,
  `SELECT *`, clonado con JSON; excepciones tragadas o genéricas, errores ignorados, `==` en JS, `var`, `any`,
  supresiones de linter, defaults mutables, imports con `*`, TODO/FIXME, prints/console.log, URLs/IPs hardcodeadas.
- **Mantenibilidad**: funciones largas, complejidad ciclomática, demasiados parámetros, anidamiento profundo,
  archivos enormes y bloques duplicados entre archivos (Python con `ast`; el resto con una heurística de llaves).
- **Secretos**: el escáner de `herramientas/seguridad/sast.py` (valor redactado).
- **Externos opcionales** (si están instalados): `semgrep` (reglas p/default, sin métricas), `ruff` y `bandit`.
  No corre ESLint ni nada que ejecute configuración del repo: el código revisado no es confiable.

Cada hallazgo es una **sospecha a confirmar** leyendo el código (lo hace el agente revisor-codigo): la salida es un
JSON para el triage, no el informe final. Una línea con `k0lmenia: ignorar` se saltea.
No ejecuta el código del proyecto ni lo modifica.
"""
import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "herramientas" / "seguridad"))
import sast  # noqa: E402  (reutiliza el escáner de secretos)

IGNORAR_DIR = sast.IGNORAR_DIR | {".idea", ".vscode", "bower_components", "jspm_packages", ".gradle", ".mvn", "Pods",
                                  "DerivedData", ".terraform", ".serverless", "obj", "bin", ".pytest_cache", ".mypy_cache",
                                  ".tox", "site-packages", "third_party", "external", "generated", "__generated__", ".git"}
LENGUAJES = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".cs": "C#",
    ".go": "Go", ".php": "PHP", ".rb": "Ruby", ".c": "C/C++", ".h": "C/C++", ".cpp": "C/C++", ".cc": "C/C++",
    ".hpp": "C/C++", ".swift": "Swift", ".rs": "Rust", ".scala": "Scala", ".sql": "SQL", ".vue": "Vue",
    ".svelte": "Svelte", ".html": "HTML", ".sh": "Shell", ".ps1": "PowerShell", ".dart": "Dart",
}
LLAVES = {"JavaScript", "TypeScript", "Java", "Kotlin", "C#", "Go", "PHP", "C/C++", "Swift", "Rust", "Scala", "Dart"}
MAX_BYTES = 1024 * 1024
SEVERIDADES = ("Crítica", "Alta", "Media", "Baja")
CATEGORIAS = ("Seguridad", "Performance", "Confiabilidad", "Malas prácticas", "Mantenibilidad")
TOPE_POR_ARCHIVO, TOPE_POR_REGLA = 15, 150

PY, JS, TS = {"Python"}, {"JavaScript", "TypeScript", "Vue", "Svelte"}, {"TypeScript"}
JVM, CS, GO, PHP, RB = {"Java", "Kotlin", "Scala"}, {"C#"}, {"Go"}, {"PHP"}, {"Ruby"}
CODIGO = PY | JS | JVM | CS | GO | PHP | RB | {"C/C++", "Swift", "Rust", "Dart"}
_SQL = r"(?:select\s[^\"'`\n]*?\bfrom|insert\s+into|update\s+\w+\s+set|delete\s+from)\b"
# Un string de SQL con datos interpolados o concatenados, por tipo de comilla (el SQL suele tener la otra adentro).
_SQL_ARMADO = "|".join(
    rf"(\bf{q}[^{q}\n]*{_SQL}[^{q}\n]*\{{)|({q}[^{q}\n]*{_SQL}[^{q}\n]*{q}\s*(\+|%\s*[\w(]|\.format\(|\.\s*\$))"
    rf"|(\${q}[^{q}\n]*{_SQL}[^{q}\n]*\{{)" for q in ('"', "'")) + rf"|(`[^`]*{_SQL}[^`]*\$\{{)"


def R(id_, cat, sev, lenguajes, patron, mensaje, recomendacion, cwe=None, en_tests=True, flags=re.I):
    return {"id": id_, "categoria": cat, "severidad": sev, "lenguajes": lenguajes, "rx": re.compile(patron, flags),
            "mensaje": mensaje, "recomendacion": recomendacion, "cwe": cwe, "en_tests": en_tests}


# Reglas por línea. Patrones conservadores: preferimos perder alguno a inundar de falsos positivos.
REGLAS = [
    # ---------------- Seguridad
    R("SEG-SQL", "Seguridad", "Alta", CODIGO, _SQL_ARMADO,
      "Consulta SQL armada concatenando o interpolando variables: posible inyección SQL.",
      "Usá consultas parametrizadas / prepared statements o el query builder del ORM; nunca concatenes datos.", "CWE-89"),
    R("SEG-EVAL", "Seguridad", "Alta", PY | JS | PHP | RB,
      r"(?<![\w.])(eval|exec)\s*\(|\bnew\s+Function\s*\(|\bsetTimeout\s*\(\s*[\"'`]|\binstance_eval\b|\bcreate_function\s*\(",
      "Evaluación dinámica de código (eval/exec/new Function).",
      "Evitá ejecutar texto como código; si hace falta, usá un parser específico (json, ast.literal_eval) o una lista blanca.", "CWE-95"),
    R("SEG-CMD", "Seguridad", "Alta", CODIGO,
      r"subprocess\.\w+\([^)]*shell\s*=\s*True|\bos\.(system|popen)\s*\(|\bexecSync?\s*\([^)]*(\+|\$\{)|"
      r"Runtime\.getRuntime\(\)\.exec\s*\(|\b(shell_exec|passthru|proc_open|popen|system)\s*\(\s*\$|"
      r"exec\.Command\(\s*\"(sh|bash|cmd|powershell)\"|Process\.Start\([^)]*\+|`[^`]*#\{",
      "Ejecución de comandos del sistema con shell o con texto armado: posible inyección de comandos.",
      "Pasá los argumentos como lista sin shell (subprocess.run([...]), execFile, ProcessBuilder) y validá contra una lista blanca.", "CWE-78"),
    R("SEG-XSS", "Seguridad", "Media", JS | PHP | PY | RB | {"HTML"},
      r"\.(innerHTML|outerHTML)\s*\+?=|document\.write\s*\(|dangerouslySetInnerHTML|insertAdjacentHTML\s*\(|\bv-html\s*=|"
      r"bypassSecurityTrust\w*\(|\bmark_safe\s*\(|\|\s*safe\b|\{\{\{[^}]+\}\}\}|<%-|\.html_safe\b|\braw\s*\(|"
      r"\becho\s+\$_(GET|POST|REQUEST|COOKIE)",
      "Salida HTML sin escapar: posible XSS si el dato viene del usuario.",
      "Escapá por contexto (textContent, el escapado del template) o sanitizá con DOMPurify/bleach antes de insertar HTML.", "CWE-79"),
    R("SEG-DESERIALIZACION", "Seguridad", "Alta", PY | JVM | CS | PHP | RB | JS,
      r"\bpickle\.loads?\s*\(|\bcPickle\.loads?\s*\(|\bmarshal\.loads?\s*\(|"
      r"\bshelve\.open\s*\(|\bObjectInputStream\b|\bXMLDecoder\b|\bBinaryFormatter\b|\bunserialize\s*\(|"
      r"\bMarshal\.load\b|node-serialize|\bTypeNameHandling\.(All|Auto|Objects)",
      "Deserialización insegura: con datos externos permite ejecutar código.",
      "Usá formatos de datos (JSON) o el modo seguro (listas blancas de tipos).", "CWE-502", flags=0),
    # yaml.load solo es peligroso en Python (PyYAML) y Ruby (Psych < 4); en JS (js-yaml 4) es seguro.
    R("SEG-DESERIALIZACION", "Seguridad", "Alta", PY | RB,
      r"\byaml\.(unsafe_)?load\s*\((?![^)]*Safe(Loader)?)|\bYAML\.(unsafe_)?load\s*\(",
      "yaml.load sin SafeLoader: con datos externos permite crear objetos arbitrarios.",
      "Usá yaml.safe_load (Python) o YAML.safe_load (Ruby).", "CWE-502", flags=0),
    R("SEG-TLS", "Seguridad", "Alta", CODIGO,
      r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED|InsecureSkipVerify\s*:\s*true|"
      r"ServerCertificate(Custom)?ValidationCallback\s*=.*=>\s*true|ssl\._create_unverified_context|CERT_NONE|"
      r"setHostnameVerifier\s*\(|ALLOW_ALL_HOSTNAME_VERIFIER|TrustAll|curl_setopt\([^)]*SSL_VERIFYPEER[^)]*(false|0)\)",
      "Verificación de certificados TLS desactivada: expone a ataques man-in-the-middle.",
      "Mantené la verificación activa; para certificados internos, configurá la CA en lugar de desactivarla.", "CWE-295"),
    R("SEG-CRIPTO", "Seguridad", "Media", CODIGO,
      r"^(?!.*usedforsecurity\s*=\s*False).*?(?:hashlib\.(md5|sha1)\s*\(|createHash\(\s*[\"'](md5|sha1)[\"']|MessageDigest\.getInstance\(\s*\"(MD5|SHA-?1)\"|"
      r"\b(MD5|SHA1)\.Create\(\)|\bmd5\s*\(|\bsha1\s*\(|Cipher\.getInstance\(\s*\"(DES|DESede|RC4|[^\"]*/ECB/)|"
      r"\bAES\.MODE_ECB\b|createCipher\s*\(|crypto/(md5|sha1|des|rc4)\")",
      "Algoritmo criptográfico débil (MD5/SHA-1/DES/RC4/ECB).",
      "Para contraseñas usá bcrypt/argon2/scrypt; para integridad, SHA-256+; para cifrado, AES-GCM con IV aleatorio.", "CWE-327"),
    R("SEG-RANDOM", "Seguridad", "Media", CODIGO,
      r"(Math\.random\(\)|\brandom\.(random|randint|choice|choices|randrange)\(|\bnew\s+Random\(|\brand\(|\bmt_rand\(|math/rand\")"
      r"(?=.*\b(token|secret|password|passwd|clave|otp|salt|nonce|session|apikey|api_key|codigo|code)\b)",
      "Aleatoriedad no criptográfica usada para un valor sensible (token, clave, OTP).",
      "Usá un generador criptográfico: secrets / crypto.randomUUID / crypto.getRandomValues / SecureRandom / random_bytes.", "CWE-338"),
    R("SEG-CORS", "Seguridad", "Media", CODIGO,
      r"Access-Control-Allow-Origin[\"']?\s*[,:]\s*[\"']\*|\bcors\(\s*\)|origin\s*:\s*[\"']\*[\"']|origin\s*:\s*true\b|"
      r"CORS_ORIGIN_ALLOW_ALL\s*=\s*True|CORS_ALLOW_ALL_ORIGINS\s*=\s*True|AllowAnyOrigin\(\)|allowedOrigins\(\s*\"\*\"",
      "CORS abierto a cualquier origen.",
      "Restringí los orígenes a una lista blanca, sobre todo si hay cookies o credenciales.", "CWE-942"),
    R("SEG-JWT", "Seguridad", "Alta", CODIGO,
      r"algorithms?\s*[:=]\s*\[?\s*[\"']none[\"']|verify_signature[\"']?\s*:\s*False|jwt\.decode\([^)]*verify\s*=\s*False|"
      r"ignoreExpiration\s*:\s*true|\.decode\(\s*token\s*\)(?!.*verify)|ValidateIssuerSigningKey\s*=\s*false|"
      r"ValidateLifetime\s*=\s*false|parseUnsecuredClaims|jwt\.decode\s*\(\s*\w+\s*\)",
      "JWT decodificado sin verificar firma o vencimiento.",
      "Verificá siempre la firma con algoritmos explícitos y el vencimiento (jwt.verify / decode con key y algorithms).", "CWE-347"),
    R("SEG-PATH", "Seguridad", "Alta", CODIGO,
      r"(open|readFile\w*|createReadStream|sendFile|send_file|File\.(Read|Open)\w*|file_get_contents|fopen|readfile|"
      r"FileInputStream|Paths\.get|os\.Open|res\.download)\s*\([^)]*(req(uest)?\.(query|params|body|args|form|files|GET|POST)|"
      r"\$_(GET|POST|REQUEST)|params\[|getParameter\()|\b(include|require)(_once)?\s*\(?\s*\$_(GET|POST|REQUEST)",
      "Ruta de archivo construida con datos de la request: posible path traversal / LFI.",
      "Resolvé la ruta contra un directorio base y verificá que quede adentro (realpath), o usá un id contra una lista blanca.", "CWE-22"),
    R("SEG-SSRF", "Seguridad", "Alta", CODIGO,
      r"(requests\.(get|post|put|delete|request)|urlopen|fetch|axios(\.\w+)?|http\.(get|request)|got|HttpClient\(\)\.\w+|"
      r"RestTemplate\(\)\.\w+|file_get_contents|curl_init|http\.Get|WebClient)\s*\([^)]*"
      r"(req(uest)?\.(query|params|body|args|form|GET|POST)|\$_(GET|POST|REQUEST)|getParameter\()",
      "La app hace un request a una URL que viene de la request del usuario: posible SSRF.",
      "Validá la URL contra una lista blanca de hosts y bloqueá IPs internas/metadata (169.254.169.254).", "CWE-918"),
    R("SEG-REDIRECT", "Seguridad", "Media", CODIGO,
      r"(redirect|sendRedirect|Redirect|res\.redirect|header\(\s*[\"']Location:)\s*\(?[^)]*"
      r"(req(uest)?\.(query|params|body|args|GET)|\$_(GET|POST|REQUEST)|getParameter\()",
      "Redirección a un destino que controla el usuario: posible open redirect.",
      "Redirigí solo a rutas relativas o a hosts de una lista blanca.", "CWE-601"),
    R("SEG-LOG-SENSIBLE", "Seguridad", "Media", CODIGO,
      r"(console\.(log|info|debug|warn|error)|\bprint\s*\(|logger\.\w+|logging\.\w+|\blog\.\w+|Log\.\w|System\.out\.print\w*|"
      r"fmt\.Print\w*|error_log|puts)\s*\(?.*\b(password|passwd|contrase(ñ|n)a|clave|secret|token|api_?key|authorization|"
      r"tarjeta|card_?number|cvv)\b",
      "Posible dato sensible (contraseña, token, tarjeta) escrito en logs o en consola.",
      "No loguees credenciales ni datos de pago; enmascaralos o logueá solo un identificador.", "CWE-532", en_tests=False),
    R("SEG-DEBUG", "Seguridad", "Media", PY | JS | PHP | CS | JVM,
      r"^\s*DEBUG\s*=\s*True\b|app\.run\([^)]*debug\s*=\s*True|display_errors[\"']?\s*,\s*[\"']?(1|on|true)|"
      r"UseDeveloperExceptionPage\(\)|app\.debug\s*=\s*True",
      "Modo debug activo en código de la app: expone trazas y a veces una consola remota.",
      "Activá el debug solo por variable de entorno y nunca en producción.", "CWE-489", en_tests=False),
    R("SEG-XXE", "Seguridad", "Baja", PY | JVM | CS | PHP,
      r"DocumentBuilderFactory\.newInstance\(\)|SAXParserFactory\.newInstance\(\)|XMLInputFactory\.newInstance\(\)|"
      r"\bxml\.etree\.ElementTree\b|\blxml\.etree\.(parse|fromstring)\b|xml\.dom\.minidom|LIBXML_NOENT|XmlResolver\s*=\s*new",
      "Parser XML que puede resolver entidades externas (XXE) si no se configura.",
      "Deshabilitá DTD/entidades externas (setFeature disallow-doctype-decl) o usá defusedxml en Python.", "CWE-611"),
    R("SEG-ASSERT", "Seguridad", "Baja", PY,
      r"^\s*assert\s+.*\b(is_admin|is_authenticated|permission|authorized|user|role|rol)\b",
      "Control de acceso con assert: se elimina al correr Python con -O.",
      "Usá un if explícito que levante una excepción.", "CWE-617", en_tests=False),

    # ---------------- Performance
    R("PERF-SELECT-ASTERISCO", "Performance", "Baja", CODIGO | {"SQL"}, r"\bselect\s+\*\s+from\b",
      "SELECT * trae todas las columnas.", "Pedí solo las columnas que se usan (menos I/O, menos red y índices cubrientes).",
      en_tests=False),
    R("PERF-IO-SINCRONA", "Performance", "Baja", JS,
      r"\b(readFileSync|writeFileSync|appendFileSync|readdirSync|statSync|execSync|spawnSync)\s*\(",
      "I/O síncrona en Node: bloquea el event loop mientras dura.",
      "En código de servidor usá las versiones async (fs.promises, execFile con callback/promesa).", en_tests=False),
    R("PERF-SLEEP", "Performance", "Baja", CODIGO,
      r"\btime\.sleep\s*\(|Thread\.sleep\s*\(|\bsleep\s*\(\s*\d|Task\.Delay\(\s*\d{4,}|time\.Sleep\(",
      "Espera fija en el código de la app.", "Reemplazá la espera fija por un evento, un reintento con backoff o un timeout.",
      en_tests=False),
    R("PERF-CLONADO-JSON", "Performance", "Baja", JS, r"JSON\.parse\(\s*JSON\.stringify\(",
      "Clonado profundo con JSON.parse(JSON.stringify()): lento y pierde fechas, Map/Set y undefined.",
      "Usá structuredClone() o copiá solo lo necesario."),
    R("PERF-CONTAR-TODO", "Performance", "Media", PY | JS | JVM | CS | PHP | RB,
      r"\blen\(\s*[\w.]+\.objects\.(all|filter)\(|\.(findAll|find|all)\(\s*\)\s*\.(length|size\(\)|count\(\)|Count\(\))|"
      r"\.ToList\(\)\.Count\b|\bcount\(\s*\$\w+->get\(\)",
      "Se traen todos los registros solo para contarlos.", "Contá en la base (COUNT / .count() / .exists()).", en_tests=False),
    R("PERF-FOREACH-ASYNC", "Confiabilidad", "Media", JS, r"\.forEach\s*\(\s*async\b",
      "forEach con callback async: no espera las promesas (los errores se pierden y el orden no está garantizado).",
      "Usá for...of con await (secuencial) o await Promise.all(items.map(async ...)) (en paralelo)."),

    # ---------------- Confiabilidad
    R("CONF-EXCEPT-DESNUDO", "Confiabilidad", "Media", PY, r"^\s*except\s*:",
      "except: sin tipo atrapa todo, incluso KeyboardInterrupt y SystemExit.",
      "Atrapá la excepción concreta (o Exception como mínimo) y logueala."),
    R("CONF-CATCH-VACIO", "Confiabilidad", "Media", JS | JVM | CS | PHP,
      r"catch\s*(\([^)]*\))?\s*\{\s*\}|\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*\{\s*\}\s*\)|\.catch\(\s*\(\)\s*=>\s*(null|undefined)\s*\)",
      "Excepción tragada: el error desaparece sin rastro.", "Logueá el error, propagalo o manejalo explícitamente."),
    R("CONF-CATCH-GENERICO", "Confiabilidad", "Baja", JVM | CS,
      r"catch\s*\(\s*(final\s+)?(Exception|Throwable|RuntimeException)\s+\w+\s*\)|catch\s*\(\s*Exception\s*\)",
      "Se atrapa Exception/Throwable genérico.", "Atrapá las excepciones concretas que sabés manejar.", en_tests=False),
    R("CONF-ERROR-IGNORADO", "Confiabilidad", "Media", GO,
      r"^\s*\w+\s*,\s*_\s*:?=\s*[\w.]+\(|^\s*_\s*=\s*[\w.]+\.(Close|Write|Exec|Commit|Flush|Sync)\(",
      "Error de Go descartado con _.", "Chequeá el error (if err != nil) o justificá por qué se ignora.", en_tests=False),
    R("CONF-ASYNC-VOID", "Confiabilidad", "Media", CS, r"\basync\s+void\s+(?!On\w*\()\w+\s*\(",
      "async void: las excepciones no se pueden atrapar y nadie espera la tarea.", "Devolvé Task (async void solo para event handlers)."),
    R("CONF-PRINTSTACKTRACE", "Confiabilidad", "Baja", JVM, r"\.printStackTrace\s*\(\s*\)",
      "printStackTrace() va a la salida estándar y no al log.", "Usá el logger con el error como parámetro.", en_tests=False),
    R("CONF-SUPRESION-ERROR", "Confiabilidad", "Baja", PHP, r"(?<![\w@])@(\$|\w+\s*\()",
      "Operador @ de PHP: silencia errores.", "Manejá el error explícitamente.", en_tests=False),
    R("CONF-COMPARA-NONE", "Malas prácticas", "Baja", PY, r"[!=]=\s*None\b",
      "Comparación con None usando == o !=.", "Usá is None / is not None."),

    # ---------------- Malas prácticas
    R("MP-CONSOLE", "Malas prácticas", "Baja", JS, r"\bconsole\.(log|debug|trace|dir)\s*\(",
      "console.log en el código.", "Sacalo o usá el logger del proyecto con nivel.", en_tests=False),
    R("MP-SYSOUT", "Malas prácticas", "Baja", JVM | CS, r"System\.(out|err)\.print|Console\.Write(Line)?\s*\(",
      "Salida por consola en lugar del logger.", "Usá el logger del proyecto.", en_tests=False),
    R("MP-DEBUGGER", "Malas prácticas", "Media", JS | PY | RB | PHP,
      r"^\s*debugger\s*;?\s*$|\bpdb\.set_trace\(\)|\bbreakpoint\(\)|\bbinding\.pry\b|\bvar_dump\s*\(|\bdd\s*\(",
      "Punto de depuración olvidado.", "Sacalo antes de mergear.", en_tests=False),
    R("MP-IGUALDAD-LAXA", "Malas prácticas", "Baja", JS, r"[^=!<>]==[^=]|!=[^=]",
      "== / != en JavaScript hace conversión de tipos.", "Usá === y !==."),
    R("MP-VAR", "Malas prácticas", "Baja", JS, r"^\s*var\s+\w", "var tiene alcance de función y hoisting.", "Usá const o let."),
    R("MP-ANY", "Malas prácticas", "Baja", TS, r":\s*any\b|\bas\s+any\b|<any>", "Tipo any: se pierde el chequeo de tipos.",
      "Tipá el valor o usá unknown y validá."),
    R("MP-SUPRESION-LINTER", "Malas prácticas", "Baja", CODIGO,
      r"@ts-ignore|@ts-nocheck|eslint-disable(?!-next-line\s+\S)|#\s*noqa\s*$|#\s*type:\s*ignore\s*$|//\s*nolint\s*$|"
      r"#\s*pylint:\s*disable=all|@SuppressWarnings\(\"all\"\)|#pragma warning disable\s*$",
      "Supresión amplia del linter o del chequeo de tipos.", "Suprimí la regla concreta y dejá el motivo en un comentario."),
    R("MP-IMPORT-ASTERISCO", "Malas prácticas", "Baja", PY | JVM, r"^\s*from\s+\S+\s+import\s+\*|^\s*import\s+[\w.]+\.\*\s*;",
      "Import con *: no se sabe de dónde sale cada nombre y puede pisar otros.", "Importá los nombres explícitos."),
    R("MP-GLOBAL", "Malas prácticas", "Baja", PY, r"^\s*global\s+\w", "Uso de global: estado compartido difícil de seguir y testear.",
      "Pasá el valor como parámetro o encapsulalo en una clase.", en_tests=False),
    R("MP-PENDIENTE", "Malas prácticas", "Baja", CODIGO, r"(#|//|/\*|\*|--)\s*(TODO|FIXME|HACK|XXX)\b",
      "Comentario de trabajo pendiente (TODO/FIXME/HACK).", "Resolvelo o pasalo a un ticket con su link.", en_tests=False, flags=0),
    R("MP-HARDCODEADO", "Malas prácticas", "Baja", CODIGO,
      r"[\"'`]https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)[:/\"'`]",
      "URL o IP de un ambiente hardcodeada.", "Leela de configuración / variables de entorno.", en_tests=False),
]

# Llamadas que, dentro de un loop, sugieren N+1 (base de datos o red).
RX_DB = re.compile(r"\.objects\.(get|filter|all|create)\(|\.(execute|executemany|query|raw|findOne|findById|findUnique|"
                   r"findFirst|findByPk|findAll|find_by|find_one|first|fetchone|fetchall|save|update_one|insert_one)\s*\(|"
                   r"\bSession\.query\(|\.Where\(|\.FirstOrDefault\(|\$wpdb->|->(get|first|find)\(\)|\bdb\.\w+\(|\bsql\.\w+\(", re.I)
RX_HTTP = re.compile(r"\brequests\.(get|post|put|patch|delete)\(|\bfetch\(|\baxios(\.\w+)?\(|\burlopen\(|\bhttp\.(get|request)\(|"
                     r"\bHttpClient\b|\.(getForObject|exchange|GetAsync|PostAsync)\(|\bhttp\.(Get|Post)\(|\bcurl_exec\(", re.I)
RX_LOOP_LLAVES = re.compile(r"^\s*(for|while|foreach)\b|\.(forEach|each)\s*\(")
RX_REGEX_COMPILE = re.compile(r"\bre\.compile\(|Pattern\.compile\(|new\s+RegExp\(|new\s+Regex\(|regexp\.(Must)?Compile\(")
SOLO_SINTAXIS = {"MP-IGUALDAD-LAXA", "MP-VAR", "MP-ANY", "CONF-COMPARA-NONE", "CONF-CATCH-VACIO", "MP-CONSOLE",
                 "CONF-EXCEPT-DESNUDO", "MP-DEBUGGER", "SEG-EVAL", "PERF-FOREACH-ASYNC"}
PALABRAS_NO_FUNCION = {"if", "for", "while", "switch", "catch", "with", "return", "foreach", "using", "lock", "elseif",
                       "else", "do", "try", "synchronized", "new", "throw", "await", "typeof", "sizeof", "function", "fixed"}
RX_HEADER = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(\w*)\s*\("            # JS function
    r"|^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function\b|\([^)]*\)\s*(?::[^=]+)?=>|\w+\s*=>)"  # JS flecha
    r"|^\s*func\s+(?:\([^)]*\)\s*)?(\w+)\s*\("                                              # Go
    r"|^\s*(?:(?:public|private|protected|internal|static|final|abstract|override|virtual|async|synchronized|suspend|"
    r"inline|open|fun|def|fn|pub|unsafe|extern|readonly|sealed|partial|function)\s+)*"
    r"(?:[\w<>\[\],.?*&:]+\s+)?(\w+)\s*(?:<[^>]*>)?\s*\([^;]*$"                               # métodos C-like
)


# ------------------------------------------------------------------ utilidades puras

def lenguaje(ruta):
    p = Path(ruta)
    if p.name.endswith(".min.js") or p.name.endswith(".min.css"):
        return None
    return LENGUAJES.get(p.suffix.lower())


def es_test(ruta):
    r = "/" + str(ruta).replace("\\", "/").lower()
    return bool(re.search(r"/(tests?|__tests__|spec|specs|testing|e2e|fixtures?|mocks?|__mocks__)/|"
                          r"(_test\.(go|py)|\.test\.\w+|\.spec\.\w+|/test_[^/]+\.py|tests?\.cs|Test\.java|Tests?\.kt)$", r))


def es_generado(ruta, texto):
    nombre = Path(ruta).name.lower()
    if re.search(r"(_pb2(_grpc)?\.py|\.pb\.go|\.g\.dart|\.designer\.cs|\.generated\.\w+|\.d\.ts|-lock\.json|\.lock)$", nombre):
        return True
    cabeza = texto[:600].lower()
    if "@generated" in cabeza or "do not edit" in cabeza or "auto-generated" in cabeza or "autogenerated" in cabeza:
        return True
    lineas = texto.count("\n") + 1
    return len(texto) / lineas > 400  # minificado


def sanear(texto, leng):
    """Reemplaza el contenido de strings y comentarios por espacios (conserva saltos de línea y la longitud),
    para contar llaves y palabras clave sin falsos positivos."""
    out, i, n = [], 0, len(texto)
    comentario_hash = leng in ("Python", "Ruby", "Shell", "PHP")
    while i < n:
        c = texto[i]
        dos = texto[i:i + 2]
        if dos == "//" and leng != "Python" or (c == "#" and comentario_hash):
            j = texto.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif dos == "/*" and leng != "Python":
            j = texto.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", texto[i:j]))
            i = j
        elif c in "\"'`":
            triple = texto[i:i + 3] if texto[i:i + 3] in ('"""', "'''") else None
            fin = triple or c
            j = i + len(fin)
            while j < n:
                if texto[j] == "\\":
                    j += 2
                    continue
                if texto.startswith(fin, j):
                    j += len(fin)
                    break
                if texto[j] == "\n" and not triple and c != "`":
                    break
                j += 1
            out.append(fin[0] + re.sub(r"[^\n]", " ", texto[i + 1:j - 1]) + (texto[j - 1] if j - 1 > i else ""))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _cerrar_bloque(saneado, desde):
    """Línea (0-based) donde se cierra el bloque que abre la primera llave a partir del offset `desde`."""
    k = saneado.find("{", desde)
    if k < 0 or saneado.count("\n", desde, k) > 3:
        return None, None
    prof = 0
    for j in range(k, len(saneado)):
        ch = saneado[j]
        if ch == "{":
            prof += 1
        elif ch == "}":
            prof -= 1
            if prof == 0:
                return saneado.count("\n", 0, k), saneado.count("\n", 0, j)
    return saneado.count("\n", 0, k), saneado.count("\n")


def funciones_llaves(texto, leng):
    """[{nombre, linea, fin, lineas, complejidad, parametros, anidamiento}] por heurística de llaves."""
    san = sanear(texto, leng)
    lineas_san = san.split("\n")
    offsets, acc = [], 0
    for ln in lineas_san:
        offsets.append(acc)
        acc += len(ln) + 1
    out, vistos = [], set()
    for i, ln in enumerate(lineas_san):
        m = RX_HEADER.match(ln)
        if not m:
            continue
        nombre = next((g for g in m.groups() if g), "") or "(anónima)"
        if nombre in PALABRAS_NO_FUNCION or (m.group(4) and not re.search(r"\)\s*(\{|:|throws|=>|where|->|$)", ln + " ")):
            continue
        if m.group(4) and re.match(r"^\s*(return|else|new|await|throw)\b", ln):
            continue
        ini, fin = _cerrar_bloque(san, offsets[i])
        if ini is None or (i, ini) in vistos:
            continue
        vistos.add((i, ini))
        cuerpo = "\n".join(lineas_san[ini:fin + 1])
        compl = 1 + len(re.findall(r"\b(if|for|foreach|while|case|catch|except|elif|elsif|when)\b|&&|\|\||\?\?", cuerpo))
        prof = maxprof = 0
        for ch in cuerpo:
            if ch == "{":
                prof += 1
                maxprof = max(maxprof, prof)
            elif ch == "}":
                prof -= 1
        params_txt = re.search(r"\(([^)]*)\)", ln)
        params = [p for p in (params_txt.group(1).split(",") if params_txt else []) if p.strip()]
        out.append({"nombre": nombre, "linea": i + 1, "fin": fin + 1, "lineas": fin - i + 1, "complejidad": compl,
                    "parametros": len(params), "anidamiento": max(0, maxprof - 1)})
    return out


class _VisitaPy(ast.NodeVisitor):
    """Métricas y patrones de Python con el árbol sintáctico real."""
    RAMAS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.With, ast.AsyncWith,
             ast.comprehension, ast.Assert)

    def __init__(self, lineas):
        self.lineas, self.funciones, self.hallazgos = lineas, [], []

    def _texto(self, n):
        return self.lineas[n - 1] if 0 < n <= len(self.lineas) else ""

    def _funcion(self, nodo):
        compl, maxprof = 1, 0

        def recorrer(n, prof):
            nonlocal compl, maxprof
            for h in ast.iter_child_nodes(n):
                if isinstance(h, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    continue
                es_rama = isinstance(h, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith))
                if isinstance(h, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.comprehension)):
                    compl += 1
                if isinstance(h, ast.BoolOp):
                    compl += len(h.values) - 1
                if hasattr(ast, "match_case") and isinstance(h, ast.match_case):
                    compl += 1
                maxprof = max(maxprof, prof + es_rama)
                recorrer(h, prof + es_rama)

        recorrer(nodo, 0)
        args = nodo.args
        params = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs if a.arg not in ("self", "cls")]
        fin = getattr(nodo, "end_lineno", nodo.lineno)
        self.funciones.append({"nombre": nodo.name, "linea": nodo.lineno, "fin": fin, "lineas": fin - nodo.lineno + 1,
                               "complejidad": compl, "parametros": len(params), "anidamiento": maxprof})
        for d in args.defaults + args.kw_defaults:
            if isinstance(d, (ast.List, ast.Dict, ast.Set)) or (isinstance(d, ast.Call) and getattr(d.func, "id", "") in ("list", "dict", "set")):
                self.hallazgos.append(("CONF-DEFAULT-MUTABLE", d.lineno))
        self.generic_visit(nodo)

    visit_FunctionDef = visit_AsyncFunctionDef = _funcion

    def _loop(self, nodo):
        es_async_for = isinstance(nodo, ast.AsyncFor)
        anidados = sum(1 for h in ast.walk(nodo) if isinstance(h, (ast.For, ast.AsyncFor, ast.While)) and h is not nodo)
        if anidados and any(isinstance(h, (ast.For, ast.AsyncFor, ast.While)) and h is not nodo and
                            any(isinstance(k, (ast.For, ast.AsyncFor, ast.While)) and k is not h for k in ast.walk(h))
                            for h in ast.walk(nodo)):
            self.hallazgos.append(("PERF-LOOPS-ANIDADOS", nodo.lineno))
        for h in ast.walk(nodo):
            if h is nodo or not hasattr(h, "lineno"):
                continue
            if isinstance(h, ast.Await) and not es_async_for:
                self.hallazgos.append(("PERF-AWAIT-EN-LOOP", h.lineno))
            if isinstance(h, ast.Call):
                t = self._texto(h.lineno)
                if RX_DB.search(t):
                    self.hallazgos.append(("PERF-N-MAS-1", h.lineno))
                elif RX_HTTP.search(t):
                    self.hallazgos.append(("PERF-HTTP-EN-LOOP", h.lineno))
                elif RX_REGEX_COMPILE.search(t):
                    self.hallazgos.append(("PERF-REGEX-EN-LOOP", h.lineno))
        self.generic_visit(nodo)

    visit_For = visit_AsyncFor = visit_While = _loop

    def visit_ExceptHandler(self, nodo):
        if len(nodo.body) == 1 and isinstance(nodo.body[0], (ast.Pass,)) or \
                (len(nodo.body) == 1 and isinstance(nodo.body[0], ast.Expr) and isinstance(getattr(nodo.body[0], "value", None), ast.Constant)
                 and nodo.body[0].value.value is Ellipsis):
            self.hallazgos.append(("CONF-EXCEPT-VACIO", nodo.lineno))
        self.generic_visit(nodo)


REGLAS_ESTRUCTURA = {
    "CONF-DEFAULT-MUTABLE": ("Confiabilidad", "Media", "Argumento por defecto mutable ([], {}, set()): se comparte entre llamadas.",
                             "Usá None como default y creá el objeto adentro de la función.", None),
    "CONF-EXCEPT-VACIO": ("Confiabilidad", "Media", "Excepción tragada con pass: el error desaparece sin rastro.",
                          "Logueá el error, propagalo o manejalo explícitamente.", "CWE-390"),
    "PERF-N-MAS-1": ("Performance", "Media", "Consulta a la base dentro de un loop: posible problema N+1.",
                     "Traé los datos en una sola consulta (IN, join, select_related/prefetch_related, include) antes del loop.", None),
    "PERF-HTTP-EN-LOOP": ("Performance", "Media", "Llamada HTTP dentro de un loop: una por iteración, en serie.",
                          "Usá un endpoint por lotes, cacheá, o hacé las llamadas en paralelo con un límite de concurrencia.", None),
    "PERF-AWAIT-EN-LOOP": ("Performance", "Baja", "await dentro de un loop: las operaciones corren una detrás de otra.",
                           "Si son independientes, lanzalas juntas (Promise.all / asyncio.gather) con un límite de concurrencia.", None),
    "PERF-REGEX-EN-LOOP": ("Performance", "Baja", "Se compila una expresión regular en cada iteración.",
                           "Compilala una vez fuera del loop (constante de módulo).", None),
    "PERF-LOOPS-ANIDADOS": ("Performance", "Baja", "Tres o más loops anidados: complejidad cúbica o peor.",
                            "Revisá si un diccionario/set o un índice evita recorrer todo en cada nivel.", None),
    "MAN-FUNCION-LARGA": ("Mantenibilidad", None, "Función demasiado larga.", "Dividila en funciones con una sola responsabilidad.", None),
    "MAN-COMPLEJIDAD": ("Mantenibilidad", None, "Complejidad ciclomática alta: muchos caminos, difícil de testear.",
                        "Extraé ramas a funciones, usá early return o tablas de despacho.", None),
    "MAN-PARAMETROS": ("Mantenibilidad", "Baja", "Demasiados parámetros.", "Agrupalos en un objeto/estructura de opciones.", None),
    "MAN-ANIDAMIENTO": ("Mantenibilidad", None, "Anidamiento profundo de bloques.", "Usá early return / guard clauses y extraé funciones.", None),
    "MAN-ARCHIVO-LARGO": ("Mantenibilidad", None, "Archivo muy largo.", "Separalo por responsabilidad en módulos más chicos.", None),
    "MAN-DUPLICADO": ("Mantenibilidad", None, "Bloque de código duplicado.", "Extraé la lógica común a una función/módulo compartido.", None),
}


def loops_llaves(texto, leng, lineas):
    """[(regla, linea)] de llamadas a BD/HTTP, await y regex dentro de loops en lenguajes con llaves."""
    san = sanear(texto, leng)
    san_lineas = san.split("\n")
    out, offsets, acc = [], [], 0
    for ln in san_lineas:
        offsets.append(acc)
        acc += len(ln) + 1
    for i, ln in enumerate(san_lineas):
        if not RX_LOOP_LLAVES.search(ln) or re.search(r"\bfor\s+await\b", ln):
            continue
        ini, fin = _cerrar_bloque(san, offsets[i])
        if ini is None:
            continue
        for j in range(ini, min(fin + 1, len(lineas))):
            t = lineas[j]
            if j == i:
                t = t[t.find("{") + 1:] if "{" in t else ""
            if RX_DB.search(t):
                out.append(("PERF-N-MAS-1", j + 1))
            elif RX_HTTP.search(t):
                out.append(("PERF-HTTP-EN-LOOP", j + 1))
            elif re.search(r"\bawait\b", t) and not re.search(r"\.(forEach|each)\s*\(", ln):
                out.append(("PERF-AWAIT-EN-LOOP", j + 1))
            elif RX_REGEX_COMPILE.search(t):
                out.append(("PERF-REGEX-EN-LOOP", j + 1))
    return sorted(set(out), key=lambda x: x[1])


def metricas_a_hallazgos(funciones):
    out = []
    for f in funciones:
        if f["lineas"] > 60:
            out.append(("MAN-FUNCION-LARGA", f["linea"], "Media" if f["lineas"] > 120 else "Baja",
                        f"{f['nombre']}: {f['lineas']} líneas (límite sugerido 60)."))
        if f["complejidad"] > 15:
            out.append(("MAN-COMPLEJIDAD", f["linea"], "Alta" if f["complejidad"] > 30 else "Media",
                        f"{f['nombre']}: complejidad {f['complejidad']} (límite sugerido 15)."))
        if f["parametros"] > 6:
            out.append(("MAN-PARAMETROS", f["linea"], "Baja", f"{f['nombre']}: {f['parametros']} parámetros (límite sugerido 6)."))
        if f["anidamiento"] > 4:
            out.append(("MAN-ANIDAMIENTO", f["linea"], "Media" if f["anidamiento"] > 6 else "Baja",
                        f"{f['nombre']}: {f['anidamiento']} niveles de anidamiento (límite sugerido 4)."))
    return out


def _normalizar(linea):
    t = linea.strip()
    if not t or t in ("{", "}", "};", ");", ")", "]", "end", "else:", "else {", "} else {", "pass", "return", "break") \
            or re.match(r"^(#|//|/\*|\*|--|import\b|from\s+\S+\s+import|using\s|package\s|@)", t):
        return None
    return re.sub(r"\s+", " ", t)


def duplicados(archivos, ventana=8):
    """[(archivo, linea, largo, [(otro_archivo, otra_linea)])] de bloques de `ventana`+ líneas normalizadas repetidos."""
    vistos, por_archivo = {}, {}
    for ruta, lineas in archivos:
        norm = [(i + 1, n) for i, l in enumerate(lineas) if (n := _normalizar(l))]
        por_archivo[ruta] = norm
        for k in range(len(norm) - ventana + 1):
            h = hashlib.md5("\n".join(x[1] for x in norm[k:k + ventana]).encode(), usedforsecurity=False).hexdigest()
            vistos.setdefault(h, []).append((ruta, k))
    dup = {(r, k): h for h, ubic in vistos.items() if len({(r, k) for r, k in ubic}) > 1 for r, k in ubic}
    out, reportados = [], set()
    for ruta, norm in por_archivo.items():
        k = 0
        while k < len(norm):
            if (ruta, k) in dup and (ruta, k - 1) not in dup:
                h = dup[(ruta, k)]
                largo = ventana
                while (ruta, k + largo - ventana + 1) in dup:
                    largo += 1
                otros = [(r, por_archivo[r][j][0]) for r, j in vistos[h] if (r, j) != (ruta, k)]
                clave = frozenset([(ruta, norm[k][0])] + otros)
                if clave not in reportados:
                    reportados.add(clave)
                    out.append((ruta, norm[k][0], largo, otros[:5]))
                k += largo - ventana + 1
            else:
                k += 1
    return out


def en_rangos(linea, rangos):
    return any(a <= linea <= b for a, b in rangos)


# ------------------------------------------------------------------ escaneo de un archivo

def revisar_archivo(rel, texto, leng):
    """[hallazgo] de un archivo (sin duplicados ni externos). Puro: recibe el texto."""
    lineas = texto.splitlines()
    test = es_test(rel)
    hall = []

    def agregar(regla, linea, cat, sev, msg, rec, cwe=None, detalle=None):
        t = lineas[linea - 1] if 0 < linea <= len(lineas) else ""
        if test and sev in ("Crítica", "Alta", "Media"):  # en tests el riesgo es menor: un nivel menos
            sev = SEVERIDADES[SEVERIDADES.index(sev) + 1]
        if "k0lmenia: ignorar" in t:
            return None
        hall.append({"regla": regla, "categoria": cat, "severidad": sev, "archivo": rel, "linea": linea,
                     "mensaje": detalle or msg, "recomendacion": rec, "cwe": cwe, "fragmento": t.strip()[:160],
                     "origen": "k0lmenia", "en_test": test})
        return hall[-1]

    san_lineas = sanear(texto, leng).split("\n") if leng in LLAVES or leng == "Python" else None
    for regla in REGLAS:
        if leng not in regla["lenguajes"] or (test and not regla["en_tests"]):
            continue
        for i, l in enumerate(lineas, 1):
            if len(l) > 1000:
                continue
            m = regla["rx"].search(l)
            if not m:
                continue
            if san_lineas and i - 1 < len(san_lineas):
                san = san_lineas[i - 1]
                # Reglas de sintaxis: si el match cae dentro de un string o comentario, no cuenta.
                if regla["id"] in SOLO_SINTAXIS and not regla["rx"].search(san):
                    continue
                # Línea que es solo un comentario o un literal de texto (docs, tablas de patrones): no es código.
                if regla["id"] not in ("SEG-SQL", "MP-PENDIENTE") and not re.sub(r"\b[rbfuRBFU]{1,2}(?=[\"'])", "", san).strip(" \t\"'`,;+()[]"):
                    continue
            agregar(regla["id"], i, regla["categoria"], regla["severidad"], regla["mensaje"], regla["recomendacion"], regla["cwe"])

    funciones = []
    if leng == "Python":
        try:
            arbol = ast.parse(texto)
            v = _VisitaPy(lineas)
            v.visit(arbol)
            funciones = v.funciones
            estructura = v.hallazgos
        except (SyntaxError, ValueError, RecursionError):
            estructura = []
    elif leng in LLAVES:
        funciones = funciones_llaves(texto, leng)
        estructura = loops_llaves(texto, leng, lineas)
    else:
        estructura = []
    for regla, linea in sorted(set(estructura), key=lambda x: x[1]):
        cat, sev, msg, rec, cwe = REGLAS_ESTRUCTURA[regla]
        if test and regla.startswith("PERF"):
            continue
        agregar(regla, linea, cat, sev, msg, rec, cwe)
    if not test:
        for regla, linea, sev, detalle in metricas_a_hallazgos(funciones):
            cat, _, msg, rec, cwe = REGLAS_ESTRUCTURA[regla]
            agregar(regla, linea, cat, sev, msg, rec, cwe, detalle=f"{msg} {detalle}")
        if len(lineas) > 500 and leng in CODIGO:
            cat, _, msg, rec, _ = REGLAS_ESTRUCTURA["MAN-ARCHIVO-LARGO"]
            agregar("MAN-ARCHIVO-LARGO", 1, cat, "Media" if len(lineas) > 1000 else "Baja", msg, rec,
                    detalle=f"{msg} {len(lineas)} líneas (límite sugerido 500).")

    for tipo, linea, frag in sast.buscar_secretos(texto):
        h = agregar("SEG-SECRETO", linea, "Seguridad", "Alta",
                    f"Posible secreto en el código: {tipo}.",
                    "Rotá la credencial, sacala del código y del histórico de git, y leela de un vault o variable de entorno.",
                    "CWE-798")
        if h:
            h["fragmento"] = frag  # redactado: nunca la línea con el valor completo
    return hall, funciones


# ------------------------------------------------------------------ externos opcionales

def correr(cmd, cwd, timeout=900):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return p.stdout


SEV_SEMGREP = {"ERROR": "Alta", "WARNING": "Media", "INFO": "Baja"}


def parse_semgrep(data):
    out = []
    for r in (data or {}).get("results") or []:
        extra = r.get("extra") or {}
        meta = extra.get("metadata") or {}
        cats = " ".join(str(x) for x in (meta.get("category"), meta.get("subcategory"), r.get("check_id")) if x).lower()
        cat = "Seguridad" if "security" in cats else "Performance" if "performance" in cats else \
            "Confiabilidad" if "correctness" in cats else "Malas prácticas"
        cwe = meta.get("cwe")
        out.append({"regla": r.get("check_id"), "categoria": cat, "severidad": SEV_SEMGREP.get(extra.get("severity"), "Media"),
                    "archivo": r.get("path"), "linea": (r.get("start") or {}).get("line"),
                    "mensaje": (extra.get("message") or "")[:300], "recomendacion": "", "origen": "semgrep",
                    "cwe": (cwe[0] if isinstance(cwe, list) and cwe else cwe or None),
                    "fragmento": (extra.get("lines") or "").strip()[:160]})
    return out


def parse_ruff(data):
    out = []
    for r in data or []:
        code = r.get("code") or ""
        pref = re.match(r"[A-Z]+", code).group(0) if re.match(r"[A-Z]+", code) else ""
        cat = {"S": "Seguridad", "PERF": "Performance", "B": "Confiabilidad", "C": "Mantenibilidad", "F": "Confiabilidad",
               "E": "Malas prácticas", "SIM": "Malas prácticas"}.get(pref, "Malas prácticas")
        sev = "Alta" if code in ("F821", "F822", "F823", "F811", "E999") else "Media" if pref in ("S", "B") else "Baja"
        out.append({"regla": f"ruff:{code}", "categoria": cat, "severidad": sev, "archivo": r.get("filename"),
                    "linea": (r.get("location") or {}).get("row"), "mensaje": (r.get("message") or "")[:300],
                    "recomendacion": "", "origen": "ruff", "cwe": None, "fragmento": ""})
    return out


def parse_bandit(data):
    sev = {"HIGH": "Alta", "MEDIUM": "Media", "LOW": "Baja"}
    out = []
    for r in (data or {}).get("results") or []:
        cwe = (r.get("issue_cwe") or {}).get("id")
        out.append({"regla": f"bandit:{r.get('test_id')}", "categoria": "Seguridad", "severidad": sev.get(r.get("issue_severity"), "Media"),
                    "archivo": r.get("filename"), "linea": r.get("line_number"), "mensaje": (r.get("issue_text") or "")[:300],
                    "recomendacion": "", "origen": "bandit", "cwe": f"CWE-{cwe}" if cwe else None,
                    "fragmento": (r.get("code") or "").strip().splitlines()[0][:160] if r.get("code") else ""})
    return out


def externos(ruta, archivos, lenguajes, inv):
    hall = []
    rel = lambda p: str(Path(p).resolve().relative_to(Path(ruta).resolve())).replace("\\", "/") \
        if Path(p).is_absolute() else str(p).replace("\\", "/").lstrip("./")  # noqa: E731
    objetivo = archivos or ["."]
    if shutil.which("semgrep"):
        try:
            d = json.loads(correr(["semgrep", "scan", "--config", "p/default", "--json", "--quiet", "--metrics=off",
                                   "--disable-version-check", *objetivo], ruta) or "null")
            hall += parse_semgrep(d)
            inv["escaneres"].append("semgrep")
        except (OSError, subprocess.TimeoutExpired, ValueError) as ex:
            inv["errores"]["semgrep"] = str(ex)[:200]
    else:
        inv["errores"]["semgrep"] = "no instalado (opcional, más reglas de seguridad): pip install semgrep"
    if "Python" in lenguajes:
        py = [a for a in objetivo if a == "." or a.endswith(".py")]
        if shutil.which("ruff") and py:
            try:
                d = json.loads(correr(["ruff", "check", "--output-format", "json", "--exit-zero", "--no-cache",
                                       "--select", "F,E9,B,S,PERF,C90,SIM", *py], ruta) or "[]")
                hall += parse_ruff(d)
                inv["escaneres"].append("ruff")
            except (OSError, subprocess.TimeoutExpired, ValueError) as ex:
                inv["errores"]["ruff"] = str(ex)[:200]
        elif py:
            inv["errores"]["ruff"] = "no instalado (opcional, linter de Python): pip install ruff"
        if shutil.which("bandit") and py:
            try:
                args = ["-r", "."] if py == ["."] else py
                d = json.loads(correr(["bandit", "-f", "json", "-q", *args], ruta) or "null")
                hall += parse_bandit(d)
                inv["escaneres"].append("bandit")
            except (OSError, subprocess.TimeoutExpired, ValueError) as ex:
                inv["errores"]["bandit"] = str(ex)[:200]
        elif py:
            inv["errores"]["bandit"] = "no instalado (opcional, seguridad de Python): pip install bandit"
    for h in hall:
        if h.get("archivo"):
            h["archivo"] = rel(h["archivo"])
        h["en_test"] = es_test(h.get("archivo") or "")
    return hall


# ------------------------------------------------------------------ revisión completa

def listar(raiz):
    for p in sorted(raiz.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        partes = p.relative_to(raiz).parts
        if any(x in IGNORAR_DIR for x in partes[:-1]):
            continue
        yield p


def revisar(ruta, cambios=None, usar_externos=True):
    raiz = Path(ruta)
    inv = {"ruta": str(raiz), "generado": datetime.now().isoformat(timespec="seconds"), "escaneres": ["reglas k0lmenIA", "secretos (integrado)"],
           "errores": {}, "modo": "cambios" if cambios is not None else "repo"}
    solo = {c["archivo"]: c.get("lineas") or [] for c in cambios or [] if c.get("estado") != "borrado"} if cambios is not None else None
    por_leng, grandes, textos, todos, funciones_top = {}, [], [], [], []
    omitidos = {"generados": 0, "grandes": 0}
    for p in listar(raiz):
        rel = p.relative_to(raiz).as_posix()
        if solo is not None and rel not in solo:
            continue
        leng = lenguaje(p)
        if not leng:
            if p.suffix.lower() in sast.EXT_TEXTO and p.stat().st_size <= MAX_BYTES:  # solo secretos en config/.env
                try:
                    t = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for tipo, linea, frag in sast.buscar_secretos(t):
                    todos.append({"regla": "SEG-SECRETO", "categoria": "Seguridad", "severidad": "Alta", "archivo": rel,
                                  "linea": linea, "mensaje": f"Posible secreto en el código: {tipo}.", "cwe": "CWE-798",
                                  "recomendacion": "Rotá la credencial, sacala del repo (y del histórico de git) y leela de un vault o variable de entorno.",
                                  "fragmento": frag, "origen": "k0lmenia", "en_test": es_test(rel)})
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                omitidos["grandes"] += 1
                continue
            texto = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if es_generado(rel, texto):
            omitidos["generados"] += 1
            continue
        n = texto.count("\n") + 1
        d = por_leng.setdefault(leng, {"archivos": 0, "lineas": 0})
        d["archivos"] += 1
        d["lineas"] += n
        grandes.append((n, rel))
        hall, funcs = revisar_archivo(rel, texto, leng)
        todos += hall
        if not es_test(rel):
            funciones_top += [{**f, "archivo": rel} for f in funcs]
            if leng in CODIGO:
                textos.append((rel, texto.splitlines()))

    for ruta_a, linea, largo, otros in duplicados(textos):
        cat, _, msg, rec, _ = REGLAS_ESTRUCTURA["MAN-DUPLICADO"]
        donde = ", ".join(f"{r}:{l}" for r, l in otros)
        todos.append({"regla": "MAN-DUPLICADO", "categoria": cat, "severidad": "Media" if largo >= 20 else "Baja",
                      "archivo": ruta_a, "linea": linea, "mensaje": f"{msg} {largo}+ líneas iguales en {donde}.",
                      "recomendacion": rec, "cwe": None, "fragmento": "", "origen": "k0lmenia", "en_test": False})

    if usar_externos:
        todos += externos(raiz, sorted(solo) if solo is not None else None, set(por_leng), inv)

    # en_cambio, topes por regla/archivo e IDs
    vistos, por_regla, por_regla_archivo, finales, recortados = set(), {}, {}, [], 0
    orden = {s: i for i, s in enumerate(SEVERIDADES)}
    for h in sorted(todos, key=lambda x: (orden.get(x["severidad"], 9), x.get("archivo") or "", x.get("linea") or 0)):
        clave = (h.get("regla"), h.get("archivo"), h.get("linea"))
        if clave in vistos:
            continue
        vistos.add(clave)
        if solo is not None:
            h["en_cambio"] = en_rangos(h.get("linea") or 0, solo.get(h.get("archivo"), []))
        ka = (h["regla"], h.get("archivo"))
        por_regla_archivo[ka] = por_regla_archivo.get(ka, 0) + 1
        por_regla[h["regla"]] = por_regla.get(h["regla"], 0) + 1
        if por_regla_archivo[ka] > TOPE_POR_ARCHIVO or por_regla[h["regla"]] > TOPE_POR_REGLA:
            recortados += 1
            continue
        finales.append(h)
    for i, h in enumerate(finales, 1):
        h["id"] = f"R-{i:04d}"

    grandes.sort(reverse=True)
    funciones_top.sort(key=lambda f: (-f["complejidad"], -f["lineas"]))
    inv["inventario"] = {"archivos": sum(d["archivos"] for d in por_leng.values()),
                         "lineas": sum(d["lineas"] for d in por_leng.values()),
                         "por_lenguaje": dict(sorted(por_leng.items(), key=lambda x: -x[1]["lineas"])),
                         "mas_grandes": [{"archivo": r, "lineas": n} for n, r in grandes[:10]], "omitidos": omitidos}
    inv["funciones_mas_complejas"] = funciones_top[:15]
    inv["hallazgos"] = finales
    inv["resumen"] = {
        "total": len(finales), "recortados_por_tope": recortados,
        "por_severidad": {s: sum(1 for h in finales if h["severidad"] == s) for s in SEVERIDADES},
        "por_categoria": {c: sum(1 for h in finales if h["categoria"] == c) for c in CATEGORIAS},
        "por_regla": dict(sorted(por_regla.items(), key=lambda x: -x[1])),
        "en_tests": sum(1 for h in finales if h.get("en_test")),
    }
    if solo is not None:
        inv["resumen"]["en_cambios"] = sum(1 for h in finales if h.get("en_cambio"))
        inv["resumen"]["archivos_cambiados"] = len(solo)
    return inv


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Revisión estática de código (seguridad, performance, malas prácticas, "
                                             "confiabilidad y mantenibilidad). Solo lectura.")
    ap.add_argument("--ruta", default="", help="ruta del código a revisar")
    ap.add_argument("--origen", default="", help="manifiesto origen.json de obtener.py (toma la ruta y los cambios)")
    ap.add_argument("--todo", action="store_true", help="con --origen de un PR/rama: revisar todo el repo, no solo lo que cambió")
    ap.add_argument("--sin-externos", action="store_true", help="no correr semgrep/ruff/bandit aunque estén instalados")
    ap.add_argument("--salida", default="", help="ruta del JSON (por defecto, revision.json al lado del origen.json)")
    args = ap.parse_args(argv)
    man = None
    if args.origen:
        man = json.loads(Path(args.origen).read_text(encoding="utf-8"))
        ruta = Path(args.ruta or man["ruta_local"])
    elif args.ruta:
        ruta = Path(args.ruta)
    else:
        print("[revision] Pasá --ruta <carpeta> o --origen <origen.json>.", file=sys.stderr)
        return 2
    if not ruta.is_dir():
        print(f"[revision] La ruta {ruta} no existe.", file=sys.stderr)
        return 2
    cambios = None if (args.todo or not man) else man.get("cambios")
    inv = revisar(ruta, cambios, usar_externos=not args.sin_externos)
    if man:
        inv["origen"] = {k: man.get(k) for k in ("origen", "proveedor", "repo", "rama", "base", "commit", "pr", "modo",
                                                  "url_blob", "web", "diff") if man.get(k) is not None}
    salida = Path(args.salida) if args.salida else (Path(args.origen).parent / "revision.json" if args.origen else None)
    texto = json.dumps(inv, ensure_ascii=False, indent=2)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto, encoding="utf-8")
        print(f"[revision] Datos en {salida}", file=sys.stderr)
    else:
        print(texto)
    r = inv["resumen"]
    extra = f" ({r['en_cambios']} en líneas cambiadas de {r['archivos_cambiados']} archivo(s))" if "en_cambios" in r else ""
    sevs = ", ".join(f"{k} {v}" for k, v in r["por_severidad"].items() if v)
    print(f"[revision] {inv['inventario']['archivos']} archivo(s), {inv['inventario']['lineas']} líneas. "
          f"{r['total']} hallazgo(s){extra}{': ' + sevs if sevs else ''}. Escáneres: {', '.join(inv['escaneres'])}.", file=sys.stderr)
    for k, v in inv["errores"].items():
        print(f"[revision] {k}: {v}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

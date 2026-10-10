"""Piezas comunes de la integración con herramientas de gestión de pruebas.

- Carga del .env único de la raíz de k0lmenIA.
- Cliente HTTP con reintentos y modo --dry-run (muestra los requests sin enviarlos).
- Trazabilidad local: qué caso (CP-001) es qué key en la herramienta (PROJ-T12).
- Normalización de estados.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_GESTION = RAIZ / "output" / "gestion"

# Estados de k0lmenIA (CLAUDE.md) -> estado normalizado que entiende cada adaptador.
ESTADOS = {
    "aprobado": "aprobado", "passed": "aprobado", "pass": "aprobado",
    "fallido": "fallido", "failed": "fallido", "fail": "fallido",
    "bloqueado": "bloqueado", "blocked": "bloqueado",
    "pendiente": "pendiente", "skipped": "pendiente", "undefined": "pendiente",
    "pending": "pendiente", "ambiguous": "fallido", "n/a": "pendiente",
    "en ejecución": "en_ejecucion", "en ejecucion": "en_ejecucion",
}


class ErrorGestion(Exception):
    """Error con mensaje claro para la persona (se muestra sin traceback)."""


def necesitar(pkg, instalar=None):
    """Igual que en generar_casos.py: instala la librería si falta o avisa claro."""
    instalar = instalar or pkg
    try:
        return __import__(pkg)
    except ImportError:
        pass
    subprocess.run([sys.executable, "-m", "pip", "install", instalar, "--quiet"], check=False)
    try:
        return __import__(pkg)
    except ImportError:
        sys.exit(f"\n[!] Falta la librería '{instalar}' y no se pudo instalar sola.\n"
                 f"    Instalá las dependencias con:  pip install -r requirements.txt\n")


def cargar_env():
    """Carga el .env de la raíz sin pisar variables ya definidas en el entorno
    (mismas reglas que k0lmena: export, comillas, comentarios al final, BOM)."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _env import cargar_env as _cargar
    _cargar()


def env(nombre, obligatoria=True, defecto=""):
    valor = os.environ.get(nombre, "").strip() or defecto
    if obligatoria and not valor:
        raise ErrorGestion(f"Falta la variable {nombre} en el .env de la raíz (ver .env.example).")
    return valor


def normalizar_estado(estado):
    clave = (estado or "").strip().lower()
    if clave not in ESTADOS:
        raise ErrorGestion(f"Estado desconocido: '{estado}'.")
    return ESTADOS[clave]


def _espera_reintento(retry_after, intento):
    """Segundos a esperar según Retry-After (número o fecha HTTP); si no viene, backoff exponencial."""
    if retry_after:
        try:
            return max(int(float(retry_after)), 1)
        except ValueError:
            from email.utils import parsedate_to_datetime
            try:
                return max(int((parsedate_to_datetime(retry_after).timestamp() - time.time())), 1)
            except (TypeError, ValueError):
                pass
    return 2 ** intento


class Http:
    """requests con reintentos ante 429/5xx y modo dry-run."""

    def __init__(self, base, headers=None, dry_run=False, nombre="api", intervalo=0.0):
        self.base = base.rstrip("/")
        self.headers = headers or {}
        self.dry_run = dry_run
        self.nombre = nombre
        self.intervalo = intervalo  # segundos mínimos entre requests (rate limit de la herramienta)
        self._ultimo = 0.0
        self._contador = 0

    def _url(self, ruta):
        return ruta if ruta.startswith("http") else f"{self.base}/{ruta.lstrip('/')}"

    def request(self, metodo, ruta, *, json_body=None, params=None, files=None, data=None,
                headers=None, esperado=(200, 201, 204)):
        url = self._url(ruta)
        hdrs = {**self.headers, **(headers or {})}
        if self.dry_run:
            self._contador += 1
            cuerpo = json.dumps(json_body, ensure_ascii=False)[:600] if json_body is not None else ""
            extra = f" files={list(files)}" if files else ""
            print(f"[dry-run] {self.nombre} {metodo} {url} {params or ''} {cuerpo}{extra}")
            return {"__dry_run__": True, "id": f"DRY-{self._contador}", "ID": f"DRY-{self._contador}",
                    "key": f"DRY-{self._contador}"}
        requests = necesitar("requests")
        # Los adjuntos se leen una sola vez: un archivo abierto ya leído en el primer intento
        # llegaría vacío en el reintento.
        if files:
            files = {k: tuple(v[:1]) + ((v[1].read() if hasattr(v[1], "read") else v[1]),) + tuple(v[2:])
                     if isinstance(v, tuple) else (v.read() if hasattr(v, "read") else v)
                     for k, v in files.items()}
        r = None
        for intento in range(5):
            espera = self.intervalo - (time.time() - self._ultimo)
            if espera > 0:
                time.sleep(espera)
            self._ultimo = time.time()
            try:
                r = requests.request(metodo, url, json=json_body, params=params, files=files,
                                     data=data, headers=hdrs, timeout=120)
            except (requests.ConnectionError, requests.Timeout) as e:
                if intento == 4:
                    raise ErrorGestion(f"{self.nombre}: {metodo} {url} no respondió ({type(e).__name__}). "
                                       "Revisá la conexión o la URL e intentá de nuevo.")
                time.sleep(min(2 ** intento, 30))
                continue
            if r.status_code in (429, 502, 503, 504) and intento < 4:
                time.sleep(min(_espera_reintento(r.headers.get("Retry-After"), intento), 30))
                continue
            break
        if r.status_code not in esperado:
            raise ErrorGestion(f"{self.nombre}: {metodo} {url} respondió {r.status_code}: {r.text[:800]}")
        if not r.content:
            return {}
        try:
            return r.json()
        except ValueError:
            return {"texto": r.text}

    def get(self, ruta, **kw):
        return self.request("GET", ruta, **kw)

    def post(self, ruta, **kw):
        return self.request("POST", ruta, **kw)

    def put(self, ruta, **kw):
        return self.request("PUT", ruta, **kw)


class Trazabilidad:
    """output/gestion/<historia o nombre>-<herramienta>.json

    {
      "herramienta": "xray-cloud", "proyecto": "PROJ", "historia": "PROJ-12",
      "carpeta": {"ruta": "/HU-001 Registro", "id": "..."},
      "casos": {"CP-001": {"key": "PROJ-45", "id": "10045", "titulo": "..."}},
      "ciclos": [{"key": "PROJ-60", "id": "...", "nombre": "...", "fecha": "..."}]
    }
    """

    def __init__(self, nombre, herramienta):
        if not re.match(r"^[\w.-]+$", str(nombre)) or str(nombre).startswith("."):
            raise ErrorGestion(f"Nombre de trazabilidad inválido: {nombre!r} (usá algo como HU-001).")
        DIR_GESTION.mkdir(parents=True, exist_ok=True)
        self.ruta = DIR_GESTION / f"{nombre}-{herramienta}.json"
        if self.ruta.exists():
            self.datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        else:
            self.datos = {"herramienta": herramienta, "casos": {}, "ciclos": []}

    def guardar(self):
        self.ruta.write_text(json.dumps(self.datos, ensure_ascii=False, indent=2), encoding="utf-8")

    def key_de(self, caso_id):
        return (self.datos["casos"].get(caso_id) or {}).get("key")


def salida(datos):
    """Todo comando termina imprimiendo un JSON: lo lee el agente."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows no es UTF-8 por defecto
    print(json.dumps(datos, ensure_ascii=False, indent=2))

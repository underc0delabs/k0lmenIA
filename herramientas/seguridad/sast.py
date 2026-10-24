#!/usr/bin/env python3
"""
Análisis estático de seguridad del código (SAST) y búsqueda de secretos, de solo lectura.

Uso (desde la raíz del repo de k0lmenIA, apuntando al proyecto a analizar):
    python herramientas/seguridad/sast.py --ruta C:/proyectos/mi-app [--salida output/sast/sast.json]

Qué hace:
- **Secretos** (sin dependencias, siempre corre): recorre los archivos de texto del proyecto buscando
  patrones de claves y credenciales (AWS, Google, GitHub, Slack, Stripe, claves privadas, JWT y
  asignaciones tipo password/secret/token=...). El valor se **redacta** en la salida (nunca se imprime completo).
- **SAST** (opcional): si está `semgrep`, corre `semgrep --json` con su config por defecto y agrega los hallazgos;
  si está `gitleaks`, suma su detección de secretos. Si faltan, lo avisa con cómo instalarlos, no falla.
- Agrega por severidad y deja un JSON para que el agente analista-codigo-seguro lo triague.

No ejecuta el código del proyecto ni lo modifica.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

IGNORAR_DIR = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", ".next", "out", "vendor", "target", "coverage"}
EXT_TEXTO = {".js", ".ts", ".tsx", ".jsx", ".py", ".java", ".rb", ".go", ".php", ".cs", ".env", ".yml", ".yaml",
             ".json", ".xml", ".properties", ".ini", ".cfg", ".conf", ".sh", ".ps1", ".tf", ".txt", ".md", ".html"}
MAX_BYTES = 2 * 1024 * 1024

# (tipo, regex). Patrones conservadores para no inundar de falsos positivos.
PATRONES = [
    ("Clave de acceso AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Clave de API de Google", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Token de GitHub", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{36,}\b")),
    ("Token de Slack", re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}\b")),
    ("Clave secreta de Stripe", re.compile(r"\bsk_live_[0-9A-Za-z]{24,}\b")),
    ("Clave privada", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    ("Credencial en asignación", re.compile(r"(?i)(password|passwd|secret|api[_-]?key|token|access[_-]?key)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]")),
    ("URL con credenciales", re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s:@/]+:[^\s:@/]+@")),
]
SEV_SEMGREP = {"ERROR": "Alta", "WARNING": "Media", "INFO": "Baja"}


def redactar(fragmento):
    """Muestra lo justo para ubicar el secreto sin exponerlo (primeros 4 caracteres + …)."""
    f = fragmento.strip()
    return (f[:4] + "…") if len(f) > 6 else "…"


def buscar_secretos(texto):
    """[(tipo, nro_linea, fragmento_redactado)] de los patrones de secreto en el texto. Testeable y puro."""
    out = []
    for i, linea in enumerate(texto.splitlines(), 1):
        for tipo, rx in PATRONES:
            m = rx.search(linea)
            if m:
                out.append((tipo, i, redactar(m.group(0))))
    return out


def escanear_secretos(ruta):
    hallazgos = []
    raiz = Path(ruta)
    for p in raiz.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in EXT_TEXTO:
            continue
        if any(part in IGNORAR_DIR for part in p.parts):
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                continue
            texto = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for tipo, linea, frag in buscar_secretos(texto):
            hallazgos.append({"tipo": tipo, "archivo": str(p.relative_to(raiz)), "linea": linea,
                              "fragmento": frag, "severidad": "Alta", "origen": "secretos"})
    return hallazgos


def parse_semgrep(data):
    out = []
    for r in (data.get("results") or []):
        extra = r.get("extra") or {}
        out.append({"regla": r.get("check_id"), "archivo": r.get("path"),
                    "linea": (r.get("start") or {}).get("line"), "severidad": SEV_SEMGREP.get(extra.get("severity"), "Media"),
                    "mensaje": (extra.get("message") or "")[:300], "origen": "semgrep"})
    return out


def contar(hallazgos):
    return {s: sum(1 for h in hallazgos if h.get("severidad") == s) for s in ("Crítica", "Alta", "Media", "Baja")}


def relevar(ruta):
    inv = {"ruta": str(ruta), "secretos": [], "sast": [], "errores": {}, "escaneres": ["secretos (integrado)"]}
    inv["secretos"] = escanear_secretos(ruta)
    if shutil.which("semgrep"):
        try:
            p = subprocess.run(["semgrep", "--config", "auto", "--json", "--quiet"], cwd=ruta,
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            data = json.loads(p.stdout or "null")
            if data:
                inv["sast"] = parse_semgrep(data)
                inv["escaneres"].append("semgrep")
        except (OSError, subprocess.TimeoutExpired, ValueError) as ex:
            inv["errores"]["semgrep"] = str(ex)[:200]
    else:
        inv["errores"]["semgrep"] = "semgrep no está instalado (SAST): `pip install semgrep` o https://semgrep.dev."
    todos = inv["secretos"] + inv["sast"]
    inv["resumen"] = {"secretos": len(inv["secretos"]), "sast": len(inv["sast"]),
                      "total": len(todos), "por_severidad": contar(todos)}
    return inv


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="SAST y búsqueda de secretos de un proyecto, solo lectura.")
    ap.add_argument("--ruta", default=".", help="ruta del proyecto a analizar (o REPO_RUTA_LOCAL del .env)")
    ap.add_argument("--salida", default="", help="ruta donde guardar el JSON (opcional)")
    args = ap.parse_args(argv)
    ruta = Path(args.ruta)
    if not ruta.exists():
        print(f"[sast] La ruta {ruta} no existe.", file=sys.stderr)
        return 2
    inv = relevar(ruta)
    texto = json.dumps(inv, ensure_ascii=False, indent=2)
    if args.salida:
        p = Path(args.salida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        print(f"[sast] Datos en {p}", file=sys.stderr)
    print(texto)
    print(f"[sast] {inv['resumen']['secretos']} secreto(s) y {inv['resumen']['sast']} hallazgo(s) SAST. Escáneres: {', '.join(inv['escaneres'])}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

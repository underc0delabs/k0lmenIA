#!/usr/bin/env python3
"""
Análisis de composición (SCA) de las dependencias de un proyecto: vulnerabilidades conocidas (CVE) y, cuando
se puede, licencias. Solo lectura — no modifica el proyecto ni instala nada.

Uso (desde la raíz del repo de k0lmenIA, apuntando al proyecto a analizar):
    python herramientas/seguridad/dependencias.py --ruta C:/proyectos/mi-app [--salida output/dependencias/sca.json]

Qué hace:
- Detecta los manifiestos del proyecto (package.json, requirements.txt/pyproject, pom.xml, go.mod, Gemfile,
  composer.json).
- Corre los escáneres disponibles en modo lectura: `npm audit --json` (Node), `pip-audit --format json`
  (Python) y, si está, `osv-scanner --format json` (multi-ecosistema). Si falta uno, lo avisa con cómo
  instalarlo, no falla.
- Agrega las vulnerabilidades por severidad (Crítica/Alta/Media/Baja) y deja un JSON para que el agente
  analista-dependencias lo triague.

No ejecuta código del proyecto ni lo modifica. La explotación y el escaneo dinámico son de analista-seguridad
y pentester-web.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SEV = {"critical": "Crítica", "high": "Alta", "moderate": "Media", "medium": "Media", "moderada": "Media",
       "low": "Baja", "info": "Baja", "negligible": "Baja", "unknown": "Media"}
ORDEN = ("Crítica", "Alta", "Media", "Baja")


def norm_sev(s):
    return SEV.get((s or "").strip().lower(), "Media")


def manifiestos(ruta):
    """Qué ecosistemas hay en el proyecto, por sus manifiestos."""
    r = Path(ruta)
    checks = {"package.json": "Node", "requirements.txt": "Python", "pyproject.toml": "Python",
              "pom.xml": "Java (Maven)", "build.gradle": "Java (Gradle)", "go.mod": "Go",
              "Gemfile": "Ruby", "composer.json": "PHP"}
    return sorted({eco for archivo, eco in checks.items() if (r / archivo).exists()})


def parse_npm_audit(data):
    """(vulnerabilidades, conteo del metadata). Soporta el formato de npm v7+."""
    vulns = []
    for nombre, v in (data.get("vulnerabilities") or {}).items():
        if not isinstance(v, dict):
            continue
        fix = v.get("fixAvailable")
        vulns.append({"paquete": nombre, "severidad": norm_sev(v.get("severity")), "rango": v.get("range"),
                      "fix": bool(fix) if not isinstance(fix, dict) else True, "ecosistema": "Node"})
    meta = ((data.get("metadata") or {}).get("vulnerabilities")) or {}
    return vulns, meta


def parse_pip_audit(data):
    """pip-audit --format json: lista de {name, version, vulns:[{id, fix_versions}]}."""
    vulns = []
    items = data if isinstance(data, list) else (data.get("dependencies") if isinstance(data, dict) else []) or []
    for dep in items:
        for v in dep.get("vulns") or []:
            vulns.append({"paquete": f'{dep.get("name")} {dep.get("version", "")}'.strip(), "id": v.get("id"),
                          "severidad": norm_sev(v.get("severity")), "fix": bool(v.get("fix_versions")), "ecosistema": "Python"})
    return vulns


def contar(vulns):
    return {s: sum(1 for v in vulns if v.get("severidad") == s) for s in ORDEN}


def _correr(cmd, ruta):
    try:
        p = subprocess.run(cmd, cwd=ruta, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    except (OSError, subprocess.TimeoutExpired) as ex:
        return None, str(ex)[:200]
    try:
        return json.loads(p.stdout or "null"), None
    except ValueError:
        return None, (p.stderr or "salida no JSON").strip()[:200]


def relevar(ruta):
    ecos = manifiestos(ruta)
    inv = {"ruta": str(ruta), "ecosistemas": ecos, "vulnerabilidades": [], "errores": {}, "escaneres": []}
    if "Node" in ecos:
        if shutil.which("npm"):
            data, err = _correr(["npm", "audit", "--json"], ruta)
            if data:
                v, _ = parse_npm_audit(data)
                inv["vulnerabilidades"] += v
                inv["escaneres"].append("npm audit")
            elif err:
                inv["errores"]["npm"] = err
        else:
            inv["errores"]["npm"] = "npm no está instalado (necesario para el SCA de Node)."
    if "Python" in ecos:
        if shutil.which("pip-audit"):
            data, err = _correr(["pip-audit", "--format", "json"], ruta)
            if data is not None:
                inv["vulnerabilidades"] += parse_pip_audit(data)
                inv["escaneres"].append("pip-audit")
            elif err:
                inv["errores"]["pip-audit"] = err
        else:
            inv["errores"]["pip-audit"] = "pip-audit no está instalado: `pip install pip-audit` (SCA de Python)."
    # osv-scanner cubre varios ecosistemas de una
    if shutil.which("osv-scanner"):
        data, err = _correr(["osv-scanner", "--format", "json", "-r", "."], ruta)
        if data:
            for res in (data.get("results") or []):
                for pkg in res.get("packages") or []:
                    nombre = (pkg.get("package") or {}).get("name")
                    for v in pkg.get("vulnerabilities") or []:
                        inv["vulnerabilidades"].append({"paquete": nombre, "id": v.get("id"), "severidad": "Media",
                                                        "ecosistema": (pkg.get("package") or {}).get("ecosystem"), "fix": None})
            inv["escaneres"].append("osv-scanner")
        elif err:
            inv["errores"]["osv-scanner"] = err
    elif not inv["escaneres"]:
        inv["errores"]["osv-scanner"] = "osv-scanner no está instalado (opcional, multi-ecosistema): https://google.github.io/osv-scanner/"
    inv["resumen"] = {"ecosistemas": ecos, "total": len(inv["vulnerabilidades"]), "por_severidad": contar(inv["vulnerabilidades"])}
    return inv


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="SCA de dependencias (CVEs) de un proyecto, solo lectura.")
    ap.add_argument("--ruta", default=".", help="ruta del proyecto a analizar (o REPO_RUTA_LOCAL del .env)")
    ap.add_argument("--salida", default="", help="ruta donde guardar el JSON (opcional)")
    args = ap.parse_args(argv)
    ruta = Path(args.ruta)
    if not ruta.exists():
        print(f"[dependencias] La ruta {ruta} no existe.", file=sys.stderr)
        return 2
    if not manifiestos(ruta):
        print(f"[dependencias] No se encontraron manifiestos de dependencias en {ruta}.", file=sys.stderr)
        return 2
    inv = relevar(ruta)
    texto = json.dumps(inv, ensure_ascii=False, indent=2)
    if args.salida:
        p = Path(args.salida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        print(f"[dependencias] Datos en {p}", file=sys.stderr)
    print(texto)
    c = inv["resumen"]["por_severidad"]
    print(f"[dependencias] {inv['resumen']['total']} vulnerabilidad(es): {c['Crítica']} crít., {c['Alta']} alta(s). Escáneres: {', '.join(inv['escaneres']) or 'ninguno'}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

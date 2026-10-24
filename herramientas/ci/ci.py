#!/usr/bin/env python3
"""
Plantillas de CI para correr las suites de k0lmena en el pipeline del equipo (sin agentes ni tokens) y,
si hay ciclo, publicar los resultados en la herramienta de gestión (scripts/gestion/gestion.py).

Uso (desde la raíz del repo de k0lmenIA):
    python herramientas/ci/ci.py listar
    python herramientas/ci/ci.py generar --plataforma github|gitlab|jenkins|azure [--suite web|api|all]
                                         [--destino <raíz del repo donde va el pipeline>] [--forzar]
    python herramientas/ci/ci.py publicar --suites "web api" [--ciclo PROJ-60] [--traza HU-001] [--dry-run]

- `generar` copia la plantilla a su lugar (.github/workflows/k0lmena.yml, .gitlab-ci.yml, Jenkinsfile o
  azure-pipelines.yml) dentro de --destino (por defecto, este repo). No pisa un archivo existente salvo --forzar.
  --suite all corre web y api (mobile necesita un dispositivo o BrowserStack: se suma a mano).
- `publicar` es lo que corre el pipeline después de las suites: por cada suite con reporte
  (herramientas/k0lmena/reports/<suite>/cucumber-report.json) hace `gestion.py extraer-resultados` y
  `publicar-resultados --ciclo`. Sin ciclo (--ciclo o GESTION_CICLO) no publica nada y sale con 0.

Las plantillas no llevan secretos: el .env entero va como secret del pipeline y llega por K0LMENA_ENV_FILE
(lo leen k0lmena y scripts/gestion). Ver herramientas/ci/README.md.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLAS = Path(__file__).resolve().parent / "plantillas"
sys.path.insert(0, str(RAIZ / "scripts"))

from _env import cargar_env  # noqa: E402

# plataforma -> (plantilla, destino dentro del repo, cómo se configura el .env)
PLATAFORMAS = {
    "github": ("github.yml", ".github/workflows/k0lmena.yml", "secret K0LMENIA_ENV"),
    "gitlab": ("gitlab.yml", ".gitlab-ci.yml", "variable K0LMENA_ENV_FILE de tipo File"),
    "jenkins": ("Jenkinsfile", "Jenkinsfile", "credencial Secret file 'k0lmenia-env'"),
    "azure": ("azure.yml", "azure-pipelines.yml", "Secure file 'k0lmenia.env'"),
}
SUITES = {"web": "web", "api": "api", "all": "web api"}
REPORTES = RAIZ / "herramientas" / "k0lmena" / "reports"


def generar(plataforma, suite="web", destino=None, forzar=False):
    """Escribe la plantilla con las suites elegidas. Devuelve la ruta; si ya existe y no hay --forzar,
    lanza FileExistsError."""
    origen, relativo, _ = PLATAFORMAS[plataforma]
    ruta = Path(destino or RAIZ) / relativo
    if ruta.exists() and not forzar:
        raise FileExistsError(f"{ruta} ya existe: revisalo y usá --forzar para reemplazarlo.")
    texto = (PLANTILLAS / origen).read_text(encoding="utf-8").replace("__SUITES__", SUITES[suite])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8", newline="\n")
    return ruta


def publicar(suites, ciclo=None, traza=None, dry_run=False, ejecutar=subprocess.call):
    """Extrae y publica los resultados de cada suite con reporte. Devuelve el código de salida."""
    cargar_env()
    ciclo = (ciclo or os.environ.get("GESTION_CICLO", "")).strip()
    if not ciclo:
        print("[ci] Sin ciclo (GESTION_CICLO): no se publican resultados.")
        return 0
    gestion = [sys.executable, str(RAIZ / "scripts" / "gestion" / "gestion.py")]
    estado = 0
    for suite in suites:
        reporte = REPORTES / suite / "cucumber-report.json"
        if not reporte.exists() or reporte.stat().st_size <= 4:
            print(f"[ci] {suite}: no hay reporte ({reporte}), se saltea.")
            continue
        resultados = RAIZ / "output" / "gestion" / f"resultados-ci-{suite}.json"
        pasos = [
            gestion + ["extraer-resultados", "--reporte", str(reporte), "--salida", str(resultados)],
            gestion + (["--dry-run"] if dry_run else []) + ["publicar-resultados", "--ciclo", ciclo,
                                                             "--resultados", str(resultados)]
            + (["--traza", traza] if traza else []),
        ]
        for cmd in pasos:
            if ejecutar(cmd, cwd=str(RAIZ)) != 0:
                print(f"[ci] {suite}: falló {' '.join(cmd[2:4])}.", file=sys.stderr)
                estado = 1
                break
        else:
            print(f"[ci] {suite}: resultados publicados en {ciclo}.")
    return estado


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="comando", required=True)
    sub.add_parser("listar", help="plataformas disponibles y dónde queda cada pipeline")
    g = sub.add_parser("generar", help="copia la plantilla de una plataforma")
    g.add_argument("--plataforma", required=True, choices=sorted(PLATAFORMAS))
    g.add_argument("--suite", default="web", choices=sorted(SUITES))
    g.add_argument("--destino", default="", help="raíz del repo donde va el pipeline (por defecto, este)")
    g.add_argument("--forzar", action="store_true", help="reemplaza el archivo si ya existe")
    p = sub.add_parser("publicar", help="publica los resultados de las suites en la herramienta de gestión")
    p.add_argument("--suites", default="web", help='suites separadas por espacio (ej. "web api")')
    p.add_argument("--ciclo", default="", help="key del ciclo (por defecto, GESTION_CICLO)")
    p.add_argument("--traza", default="", help="trazabilidad para traducir los @CP-XXX (ver scripts/gestion)")
    p.add_argument("--dry-run", action="store_true", help="muestra los requests sin enviarlos")
    args = ap.parse_args(argv)

    if args.comando == "listar":
        for nombre, (_, relativo, secreto) in sorted(PLATAFORMAS.items()):
            print(f"{nombre:<8} -> {relativo:<32} .env como {secreto}")
        return 0
    if args.comando == "generar":
        try:
            ruta = generar(args.plataforma, args.suite, args.destino or None, args.forzar)
        except FileExistsError as e:
            print(f"[ci] {e}", file=sys.stderr)
            return 1
        print(f"[ci] Pipeline en {ruta}. Configurá el .env como {PLATAFORMAS[args.plataforma][2]} "
              "(ver herramientas/ci/README.md).")
        return 0
    return publicar(args.suites.split(), args.ciclo or None, args.traza or None, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())

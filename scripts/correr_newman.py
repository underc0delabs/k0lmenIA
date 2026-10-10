#!/usr/bin/env python3
"""
Corre una colección de Postman con Newman y deja el reporte HTML de la corrida (agente ejecutor-api).

Uso (desde la raíz del repo; en Mac/Linux, python3):
    python scripts/correr_newman.py <coleccion.json> [--historia HU-001] [--titulo "Auth API"]
                                    [--carpeta "Login"] [--environment env.json] [--base-url URL]

Qué hace:
1. Toma del .env de la raíz API_TOKEN (variable {{token}} de la colección). La URL ({{base_url}})
   sale, en este orden, de --base-url, del environment o de la colección, y si ninguno la define,
   de API_BASEURL del .env. Funciona igual en PowerShell, bash y zsh: no hace falta cargar el .env.
2. Corre Newman (instalado globalmente o con npx) y exporta su JSON.
3. Lo convierte al formato de resultados (scripts/newman_a_resultados.py), con la historia.
4. Genera el reporte HTML (scripts/generar_reporte.py) y borra el JSON crudo de Newman.

Salida en output/ejecuciones/: reporte-<HU o API>-<fecha-hora>.html y _resultados-<HU o API>-<fecha-hora>.json.
El token nunca se escribe en archivos ni en el reporte.
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
from _env import leer_env  # noqa: E402

SALIDA = RAIZ / "output" / "ejecuciones"


def newman():
    if shutil.which("newman"):
        return ["newman"]
    if shutil.which("npx"):
        return ["npx", "-y", "newman@6"]
    sys.exit("No encuentro Newman ni npx. Instalá Node.js y después: npm install -g newman")


def base_url_propia(coleccion, environment):
    """El base_url que ya traen el environment o la colección (si lo traen, no se pisa con el .env)."""
    for archivo, clave in ((environment, "values"), (coleccion, "variable")):
        if not archivo:
            continue
        try:
            datos = json.loads(Path(archivo).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for v in datos.get(clave) or []:
            if v.get("key") == "base_url" and v.get("value") and v.get("enabled", True) is not False:
                return v["value"]
    return None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Corre una colección de Postman y genera el reporte HTML")
    ap.add_argument("coleccion")
    ap.add_argument("--historia", help="HU-XXX: va en el nombre de los archivos y en el reporte")
    ap.add_argument("--titulo", help="título del reporte (por defecto, el nombre de la colección)")
    ap.add_argument("--carpeta", help="solo esta carpeta de la colección (--folder de Newman)")
    ap.add_argument("--environment", help="environment de Postman (.json), si la colección lo usa")
    ap.add_argument("--base-url", help="pisa API_BASEURL del .env")
    a = ap.parse_args()

    coleccion = Path(a.coleccion)
    if not coleccion.exists():
        sys.exit(f"No existe la colección {coleccion}.")
    if a.historia and not re.match(r"^HU-\d+$", a.historia, re.I):
        sys.exit("--historia tiene que ser un ID como HU-001.")
    env = leer_env()
    prefijo = a.historia.upper() if a.historia else "API"
    marca = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    SALIDA.mkdir(parents=True, exist_ok=True)
    crudo = SALIDA / f"_newman-{prefijo}-{marca}.json"
    resultados = SALIDA / f"_resultados-{prefijo}-{marca}.json"
    reporte = SALIDA / f"reporte-{prefijo}-{marca}.html"

    cmd = newman() + ["run", str(coleccion), "-r", "cli,json", "--reporter-json-export", str(crudo)]
    if a.environment:
        cmd += ["-e", a.environment]
    if a.carpeta:
        cmd += ["--folder", a.carpeta]
    propia = base_url_propia(coleccion, a.environment)
    base = a.base_url or (None if propia else env.get("API_BASEURL"))
    if base:
        cmd += ["--env-var", f"base_url={base}"]  # --env-var le gana al environment y a la colección
    base = base or propia
    if env.get("API_TOKEN"):
        cmd += ["--env-var", f"token={env['API_TOKEN']}"]  # solo en la línea del proceso, nunca en archivos

    print(f"Newman · {coleccion.name}" + (f" · carpeta {a.carpeta}" if a.carpeta else "") + (f" · {base}" if base else ""))
    r = subprocess.run(cmd, shell=(sys.platform == "win32"))
    if not crudo.exists():
        sys.exit(f"Newman no generó resultados (código {r.returncode}). Revisá la salida de arriba.")

    titulo = a.titulo or json.loads(coleccion.read_text(encoding="utf-8")).get("info", {}).get("name", coleccion.stem)
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "newman_a_resultados.py"), str(crudo), str(resultados), titulo], check=True)
    datos = json.loads(resultados.read_text(encoding="utf-8"))
    if a.historia:
        datos["historia"] = a.historia.upper()
    if base:
        datos["url"] = base
    resultados.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "generar_reporte.py"), str(resultados), str(reporte)], check=True)
    crudo.unlink(missing_ok=True)

    casos = datos.get("casos", [])
    cuenta = {e: sum(1 for c in casos if c.get("estado") == e) for e in ("Aprobado", "Fallido", "Bloqueado")}
    print(f"\nResultado: {len(casos)} requests · {cuenta['Aprobado']} aprobados · {cuenta['Fallido']} fallidos · {cuenta['Bloqueado']} bloqueados")
    print(f"Reporte:    {reporte.relative_to(RAIZ).as_posix()}")
    print(f"Resultados: {resultados.relative_to(RAIZ).as_posix()}")


if __name__ == "__main__":
    main()

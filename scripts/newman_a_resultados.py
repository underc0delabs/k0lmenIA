#!/usr/bin/env python3
"""
Convierte el JSON que exporta Newman (--reporter-json-export) al formato de
resultados que consume scripts/generar_reporte.py. Así las ejecuciones de API
reusan el mismo reporte HTML (dashboard, modo oscuro) que las E2E.

Uso:
    python scripts/newman_a_resultados.py <newman.json> <salida-resultados.json> [titulo]

Cómo mapea cada request ejecutado a un "caso":
  - Sin asserts fallidos            -> Aprobado.
  - Con al menos un assert fallido  -> Fallido (motivo = primer assert que falló).
  - El request no se pudo hacer      -> Bloqueado (motivo = error de red/conexión).

id y prioridad se pueden codificar (opcional) en el NOMBRE del request en Postman:
    "API-001 — Crear post (Alta)"
  - id: prefijo tipo CODIGO-XXX seguido de — · - o :
  - prioridad: Crítica | Alta | Media | Baja, entre paréntesis al final
Si el nombre no los trae, el id se autonumera (API-001, API-002, …) y la
prioridad queda vacía.
"""
import sys
import json
import re
from datetime import datetime

PRIO_CANON = {"critica": "Crítica", "crítica": "Crítica",
              "alta": "Alta", "media": "Media", "baja": "Baja"}


def parse_nombre(nombre):
    """Devuelve (id, titulo, prioridad) a partir del nombre del request."""
    titulo = (nombre or "").strip()
    prioridad = ""
    m = re.search(r"\(([^)]+)\)\s*$", titulo)
    if m and m.group(1).strip().lower() in PRIO_CANON:
        prioridad = PRIO_CANON[m.group(1).strip().lower()]
        titulo = titulo[:m.start()].strip()
    idv = ""
    m = re.match(r"^([A-Za-z]+-[A-Za-z0-9-]+)\s*[—\-:·]\s*(.+)$", titulo)
    if m:
        idv, titulo = m.group(1).strip(), m.group(2).strip()
    return idv, titulo, prioridad


def buscar_base_url(nm):
    """Busca una variable base_url en el environment o en la colección."""
    for cont in (nm.get("environment") or {}, nm.get("collection") or {}):
        for v in (cont.get("values") or cont.get("variable") or []):
            if (v.get("key") or "").lower() in ("base_url", "baseurl", "url"):
                return v.get("value") or ""
    return ""


def fmt_request_error(err):
    """Convierte el error de request de Newman en un texto legible."""
    if isinstance(err, dict):
        if err.get("message"):
            return err["message"]
        code = err.get("code") or err.get("name") or "Error de conexión"
        addr, port = err.get("address") or "", err.get("port")
        loc = f"{addr}:{port}" if addr and port else (addr or "")
        return " ".join(p for p in [code, err.get("syscall") or "", loc] if p).strip()
    return str(err)


def convertir(nm, titulo_arg=""):
    run = nm.get("run") or {}
    casos = []
    for i, ex in enumerate(run.get("executions", []), start=1):
        nombre = (ex.get("item") or {}).get("name") or f"Request {i}"
        idv, titulo, prioridad = parse_nombre(nombre)
        if not idv:
            idv = f"API-{i:03d}"

        if ex.get("requestError"):
            estado, motivo = "Bloqueado", fmt_request_error(ex.get("requestError"))
        else:
            fallidas = [a for a in (ex.get("assertions") or []) if a.get("error")]
            if fallidas:
                err = fallidas[0].get("error") or {}
                detalle = err.get("message") or err.get("name") or ""
                motivo = f'{fallidas[0].get("assertion", "")}: {detalle}'.strip(": ").strip()
                estado = "Fallido"
            else:
                estado, motivo = "Aprobado", ""

        casos.append({"id": idv, "titulo": titulo, "prioridad": prioridad,
                      "estado": estado, "motivo": motivo})

    info = (nm.get("collection") or {}).get("info") or {}
    started = (run.get("timings") or {}).get("started")
    fecha = (datetime.fromtimestamp(started / 1000) if started else datetime.now()
             ).strftime("%Y-%m-%d %H:%M")

    return {
        "titulo": titulo_arg or info.get("name") or "Ejecución de API",
        "fecha": fecha,
        "modo": "API (Newman)",
        "url": buscar_base_url(nm),
        "casos": casos,
    }


def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/newman_a_resultados.py <newman.json> <salida.json> [titulo]")
        sys.exit(1)
    entrada, salida = sys.argv[1], sys.argv[2]
    titulo_arg = sys.argv[3] if len(sys.argv) > 3 else ""

    with open(entrada, encoding="utf-8") as f:
        nm = json.load(f)
    out = convertir(nm, titulo_arg)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"OK: {salida} ({len(out['casos'])} casos)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Lectura de un reporte de mutation testing (formato estándar de Stryker / mutation-testing-report-schema),
de solo lectura: calcula el mutation score, los mutantes sobrevivientes y el score por archivo.

Uso (desde la raíz del repo, tras correr la herramienta de mutación del proyecto):
    python herramientas/mutacion/mutacion.py --reporte reports/mutation/mutation.json [--umbral 70] [--salida ...]

Qué hace:
- Parsea el JSON de Stryker (StrykerJS, Stryker.NET y los que exportan a ese esquema) y agrega por estado
  (Killed, Survived, Timeout, NoCoverage…), calcula el **mutation score** global y por archivo, y lista los
  **mutantes que sobrevivieron** (los que tus tests no detectaron) y el código **sin cobertura**.
- Con --umbral marca los archivos por debajo del score mínimo.

No corre la mutación (eso lo hace el agente analista-mutacion con la herramienta del proyecto: Stryker para
JS/TS/C#, mutmut/cosmic-ray para Python, PITest para JVM, Infection para PHP). Solo lee el reporte.
"""
import argparse
import json
import sys
from pathlib import Path

DETECTADOS = ("Killed", "Timeout")
VALIDOS = ("Killed", "Timeout", "Survived", "NoCoverage")


def _score(det, val):
    return round(det / val * 100, 1) if val else None


def parse_stryker(data):
    """Resumen del reporte de Stryker. Puro y testeable."""
    files = (data or {}).get("files") or {}
    por_estado, survived, por_archivo = {}, [], {}
    for archivo, info in files.items():
        mutantes = info.get("mutants") or []
        for m in mutantes:
            st = m.get("status")
            por_estado[st] = por_estado.get(st, 0) + 1
            if st in ("Survived", "NoCoverage"):
                survived.append({"archivo": archivo, "mutator": m.get("mutatorName"),
                                 "linea": ((m.get("location") or {}).get("start") or {}).get("line"), "status": st})
        det = sum(1 for m in mutantes if m.get("status") in DETECTADOS)
        val = sum(1 for m in mutantes if m.get("status") in VALIDOS)
        por_archivo[archivo] = {"score": _score(det, val),
                                "survived": sum(1 for m in mutantes if m.get("status") in ("Survived", "NoCoverage")),
                                "total": len(mutantes)}
    det = sum(v for k, v in por_estado.items() if k in DETECTADOS)
    val = sum(v for k, v in por_estado.items() if k in VALIDOS)
    return {"score": _score(det, val), "por_estado": por_estado, "survived": survived,
            "por_archivo": por_archivo, "total": sum(por_estado.values())}


def bajo_umbral(por_archivo, umbral):
    """Archivos con score por debajo del umbral. Puro y testeable."""
    return sorted([a for a, v in (por_archivo or {}).items() if v.get("score") is not None and v["score"] < umbral],
                  key=lambda a: por_archivo[a]["score"])


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Lee un reporte de mutation testing (Stryker JSON), solo lectura.")
    ap.add_argument("--reporte", default="reports/mutation/mutation.json", help="ruta del JSON de Stryker")
    ap.add_argument("--umbral", type=float, default=70.0, help="score mínimo por archivo")
    ap.add_argument("--salida", default="")
    args = ap.parse_args(argv)
    rep = Path(args.reporte)
    if not rep.exists():
        print(f"[mutacion] No existe el reporte: {rep}. Corré primero la herramienta de mutación del proyecto "
              f"(Stryker/mutmut/PITest) y apuntá --reporte a su JSON.", file=sys.stderr)
        return 2
    try:
        data = json.loads(rep.read_text(encoding="utf-8"))
    except ValueError as ex:
        print(f"[mutacion] El reporte no es JSON válido: {ex}", file=sys.stderr)
        return 2
    inv = parse_stryker(data)
    inv["bajo_umbral"] = bajo_umbral(inv["por_archivo"], args.umbral)
    inv["umbral"] = args.umbral
    texto = json.dumps(inv, ensure_ascii=False, indent=2)
    if args.salida:
        p = Path(args.salida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        print(f"[mutacion] Datos en {p}", file=sys.stderr)
    print(texto)
    print(f"[mutacion] score={inv['score']}% · {len(inv['survived'])} mutante(s) sobreviviente(s) · "
          f"{len(inv['bajo_umbral'])} archivo(s) bajo {args.umbral}%.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

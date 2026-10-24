#!/usr/bin/env python3
"""
Relevamiento de observabilidad de un servicio, de solo lectura y sin dependencias (urllib + regex stdlib):
healthchecks y el endpoint de métricas estilo Prometheus.

Uso (desde la raíz del repo):
    python herramientas/observabilidad/observabilidad.py --url https://mi-servicio
        [--health /health] [--metrics /metrics] [--esperadas http_requests_total,http_request_duration_seconds]
        [--salida output/observabilidad/svc.json]

Qué hace (solo GET):
- Consulta el/los healthcheck(s) (liveness/readiness) y reporta su estado y tiempo de respuesta.
- Trae el endpoint de métricas (formato texto de Prometheus/OpenMetrics), lista las métricas con su TYPE y
  HELP, y chequea cuáles de las esperadas faltan.

No genera carga (para eso, performance-mapper). La validación de logs/traces y de que las alertas disparen
la hace el agente analista-observabilidad con este insumo, los logs (analista-logs) y la base/APM.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = "k0lmenIA-QA/1.0 (observabilidad de solo lectura)"


def parse_prometheus(texto):
    """Métricas de un endpoint estilo Prometheus. Devuelve {nombre: {type, help}}. Puro y testeable."""
    metricas = {}
    tipo, ayuda = {}, {}
    for linea in (texto or "").splitlines():
        linea = linea.strip()
        if linea.startswith("# TYPE "):
            partes = linea[len("# TYPE "):].split()
            if len(partes) >= 2:
                tipo[partes[0]] = partes[1]
        elif linea.startswith("# HELP "):
            partes = linea[len("# HELP "):].split(maxsplit=1)
            if partes:
                ayuda[partes[0]] = partes[1] if len(partes) > 1 else ""
        elif linea and not linea.startswith("#"):
            m = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)", linea)
            if m:
                nombre = m.group(1)
                base = re.sub(r"_(bucket|sum|count)$", "", nombre)
                for n in {nombre, base}:
                    metricas.setdefault(n, {"type": tipo.get(n), "help": ayuda.get(n)})
    # completar type/help conocidos
    for n, v in metricas.items():
        v["type"] = v["type"] or tipo.get(n)
        v["help"] = v["help"] or ayuda.get(n)
    return metricas


def faltantes(metricas, esperadas):
    """Métricas esperadas que no están. Puro y testeable."""
    presentes = set(metricas or {})
    return [e for e in esperadas or [] if e and e not in presentes]


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read(3 * 1024 * 1024).decode(r.headers.get_content_charset() or "utf-8", "replace")
            return r.status, txt, int((time.monotonic() - t0) * 1000), None
    except urllib.error.HTTPError as ex:
        return ex.code, "", int((time.monotonic() - t0) * 1000), None
    except Exception as ex:
        return 0, "", int((time.monotonic() - t0) * 1000), f"{type(ex).__name__}: {ex}"


def relevar(base, health, metrics, esperadas):
    base = base.rstrip("/")
    inv = {"url": base, "health": [], "metricas": {}, "errores": {}}
    for ruta in [p for p in (health or "").split(",") if p.strip()]:
        st, _, ms, err = _get(base + ruta)
        inv["health"].append({"ruta": ruta, "status": st, "ok": bool(st and 200 <= st < 300), "ms": ms, "error": err})
    st, txt, ms, err = _get(base + metrics)
    if err or not (st and 200 <= st < 300):
        inv["errores"]["metrics"] = err or f"HTTP {st} en {metrics}"
    else:
        inv["metricas"] = parse_prometheus(txt)
    inv["faltantes"] = faltantes(inv["metricas"], esperadas)
    inv["resumen"] = {"health_ok": all(h["ok"] for h in inv["health"]) if inv["health"] else None,
                      "metricas": len(inv["metricas"]), "faltantes": len(inv["faltantes"])}
    return inv


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Relevamiento de observabilidad (healthchecks y métricas), solo lectura.")
    ap.add_argument("--url", required=True, help="base del servicio")
    ap.add_argument("--health", default="/health,/healthz,/readyz", help="rutas de healthcheck separadas por coma")
    ap.add_argument("--metrics", default="/metrics", help="ruta del endpoint de métricas (Prometheus)")
    ap.add_argument("--esperadas", default="", help="métricas que deben existir, separadas por coma")
    ap.add_argument("--salida", default="")
    args = ap.parse_args(argv)
    inv = relevar(args.url, args.health, args.metrics, [m.strip() for m in args.esperadas.split(",") if m.strip()])
    texto = json.dumps(inv, ensure_ascii=False, indent=2)
    if args.salida:
        p = Path(args.salida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        print(f"[observabilidad] Datos en {p}", file=sys.stderr)
    print(texto)
    r = inv["resumen"]
    print(f"[observabilidad] health_ok={r['health_ok']} métricas={r['metricas']} faltantes={r['faltantes']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

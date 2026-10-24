#!/usr/bin/env python3
"""
Caos server-side con Toxiproxy: inyecta fallas reales en las dependencias de un servicio (latencia, caída,
ancho de banda, timeout) poniendo a Toxiproxy como proxy entre el servicio y su dependencia (base, API, cache).
Sin dependencias: habla con la API REST de Toxiproxy (por defecto http://localhost:8474) con urllib.

Uso (desde la raíz del repo, con Toxiproxy corriendo y los proxies configurados):
    python herramientas/resiliencia/toxiproxy.py --accion listar
    python herramientas/resiliencia/toxiproxy.py --accion latencia --proxy db --ms 2000 --jitter 500
    python herramientas/resiliencia/toxiproxy.py --accion caida --proxy db        # corta la dependencia
    python herramientas/resiliencia/toxiproxy.py --accion recuperar --proxy db     # la restablece
    python herramientas/resiliencia/toxiproxy.py --accion reset                     # saca todas las toxics

Las acciones que inyectan o quitan fallas (latencia/caida/lento/toxic/recuperar/reset) **tienen efecto** sobre
el ambiente: el agente probador-resiliencia las confirma y las corre solo en QA. `listar` es de lectura.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


def toxic_payload(tipo, stream="downstream", attributes=None, toxicity=1.0, nombre=None):
    """Arma el cuerpo de una toxic de Toxiproxy. Puro y testeable."""
    return {"name": nombre or f"{tipo}_{stream}", "type": tipo, "stream": stream,
            "toxicity": toxicity, "attributes": attributes or {}}


def resumen_proxies(proxies):
    """Resumen testeable: nombre, si está habilitado y cuántas toxics tiene cada proxy."""
    out = []
    for p in proxies or []:
        out.append({"nombre": p.get("name"), "habilitado": p.get("enabled"),
                    "listen": p.get("listen"), "upstream": p.get("upstream"),
                    "toxics": len(p.get("toxics") or [])})
    return out


def _api(host, metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    req = urllib.request.Request(host.rstrip("/") + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            txt = r.read().decode("utf-8", "replace")
            return json.loads(txt) if txt.strip() else {}, None
    except urllib.error.HTTPError as ex:
        return None, f"HTTP {ex.code}: {ex.read().decode('utf-8', 'replace')[:160]}"
    except Exception as ex:
        return None, f"{type(ex).__name__}: {ex} (¿Toxiproxy está corriendo en {host}?)"


def listar(host):
    d, err = _api(host, "GET", "/proxies")
    if err:
        return None, err
    return resumen_proxies(list(d.values()) if isinstance(d, dict) else d), None


def agregar_toxic(host, proxy, tipo, stream, attributes, toxicity=1.0):
    return _api(host, "POST", f"/proxies/{proxy}/toxics", toxic_payload(tipo, stream, attributes, toxicity))


def habilitar(host, proxy, enabled):
    return _api(host, "POST", f"/proxies/{proxy}", {"enabled": enabled})


def reset(host):
    return _api(host, "POST", "/reset")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Caos server-side con Toxiproxy (latencia, caída, lentitud).")
    ap.add_argument("--host", default="http://localhost:8474", help="API de Toxiproxy (o TOXIPROXY_URL)")
    ap.add_argument("--accion", required=True, choices=["listar", "latencia", "caida", "recuperar", "lento", "toxic", "reset"])
    ap.add_argument("--proxy", default="", help="nombre del proxy (la dependencia)")
    ap.add_argument("--ms", type=int, default=1000, help="latencia en ms (acción latencia)")
    ap.add_argument("--jitter", type=int, default=0)
    ap.add_argument("--rate", type=int, default=100, help="ancho de banda en KB/s (acción lento)")
    ap.add_argument("--stream", default="downstream", choices=["downstream", "upstream"])
    ap.add_argument("--tipo", default="", help="tipo de toxic (acción toxic)")
    args = ap.parse_args(argv)

    import os
    host = os.environ.get("TOXIPROXY_URL") or args.host

    if args.accion == "listar":
        res, err = listar(host)
    elif args.accion == "latencia":
        res, err = agregar_toxic(host, args.proxy, "latency", args.stream, {"latency": args.ms, "jitter": args.jitter})
    elif args.accion == "caida":
        res, err = habilitar(host, args.proxy, False)
    elif args.accion == "recuperar":
        res, err = habilitar(host, args.proxy, True)
    elif args.accion == "lento":
        res, err = agregar_toxic(host, args.proxy, "bandwidth", args.stream, {"rate": args.rate})
    elif args.accion == "toxic":
        res, err = agregar_toxic(host, args.proxy, args.tipo, args.stream, {})
    elif args.accion == "reset":
        res, err = reset(host)
    else:
        res, err = None, "acción no soportada"

    if err:
        print(f"[toxiproxy] {err}", file=sys.stderr)
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"[toxiproxy] {args.accion} ok" + (f" (proxy {args.proxy})" if args.proxy else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

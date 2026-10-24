#!/usr/bin/env python3
"""
Herramienta de pruebas de mensajería / eventos (async): publica, consume e inspecciona mensajes en los
brokers más comunes, y trae las verificaciones de QA que no dependen del broker (orden, duplicados, esquema).

Uso (desde la raíz del repo de k0lmenIA, contra un broker de QA):
    # Consumir N mensajes de un topic de Kafka durante 10 s
    python herramientas/mensajeria/mensajeria.py --broker kafka --accion consumir --servidor localhost:9092 --destino pedidos --timeout 10
    # Publicar un mensaje de prueba en una cola de RabbitMQ (acción con efecto: el agente la confirma)
    python herramientas/mensajeria/mensajeria.py --broker rabbitmq --accion publicar --servidor amqp://localhost --destino cola.pedidos --mensaje '{"id":1}'
    # Escuchar un WebSocket o un SSE
    python herramientas/mensajeria/mensajeria.py --broker websocket --accion consumir --destino wss://host/ws --timeout 15

Brokers: kafka (kafka-python), rabbitmq (pika), mqtt (paho-mqtt), websocket (websocket-client) y sse (stdlib).
Las librerías se importan de forma perezosa: si falta una, se avisa cómo instalarla y no falla el import.

`consumir`/`inspeccionar` son de lectura; `publicar` tiene efecto (se confirma). Las verificaciones de orden,
duplicados y esquema (abajo) son puras y testeables.
"""
import argparse
import json
import sys
import time
from pathlib import Path


# ------------------------------------------------------------------ verificaciones puras (sin broker)
def verificar_orden(esperados, recibidos):
    """¿La subsecuencia `esperados` aparece en `recibidos` en ese orden? Devuelve (ok, detalle)."""
    i = 0
    for m in recibidos:
        if i < len(esperados) and m == esperados[i]:
            i += 1
    ok = i == len(esperados)
    return ok, (f"{i}/{len(esperados)} en orden" if esperados else "sin esperados")


def detectar_duplicados(mensajes, clave=None):
    """IDs que aparecen más de una vez (idempotencia / at-least-once). `clave`: función o nombre de campo."""
    def k(m):
        if clave is None:
            return json.dumps(m, sort_keys=True) if isinstance(m, (dict, list)) else m
        if callable(clave):
            return clave(m)
        return m.get(clave) if isinstance(m, dict) else None
    vistos, dups = {}, []
    for m in mensajes:
        kk = k(m)
        vistos[kk] = vistos.get(kk, 0) + 1
    return [kk for kk, n in vistos.items() if n > 1]


def validar_esquema(mensaje, requeridos):
    """Campos obligatorios que faltan en el mensaje (chequeo liviano, sin dependencias)."""
    if not isinstance(mensaje, dict):
        return list(requeridos)
    return [c for c in requeridos if c not in mensaje or mensaje.get(c) in (None, "")]


def _falta(lib, pip):
    return RuntimeError(f"Falta la librería '{lib}': instalala con `pip install {pip}` (solo para el broker correspondiente).")


# ------------------------------------------------------------------ operaciones por broker (import perezoso)
def _kafka(accion, servidor, destino, mensaje, n, timeout):
    try:
        from kafka import KafkaConsumer, KafkaProducer
    except ImportError:
        raise _falta("kafka", "kafka-python")
    if accion == "publicar":
        p = KafkaProducer(bootstrap_servers=servidor)
        p.send(destino, (mensaje or "").encode("utf-8")).get(timeout=timeout)
        p.flush()
        return {"publicados": 1}
    c = KafkaConsumer(destino, bootstrap_servers=servidor, auto_offset_reset="earliest",
                      consumer_timeout_ms=int(timeout * 1000), enable_auto_commit=False)
    msgs = []
    for m in c:
        msgs.append(m.value.decode("utf-8", "replace"))
        if len(msgs) >= n:
            break
    c.close()
    return {"mensajes": msgs}


def _rabbitmq(accion, servidor, destino, mensaje, n, timeout):
    try:
        import pika
    except ImportError:
        raise _falta("pika", "pika")
    conn = pika.BlockingConnection(pika.URLParameters(servidor))
    ch = conn.channel()
    if accion == "publicar":
        ch.basic_publish(exchange="", routing_key=destino, body=(mensaje or "").encode("utf-8"))
        conn.close()
        return {"publicados": 1}
    msgs, fin = [], time.monotonic() + timeout
    while len(msgs) < n and time.monotonic() < fin:
        method, _, body = ch.basic_get(queue=destino, auto_ack=False)
        if body is None:
            time.sleep(0.2)
            continue
        msgs.append(body.decode("utf-8", "replace"))
    conn.close()
    return {"mensajes": msgs}


def _mqtt(accion, servidor, destino, mensaje, n, timeout):
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        raise _falta("paho-mqtt", "paho-mqtt")
    host, _, puerto = servidor.partition(":")
    cli = mqtt.Client()
    cli.connect(host, int(puerto or 1883), keepalive=max(10, int(timeout) + 5))
    if accion == "publicar":
        cli.publish(destino, mensaje or "")
        cli.disconnect()
        return {"publicados": 1}
    msgs = []
    cli.on_message = lambda c, u, m: msgs.append(m.payload.decode("utf-8", "replace"))
    cli.subscribe(destino)
    cli.loop_start()
    fin = time.monotonic() + timeout
    while len(msgs) < n and time.monotonic() < fin:
        time.sleep(0.2)
    cli.loop_stop()
    cli.disconnect()
    return {"mensajes": msgs}


def _websocket(accion, destino, mensaje, n, timeout):
    try:
        import websocket
    except ImportError:
        raise _falta("websocket", "websocket-client")
    ws = websocket.create_connection(destino, timeout=timeout)
    if mensaje:
        ws.send(mensaje)
    msgs = []
    fin = time.monotonic() + timeout
    while len(msgs) < n and time.monotonic() < fin:
        try:
            msgs.append(ws.recv())
        except Exception:
            break
    ws.close()
    return {"mensajes": msgs}


def _sse(destino, n, timeout):
    import urllib.request
    msgs = []
    with urllib.request.urlopen(destino, timeout=timeout) as r:
        fin = time.monotonic() + timeout
        for raw in r:
            linea = raw.decode("utf-8", "replace").strip()
            if linea.startswith("data:"):
                msgs.append(linea[5:].strip())
            if len(msgs) >= n or time.monotonic() > fin:
                break
    return {"mensajes": msgs}


def correr(broker, accion, servidor, destino, mensaje, n, timeout):
    if broker == "kafka":
        return _kafka(accion, servidor, destino, mensaje, n, timeout)
    if broker == "rabbitmq":
        return _rabbitmq(accion, servidor, destino, mensaje, n, timeout)
    if broker == "mqtt":
        return _mqtt(accion, servidor, destino, mensaje, n, timeout)
    if broker == "websocket":
        return _websocket(accion, destino, mensaje, n, timeout)
    if broker == "sse":
        return _sse(destino, n, timeout)
    raise RuntimeError(f"Broker no soportado: {broker}")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Pruebas de mensajería / eventos (publicar, consumir, inspeccionar).")
    ap.add_argument("--broker", required=True, choices=["kafka", "rabbitmq", "mqtt", "websocket", "sse"])
    ap.add_argument("--accion", default="consumir", choices=["publicar", "consumir", "inspeccionar"])
    ap.add_argument("--servidor", default="", help="bootstrap/URL/host del broker (o la variable de entorno correspondiente)")
    ap.add_argument("--destino", default="", help="topic / cola / URL (ws/sse)")
    ap.add_argument("--mensaje", default="", help="payload a publicar")
    ap.add_argument("--n", type=int, default=10, help="cantidad máxima de mensajes a consumir")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--salida", default="")
    args = ap.parse_args(argv)
    try:
        res = correr(args.broker, args.accion, args.servidor, args.destino, args.mensaje, args.n, args.timeout)
    except RuntimeError as ex:
        print(f"[mensajeria] {ex}", file=sys.stderr)
        return 2
    except Exception as ex:
        print(f"[mensajeria] Error con {args.broker}: {ex}", file=sys.stderr)
        return 2
    datos = {"broker": args.broker, "accion": args.accion, "destino": args.destino, **res}
    texto = json.dumps(datos, ensure_ascii=False, indent=2)
    if args.salida:
        p = Path(args.salida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        print(f"[mensajeria] Datos en {p}", file=sys.stderr)
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())

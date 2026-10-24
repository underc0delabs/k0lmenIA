---
name: pruebas-async
description: El cómo de probar mensajería y eventos async — brokers (Kafka, RabbitMQ, SQS/SNS, Pub/Sub, MQTT, WebSocket, SSE), entrega, orden, idempotencia, reintentos, DLQ, esquemas, consumer lag, outbox y seguridad. Lo usa el probador-mensajeria.
---

# Pruebas de mensajería y eventos (async)

Lo asíncrono no se prueba como una API request/response: un productor **publica** y un consumidor **procesa después**, quizás varias veces, fuera de orden o nunca. Lo que importa es **la entrega, el orden, la idempotencia y qué pasa cuando algo falla**. Se complementa con `tecnicas-de-diseno` y, para lo que termina en una base, con `verificador-datos`.

## 1. Brokers y protocolos

- **Kafka**: log particionado; orden **por partición**, consumer groups, offsets, consumer lag, retención.
- **RabbitMQ / AMQP**: colas y exchanges (direct, topic, fanout), ack/nack, DLX (dead-letter exchange), TTL, prefetch.
- **AWS SQS/SNS, Google Pub/Sub**: colas/temas gestionados, visibility timeout, DLQ, fan-out.
- **MQTT** (IoT): QoS 0/1/2, retained messages, last will, topics jerárquicos.
- **WebSocket / SSE**: tiempo real sobre HTTP; reconexión, heartbeat, backpressure, autorización por conexión.

Confirmá cuál es: cambia qué garantías existen (p. ej. Kafka ordena por partición, no global).

## 2. Entrega y garantías

- **At-least-once** es lo normal: un mensaje se puede entregar **más de una vez** → el consumidor **tiene que ser idempotente**. Probalo reenviando el mismo evento.
- **Exactly-once** rara vez es real de punta a punta: confirmá qué garantiza de verdad el sistema y probá el caso de doble entrega.
- **Mensaje perdido**: un consumidor que falla **después** de procesar pero **antes** del ack, ¿reprocesa o pierde? Un ack antes de procesar pierde mensajes ante un crash.

## 3. Orden

- El orden suele garantizarse **por clave/partición**, no global. Eventos de la **misma entidad** (p. ej. un pedido) deben procesarse en orden; de entidades distintas, no importa.
- Probá eventos fuera de orden (un "cancelado" que llega antes del "creado"): el consumidor no debe dejar un estado inconsistente.

## 4. Idempotencia y deduplicación

- Reenviá el mismo evento (misma clave de idempotencia / id): **un solo efecto** (un pago, un registro), no dos.
- Dedup por ventana de tiempo, por id persistido, o por la clave del broker; probá los bordes de esa ventana.

## 5. Reintentos, backoff y DLQ

- Un consumidor que falla debe **reintentar con backoff**, no en bucle cerrado (tormenta de reintentos).
- Después de N fallos, el mensaje va a la **DLQ** (dead-letter), no se pierde ni bloquea la cola. Probá un **mensaje envenenado** (que siempre falla): no debe frenar el resto.
- Revisá la DLQ: mensajes ahí = algo no se procesó; que haya forma de reprocesarlos.

## 6. Esquemas y compatibilidad

- Con **Schema Registry** (Avro/Protobuf) o **JSON Schema**: un mensaje que no cumple el esquema se rechaza, no rompe al consumidor.
- **Compatibilidad**: agregar un campo (backward), sacar uno, cambiar un tipo. Un productor nuevo no debe romper a un consumidor viejo (ni al revés), según la política de compatibilidad.

## 7. Particiones, consumer lag y contrapresión

- **Consumer lag**: si el consumidor no da abasto, el lag crece; medilo bajo carga (con `performance-mapper`).
- **Rebalanceo** al sumar/quitar consumidores: no se duplican ni se pierden mensajes durante el reajuste.
- **Consumidor lento / contrapresión**: el sistema no se cae ni acumula sin límite.

## 8. Transacciones y outbox

- Si un servicio escribe en su base **y** publica un evento, deben ser atómicos (o se publica sin guardar, o al revés). El **patrón outbox** resuelve esto: verificá que no haya eventos publicados sin su cambio en la base (o al revés), cruzando con `verificador-datos`.

## 9. Correlación y trazas

- Cada evento lleva un **correlation id** que viaja por toda la cadena; sirve para seguir un flujo que pasa por varios servicios/colas. Verificá que se propague.

## 10. Seguridad

- **TLS** en tránsito, autenticación (SASL/mTLS) y **ACLs** por topic/cola (un servicio solo publica/consume lo suyo). En WebSocket/SSE, autorización por conexión y que no se filtren mensajes de otro usuario/sala.

## 11. WebSocket / SSE

- **Reconexión** automática tras caída de red, sin perder ni duplicar; **heartbeat**/ping-pong; **backpressure** si el cliente es lento; cierre limpio.
- Autorización: un cliente solo recibe los mensajes de su canal; probá suscribirse a uno ajeno.

## 12. Automatizar (herramienta de mensajería)

- `k0lmenia mensajeria` (`${CLAUDE_PLUGIN_ROOT}/herramientas/mensajeria/mensajeria.py`) publica, consume e inspecciona en Kafka, RabbitMQ, MQTT, WebSocket y SSE; las verificaciones **puras** (orden, duplicados, esquema) no dependen del broker y se usan sobre lo consumido.
- Patrón: **publicar** un evento de prueba → **consumir** en el otro extremo → verificar efecto (estado, base con `verificador-datos`), orden y que no se duplicó.
- Para carga y consumer lag, `guia-performance` + `performance-mapper`.

## 13. Bugs típicos de mensajería

- Consumidor **no idempotente**: el mismo evento procesado dos veces cobra/registra dos veces.
- Ack antes de procesar → mensajes perdidos ante un crash.
- Eventos de la misma entidad procesados **fuera de orden** dejan estado inconsistente.
- Mensaje envenenado que **bloquea la cola** (sin DLQ) o bucle de reintentos sin backoff.
- Cambio de esquema que **rompe** a los consumidores viejos.
- Evento publicado **sin** su cambio en la base (o al revés): falta outbox/atomicidad.
- WebSocket que no reconecta o que entrega mensajes de otra sala.
- Consumer lag que crece sin alarma bajo carga.

## 14. Preguntas típicas para el PO (async)

Cuando no está escrito, son `FI-XX`:

- ¿Qué broker/protocolo y qué garantía de entrega se espera (at-least-once, exactly-once)?
- ¿El orden importa y por qué clave? ¿Qué eventos de una misma entidad hay?
- ¿El consumidor es idempotente? ¿Con qué clave deduplica?
- ¿Qué pasa con un mensaje que falla siempre? ¿Hay DLQ y reproceso?
- ¿Hay Schema Registry y qué política de compatibilidad?
- ¿Se usa el patrón outbox para publicar + persistir?

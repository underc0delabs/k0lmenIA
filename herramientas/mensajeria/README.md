# Mensajería y eventos (async)

Herramienta de pruebas de sistemas **asíncronos / event-driven**: publica, consume e inspecciona mensajes en los brokers más comunes, y trae las verificaciones de QA que no dependen del broker. La usa el agente `probador-mensajeria`.

- **`mensajeria.py`** (`npm run mensajeria`) — publica/consume/inspecciona en **Kafka** (kafka-python), **RabbitMQ/AMQP** (pika), **MQTT** (paho-mqtt), **WebSocket** (websocket-client) y **SSE** (stdlib). Incluye verificaciones **puras** (sin broker): `verificar_orden`, `detectar_duplicados` y `validar_esquema`.

```bash
# Consumir de un topic de Kafka
npm run mensajeria -- --broker kafka --accion consumir --servidor localhost:9092 --destino pedidos --timeout 10
# Publicar un mensaje de prueba en RabbitMQ (acción con efecto: el agente la confirma)
npm run mensajeria -- --broker rabbitmq --accion publicar --servidor amqp://localhost --destino cola.pedidos --mensaje '{"id":1}'
# Escuchar un WebSocket
npm run mensajeria -- --broker websocket --accion consumir --destino wss://host/ws --timeout 15
```

`consumir`/`inspeccionar` son de **lectura**; `publicar` tiene efecto (dispara consumidores), así que el agente lo confirma y se hace contra un **broker de QA**, nunca producción.

**Requisitos (opcionales, por broker)**: `pip install kafka-python` (Kafka), `pip install pika` (RabbitMQ), `pip install paho-mqtt` (MQTT), `pip install websocket-client` (WebSocket). SSE no necesita nada. Las librerías se importan de forma perezosa: si falta una, la herramienta avisa cómo instalarla y no rompe.

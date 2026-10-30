---
name: pruebas-grpc
description: El cómo de probar APIs gRPC — Protobuf, los cuatro modos de RPC, status codes, deadlines, TLS/mTLS, gRPC-Web y grpcurl; más WebSocket. La usan ejecutor-api y api-mapper.
---

# Pruebas de gRPC (y APIs de tiempo real)

gRPC no es REST: usa **HTTP/2 + Protocol Buffers** (binario), con un **contrato fuerte en el `.proto`**, **cuatro modos de RPC** y **status codes propios** (no HTTP). Se suma a la familia de API (`ejecucion-api`); el detalle de WebSocket está disponible en K0lmenIA Pro.

## 1. El contrato: Protocol Buffers (.proto)

- El `.proto` define servicios, métodos (RPCs), mensajes, **campos con su número** (el número es el contrato binario, no el nombre), tipos escalares, `enum`, `oneof`, `repeated` (listas), `map`, y los **well-known types** (`Timestamp`, `Duration`, `Any`, `Struct`).
- **Reflection**: si el servidor la expone, podés listar servicios/métodos sin el `.proto`; si no, necesitás el archivo.

## 2. Los cuatro modos de RPC

- **Unary**: request → response (como una llamada normal).
- **Server-streaming**: un request → muchos responses (un stream que termina).
- **Client-streaming**: muchos requests → un response.
- **Bidirectional**: ambos streams a la vez.
- Cada modo se prueba distinto: en los streaming, probá el fin del stream, un stream vacío, muchos elementos, y la **cancelación** a mitad.

## 3. Status codes y errores

- gRPC tiene **status codes propios**: `OK`, `INVALID_ARGUMENT`, `NOT_FOUND`, `ALREADY_EXISTS`, `UNAUTHENTICATED`, `PERMISSION_DENIED`, `DEADLINE_EXCEEDED`, `RESOURCE_EXHAUSTED`, `UNAVAILABLE`, `INTERNAL`…
- Cada error de negocio debe devolver el **status correcto** con un mensaje útil (y opcionalmente detalles ricos con `google.rpc.Status`), no un `INTERNAL` genérico ni un `OK` con un error adentro.
- Probá entradas inválidas → `INVALID_ARGUMENT`; recurso inexistente → `NOT_FOUND`; sin token → `UNAUTHENTICATED`; sin permiso → `PERMISSION_DENIED`.

## 4. Metadata, deadlines y cancelación

- **Metadata** (headers/trailers): autenticación (token en `authorization`), correlation id, y trailers con info del resultado.
- **Deadlines/timeouts**: el cliente fija un deadline; si el servidor tarda más, `DEADLINE_EXCEEDED`. Probá un deadline corto en una operación lenta.
- **Cancelación**: si el cliente cancela, el servidor debería dejar de trabajar (no seguir procesando).

## 5. Seguridad

- **TLS / mTLS** (certificados de cliente y servidor); autenticación por token en metadata; que un método protegido rechace sin credenciales (`UNAUTHENTICATED`/`PERMISSION_DENIED`).
- **Límites**: tamaño máximo de mensaje (`RESOURCE_EXHAUSTED` si se excede), compresión.

## 6. Compatibilidad del esquema (contract testing nativo)

- La compatibilidad de Protobuf es por **número de campo**: **agregar** un campo nuevo es compatible; **reusar** un número viejo o **cambiar el tipo** de un campo rompe a los clientes viejos; los campos removidos deben quedar **reservados** (`reserved`).
- Cambiar un `enum` o un `oneof` sin cuidado rompe. Esto es contract testing: el `.proto` es el contrato.

## 7. gRPC-Web e interceptores

- **gRPC-Web** para navegadores (sobre HTTP/1.1 o 2 con un proxy): probá que el proxy traduzca bien y que los errores lleguen.
- **Interceptores** (auth, logging, retry): que no alteren el contrato ni traguen errores.

## 8. WebSocket (API de tiempo real)

- Para APIs de tiempo real por **WebSocket** (suscripciones, push): reconexión sin perder/duplicar, heartbeat, orden y autorización por conexión — el detalle está disponible en K0lmenIA Pro.

## 9. Automatizar

- **grpcurl** (CLI) para invocar métodos con el `.proto` o por reflection; **Postman** soporta gRPC; **Buf** para lint y **breaking-change detection** del `.proto`.
- Derivá los casos desde el `.proto` (por método y modo, status esperados, validación, auth); el `ejecutor-api` los corre; el `api-mapper` los automatiza en k0lmena.
- Datos de prueba: un request válido, uno inválido por tipo/obligatorio, uno que dispare cada status, un stream vacío y uno largo.

## 10. Bugs típicos de gRPC

- Error de negocio devuelto como `INTERNAL` genérico o como `OK` con error adentro, en vez del status correcto.
- Reusar el número de un campo o cambiar su tipo → rompe a los clientes viejos (incompatibilidad de Protobuf).
- Deadline ignorado: el servidor sigue procesando tras `DEADLINE_EXCEEDED`.
- Stream que no cierra bien o que no maneja la cancelación del cliente.
- Método protegido que responde sin credenciales.
- Mensaje que excede el límite sin `RESOURCE_EXHAUSTED` claro.

## 11. Preguntas típicas para el equipo

Cuando no está escrito, son `FI-XX`:

- ¿Tenés el `.proto` o el servidor expone reflection? ¿Dónde está el endpoint de QA?
- ¿Qué modos de RPC usa (unary/streaming)?
- ¿Qué status debe devolver cada error de negocio?
- ¿Usa TLS/mTLS y autenticación por metadata?
- ¿Hay política de compatibilidad del `.proto` (Buf breaking)?
- ¿Hay gRPC-Web o WebSocket de por medio?

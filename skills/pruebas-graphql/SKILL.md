---
name: pruebas-graphql
description: El cómo de probar APIs GraphQL — introspección, queries y mutations, errores con HTTP 200, nulabilidad, paginación, N+1 y autorización por campo. La usan ejecutor-api y api-mapper.
---

# Pruebas de APIs GraphQL

GraphQL no es REST: hay **un solo endpoint** (`/graphql`), el cliente pide exactamente los campos que quiere, y **los errores viajan en el cuerpo** (`errors`) con HTTP **200**, no en el código HTTP. Eso cambia cómo se prueba. Se complementa con `ejecucion-api` (ejecución) y `tecnicas-de-diseno` (diseño de casos).

## 1. Esquema e introspección

- El **esquema** es el contrato: tipos, `Query`, `Mutation`, `Subscription`, campos, argumentos, enums, interfaces, uniones y **deprecaciones** (`@deprecated`).
- La **introspección** (`__schema`, `__type`) permite relevarlo; `${CLAUDE_PLUGIN_ROOT}/scripts/resumir_graphql.py` lo resume (por URL, SDL o JSON).
- **Introspección en producción**: suele deshabilitarse por seguridad; en QA sirve para armar los casos. Verificá cuál es la política.

## 2. Queries y mutations

- **Queries** (lectura) y **mutations** (escritura): probá cada operación del alcance con **variables** (no hardcodeadas en la query), **fragments**, **alias** y **directivas** (`@include(if:)`, `@skip(if:)`).
- Pedí **subconjuntos** de campos distintos: la respuesta trae exactamente lo pedido, ni más ni menos.
- **Mutations**: efecto correcto, idempotencia donde aplique, y que devuelvan el estado nuevo.

## 3. Manejo de errores (lo más distinto de REST)

- Una respuesta puede traer **`data` y `errors` a la vez**: un campo que falla se vuelve `null` y el error aparece en `errors` con su `path`, pero el resto de la respuesta llega igual (**error parcial**).
- **Nulabilidad**: si un campo **non-null** (`!`) falla, el error se **propaga hacia arriba** y anula toda la rama (hasta un campo nullable). Probá que un error en un campo opcional no tire abajo toda la query.
- Errores de **validación** (campo inexistente, tipo de variable mal, argumento faltante) → error de GraphQL, normalmente con HTTP 200 o 400 según la implementación.
- Un error de negocio **no** debería ser solo un `null` silencioso: tiene que estar en `errors` con un mensaje/código útil.

## 4. Autorización por campo y por tipo

- La autorización en GraphQL es **por campo/tipo**, no por ruta: un usuario puede ver `user.name` pero no `user.email`. Probá pedir campos sensibles con un rol que no debería verlos → deben venir en `errors`/`null`, no filtrarse.
- **IDOR**: pedir por id un recurso de otro usuario.

## 5. Rendimiento y abuso del backend

- **N+1**: una query que pide una lista con un campo relacionado puede disparar una consulta por elemento al backend. Pedí listas grandes con campos anidados y mirá los tiempos de respuesta.
- **Profundidad y complejidad**: GraphQL permite queries muy anidadas o costosas (incluso ciclos entre tipos). Debe haber **límite de profundidad** y de **complejidad/costo** y **rate limiting**; probá una query profunda/cara y verificá que se rechace.
- **Batching**: varias operaciones en una request; que no evada los límites.

## 6. Paginación

- **Cursor/Relay** (`edges`, `node`, `pageInfo`, `hasNextPage`, `endCursor`) u **offset** (`limit/offset`): recorré todas las páginas, la última, una vacía, y un cursor inválido.

## 7. Subscriptions (tiempo real)

- Por **WebSocket**: suscribirse, recibir los eventos esperados, reconexión y autorización por suscripción (el detalle de WebSocket está disponible en K0lmenIA Pro).

## 8. Persisted queries, caché y versionado

- **Persisted queries / APQ**: si está, solo se aceptan queries pre-registradas (por hash); una query arbitraria se rechaza.
- **Caché** por campo y su invalidación tras una mutation.
- GraphQL **no versiona** como REST: evoluciona con deprecaciones; un campo `@deprecated` sigue andando hasta que se retira.

## 9. Automatizar

- **POST** a `/graphql` con `{ "query": "...", "variables": {...} }` y validar `data`/`errors` con el `ejecutor-api` (Newman) o los **steps GraphQL de k0lmena** (`automatizacion-k0lmena`): `envío la consulta GraphQL:`, `la respuesta GraphQL no tiene errores`, etc.
- Resumí el esquema con `${CLAUDE_PLUGIN_ROOT}/scripts/resumir_graphql.py` para armar los casos: variables inválidas, campos inexistentes, autorización por campo, errores parciales, profundidad y paginación.

## 10. Bugs típicos de GraphQL

- Error de negocio que llega como `null` silencioso, sin nada en `errors`.
- Un error en un campo non-null que **tira abajo toda la query** por mala nulabilidad.
- **Sin límite de profundidad/complejidad**: una query anidada tumba el backend.
- **N+1** no resuelto (sin dataloader): una lista con relaciones dispara cientos de consultas.
- Autorización por ruta en vez de por campo: un campo sensible se filtra.
- Introspección habilitada en producción.
- Paginación que se rompe en la última página o con un cursor inválido.

## 11. Preguntas típicas para el PO (GraphQL)

Cuando no está escrito, son `FI-XX`:

- ¿Dónde está el endpoint y está la introspección habilitada en QA? ¿Y en producción?
- ¿Qué operaciones (queries/mutations/subscriptions) entran en el alcance?
- ¿La autorización es por campo/tipo? ¿Qué campos son sensibles por rol?
- ¿Hay límites de profundidad, complejidad o rate limiting?
- ¿Usan persisted queries / APQ?
- ¿Qué paginación (cursor/Relay u offset)?

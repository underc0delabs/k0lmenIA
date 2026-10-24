---
name: pruebas-scalar
description: El cómo de probar APIs en Scalar — conectarse al MCP que genera desde el OpenAPI, bajar el Registry, escribir casos, armar una colección ejecutable con tests pm (Newman) e importarla, y publicar ejemplos y scripts en el OpenAPI con confirmación. Lo usa probador-scalar; complementa a la familia de API.
---

# Pruebas de APIs en Scalar

Scalar guarda los **documentos OpenAPI** de las APIs del equipo (el **Registry**), los muestra como referencia, tiene un **cliente** (con colecciones y tests) y puede generar un **server MCP** de cada API. k0lmenIA usa las tres cosas: el MCP para explorar y llamar, el Registry para traer el contrato y para devolverle los casos, y la colección para correrlos sin agentes.

Herramienta: `npm run scalar -- <comando>` (`herramientas/scalar/scalar.py`). Conector: `scalar` (`npm run conector -- activar scalar`, ver `CONECTORES.md`).

## 1. Qué expone el MCP de Scalar

- Un server por API (`https://mcp.scalar.com/@<equipo>/<api>`, con `?env=<ambiente>`), generado desde el OpenAPI. Expone un conjunto chico de herramientas: buscar operaciones (p. ej. `search-openapi-operations`, que devuelve el request de ejemplo y lo que responde) y ejecutar las que el dashboard dejó en **Execute**. Revisá con `/mcp` qué herramientas tiene el tuyo: **no inventes nombres de tools**.
- **Search**: consulta la operación sin llamar a la API. **Execute**: manda el request real con las credenciales que guarda Scalar (el agente nunca las ve).
- Cada ejecución **consume créditos** del dueño de Scalar y hay límite de requests por minuto: el MCP es para **explorar y verificar**, no para correr la regresión (para eso, la colección con Newman).
- **Efecto**: ejecutar por el MCP un `POST`/`PUT`/`PATCH`/`DELETE` crea, modifica o borra datos reales del ambiente. Solo con confirmación explícita y en un ambiente de pruebas; los `GET` se pueden ejecutar libremente.

## 2. Traer el contrato

```bash
npm run scalar -- descargar --namespace <equipo> --slug <api> [--version latest]
python scripts/resumir_openapi.py input/api/scalar/<api>.json
```

Queda en `input/api/scalar/<api>.json` (contexto para todos los agentes de API). Si el Registry dice 401/403/404 y la API es privada: falta `SCALAR_API_KEY`. `npm run scalar -- listar --namespace <equipo>` lista las APIs del equipo.

## 3. Explorar

- Resumí el contrato (endpoints, auth, parámetros, body, status documentados) con `resumir_openapi.py`.
- Con el MCP, **buscá** cada operación del alcance para ver el request de ejemplo y lo que responde; **ejecutá** solo lecturas para ver datos reales (ids existentes, formatos, paginación), que después sirven para los casos.
- Anotá lo que el contrato no dice (un código de error sin documentar, una validación) como `Falta información` (`FI-XX`).

## 4. Casos de prueba

Con las mismas reglas de la familia de API (como el `generador-casos-api`): positivos, negativos (campos faltantes o inválidos, tipos, límites), de autenticación y autorización, de borde, paginación y errores documentados. **No inventes endpoints, campos ni status**: lo que no está en el contrato es un `FI-XX`. Si salen de una historia, primero `investigacion-contexto`.

Cada caso se escribe en `output/scalar/<api>/casos.json` (el formato está en el encabezado de `herramientas/scalar/scalar.py`): la operación (`metodo` + `ruta` del contrato, o `operationId`), los parámetros (`path`, `query`, `headers`), `auth`, el `body` y lo `esperado` (status; `json` con lo que el cuerpo **tiene que contener**; `campos` que tienen que existir, con puntos para anidar: `meta.total`; `headers`; `tiempo_ms`). Además, el Markdown legible de los casos (`casos-api-<HU o api>.md`, mismo formato que los del `generador-casos-api`).

## 5. Ejecutar (sin gastar créditos ni tokens en cada corrida)

```bash
npm run scalar -- coleccion --openapi input/api/scalar/<api>.json --casos output/scalar/<api>/casos.json
python scripts/correr_newman.py output/scalar/<api>/<api>.postman_collection.json --historia HU-XXX --base-url <url del ambiente>
```

La colección tiene **un request por caso**, agrupados por operación, con sus `pm.test`: el status esperado, el cuerpo, los campos, los headers, el tiempo y el **schema de la respuesta documentada** (resuelto del contrato). `{{base_url}}` y `{{token}}` salen de `--base-url`/`API_BASEURL` y `API_TOKEN` del `.env`. El reporte queda en `output/ejecuciones/` como cualquier corrida del `ejecutor-api`. Para automatizarlos en k0lmena (BDD), el `api-mapper` trabaja con el mismo OpenAPI.

Un test que falla **no es automáticamente un bug**: puede ser el caso, el dato o el ambiente. Confirmalo (repetí el request, miralo con el MCP) antes de pasarlo al `generador-reportes-bug`.

## 6. Llevar los casos a Scalar

Dos caminos, los dos con los mismos tests (Scalar usa la API `pm` de Postman):

1. **Al Registry, dentro del OpenAPI** (lo ve todo el equipo en el cliente de Scalar):
   ```bash
   npm run scalar -- enriquecer --openapi input/api/scalar/<api>.json --casos output/scalar/<api>/casos.json
   npm run scalar -- validar output/scalar/<api>/<api>.k0lmenia.json
   npm run scalar -- publicar output/scalar/<api>/<api>.k0lmenia.json --namespace <equipo> --slug <api> --version <versión nueva> --confirmar
   ```
   `enriquecer` agrega un **ejemplo por caso** (en el body y en los parámetros, con el `CP-API-XXX` como nombre) y, en cada operación, un `x-post-response` con los tests del **contrato** (status documentado y schema) y los de **cada caso** (se activan cuando el request coincide con el ejemplo del caso). El bloque va entre marcas `k0lmenIA:inicio/fin`: si alguien ya escribió scripts a mano, se conservan. **Publicar tiene efecto**: solo con confirmación explícita, como **versión nueva** (p. ej. `1.4.0-qa`) y **privada** por defecto; `--forzar` (pisar una versión) solo si la persona lo pide.
2. **Como colección**: la colección de Postman v2.1 del paso 5 se importa en el cliente de Scalar (importa colecciones de Postman v2.0/v2.1). La importación la hace la persona desde el cliente.

## 7. Preguntas para el responsable

- ¿Qué ambiente usa el server MCP (`?env=`) y qué operaciones están en Execute? ¿Se puede escribir en ese ambiente?
- ¿Hay créditos y límite suficientes para explorar?
- ¿En qué namespace y con qué versión se publican los casos? ¿Pública o privada?
- ¿Quién mantiene el OpenAPI? (si el equipo lo regenera desde el código, publicar una versión enriquecida puede pisarse: conviene una versión o un slug aparte, p. ej. `<api>-qa`).

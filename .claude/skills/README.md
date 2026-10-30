# Skills

Los **skills** son conocimiento empaquetado que Claude Code carga **on-demand** (solo cuando hace falta, sin pesar en el contexto si no se usan). Sirven para encapsular el "cómo" de una capacidad reutilizable que varios agentes pueden aprovechar.

## Skills disponibles

- **`tecnicas-de-diseno/`** — técnicas formales de diseño de casos de caja negra (clases de equivalencia, valores límite, tabla de decisión, transición de estados, pairwise). Sirve para derivar casos más completos al generar pruebas manuales, BDD o de API.
- **`ejecucion-e2e/`** — cómo ejecutar pruebas E2E en el navegador con Playwright MCP (modo headed/headless, ubicar elementos por accesibilidad, esperas para evitar flakiness, evidencia). Lo usa el agente `ejecutor-e2e`.
- **`ejecucion-api/`** — cómo ejecutar pruebas de API con Newman (la CLI de Postman): correr una colección, escribir validaciones, manejar base_url y token, e interpretar los resultados. Lo usa el agente `ejecutor-api`.
- **`investigacion-contexto/`** — cómo investigar a fondo una historia antes de trabajarla (primero la documentación del proyecto de `input/documentacion/` que arma el `documentador-proyecto`; después Jira con comentarios, subtareas, épica e issues vinculados; contratos; `input/`) y cómo registrar lo que falta como **Falta información** (`FI-XX`) en la ficha `output/contexto/contexto-HU-XXX.md`. Lo usan el analista, los generadores de casos, el revisor, los mappers y el `documentador-proyecto`.
- **`empezar/`** — bienvenida y puesta en marcha (`/k0lmenia:empezar` en el plugin): detecta si es plugin o repo clonado, prepara el proyecto (`k0lmenia init`), revisa el entorno (`doctor`), guía la conexión de herramientas (`configurar`, que corre la persona en una terminal) y sugiere la primera tarea o deriva a `guia-pruebas`; deja el estado en `output/entorno/informe-entorno.html`. Lo usa la conversación principal.
- **`guia-pruebas/`** — asistente interactivo que guía a la persona para elegir qué probar y con qué agente o skill: pregunta paso a paso, ramifica según las respuestas y recomienda o ejecuta; incluye el mapa de plataforma y tipo de prueba hacia el agente/skill que corresponde. Cuando la guía termina en un plan de más de un paso, lo deja en HTML en `output/guia/<tema>/`. Lo usa la conversación principal (los subagentes no pueden preguntar).
- **`base-conocimiento/`** — flujo de la conversación principal para armar y mantener la base de conocimiento de **todo** el proyecto en `input/documentacion/` (documentador en modo barrido y con la app recorrida de punta a punta con sesión), usarla para escribir y automatizar casos, y mantenerla al día cuando cambian los requerimientos (historias, código y aplicación).
- **`ejecucion-manual/`** — guía al QA por los casos manuales paso a paso desde la conversación principal (`/k0lmenia:ejecucion-manual HU-012`): resultados, evidencia, tiempos, bugs y pausa/retomar; lo cierra el `asistente-ejecucion-manual`.
- **`documentacion-proyecto/`** — Referencia del documentador-proyecto — cómo leer el repositorio y qué buscar en el código, el mapa funcional, qué se guarda en input/documentacion/ (encabezado, fuentes, dossier), y los pasos detallados de los modos barrido y actualizar con scripts/cambios_documentacion.py.
- **`redaccion-casos-manuales/`** — Referencia del generador-casos-manuales — columnas de la planilla, esquema del JSON para scripts/generar_casos.py (con Falta información y versión en inglés), reglas de cada campo, qué genera el script y las secciones del informe de cobertura.
- **`pruebas-graphql/`** — cómo probar APIs GraphQL: schema e introspección, queries/mutations/subscriptions con variables y fragments, errores parciales y nulabilidad (data + errors con HTTP 200), autorización por campo/tipo, N+1, límites de profundidad y complejidad, paginación (cursor/offset) y persisted queries. La usan el `ejecutor-api` y el `api-mapper`.
- **`pruebas-grpc/`** — cómo probar gRPC y APIs de tiempo real: Protocol Buffers (.proto, campos y números), los cuatro modos de RPC, status codes de gRPC, metadata, deadlines y cancelación, TLS/mTLS, compatibilidad de Protobuf y gRPC-Web. La usan el `ejecutor-api` y el `api-mapper`.
- **`automatizacion-k0lmena/`** — convenciones para generar automatización en k0lmena (`herramientas/k0lmena`): estructura web y api, nombres y tags, reutilización de steps, helpers, steps genéricos de API y validación con `npm`. Incluye los steps de verificación en base de datos (que se agregan solo cuando se piden). Lo usan `web-mapper` y `api-mapper`.


## Cómo agregar uno

Creá una carpeta en `.claude/skills/` con un `SKILL.md` adentro:

```
.claude/skills/
└── mi-skill/
    ├── SKILL.md          # obligatorio: frontmatter (name, description) + instrucciones
    ├── references/       # opcional: detalle que se carga solo si hace falta
    └── scripts/          # opcional: scripts que el skill ejecuta
```

El `description` del frontmatter es lo que usa Claude Code para decidir cuándo cargar el skill. Más detalle en [`../../ARQUITECTURA.md`](../../ARQUITECTURA.md).

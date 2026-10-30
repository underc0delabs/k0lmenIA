# Catálogo de agentes

Los 13 agentes de K0lmenIA Light: para qué sirve cada uno, cómo pedírselo, qué skills, scripts, herramientas y conectores usa, y qué entrega. No hace falta nombrar al agente: Claude Code elige el que corresponde según el pedido (también se lo podés pedir por su nombre).

**Leyenda**
- **Tokens**: *en cada uso* = trabaja con el modelo cada vez que lo pedís; *una vez* = genera algo que después corre solo, sin agentes ni tokens (`k0lmenia test`).
- **Confirma**: el agente no hace la acción sin tu ok explícito (por ejemplo, crear casos en Xray). Como los agentes no pueden preguntar a mitad del trabajo, devuelven **"Necesito que confirmes"** y Claude te pregunta.
- **Conectores**: los que vienen activos (`playwright`, `atlassian`) no necesitan nada; `k0lmena-tmt` se activa con `k0lmenia conector -- activar k0lmena-tmt` (ver `CONECTORES.md`).

## Resumen

| Agente | Familia | Para qué | Skills | Herramientas y scripts | Conectores | Salida |
|---|---|---|---|---|---|---|
| documentador-proyecto | Análisis y diseño | Documentación del proyecto: repo, historias, links y web | documentacion-proyecto, investigacion-contexto, ejecucion-e2e | k0lmenia mapa-funcional, indice_documentacion.py | atlassian, playwright-headless | input/documentacion/ |
| analista-historias | Análisis y diseño | Ambigüedades, riesgos y preguntas de una historia | investigacion-contexto | formatear_tablas.py | atlassian | output/analisis-historias/ |
| generador-casos-manuales | Análisis y diseño | Casos manuales en Excel, Markdown y cobertura | redaccion-casos-manuales, tecnicas-de-diseno, investigacion-contexto | generar_casos.py, formatear_tablas.py | atlassian | output/casos-de-prueba/manuales/ |
| generador-casos-bdd | Análisis y diseño | Escenarios Gherkin y cobertura | investigacion-contexto, tecnicas-de-diseno | formatear_tablas.py | atlassian | output/casos-de-prueba/bdd/ |
| revisor-casos | Análisis y diseño | Calidad de los casos, duplicados y tiempo de ejecución | investigacion-contexto, tecnicas-de-diseno | revisar_casos.py, generar_informe_revision.py, estimacion.py | atlassian | output/revision-casos/ |
| triador-bugs | Análisis y diseño | Duplicados, regresiones y clasificación de bugs antes de cargarlos | — | buscar_duplicados.py, avisar.py | atlassian | output/triage/ |
| ejecutor-e2e | Ejecución en vivo | Corre casos en el navegador con evidencia | ejecucion-e2e | Playwright MCP, generar_reporte.py | playwright, playwright-headless | output/ejecuciones/ |
| ejecutor-api | Ejecución en vivo | Corre una colección de Postman, Bruno o Insomnia | ejecucion-api, pruebas-graphql, pruebas-grpc | Newman, correr_newman.py | — | output/ejecuciones/ |
| asistente-ejecucion-manual | Ejecución en vivo | Cierra la ejecución manual acompañada: informe y publicación | ejecucion-manual | ejecucion_manual.py, generar_informe_ejecucion_manual.py | — | output/ejecucion-manual/ |
| web-mapper | Automatización con k0lmena | Automatiza casos web en k0lmena | automatizacion-k0lmena, ejecucion-e2e, investigacion-contexto | k0lmena web | playwright, playwright-headless | herramientas/k0lmena/web/ |
| api-mapper | Automatización con k0lmena | Automatiza endpoints desde Postman o Swagger/OpenAPI | automatizacion-k0lmena, investigacion-contexto, tecnicas-de-diseno, pruebas-graphql, pruebas-grpc | k0lmena api, resumir_openapi.py, resumir_graphql.py | — | herramientas/k0lmena/api/ |
| gestor-pruebas | Gestión de pruebas | Carpetas, casos y ciclos en Xray o k0lmenaTMT | — | ${CLAUDE_PLUGIN_ROOT}/scripts/gestion/gestion.py | k0lmena-tmt (consultas) | Xray o k0lmenaTMT + output/gestion/ |
| publicador-resultados | Gestión de pruebas | Resultados de `k0lmenia test` al ciclo, con evidencias | — | ${CLAUDE_PLUGIN_ROOT}/scripts/gestion/gestion.py | — | Xray o k0lmenaTMT |

## Análisis y diseño

### documentador-proyecto
- **Cuándo**: al empezar con un proyecto (para armar la base de contexto) y antes de trabajar una historia o épica (para juntar todo lo que hay sobre ella), así los demás agentes escriben casos con contexto real.
- **Pedido de ejemplo**: *"Documentá el proyecto"* · *"Juntá todo el contexto de PROJ-12 antes de escribir los casos"* · *"Documentá todas las historias de la épica PROJ-3"* (modo barrido) · *"Explorá la plataforma de punta a punta"* · *"Actualizá la documentación: cambiaron los requerimientos"*.
- **Entradas**: el repositorio de la aplicación clonado en tu PC (`REPO_RUTA_LOCAL` en el `.env`), la historia o épica (key de Jira o `HU-XXX`) y la URL de la app (`APP_URL`).
- **Usa**: skill `documentacion-proyecto` (lectura del repo, mapa funcional, estructura y dossier, modos barrido y actualizar); el código del repositorio local en solo lectura (README y docs, validaciones, límites, mensajes, estados, roles y permisos, rutas y contratos de API); skill `investigacion-contexto` (historia de Jira, comentarios, subtareas, épica y vínculos) y links públicos; `k0lmenia mapa-funcional` (páginas, menús, formularios con sus campos, botones y mensajes, sin enviar nada) y, puntualmente, Playwright MCP con el skill `ejecucion-e2e`; `${CLAUDE_PLUGIN_ROOT}/scripts/indice_documentacion.py` y `${CLAUDE_PLUGIN_ROOT}/scripts/formatear_tablas.py`.
- **Entrega**: en `input/documentacion/` (no se versiona), `INDICE.md`; `proyecto/` con resumen, repositorio, reglas de negocio, mensajes, estados y permisos, mapa funcional y links; `api/` con los contratos; y `historias/<HU o key>/dossier.md` (historia, decisiones, links, código tocado, pantallas, contradicciones y pistas para probar). Cada dato con su fuente. El skill `investigacion-contexto` lo lee primero, así que lo aprovechan todos los agentes que investigan una historia.
- **Tokens**: en cada uso (el recorrido de la web y el índice los hacen scripts).

### analista-historias
- **Cuándo**: antes de diseñar pruebas, para encontrar huecos y ambigüedades en una historia.
- **Pedido de ejemplo**: *"Analizá la historia HU-001"* · *"Revisá PROJ-12 de Jira y decime qué falta definir"*.
- **Entradas**: la historia (en `input/historias/` o una key de Jira) y su documentación.
- **Usa**: skill `investigacion-contexto` (comentarios, subtareas, épica y vínculos); `${CLAUDE_PLUGIN_ROOT}/scripts/formatear_tablas.py`.
- **Entrega**: `output/analisis-historias/analisis-HU-XXX.md` con ambigüedades, riesgos, casos no contemplados y preguntas para el PO; la ficha `output/contexto/contexto-HU-XXX.md` con los `FI-XX`.
- **Tokens**: en cada uso.

### generador-casos-manuales
- **Cuándo**: para escribir los casos de prueba de una historia.
- **Pedido de ejemplo**: *"Generá los casos de prueba de HU-001"*.
- **Usa**: skill `redaccion-casos-manuales` (columnas, esquema del JSON, reglas de campos e informe de cobertura); skills `investigacion-contexto` y `tecnicas-de-diseno` (equivalencia, valores límite, tabla de decisión, estados, pairwise); `${CLAUDE_PLUGIN_ROOT}/scripts/generar_casos.py` y `${CLAUDE_PLUGIN_ROOT}/scripts/formatear_tablas.py`.
- **Entrega**: en `output/casos-de-prueba/manuales/`, `casos-HU-XXX.xlsx` + `casos-HU-XXX.md` + `casos-HU-XXX-cobertura.md` (cobertura por criterio, ambigüedades y preguntas). Los casos con información faltante quedan resaltados y con su `FI-XX`.
- **Tokens**: en cada uso.

### generador-casos-bdd
- **Cuándo**: para tener los escenarios en Gherkin (por ejemplo, para automatizarlos después).
- **Pedido de ejemplo**: *"Pasá HU-001 a BDD"*.
- **Usa**: skills `investigacion-contexto` y `tecnicas-de-diseno`; `${CLAUDE_PLUGIN_ROOT}/scripts/formatear_tablas.py`.
- **Entrega**: en `output/casos-de-prueba/bdd/`, `HU-XXX-<tema>.feature` (keywords en inglés, contenido en español, cada escenario con `@CP-XXX`) + `HU-XXX-cobertura.md`.
- **Tokens**: en cada uso.

### revisor-casos
- **Cuándo**: para revisar casos que ya existen antes de ejecutarlos, subirlos a la herramienta de gestión o automatizarlos.
- **Pedido de ejemplo**: *"Revisá los casos de HU-001"* · *"¿Hay casos duplicados en la regresión?"* · *"¿Cuánto lleva ejecutar a mano los casos del sprint?"*.
- **Usa**: skills `investigacion-contexto` y `tecnicas-de-diseno`; `${CLAUDE_PLUGIN_ROOT}/scripts/revisar_casos.py`, `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_revision.py` y `${CLAUDE_PLUGIN_ROOT}/scripts/estimacion.py`.
- **Entrega**: en `output/revision-casos/<HU o nombre>/`, `informe-revision.html` (puntaje de cada caso, problemas con su sugerencia, duplicados, historias sin negativos, tiempo de ejecución manual y la versión mejorada que propone) y, si lo pedís, la planilla corregida en un archivo nuevo.
- **Confirma**: actualizar casos en la herramienta de gestión.
- **Tokens**: en cada uso (la revisión mecánica la hace el script).

### triador-bugs
- **Cuándo**: antes de cargar un bug en Jira, o para revisar un lote de bugs del sprint, para que no entren duplicados y cada bug llegue con severidad, componente e historia.
- **Pedido de ejemplo**: *"¿BUG-008 ya está cargado en Jira?"* · *"Triá los bugs de output/reportes-bug"* · *"Buscá duplicados de 'el pago rechaza tarjetas válidas'"*.
- **Entradas**: el bug (`output/reportes-bug/`, `input/bugs/`, texto o key de Jira) y el proyecto donde buscar.
- **Usa**: conector `atlassian` (JQL) para traer candidatos, incluidos los cerrados; `${CLAUDE_PLUGIN_ROOT}/scripts/buscar_duplicados.py` (similitud con normalización y sinónimos); `${CLAUDE_PLUGIN_ROOT}/scripts/avisar.py` para avisar un bug crítico, solo si se pide.
- **Entrega**: veredicto (nuevo, duplicado, posible regresión de un bug cerrado o relacionado), severidad y prioridad con su criterio, componente, responsable sugerido (solo el usuario de la herramienta) e historia a vincular; `output/triage/<nombre>/` con `candidatos.json`, `triage.json` y `triage.md` (con la **Conclusión del triador** al final).
- **Tokens**: en cada uso (el puntaje lo hace el script).
- **Confirma**: crear, vincular, comentar, reabrir o cambiar campos en Jira.

## Ejecución en vivo

### ejecutor-e2e
- **Cuándo**: para correr en el navegador casos o escenarios que no están automatizados.
- **Pedido de ejemplo**: *"Ejecutá CP-001 y CP-002 de HU-001 contra https://tu-app.com en headless"*.
- **Usa**: skill `ejecucion-e2e`; conectores `playwright` (headed, ves el navegador) o `playwright-headless`; `${CLAUDE_PLUGIN_ROOT}/scripts/generar_reporte.py`.
- **Entrega**: en `output/ejecuciones/`, `reporte-HU-XXX-<fecha-hora>.html` + `_resultados-HU-XXX-<fecha-hora>.json`, y capturas en `evidencia/`.
- **Confirma**: el modo (headed o headless) si no lo dijiste. Las credenciales salen del `.env`.
- **Tokens**: en cada uso.

### ejecutor-api
- **Cuándo**: para correr una colección de Postman, Bruno o Insomnia contra una API.
- **Pedido de ejemplo**: *"Corré la colección de input/api para HU-001"*.
- **Usa**: skills `ejecucion-api`, `pruebas-graphql` y `pruebas-grpc`; Newman, con `${CLAUDE_PLUGIN_ROOT}/scripts/correr_newman.py` (token y URL del `.env`, en cualquier sistema).
- **Entrega**: en `output/ejecuciones/`, `reporte-HU-XXX-<fecha-hora>.html` + `_resultados-HU-XXX-<fecha-hora>.json`.
- **Confirma**: correr métodos con efecto (POST/PUT/PATCH/DELETE, mutations).
- **Tokens**: en cada uso.

### asistente-ejecucion-manual
- **Cuándo**: para ejecutar casos manuales sin ir y venir entre la app y la planilla. La conversación principal guía al QA caso por caso y paso por paso con el skill `ejecucion-manual` (`/k0lmenia:ejecucion-manual HU-012`). El agente cierra la sesión, arma el informe y deja lista la publicación.
- **Pedido de ejemplo**: *"Acompañame a ejecutar los casos de HU-012"* · *"Retomemos la ejecución manual de ayer"* · *"Cerrá la sesión manual de HU-950 y armá el informe"*.
- **Entradas**: la planilla de casos (`.xlsx` de `generar_casos.py`, su `.json`, un `.feature`, o los casos bajados de la herramienta de gestión), el ambiente, el navegador y el tester; la evidencia que va sacando el QA.
- **Usa**: skill `ejecucion-manual`; `${CLAUDE_PLUGIN_ROOT}/scripts/ejecucion_manual.py` (sesión con pausa y retomar, tiempos sin pausas, redacción de secretos, inconsistencias) y `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_ejecucion_manual.py`. Se apoya en el `triador-bugs` para los fallos y en el `publicador-resultados` para publicar.
- **Entrega**: en `output/ejecucion-manual/<HU>/`, `sesion.json`, `analisis.json` e `informe-ejecucion-manual.html` (ES/EN: avance, resultados, tiempo real contra estimado, por prioridad, inconsistencias, pasos fallidos, bugs, pendientes y publicación) y `output/ejecuciones/_resultados-<HU>-manual-<fecha>.json` para el informe de ejecución.
- **Confirma**: publicar en Xray o k0lmenaTMT; crear o vincular bugs en Jira; cambiar un resultado que registró el QA.
- **Tokens**: pocos por paso (una pregunta corta por paso); el cierre y el informe son scripts.

## Automatización con k0lmena

### web-mapper
- **Cuándo**: para automatizar casos web.
- **Pedido de ejemplo**: *"Automatizá en k0lmena los casos de HU-001 contra https://tu-app.com"*.
- **Usa**: skills `automatizacion-k0lmena`, `ejecucion-e2e` e `investigacion-contexto`; conectores `playwright` / `playwright-headless`; k0lmena web (Playwright + Cucumber).
- **Entrega**: `herramientas/k0lmena/web/features/HU-XXX-<tema>.feature`, `steps/HU-XXX.steps.ts`, `locators/HU-XXX.locators.ts` y `output/mapeos/mapeo-HU-XXX-web.md`. Se corre con `k0lmenia test:web`.
- **Confirma**: headed o headless, si no lo dijiste.
- **Tokens**: una vez.

### api-mapper
- **Cuándo**: para automatizar pruebas de API desde una colección de Postman o un Swagger/OpenAPI (REST, GraphQL o gRPC).
- **Pedido de ejemplo**: *"Automatizá los endpoints de /pet de https://petstore.swagger.io/v2/swagger.json"*.
- **Usa**: skills `automatizacion-k0lmena`, `investigacion-contexto`, `tecnicas-de-diseno`, `pruebas-graphql` y `pruebas-grpc`; `${CLAUDE_PLUGIN_ROOT}/scripts/resumir_openapi.py` y `${CLAUDE_PLUGIN_ROOT}/scripts/resumir_graphql.py`; k0lmena api (axios + Cucumber, steps genéricos).
- **Entrega**: `herramientas/k0lmena/api/features/*.feature` y `output/mapeos/mapeo-<HU o contrato>-api.md`. Se corre con `k0lmenia test:api`.
- **Confirma**: el alcance y los métodos con efecto (POST, PUT, PATCH, DELETE) antes de llamarlos.
- **Tokens**: una vez.

## Gestión de pruebas

### gestor-pruebas
- **Cuándo**: para llevar los casos a la herramienta del equipo y armar los ciclos.
- **Pedido de ejemplo**: *"Subí los casos de HU-001 a Xray en la carpeta 'HU-001 Registro', vinculados a PROJ-12"*.
- **Usa**: `${CLAUDE_PLUGIN_ROOT}/scripts/gestion/gestion.py` (Xray Cloud, Xray Server/DC y k0lmenaTMT, este último por su server MCP sin el modelo; el conector `k0lmena-tmt` queda para consultas).
- **Entrega**: carpetas, casos, vínculos con la historia y ciclos en la herramienta, y la trazabilidad `output/gestion/HU-XXX-<herramienta>.json`.
- **Confirma**: carpeta, historia y ciclo; la primera vez, una prueba en seco (`--dry-run`).
- **Tokens**: en cada uso (poco: el script hace el trabajo).

### publicador-resultados
- **Cuándo**: después de correr `k0lmenia test`, para cargar los resultados en el ciclo.
- **Pedido de ejemplo**: *"Subí los resultados de la última corrida web al ciclo PROJ-60"*.
- **Usa**: `${CLAUDE_PLUGIN_ROOT}/scripts/gestion/gestion.py` (`extraer-resultados` y `publicar-resultados`; en k0lmenaTMT, la ejecución de cada caso con sus evidencias y un `resultado.txt` con el detalle).
- **Entrega**: el estado de cada caso en el ciclo, con el error y las evidencias (captura, GIF y video si falló). Publica una historia por vez para no mezclar casos. Sirve para k0lmena y para cualquier framework que genere JUnit XML.
- **Confirma**: el ciclo, si lo propuso él.
- **Tokens**: en cada uso (poco: el script hace el trabajo).

## Skills: el "cómo" que usan los agentes

Los skills se cargan solo cuando hacen falta.

| Skill | Qué enseña | Lo usan |
|---|---|---|
| investigacion-contexto | Investigar la historia completa (documentación del proyecto, comentarios, subtareas, épica, contratos) y registrar la Falta información (FI-XX) | analista-historias, generador-casos-manuales, generador-casos-bdd, revisor-casos, web-mapper, api-mapper, documentador-proyecto |
| tecnicas-de-diseno | Equivalencia, valores límite, tabla de decisión, transición de estados y pairwise | generador-casos-manuales, generador-casos-bdd, api-mapper, revisor-casos |
| redaccion-casos-manuales | Columnas, esquema del JSON de generar_casos.py, reglas de campos e informe de cobertura | generador-casos-manuales |
| ejecucion-e2e | Ejecutar en el navegador con Playwright MCP: modos, snapshots, esperas y evidencia | ejecutor-e2e, web-mapper, documentador-proyecto |
| ejecucion-api | Correr colecciones con Newman: base_url, token, validaciones y resultados | ejecutor-api |
| pruebas-graphql | Probar APIs GraphQL: schema e introspección, queries, mutations y subscriptions, errores parciales, autorización por campo, N+1, profundidad y paginación | ejecutor-api, api-mapper |
| pruebas-grpc | gRPC (Protobuf, modos de RPC, status codes, deadlines, compatibilidad) y WebSocket | ejecutor-api, api-mapper |
| automatizacion-k0lmena | Convenciones de k0lmena: features, steps, locators, tags y steps de BD | web-mapper, api-mapper |
| documentacion-proyecto | Lectura del repositorio, mapa funcional, estructura de input/documentacion/ y dossier, modos barrido y actualizar | documentador-proyecto |
| base-conocimiento | Armar y mantener la base de conocimiento del proyecto en input/documentacion/ y la rutina ágil cuando cambian los requerimientos | la conversación principal |
| ejecucion-manual | Ejecución manual acompañada: caso por caso y paso por paso, resultados, evidencia, tiempos, bugs, pausa y retomar | la conversación principal (`/k0lmenia:ejecucion-manual`) y asistente-ejecucion-manual |
| guia-pruebas | Asistente interactivo para elegir qué probar y con qué agente o skill | la conversación principal |
| empezar | Bienvenida y puesta en marcha: preparar el proyecto, revisar el entorno, conectar herramientas y elegir la primera tarea | la conversación principal (`/k0lmenia:empezar` en el plugin) |

## Herramientas y scripts: quién usa qué

| Herramienta o script | Para qué | La usan |
|---|---|---|
| k0lmena (herramientas/k0lmena) | Automatización web y API; corre sin tokens con `k0lmenia test` | web-mapper, api-mapper |
| Playwright MCP | Navegador en vivo | ejecutor-e2e, web-mapper, documentador-proyecto |
| Newman (${CLAUDE_PLUGIN_ROOT}/herramientas/newman) | Colecciones de Postman, Bruno e Insomnia | ejecutor-api |
| ${CLAUDE_PLUGIN_ROOT}/herramientas/ci (k0lmenia ci) | Pipeline de k0lmena para GitHub Actions, GitLab CI, Jenkins o Azure Pipelines | a pedido |
| ${CLAUDE_PLUGIN_ROOT}/scripts/generar_casos.py | Planilla de casos `.xlsx` desde el JSON del generador | generador-casos-manuales |
| ${CLAUDE_PLUGIN_ROOT}/scripts/revisar_casos.py · generar_informe_revision.py | Revisión mecánica de casos e informe | revisor-casos |
| ${CLAUDE_PLUGIN_ROOT}/scripts/estimacion.py | Tiempo de ejecución manual estimado | revisor-casos, asistente-ejecucion-manual |
| ${CLAUDE_PLUGIN_ROOT}/scripts/buscar_duplicados.py | Similitud entre bugs para detectar duplicados y regresiones | triador-bugs |
| ${CLAUDE_PLUGIN_ROOT}/scripts/generar_reporte.py | Reporte HTML de una ejecución | ejecutor-e2e, ejecutor-api |
| ${CLAUDE_PLUGIN_ROOT}/scripts/correr_newman.py · newman_a_resultados.py | Correr Newman con el `.env` y pasar los resultados al formato común | ejecutor-api |
| ${CLAUDE_PLUGIN_ROOT}/scripts/resumir_openapi.py · resumir_graphql.py | Resumen de un contrato OpenAPI o un schema GraphQL | api-mapper, ejecutor-api |
| ${CLAUDE_PLUGIN_ROOT}/scripts/indice_documentacion.py | Índice de input/documentacion/ | documentador-proyecto |
| ${CLAUDE_PLUGIN_ROOT}/scripts/ejecucion_manual.py (k0lmenia ejecucion-manual) | Sesión de ejecución manual: iniciar, siguiente, registrar, pausar, retomar, estado y cerrar | skill ejecucion-manual y asistente-ejecucion-manual |
| ${CLAUDE_PLUGIN_ROOT}/scripts/gestion/gestion.py | Casos, ciclos y resultados en Xray Cloud, Xray Server/DC y k0lmenaTMT | gestor-pruebas, publicador-resultados |
| ${CLAUDE_PLUGIN_ROOT}/scripts/avisar.py (k0lmenia avisar) | Avisos a Slack y Teams | triador-bugs (a pedido) |
| ${CLAUDE_PLUGIN_ROOT}/scripts/formatear_tablas.py | Alinea las tablas Markdown | todos los que escriben Markdown |

## Conectores: qué agentes los aprovechan

| Conector | Activo por defecto | Lo aprovechan |
|---|---|---|
| playwright · playwright-headless | Sí | ejecutor-e2e, web-mapper, documentador-proyecto |
| atlassian (Jira) | Sí | todos los que investigan una historia (skill investigacion-contexto), triador-bugs |
| k0lmena-tmt | No | consultas en k0lmenaTMT (casos, planes, estadísticas); las cargas van por ${CLAUDE_PLUGIN_ROOT}/scripts/gestion |

¿Necesitás más agentes? **K0lmenIA Pro** suma todos los agentes para probar (101 en total) y **K0lmenIA Empresa**, los de métricas, auditoría y gestión del equipo: https://k0lmena.com/k0lmenia/

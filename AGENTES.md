# Catálogo de agentes

Los 19 agentes de k0lmenIA: para qué sirve cada uno, cómo pedírselo, qué skills, scripts, herramientas y conectores usa, y qué entrega. No hace falta nombrar al agente: Claude Code elige el que corresponde según el pedido (también se lo podés pedir por su nombre).

**Leyenda**
- **Tokens**: *en cada uso* = trabaja con el modelo cada vez que lo pedís; *una vez* = genera algo que después corre solo, sin agentes ni tokens (`npm test`, `npm run perf`).
- **Confirma**: el agente no hace la acción sin tu ok explícito (por ejemplo, escribir en una base o crear casos en Xray). Como los agentes no pueden preguntar a mitad del trabajo, devuelven **"Necesito que confirmes"** y Claude te pregunta.
- **Conectores**: los que vienen activos (`playwright`, `atlassian`) no necesitan nada; los demás se activan con `npm run conector -- activar <nombre>` (ver `CONECTORES.md`).

## Resumen

| Agente                   | Familia                  | Para qué                                              | Skills                                                             | Herramientas y scripts                                        | Conectores                           | Salida                                                  |
| ------------------------ | ------------------------ | ----------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------- |
| analista-historias       | Análisis y diseño        | Ambigüedades, riesgos y preguntas de una historia     | investigacion-contexto                                             | formatear_tablas.py                                           | atlassian, azure-devops, figma       | output/analisis-historias/                              |
| estratega-pruebas        | Análisis y diseño        | Plan de pruebas (alcance, riesgos, criterios)         | investigacion-contexto                                             | generar_plan.py                                               | atlassian, azure-devops, figma       | output/planes-de-prueba/                                |
| generador-casos-manuales | Análisis y diseño        | Casos manuales en Excel, Markdown y cobertura         | investigacion-contexto, tecnicas-de-diseno                         | generar_casos.py, formatear_tablas.py                         | atlassian, azure-devops, figma       | output/casos-de-prueba/manuales/                        |
| generador-casos-bdd      | Análisis y diseño        | Escenarios Gherkin y cobertura                        | investigacion-contexto, tecnicas-de-diseno                         | formatear_tablas.py                                           | atlassian, azure-devops, figma       | output/casos-de-prueba/bdd/                             |
| generador-casos-api      | Análisis y diseño        | Casos de API desde un contrato                        | investigacion-contexto, tecnicas-de-diseno                         | formatear_tablas.py                                           | atlassian, azure-devops              | output/casos-api/                                       |
| generador-datos-prueba   | Análisis y diseño        | Datos válidos, inválidos y de borde                   | investigacion-contexto                                             | formatear_tablas.py                                           | atlassian, azure-devops              | output/datos-de-prueba/                                 |
| generador-reportes-bug   | Análisis y diseño        | Reporte de bug desde una observación                  | —                                                                  | formatear_tablas.py, plantilla de bug                         | atlassian, azure-devops              | output/reportes-bug/                                    |
| ejecutor-e2e             | Ejecución en vivo        | Corre casos en el navegador con evidencia             | ejecucion-e2e                                                      | Playwright MCP, generar_reporte.py                            | playwright, playwright-headless      | output/ejecuciones/                                     |
| ejecutor-api             | Ejecución en vivo        | Corre una colección de Postman                        | ejecucion-api                                                      | Newman, correr_newman.py                                      | —                                    | output/ejecuciones/                                     |
| analista-seguridad       | Ejecución en vivo        | Escaneo de seguridad web pasivo e informe             | —                                                                  | OWASP ZAP (Docker), escanear.py, generar_informe_seguridad.py | —                                    | output/seguridad/                                       |
| generador-reporte-html   | Reportes                 | Reporte HTML de una corrida                           | —                                                                  | generar_reporte.py                                            | —                                    | output/ejecuciones/                                     |
| generador-reporte-cierre | Reportes                 | Informe de cierre y go/no-go de la ronda              | —                                                                  | recolectar_resultados.py, generar_informe_cierre.py           | —                                    | output/informes-cierre/                                 |
| web-mapper               | Automatización (k0lmena) | Automatiza casos web                                  | automatizacion-k0lmena, ejecucion-e2e, investigacion-contexto      | k0lmena (Playwright + Cucumber)                               | playwright, playwright-headless      | herramientas/k0lmena/web/ + output/mapeos/              |
| api-mapper               | Automatización (k0lmena) | Automatiza APIs desde Postman o Swagger               | automatizacion-k0lmena, investigacion-contexto, tecnicas-de-diseno | k0lmena (axios + Cucumber)                                    | —                                    | herramientas/k0lmena/api/ + output/mapeos/              |
| mobile-mapper            | Automatización (k0lmena) | Automatiza casos mobile                               | automatizacion-k0lmena, investigacion-contexto                     | k0lmena (WebdriverIO + Appium)                                | appium-mcp                           | herramientas/k0lmena/mobile/ + output/mapeos/           |
| performance-mapper       | Automatización (k0lmena) | Carga, estrés, soak y picos con informe               | automatizacion-k0lmena, guia-performance                           | k6, Artillery, JMeter, generar_informe_performance.py         | —                                    | herramientas/k0lmena/performance/ + output/performance/ |
| verificador-datos        | Automatización (k0lmena) | Consulta y verifica datos en bases                    | automatizacion-k0lmena                                             | k0lmena tools/bd (npm run bd)                                 | —                                    | chat (+ output/verificaciones-datos/)                   |
| gestor-pruebas           | Gestión                  | Carpetas, casos y ciclos en la herramienta de gestión | —                                                                  | gestion.py, para_azure_devops.py                              | azure-devops (para Azure Test Plans) | Xray / QMetry / AIO / Azure DevOps + output/gestion/    |
| publicador-resultados    | Gestión                  | Sube resultados de npm test con evidencias            | —                                                                  | gestion.py                                                    | —                                    | Xray / QMetry / AIO                                     |

---

## Análisis y diseño

### analista-historias
- **Cuándo**: antes de diseñar pruebas, para encontrar huecos y ambigüedades en una historia.
- **Pedido de ejemplo**: *"Analizá la historia HU-001"* · *"Revisá PROJ-12 de Jira y decime qué falta definir"*.
- **Entradas**: la historia (en `input/historias/`, una key de Jira o un work item de Azure DevOps) y su documentación.
- **Usa**: skill `investigacion-contexto` (comentarios, subtareas, épica, Confluence, Figma); `scripts/formatear_tablas.py`.
- **Entrega**: `output/analisis-historias/analisis-HU-XXX.md` con ambigüedades, riesgos, casos no contemplados y preguntas para el PO; la ficha `output/contexto/contexto-HU-XXX.md` con los `FI-XX`.
- **Tokens**: en cada uso.

### estratega-pruebas
- **Cuándo**: al empezar una historia, feature o release, para acordar qué se prueba y cómo.
- **Pedido de ejemplo**: *"Armá el plan de pruebas de HU-001"*.
- **Usa**: skill `investigacion-contexto`; `scripts/generar_plan.py`.
- **Entrega**: `output/planes-de-prueba/plan-HU-XXX-<fecha>.html` (dashboard): objetivos, alcance, tipos de prueba, riesgos, datos y entorno, criterios de entrada y salida, supuestos y preguntas.
- **Tokens**: en cada uso.

### generador-casos-manuales
- **Cuándo**: para escribir los casos de prueba de una historia.
- **Pedido de ejemplo**: *"Generá los casos de prueba de HU-001"*.
- **Usa**: skills `investigacion-contexto` y `tecnicas-de-diseno` (equivalencia, valores límite, tabla de decisión, estados, pairwise); `scripts/generar_casos.py` y `scripts/formatear_tablas.py`.
- **Entrega**: en `output/casos-de-prueba/manuales/`, `casos-HU-XXX.xlsx` + `casos-HU-XXX.md` + `casos-HU-XXX-cobertura.md` (cobertura por criterio, ambigüedades y preguntas). Los casos con información faltante quedan resaltados y con su `FI-XX`.
- **Tokens**: en cada uso.

### generador-casos-bdd
- **Cuándo**: para tener los escenarios en Gherkin (por ejemplo, para automatizarlos después).
- **Pedido de ejemplo**: *"Pasá HU-001 a BDD"*.
- **Usa**: skills `investigacion-contexto` y `tecnicas-de-diseno`; `scripts/formatear_tablas.py`.
- **Entrega**: en `output/casos-de-prueba/bdd/`, `HU-XXX-<tema>.feature` (keywords en inglés, contenido en español, cada escenario con `@CP-XXX`) + `HU-XXX-cobertura.md`.
- **Tokens**: en cada uso.

### generador-casos-api
- **Cuándo**: para diseñar las pruebas de una API desde su contrato.
- **Pedido de ejemplo**: *"Generá los casos de API de input/api/auth-endpoints.md"*.
- **Usa**: skills `investigacion-contexto` (si sale de una historia) y `tecnicas-de-diseno`; `scripts/formatear_tablas.py`.
- **Entrega**: `output/casos-api/casos-api-<tema>.md`: tabla resumen y detalle de cada caso con método, endpoint, headers, body y respuesta esperada (positivos, negativos, schema y autorización).
- **Tokens**: en cada uso. Para correrlos, `ejecutor-api`; para automatizarlos, `api-mapper`.

### generador-datos-prueba
- **Cuándo**: para tener datos realistas con los que probar.
- **Pedido de ejemplo**: *"Generá datos de prueba para el registro de HU-001, en CSV"*.
- **Usa**: skill `investigacion-contexto` (las reglas de cada campo); `scripts/formatear_tablas.py`.
- **Entrega**: `output/datos-de-prueba/datos-HU-XXX.md` o `.csv` con datos válidos, inválidos y de borde. No toca ninguna base (para eso, `verificador-datos`).
- **Tokens**: en cada uso.

### generador-reportes-bug
- **Cuándo**: cuando encontraste un error y tenés notas sueltas.
- **Pedido de ejemplo**: *"Armá el reporte de bug de input/bugs/observacion.md"* o pegale la observación.
- **Usa**: `plantillas/plantilla-reporte-bug.md`, `scripts/formatear_tablas.py`; la ficha de contexto si existe.
- **Entrega**: `output/reportes-bug/BUG-XXX.md` (el número siguiente al más alto) con historia, estado, severidad y prioridad justificadas; lo que falta queda marcado, nunca inventado.
- **Tokens**: en cada uso.

## Ejecución en vivo

Gastan tokens en cada corrida: sirven para casos sueltos. Lo que se repite conviene automatizarlo con los mappers.

### ejecutor-e2e
- **Cuándo**: para correr en el navegador casos o escenarios que no están automatizados.
- **Pedido de ejemplo**: *"Ejecutá CP-001 y CP-002 de HU-001 contra https://tu-app.com en headless"*.
- **Usa**: skill `ejecucion-e2e`; conectores `playwright` (headed, ves el navegador) o `playwright-headless`; `scripts/generar_reporte.py`.
- **Entrega**: en `output/ejecuciones/`, `reporte-HU-XXX-<fecha-hora>.html` + `_resultados-HU-XXX-<fecha-hora>.json`, y capturas en `evidencia/`.
- **Confirma**: el modo (headed o headless) si no lo dijiste. Las credenciales salen del `.env`.
- **Tokens**: en cada uso.

### ejecutor-api
- **Cuándo**: para correr una colección de Postman contra una API.
- **Pedido de ejemplo**: *"Corré la colección de input/api para HU-001"*.
- **Usa**: skill `ejecucion-api`; Newman, con `scripts/correr_newman.py` (token y URL del `.env`, en cualquier sistema).
- **Entrega**: en `output/ejecuciones/`, `reporte-HU-XXX-<fecha-hora>.html` + `_resultados-HU-XXX-<fecha-hora>.json`.
- **Tokens**: en cada uso.

### analista-seguridad
- **Cuándo**: para revisar la seguridad de una web propia o autorizada.
- **Pedido de ejemplo**: *"Revisá la seguridad de https://staging.tu-app.com para HU-001"*.
- **Usa**: OWASP ZAP en modo pasivo (Docker), `herramientas/zap/escanear.py` y `scripts/generar_informe_seguridad.py`.
- **Entrega**: en `output/seguridad/<HU>/<fecha>/`, `informe-seguridad.html` (hallazgos por riesgo, evidencia, cómo corregir, recomendaciones), `zap.json` y `analisis.json`.
- **Confirma**: la URL (tiene que estar en `SEGURIDAD_URLS_AUTORIZADAS`) y la duración del escaneo. Nunca escanea en modo activo.
- **Tokens**: en cada uso.

## Reportes

### generador-reporte-html
- **Cuándo**: para regenerar el reporte de una corrida desde su JSON (los ejecutores ya lo generan solos).
- **Pedido de ejemplo**: *"Rearmá el reporte de output/ejecuciones/_resultados-HU-001-20261010-1030.json"*.
- **Usa**: `scripts/generar_reporte.py`.
- **Entrega**: `output/ejecuciones/reporte-HU-XXX-<fecha-hora>.html`.
- **Tokens**: en cada uso (poco: el script hace el trabajo).

### generador-reporte-cierre
- **Cuándo**: al terminar una ronda o historia, para decidir si sale.
- **Pedido de ejemplo**: *"Armá el informe de cierre de HU-001"*.
- **Usa**: `scripts/recolectar_resultados.py` (junta ejecuciones en vivo, `npm test`, bugs, performance y seguridad) y `scripts/generar_informe_cierre.py`.
- **Entrega**: `output/informes-cierre/cierre-HU-XXX-<fecha>.html` con la recomendación (Apto / Apto con observaciones / No apto), resultados, bugs por severidad, alcance, riesgos y falta información.
- **Tokens**: en cada uso.

## Automatización con k0lmena

Escriben la automatización **una vez**; después corre sin agentes ni tokens con `npm test` o `npm run perf`.

### web-mapper
- **Cuándo**: para automatizar casos web.
- **Pedido de ejemplo**: *"Automatizá en k0lmena los casos de HU-001 contra https://tu-app.com"*.
- **Usa**: skills `automatizacion-k0lmena`, `ejecucion-e2e` e `investigacion-contexto`; conectores `playwright` / `playwright-headless`; k0lmena web (Playwright + Cucumber).
- **Entrega**: `herramientas/k0lmena/web/features/HU-XXX-<tema>.feature`, `steps/HU-XXX.steps.ts`, `locators/HU-XXX.locators.ts` y `output/mapeos/mapeo-HU-XXX-web.md`. Se corre con `npm run test:web`.
- **Confirma**: headed o headless, si no lo dijiste.
- **Tokens**: una vez.

### api-mapper
- **Cuándo**: para automatizar pruebas de API desde una colección de Postman o un Swagger/OpenAPI.
- **Pedido de ejemplo**: *"Automatizá los endpoints de /pet de https://petstore.swagger.io/v2/swagger.json"*.
- **Usa**: skills `automatizacion-k0lmena`, `investigacion-contexto` y `tecnicas-de-diseno`; k0lmena api (axios + Cucumber, steps genéricos).
- **Entrega**: `herramientas/k0lmena/api/features/*.feature` y `output/mapeos/mapeo-<HU o contrato>-api.md`. Se corre con `npm run test:api`.
- **Confirma**: el alcance y los métodos con efecto (POST, PUT, PATCH, DELETE) antes de llamarlos.
- **Tokens**: una vez.

### mobile-mapper
- **Cuándo**: para automatizar casos de una app Android o iOS.
- **Pedido de ejemplo**: *"Automatizá los casos de HU-005 en el emulador de Android"*.
- **Usa**: skills `automatizacion-k0lmena` e `investigacion-contexto`; conector `appium-mcp` (se activa con `npm run conector -- activar appium-mcp`); k0lmena mobile (WebdriverIO + Appium).
- **Entrega**: `herramientas/k0lmena/mobile/features`, `steps` y `locators` de la historia, y `output/mapeos/mapeo-HU-XXX-mobile.md`. Se corre con `npm run test:mobile`.
- **Tokens**: una vez.

### performance-mapper
- **Cuándo**: para pruebas de carga, estrés, resistencia o picos.
- **Pedido de ejemplo**: *"Quiero hacer una prueba de carga del login"*. Antes, Claude te guía paso a paso con el skill `guia-performance` (tipo de prueba, herramienta, usuarios, rampa, duración, umbrales).
- **Usa**: skills `guia-performance` y `automatizacion-k0lmena`; k6, Artillery + Playwright o JMeter; `scripts/generar_informe_performance.py`.
- **Entrega**: el script en `herramientas/k0lmena/performance/`, el plan y el informe (métricas, gráficos, hallazgos, recomendaciones) en `output/performance/HU-XXX/`. Se vuelve a correr con `npm run perf -- <script> <perfil>`.
- **Confirma**: cada corrida con carga.
- **Tokens**: una vez (más el análisis del informe).

### verificador-datos
- **Cuándo**: para revisar qué dejaron guardado las pruebas o verificar un dato en una base.
- **Pedido de ejemplo**: *"Verificá en la base si existe el usuario ana@test.com"* · *"Sumá al escenario de registro la verificación en la base"*.
- **Usa**: skill `automatizacion-k0lmena` (steps de base de datos); `npm run bd` (PostgreSQL, MySQL/MariaDB, SQL Server, MongoDB).
- **Entrega**: la respuesta en el chat (y `output/verificaciones-datos/` si lo pedís); los steps de BD en el `.feature` solo si los pedís.
- **Confirma**: toda escritura (y nunca escribe en producción).
- **Tokens**: en cada consulta; las verificaciones en los `.feature`, una vez.

## Gestión de pruebas

### gestor-pruebas
- **Cuándo**: para llevar los casos a la herramienta del equipo y armar los ciclos.
- **Pedido de ejemplo**: *"Subí los casos de HU-001 a Xray en la carpeta 'HU-001 Registro', vinculados a PROJ-12"*.
- **Usa**: `scripts/gestion/gestion.py` (Xray Cloud, Xray Server/DC, QTM4J y AIO Tests); para Azure Test Plans, el conector `azure-devops` y `scripts/gestion/para_azure_devops.py`.
- **Entrega**: carpetas, casos, vínculos con la historia y ciclos en la herramienta, y la trazabilidad `output/gestion/HU-XXX-<herramienta>.json`.
- **Confirma**: carpeta, historia y ciclo; la primera vez, una prueba en seco (`--dry-run`).
- **Tokens**: en cada uso (poco: el script hace el trabajo).

### publicador-resultados
- **Cuándo**: después de correr `npm test`, para cargar los resultados en el ciclo.
- **Pedido de ejemplo**: *"Subí los resultados de la última corrida web al ciclo PROJ-60"*.
- **Usa**: `scripts/gestion/gestion.py` (`extraer-resultados` y `publicar-resultados`).
- **Entrega**: el estado de cada caso en el ciclo, con el error y las evidencias (captura, GIF y video si falló). Publica una historia por vez para no mezclar casos. Azure DevOps todavía no.
- **Confirma**: el ciclo, si lo propuso él.
- **Tokens**: en cada uso (poco: el script hace el trabajo).

---

## Skills: el "cómo" que usan los agentes

Los skills se cargan solo cuando hacen falta.

| Skill                  | Qué enseña                                                                                                                             | Lo usan                                                                                                    |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| investigacion-contexto | Investigar la historia completa (comentarios, subtareas, épica, Confluence, Figma, contratos) y registrar la Falta información (FI-XX) | analista-historias, estratega-pruebas, generadores de casos y datos, web-mapper, api-mapper, mobile-mapper |
| tecnicas-de-diseno     | Equivalencia, valores límite, tabla de decisión, transición de estados y pairwise                                                      | generador-casos-manuales, generador-casos-bdd, generador-casos-api, api-mapper                             |
| ejecucion-e2e          | Ejecutar en el navegador con Playwright MCP: modos, snapshots, esperas y evidencia                                                     | ejecutor-e2e, web-mapper                                                                                   |
| ejecucion-api          | Correr colecciones con Newman: base_url, token, validaciones y resultados                                                              | ejecutor-api                                                                                               |
| automatizacion-k0lmena | Convenciones de k0lmena: features, steps, locators, tags, steps de BD y scripts de performance                                         | web-mapper, api-mapper, mobile-mapper, performance-mapper, verificador-datos                               |
| guia-performance       | Guía paso a paso para planificar una prueba de performance con la persona                                                              | la conversación principal (antes de performance-mapper) y performance-mapper                               |

## Herramientas y scripts: quién usa qué

| Herramienta o script                                         | Para qué                                                        | La usan                                                                      |
| ------------------------------------------------------------ | --------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| k0lmena (herramientas/k0lmena)                               | Automatización web, API, mobile y performance; corre sin tokens | web-mapper, api-mapper, mobile-mapper, performance-mapper, verificador-datos |
| Playwright MCP                                               | Navegador en vivo                                               | ejecutor-e2e, web-mapper                                                     |
| Newman (herramientas/newman)                                 | Colecciones de Postman                                          | ejecutor-api                                                                 |
| OWASP ZAP (herramientas/zap)                                 | Seguridad web pasiva                                            | analista-seguridad                                                           |
| k6 · Artillery · JMeter                                      | Performance                                                     | performance-mapper                                                           |
| scripts/generar_casos.py                                     | Planilla y Markdown de casos                                    | generador-casos-manuales                                                     |
| scripts/formatear_tablas.py                                  | Tablas alineadas en los .md                                     | casi todos los que escriben .md                                              |
| scripts/generar_plan.py                                      | Plan de pruebas HTML                                            | estratega-pruebas                                                            |
| scripts/generar_reporte.py                                   | Reporte HTML de una corrida                                     | ejecutor-e2e, ejecutor-api, generador-reporte-html                           |
| scripts/correr_newman.py                                     | Newman con el .env y su reporte                                 | ejecutor-api                                                                 |
| scripts/recolectar_resultados.py · generar_informe_cierre.py | Informe de cierre                                               | generador-reporte-cierre                                                     |
| scripts/generar_informe_performance.py                       | Informe de performance                                          | performance-mapper                                                           |
| scripts/generar_informe_seguridad.py                         | Informe de seguridad                                            | analista-seguridad                                                           |
| scripts/gestion/                                             | Xray, QTM4J y AIO Tests; conversión para Azure Test Plans       | gestor-pruebas, publicador-resultados                                        |
| scripts/doctor.py (npm run doctor)                           | Revisa el entorno y la configuración                            | vos, al instalar o cuando algo no anda                                       |

## Conectores: qué agentes los aprovechan

| Conector                         | Activo por defecto | Lo aprovechan                                                                                |
| -------------------------------- | ------------------ | -------------------------------------------------------------------------------------------- |
| playwright · playwright-headless | Sí                 | ejecutor-e2e, web-mapper                                                                     |
| atlassian (Jira y Confluence)    | Sí                 | todos los que investigan una historia (skill investigacion-contexto), generador-reportes-bug |
| azure-devops                     | No                 | los mismos que atlassian, si tu equipo usa Azure DevOps; gestor-pruebas (Azure Test Plans)   |
| figma · figma-desktop            | No                 | los que investigan una historia (textos, estados y validaciones del diseño), web-mapper      |
| qtm4j · qmetry · aio-tests       | No                 | consultas desde el chat (la carga de casos y resultados va por scripts/gestion)              |
| k0lmena-tmt                      | No                 | cargar y consultar casos en k0lmenaTMT                                                       |
| appium-mcp                       | No                 | mobile-mapper                                                                                |

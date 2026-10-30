# Referencia de K0lmenIA Light

Lo que no hace falta en cada conversación y por eso no está en el skill `k0lmenia:estandares`: la tabla de agentes con dónde guarda cada uno su salida, los comandos npm, qué hace cada script y herramienta, y los nombres de los archivos de salida. Claude lo lee cuando lo necesita; el skill `k0lmenia:estandares` queda corto y se gastan menos tokens en cada sesión.

---

## Agentes y dónde guardan la salida

```
+------------------------------+-----------------------------------------+------------------------------------+
| Agente                       | Para qué sirve                          | Guarda la salida en                |
+==============================+=========================================+====================================+
| `documentador-proyecto`      | Junta la documentación del proyecto:    | `input/documentacion/`             |
|                              | repositorio local (solo lectura),       |                                    |
|                              | historias de Jira con comentarios y     |                                    |
|                              | links, y mapa funcional de la web; base |                                    |
|                              | del proyecto, dossier por historia e    |                                    |
|                              | índice                                  |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
| `analista-historias`         | Analiza historias y criterios de        | `output/analisis-historias/`       |
|                              | aceptación; detecta ambigüedades y arma |                                    |
|                              | preguntas de refinamiento               |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
| `generador-casos-manuales`   | Casos de prueba en Excel (.xlsx) y      | `output/casos-de-prueba/manuales/` |
|                              | Markdown (.md), + informe de cobertura  |                                    |
|                              | (.md) con ambigüedades y preguntas para |                                    |
|                              | el PO                                   |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
| `generador-casos-bdd`        | Escenarios en Gherkin (keywords en      | `output/casos-de-prueba/bdd/`      |
|                              | inglés, contenido en español) + informe |                                    |
|                              | de cobertura por criterio (.md)         |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
| `revisor-casos`              | Revisa la calidad de casos existentes:  | `output/revision-casos/`           |
|                              | puntaje, problemas, duplicados y tiempo |                                    |
|                              | de ejecución manual                     |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
| `triador-bugs`               | Busca duplicados y regresiones (Jira y  | `output/triage/`                   |
|                              | bugs locales) y sugiere severidad,      |                                    |
|                              | componente, responsable e historia      |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
| `ejecutor-e2e`               | Ejecuta casos en el navegador con       | `output/ejecuciones/`              |
|                              | Playwright MCP, con evidencia           |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
| `ejecutor-api`               | Corre una colección de Postman, Bruno o | `output/ejecuciones/`              |
|                              | Insomnia con Newman                     |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
| `asistente-ejecucion-manual` | Cierra la sesión de ejecución manual    | `output/ejecucion-manual/`         |
|                              | acompañada: informe, resultados y       |                                    |
|                              | publicación con confirmación            |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
| `web-mapper`                 | Automatiza casos web en k0lmena         | `herramientas/k0lmena/web/` +      |
|                              | (`.feature`, steps y locators)          | `output/mapeos/`                   |
+------------------------------+-----------------------------------------+------------------------------------+
| `api-mapper`                 | Automatiza endpoints desde Postman o    | `herramientas/k0lmena/api/` +      |
|                              | Swagger/OpenAPI (REST, GraphQL o gRPC)  | `output/mapeos/`                   |
+------------------------------+-----------------------------------------+------------------------------------+
| `gestor-pruebas`             | Carpetas, casos, vínculos y ciclos en   | `output/gestion/`                  |
|                              | Xray (Cloud o Server/DC) o k0lmenaTMT,  |                                    |
|                              | vía `${CLAUDE_PLUGIN_ROOT}/scripts/gestion/`                  |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
| `publicador-resultados`      | Publica los resultados de `k0lmenia test` (o | Xray o k0lmenaTMT                  |
|                              | de un JUnit XML) en el ciclo, con       |                                    |
|                              | evidencias                              |                                    |
+------------------------------+-----------------------------------------+------------------------------------+
```

---

## Comandos npm

Todos los comandos de `package.json`, desde la raíz del repo (con el plugin, `k0lmenia <comando>`; `k0lmenia test` es `k0lmenia test`). Los que corren sin agentes ni tokens se pueden usar a mano.

```
+-----------------------------------+------------------------------------------+------------------------------------+
| Comando                           | Qué hace                                 | Lo usa                             |
+===================================+==========================================+====================================+
| `k0lmenia test`                        | Corre las suites de k0lmena (web y API   | —                                  |
|                                   | según lo automatizado), sin agentes ni   |                                    |
|                                   | tokens                                   |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia test:web`                | Solo la suite web (Playwright +          | —                                  |
|                                   | Cucumber)                                |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia test:api`                | Solo la suite de API (axios + Cucumber)  | —                                  |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia test:all`                | Todas las suites, una detrás de otra     | —                                  |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia report:web`              | Reporte HTML completo de la última       | —                                  |
|                                   | corrida web                              |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia report:api`              | Reporte HTML de la última corrida de API | —                                  |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia debug`                   | Corre Cucumber en modo depuración (paso  | —                                  |
|                                   | a paso, con el navegador visible)        |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia login`                   | Abre el navegador para loguearte a mano  | —                                  |
|                                   | (captcha, 2FA, SSO) y guarda la sesión   |                                    |
|                                   | en `.auth/`                              |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia record`                  | Graba un flujo en el navegador (codegen  | —                                  |
|                                   | de Playwright)                           |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia record:generator`        | Pasa una grabación a feature, steps y    | —                                  |
|                                   | locators de k0lmena                      |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia bd`                      | Verificación en base de datos sin        | —                                  |
|                                   | agente: `conexiones`, `esquema`,         |                                    |
|                                   | `existe`, `consultar` (solo lectura por  |                                    |
|                                   | defecto)                                 |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia mapa-funcional`          | Mapa funcional de la web: páginas,       | documentador-proyecto              |
|                                   | menús, formularios y mensajes, solo GET  |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia actualizar-conocimiento` | Actualiza la base de conocimiento        | skill base-conocimiento            |
|                                   | (aplicación y código) sin tokens;        |                                    |
|                                   | `--programar` la deja programada         |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia ejecucion-manual`        | Sesión de ejecución manual: `iniciar`,   | skill ejecucion-manual, asistente- |
|                                   | `siguiente`, `registrar`, `pausar`,      | ejecucion-manual                   |
|                                   | `retomar`, `estado` y `cerrar`           |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia ci`                      | Genera el pipeline de k0lmena para       | —                                  |
|                                   | GitHub Actions, GitLab CI, Jenkins o     |                                    |
|                                   | Azure Pipelines                          |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia portal`                  | Regenera el portal de informes           | —                                  |
|                                   | `output/index.html`                      |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia avisar`                  | Aviso a Slack o Teams por webhook;       | triador-bugs (a pedido)            |
|                                   | `--desde-cucumber` resume un `k0lmenia test`  |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia evals`                   | Evals de los agentes (gastan tokens):    | —                                  |
|                                   | `--listar`, `--correr`, `--solo-         |                                    |
|                                   | verificar`                               |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia novedades`               | Qué cambió desde la última vez (desde el | hook de inicio del plugin          |
|                                   | CHANGELOG); `--todas`, `--ultimas N`     |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia doctor`                  | Revisa el entorno y la configuración y   | skill empezar                      |
|                                   | dice qué falta                           |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia configurar`              | Asistente en español: tu app y tus       | —                                  |
|                                   | herramientas (crea el `.env` y activa    |                                    |
|                                   | los conectores)                          |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia conector`                | Lista, activa o desactiva conectores     | —                                  |
|                                   | MCP; `listar --html` deja el estado en   |                                    |
|                                   | `output/conectores/`                     |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia test:repo`               | Tests de Node del repo (`tests/node/`)   | —                                  |
+-----------------------------------+------------------------------------------+------------------------------------+
| `k0lmenia postinstall`             | Instala k0lmena en                       | —                                  |
|                                   | `herramientas/k0lmena` (corre solo con   |                                    |
|                                   | `npm install`)                           |                                    |
+-----------------------------------+------------------------------------------+------------------------------------+
```

---

## Scripts y herramientas

- `bin/k0lmenia` → el comando del plugin (Claude Code lo pone en el PATH): `init`, `actualizar` (el framework k0lmena del proyecto, sin tocar las pruebas del QA; lo que el QA modificó queda con un `.nuevo` al lado), `py <script>`, cualquier `npm run <x>` como `k0lmenia <x>` y `preparar` (el hook de inicio). Los datos van al proyecto (`K0LMENIA_PROYECTO`, la carpeta actual) y el código queda en el plugin (`K0LMENIA_CODIGO`).
- `${CLAUDE_PLUGIN_ROOT}/scripts/construir_plugin.py` → arma el plugin en `dist/plugin/` (agentes y skills con los comandos `k0lmenia`, `skills/estandares` desde el skill `k0lmenia:estandares`, hook de inicio, conectores y marketplace). Lo publica el workflow `plugin.yml` en la rama `plugin`.
- `${CLAUDE_PLUGIN_ROOT}/scripts/_proyecto.py` y `herramientas/k0lmena/tools/rutas.js` → la regla de carpetas: datos del proyecto (`output/`, `input/`, `.env`, `.auth/`, `herramientas/k0lmena`) en `K0LMENIA_PROYECTO` o, si no está, en el repo; el código, en el repo o en el plugin.
- `${CLAUDE_PLUGIN_ROOT}/scripts/py.js` → lanzador de los `npm run` de Python (`node ${CLAUDE_PLUGIN_ROOT}/scripts/py.js <script.py> [args]`): elige `python` o `python3` y devuelve el código de salida del script.
- `${CLAUDE_PLUGIN_ROOT}/scripts/configurar.js` → el asistente de `k0lmenia configurar`.
- `${CLAUDE_PLUGIN_ROOT}/scripts/_env.py`, `${CLAUDE_PLUGIN_ROOT}/scripts/_estilos_reporte.py`, `${CLAUDE_PLUGIN_ROOT}/scripts/_etiquetas.py`, `${CLAUDE_PLUGIN_ROOT}/scripts/_texto.py` y `${CLAUDE_PLUGIN_ROOT}/scripts/_programacion.py` → utilidades comunes: lectura del `.env`, estilos de los informes HTML, etiquetas de los casos, normalización de textos y husos horarios para programar tareas.
- `${CLAUDE_PLUGIN_ROOT}/scripts/generar_casos.py` → arma la planilla `.xlsx` y el `.md` de casos de prueba. Acepta `--limpiar` para borrar su JSON de entrada al terminar (cross-platform, sin depender de `rm`).
- `${CLAUDE_PLUGIN_ROOT}/scripts/formatear_tablas.py` → alinea las tablas de cualquier `.md` (lo usan todos los agentes que generan informes).
- `${CLAUDE_PLUGIN_ROOT}/scripts/estimacion.py` → **tiempo estimado de ejecución manual** de cada caso (fórmula en `${CLAUDE_PLUGIN_ROOT}/plantillas/estimacion-tiempos.md`): va en la planilla de casos, en la herramienta de gestión al subirlos y en la revisión.
- `${CLAUDE_PLUGIN_ROOT}/scripts/revisar_casos.py` y `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_revision.py` → revisión mecánica de casos y su informe HTML (`revisor-casos`).
- `${CLAUDE_PLUGIN_ROOT}/scripts/buscar_duplicados.py` → similitud entre bugs para el `triador-bugs` (duplicados, regresiones, relacionados).
- `${CLAUDE_PLUGIN_ROOT}/scripts/correr_newman.py` → corre una colección de Postman, Bruno o Insomnia con el token y la URL del `.env` (`--datos` para iterar con un CSV/JSON) y genera su reporte (`ejecutor-api`); un request sin `pm.test` queda Bloqueado ("Sin validaciones").
- `${CLAUDE_PLUGIN_ROOT}/scripts/convertir_coleccion.py` → convierte colecciones de Bruno (carpeta con `bruno.json`) e Insomnia (v4 `.json` / v5 `.yaml`) a Postman v2.1, con las advertencias de lo que no se pudo convertir (`correr_newman.py` lo usa solo).
- `${CLAUDE_PLUGIN_ROOT}/scripts/newman_a_resultados.py` → convierte la salida de Newman al formato de `generar_reporte.py` (`ejecutor-api`).
- `${CLAUDE_PLUGIN_ROOT}/scripts/generar_reporte.py` → reporte HTML de una ejecución en vivo desde `_resultados-*.json` (`ejecutor-e2e`, `ejecutor-api`).
- `${CLAUDE_PLUGIN_ROOT}/scripts/resumir_openapi.py` y `${CLAUDE_PLUGIN_ROOT}/scripts/resumir_graphql.py` → resumen de un Swagger 2.0 / OpenAPI 3 o de un schema GraphQL (introspección por URL, SDL o JSON) para el `api-mapper` y el `ejecutor-api`.
- `${CLAUDE_PLUGIN_ROOT}/scripts/indice_documentacion.py` → arma `input/documentacion/INDICE.md` (qué documentación hay, sus fuentes y si está vigente).
- `${CLAUDE_PLUGIN_ROOT}/scripts/cambios_documentacion.py` → documentación incremental: guarda en `input/documentacion/.estado.json` qué se documentó y, con lo que cambió, dice qué documentos rehacer y qué casos revisar (`cambios.md`, `cambios-historias.md`).
- `${CLAUDE_PLUGIN_ROOT}/scripts/actualizar_conocimiento.py` (`k0lmenia actualizar-conocimiento`) → actualización de la base de conocimiento para correr sola: aplicación (mapa funcional y sus cambios) y código sin tokens; con `--con-agente`, las historias con el `documentador-proyecto` por `claude -p` con tope de gasto; resumen en `output/conocimiento/` y aviso a Slack/Teams si algo cambió.
- `${CLAUDE_PLUGIN_ROOT}/scripts/ejecucion_manual.py` → sesión de ejecución manual paso a paso con pausa/retomar, cierre e informe (`asistente-ejecucion-manual`).
- `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_ejecucion_manual.py` → informe de la sesión de ejecución manual (`asistente-ejecucion-manual`).
- `${CLAUDE_PLUGIN_ROOT}/scripts/gestion/` → `gestion.py`, la integración con **Xray Cloud, Xray Server/DC y k0lmenaTMT** (carpetas, casos, vínculos, ciclos, `sincronizar-casos`, `extraer-resultados` y `publicar-resultados`). Detalle en `${CLAUDE_PLUGIN_ROOT}/scripts/gestion/README.md`.
- `${CLAUDE_PLUGIN_ROOT}/scripts/portal_informes.py` → `output/index.html`: tablero de inicio y todos los informes con su historial, con filtros por texto, herramienta, historia, estado y fechas. Antes de indexar arma el HTML de los artefactos (`generar_informe_artefacto.py`). Se regenera solo al terminar cada informe (`K0LMENIA_PORTAL=0` lo desactiva).
- `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_artefacto.py` → el HTML bilingüe de los artefactos sin informe propio: bugs, casos manuales, BDD, análisis, contexto, triage y mapeos. `--todo` actualiza los que cambiaron.
- `${CLAUDE_PLUGIN_ROOT}/scripts/_i18n.py` y `${CLAUDE_PLUGIN_ROOT}/scripts/i18n/en/*.json` → informes en español e inglés: `escribir_bilingue` escribe `es/informe.html`, `en/informe.html` y el acceso `informe.html` (abre el idioma elegido), `localizar` mezcla el bloque `en` del análisis y el diccionario traduce la interfaz.
- `${CLAUDE_PLUGIN_ROOT}/scripts/_historial.py` (y `herramientas/k0lmena/tools/historial/`) → guardan las últimas 5 corridas y arman la sección de evolución de los informes.
- `${CLAUDE_PLUGIN_ROOT}/scripts/avisar.py` → avisos a Slack y Teams por webhook (`SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL`); `--desde-cucumber` resume un `k0lmenia test`. Sin webhook no manda nada.
- `${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py` → revisa el entorno y la configuración por secciones (Python, Node y k0lmena, herramientas, fuentes, `.env`, integraciones, conectores y git), sin mostrar secretos. `--seccion env,integraciones`, `--rapido` (sin red) y `--json`.
- `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_entorno.py` → informe de la puesta en marcha (skill `empezar`) desde el JSON del doctor.
- `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_conectores.py` → estado de los conectores MCP en HTML (`output/conectores/estado.html`, ES/EN), sin valores del `.env`; lo corre `k0lmenia conector -- listar --html`.
- `${CLAUDE_PLUGIN_ROOT}/scripts/mcp/` → lanzadores de los conectores MCP que leen el `.env` (`playwright.js`, `k0lmena-tmt-headers.js`, `atlassian-headers.js`, `headers-env.js`, `conector.js` y `catalogo.json`).
- `${CLAUDE_PLUGIN_ROOT}/scripts/metricas_tokens.py` → **uso de tokens** de los agentes: lee las transcripciones de Claude Code del proyecto (solo conteos, nunca el texto), atribuye el uso a cada agente y estima el costo por agente, día y modelo.
- `${CLAUDE_PLUGIN_ROOT}/scripts/evaluar_agentes.py` → **evals de los agentes** (`evals/`): casos con trampas deliberadas que corren en un workspace aislado con `claude -p` y se verifican con chequeos determinísticos. **Gastan tokens** (tope por caso); `--solo-verificar` revisa salidas ya generadas.
- `${CLAUDE_PLUGIN_ROOT}/scripts/novedades.py` (`k0lmenia novedades`, `k0lmenia novedades`) → qué cambió desde la última vez que lo viste, a partir del CHANGELOG; `--todas`, `--ultimas N`; con `--contexto` lo usa el hook de inicio del plugin.
- `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_novedades.py` → informe HTML de las novedades (`output/novedades/`).
- `herramientas/k0lmena/` → el framework de automatización (web y API, steps de base de datos, sesión guardada, mapa funcional y grabación). Detalle en `herramientas/k0lmena/README.md`.
- `${CLAUDE_PLUGIN_ROOT}/herramientas/newman/` → Newman, el CLI de Postman: corre las colecciones de Postman, Bruno e Insomnia (`ejecutor-api`, con `${CLAUDE_PLUGIN_ROOT}/scripts/correr_newman.py`).
- `${CLAUDE_PLUGIN_ROOT}/herramientas/ci/` → plantillas de pipeline para correr k0lmena en GitHub, GitLab, Azure y Jenkins (`k0lmenia ci`).

---

## Nombres de archivos de salida (sugerencia)

- Documentación del proyecto (`documentador-proyecto`, no se versiona): `input/documentacion/` con `INDICE.md`, `proyecto/` (resumen, repositorio, reglas de negocio, mensajes, estados y permisos, mapa funcional, links), `api/` y `historias/<HU o key>/dossier.md`.
- Ficha de contexto: `output/contexto/contexto-HU-001.md` (fuentes consultadas, hallazgos y Falta información)
- Análisis de historia: `analisis-HU-001.md`
- Casos manuales: `casos-HU-001.xlsx` + `casos-HU-001.md` + `casos-HU-001-cobertura.md` (cada caso con su tiempo estimado de ejecución manual)
- Casos BDD: `HU-001-registro.feature` + `HU-001-cobertura.md`
- Reporte de bug: `BUG-001.md` (siguiendo `${CLAUDE_PLUGIN_ROOT}/plantillas/plantilla-reporte-bug.md`)
- Revisión de casos: `output/revision-casos/<HU o nombre>/` con `revision.json` e `informe-revision.html`.
- Triage de bugs: `output/triage/<bug o lote>/` con `candidatos.json`, `triage.json` y `triage.md`.
- Ejecución E2E (un reporte por corrida): `reporte-HU-001-<fecha-hora>.html` + `_resultados-HU-001-<fecha-hora>.json`, en `output/ejecuciones/`; evidencia en `output/ejecuciones/evidencia/<fecha-hora>-<id>.png`.
- Ejecución de API (`ejecutor-api`): `reporte-HU-001-<fecha-hora>.html` + `_resultados-HU-001-<fecha-hora>.json` en `output/ejecuciones/` (o `API` en lugar de la historia si la corrida no es de una).
- Ejecución manual: `output/ejecucion-manual/<HU>/` con `sesion.json`, `analisis.json` e `informe-ejecucion-manual.html`, y `output/ejecuciones/_resultados-<HU>-manual-<fecha>.json`.
- Mapeo a automatización: `herramientas/k0lmena/<web|api>/features/HU-001-<slug>.feature` + `steps/HU-001.steps.ts` + `locators/HU-001.locators.ts`, y el reporte `output/mapeos/mapeo-HU-001-<web|api>.md`.
- Gestión de pruebas: `output/gestion/HU-001-<herramienta>.json` (qué `CP-XXX` es qué key remota).
- **Historial**: la corrida de `k0lmenia test` guarda sus **últimas 5 corridas** en `herramientas/k0lmena/reports/<suite>/historial/` y cada informe trae la sección **Evolución de las corridas**.
- Portal de informes: `output/index.html`. Estado de los conectores: `output/conectores/estado.html`. Novedades: `output/novedades/`.
- Evals: `evals/resultados/<fecha>/` con `resultados.json` e `informe-evals.html` (no se versiona).
- Uso de tokens: `output/metricas-tokens/<nombre>/` con `metricas.json` e `informe-metricas.html`.

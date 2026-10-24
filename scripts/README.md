# Scripts

Utilidades en **Python** propias del repo: tareas mecánicas y repetibles que conviene que haga código y no el modelo (formato exacto, cálculos, generación de archivos).

Actuales:

- `generar_casos.py` — genera la planilla `.xlsx` y el `.md` de casos de prueba (ordenados por prioridad). Acepta `--limpiar`.
- `formatear_tablas.py` — normaliza las tablas de cualquier `.md` a un formato alineado.
- `indice_documentacion.py` — arma `input/documentacion/INDICE.md` a partir del encabezado de cada documento: tipo, fuentes, fecha y si conviene revisarlo (`documentador-proyecto`).
- `generar_reporte.py` — genera un reporte HTML autocontenido (dashboard) de una ejecución, a partir de un JSON de resultados.
- `newman_a_resultados.py` — convierte la salida de Newman (JSON) al formato que consume `generar_reporte.py`, para que las pruebas de API usen el mismo reporte.
- `generar_plan.py` — genera el **plan de pruebas** en HTML (dashboard oscuro) a partir de un JSON.
- `generar_informe_cierre.py` — genera el **informe de cierre** de una ronda en HTML (dashboard oscuro) a partir de un JSON.
- `generar_informe_performance.py` — genera el **informe de performance** en HTML (dashboard oscuro): toma las métricas de los resúmenes de `npm run perf` y suma el plan, los hallazgos y las recomendaciones del JSON del `performance-mapper`.
- `gestion/` — integración con **Xray (Cloud y Server/DC), QMetry para Jira (QTM4J), AIO Tests y Zephyr Scale**: carpetas, casos, vínculos con historias, ciclos y publicación de resultados. Incluye `para_azure_devops.py`, que convierte los casos (`.xlsx` / `.feature`) al formato de Azure Test Plans para el conector MCP `azure-devops`. La usan los agentes `gestor-pruebas` y `publicador-resultados` (los resultados se suben con sus evidencias).
- `mcp/` — lanzadores de los conectores MCP de `.mcp.json`: leen las credenciales del `.env` y se las pasan al server sin escribirlas en ningún archivo versionado; los servers de `npx` usan versiones fijas (`lanzar.js`). Ver `CONECTORES.md`.
- `correr_newman.py` — corre una colección de Postman con el token y la URL del `.env` (PowerShell, bash y zsh) y deja su reporte HTML (`ejecutor-api`).
- `recolectar_resultados.py` — junta los resultados de una historia (ejecuciones en vivo, `npm test`, bugs, performance y seguridad) para el informe de cierre.
- `generar_informe_seguridad.py` — genera el **informe de seguridad web** en HTML a partir del `zap.json` de OWASP ZAP y del análisis del agente.
- `generar_informe_exploratorio.py` — genera el **informe de pruebas exploratorias** en HTML a partir del `exploracion.json` de `npm run explorar` y del análisis del agente `explorador-web`.
- `generar_informe_accesibilidad.py` — genera el **informe de accesibilidad** en HTML a partir del `auditoria.json` de `npm run accesibilidad` y del análisis del agente `analista-accesibilidad`.
- `generar_informe_rendimiento.py` — genera el **informe de rendimiento web** en HTML a partir del `rendimiento.json` de `npm run rendimiento` (Lighthouse) y del análisis del agente `auditor-rendimiento-web`.
- `_estilos_reporte.py` — el sistema de diseño de todos los reportes HTML, con el estilo de k0lmena.com (barra lateral con índice, grilla bento, indicadores, gráficos y tablas con buscador y filtros); `fuentes/` tiene las tipografías de k0lmena.com (Saira, Inter y JetBrains Mono) que se incrustan en cada reporte.
- `analizar_fallos.py` + `generar_informe_fallos.py` — clasifican las fallas de `npm test`, comparan con reintentos para detectar inestables, rescatan la evidencia y arman el **informe de análisis de fallos** (`analista-fallos`).
- `analizar_cobertura.py` + `generar_informe_cobertura.py` — arman la **matriz de cobertura y trazabilidad** por historia (criterios, casos, automatización, gestión, resultados y bugs) y el informe con los huecos (`analista-cobertura`).
- `seleccionar_casos.py` + `generar_informe_seleccion.py` — cruzan un cambio (git, PR, Jira, notas de la release) con el inventario de casos y arman la **selección priorizada por riesgo** con el comando `npm test`, el CSV de lo manual y los cambios sin cobertura (`selector-casos-de-prueba`).
- `generar_informe_pixel_perfect.py` — genera el **informe de regresión visual** a partir del `pixel-perfect.json` de `npm run pixel-perfect`, con el comparador deslizable referencia/actual (`pixel-perfect`).
- `generar_informe_cross_browser.py` — genera el **informe cross-browser** a partir del `cross-browser.json` de `npm run cross-browser` (`cross-browser`).
- `generar_informe_reparacion.py` — genera el **informe de reparación de la automatización** a partir del `reparaciones.json` de `npm run reparar` (`reparador-automatizacion`).
- `generar_informe_correos.py` — genera el **informe de correos** a partir del `correos.json` de `npm run correos` (`verificador-correos`).
- `generar_informe_traductor.py` — genera el **informe de traducciones** a partir del `traductor.json` de `npm run traductor` (`analista-traductor`).
- `_historial.py` — guarda las **últimas 5 corridas** de cada herramienta en `historial/` y arma la sección "Evolución de las corridas" de los informes (nuevos, resueltos, indicadores en el tiempo).
- `estimacion.py` — **tiempo estimado de ejecución manual** de cada caso y de cada paso (fórmula en `plantillas/estimacion-tiempos.md`); también por consola: `python scripts/estimacion.py casos.xlsx`.
- `revisar_casos.py` + `generar_informe_revision.py` — revisión de la calidad de los casos (`revisor-casos`).
- `generar_charters.py` — hojas de sesión y el informe de las sesiones exploratorias (`generador-charters`).
- `generar_informe_ux.py` y `generar_informe_formularios.py` — los informes de `npm run ux` y `npm run formularios` (`evaluador-ux`, `probador-formularios`).
- `analizar_logs.py` + `generar_informe_logs.py` — logs agrupados y cruzados con la corrida (`analista-logs`).
- `generar_informe_permisos.py` y `generar_informe_resiliencia.py` — los informes de `npm run permisos` y `npm run resiliencia` (`probador-permisos`, `probador-resiliencia`).
- `buscar_duplicados.py` — similitud entre bugs: duplicados, posibles regresiones y relacionados (`triador-bugs`).
- `tablero_calidad.py` — tablero de calidad por sprint o release (`tablero-calidad`).
- `portal_informes.py` — `output/index.html` con el último informe de cada herramienta; `_estilos_reporte.page()` lo programa para regenerarse al terminar cada informe (`K0LMENIA_PORTAL=0` lo desactiva).
- `avisar.py` — avisos a Slack y Teams por webhook del `.env`; `--desde-cucumber` resume un `npm test`.
- `generar_informe_monitoreo.py` — informe de `npm run monitorear` (monitoreo sintético) con la disponibilidad y los tiempos.
- `cambios_documentacion.py` — documentación incremental del `documentador-proyecto`: estado de lo documentado y qué documentos y casos afecta un cambio.
- `convertir_coleccion.py` — Bruno e Insomnia a Postman v2.1 (lo usa `correr_newman.py`); `resumir_graphql.py` — resumen de un schema GraphQL (introspección, SDL o JSON); `resumir_openapi.py` — resumen de un Swagger/OpenAPI para automatizarlo (base URL, autenticación, endpoints, bodies y status).
- `evaluar_agentes.py` — evals de los agentes (`evals/`): preparar el workspace aislado, correr con `claude -p`, verificar y armar el informe con regresiones.
- `metricas_tokens.py` — uso de tokens y costo estimado por agente a partir de las transcripciones de Claude Code (solo conteos).
- `generar_onboarding.py` — plan de onboarding del `guia-onboarding` (HTML con checklist y Markdown).
- `doctor.py` — revisa el entorno (Python, Node, k0lmena, Playwright, Newman, Java, Docker, `.env` y conectores) y dice qué falta. También: `npm run doctor`.
- `_env.py` — lectura del `.env` de la raíz con las mismas reglas que k0lmena y `scripts/mcp/leer-env.js` (la usan los scripts de Python).
- `_estilos_reporte.py` — sistema de diseño de todos los reportes HTML (plan, ejecución, cierre, performance y seguridad): modo oscuro, paleta categórica y de estado validadas para daltonismo y contraste, indicadores, pastillas con ícono, tooltips y gráficos (dona, barras, barras apiladas, columnas agrupadas y líneas con crosshair, siempre con un solo eje). Los reportes de k0lmena usan los mismos colores (`herramientas/k0lmena/reports/tema-oscuro.js` y el reporte de performance).

Necesitan **Python 3** (ver `requirements.txt`).

> No confundir con `herramientas/` (herramientas externas de testing como JMeter, que los agentes ejecutan por CLI) ni con `.mcp.json` (conexiones a sistemas externos por MCP, como Jira o Xray).

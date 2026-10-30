# Scripts

Utilidades en **Python** propias del repo: tareas mecánicas y repetibles que conviene que haga código y no el modelo (formato exacto, cálculos, generación de archivos).

Actuales:

- `generar_casos.py` — genera la planilla `.xlsx` y el `.md` de casos de prueba (ordenados por prioridad). Acepta `--limpiar`.
- `formatear_tablas.py` — normaliza las tablas de cualquier `.md` a un formato alineado.
- `estimacion.py` — **tiempo estimado de ejecución manual** de cada caso y de cada paso (fórmula en `plantillas/estimacion-tiempos.md`); también por consola: `python scripts/estimacion.py casos.xlsx`.
- `revisar_casos.py` + `generar_informe_revision.py` — revisión de la calidad de los casos (`revisor-casos`).
- `buscar_duplicados.py` — similitud entre bugs: duplicados, posibles regresiones y relacionados (`triador-bugs`).
- `indice_documentacion.py` — arma `input/documentacion/INDICE.md` a partir del encabezado de cada documento: tipo, fuentes, fecha y si conviene revisarlo (`documentador-proyecto`).
- `cambios_documentacion.py` — documentación incremental del `documentador-proyecto`: estado de lo documentado y qué documentos y casos afecta un cambio.
- `actualizar_conocimiento.py` — actualiza la base de conocimiento del proyecto (`input/documentacion/`) cuando cambian historias, código o aplicación; pensado para correr programado (skill `base-conocimiento`, `npm run actualizar-conocimiento`).
- `generar_reporte.py` — genera un reporte HTML autocontenido (dashboard) de una ejecución, a partir de un JSON de resultados.
- `newman_a_resultados.py` — convierte la salida de Newman (JSON) al formato que consume `generar_reporte.py`, para que las pruebas de API usen el mismo reporte.
- `correr_newman.py` — corre una colección de Postman con el token y la URL del `.env` (PowerShell, bash y zsh) y deja su reporte HTML (`ejecutor-api`).
- `convertir_coleccion.py` — Bruno e Insomnia a Postman v2.1 (lo usa `correr_newman.py`); `resumir_graphql.py` — resumen de un schema GraphQL (introspección, SDL o JSON); `resumir_openapi.py` — resumen de un Swagger/OpenAPI para automatizarlo (base URL, autenticación, endpoints, bodies y status).
- `ejecucion_manual.py` — sesión de ejecución manual (casos desde .xlsx/.json/.feature), paso a paso, con pausa y retomar, tiempos sin pausas, redacción de secretos, inconsistencias y, al cerrar, _resultados para generar_reporte.py y el informe (`ejecucion-manual`, `asistente-ejecucion-manual`).
- `generar_informe_ejecucion_manual.py` — informe HTML (ES/EN) de una sesión de ejecución manual: avance, resultados, tiempo real contra estimado, por prioridad, inconsistencias, pasos fallidos, bugs, pendientes y publicación.
- `gestion/` — integración con **Xray (Cloud y Server/DC) y k0lmenaTMT**: carpetas, casos, vínculos con historias, ciclos y publicación de resultados. La usan los agentes `gestor-pruebas` y `publicador-resultados` (los resultados se suben con sus evidencias).
- `mcp/` — lanzadores de los conectores MCP de `.mcp.json`: leen las credenciales del `.env` y se las pasan al server sin escribirlas en ningún archivo versionado; los servers de `npx` usan versiones fijas (`lanzar.js`). Ver `CONECTORES.md`.
- `generar_informe_artefacto.py` — HTML (ES + EN) de los artefactos sin informe propio (casos, BDD, bugs, análisis de historias, fichas de contexto, triage) para el portal.
- `portal_informes.py` — `output/index.html` con el último informe de cada herramienta; `_estilos_reporte.page()` lo programa para regenerarse al terminar cada informe (`K0LMENIA_PORTAL=0` lo desactiva).
- `avisar.py` — avisos a Slack y Teams por webhook del `.env`; `--desde-cucumber` resume un `npm test`.
- `generar_informe_conectores.py` — estado de los conectores MCP en HTML: incluidos, activos, listos para activar y con datos faltantes, con cómo activar cada uno; nunca muestra valores del .env (`npm run conector -- listar --html`).
- `generar_informe_entorno.py` — informe HTML de la puesta en marcha desde la salida JSON del doctor (`--correr` lo corre solo): qué está listo, qué falta y cómo resolverlo (skill `empezar`).
- `doctor.py` — revisa el entorno (Python, Node, k0lmena, Playwright, Newman, `.env` y conectores) y dice qué falta. También: `npm run doctor`.
- `construir_plugin.py` — arma K0lmenIA Light como plugin de Claude Code (lo publica el workflow `plugin.yml` en la rama `plugin`).
- `novedades.py` — novedades desde la última vez (`npm run novedades`, `k0lmenia novedades`): lee el CHANGELOG, guarda la marca de lo visto (en el plugin, en CLAUDE_PLUGIN_DATA) y con `--contexto` le da al hook de inicio del plugin el resumen corto para que Claude lo cuente.
- `generar_informe_novedades.py` — informe HTML de las novedades (cantidad, cambios por entrada, línea de tiempo y detalle).
- `evaluar_agentes.py` — evals de los agentes (`evals/`): preparar el workspace aislado, correr con `claude -p`, verificar y armar el informe con regresiones.
- `metricas_tokens.py` — uso de tokens y costo estimado por agente a partir de las transcripciones de Claude Code (solo conteos).
- `i18n/` — los diccionarios de la versión en inglés de los informes (`en/*.json`); los usa `_i18n.py`.
- `_historial.py` — guarda las **últimas 5 corridas** en `historial/` y arma la sección "Evolución de las corridas" de los informes (nuevos, resueltos, indicadores en el tiempo).
- `_env.py` — lectura del `.env` de la raíz con las mismas reglas que k0lmena y `scripts/mcp/leer-env.js` (la usan los scripts de Python).
- `_estilos_reporte.py` — sistema de diseño de todos los reportes HTML: modo oscuro, paleta categórica y de estado validadas para daltonismo y contraste, indicadores, pastillas con ícono, tooltips y gráficos; `fuentes/` tiene las tipografías (Saira, Inter y JetBrains Mono) que se incrustan en cada reporte.
- `_i18n.py` — informes en español e inglés (`escribir_bilingue`, `localizar` y el diccionario de la interfaz).
- `_etiquetas.py`, `_texto.py`, `_programacion.py` y `_proyecto.py` — etiquetas de los casos, normalización de textos, husos horarios para programar tareas y la regla de carpetas (proyecto o plugin).
- `py.js` y `configurar.js` — lanzador de los `npm run` de Python y el asistente de `npm run configurar`.

Necesitan **Python 3** (ver `requirements.txt`).

> No confundir con `herramientas/` (herramientas externas de testing como Newman, que los agentes ejecutan por CLI) ni con `.mcp.json` (conexiones a sistemas externos por MCP, como Jira).

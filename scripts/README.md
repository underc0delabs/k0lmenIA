# Scripts

Utilidades en **Python** propias del repo: tareas mecánicas y repetibles que conviene que haga código y no el modelo (formato exacto, cálculos, generación de archivos).

Actuales:

- `generar_casos.py` — genera la planilla `.xlsx` y el `.md` de casos de prueba (ordenados por prioridad). Acepta `--limpiar`.
- `formatear_tablas.py` — normaliza las tablas de cualquier `.md` a un formato alineado.
- `generar_reporte.py` — genera un reporte HTML autocontenido (dashboard) de una ejecución, a partir de un JSON de resultados.
- `newman_a_resultados.py` — convierte la salida de Newman (JSON) al formato que consume `generar_reporte.py`, para que las pruebas de API usen el mismo reporte.
- `generar_plan.py` — genera el **plan de pruebas** en HTML (dashboard oscuro) a partir de un JSON.
- `generar_informe_cierre.py` — genera el **informe de cierre** de una ronda en HTML (dashboard oscuro) a partir de un JSON.
- `generar_informe_performance.py` — genera el **informe de performance** en HTML (dashboard oscuro): toma las métricas de los resúmenes de `npm run perf` y suma el plan, los hallazgos y las recomendaciones del JSON del `performance-mapper`.
- `gestion/` — integración con **Xray (Cloud y Server/DC), QMetry para Jira (QTM4J) y AIO Tests**: carpetas, casos, vínculos con historias, ciclos y publicación de resultados. Incluye `para_azure_devops.py`, que convierte los casos (`.xlsx` / `.feature`) al formato de Azure Test Plans para el conector MCP `azure-devops`
- `mcp/` — lanzadores de los conectores MCP de `.mcp.json`: leen las credenciales del `.env` y se las pasan al server sin escribirlas en ningún archivo versionado (ver `CONECTORES.md`) con evidencias. La usan los agentes `gestor-pruebas` y `publicador-resultados`. Ver `gestion/README.md`.
- `_estilos_reporte.py` — sistema de diseño de todos los reportes HTML (plan, ejecución, cierre, performance y seguridad): modo oscuro, paleta categórica y de estado validadas para daltonismo y contraste, indicadores, pastillas con ícono, tooltips y gráficos (dona, barras, barras apiladas, columnas agrupadas y líneas con crosshair, siempre con un solo eje). Los reportes de k0lmena usan los mismos colores (`herramientas/k0lmena/reports/tema-oscuro.js` y el reporte de performance).

Necesitan **Python 3** (ver `requirements.txt`).

> No confundir con `herramientas/` (herramientas externas de testing como JMeter, que los agentes ejecutan por CLI) ni con `.mcp.json` (conexiones a sistemas externos por MCP, como Jira o Xray).

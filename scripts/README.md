# Scripts

Utilidades en **Python** propias del repo: tareas mecánicas y repetibles que conviene que haga código y no el modelo (formato exacto, cálculos, generación de archivos).

Actuales:

- `generar_casos.py` — genera la planilla `.xlsx` y el `.md` de casos de prueba (ordenados por prioridad). Acepta `--limpiar`.
- `formatear_tablas.py` — normaliza las tablas de cualquier `.md` a un formato alineado.
- `generar_reporte.py` — genera un reporte HTML autocontenido (dashboard) de una ejecución, a partir de un JSON de resultados.
- `newman_a_resultados.py` — convierte la salida de Newman (JSON) al formato que consume `generar_reporte.py`, para que las pruebas de API usen el mismo reporte.
- `generar_plan.py` — genera el **plan de pruebas** en HTML (dashboard oscuro) a partir de un JSON.
- `generar_informe_cierre.py` — genera el **informe de cierre** de una ronda en HTML (dashboard oscuro) a partir de un JSON.
- `_estilos_reporte.py` — módulo común con la paleta, el CSS y los gráficos del modo oscuro (lo usan `generar_plan.py` y `generar_informe_cierre.py`); centraliza el tema para que todos los reportes se vean igual.

Necesitan **Python 3** (ver `requirements.txt`).

> No confundir con `herramientas/` (herramientas externas de testing como JMeter, que los agentes ejecutan por CLI) ni con `.mcp.json` (conexiones a sistemas externos por MCP, como Jira o Xray).

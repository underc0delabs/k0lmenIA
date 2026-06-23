# Agentes QARMY — Contexto del proyecto

Este repositorio es un conjunto de **agentes de QA para Claude Code**, pensados para que profesionales de testing manual aceleren sus tareas del día a día: analizar historias, escribir casos de prueba (manuales, BDD y de API), generar datos de prueba, redactar reportes de bug, ejecutar pruebas end-to-end en el navegador y generar reportes de resultados en HTML.

Todo el trabajo y todas las salidas son **en español**.

---

## Cómo funciona el flujo

1. **`input/`** — Acá se ponen los insumos: historias de usuario, documentación del producto, contratos de API y observaciones de errores.
2. **Agentes** (`.claude/agents/`) — Cada agente es un especialista. Claude Code los invoca solo según lo que pida la persona; también se les puede pedir explícitamente.
3. **`plantillas/` y `scripts/`** — Definen el **formato de salida**. El **reporte de bug** sigue `plantillas/plantilla-reporte-bug.md`. Los **casos de prueba** se generan como planilla **Excel** (`.xlsx`) con `scripts/generar_casos.py` (referencia: `plantillas/plantilla-casos-prueba.xlsx`) y un **informe de cobertura** en Markdown (referencia: `plantillas/plantilla-cobertura.md`).
4. **`output/`** — Acá se guardan los artefactos generados, ordenados por tipo.

```
input/ → [ agente ] → output/
              ↑
   plantillas/ + scripts/  (formato)
```

---

## Agentes disponibles

| Agente | Para qué sirve | Guarda la salida en |
|--------|----------------|---------------------|
| `analista-historias` | Analiza historias y criterios de aceptación; detecta ambigüedades y arma preguntas de refinamiento | `output/analisis-historias/` |
| `generador-casos-manuales` | Casos de prueba en Excel (.xlsx) y Markdown (.md), + informe de cobertura (.md) con ambigüedades y preguntas para el PO | `output/casos-de-prueba/manuales/` |
| `generador-casos-bdd` | Escenarios en Gherkin (keywords en inglés, contenido en español) + informe de cobertura por criterio (.md) | `output/casos-de-prueba/bdd/` |
| `generador-reportes-bug` | Reportes de bug, siguiendo `plantillas/plantilla-reporte-bug.md` | `output/reportes-bug/` |
| `generador-datos-prueba` | Datos de prueba realistas (Markdown o CSV) | `output/datos-de-prueba/` |
| `generador-casos-api` | Casos de prueba de API (tabla resumen + detalle con JSON) a partir de contratos/endpoints | `output/casos-api/` |
| `ejecutor-e2e` | Ejecuta los casos/escenarios pedidos en el navegador con Playwright MCP (pregunta headed o headless), reporta con evidencia y genera el reporte HTML de la corrida | `output/ejecuciones/` |
| `generador-reporte-html` | Arma el reporte HTML (dashboard en modo oscuro, con indicadores y gráficos) de una ejecución, a partir de sus resultados | `output/ejecuciones/` |

---

## Estándares de QA del proyecto

Estos principios aplican a **todos** los agentes:

- **No inventar.** Si falta información para hacer bien la tarea (un paso, un dato, una regla de negocio, un resultado esperado), el agente lo **marca y lo pregunta**; nunca rellena con suposiciones disfrazadas de hechos. Es preferible un artefacto con huecos señalados que uno completo pero inventado.
- **Respetar los formatos.** Los campos, su orden y sus valores permitidos los define la plantilla (o el script), no el agente.
- **Trazabilidad.** Todo artefacto referencia la historia (`HU-XXX`) o el contrato del que sale.
- **Cobertura pensada.** Los casos contemplan escenarios positivos, negativos, de borde y validaciones de campos, no solo el camino feliz.
- **Claridad.** Títulos descriptivos, pasos accionables y sin ambigüedad, lenguaje claro y profesional.

## Convenciones de IDs

- Historias de usuario: `HU-001`, `HU-002`, …
- Criterios de aceptación: `CA1`, `CA2`, … (dentro de cada historia)
- Casos de prueba manuales: `CP-001`, `CP-002`, …
- Casos de prueba de API: `CP-API-001`, `CP-API-002`, …
- Bugs: `BUG-001`, `BUG-002`, …

## Escalas

- **Severidad / Criticidad:** `Crítica` · `Alta` · `Media` · `Baja`
- **Prioridad:** `Crítica` · `Alta` · `Media` · `Baja`
- **Estado de un caso:** `N/A` · `Pendiente` · `En ejecución` · `Aprobado` · `Fallido` · `Bloqueado`

## Formato de tablas en los archivos `.md`

**Toda tabla de un `.md` debe verse alineada y con el mismo formato.** Para garantizarlo sin depender de armar cada tabla a mano:

1. Escribí las tablas como **Markdown normal** (`| col | col |`), en cualquier sección.
2. **Al terminar de escribir el `.md`, normalizá el archivo una vez:**

```bash
python scripts/formatear_tablas.py <archivo.md>
```

Convierte **todas** las tablas Markdown del archivo a tablas ASCII alineadas (dentro de bloques de código), sin importar la sección ni cuánto texto tengan. No toca lo que ya está en bloques de código, así que es seguro correrlo más de una vez.

Reglas (valen para **todos** los agentes y cualquier sección, incluidas las que armes sobre la marcha):

- Nunca dejes una tabla en Markdown crudo en el entregable: siempre pasá el `.md` por `formatear_tablas.py`.
- **Sin emojis dentro de las celdas** (descuadran el ASCII): usá texto (`Cubierto`, `Sí`, `No`, `Parcial`).
- Lo que es **código** (un body o response JSON) va en bloques ```` ```json ```` aparte; el normalizador no lo toca.
- Excepción: el `.md` de **casos de prueba** lo arma `scripts/generar_casos.py` (ya sale alineado, con el mismo estilo).

## Requisitos del entorno

**Python 3** lo usan los scripts que dan formato a las salidas. Instalan `openpyxl`/`tabulate` solo si faltan; o se instalan con `pip install -r requirements.txt`. Si falta una librería y no se puede instalar, el script avisa con un mensaje claro (no falla en silencio).

- `scripts/generar_casos.py` → arma la planilla `.xlsx` y el `.md` de casos de prueba. Acepta `--limpiar` para borrar su JSON de entrada al terminar (cross-platform, sin depender de `rm`).
- `scripts/formatear_tablas.py` → alinea las tablas de cualquier `.md` (lo usan todos los agentes que generan informes).

---

## Nombres de archivos de salida (sugerencia)

- Análisis de historia: `analisis-HU-001.md`
- Casos manuales: `casos-HU-001.xlsx` + `casos-HU-001.md` + `casos-HU-001-cobertura.md`
- Casos BDD: `HU-001-registro.feature` + `HU-001-cobertura.md`
- Reporte de bug: `BUG-001.md`
- Datos de prueba: `datos-HU-001.md` (o `.csv`)
- Casos de API: `casos-api-auth.md`
- Ejecución E2E (un reporte por corrida): `reporte-HU-001-<fecha-hora>.html` (dashboard, modo oscuro) + `_resultados-HU-001-<fecha-hora>.json` (datos), en `output/ejecuciones/`; evidencia en `output/ejecuciones/evidencia/`. Cada reporte cubre solo los casos de esa ejecución.

---

## Arquitectura (cómo crece el repo)

El repo se apoya en estas piezas: **agentes** (`.claude/agents/`, el quién), **skills** (`.claude/skills/`, el cómo, cargados on-demand), **MCP** (`.mcp.json`, conexiones a sistemas externos — un solo archivo que escala a muchas conexiones: Jira, Xray, Playwright…), **herramientas** (`herramientas/`, herramientas externas de testing como JMeter, una subcarpeta por herramienta) y **scripts** (`scripts/`, utilidades internas determinísticas). El detalle y cómo extender cada una está en `ARQUITECTURA.md`.

Secretos (tokens, credenciales): van en variables de entorno con `${VARIABLE}` o en un `.env` local (gitignored), **nunca** commiteados; hay una plantilla `.env.example`. El `.mcp.json` está versionado y trae la conexión a Playwright (sin secretos); `.mcp.json.example` es la plantilla para sumar conexiones con token (Jira, Xray…).

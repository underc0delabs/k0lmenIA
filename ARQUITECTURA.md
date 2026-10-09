# Arquitectura del repositorio

Este repo está pensado para crecer de forma ordenada. Cubre tanto **planificar y generar** artefactos de QA (plan de pruebas, análisis de historias, casos manuales, BDD, casos de API, datos de prueba, reportes de bug) como **ejecutar** pruebas (end-to-end en el navegador y de API) y **reportar** los resultados (reporte de cada corrida e informe de cierre de la ronda). Para que cada capacidad nueva entre sin romper lo que ya funciona, todo se organiza en piezas, cada una con su lugar.

## Las piezas

### Agentes — el *quién* (`.claude/agents/`)

Cada agente es un subagente de Claude Code con su rol, su proceso y sus reglas. Es a quién se le delega una tarea entera. Hoy hay once. La clave de cada uno está en el `description` de su frontmatter: es lo que usa Claude Code para saber cuándo invocarlo.

### Skills — el *cómo* (`.claude/skills/`)

Conocimiento empaquetado que Claude Code carga **on-demand** (solo cuando hace falta). Encapsula el "cómo" de una capacidad reutilizable, para que varios agentes lo aprovechen sin repetir instrucciones. Cada skill es una carpeta con un `SKILL.md` (ver `.claude/skills/README.md`).

> Lo que un agente usa para **actuar** viene en tres formas: conexiones MCP, herramientas externas y scripts internos.

### MCP — conexiones a sistemas externos (`.mcp.json`)

Para tocar sistemas de afuera (Jira, Xray, un navegador…), un agente usa un **server MCP**. **Es un solo archivo, pero escala a todas las conexiones que quieras**: `.mcp.json` es un *registro* de servers, donde agregás una entrada por cada integración.

```json
{
  "mcpServers": {
    "atlassian":  { "type": "http", "url": "https://mcp.atlassian.com/v2/mcp" },
    "qtm4j":      { "type": "stdio", "command": "node", "args": ["scripts/mcp/con-env.js", "qtm4j", "--requeridas", "QTM4J_API_KEY", "--", "npx", "-y", "@smartbear/mcp@latest"], "env": { "MCP_CLIENTS": "QTM4J" } },
    "playwright": { "type": "stdio", "command": "npx", "args": ["-y", "@playwright/mcp@latest"] }
  }
}
```

En este repo, `.mcp.json` viene **versionado con todos los conectores** (Playwright, Jira y Confluence, Figma, QMetry, AIO Tests, k0lmenaTMT, Azure DevOps, Appium) y **ninguno lleva secretos**: los que necesitan token arrancan con un script de `scripts/mcp/` que lo lee del `.env`. Solo Playwright viene habilitado (headed y headless), así la ejecución E2E funciona out-of-the-box; cada persona habilita los demás en su `.claude/settings.local.json`. El paso a paso de cada conector está en [`CONECTORES.md`](CONECTORES.md).

> **Regla de oro de los secretos:** tokens y credenciales van en el `.env` local (gitignored) o en variables de entorno, **nunca** con el valor real en `.mcp.json` ni en otro archivo versionado. Hay una plantilla `.env.example` con los nombres de variable; se copia a `.env` y se completan los valores reales. Si se commitea un secreto, rotalo de inmediato.

### Herramientas — herramientas externas de testing (`herramientas/`)

Herramientas que el agente **ejecuta** por línea de comandos, con sus plantillas y configuraciones. Hay dos integradas: **Newman** (la CLI de Postman), que usa `ejecutor-api` para correr pruebas de API, y **k0lmena**, el framework de automatización (web, api, mobile y performance con Artillery y k6, más verificaciones en bases de datos PostgreSQL, MySQL / MariaDB, SQL Server y MongoDB). En k0lmena los agentes *mapper* escriben la automatización una sola vez y después corre con `npm test`, **sin agentes ni tokens**. Cada herramienta va en su **propia subcarpeta**, así escala: sumar una herramienta = sumar una carpeta (ver `herramientas/README.md`).

### Scripts — utilidades internas (`scripts/`)

Código Python propio del repo para tareas mecánicas (generar la planilla `.xlsx`, normalizar tablas). Incluye `scripts/gestion/`, la integración con Xray, QMetry (QTM4J) y AIO Tests sobre sus APIs oficiales: los agentes deciden qué hacer y el script lo ejecuta, sin depender de servers MCP. Las utilidades internas nuevas viven acá.

## En resumen

- **Agente** = a quién le pido la tarea.
- **Skill** = el conocimiento de cómo hacerla.
- **MCP** = conexiones a sistemas externos (un archivo, muchas conexiones: Jira, Confluence, Figma, QMetry, AIO Tests, Azure DevOps, Playwright…).
- **Herramientas** = herramientas externas que se ejecutan por CLI (Newman y k0lmena).
- **Script** = utilidad interna determinística.

Hoy ya están en uso las cinco piezas: **agentes**, **skills** (investigación de contexto, técnicas de diseño, ejecución E2E y de API, automatización con k0lmena), la **conexión MCP** con Playwright (para el navegador), las **herramientas** Newman (para API) y k0lmena (automatización sin tokens) y los **scripts** de formato, reporte y conversión. Sumar capacidades nuevas es repetir el patrón: un agente nuevo en `.claude/agents/`, un skill en `.claude/skills/`, una conexión en `.mcp.json`, una herramienta en `herramientas/` o un script en `scripts/`.

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
    "atlassian":  { "type": "http", "url": "https://mcp.atlassian.com/v1/mcp" },
    "qtm4j":      { "type": "stdio", "command": "npx", "args": ["-y", "@smartbear/mcp@latest"], "env": { "QTM4J_API_KEY": "${QTM4J_API_KEY}" } },
    "playwright": { "type": "stdio", "command": "npx", "args": ["-y", "@playwright/mcp@latest"] }
  }
}
```

En este repo, `.mcp.json` ya viene **versionado** con la conexión a **Playwright** (headed y headless), que no lleva secretos, así la ejecución E2E funciona out-of-the-box. El `.mcp.json.example` es la **plantilla** para sumar conexiones que sí piden token (Jira, Xray, QMetry, AIO Tests…): copiás la entrada que necesites a tu `.mcp.json` y el token va por `${VARIABLE}` (ver la regla de secretos). El paso a paso de cada conector de gestión de pruebas está en [`CONECTORES.md`](CONECTORES.md).

> **Regla de oro de los secretos:** tokens y credenciales van como variables de entorno con `${VARIABLE}` (en tu entorno o un `.env` local, gitignored), **nunca** con el valor real en el archivo. Hay una plantilla `.env.example` con los nombres de variable; se copia a `.env` y se completan los valores reales. Si se commitea un secreto, rotalo de inmediato.

### Herramientas — herramientas externas de testing (`herramientas/`)

Herramientas que el agente **ejecuta** por línea de comandos, con sus plantillas y configuraciones. Hay dos integradas: **Newman** (la CLI de Postman), que usa `ejecutor-api` para correr pruebas de API, y **k0lmena**, el framework de automatización (web, api, mobile y performance con Artillery y k6). En k0lmena los agentes *mapper* escriben la automatización una sola vez y después corre con `npm test`, **sin agentes ni tokens**. Cada herramienta va en su **propia subcarpeta**, así escala: sumar una herramienta = sumar una carpeta (ver `herramientas/README.md`).

### Scripts — utilidades internas (`scripts/`)

Código Python propio del repo para tareas mecánicas (generar la planilla `.xlsx`, normalizar tablas). Las utilidades internas nuevas viven acá.

## En resumen

- **Agente** = a quién le pido la tarea.
- **Skill** = el conocimiento de cómo hacerla.
- **MCP** = conexiones a sistemas externos (un archivo, muchas conexiones: Jira, Xray, QMetry, AIO Tests, Playwright…).
- **Herramientas** = herramientas externas que se ejecutan por CLI (Newman y k0lmena).
- **Script** = utilidad interna determinística.

Hoy ya están en uso las cinco piezas: **agentes**, **skills** (técnicas de diseño, ejecución E2E y de API, automatización con k0lmena), la **conexión MCP** con Playwright (para el navegador), las **herramientas** Newman (para API) y k0lmena (automatización sin tokens) y los **scripts** de formato, reporte y conversión. Sumar capacidades nuevas es repetir el patrón: un agente nuevo en `.claude/agents/`, un skill en `.claude/skills/`, una conexión en `.mcp.json`, una herramienta en `herramientas/` o un script en `scripts/`.

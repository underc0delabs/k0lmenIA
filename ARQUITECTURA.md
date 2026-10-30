# Arquitectura del repositorio

Este repo está pensado para crecer de forma ordenada. Cubre tanto **planificar y generar** artefactos de QA (análisis de historias, casos manuales y BDD, revisión de casos, triage de bugs) como **ejecutar** pruebas (end-to-end en el navegador, de API y manuales acompañadas), **automatizar** con k0lmena y **reportar** los resultados en la herramienta de gestión. Para que cada capacidad nueva entre sin romper lo que ya funciona, todo se organiza en piezas, cada una con su lugar.

## Las piezas

![Cómo se relacionan las piezas](docs/assets/img/relaciones.png)

El agente es el centro: carga **skills** (el cómo), respeta las **plantillas** (el formato), ejecuta **scripts** (lo mecánico) y **herramientas** (por terminal), y usa **conectores MCP** para hablar con sistemas externos; lee de `input/` y deja todo en `output/`. El diagrama se edita en `docs/diagramas/relaciones.html` y se regenera con `node docs/generar.js`.

### Agentes — el *quién* (`.claude/agents/`)

Cada agente es un subagente de Claude Code con su rol, su proceso y sus reglas. Es a quién se le delega una tarea entera. Hoy hay 13 agentes, agrupados en análisis y diseño (documentación del proyecto, análisis de historias, casos manuales y BDD, revisión de casos y triage de bugs), ejecución en vivo (E2E, API y el cierre de la ejecución manual acompañada), automatización con k0lmena (web y API) y gestión (casos, ciclos y resultados en Xray o k0lmenaTMT). El catálogo, con los skills, herramientas y conectores de cada uno, está en `AGENTES.md`. Como corren como subagentes, no pueden hacerle preguntas a la persona a mitad del trabajo: si les falta un dato, terminan devolviendo "Necesito que confirmes" y la conversación principal pregunta y los continúa. La clave de cada uno está en el `description` de su frontmatter: es lo que usa Claude Code para saber cuándo invocarlo.

### Skills — el *cómo* (`.claude/skills/`)

Conocimiento empaquetado que Claude Code carga **on-demand** (solo cuando hace falta). Encapsula el "cómo" de una capacidad reutilizable, para que varios agentes lo aprovechen sin repetir instrucciones. Cada skill es una carpeta con un `SKILL.md` (ver `.claude/skills/README.md`); hoy hay 13 skills. Algunos los usa la **conversación principal** y no un agente, porque necesitan preguntarle cosas a la persona: `empezar` (la bienvenida y puesta en marcha de quien recién instala el plugin), `guia-pruebas` (qué probar y con qué), `ejecucion-manual` (guiar los casos manuales paso a paso) y `base-conocimiento` (documentar todo el proyecto y mantenerlo al día).

### Base de conocimiento — lo que se sabe del proyecto (`input/documentacion/`)

Todo lo que el `documentador-proyecto` investiga (repositorio, un dossier por historia, mapa funcional de la app con sus locators) queda como Markdown con un encabezado (título, tipo, fuentes, fecha y **confiabilidad**) y un índice, `INDICE.md`. Los agentes que analizan, escriben casos o automatizan lo leen primero con el skill `investigacion-contexto`, así no vuelven a investigar lo mismo. Es **incremental**: `.estado.json` guarda qué se documentó (commit del código, fecha y huella de cada historia) y la actualización lee solo lo nuevo o lo que cambió; `npm run actualizar-conocimiento` la puede correr programada. No se versiona (es del proyecto que se prueba, no de K0lmenIA).

> Lo que un agente usa para **actuar** viene en tres formas: conexiones MCP, herramientas externas y scripts internos.

### MCP — conexiones a sistemas externos (`.mcp.json`)

Para tocar sistemas de afuera (Jira, un navegador…), un agente usa un **server MCP**. **Es un solo archivo, pero escala a todas las conexiones que quieras**: `.mcp.json` es un *registro* de servers, donde agregás una entrada por cada integración.

```json
{
  "mcpServers": {
    "atlassian":  { "type": "http", "url": "https://mcp.atlassian.com/v2/mcp" },
    "playwright": { "type": "stdio", "command": "node", "args": ["scripts/mcp/playwright.js"] }
  }
}
```

En este repo, `.mcp.json` viene **versionado con los conectores que todos usan** (Playwright headed y headless, y Atlassian para Jira), todos habilitados en `.claude/settings.json`: así Claude Code arranca directo, sin pedir aprobaciones. El de k0lmenaTMT está en `scripts/mcp/catalogo.json` y cada persona lo activa con `npm run conector -- activar k0lmena-tmt`, que lo registra con alcance local de Claude Code (solo para esa persona, sin tocar archivos versionados). **Ninguno lleva secretos**: los que necesitan token arrancan con un script de `scripts/mcp/` que lo lee del `.env` (`headers-env.js` arma headers Bearer o Basic desde el `.env`; `lanzar.js` fija las versiones de npm).

> **Regla de oro de los secretos:** tokens y credenciales van en el `.env` local (gitignored) o en variables de entorno, **nunca** con el valor real en `.mcp.json` ni en otro archivo versionado. Hay una plantilla `.env.example` con los nombres de variable; se copia a `.env` y se completan los valores reales. Si se commitea un secreto, rotalo de inmediato.

### Herramientas — herramientas externas de testing (`herramientas/`)

Herramientas que el agente **ejecuta** por línea de comandos, con sus plantillas y configuraciones. Hay tres integradas: **Newman** (la CLI de Postman), que usa `ejecutor-api` para correr pruebas de API; **k0lmena**, el framework de automatización (web y api, más verificaciones en bases de datos PostgreSQL, MySQL / MariaDB, SQL Server y MongoDB y el mapa funcional `npm run mapa-funcional` que usa el `documentador-proyecto`); y **ci** (plantillas de pipeline para correr k0lmena en GitHub Actions, GitLab CI, Jenkins o Azure Pipelines). En k0lmena los agentes *mapper* escriben la automatización una sola vez y después corre con `npm test`, **sin agentes ni tokens**. Cada herramienta va en su **propia subcarpeta**, así escala: sumar una herramienta = sumar una carpeta (ver `herramientas/README.md`).

### Scripts — utilidades internas (`scripts/`)

Código Python propio del repo para tareas mecánicas (generar la planilla `.xlsx`, normalizar tablas, armar los informes). Incluye `scripts/gestion/`, la integración con Xray (Cloud y Server/DC) y k0lmenaTMT sobre sus APIs oficiales: los agentes deciden qué hacer y el script lo ejecuta. Las utilidades internas nuevas viven acá.

### Evals — la calidad de los agentes (`evals/`)

Los tests (`tests/`) cubren los scripts; los **evals** miden la calidad de lo que generan los agentes. Cada caso trae insumos con trampas deliberadas y chequeos determinísticos versionados; `scripts/evaluar_agentes.py` los corre en un workspace aislado con `claude -p` y arma un informe con las regresiones contra la corrida anterior. Al cambiar un agente o un skill, se corren antes y después.

## En resumen

- **Agente** = a quién le pido la tarea.
- **Skill** = el conocimiento de cómo hacerla.
- **MCP** = conexiones a sistemas externos (un archivo, muchas conexiones: Jira, k0lmenaTMT, Playwright…).
- **Herramientas** = herramientas externas que se ejecutan por CLI (Newman, k0lmena y ci).
- **Script** = utilidad interna determinística.
- **Base de conocimiento** = lo que se sabe del proyecto, en `input/documentacion/`, para que los agentes no investiguen dos veces.

Hoy están en uso todas las piezas: **agentes**, **skills**, las **conexiones MCP** (navegador, Jira y k0lmenaTMT), las **herramientas** (con k0lmena para automatizar sin tokens), los **scripts** de formato, reporte y conversión, la **base de conocimiento** y los **evals**. Sumar capacidades nuevas es repetir el patrón: un agente nuevo en `.claude/agents/`, un skill en `.claude/skills/`, una conexión en `.mcp.json`, una herramienta en `herramientas/` o un script en `scripts/`.

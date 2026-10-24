# Arquitectura del repositorio

Este repo está pensado para crecer de forma ordenada. Cubre tanto **planificar y generar** artefactos de QA (plan de pruebas, análisis de historias, casos manuales, BDD, casos de API, datos de prueba, reportes de bug) como **ejecutar** pruebas (end-to-end en el navegador y de API) y **reportar** los resultados (reporte de cada corrida e informe de cierre de la ronda). Para que cada capacidad nueva entre sin romper lo que ya funciona, todo se organiza en piezas, cada una con su lugar.

## Las piezas

![Cómo se relacionan las piezas](docs/assets/img/relaciones.png)

El agente es el centro: carga **skills** (el cómo), respeta las **plantillas** (el formato), ejecuta **scripts** (lo mecánico) y **herramientas** (por terminal), y usa **conectores MCP** para hablar con sistemas externos; lee de `input/` y deja todo en `output/`. El diagrama se edita en `docs/diagramas/relaciones.html` y se regenera con `node docs/generar.js`.

### Agentes — el *quién* (`.claude/agents/`)

Cada agente es un subagente de Claude Code con su rol, su proceso y sus reglas. Es a quién se le delega una tarea entera. Hoy hay 79 agentes, agrupados en documentación del proyecto (investigación de todo el proyecto, documentación de historias, código y aplicación, manuales de usuario), análisis y diseño (con el triage de bugs, las consultas sobre el producto y el onboarding), ejecución en vivo (incluidas las pruebas exploratorias, de accesibilidad, de rendimiento web, de permisos por rol, de resiliencia, la regresión visual, el cross-browser, los correos, las traducciones y las plataformas: e-commerce, SAP, Salesforce, mobile, desktop, IA, mensajería, SOAP, APIs en Scalar y más), reportes (con el análisis de fallos, la cobertura y el tablero de calidad), automatización con k0lmena (con la reparación de locators), la selección de casos por cambio, seguridad (dinámica, dependencias, código seguro y revisión de código) y gestión (el catálogo, con los skills, herramientas y conectores de cada uno, está en `AGENTES.md`). Como corren como subagentes, no pueden hacerle preguntas a la persona a mitad del trabajo: si les falta un dato, terminan devolviendo "Necesito que confirmes" y la conversación principal pregunta y los continúa. La clave de cada uno está en el `description` de su frontmatter: es lo que usa Claude Code para saber cuándo invocarlo.

### Skills — el *cómo* (`.claude/skills/`)

Conocimiento empaquetado que Claude Code carga **on-demand** (solo cuando hace falta). Encapsula el "cómo" de una capacidad reutilizable, para que varios agentes lo aprovechen sin repetir instrucciones. Cada skill es una carpeta con un `SKILL.md` (ver `.claude/skills/README.md`); hoy hay 48 skills. Algunos los usa la **conversación principal** y no un agente, porque necesitan preguntarle cosas a la persona: `guia-pruebas` (qué probar y con qué), `guia-performance` (el plan de carga) y `base-conocimiento` (investigar y documentar todo el proyecto y mantenerlo al día).

### Base de conocimiento — lo que se sabe del proyecto (`input/documentacion/`)

Todo lo que los agentes investigan queda como Markdown con un encabezado (título, tipo, fuentes, fecha y **confiabilidad**) y un índice, `INDICE.md`: el `documentador-proyecto` (repositorio, un dossier por historia, mapa funcional de la app con sus locators), el `investigador-proyecto` (lo relevado de tableros y wiki) y el `redactor-manual` (cómo se usa la app, verificado). Los agentes que analizan, escriben casos o automatizan lo leen primero con el skill `investigacion-contexto`, así no vuelven a investigar lo mismo. Es **incremental**: `.estado.json` guarda qué se documentó (commit del código, fecha y huella de cada historia) y la actualización lee solo lo nuevo o lo que cambió; `npm run actualizar-conocimiento` la puede correr programada. No se versiona (es del proyecto que se prueba, no de k0lmenIA).

> Lo que un agente usa para **actuar** viene en tres formas: conexiones MCP, herramientas externas y scripts internos.

### MCP — conexiones a sistemas externos (`.mcp.json`)

Para tocar sistemas de afuera (Jira, Xray, un navegador…), un agente usa un **server MCP**. **Es un solo archivo, pero escala a todas las conexiones que quieras**: `.mcp.json` es un *registro* de servers, donde agregás una entrada por cada integración.

```json
{
  "mcpServers": {
    "atlassian":  { "type": "http", "url": "https://mcp.atlassian.com/v2/mcp" },
    "qtm4j":      { "type": "stdio", "command": "node", "args": ["scripts/mcp/con-env.js", "qtm4j", "--requeridas", "QTM4J_API_KEY", "--", "@smartbear/mcp"], "env": { "MCP_CLIENTS": "QTM4J" } },
    "playwright": { "type": "stdio", "command": "node", "args": ["scripts/mcp/playwright.js"] }
  }
}
```

En este repo, `.mcp.json` viene **versionado con los conectores que todos usan** (Playwright headed y headless, y Atlassian para Jira y Confluence), todos habilitados en `.claude/settings.json`: así Claude Code arranca directo, sin pedir aprobaciones. Los opcionales (Azure DevOps, Figma, GitHub, GitLab, Linear, ClickUp, monday.com, Asana, Trello, Notion, YouTrack, Shortcut, QMetry, AIO Tests, k0lmenaTMT, Appium, Salesforce, Scalar) están en `scripts/mcp/catalogo.json` y cada persona los activa con `npm run conector -- activar <nombre>`, que los registra con alcance local de Claude Code (solo para esa persona, sin tocar archivos versionados). **Ninguno lleva secretos**: los que necesitan token arrancan con un script de `scripts/mcp/` que lo lee del `.env`.

> **Regla de oro de los secretos:** tokens y credenciales van en el `.env` local (gitignored) o en variables de entorno, **nunca** con el valor real en `.mcp.json` ni en otro archivo versionado. Hay una plantilla `.env.example` con los nombres de variable; se copia a `.env` y se completan los valores reales. Si se commitea un secreto, rotalo de inmediato.

### Herramientas — herramientas externas de testing (`herramientas/`)

Herramientas que el agente **ejecuta** por línea de comandos, con sus plantillas y configuraciones. Hay cuatro integradas: **Mailpit**, el buzón de prueba que usa `verificador-correos` para atrapar los mails de la app; **Newman** (la CLI de Postman), que usa `ejecutor-api` para correr pruebas de API; **OWASP ZAP**, que usa `analista-seguridad` para el escaneo de seguridad pasivo; y **k0lmena**, el framework de automatización (web, api, mobile y performance con k6, Artillery y JMeter, más verificaciones en bases de datos PostgreSQL, MySQL / MariaDB, SQL Server y MongoDB, el recorrido exploratorio `npm run explorar` que usa `explorador-web` la auditoría de accesibilidad `npm run accesibilidad` que usa `analista-accesibilidad` la de rendimiento `npm run rendimiento` (Lighthouse) que usa `auditor-rendimiento-web`, la regresión visual `npm run pixel-perfect` que usa `pixel-perfect`, las pruebas en Chromium, Firefox y WebKit `npm run cross-browser` que usa `cross-browser` la reparación de locators `npm run reparar` que usa `reparador-automatizacion`, la revisión de correos `npm run correos` que usa `verificador-correos` y la de idiomas `npm run traductor` que usa `analista-traductor`). A esas se suman **streaming** (ffprobe/ffmpeg y ONVIF) para los agentes de video y cámaras, **Salesforce** (la CLI `sf`) que usa `probador-salesforce` para relevar una org en solo lectura, y las de cada familia: **ecommerce**, **sap**, **desktop**, **seguridad** (dependencias y SAST), **codigo** (revisión de código de repos y PR/MR), **manual** (manuales de usuario en Markdown, HTML y Word), **scalar** (APIs en Scalar), **mensajeria**, **soap**, **seo**, **resiliencia**, **observabilidad**, **documentos**, **contenido** y **mutacion**. Todas guardan sus últimas 5 corridas en `historial/` para compararlas. En k0lmena los agentes *mapper* escriben la automatización una sola vez y después corre con `npm test`, **sin agentes ni tokens**. Cada herramienta va en su **propia subcarpeta**, así escala: sumar una herramienta = sumar una carpeta (ver `herramientas/README.md`).

### Scripts — utilidades internas (`scripts/`)

Código Python propio del repo para tareas mecánicas (generar la planilla `.xlsx`, normalizar tablas). Incluye `scripts/gestion/`, la integración con Xray, QMetry (QTM4J) y AIO Tests sobre sus APIs oficiales: los agentes deciden qué hacer y el script lo ejecuta, sin depender de servers MCP. Las utilidades internas nuevas viven acá.

### Evals — la calidad de los agentes (`evals/`)

Los tests (`tests/`) cubren los scripts; los **evals** miden la calidad de lo que generan los agentes. Cada caso trae insumos con trampas deliberadas y chequeos determinísticos versionados; `scripts/evaluar_agentes.py` los corre en un workspace aislado con `claude -p` y arma un informe con las regresiones contra la corrida anterior. Al cambiar un agente o un skill, se corren antes y después.

## En resumen

- **Agente** = a quién le pido la tarea.
- **Skill** = el conocimiento de cómo hacerla.
- **MCP** = conexiones a sistemas externos (un archivo, muchas conexiones: Jira, Confluence, Figma, QMetry, AIO Tests, Azure DevOps, Scalar, Playwright…).
- **Herramientas** = herramientas externas que se ejecutan por CLI (Newman, k0lmena, ZAP y una carpeta por familia).
- **Script** = utilidad interna determinística.
- **Base de conocimiento** = lo que se sabe del proyecto, en `input/documentacion/`, para que los agentes no investiguen dos veces.

Hoy están en uso todas las piezas: **agentes**, **skills**, las **conexiones MCP** (navegador, gestión de proyectos y de pruebas, repositorios, diseños, Scalar), las **herramientas** (con k0lmena para automatizar sin tokens), los **scripts** de formato, reporte y conversión, la **base de conocimiento** y los **evals**. Sumar capacidades nuevas es repetir el patrón: un agente nuevo en `.claude/agents/`, un skill en `.claude/skills/`, una conexión en `.mcp.json`, una herramienta en `herramientas/` o un script en `scripts/`.

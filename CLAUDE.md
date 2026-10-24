# k0lmenIA — Contexto del proyecto

Este repositorio es un conjunto de **agentes de QA para Claude Code**, pensados para que profesionales de testing manual aceleren sus tareas del día a día: planificar la estrategia de pruebas, analizar historias, escribir casos de prueba (manuales, BDD y de API), generar datos de prueba, redactar reportes de bug, ejecutar pruebas end-to-end en el navegador, ejecutar pruebas de API, generar reportes de resultados en HTML y armar el informe de cierre de la ronda.

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

### Preguntas y confirmaciones (conversación principal ↔ agentes)

Los agentes corren como subagentes y **no pueden hacerle preguntas a la persona a mitad del trabajo**. Por eso:

- **Antes de invocar un agente**, la conversación principal resuelve con la persona lo que el agente seguro va a necesitar y no está en el pedido. Por ejemplo: headed o headless (`ejecutor-e2e`, `web-mapper`), qué historia si hay varias, la URL o el ambiente, y la key de la historia en Jira o Azure DevOps para la gestión.
- **Si un agente termina devolviendo "Necesito que confirmes"**, la conversación principal le hace esas preguntas a la persona (con opciones, la recomendada primero) y **continúa al mismo agente** con las respuestas; no empieza uno nuevo.
- Las acciones con efecto (escribir en una base, crear o modificar datos en Jira/Xray/QMetry/AIO/Zephyr/Azure DevOps, correr carga, métodos con efecto) se confirman **con la persona** y se le pasan al agente explícitamente; nunca se asumen.
- **Performance**: la planificación guiada la hace la conversación principal con el skill `guia-performance`; el `performance-mapper` trabaja con el plan confirmado.
- **Manual de usuario** (`redactor-manual`): la conversación principal resuelve antes el alcance (funcionalidad, módulo o toda la plataforma; crear o actualizar), la URL del ambiente y el login (la persona corre `npm run login` e inicia sesión a mano, con `SESION=si` en el `.env`; nadie escribe credenciales). El agente devuelve sus dudas como `REVIEW-NNN` en "Necesito que confirmes"; las respuestas y la **aprobación explícita** de la versión final ("aprobado", no "seguí") se le pasan al mismo agente.
- **Investigar o documentar todo el proyecto** (y mantenerlo al día): la conversación principal sigue el skill `base-conocimiento`: encadena `investigador-proyecto` (profundidad `total`), `documentador-proyecto` (modo barrido y la app de punta a punta con sesión) y `redactor-manual`, y la rutina de actualización cuando cambian los requerimientos (historias, código y aplicación → qué rehacer y qué casos revisar).
- **No sabés qué probar o con qué agente/skill**: la conversación principal usa el skill `guia-pruebas` para preguntarte paso a paso y recomendar o ejecutar el agente/skill que corresponde (también es un skill de la conversación principal, porque los subagentes no pueden preguntar).
- **Correr pruebas ya automatizadas**: es `npm test` en k0lmena (sin agentes ni tokens). Los ejecutores en vivo (`ejecutor-e2e`, `ejecutor-api`) son para casos sueltos que no vale la pena automatizar.

---

## Agentes disponibles

Hay 79 agentes. Claude Code elige el que corresponde por el `description` de cada uno (`.claude/agents/`), así que acá va solo el índice por familia. Qué hace cada uno, cómo pedírselo, qué usa, dónde guarda la salida y qué confirma está en `AGENTES.md`; la tabla de salidas y la lista de scripts, en `REFERENCIA.md`.

- **Análisis y diseño**: `documentador-proyecto`, `analista-historias`, `estratega-pruebas`, `generador-casos-manuales`, `generador-casos-bdd`, `generador-casos-api`, `generador-datos-prueba`, `selector-casos-de-prueba`, `revisor-casos`, `generador-charters`, `generador-reportes-bug`, `triador-bugs`, `consultor-proyecto`, `guia-onboarding`, `investigador-proyecto`, `redactor-manual`.
- **Ejecución en vivo**: `ejecutor-e2e`, `ejecutor-api`, `analista-seguridad`, `pentester-web`, `probador-salesforce`, `probador-billeteras`, `probador-shopify`, `probador-wordpress`, `probador-prestashop`, `probador-vtex`, `probador-sap`, `probador-desktop`, `probador-mobile`, `probador-ia`, `probador-mensajeria`, `probador-soap`, `probador-scalar`, `probador-contratos`, `probador-dynamics`, `probador-blockchain`, `probador-ivr`, `probador-juegos`, `probador-pos`, `probador-busqueda`, `probador-documentos`, `probador-streaming`, `probador-onvif`, `calidad-imagen`, `verificador-grabaciones`, `analista-seguridad-camaras`, `explorador-web`, `analista-accesibilidad`, `auditor-rendimiento-web`, `pixel-perfect`, `cross-browser`, `verificador-correos`, `analista-traductor`, `evaluador-ux`, `probador-formularios`, `probador-permisos`, `probador-resiliencia`.
- **Análisis (solo lectura)**: `analista-dependencias`, `analista-codigo-seguro`, `revisor-codigo`, `analista-seo`, `probador-datos`, `analista-observabilidad`, `revisor-contenido`, `analista-mutacion`.
- **Reportes**: `generador-reporte-html`, `generador-reporte-cierre`, `analista-cobertura`, `tablero-calidad`.
- **Automatización (k0lmena)**: `web-mapper`, `api-mapper`, `mobile-mapper`, `performance-mapper`, `verificador-datos`, `analista-fallos`, `reparador-automatizacion`, `analista-logs`.
- **Gestión**: `gestor-pruebas`, `publicador-resultados`.

---

## Estándares de QA del proyecto

Estos principios aplican a **todos** los agentes:

- **No inventar.** Si falta información para hacer bien la tarea (un paso, un dato, una regla de negocio, un resultado esperado), el agente lo **marca y lo pregunta**; nunca rellena con suposiciones disfrazadas de hechos. Es preferible un artefacto con huecos señalados que uno completo pero inventado.
- **Investigar antes de suponer.** Antes de analizar, planificar, escribir casos o automatizar una historia, se revisa su contexto completo con el skill `investigacion-contexto`: primero la documentación del proyecto de `input/documentacion/` (la arma el `documentador-proyecto`: índice, dossier de la historia, reglas del código, mensajes, mapa funcional; la completan el `investigador-proyecto` con lo relevado de los tableros y la wiki, y el `redactor-manual` con cómo se usa la app, verificado; cada documento declara su confiabilidad: `confirmado`, `borrador`, `investigacion` o `sin-confirmar`), y después la historia de Jira con **todos** sus comentarios, subtareas, épica e issues vinculados, las páginas de Confluence y los diseños de Figma relacionados, contratos y `input/`. El resultado queda en una ficha reutilizable `output/contexto/contexto-HU-XXX.md`.
- **Marcar lo que falta.** Lo que no aparece en ninguna fuente se registra como **Falta información** con un ID por historia (`FI-01`, `FI-02`, …) y viaja con ese ID a todos los artefactos: casos (resaltados, etiqueta `@falta-info`, hoja *Falta información*), `.feature` (`@falta-info @FI-01`), coberturas, mapeos, reportes de ejecución, informe de cierre y lo que se publica en Xray/QMetry/AIO. En los `analisis.json` y `_resultados-*.json` de los informes HTML va como `falta_informacion: [{"id": "FI-01", "que_falta": "…", "pregunta": "…"}]`.
- **Informes en español e inglés.** Cada informe HTML sale en dos archivos (`informe.html` e `informe.en.html`, con una banderita para pasar de uno al otro). El agente escribe en el JSON del informe un bloque `"en"` con la traducción de sus textos (mismas claves e IDs); la interfaz la traduce el script (`scripts/_i18n.py`, diccionarios en `scripts/i18n/en/`).
- **Anti-bots: frenar, no esquivar.** Si la app frena al navegador con un desafío o un captcha, el caso queda **Bloqueado** (no Fallido) y se sugiere la excepción para QA o `npm run login` (guía en `herramientas/k0lmena/tools/navegador/README.md`). Nunca se intenta resolver el captcha ni disfrazar el navegador.
- **Respetar los formatos.** Los campos, su orden y sus valores permitidos los define la plantilla (o el script), no el agente.
- **Trazabilidad.** Todo artefacto referencia la historia (`HU-XXX`) o el contrato del que sale.
- **Cobertura pensada.** Los casos contemplan escenarios positivos, negativos, de borde y validaciones de campos, no solo el camino feliz.
- **Claridad.** Títulos descriptivos, pasos accionables y sin ambigüedad, lenguaje claro y profesional.

## Convenciones de IDs

- Historias de usuario: `HU-001`, `HU-002`, …
- Criterios de aceptación: `CA1`, `CA2`, … (dentro de cada historia)
- Casos de prueba manuales: `CP-001`, `CP-002`, … (numeración **por historia**; si la historia ya tiene casos —manuales, BDD, automatización o gestión—, se conservan sus IDs y los nuevos siguen desde el último). Los escenarios BDD usan la **misma** numeración como tag `@CP-XXX`, y la `Feature` lleva `@HU-XXX`: el par `@HU` + `@CP` identifica cada caso en la automatización, la gestión y los resultados. Un `Scenario Outline` es un solo caso (un solo `@CP`).
- Casos de prueba de API: `CP-API-001`, `CP-API-002`, … (numeración por historia, o por contrato si no hay historia)
- Bugs: `BUG-001`, `BUG-002`, …
- Falta información: `FI-01`, `FI-02`, … (por historia; tags `@falta-info @FI-01`)
- Historia en nombres de archivo: el `HU-XXX` si existe (`contexto-HU-001.md`, `casos-HU-001…`, campo **Historia** de los bugs); si la historia solo tiene key de la herramienta, la key (`contexto-PROJ-12.md`). El dossier de `input/documentacion/historias/` va por key y lleva los dos IDs en su encabezado `historia:`.

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

**Versiones**: Python 3.10+, Node.js 20+ (22 LTS recomendado; mobile necesita 22+). Opcionales: Java 8+ (JMeter), Docker (seguridad web con ZAP), JDK + Android SDK o Xcode (mobile). Para revisar todo de una vez: `npm run doctor` (o `python scripts/doctor.py`), que dice qué falta y cómo resolverlo.

**Python**: en Windows el comando es `python`; en Mac y Linux, `python3` (y `pip3`). Los agentes usan el que corresponda al sistema. Los scripts instalan `openpyxl`/`tabulate`/`requests` solo si faltan; o se instalan con `pip install -r requirements.txt`. Si falta una librería y no se puede instalar, el script avisa con un mensaje claro (no falla en silencio).

Qué hace cada script y herramienta de `scripts/` y `herramientas/` (y con qué agente va) está en `REFERENCIA.md`. Se lee cuando hace falta, no en cada conversación.

- **Tests del repo**: `python -m pytest tests` y `npm run test:repo` (también corren en CI, en Ubuntu y Windows).

---

## Nombres de archivos de salida

Cada agente define en su archivo dónde guarda lo que genera. La lista completa (carpetas, archivos, historial de corridas) está en `REFERENCIA.md`. Regla general: todo va a `output/<herramienta>/<HU o nombre>/`, con el `HU-XXX` en el nombre si existe, y la corrida anterior pasa a `historial/` (últimas 5).

---

## Arquitectura (cómo crece el repo)

El repo se apoya en estas piezas: **agentes** (`.claude/agents/`, el quién), **skills** (`.claude/skills/`, el cómo, cargados on-demand), **MCP** (`.mcp.json`, conexiones a sistemas externos — un solo archivo que escala a muchas conexiones: Jira, Xray, Playwright…), **herramientas** (`herramientas/`, herramientas externas de testing, una subcarpeta por herramienta: Newman, **k0lmena**, OWASP ZAP, **streaming** (ffmpeg/ONVIF), **salesforce** (CLI `sf`), **ecommerce** (Shopify/WooCommerce/PrestaShop/VTEX), **sap** (SAP GUI Scripting), **desktop** (pywinauto), **seguridad** (SCA/SAST: dependencias y código), **codigo** (code review estático de repos y PR/MR), **mensajeria** (Kafka/RabbitMQ/MQTT/WebSocket/SSE), **soap** (WSDL), **seo** (SEO/GEO), **resiliencia** (caos server-side con Toxiproxy), **observabilidad**, **documentos** (PDF/Excel), **contenido** (typos), **mutacion** (mutation testing), **manual** (manuales de usuario) y **scalar** (APIs en Scalar)) y **scripts** (`scripts/`, utilidades internas determinísticas). El detalle y cómo extender cada una está en `ARQUITECTURA.md`.

### Modelo por agente (costo de tokens)

Cada agente fija su modelo en el frontmatter (`model:`) para no gastar de más. Criterio por niveles:

- **`haiku`** — trabajo mecánico que sobre todo corre un script y arma el JSON/HTML (tablero-calidad, analista-cobertura, analista-logs, generador-reporte-html, selector-casos-de-prueba, publicador-resultados, generador-charters, guia-onboarding).
- **`sonnet`** — la mayoría del trabajo de QA (mappers, ejecutores, generadores de casos y datos, probadores —incluidos `probador-salesforce`, `probador-billeteras`, `probador-shopify`, `probador-wordpress`, `probador-prestashop`, `probador-vtex`, `probador-sap`, `probador-desktop`, `probador-mobile`, `probador-ia`, `probador-mensajeria`, `probador-soap`, `analista-dependencias`, `probador-contratos`, `analista-seo`, `probador-datos`, `probador-dynamics`, `probador-ivr`, `probador-juegos`, `probador-pos`, `analista-observabilidad`, `probador-busqueda`, `probador-documentos`, `revisor-contenido`, `analista-mutacion`, `redactor-manual` y `probador-scalar`—, auditores, documentador, `investigador-proyecto`, triador, análisis de fallos, reparador, gestor, consultor, reportes de bug y de cierre…).
- **`opus`** — lo que más razona o es sensible: `analista-historias`, `analista-seguridad`, `pentester-web`, `analista-seguridad-camaras`, `analista-codigo-seguro`, `revisor-codigo`, `probador-blockchain`.

Un agente nuevo lleva su `model:` según este criterio. El costo real por agente lo mide `scripts/metricas_tokens.py` (lo resume el tablero de calidad): si uno queda flojo en Haiku/Sonnet, se sube; si otro no necesita Opus, se baja.

## APIs: REST y GraphQL; Postman, Bruno e Insomnia

`ejecutor-api` corre colecciones de **Postman, Bruno o Insomnia** con Newman (`correr_newman.py` convierte Bruno e Insomnia con `scripts/convertir_coleccion.py` y avisa lo que no tiene equivalente). `api-mapper` automatiza también **GraphQL** en k0lmena, con steps genéricos (`envío la consulta GraphQL:`, `la respuesta GraphQL no tiene errores`, …) y el schema resumido por `scripts/resumir_graphql.py`; `generador-casos-api` incluye casos GraphQL (variables inválidas, campos inexistentes, autorización por campo, errores parciales, profundidad y paginación).

## Avisos, portal y monitoreo

- **Avisos**: `scripts/avisar.py` publica en Slack y Teams por webhook del `.env`. Lo usan el triador (bug crítico), el tablero de calidad y el monitoreo, siempre que se pida o esté configurado.
- **Portal**: `output/index.html` muestra el último informe de cada herramienta y se regenera solo.
- **Monitoreo sintético**: `npm run monitorear`, de solo lectura, contra cualquier ambiente; avisa cuando algo se rompe o se recupera.

## Herramientas de gestión de pruebas

`scripts/gestion/gestion.py` integra **Xray Cloud, Xray Server/DC, QTM4J, AIO Tests y Zephyr Scale** con los mismos comandos (configurados en el `.env` de la raíz con `GESTION_HERRAMIENTA` y `GESTION_PROYECTO`). **Azure DevOps** (Boards y Test Plans) se integra por el conector MCP `azure-devops`, configurado también en el `.env` (`ADO_ORGANIZACION`, `ADO_PAT`, `ADO_PROYECTO`); los pasos de los casos los arma `scripts/gestion/para_azure_devops.py`. La trazabilidad local `output/gestion/<HU>-<herramienta>.json` guarda qué `CP-XXX` es qué key remota. Detalle en `scripts/gestion/README.md`.

## Automatización con k0lmena (ahorro de tokens)

`herramientas/k0lmena/` es el framework de automatización (web, api, mobile y performance). Los agentes **mapper** escriben la automatización **una sola vez** (skill `automatizacion-k0lmena`); después la suite corre **sin agentes ni tokens** con `cd herramientas/k0lmena && npm test` (performance: `npm run perf -- <script> <perfil>`). Para correr pruebas ya automatizadas, preferí `npm test` antes que los ejecutores en vivo (`ejecutor-e2e` / `ejecutor-api`), que gastan tokens en cada corrida.

Secretos (tokens, credenciales): van en el `.env` local (gitignored) o en variables de entorno, **nunca** commiteados; hay una plantilla `.env.example`. El `.mcp.json` está versionado con los conectores que vienen activos para todos (Playwright y Atlassian: Jira y Confluence), así Claude Code arranca sin pedir aprobaciones. Los opcionales (Azure DevOps, Figma, GitHub, GitLab, Linear, ClickUp, monday.com, Asana, Trello, Notion, YouTrack, Shortcut, QMetry/QTM4J, AIO Tests, k0lmenaTMT, Appium, Scalar) los activa cada persona con `npm run conector -- activar <nombre>`. Ninguno lleva secretos: los que piden token lo leen del `.env` con los scripts de `scripts/mcp/`. Si un agente necesita un conector que no está activo, o la persona quiere conectar una herramienta o configurar el proyecto, indicale que corra **`npm run configurar`** en una terminal (la de VS Code): pregunta todo en español y activa los conectores. **No le pidas tokens ni contraseñas en el chat**: van solo en ese asistente o en el `.env`. Detalle en `CONECTORES.md`.

**Repositorio de la aplicación:** el `documentador-proyecto` lo lee en solo lectura con el conector de su proveedor (`github`, `gitlab`, `azure-devops` para Azure Repos o `atlassian` para Bitbucket Cloud), configurado en el bloque *Repositorio de la aplicación* del `.env` (`REPO_PROVEEDOR`, `REPO_NOMBRE`, `REPO_RAMA`, `REPO_RUTA_LOCAL`).

**Fuentes externas por MCP:** si la persona da una key de Jira, un work item de Azure DevOps, una tarea de Linear, ClickUp, monday.com, Asana, Trello, Notion, YouTrack o Shortcut, una página de Confluence o de la Wiki de Azure DevOps, o un link de Figma y el conector (`atlassian`, `azure-devops` o `figma`) está activo, cualquier agente puede leerlos como insumo, igual que un archivo de `input/` (trazabilidad: citá la key, la página o el link). Si el conector no está activo, pedí el contenido o indicá cómo activarlo (`CONECTORES.md`); no lo supongas.

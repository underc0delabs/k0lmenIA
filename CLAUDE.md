# K0lmenIA Light — Contexto del proyecto

Este repositorio es un conjunto de **agentes de QA para Claude Code**, pensados para que profesionales de testing manual aceleren sus tareas del día a día: analizar historias, escribir casos de prueba (manuales y BDD), revisarlos, triar bugs, ejecutar pruebas end-to-end en el navegador y de API, acompañar la ejecución manual, automatizar con k0lmena y llevar casos y resultados a Xray o k0lmenaTMT.

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

- **Antes de invocar un agente**, la conversación principal resuelve con la persona lo que el agente seguro va a necesitar y no está en el pedido. Por ejemplo: headed o headless (`ejecutor-e2e`, `web-mapper`), qué historia si hay varias, la URL o el ambiente, y la key de la historia en Jira para la gestión.
- **Si un agente termina devolviendo "Necesito que confirmes"**, la conversación principal le hace esas preguntas a la persona (con opciones, la recomendada primero) y **continúa al mismo agente** con las respuestas; no empieza uno nuevo.
- Las acciones con efecto (crear o modificar datos en Jira, Xray o k0lmenaTMT, métodos con efecto en una API) se confirman **con la persona** y se le pasan al agente explícitamente; nunca se asumen.
- **Contexto y documentación en inglés**: las fichas de contexto, la documentación del proyecto (`documentador-proyecto`) y los mapeos se escriben en español. Antes de invocar al agente que los arma, si `DOCUMENTACION_EN` del `.env` está vacía, preguntá *"¿Lo querés también en inglés?"* (y sugerí fijar la respuesta en `DOCUMENTACION_EN=si|no` para no volver a preguntar) y pasale al agente *"Versión en inglés: sí"* o *"no"*. Con `si` o `no` en el `.env`, no se pregunta.
- **Documentar todo el proyecto** (y mantenerlo al día): la conversación principal sigue el skill `base-conocimiento`: encadena el `documentador-proyecto` (modo barrido y la app de punta a punta con sesión) y la rutina de actualización cuando cambian los requerimientos (historias, código y aplicación → qué rehacer y qué casos revisar).
- **Ejecución manual** (casos manuales paso a paso): la conduce la conversación principal con el skill `ejecucion-manual`; el `asistente-ejecucion-manual` cierra la sesión y publica con confirmación.
- **Primer uso** ("¿cómo empiezo?", recién instalado): la conversación principal sigue el skill `empezar` (en el plugin, `/k0lmenia:empezar`).
- **No sabés qué probar o con qué agente/skill**: la conversación principal usa el skill `guia-pruebas` para preguntarte paso a paso y recomendar o ejecutar el agente/skill que corresponde (también es un skill de la conversación principal, porque los subagentes no pueden preguntar).
- **Correr pruebas ya automatizadas**: es `npm test` en k0lmena (sin agentes ni tokens). Los ejecutores en vivo (`ejecutor-e2e`, `ejecutor-api`) son para casos sueltos que no vale la pena automatizar.
- **Lo que no está en Light** (accesibilidad, rendimiento, seguridad, performance, mobile, métricas, entre otros): decí que está disponible en K0lmenIA Pro o K0lmenIA Empresa (https://k0lmena.com/k0lmenia/) y ofrecé lo que sí se puede hacer con Light.

---

## Agentes disponibles

Hay 13 agentes. Claude Code elige el que corresponde por el `description` de cada uno (`.claude/agents/`), así que acá va solo el índice por familia. Qué hace cada uno, cómo pedírselo, qué usa, dónde guarda la salida y qué confirma está en `AGENTES.md`; la tabla de salidas y la lista de scripts, en `REFERENCIA.md`.

- **Análisis y diseño**: `documentador-proyecto`, `analista-historias`, `generador-casos-manuales`, `generador-casos-bdd`, `revisor-casos`, `triador-bugs`.
- **Ejecución en vivo**: `ejecutor-e2e`, `ejecutor-api`, `asistente-ejecucion-manual`.
- **Automatización (k0lmena)**: `web-mapper`, `api-mapper`.
- **Gestión**: `gestor-pruebas`, `publicador-resultados`.

---

## Estándares de QA del proyecto

Estos principios aplican a **todos** los agentes:

- **No inventar.** Si falta información para hacer bien la tarea (un paso, un dato, una regla de negocio, un resultado esperado), el agente lo **marca y lo pregunta**; nunca rellena con suposiciones disfrazadas de hechos. Es preferible un artefacto con huecos señalados que uno completo pero inventado.
- **Investigar antes de suponer.** Antes de analizar, escribir casos o automatizar una historia, se revisa su contexto completo con el skill `investigacion-contexto`: primero la documentación del proyecto de `input/documentacion/` (la arma el `documentador-proyecto`: índice, dossier de la historia, reglas del código, mensajes, mapa funcional; cada documento declara su confiabilidad: `confirmado`, `borrador`, `investigacion` o `sin-confirmar`), y después la historia de Jira con **todos** sus comentarios, subtareas, épica e issues vinculados, contratos y `input/`. El resultado queda en una ficha reutilizable `output/contexto/contexto-HU-XXX.md`.
- **Marcar lo que falta.** Lo que no aparece en ninguna fuente se registra como **Falta información** con un ID por historia (`FI-01`, `FI-02`, …) y viaja con ese ID a todos los artefactos: casos (resaltados, etiqueta `@falta-info`, hoja *Falta información*), `.feature` (`@falta-info @FI-01`), coberturas, mapeos, reportes de ejecución y lo que se publica en Xray o k0lmenaTMT. En los `analisis.json` y `_resultados-*.json` de los informes HTML va como `falta_informacion: [{"id": "FI-01", "que_falta": "…", "pregunta": "…"}]`.
- **Informes en español e inglés.** Cada informe HTML sale en una carpeta por idioma (`es/informe.html` y `en/informe.html`); el acceso `informe.html` abre el idioma que se eligió con la banderita (español por defecto). El agente escribe en el JSON del informe un bloque `"en"` con la traducción de sus textos (mismas claves e IDs); la interfaz la traduce el script (`scripts/_i18n.py`, diccionarios en `scripts/i18n/en/`).
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

**Versiones**: Python 3.10+, Node.js 20+ (22 LTS recomendado). Para revisar todo de una vez: `npm run doctor` (o `python scripts/doctor.py`), que dice qué falta y cómo resolverlo.

**Python**: en Windows el comando es `python`; en Mac y Linux, `python3` (y `pip3`). Los agentes usan el que corresponda al sistema. Los scripts instalan `openpyxl`/`tabulate`/`requests` solo si faltan; o se instalan con `pip install -r requirements.txt`. Si falta una librería y no se puede instalar, el script avisa con un mensaje claro (no falla en silencio).

Qué hace cada script y herramienta de `scripts/` y `herramientas/` (y con qué agente va) está en `REFERENCIA.md`. Se lee cuando hace falta, no en cada conversación.

- **Tests del repo**: `python -m pytest tests` y `npm run test:repo` (también corren en CI, en Ubuntu y Windows).

---

## Nombres de archivos de salida

Cada agente define en su archivo dónde guarda lo que genera. La lista completa (carpetas, archivos, historial de corridas) está en `REFERENCIA.md`. Regla general: todo va a `output/<herramienta>/<HU o nombre>/`, con el `HU-XXX` en el nombre si existe, y la corrida anterior pasa a `historial/` (últimas 5).

---

## Arquitectura (cómo crece el repo)

El repo se apoya en estas piezas: **agentes** (`.claude/agents/`, el quién), **skills** (`.claude/skills/`, el cómo, cargados on-demand), **MCP** (`.mcp.json`, conexiones a sistemas externos: Jira, Playwright…), **herramientas** (`herramientas/`, herramientas externas de testing, una subcarpeta por herramienta: Newman, **k0lmena** y **ci**) y **scripts** (`scripts/`, utilidades internas determinísticas). El detalle y cómo extender cada una está en `ARQUITECTURA.md`.

### Modelo por agente (costo de tokens)

Cada agente fija su modelo en el frontmatter (`model:`) para no gastar de más. Criterio por niveles:

- **`haiku`** — trabajo mecánico que sobre todo corre un script y arma el JSON/HTML (`publicador-resultados`).
- **`sonnet`** — la mayoría del trabajo de QA (mappers, ejecutores, generadores de casos, revisor, documentador, triador, gestor y `asistente-ejecucion-manual`).
- **`opus`** — lo que más razona: `analista-historias`.

Un agente nuevo lleva su `model:` según este criterio. El costo real por agente lo mide `scripts/metricas_tokens.py`: si uno queda flojo en Haiku/Sonnet, se sube; si otro no necesita Opus, se baja.

## APIs: REST, GraphQL y gRPC; Postman, Bruno e Insomnia

`ejecutor-api` corre colecciones de **Postman, Bruno o Insomnia** con Newman (`correr_newman.py` convierte Bruno e Insomnia con `scripts/convertir_coleccion.py` y avisa lo que no tiene equivalente). `api-mapper` automatiza también **GraphQL** en k0lmena, con steps genéricos (`envío la consulta GraphQL:`, `la respuesta GraphQL no tiene errores`, …) y el schema resumido por `scripts/resumir_graphql.py`; para gRPC y WebSocket, el skill `pruebas-grpc`.

## Avisos y portal

- **Avisos**: `scripts/avisar.py` publica en Slack y Teams por webhook del `.env`. Lo usa el triador (bug crítico), siempre que se pida o esté configurado.
- **Portal**: `output/index.html` muestra el último informe de cada herramienta y se regenera solo.

## Herramientas de gestión de pruebas

`scripts/gestion/gestion.py` integra **Xray Cloud, Xray Server/DC y k0lmenaTMT** con los mismos comandos (configurados en el `.env` de la raíz con `GESTION_HERRAMIENTA` y `GESTION_PROYECTO`). La trazabilidad local `output/gestion/<HU>-<herramienta>.json` guarda qué `CP-XXX` es qué key remota. Detalle en `scripts/gestion/README.md`.

## Automatización con k0lmena (ahorro de tokens)

`herramientas/k0lmena/` es el framework de automatización (web y api). Los agentes **mapper** escriben la automatización **una sola vez** (skill `automatizacion-k0lmena`); después la suite corre **sin agentes ni tokens** con `npm test`. Para correr pruebas ya automatizadas, preferí `npm test` antes que los ejecutores en vivo (`ejecutor-e2e` / `ejecutor-api`), que gastan tokens en cada corrida.

Secretos (tokens, credenciales): van en el `.env` local (gitignored) o en variables de entorno, **nunca** commiteados; hay una plantilla `.env.example`. El `.mcp.json` está versionado con los conectores que vienen activos para todos (Playwright y Atlassian para Jira), así Claude Code arranca sin pedir aprobaciones. El de k0lmenaTMT lo activa cada persona con `npm run conector -- activar k0lmena-tmt`. Ninguno lleva secretos: los que piden token lo leen del `.env` con los scripts de `scripts/mcp/`. Si un agente necesita un conector que no está activo, o la persona quiere conectar una herramienta o configurar el proyecto, indicale que corra **`npm run configurar`** en una terminal (la de VS Code): pregunta todo en español y activa los conectores. **No le pidas tokens ni contraseñas en el chat**: van solo en ese asistente o en el `.env`. Detalle en `CONECTORES.md`.

**Repositorio de la aplicación:** el `documentador-proyecto` lo lee en solo lectura desde el clon local (`REPO_RUTA_LOCAL` en el bloque *Repositorio de la aplicación* del `.env`).

**Fuentes externas por MCP:** si la persona da una key de Jira y el conector `atlassian` está activo, cualquier agente puede leerla como insumo, igual que un archivo de `input/` (trazabilidad: citá la key). Si el conector no está activo, pedí el contenido o indicá cómo activarlo (`CONECTORES.md`); no lo supongas.

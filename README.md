<div align="center">

# 🪖 K0lmenIA Light

### Agentes de QA para Claude Code

**Diseñá, ejecutá y automatizá pruebas conversando en español.**<br>
Análisis de historias, casos de prueba, ejecución web y de API, automatización con k0lmena y gestión en Xray o k0lmenaTMT.

<br>

[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-22c55e?style=flat-square)](#licencia)
[![Idioma](https://img.shields.io/badge/idioma-español-0ea5e9?style=flat-square)](#)
[![Agentes](https://img.shields.io/badge/agentes-13-8b5cf6?style=flat-square)](#-agentes)
[![Suites sin tokens](https://img.shields.io/badge/suites-sin%20tokens-10b981?style=flat-square)](#️-automatización-con-k0lmena)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-D97757?style=flat-square&logo=anthropic&logoColor=white)](https://docs.claude.com/en/docs/claude-code/overview)

**Automatización**

![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white)
![Cucumber](https://img.shields.io/badge/Cucumber-23D96C?style=flat-square&logo=cucumber&logoColor=white)
![Postman](https://img.shields.io/badge/Postman%20·%20Newman-FF6C37?style=flat-square&logo=postman&logoColor=white)

**Stack**

![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-20+-5FA04E?style=flat-square&logo=nodedotjs&logoColor=white)
![Python](https://img.shields.io/badge/Python-3-3776AB?style=flat-square&logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-conectores-111827?style=flat-square)

**Bases de datos**

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white)
![MariaDB](https://img.shields.io/badge/MariaDB-003545?style=flat-square&logo=mariadb&logoColor=white)
![SQL Server](https://img.shields.io/badge/SQL%20Server-CC2927?style=flat-square)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)

**Integraciones**

![Jira](https://img.shields.io/badge/Jira-0052CC?style=flat-square&logo=jira&logoColor=white)
![Xray](https://img.shields.io/badge/Xray-Cloud%20·%20DC-00C7B1?style=flat-square)
![k0lmenaTMT](https://img.shields.io/badge/k0lmenaTMT-MCP-F9B006?style=flat-square)

<br>

[**📖 Documentación web**](https://underc0delabs.github.io/k0lmenIA/) · [**📄 Documentación en PDF**](https://github.com/underc0delabs/k0lmenIA/releases/download/docs/k0lmenIA-documentacion.pdf) · [**🇬🇧 English**](https://underc0delabs.github.io/k0lmenIA/en/) ([PDF](https://github.com/underc0delabs/k0lmenIA/releases/download/docs/k0lmenIA-documentation.pdf)) · [**🚀 Empezar**](#-instalación-rápida) · [**🌐 qarmy.ar**](https://qarmy.ar) · [**▶️ YouTube**](https://www.youtube.com/@QARMY-UC?sub_confirmation=1) · [**💬 WhatsApp**](https://whatsapp.com/channel/0029VaSzkgD1CYoTmiX8Uv26)

</div>

---

## ⚡ Instalación rápida

Con [Claude Code](https://claude.com/claude-code) instalado, en una terminal:

```
claude plugin marketplace add underc0delabs/k0lmenIA
claude plugin install k0lmenia@k0lmenia
```

Después abrí Claude Code en la carpeta de tu proyecto y escribí **`/k0lmenia:empezar`**: te deja todo listo y te propone la primera tarea. Más detalles en [Como plugin de Claude Code](#-como-plugin-de-claude-code); si preferís clonar el repo, en [Instalación](#-instalación).

---

## ✨ Qué ofrece

> Pensado para QAs manuales: no hace falta programar. Se trabaja conversando con Claude Code dentro de VS Code.

| | |
|---|---|
| 🧠 **Diseño de pruebas** | Analiza historias, escribe casos manuales (Excel) y BDD (Gherkin), revisa la calidad de los casos y tria los bugs antes de cargarlos. |
| 🤖 **Automatización sin tokens** | Los agentes *mapper* recorren tu app **una sola vez** y escriben la automatización en k0lmena. Después corre con `npm test`, sin agentes. |
| 🌐 **Web y API** | Playwright + Cucumber en el navegador; axios + Cucumber para APIs REST, GraphQL y gRPC; colecciones de Postman, Bruno o Insomnia con Newman. |
| 🧭 **Ejecución manual acompañada** | Te guía caso por caso y paso por paso, registra resultados, evidencia y tiempos, y deja el informe. |
| 📸 **Evidencia completa** | Captura (y GIF) de cada test que pasa; video, logs, trace y error de cada test que falla, en reportes HTML. |
| 🗂️ **Gestión de pruebas** | Carpetas, casos, ciclos y resultados con evidencias en **Xray** (Cloud y Server/DC) y **k0lmenaTMT**. |
| 🗄️ **Verificación en base de datos** | Steps de k0lmena para revisar lo que dejaron guardado tus pruebas en **PostgreSQL, MySQL/MariaDB, SQL Server o MongoDB**. Solo lectura por defecto. |
| 🔌 **Conectado** | Lee historias de **Jira** con todos sus comentarios, subtareas, épica e issues vinculados, y el código del repositorio de tu app clonado en tu PC. |
| 🛡️ **No inventa** | Lo que no está en ninguna fuente queda marcado como **Falta información** (`FI-01`) en todos los reportes, con la pregunta para el PO. |

<p align="center">
  <img src="docs/assets/img/arquitectura.png" alt="Arquitectura de K0lmenIA Light" width="100%">
</p>

<p align="center">
  <img src="docs/assets/img/relaciones.png" alt="Cómo se relacionan agentes, skills, plantillas, scripts, herramientas y conectores MCP" width="100%">
</p>

<p align="center">
  <img src="docs/assets/img/uso.png" alt="Cómo se usa K0lmenIA Light" width="100%">
</p>

---

## 📚 Contenido

- [Agentes](#-agentes)
- [Requisitos](#-requisitos)
- [Como plugin de Claude Code](#-como-plugin-de-claude-code)
- [Instalación](#-instalación)
- [Configuración: el archivo `.env`](#️-configuración-el-archivo-env)
- [Cómo se usa](#-cómo-se-usa)
- [Investigación de contexto y "Falta información"](#-investigación-de-contexto-y-falta-información)
- [Documentación del proyecto](#-documentación-del-proyecto)
- [Automatización con k0lmena](#️-automatización-con-k0lmena)
- [Gestión de pruebas: Xray y k0lmenaTMT](#️-gestión-de-pruebas-xray-y-k0lmenatmt)
- [k0lmena en el pipeline (CI)](#-k0lmena-en-el-pipeline-ci)
- [Triage de bugs](#-triage-de-bugs)
- [Ejecución manual acompañada](#-ejecución-manual-acompañada)
- [Historial de corridas y portal de informes](#-historial-de-corridas-y-portal-de-informes)
- [Avisos a Slack y Teams](#-avisos-a-slack-y-teams)
- [Evals de los agentes](#-evals-de-los-agentes)
- [Uso de tokens](#-uso-de-tokens)
- [Apps con protección anti-bots](#-apps-con-protección-anti-bots)
- [Verificación en base de datos](#️-verificación-en-base-de-datos)
- [Conectores MCP](#-conectores-mcp)
- [¿Necesitás más?](#-necesitás-más)
- [Referencia](#-referencia): flujo completo, convenciones, estructura, problemas frecuentes y cómo extenderlo

---

## 🤖 Agentes

Claude Code elige el agente según lo que pidas; también podés nombrarlo (*"usá el web-mapper para…"*). Son 13 agentes. **El catálogo completo** —cuándo usar cada agente, un pedido de ejemplo, qué skills, scripts, herramientas y conectores usa, qué entrega y qué te confirma antes— está en [`AGENTES.md`](AGENTES.md).

<table>
<tr><th>Familia</th><th>Agente</th><th>Qué hace</th></tr>
<tr><td rowspan="6"><b>🧠 Análisis<br>y diseño</b></td>
  <td><code>documentador-proyecto</code></td><td>Arma la documentación del proyecto en <code>input/documentacion/</code>: lee el repositorio local (solo lectura), las historias de Jira con sus comentarios y links, y hace un mapa funcional de la web</td></tr>
<tr><td><code>analista-historias</code></td><td>Investiga el contexto (comentarios, subtareas, épica, vínculos) y detecta ambigüedades, vacíos, riesgos y Falta información</td></tr>
<tr><td><code>generador-casos-manuales</code></td><td>Casos en Excel y Markdown + informe de cobertura</td></tr>
<tr><td><code>generador-casos-bdd</code></td><td>Escenarios Gherkin (keywords en inglés, contenido en español) + cobertura</td></tr>
<tr><td><code>revisor-casos</code></td><td>Revisa la calidad de los casos existentes: puntaje, problemas, duplicados, tiempo de ejecución manual y la versión mejorada</td></tr>
<tr><td><code>triador-bugs</code></td><td>Antes de cargar un bug, busca si ya existe en Jira o en los bugs locales, detecta regresiones de bugs cerrados y sugiere severidad, componente, responsable e historia</td></tr>
<tr><td rowspan="3"><b>▶️ Ejecución<br>en vivo</b></td>
  <td><code>ejecutor-e2e</code></td><td>Ejecuta casos en un navegador real con Playwright MCP, con evidencia</td></tr>
<tr><td><code>ejecutor-api</code></td><td>Corre una colección de Postman, Bruno o Insomnia con Newman (REST y GraphQL)</td></tr>
<tr><td><code>asistente-ejecucion-manual</code></td><td>Ejecución manual acompañada: cierra la sesión, arma el informe con resultados, evidencia y tiempos, y deja lista la publicación</td></tr>
<tr><td rowspan="2"><b>🤖 Automatización<br>con k0lmena</b></td>
  <td><code>web-mapper</code></td><td>Recorre la web siguiendo tus casos y genera <code>.feature</code>, steps y locators</td></tr>
<tr><td><code>api-mapper</code></td><td>Lee Postman o Swagger/OpenAPI, verifica los endpoints y genera los <code>.feature</code></td></tr>
<tr><td rowspan="2"><b>🗂️ Gestión</b></td>
  <td><code>gestor-pruebas</code></td><td>Carpetas, casos, vínculos con la historia y ciclos en Xray o k0lmenaTMT</td></tr>
<tr><td><code>publicador-resultados</code></td><td>Sube los resultados de <code>npm test</code> al ciclo con sus evidencias</td></tr>
</table>

<details>
<summary><b>Los 13 skills</b> (el "cómo" que usan los agentes y la conversación principal)</summary>

<table>
<tr><th>Skill</th><th>Qué enseña</th><th>Lo usan</th></tr>
<tr><td><code>investigacion-contexto</code></td><td>Investigar la historia completa (documentación del proyecto, comentarios, subtareas, épica, contratos) y registrar la Falta información (FI-XX)</td><td>analista-historias, generadores de casos, revisor-casos, web-mapper, api-mapper, documentador-proyecto</td></tr>
<tr><td><code>tecnicas-de-diseno</code></td><td>Equivalencia, valores límite, tabla de decisión, transición de estados y pairwise</td><td>generador-casos-manuales, generador-casos-bdd, api-mapper, revisor-casos</td></tr>
<tr><td><code>redaccion-casos-manuales</code></td><td>Referencia del generador de casos manuales: columnas, esquema del JSON de generar_casos.py, reglas de campos e informe de cobertura</td><td>generador-casos-manuales</td></tr>
<tr><td><code>ejecucion-e2e</code></td><td>Ejecutar en el navegador con Playwright MCP: modos, snapshots, esperas y evidencia</td><td>ejecutor-e2e, web-mapper, documentador-proyecto</td></tr>
<tr><td><code>ejecucion-api</code></td><td>Correr colecciones con Newman: base_url, token, validaciones y resultados</td><td>ejecutor-api</td></tr>
<tr><td><code>pruebas-graphql</code></td><td>Probar APIs GraphQL: schema e introspección, queries, mutations y subscriptions, errores parciales y nulabilidad, autorización por campo, N+1, profundidad y paginación</td><td>ejecutor-api, api-mapper</td></tr>
<tr><td><code>pruebas-grpc</code></td><td>gRPC (Protobuf, modos de RPC, status codes, deadlines, compatibilidad) y WebSocket en la familia de API</td><td>ejecutor-api, api-mapper</td></tr>
<tr><td><code>automatizacion-k0lmena</code></td><td>Convenciones de k0lmena: features, steps, locators, tags y steps de BD</td><td>web-mapper, api-mapper</td></tr>
<tr><td><code>documentacion-proyecto</code></td><td>Referencia del documentador: lectura del repositorio, mapa funcional, estructura de input/documentacion/ y dossier, modos barrido y actualizar</td><td>documentador-proyecto</td></tr>
<tr><td><code>base-conocimiento</code></td><td>Armar y mantener la base de conocimiento del proyecto en input/documentacion/ y la rutina ágil cuando cambian los requerimientos</td><td>la conversación principal</td></tr>
<tr><td><code>ejecucion-manual</code></td><td>Ejecución manual acompañada en la conversación: caso por caso y paso por paso, resultados, evidencia, tiempos, bugs, pausa y retomar</td><td>conversación principal (/k0lmenia:ejecucion-manual) y asistente-ejecucion-manual</td></tr>
<tr><td><code>guia-pruebas</code></td><td>Asistente interactivo para elegir qué probar y con qué agente o skill: pregunta paso a paso y recomienda o ejecuta</td><td>la conversación principal</td></tr>
<tr><td><code>empezar</code></td><td>Bienvenida y puesta en marcha: preparar el proyecto, revisar el entorno, conectar herramientas y elegir la primera tarea (`/k0lmenia:empezar` en el plugin)</td><td>conversación principal</td></tr>
</table>

</details>

## 📋 Requisitos

| Para… | Necesitás |
|---|---|
| Usar los agentes | **Claude Code** + cuenta de Claude (Pro, Max, Team o Enterprise) o API de Anthropic. VS Code recomendado. |
| Casos, reportes y gestión | **Python 3.10+** (`pip install -r requirements.txt`; en Mac/Linux, `pip3`) |
| Ejecutar E2E en vivo | **Node.js 20+** (22 LTS recomendado) y navegadores de Playwright |
| Colecciones de Postman | **Newman** |
| Automatizar con k0lmena | **Node.js 20+** (22 LTS recomendado) |

---

## 🧩 Como plugin de Claude Code

La forma más fácil de usar K0lmenIA Light: se instala como **plugin** y funciona en la carpeta de cualquier proyecto, sin clonar este repo. Las actualizaciones llegan solas y nunca tocan tu trabajo.

**1. Instalalo** (una sola vez, desde una terminal):

```
claude plugin marketplace add underc0delabs/k0lmenIA
claude plugin install k0lmenia@k0lmenia
```

(O adentro de Claude Code: `/plugin marketplace add underc0delabs/k0lmenIA` y `/plugin install k0lmenia@k0lmenia`.)

**2. Abrí Claude Code en la carpeta de tu proyecto y escribí `/k0lmenia:empezar`.** Te prepara el proyecto (carpetas, `.env` y k0lmena para las pruebas automatizadas), revisa que tengas todo instalado, te ayuda a conectar Jira y te propone la primera tarea.

**3. Pedí lo que necesites en lenguaje natural**: *"Escribí los casos de prueba de PROJ-12"*, *"Probá el login en el navegador"*, *"Automatizá los casos de HU-001"*.

- **Comandos**: lo que acá es `npm run <x>` o `python scripts/<x>.py`, en el plugin es `k0lmenia <x>` (`k0lmenia ayuda` los lista). Los agentes se llaman `k0lmenia:<agente>`.
- **Requisitos**: Python 3.10+ y Node.js 20+ (`/k0lmenia:empezar` te dice si falta algo y cómo instalarlo).
- **Qué instala y dónde**: el código (agentes, skills, scripts y herramientas) queda en la caché de Claude Code y se actualiza solo. En la carpeta de tu proyecto, `k0lmenia init` (o `/k0lmenia:empezar`) deja todo lo tuyo: `input/` con los mismos ejemplos que el repo, `output/` con los informes y el portal, el `.env`, `TAREAS.md`, tu copia de k0lmena para las pruebas automatizadas y, en `.claude/settings.json`, los mismos permisos que el repo clonado (Claude te pide las mismas confirmaciones). Nunca pisa un archivo que ya existe.
- **Igual que clonar el repo**: mismos agentes, skills, comandos, informes, portal y conectores. Lo único que no viaja es lo del desarrollo: la web y el PDF (están online), los tests del repo y los evals de los agentes.
- **Actualizar**: cada push a `main` se publica solo en la rama `plugin`. Para recibirlo, activá una vez la actualización automática (`/plugin` → Marketplaces → `k0lmenia` → *Enable auto-update*) o corré `/plugin marketplace update k0lmenia`. El plugin vive en la caché de Claude Code; tu proyecto (`input/`, `output/`, `.env`) no se toca.
- **Novedades**: después de una actualización, al iniciar la sesión Claude te cuenta en dos o tres líneas qué cambió desde la última vez que lo usaste. A pedido: `k0lmenia novedades` (las nuevas), `--todas` o `--ultimas 5`; deja el informe en `output/novedades/`. Con el repo clonado: `npm run novedades`.
- **Actualizar k0lmena** (el framework de automatización de tu proyecto): `k0lmenia actualizar`. Claude te avisa al iniciar la sesión cuando hay versión nueva. Tus pruebas (features, steps, locators) no se tocan, y si modificaste un archivo del framework, la versión nueva queda al lado como `.nuevo` para que la compares.
- **Personalizar un agente**: copialo a `.claude/agents/` de tu proyecto. Esa copia le gana a la del plugin, pero deja de recibir las mejoras de ese agente.
- **Para todo el equipo**: declarás el marketplace y el plugin en el `.claude/settings.json` del proyecto (instrucciones en la rama [`plugin`](https://github.com/underc0delabs/k0lmenIA/tree/plugin)).
- **Cómo se arma**: la rama `plugin` la publica sola el workflow `plugin.yml` en cada push a `main`, con `python scripts/construir_plugin.py`. El catálogo (`.claude-plugin/marketplace.json` de `main`) apunta a esa rama, por eso el comando de instalación no lleva `#plugin`.

## 🚀 Instalación

```bash
# 1. Claude Code (macOS / Linux; en Windows seguí la guía oficial, abajo)
curl -fsSL https://claude.ai/install.sh | bash

# 2. El repositorio (si ya lo tenés clonado con otro nombre, entrá a esa carpeta)
git clone https://github.com/underc0delabs/k0lmenIA.git
cd k0lmenIA
pip install -r requirements.txt   # en Mac/Linux: pip3 install -r requirements.txt
npm install                       # k0lmena (se instala en herramientas/k0lmena)
npm run configurar                # preguntas simples: tu app y tus herramientas (crea el .env y activa los conectores)

# 3. Revisá que esté todo listo
npm run doctor                    # dice qué falta y cómo resolverlo

# 4. A trabajar
code .
claude                            # en la terminal de VS Code
```

> En Windows el comando de Python es `python`; en Mac y Linux, `python3` y `pip3`. Si en Mac `pip3` responde *externally-managed-environment*, usá un entorno virtual: `python3 -m venv .venv && source .venv/bin/activate` (`.venv/` ya está en `.gitignore`).

<details>
<summary><b>Instalar lo opcional</b> (ejecución en vivo, Newman, k0lmena)</summary>

```bash
npx playwright install                  # ejecución E2E en vivo
npm install -g newman                   # colecciones de Postman

npm install                             # k0lmena (desde la raíz; instala en herramientas/k0lmena)
cd herramientas/k0lmena
npx playwright install chromium
```

Claude Code también se instala con `npm install -g @anthropic-ai/claude-code` (con Node.js 22 LTS cubrís Claude Code y todo el proyecto). Guía oficial: https://docs.claude.com/en/docs/claude-code/overview
</details>

---

## ⚙️ Configuración: el archivo `.env`

Hay **un solo `.env`, en la raíz**. Lo usan los agentes, k0lmena y los scripts de gestión. Nunca se sube al repo; la plantilla comentada es [`.env.example`](.env.example).

**La forma fácil:** `npm run configurar`. Pregunta la URL de tu app y qué herramientas usa tu equipo, pide solo los datos de esas herramientas y activa los conectores. Se puede correr las veces que quieras: Enter deja lo que ya estaba. Lo de abajo es para quien quiera editar el `.env` a mano.

| Grupo | Variables |
|---|---|
| App bajo prueba | `APP_URL` `APP_USER` `APP_PASSWORD` |
| API | `API_TOKEN` `API_BASEURL` |
| Web (k0lmena) | `BROWSER` `HEADLESS` `VIEWPORT_WIDTH` `VIEWPORT_HEIGHT` `LOCALE` `TIMEZONE` (la URL es `APP_URL`) |
| Ejecución y evidencias | `TAGS` `PARALLEL` `EVIDENCE` (`captura` · `ambos` · `off`) `VIDEO` `TRACE` `K0LMENA_AUTO_HEALING` |
| Bases de datos | `DB_CONEXIONES` + por conexión `DB_<NOMBRE>_MOTOR` `_HOST` `_PUERTO` `_BASE` `_USUARIO` `_CLAVE` (o `_URL`) `_ESCRITURA` `_PRODUCCION` |
| Repositorio de la app | `REPO_RUTA_LOCAL` (la carpeta donde lo tenés clonado) |
| Gestión | `GESTION_HERRAMIENTA` `GESTION_PROYECTO` + credenciales de Xray o k0lmenaTMT (`K0LMENA_TMT_TOKEN`) |

> [!WARNING]
> Usá credenciales de un entorno de **prueba**. Los agentes leen los secretos del `.env`: nunca pegues un token en el chat.

---

## 💬 Cómo se usa

1. Pedí *"Documentá el proyecto"* para juntar el contexto (repositorio, historias, links y web) en `input/documentacion/`; poné tus insumos en `input/` (`historias/`, `api/`, `bugs/`), o pasá una key de Jira.
2. Pedí lo que necesitás en lenguaje natural.
3. Revisá el resultado en `output/` o en `herramientas/k0lmena/`.

| Le pedís | Obtenés |
|---|---|
| *"Documentá el proyecto"* · *"Juntá el contexto de PROJ-12"* | Base del proyecto + dossier de la historia en `input/documentacion/` |
| *"Investigá el contexto de PROJ-12"* | Ficha de contexto con fuentes, hallazgos y Falta información |
| *"Analizá la historia HU-001"* | Ambigüedades y preguntas para el PO |
| *"Generá los casos de HU-001"* | `casos-HU-001.xlsx` + `.md` + cobertura |
| *"Pasá la historia HU-001 a escenarios BDD"* | `HU-001-<slug>.feature` + cobertura |
| *"Revisá los casos de HU-001"* | Puntaje, problemas, duplicados y tiempo de ejecución |
| *"¿Este bug ya está cargado en Jira?"* | Duplicados, posibles regresiones y severidad sugerida |
| *"Ejecutá el escenario de registro válido contra https://tu-app.com"* | Reporte HTML de la corrida con evidencia |
| *"Corré la colección de input/api para HU-001"* | Reporte HTML de la corrida de API |
| *"Acompañame a ejecutar los casos de HU-012"* | Sesión guiada paso a paso + informe de ejecución manual |
| *"Automatizá en k0lmena los casos de HU-001 contra https://tu-app.com"* | `.feature` + steps + locators |
| *"Subí los casos de HU-001 a Xray, vinculados a PROJ-12, y creá el ciclo Sprint 5"* | Casos y ciclo en Xray |
| *"Subí los resultados de la última corrida al ciclo PROJ-60"* | Estados y evidencias en el ciclo |
| *"Avisá en Slack el resultado de la última corrida"* | Mensaje en Slack o Teams |

### Lista de tareas (`TAREAS.md`)

Para encargar varias cosas de una vez, escribí en [`TAREAS.md`](TAREAS.md) una tarea por línea, en el orden en que querés que se hagan, y pedí *"Hacé las tareas de TAREAS.md"*:

```markdown
- [ ] Armar la ficha de contexto de la HU-001
- [ ] Escribir los casos manuales de la HU-001 (módulo login)
- [ ] Subir los casos de la HU-001 a k0lmenaTMT
```

Claude las lee todas y te pregunta lo que necesita antes de empezar, así no se frena entre una y otra. Después las hace en orden y marca cada una: `- [x]` con dónde quedó el resultado, o `- [!]` con lo que le falta. Antes de escribir en Jira o en la herramienta de gestión, pide confirmación.

---

## 🔎 Investigación de contexto y "Falta información"

Antes de analizar, escribir casos o automatizar una historia, los agentes **investigan su contexto completo** (skill `investigacion-contexto`) en lugar de suponer:

| Fuente | Qué revisan |
|---|---|
| Documentación del proyecto | Primero: el índice y el dossier de la historia que arma el `documentador-proyecto` en `input/documentacion/` |
| Historia de Jira | Descripción, criterios, estado, labels, componentes y adjuntos |
| Comentarios | **Todos**: las decisiones que se tomaron después (*"acordamos que el límite es 50"*) reemplazan a la descripción |
| Subtareas, épica e issues vinculados | Reglas generales, historias hermanas y bugs conocidos del flujo |
| Contratos y `input/` | Swagger, Postman y documentación local |

El resultado es una **ficha de contexto** reutilizable (`output/contexto/contexto-HU-XXX.md`) con las fuentes consultadas, los hallazgos por criterio, las decisiones y las contradicciones. Si la historia no cambió, los demás agentes la reusan sin volver a investigar.

**Lo que no aparece en ninguna fuente se marca como "Falta información"** con un ID por historia (`FI-01`, `FI-02`, …), que viaja a todos los reportes:

| Dónde | Cómo se ve |
|---|---|
| Planilla de casos (`.xlsx`) | Casos resaltados en ámbar, etiqueta `@falta-info`, detalle en Comentarios y hoja **Falta información** |
| Coberturas y análisis | Sección **Falta información** (qué falta, dónde se buscó, a qué afecta, pregunta para el PO); criterios `Parcial (falta información)` |
| `.feature` de k0lmena | Tags `@falta-info @FI-01` y comentario `# FALTA INFORMACIÓN (FI-01): …` |
| Reporte de mapeo | Estado `Falta información`: el mapper **no usa la app para completar el dato** |
| Reportes de k0lmena y de ejecución | Nota visible en el escenario y aviso en el resumen |
| Xray · k0lmenaTMT | El comentario del resultado (en k0lmenaTMT, el `resultado.txt` de la ejecución) aclara que el caso depende de información faltante |

> *"Investigá el contexto de PROJ-12 y generá los casos"* → ficha de contexto + casos, con lo que falte marcado y las preguntas listas para el PO.

---

## 📚 Documentación del proyecto

El **documentador-proyecto** junta el contexto real del proyecto y lo deja en `input/documentacion/`, para que el analista y los generadores de casos trabajen sobre lo que existe y no sobre suposiciones:

| Fuente | Qué lee |
|---|---|
| Repositorio de la app | El clon local (`REPO_RUTA_LOCAL`): README y docs, validaciones y límites, mensajes, estados, roles y permisos, rutas y contratos de API (solo lectura) |
| Historias | Jira con todos sus comentarios, subtareas, épica, vínculos y bugs |
| Links | Páginas públicas; los privados quedan listados como *No accesible* |
| La aplicación | `npm run mapa-funcional`: páginas, menús, formularios con cada campo, botones y mensajes (solo GET, sin enviar nada) |

Deja una **base del proyecto** (resumen, reglas de negocio, mensajes, estados y permisos, mapa funcional, API y links), un **dossier por historia** (decisiones, código tocado, pantallas, contradicciones y pistas para probar) y un **índice** (`INDICE.md`). Cada dato lleva su fuente (`src/...:línea`, el comentario). El skill `investigacion-contexto` lo lee primero, así que lo aprovechan todos los agentes. `input/documentacion/` no se versiona.

**Incremental**: el documentador guarda qué documentó (commit del repositorio, fuentes de cada documento, fecha de cada historia) en `input/documentacion/.estado.json`. Al pedirle *"Actualizá la documentación"* rehace solo lo que cambió y deja en `cambios.md` los casos que conviene pasar al `revisor-casos`. `npm run actualizar-conocimiento` la puede correr programada.

> *"Documentá el proyecto"* · *"Juntá todo el contexto de PROJ-12 antes de escribir los casos"*

---

## ⚙️ Automatización con k0lmena

[k0lmena](https://github.com/underc0delabs/k0lmena) vive en `herramientas/k0lmena/`. Los agentes *mapper* verifican tus casos contra la app real y escriben la automatización **una sola vez**; después la suite corre las veces que quieras, **sin tokens**. Las carpetas vienen vacías: todo lo generan los mappers para tu aplicación.

Los comandos se pueden correr desde la raíz del repo (el `package.json` de la raíz los delega a k0lmena) o dentro de `herramientas/k0lmena`:

```bash
npm test                          # web + API
npm run test:web                  # también: test:api · test:all
TAGS=@HU-001 npm test             # filtrar por tag (PowerShell: $env:TAGS="@HU-001"; npm test)
npm run report:web                # regenera el reporte HTML (npm test ya lo arma solo; también: report:api)
```

| Suite | Test que pasa | Test que falla |
|---|---|---|
| 🌐 Web | Captura final (+ GIF opcional) | Video completo, captura, error, logs del navegador y de Node, trace de Playwright |
| 🔗 API | Request y response (`Authorization` oculto) | Lo mismo + la validación que falló |

- `@bloqueado`: escenario con un paso que el mapper no pudo verificar; no se ejecuta hasta que se resuelva.
- **Sesión guardada**: `npm run login` abre el navegador, te logueás a mano (sirve con captcha, 2FA o SSO) y la sesión queda en `.auth/`. Con `SESION=si` en el `.env`, `npm test` y el navegador de los agentes arrancan logueados; `@sin-sesion` lo evita en los escenarios que prueban el login.
- Extras: `npm run mapa-funcional` (páginas, formularios y mensajes, para la documentación), `npm run record` y `npm run record:generator` (grabar un flujo), `npm run debug` y auto-healing de locators.

Detalle en [`herramientas/k0lmena/README.md`](herramientas/k0lmena/README.md).

---

## 🗂️ Gestión de pruebas: Xray y k0lmenaTMT

Configurá `GESTION_HERRAMIENTA` (`xray-cloud` · `xray-dc` · `k0lmena-tmt`), `GESTION_PROYECTO` y las credenciales en el `.env`, y pedí:

- *"Subí los casos de HU-001 a Xray en la carpeta 'HU-001 Registro', vinculados a PROJ-12"* → **gestor-pruebas** crea la carpeta, sube los casos y los vincula a la historia.
- *"Creá el ciclo Sprint 5 con esos casos"* → crea el ciclo (Test Execution en Xray) vinculado a la historia.
- *"Subí los resultados de la última corrida al ciclo PROJ-60"* → **publicador-resultados** carga estado, error y evidencias (captura, GIF y video si falló). Sirve para k0lmena y para cualquier framework que genere **JUnit XML** (Cypress, Playwright, pytest, Maven, Jest): el caso se identifica por el `CP-XXX` o la key en el nombre del test.
- *"Actualizá en Xray los casos de HU-001 que cambiaron"* → **gestor-pruebas** corre `sincronizar-casos`: pone al día en la herramienta los casos ya subidos que cambiaron en la planilla o el `.feature`. Los que no cambiaron no se tocan.

La trazabilidad (`output/gestion/<HU>-<herramienta>.json`) evita duplicados. También hay comandos manuales: [`scripts/gestion/README.md`](scripts/gestion/README.md).

### k0lmenaTMT

**k0lmenaTMT** es el gestor de pruebas de la suite k0lmena. Se integra con el **token personal** (`kolm_pat_...`) que se genera en k0lmenaTMT:

```env
GESTION_HERRAMIENTA=k0lmena-tmt
GESTION_PROYECTO=3            # el id numérico del proyecto (está en su URL en k0lmenaTMT)
K0LMENA_TMT_TOKEN=kolm_pat_…
# K0LMENA_TMT_URL=http://localhost:4000/api/v1/mcp   (si no es la de por defecto)
```

- **Las cargas las hace el script, no el agente**: con el token, k0lmenaTMT expone su server MCP. `scripts/gestion` es el cliente: crea carpetas, casos (con pasos, etiquetas, prioridad y tiempo estimado), ciclos y resultados sin pasar cada caso ni cada evidencia por la conversación. Cada escritura de k0lmenaTMT es una propuesta (change-set) que el script aplica, así que todo queda registrado y se puede deshacer desde k0lmenaTMT.
- **El conector MCP `k0lmena-tmt`** queda para **consultar** desde el chat (qué casos o planes hay, estadísticas, los tests que más fallan) y para ajustes puntuales.
- **Keys**: `TC-<id>` (casos) y `CY-<id>` (ciclos): *"publicá en el ciclo CY-45"*, tags `@TC-123` en los escenarios.
- **Casos BDD**: el escenario queda en la pestaña **Gherkin** del caso y el caso como `automated`.
- **Historia**: k0lmenaTMT no se conecta a Jira, así que la historia va como etiqueta del caso y en la descripción del ciclo.
- **Resultados**: cada caso del ciclo registra su estado y su tiempo real, y como evidencia la captura, el GIF, el video si falló y un `resultado.txt` con el error. Hasta 10 MB por archivo.
- **Comprobado**: `npm run doctor` revisa que k0lmenaTMT responda y que el token valga.

> *"Subí a k0lmenaTMT los casos de `casos-HU-001.xlsx` en la carpeta 'HU-001 Registro' y creá el ciclo Sprint 5"* · *"Publicá en k0lmenaTMT los resultados de la última corrida en el ciclo CY-45"*

---

## 🚦 k0lmena en el pipeline (CI)

Las suites de k0lmena corren solas en el pipeline del equipo, sin agentes ni tokens. `npm run ci` deja el archivo listo para **GitHub Actions, GitLab CI, Jenkins o Azure Pipelines**:

```bash
npm run ci -- generar --plataforma github                # → .github/workflows/k0lmena.yml
npm run ci -- generar --plataforma gitlab --suite all    # → .gitlab-ci.yml (web y api)
npm run ci -- generar --plataforma jenkins               # → Jenkinsfile
npm run ci -- generar --plataforma azure --suite api     # → azure-pipelines.yml
```

El pipeline instala k0lmena y Chromium, corre las suites y guarda los reportes como artefacto. Si hay `GESTION_CICLO`, además publica los resultados en Xray o k0lmenaTMT. La plantilla no lleva ningún valor: el `.env` entero va como **secret del pipeline** y llega por `K0LMENA_ENV_FILE`. No pisa un pipeline existente salvo `--forzar`. Detalle por plataforma en [`herramientas/ci/README.md`](herramientas/ci/README.md).

---

## 🐞 Triage de bugs

El **triador-bugs**, antes de cargar un bug, busca si ya existe en Jira o en los bugs locales, detecta **regresiones** de bugs cerrados y sugiere severidad, prioridad, componente, responsable e historia (`scripts/buscar_duplicados.py`). Crear o vincular en Jira, solo con tu confirmación.

> *"¿BUG-008 ya está cargado en Jira?"* · *"Triá los bugs de output/reportes-bug"*

---

## 🧭 Ejecución manual acompañada

Con el skill **`ejecucion-manual`** la conversación te guía por los casos manuales: un caso y un paso por vez, el resultado con un clic, la evidencia, el tiempo real contra el estimado (sin contar las pausas) y el bug redactado en el momento si algo falla. La sesión queda en `output/ejecucion-manual/<HU>/sesion.json`, así que se pausa y se retoma otro día. Al cerrar, el **asistente-ejecucion-manual** arma el informe (ES/EN), los resultados para el informe de ejecución y avisa las inconsistencias; publicar en Xray o k0lmenaTMT, solo con confirmación.

```bash
# en Claude Code
/k0lmenia:ejecucion-manual HU-012
# o a mano
npm run ejecucion-manual -- iniciar --casos output/casos-de-prueba/manuales/casos-HU-012.xlsx --ambiente QA
npm run ejecucion-manual -- estado --sesion output/ejecucion-manual/HU-012
```

---

## 📊 Historial de corridas y portal de informes

- **Historial**: cada corrida de `npm test` guarda sus **últimas 5 corridas** con su evidencia en `herramientas/k0lmena/reports/<suite>/historial/` y cada informe trae la sección **Evolución de las corridas**: qué es nuevo, qué se resolvió, qué sigue y cómo evolucionan los indicadores.
- **Portal de informes**: `output/index.html` abre con un **tablero de inicio**: arriba los indicadores globales (cada suite de `npm test` con su % aprobado y la tendencia de las corridas guardadas, bugs abiertos, informes de hoy y de la semana), una franja de **alertas** con lo que hay que revisar y una **tarjeta por categoría** con el último informe de cada herramienta y su estado. Abajo, el buscador lleva a **Todos los informes**, con filtros por texto, herramienta, historia, estado y fechas, el historial y los links ES/EN. Se arma solo (`npm run portal`) y se abre con doble clic.

### 🌐 Informes en español e inglés

Cada informe tiene una carpeta por idioma y un acceso que abre el que elegiste:

```
output/ejecucion-manual/HU-012/
  informe-ejecucion-manual.html      ← acceso: abre el idioma elegido (español por defecto)
  es/informe-ejecucion-manual.html   ← español
  en/informe-ejecucion-manual.html   ← inglés
  sesion.json analisis.json …        ← la evidencia es la misma para los dos
```

La banderita de arriba a la derecha pasa de un idioma al otro y recuerda tu elección: el portal (`output/index.html`) y los accesos abren siempre ese idioma.

- **Lo que escribe el agente** (veredicto, resumen, hallazgos, recomendaciones) lo traduce el mismo agente al armar el informe: lo pone en un bloque `"en"` del JSON. En los artefactos en Markdown escribe la versión al lado: `BUG-001.en.md`, `analisis-HU-001.en.md`.
- **Contexto y documentación** se escriben en español. Antes de armarlos, Claude pregunta si también los querés en inglés (o lo decide `DOCUMENTACION_EN` en el `.env`).
- **La interfaz** (títulos, columnas, estados, gráficos) la traduce el script con un diccionario (`scripts/i18n/en/`), sin gastar tokens.

---

## 📣 Avisos a Slack y Teams

`npm run avisar -- --titulo "…" --texto "…" --nivel error` publica por webhook (`SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL` en el `.env`); `--desde-cucumber herramientas/k0lmena/reports/web/cucumber-report.json` resume un `npm test`. Lo usa el triador cuando se pide.

---

## 🧪 Evals de los agentes

Los tests cubren los scripts; los **evals** (`evals/`) miden la calidad de lo que generan los agentes. Cada caso les da una historia, un contrato o una observación con **trampas deliberadas** (ambigüedades, contradicciones, mensajes sin definir, límites, secretos) y verifica con chequeos determinísticos que marquen la Falta información, apliquen valores límite, respeten las plantillas y no inventen. Corren en un workspace aislado con `claude -p` y dejan un informe con el puntaje por agente y las **regresiones** contra la corrida anterior:

```bash
npm run evals -- --listar
npm run evals -- --correr --agente generador-casos-manuales
```

**Gastan tokens**: cada caso es una conversación completa, con un tope por caso (`--presupuesto-usd`). `--solo-verificar` revisa salidas ya generadas sin volver a correr el agente.

---

## 🪙 Uso de tokens

`python scripts/metricas_tokens.py` lee las transcripciones de Claude Code de este proyecto (solo los conteos, **nunca el texto**), atribuye el uso a cada agente y arma un informe con el costo estimado por agente, día y modelo, el % leído desde caché y los agentes que más se usan para lo mismo (candidatos a automatizar en k0lmena, que después corre sin tokens).

```bash
python scripts/metricas_tokens.py --nombre octubre --desde 2026-10-01
```

---

## 🤖 Apps con protección anti-bots

Si la app tiene Cloudflare, Akamai, DataDome, Imperva, AWS WAF o un captcha, puede frenar al navegador automatizado. K0lmenIA no intenta esquivarlo. Lo trabaja así:

- **No da falsos fallos.** Cuando la app responde con un desafío o un acceso denegado, el escenario queda **Bloqueado: anti-bots** (también en Xray y k0lmenaTMT). Los agentes frenan y lo reportan.
- **Header de bypass.** Si el equipo de la app crea una excepción para QA, ponés `QA_BYPASS_HEADER` y `QA_BYPASS_TOKEN` en el `.env`. `npm test` y el navegador de los agentes mandan el header **solo a los hosts de la app**, nunca a terceros.
- **Chrome real y ritmo humano.** `NAVEGADOR_CANAL=chrome` usa el Chrome instalado y `RITMO_HUMANO=si` agrega pausas entre acciones.
- **Plan B manual.** `npm run login` abre tu Chrome: resolvés el desafío o el captcha a mano y la sesión queda guardada (`SESION=si`).

La guía para pasarle al equipo de la app está en [`herramientas/k0lmena/tools/navegador/README.md`](herramientas/k0lmena/tools/navegador/README.md). `npm run doctor` revisa la configuración.

---

## 🗄️ Verificación en base de datos

k0lmena trae steps para verificar en las bases configuradas en el `.env` (**PostgreSQL, MySQL / MariaDB, SQL Server y MongoDB**, con varias conexiones con nombre) lo que dejaron guardado tus pruebas. Los mappers los suman a un `.feature` **solo cuando lo pedís** (*"Sumá al escenario de registro la verificación en la base de datos"*) y después corren con `npm test`, sin tokens:

```gherkin
When envío un POST a "/usuarios" con el body: ...
And guardo el campo "id" de la respuesta como "idUsuario"
Then el registro de "usuarios" donde "id" es "{idUsuario}" tiene:
  | campo  | valor  |
  | estado | ACTIVO |
```

> [!IMPORTANT]
> **Solo lectura por defecto**: las consultas corren en transacciones de solo lectura que se descartan, y las columnas sensibles (contraseñas, tokens, tarjetas) se enmascaran. Para preparar o limpiar datos, la conexión necesita `DB_<NOMBRE>_ESCRITURA=si`; con `DB_<NOMBRE>_PRODUCCION=si` nunca escribe. Recomendado: un usuario de base de datos con permisos de solo lectura.

También se usa sin agente: `npm run bd -- conexiones | esquema | existe | consultar`.

---

## 🔌 Conectores MCP

| Conector | Para qué | Autenticación |
|---|---|---|
| `playwright` · `playwright-headless` | Navegador para el ejecutor E2E, el web-mapper y el documentador | Activo por defecto |
| `atlassian` | **Jira**: historias, criterios, comentarios y vínculos | Activo por defecto: tu cuenta (OAuth) o API token |
| `k0lmena-tmt` | Consultas en k0lmenaTMT (las cargas, por `gestion.py`) | Token personal |

Claude Code arranca directo, sin pedir aprobar conectores: vienen activos Playwright y Atlassian. k0lmenaTMT lo activa cada QA con un comando. Ninguno lleva secretos: las credenciales se leen del `.env`. Guía completa en [`CONECTORES.md`](CONECTORES.md).

```bash
npm run conector                            # lista los conectores y cuáles tenés activos
npm run conector -- activar k0lmena-tmt     # queda solo para vos; reiniciá Claude Code
```

`npm run conector -- listar --html` deja `output/conectores/estado.html` con el estado de cada conector, sin mostrar valores del `.env`. `npm run doctor` te dice qué variables le faltan a cada conector activo.

---

## 🚀 ¿Necesitás más?

K0lmenIA Light trae lo elemental del día a día de QA. Cuando el equipo necesita más, hay dos planes pagos:

| Plan | Qué suma | Precio |
|---|---|---|
| **K0lmenIA Pro** | Todos los agentes para probar (101 en total): accesibilidad, rendimiento, seguridad, performance, mobile, regresión visual, exploratorias, análisis de fallos, causa raíz, e-commerce, IA y chatbots, analytics, datos y más, con más conectores (Confluence, Figma, GitHub, GitLab, Linear, observabilidad y otros) | USD 29 por usuario por mes |
| **K0lmenIA Empresa** | Todo Pro más métricas, tablero de calidad, trazabilidad, evidencias de auditoría, presentaciones, onboarding, SAP, Salesforce y Dynamics, resumen diario, planificación de capacidad y gestión en QMetry, AIO Tests, Zephyr Scale y Azure DevOps | USD 590 por mes hasta 10 personas |

Más información en **https://k0lmena.com/k0lmenia/**.

---

## 📎 Referencia

<details>
<summary><b>Un flujo completo, de punta a punta</b></summary>

```
0. "Investigá el contexto de PROJ-12"                  → ficha de contexto + Falta información (FI-XX)
1. "Analizá HU-001"                                    → preguntas para el PO
2. "Generá los casos de HU-001"                        → casos-HU-001.xlsx + cobertura
3. "Revisá los casos de HU-001"                        → puntaje, duplicados y tiempo de ejecución
4. "Subí los casos a Xray y creá el ciclo Sprint 5"    → casos y ciclo en Xray
5. "Automatizá en k0lmena los casos de HU-001"         → .feature + steps + locators
6. npm test                                           → reporte con evidencias (sin tokens)
7. "Subí los resultados al ciclo del Sprint 5"         → estados y evidencias en Xray
8. "Acompañame a ejecutar los casos manuales"          → sesión guiada + informe de ejecución manual
```
</details>

<details>
<summary><b>Convenciones</b></summary>

| Elemento | Formato |
|---|---|
| Historias · criterios | `HU-001` · `CA1` |
| Casos manuales · de API | `CP-001` · `CP-API-001` |
| Bugs | `BUG-001` |
| Falta información | `FI-01` (por historia) · tags `@falta-info @FI-01` |
| Severidad y prioridad | Crítica · Alta · Media · Baja |
| Estado de un caso | N/A · Pendiente · En ejecución · Aprobado · Fallido · Bloqueado |
| Tags en k0lmena | Feature: `@HU-001 @web` · Scenario: `@CP-001` (`@smoke` si es crítico) · `@bloqueado` |
| Automatización | `<tipo>/features/HU-001-<slug>.feature` · `steps/HU-001.steps.ts` · `locators/HU-001.locators.ts` |
</details>

<details>
<summary><b>Estructura del repositorio</b></summary>

```
k0lmenIA/
├── CLAUDE.md               Contexto y estándares (Claude Code lo lee siempre; corto a propósito)
├── REFERENCIA.md           Salida de cada agente, scripts y nombres de archivos (se lee a pedido)
├── AGENTES.md              Catálogo de agentes: skills, herramientas, conectores y salidas
├── ARQUITECTURA.md         Cómo crece el repo
├── CONECTORES.md           Cómo activar los conectores MCP
├── CHANGELOG.md            Cambios de cada versión
├── LICENSE                 Licencia MIT
├── .env.example            Plantilla de variables (copiar a .env)
├── .mcp.json               Conectores MCP (sin secretos; activos según settings)
├── package.json            Atajos para correr k0lmena desde la raíz (npm test…)
├── docs/                   Documentación web, PDF y diagramas
├── tests/                  Tests de los scripts del repo (pytest y node --test)
├── evals/                  Evals de los agentes: casos con trampas, insumos y chequeos
├── .github/workflows/      CI (tests), plugin, documentación y evals (manuales)
├── .claude/
│   ├── agents/             Los 13 agentes
│   ├── skills/             Los 13 skills
│   └── settings.json       Conectores habilitados y permisos del proyecto
├── input/                  historias/ documentacion/ api/ bugs/ (ver input/README.md)
├── output/                 Lo que generan los agentes (contexto/, casos, reportes, mapeos…)
├── plantillas/             Bug, planilla de casos, cobertura
├── scripts/                Casos, reportes HTML, Newman, ejecución manual, portal y doctor
│   ├── gestion/            Xray Cloud, Xray Server/DC y k0lmenaTMT
│   └── mcp/                Lanzadores de los conectores MCP (leen el .env)
└── herramientas/
    ├── newman/             Colecciones de Postman, Bruno e Insomnia
    ├── ci/                 Plantillas de pipeline (GitHub, GitLab, Jenkins, Azure)
    └── k0lmena/            web/ api/ reports/
```
</details>

<details>
<summary><b>Problemas frecuentes</b></summary>

| Problema | Solución |
|---|---|
| Un agente nuevo no aparece | Reiniciá Claude Code. |
| La suite web falla sin URL | Falta el `.env` de la raíz: `cp .env.example .env` y completalo. |
| `npm test` corre 0 escenarios | Todavía no automatizaste nada o `TAGS` no coincide. |
| Un escenario nunca se ejecuta | Tiene `@bloqueado`; el motivo está en un comentario arriba. |
| Una carpeta de Xray sale como `C:/Program Files/Git/…` | En Git Bash escribí las carpetas sin `/` inicial. |
| ¿Los tests verifican la base de datos siempre? | No: las verificaciones de BD se agregan a un `.feature` solo cuando las pedís; sin `DB_CONEXIONES`, la suite corre igual. |
| Un conector MCP no conecta | Corré `npm run doctor`: dice qué variable falta en el `.env`. Atlassian se autoriza desde `/mcp`. |
| No sé qué me falta instalar | `npm run doctor` revisa Python, Node, k0lmena, Playwright, Newman, las fuentes, el `.env`, las integraciones, los conectores y git (`--seccion env` para revisar solo una parte). |
| Un agente devuelve "Necesito que confirmes" | Es a propósito: los agentes no pueden preguntar a mitad del trabajo. Respondé y Claude lo continúa. |
</details>

<details>
<summary><b>Cómo extender el proyecto</b></summary>

- **Agente**: un `.md` en `.claude/agents/` con `name` y `description` (es lo que usa Claude Code para decidir cuándo invocarlo) y el cuerpo en español: rol, entradas, proceso, salida y reglas.
- **Skill**: una carpeta en `.claude/skills/` con su `SKILL.md`.
- **Conector**: una entrada en `.mcp.json`, sin secretos; los tokens se leen del `.env` con un script de `scripts/mcp/`.
- **Herramienta**: una subcarpeta en `herramientas/` con su README.
- **Tests del repo**: `python -m pytest tests` y `npm run test:repo` (corren también en CI, en Ubuntu y Windows). Sumá un test cuando cambies un script.
- **Documentación**: el sitio es [`docs/index.html`](docs/index.html), publicado en https://underc0delabs.github.io/k0lmenIA/ (GitHub Pages desde `docs/`), con su versión en inglés en [`docs/en/index.html`](docs/en/index.html) (mismos `id` de sección; los diagramas en inglés están en `docs/diagramas/en/`). `node docs/generar.js` regenera los diagramas y los dos PDF. Si cambiás la página en español, actualizá también la inglesa.

Más detalle en [`ARQUITECTURA.md`](ARQUITECTURA.md).
</details>

---

## Licencia

**MIT** — © 2026 **QARMY**. Podés usarlo, modificarlo y compartirlo libremente; se entrega sin garantías. k0lmena es un proyecto open source de **Danilo Vezzoni**.

<div align="center">
<br>
Hecho con 🪖 por la comunidad de <b>Underc0de</b>
</div>

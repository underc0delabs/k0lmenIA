# Conectores MCP

Cómo conectar k0lmenIA por MCP a **Jira y Confluence** (Atlassian), **Figma**, el **repositorio de la aplicación** (GitHub, GitLab, Azure Repos o Bitbucket), **otras herramientas de gestión de proyecto** (Linear, ClickUp, monday.com, Asana, Trello, Notion, YouTrack y Shortcut), **QMetry**, **AIO Tests**, **k0lmenaTMT**, **Azure DevOps** y **Appium**. Xray se integra sin MCP (ver abajo).

> **La forma fácil:** corré `npm run configurar` en una terminal. Te pregunta qué herramientas usa tu equipo, pide solo sus datos y activa los conectores que hagan falta. Lo de abajo es el detalle, para configurar a mano o algo puntual.

Claude Code **arranca directo, sin pedir aprobar conectores**: `.mcp.json` trae solo los que vienen habilitados para todos (Playwright y **Atlassian: Jira y Confluence**). Los demás están en un catálogo (`scripts/mcp/catalogo.json`) y cada persona activa los que usa con `npm run conector -- activar <nombre>`. Ninguno lleva secretos: las credenciales se leen del `.env` de la raíz o se autorizan con tu cuenta (OAuth).

## Resumen

```
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| Conector                         | Herramienta                             | Server MCP                              | Tipo    | Transporte   | Habilitado por defecto   |
+==================================+=========================================+=========================================+=========+==============+==========================+
| playwright · playwright-headless | Navegador (ejecutor-e2e, web-mapper,    | @playwright/mcp                         | Oficial | stdio        | Sí                       |
|                                  | explorador-web, analista-               |
|                                  | accesibilidad)                          |                                         |         |              |                          |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| atlassian                        | Jira y Confluence (Cloud)               | Atlassian Rovo MCP Server (remoto)      | Oficial | http         | Sí                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| azure-devops                     | Azure DevOps (Boards, Test Plans, Wiki) | @azure-devops/mcp (Microsoft)           | Oficial | stdio        | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| figma                            | Figma (diseños)                         | Figma MCP Server remoto                 | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| figma-desktop                    | Figma (app de escritorio)               | Figma MCP Server de escritorio (local)  | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| github                           | GitHub (repositorio de la app)          | GitHub MCP Server remoto (solo lectura) | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| gitlab                           | GitLab (repositorio de la app)          | GitLab MCP Server (/api/v4/mcp)         | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| linear                           | Linear (historias)                      | Linear MCP Server (remoto, solo         | Oficial | http         | No                       |
|                                  |                                         | lectura)                                |         |              |                          |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| clickup                          | ClickUp (historias)                     | ClickUp MCP Server (remoto)             | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| monday                           | monday.com (historias)                  | monday.com MCP Server (remoto)          | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| asana                            | Asana (historias)                       | Asana MCP Server V2 (remoto)            | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| trello                           | Trello (historias)                      | Trello MCP Server (remoto, Atlassian)   | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| notion                           | Notion (documentación y backlogs)       | Notion MCP Server (remoto)              | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| youtrack                         | YouTrack (historias)                    | MCP integrado de YouTrack (tu sitio)    | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| shortcut                         | Shortcut (historias)                    | Shortcut MCP Server (remoto)            | Oficial | http         | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| qmetry                           | QMetry Test Management                  | @smartbear/mcp                          | Oficial | stdio        | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| qtm4j                            | QMetry Test Management for Jira (QTM4J) | @smartbear/mcp                          | Oficial | stdio        | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| aio-tests                        | AIO Tests for Jira                      | Server remoto de AIO Tests (por tenant) | Oficial | stdio        | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| k0lmena-tmt                      | k0lmenaTMT                              | Server MCP de k0lmenaTMT (local o       | Oficial | http         | No                       |
|                                  |                                         | propio)                                 |         |              |                          |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| appium-mcp                       | Appium (mobile-mapper)                  | appium-mcp                              | Oficial | stdio        | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| salesforce                       | Salesforce (probador-salesforce)        | @salesforce/mcp (Salesforce DX)         | Oficial | stdio        | No                       |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
| scalar                           | Scalar (probador-scalar): tu API        | Scalar MCP (remoto, generado desde el   | Oficial | http         | No                       |
|                                  |                                         | OpenAPI)                                |         |              |                          |
+----------------------------------+-----------------------------------------+-----------------------------------------+---------+--------------+--------------------------+
```

> **Para crear carpetas, casos, ciclos y publicar resultados no hace falta ningún MCP**: lo hace la integración propia `scripts/gestion/` (agentes `gestor-pruebas` y `publicador-resultados`), que soporta **Xray Cloud, Xray Server/Data Center, QTM4J y AIO Tests** con sus APIs oficiales. Configuración en [`scripts/gestion/README.md`](scripts/gestion/README.md). La excepción es **Azure DevOps**, que se integra por su MCP (ver [Azure DevOps](#azure-devops)). Los MCP de esta página son opcionales, para consultar o explorar la herramienta desde el chat.

---

## Qué configurar según tu equipo

Todos los conectores ya están en `.mcp.json` y todas las variables, en `.env.example` (un bloque por herramienta, comentado). Cada QA completa solo lo de las herramientas que usa su equipo:

```
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Si tu equipo usa…         | Conector / integración                | Variables en el `.env`                   | Habilitado por defecto          |
+===========================+=======================================+==========================================+=================================+
| Jira y Confluence         | `atlassian` (MCP)                     | Ninguna con OAuth; con token:            | Sí                              |
|                           |                                       | `ATLASSIAN_MCP_AUTENTICACION=token`,     |                                 |
|                           |                                       | `JIRA_EMAIL`, `JIRA_API_TOKEN`           |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Azure DevOps              | `azure-devops` (MCP)                  | `ADO_ORGANIZACION`, `ADO_PAT`,           | No                              |
|                           |                                       | `ADO_PROYECTO`                           |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Figma                     | `figma` o `figma-desktop` (MCP)       | Ninguna (OAuth)                          | No                              |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Repositorio en GitHub     | `github` (MCP)                        | `REPO_PROVEEDOR=github`, `REPO_NOMBRE`,  | No                              |
|                           |                                       | `GITHUB_TOKEN`                           |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Repositorio en GitLab     | `gitlab` (MCP)                        | `REPO_PROVEEDOR=gitlab`, `REPO_NOMBRE`,  | No                              |
|                           |                                       | `GITLAB_URL`; `GITLAB_TOKEN` opcional    |                                 |
|                           |                                       | (OAuth)                                  |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Repositorio en Azure      | `azure-devops` (MCP)                  | `REPO_PROVEEDOR=azure-repos`,            | No                              |
| Repos                     |                                       | `REPO_NOMBRE` + las de Azure DevOps      |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Repositorio en Bitbucket  | `atlassian` (MCP)                     | `REPO_PROVEEDOR=bitbucket`,              | Sí (con token)                  |
| Cloud                     |                                       | `REPO_NOMBRE`,                           |                                 |
|                           |                                       | `ATLASSIAN_MCP_AUTENTICACION=token` +    |                                 |
|                           |                                       | las de Jira                              |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Linear                    | `linear` (MCP)                        | Ninguna (OAuth); opcional                | No                              |
|                           |                                       | `LINEAR_API_KEY`                         |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| ClickUp                   | `clickup` (MCP)                       | Ninguna (OAuth)                          | No                              |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| monday.com                | `monday` (MCP)                        | Ninguna (OAuth); opcional                | No                              |
|                           |                                       | `MONDAY_API_TOKEN`                       |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Asana                     | `asana` (MCP)                         | `ASANA_CLIENT_ID`, `ASANA_CLIENT_SECRET` | No                              |
|                           |                                       | (app MCP propia)                         |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Trello                    | `trello` (MCP)                        | Ninguna (OAuth)                          | No                              |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Notion                    | `notion` (MCP)                        | Ninguna (OAuth)                          | No                              |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| YouTrack                  | `youtrack` (MCP)                      | `YOUTRACK_URL`, `YOUTRACK_TOKEN`         | No                              |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Shortcut                  | `shortcut` (MCP)                      | Ninguna (OAuth)                          | No                              |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Xray Cloud                | `scripts/gestion` (sin MCP)           | `GESTION_HERRAMIENTA=xray-cloud`,        | Listo al completar el `.env`    |
|                           |                                       | `GESTION_PROYECTO`,                      |                                 |
|                           |                                       | `XRAY_CLOUD_CLIENT_ID`,                  |                                 |
|                           |                                       | `XRAY_CLOUD_CLIENT_SECRET` + las de Jira |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| Xray Server / Data Center | `scripts/gestion` (sin MCP)           | `GESTION_HERRAMIENTA=xray-dc`,           | Listo al completar el `.env`    |
|                           |                                       | `GESTION_PROYECTO`, `XRAY_DC_URL`,       |                                 |
|                           |                                       | `XRAY_DC_TOKEN` (o `XRAY_DC_USER` +      |                                 |
|                           |                                       | `XRAY_DC_PASSWORD`)                      |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| QMetry para Jira (QTM4J)  | `scripts/gestion` + `qtm4j` (MCP)     | `GESTION_HERRAMIENTA=qtm4j`,             | `scripts/gestion`: sí · MCP: no |
|                           |                                       | `GESTION_PROYECTO`, `QTM4J_API_KEY`      |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| QMetry Test Management    | `qmetry` (MCP)                        | `QMETRY_API_KEY`                         | No                              |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| AIO Tests                 | `scripts/gestion` + `aio-tests` (MCP) | `GESTION_HERRAMIENTA=aio`,               | `scripts/gestion`: sí · MCP: no |
|                           |                                       | `GESTION_PROYECTO`, `AIO_API_TOKEN`,     |                                 |
|                           |                                       | `AIO_MCP_URL`                            |                                 |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
| k0lmenaTMT                | `k0lmena-tmt` (MCP)                   | `K0LMENA_TMT_TOKEN`                      | No                              |
+---------------------------+---------------------------------------+------------------------------------------+---------------------------------+
```

**Activar los opcionales** (Azure DevOps, Figma, GitHub, GitLab, Linear, ClickUp, monday.com, Asana, Trello, Notion, YouTrack, Shortcut, QMetry, AIO Tests, k0lmenaTMT, Appium):

```bash
npm run conector                              # lista los conectores y cuáles tenés activos
npm run conector -- activar azure-devops      # también varios: activar azure-devops figma
npm run conector -- desactivar azure-devops
```

`activar` lo registra con `claude mcp add-json --scope local`: queda **solo para vos, en este proyecto**, no toca ningún archivo versionado y no dispara avisos al iniciar. Si le faltan variables en el `.env`, te avisa cuáles. Después reiniciá Claude Code y verificá con `/mcp`; `npm run doctor` revisa las variables de todos los conectores activos. **Las integraciones de `scripts/gestion`** (Xray, QTM4J y AIO) no necesitan activarse: funcionan en cuanto el `.env` tiene sus variables.

---

## Pasos para activar un conector

1. **Completá sus variables en el `.env`** de la raíz (están en `.env.example` y en la sección de cada conector). `atlassian` y `figma` no usan variables: se autorizan con tu cuenta.
2. **Activalo** (si no es de los que vienen habilitados): `npm run conector -- activar <nombre>`.
3. **Reiniciá Claude Code** y verificá la conexión con `/mcp`.

**Cómo llegan los tokens al server sin quedar en `.mcp.json`:** los conectores con credenciales no llaman al server directo, sino a un script de `scripts/mcp/` que lee las variables del entorno o, si no están, del `.env`, y arranca el server pasándoselas solo por variable de entorno:

```
+--------------------------+---------------------------------+------------------------------------------+
| Script                   | Conectores                      | Qué hace                                 |
+==========================+=================================+==========================================+
| `playwright.js`          | playwright, playwright-headless | Arranca Playwright con la carpeta de     |
|                          |                                 | evidencias y, si existe el `.env`, con   |
|                          |                                 | `--secrets .env` (oculta esos valores en |
|                          |                                 | las respuestas)                          |
+--------------------------+---------------------------------+------------------------------------------+
| `con-env.js`             | qmetry, qtm4j, appium-mcp       | Pasa al server las variables que pide la |
|                          |                                 | entrada (y nada más del `.env`)          |
+--------------------------+---------------------------------+------------------------------------------+
| `azure-devops.js`        | azure-devops                    | Arma el PAT en el formato del server y   |
|                          |                                 | elige las áreas habilitadas              |
+--------------------------+---------------------------------+------------------------------------------+
| `salesforce.js`          | salesforce                      | Apunta a la org de `SALESFORCE_ORG` (de  |
|                          |                                 | la lista autorizada) y acota el server a |
|                          |                                 | SOQL de solo lectura y tests de Apex     |
+--------------------------+---------------------------------+------------------------------------------+
| `aio-tests.js`           | aio-tests                       | Conecta con la URL de tu tenant vía      |
|                          |                                 | `mcp-remote`, con el token en el header  |
+--------------------------+---------------------------------+------------------------------------------+
| `k0lmena-tmt-headers.js` | k0lmena-tmt                     | Devuelve el header `Authorization` (es   |
|                          |                                 | un `headersHelper`)                      |
+--------------------------+---------------------------------+------------------------------------------+
| `atlassian-headers.js`   | atlassian                       | Con `ATLASSIAN_MCP_AUTENTICACION=token`  |
|                          |                                 | arma el header con el API token; con     |
|                          |                                 | `oauth` (por defecto) no agrega nada     |
+--------------------------+---------------------------------+------------------------------------------+
| `github-headers.js`      | github                          | Devuelve el token como `Bearer`, el modo |
|                          |                                 | solo lectura y los toolsets (es un       |
|                          |                                 | `headersHelper`)                         |
+--------------------------+---------------------------------+------------------------------------------+
| `gitlab-headers.js`      | gitlab                          | Elige los toolsets y, si hay             |
|                          |                                 | `GITLAB_TOKEN`, agrega el `Bearer`; sin  |
|                          |                                 | token, OAuth desde `/mcp`                |
+--------------------------+---------------------------------+------------------------------------------+
| `bearer-headers.js`      | linear, monday, youtrack        | Manda el token del `.env` como `Bearer`; |
|                          |                                 | en linear y monday es opcional (sin      |
|                          |                                 | token, OAuth)                            |
+--------------------------+---------------------------------+------------------------------------------+
| `lanzar.js`              | todos los de `npx`              | Versiones fijas de cada paquete,         |
|                          |                                 | lanzamiento en Windows y cierre del      |
|                          |                                 | árbol de procesos                        |
+--------------------------+---------------------------------+------------------------------------------+
| `leer-env.js`            | todos                           | Lee el `.env` con las mismas reglas que  |
|                          |                                 | k0lmena y `scripts/_env.py`              |
+--------------------------+---------------------------------+------------------------------------------+
```

Si falta una variable, el script corta enseguida con un mensaje claro (por ejemplo *"qtm4j: falta QTM4J_API_KEY en el .env de la raíz"*), que se ve en `/mcp`.

**Versiones fijas**: los servers que se instalan con `npx` (Playwright, Azure DevOps, QMetry/QTM4J, Appium y `mcp-remote` de AIO) usan una versión concreta, definida en `scripts/mcp/lanzar.js`, nunca `@latest`: así una versión nueva no revisada no recibe tus tokens sin que alguien lo decida. Para actualizar, cambiá la versión ahí (para probar una sin tocar el archivo: `PLAYWRIGHT_MCP_MCP_VERSION=0.0.84`, `AZURE_DEVOPS_MCP_MCP_VERSION=…`, etc.).

> Nunca pongas el valor real de un token en `.mcp.json`. Para sumar un conector nuevo con credenciales, usá `con-env.js` o un script propio en `scripts/mcp/`.

---

## Xray

Xray **no tiene un server MCP oficial** y los comunitarios no cubren carpetas, vínculos con historias ni evidencias. Por eso Xray (Cloud y Server/Data Center) se integra con los scripts propios de `scripts/gestion/`, sobre la API oficial de Xray, y no tiene entrada en `.mcp.json`. Ver [`scripts/gestion/README.md`](scripts/gestion/README.md).

## QMetry

Usa el server oficial de SmartBear, [`@smartbear/mcp`](https://github.com/SmartBear/smartbear-mcp), que requiere **Node.js 20+**. Hay dos conectores según qué producto de QMetry uses; activá solo el tuyo.

**`qmetry` — QMetry Test Management (standalone):**

```
+-----------------+-------------+---------------------------------------+
| Variable        | Obligatoria | Descripción                           |
+=================+=============+=======================================+
| QMETRY_API_KEY  | Sí          | Open API Key de QMetry                |
+-----------------+-------------+---------------------------------------+
| QMETRY_BASE_URL | No          | Por defecto                           |
|                 |             | https://testmanagement.qmetry.com;    |
|                 |             | cambiala si tu instancia usa otra URL |
+-----------------+-------------+---------------------------------------+
```

**`qtm4j` — QMetry Test Management for Jira (Cloud):**

```
+--------------------------+---------------+------------------------------------------+
| Variable                 | Obligatoria   | Descripción                              |
+==========================+===============+==========================================+
| QTM4J_API_KEY            | Sí            | API Key de QTM4J                         |
+--------------------------+---------------+------------------------------------------+
| QTM4J_BASE_URL           | No            | US (por defecto):                        |
|                          |               | https://qtmcloud.qmetry.com · Australia: |
|                          |               | https://syd-qtmcloud.qmetry.com ·        |
|                          |               | Europa: https://eu-                      |
|                          |               | qtm4j-cloud.qmetry.com                   |
+--------------------------+---------------+------------------------------------------+
| QTM4J_AUTOMATION_API_KEY | No            | Solo para las herramientas de            |
|                          |               | automatización; vacía las deshabilita    |
+--------------------------+---------------+------------------------------------------+
```

Las dos entradas ejecutan `scripts/mcp/con-env.js`, que toma estas variables del entorno o, si no están, del `.env`.

## AIO Tests

Usa el server MCP **oficial** de AIO Tests, que es remoto (no hay que instalar nada). Cada tenant tiene su propia URL.

```
+---------------+-------------+------------------------------------------+
| Variable      | Obligatoria | Descripción                              |
+===============+=============+==========================================+
| AIO_MCP_URL   | Sí          | URL del server; se copia de **My         |
|               |             | Settings > MCP Authorization** en AIO    |
|               |             | Tests                                    |
+---------------+-------------+------------------------------------------+
| AIO_API_TOKEN | Sí          | Public API Token, de **My Settings > API |
|               |             | Token**                                  |
+---------------+-------------+------------------------------------------+
```

La entrada ejecuta `scripts/mcp/aio-tests.js`, que toma las dos variables del `.env` y se conecta al server remoto con [`mcp-remote`](https://github.com/geelen/mcp-remote) (por `npx`), pasando el token solo por variable de entorno. Como la URL es propia de cada tenant, no puede ir fija en `.mcp.json`.

**Alternativa sin token (OAuth):** AIO Tests también acepta OAuth 2.1 si usás la versión Forge de la app. En ese caso registrá el server remoto solo para vos (`claude mcp add --transport http --scope local aio-tests <tu AIO_MCP_URL>`), que tiene prioridad sobre la entrada del proyecto, y autorizá desde `/mcp` > *Authenticate*.

---

## k0lmenaTMT

Conecta los agentes con **k0lmenaTMT** por su server MCP, para consultar desde el chat (casos, planes, ejecuciones, estadísticas, los tests que más fallan) y hacer ajustes puntuales. Se autentica con un **token personal** (`kolm_pat_...`) que se genera en k0lmenaTMT.

> **Las cargas no van por el conector**: subir casos, crear ciclos y publicar resultados con evidencias lo hace `scripts/gestion` con `GESTION_HERRAMIENTA=k0lmena-tmt` (lo usan `gestor-pruebas` y `publicador-resultados`). Usa el mismo server MCP y el mismo token, pero sin pasar cada caso ni cada evidencia por la conversación. Ver `scripts/gestion/README.md`.

```
+-------------------+-------------+------------------------------------------+
| Variable          | Obligatoria | Descripción                              |
+===================+=============+==========================================+
| K0LMENA_TMT_TOKEN | Sí          | Token personal de k0lmenaTMT. Va en el   |
|                   |             | .env de la raíz                          |
+-------------------+-------------+------------------------------------------+
| K0LMENA_TMT_URL   | No          | Por defecto                              |
|                   |             | http://localhost:4000/api/v1/mcp; para   |
|                   |             | otra URL, definila en el .env antes de   |
|                   |             | activar (o en el entorno)                |
+-------------------+-------------+------------------------------------------+
```

**El token se lee del `.env`**: la entrada usa `headersHelper`, que ejecuta `scripts/mcp/k0lmena-tmt-headers.js` cada vez que Claude Code se conecta. El script toma `K0LMENA_TMT_TOKEN` del entorno o, si no está, del `.env`, y arma el header `Authorization: Bearer …`. El token nunca queda en `.mcp.json`.

Para activarlo:

1. Agregá `K0LMENA_TMT_TOKEN=<tu token>` al `.env` de la raíz.
2. Activalo: `npm run conector -- activar k0lmena-tmt`.
3. Con k0lmenaTMT levantado, reiniciá Claude Code y verificá con `/mcp`.

> No uses `claude mcp add ... --header "Authorization: Bearer <token>"`: deja el token escrito en la configuración de Claude Code.

Ejemplos de uso:

> *"Subí a k0lmenaTMT los casos de `casos-HU-001.xlsx` y creá el ciclo Sprint 5"* (gestor-pruebas, por `gestion.py`) · *"Publicá en k0lmenaTMT los resultados de la última corrida en el ciclo CY-45"* (publicador-resultados) · *"¿Cuáles son los tests que más fallan en k0lmenaTMT?"* (conector MCP)

---

## Atlassian: Jira y Confluence

El conector `atlassian` es el server MCP **oficial de Atlassian** (Rovo MCP Server). Con **una sola conexión** da acceso a **Jira y Confluence** Cloud, con los permisos de tu usuario: los agentes pueden leer historias y sus criterios desde Jira y la documentación funcional desde páginas de Confluence, en lugar de copiarlas a `input/`.

**Viene habilitado por defecto.** Tiene dos formas de autenticarse, que se eligen con `ATLASSIAN_MCP_AUTENTICACION` en el `.env`:

- **`oauth` (por defecto, recomendado para uso interactivo)**: no usa token. La primera vez ejecutá `/mcp`, elegí `atlassian` y autorizá el acceso con tu cuenta en el navegador.
- **`token`**: usa `JIRA_EMAIL` y `JIRA_API_TOKEN` (las mismas que usa la integración con Xray Cloud) y arma el header `Authorization: Basic …`. Para una cuenta de servicio, poné su API key en `ATLASSIAN_API_KEY` y se envía como `Bearer`. **Requisito**: un admin de Atlassian tiene que habilitar el API token en *Atlassian Administration > Rovo > Rovo MCP server > Authentication*. El token se crea en https://id.atlassian.com/manage-profile/security/api-tokens.

La entrada de `.mcp.json` usa `headersHelper` (`scripts/mcp/atlassian-headers.js`): con `oauth` no agrega nada y con `token` arma el header leyendo el `.env`. El token nunca queda en `.mcp.json`.

Si tu organización restringe las apps de IA, un admin de Atlassian tiene que habilitar el Rovo MCP Server para el sitio.

**Bitbucket Cloud**: el mismo conector da acceso a los repositorios de Bitbucket Cloud (archivos, commits y pull requests), pero **solo con `ATLASSIAN_MCP_AUTENTICACION=token`** (Bitbucket todavía no acepta OAuth en el Rovo MCP Server) y con un workspace vinculado a la organización de Atlassian. Lo usa el `documentador-proyecto` (ver [Repositorio de la aplicación](#repositorio-de-la-aplicación)).

Ejemplos de uso:

> *"Leé la historia PROJ-12 de Jira y analizala."* · *"Generá los casos de PROJ-12 usando la página de Confluence 'Reglas de facturación' como documentación."*

---

## Figma

El conector `figma` es el server MCP **oficial de Figma**. Les da a los agentes el contexto de un diseño a partir de un **link a un frame, una capa o un archivo**: textos, componentes, estados y capturas. Sirve para diseñar casos de UI (textos esperados, validaciones visibles, estados vacíos y de error), comparar la app contra el diseño y dar contexto al `web-mapper`.

- **Requisitos**: un asiento **Full** o **Dev** de Figma (otros asientos tienen límites de uso) y permiso de edición o lectura sobre el archivo.
- **No usa token**: se autentica con tu cuenta de Figma por OAuth.
- Para activarlo, cualquiera de estas dos opciones:
  - **Plugin oficial (recomendado por Figma)**: `claude plugin install figma@claude-plugins-official`, reiniciá Claude Code, entrá a `/plugin` → *Installed* → `figma` y autorizá el acceso. Incluye el server y skills de Figma.
  - **Solo el server**: `npm run conector -- activar figma` (o `figma-desktop` para la app de escritorio), reiniciá y autorizá desde `/mcp`.
- **Variante de escritorio** (`figma-desktop`): para organizaciones que no permiten el server remoto. Requiere la app de escritorio de Figma con el server MCP habilitado (modo Dev → panel derecho) y se conecta a `http://127.0.0.1:3845/mcp`.

Ejemplos de uso:

> *"Generá los casos de HU-001 tomando como referencia este diseño: https://www.figma.com/design/…?node-id=…"* · *"Compará la pantalla de registro de https://tu-app.com con el diseño de Figma y reportá las diferencias."*

---

## Azure DevOps

Usa el server MCP **oficial de Microsoft**, [`@azure-devops/mcp`](https://github.com/microsoft/azure-devops-mcp) (requiere **Node.js 20+**). Con una sola conexión los agentes pueden:

- **Consultar historias** (*User Story*, *Product Backlog Item*, *Bug*) de Azure Boards con sus comentarios, tareas hijas, padre (*Feature* / *Epic*) y vínculos, y leer la **Wiki** del proyecto. Lo usa el skill `investigacion-contexto`, igual que Jira y Confluence.
- **Leer el repositorio en Azure Repos** (dominio `repositories`, solo lectura para el `documentador-proyecto`): archivos y carpetas, pull requests con sus comentarios y búsqueda de commits.
- **Gestionar pruebas en Azure Test Plans**: crear planes y suites, crear casos de prueba (*Test Case*) con sus pasos y resultado esperado, vincularlos a la historia (*Tests* / *Tested By*) y agregarlos a una suite. Lo hace el agente `gestor-pruebas`.

```
+-------------------+---------------+------------------------------------------+
| Variable          | Obligatoria   | Descripción                              |
+===================+===============+==========================================+
| ADO_ORGANIZACION  | Sí            | Nombre de la organización, el de         |
|                   |               | `https://dev.azure.com/<organizacion>`   |
|                   |               | (no la URL)                              |
+-------------------+---------------+------------------------------------------+
| ADO_PAT           | Sí (con PAT)  | Personal Access Token. Va en el .env de  |
|                   |               | la raíz                                  |
+-------------------+---------------+------------------------------------------+
| ADO_PROYECTO      | No            | Proyecto por defecto; si falta, se       |
|                   |               | indica en cada pedido                    |
+-------------------+---------------+------------------------------------------+
| ADO_EQUIPO        | No            | Equipo por defecto (backlog,             |
|                   |               | iteraciones)                             |
+-------------------+---------------+------------------------------------------+
| ADO_AUTENTICACION | No            | `pat` (por defecto), `interactive`       |
|                   |               | (login en el navegador) o `azcli`        |
|                   |               | (sesión de `az login`)                   |
+-------------------+---------------+------------------------------------------+
| ADO_TENANT        | No            | Tenant de Microsoft Entra, solo con      |
|                   |               | `interactive` o `azcli`                  |
+-------------------+---------------+------------------------------------------+
| ADO_DOMINIOS      | No            | Áreas habilitadas. Por defecto: `core    |
|                   |               | work work-items repositories test-plans  |
|                   |               | wiki search`; sumá `pipelines` si la     |
|                   |               | necesitás                                |
+-------------------+---------------+------------------------------------------+
```

Igual que k0lmenaTMT, **la configuración se lee del `.env`**: la entrada ejecuta `scripts/mcp/azure-devops.js`, que toma las variables del entorno o, si no están, del `.env`, y arranca el server pasándole el PAT solo por variable de entorno. El token nunca queda en `.mcp.json`.

**El PAT** se crea en Azure DevOps > *User settings* > *Personal access tokens*, con la organización correcta y estos scopes mínimos:

```
+------------------+--------------+-----------------------------------------+
| Scope            | Permiso      | Para qué                                |
+==================+==============+=========================================+
| Work Items       | Read & write | Leer historias y comentarios; crear     |
|                  |              | casos y vínculos                        |
+------------------+--------------+-----------------------------------------+
| Test Management  | Read & write | Planes, suites y casos de prueba        |
+------------------+--------------+-----------------------------------------+
| Project and Team | Read         | Listar proyectos y equipos              |
+------------------+--------------+-----------------------------------------+
| Wiki             | Read         | Leer la Wiki del proyecto               |
+------------------+--------------+-----------------------------------------+
| Code             | Read         | Búsqueda de código y `repositories`     |
|                  |              | (Azure Repos, documentador-proyecto)    |
+------------------+--------------+-----------------------------------------+
```

Para activarlo:

1. Agregá al `.env` de la raíz `ADO_ORGANIZACION`, `ADO_PAT` y, si querés, `ADO_PROYECTO` (ver `.env.example`).
2. Activalo: `npm run conector -- activar azure-devops` (queda solo para vos; te avisa si falta alguna variable).
3. Reiniciá Claude Code y verificá con `/mcp`.

**Sin PAT:** con `ADO_AUTENTICACION=interactive` el server abre el login de Microsoft en el navegador; con `azcli` usa tu sesión de `az login`. Microsoft también ofrece un server remoto (`https://mcp.dev.azure.com/<organizacion>`) que se autentica con Microsoft Entra; no acepta PAT.

**Limitaciones:** el server no registra resultados de ejecución (*test runs*) ni sube evidencias a Test Plans, así que `publicador-resultados` todavía no soporta Azure DevOps. Tampoco hay integración en `scripts/gestion/`: las operaciones pasan por el MCP.

Ejemplos de uso:

> *"Leé la historia 1234 de Azure DevOps y analizala."* · *"Subí los casos de `casos-HU-001.xlsx` a Azure Test Plans, en el plan 'Sprint 5', suite 'HU-001 Registro', vinculados a la historia 1234."*

---

## Repositorio de la aplicación

El agente `documentador-proyecto` lee el repositorio de la aplicación **en solo lectura** (README y docs, validaciones, mensajes, estados, permisos, rutas, contratos de API y los PRs y commits de cada historia) para dejar el contexto del proyecto en `input/documentacion/`. Se configura en el bloque *Repositorio de la aplicación* del `.env`:

```
+-------------------+-------------------------------------------------------------------+
| Variable          | Descripción                                                       |
+===================+===================================================================+
| REPO_PROVEEDOR    | `github`, `gitlab`, `azure-repos` o `bitbucket`                   |
+-------------------+-------------------------------------------------------------------+
| REPO_NOMBRE       | Uno o varios, separados por coma: `dueño/repo` (GitHub),          |
|                   | `grupo/proyecto` (GitLab), `proyecto/repo` (Azure Repos),         |
|                   | `workspace/repo` (Bitbucket)                                      |
+-------------------+-------------------------------------------------------------------+
| REPO_RAMA         | Rama a documentar (vacío = la rama por defecto)                   |
+-------------------+-------------------------------------------------------------------+
| REPO_RUTA_LOCAL   | Opcional: un clon local del mismo repositorio. El código se lee   |
|                   | de ahí (más rápido y sin gastar tokens del conector); PRs y       |
|                   | commits siguen por el conector                                    |
+-------------------+-------------------------------------------------------------------+
```

Cada proveedor usa su server MCP oficial:

- **GitHub** — conector `github`: el server remoto oficial (`https://api.githubcopilot.com/mcp/readonly`) en **modo solo lectura** (`X-MCP-Readonly`), con los toolsets `context,repos,issues,pull_requests` (`GITHUB_TOOLSETS` para cambiarlos). Necesita `GITHUB_TOKEN`: un token *fine-grained* con permisos de solo lectura sobre los repositorios (*Contents*, *Pull requests*, *Issues* y *Metadata*: Read-only). `scripts/mcp/github-headers.js` lo lee del `.env` y lo manda como `Bearer`. El server remoto no soporta GitHub Enterprise Server.
- **GitLab** — conector `gitlab`: el server oficial de GitLab en `<GITLAB_URL>/api/v4/mcp` (GitLab.com, o Self-Managed y Dedicated desde la 19.5, en todos los planes; en GitLab.com el grupo tiene que permitir el acceso al server MCP). Sin `GITLAB_TOKEN` te autorizás con tu cuenta (OAuth) desde `/mcp`; con token, tiene que ser un personal access token *fine-grained* con el recurso *MCP tool* y permiso *Execute* (los tokens clásicos los rechaza con 403). `scripts/mcp/gitlab-headers.js` limita los toolsets a `meta,core,merge_requests,work_items,repository,wikis` (`GITLAB_TOOLSETS`). La URL se toma del `.env` al activarlo: si cambiás `GITLAB_URL`, volvé a activar el conector.
- **Azure Repos** — conector `azure-devops`, con el dominio `repositories` (viene por defecto en `ADO_DOMINIOS`) y el PAT con *Code (Read)*. Ver [Azure DevOps](#azure-devops).
- **Bitbucket Cloud** — conector `atlassian` con `ATLASSIAN_MCP_AUTENTICACION=token` y un API token con los permisos de Bitbucket. Bitbucket Data Center no está soportado por el Rovo MCP Server. Ver [Atlassian](#atlassian-jira-y-confluence).

Para activar GitHub o GitLab:

1. Completá el bloque *Repositorio de la aplicación* del `.env` (ver `.env.example`).
2. `npm run conector -- activar github` (o `gitlab`).
3. Reiniciá Claude Code y verificá con `/mcp` (con GitLab sin token, autorizá con tu cuenta la primera vez).

**Solo lectura**: GitHub ya arranca en modo solo lectura. GitLab, Azure DevOps y Atlassian exponen también herramientas de escritura (crear ramas, archivos o PRs): el `documentador-proyecto` tiene prohibido usarlas, Claude Code pide confirmación antes de cada una, y conviene que el token tenga permisos de lectura.

Ejemplos de uso:

> *"Documentá el proyecto"* · *"Juntá todo el contexto de PROJ-12 antes de escribir los casos"*

---

## Otras herramientas de gestión de proyecto

Si tu equipo no trabaja con Jira ni con Azure DevOps, las historias se leen igual desde su herramienta: cada una tiene su server MCP **oficial** y el skill `investigacion-contexto` recorre las mismas fuentes (descripción, criterios, comentarios, subtareas o checklists, padre, vínculos) con los nombres de cada herramienta. Así lo aprovechan el analista, el estratega, los generadores de casos, los mappers y el `documentador-proyecto`.

```
+-----------+-------------------------------------+------------------------------------+-----------------------------------------+
| Conector  | Server                              | Autenticación                      | Qué da                                  |
+===========+=====================================+====================================+=========================================+
| linear    | https://mcp.linear.app/mcp/readonly | OAuth, o `LINEAR_API_KEY` (key de  | Issues, comentarios, sub-issues,        |
|           |                                     | solo lectura)                      | proyectos, ciclos y relaciones. Solo    |
|           |                                     |                                    | lectura                                 |
+-----------+-------------------------------------+------------------------------------+-----------------------------------------+
| clickup   | https://mcp.clickup.com/mcp         | Solo OAuth                         | Tareas, subtareas, checklists,          |
|           |                                     |                                    | comentarios y Docs                      |
+-----------+-------------------------------------+------------------------------------+-----------------------------------------+
| monday    | https://mcp.monday.com/mcp          | OAuth, o `MONDAY_API_TOKEN` (token | Ítems de los tableros, subítems,        |
|           |                                     | personal)                          | updates (comentarios) y docs            |
+-----------+-------------------------------------+------------------------------------+-----------------------------------------+
| asana     | https://mcp.asana.com/v2/mcp        | OAuth con una app MCP propia       | Tareas, subtareas, comentarios,         |
|           |                                     | (`ASANA_CLIENT_ID`,                | proyectos y secciones                   |
|           |                                     | `ASANA_CLIENT_SECRET`)             |                                         |
+-----------+-------------------------------------+------------------------------------+-----------------------------------------+
| trello    | https://mcp.trello.com/v1           | Solo OAuth                         | Tarjetas, listas, checklists y          |
|           |                                     |                                    | comentarios                             |
+-----------+-------------------------------------+------------------------------------+-----------------------------------------+
| notion    | https://mcp.notion.com/mcp          | Solo OAuth                         | Páginas, bases de datos (backlogs) y    |
|           |                                     |                                    | wikis                                   |
+-----------+-------------------------------------+------------------------------------+-----------------------------------------+
| youtrack  | `<YOUTRACK_URL>/mcp`                | `YOUTRACK_TOKEN` (permanent token) | Issues, comentarios, vínculos, tags y   |
|           |                                     |                                    | artículos de la base de conocimiento    |
+-----------+-------------------------------------+------------------------------------+-----------------------------------------+
| shortcut  | https://mcp.shortcut.com/mcp        | Solo OAuth                         | Stories, epics, comentarios, tareas y   |
|           |                                     |                                    | documentos                              |
+-----------+-------------------------------------+------------------------------------+-----------------------------------------+
```

Para activar cualquiera:

1. Si usa variables, completalas en el bloque *Otras herramientas de gestión de proyecto* del `.env` (ver `.env.example`).
2. `npm run conector -- activar <nombre>` (por ejemplo `linear`).
3. Reiniciá Claude Code, entrá a `/mcp` y, si es OAuth, autorizá con tu cuenta.

Detalles por herramienta:

- **Linear**: el conector apunta al endpoint **de solo lectura** (`/mcp/readonly`), que alcanza para leer historias. Con `LINEAR_API_KEY` (una key con permiso *Read*) se salta el OAuth.
- **ClickUp**: solo OAuth; al autorizar elegís el Workspace. ClickUp no acepta API tokens en su server MCP.
- **monday.com**: con OAuth puede hacer falta que un admin de la cuenta apruebe la conexión; con `MONDAY_API_TOKEN` (tu token personal, sin aprobación de admin) el `headersHelper` lo manda como `Bearer`.
- **Asana**: el server V2 **no acepta el registro automático de clientes OAuth**, así que hace falta una app propia: en https://app.asana.com/0/my-apps, *Create new app* > *MCP app*, redirect URL `http://localhost:8080/callback`, y en *Manage distribution* los workspaces. Copiá el Client ID y el Client secret al `.env`; `npm run conector -- activar asana` lo registra con `claude mcp add --client-id … --client-secret --callback-port 8080`. El secret se guarda en el llavero del sistema (si Claude Code no lo toma de la variable, te lo pide oculto en la terminal). El server viejo (`/sse`, V1) ya no está disponible.
- **Trello**: es el server oficial de Trello (separado del Rovo MCP Server de Atlassian). Al autorizar elegís los workspaces y los permisos (*Read*, *Write*, *Search*); no borra nada (solo archiva). En organizaciones Enterprise, un admin puede limitarlo desde *Atlassian Administration > Connectors*.
- **Notion**: solo OAuth (no acepta tokens). Lee lo que la conexión puede ver en tu workspace; sirve para backlogs armados como base de datos y para la documentación del proyecto.
- **YouTrack**: el server MCP viene integrado en YouTrack Cloud y en YouTrack Server reciente, en `<tu sitio>/mcp`. YouTrack no acepta el registro dinámico de clientes OAuth, así que el conector usa un *permanent token* (Perfil > *Account Security* > *New token*, con el scope YouTrack) que `bearer-headers.js` lee del `.env`. La URL se toma del `.env` al activarlo.
- **Shortcut**: el server remoto oficial (el paquete `@shortcut/mcp` por npx quedó archivado); solo OAuth.
- **GitHub Issues y Projects, GitLab Issues y work items**: no necesitan otro conector, los leen `github` y `gitlab` (ver [Repositorio de la aplicación](#repositorio-de-la-aplicación)).

**Las herramientas de escritura modifican datos compartidos**: salvo Linear (solo lectura), estos servers también pueden crear o editar tareas. Los agentes de k0lmenIA solo las leen, y Claude Code pide confirmación antes de cada acción de escritura.

Ejemplos de uso:

> *"Analizá la historia ENG-142 de Linear"* · *"Generá los casos de la tarjeta 'Checkout con cupones' de Trello"* · *"Juntá el contexto de la tarea de Asana 'Alta de clientes' antes de escribir los casos"*

---

## Appium (para el mobile-mapper)

No es una herramienta de gestión de pruebas: es el server MCP **oficial de Appium**, [`appium-mcp`](https://github.com/appium/appium-mcp), que usa el agente `mobile-mapper` para recorrer una app en un dispositivo o emulador. Requiere **Node.js 22+**, JDK y, para Android, el Android SDK (los drivers UiAutomator2 y XCUITest vienen incluidos). Para iOS hace falta macOS con Xcode.

```
+--------------+---------------+---------------------+
| Variable     | Obligatoria   | Descripción         |
+==============+===============+=====================+
| ANDROID_HOME | Sí (Android)  | Ruta al Android SDK |
+--------------+---------------+---------------------+
```

Se activa con `npm run conector -- activar appium-mcp`. `ANDROID_HOME` se toma del entorno o, si no está, del `.env` (con `scripts/mcp/con-env.js`). La suite que genera el mapper después corre sin MCP, con `npm run test:mobile`, en dispositivo, emulador o BrowserStack (ver `herramientas/k0lmena/README.md`).

---

## Salesforce (para el probador-salesforce)

Es el server MCP **oficial de Salesforce DX**, [`@salesforce/mcp`](https://github.com/salesforcecli/mcp), que usa el agente `probador-salesforce` para consultar una org. **k0lmenIA lo arranca acotado a solo lectura**: habilita únicamente el toolset `data` (consultas **SOQL**) y la herramienta `run_apex_test` (tests de Apex). No habilita metadata (deploy/retrieve) ni la gestión de usuarios/permisos.

Requiere la **CLI de Salesforce** (`npm install --global @salesforce/cli`, Node.js 18+) y la org **autorizada localmente** antes de usarla:

```bash
sf org login web --alias mi-sandbox-qa --instance-url https://test.salesforce.com
```

```
+-----------------------------+---------------+-------------------------------------------------------------+
| Variable                    | Obligatoria   | Descripción                                                 |
+=============================+===============+=============================================================+
| SALESFORCE_ORGS_AUTORIZADAS | Sí            | Alias de las orgs permitidas (sandbox), separados por coma  |
+-----------------------------+---------------+-------------------------------------------------------------+
| SALESFORCE_ORG              | Sí            | El alias de la org con la que se conecta (de la lista)      |
+-----------------------------+---------------+-------------------------------------------------------------+
```

El conector apunta a **una** org concreta (`SALESFORCE_ORG`), que tiene que estar en `SALESFORCE_ORGS_AUTORIZADAS`; nunca `ALLOW_ALL_ORGS`. La autorización vive en la CLI local, así que **por `.mcp.json` no viaja ningún token**. Se activa con `npm run conector -- activar salesforce`. El relevamiento de solo lectura (sin este MCP, con la CLI directa) lo hace `npm run salesforce` (ver `herramientas/salesforce/README.md`).

---

## Scalar (para el probador-scalar)

[Scalar](https://scalar.com) genera un **server MCP hosteado desde el OpenAPI** de tu API (Dashboard → **MCP** → crear el server, elegir la API y el ambiente, y en **Configure → MCP Tools** qué operaciones exponer). Cada operación está en modo **Search** (el agente la consulta sin llamar a la API) o **Execute** (manda requests reales, con las credenciales que guarda Scalar: el agente nunca las ve). Recomendado para QA: **lecturas en Execute y escrituras en Search** hasta que el equipo lo decida.

```
+------------------+---------------+-------------------------------------------------------------+
| Variable         | Obligatoria   | Descripción                                                 |
+==================+===============+=============================================================+
| SCALAR_MCP_URL   | Sí            | URL de conexión del server, p. ej.                          |
|                  |               | https://mcp.scalar.com/@mi-equipo/pagos (con ?env=staging   |
|                  |               | para elegir el ambiente)                                    |
+------------------+---------------+-------------------------------------------------------------+
| SCALAR_API_KEY   | No            | Token personal (Account → API Keys). Sin token, el conector |
|                  |               | se autoriza con tu cuenta (OAuth) desde /mcp. También lo    |
|                  |               | usa npm run scalar para el Registry y la CLI.               |
+------------------+---------------+-------------------------------------------------------------+
| SCALAR_NAMESPACE | No            | Namespace del equipo en el Registry (npm run scalar)        |
+------------------+---------------+-------------------------------------------------------------+
```

Se activa con `npm run conector -- activar scalar` (y reiniciando Claude Code). Los MCP hosteados de Scalar son de los planes pagos y cada llamada que ejecuta consume créditos del dueño. Además del MCP, `npm run scalar` (`herramientas/scalar/scalar.py`) baja los documentos del **Registry**, arma los casos como colección ejecutable y publica el OpenAPI con los tests en `x-post-response` (con la CLI oficial `@scalar/cli`; publicar siempre con confirmación). Ver `herramientas/scalar/README.md`.

---

## Buenas prácticas

- **Las herramientas de escritura modifican datos compartidos** (crear o editar casos, importar resultados). Por eso los conectores no se agregan a `permissions.allow`: Claude Code pide confirmación antes de cada acción.
- Usá un **proyecto de prueba** o un **usuario de servicio** con permisos acotados al probar la conexión.
- Si un token se filtra (por ejemplo, si se commitea), **rotalo de inmediato**.

## Fuentes

- Atlassian Rovo MCP Server: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/
- Atlassian Rovo MCP Server, autenticación por API token: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/configuring-authentication-via-api-token/
- Figma MCP Server (remoto): https://help.figma.com/hc/en-us/articles/35281350665623
- Figma MCP Server con Claude Code: https://help.figma.com/hc/en-us/articles/39888612464151
- SmartBear MCP (QMetry y QTM4J): https://github.com/SmartBear/smartbear-mcp
- AIO Tests MCP Server, guía de configuración: https://aiosupport.atlassian.net/wiki/spaces/AioTests/pages/3097624764/AIO+Tests+MCP+Server+Setup+Configuration+Guide
- AIO MCP Tools: https://aiosupport.atlassian.net/wiki/spaces/AioTests/pages/3115253762/AIO+MCP+Tools
- Xray Cloud GraphQL API (integración propia): https://docs.getxray.app/display/XRAYCLOUD/GraphQL+API
- Xray Server/DC REST API (integración propia): https://docs.getxray.app/display/XRAY/REST+API
- Appium MCP (oficial): https://github.com/appium/appium-mcp
- Salesforce DX MCP Server (oficial): https://github.com/salesforcecli/mcp
- Azure DevOps MCP Server (oficial): https://github.com/microsoft/azure-devops-mcp
- Linear MCP Server: https://linear.app/docs/mcp
- ClickUp MCP Server: https://developer.clickup.com/docs/connect-an-ai-assistant-to-clickups-mcp-server-1
- monday.com MCP: https://developer.monday.com/api-reference/docs/integrate-with-monday-mcp
- Asana MCP Server V2: https://developers.asana.com/docs/integrating-with-asanas-mcp-server · con Claude Code: https://developers.asana.com/docs/connecting-mcp-clients-to-asanas-v2-server
- Trello MCP: https://support.atlassian.com/trello/docs/connect-trello-to-ai-assistants-with-trello-mcp/
- Notion MCP: https://developers.notion.com/docs/get-started-with-mcp
- YouTrack MCP Server: https://www.jetbrains.com/help/youtrack/cloud/model-context-protocol-server.html · Server: https://www.jetbrains.com/help/youtrack/server/model-context-protocol-server.html
- Shortcut MCP: https://www.shortcut.com/help/integrations/mcp-server
- Azure DevOps MCP, herramientas por dominio: https://github.com/microsoft/azure-devops-mcp/blob/main/docs/TOOLSET.md
- GitHub MCP Server: https://github.com/github/github-mcp-server (server remoto: https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md)
- GitLab MCP Server: https://docs.gitlab.com/user/model_context_protocol/mcp_server/
- Bitbucket Cloud en el Atlassian Rovo MCP Server: https://www.atlassian.com/blog/bitbucket/the-atlassian-rovo-mcp-server-now-supports-bitbucket-cloud
- Azure DevOps MCP, autenticación: https://github.com/microsoft/azure-devops-mcp/blob/main/docs/GETTINGSTARTED.md

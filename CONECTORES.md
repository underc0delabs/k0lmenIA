# Conectores MCP

Cómo conectar K0lmenIA Light por MCP a **Jira** (Atlassian), al navegador (**Playwright**) y a **k0lmenaTMT**. Xray se integra sin MCP (ver abajo).

> **La forma fácil:** corré `npm run configurar` en una terminal. Te pregunta qué herramientas usa tu equipo, pide solo sus datos y activa los conectores que hagan falta. Lo de abajo es el detalle, para configurar a mano o algo puntual.

Claude Code **arranca directo, sin pedir aprobar conectores**: `.mcp.json` trae los que vienen habilitados para todos (Playwright y **Atlassian para Jira**). k0lmenaTMT está en el catálogo (`scripts/mcp/catalogo.json`) y cada persona lo activa con `npm run conector -- activar k0lmena-tmt`. Ninguno lleva secretos: las credenciales se leen del `.env` de la raíz o se autorizan con tu cuenta (OAuth).

## Resumen

```
+----------------------------------+--------------------------------------+------------------------------------+---------+--------------+--------------------------+
| Conector                         | Herramienta                          | Server MCP                         | Tipo    | Transporte   | Habilitado por defecto   |
+==================================+======================================+====================================+=========+==============+==========================+
| playwright · playwright-headless | Navegador (ejecutor-e2e, web-mapper, | @playwright/mcp                    | Oficial | stdio        | Sí                       |
|                                  | documentador-proyecto)               |                                    |         |              |                          |
+----------------------------------+--------------------------------------+------------------------------------+---------+--------------+--------------------------+
| atlassian                        | Jira (Cloud)                         | Atlassian Rovo MCP Server (remoto) | Oficial | http         | Sí                       |
+----------------------------------+--------------------------------------+------------------------------------+---------+--------------+--------------------------+
| k0lmena-tmt                      | k0lmenaTMT                           | Server MCP de k0lmenaTMT (local o  | Oficial | http         | No                       |
|                                  |                                      | propio)                            |         |              |                          |
+----------------------------------+--------------------------------------+------------------------------------+---------+--------------+--------------------------+
```

> **Para crear carpetas, casos, ciclos y publicar resultados no hace falta ningún MCP**: lo hace la integración propia `scripts/gestion/` (agentes `gestor-pruebas` y `publicador-resultados`), que soporta **Xray Cloud, Xray Server/Data Center y k0lmenaTMT** con sus APIs oficiales. Configuración en [`scripts/gestion/README.md`](scripts/gestion/README.md).

---

## Qué configurar según tu equipo

Todas las variables están en `.env.example` (un bloque por herramienta, comentado). Cada QA completa solo lo de las herramientas que usa su equipo:

```
+--------------------------+-----------------------------------------+------------------------------------------+--------------------------+
| Si tu equipo usa…        | Conector / integración                  | Variables en el `.env`                   | Habilitado por defecto   |
+==========================+=========================================+==========================================+==========================+
| Jira                     | `atlassian` (MCP)                       | Ninguna con OAuth; con token:            | Sí                       |
|                          |                                         | `ATLASSIAN_MCP_AUTENTICACION=token`,     |                          |
|                          |                                         | `JIRA_EMAIL`, `JIRA_API_TOKEN`           |                          |
+--------------------------+-----------------------------------------+------------------------------------------+--------------------------+
| Xray Cloud               | `scripts/gestion` (API)                 | `GESTION_HERRAMIENTA=xray-cloud`,        | —                        |
|                          |                                         | `XRAY_CLOUD_CLIENT_ID`,                  |                          |
|                          |                                         | `XRAY_CLOUD_CLIENT_SECRET`,              |                          |
|                          |                                         | `GESTION_PROYECTO`                       |                          |
+--------------------------+-----------------------------------------+------------------------------------------+--------------------------+
| Xray Server/DC           | `scripts/gestion` (API)                 | `GESTION_HERRAMIENTA=xray-dc` y los      | —                        |
|                          |                                         | datos de tu Jira Server                  |                          |
+--------------------------+-----------------------------------------+------------------------------------------+--------------------------+
| k0lmenaTMT               | `scripts/gestion` + `k0lmena-tmt` (MCP) | `GESTION_HERRAMIENTA=k0lmena-tmt`,       | No                       |
|                          |                                         | `K0LMENA_TMT_TOKEN`, `GESTION_PROYECTO`  |                          |
+--------------------------+-----------------------------------------+------------------------------------------+--------------------------+
| El repositorio de la app | Lectura local, sin conector             | `REPO_RUTA_LOCAL` (la carpeta donde está | —                        |
|                          |                                         | clonado)                                 |                          |
+--------------------------+-----------------------------------------+------------------------------------------+--------------------------+
```

---

## Pasos para activar un conector

1. **Completá sus variables en el `.env`** de la raíz (están en `.env.example` y en la sección de cada conector). `atlassian` con OAuth no usa variables: se autoriza con tu cuenta.
2. **Activalo** (si no es de los que vienen habilitados): `npm run conector -- activar <nombre>`.
3. **Reiniciá Claude Code** y verificá la conexión con `/mcp`.

**Cómo llegan los tokens al server sin quedar en `.mcp.json`:** los conectores con credenciales no llaman al server directo, sino a un script de `scripts/mcp/` que lee las variables del entorno o, si no están, del `.env`:

```
+------------------------------------------+---------------------------------+------------------------------------------+
| Script                                   | Conectores                      | Qué hace                                 |
+==========================================+=================================+==========================================+
| `playwright.js`                          | playwright, playwright-headless | Arranca Playwright con la carpeta de     |
|                                          |                                 | evidencias y, si existe el `.env`, con   |
|                                          |                                 | `--secrets .env` (oculta esos valores en |
|                                          |                                 | las respuestas)                          |
+------------------------------------------+---------------------------------+------------------------------------------+
| `k0lmena-tmt-headers.js`                 | k0lmena-tmt                     | Devuelve el header `Authorization` (es   |
|                                          |                                 | un `headersHelper`)                      |
+------------------------------------------+---------------------------------+------------------------------------------+
| `atlassian-headers.js`                   | atlassian                       | Con `ATLASSIAN_MCP_AUTENTICACION=token`  |
|                                          |                                 | arma el header con el API token; con     |
|                                          |                                 | `oauth` (por defecto) no agrega nada     |
+------------------------------------------+---------------------------------+------------------------------------------+
| `headers-env.js` · `bearer-headers.js` · | conectores que se sumen         | Arman headers o variables desde el       |
| `con-env.js`                             |                                 | `.env` para conectores nuevos            |
+------------------------------------------+---------------------------------+------------------------------------------+
| `lanzar.js`                              | todos los de `npx`              | Versiones fijas de cada paquete,         |
|                                          |                                 | lanzamiento en Windows y cierre del      |
|                                          |                                 | árbol de procesos                        |
+------------------------------------------+---------------------------------+------------------------------------------+
| `leer-env.js`                            | todos                           | Lee el `.env` con las mismas reglas que  |
|                                          |                                 | k0lmena y `scripts/_env.py`              |
+------------------------------------------+---------------------------------+------------------------------------------+
```

Si falta una variable, el script corta enseguida con un mensaje claro, que se ve en `/mcp`.

**Versiones fijas**: los servers que se instalan con `npx` (Playwright) usan una versión concreta, definida en `scripts/mcp/lanzar.js`, nunca `@latest`: así una versión nueva no revisada no recibe tus tokens sin que alguien lo decida.

> Nunca pongas el valor real de un token en `.mcp.json`. Para sumar un conector nuevo con credenciales, usá `con-env.js` o un script propio en `scripts/mcp/`.

---

## Xray

Xray **no tiene un server MCP oficial** y los comunitarios no cubren carpetas, vínculos con historias ni evidencias. Por eso Xray (Cloud y Server/Data Center) se integra con los scripts propios de `scripts/gestion/`, sobre la API oficial de Xray, y no tiene entrada en `.mcp.json`. Ver [`scripts/gestion/README.md`](scripts/gestion/README.md).

---

## k0lmenaTMT

Conecta los agentes con **k0lmenaTMT** por su server MCP, para consultar desde el chat (casos, planes, ejecuciones, estadísticas, los tests que más fallan) y hacer ajustes puntuales. Se autentica con un **token personal** (`kolm_pat_...`) que se genera en k0lmenaTMT.

> **Las cargas no van por el conector**: subir casos, crear ciclos y publicar resultados con evidencias lo hace `scripts/gestion` con `GESTION_HERRAMIENTA=k0lmena-tmt` (lo usan `gestor-pruebas` y `publicador-resultados`). Usa el mismo server MCP y el mismo token, pero sin pasar cada caso ni cada evidencia por la conversación. Ver `scripts/gestion/README.md`.

```
+-------------------+---------------+----------------------------------------+
| Variable          | Obligatoria   | Descripción                            |
+===================+===============+========================================+
| K0LMENA_TMT_TOKEN | Sí            | Token personal de k0lmenaTMT. Va en el |
|                   |               | .env de la raíz                        |
+-------------------+---------------+----------------------------------------+
| K0LMENA_TMT_URL   | No            | Por defecto                            |
|                   |               | http://localhost:4000/api/v1/mcp; para |
|                   |               | otra URL, definila en el .env antes de |
|                   |               | activar (o en el entorno)              |
+-------------------+---------------+----------------------------------------+
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

## Atlassian: Jira

El conector `atlassian` es el server MCP **oficial de Atlassian** (Rovo MCP Server). Da acceso a **Jira** Cloud con los permisos de tu usuario: los agentes leen las historias con sus criterios, comentarios, subtareas, épica y vínculos, en lugar de copiarlas a `input/`.

**Viene habilitado por defecto.** Tiene dos formas de autenticarse, que se eligen con `ATLASSIAN_MCP_AUTENTICACION` en el `.env`:

- **`oauth` (por defecto, recomendado para uso interactivo)**: no usa token. La primera vez ejecutá `/mcp`, elegí `atlassian` y autorizá el acceso con tu cuenta en el navegador.
- **`token`**: usa `JIRA_EMAIL` y `JIRA_API_TOKEN` (las mismas que usa la integración con Xray Cloud) y arma el header `Authorization: Basic …`. Para una cuenta de servicio, poné su API key en `ATLASSIAN_API_KEY` y se envía como `Bearer`. **Requisito**: un admin de Atlassian tiene que habilitar el API token en *Atlassian Administration > Rovo > Rovo MCP server > Authentication*. El token se crea en https://id.atlassian.com/manage-profile/security/api-tokens.

La entrada de `.mcp.json` usa `headersHelper` (`scripts/mcp/atlassian-headers.js`): con `oauth` no agrega nada y con `token` arma el header leyendo el `.env`. El token nunca queda en `.mcp.json`.

Si tu organización restringe las apps de IA, un admin de Atlassian tiene que habilitar el Rovo MCP Server para el sitio.

Ejemplos de uso:

> *"Leé la historia PROJ-12 de Jira y analizala."* · *"¿BUG-008 ya está cargado en Jira?"*

---

## Repositorio de la aplicación

El agente `documentador-proyecto` lee el repositorio de la aplicación **en solo lectura** desde un clon en tu PC (README y docs, validaciones, mensajes, estados, permisos, rutas y contratos de API) para dejar el contexto del proyecto en `input/documentacion/`. No necesita conector: alcanza con `REPO_RUTA_LOCAL` en el bloque *Repositorio de la aplicación* del `.env`, apuntando a la carpeta donde lo tenés clonado.

---

## Estado de los conectores en HTML

`npm run conector -- listar --html` (con el plugin, `k0lmenia conector -- listar --html`) deja **`output/conectores/estado.html`** (español e inglés): cuáles vienen incluidos, cuáles están activos, cuáles están listos para activar y a cuáles les faltan datos en el `.env`, cómo se autoriza cada uno y el comando para activarlo. Nunca muestra valores del `.env`: solo si cada variable está o no. Aparece en el portal `output/index.html`.

---

## ¿Necesitás más conectores?

Confluence, Figma, GitHub, GitLab, Linear, ClickUp, monday.com, Asana, Trello, Notion, YouTrack, Shortcut, Appium, observabilidad, analytics, soporte y plataformas de testing están en K0lmenIA Pro; Azure DevOps, QMetry, AIO Tests y Salesforce, en K0lmenIA Empresa. Más información en https://k0lmena.com/k0lmenia/

---

## Buenas prácticas

- **Las herramientas de escritura modifican datos compartidos** (crear o editar casos, importar resultados). Por eso los conectores no se agregan a `permissions.allow`: Claude Code pide confirmación antes de cada acción.
- Usá un **proyecto de prueba** o un **usuario de servicio** con permisos acotados al probar la conexión.
- Si un token se filtra (por ejemplo, si se commitea), **rotalo de inmediato**.

## Fuentes

- Atlassian Rovo MCP Server: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/
- Atlassian Rovo MCP Server, autenticación por API token: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/configuring-authentication-via-api-token/
- Xray Cloud GraphQL API (integración propia): https://docs.getxray.app/display/XRAYCLOUD/GraphQL+API
- Xray Server/DC REST API (integración propia): https://docs.getxray.app/display/XRAY/REST+API
- Playwright MCP: https://github.com/microsoft/playwright-mcp

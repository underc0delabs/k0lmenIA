# Conectores MCP

Cómo conectar k0lmenIA por MCP a **Jira y Confluence** (Atlassian), **Figma**, **QMetry**, **AIO Tests**, **k0lmenaTMT**, **Azure DevOps** y **Appium**. Xray se integra sin MCP (ver abajo).

Todas las conexiones están en el `.mcp.json` del proyecto y **ninguna lleva secretos**: las credenciales se leen del `.env` de la raíz o se autorizan con tu cuenta (OAuth). Solo Playwright viene habilitado; cada persona habilita en su `.claude/settings.local.json` las que usa.

## Resumen

```
+-----------+-----------------------------------------+-----------------------------------------+-------------+------------+
| Conector  | Herramienta                             | Server MCP                              | Tipo        | Transporte |
+===========+=========================================+=========================================+=============+============+
| atlassian | Jira y Confluence (Cloud)               | Atlassian Rovo MCP Server (remoto)      | Oficial     | http       |
+-----------+-----------------------------------------+-----------------------------------------+-------------+------------+
| figma     | Figma (diseños)                         | Figma MCP Server remoto                 | Oficial     | http       |
+-----------+-----------------------------------------+-----------------------------------------+-------------+------------+
| figma-    | Figma (app de escritorio)               | Figma MCP Server de escritorio          | Oficial     | http       |
| desktop   |                                         | (local)                                 |             |            |
+-----------+-----------------------------------------+-----------------------------------------+-------------+------------+
| qmetry    | QMetry Test Management                  | @smartbear/mcp                          | Oficial     | stdio      |
+-----------+-----------------------------------------+-----------------------------------------+-------------+------------+
| qtm4j     | QMetry Test Management for Jira (QTM4J) | @smartbear/mcp                          | Oficial     | stdio      |
+-----------+-----------------------------------------+-----------------------------------------+-------------+------------+
| aio-tests | AIO Tests for Jira                      | Server remoto de AIO Tests (por tenant) | Oficial     | stdio      |
+-----------+-----------------------------------------+-----------------------------------------+-------------+------------+
| k0lmena-  | k0lmenaTMT                              | Server MCP de k0lmenaTMT (local o       | Oficial     | http       |
| tmt       |                                         | propio)                                 |             |            |
+-----------+-----------------------------------------+-----------------------------------------+-------------+------------+
| azure-    | Azure DevOps (Boards, Test Plans, Wiki) | @azure-devops/mcp (Microsoft)           | Oficial     | stdio      |
| devops    |                                         |                                         |             |            |
+-----------+-----------------------------------------+-----------------------------------------+-------------+------------+
```

> **Para crear carpetas, casos, ciclos y publicar resultados no hace falta ningún MCP**: lo hace la integración propia `scripts/gestion/` (agentes `gestor-pruebas` y `publicador-resultados`), que soporta **Xray Cloud, Xray Server/Data Center, QTM4J y AIO Tests** con sus APIs oficiales. Configuración en [`scripts/gestion/README.md`](scripts/gestion/README.md). La excepción es **Azure DevOps**, que se integra por su MCP (ver [Azure DevOps](#azure-devops)). Los MCP de esta página son opcionales, para consultar o explorar la herramienta desde el chat.

---

## Pasos para activar un conector

1. **Completá sus variables en el `.env`** de la raíz (están en `.env.example` y en la sección de cada conector). `atlassian` y `figma` no usan variables: se autorizan con tu cuenta.
2. **Habilitalo** agregando su nombre a `enabledMcpjsonServers` en tu `.claude/settings.local.json` (no se versiona, así que solo te afecta a vos):

```json
"enabledMcpjsonServers": ["playwright", "playwright-headless", "qtm4j"]
```

3. **Reiniciá Claude Code** y verificá la conexión con `/mcp`. Si Claude Code pregunta si aprobás los servers del `.mcp.json`, aprobá solo los que vas a usar.

**Cómo llegan los tokens al server sin quedar en `.mcp.json`:** los conectores con credenciales no llaman al server directo, sino a un script de `scripts/mcp/` que lee las variables del entorno o, si no están, del `.env`, y arranca el server pasándoselas solo por variable de entorno:

```
+--------------------------+---------------------------+------------------------------------------+
| Script                   | Conectores                | Qué hace                                 |
+==========================+===========================+==========================================+
| `con-env.js`             | qmetry, qtm4j, appium-mcp | Pasa al server las variables que pide la |
|                          |                           | entrada (y nada más del `.env`)          |
+--------------------------+---------------------------+------------------------------------------+
| `azure-devops.js`        | azure-devops              | Arma el PAT en el formato del server y   |
|                          |                           | elige las áreas habilitadas              |
+--------------------------+---------------------------+------------------------------------------+
| `aio-tests.js`           | aio-tests                 | Conecta con la URL de tu tenant vía      |
|                          |                           | `mcp-remote`, con el token en el header  |
+--------------------------+---------------------------+------------------------------------------+
| `k0lmena-tmt-headers.js` | k0lmena-tmt               | Devuelve el header `Authorization` (es   |
|                          |                           | un `headersHelper`)                      |
+--------------------------+---------------------------+------------------------------------------+
```

Si falta una variable, el script corta enseguida con un mensaje claro (por ejemplo *"qtm4j: falta QTM4J_API_KEY en el .env de la raíz"*), que se ve en `/mcp`.

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
+--------------------------+-------------+---------------------------------------+
| Variable                 | Obligatoria | Descripción                           |
+==========================+=============+=======================================+
| QTM4J_API_KEY            | Sí          | API Key de QTM4J                      |
+--------------------------+-------------+---------------------------------------+
| QTM4J_BASE_URL           | No          | US (por defecto):                     |
|                          |             | https://qtmcloud.qmetry.com ·         |
|                          |             | Australia: https://syd-               |
|                          |             | qtmcloud.qmetry.com                   |
+--------------------------+-------------+---------------------------------------+
| QTM4J_AUTOMATION_API_KEY | No          | Solo para las herramientas de         |
|                          |             | automatización; vacía las deshabilita |
+--------------------------+-------------+---------------------------------------+
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

Conecta los agentes con **k0lmenaTMT** por su server MCP, para cargar y consultar casos de prueba desde el chat. Se autentica con un **token personal** (`kolm_pat_...`) que se genera en k0lmenaTMT.

```
+-------------------+-------------+------------------------------------------+
| Variable          | Obligatoria | Descripción                              |
+===================+=============+==========================================+
| K0LMENA_TMT_TOKEN | Sí          | Token personal de k0lmenaTMT. Va en el   |
|                   |             | .env de la raíz                          |
+-------------------+-------------+------------------------------------------+
| K0LMENA_TMT_URL   | No          | Por defecto                              |
|                   |             | http://localhost:4000/api/v1/mcp; para   |
|                   |             | otra URL, definila en el entorno         |
+-------------------+-------------+------------------------------------------+
```

**El token se lee del `.env`**: la entrada usa `headersHelper`, que ejecuta `scripts/mcp/k0lmena-tmt-headers.js` cada vez que Claude Code se conecta. El script toma `K0LMENA_TMT_TOKEN` del entorno o, si no está, del `.env`, y arma el header `Authorization: Bearer …`. El token nunca queda en `.mcp.json`.

Para activarlo:

1. Agregá `K0LMENA_TMT_TOKEN=<tu token>` al `.env` de la raíz.
2. Agregá `"k0lmena-tmt"` a `enabledMcpjsonServers` en `.claude/settings.local.json`.
3. Con k0lmenaTMT levantado, reiniciá Claude Code y verificá con `/mcp`.

> No uses `claude mcp add ... --header "Authorization: Bearer <token>"`: deja el token escrito en la configuración de Claude Code.

Ejemplos de uso:

> *"Cargá en k0lmenaTMT los casos de `output/casos-de-prueba/manuales/casos-HU-001.xlsx`."* · *"¿Qué casos de HU-001 hay en k0lmenaTMT?"*

---

## Atlassian: Jira y Confluence

El conector `atlassian` es el server MCP **oficial de Atlassian** (Rovo MCP Server). Con **una sola conexión** da acceso a **Jira y Confluence** Cloud, con los permisos de tu usuario: los agentes pueden leer historias y sus criterios desde Jira y la documentación funcional desde páginas de Confluence, en lugar de copiarlas a `input/`.

- **No usa token**: se autentica con tu cuenta de Atlassian por OAuth. No hace falta ninguna variable de entorno.
- Para activarlo:
  1. Agregá `"atlassian"` a `enabledMcpjsonServers` en `.claude/settings.local.json`.
  2. Reiniciá Claude Code, ejecutá `/mcp`, elegí `atlassian` y autorizá el acceso en el navegador.
- Si tu organización restringe las apps de IA, un admin de Atlassian tiene que habilitar el Rovo MCP Server para el sitio.

Ejemplos de uso:

> *"Leé la historia PROJ-12 de Jira y analizala."* · *"Generá los casos de PROJ-12 usando la página de Confluence 'Reglas de facturación' como documentación."*

---

## Figma

El conector `figma` es el server MCP **oficial de Figma**. Les da a los agentes el contexto de un diseño a partir de un **link a un frame, una capa o un archivo**: textos, componentes, estados y capturas. Sirve para diseñar casos de UI (textos esperados, validaciones visibles, estados vacíos y de error), comparar la app contra el diseño y dar contexto al `web-mapper`.

- **Requisitos**: un asiento **Full** o **Dev** de Figma (otros asientos tienen límites de uso) y permiso de edición o lectura sobre el archivo.
- **No usa token**: se autentica con tu cuenta de Figma por OAuth.
- Para activarlo, cualquiera de estas dos opciones:
  - **Plugin oficial (recomendado por Figma)**: `claude plugin install figma@claude-plugins-official`, reiniciá Claude Code, entrá a `/plugin` → *Installed* → `figma` y autorizá el acceso. Incluye el server y skills de Figma.
  - **Solo el server**: agregá `"figma"` a `enabledMcpjsonServers` en `.claude/settings.local.json`, reiniciá y autorizá desde `/mcp`.
- **Variante de escritorio** (`figma-desktop`): para organizaciones que no permiten el server remoto. Requiere la app de escritorio de Figma con el server MCP habilitado (modo Dev → panel derecho) y se conecta a `http://127.0.0.1:3845/mcp`.

Ejemplos de uso:

> *"Generá los casos de HU-001 tomando como referencia este diseño: https://www.figma.com/design/…?node-id=…"* · *"Compará la pantalla de registro de https://tu-app.com con el diseño de Figma y reportá las diferencias."*

---

## Azure DevOps

Usa el server MCP **oficial de Microsoft**, [`@azure-devops/mcp`](https://github.com/microsoft/azure-devops-mcp) (requiere **Node.js 20+**). Con una sola conexión los agentes pueden:

- **Consultar historias** (*User Story*, *Product Backlog Item*, *Bug*) de Azure Boards con sus comentarios, tareas hijas, padre (*Feature* / *Epic*) y vínculos, y leer la **Wiki** del proyecto. Lo usa el skill `investigacion-contexto`, igual que Jira y Confluence.
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
|                   |               | work work-items test-plans wiki search`; |
|                   |               | sumá `repositories` o `pipelines` si las |
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
| Code             | Read         | Solo si habilitás la búsqueda de código |
|                  |              | o `repositories`                        |
+------------------+--------------+-----------------------------------------+
```

Para activarlo:

1. Agregá al `.env` de la raíz `ADO_ORGANIZACION`, `ADO_PAT` y, si querés, `ADO_PROYECTO` (ver `.env.example`).
2. Habilitalo agregando `"azure-devops"` a `enabledMcpjsonServers` en tu `.claude/settings.local.json`. Solo queda activa para quien la habilita y tiene las variables en su `.env`.
3. Reiniciá Claude Code y verificá con `/mcp`.

**Sin PAT:** con `ADO_AUTENTICACION=interactive` el server abre el login de Microsoft en el navegador; con `azcli` usa tu sesión de `az login`. Microsoft también ofrece un server remoto (`https://mcp.dev.azure.com/<organizacion>`) que se autentica con Microsoft Entra; no acepta PAT.

**Limitaciones:** el server no registra resultados de ejecución (*test runs*) ni sube evidencias a Test Plans, así que `publicador-resultados` todavía no soporta Azure DevOps. Tampoco hay integración en `scripts/gestion/`: las operaciones pasan por el MCP.

Ejemplos de uso:

> *"Leé la historia 1234 de Azure DevOps y analizala."* · *"Subí los casos de `casos-HU-001.xlsx` a Azure Test Plans, en el plan 'Sprint 5', suite 'HU-001 Registro', vinculados a la historia 1234."*

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

Se activa igual que los demás conectores, habilitando `appium-mcp`. `ANDROID_HOME` se toma del entorno o, si no está, del `.env` (con `scripts/mcp/con-env.js`). La suite que genera el mapper después corre sin MCP, con `npm run test:mobile`, en dispositivo, emulador o BrowserStack (ver `herramientas/k0lmena/README.md`).

---

## Buenas prácticas

- **Las herramientas de escritura modifican datos compartidos** (crear o editar casos, importar resultados). Por eso los conectores no se agregan a `permissions.allow`: Claude Code pide confirmación antes de cada acción.
- Usá un **proyecto de prueba** o un **usuario de servicio** con permisos acotados al probar la conexión.
- Si un token se filtra (por ejemplo, si se commitea), **rotalo de inmediato**.

## Fuentes

- Atlassian Rovo MCP Server: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/
- Figma MCP Server (remoto): https://help.figma.com/hc/en-us/articles/35281350665623
- Figma MCP Server con Claude Code: https://help.figma.com/hc/en-us/articles/39888612464151
- SmartBear MCP (QMetry y QTM4J): https://github.com/SmartBear/smartbear-mcp
- AIO Tests MCP Server, guía de configuración: https://aiosupport.atlassian.net/wiki/spaces/AioTests/pages/3097624764/AIO+Tests+MCP+Server+Setup+Configuration+Guide
- AIO MCP Tools: https://aiosupport.atlassian.net/wiki/spaces/AioTests/pages/3115253762/AIO+MCP+Tools
- Xray Cloud GraphQL API (integración propia): https://docs.getxray.app/display/XRAYCLOUD/GraphQL+API
- Xray Server/DC REST API (integración propia): https://docs.getxray.app/display/XRAY/REST+API
- Appium MCP (oficial): https://github.com/appium/appium-mcp
- Azure DevOps MCP Server (oficial): https://github.com/microsoft/azure-devops-mcp
- Azure DevOps MCP, autenticación: https://github.com/microsoft/azure-devops-mcp/blob/main/docs/GETTINGSTARTED.md

# Conectores MCP

Cómo conectar k0lmenIA por MCP a **Jira y Confluence** (Atlassian), **Figma**, **QMetry**, **AIO Tests** y **Appium**. Xray se integra sin MCP (ver abajo).

Las conexiones están definidas en `.mcp.json.example`. No vienen activas en `.mcp.json` porque cada una necesita credenciales o una cuenta propia. Activá solo las que uses.

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
| aio-tests | AIO Tests for Jira                      | Server remoto de AIO Tests (por tenant) | Oficial     | http       |
+-----------+-----------------------------------------+-----------------------------------------+-------------+------------+
```

> **Para crear carpetas, casos, ciclos y publicar resultados no hace falta ningún MCP**: lo hace la integración propia `scripts/gestion/` (agentes `gestor-pruebas` y `publicador-resultados`), que soporta **Xray Cloud, Xray Server/Data Center, QTM4J y AIO Tests** con sus APIs oficiales. Configuración en [`scripts/gestion/README.md`](scripts/gestion/README.md). Los MCP de esta página son opcionales, para consultar o explorar la herramienta desde el chat.

---

## Pasos para activar un conector

1. **Copiá la entrada** del conector desde `.mcp.json.example` a la sección `mcpServers` de tu `.mcp.json`.
2. **Habilitala** agregando su nombre a `enabledMcpjsonServers` en `.claude/settings.json` (o en tu `.claude/settings.local.json`, que no se versiona):

```json
"enabledMcpjsonServers": ["playwright", "playwright-headless", "qtm4j"]
```

3. **Definí las variables de entorno** que pide (están listadas en `.env.example`). Claude Code reemplaza cada `${VARIABLE}` con el valor del **entorno** donde se lanza `claude`; no lee el `.env` por su cuenta. Por ejemplo, en PowerShell:

```powershell
$env:QTM4J_API_KEY = "tu-api-key"
claude
```

4. **Reiniciá Claude Code** y verificá la conexión con `/mcp`.

> Nunca pongas el valor real de un token en `.mcp.json`: solo `${VARIABLE}`.

---

## Xray

Xray **no tiene un server MCP oficial** y los comunitarios no cubren carpetas, vínculos con historias ni evidencias. Por eso Xray (Cloud y Server/Data Center) se integra con los scripts propios de `scripts/gestion/`, sobre la API oficial de Xray. Ver [`scripts/gestion/README.md`](scripts/gestion/README.md).

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

**Alternativa sin token (OAuth):** AIO Tests también acepta OAuth 2.1 si usás la versión Forge de la app. En ese caso borrá el bloque `headers` del conector y Claude Code abre el login en el navegador la primera vez (`/mcp` > *Authenticate*).

---

## Atlassian: Jira y Confluence

El conector `atlassian` es el server MCP **oficial de Atlassian** (Rovo MCP Server). Con **una sola conexión** da acceso a **Jira y Confluence** Cloud, con los permisos de tu usuario: los agentes pueden leer historias y sus criterios desde Jira y la documentación funcional desde páginas de Confluence, en lugar de copiarlas a `input/`.

- **No usa token**: se autentica con tu cuenta de Atlassian por OAuth. No hace falta ninguna variable de entorno.
- Para activarlo:
  1. Copiá la entrada `atlassian` de `.mcp.json.example` a `.mcp.json` (o ejecutá `claude mcp add --transport http atlassian https://mcp.atlassian.com/v2/mcp`).
  2. Agregá `"atlassian"` a `enabledMcpjsonServers` en `.claude/settings.local.json`.
  3. Reiniciá Claude Code, ejecutá `/mcp`, elegí `atlassian` y autorizá el acceso en el navegador.
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
  - **Solo el server**: copiá la entrada `figma` de `.mcp.json.example` a `.mcp.json`, agregá `"figma"` a `enabledMcpjsonServers` en `.claude/settings.local.json`, reiniciá y autorizá desde `/mcp`.
- **Variante de escritorio** (`figma-desktop`): para organizaciones que no permiten el server remoto. Requiere la app de escritorio de Figma con el server MCP habilitado (modo Dev → panel derecho) y se conecta a `http://127.0.0.1:3845/mcp`.

Ejemplos de uso:

> *"Generá los casos de HU-001 tomando como referencia este diseño: https://www.figma.com/design/…?node-id=…"* · *"Compará la pantalla de registro de https://tu-app.com con el diseño de Figma y reportá las diferencias."*

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

Se activa igual que los demás conectores (entrada `appium-mcp` de `.mcp.json.example`). La suite que genera el mapper después corre sin MCP, con `npm run test:mobile`, en dispositivo, emulador o BrowserStack (ver `herramientas/k0lmena/README.md`).

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

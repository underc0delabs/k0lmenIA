# Conectores de gestión de pruebas (MCP)

Cómo conectar k0lmenIA a **Xray**, **QMetry** y **AIO Tests** para que los agentes lean y escriban casos, ejecuciones y resultados directamente en tu herramienta de gestión de pruebas.

Las conexiones están definidas en `.mcp.json.example`. No vienen activas en `.mcp.json` porque cada una necesita credenciales propias. Activá solo las que uses.

## Resumen

```
+------------+-----------------------------------------+-----------------------------------------+-------------+--------------+
| Conector   | Herramienta                             | Server MCP                              | Tipo        | Transporte   |
+============+=========================================+=========================================+=============+==============+
| xray       | Xray (Cloud o Server/Data Center)       | jithinjosejacob/xray-mcp-server       | Comunitario | stdio        |
+------------+-----------------------------------------+-----------------------------------------+-------------+--------------+
| qmetry     | QMetry Test Management                  | @smartbear/mcp                        | Oficial     | stdio        |
+------------+-----------------------------------------+-----------------------------------------+-------------+--------------+
| qtm4j      | QMetry Test Management for Jira (QTM4J) | @smartbear/mcp                        | Oficial     | stdio        |
+------------+-----------------------------------------+-----------------------------------------+-------------+--------------+
| aio-tests  | AIO Tests for Jira                      | Server remoto de AIO Tests (por tenant) | Oficial     | http         |
+------------+-----------------------------------------+-----------------------------------------+-------------+--------------+
```

> Xray no tiene un server MCP oficial. El conector usa un proyecto de la comunidad: revisá su código antes de darle credenciales.

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

Usa el server comunitario [`jithinjosejacob/xray-mcp-server`](https://github.com/jithinjosejacob/xray-mcp-server), que soporta Xray Cloud y Server/Data Center. No está publicado en npm, así que se clona y se compila una vez:

```bash
git clone https://github.com/jithinjosejacob/xray-mcp-server.git
cd xray-mcp-server
npm install
npm run build
```

```
+--------------------------+---------------+-----------------------------------------+
| Variable                 | Obligatoria   | Descripción                             |
+==========================+===============+=========================================+
| XRAY_MCP_PATH            | Sí            | Ruta absoluta a la carpeta clonada (usá |
|                          |               | / también en Windows)                 |
+--------------------------+---------------+-----------------------------------------+
| XRAY_DEPLOYMENT          | No (cloud)  | cloud o server                      |
+--------------------------+---------------+-----------------------------------------+
| XRAY_CLOUD_CLIENT_ID     | Sí (Cloud)    | Client ID de la API key de Xray         |
+--------------------------+---------------+-----------------------------------------+
| XRAY_CLOUD_CLIENT_SECRET | Sí (Cloud)    | Client Secret de la API key de Xray     |
+--------------------------+---------------+-----------------------------------------+
```

La API key se crea en Jira, en **Configuración global de Xray > API Keys**, idealmente con un usuario de servicio.

**Xray Server / Data Center:** poné `XRAY_DEPLOYMENT=server` y agregá al bloque `env` del conector `XRAY_JIRA_BASE_URL`, `XRAY_AUTH_TYPE` (`token` o `basic`) y `XRAY_TOKEN` (o `XRAY_USERNAME` y `XRAY_PASSWORD` si usás `basic`).

## QMetry

Usa el server oficial de SmartBear, [`@smartbear/mcp`](https://github.com/SmartBear/smartbear-mcp), que requiere **Node.js 20+**. Hay dos conectores según qué producto de QMetry uses; activá solo el tuyo.

**`qmetry` — QMetry Test Management (standalone):**

```
+-----------------+---------------+---------------------------------------+
| Variable        | Obligatoria   | Descripción                           |
+=================+===============+=======================================+
| QMETRY_API_KEY  | Sí            | Open API Key de QMetry                |
+-----------------+---------------+---------------------------------------+
| QMETRY_BASE_URL | No            | Por defecto                           |
|                 |               | https://testmanagement.qmetry.com;  |
|                 |               | cambiala si tu instancia usa otra URL |
+-----------------+---------------+---------------------------------------+
```

**`qtm4j` — QMetry Test Management for Jira (Cloud):**

```
+--------------------------+---------------+---------------------------------------+
| Variable                 | Obligatoria   | Descripción                           |
+==========================+===============+=======================================+
| QTM4J_API_KEY            | Sí            | API Key de QTM4J                      |
+--------------------------+---------------+---------------------------------------+
| QTM4J_BASE_URL           | No            | US (por defecto):                     |
|                          |               | https://qtmcloud.qmetry.com ·       |
|                          |               | Australia: https://syd-              |
|                          |               | qtmcloud.qmetry.com                  |
+--------------------------+---------------+---------------------------------------+
| QTM4J_AUTOMATION_API_KEY | No            | Solo para las herramientas de         |
|                          |               | automatización; vacía las deshabilita |
+--------------------------+---------------+---------------------------------------+
```

## AIO Tests

Usa el server MCP **oficial** de AIO Tests, que es remoto (no hay que instalar nada). Cada tenant tiene su propia URL.

```
+---------------+---------------+------------------------------------------+
| Variable      | Obligatoria   | Descripción                              |
+===============+===============+==========================================+
| AIO_MCP_URL   | Sí            | URL del server; se copia de **My         |
|               |               | Settings > MCP Authorization** en AIO    |
|               |               | Tests                                    |
+---------------+---------------+------------------------------------------+
| AIO_API_TOKEN | Sí            | Public API Token, de **My Settings > API |
|               |               | Token**                                  |
+---------------+---------------+------------------------------------------+
```

**Alternativa sin token (OAuth):** AIO Tests también acepta OAuth 2.1 si usás la versión Forge de la app. En ese caso borrá el bloque `headers` del conector y Claude Code abre el login en el navegador la primera vez (`/mcp` > *Authenticate*).

---

## Buenas prácticas

- **Las herramientas de escritura modifican datos compartidos** (crear o editar casos, importar resultados). Por eso los conectores no se agregan a `permissions.allow`: Claude Code pide confirmación antes de cada acción.
- Usá un **proyecto de prueba** o un **usuario de servicio** con permisos acotados al probar la conexión.
- Si un token se filtra (por ejemplo, si se commitea), **rotalo de inmediato**.

## Fuentes

- SmartBear MCP (QMetry y QTM4J): https://github.com/SmartBear/smartbear-mcp
- AIO Tests MCP Server, guía de configuración: https://aiosupport.atlassian.net/wiki/spaces/AioTests/pages/3097624764/AIO+Tests+MCP+Server+Setup+Configuration+Guide
- AIO MCP Tools: https://aiosupport.atlassian.net/wiki/spaces/AioTests/pages/3115253762/AIO+MCP+Tools
- Xray MCP Server (comunitario): https://github.com/jithinjosejacob/xray-mcp-server

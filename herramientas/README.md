# Herramientas

Acá se integran las **herramientas externas de testing** que los agentes usan para *ejecutar* (no para generar): herramientas que se corren por línea de comandos o que necesitan sus propios archivos de configuración y plantillas.

Cada herramienta va en su **propia subcarpeta**, así el repo escala sin pisarse: sumar una herramienta = sumar una carpeta.

```
herramientas/
├── newman/          # Postman CLI: ejecuta colecciones de pruebas de API (integrada)
├── zap/             # OWASP ZAP: seguridad web en modo pasivo, en Docker (integrada)
│   └── README.md    # qué es, instalación y cómo la usa el agente
├── k0lmena/         # Framework de automatización (integrado): web, api, mobile y performance
│   ├── web/ api/ mobile/ performance/
│   └── README.md    # instalación, npm test y cómo lo usan los mappers
└── ...              # otras (JMeter, etc.)
```

Hay tres integradas:

- **Newman** (en `newman/`): la usa el agente `ejecutor-api` para correr pruebas de API.
- **OWASP ZAP** (en `zap/`): la usa el agente `analista-seguridad` para escanear, en modo pasivo, sitios propios o autorizados y armar el informe de seguridad.
- **k0lmena** (en `k0lmena/`): copia del framework [underc0delabs/k0lmena](https://github.com/underc0delabs/k0lmena). Los agentes `web-mapper`, `api-mapper` y `mobile-mapper` generan ahí los `.feature`, steps y locators, y después la suite corre con `npm test` sin agentes ni tokens. El `performance-mapper` genera los scripts de k6, Artillery y JMeter, que corren con `npm run perf`. El `verificador-datos` consulta las bases de datos del `.env` (`npm run bd`) y, si se lo piden, suma verificaciones de base de datos a los `.feature`.

Las que vengan se suman con el mismo patrón: una subcarpeta + su README.

> ¿En qué se diferencia de `scripts/` y de `.mcp.json`?
> - **`herramientas/`** → herramientas externas que se ejecutan por CLI (JMeter, k6…), con sus plantillas y configs.
> - **`scripts/`** → utilidades en Python propias del repo (generan o dan formato a los artefactos).
> - **`.mcp.json`** → conexiones a sistemas externos por protocolo MCP (Jira, Xray, navegador vía Playwright…).

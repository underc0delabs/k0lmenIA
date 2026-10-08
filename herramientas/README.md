# Herramientas

Acá se integran las **herramientas externas de testing** que los agentes usan para *ejecutar* (no para generar): herramientas que se corren por línea de comandos o que necesitan sus propios archivos de configuración y plantillas.

Cada herramienta va en su **propia subcarpeta**, así el repo escala sin pisarse: sumar una herramienta = sumar una carpeta.

```
herramientas/
├── newman/          # Postman CLI: ejecuta colecciones de pruebas de API (integrada)
│   └── README.md    # qué es, instalación y cómo la usa el agente
├── k0lmena/         # Framework de automatización (integrado): web, api, mobile y performance
│   ├── web/ api/ mobile/ performance/
│   └── README.md    # instalación, npm test y cómo lo usan los mappers
└── ...              # otras (JMeter, etc.)
```

Hay dos integradas:

- **Newman** (en `newman/`): la usa el agente `ejecutor-api` para correr pruebas de API.
- **k0lmena** (en `k0lmena/`): copia del framework [underc0delabs/k0lmena](https://github.com/underc0delabs/k0lmena). Los agentes `web-mapper`, `api-mapper` y `mobile-mapper` generan ahí los `.feature`, steps y locators, y después la suite corre con `npm test` sin agentes ni tokens.

Las que vengan (JMeter…) se suman con el mismo patrón: una subcarpeta + su README.

> ¿En qué se diferencia de `scripts/` y de `.mcp.json`?
> - **`herramientas/`** → herramientas externas que se ejecutan por CLI (JMeter, k6…), con sus plantillas y configs.
> - **`scripts/`** → utilidades en Python propias del repo (generan o dan formato a los artefactos).
> - **`.mcp.json`** → conexiones a sistemas externos por protocolo MCP (Jira, Xray, navegador vía Playwright…).

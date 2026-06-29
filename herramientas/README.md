# Herramientas

Acá se integran las **herramientas externas de testing** que los agentes usan para *ejecutar* (no para generar): herramientas que se corren por línea de comandos o que necesitan sus propios archivos de configuración y plantillas.

Cada herramienta va en su **propia subcarpeta**, así el repo escala sin pisarse: sumar una herramienta = sumar una carpeta.

```
herramientas/
├── newman/          # Postman CLI: ejecuta colecciones de pruebas de API (integrada)
│   └── README.md    # qué es, instalación y cómo la usa el agente
├── jmeter/          # ejemplo a futuro: pruebas de performance
│   ├── planes/      # plantillas .jmx
│   └── README.md    # cómo la usa el agente
└── ...              # otras (k6, etc.)
```

La primera herramienta integrada es **Newman** (en `newman/`): la usa el agente `ejecutor-api` para correr pruebas de API. Las que vengan (k6, JMeter…) se suman con el mismo patrón: una subcarpeta + su README.

> ¿En qué se diferencia de `scripts/` y de `.mcp.json`?
> - **`herramientas/`** → herramientas externas que se ejecutan por CLI (JMeter, k6…), con sus plantillas y configs.
> - **`scripts/`** → utilidades en Python propias del repo (generan o dan formato a los artefactos).
> - **`.mcp.json`** → conexiones a sistemas externos por protocolo MCP (Jira, Xray, navegador vía Playwright…).

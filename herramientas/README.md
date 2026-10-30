# Herramientas

Acá se integran las **herramientas externas de testing** que los agentes usan para *ejecutar* (no para generar): herramientas que se corren por línea de comandos o que necesitan sus propios archivos de configuración y plantillas.

Cada herramienta va en su **propia subcarpeta**, así el repo escala sin pisarse: sumar una herramienta = sumar una carpeta.

```
herramientas/
├── newman/          # Postman CLI: ejecuta colecciones de pruebas de API (integrada)
├── k0lmena/         # Framework de automatización (integrado): web y api
│   ├── web/ api/ reports/
│   └── README.md    # instalación, npm test y cómo lo usan los mappers
├── ci/              # Plantillas de pipeline (GitHub, GitLab, Jenkins, Azure)
└── ...              # otras: una subcarpeta + su README
```

Las integradas:

- **Newman** (en `newman/`): la usa el agente `ejecutor-api` para correr pruebas de API (colecciones de Postman, Bruno e Insomnia).
- **k0lmena** (en `k0lmena/`): copia del framework [underc0delabs/k0lmena](https://github.com/underc0delabs/k0lmena). Los agentes `web-mapper` y `api-mapper` generan ahí los `.feature`, steps y locators, y después la suite corre con `npm test` sin agentes ni tokens. Con `npm run bd` se consultan las bases de datos del `.env` y, si se pide, los mappers suman verificaciones de base de datos a los `.feature`. El `documentador-proyecto` arma el mapa funcional del sitio con `npm run mapa-funcional` (páginas, menús, formularios con sus campos, botones y mensajes, sin enviar nada) en `input/documentacion/`. `npm test` guarda sus últimas 5 corridas en `reports/<suite>/historial/`.
- **ci** (en `ci/`): plantillas de pipeline para GitHub Actions, GitLab CI, Jenkins y Azure Pipelines (`npm run ci -- generar --plataforma <x>`) que corren las suites de k0lmena sin agentes ni tokens, guardan los reportes como artefacto y, si hay `GESTION_CICLO`, publican los resultados con `scripts/gestion` (`npm run ci -- publicar`). El `.env` va entero como secret del pipeline. Ver `herramientas/ci/README.md`.

Las que vengan se suman con el mismo patrón: una subcarpeta + su README.

> ¿En qué se diferencia de `scripts/` y de `.mcp.json`?
> - **`herramientas/`** → herramientas externas que se ejecutan por CLI (Newman, k0lmena…), con sus plantillas y configs.
> - **`scripts/`** → utilidades en Python propias del repo (generan o dan formato a los artefactos).
> - **`.mcp.json`** → conexiones a sistemas externos por protocolo MCP (Jira, navegador vía Playwright…).

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
├── streaming/       # ffmpeg/ONVIF: video, cámaras y grabaciones (agentes de streaming)
├── salesforce/      # CLI sf: inventario de QA de una org de Salesforce (probador-salesforce)
├── ecommerce/       # Shopify y WordPress/WooCommerce: relevamiento funcional de tiendas (probador-shopify, probador-wordpress)
└── ...              # otras: una subcarpeta + su README
```

Las integradas:

- **Mailpit** (en `mailpit/`): buzón de prueba que atrapa los mails de la app; lo usan el agente `verificador-correos` (`npm run correos`) y los steps de correo de k0lmena.
- **Newman** (en `newman/`): la usa el agente `ejecutor-api` para correr pruebas de API.
- **OWASP ZAP** (en `zap/`): la usa el agente `analista-seguridad` para escanear, en modo pasivo, sitios propios o autorizados y armar el informe de seguridad.
- **k0lmena** (en `k0lmena/`): copia del framework [underc0delabs/k0lmena](https://github.com/underc0delabs/k0lmena). Los agentes `web-mapper`, `api-mapper` y `mobile-mapper` generan ahí los `.feature`, steps y locators, y después la suite corre con `npm test` sin agentes ni tokens. El `performance-mapper` genera los scripts de k6, Artillery y JMeter, que corren con `npm run perf`. El `verificador-datos` consulta las bases de datos del `.env` (`npm run bd`) y, si se lo piden, suma verificaciones de base de datos a los `.feature`. El `explorador-web` recorre el sitio con `npm run explorar` (links, imágenes, errores, responsive y tiempos de carga, con capturas, videos e informe HTML) el `analista-accesibilidad` audita WCAG 2.2 con `npm run accesibilidad` (axe-core, teclado y reflow) el `auditor-rendimiento-web` mide la velocidad de carga con `npm run rendimiento` (Lighthouse), el `pixel-perfect` hace la regresión visual con `npm run pixel-perfect`, el `cross-browser` prueba en Chromium, Firefox y WebKit con `npm run cross-browser` y el `reparador-automatizacion` diagnostica y repara locators con `npm run reparar` (usa el DOM que la suite web guarda al fallar en `reports/web/dom/`), el `verificador-correos` revisa los mails con `npm run correos` el `analista-traductor` los idiomas con `npm run traductor`, el `evaluador-ux` la usabilidad con `npm run ux` y el `probador-formularios` las validaciones con `npm run formularios`. El `probador-permisos` arma la matriz por rol con `npm run permisos`, el `probador-resiliencia` simula fallas de API, red y recursos con `npm run resiliencia` y `npm run monitorear` hace el monitoreo sintético de solo lectura (con avisos a Slack y Teams). El `documentador-proyecto` arma el mapa funcional del sitio con `npm run mapa-funcional` (páginas, menús, formularios con sus campos, botones y mensajes, sin enviar nada) en `input/documentacion/`. Cada herramienta guarda sus últimas 5 corridas en `historial/`, y `npm test` las suyas en `reports/<suite>/historial/`.
- **streaming** (en `streaming/`): ffprobe/ffmpeg y ONVIF para los agentes de video y cámaras (`probador-streaming`, `probador-onvif`, `calidad-imagen`, `verificador-grabaciones`, `analista-seguridad-camaras`). Ver `herramientas/streaming/README.md`.
- **salesforce** (en `salesforce/`): la CLI `sf` para relevar una org de Salesforce en solo lectura (`probador-salesforce`, `npm run salesforce`). Ver `herramientas/salesforce/README.md`.
- **ecommerce** (en `ecommerce/`): relevamientos funcionales de solo lectura de tiendas Shopify (`npm run shopify`, Admin API y Theme Check opcionales) y WordPress / WooCommerce (`npm run wordpress`, REST API de WooCommerce y WP-CLI opcionales), para el `probador-shopify` y el `probador-wordpress`. Ver `herramientas/ecommerce/README.md`.

- **codigo** (en `codigo/`): code review estático de solo lectura para el `revisor-codigo` — trae el código de GitHub, GitLab, Bitbucket, Azure Repos, Gitea o cualquier git sin ejecutar nada (`npm run obtener-codigo`, con el diff de un PR/MR contra el merge-base) y lo revisa con reglas por lenguaje, métricas, duplicados, secretos y semgrep/ruff/bandit si están (`npm run revision-codigo`). Ver `herramientas/codigo/README.md`.

- **manual** (en `manual/`): la herramienta del `redactor-manual` (`npm run manual`) — carpetas y versiones de cada manual, capturas, HTML autocontenido y Word con el diseño de k0lmena, checklist antes de la versión final, plan de la plataforma por módulos y exportación del conocimiento a `input/documentacion/manual-usuario/`.
- **scalar** (en `scalar/`): la herramienta del `probador-scalar` (`npm run scalar`) — trae las APIs del Registry de Scalar, arma los casos como colección con tests `pm` (corre con Newman) y como OpenAPI con `x-post-response` para publicar en Scalar con la CLI oficial. Ver `herramientas/scalar/README.md`.
- **ci** (en `ci/`): plantillas de pipeline para GitHub Actions, GitLab CI, Jenkins y Azure Pipelines (`npm run ci -- generar --plataforma <x>`) que corren las suites de k0lmena sin agentes ni tokens, guardan los reportes como artefacto y, si hay `GESTION_CICLO`, publican los resultados con `scripts/gestion` (`npm run ci -- publicar`). El `.env` va entero como secret del pipeline. Ver `herramientas/ci/README.md`.
Las que vengan se suman con el mismo patrón: una subcarpeta + su README.

> ¿En qué se diferencia de `scripts/` y de `.mcp.json`?
> - **`herramientas/`** → herramientas externas que se ejecutan por CLI (Newman, ZAP, k0lmena con k6, Artillery y JMeter…), con sus plantillas y configs.
> - **`scripts/`** → utilidades en Python propias del repo (generan o dan formato a los artefactos).
> - **`.mcp.json`** → conexiones a sistemas externos por protocolo MCP (Jira, Xray, navegador vía Playwright…).

# Cambios de k0lmenIA

Los cambios más relevantes, del más nuevo al más viejo. El detalle de cada uno está en el historial de git.

## 2026-10-10 — Inicio directo, conectores a pedido
- Claude Code arranca sin pedir aprobar conectores: `.mcp.json` trae solo los que vienen activos para todos (Playwright y Atlassian).
- Los opcionales (Azure DevOps, Figma, QMetry, QTM4J, AIO Tests, k0lmenaTMT, Appium) pasan a `scripts/mcp/catalogo.json` y cada persona activa los suyos con `npm run conector -- activar <nombre>` (alcance local de Claude Code: solo para esa persona, sin tocar archivos versionados).
- `npm run doctor` revisa también los conectores activados así. Tests que garantizan que todo lo de `.mcp.json` venga habilitado.

## 2026-10-09 (3) — Verificación funcional
- `correr_newman.py` respeta el `base_url` del environment o de la colección; `API_BASEURL` del `.env` se usa solo si no lo definen (la demo terminaba pegándole a Petstore).
- `npm run doctor` acepta Xray Server/DC con usuario y contraseña, y Azure DevOps sin PAT (login interactivo o `az login`).
- `npm run perf` avisa si un mismo nombre de script existe en dos herramientas, en vez de elegir uno en silencio.
- `npm run test:repo` funciona también con Node 20.

## 2026-10-09 (2) — Revisión completa: robustez, seguridad, tests y documentación

**Correcciones**
- Seis agentes (análisis, generadores de casos, datos y bugs) ya pueden leer Jira, Azure DevOps, Confluence y Figma: tenían la lista de herramientas restringida.
- Ningún agente se queda esperando una respuesta: si falta un dato, termina y devuelve "Necesito que confirmes"; la conversación principal pregunta y lo continúa.
- Los escenarios BDD llevan `@CP-XXX`: la trazabilidad BDD → automatización → gestión → resultados ya no se corta. `@smoke` siempre en minúscula.
- Publicación de resultados por historia: un `@CP-001` de otra historia ya no se carga en el caso equivocado.
- Los reintentos ante 429/5xx reenvían las evidencias completas (antes podían subir vacías); los cortes de red se reintentan.
- `subir-casos` registra cada caso apenas lo crea: si falla el vínculo, no se duplica y el vínculo se reintenta.
- El informe de cierre suma todas las fuentes (ejecuciones en vivo, `npm test`, bugs, performance y seguridad) con `scripts/recolectar_resultados.py`; la plantilla de bug suma Historia, Estado y Prioridad.
- El lector de `.feature` conserva los `Examples` con tags y soporta `Rule`.
- Tres agentes (generador-casos-manuales, generador-reporte-cierre y performance-mapper) no cargaban: su descripción tenía ": " sin comillas y el YAML era inválido. Un test valida ahora el encabezado de todos los agentes y skills.

**Seguridad**
- Servers MCP con versiones fijas (sin `@latest`) y Playwright con `--secrets .env`.
- Bases de datos con SSL: se verifica el certificado (`sin-verificar` es explícito); `DB_<NOMBRE>_SSL_CA` para CA propias.
- k6 se descarga verificando su SHA-256; validaciones de keys, historias y rutas en los scripts.
- Permisos del proyecto: se permiten los comandos de solo lectura y generación; lo que escribe afuera sigue pidiendo confirmación.

**Nuevo**
- `npm run doctor`: revisa el entorno y dice qué falta.
- `scripts/correr_newman.py`: corre colecciones con el token y la URL del `.env` en cualquier sistema.
- Tests del repo (pytest y node --test) y CI en GitHub Actions (Ubuntu y Windows).
- `LICENSE`, este `CHANGELOG` y `input/README.md`.

## 2026-10-09 (1) — Nuevas integraciones y reportes
- Rediseño de todos los reportes: modo oscuro moderno, paletas validadas y gráficos con tooltips.
- Todos los conectores listos (Jira, Azure DevOps, Confluence, Figma, QMetry, AIO Tests, k0lmenaTMT, Xray) y Jira habilitado por defecto.
- Seguridad web con OWASP ZAP (escaneo pasivo) y su informe.
- JMeter en performance, guía paso a paso de la prueba e informe final.
- Azure DevOps (Boards, Test Plans, Wiki) y credenciales de todos los conectores leídas del `.env`.

## 2026-10-08
- Conector de k0lmenaTMT; investigación de contexto y "Falta información" (`FI-XX`).
- Agente verificador-datos y verificaciones en base de datos.
- Sitio de documentación (GitHub Pages), PDF y diagramas.
- performance-mapper y el runner de performance de k0lmena.
- Integración con Xray, QMetry (QTM4J) y AIO Tests; GIF como evidencia.
- Integración de k0lmena y los agentes web-mapper, api-mapper y mobile-mapper.
- El proyecto pasa a llamarse k0lmenIA.

## 2026-06
- Primeras versiones de los agentes QARMY: análisis, casos, datos, bugs, API, plan de pruebas e informe final.

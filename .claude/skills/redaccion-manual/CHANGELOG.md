# Changelog — skill redaccion-manual

Versionado `MAJOR.MINOR.PATCH`: MAJOR cambia el proceso o el formato de forma incompatible (carpetas, `qa-review.md`), MINOR suma funcionalidades compatibles, PATCH corrige.

## [1.0.0] — 2026-10-23

Primera versión.

- Manuales de usuario basados en evidencia, para cualquier tipo de proyecto: de una funcionalidad, un módulo o toda la plataforma (plan por módulos desde el menú y el mapa funcional).
- Fuentes de k0lmenIA primero (`input/documentacion/`: dossiers de historias, investigación, mapa funcional, reglas y mensajes; casos, `.feature` y la herramienta de gestión configurada), después la aplicación con **Playwright MCP** y la sesión de `npm run login`.
- Matriz de evidencia por fuente (`CONFIRMED` / `REVIEW` / `BLOCKED` / `NOT_APPLICABLE`), gaps antes de abrir la app, acciones prohibidas y datos de prueba solo con autorización.
- Bloques `⚠️ QA REVIEW (REVIEW-NNN)` en el borrador y `qa-review.md` 1 a 1; aprobación explícita; checklist automatizado (`npm run manual -- verificar`).
- Salidas en `output/manuales/<slug>/`: Markdown, HTML y Word con el diseño de k0lmena (fuentes de la casa embebidas).
- Conocimiento para los demás agentes: `npm run manual -- a-input` deja el manual en `input/documentacion/manual-usuario/` (estado `borrador` o `confirmado`, los REVIEW como *Sin confirmar*) con las **Pistas para probar**.

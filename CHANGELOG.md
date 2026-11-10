# Cambios de K0lmenIA Light

Los cambios más relevantes, del más nuevo al más viejo. El detalle de cada uno está en el historial de git.

## 2026-11-10 — Planes como plugins

- **Pro y Empresa se suman como plugins aparte** (`k0lmenia-pro` y `k0lmenia-empresa`) desde el mismo marketplace `k0lmenia`: el core gratis queda instalado y cada plan pago suma sus agentes, skills y conectores encima.
- **`/k0lmenia:setup`** muestra qué plan tenés, a cuáles tenés acceso (según tu acceso a sus repos en GitHub) y qué suma cada uno, instala los que te corresponden y configura k0lmenaTMT. Desde una terminal: `k0lmenia planes`.
- Los agentes del core usan la versión completa de su texto: si pedís algo de un plan que no tenés, te dice en cuál está.
- **`/k0lmenia:options`**: cuadro comparativo de los tres planes (una fila por capacidad) y todas las opciones de cada uno: agentes, skills y conectores. Desde una terminal: `k0lmenia planes --opciones`.
- **`/k0lmenia:setup` arranca por tu proyecto**: te pide la web principal, la recorre, te recomienda qué agentes y planes te sirven y te muestra checks para activar los plugins de los planes a los que tenés acceso. Desde una terminal: `k0lmenia planes --recomendar <url>`.

## 2026-10-30 — K0lmenIA Light

Primera versión de K0lmenIA Light, la versión gratuita (licencia MIT): lo elemental del día a día de QA.

- **13 agentes**: `documentador-proyecto`, `analista-historias`, `generador-casos-manuales`, `generador-casos-bdd`, `revisor-casos` y `triador-bugs` (análisis y diseño); `ejecutor-e2e`, `ejecutor-api` y `asistente-ejecucion-manual` (ejecución en vivo); `web-mapper` y `api-mapper` (automatización con k0lmena); `gestor-pruebas` y `publicador-resultados` (gestión en Xray Cloud, Xray Server/DC y k0lmenaTMT).
- **13 skills**: investigación de contexto y Falta información, técnicas de diseño, redacción de casos manuales, ejecución E2E y de API, GraphQL y gRPC, automatización con k0lmena, documentación del proyecto, base de conocimiento, ejecución manual acompañada (`/k0lmenia:ejecucion-manual`), guía de pruebas y puesta en marcha (`/k0lmenia:empezar`).
- **24 comandos npm**: las suites de k0lmena (`npm test`, web y API, reportes, sesión guardada, grabación, base de datos y mapa funcional), ejecución manual, pipeline de CI, portal de informes, avisos a Slack y Teams, evals, novedades, doctor, configuración y conectores.
- **Conectores**: Playwright (headed y headless), Atlassian para Jira y k0lmenaTMT.
- **Informes en español e inglés** con portal de informes (`output/index.html`) e historial de las últimas 5 corridas.
- Se instala como **plugin de Claude Code** (`claude plugin marketplace add underc0delabs/k0lmenIA` y `claude plugin install k0lmenia@k0lmenia`) o clonando el repo.
- Para más agentes y conectores: **K0lmenIA Pro** y **K0lmenIA Empresa** (https://k0lmena.com/k0lmenia/).

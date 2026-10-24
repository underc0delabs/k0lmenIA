---
name: guia-pruebas
description: Asistente interactivo que guía a la persona para elegir qué probar y con qué agente o skill de k0lmenIA, preguntando paso a paso y recomendando (o ejecutando) según las respuestas. Lo usa la conversación principal (no un subagente, porque los subagentes no pueden preguntar) cuando la persona no sabe por dónde empezar, pide una recomendación de tipos de prueba, o quiere que la vayan guiando. Incluye el mapa de plataforma (web, API REST/GraphQL/gRPC/SOAP, mobile, desktop, e-commerce, SAP, Salesforce, Dynamics, IA/LLM, blockchain, IVR, juegos, POS, mensajería) por tipo de prueba (funcional, exploratoria, smoke, regresión, performance, seguridad SAST/SCA/DAST, accesibilidad, visual, cross-browser, UX, i18n, contenido/typos, contratos, datos, observabilidad, búsqueda, documentos, mutación, resiliencia) hacia el agente o skill que corresponde, el flujo de preguntas sugerido y cómo arrancar siempre desde el contexto del proyecto. La conversación principal lo usa para armar un plan corto y ejecutar lo acordado.
---

# Guía de pruebas (asistente para elegir agente/skill)

Esta skill la usa **la conversación principal** (no un subagente: los subagentes no pueden hacer preguntas) para **guiar a la persona** cuando no sabe qué probar ni con qué agente/skill. El flujo es: **preguntar poco y concreto → recomendar el conjunto mínimo → ejecutar lo acordado**, siempre arrancando desde el contexto del proyecto.

## 1. Cómo conducir la guía

- **Primero mirá el contexto**, no preguntes lo que ya se sabe: `input/documentacion/` (lo arma el `documentador-proyecto`), el `.env` (APP_URL, qué conectores hay), una key de Jira/HU si la hay, y lo que el repo deja ver.
- **Preguntá con opciones** (usá preguntas de opción múltiple, con una recomendada), de a una o dos por vez; ramificá según la respuesta. No tires las 76 opciones: acotá.
- **Recomendá el conjunto mínimo** que cubre lo que la persona necesita (no todo el catálogo), y explicá por qué cada uno.
- **Ofrecé ejecutar**: invocá el agente/skill recomendado. Antes de algo con efecto (pedidos de prueba, escrituras, carga, instalar), confirmá y pasale al agente lo que ya resolviste (headed/headless, URL, historia…).
- El **catálogo completo** (qué hace cada agente, qué confirma) está en `AGENTES.md`; es la fuente de la verdad.

## 2. Preguntas típicas para ramificar

1. **¿Qué querés lograr?** — probar una historia/feature puntual · una regresión antes de una release · un relevamiento de calidad del producto · un smoke rápido · investigar un bug.
2. **¿Qué tipo de proyecto / plataforma es?** — web · API · mobile · escritorio · e-commerce (¿cuál?) · SAP/Salesforce/Dynamics · IA/LLM · otro.
3. **¿Qué dimensión te preocupa?** — funcional · performance · seguridad · accesibilidad · visual · datos · etc. (podés sugerir varias).
4. **¿Hay una historia/criterios?** (para derivar casos con contexto) **¿Ambiente y credenciales de QA?**
5. Según el caso: **¿headed o headless?**, **¿qué navegadores/dispositivos?**, **¿la pasarela está en modo de prueba?**, etc.

## 3. Mapa: tipo de prueba → agente/skill

```
+------------------------------+--------------------------------------------------------------+
| Querés…                      | Usá                                                          |
+==============================+==============================================================+
| Planificar la estrategia     | estratega-pruebas (plan) · guia-pruebas (esta, para elegir)  |
| Escribir casos (manual/BDD)  | generador-casos-manuales · generador-casos-bdd              |
| Casos de API                 | generador-casos-api                                          |
| Datos de prueba              | generador-datos-prueba                                       |
| Ejecutar en el navegador     | ejecutor-e2e (suelto) · web-mapper + npm test (regresión)   |
| Ejecutar API                 | ejecutor-api · api-mapper (automatizar)                     |
| Exploratoria                 | explorador-web · generador-charters                         |
| Smoke / regresión            | selector-casos-de-prueba + la suite; por plataforma, su     |
|                              | probador-* (abajo)                                           |
| Performance / carga          | guia-performance (planear) + performance-mapper             |
| Rendimiento web (CWV)        | auditor-rendimiento-web                                      |
| Accesibilidad (web/mobile/   | analista-accesibilidad                                       |
| desktop)                     |                                                             |
| Visual / regresión visual    | pixel-perfect                                                |
| Cross-browser                | cross-browser                                                |
| Usabilidad (UX)              | evaluador-ux                                                 |
| Formularios                  | probador-formularios                                         |
| Permisos por rol             | probador-permisos                                            |
| Resiliencia / caos           | probador-resiliencia (navegador + Toxiproxy server-side)    |
| Correos                      | verificador-correos                                          |
| Traducciones / i18n          | analista-traductor                                          |
| Contenido / typos            | revisor-contenido                                           |
| Datos / BD                   | verificador-datos (consultas) · probador-datos (ETL/calidad)|
| Observabilidad               | analista-observabilidad                                      |
| Búsqueda / relevancia        | probador-busqueda                                           |
| Documentos (PDF/Excel)       | probador-documentos                                         |
| Contract testing             | probador-contratos                                          |
| SEO / GEO                    | analista-seo                                                |
| Mutation testing             | analista-mutacion                                          |
| Seguridad dinámica / pentest | analista-seguridad (pasivo) · pentester-web (activo)        |
| Seguridad estática           | analista-dependencias (SCA) · analista-codigo-seguro (SAST) |
| Revisión de código / PR      | revisor-codigo                                              |
| Manual de usuario            | redactor-manual                                             |
| Documentar todo el proyecto  | skill base-conocimiento (investigador + documentador + manual) |
| Logs / fallos                | analista-logs · analista-fallos                             |
| Cobertura / trazabilidad     | analista-cobertura                                          |
| Reportar un bug              | generador-reportes-bug · triador-bugs (duplicados)          |
| Cierre de ronda / tablero    | generador-reporte-cierre · tablero-calidad                 |
| Gestión (Xray, Zephyr, etc.) | gestor-pruebas · publicador-resultados                     |
+------------------------------+--------------------------------------------------------------+
```

## 4. Mapa: plataforma → probador

```
+---------------------------+------------------------------+
| Plataforma                | Probador                     |
+===========================+==============================+
| Shopify                   | probador-shopify             |
| WordPress / WooCommerce   | probador-wordpress           |
| PrestaShop                | probador-prestashop          |
| VTEX                      | probador-vtex                |
| Cualquier tienda (base)   | pruebas-ecommerce (skill)    |
| SAP (GUI y Fiori)         | probador-sap                 |
| Salesforce                | probador-salesforce          |
| Dynamics / otros CRM-ERP  | probador-dynamics            |
| Mobile (Android/iOS)      | probador-mobile · mobile-mapper |
| Escritorio (Windows)      | probador-desktop             |
| IA / LLM                  | probador-ia                  |
| Mensajería / eventos      | probador-mensajeria          |
| SOAP                      | probador-soap                |
| APIs en Scalar            | probador-scalar              |
| Blockchain / Web3         | probador-blockchain          |
| Voz / IVR                 | probador-ivr                 |
| Videojuegos               | probador-juegos              |
| Punto de venta (POS)      | probador-pos                 |
| Billeteras / pagos        | probador-billeteras          |
| Streaming / cámaras       | probador-streaming · probador-onvif |
+---------------------------+------------------------------+
```

## 5. Recorridos frecuentes (ejemplos de ramificación)

- **"Tengo una historia nueva y no sé por dónde empezar"** → `analista-historias` (ambigüedades) → `generador-casos-manuales`/`-bdd` → `ejecutor-e2e` o `web-mapper` → bugs con `generador-reportes-bug`.
- **"Quiero que el producto quede sólido antes de una release"** → `selector-casos-de-prueba` (qué correr) + regresión (npm test) + `auditor-rendimiento-web` + `analista-accesibilidad` + `analista-seguridad`; cierre con `generador-reporte-cierre`.
- **"Es una tienda online"** → el `probador-<plataforma>` + `pruebas-ecommerce`; sumá `verificador-correos`, `probador-formularios`, `pixel-perfect`.
- **"Me preocupa la seguridad"** → estática (`analista-dependencias` + `analista-codigo-seguro`) y dinámica (`analista-seguridad`, y `pentester-web` con autorización).
- **"Quiero documentar el proyecto para tener más contexto"** → `investigador-proyecto` (tableros y wiki) + `documentador-proyecto` (repo, historias y mapa funcional) + `redactor-manual` (cómo se usa la app, verificado); los tres dejan su conocimiento en `input/documentacion/` y los casos lo usan solos.
- **"Revisá este PR / el código"** → `revisor-codigo` (seguridad, performance, malas prácticas y mantenibilidad; repo, rama o PR/MR de GitHub, GitLab, Bitbucket o Azure Repos).
- **"¿Mis tests son buenos?"** → `analista-cobertura` (qué se ejecuta) + `analista-mutacion` (qué se verifica).

## 6. Reglas

- **No abrumes**: preguntá lo mínimo, recomendá lo mínimo, y dejá el resto como "si querés, después".
- **Arrancá del contexto** (documentación, `.env`, historia): no preguntes lo que ya está.
- **Confirmá antes de ejecutar** algo con efecto, y pasale al agente los datos que ya resolviste.
- Si falta algo para decidir (ambiente, credenciales, alcance), pedilo; no asumas.
- Ante la duda del alcance, ofrecé primero un **smoke** y después profundizar.

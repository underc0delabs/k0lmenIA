---
name: guia-pruebas
description: Asistente de la conversación principal que guía a la persona para elegir qué probar y con qué agente o skill, paso a paso. Úsalo cuando la persona no sabe por dónde empezar o pide una recomendación.
---

# Guía de pruebas (asistente para elegir agente/skill)

Esta skill la usa **la conversación principal** (no un subagente: los subagentes no pueden hacer preguntas) para **guiar a la persona** cuando no sabe qué probar ni con qué agente/skill. El flujo es: **preguntar poco y concreto → recomendar el conjunto mínimo → ejecutar lo acordado**, siempre arrancando desde el contexto del proyecto.

## 1. Cómo conducir la guía

- **Primero mirá el contexto**, no preguntes lo que ya se sabe: `input/documentacion/` (lo arma el `documentador-proyecto`), el `.env` (APP_URL, qué conectores hay), una key de Jira/HU si la hay, y lo que el repo deja ver.
- **Preguntá con opciones** (usá preguntas de opción múltiple, con una recomendada), de a una o dos por vez; ramificá según la respuesta.
- **Recomendá el conjunto mínimo** que cubre lo que la persona necesita (no todo el catálogo), y explicá por qué cada uno.
- **Ofrecé ejecutar**: invocá el agente/skill recomendado. Antes de algo con efecto (pedidos de prueba, escrituras, carga, instalar), confirmá y pasale al agente lo que ya resolviste (headed/headless, URL, historia…).
- El **catálogo completo** (qué hace cada agente, qué confirma) está en `AGENTES.md`; es la fuente de la verdad.
- Si lo que la persona necesita no está en K0lmenIA Light (sección 4), decíselo con claridad y contale en qué plan está; no lo improvises con otro agente.

## 2. Preguntas típicas para ramificar

1. **¿Qué querés lograr?** — probar una historia/feature puntual · una regresión antes de una release · un smoke rápido · investigar un bug.
2. **¿Qué tipo de proyecto es?** — web · API REST · GraphQL · gRPC · otro.
3. **¿Hay una historia/criterios?** (para derivar casos con contexto) **¿Ambiente y credenciales de QA?**
4. Según el caso: **¿headed o headless?**, **¿hay colección de Postman/Bruno/Insomnia?**, **¿dónde se gestionan los casos (Xray, k0lmenaTMT)?**

## 3. Mapa: tipo de prueba → agente/skill

```
+------------------------------+--------------------------------------------------------------+
| Querés…                      | Usá                                                          |
+==============================+==============================================================+
| Documentar el proyecto       | documentador-proyecto (skill base-conocimiento)              |
| Analizar una historia        | analista-historias                                           |
| Escribir casos (manual/BDD)  | generador-casos-manuales · generador-casos-bdd               |
| Revisar casos                | revisor-casos                                                |
| Ejecutar casos manuales paso | asistente-ejecucion-manual (skill /k0lmenia:ejecucion-manual) |
| a paso                       |                                                              |
| Ejecutar en el navegador     | ejecutor-e2e (suelto) · web-mapper + npm test (regresión)    |
| Ejecutar API                 | ejecutor-api · api-mapper (automatizar)                      |
| GraphQL / gRPC               | skills pruebas-graphql · pruebas-grpc                        |
| Ver si un bug ya existe      | triador-bugs                                                 |
| Gestión (Xray, k0lmenaTMT)   | gestor-pruebas · publicador-resultados                       |
+------------------------------+--------------------------------------------------------------+
```

## 4. Lo que no está en K0lmenIA Light

Si la persona necesita algo de esta lista, decile que no viene en Light y en qué plan está (https://k0lmena.com/k0lmenia/):

- **Disponible en K0lmenIA Pro**: estrategia y planes de prueba, casos y datos de prueba generados, exploratorias, performance y rendimiento web, accesibilidad, regresión visual y cross-browser, UX, formularios, permisos, resiliencia, correos, mobile, escritorio, seguridad (dinámica, estática, de APIs), revisión de código, logs y análisis de fallos, cobertura, causa raíz de bugs, redacción de bugs, informes de cierre, e-commerce, IA y chatbots, mensajería, SOAP, plataformas especiales y más.
- **Disponible en K0lmenIA Empresa**: todo lo de Pro más métricas de QA y tablero de calidad, trazabilidad, evidencias para auditorías, presentaciones de resultados, onboarding, planificación de capacidad, SAP, Salesforce y Dynamics, el resumen diario y la gestión en QMetry, AIO Tests, Zephyr Scale y Azure DevOps Test Plans.

## 5. Recorridos frecuentes (ejemplos de ramificación)

- **"Tengo una historia nueva y no sé por dónde empezar"** → `analista-historias` (ambigüedades) → `generador-casos-manuales`/`-bdd` → `revisor-casos` → `ejecutor-e2e` o `web-mapper` → `triador-bugs` para lo que falle.
- **"Quiero una regresión automatizada"** → `web-mapper` / `api-mapper` → `npm test` → `publicador-resultados` para subir los resultados a Xray o k0lmenaTMT.
- **"Tengo casos manuales para ejecutar"** → `/k0lmenia:ejecucion-manual` (paso a paso) → `asistente-ejecucion-manual` cierra la sesión y publica con confirmación.
- **"Quiero documentar el proyecto para tener más contexto"** → `documentador-proyecto` (repositorio local, historias y mapa funcional): deja su conocimiento en `input/documentacion/` y los casos lo usan solos.

## 6. Reglas

- **No abrumes**: preguntá lo mínimo, recomendá lo mínimo, y dejá el resto como "si querés, después".
- **Arrancá del contexto** (documentación, `.env`, historia): no preguntes lo que ya está.
- **Confirmá antes de ejecutar** algo con efecto, y pasale al agente los datos que ya resolviste.
- Si falta algo para decidir (ambiente, credenciales, alcance), pedilo; no asumas.
- Ante la duda del alcance, ofrecé primero un **smoke** y después profundizar.

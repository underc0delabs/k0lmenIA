---
name: guia-pruebas
description: Asistente de la conversación principal que guía a la persona para elegir qué probar y con qué agente o skill, paso a paso. Úsalo cuando la persona no sabe por dónde empezar o pide una recomendación.
---

# Guía de pruebas (asistente para elegir agente/skill)

Esta skill la usa **la conversación principal** (no un subagente: los subagentes no pueden hacer preguntas) para **guiar a la persona** cuando no sabe qué probar ni con qué agente/skill. El flujo es: **preguntar poco y concreto → recomendar el conjunto mínimo → ejecutar lo acordado**, siempre arrancando desde el contexto del proyecto.

## 1. Cómo conducir la guía

- **Primero mirá el contexto**, no preguntes lo que ya se sabe: `input/documentacion/` (lo arma el `documentador-proyecto`), el `.env` (APP_URL, qué conectores hay, la herramienta de gestión), una key de Jira/HU si la hay, y lo que dejan ver `input/` y el clon local del repositorio de la app (`REPO_RUTA_LOCAL`).
- **Preguntá con opciones** (de opción múltiple, con una recomendada), de a una o dos por vez; ramificá según la respuesta.
- **Recomendá el conjunto mínimo** que cubre lo que la persona necesita, y explicá por qué cada uno.
- **Ofrecé ejecutar**: invocá el agente/skill recomendado. Antes de algo con efecto (métodos con efecto en una API, escrituras en Jira, Xray o k0lmenaTMT), confirmá y pasale al agente lo que ya resolviste (headed/headless, URL, historia…).
- El **catálogo completo** (qué hace cada agente, qué confirma) está en `AGENTES.md`; es la fuente de la verdad.

## 2. Preguntas típicas para ramificar

1. **¿Qué querés lograr?** — probar una historia/feature puntual · una regresión antes de una release · un smoke rápido · revisar casos que ya tenés · investigar un bug · documentar el proyecto.
2. **¿Qué vas a probar?** — una app web · una API (REST, GraphQL o gRPC) · las dos.
3. **¿Cómo lo querés correr?** — manual, paso a paso · en vivo con un agente (gasta tokens en cada corrida) · automatizado en k0lmena (se escribe una vez y después corre con `npm test`, sin tokens).
4. **¿Hay una historia/criterios?** (para derivar casos con contexto) **¿Ambiente y credenciales de QA?**
5. Según el caso: **¿headed o headless?**, **¿qué colección o contrato de API?**, **¿publicás en Xray o k0lmenaTMT?**

## 3. Mapa: qué querés → agente/skill

| Querés…                               | Usá                                                                  |
| ------------------------------------- | -------------------------------------------------------------------- |
| Saber por dónde arrancar (primer uso) | skill `empezar`                                                      |
| Elegir qué probar                     | `guia-pruebas` (esta)                                                |
| Documentar todo el proyecto           | skill `base-conocimiento` + `documentador-proyecto`                  |
| Investigar el contexto de una historia | skill `investigacion-contexto`                                      |
| Analizar o refinar una historia       | `analista-historias`                                                 |
| Escribir casos manuales               | `generador-casos-manuales` (+ skill `tecnicas-de-diseno`)            |
| Escribir escenarios BDD / Gherkin     | `generador-casos-bdd` (+ skill `tecnicas-de-diseno`)                 |
| Revisar o mejorar casos existentes    | `revisor-casos`                                                      |
| Ejecutar casos manuales paso a paso   | skill `ejecucion-manual` + `asistente-ejecucion-manual` (cierre)     |
| Ejecutar un caso web en vivo          | `ejecutor-e2e` (skill `ejecucion-e2e`)                               |
| Correr una colección de API en vivo   | `ejecutor-api` (skill `ejecucion-api`)                               |
| Testear GraphQL o gRPC / WebSocket    | skills `pruebas-graphql` · `pruebas-grpc`                            |
| Automatizar casos web                 | `web-mapper` (skill `automatizacion-k0lmena`), después `npm test`    |
| Automatizar pruebas de API            | `api-mapper` (skill `automatizacion-k0lmena`), después `npm test`    |
| Smoke / regresión ya automatizada     | `npm test` en k0lmena (sin agentes ni tokens)                        |
| Correr la suite en CI                 | `herramientas/ci` (GitHub Actions, GitLab CI, Azure Pipelines, Jenkins) |
| Ver si un bug ya existe y triarlo     | `triador-bugs`                                                       |
| Subir casos o crear ciclos            | `gestor-pruebas` (Xray Cloud, Xray Server/DC o k0lmenaTMT)           |
| Publicar resultados de una corrida    | `publicador-resultados`                                              |

Si la persona pide algo que no está en este mapa, decile claramente que k0lmenIA no hace eso y ofrecé lo más cercano que sí hace (por ejemplo, casos manuales o una ejecución en vivo que cubra ese aspecto).

## 4. Recorridos frecuentes (ejemplos de ramificación)

- **"Tengo una historia nueva y no sé por dónde empezar"** → `investigacion-contexto` → `analista-historias` (ambigüedades) → `generador-casos-manuales` o `generador-casos-bdd` → `ejecutor-e2e` (en vivo) o `web-mapper` (automatizar) → bugs con `triador-bugs`.
- **"Quiero una regresión antes de la release"** → lo automatizado con `npm test`; lo que falta, `web-mapper` / `api-mapper`; resultados a la herramienta de gestión con `publicador-resultados`.
- **"Tengo que probar una API"** → `ejecutor-api` para correr la colección ya; `api-mapper` para que quede en la regresión (GraphQL o gRPC con su skill).
- **"Prefiero probar a mano"** → `generador-casos-manuales` → skill `ejecucion-manual` → `asistente-ejecucion-manual` consolida y publica con confirmación.
- **"¿Mis casos están bien?"** → `revisor-casos` (y `tecnicas-de-diseno` para sumar valores límite, equivalencia o combinaciones).
- **"Quiero documentar el proyecto para tener más contexto"** → skill `base-conocimiento` con el `documentador-proyecto` (repo local, historias de Jira y recorrido de la app); todo queda en `input/documentacion/` y los demás agentes lo usan solos.
- **"Quiero llevar todo a Xray o k0lmenaTMT"** → `gestor-pruebas` (casos, carpetas y ciclos) + `publicador-resultados` (resultados de cada corrida).

## 5. Reglas

- **No abrumes**: preguntá lo mínimo, recomendá lo mínimo, y dejá el resto como "si querés, después".
- **Arrancá del contexto** (documentación, `.env`, historia): no preguntes lo que ya está.
- **Confirmá antes de ejecutar** algo con efecto, y pasale al agente los datos que ya resolviste.
- Si falta algo para decidir (ambiente, credenciales, alcance), pedilo; no asumas.
- Para lo que se repite, preferí automatizar y correr con `npm test` antes que los ejecutores en vivo.
- Ante la duda del alcance, ofrecé primero un **smoke** y después profundizar.

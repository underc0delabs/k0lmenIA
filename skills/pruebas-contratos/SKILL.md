---
name: pruebas-contratos
description: El cómo del contract testing — consumer-driven (Pact) vs. provider, el flujo consumidor→broker→proveedor, expectativas y matchers, verificación del proveedor, Pact Broker y can-i-deploy, compatibilidad, para REST, GraphQL, mensajería y gRPC. Lo usa el probador-contratos; complementa a los agentes de API y mensajería.
---

# Contract testing (pruebas de contrato)

El contract testing verifica que **dos servicios se entiendan** sin levantar todo el sistema: el **consumidor** declara qué espera de la API y el **proveedor** se verifica contra esa expectativa. Atrapa los "se rompió la integración" sin la lentitud ni la fragilidad de un E2E. Se complementa con los skills de API (`ejecucion-api`, `pruebas-graphql`, `pruebas-grpc`) y `pruebas-async`.

## 1. Qué es y qué no

- **No es** un test E2E ni de integración: no valida reglas de negocio ni datos reales, valida **la forma del intercambio** (endpoints, campos, tipos, status, eventos).
- Atrapa cambios que rompen la compatibilidad (un campo renombrado, un tipo cambiado, un status distinto) **antes** de desplegar.
- No reemplaza las pruebas funcionales del proveedor; las complementa.

## 2. Consumer-driven (Pact)

- El **consumidor** define el contrato: "cuando pido `GET /pago/123`, espero `200` con `{id, estado, monto}`". Eso genera un **pact** (un archivo).
- El **proveedor** se **verifica** contra ese pact: reproduce cada interacción y confirma que responde como el consumidor espera.
- Así el proveedor sabe **a quién rompe** si cambia algo: si una verificación falla, hay un consumidor real que dejaría de andar.

## 3. El Pact Broker y can-i-deploy

- Los pacts se publican en un **Pact Broker** (o PactFlow), versionados por el commit y **tagueados** por rama/entorno.
- **`can-i-deploy`**: antes de desplegar, pregunta al broker si esta versión es compatible con lo que hay en el otro lado en ese entorno. Es la red de seguridad real del contract testing.
- El **WIP/pending pacts** evita que un pact nuevo de un consumidor rompa el build del proveedor de golpe.

## 4. Matchers y provider states

- Las expectativas usan **matchers por tipo** (es un string, un número, una fecha ISO), **no por valor exacto**: si matcheás el valor literal, el contrato se rompe con cualquier dato distinto (falso positivo).
- **Provider states**: "dado que existe el pago 123" — el proveedor prepara ese estado antes de verificar la interacción. Sin provider states bien definidos, la verificación es frágil.

## 5. Versionado y compatibilidad

- El contrato es la unidad de compatibilidad: **agregar un campo opcional** no rompe; **sacar un campo, cambiar un tipo o un status** sí. Probá la evolución de la API contra los consumidores viejos.
- **Hacia atrás** (consumidor viejo, proveedor nuevo) y **hacia adelante** (consumidor nuevo, proveedor viejo) según la política de despliegue.

## 6. REST, GraphQL, mensajería y gRPC

- **REST**: lo clásico (request/response).
- **GraphQL**: el contrato es sobre la query y la forma del `data`/`errors` (ver `pruebas-graphql`).
- **Mensajería/eventos** (async): **message pacts** — el productor publica un evento con cierta forma y el consumidor lo espera así (ver `pruebas-async`); el broker no está en el loop, se verifica la forma del mensaje.
- **gRPC**: el `.proto` es el contrato; la compatibilidad de Protobuf (campos reservados, no reusar números) es contract testing nativo (ver `pruebas-grpc`).

## 7. Bi-direccional

- **Contract testing bi-direccional**: comparar la **spec del proveedor** (OpenAPI) contra el **pact del consumidor**, sin que el proveedor corra la verificación. Útil cuando el proveedor ya tiene una OpenAPI confiable.

## 8. Herramientas

- **Pact** (multi-lenguaje) + **Pact Broker/PactFlow** es el estándar de consumer-driven.
- **Spring Cloud Contract** en el mundo JVM.
- **Schemathesis / Dredd** validan una API corriendo contra su **OpenAPI** (contrato proveedor-first).
- El agente orquesta estas herramientas (con el `ejecutor-api` para la parte HTTP) y resume el resultado.

## 9. Pitfalls

- **Matchers por valor** en vez de por tipo → contratos frágiles que fallan con cualquier dato.
- Meter **lógica de negocio** en el contrato (validar montos, cálculos): eso es funcional, no contrato.
- **Pacts desactualizados**: un consumidor que ya no existe deja un pact que frena al proveedor.
- No usar `can-i-deploy`: tener pacts pero desplegar igual sin chequear compatibilidad.
- Provider states no implementados → verificaciones que fallan por el estado, no por el contrato.

## 10. Preguntas típicas para el equipo

Cuando no está escrito, son `FI-XX`:

- ¿Qué servicios son consumidor y proveedor, y qué protocolo (REST/GraphQL/gRPC/eventos)?
- ¿Usan Pact/PactFlow u otra herramienta? ¿Hay un broker?
- ¿Se corre `can-i-deploy` en el pipeline antes de desplegar?
- ¿Qué política de compatibilidad (hacia atrás, hacia adelante)?
- ¿Quién define los provider states y cómo se preparan?

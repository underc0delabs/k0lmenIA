---
name: pruebas-observabilidad
description: El cómo de probar la observabilidad — logs estructurados (con trace id, sin PII), métricas Prometheus (RED/USE, cardinalidad), trazas OpenTelemetry, healthchecks (liveness vs. readiness), error tracking, SLOs y alertas. Lo usa el analista-observabilidad; se apoya en analista-logs y el monitoreo sintético.
---

# Pruebas de observabilidad

Un sistema es observable si, cuando algo falla en producción, **se puede entender qué pasó** desde afuera: por sus **logs, métricas y trazas**. Acá se valida que la app **emita bien** esas señales (no que anden los features), más los healthchecks y las alertas. Se complementa con `analista-logs` (análisis de logs) y el monitoreo sintético (`npm run monitorear`).

## 1. Logs (structured logging)

- **Formato estructurado** (JSON), no texto suelto; con **nivel** correcto (error/warn/info/debug) y timestamp.
- **Correlación**: cada log de una request lleva un **request id / trace id** que permite seguir todo el flujo.
- **Sin PII ni secretos** en los logs (tokens, tarjetas, contraseñas, datos personales) — es el hallazgo más común y grave.
- Un error se loguea **una vez**, con contexto útil (no 50 líneas de ruido ni un stack trace mostrado al usuario).

## 2. Métricas (Prometheus/OpenMetrics)

- Que existan las **métricas esperadas** (la herramienta `npm run observabilidad` las lista y marca las que faltan).
- **RED** para servicios (Rate, Errors, Duration) y **USE** para recursos (Utilization, Saturation, Errors).
- **Nombres y labels** consistentes y con sentido; **cardinalidad** controlada (un label con el id de usuario explota la métrica).
- Los **contadores** suben ante tráfico real; los **histogramas** de latencia tienen buckets razonables.

## 3. Trazas distribuidas (OpenTelemetry)

- Cada operación genera **spans** con nombre y atributos; el **contexto se propaga** entre servicios (header `traceparent`), así una request se ve de punta a punta.
- **Sampling** configurado (no el 100% en prod si no corresponde); la latencia por span ayuda a encontrar el cuello de botella.
- Que una llamada a una dependencia (DB, API) aparezca como span hijo.

## 4. Healthchecks

- **Liveness** (¿el proceso está vivo?) vs. **readiness** (¿puede atender tráfico?): son distintos. La readiness debe dar **no-ready** si una dependencia crítica está caída (cruza con `probador-resiliencia`), para que el balanceador lo saque de rotación.
- `/health`, `/healthz`, `/readyz` y `/metrics` responden rápido y sin autenticación pesada.

## 5. Error tracking

- Los errores llegan al tracker (Sentry, etc.) con **stack, request id, usuario y release/version**; sin duplicados masivos; con breadcrumbs útiles.

## 6. SLIs / SLOs y alertas

- Definí los **SLIs** (disponibilidad, latencia p95/p99, tasa de error) y verificá que las **alertas disparen** cuando se viola el umbral y **se resuelvan** al normalizar (probalo provocando la condición en QA, p. ej. con caos de `probador-resiliencia`).
- Alertas accionables (sin ruido/fatiga): que apunten a un runbook.

## 7. Automatizar

- `npm run observabilidad` (`herramientas/observabilidad/observabilidad.py`) chequea healthchecks y el `/metrics` (métricas presentes/faltantes) — solo lectura, sin carga.
- Generá tráfico (con `ejecutor-api` o Playwright) y **verificá la señal**: en el backend de observabilidad (Prometheus/Grafana, Loki, Jaeger/Tempo, ELK) o en los logs (`analista-logs`); la correlación por trace id.
- Para carga y ver el comportamiento bajo estrés, `performance-mapper`.

## 8. Bugs típicos de observabilidad

- **PII o secretos en los logs**.
- Logs sin trace id → imposible correlacionar una request entre servicios.
- Métrica esperada que no existe; label de alta cardinalidad (id de usuario/request) que infla el TSDB.
- Readiness que da OK aunque la base esté caída → el balanceador manda tráfico a un pod que no puede atender.
- Contexto de traza que **no se propaga** (cada servicio arranca su propia traza).
- Alerta que no dispara (umbral mal) o que dispara siempre (ruido).
- Stack trace mostrado al usuario final.

## 9. Preguntas típicas para el equipo

Cuando no está escrito, son `FI-XX`:

- ¿Qué stack de observabilidad usan (Prometheus/Grafana, OTel, ELK, Datadog…)?
- ¿Qué métricas y SLOs son los oficiales? ¿Qué latencia/error es aceptable?
- ¿Qué debe hacer no-ready la readiness (qué dependencias son críticas)?
- ¿Qué se puede loguear y qué está prohibido (PII, secretos)?
- ¿Cómo se prueban las alertas en QA?

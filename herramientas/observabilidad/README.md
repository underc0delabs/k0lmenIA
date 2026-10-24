# Observabilidad

Relevamiento de **solo lectura** de la observabilidad de un servicio: healthchecks y métricas estilo Prometheus. Lo usa el agente `analista-observabilidad`.

- **`observabilidad.py`** (`npm run observabilidad`) — consulta los healthcheck(s) (liveness/readiness) y el endpoint `/metrics` (formato Prometheus/OpenMetrics), lista las métricas con su TYPE/HELP y chequea cuáles de las esperadas faltan.

```bash
npm run observabilidad -- --url https://mi-servicio --esperadas http_requests_total,http_request_duration_seconds
```

Solo GET; no genera carga (para eso, `performance-mapper`). La validación de logs y traces, y de que las alertas/SLOs disparen, la hace el `analista-observabilidad` con este insumo, los logs (`analista-logs`) y el APM. Sin dependencias (urllib de la stdlib).

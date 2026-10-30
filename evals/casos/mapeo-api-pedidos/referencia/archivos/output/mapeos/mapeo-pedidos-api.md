# Mapeo API · contrato pedidos 1.4.0

Fuente: input/api/openapi-pedidos.yaml · verificación: input/mapeos/verificacion-pedidos.md (staging, sin red ahora).

| Endpoint | Escenario | Estado | Nota |
|---|---|---|---|
| GET /pedidos | CP-API-001 Listar pedidos pagados | Mapeado | |
| GET /pedidos | CP-API-002 Sin token | Mapeado | 401 |
| GET /pedidos/{id} | CP-API-003 Detalle | Difiere de la spec | total llega como string; la spec dice number. Posible bug o spec desactualizada |
| GET /pedidos/{id} | CP-API-004 No existe | Mapeado | El cuerpo del 404 no está documentado: no se valida |
| GET /pedidos | CP-API-005 Estado inválido | Falta información | FI-01: con estado cancelado la API responde 200 con lista vacía; la spec no dice qué esperar |
| POST /pedidos | CP-API-006 Crear | Bloqueado | Método con efecto sin autorización: verificarlo con autorización y sacar @bloqueado |
| DELETE /pedidos/{id} | CP-API-007 Cancelar | Bloqueado | Método con efecto sin autorización |

El token se lee de API_TOKEN. Para correrlo: `cd herramientas/k0lmena && TAGS=@contrato-pedidos npm run test:api`

# Verificación contra la API de staging (sesión anterior, sin red ahora)

Base: https://api-staging.tienda-eval.com/v1 · token: API_TOKEN del .env
Solo se ejecutaron métodos sin efecto (GET). No hubo autorización para POST ni DELETE.

## GET /pedidos?estado=pagado
Request:
  GET /pedidos?estado=pagado
  Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.k0TokenApiEval.firma
Respuesta: 200
  [{"id": 1201, "estado": "pagado", "total": "1500.00"}, {"id": 1202, "estado": "pagado", "total": "830.50"}]

## GET /pedidos (sin token)
Respuesta: 401 {"error": "token requerido"}

## GET /pedidos/1201
Respuesta: 200 {"id": 1201, "estado": "pagado", "total": "1500.00"}
Nota: la spec dice que total es number; la API lo devuelve como string.

## GET /pedidos/999999
Respuesta: 404 {"codigo": "PED-404", "mensaje": "Pedido no encontrado"}
Nota: la spec no documenta el cuerpo del 404.

## GET /pedidos?estado=cancelado
Respuesta: 200 []
Nota: la spec solo lista pendiente, pagado y enviado; no dice qué responde con otro estado (¿400 o lista vacía?).

## POST /pedidos y DELETE /pedidos/{id}
No se ejecutaron: métodos con efecto sin autorización.

# Casos de API — pedidos (GraphQL, input/api/pedidos.graphql)

En GraphQL los errores vuelven en el arreglo `errors` de la respuesta (HTTP 200): cada caso negativo verifica `errors[0].extensions.code`.

| ID | Operación | Escenario | Verificación |
|---|---|---|---|
| CP-API-001 | query pedido | Pedido propio | data.pedido con id, estado y total |
| CP-API-002 | query pedido | Sin token | errors[0].extensions.code = UNAUTHENTICATED |
| CP-API-003 | query pedido | Pedido de otro usuario | errors[0].extensions.code = FORBIDDEN |
| CP-API-004 | query misPedidos | Sin limite (10 por defecto) | Hasta 10 pedidos, del más nuevo al más viejo |
| CP-API-005 | mutation crearPedido | cantidad 1 (mínimo) | Pedido creado en PENDIENTE |
| CP-API-006 | mutation crearPedido | cantidad 10 (máximo) | Pedido creado |
| CP-API-007 | mutation crearPedido | cantidad 0 (mínimo - 1) | errors[0].extensions.code = BAD_USER_INPUT |
| CP-API-008 | mutation crearPedido | cantidad 11 (máximo + 1) | errors[0].extensions.code = BAD_USER_INPUT |
| CP-API-009 | mutation cancelarPedido | Pedido PENDIENTE | data.cancelarPedido = true |
| CP-API-010 | mutation cancelarPedido | Pedido PAGADO | A confirmar (FI-01) |

## CP-API-002 — Sin token

```graphql
query { pedido(id: "P-1") { id estado } }
```

```json
{"data": {"pedido": null}, "errors": [{"message": "...", "extensions": {"code": "UNAUTHENTICATED"}}]}
```

## CP-API-007 — cantidad 0

```json
{"query": "mutation($i: PedidoInput!) { crearPedido(input: $i) { id } }", "variables": {"i": {"productoId": "PR-1", "cantidad": 0}}}
```

## Falta información

| ID | Qué falta | Pregunta |
|---|---|---|
| FI-01 | Qué pasa al cancelar un pedido PAGADO | ¿Se rechaza? ¿Con qué extensions.code? |

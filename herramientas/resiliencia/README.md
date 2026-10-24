# Resiliencia (caos server-side)

Inyección de fallas **reales en las dependencias** de un servicio con **Toxiproxy**, para probar cómo se comporta el sistema cuando una base, una API o un cache se ponen lentos o se caen. Complementa al `probador-resiliencia`, que simula fallas **del lado del navegador** (interceptando pedidos); esto es del **lado del servidor**.

- **`toxiproxy.py`** (`npm run toxiproxy`) — habla con la API REST de Toxiproxy (por defecto `http://localhost:8474`, o `TOXIPROXY_URL`) con la stdlib. Lista proxies e inyecta **latencia**, **caída** (deshabilita el proxy), **lentitud** (ancho de banda) y otras toxics, y las quita (`recuperar`/`reset`).

```bash
npm run toxiproxy -- --accion listar
npm run toxiproxy -- --accion latencia --proxy db --ms 2000 --jitter 500
npm run toxiproxy -- --accion caida --proxy db        # corta la dependencia
npm run toxiproxy -- --accion recuperar --proxy db     # la restablece
npm run toxiproxy -- --accion reset                     # saca todas las toxics
```

Cómo se usa: se pone **Toxiproxy entre el servicio y su dependencia** (el servicio apunta al puerto de Toxiproxy, y Toxiproxy reenvía a la dependencia real). Después se inyecta la falla, se observa cómo degrada el servicio (timeouts, reintentos, circuit breaker, fallback, mensaje claro) y **al terminar se hace `reset`**.

`listar` es de **lectura**; inyectar/quitar fallas **tiene efecto**, así que el `probador-resiliencia` lo confirma y lo corre solo en **QA**, nunca en producción.

**Requisitos**: tener **Toxiproxy** corriendo (binario `toxiproxy-server` o el contenedor `ghcr.io/shopify/toxiproxy`) con los proxies configurados hacia las dependencias. La herramienta no necesita librerías extra.

---
name: pruebas-ecommerce
description: El cómo de probar una tienda online de cualquier plataforma — catálogo, variantes, precios y redondeo, stock, carrito, checkout, impuestos, envíos, cupones, pagos de prueba, pedidos, reembolsos, correos, mobile y seguridad de la tienda. Lo usan probador-shopify, -wordpress, -prestashop, -vtex y los generadores cuando la historia es de una tienda.
---

# Pruebas de e-commerce

En una tienda, los bugs que más cuestan son los que **cambian lo que paga el comprador** o **lo que recibe la tienda**: un total mal calculado, un cupón que se aplica dos veces, un producto que se vende sin stock, un pago aprobado con el pedido en "pendiente". Este skill dice qué mirar en cualquier plataforma; los de cada una (`pruebas-shopify`, `pruebas-wordpress`) suman lo propio.

## 1. Antes de probar: el ambiente

- **Tienda de prueba o staging**, nunca la tienda real con clientes. Si es la real, solo se mira (relevamiento de solo lectura) y no se compra.
- **Pasarela en modo de prueba** (sandbox) y **tarjetas de prueba** del proveedor. Si la pasarela está en modo real, **no se paga**: se avisa y se espera a que la pasen a prueba.
- **Datos propios**: clientes, pedidos y cupones de prueba con el prefijo `QA-`, anotados para poder limpiarlos.
- **Lo que se espera** (montos de envío, regla de redondeo, mínimo para envío gratis, cuándo se descuenta el stock) sale de la historia o del negocio, **no de lo que hace hoy la tienda**. Si no está definido, es `FI-XX`.

## 2. Qué probar

```
+--------------------+-----------------------------------------------------------------+
| Área               | Qué mirar                                                       |
+====================+=================================================================+
| Catálogo           | Colecciones/categorías, filtros y orden, paginación, búsqueda   |
|                    | (sin resultados, acentos, plural, SKU), productos ocultos que   |
|                    | no aparecen                                                     |
+--------------------+-----------------------------------------------------------------+
| Ficha y variantes  | Cada combinación cambia precio, imagen, stock y URL; la         |
|                    | combinación inexistente o agotada no se puede comprar           |
+--------------------+-----------------------------------------------------------------+
| Precios            | Precio tachado mayor que el precio, redondeo, separadores de    |
|                    | miles y decimales, moneda, precio con y sin impuestos           |
+--------------------+-----------------------------------------------------------------+
| Stock              | Agotado: no se puede agregar (tampoco por URL directa);         |
|                    | preventa/backorder: avisa; dos compradores por la última unidad |
+--------------------+-----------------------------------------------------------------+
| Carrito            | Cantidad 0, 1, máximo y más que el stock; quitar; mini-carrito  |
|                    | y carrito con el mismo total; sesión vencida; volver atrás      |
+--------------------+-----------------------------------------------------------------+
| Checkout           | Invitado, crear cuenta, con sesión; validación de cada campo    |
|                    | (probador-formularios); cambio de dirección recalcula envío e   |
|                    | impuestos; doble clic en "Pagar"                                |
+--------------------+-----------------------------------------------------------------+
| Impuestos          | Por país/provincia, incluidos o no en el precio, sobre el envío |
+--------------------+-----------------------------------------------------------------+
| Envíos             | Cada zona y método, fuera de zona, límites de peso o valor de   |
|                    | cada tarifa, envío gratis justo en el mínimo, retiro en tienda  |
+--------------------+-----------------------------------------------------------------+
| Cupones            | Válido, vencido, mayúsculas/espacios, agotado, bajo el mínimo,  |
|                    | productos excluidos, combinado con otro, uno por cliente        |
+--------------------+-----------------------------------------------------------------+
| Pagos              | Aprobado, rechazado, error, 3-D Secure, abandonar la pasarela y |
|                    | volver, reintentar; estado del pedido y stock en cada caso      |
+--------------------+-----------------------------------------------------------------+
| Posventa           | Estados del pedido, cancelación, reembolso total y parcial      |
|                    | (devuelve stock), devoluciones                                  |
+--------------------+-----------------------------------------------------------------+
| Correos            | Confirmación, envío, reembolso, carrito abandonado, contraseña  |
|                    | (verificador-correos)                                           |
+--------------------+-----------------------------------------------------------------+
| Cuenta             | Registro, login, recuperar contraseña, direcciones, pedidos;    |
|                    | un cliente no ve pedidos ajenos (probador-permisos)             |
+--------------------+-----------------------------------------------------------------+
| Multi-moneda/idioma| Mismo importe en vidriera, carrito, checkout y correo;          |
|                    | traducciones (analista-traductor)                               |
+--------------------+-----------------------------------------------------------------+
| Mobile             | Checkout completo en mobile, teclado numérico en tarjeta y      |
|                    | teléfono, botón de pago visible                                 |
+--------------------+-----------------------------------------------------------------+
| SEO y legales      | Datos estructurados de producto, sitemap, políticas de          |
|                    | reembolso, privacidad y términos enlazadas en el checkout       |
+--------------------+-----------------------------------------------------------------+
```

## 3. Lo que suele quedar afuera

Además de las áreas de la tabla anterior, estas aparecen en casi toda tienda y casi nunca están en los casos:

```
+----------------------------+------------------------------------------+
| Área                       | Qué mirar                                |
+============================+==========================================+
| Página de gracias          | Recargarla o volver atrás después de     |
|                            | pagar no crea un segundo pedido ni cobra |
|                            | de nuevo; el número de pedido es el del  |
|                            | panel                                    |
+----------------------------+------------------------------------------+
| Carrito persistente        | El carrito sobrevive al cerrar el        |
|                            | navegador; al iniciar sesión se fusiona  |
|                            | con el de la cuenta sin duplicar ni      |
|                            | perder productos                         |
+----------------------------+------------------------------------------+
| Concurrencia               | Dos compradores por la última unidad:    |
|                            | uno compra, el otro recibe un aviso      |
|                            | claro (nunca los dos)                    |
+----------------------------+------------------------------------------+
| Carrito abandonado         | El correo llega con el carrito correcto  |
|                            | y el link lo recupera; no llega si la    |
|                            | compra se completó                       |
+----------------------------+------------------------------------------+
| Tarjetas de regalo y saldo | Saldo parcial, saldo que no alcanza      |
|                            | (paga la diferencia), vencida, usada en  |
|                            | dos pestañas a la vez                    |
+----------------------------+------------------------------------------+
| Productos digitales        | Link de descarga solo después de pagar,  |
|                            | límite de descargas y vencimiento, sin   |
|                            | envío en el checkout                     |
+----------------------------+------------------------------------------+
| Suscripciones              | Primer cobro, renovación, cambio de      |
|                            | plan, pausa, cancelación, tarjeta        |
|                            | vencida en la renovación                 |
+----------------------------+------------------------------------------+
| Precios por cliente (B2B)  | Lista de precios por grupo, mínimos por  |
|                            | pedido, precio con y sin sesión          |
+----------------------------+------------------------------------------+
| Cuotas                     | Cantidad de cuotas por tarjeta, interés  |
|                            | y total financiado mostrado igual en     |
|                            | checkout, pasarela y correo              |
+----------------------------+------------------------------------------+
| Monedas sin decimales      | Pesos chilenos, yenes: sin ",00" y sin   |
|                            | redondeos raros; separador de miles del  |
|                            | país                                     |
+----------------------------+------------------------------------------+
| Facturación                | Datos fiscales (CUIT/RUT/NIF, condición  |
|                            | frente al IVA), tipo de factura, factura |
|                            | en el correo o en Mi cuenta              |
+----------------------------+------------------------------------------+
| Direcciones                | Países sin provincias, códigos postales  |
|                            | con letras, dirección larga,             |
|                            | autocompletado del navegador             |
+----------------------------+------------------------------------------+
| Avisos de stock            | "Avisame cuando vuelva": llega una sola  |
|                            | vez cuando hay stock                     |
+----------------------------+------------------------------------------+
| Reseñas y favoritos        | Reseña solo de quien compró (si es la    |
|                            | regla), favoritos que sobreviven al      |
|                            | login                                    |
+----------------------------+------------------------------------------+
| Analítica y píxeles        | El evento de compra se dispara una sola  |
|                            | vez (no al recargar la página de         |
|                            | gracias), con el importe y la moneda     |
|                            | correctos                                |
+----------------------------+------------------------------------------+
| Feeds de productos         | El feed de Google Merchant o Meta tiene  |
|                            | el precio, la disponibilidad y la moneda |
|                            | de la vidriera                           |
+----------------------------+------------------------------------------+
| Cookies y consentimiento   | Sin aceptar, no se cargan los píxeles de |
|                            | marketing; el banner no tapa el botón de |
|                            | pagar en mobile                          |
+----------------------------+------------------------------------------+
```

## 4. La cuenta tiene que cerrar

En cada compra de prueba anotá y verificá: **subtotal + envío + impuestos − descuentos = total**, y que ese mismo total aparezca en el carrito, el checkout, la pasarela, el pedido del panel y el correo. Cualquier diferencia de centavos es un hallazgo.

- Con **cuotas**, además: total financiado = cuota × cantidad de cuotas, igual en el checkout y en la pasarela.
- Con **reembolso parcial**: lo devuelto + lo que queda cobrado = total original; el stock vuelve solo de lo devuelto.
- Con **varias monedas**: el redondeo se aplica una vez (por línea o por total, según la regla del negocio); si la regla no está escrita, es `FI-XX`.

## 5. Técnicas de diseño que más rinden en una tienda

Con el skill `tecnicas-de-diseno`:

```
+------------------------+------------------------------------------+
| Técnica                | Dónde aplicarla                          |
+========================+==========================================+
| Valores límite         | Mínimo para envío gratis y de un cupón   |
|                        | (justo, un centavo menos), tramos de     |
|                        | peso de cada tarifa, stock 0 / 1 /       |
|                        | máximo, cantidad máxima por pedido,      |
|                        | cuotas mínimas                           |
+------------------------+------------------------------------------+
| Clases de equivalencia | Direcciones por zona de envío, tarjetas  |
|                        | por resultado (aprobada, rechazada,      |
|                        | fondos insuficientes, 3-D Secure), tipos |
|                        | de producto (simple, variable, digital,  |
|                        | suscripción)                             |
+------------------------+------------------------------------------+
| Tabla de decisión      | Combinaciones de descuentos (cupón +     |
|                        | automático + envío gratis), impuestos    |
|                        | incluidos o no por país, invitado o con  |
|                        | cuenta                                   |
+------------------------+------------------------------------------+
| Transición de estados  | Estados del pedido (pendiente, pagado,   |
|                        | enviado, entregado, cancelado,           |
|                        | reembolsado) y del pago; qué transición  |
|                        | no debería poder pasar                   |
+------------------------+------------------------------------------+
| Pairwise               | Navegador × dispositivo × medio de pago  |
|                        | × moneda cuando no se puede probar todo  |
+------------------------+------------------------------------------+
```

## 6. Datos de prueba

- **Tarjetas de prueba** de cada proveedor (Stripe, Mercado Pago, PayPal, Adyen…): una aprobada, una rechazada, una con 3-D Secure y una con fondos insuficientes, tomadas de la documentación del proveedor.
- **Direcciones**: una por zona de envío, una fuera de toda zona, una de cada país con impuestos distintos.
- **Productos**: uno simple, uno con variantes, uno sin stock, uno con preventa, uno digital, uno con peso en el límite de una tarifa, uno excluido de los cupones.
- **Clientes**: invitado, con cuenta nueva, con historial de pedidos y, si aplica, de un grupo B2B.
- Los arma el `generador-datos-prueba`; todos con el prefijo `QA-` y anotados para limpiarlos.

## 7. Smoke, regresión y campañas

**Smoke test (5–10 min, después de cada deploy o para saber si la tienda "está viva"):**

1. La portada, una categoría y una ficha abren sin error y sin la consola en rojo.
2. Buscar un producto conocido devuelve resultados.
3. Agregar al carrito, ir al checkout y llegar hasta el pago (sin pagar).
4. Login de un cliente de prueba y "Mi cuenta" cargan.
5. La pasarela está en modo de prueba (si está en modo real, se corta y se avisa).

Si algo de esto falla, es **bloqueante**: no tiene sentido seguir con el resto hasta resolverlo.

**Regresión después de un cambio técnico** (tema o plantilla, app/plugin/módulo, actualización de versión o de la pasarela): correr el flujo principal completo —catálogo → ficha con variantes → carrito → checkout invitado y con cuenta → pago aprobado y rechazado → estado del pedido → correo— mirando la consola, más las áreas que toca el cambio. Lo ideal es tenerlo **automatizado** (`web-mapper` y después `npm test`, sin tokens) y sumar la **regresión visual** (`pixel-perfect`) y **cross-browser** (`cross-browser`) cuando cambió el tema. Después de actualizar algo, purgar la caché y verificar que el cambio se vea.

**Antes de una campaña o una release (regresión de campaña):**

1. Comprar un producto simple y uno con variantes, como invitado y con cuenta, con la pasarela de prueba: aprobado y rechazado.
2. Aplicar el cupón o descuento de la campaña: válido, antes de la fecha de inicio y después de la de fin (en la zona horaria de la tienda).
3. Precios programados de la campaña: empiezan y terminan a la hora pactada.
4. Envío gratis justo en el mínimo y un centavo debajo.
5. Stock de los productos en oferta y qué pasa al agotarse.
6. Correos de confirmación y de envío.
7. Ficha, colección y checkout en mobile: carga (`auditor-rendimiento-web`) y sin errores de consola.
8. Si se espera mucho tráfico: prueba de carga con el `performance-mapper` y que la caché no muestre carritos ajenos.

## 8. Rendimiento (qué medir en una tienda)

La velocidad se mide con el `auditor-rendimiento-web` (Lighthouse, Core Web Vitals) y la carga con el `performance-mapper` (plan guiado con `guia-performance`); este skill dice **dónde** mirar en una tienda:

- **Páginas que importan**: portada, **categoría con muchos productos** (paginación, filtros, orden), **ficha** (con variantes y galería), **resultados de búsqueda**, carrito y checkout. No alcanza con medir solo la portada.
- **Core Web Vitals**: LCP (imagen principal de la ficha y banner de la portada), CLS (precio, botón o banners que se mueven al cargar), INP (filtros, selector de variante, agregar al carrito).
- **Peso de imágenes**: formatos modernos (WebP/AVIF), tamaño correcto por dispositivo, lazy-load fuera de la primera pantalla.
- **Scripts de terceros**: apps, módulos y píxeles que bloquean el render o inflan el JS; medir con y sin ellos para ver cuánto cuesta cada uno.
- **Caché y su correctitud**: la caché acelera, pero **el carrito, el checkout y "Mi cuenta" no se cachean**: con dos navegadores, un carrito no puede aparecer en el otro. Tras cambiar precios o stock, el cambio tiene que verse (purgar la caché).
- **Backend**: páginas con cientos de consultas SQL (N+1 de un módulo), TTFB alto, APIs internas lentas (`verificador-datos` ayuda a ver la base).
- **Carga y picos**: antes de una campaña con mucho tráfico, prueba de carga del **flujo de compra** (no solo la portada) y confirmar que bajo carga la caché no muestre datos de otro comprador.

## 9. Seguridad de la tienda (qué revisar)

El escaneo y la explotación los hacen el `analista-seguridad` (pasivo) y el `pentester-web` (activo y autorizado); este skill lista los riesgos **propios de una tienda** para que no se escapen:

- **Manipulación de precio y cantidad**: cambiar el precio, la cantidad (0, negativa, enorme) o el total en la llamada que agrega al carrito o crea el pedido. El servidor tiene que recalcular y rechazar, nunca confiar en el valor que manda el cliente.
- **IDOR / datos de otro cliente**: ver el pedido, la factura, la dirección o la descarga **ajenos** cambiando el id en la URL o la API; "Mi cuenta" y las facturas solo del dueño.
- **Abuso de cupones y vales**: reusar un cupón de un solo uso, aplicarlo varias veces, códigos adivinables, saldo de una tarjeta de regalo gastado en dos pestañas a la vez.
- **Webhooks y notificaciones de pago**: la notificación de la pasarela se valida (firma/HMAC) y se procesa **una sola vez**; un pago no se puede marcar aprobado falsificando el callback.
- **Exposición**: pasarela en modo real en QA, panel de administración o modo debug accesibles, y `logs`, `.env` o backups que se bajan por URL son hallazgos.
- **PII y secretos**: datos personales o tokens en la URL, el correo o el HTML; claves de API con más permisos de los necesarios (mínimo privilegio).
- **Fuerza bruta y abuso**: login, recuperación de contraseña, aplicación de cupones y alta de cuentas con límite de intentos (rate limiting) y captcha donde corresponda.
- **Transporte**: HTTPS en todo el sitio, cabeceras de seguridad y cookies de sesión `Secure`/`HttpOnly`.
- **Pagos (PCI)**: los datos de tarjeta van directo a la pasarela (iframe/tokenización) y la tienda no los almacena. Para dinero, idempotencia y conciliación, el `probador-billeteras`.

## 10. Qué agente cubre cada parte

```
+---------------------------------------+--------------------------------------+
| Parte                                 | Herramienta o agente                 |
+=======================================+======================================+
| Flujos de compra en el navegador      | Playwright MCP (skill ejecucion-e2e) |
+---------------------------------------+--------------------------------------+
| Validaciones del checkout             | probador-formularios                 |
+---------------------------------------+--------------------------------------+
| Correos de la tienda                  | verificador-correos                  |
+---------------------------------------+--------------------------------------+
| Roles (cliente, gestor)               | probador-permisos                    |
+---------------------------------------+--------------------------------------+
| Velocidad de ficha y checkout         | auditor-rendimiento-web              |
+---------------------------------------+--------------------------------------+
| Accesibilidad del checkout            | analista-accesibilidad               |
+---------------------------------------+--------------------------------------+
| Cambios visuales del tema             | pixel-perfect                        |
+---------------------------------------+--------------------------------------+
| Safari y Firefox                      | cross-browser                        |
+---------------------------------------+--------------------------------------+
| Traducciones y formato de precios por | analista-traductor                   |
| país                                  |                                      |
+---------------------------------------+--------------------------------------+
| Pasarela caída o lenta                | probador-resiliencia                 |
+---------------------------------------+--------------------------------------+
| Campañas con mucho tráfico            | performance-mapper                   |
+---------------------------------------+--------------------------------------+
| Pedidos y stock en la base            | verificador-datos                    |
+---------------------------------------+--------------------------------------+
| Datos de prueba                       | generador-datos-prueba               |
+---------------------------------------+--------------------------------------+
| Seguridad                             | analista-seguridad, pentester-web    |
+---------------------------------------+--------------------------------------+
| Dinero, idempotencia y conciliación   | probador-billeteras                  |
+---------------------------------------+--------------------------------------+
| Regresión sin tokens                  | web-mapper y después npm test        |
+---------------------------------------+--------------------------------------+
```

## 11. Cómo reportar un bug de tienda

Además de la plantilla del proyecto (`generador-reportes-bug`), un bug de tienda lleva: **número del pedido de prueba**, los **importes** (subtotal, envío, impuestos, descuentos, total esperado y obtenido), el **cupón** o descuento, la **dirección o zona**, la **moneda o mercado**, el **medio de pago y la tarjeta de prueba** (solo su tipo, nunca el número completo de una real), el **dispositivo y navegador** y si fue **invitado o con cuenta**.

## 12. Preguntas típicas para el PO

Cuando la historia no lo dice, son `FI-XX`:

- ¿El redondeo es por línea o por total? ¿Los precios se muestran con impuestos incluidos?
- ¿Cuándo se descuenta el stock: al agregar al carrito, al pagar o al confirmar el pago?
- ¿Cuánto tiempo se reserva el stock de un pedido impago?
- ¿Los cupones se combinan entre sí y con los descuentos automáticos?
- ¿El envío gratis se calcula antes o después del descuento?
- ¿Qué pasa con un pedido si el pago queda pendiente (transferencia, efectivo)?
- ¿Se puede comprar sin cuenta? ¿Qué datos fiscales son obligatorios?
- ¿Un reembolso parcial devuelve el envío? ¿Y el stock?

## 13. Bugs típicos

- El total del correo o del pedido no coincide con el del checkout (redondeo, impuestos sobre el envío).
- Cupón que se aplica dos veces o sobre productos excluidos.
- Producto agotado que se puede agregar por URL directa o desde el mini-carrito.
- Pago aprobado en la pasarela con el pedido en "pendiente" o "fallido" (webhook o notificación que no llegó).
- Recargar la página de gracias crea un pedido duplicado o vuelve a disparar el evento de compra.
- Dos compradores se llevan la última unidad.
- Reembolso que no devuelve el stock.
- Cambio de dirección que no recalcula el envío.
- Envío gratis que se sigue ofreciendo después de que un cupón baja el subtotal debajo del mínimo.
- Precio tachado menor que el precio de venta.
- Moneda distinta entre vidriera y checkout, o ",00" en una moneda sin decimales.
- Oferta programada que empieza o termina a otra hora (zona horaria del servidor).
- Carrito que se pierde o se duplica al iniciar sesión.
- Checkout que se rompe después de actualizar el tema o un plugin/app.

## 14. Referencia común de los probadores de tienda (`probador-prestashop`, `probador-vtex`, …)

**Interpretar el relevamiento** (`<plataforma>.json` del script): leé solo `hallazgos`, `sugerencias`, `vidriera.chequeos` y las `tablas` que toca el alcance. Revisá `errores`: una consulta que falló por permiso de la clave o la app deja esa parte sin relevar, y se dice. Sin credenciales de administración solo hay vidriera (y catálogo público).

**Ejecución en el navegador**: Playwright MCP con el skill `ejecucion-e2e`, en **mobile y desktop**, siguiendo las pautas de Playwright del skill de la plataforma. Una captura por hallazgo en `output/<plataforma>/<HU o host>/capturas/`. En cada compra de prueba, **la cuenta tiene que cerrar** (sección 4) en todas las vistas: carrito, checkout, pasarela, pedido en el back-office y correo.

**Rendimiento y seguridad**, si entran en el alcance: el rendimiento al `auditor-rendimiento-web` (portada, categoría con muchos productos y ficha) y la carga al `performance-mapper`, planificada con `guia-performance`; la seguridad al `analista-seguridad` / `pentester-web`, con lo que dejó el relevamiento.

**`analisis.json`** (en `output/<plataforma>/<HU o host>/`, esquema del encabezado de `scripts/generar_informe_ecommerce.py`): `veredicto`, `veredicto_tono`, `resumen`, `pruebas` (cada una con `id` `CP-XXX` de la historia si existe, área, caso, dispositivo, resultado de la escala del proyecto, detalle y evidencia), `hallazgos` propios, `descartados` (del relevamiento, con motivo), `recomendaciones`, `proximos_pasos` y `falta_informacion`. Se regenera con:

```bash
python scripts/generar_informe_ecommerce.py output/<plataforma>/<HU o host>/<plataforma>.json output/<plataforma>/<HU o host>/informe-<plataforma>.html --analisis output/<plataforma>/<HU o host>/analisis.json
```

**Bugs**: cada falla confirmada se redacta con el `generador-reportes-bug`, con los datos de la plataforma (versión o cuenta, tema, módulo o app, tienda o canal), el dispositivo y el número del pedido de prueba.

**Respuesta**: el ambiente (staging, copia local, workspace de QA o producción), los hallazgos críticos y altos, las pruebas corridas con su resultado, los pedidos y clientes `QA-` creados (para limpiarlos), lo que no se pudo relevar y la ruta del informe; si conviene automatizar la regresión, el `web-mapper`.

**Antes de entregar**:
- La tienda estaba en `ECOMMERCE_URLS_AUTORIZADAS` y no se cambió nada de su configuración.
- Los pedidos de prueba fueron con la pasarela en modo de prueba (sandbox o medios que no cobran), confirmados, y están listados para limpiarlos.
- Lo esperado salió de la historia o del negocio; lo que no estaba definido quedó como `FI-XX`.
- `analisis.json` es JSON válido, con las severidades y resultados de la escala del proyecto, y el informe se regeneró sin error.

---
name: pruebas-shopify
description: El cómo de probar Shopify — tiendas de desarrollo y con contraseña, temas (OS 2.0, Theme Check), Liquid y traducciones, checkout y Bogus Gateway, Markets, envíos, descuentos, webhooks con HMAC y la Admin API de lectura. Lo usan probador-shopify y los mappers.
---

# Pruebas en Shopify

Shopify maneja el servidor, el checkout y los pagos; lo que cambia de una tienda a otra es **el tema, las apps y la configuración** (mercados, envíos, impuestos, descuentos). Ahí están casi todos los bugs. Se suma al skill `pruebas-ecommerce`.

## 1. La tienda

- **Tienda de desarrollo** (`plan.partnerDevelopment = true`): se pueden hacer pedidos de prueba sin cobro. Es donde se prueba.
- **Tienda real**: solo relevamiento de lectura. Un pedido de prueba, solo con la pasarela en modo de prueba, con confirmación, y después se cancela y archiva.
- **Tienda con contraseña** (`/password`): los chequeos públicos no pasan; con Playwright, se entra con la contraseña de la vidriera (del `.env`, nunca en el chat).

## 2. Tema

- **Vista previa sin publicar**: `?preview_theme_id=<id>` permite probar un tema nuevo sin afectar a los clientes. Comparar contra el publicado con `pixel-perfect`.
- **Secciones y bloques** (Online Store 2.0): cada plantilla (portada, colección, producto, carrito, página, blog, 404, búsqueda) puede tener secciones distintas; recorrelas todas.
- **Errores de Liquid** (`Liquid error: ...`, `Could not find asset snippets/...`) y **traducciones faltantes** (`translation missing: es.products.product.add_to_cart`) aparecen en la página: son bugs.
- **Theme Check** (`shopify theme check`, con la CLI de Shopify y el código del tema) encuentra errores de Liquid, assets pesados y traducciones que faltan antes de publicar.
- El objeto `Shopify.theme` del HTML dice qué tema y versión se está viendo.
- **Antes de editar, duplicar**: el tema duplicado es la copia de respaldo y el lugar para probar. Comparar el duplicado editado contra el publicado antes de publicarlo.
- **Restos de apps desinstaladas**: las apps viejas pegaban código en el tema (snippets, `{% render %}`, scripts); al desinstalarlas quedan llamadas a archivos que ya no existen (404 en la consola, `Could not find asset`). Las apps nuevas usan **theme app extensions** (bloques y app embeds) que se van con la app.
- **Metacampos y metaobjetos** (`product.metafields...`): si el tema los muestra (tabla de talles, materiales, ficha técnica), probar productos con el metacampo vacío, largo y con formato.
- **Búsqueda y filtros** (app Search & Discovery): filtros por variante, precio y disponibilidad; orden; sinónimos; productos agotados (si se ocultan o van al final, según la regla).
- **`robots.txt.liquid`** y **redirecciones de URL** (Navegación → Redirecciones): después de una migración o de cambiar handles, las URLs viejas tienen que redirigir, no dar 404.

## 3. Apps

- Las apps inyectan scripts (app embeds) y bloques: revisá la consola en cada página clave y el tiempo de carga con y sin la app (desactivar el embed en un tema duplicado).
- Después de instalar o actualizar una app: regresión de ficha, carrito y checkout.
- Las apps de suscripciones, reseñas, filtros y traducción son las que más rompen.

## 4. Checkout y pagos

- **Bogus Gateway** (proveedor de prueba): número de tarjeta `1` aprobada, `2` rechazada, `3` error de la pasarela; cualquier nombre, fecha futura y CVV.
- **Shopify Payments en modo de prueba**: las tarjetas de prueba de Shopify (por ejemplo, 4242 4242 4242 4242 aprobada, y las de rechazo y 3-D Secure de su documentación).
- Probar como **invitado** y con **cuentas de cliente** (las nuevas son sin contraseña, con código por correo).
- Las **extensiones de checkout** (checkout extensibility) y las **funciones** de descuento/envío/pago cambian el checkout: cada una es un caso.
- El total del checkout tiene que coincidir con `/cart.js` y con el pedido en el panel.
- **Botones de pago acelerado** (Shop Pay, Apple Pay, Google Pay, PayPal) en la ficha y el carrito: **saltean el carrito**, así que se saltean también lo que el tema valide ahí (nota obligatoria, casilla de términos, mínimo de compra). Probá que esas reglas se cumplan igual o que los botones no se muestren.
- **`checkout.liquid` ya no existe**: Shopify lo retiró y las personalizaciones viejas de Plus (scripts en el checkout, en la página de gracias y en el estado del pedido) se reemplazan por **extensiones de checkout** y **píxeles**. Si la tienda viene de esa época, probá que lo que hacía el código viejo (seguimiento, campos extra, mensajes) siga funcionando.
- **Pagos manuales** (transferencia, efectivo, contra entrega): el pedido queda con el pago pendiente; marcar como pagado desde el panel descuenta o no el stock según la configuración.

## 5. Pedidos y posventa

- Los pedidos hechos con Bogus Gateway o en modo de prueba quedan marcados como **de prueba** en el panel; igual descuentan stock y mandan correos.
- **Reembolso** desde el panel: total o parcial, con o sin **reponer el stock** (casilla *Restock*), y con o sin devolver el envío.
- **Editar un pedido** (agregar o quitar productos, cambiar cantidades): recalcula el total y pide un cobro o una devolución por la diferencia.
- **Cancelar** un pedido: reembolso y reposición de stock según lo que se marque.
- **Tarjetas de regalo** nativas: se venden como producto, llegan por correo con el código, se usan en el checkout (saldo parcial, saldo que no alcanza) y se pueden desactivar.
- **Suscripciones** (apps sobre *selling plans*): el selector de plan en la ficha, el primer cobro, la renovación y la cancelación desde la cuenta del cliente.
- **Shopify Flow** y apps de automatización: etiquetas, avisos y cambios automáticos que se disparan con el pedido; probá que se disparen una vez y con el pedido correcto.
- **B2B** (Plus): empresas y ubicaciones, catálogos con precios propios, mínimos y términos de pago (pagar a 30 días).
- **POS y retiro en tienda**: el stock se comparte entre la tienda online y el punto de venta; el retiro o la entrega local solo se ofrecen en las direcciones o ubicaciones configuradas.

## 6. Markets, moneda e impuestos

- Cada **mercado** puede tener moneda, idioma, dominio o subcarpeta, precios y redondeo propios: probar como comprador de cada uno (cambiar el país en el selector o por la URL del mercado).
- **Impuestos incluidos o no** (`taxesIncluded`) cambian el precio que se muestra; los impuestos sobre el envío (`taxShipping`) cambian el total.
- **Redondeo de precios** por mercado (por ejemplo, a ,99 o a números enteros) y **precios fijos** por mercado en lugar de la conversión automática: probar ambos.
- **Aranceles e impuestos de importación** en ventas internacionales: si se cobran en el checkout, que aparezcan en el total y en el pedido.
- **Redirección por geolocalización** (o el aviso de "¿Querés ir a la tienda de tu país?"): que no impida elegir otro país a mano y que no rompa el checkout.
- **Idiomas** (Translate & Adapt u otra app): textos del tema, de las notificaciones y del checkout en cada idioma (`analista-traductor`).

## 7. Envíos, ubicaciones e inventario

- **Perfiles de envío**: productos con perfiles distintos en el mismo carrito suman tarifas; un perfil sin métodos activos deja productos sin poder comprarse.
- **Ubicaciones**: de cuál se descuenta el stock y si se ofrece retiro en tienda.
- **Seguir vendiendo sin stock** (`inventoryPolicy = CONTINUE`) es preventa: confirmar con el negocio que es intencional.

## 8. Descuentos

- **Por código** (básico, compra X lleva Y, envío gratis) y **automáticos**; las reglas de **combinación** entre descuentos de producto, de pedido y de envío son la fuente más común de totales mal calculados.
- Límite de usos, uno por cliente, fechas, mínimo de compra o de cantidad, productos o colecciones incluidos.

## 9. Webhooks

- Cada webhook firma el cuerpo con **X-Shopify-Hmac-Sha256**: el receptor tiene que validarlo y rechazar uno alterado.
- Shopify reintenta: el receptor tiene que procesar **una sola vez** el mismo evento (`X-Shopify-Webhook-Id`).
- Un webhook a `http://`, `localhost` o un túnel (ngrok) en un ambiente compartido es un hallazgo.

## 10. APIs para el relevamiento (solo lectura)

- **Públicas**: `/products.json` (catálogo, paginado), `/products/<handle>.js`, `/cart.js` (carrito actual), `/policies/<política>`.
- **Admin API GraphQL** con el token de una **app personalizada con alcances `read_*`** solamente (`read_products`, `read_inventory`, `read_themes`, `read_shipping`, `read_markets`, `read_discounts`, `read_locations`). Nunca mutations. Tiene **límite de costo** por consulta: si responde `THROTTLED`, esperar y reintentar.
- La versión de la API (`SHOPIFY_API_VERSION`) es trimestral (`2026-07`, `2026-10`…) y cada una dura un año. Si una consulta falla en una versión, puede ser que el campo cambió de nombre: el relevamiento lo deja en "Consultas que no se pudieron hacer".
- `/products.json` devuelve hasta 250 productos por página (`?limit=250&page=N`) y no muestra el stock; el stock real sale de la Admin API.

## 11. Analítica y píxeles

- Los **eventos de cliente** (Configuración → Eventos de cliente: píxeles de Google, Meta, TikTok y personalizados) se disparan en el checkout: el evento de compra (`checkout_completed`) tiene que salir **una vez**, con el importe, la moneda y los productos del pedido, y no volver a salir al recargar la página de estado del pedido.
- Con el banner de cookies sin aceptar, los píxeles de marketing no tienen que cargar (Shopify respeta el consentimiento si el banner está bien configurado).

## 12. Automatizar con Playwright (web-mapper)

- Ubicar por rol y nombre accesible; los IDs de sección (`shopify-section-template--1234__main`) cambian al editar el tema.
- El **checkout** vive en otro dominio o subruta y carga campos de tarjeta en **iframes** (`card-fields`): usar `frameLocator`.
- Esperar a que `/cart/add.js` y `/cart/change.js` respondan antes de leer el contador del carrito.
- Sacar el aviso de cookies y los popups de suscripción al principio del escenario.
- **Tienda con contraseña**: completar el formulario de `/password` una vez y reutilizar la sesión guardada (`npm run login`), no en cada escenario.
- **Vista previa de un tema**: `?preview_theme_id=<id>` agrega una barra de vista previa abajo; cerrala para que no tape el botón de compra en mobile.
- **Captcha** (protección contra bots en cuentas y formularios de contacto): no se evade. En la tienda de desarrollo, pedí que lo desactiven para las pruebas automatizadas o dejá esos pasos como manuales.
- **Datos que cambian solos** (stock, precios de un mercado): verificá relativo al dato que leíste al empezar, no contra un número fijo.

## 13. Bugs típicos de Shopify

- `Liquid error` o `translation missing` a la vista después de editar el tema.
- Una app que duplica el botón de compra o rompe el selector de variantes.
- Precio por mercado sin redondear o con la moneda del mercado principal.
- Descuentos que se combinan cuando no deberían.
- Producto sin stock en la ubicación de despacho que igual se ofrece.
- Política de reembolso o privacidad sin publicar (falta en el pie del checkout).
- Botón de pago acelerado que permite comprar sin cumplir el mínimo o sin la casilla de términos del carrito.
- Restos de una app desinstalada que dan 404 en la consola o dejan un bloque vacío.
- URLs viejas sin redirección después de cambiar el handle de un producto o colección.
- Evento de compra del píxel duplicado al recargar la página de estado del pedido.
- Reembolso hecho sin reponer el stock cuando la regla era reponerlo.
- Metacampo vacío que deja un título sin contenido en la ficha.

## 14. Preguntas típicas para el PO (Shopify)

Además de las del skill `pruebas-ecommerce`, cuando no está escrito son `FI-XX`:

- ¿Se sigue vendiendo sin stock en algún producto (preventa)? ¿En cuáles?
- ¿Qué descuentos se pueden combinar (producto, pedido, envío)?
- ¿Los precios por mercado se convierten solos o son fijos? ¿Con qué redondeo?
- ¿Los botones de pago acelerado van en la ficha, en el carrito o en ninguno?
- ¿Las cuentas de cliente son obligatorias, opcionales o están desactivadas?
- ¿Qué apps están en el alcance de la prueba y cuáles son de terceros que no se prueban?
- ¿Un reembolso repone el stock por defecto?

## 15. Smoke, regresión, rendimiento y seguridad (Shopify)

Lo genérico (los cinco tipos de prueba) está en `pruebas-ecommerce`; acá lo propio de Shopify.

- **Smoke** (tienda de desarrollo o un tema en vista previa): portada, colección y ficha sin `Liquid error` ni `translation missing`; agregar al carrito y llegar al checkout; la pasarela en modo de prueba (Bogus Gateway o Shopify Payments test). Rápido y bloqueante.
- **Regresión**: después de **publicar un tema**, **instalar o actualizar una app** o un cambio de **checkout extensibility**, correr el flujo de compra completo (invitado y cuenta, aprobado y rechazado) mirando la consola; sumar `pixel-perfect` contra el tema publicado y `cross-browser`. Usar la **vista previa** del tema (`?preview_theme_id=`) para probar antes de publicar. Comparar con `Theme Check`.
- **Rendimiento**: el **Online Store speed report** de Shopify y Lighthouse (`auditor-rendimiento-web`) en portada, colección y ficha; el impacto de cada **app embed** (medir con y sin el embed en un tema duplicado); imágenes servidas por el CDN de Shopify con el tamaño correcto; secciones pesadas de Online Store 2.0. El servidor, el checkout y los pagos los maneja Shopify, así que el margen está en **tema y apps**.
- **Seguridad**: Shopify maneja la infraestructura y el PCI del checkout, así que el foco es la **configuración**: webhooks firmados con **X-Shopify-Hmac-Sha256** y procesados una sola vez (`X-Shopify-Webhook-Id`); tokens de la Storefront API y claves de apps privadas con el **mínimo alcance**; que no queden tokens ni secretos en el código del tema ni en metafields públicos; cuentas de cliente (que un cliente no vea pedidos ajenos); **app proxy** que valida la firma; contraseña de la vidriera en staging. La seguridad activa, con `analista-seguridad` / `pentester-web`.

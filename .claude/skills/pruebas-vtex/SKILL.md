---
name: pruebas-vtex
description: El cómo de probar VTEX — cuentas y workspaces (master vs. QA), storefront (Store Framework/IO), Catalog, Pricing, Logistics, Payments, Checkout y orderForm, OMS, marketplace, multi-moneda e idioma, rendimiento y seguridad, con las APIs de lectura. Lo usan probador-vtex y los mappers.
---

# Pruebas en VTEX

VTEX es una plataforma **SaaS, API-first y nativamente marketplace** (muy usada en LATAM). Como en Shopify, VTEX maneja la infraestructura, el checkout y gran parte de los pagos; lo que cambia de una tienda a otra (y donde están los bugs) es **el catálogo y sus trade policies, las promociones, el envío, los medios de pago, las apps de VTEX IO y el tema**. Se suma al skill `pruebas-ecommerce`.

## 1. Cuenta, entornos y workspaces

- Una tienda es una **cuenta** (`micuenta`). El admin vive en `micuenta.myvtex.com`; las APIs, en `micuenta.vtexcommercestable.com.br`.
- **Workspaces**: copias aisladas de la cuenta. **`master` es producción**. Para QA se usa un **workspace propio** (`qa--micuenta.myvtex.com`): mismos datos, cambios aislados. Es el equivalente a staging; **nunca se prueba destructivo contra master**.
- **Bindings y sales channels (trade policies)**: una cuenta puede tener varias vidrieras (dominios/idiomas/monedas) atadas a **canales de venta**. Un producto se vende en un canal solo si tiene esa trade policy; probar **cada canal**.
- **Sales channel en la URL/API**: `?sc=1` fija el canal; precios y disponibilidad cambian por canal.

## 2. Storefront y apps (VTEX IO)

- Tres generaciones de storefront: **Store Framework** (VTEX IO, React, SSR), **FastStore** (Next.js, headless) y el **legacy CMS Portal**. Confirmá cuál usa: cambian el tema, el deploy y dónde se rompe.
- **VTEX IO** son apps versionadas que se instalan por workspace (`vtex list`); una app nueva se prueba en un workspace antes de promover a master. Un error de render (`RenderRuntime`, pantalla en blanco, GraphQL error) es un bug.
- Las apps de reseñas, búsqueda inteligente (**Intelligent Search**), wishlist y los pixels suelen ser las que más rompen.

## 3. Catalog System

- **Producto → SKUs** (las variantes de VTEX): cada SKU tiene su referencia (RefId), EAN, imágenes, dimensiones y specifications. Un SKU sin precio o sin stock en el canal no se puede comprar.
- **Categorías, marcas y specifications** (campos y filtros): productos sin categoría activa o sin specification obligatoria no aparecen bien en el catálogo o los filtros.
- **Trade policies**: el SKU tiene que estar en la trade policy del canal para venderse ahí.
- **Indexación**: tras cargar o cambiar productos, la búsqueda (Intelligent Search) tarda en indexar; un producto "nuevo que no aparece" puede ser indexación, no un bug.

## 4. Pricing

- Los precios viven en **price tables** por canal/lista; además hay **precios fijos** por fecha o cantidad. El `Price` (con promo) y el `ListPrice` (tachado): el tachado tiene que ser **mayor** que el precio.
- Un SKU **sin precio** en la tabla del canal no se vende aunque tenga stock.

## 5. Logistics (inventario y envíos)

- **Inventario por depósito (warehouse)** y **docks**; el stock disponible depende del depósito que cubre la región del comprador.
- **Políticas de envío (SLAs)** y **carriers**: cada una con región, costo, peso y tiempo. **Sin ninguna SLA activa no se puede comprar con envío.** Probar por **región/CEP (código postal)**, envío gratis, retiro en punto (pickup) y el recálculo al cambiar la dirección.

## 6. Promotions & Taxes

- **Promociones** (regular, combo, "compre junto", progresiva, por cupón): fechas, canal, condiciones y **acumulación** (qué promos se combinan). La acumulación mal configurada es la causa típica de totales mal calculados.
- **Cupones**: válido, vencido, por canal, límite de uso.
- **Impuestos**: por región o integrados con un proveedor fiscal; el total tiene que reflejarlos.

## 7. Payments

- **Condiciones de pago** y **gateways** por canal; cada medio en **sandbox** (aprobado, rechazado, 3-D Secure) y, si aplica, **cuotas** (interés y total financiado iguales en checkout, pasarela y correo).
- **Antifraude**: no tiene que rechazar una compra legítima de prueba; revisar el flujo de análisis (aprobado/denegado/en análisis).
- Una condición de pago en **modo real** en QA es un hallazgo.

## 8. Checkout y orderForm

- El carrito y el checkout son el **orderForm** (API `/api/checkout/pub/orderForm`): items, precios, envío, pago, **marketing data** (cupones/UTM) y totalizadores.
- **La cuenta tiene que cerrar**: el total del orderForm = el del checkout = el de la pasarela = el del pedido (OMS) = el del correo. Cualquier diferencia es un hallazgo.
- Probar **invitado y con cuenta**, cambio de dirección que recalcula envío e impuestos, doble clic en pagar (no duplica el pedido), y la página de confirmación (recargarla no crea otro pedido ni re-dispara el pixel de compra).

## 9. OMS, posventa y suscripciones

- **OMS**: estados del pedido (payment-pending, payment-approved, handling, invoiced, shipped, delivered, canceled); que las transiciones y los correos salgan en el momento correcto.
- **Cancelación y devolución**: reposición de stock y reembolso según la regla.
- **Subscriptions** (si está la app): primer cobro, renovación, cambio y cancelación.
- **Marketplace/seller**: VTEX es nativamente marketplace (1P y 3P); un pedido con sellers distintos se separa y cada seller maneja su envío y su estado.

## 10. Master Data y B2B

- **Master Data** guarda clientes (CL), direcciones (AD) y entidades propias. Un cliente ve solo lo suyo; probar que no se acceda a datos ajenos por la API (IDOR).
- **B2B** (VTEX B2B Suite): organizaciones, costos y roles; listas de precios y aprobación de pedidos por organización.

## 11. Smoke test

Rápido y bloqueante (en un workspace de QA, no en master):

1. La portada, una categoría y una ficha abren sin error de render ni consola rota.
2. La búsqueda (Intelligent Search) devuelve resultados.
3. Agregar un SKU al carrito y llegar al checkout (orderForm con el ítem y el total).
4. Login de un cliente de prueba y "Mis pedidos" cargan.
5. Hay al menos un canal de venta activo, una SLA de envío y una condición de pago (en sandbox).

## 12. Regresión

- Después de **promover una app de VTEX IO**, **cambiar el tema** o tocar catálogo/precios/promos, correr el flujo de compra completo en el workspace de QA antes de promover a master: catálogo → ficha con SKUs → carrito → checkout invitado y con cuenta → pago aprobado y rechazado → estado del pedido → correo, mirando la consola.
- Sumar **regresión visual** (`pixel-perfect`) y **cross-browser** (`cross-browser`) cuando cambió el tema, y comparar el workspace de QA contra master.

## 13. Rendimiento

- Medir con el `auditor-rendimiento-web` (CWV) en portada, categoría con filtros, ficha y búsqueda; para carga, el `performance-mapper` (`guia-performance`).
- Propio de VTEX: el **SSR de VTEX IO** y la **CDN**, la **latencia del orderForm** y del **search (Intelligent Search)**, el impacto de cada app de VTEX IO (bloquea render / infla el JS). El checkout y el orderForm no se cachean.

## 14. Seguridad

El escaneo y la explotación los hacen el `analista-seguridad` y el `pentester-web`; propio de VTEX:

- **AppKey/AppToken con mínimo privilegio** (roles del License Manager), nunca en el front ni en el repo; rotación.
- **Manipulación del orderForm**: cambiar precio, cantidad o marketing data en la API; el servidor tiene que recalcular y rechazar.
- **IDOR** en OMS (`/api/oms/.../orders/{id}`) y Master Data: no ver pedidos, direcciones ni documentos ajenos.
- **Antifraude** activo y **webhooks/hooks** de pago validados y procesados una sola vez.
- **Workspaces y exposición**: un workspace de QA con datos sensibles accesible públicamente; endpoints `pvt` que respondan sin credenciales.

## 15. APIs para el relevamiento (solo lectura)

- **Públicas** (sin credenciales): Catalog System `GET /api/catalog_system/pub/products/search` (catálogo del canal con SKUs, precio y disponibilidad en `commertialOffer`), `GET /api/catalog_system/pub/portal/pagetype/...`, y el `GET /api/checkout/pub/orderForm/{id}` de un orderForm existente.
- **Administración** (headers `X-VTEX-API-AppKey` y `X-VTEX-API-AppToken`, solo lectura): canales de venta (`/api/catalog_system/pvt/saleschannel/list`), políticas de envío (`/api/logistics/pvt/shipping-policies`), promociones (`/api/rnb/pvt/benefits/calculatorconfiguration`), inventario, pricing y OMS. Nunca métodos de escritura.
- La herramienta `npm run vtex` releva la vidriera y el catálogo público siempre, y con AppKey/AppToken suma canales, envíos y promociones.

## 16. Automatizar con Playwright (web-mapper)

- Ubicá por rol y nombre accesible; en Store Framework los `class` de los bloques (`vtex-store-components-*`) cambian al actualizar la app.
- Esperá a que respondan las llamadas del **orderForm** (`/api/checkout/pub/orderForm`) antes de leer el total o el contador del carrito; la búsqueda llama a Intelligent Search.
- Probá sobre el **workspace de QA** (`qa--micuenta.myvtex.com`), no master.
- Sacá el aviso de cookies y los popups de newsletter al principio del escenario.
- Captcha en login o contacto: no se evade; pedí desactivarlo en el workspace de QA o dejá esos pasos como manuales.

## 17. Bugs típicos de VTEX

- Producto sin precio o sin stock en el canal que igual aparece (o al revés: con stock pero fuera de la trade policy).
- Promociones que se acumulan cuando no deberían, o que no respetan el canal o la fecha.
- SLA de envío sin cobertura para una región → no se puede comprar ahí.
- Total del orderForm distinto al del pedido en OMS (impuestos, envío, promo).
- Una app de VTEX IO promovida a master que rompe la ficha o el checkout.
- Pixel de compra duplicado al recargar la confirmación.
- Precio tachado (ListPrice) menor o igual al precio de venta.
- Pedido de marketplace con varios sellers que no se separa bien.
- AppKey/AppToken con permisos de más o expuesto en el front.
- Workspace de QA con datos de producción accesible públicamente.

## 18. Preguntas típicas para el PO (VTEX)

Además de las del skill `pruebas-ecommerce`, cuando no está escrito son `FI-XX`:

- ¿Qué storefront usa (Store Framework, FastStore, legacy)?
- ¿Qué canales de venta (trade policies) entran en la prueba y con qué moneda cada uno?
- ¿Qué promociones se pueden acumular entre sí?
- ¿Qué medios de pago y en qué modo (sandbox)? ¿Hay cuotas?
- ¿Hay marketplace con sellers 3P? ¿Y suscripciones o B2B?
- ¿Sobre qué workspace se prueba (nunca master)?
- ¿Qué apps de VTEX IO están en el alcance y cuáles son de terceros?

## Referencia del `probador-vtex`

**Relevamiento** (solo lectura): `npm run vtex -- --tienda https://www.mi-tienda.com --cuenta micuenta [--historia HU-001] [--sc 1] [--producto <url>] --confirmar` deja `output/vtex/<HU o host>/vtex.json` e `informe-vtex.html` (la corrida anterior pasa a `historial/`). Con `VTEX_APP_KEY` y `VTEX_APP_TOKEN` (app de solo lectura) suma las APIs de administración; sin ellos, vidriera y catálogo público. La cuenta sale de `--cuenta`/`VTEX_ACCOUNT` o de la URL `*.myvtex.com`/`*.vtexcommercestable.com.br`; el canal de ventas puntual, de `--sc`.

**Prioridades**: primero lo que impide comprar (sin canal de venta activo, sin SLA de envío, sin precio/stock en el canal, condición de pago en modo real), después lo que cambia el total (promociones y su acumulación, impuestos, envío, moneda por canal), SKUs y stock, el checkout/orderForm (invitado y cuenta), OMS y marketplace, el rendimiento (VTEX IO, orderForm, search) y la seguridad.

**Smoke primero** (sobre el workspace de QA): portada, categoría, ficha y búsqueda sin error de render ni consola rota; agregar un SKU al carrito y llegar al checkout (orderForm con el ítem y el total); canal activo, SLA de envío y condición de pago en sandbox. Si falla, es bloqueante y se corta ahí.

**La cuenta tiene que cerrar**: total del orderForm = checkout = pasarela = pedido (OMS) = correo.

**Seguridad a derivar** con lo del relevamiento: orderForm manipulable, IDOR en OMS, AppKey con permisos de más, promos que se acumulan mal.

**Complementos** según el alcance: `npm run formularios` (checkout), `npm run correos` (transaccionales), `npm run permisos` (Mi cuenta y pedidos ajenos), `npm run accesibilidad` y `npm run pixel-perfect` (tema o app nueva contra master).

**En el bug**: cuenta, workspace, canal de venta, app de VTEX IO (si aplica), dispositivo y número del pedido de prueba. **Antes de entregar**, además de lo común: no se tocó master de forma destructiva.

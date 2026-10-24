---
name: pruebas-wordpress
description: El cómo de probar WordPress y WooCommerce — staging y WP-CLI, plugins y temas, bloques, caché y WP-Cron, REST API y Store API, checkout clásico vs. de bloques, pasarelas de prueba, HPOS, envíos, cupones, stock, correos, multisitio y multi-idioma. Lo usan probador-wordpress y los mappers.
---

# Pruebas en WordPress y WooCommerce

En WordPress casi todo lo que se rompe viene de **la combinación de plugins, tema y versiones**: una actualización cambia algo en otra parte. Por eso cada actualización se prueba en **staging** con la regresión del flujo principal. Se suma al skill `pruebas-ecommerce`.

## 1. Ambientes

- **Staging** o copia local (Docker, Local, WP-CLI). Si es copia de producción, puede tener **clientes y pedidos reales**: no se mandan correos a clientes (usar Mailpit, ver `verificador-correos`) y se enmascaran los datos en las capturas.
- **WP-CLI** (`wp plugin list`, `wp core check-update`, `wp cron event list`) da el estado real del sitio; solo se usan comandos de lectura.
- El **enlace permanente** tiene que estar en un modo "bonito" para que `/wp-json/` funcione.

## 2. Plugins y tema

- **Actualizaciones**: un plugin desactualizado no es un bug, pero **actualizarlo es un riesgo**: se actualiza en staging y se corre la regresión de catálogo, carrito, checkout y Mi cuenta, mirando la consola.
- **Conflictos**: si algo falla, desactivar plugins de a uno (en staging) o probar con un tema por defecto para aislar.
- **Tema hijo**: los cambios van en el hijo; si se editó el padre, se pierden al actualizar.
- **Templates de WooCommerce sobrescritos** por el tema (`tema/woocommerce/...`): si su versión es vieja ("outdated templates" en el estado del sistema), el carrito, el checkout o los correos pueden verse mal o perder campos. Es de los hallazgos más importantes.
- **Caché** (plugin, servidor o CDN): el carrito, el checkout y Mi cuenta **no** se cachean; probá con dos navegadores que un carrito no aparezca en otro. Después de cambiar precios o el tema, purgar la caché y verificar que el cambio se vea.
- **Antes de actualizar**: respaldo (base y archivos) y un camino para volver atrás. Una actualización se prueba en staging y recién después se pasa a producción.
- **Actualizaciones automáticas** de plugins o de WordPress en producción: se actualizan sin pasar por staging. Si están activas en plugins críticos (WooCommerce, pasarelas, envíos), es un riesgo para conversar con el equipo.
- **Aislar un conflicto sin afectar a los visitantes**: el plugin *Health Check & Troubleshooting* tiene un modo de solución de problemas que desactiva plugins y cambia el tema solo para tu sesión. *Herramientas → Salud del sitio* resume problemas de configuración.
- **Constructores** (Elementor, Divi, WPBakery) y **temas de bloques** (editor del sitio completo): un cambio en una plantilla o una parte global (encabezado, pie) se ve en todas las páginas que la usan; probá varias páginas, no solo la editada.

## 3. WP-Cron

- WP-Cron corre cuando alguien visita el sitio. Sin visitas o si está desactivado (`DISABLE_WP_CRON`) sin un cron del servidor, no se cancelan pedidos impagos, no empiezan ni terminan las ofertas programadas y no salen algunos correos.
- Eventos atrasados más de una hora en `wp cron event list` = el cron no corre.
- **Action Scheduler** (WooCommerce → Estado → Acciones programadas, o `wp action-scheduler action list --status=failed`): la cola donde WooCommerce y sus extensiones dejan los correos diferidos, los webhooks, las renovaciones de suscripciones y los reportes. Acciones **fallidas** o **pendientes con fecha vencida** son tareas que no se hicieron.

## 4. WooCommerce: checkout

- **Checkout clásico (shortcode) o de bloques**: muchas pasarelas, campos extra y plugins de envío solo funcionan con uno. Verificá cuál usa la página y que cada plugin del checkout sea compatible.
- Las páginas de **Carrito, Finalizar compra y Mi cuenta** tienen que existir, estar publicadas y tener su shortcode o bloque (el estado del sistema lo dice).
- **Pasarelas**: cada una en **modo de prueba** (Stripe test, Mercado Pago sandbox, PayPal sandbox). Aprobado, rechazado, 3-D Secure, volver atrás desde la pasarela y reintentar. Después de pagar: estado del pedido (procesando), stock descontado, nota del pedido y correo.
- Una pasarela en **modo real** en QA es un hallazgo: no se paga con ella.
- **Ajustes del checkout** que cambian el flujo: permitir compra como invitado, crear cuenta durante el pago, generar la contraseña automáticamente, iniciar sesión durante el pago, página de términos obligatoria. Cada combinación es un camino.
- **Pagos fuera de línea** (transferencia, cheque, contra reembolso): el pedido queda **en espera**; si "retener stock" es corto y el cron corre, se cancela solo antes de que el cliente transfiera.

## 5. Almacenamiento de pedidos (HPOS)

- WooCommerce guarda los pedidos en **tablas propias** (HPOS, almacenamiento de pedidos de alto rendimiento) en lugar de entradas de WordPress. En *WooCommerce → Ajustes → Avanzado → Características* dice qué modo se usa, si está la **sincronización** con las tablas viejas y qué plugins **no son compatibles**.
- Un plugin incompatible con HPOS puede no ver los pedidos nuevos (facturación, envíos, ERP, reportes). Con HPOS activo, probá cada plugin que lee o escribe pedidos: crea su dato, el pedido se ve completo en el panel y en Mi cuenta, y la búsqueda de pedidos lo encuentra.
- Al **cambiar de modo** (activar HPOS o desactivar la sincronización) en staging: los pedidos viejos siguen visibles con sus notas, reembolsos y metadatos.

## 6. Tipos de producto

- **Simple, variable, agrupado y externo/afiliado**: el agrupado agrega varios a la vez (cantidades por hijo); el externo lleva a otra web y no pasa por el carrito.
- **Virtual** (sin envío) y **descargable**: el checkout no pide envío; el link de descarga aparece solo con el pedido pagado (procesando o completado), respeta el **límite de descargas** y el **vencimiento**, y no se puede abrir sin sesión si la regla lo pide.
- Extensiones con productos propios: **Subscriptions** (renovación, cambio de plan, cancelación, tarjeta vencida), **Bookings** (disponibilidad, reservas superpuestas, zona horaria), **Memberships** (contenido y precios por plan), **Product Add-Ons** (campos extra que suman al precio).

## 7. Envíos, impuestos y cupones

- **Zonas de envío**: se elige la primera zona que coincide con la dirección, en orden; una dirección que no coincide con ninguna cae en "Resto del mundo". Una zona sin métodos habilitados deja sin envío.
- **Envío gratis** con mínimo: justo en el mínimo, un centavo menos y con cupón que baja el subtotal debajo del mínimo.
- **Impuestos**: precios con o sin impuestos (`woocommerce_prices_include_tax`), por país y provincia, sobre el envío, y redondeo por línea o por total. **Clases de impuesto** (estándar, tasa reducida, tasa cero) por producto; cómo se muestran los precios en la tienda y en el carrito (pueden ser distintos: con impuestos en la tienda y sin impuestos en el carrito confunde al comprador); "calcular impuestos según" la dirección de envío, de facturación o la de la tienda.
- **Cupones**: porcentaje, fijo al carrito, fijo al producto; vencidos, agotados, uso individual, productos o categorías excluidos, mínimo y máximo, restricción por correo.

## 8. Stock y pedidos

- **Gestionar stock** por producto o variación; **pedidos pendientes** (backorders: no, avisar, sí). Stock bajo y sin stock disparan correos al administrador.
- **Estados del pedido**: pendiente de pago, procesando, en espera, completado, cancelado, reembolsado, fallido. Un pedido impago se cancela solo después del tiempo de "retener stock" (si el cron corre).
- **Reembolso** total y parcial: devuelve stock si se marca, y la pasarela devuelve el dinero solo si lo soporta.

## 9. Correos de WooCommerce

Nuevo pedido (a la tienda), pedido cancelado y fallido (a la tienda), pedido en espera, procesando, completado, reembolsado, nota al cliente, restablecer contraseña y cuenta nueva. Se prueban con el `verificador-correos` y Mailpit.

- Sin un plugin de **SMTP** (WP Mail SMTP, FluentSMTP…) o un servicio de envío, WordPress manda con la función de correo del servidor: muchos correos no salen o van a spam. Verificá que salgan por el servicio configurado.
- En sitios **multi-idioma**, el correo sale en el idioma del cliente (el del pedido), no en el del administrador.

## 10. Multisitio y multi-idioma

- **Multisitio**: cada sitio de la red tiene sus plugins activos, usuarios y roles; un plugin activado "para toda la red" afecta a todos. Probá en el sitio de la red que corresponde.
- **WPML o Polylang** (con WooCommerce Multilingual o similar): productos, categorías y slugs traducidos, el selector de idioma conserva el carrito, el checkout y los correos en el idioma elegido, y los precios por moneda si hay multi-moneda. Las traducciones las revisa el `analista-traductor`.

## 11. Webhooks

WooCommerce **desactiva un webhook** después de varios fallos de entrega seguidos (queda `disabled`): el ERP o la integración deja de recibir pedidos sin que nadie se entere. Cada webhook firma el cuerpo con **X-WC-Webhook-Signature**.

## 12. Roles

- **Cliente**: Mi cuenta, sus pedidos y direcciones; nunca pedidos ajenos (cambiar el ID en la URL de "ver pedido").
- **Gestor de la tienda** (`shop_manager`): pedidos, productos y cupones, pero no plugins ni usuarios administradores.
- Lo prueba el `probador-permisos`.

## 13. Sitios WordPress que no son tienda

- **Formularios** (Contact Form 7, Gravity Forms, WPForms, Elementor): validaciones (`probador-formularios`), mensaje de confirmación, que el correo llegue a quien corresponde (`verificador-correos`) y que el antispam no bloquee envíos legítimos.
- **Comentarios**: moderación, el primer comentario queda pendiente si esa es la regla, los links se marcan como spam.
- **Menús, búsqueda y 404**: todos los links del menú abren (`explorador-web`), la búsqueda encuentra entradas y páginas, la 404 ofrece cómo seguir.
- **Redirecciones** (plugin Redirection o el del SEO): las URLs viejas redirigen con 301 después de cambiar un slug o migrar.
- **SEO** (Yoast, Rank Math): título y descripción de cada tipo de página, canónica, el sitemap del plugin y que "Disuadir a los motores de búsqueda" (Ajustes → Lectura) esté activo en staging e **inactivo** en producción.
- **Medios**: tamaños de imagen generados, carga diferida, formatos (WebP/AVIF) y textos alternativos (`analista-accesibilidad`).
- **Usuarios y privacidad**: registro (si está abierto, con qué rol por defecto), exportar y borrar datos personales (Herramientas → Exportar/Borrar datos personales).

## 14. APIs para el relevamiento (solo lectura)

- **`/wp-json/`**: nombre del sitio y namespaces (qué plugins exponen API: `wc/v3`, `yoast/v1`, `contact-form-7/v1`…).
- **Store API** (`/wp-json/wc/store/v1/products`): catálogo público; los precios vienen en **unidades menores** (`1599` con `currency_minor_unit: 2` = 15,99).
- **REST API de WooCommerce** (`/wp-json/wc/v3/...`) con una clave de **solo lectura** (WooCommerce → Ajustes → Avanzado → REST API, permiso *Lectura*): `system_status`, `payment_gateways`, `shipping/zones`, `coupons`, `webhooks`, `settings/general`, `products`.

## 15. Automatizar con Playwright (web-mapper)

- Los checkouts de bloques son React: esperar a que termine de recalcular (el spinner del resumen) antes de leer el total.
- Los campos de tarjeta de Stripe y otras pasarelas van en **iframes**.
- `?add-to-cart=<id>` agrega directo al carrito: sirve para preparar el escenario rápido.
- Los nonces vencen: no grabes URLs con `_wpnonce`.

## 16. Bugs típicos

- El checkout deja de funcionar después de actualizar WooCommerce porque el tema tiene templates viejos.
- Un plugin de caché que muestra el carrito de otro visitante.
- Pedido pagado que queda en "pendiente" porque la notificación de la pasarela no llega (llamadas salientes bloqueadas, URL de notificación mal configurada).
- Webhook desactivado y el ERP sin pedidos.
- Ofertas programadas que no empiezan porque el cron no corre.
- Envío gratis que se sigue ofreciendo después de aplicar un cupón que baja el subtotal debajo del mínimo.
- Un plugin de facturación o envíos que no ve los pedidos nuevos porque no es compatible con HPOS.
- Acciones programadas fallidas: renovaciones de suscripciones o correos diferidos que nunca salieron.
- Un plugin crítico que se actualizó solo en producción y rompió el checkout.
- Pedidos por transferencia cancelados solos antes de que el cliente pague ("retener stock" muy corto).
- Links de descarga que no vencen o que se abren sin haber pagado.
- Correos que no llegan porque el sitio no tiene SMTP configurado.
- Producción con "Disuadir a los motores de búsqueda" activado después de copiar el staging.

## 17. Preguntas típicas para el PO (WordPress / WooCommerce)

Además de las del skill `pruebas-ecommerce`, cuando no está escrito son `FI-XX`:

- ¿Se permite comprar como invitado? ¿Se crea la cuenta durante el pago?
- ¿Cuántos minutos se retiene el stock de un pedido impago? ¿Aplica a transferencias?
- ¿Se permiten pedidos pendientes (backorders) y en qué productos?
- ¿Los precios se cargan con o sin impuestos? ¿Cómo se muestran en la tienda y en el carrito?
- ¿Qué plugins están en el alcance de la prueba y quién los actualiza?
- ¿Las actualizaciones automáticas están activas en producción?
- ¿Cuánto tiempo y cuántas veces se puede descargar un producto descargable?

## 18. Smoke, regresión, rendimiento y seguridad (WordPress / WooCommerce)

Lo genérico (los cinco tipos de prueba) está en `pruebas-ecommerce`; acá lo propio de WordPress.

- **Smoke** (staging): portada, una categoría y una ficha sin el "error crítico" de WordPress ni avisos de PHP; `/wp-json` responde; agregar al carrito y llegar al checkout; "Mi cuenta" carga; la pasarela en modo de prueba. En WooCommerce, el **estado del sistema** (WooCommerce → Estado) es el smoke de fondo: sin base pendiente de actualizar, sin templates desactualizados, con `remote_post` OK.
- **Regresión**: WooCommerce es sensible a la **combinación de plugins, tema y versiones**. Después de **actualizar** WordPress, WooCommerce, el tema o un plugin (en staging, con respaldo), correr la regresión de catálogo → carrito → checkout (clásico o de bloques) → pago → Mi cuenta mirando la consola; sumar `pixel-perfect` y `cross-browser` si cambió el tema. El modo *Health Check & Troubleshooting* aísla un conflicto sin afectar a los visitantes.
- **Rendimiento**: caché de objetos (Redis/Memcached) y de página (plugin/servidor/CDN), **opciones autocargadas** (`autoload`) infladas, **WP-Cron** sobrecargado, cantidad de plugins y su peso (Query Monitor para el conteo de consultas y las queries lentas), HPOS vs. entradas para pedidos. El carrito, el checkout y Mi cuenta no se cachean: verificarlo. Medir con `auditor-rendimiento-web` y, para carga, `performance-mapper`.
- **Seguridad**: **plugins/tema/core desactualizados** son la principal fuente de CVEs (el relevamiento marca los que tienen actualización); **enumeración de usuarios** por `/wp-json/wp/v2/users` y `?author=1`; **XML-RPC** (`xmlrpc.php`) para fuerza bruta y amplificación; `wp-login.php` sin límite de intentos; `wp-config.php`, `debug.log` y backups accesibles por URL; permisos de archivos; nonces/CSRF en formularios; la **REST API de WooCommerce** no debe exponer pedidos sin clave; un cliente no ve pedidos ajenos (`?view-order=` / IDOR). La seguridad activa, con `analista-seguridad` / `pentester-web`.

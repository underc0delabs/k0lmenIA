---
name: pruebas-prestashop
description: El cómo de probar PrestaShop (1.6, 1.7, 8.x) — smoke con Docker, back y front office, temas Smarty y overrides, caché y modo desarrollador, checkout, combinaciones y stock, reglas de carrito, multitienda y la Webservice API de lectura. Lo usan probador-prestashop y los mappers.
---

# Pruebas en PrestaShop

PrestaShop es **self-hosted (PHP + MySQL)**: vos controlás el servidor, la base, el tema y los módulos. A diferencia de Shopify, casi todo lo que se rompe viene de **la combinación de módulos, tema y configuración**, y de cómo está puesto el **rendimiento** (caché y compilación). Se suma al skill `pruebas-ecommerce`.

Versiones vivas: **1.6** (legacy, checkout de 5 pasos clásico), **1.7** y **8.x** (Symfony en el BO, checkout de una página, temas basados en `classic`). Confirmá la versión antes de probar: cambia el BO, el checkout y los hooks.

## 1. Ambientes y smoke test

- Se prueba en **staging** o en una **copia local** (Docker es lo más rápido): nunca pedidos de prueba contra producción.
- **Levantar PrestaShop local con Docker** (smoke test de instalación):
  ```bash
  docker run -ti --name ps -e DB_SERVER=auto -p 8080:80 prestashop/prestashop:8
  # o con docker-compose: un servicio mysql/mariadb + uno prestashop apuntando a DB_SERVER
  ```
  Smoke test después de levantar: el **FO** abre en `/`, el **BO** en `/admin-XXXX` (la carpeta admin se renombra sola), se puede iniciar sesión con el usuario del instalador, no hay errores de PHP a la vista y el `var/logs/` (8.x) o `log/` no tiene fatales.
- **Modo mantenimiento** (`PS_SHOP_ENABLE = 0`, BO → Parámetros de la tienda → General → Mantenimiento): el FO queda cerrado salvo para las IP de `PS_MAINTENANCE_IP`. En staging suele estar así a propósito; confirmalo antes de reportarlo.
- **Datos de demo**: la instalación trae catálogo de demo (productos "Hummingbird", categorías). Si la tienda real los tiene, es un bug de limpieza.

## 2. Back-office (BO) y front-office (FO)

- Lo que configura el negocio vive en el **BO**; lo que ve el cliente, en el **FO**. Casi toda prueba cruza los dos: cambiás algo en el BO y verificás en el FO (con la caché purgada).
- **8.x / 1.7** tienen el BO en **Symfony** (rutas nuevas) conviviendo con páginas legacy; un error de Symfony se ve distinto a uno legacy. Revisá `var/logs/*.log`.
- El **multistore** se activa en el BO (Parámetros avanzados → Multitienda) y agrega un selector de tienda arriba: cada cambio puede ser "para todas las tiendas" o "para esta tienda". Es fuente típica de "lo configuré y no se ve".

## 3. Temas y plantillas (Smarty)

- El tema por defecto de 1.7/8 es **`classic`**; los temas se basan en él. Las plantillas son **Smarty** (`.tpl`) en `themes/<tema>/templates/`.
- **Tema hijo**: los cambios van en el hijo (hereda de `classic` o del padre); si se editó el padre, se pierden al actualizarlo.
- **Plantillas sobrescritas**: un tema o un módulo puede sobrescribir `.tpl` del core o de otro módulo (`themes/<tema>/modules/<módulo>/`). Si quedaron de una versión vieja, el carrito, el checkout o la ficha pueden verse o comportarse mal. Es de los hallazgos más importantes (equivalente a los "templates desactualizados" de WooCommerce).
- **Errores de Smarty/PHP a la vista** (`Fatal error`, `Notice`, `Warning`, o una **excepción de PrestaShop** con stack trace) aparecen en la página: casi siempre significan que **el modo desarrollador quedó encendido** (ver §5) y son bugs en producción.
- Después de editar un `.tpl`, hay que **recompilar/purgar** (ver §5) para que el cambio se vea.

## 4. Módulos y overrides

- Los **módulos** agregan funciones y se enganchan con **hooks** (`displayHeader`, `displayProductAdditionalInfo`, `actionValidateOrder`, …). Un módulo mal hecho que se cuelga de un hook rompe esa zona en todas las páginas.
- **Conflictos**: si algo falla, desactivá módulos de a uno en el BO para aislar. Los de pago, envío, traducción y constructores de página son los que más rompen.
- **Overrides** (`override/classes/...`, `override/controllers/...`): PHP que pisa clases del core. Dos módulos que pisan la misma clase **chocan**. Si la tienda tiene `PS_DISABLE_OVERRIDES = 1`, los overrides no se aplican (puede ser intencional por seguridad, o un bug si algo dejó de andar). Después de instalar o actualizar módulos conviene borrar `cache/class_index.php`.
- **Restos de módulos desinstalados**: `.tpl` sobrescritos, overrides o hooks que quedaron apuntando a archivos que ya no existen (fatales o 404 en la consola).
- Después de instalar/actualizar un módulo: regresión de ficha, carrito, checkout y "Mi cuenta", mirando la consola y `var/logs/`.

## 5. Caché, compilación y rendimiento

Esto es específico de PrestaShop y pesa mucho (BO → Parámetros avanzados → **Rendimiento**):

- **Smarty · Compilar plantillas**: en producción tiene que ser *"Recompilar solo si cambió el archivo"* (`PS_SMARTY_FORCE_COMPILE = 0`). *"Forzar la recompilación en cada carga"* (1 o 2) hace lento **todo** el sitio.
- **Smarty · Caché** (`PS_SMARTY_CACHE`): activada en producción.
- **Combinar, comprimir y cachear (CCC)** CSS (`PS_CCCCSS`) y JS (`PS_CCCJS`): reduce la cantidad de pedidos y bytes. Activarlos y **verificar que el tema no se rompa** (es el riesgo típico de activar CCC).
- **Caché de PrestaShop** (`PS_CACHE_ENABLED`, con FS/Memcached/Redis según el servidor).
- **Modo desarrollador** (`_PS_MODE_DEV_` en `config/defines.inc.php`): enciende errores, perfilado y desactiva parte de la caché → **lento y filtra información**. En producción tiene que estar **apagado**. El `prestashop.py` con `--local` lo detecta.
- **Perfilado** (`_PS_DEBUG_PROFILING_`): muestra tiempos y **conteo de consultas SQL** por página — útil para encontrar páginas con cientos de queries (N+1 de un módulo). Solo en staging.
- Medí la velocidad real con el **`auditor-rendimiento-web`** (Lighthouse) en portada, una **categoría con muchos productos** (paginación/filtros) y una **ficha**, con y sin CCC y caché. Para carga, el **`performance-mapper`** (plan guiado con `guia-performance`).

## 6. URLs amigables y .htaccess

- Las **URLs amigables** (BO → Tráfico y SEO → URL) necesitan `mod_rewrite` y un `.htaccess` generado. Si están activas pero el `.htaccess` no se regeneró, las fichas y categorías dan 404.
- Después de cambiar el `link_rewrite` de un producto o categoría, la URL vieja tiene que **redirigir 301**, no dar 404 (BO → SEO, o un módulo de redirecciones).

## 7. Checkout

- **1.7 / 8.x**: checkout de **una página** (`PS_ORDER_PROCESS_TYPE = 1`) con secciones (identificación, dirección, transportista, pago). **1.6**: **5 pasos**. Confirmá cuál es.
- **Compra de invitado** (`PS_GUEST_CHECKOUT_ENABLED`): si está activa, se compra sin crear cuenta; si no, obliga a registrarse o iniciar sesión. Probá el camino que corresponda.
- **Transportistas y zonas**: cada transportista tiene zonas, rangos por peso o por precio y costo (o gratis). **Sin ningún transportista activo no se puede comprar.** Productos de un carrito que caen en transportistas distintos, y cambio de dirección a otra zona que recalcula el envío.
- **Términos y condiciones** (`PS_CONDITIONS = 1`): la casilla es obligatoria y su link abre la página CMS de condiciones.
- El **total** tiene que cerrar igual en carrito, checkout, pedido (BO) y correo: subtotal + envío + impuestos − descuentos.

## 8. Pagos

- Cada pasarela, en **modo de prueba/sandbox** (Stripe test, Redsys pruebas, PayPal sandbox, Mercado Pago sandbox). Aprobado, rechazado, 3-D Secure, volver atrás desde la pasarela y reintentar.
- Una pasarela en **modo real** en QA es un hallazgo: no se paga con ella.
- Módulos de pago nativos para probar sin pasarela real: **"Pago por transferencia"** y **"Pago contra reembolso"** dejan el pedido en un estado de pago pendiente — sirven para probar el flujo del pedido sin cobrar.
- Después de pagar: **estado del pedido**, stock descontado, factura/comprobante, nota del pedido y **correo** (ver §13).

## 9. Productos, combinaciones y stock

- **Combinaciones** (tallas/colores): cada combinación cambia precio, referencia, imagen y **stock**; una combinación sin stock o inexistente no se puede agregar.
- **Stock** (`stock_availables`): cantidad por producto/combinación. **"Cuando no hay stock"** por producto: *denegar pedidos* (no se puede comprar), *permitir pedidos* (se vende sin stock → sobreventa) o *usar el valor por defecto de la tienda* (`PS_ORDER_OUT_OF_STOCK`). Probá los tres.
- **Precios específicos** (descuentos por cantidad, por grupo de cliente, por rango de fechas, por tienda): el precio que se muestra y el del carrito tienen que respetarlos; cuidado con el tachado.
- **Productos**: a la venta con precio 0, sin imagen, sin referencia (SKU), sin grupo de impuestos, no disponibles para pedido pero visibles. El `prestashop.py` los marca.

## 10. Impuestos, redondeo y moneda

- **Grupos de reglas de impuestos** por país/estado; `PS_TAX` activa o no el cálculo. Precios con y sin impuesto (`price` es sin impuesto).
- **Redondeo** (`PS_ROUND_TYPE`: por línea, por línea con cantidad, o total; `PS_PRICE_ROUND_MODE`: arriba, abajo, medio): es la causa más común de totales que no cierran por un centavo. Probá con cantidades que generen decimales.
- **Multi-moneda**: cambiar de moneda convierte con la tasa; verificá el redondeo y que el cobro sea en la moneda mostrada.

## 11. Multitienda (multishop)

- Con multitienda activa (`PS_MULTISHOP_FEATURE_ACTIVE = 1`), cada tienda (o grupo) puede tener su **catálogo, precios, transportistas, módulos y tema**. Hay que probar **cada tienda** (cambiar de tienda en el selector del BO y recorrer su FO por su dominio o subcarpeta).

## 12. Multi-idioma

- Cada idioma activo tiene sus traducciones (BO → Internacional → Traducciones) y sus campos multilenguaje (nombre, descripción, meta). Revisá cada página en cada idioma con el **`analista-traductor`**: textos sin traducir, claves a la vista, fichas, checkout y correos.

## 13. Correos transaccionales

- PrestaShop manda correos por **plantilla** (`mails/<idioma>/`) con variables `{variable}`. Probá con el **`verificador-correos`** (Mailpit): confirmación del pedido, pago aceptado, en preparación, enviado, devolución y cambio de contraseña.
- Variables sin reemplazar (`{firstname}` a la vista), links rotos y la vista en desktop y mobile.
- Configurá el envío por **SMTP** apuntando a Mailpit en staging para no mandarle correos a clientes reales.

## 14. Webservice API (relevamiento de solo lectura)

- La **Webservice** (BO → Parámetros avanzados → Webservice) expone recursos REST (XML, o JSON con `?output_format=JSON`). Auth: **HTTP Basic con la clave como usuario y contraseña vacía**.
- Para QA se usa una clave con permiso de **solo lectura** sobre: `configurations`, `products`, `stock_availables`, `carriers`, `zones`, `currencies`, `languages`, `cart_rules` y `shops`.
- `?display=full` trae todos los campos; `?limit=N`; `filter[campo]=valor` (y `[a|b|c]` para OR). Nunca se usan métodos de escritura (POST/PUT/DELETE).
- La **versión** de PrestaShop no se expone por la Webservice (seguridad): sale de la instalación local (`--local`: `app/AppKernel.php` en 1.7/8, `config/settings.inc.php` en 1.6).

## 15. Automatizar con Playwright (web-mapper)

- Ubicá por rol y nombre accesible; el tema `classic` tiene clases estables (`.product-add-to-cart`, `#checkout`), pero los IDs que genera Smarty cambian.
- El **BO** vive en `/admin-XXXX` (carpeta renombrada): guardala en el `.env`, no la adivines.
- Esperá a que respondan las llamadas AJAX del carrito (`?controller=cart&action=...` / `/cart`) antes de leer el total o el contador.
- Sacá el **aviso de cookies** (RGPD) y los popups de newsletter al principio del escenario.
- **Combinaciones**: al elegir una variante se recarga el precio y el stock por AJAX; esperá ese fetch.
- **Captcha** (reCAPTCHA en contacto o registro): no se evade; pedí desactivarlo en staging o dejá esos pasos como manuales.
- **Datos que cambian solos** (stock, precios específicos por fecha): verificá relativo al dato que leíste al empezar.

## 16. Bugs típicos de PrestaShop

- Errores de PHP o una excepción de PrestaShop a la vista (modo desarrollador encendido en producción).
- `.tpl` de un módulo o del tema sobrescritos y desactualizados: checkout o ficha rotos.
- Dos módulos que pisan la misma clase por override y chocan.
- URLs amigables activas sin `.htaccess` regenerado → 404 en fichas y categorías.
- Sin ningún transportista activo o sin método para una zona → no se puede comprar.
- Smarty forzando recompilación o CCC apagado en producción → tienda lenta.
- Activar CCC rompe el tema (CSS/JS que dependían de estar separados).
- Totales que no cierran por el redondeo (`PS_ROUND_TYPE` / `PS_PRICE_ROUND_MODE`).
- Combinación sin stock que igual se puede comprar (o al revés).
- Correo con variables `{...}` sin reemplazar.
- Catálogo de demo o módulos de demo en una tienda real.
- Un cambio hecho "para esta tienda" en multitienda que no se ve en la otra (o al revés).

## 17. Preguntas típicas para el PO (PrestaShop)

Además de las del skill `pruebas-ecommerce`, cuando no está escrito son `FI-XX`:

- ¿Qué versión de PrestaShop (1.6, 1.7, 8.x) y qué tema (hijo de `classic` o propio)?
- ¿La compra de invitado está activa o se exige cuenta?
- ¿Qué transportistas y zonas están en el alcance? ¿Hay envío gratis y bajo qué condición?
- ¿Cómo se comporta un producto sin stock (denegar, permitir, según la tienda)?
- ¿Qué redondeo usa la tienda y en qué nivel (línea o total)?
- ¿La tienda es multitienda? ¿Cuáles entran en la prueba?
- ¿Qué módulos están en el alcance y cuáles son de terceros que no se prueban?
- ¿La prueba incluye rendimiento (CCC, caché, Smarty) o solo funcional?

## 18. Smoke, regresión, rendimiento y seguridad (PrestaShop)

Lo genérico (los cinco tipos de prueba) está en `pruebas-ecommerce`; el **smoke local** está en §1 y el **rendimiento** (Smarty, CCC, caché, modo dev, perfilado) en §5. Acá el resto propio de PrestaShop.

- **Regresión**: PrestaShop rompe por la **combinación de módulos, tema y overrides**. Después de **instalar o actualizar un módulo o el tema**, o de una actualización de versión (en staging, con respaldo de base y archivos), correr el flujo de compra completo —catálogo → ficha con combinaciones → carrito → checkout (una página o 5 pasos) → pago → estado del pedido → correo— mirando la consola y `var/logs/`; borrar `cache/class_index.php` y purgar la caché; sumar `pixel-perfect` y `cross-browser` si cambió el tema. En multitienda, repetir por cada tienda.
- **Seguridad**: la **clave de la Webservice** con mínimo privilegio y no expuesta; la **carpeta del back-office** (`/admin-XXXX`) renombrada y no indexada; **IDOR** en el PDF de factura o el detalle de pedido (`?id_order=`, `controller=pdf-invoice`) que no deje ver pedidos ajenos; el **modo desarrollador apagado** en producción (si no, filtra errores y stack traces — el relevamiento lo detecta); `app/config`, `.env`, `var/logs/` y backups no accesibles por URL; SQL de módulos de terceros; tokens del front activos (`PS_TOKEN_ENABLE`); HTTPS en todo el sitio. La seguridad activa, con `analista-seguridad` / `pentester-web`.

## 19. Referencia del `probador-prestashop`

**Relevamiento** (solo lectura): `k0lmenia prestashop -- --tienda https://staging.mitienda.com [--historia HU-001] [--producto <url>] [--local C:/www/mitienda] --confirmar` deja `output/prestashop/<HU o host>/prestashop.json` e `informe-prestashop.html` (la corrida anterior pasa a `historial/`). Con `PRESTASHOP_WEBSERVICE_KEY` (clave de solo lectura) suma la Webservice; con `--local` / `PRESTASHOP_RUTA_LOCAL`, la versión y si el modo desarrollador quedó encendido.

**Prioridades**: primero lo que impide comprar (sin transportista activo, modo catálogo, modo mantenimiento, sin HTTPS), después lo que cambia el total (redondeo, impuestos, envío, moneda, vales), stock y combinaciones, el checkout (invitado y cuenta), el rendimiento (Smarty, CCC, caché, modo dev) y, si aplica, multitienda y multi-idioma.

**Smoke test local** (si el alcance es levantar/instalar): que el FO (`/`) y el BO (`/admin-XXXX`) abran, se pueda iniciar sesión, no haya errores de PHP a la vista ni fatales en `var/logs/` (8.x) o `log/`, y que el catálogo de demo no esté en una tienda real.

**Seguridad a derivar** con lo del relevamiento: modo dev encendido, clave de Webservice expuesta, IDOR en facturas/pedidos, carpeta del BO, sin HTTPS.

**Complementos** según el alcance: `k0lmenia formularios` (dirección y checkout), `k0lmenia correos` (transaccionales), `k0lmenia accesibilidad` y `k0lmenia pixel-perfect` (tema o módulo nuevo).

**En el bug**: versión, tema, módulo, tienda (si es multistore), dispositivo y número del pedido de prueba.

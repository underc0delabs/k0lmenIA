# E-commerce (Shopify, WordPress / WooCommerce, PrestaShop y VTEX)

Relevamientos funcionales de **solo lectura** de tiendas online. Los usan los agentes `probador-shopify`, `probador-wordpress`, `probador-prestashop` y `probador-vtex`.

- **`shopify.py`** (`npm run shopify`) — vidriera pública (páginas clave, tema publicado, errores de Liquid y traducciones faltantes, políticas legales, `/products.json`, `/cart.js`, datos estructurados de una ficha) y, con un token de lectura de la **Admin API GraphQL**, la tienda (plan, si es de desarrollo, monedas, impuestos), temas, productos con variantes y stock, ubicaciones, mercados, perfiles de envío, códigos de descuento, webhooks y los alcances del token. Con `--theme-check` corre `shopify theme check` sobre el código del tema.
- **`wordpress.py`** (`npm run wordpress`) — vidriera pública (páginas clave, errores de PHP o el error crítico de WordPress, módulos de `/wp-json`, catálogo de la Store API) y, con una clave de lectura de la **REST API de WooCommerce**, el estado del sistema (base pendiente de actualizar, cron, llamadas salientes, plugins desactualizados, templates del tema viejos, páginas de WooCommerce), pasarelas y su modo, zonas y métodos de envío, cupones, webhooks y productos. Con `--wp-cli`, por WP-CLI: actualizaciones disponibles y automáticas, cron atrasado y acciones fallidas de Action Scheduler.
- **`prestashop.py`** (`npm run prestashop`) — vidriera pública (páginas clave, errores de PHP o excepciones de PrestaShop a la vista, datos estructurados de una ficha) y, con una clave de la **Webservice API** de solo lectura, los productos con stock y combinaciones, transportistas (y si hay alguno activo), zonas, monedas, idiomas, reglas de carrito (vales), tiendas (multistore) y las configuraciones clave de QA y rendimiento (modo mantenimiento, modo catálogo, HTTPS, Smarty y compilación, combinar-comprimir-cachear CSS/JS, checkout de invitado, redondeo, impuestos, términos). Con `--local` lee la versión y si `_PS_MODE_DEV_` quedó encendido.
- **`vtex.py`** (`npm run vtex`) — vidriera pública (páginas clave, errores de la tienda o de VTEX IO a la vista, datos estructurados de una ficha) y el **Catalog System público** (catálogo del canal con SKUs, precio y disponibilidad); con una app de solo lectura (`X-VTEX-API-AppKey`/`AppToken`), los canales de venta (trade policies), las políticas de envío (SLAs) y las promociones. Detecta el storefront (Store Framework, FastStore o legacy) y avisa si se releva el workspace `master`.
- **`_comun.py`** — autorización, HTTP de solo lectura, chequeos comunes de la vidriera (páginas clave, robots, sitemap, 404, errores a la vista, JSON-LD de producto), análisis del catálogo (precio 0, sin imagen, sobreventa, precio tachado, sin SKU, sin impuesto) y guardado con historial.

Cada corrida deja en `output/<shopify|wordpress|prestashop|vtex>/<historia o host>/` el `<plataforma>.json` y el `informe-<plataforma>.html` (`scripts/generar_informe_ecommerce.py`); la anterior pasa a `historial/` (últimas 5).

## Uso

```bash
# Shopify: solo vidriera, o con la Admin API si hay SHOPIFY_TIENDA y SHOPIFY_ADMIN_TOKEN en el .env
npm run shopify -- --tienda https://mi-tienda.myshopify.com --historia HU-010 --confirmar
npm run shopify -- --tienda https://mi-tienda.myshopify.com --theme-check --confirmar

# WordPress / WooCommerce: con la REST API si hay WOOCOMMERCE_CONSUMER_KEY/SECRET en el .env
npm run wordpress -- --sitio https://staging.mitienda.com --confirmar
npm run wordpress -- --sitio https://staging.mitienda.com --wp-cli --confirmar

# PrestaShop: con la Webservice API si hay PRESTASHOP_WEBSERVICE_KEY en el .env
npm run prestashop -- --tienda https://staging.mitienda.com --confirmar
npm run prestashop -- --tienda https://staging.mitienda.com --local C:/www/mitienda --confirmar

# VTEX: catálogo público siempre; con las APIs de administración si hay VTEX_APP_KEY/VTEX_APP_TOKEN
npm run vtex -- --tienda https://www.mi-tienda.com --cuenta micuenta --confirmar
npm run vtex -- --tienda https://www.mi-tienda.com --cuenta micuenta --sc 1 --confirmar
```

## Autorización y alcance

- **Solo URLs de `ECOMMERCE_URLS_AUTORIZADAS`** del `.env` (el host tiene que coincidir; si la entrada tiene ruta, la URL tiene que empezar con ella).
- **Solo lectura**: GET a la vidriera y a las APIs, consultas GraphQL sin mutations (se rechazan antes de enviarse) y comandos de lectura de WP-CLI. No crea pedidos, clientes ni productos y no cambia ajustes.
- Las credenciales son de **lectura** (alcances `read_*` en Shopify, permiso *Lectura* en WooCommerce) y viven en el `.env`.
- **No es una herramienta de seguridad**: la seguridad de la tienda la revisan el `analista-seguridad` y el `pentester-web`.
- Opcionales: la CLI de Shopify (`npm install --global @shopify/cli`) para Theme Check y [WP-CLI](https://wp-cli.org) para `--wp-cli` (el `npm run doctor` avisa si faltan).

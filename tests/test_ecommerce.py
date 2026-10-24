"""Probadores de e-commerce (Shopify y WordPress / WooCommerce): autorización, catálogo, hallazgos, sugerencias e informe."""
import datetime
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "herramientas" / "ecommerce"))

import _comun as c  # noqa: E402
import generar_informe_ecommerce as gi  # noqa: E402
import prestashop  # noqa: E402
import shopify  # noqa: E402
import vtex  # noqa: E402
import wordpress  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402


def test_autorizacion_por_host_y_ruta():
    lista = c.lista_autorizadas({"ECOMMERCE_URLS_AUTORIZADAS": "https://tienda-qa.example.com, staging.example.com/shop"})
    assert c.esta_autorizada("https://tienda-qa.example.com/products/x", lista)
    assert c.esta_autorizada("https://staging.example.com/shop/cart", lista)
    assert not c.esta_autorizada("https://staging.example.com/otra", lista)
    assert not c.esta_autorizada("https://tienda-qa.example.com.evil.com", lista)
    assert not c.esta_autorizada("https://staging.example.com/shopping", lista)  # la ruta tiene que coincidir entera


def test_sin_autorizadas_corta():
    with pytest.raises(SystemExit):
        c.autorizar("https://x.example.com", {})


def test_robots_bloquea_todo():
    assert c.robots_bloquea_todo("User-agent: *\nDisallow: /\n")
    assert not c.robots_bloquea_todo("User-agent: *\nDisallow: /checkout\n\nUser-agent: BadBot\nDisallow: /\n")


def test_errores_en_html_ignora_scripts():
    html = "<script>var x='Liquid error';</script><p>Liquid error: Could not find asset</p>"
    assert c.errores_en_html(html, shopify.PATRONES_ERROR)[0][0] == "Error de Liquid"
    assert not c.errores_en_html("<script>Liquid error</script><p>ok</p>", shopify.PATRONES_ERROR)


def test_jsonld_producto_con_offers():
    html = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","offers":{"@type":"Offer","price":"10"}}</script>'
    assert {"Product", "Offer"} <= c.tipos_jsonld(html)


def test_catalogo_agrega_problemas():
    prods = [{"titulo": "Gratis", "activo": True, "precios": [0.0], "imagen": True},
             {"titulo": "Sin foto", "activo": True, "precios": [10.0], "imagen": False},
             {"titulo": "Preventa", "activo": True, "precios": [5.0], "controla_stock": True, "stock": 0, "sigue_vendiendo": True},
             {"titulo": "Tachado mal", "activo": True, "precios": [10.0], "comparar": [8.0]},
             {"titulo": "Borrador", "activo": False, "precios": [0.0]}]
    h, filas, n = c.analizar_catalogo(prods)
    assert n == 4  # el borrador no cuenta
    textos = " ".join(x["texto"] for x in h)
    assert "precio 0" in textos and "sin imagen" in textos and "sobreventa" in textos and "tachado" in textos
    assert h[0]["severidad"] == "Alta"


def test_shopify_normaliza_y_detecta():
    p = shopify.normalizar_admin({"title": "Remera", "handle": "remera", "status": "ACTIVE", "totalInventory": 0, "tracksInventory": True,
                                  "onlineStoreUrl": None, "featuredMedia": None, "seo": {"description": ""},
                                  "variants": {"nodes": [{"sku": "", "price": "0.00", "compareAtPrice": None, "inventoryPolicy": "CONTINUE"}]}})
    assert set(c.problemas_producto(p)) >= {"precio_cero", "sobreventa", "sin_imagen", "sin_sku", "no_publicado", "sin_seo"}


def test_shopify_hallazgos_y_sugerencias():
    inv = {"tienda": {"plan": {"partnerDevelopment": False, "publicDisplayName": "Basic"}, "enabledPresentmentCurrencies": ["ARS", "USD"]},
           "politicas": {"refund-policy": 404, "privacy-policy": 200, "terms-of-service": 200, "shipping-policy": 200},
           "webhooks": [{"topic": "ORDERS_CREATE", "uri": "http://receptor.example.com/hook"}],
           "descuentos": [{"codeDiscount": {"title": "BIENVENIDA", "status": "ACTIVE"}}],
           "envios": [{"name": "General", "default": True, "activeMethodDefinitionsCount": 0}],
           "alcances": ["read_products", "write_orders"], "productos_norm": []}
    h, s = shopify.hallazgos_y_sugerencias(inv)
    textos = " ".join(x["texto"] for x in h)
    assert "No es una tienda de desarrollo" in textos and "reembolso" in textos and "sin HTTPS" in textos
    assert "no tiene métodos activos" in textos and "write_orders" in textos
    assert any(x["elemento"] == "BIENVENIDA" for x in s) and any(x["area"] == "Mercados" for x in s)
    assert any("Bogus Gateway" in x["prueba"] for x in s)


def test_shopify_rechaza_mutations():
    with pytest.raises(ValueError):
        shopify.graphql("x.myshopify.com", "t", "2026-07", "mutation { productDelete(input:{id:\"1\"}) { deletedProductId } }")


def test_shopify_tema_publico():
    html = '<script>Shopify.theme = {"name":"Dawn","id":1,"schema_version":"15.0.0","role":"main"};</script>'
    assert shopify.tema_publico(html)["schema_version"] == "15.0.0"


def test_woocommerce_modo_prueba():
    assert wordpress.en_modo_prueba({"settings": {"testmode": {"value": "yes"}}}) is True
    assert wordpress.en_modo_prueba({"settings": {"environment": {"value": "live"}}}) is False
    assert wordpress.en_modo_prueba({"settings": {}}) is None


def test_store_api_precio_en_unidades_menores():
    p = wordpress.normalizar_store({"name": "Taza", "slug": "taza", "prices": {"price": "1599", "regular_price": "1999", "currency_minor_unit": 2},
                                    "on_sale": True, "images": [], "type": "simple"})
    assert p["precios"] == [15.99] and p["comparar"] == [19.99] and p["imagen"] is False


def test_wordpress_hallazgos_y_sugerencias():
    ahora = datetime.datetime(2026, 10, 19, 12, tzinfo=datetime.timezone.utc)
    inv = {"woocommerce": True,
           "system_status": {"environment": {"version": "9.3.1", "wp_cron": False, "remote_post_successful": False, "php_version": "7.4"},
                             "database": {"wc_database_version": "8.9.0"},
                             "active_plugins": [{"plugin": "woocommerce-gateway-stripe/x.php", "name": "Stripe", "version": "8.0.0", "version_latest": "9.1.0"}],
                             "theme": {"name": "Tienda", "has_outdated_templates": True, "has_woocommerce_support": True,
                                       "overrides": [{"file": "woocommerce/checkout/form-checkout.php", "version": "3.5.0", "core_version": "9.4.0"}]},
                             "pages": [{"page_name": "Checkout", "page_set": True, "page_exists": True, "page_visible": True,
                                        "shortcode_required": True, "shortcode_present": False, "block_present": False}]},
           "pasarelas": [{"id": "stripe", "title": "Tarjeta", "enabled": True, "settings": {"testmode": {"value": "no"}}}],
           "zonas": [{"name": "Patagonia", "metodos": []}],
           "cupones": [{"code": "VIEJO", "date_expires": "2025-01-01T00:00:00"}, {"code": "HOY10", "minimum_amount": "5000"}],
           "webhooks": [{"name": "ERP", "topic": "order.created", "status": "disabled"}],
           "cli_cron": [{"hook": "woocommerce_cancel_unpaid_orders", "next_run_gmt": "2026-10-19 08:00:00"}],
           "productos_norm": []}
    h, s = wordpress.hallazgos_y_sugerencias(inv, ahora)
    textos = " ".join(x["texto"] for x in h)
    for esperado in ("falta correr la actualización de la base", "WP-Cron", "remote_post", "Stripe 8.0.0", "desactualizados",
                     "le falta el shortcode", "modo REAL", "Patagonia", "VIEJO", "disabled", "cron atrasados"):
        assert esperado in textos, esperado
    assert any(x["elemento"] == "HOY10" and "5000" in x["prueba"] for x in s)
    assert any(x["area"] == "Pagos" for x in s)


def test_wordpress_action_scheduler_y_actualizaciones_automaticas():
    inv = {"woocommerce": True, "cli_acciones_fallidas": 7,
           "cli_plugins": [{"name": "woocommerce", "status": "active", "auto_update": "on"},
                           {"name": "viejo", "status": "inactive", "auto_update": "on"}]}
    h, _ = wordpress.hallazgos_y_sugerencias(inv)
    textos = " ".join(x["texto"] for x in h)
    assert "7 acción(es) programadas fallidas" in textos
    assert "1 plugin(s) activos con actualización automática (woocommerce)" in textos  # el inactivo no cuenta


def test_wordpress_tabla_muestra_hpos():
    inv = {"system_status": {"settings": {"HPOS_enabled": True, "HPOS_sync_enabled": True}}, "productos_norm": []}
    _, tablas, _ = wordpress.tablas_e_indicadores(inv, "https://qa.example.com")
    assert ["Almacenamiento de pedidos", "HPOS (tablas propias) con sincronización"] in tablas[0]["filas"]


def test_prestashop_multilenguaje():
    assert prestashop.ml([{"id": "1", "value": "Remera"}, {"id": "2", "value": "T-shirt"}]) == "Remera"
    assert prestashop.ml({"language": [{"id": "1", "value": "Hola"}]}) == "Hola"
    assert prestashop.ml("texto") == "texto"
    assert prestashop.ml([]) is None


def test_prestashop_normaliza_y_detecta():
    p = prestashop.normalizar_producto(
        {"id": "5", "name": [{"id": "1", "value": "Remera"}], "reference": "", "price": "0.000000", "active": "1",
         "available_for_order": "0", "id_tax_rules_group": "0", "meta_description": [{"id": "1", "value": ""}],
         "id_default_image": "0", "out_of_stock": "1", "associations": {}},
        {"5": 0}, {"PS_TAX": "1", "PS_ORDER_OUT_OF_STOCK": "0"}, "https://qa.example.com")
    assert set(c.problemas_producto(p)) >= {"precio_cero", "sobreventa", "sin_imagen", "sin_sku", "no_publicado", "sin_seo"}
    assert p["url"].endswith("id_product=5")


def test_prestashop_stock_total_por_producto():
    m = prestashop.mapa_stock([{"id_product": "7", "id_product_attribute": "0", "quantity": "12"},
                               {"id_product": "7", "id_product_attribute": "3", "quantity": "4"}])
    assert m == {"7": 12}  # la fila con atributo 0 es el total del producto


def test_prestashop_hallazgos_y_sugerencias():
    ahora = datetime.datetime(2026, 10, 19, 12, tzinfo=datetime.timezone.utc)
    inv = {"webservice": True,
           "config": {"PS_SHOP_ENABLE": "0", "PS_CATALOG_MODE": "1", "PS_SSL_ENABLED": "0", "PS_SMARTY_FORCE_COMPILE": "2",
                      "PS_CCCCSS": "0", "PS_CCCJS": "0", "PS_GUEST_CHECKOUT_ENABLED": "1", "PS_ORDER_PROCESS_TYPE": "1",
                      "PS_MULTISHOP_FEATURE_ACTIVE": "0"},
           "carriers": [{"id": "1", "name": [{"id": "1", "value": "Correo"}], "active": "0", "deleted": "0", "is_free": "0"}],
           "currencies": [{"iso_code": "ARS", "active": "1"}, {"iso_code": "USD", "active": "1"}],
           "languages": [{"iso_code": "es", "active": "1"}, {"iso_code": "en", "active": "1"}],
           "cart_rules": [{"id": "1", "code": "VIEJO", "active": "1", "date_to": "2025-01-01 00:00:00", "quantity": "5"},
                          {"id": "2", "code": "HOY10", "active": "1", "date_to": "0000-00-00 00:00:00", "quantity": "10"}],
           "shops": [{"id": "1"}], "ps_mode_dev": True, "productos_norm": []}
    h, s = prestashop.hallazgos_y_sugerencias(inv, ahora)
    textos = " ".join(x["texto"] for x in h)
    for esperado in ("modo mantenimiento", "modo catálogo", "HTTPS", "Smarty recompila", "combinan ni comprimen",
                     "transportista activo", "VIEJO", "modo desarrollador"):
        assert esperado in textos, esperado
    assert any(x["elemento"] == "HOY10" for x in s)
    assert any(x["area"] == "Monedas" for x in s) and any(x["area"] == "Idiomas" for x in s)
    assert any(x["elemento"] == "Compra de invitado" for x in s)


def test_vtex_items_normaliza_lista_o_paginado():
    assert vtex._items([{"a": 1}]) == [{"a": 1}]
    assert vtex._items({"items": [1, 2]}) == [1, 2]
    assert vtex._items(None) == []


def test_vtex_normaliza_y_detecta():
    p = {"productName": "Remera", "productId": "10", "productReference": "", "linkText": "remera",
         "link": "https://t/remera/p", "metaTagDescription": "",
         "items": [{"itemId": "1", "referenceId": [{"Key": "RefId", "Value": ""}], "images": [],
                    "sellers": [{"sellerId": "1", "commertialOffer": {"Price": 0.0, "ListPrice": 0.0, "AvailableQuantity": 0, "IsAvailable": False}}]}]}
    n = vtex.normalizar(p, "https://t")
    assert set(c.problemas_producto(n)) >= {"precio_cero", "sin_imagen", "sin_sku", "no_publicado", "sin_seo"}
    assert n["url"] == "https://t/remera/p"


def test_vtex_hallazgos_y_sugerencias():
    ahora = datetime.datetime(2026, 10, 19, 12, tzinfo=datetime.timezone.utc)
    inv = {"api_publica": True, "workspace": "master",
           "saleschannels": [{"Id": "1", "Name": "Main", "IsActive": True, "CurrencyCode": "BRL"}],
           "shipping": {"items": []},
           "promotions": {"items": [{"name": "BLACK", "isActive": True, "endDateUtc": "2025-01-01T00:00:00Z"},
                                    {"name": "NAVIDAD", "isActive": True, "endDateUtc": "2027-01-01T00:00:00Z"}]},
           "productos_norm": []}
    h, s = vtex.hallazgos_y_sugerencias(inv, ahora)
    textos = " ".join(x["texto"] for x in h)
    assert "workspace master" in textos
    assert "política de envío" in textos
    assert "BLACK" in textos
    assert any(x["elemento"] == "NAVIDAD" for x in s)
    assert any(x["area"] == "Canales de venta" for x in s)


def test_informe_html_con_analisis_e_historial(tmp_path, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    datos = {"generado": "2026-10-19T10:00:00", "historia": "HU-020", "plataforma": "wordpress",
             "tienda": {"url": "https://qa.example.com", "nombre": "QA", "version": "WordPress 6.8 · WooCommerce 9.4", "ambiente": "—"},
             "vidriera": {"chequeos": [{"chequeo": "Portada", "estado": "ok", "detalle": "HTTP 200"}]},
             "indicadores": [{"etiqueta": "Productos con problemas", "valor": 2, "tono": "bad", "detalle": "precio"}],
             "tablas": [{"titulo": "Pasarelas de pago", "columnas": ["Pasarela", "Modo"], "filas": [["Tarjeta", "Prueba"]]}],
             "hallazgos": [{"severidad": "Alta", "area": "Pagos", "texto": "Pasarela en modo REAL"},
                           {"severidad": "Baja", "area": "SEO", "texto": "Sin sitemap"}],
             "sugerencias": [{"area": "Pagos", "elemento": "Tarjeta", "prueba": "Pagar aprobado y rechazado"}],
             "resumen": {"hallazgos": 2, "criticos": 1, "productos_con_problemas": 2, "sugerencias": 1}, "errores": {"cupones": "HTTP 403"}}
    (tmp_path / "wordpress.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    analisis = {"veredicto": "Lista con 1 riesgo", "veredicto_tono": "warn", "descartados": [{"texto": "Sin sitemap", "motivo": "staging"}],
                "pruebas": [{"id": "CP-001", "area": "Pagos", "caso": "Pago rechazado", "resultado": "Aprobado"}],
                "falta_informacion": [{"id": "FI-01", "que_falta": "monto mínimo de envío gratis", "pregunta": "¿Cuál es?"}]}
    (tmp_path / "analisis.json").write_text(json.dumps(analisis, ensure_ascii=False), encoding="utf-8")
    gi.generar(tmp_path / "wordpress.json", tmp_path / "informe-wordpress.html", tmp_path / "analisis.json")
    html = ruta_es(tmp_path / "informe-wordpress.html").read_text(encoding="utf-8")
    for esperado in ("WordPress / WooCommerce", "Lista con 1 riesgo", "Pasarela en modo REAL", "Pago rechazado", "Pasarelas de pago",
                     "FI-01", "HTTP 403", "Evolución de las corridas", "Chequeos de la vidriera"):
        assert esperado in html, esperado
    assert "Sin sitemap" not in html  # descartado por el agente


def test_guardar_archiva_la_corrida_anterior(tmp_path, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    base = {"plataforma": "shopify", "tienda": {"url": "https://x.myshopify.com"}, "hallazgos": [{"severidad": "Media", "area": "Legal", "texto": "a"}],
            "sugerencias": [], "tablas": [], "indicadores": []}
    c.guardar("shopify", dict(base, generado="2026-10-18T10:00:00"), tmp_path)
    c.guardar("shopify", dict(base, generado="2026-10-19T10:00:00"), tmp_path)
    assert (tmp_path / "shopify.json").exists() and (tmp_path / "informe-shopify.html").exists()
    assert len(list((tmp_path / "historial").glob("*/shopify.json"))) == 1
    assert json.loads((tmp_path / "shopify.json").read_text(encoding="utf-8"))["resumen"]["por_severidad"]["Media"] == 1

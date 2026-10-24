#!/usr/bin/env python3
"""
Relevamiento funcional de QA de una tienda PrestaShop AUTORIZADA (solo lectura).

Uso (desde la raíz del repo):
    python herramientas/ecommerce/prestashop.py --tienda https://mi-tienda-qa.example.com [--historia HU-001]
        [--producto https://.../producto.html] [--max-productos 300] [--local C:/www/mitienda] [--confirmar]

Qué hace:
- Verifica que la tienda esté en ECOMMERCE_URLS_AUTORIZADAS del .env.
- Vidriera pública: chequeos comunes (portada y páginas clave, robots, sitemap, 404, errores de PHP o
  excepciones de PrestaShop a la vista —señal de que el modo desarrollador quedó activo—) y datos
  estructurados de una ficha de producto.
- Webservice API (opcional, con PRESTASHOP_WEBSERVICE_KEY de una clave de SOLO LECTURA): productos con
  stock y combinaciones, transportistas y si hay alguno activo, zonas y países, monedas, reglas de carrito
  (vales/cupones), tiendas (multistore), idiomas y las configuraciones que más pesan en QA y rendimiento
  (modo mantenimiento, modo catálogo, HTTPS, Smarty/compilación, combinar-comprimir-cachear CSS y JS,
  checkout de invitado, redondeo, impuestos, términos obligatorios).
- Instalación local (opcional, --local o PRESTASHOP_RUTA_LOCAL): versión de PrestaShop y si _PS_MODE_DEV_
  quedó encendido (lento y filtra errores en producción).
- Calcula hallazgos y sugerencias de prueba y deja en output/prestashop/<historia o host>/: prestashop.json
  e informe-prestashop.html (la corrida anterior pasa a historial/).

Solo GET (y lectura de archivos locales). No crea pedidos, clientes ni productos ni cambia ajustes. La
seguridad de la tienda no se revisa acá (analista-seguridad, pentester-web).
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _comun as c  # noqa: E402

PATRONES_ERROR = [("Error de PHP", r"(?:Fatal error|Parse error|Warning|Notice|Deprecated):\s.{0,200}? on line \d+"),
                  ("Excepción de PrestaShop", r"PrestaShop(?:Database)?Exception|\[PrestaShop\][^<]{0,120}(?:error|exception)"),
                  ("Error SQL a la vista", r"(?:SQLSTATE\[|You have an error in your SQL syntax|Duplicate entry '[^']*' for key)"),
                  ("Sin conexión a la base", r"Link to database cannot be established|Error establishing a database connection")]

# Configuraciones que pedimos a la Webservice (filtradas por nombre) y qué significan para QA / rendimiento.
CONFIG_CLAVES = ["PS_SHOP_ENABLE", "PS_MAINTENANCE_IP", "PS_CATALOG_MODE", "PS_SSL_ENABLED", "PS_SSL_ENABLED_EVERYWHERE",
                 "PS_SMARTY_CACHE", "PS_SMARTY_FORCE_COMPILE", "PS_SMARTY_CONSOLE", "PS_CSS_THEME_CACHE", "PS_JS_THEME_CACHE",
                 "PS_CCCCSS", "PS_CCCJS", "PS_HTML_THEME_COMPRESSION", "PS_CACHE_ENABLED", "PS_HTACCESS_CACHE_CONTROL",
                 "PS_GUEST_CHECKOUT_ENABLED", "PS_ORDER_PROCESS_TYPE", "PS_CONDITIONS", "PS_REGISTRATION_PROCESS_TYPE",
                 "PS_TAX", "PS_ROUND_TYPE", "PS_PRICE_ROUND_MODE", "PS_STOCK_MANAGEMENT", "PS_ORDER_OUT_OF_STOCK",
                 "PS_TOKEN_ENABLE", "PS_MULTISHOP_FEATURE_ACTIVE", "PS_CURRENCY_DEFAULT", "PS_ALLOW_MULTISHIPPING"]


def ml(v):
    """Un campo multilenguaje de la Webservice puede venir como string, {"value":..} o lista por idioma."""
    if isinstance(v, dict):
        if "language" in v:
            v = v["language"]
        else:
            return v.get("value")
    if isinstance(v, list):
        if not v:
            return None
        return v[0].get("value") if isinstance(v[0], dict) else v[0]
    return v


def ps(base, key, recurso, params=""):
    """GET a la Webservice de PrestaShop con la clave como usuario (sin contraseña). (datos, error)."""
    sep = "&" if "?" in params else "?"
    url = f"{base}/api/{recurso}{params}{sep}output_format=JSON" if params else f"{base}/api/{recurso}?output_format=JSON"
    r = c.http(url, headers={"Accept": "application/json"}, usuario=key, clave="", timeout=40)
    if r.error:
        return None, r.error
    if r.status in (401, 403):
        return None, f"HTTP {r.status}: la clave de la Webservice no es válida o no tiene permiso de lectura sobre «{recurso}»"
    if r.status == 404:
        return None, f"HTTP 404: el recurso «{recurso}» no está habilitado en la Webservice"
    if not r.ok:
        return None, f"HTTP {r.status}: {(r.texto or '')[:160]}"
    d = r.json()
    return (d, None) if d is not None else (None, "respuesta no JSON (¿la Webservice responde XML? se pidió JSON)")


def _lista(d, clave):
    """La Webservice devuelve {"products": [...]}; a veces un solo objeto en vez de lista."""
    if not isinstance(d, dict):
        return []
    v = d.get(clave)
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _num(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def mapa_stock(filas):
    """id_product -> cantidad total (la fila con id_product_attribute 0 es el total del producto)."""
    m = {}
    for s in filas:
        pid = str(s.get("id_product") or "")
        q = _num(s.get("quantity"))
        if not pid or q is None:
            continue
        if str(s.get("id_product_attribute") or "0") == "0" or pid not in m:
            m[pid] = int(q)
    return m


def normalizar_producto(p, stock, cfg, base):
    pid = str(p.get("id") or "")
    precio = _num(p.get("price"))
    activo = str(p.get("active")) == "1"
    asociaciones = p.get("associations") or {}
    combinaciones = _lista(asociaciones, "combinations")
    imagenes = _lista(asociaciones, "images")
    oos = str(p.get("out_of_stock") or "2")  # 0 denegar, 1 permitir, 2 según la configuración de la tienda
    permite_global = cfg.get("PS_ORDER_OUT_OF_STOCK") == "1"
    calcula = cfg.get("PS_TAX") != "0"
    return {"titulo": ml(p.get("name")), "ref": (p.get("reference") or "").strip() or pid, "activo": activo,
            "url": f"{base}/index.php?controller=product&id_product={pid}" if pid else None,
            "precios": [precio] if not combinaciones else [],
            "comparar": [None],
            "imagen": bool(imagenes) or str(p.get("id_default_image") or "0") != "0",
            "stock": stock.get(pid), "controla_stock": stock.get(pid) is not None,
            "sigue_vendiendo": oos == "1" or (oos == "2" and permite_global),
            "variantes": len(combinaciones) or 1,
            "sin_sku": 0 if (p.get("reference") or "").strip() else 1,
            "impuesto": (str(p.get("id_tax_rules_group") or "0") != "0") if calcula else None,
            "seo": bool(ml(p.get("meta_description"))),
            "publicado": str(p.get("available_for_order")) == "1",
            "tipo": "combinaciones" if combinaciones else "simple"}


def _fecha(s):
    s = (s or "").strip()
    if not s or s.startswith("0000"):
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("T", " ")).replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def hallazgos_y_sugerencias(inv, ahora=None):
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    h, s = [], []
    cfg = inv.get("config") or {}

    if inv.get("webservice") and cfg.get("PS_SHOP_ENABLE") == "0":
        h.append({"severidad": "Alta", "area": "Tienda", "texto": "La tienda está en modo mantenimiento (PS_SHOP_ENABLE = 0): los visitantes no la ven. En staging puede ser intencional; confirmalo."})
    if cfg.get("PS_CATALOG_MODE") == "1":
        h.append({"severidad": "Alta", "area": "Tienda", "texto": "El modo catálogo está activo (PS_CATALOG_MODE = 1): no hay carrito ni checkout, solo vidriera. Si se espera vender, es un bug."})
    if cfg.get("PS_SSL_ENABLED") == "0":
        h.append({"severidad": "Alta", "area": "Tienda", "texto": "La tienda no tiene HTTPS activo (PS_SSL_ENABLED = 0): el login y el pago viajan sin cifrar."})
    elif cfg.get("PS_SSL_ENABLED") == "1" and cfg.get("PS_SSL_ENABLED_EVERYWHERE") == "0":
        h.append({"severidad": "Baja", "area": "Tienda", "texto": "HTTPS está activo pero no en toda la tienda (PS_SSL_ENABLED_EVERYWHERE = 0): hay páginas que se sirven por HTTP."})

    # Rendimiento (Parámetros avanzados → Rendimiento)
    if cfg.get("PS_SMARTY_FORCE_COMPILE") in ("1", "2"):
        h.append({"severidad": "Media", "area": "Rendimiento", "texto": "Smarty recompila las plantillas en cada carga (PS_SMARTY_FORCE_COMPILE ≠ 0): en producción debe compilar solo si el archivo cambió. Enlentece todas las páginas."})
    if cfg.get("PS_SMARTY_CACHE") == "0":
        h.append({"severidad": "Media", "area": "Rendimiento", "texto": "La caché de plantillas de Smarty está desactivada (PS_SMARTY_CACHE = 0): cada página se arma de cero."})
    if cfg.get("PS_CCCCSS") == "0" or cfg.get("PS_CCCJS") == "0":
        que = ", ".join(x for x, k in (("CSS", "PS_CCCCSS"), ("JS", "PS_CCCJS")) if cfg.get(k) == "0")
        h.append({"severidad": "Baja", "area": "Rendimiento", "texto": f"No se combinan ni comprimen los {que} (CCC desactivado): más pedidos y más bytes por página. Activarlo en producción y revisar que el tema no se rompa."})
    if cfg.get("PS_CACHE_ENABLED") == "0":
        h.append({"severidad": "Baja", "area": "Rendimiento", "texto": "La caché de PrestaShop está desactivada (PS_CACHE_ENABLED = 0)."})

    # Checkout y precios
    if cfg.get("PS_TOKEN_ENABLE") == "0":
        h.append({"severidad": "Media", "area": "Checkout", "texto": "Los tokens de seguridad del front están desactivados (PS_TOKEN_ENABLE = 0): el carrito y el checkout quedan sin protección CSRF."})
    if cfg.get("PS_GUEST_CHECKOUT_ENABLED") is not None:
        inv_guest = cfg.get("PS_GUEST_CHECKOUT_ENABLED") == "1"
        s.append({"area": "Checkout", "elemento": "Compra de invitado", "prueba": f"La compra de invitado está {'activada' if inv_guest else 'desactivada'}: {'comprar sin crear cuenta y que el pedido quede asociado al correo' if inv_guest else 'verificar que obligue a registrarse / iniciar sesión antes de pagar'}."})
    if cfg.get("PS_ORDER_PROCESS_TYPE") is not None:
        s.append({"area": "Checkout", "elemento": "Proceso de compra", "prueba": f"El checkout es {'de una página' if cfg.get('PS_ORDER_PROCESS_TYPE') == '1' else 'de 5 pasos'}: recorrer dirección, transportista, pago y confirmación en mobile y desktop."})
    if cfg.get("PS_CONDITIONS") == "1":
        s.append({"area": "Checkout", "elemento": "Términos y condiciones", "prueba": "Los términos son obligatorios: no se puede confirmar el pedido sin tildar la casilla y el link abre la página de condiciones (CMS)."})
    if cfg.get("PS_ROUND_TYPE") or cfg.get("PS_PRICE_ROUND_MODE"):
        s.append({"area": "Checkout", "elemento": "Redondeo de precios", "prueba": "Verificar el redondeo (PS_ROUND_TYPE / PS_PRICE_ROUND_MODE): que subtotal, impuestos, envío y total cierren en el carrito, el checkout, el pedido y el correo, con cantidades que generen decimales."})

    # Transportistas
    carriers = [t for t in inv.get("carriers") or [] if str(t.get("active")) == "1" and str(t.get("deleted") or "0") == "0"]
    if inv.get("carriers") is not None and not carriers:
        h.append({"severidad": "Alta", "area": "Envíos", "texto": "No hay ningún transportista activo: no se puede completar una compra con envío."})
    for t in carriers[:6]:
        nombre = ml(t.get("name")) or t.get("id")
        s.append({"area": "Envíos", "elemento": nombre, "prueba": f"Checkout eligiendo «{nombre}»{' (envío gratis)' if str(t.get('is_free')) == '1' else ''}: costo por zona y peso, franjas de precio, mínimo para envío gratis y recálculo al cambiar de dirección."})

    # Monedas
    monedas = [m for m in inv.get("currencies") or [] if str(m.get("active")) == "1" and str(m.get("deleted") or "0") == "0"]
    if len(monedas) > 1:
        s.append({"area": "Monedas", "elemento": ", ".join(m.get("iso_code") or "?" for m in monedas[:6]), "prueba": "Cambiar de moneda en la tienda: que los precios se conviertan con la tasa esperada, el redondeo sea correcto y el pago se cobre en la moneda que se muestra."})

    # Idiomas
    idiomas = [i for i in inv.get("languages") or [] if str(i.get("active")) == "1"]
    if len(idiomas) > 1:
        s.append({"area": "Idiomas", "elemento": ", ".join(i.get("iso_code") or "?" for i in idiomas[:8]), "prueba": "Con el analista-traductor: cada página en cada idioma activo (textos sin traducir, claves a la vista, fichas, checkout y correos)."})

    # Vales / reglas de carrito
    for cr in inv.get("cart_rules") or []:
        activo = str(cr.get("active")) == "1"
        vence = _fecha(cr.get("date_to"))
        codigo = (cr.get("code") or "").strip() or ml(cr.get("name")) or cr.get("id")
        if activo and vence and vence < ahora:
            h.append({"severidad": "Baja", "area": "Vales", "texto": f"El vale «{codigo}» está activo pero venció ({str(cr.get('date_to'))[:10]})."})
        elif activo and _num(cr.get("quantity")) == 0:
            h.append({"severidad": "Baja", "area": "Vales", "texto": f"El vale «{codigo}» está activo pero sin usos disponibles (quantity = 0)."})
        elif activo:
            s.append({"area": "Vales", "elemento": codigo, "prueba": f"Aplicar «{codigo}» en el carrito: con el mínimo justo y por debajo, en combinación con otro vale y sobre productos excluidos; verificar descuento, impuestos y envío."})

    # Multitienda
    tiendas = inv.get("shops") or []
    if cfg.get("PS_MULTISHOP_FEATURE_ACTIVE") == "1" or len(tiendas) > 1:
        h.append({"severidad": "Media", "area": "Multitienda", "texto": f"Multitienda está activo ({len(tiendas) or 'varias'} tienda(s)): cada tienda puede tener su catálogo, precios, transportistas y temas. Hay que probar cada una."})

    # Catálogo (mismo criterio que las otras plataformas)
    prods = inv.get("productos_norm") or []
    hc, _, _ = c.analizar_catalogo(prods)
    h += hc
    for p in c.agotados(prods)[:3]:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": "Producto sin stock y con «denegar pedidos»: no se puede agregar al carrito ni comprar por URL directa; el botón figura agotado."})
    for p in [p for p in prods if "sobreventa" in c.problemas_producto(p)][:3]:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": "Comprar sin stock con «permitir pedidos»: aviso de disponibilidad al comprador, estado del pedido y stock negativo controlado."})
    for p in [p for p in prods if p.get("tipo") == "combinaciones"][:3]:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": "Producto con combinaciones: cada combinación cambia precio, imagen, referencia y stock; una combinación sin stock o inexistente no se puede agregar."})

    if inv.get("ps_mode_dev") is True:
        h.append({"severidad": "Media", "area": "Tienda", "texto": "El modo desarrollador está encendido (_PS_MODE_DEV_ = true): muestra errores y perfilado, y es más lento. En producción tiene que estar apagado."})

    if inv.get("webservice"):
        s += [{"area": "Checkout", "elemento": "Flujo de compra", "prueba": "Comprar como invitado y con cuenta, con pasarela en modo de prueba; validaciones de cada campo de la dirección (probador-formularios) y que subtotal + envío + impuestos − descuentos = total en carrito, checkout, pedido y correo."},
              {"area": "Correos", "elemento": "Correos transaccionales", "prueba": "Con el verificador-correos: confirmación del pedido, pago aceptado, en preparación, enviado y cambio de contraseña; variables sin reemplazar y links."},
              {"area": "Permisos", "elemento": "Roles", "prueba": "Con el probador-permisos: cliente, invitado y anónimo sobre «Mi cuenta», pedidos ajenos y el back-office (acceso por URL directa)."},
              {"area": "Rendimiento", "elemento": "Fichas y listados", "prueba": "Con el auditor-rendimiento-web: portada, categoría con muchos productos y ficha; medir con y sin la caché y la combinación de CSS/JS activadas."}]
    return c.ordenar(h), s


def tablas_e_indicadores(inv, base):
    cfg = inv.get("config") or {}
    prods = inv.get("productos_norm") or []
    _, filas_cat, n_prob = c.analizar_catalogo(prods)
    carriers_act = [t for t in inv.get("carriers") or [] if str(t.get("active")) == "1" and str(t.get("deleted") or "0") == "0"]
    monedas = [m for m in inv.get("currencies") or [] if str(m.get("active")) == "1"]
    idiomas = [i for i in inv.get("languages") or [] if str(i.get("active")) == "1"]
    si_no = {"1": "Sí", "0": "No"}
    datos = [["URL", base], ["Nombre", inv.get("nombre") or "—"],
             ["Versión", inv.get("version") or "—"],
             ["Modo desarrollador", {True: "Encendido", False: "Apagado"}.get(inv.get("ps_mode_dev"), "—")],
             ["Tienda activa", si_no.get(cfg.get("PS_SHOP_ENABLE"), "—")],
             ["Modo catálogo", si_no.get(cfg.get("PS_CATALOG_MODE"), "—")],
             ["HTTPS", si_no.get(cfg.get("PS_SSL_ENABLED"), "—") + (" (en todo el sitio)" if cfg.get("PS_SSL_ENABLED_EVERYWHERE") == "1" else "")],
             ["Multitienda", si_no.get(cfg.get("PS_MULTISHOP_FEATURE_ACTIVE"), "Sí" if len(inv.get("shops") or []) > 1 else "—")],
             ["Checkout", {"1": "Una página", "0": "5 pasos"}.get(cfg.get("PS_ORDER_PROCESS_TYPE"), "—")],
             ["Compra de invitado", si_no.get(cfg.get("PS_GUEST_CHECKOUT_ENABLED"), "—")],
             ["Idiomas activos", ", ".join(i.get("iso_code") or "?" for i in idiomas) or "—"],
             ["Monedas activas", ", ".join(m.get("iso_code") or "?" for m in monedas) or "—"],
             ["Webservice API", "con clave de lectura" if inv.get("webservice") else "sin clave (solo vidriera pública)"]]
    tablas = [c.tabla("La tienda", ["Dato", "Valor"], datos)]
    if filas_cat:
        tablas.append(c.tabla("Productos con problemas", ["Producto", "Referencia", "Problemas"], filas_cat[:150], f"{n_prob} de {len(prods)} revisados"))
    if inv.get("carriers"):
        tablas.append(c.tabla("Transportistas", ["Transportista", "Activo", "Gratis"],
                              [[ml(t.get("name")) or t.get("id"), si_no.get(str(t.get("active")), "No"), si_no.get(str(t.get("is_free")), "No")] for t in inv["carriers"]]))
    if inv.get("currencies"):
        tablas.append(c.tabla("Monedas", ["Moneda", "ISO", "Tasa", "Activa"],
                              [[ml(m.get("name")) or m.get("id"), m.get("iso_code"), m.get("conversion_rate"), si_no.get(str(m.get("active")), "No")] for m in inv["currencies"]]))
    if inv.get("cart_rules"):
        tablas.append(c.tabla("Vales (reglas de carrito)", ["Código", "Activo", "Vence", "Usos"],
                              [[(cr.get("code") or "").strip() or ml(cr.get("name")) or cr.get("id"), si_no.get(str(cr.get("active")), "No"),
                                (str(cr.get("date_to"))[:10] if _fecha(cr.get("date_to")) else "—"), cr.get("quantity")] for cr in inv["cart_rules"]]))
    rend = [[k, cfg.get(k)] for k in ("PS_SMARTY_CACHE", "PS_SMARTY_FORCE_COMPILE", "PS_CCCCSS", "PS_CCCJS", "PS_CACHE_ENABLED", "PS_HTACCESS_CACHE_CONTROL") if cfg.get(k) is not None]
    if rend:
        tablas.append(c.tabla("Rendimiento (configuración)", ["Parámetro", "Valor"], rend))
    indicadores = [{"etiqueta": "Productos revisados", "valor": len(prods), "tono": "", "detalle": "Webservice API" if inv.get("webservice") else "sin clave"},
                   {"etiqueta": "Productos con problemas", "valor": n_prob, "tono": "bad" if n_prob else "ok", "detalle": "precio, stock, imagen, impuestos"},
                   {"etiqueta": "Transportistas activos", "valor": len(carriers_act), "tono": "bad" if (inv.get("carriers") is not None and not carriers_act) else "ok", "detalle": f"de {len(inv.get('carriers') or [])}"}]
    return indicadores, tablas, n_prob


def leer_local(ruta):
    """Versión de PrestaShop y si el modo desarrollador quedó encendido, leyendo la instalación local."""
    base = Path(ruta)
    info = {"version": None, "ps_mode_dev": None, "errores": {}}
    for rel, rx in (("app/AppKernel.php", r"const VERSION\s*=\s*'([^']+)'"),
                    ("config/settings.inc.php", r"_PS_VERSION_['\"]?\s*,\s*'([^']+)'"),
                    ("install/install_version.php", r"_PS_INSTALL_VERSION_['\"]?\s*,\s*'([^']+)'")):
        try:
            m = re.search(rx, (base / rel).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if m:
            info["version"] = m.group(1)
            break
    for rel in ("config/defines_custom.inc.php", "config/defines.inc.php"):
        try:
            txt = (base / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.search(r"_PS_MODE_DEV_['\"]?\s*,\s*(true|false|1|0)", txt, re.I)
        if m:
            info["ps_mode_dev"] = m.group(1).lower() in ("true", "1")
            break
    if info["version"] is None and info["ps_mode_dev"] is None:
        info["errores"]["local"] = f"No se encontró la instalación de PrestaShop en {ruta} (app/AppKernel.php, config/defines.inc.php)."
    return info


def main(argv=None):
    c.preparar_consola()
    ap = argparse.ArgumentParser(description="Relevamiento funcional de QA de una tienda PrestaShop (solo lectura).")
    ap.add_argument("--tienda", help="URL de la tienda (o PRESTASHOP_URL del .env)")
    ap.add_argument("--historia", default="")
    ap.add_argument("--producto", default="", help="URL de una ficha de producto para revisar (si no, la primera del catálogo)")
    ap.add_argument("--max-productos", type=int, default=300)
    ap.add_argument("--local", default="", help="ruta de la instalación local para leer la versión y el modo dev (o PRESTASHOP_RUTA_LOCAL)")
    ap.add_argument("--confirmar", action="store_true")
    args = ap.parse_args(argv)

    env = c.leer_env("PRESTASHOP_")
    base = c.normalizar_url(args.tienda or env.get("PRESTASHOP_URL") or "")
    if not base:
        c.salir("Falta la tienda: pasala con --tienda https://mi-tienda.example.com o poné PRESTASHOP_URL en el .env.")
    c.autorizar(base, env)
    key = (env.get("PRESTASHOP_WEBSERVICE_KEY") or "").strip()
    c.confirmar(f"Vas a relevar la tienda PrestaShop {base} (solo lectura{'; con la Webservice API' if key else ''}).", args.confirmar)

    inv, errores = {"webservice": bool(key)}, {}
    local = args.local or env.get("PRESTASHOP_RUTA_LOCAL") or ""
    if local:
        print(f"[prestashop] Instalación local {local} …", file=sys.stderr)
        li = leer_local(local)
        inv["version"], inv["ps_mode_dev"] = li["version"], li["ps_mode_dev"]
        errores.update(li["errores"])

    if key:
        print(f"[prestashop] Webservice {base}/api …", file=sys.stderr)
        cfg_rows, err = ps(base, key, "configurations", f"display=full&filter[name]=[{'|'.join(CONFIG_CLAVES)}]&limit=200")
        if err:
            errores["configurations"] = err
        inv["config"] = {ml(x.get("name")) or x.get("name"): ml(x.get("value")) for x in _lista(cfg_rows, "configurations")}

        for clave, recurso, params in (("carriers", "carriers", "display=full&limit=200"),
                                       ("zones", "zones", "display=full"),
                                       ("currencies", "currencies", "display=full"),
                                       ("languages", "languages", "display=full"),
                                       ("cart_rules", "cart_rules", "display=full&limit=200"),
                                       ("shops", "shops", "display=full")):
            print(f"[prestashop] Webservice · {clave} …", file=sys.stderr)
            d, err = ps(base, key, recurso, params)
            inv[clave] = _lista(d, recurso)
            if err:
                errores[clave] = err

        print("[prestashop] Webservice · stock_availables …", file=sys.stderr)
        st, err = ps(base, key, "stock_availables", f"display=full&limit={args.max_productos * 3}")
        if err:
            errores["stock_availables"] = err
        stock = mapa_stock(_lista(st, "stock_availables"))

        print("[prestashop] Webservice · products …", file=sys.stderr)
        pr, err = ps(base, key, "products", f"display=full&filter[active]=1&limit={args.max_productos}")
        if err:
            errores["products"] = err
        inv["productos_norm"] = [normalizar_producto(p, stock, inv.get("config") or {}, base) for p in _lista(pr, "products")]
        nombre_cfg = (inv.get("config") or {}).get("PS_SHOP_NAME")
    else:
        inv["config"], inv["productos_norm"], nombre_cfg = {}, [], None

    # Vidriera pública
    url_producto = args.producto or next((p.get("url") for p in inv["productos_norm"] if p.get("url")), "")
    print(f"[prestashop] Vidriera {base} …", file=sys.stderr)
    chequeos, hallazgos_vid, home = c.chequear_vidriera(base, PATRONES_ERROR, [url_producto] if url_producto else [])
    ch_p, h_p = c.chequear_producto(url_producto)
    es_ps = bool(re.search(r'name=["\']generator["\'][^>]*PrestaShop|var\s+prestashop\s*=|/modules/ps_', home.texto or "", re.I))
    inv["nombre"] = nombre_cfg or re.sub(r"^https?://", "", base)
    chequeos += ch_p + [{"chequeo": "PrestaShop detectado", "estado": "ok" if es_ps else "aviso",
                         "detalle": "sí (generator/variables del front)" if es_ps else "no se reconocieron señales de PrestaShop en la portada"},
                        {"chequeo": "Webservice API", "estado": "ok" if key and not errores.get("products") else ("aviso" if key else "info"),
                         "detalle": f'{len(inv["productos_norm"])} producto(s)' if key else "sin clave (solo vidriera pública)"}]

    hallazgos, sugerencias = hallazgos_y_sugerencias(inv)
    hallazgos = c.ordenar(hallazgos_vid + h_p + hallazgos)
    indicadores, tablas, n_prob = tablas_e_indicadores(inv, base)
    datos = {"historia": args.historia or None, "plataforma": "prestashop",
             "tienda": {"url": base, "nombre": inv.get("nombre"),
                        "version": f'PrestaShop {inv.get("version")}' if inv.get("version") else "PrestaShop",
                        "ambiente": "—"},
             "vidriera": {"chequeos": chequeos}, "inventario": {k: v for k, v in inv.items() if k != "productos_norm"},
             "indicadores": indicadores, "tablas": tablas, "hallazgos": hallazgos, "sugerencias": sugerencias,
             "resumen": {"productos": len(inv["productos_norm"]), "productos_con_problemas": n_prob}, "errores": errores}
    c.guardar("prestashop", datos, c.carpeta_salida("prestashop", args.historia, base))
    return 0


if __name__ == "__main__":
    sys.exit(main())

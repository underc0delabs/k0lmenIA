#!/usr/bin/env python3
"""
Relevamiento funcional de QA de un sitio WordPress / WooCommerce AUTORIZADO (solo lectura).

Uso (desde la raíz del repo):
    python herramientas/ecommerce/wordpress.py --sitio https://mi-tienda-qa.example.com [--historia HU-001]
        [--producto https://.../producto/remera/] [--max-productos 300] [--wp-cli] [--confirmar]

Qué hace:
- Verifica que el sitio esté en ECOMMERCE_URLS_AUTORIZADAS del .env.
- Vidriera pública: chequeos comunes (portada y páginas clave, robots, sitemap, 404, errores de PHP o el
  "error crítico" de WordPress a la vista), qué módulos expone la REST API (/wp-json: WooCommerce, SEO,
  formularios, constructores) y el catálogo público de la Store API de WooCommerce.
- WooCommerce REST API (opcional, con WOOCOMMERCE_CONSUMER_KEY/SECRET de una clave de LECTURA): estado del
  sistema (versiones, base de datos pendiente de actualizar, cron, llamadas salientes, plugins y su última
  versión, templates del tema sobrescritos y desactualizados, páginas de WooCommerce), pasarelas de pago y
  si están en modo de prueba, zonas y métodos de envío, cupones, webhooks, ajustes generales y productos
  con stock y pedidos pendientes (backorders).
- WP-CLI (opcional, --wp-cli con WORDPRESS_RUTA_LOCAL o WORDPRESS_WP_CLI): actualizaciones de WordPress,
  plugins y temas, y eventos de cron atrasados.
- Calcula hallazgos y sugerencias de prueba y deja en output/wordpress/<historia o host>/: wordpress.json e
  informe-wordpress.html (la corrida anterior pasa a historial/).

Solo GET (y comandos de lectura de WP-CLI). No crea pedidos, clientes ni productos ni cambia ajustes. La
seguridad del sitio no se revisa acá (analista-seguridad, pentester-web).
"""
import argparse
import datetime
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _comun as c  # noqa: E402

PATRONES_ERROR = [("Error de PHP", r"(?:Fatal error|Parse error|Warning|Notice|Deprecated):\s.{0,200}? on line \d+"),
                  ("Error crítico de WordPress", r"There has been a critical error on this website|Ha habido un error crítico en esta web"),
                  ("Sin conexión a la base", r"Error establishing a database connection|Error al establecer una conexión con la base de datos")]
NAMESPACES = {"wc/v3": "WooCommerce", "wc/store/v1": "WooCommerce (Store API)", "yoast/v1": "Yoast SEO", "rankmath/v1": "Rank Math",
              "contact-form-7/v1": "Contact Form 7", "gf/v2": "Gravity Forms", "elementor/v1": "Elementor", "jetpack/v4": "Jetpack",
              "wpml/v1": "WPML", "pll/v1": "Polylang", "wc-admin": "WooCommerce Admin", "wc-analytics": "WooCommerce Analytics",
              "mailpoet/v1": "MailPoet", "litespeed/v1": "LiteSpeed Cache", "wp-rocket/v1": "WP Rocket"}
CLAVES_PRUEBA = ("testmode", "test_mode", "sandbox", "sandbox_mode", "environment", "mode")


def wc(base, ck, cs, ruta):
    """GET a la REST API de WooCommerce con clave de lectura. (datos, error)."""
    r = c.http(f"{base}/wp-json/wc/v3/{ruta}", headers={"Accept": "application/json"}, usuario=ck, clave=cs, timeout=40)
    if r.error:
        return None, r.error
    if r.status in (401, 403):
        return None, f"HTTP {r.status}: la clave no es válida o no tiene permiso de lectura"
    if not r.ok:
        return None, f"HTTP {r.status}: {(r.texto or '')[:160]}"
    d = r.json()
    return (d, None) if d is not None else (None, "respuesta no JSON")


def productos_store(base, maximo):
    salida, pagina = [], 1
    while len(salida) < maximo and pagina <= 20:
        r = c.http(f"{base}/wp-json/wc/store/v1/products?per_page=100&page={pagina}", headers={"Accept": "application/json"}, timeout=30)
        d = r.json() if r.ok else None
        if not isinstance(d, list) or not d:
            break
        salida += d
        pagina += 1
    return salida[:maximo]


def productos_v3(base, ck, cs, maximo):
    salida, pagina, err = [], 1, None
    while len(salida) < maximo and pagina <= 20:
        d, err = wc(base, ck, cs, f"products?per_page=100&page={pagina}&status=publish")
        if not isinstance(d, list) or not d:
            break
        salida += d
        pagina += 1
    return salida[:maximo], err


def _num(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def normalizar_store(p):
    pr = p.get("prices") or {}
    div = 10 ** int(pr.get("currency_minor_unit") or 0)
    precio = _num(pr.get("price"))
    regular = _num(pr.get("regular_price"))
    return {"titulo": p.get("name"), "ref": p.get("slug"), "activo": True, "url": p.get("permalink"),
            "precios": [precio / div if precio is not None else None],
            "comparar": [regular / div if regular is not None and p.get("on_sale") else None],
            "imagen": bool(p.get("images")), "stock": None, "controla_stock": None, "sigue_vendiendo": None,
            "variantes": len(p.get("variations") or []) or 1, "sin_sku": 0, "seo": None, "publicado": True,
            "disponible": p.get("is_in_stock"), "tipo": p.get("type")}


def normalizar_v3(p, calcula_impuestos):
    precio, regular = _num(p.get("price")), _num(p.get("regular_price"))
    return {"titulo": p.get("name"), "ref": p.get("slug"), "activo": p.get("status") == "publish" and p.get("purchasable", True),
            "url": p.get("permalink"), "precios": [precio] if p.get("type") != "variable" else [],
            "comparar": [regular if p.get("on_sale") and regular and precio and regular <= precio else None],
            "imagen": bool(p.get("images")), "stock": p.get("stock_quantity"), "controla_stock": bool(p.get("manage_stock")),
            "sigue_vendiendo": p.get("backorders") in ("yes", "notify"), "variantes": len(p.get("variations") or []) or 1,
            "sin_sku": 0 if (p.get("sku") or "").strip() else 1,
            "impuesto": (p.get("tax_status") != "none") if calcula_impuestos else None, "seo": None, "publicado": True,
            "disponible": p.get("stock_status") != "outofstock", "tipo": p.get("type")}


def _version(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v or ""))[:4])


def en_modo_prueba(gw):
    """True / False / None (no se sabe) según los ajustes de la pasarela."""
    ajustes = gw.get("settings") or {}
    for clave in CLAVES_PRUEBA:
        if clave in ajustes:
            v = str((ajustes[clave] or {}).get("value", "")).lower()
            if v in ("yes", "1", "true", "sandbox", "test", "staging"):
                return True
            if v in ("no", "0", "false", "live", "production", "produccion"):
                return False
    return None


def wp_cli(inv_cli, ruta, args):
    cmd = shlex.split(inv_cli) + list(args) + (["--path=" + ruta] if ruta else []) + ["--skip-themes", "--quiet"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    except (OSError, subprocess.TimeoutExpired) as ex:
        return None, str(ex)[:200]
    if p.returncode != 0:
        return None, (p.stderr or p.stdout or "error de WP-CLI").strip()[:300]
    try:
        return json.loads(p.stdout or "null"), None
    except ValueError:
        return None, "salida no JSON"


def hallazgos_y_sugerencias(inv, ahora=None):
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    h, s = [], []
    ss = inv.get("system_status") or {}
    env = ss.get("environment") or {}
    db = ss.get("database") or {}
    if not inv.get("woocommerce"):
        h.append({"severidad": "Baja", "area": "Sitio", "texto": "No se detectó WooCommerce en la REST API: se relevó como sitio WordPress (sin tienda)."})
    if env.get("version") and db.get("wc_database_version") and _version(env["version"])[:2] != _version(db["wc_database_version"])[:2]:
        h.append({"severidad": "Alta", "area": "WooCommerce", "texto": f'La base de WooCommerce está en {db["wc_database_version"]} y el plugin en {env["version"]}: falta correr la actualización de la base (pedidos y stock pueden fallar).'})
    if env.get("wp_cron") is False:
        h.append({"severidad": "Media", "area": "Sitio", "texto": "WP-Cron está desactivado: ofertas programadas, cancelación de pedidos impagos y correos diferidos dependen de un cron del servidor. Confirmar que existe."})
    if env.get("remote_post_successful") is False:
        h.append({"severidad": "Alta", "area": "Integraciones", "texto": "El sitio no puede hacer llamadas salientes (remote_post): las pasarelas, los webhooks y las notificaciones de pago pueden fallar."})
    if env.get("php_version") and _version(env["php_version"]) < (8, 1):
        h.append({"severidad": "Baja", "area": "Sitio", "texto": f'PHP {env["php_version"]}: varias versiones actuales de plugins exigen 8.1 o más.'})
    if env.get("default_timezone") and env["default_timezone"] != "UTC":
        h.append({"severidad": "Baja", "area": "Sitio", "texto": f'La zona horaria por defecto de PHP es {env["default_timezone"]} y WooCommerce espera UTC: revisar fechas de pedidos y cupones.'})

    viejos = [p for p in ss.get("active_plugins") or [] if p.get("version_latest") and _version(p.get("version_latest")) > _version(p.get("version"))]
    viejos += [p for p in inv.get("cli_plugins") or [] if p.get("update") == "available" and p.get("status") in ("active", "active-network")
               and not any((x.get("plugin") or "").split("/")[0] == p.get("name") for x in viejos)]
    if viejos:
        nombres = [f'{p.get("name")} {p.get("version")}' for p in viejos]
        h.append({"severidad": "Media", "area": "Plugins", "texto": f'{len(viejos)} plugin(s) activos con actualización disponible: {", ".join(nombres[:6])}{"…" if len(nombres) > 6 else ""}. Actualizar en staging y correr la regresión del flujo de compra.'})
        for p in viejos[:5]:
            s.append({"area": "Plugins", "elemento": p.get("name"), "prueba": f'Después de actualizar {p.get("name")} en staging: recorrer catálogo, carrito, checkout y Mi cuenta, y revisar la consola del navegador.'})
    inactivos = ss.get("inactive_plugins") or []
    if len(inactivos) > 5:
        h.append({"severidad": "Baja", "area": "Plugins", "texto": f"{len(inactivos)} plugins instalados e inactivos: conviene borrar los que no se usan."})
    if inv.get("cli_core_update"):
        h.append({"severidad": "Media", "area": "Sitio", "texto": f'Hay una actualización de WordPress disponible ({", ".join(u.get("version", "?") for u in inv["cli_core_update"][:2])}).'})

    tema = ss.get("theme") or {}
    if tema.get("has_outdated_templates"):
        viejas = [o for o in tema.get("overrides") or [] if o.get("version") and o.get("core_version") and o["version"] != o["core_version"]]
        h.append({"severidad": "Alta", "area": "Tema", "texto": f'El tema {tema.get("name")} sobrescribe {len(viejas) or "varios"} template(s) de WooCommerce desactualizados: el carrito, el checkout o los correos pueden verse o comportarse mal.'})
        for o in viejas[:5]:
            s.append({"area": "Tema", "elemento": o.get("file"), "prueba": f'Revisar la pantalla que usa {o.get("file")} (template {o.get("version")}, WooCommerce espera {o.get("core_version")}): textos, campos y botones.'})
    if inv.get("woocommerce") and tema and tema.get("has_woocommerce_support") is False and not tema.get("is_block_theme"):
        h.append({"severidad": "Media", "area": "Tema", "texto": f'El tema {tema.get("name")} no declara soporte de WooCommerce.'})

    for pg in ss.get("pages") or []:
        nombre = pg.get("page_name") or "?"
        if pg.get("page_set") is False or pg.get("page_exists") is False:
            h.append({"severidad": "Alta", "area": "WooCommerce", "texto": f'La página de WooCommerce "{nombre}" no está configurada o no existe.'})
        elif pg.get("page_visible") is False:
            h.append({"severidad": "Alta", "area": "WooCommerce", "texto": f'La página "{nombre}" existe pero no está publicada.'})
        elif pg.get("shortcode_required") and not pg.get("shortcode_present") and not pg.get("block_present"):
            h.append({"severidad": "Alta", "area": "WooCommerce", "texto": f'A la página "{nombre}" le falta el shortcode o bloque de WooCommerce: se ve vacía.'})
        if pg.get("block_present"):
            s.append({"area": "Checkout", "elemento": nombre, "prueba": f'"{nombre}" usa bloques: verificar que los plugins de pago, envío y campos extra funcionen con el checkout de bloques (no todos son compatibles).'})

    activas = [g for g in inv.get("pasarelas") or [] if g.get("enabled")]
    if inv.get("woocommerce") and inv.get("pasarelas") is not None and not activas:
        h.append({"severidad": "Alta", "area": "Pagos", "texto": "No hay ninguna pasarela de pago habilitada: no se puede completar una compra."})
    for g in activas:
        prueba = en_modo_prueba(g)
        if prueba is False:
            h.append({"severidad": "Alta", "area": "Pagos", "texto": f'La pasarela "{g.get("title") or g.get("id")}" está habilitada en modo REAL: en QA no se ejecutan pagos con ella hasta pasarla a modo de prueba.'})
        s.append({"area": "Pagos", "elemento": g.get("title") or g.get("id"),
                  "prueba": f'Pagar con "{g.get("title") or g.get("id")}" {"en modo de prueba " if prueba else "(confirmar antes que esté en modo de prueba) "}con tarjeta aprobada, rechazada y con 3-D Secure; verificar estado del pedido, stock, nota del pedido y correo. Volver atrás desde la pasarela y repetir el pago.'})

    for z in inv.get("zonas") or []:
        metodos = [m for m in z.get("metodos") or [] if m.get("enabled")]
        if not metodos:
            h.append({"severidad": "Media", "area": "Envíos", "texto": f'La zona de envío "{z.get("name")}" no tiene métodos habilitados: a esas direcciones no se puede comprar con envío.'})
        for m in metodos[:4]:
            s.append({"area": "Envíos", "elemento": f'{z.get("name")} · {m.get("title")}', "prueba": f'Checkout con dirección de la zona "{z.get("name")}" eligiendo "{m.get("title")}": costo, mínimo para envío gratis, cambio de dirección a otra zona y recálculo del total.'})

    for cu in inv.get("cupones") or []:
        vence = cu.get("date_expires_gmt") or cu.get("date_expires")
        vencido = False
        if vence:
            try:
                vencido = datetime.datetime.fromisoformat(vence.replace("Z", "")).replace(tzinfo=datetime.timezone.utc) < ahora
            except ValueError:
                pass
        if vencido:
            h.append({"severidad": "Baja", "area": "Cupones", "texto": f'El cupón "{cu.get("code")}" está vencido ({vence[:10]}) y sigue publicado.'})
        elif cu.get("usage_limit") and (cu.get("usage_count") or 0) >= cu["usage_limit"]:
            h.append({"severidad": "Baja", "area": "Cupones", "texto": f'El cupón "{cu.get("code")}" agotó sus usos ({cu.get("usage_count")} de {cu.get("usage_limit")}).'})
        else:
            s.append({"area": "Cupones", "elemento": cu.get("code"), "prueba": f'Aplicar "{cu.get("code")}" válido, en mayúsculas, con espacios, sobre un carrito bajo el mínimo{" (" + str(cu.get("minimum_amount")) + ")" if _num(cu.get("minimum_amount")) else ""}, con productos excluidos y junto con otro cupón; verificar descuento, impuestos y envío.'})

    for w in inv.get("webhooks") or []:
        if w.get("status") in ("disabled", "paused"):
            h.append({"severidad": "Alta", "area": "Integraciones", "texto": f'El webhook "{w.get("name")}" ({w.get("topic")}) está {w.get("status")}: WooCommerce los desactiva después de varios fallos de entrega.'})
        elif w.get("status") == "active":
            s.append({"area": "Integraciones", "elemento": w.get("topic"), "prueba": f'Disparar {w.get("topic")} y verificar que el receptor lo procese una sola vez y valide la firma X-WC-Webhook-Signature.'})

    atrasados = []
    for ev in inv.get("cli_cron") or []:
        try:
            prox = datetime.datetime.fromisoformat(str(ev.get("next_run_gmt")).replace(" ", "T")).replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
        if (ahora - prox).total_seconds() > 3600:
            atrasados.append(ev.get("hook"))
    if atrasados:
        h.append({"severidad": "Media", "area": "Sitio", "texto": f'{len(atrasados)} evento(s) de cron atrasados más de una hora: {", ".join(atrasados[:5])}. El cron no se está ejecutando.'})
    fallidas = inv.get("cli_acciones_fallidas")
    if isinstance(fallidas, int) and fallidas > 0:
        h.append({"severidad": "Media", "area": "WooCommerce", "texto": f"{fallidas} acción(es) programadas fallidas en Action Scheduler: correos diferidos, webhooks, renovaciones o reportes que no se ejecutaron (WooCommerce → Estado → Acciones programadas)."})
    auto = [p.get("name") for p in inv.get("cli_plugins") or [] if p.get("auto_update") == "on" and p.get("status") in ("active", "active-network")]
    if auto:
        h.append({"severidad": "Baja", "area": "Plugins", "texto": f'{len(auto)} plugin(s) activos con actualización automática ({", ".join(auto[:6])}): en producción se actualizan sin pasar por staging.'})

    prods = inv.get("productos_norm") or []
    hc, _, _ = c.analizar_catalogo(prods)
    h += hc
    for p in c.agotados(prods)[:3]:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": "Producto sin stock y sin pedidos pendientes: el botón de compra no aparece y no se puede agregar por ?add-to-cart=ID."})
    for p in [p for p in prods if "sobreventa" in c.problemas_producto(p)][:3]:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": "Comprar sin stock con pedidos pendientes (backorders): aviso al comprador, estado del pedido y stock negativo controlado."})
    for p in [p for p in prods if p.get("tipo") == "variable"][:3]:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": "Producto variable: cada combinación cambia precio, imagen y stock; una combinación sin stock o inexistente no se puede agregar."})

    if inv.get("woocommerce"):
        s += [{"area": "Checkout", "elemento": "Invitado y cuenta", "prueba": "Comprar como invitado, creando cuenta en el checkout y con sesión iniciada; validaciones de cada campo (probador-formularios)."},
              {"area": "Checkout", "elemento": "Carrito", "prueba": "Cantidades 0, 1, máximo de stock y más; quitar productos; carrito con la sesión vencida; mini-carrito y página de carrito con el mismo total."},
              {"area": "Correos", "elemento": "Correos de WooCommerce", "prueba": "Con el verificador-correos: pedido nuevo (tienda), procesando, completado, reembolsado, nota al cliente y restablecer contraseña."},
              {"area": "Permisos", "elemento": "Roles", "prueba": "Con el probador-permisos: cliente, gestor de la tienda (shop_manager) y anónimo sobre Mi cuenta, pedidos ajenos y el panel."}]
    return c.ordenar(h), s


def tablas_e_indicadores(inv, base):
    ss = inv.get("system_status") or {}
    env = ss.get("environment") or {}
    tema = ss.get("theme") or {}
    prods = inv.get("productos_norm") or []
    _, filas_cat, n_prob = c.analizar_catalogo(prods)
    ajustes = {a.get("id"): a.get("value") for a in inv.get("ajustes") or []}
    datos = [["URL", base], ["Nombre", inv.get("nombre") or "—"], ["WordPress", env.get("wp_version") or inv.get("version_publica") or "—"],
             ["WooCommerce", env.get("version") or ("detectado" if inv.get("woocommerce") else "no")],
             ["PHP", env.get("php_version") or "—"], ["Multisitio", {True: "Sí", False: "No"}.get(env.get("wp_multisite"), "—")],
             ["Tema", f'{tema.get("name") or "—"} {tema.get("version") or ""}'.strip()],
             ["Almacenamiento de pedidos", {True: "HPOS (tablas propias)", False: "Entradas de WordPress"}.get((ss.get("settings") or {}).get("HPOS_enabled"), "—")
              + (" con sincronización" if (ss.get("settings") or {}).get("HPOS_sync_enabled") else "")],
             ["Moneda", ajustes.get("woocommerce_currency") or "—"], ["Calcula impuestos", {"yes": "Sí", "no": "No"}.get(ajustes.get("woocommerce_calc_taxes"), "—")],
             ["Módulos en la REST API", ", ".join(inv.get("modulos") or []) or "—"],
             ["REST API de WooCommerce", "con clave de lectura" if inv.get("system_status") else "sin clave (solo catálogo público)"]]
    tablas = [c.tabla("El sitio", ["Dato", "Valor"], datos)]
    if filas_cat:
        tablas.append(c.tabla("Productos con problemas", ["Producto", "Slug", "Problemas"], filas_cat[:150], f"{n_prob} de {len(prods)} revisados"))
    plugins = ss.get("active_plugins") or []
    if plugins:
        tablas.append(c.tabla("Plugins activos", ["Plugin", "Versión", "Última", "Estado"],
                              [[p.get("name"), p.get("version"), p.get("version_latest") or "—",
                                "Desactualizado" if p.get("version_latest") and _version(p["version_latest"]) > _version(p.get("version")) else "Al día"] for p in plugins]))
    elif inv.get("cli_plugins"):
        tablas.append(c.tabla("Plugins (WP-CLI)", ["Plugin", "Estado", "Versión", "Actualización"],
                              [[p.get("name"), p.get("status"), p.get("version"), p.get("update_version") or ("disponible" if p.get("update") == "available" else "—")] for p in inv["cli_plugins"]]))
    over = [o for o in tema.get("overrides") or [] if o.get("version") and o.get("core_version") and o["version"] != o["core_version"]]
    if over:
        tablas.append(c.tabla("Templates de WooCommerce desactualizados", ["Archivo", "Versión del tema", "Versión de WooCommerce"],
                              [[o.get("file"), o.get("version"), o.get("core_version")] for o in over]))
    if ss.get("pages"):
        tablas.append(c.tabla("Páginas de WooCommerce", ["Página", "Configurada", "Publicada", "Contenido"],
                              [[pg.get("page_name"), "Sí" if pg.get("page_set") and pg.get("page_exists") else "No", "Sí" if pg.get("page_visible") else "No",
                                "Bloques" if pg.get("block_present") else ("Shortcode" if pg.get("shortcode_present") else "—")] for pg in ss["pages"]]))
    if inv.get("pasarelas"):
        tablas.append(c.tabla("Pasarelas de pago", ["Pasarela", "Habilitada", "Modo"],
                              [[g.get("title") or g.get("id"), "Sí" if g.get("enabled") else "No",
                                {True: "Prueba", False: "REAL"}.get(en_modo_prueba(g), "No se pudo saber")] for g in inv["pasarelas"]]))
    if inv.get("zonas"):
        tablas.append(c.tabla("Zonas de envío", ["Zona", "Métodos habilitados"],
                              [[z.get("name"), ", ".join(m.get("title") for m in z.get("metodos") or [] if m.get("enabled")) or "ninguno"] for z in inv["zonas"]]))
    if inv.get("cupones"):
        tablas.append(c.tabla("Cupones", ["Código", "Tipo", "Importe", "Vence", "Usos"],
                              [[cu.get("code"), cu.get("discount_type"), cu.get("amount"), (cu.get("date_expires") or "—")[:10],
                                f'{cu.get("usage_count") or 0}/{cu.get("usage_limit") or "∞"}'] for cu in inv["cupones"]]))
    if inv.get("webhooks"):
        tablas.append(c.tabla("Webhooks", ["Nombre", "Evento", "Estado", "Destino"],
                              [[w.get("name"), w.get("topic"), w.get("status"), w.get("delivery_url")] for w in inv["webhooks"]]))
    n_viejos = sum(1 for p in plugins if p.get("version_latest") and _version(p["version_latest"]) > _version(p.get("version"))) \
        or sum(1 for p in inv.get("cli_plugins") or [] if p.get("update") == "available")
    indicadores = [{"etiqueta": "Productos revisados", "valor": len(prods), "tono": "", "detalle": "REST API" if inv.get("system_status") else "Store API pública"},
                   {"etiqueta": "Productos con problemas", "valor": n_prob, "tono": "bad" if n_prob else "ok", "detalle": "precio, stock, imagen, impuestos"},
                   {"etiqueta": "Plugins desactualizados", "valor": n_viejos, "tono": "warn" if n_viejos else "ok", "detalle": f"de {len(plugins or inv.get('cli_plugins') or [])}"}]
    if tema:
        indicadores.append({"etiqueta": "Templates desactualizados", "valor": len(over), "tono": "bad" if over else "ok", "detalle": "sobrescritos por el tema"})
    return indicadores, tablas, n_prob


def main(argv=None):
    c.preparar_consola()
    ap = argparse.ArgumentParser(description="Relevamiento funcional de QA de un sitio WordPress / WooCommerce (solo lectura).")
    ap.add_argument("--sitio", help="URL del sitio (o WORDPRESS_URL del .env)")
    ap.add_argument("--historia", default="")
    ap.add_argument("--producto", default="", help="URL de una ficha de producto para revisar (si no, la primera del catálogo)")
    ap.add_argument("--max-productos", type=int, default=300)
    ap.add_argument("--wp-cli", action="store_true", help="consultar actualizaciones y cron con WP-CLI (WORDPRESS_RUTA_LOCAL o WORDPRESS_WP_CLI)")
    ap.add_argument("--confirmar", action="store_true")
    args = ap.parse_args(argv)

    env = c.leer_env("WORDPRESS_", "WOOCOMMERCE_")
    base = c.normalizar_url(args.sitio or env.get("WORDPRESS_URL") or "")
    if not base:
        c.salir("Falta el sitio: pasalo con --sitio https://mi-tienda.example.com o poné WORDPRESS_URL en el .env.")
    c.autorizar(base, env)
    ck, cs = (env.get("WOOCOMMERCE_CONSUMER_KEY") or "").strip(), (env.get("WOOCOMMERCE_CONSUMER_SECRET") or "").strip()
    c.confirmar(f"Vas a relevar el sitio WordPress {base} (solo lectura{'; con la REST API de WooCommerce' if ck and cs else ''}).", args.confirmar)

    inv, errores = {}, {}
    print(f"[wordpress] REST API {base}/wp-json …", file=sys.stderr)
    raiz = c.http(base + "/wp-json/", headers={"Accept": "application/json"}, timeout=25)
    info = raiz.json() if raiz.ok else None
    if not isinstance(info, dict):
        errores["wp-json"] = f"HTTP {raiz.status or raiz.error}: la REST API no responde (¿enlaces permanentes simples o deshabilitada?)"
        info = {}
    ns = info.get("namespaces") or []
    inv["nombre"] = info.get("name")
    inv["modulos"] = sorted({v for k, v in NAMESPACES.items() if any(n == k or n.startswith(k + "/") for n in ns)})
    inv["woocommerce"] = any(n.startswith("wc/") for n in ns)
    feed = c.http(base + "/feed/", timeout=15)
    m = re.search(r"<generator>https?://wordpress\.org/\?v=([\d.]+)</generator>", feed.texto or "")
    inv["version_publica"] = m.group(1) if m else None

    publicos = productos_store(base, args.max_productos) if inv["woocommerce"] else []
    if ck and cs and inv["woocommerce"]:
        for clave, ruta in (("system_status", "system_status"), ("pasarelas", "payment_gateways"), ("cupones", "coupons?per_page=100"),
                            ("webhooks", "webhooks?per_page=100"), ("ajustes", "settings/general")):
            print(f"[wordpress] WooCommerce · {clave} …", file=sys.stderr)
            d, err = wc(base, ck, cs, ruta)
            inv[clave] = d
            if err:
                errores[clave] = err
        zonas, err = wc(base, ck, cs, "shipping/zones")
        if err:
            errores["zonas"] = err
        inv["zonas"] = []
        for z in zonas or []:
            metodos, err = wc(base, ck, cs, f'shipping/zones/{int(z.get("id", 0))}/methods')
            inv["zonas"].append({"id": z.get("id"), "name": z.get("name"), "metodos": metodos or []})
        print("[wordpress] WooCommerce · productos …", file=sys.stderr)
        v3, err = productos_v3(base, ck, cs, args.max_productos)
        if err:
            errores["productos"] = err
        calcula = {a.get("id"): a.get("value") for a in inv.get("ajustes") or []}.get("woocommerce_calc_taxes") == "yes"
        inv["productos_norm"] = [normalizar_v3(p, calcula) for p in v3] if v3 else [normalizar_store(p) for p in publicos]
    else:
        inv["productos_norm"] = [normalizar_store(p) for p in publicos]

    if args.wp_cli:
        cli = env.get("WORDPRESS_WP_CLI") or ("wp" if shutil.which("wp") else "")
        ruta = env.get("WORDPRESS_RUTA_LOCAL") or ""
        if not cli:
            errores["wp-cli"] = "No se encontró WP-CLI (https://wp-cli.org) ni WORDPRESS_WP_CLI en el .env."
        else:
            print("[wordpress] WP-CLI …", file=sys.stderr)
            for clave, cmd in (("cli_plugins", ["plugin", "list", "--format=json", "--fields=name,status,version,update,update_version,auto_update"]),
                               ("cli_core_update", ["core", "check-update", "--format=json"]),
                               ("cli_cron", ["cron", "event", "list", "--format=json", "--fields=hook,next_run_gmt"]),
                               ("cli_acciones_fallidas", ["action-scheduler", "action", "list", "--status=failed", "--format=count"])):
                d, err = wp_cli(cli, ruta, cmd)
                inv[clave] = d or []
                if err:
                    errores[clave] = err

    url_producto = args.producto or next((p.get("url") for p in inv["productos_norm"] if p.get("url")), "")
    paginas = [url_producto] + [f'{base}/?page_id={int(pg["page_id"])}' for pg in (inv.get("system_status") or {}).get("pages") or []
                                if str(pg.get("page_id") or "").isdigit() and int(pg["page_id"]) > 0][:5]
    print(f"[wordpress] Vidriera {base} …", file=sys.stderr)
    chequeos, hallazgos_vid, _ = c.chequear_vidriera(base, PATRONES_ERROR, paginas + [f"{base}/?s=a"])
    ch_p, h_p = c.chequear_producto(url_producto)
    chequeos += ch_p + [{"chequeo": "REST API (/wp-json)", "estado": "ok" if not errores.get("wp-json") else "aviso", "detalle": f'{len(ns)} namespace(s)'},
                        {"chequeo": "Catálogo público (Store API)", "estado": "ok" if publicos else ("aviso" if inv["woocommerce"] else "info"),
                         "detalle": f"{len(publicos)} producto(s)" if publicos else ("sin productos" if inv["woocommerce"] else "sin WooCommerce")}]

    hallazgos, sugerencias = hallazgos_y_sugerencias(inv)
    hallazgos = c.ordenar(hallazgos_vid + h_p + hallazgos)
    indicadores, tablas, n_prob = tablas_e_indicadores(inv, base)
    envr = (inv.get("system_status") or {}).get("environment") or {}
    datos = {"historia": args.historia or None, "plataforma": "wordpress",
             "tienda": {"url": base, "nombre": inv.get("nombre") or re.sub(r"^https?://", "", base),
                        "version": f'WordPress {envr.get("wp_version") or inv.get("version_publica") or "?"}'
                                   + (f' · WooCommerce {envr["version"]}' if envr.get("version") else ""),
                        "ambiente": "—"},
             "vidriera": {"chequeos": chequeos}, "inventario": {k: v for k, v in inv.items() if k != "productos_norm"},
             "indicadores": indicadores, "tablas": tablas, "hallazgos": hallazgos, "sugerencias": sugerencias,
             "resumen": {"productos": len(inv["productos_norm"]), "productos_con_problemas": n_prob}, "errores": errores}
    c.guardar("wordpress", datos, c.carpeta_salida("wordpress", args.historia, base))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Relevamiento de QA de una tienda Shopify AUTORIZADA (solo lectura).

Uso (desde la raíz del repo):
    python herramientas/ecommerce/shopify.py --tienda https://mi-tienda.myshopify.com [--historia HU-001]
        [--producto https://.../products/remera] [--max-productos 250] [--theme-check] [--confirmar]

Qué hace:
- Verifica que la vidriera esté en ECOMMERCE_URLS_AUTORIZADAS del .env.
- Vidriera pública (sin credenciales): chequeos comunes (páginas clave, robots, sitemap, 404), si la tienda está protegida con contraseña, el tema publicado (Shopify.theme),
  errores de Liquid y traducciones faltantes a la vista, las políticas legales (reembolso, privacidad,
  términos, envíos), el catálogo público (/products.json), el carrito (/cart.js) y una ficha de producto.
- Admin API GraphQL (opcional, con SHOPIFY_ADMIN_TOKEN de una app personalizada con alcances de LECTURA):
  la tienda (plan, si es de desarrollo, monedas, impuestos), temas, productos con variantes y stock,
  ubicaciones, mercados, webhooks, códigos de descuento, perfiles de envío y los alcances del token.
  Solo consultas: cualquier "mutation" se rechaza antes de enviarse.
- Theme Check (opcional, --theme-check): corre `shopify theme check` sobre el código del tema
  (SHOPIFY_TEMA_RUTA) con la CLI de Shopify.
- Calcula hallazgos y sugerencias de prueba y deja en output/shopify/<historia o host>/: shopify.json e
  informe-shopify.html (la corrida anterior pasa a historial/).

No crea pedidos, clientes, productos ni descuentos; no instala apps ni cambia el tema.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _comun as c  # noqa: E402

API_VERSION = "2026-07"
PATRONES_ERROR = [("Error de Liquid", r"Liquid (?:syntax )?error"), ("Traducción faltante", r"[Tt]ranslation missing:"),
                  ("Error de Liquid", r"Could not find asset snippets/")]
POLITICAS = {"refund-policy": "reembolso", "privacy-policy": "privacidad", "terms-of-service": "términos del servicio",
             "shipping-policy": "envíos"}
ALCANCES_PELIGROSOS = re.compile(r"^write_")

# clave: lista de alternativas (si la primera falla por el esquema de la versión de la API, se prueba la siguiente)
CONSULTAS = {
    "tienda": ["""{ shop { name myshopifyDomain primaryDomain { url host sslEnabled } currencyCode enabledPresentmentCurrencies
                 ianaTimezone weightUnit taxesIncluded taxShipping checkoutApiSupported setupRequired
                 plan { partnerDevelopment shopifyPlus publicDisplayName } shopPolicies { type url } } }""",
               """{ shop { name myshopifyDomain primaryDomain { url host sslEnabled } currencyCode enabledPresentmentCurrencies
                 ianaTimezone taxesIncluded checkoutApiSupported plan { partnerDevelopment shopifyPlus displayName } } }"""],
    "temas": ["{ themes(first: 30) { nodes { id name role updatedAt } } }"],
    "ubicaciones": ["{ locations(first: 30) { nodes { name isActive fulfillsOnlineOrders } } }"],
    "mercados": ["{ markets(first: 30) { nodes { name handle status type } } }",
                 "{ markets(first: 30) { nodes { name handle enabled primary } } }"],
    "webhooks": ["{ webhookSubscriptions(first: 100) { nodes { topic uri } } }",
                 "{ webhookSubscriptions(first: 100) { nodes { topic endpoint { __typename ... on WebhookHttpEndpoint { callbackUrl } } } } }"],
    "descuentos": ["""{ codeDiscountNodes(first: 100) { nodes { codeDiscount { __typename
                     ... on DiscountCodeBasic { title status startsAt endsAt usageLimit appliesOncePerCustomer }
                     ... on DiscountCodeBxgy { title status startsAt endsAt usageLimit }
                     ... on DiscountCodeFreeShipping { title status startsAt endsAt usageLimit } } } } }"""],
    "envios": ["{ deliveryProfiles(first: 20) { nodes { name default activeMethodDefinitionsCount zoneCountryCount } } }",
               "{ deliveryProfiles(first: 20) { nodes { name default } } }"],
    "alcances": ["{ currentAppInstallation { accessScopes { handle } } }"],
}
CONSULTA_PRODUCTOS = """query($cursor: String) { products(first: 100, after: $cursor) { pageInfo { hasNextPage endCursor }
  nodes { title handle status totalInventory tracksInventory onlineStoreUrl featuredMedia { id } seo { description }
          variants(first: 50) { nodes { sku price compareAtPrice inventoryQuantity inventoryPolicy } } } } }"""


def graphql(dominio, token, version, consulta, variables=None, intentos=3):
    """(data, error). Solo consultas: una mutation no se envía."""
    if re.search(r"\bmutation\b", consulta, re.I):
        raise ValueError("solo consultas de lectura: las mutations no se envían")
    url = f"https://{dominio}/admin/api/{version}/graphql.json"
    cuerpo = json.dumps({"query": consulta, "variables": variables or {}})
    for i in range(intentos):
        r = c.http(url, "POST", {"Content-Type": "application/json", "Accept": "application/json", "X-Shopify-Access-Token": token}, cuerpo, timeout=40)
        if r.error:
            return None, r.error
        d = r.json() or {}
        errores = d.get("errors")
        if r.status == 429 or (isinstance(errores, list) and any((e.get("extensions") or {}).get("code") == "THROTTLED" for e in errores)):
            time.sleep(2 * (i + 1))
            continue
        if r.status in (401, 403):
            return None, f"HTTP {r.status}: el token no es válido o le falta el alcance de lectura"
        if errores:
            msg = errores if isinstance(errores, str) else "; ".join(str(e.get("message")) for e in errores)
            return d.get("data"), msg[:300]
        return d.get("data"), None
    return None, "la API respondió THROTTLED varias veces (límite de consultas)"


def consultar(dominio, token, version, alternativas):
    err = None
    for q in alternativas:
        data, err = graphql(dominio, token, version, q)
        if data and not err:
            return data, None
    return None, err


def productos_admin(dominio, token, version, maximo):
    salida, cursor, err = [], None, None
    while len(salida) < maximo:
        data, err = graphql(dominio, token, version, CONSULTA_PRODUCTOS, {"cursor": cursor})
        if not data or not data.get("products"):
            break
        prods = data["products"]
        salida += prods.get("nodes") or []
        if not (prods.get("pageInfo") or {}).get("hasNextPage"):
            break
        cursor = prods["pageInfo"]["endCursor"]
    return salida[:maximo], err


def productos_publicos(base, maximo):
    salida, pagina = [], 1
    while len(salida) < maximo and pagina <= 10:
        r = c.http(f"{base}/products.json?limit=250&page={pagina}", headers={"Accept": "application/json"}, timeout=30)
        prods = (r.json() or {}).get("products") if r.ok else None
        if not prods:
            break
        salida += prods
        pagina += 1
    return salida[:maximo]


def _num(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def normalizar_admin(p):
    vs = ((p.get("variants") or {}).get("nodes")) or []
    return {"titulo": p.get("title"), "ref": p.get("handle"), "activo": p.get("status") == "ACTIVE",
            "precios": [_num(v.get("price")) for v in vs], "comparar": [_num(v.get("compareAtPrice")) for v in vs],
            "imagen": bool(p.get("featuredMedia")), "stock": p.get("totalInventory"), "controla_stock": p.get("tracksInventory"),
            "sigue_vendiendo": any(v.get("inventoryPolicy") == "CONTINUE" for v in vs), "variantes": len(vs),
            "sin_sku": sum(1 for v in vs if not (v.get("sku") or "").strip()),
            "seo": bool(((p.get("seo") or {}).get("description") or "").strip()), "publicado": bool(p.get("onlineStoreUrl"))}


def normalizar_publico(p):
    vs = p.get("variants") or []
    return {"titulo": p.get("title"), "ref": p.get("handle"), "activo": True,
            "precios": [_num(v.get("price")) for v in vs], "comparar": [_num(v.get("compare_at_price")) for v in vs],
            "imagen": bool(p.get("images")), "stock": None, "controla_stock": None, "sigue_vendiendo": None,
            "variantes": len(vs), "disponible": any(v.get("available") for v in vs), "sin_sku": 0, "seo": None, "publicado": True}


def tema_publico(html):
    m = re.search(r"Shopify\.theme\s*=\s*(\{.*?\});", html or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        nombre = re.search(r'"name"\s*:\s*"([^"]+)"', m.group(1))
        return {"name": nombre.group(1)} if nombre else None


def theme_check(ruta):
    cli = shutil.which("shopify")
    if not cli:
        return {"error": "No se encontró la CLI de Shopify (npm install --global @shopify/cli)."}
    if not ruta or not Path(ruta).is_dir():
        return {"error": f"La carpeta del tema no existe: {ruta!r} (SHOPIFY_TEMA_RUTA o --tema-ruta)."}
    try:
        p = subprocess.run([cli, "theme", "check", "--path", str(ruta), "--output", "json"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
    except subprocess.TimeoutExpired:
        return {"error": "theme check tardó más de 10 minutos"}
    inicio = min([i for i in (p.stdout.find("["), p.stdout.find("{")) if i >= 0] or [-1])
    try:
        datos = json.loads(p.stdout[inicio:]) if inicio >= 0 else None
    except ValueError:
        datos = None
    if datos is None:
        return {"error": (p.stderr or p.stdout or "sin salida").strip()[:300]}
    archivos = datos if isinstance(datos, list) else datos.get("files") or []
    ofensas = []
    for a in archivos:
        for o in a.get("offenses") or []:
            sev = o.get("severity")
            ofensas.append({"archivo": a.get("path"), "regla": o.get("check"), "mensaje": (o.get("message") or "")[:200],
                            "linea": (o.get("start_row") if o.get("start_row") is not None else (o.get("start") or {}).get("line")),
                            "nivel": {0: "error", 1: "advertencia", 2: "info"}.get(sev, str(sev or "")).lower()})
    return {"ofensas": ofensas, "errores": sum(1 for o in ofensas if o["nivel"] == "error"),
            "advertencias": sum(1 for o in ofensas if o["nivel"] in ("advertencia", "warning"))}


def _url_webhook(w):
    return w.get("uri") or ((w.get("endpoint") or {}).get("callbackUrl")) or ""


def hallazgos_y_sugerencias(inv):
    h, s = [], []
    tienda = inv.get("tienda") or {}
    plan = tienda.get("plan") or {}
    if inv.get("password"):
        h.append({"severidad": "Baja", "area": "Vidriera", "texto": "La tienda está protegida con contraseña (/password): los chequeos públicos quedan limitados; para recorrerla, el agente entra con Playwright y la contraseña de la vidriera."})
    if plan and plan.get("partnerDevelopment") is False:
        h.append({"severidad": "Alta", "area": "Tienda", "texto": f"No es una tienda de desarrollo (plan {plan.get('publicDisplayName') or plan.get('displayName') or '?'}): los pedidos de prueba solo con la pasarela en modo de prueba (o Bogus Gateway) y con confirmación; después se cancelan y archivan."})
    if tienda.get("setupRequired"):
        h.append({"severidad": "Baja", "area": "Tienda", "texto": "Shopify marca que a la tienda le falta configuración inicial (setupRequired)."})
    if tienda.get("checkoutApiSupported") is False:
        h.append({"severidad": "Media", "area": "Checkout", "texto": "El plan no permite completar el checkout por API (checkoutApiSupported = false)."})

    for pol, nombre in POLITICAS.items():
        estado = (inv.get("politicas") or {}).get(pol)
        if estado is not None and estado != 200:
            h.append({"severidad": "Media" if pol != "shipping-policy" else "Baja", "area": "Legal",
                      "texto": f"La política de {nombre} no está publicada (/policies/{pol} → HTTP {estado}): se muestra en el pie del checkout y la exigen muchas pasarelas."})

    tema = inv.get("tema_publico") or {}
    if tema.get("role") and tema.get("role") != "main":
        h.append({"severidad": "Baja", "area": "Tema", "texto": f'La vidriera se está viendo con un tema que no es el publicado (role {tema.get("role")}).'})
    temas = inv.get("temas") or []
    dev = [t for t in temas if t.get("role") in ("DEVELOPMENT", "UNPUBLISHED")]
    if len(dev) >= 15:
        h.append({"severidad": "Baja", "area": "Tema", "texto": f"{len(dev)} temas sin publicar o de desarrollo (Shopify permite 20): conviene limpiar."})
    for t in temas:
        if t.get("role") == "MAIN":
            s.append({"area": "Tema", "elemento": t.get("name"), "prueba": f'Antes de publicar cambios del tema "{t.get("name")}", compararlo con su vista previa (pixel-perfect) y recorrer portada, colección, producto, carrito y búsqueda en mobile y desktop.'})

    tc = inv.get("theme_check") or {}
    if tc.get("errores"):
        h.append({"severidad": "Media", "area": "Tema", "texto": f'Theme Check: {tc["errores"]} error(es) y {tc.get("advertencias", 0)} advertencia(s) en el código del tema.'})

    hc, _, _ = c.analizar_catalogo(inv.get("productos_norm"))
    h += hc
    for p in c.agotados(inv.get("productos_norm"))[:5]:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": f'Producto agotado que no se vende sin stock: verificar que "Agregar al carrito" esté deshabilitado y diga "Agotado", y que no se pueda forzar por /cart/add.'})
    sobre = [p for p in inv.get("productos_norm") or [] if "sobreventa" in c.problemas_producto(p)][:3]
    for p in sobre:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": "Comprar el producto sin stock: confirmar con el negocio si la preventa es intencional y que el inventario quede negativo de forma controlada."})
    variantes = [p for p in inv.get("productos_norm") or [] if (p.get("variantes") or 0) > 1][:3]
    for p in variantes:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": "Elegir cada combinación de opciones: cambian precio, imagen, disponibilidad y la URL (?variant=); la combinación inexistente no se puede comprar."})

    for w in inv.get("webhooks") or []:
        url = _url_webhook(w)
        if url.startswith("http://"):
            h.append({"severidad": "Alta", "area": "Integraciones", "texto": f'El webhook {w.get("topic")} envía a {url} sin HTTPS.'})
        elif re.search(r"localhost|127\.0\.0\.1|ngrok|loca\.lt|trycloudflare", url):
            h.append({"severidad": "Media", "area": "Integraciones", "texto": f'El webhook {w.get("topic")} apunta a un túnel o máquina local ({url}): en un ambiente compartido se pierde cuando se apaga.'})
        s.append({"area": "Integraciones", "elemento": w.get("topic"), "prueba": f'Disparar el evento {w.get("topic")} y verificar que el receptor lo procese una sola vez (reintentos), valide la firma X-Shopify-Hmac-Sha256 y rechace un payload alterado.'})

    for d in inv.get("descuentos") or []:
        cd = d.get("codeDiscount") or {}
        if cd.get("status") == "ACTIVE":
            s.append({"area": "Descuentos", "elemento": cd.get("title"), "prueba": f'Aplicar "{cd.get("title")}" válido, en minúsculas, con espacios, vencido{", superando el límite de usos" if cd.get("usageLimit") else ""}, combinado con otro descuento y sobre un carrito que no cumple el mínimo; verificar el total, los impuestos y el envío.'})
        if cd.get("status") == "ACTIVE" and not cd.get("usageLimit") and not cd.get("endsAt"):
            h.append({"severidad": "Baja", "area": "Descuentos", "texto": f'El descuento "{cd.get("title")}" está activo sin límite de usos ni fecha de fin: confirmar que es intencional.'})

    for m in inv.get("mercados") or []:
        if m.get("status", "ACTIVE" if m.get("enabled", True) else "DRAFT") == "ACTIVE":
            s.append({"area": "Mercados", "elemento": m.get("name"), "prueba": f'Navegar como comprador del mercado "{m.get("name")}": moneda, redondeo de precios, impuestos incluidos o no, idioma, envíos disponibles y precio final en el checkout.'})
    monedas = tienda.get("enabledPresentmentCurrencies") or []
    if len(monedas) > 1:
        s.append({"area": "Mercados", "elemento": ", ".join(monedas[:8]), "prueba": "Cambiar de moneda en la vidriera y verificar que el carrito, el checkout y el correo de confirmación muestren la misma moneda e importe."})

    for e in inv.get("envios") or []:
        if e.get("activeMethodDefinitionsCount") == 0:
            h.append({"severidad": "Alta", "area": "Envíos", "texto": f'El perfil de envío "{e.get("name")}" no tiene métodos activos: sus productos no se pueden comprar con envío.'})
        s.append({"area": "Envíos", "elemento": e.get("name"), "prueba": f'Checkout con productos del perfil "{e.get("name")}" a una dirección dentro y fuera de sus zonas, con peso/valor en los límites de cada tarifa y con envío gratis.'})
    ubic = [u for u in inv.get("ubicaciones") or [] if u.get("isActive")]
    if ubic and not any(u.get("fulfillsOnlineOrders") for u in ubic):
        h.append({"severidad": "Alta", "area": "Inventario", "texto": "Ninguna ubicación activa despacha pedidos online."})
    if len(ubic) > 1:
        s.append({"area": "Inventario", "elemento": ", ".join(u.get("name") for u in ubic[:5]), "prueba": "Con stock en una sola ubicación, comprar y verificar de cuál se descuenta y si se ofrece retiro en tienda."})

    alcances = inv.get("alcances") or []
    escritura = [a for a in alcances if ALCANCES_PELIGROSOS.match(a)]
    if escritura:
        h.append({"severidad": "Baja", "area": "Token de QA", "texto": f'El token de QA tiene alcances de escritura ({", ".join(escritura[:8])}): para relevar alcanza con read_*. Conviene un token de solo lectura.'})

    s += [{"area": "Checkout", "elemento": "Pasarela de prueba", "prueba": "Con Bogus Gateway o el modo de prueba de Shopify Payments: pago aprobado, rechazado y con error; verificar el estado del pedido, el stock descontado y el correo de confirmación."},
          {"area": "Checkout", "elemento": "Invitado y cliente", "prueba": "Comprar como invitado y con cuenta de cliente: datos precargados, direcciones guardadas, historial de pedidos y correos."},
          {"area": "Checkout", "elemento": "Carrito", "prueba": "Agregar, cambiar cantidad (0, 1, máximo de stock, más que el stock), quitar y volver atrás: el contador del carrito y el subtotal tienen que coincidir con /cart.js."},
          {"area": "Correos", "elemento": "Notificaciones", "prueba": "Revisar con el verificador-correos la confirmación de pedido, envío, reembolso y carrito abandonado: variables reemplazadas, links y moneda."}]
    return c.ordenar(h), s


def tablas_e_indicadores(inv, base):
    tienda = inv.get("tienda") or {}
    plan = tienda.get("plan") or {}
    tema = inv.get("tema_publico") or {}
    _, filas_cat, n_prob = c.analizar_catalogo(inv.get("productos_norm"))
    tablas = []
    datos_tienda = [["URL", base], ["Nombre", tienda.get("name") or "—"], ["Dominio myshopify", tienda.get("myshopifyDomain") or "—"],
                    ["Plan", plan.get("publicDisplayName") or plan.get("displayName") or "—"],
                    ["Tienda de desarrollo", {True: "Sí", False: "No"}.get(plan.get("partnerDevelopment"), "—")],
                    ["Shopify Plus", {True: "Sí", False: "No"}.get(plan.get("shopifyPlus"), "—")],
                    ["Moneda", tienda.get("currencyCode") or inv.get("moneda_carrito") or "—"],
                    ["Monedas de presentación", ", ".join(tienda.get("enabledPresentmentCurrencies") or []) or "—"],
                    ["Impuestos incluidos en el precio", {True: "Sí", False: "No"}.get(tienda.get("taxesIncluded"), "—")],
                    ["Zona horaria", tienda.get("ianaTimezone") or "—"],
                    ["Tema publicado", f'{tema.get("name") or "—"}{" " + tema["schema_version"] if tema.get("schema_version") else ""}'],
                    ["Protegida con contraseña", "Sí" if inv.get("password") else "No"],
                    ["Admin API", f'versión {inv.get("api_version")}' if inv.get("admin") else "sin token (solo vidriera pública)"]]
    tablas.append(c.tabla("La tienda", ["Dato", "Valor"], datos_tienda))
    if filas_cat:
        tablas.append(c.tabla("Productos con problemas", ["Producto", "Handle", "Problemas"], filas_cat[:150], f"{n_prob} de {len(inv.get('productos_norm') or [])} revisados"))
    if inv.get("politicas"):
        tablas.append(c.tabla("Políticas legales", ["Política", "Estado"], [[POLITICAS[k], "Publicada" if v == 200 else f"HTTP {v}"] for k, v in inv["politicas"].items()]))
    if inv.get("temas"):
        tablas.append(c.tabla("Temas", ["Tema", "Rol", "Actualizado"], [[t.get("name"), t.get("role"), (t.get("updatedAt") or "")[:10]] for t in inv["temas"]]))
    if inv.get("mercados"):
        tablas.append(c.tabla("Mercados", ["Mercado", "Handle", "Estado"], [[m.get("name"), m.get("handle"), m.get("status") or ("Activo" if m.get("enabled") else "Inactivo")] for m in inv["mercados"]]))
    if inv.get("envios"):
        tablas.append(c.tabla("Perfiles de envío", ["Perfil", "General", "Métodos activos", "Países"], [[e.get("name"), "Sí" if e.get("default") else "No", e.get("activeMethodDefinitionsCount", "—"), e.get("zoneCountryCount", "—")] for e in inv["envios"]]))
    if inv.get("ubicaciones"):
        tablas.append(c.tabla("Ubicaciones", ["Ubicación", "Activa", "Despacha online"], [[u.get("name"), "Sí" if u.get("isActive") else "No", "Sí" if u.get("fulfillsOnlineOrders") else "No"] for u in inv["ubicaciones"]]))
    if inv.get("descuentos"):
        tablas.append(c.tabla("Códigos de descuento", ["Descuento", "Tipo", "Estado", "Desde", "Hasta", "Límite de usos"],
                              [[(d.get("codeDiscount") or {}).get("title"), (d.get("codeDiscount") or {}).get("__typename", "").replace("DiscountCode", ""),
                                (d.get("codeDiscount") or {}).get("status"), ((d.get("codeDiscount") or {}).get("startsAt") or "")[:10],
                                ((d.get("codeDiscount") or {}).get("endsAt") or "—")[:10], (d.get("codeDiscount") or {}).get("usageLimit") or "sin límite"] for d in inv["descuentos"]]))
    if inv.get("webhooks"):
        tablas.append(c.tabla("Webhooks", ["Evento", "Destino"], [[w.get("topic"), _url_webhook(w)] for w in inv["webhooks"]]))
    tc = inv.get("theme_check") or {}
    if tc.get("ofensas"):
        tablas.append(c.tabla("Theme Check", ["Nivel", "Regla", "Archivo", "Línea", "Mensaje"],
                              [[o["nivel"], o["regla"], o["archivo"], o.get("linea") or "", o["mensaje"]] for o in tc["ofensas"][:200]], f'{len(tc["ofensas"])} en total'))
    indicadores = [{"etiqueta": "Productos revisados", "valor": len(inv.get("productos_norm") or []), "tono": "", "detalle": "Admin API" if inv.get("admin") else "catálogo público"},
                   {"etiqueta": "Productos con problemas", "valor": n_prob, "tono": "bad" if n_prob else "ok", "detalle": "precio, stock, imagen, SEO"}]
    if tc and not tc.get("error"):
        indicadores.append({"etiqueta": "Theme Check", "valor": tc.get("errores", 0), "tono": "bad" if tc.get("errores") else "ok", "detalle": f'errores · {tc.get("advertencias", 0)} advertencias'})
    return indicadores, tablas, n_prob


def main(argv=None):
    c.preparar_consola()
    ap = argparse.ArgumentParser(description="Relevamiento de QA de una tienda Shopify (solo lectura).")
    ap.add_argument("--tienda", help="URL de la vidriera (o SHOPIFY_TIENDA_URL del .env)")
    ap.add_argument("--historia", default="")
    ap.add_argument("--producto", default="", help="URL de una ficha de producto para revisar (si no, la primera del catálogo)")
    ap.add_argument("--max-productos", type=int, default=250)
    ap.add_argument("--api-version", default="")
    ap.add_argument("--theme-check", action="store_true", help="correr shopify theme check sobre SHOPIFY_TEMA_RUTA")
    ap.add_argument("--tema-ruta", default="")
    ap.add_argument("--confirmar", action="store_true")
    args = ap.parse_args(argv)

    env = c.leer_env("SHOPIFY_")
    base = c.normalizar_url(args.tienda or env.get("SHOPIFY_TIENDA_URL") or "")
    if not base:
        c.salir("Falta la tienda: pasala con --tienda https://mi-tienda.myshopify.com o poné SHOPIFY_TIENDA_URL en el .env.")
    c.autorizar(base, env)
    dominio = (env.get("SHOPIFY_TIENDA") or "").strip().lower()
    token = (env.get("SHOPIFY_ADMIN_TOKEN") or "").strip()
    version = args.api_version or env.get("SHOPIFY_API_VERSION") or API_VERSION
    if token and not dominio:
        dominio = re.sub(r"^https?://", "", base).split("/")[0] if base.endswith(".myshopify.com") else ""
        if not dominio:
            print("[aviso] Hay SHOPIFY_ADMIN_TOKEN pero falta SHOPIFY_TIENDA (mi-tienda.myshopify.com): se releva solo la vidriera.", file=sys.stderr)
    if dominio and not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", dominio):
        c.salir(f"SHOPIFY_TIENDA tiene que ser el dominio myshopify (mi-tienda.myshopify.com), no {dominio!r}.")
    c.confirmar(f"Vas a relevar la tienda Shopify {base} (solo lectura{'; con la Admin API de ' + dominio if token and dominio else ''}).", args.confirmar)

    inv, errores = {"api_version": version, "admin": bool(token and dominio)}, {}
    print(f"[shopify] Vidriera {base} …", file=sys.stderr)
    pw = c.http(base + "/", timeout=20)
    inv["password"] = "/password" in (pw.url or "") or bool(re.search(r'<form[^>]+action="/password"', pw.texto or ""))
    inv["tema_publico"] = tema_publico(pw.texto)
    if not pw.error and "shopify" not in (pw.texto or "").lower() and "x-shopid" not in pw.headers and "powered-by" not in pw.headers:
        print("[aviso] La portada no parece de Shopify (sin cdn.shopify.com ni encabezados de Shopify).", file=sys.stderr)

    publicos = [] if inv["password"] else productos_publicos(base, args.max_productos)
    url_producto = args.producto or (f"{base}/products/{publicos[0]['handle']}" if publicos else "")
    chequeos, hallazgos_vid, _ = c.chequear_vidriera(base, PATRONES_ERROR, [url_producto, f"{base}/collections/all", f"{base}/cart", f"{base}/search?q=a"]
                                                     if not inv["password"] else [])
    ch_p, h_p = c.chequear_producto(url_producto) if not inv["password"] else ([], [])
    chequeos += ch_p
    hallazgos_vid += h_p
    inv["politicas"] = {} if inv["password"] else {k: c.http(f"{base}/policies/{k}", timeout=15).status for k in POLITICAS}
    carrito = c.http(base + "/cart.js", headers={"Accept": "application/json"}, timeout=15)
    inv["moneda_carrito"] = (carrito.json() or {}).get("currency") if carrito.ok else None
    chequeos.append({"chequeo": "Carrito (/cart.js)", "estado": "ok" if carrito.ok else "aviso", "detalle": f"HTTP {carrito.status or carrito.error}"})
    chequeos.append({"chequeo": "Catálogo público (/products.json)", "estado": "ok" if publicos else "aviso",
                     "detalle": f"{len(publicos)} producto(s)" if publicos else "no disponible (contraseña o deshabilitado)"})

    admin = []
    if inv["admin"]:
        for clave, alternativas in CONSULTAS.items():
            print(f"[shopify] Admin API · {clave} …", file=sys.stderr)
            data, err = consultar(dominio, token, version, alternativas)
            if err:
                errores[clave] = err
            data = data or {}
            if clave == "tienda":
                inv["tienda"] = data.get("shop") or {}
            elif clave == "temas":
                inv["temas"] = (data.get("themes") or {}).get("nodes") or []
            elif clave == "ubicaciones":
                inv["ubicaciones"] = (data.get("locations") or {}).get("nodes") or []
            elif clave == "mercados":
                inv["mercados"] = (data.get("markets") or {}).get("nodes") or []
            elif clave == "webhooks":
                inv["webhooks"] = (data.get("webhookSubscriptions") or {}).get("nodes") or []
            elif clave == "descuentos":
                inv["descuentos"] = (data.get("codeDiscountNodes") or {}).get("nodes") or []
            elif clave == "envios":
                inv["envios"] = (data.get("deliveryProfiles") or {}).get("nodes") or []
            elif clave == "alcances":
                inv["alcances"] = [a.get("handle") for a in ((data.get("currentAppInstallation") or {}).get("accessScopes") or [])]
        print("[shopify] Admin API · productos …", file=sys.stderr)
        admin, err = productos_admin(dominio, token, version, args.max_productos)
        if err:
            errores["productos"] = err
    inv["productos_norm"] = [normalizar_admin(p) for p in admin] if admin else [normalizar_publico(p) for p in publicos]

    if args.theme_check:
        print("[shopify] Theme Check …", file=sys.stderr)
        inv["theme_check"] = theme_check(args.tema_ruta or env.get("SHOPIFY_TEMA_RUTA"))
        if inv["theme_check"].get("error"):
            errores["theme_check"] = inv["theme_check"]["error"]

    hallazgos, sugerencias = hallazgos_y_sugerencias(inv)
    hallazgos = c.ordenar(hallazgos_vid + hallazgos)
    indicadores, tablas, n_prob = tablas_e_indicadores(inv, base)
    tienda = inv.get("tienda") or {}
    plan = tienda.get("plan") or {}
    datos = {"historia": args.historia or None, "plataforma": "shopify",
             "tienda": {"url": base, "nombre": tienda.get("name") or re.sub(r"^https?://", "", base),
                        "version": f'tema {(inv.get("tema_publico") or {}).get("name") or "—"}',
                        "ambiente": ("Desarrollo" if plan.get("partnerDevelopment") else "Tienda real") if plan else "—"},
             "vidriera": {"chequeos": chequeos}, "inventario": {k: v for k, v in inv.items() if k != "productos_norm"},
             "indicadores": indicadores, "tablas": tablas, "hallazgos": hallazgos, "sugerencias": sugerencias,
             "resumen": {"productos": len(inv["productos_norm"]), "productos_con_problemas": n_prob}, "errores": errores}
    c.guardar("shopify", datos, c.carpeta_salida("shopify", args.historia, base))
    return 0


if __name__ == "__main__":
    sys.exit(main())

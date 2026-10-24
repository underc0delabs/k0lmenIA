#!/usr/bin/env python3
"""
Relevamiento funcional de QA de una tienda VTEX AUTORIZADA (solo lectura).

Uso (desde la raíz del repo):
    python herramientas/ecommerce/vtex.py --tienda https://www.mi-tienda.com --cuenta micuenta
        [--historia HU-001] [--producto https://.../p] [--max-productos 300] [--sc 1] [--confirmar]

Qué hace:
- Verifica que la tienda esté en ECOMMERCE_URLS_AUTORIZADAS del .env.
- Vidriera pública: chequeos comunes (portada y páginas clave, robots, sitemap, 404, errores de la tienda o
  de VTEX IO a la vista) y datos estructurados de una ficha.
- Catalog System público (sin credenciales): el catálogo del canal de ventas (`/api/catalog_system/pub/
  products/search`) con SKUs, precio y disponibilidad (commertialOffer) — alcanza para analizar el catálogo.
- APIs de administración (opcional, con VTEX_APP_KEY/VTEX_APP_TOKEN de una app con alcances de SOLO LECTURA):
  canales de venta (trade policies), políticas de envío (SLAs) y promociones.
- Calcula hallazgos y sugerencias de prueba y deja en output/vtex/<historia o host>/: vtex.json e
  informe-vtex.html (la corrida anterior pasa a historial/).

Solo GET. No crea orderForms de compra, pedidos ni datos y no cambia configuración. La seguridad de la
tienda no se revisa acá (analista-seguridad, pentester-web).
"""
import argparse
import datetime
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _comun as c  # noqa: E402

PATRONES_ERROR = [("Error de la tienda", r"Internal Server Error|Something went wrong|503 Service"),
                  ("Error de VTEX IO", r"RenderRuntime|Failed to fetch|GraphQL error|react-error"),
                  ("Error de VTEX a la vista", r'"error"\s*:\s*\{|VtexIdclientAutCookie|Workspace .* not found')]


def _num(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _items(d):
    """Las APIs de VTEX devuelven una lista, o {"items": [...]} (paginado). Normaliza a lista."""
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        return d.get("items") or d.get("Items") or []
    return []


def api_host(cuenta, entorno):
    return f"https://{cuenta}.{entorno}.com.br"


def vtex_get(url, key=None, token=None, timeout=40):
    """GET público o, con AppKey/AppToken, de administración. (datos, error)."""
    headers = {"Accept": "application/json"}
    if key and token:
        headers["X-VTEX-API-AppKey"] = key
        headers["X-VTEX-API-AppToken"] = token
    r = c.http(url, headers=headers, timeout=timeout)
    if r.error:
        return None, r.error
    if r.status in (401, 403):
        return None, f"HTTP {r.status}: la app (AppKey/AppToken) no es válida o no tiene permiso de lectura"
    if r.status == 404:
        return None, "HTTP 404: el recurso no está disponible en esta cuenta"
    if not r.ok:
        return None, f"HTTP {r.status}: {(r.texto or '')[:160]}"
    d = r.json()
    return (d, None) if d is not None else (None, "respuesta no JSON")


def productos_pub(host, maximo, sc=None):
    """Catálogo público del canal de ventas, paginado de a 50 (límite de la API)."""
    salida, desde = [], 0
    sc_q = f"&sc={sc}" if sc else ""
    while len(salida) < maximo and desde < 2500:
        hasta = desde + 49
        d, err = vtex_get(f"{host}/api/catalog_system/pub/products/search?_from={desde}&_to={hasta}{sc_q}", timeout=30)
        lote = d if isinstance(d, list) else []
        if not lote:
            break
        salida += lote
        if len(lote) < 50:
            break
        desde += 50
    return salida[:maximo]


def normalizar(p, base):
    items = p.get("items") or []
    ofertas, tiene_img, sin_sku = [], False, 0
    for it in items:
        if it.get("images"):
            tiene_img = True
        refs = it.get("referenceId") or []
        if not any((r.get("Value") or "").strip() for r in refs):
            sin_sku += 1
        for s in it.get("sellers") or []:
            co = s.get("commertialOffer") or {}
            ofertas.append((_num(co.get("Price")), _num(co.get("ListPrice")), bool(co.get("IsAvailable")), int(co.get("AvailableQuantity") or 0)))
    precios_v = [o[0] for o in ofertas if o[0] is not None]
    precio_min = min(precios_v) if precios_v else None
    lp_rep = next((o[1] for o in ofertas if o[0] == precio_min), None)
    link = p.get("link") or (f'{base}/{p.get("linkText")}/p' if p.get("linkText") else None)
    return {"titulo": p.get("productName"), "ref": (p.get("productReference") or "").strip() or p.get("productId"),
            "activo": True, "url": link,
            "precios": [precio_min] if precio_min is not None else [],
            "comparar": [lp_rep],
            "imagen": tiene_img, "stock": sum(o[3] for o in ofertas), "controla_stock": True,
            "sigue_vendiendo": None, "variantes": len(items) or 1, "sin_sku": sin_sku,
            "impuesto": None, "seo": bool(p.get("metaTagDescription")),
            "publicado": any(o[2] for o in ofertas), "tipo": "sku multiple" if len(items) > 1 else "simple"}


def _fecha(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def hallazgos_y_sugerencias(inv, ahora=None):
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    h, s = [], []

    if inv.get("workspace") and inv["workspace"].lower() == "master":
        h.append({"severidad": "Media", "area": "Ambiente", "texto": "Estás relevando el workspace master (producción). Para QA conviene un workspace propio (qa--micuenta.myvtex.com), que es una copia aislada."})

    prods = inv.get("productos_norm") or []
    if inv.get("api_publica") and not prods:
        h.append({"severidad": "Alta", "area": "Catálogo", "texto": "El catálogo público no devolvió productos para el canal de ventas: nada para comprar (¿canal de ventas equivocado, catálogo sin indexar o productos sin trade policy?)."})

    canales = _items(inv.get("saleschannels"))
    activos = [t for t in canales if t.get("IsActive")]
    if inv.get("saleschannels") is not None and not activos:
        h.append({"severidad": "Alta", "area": "Canales de venta", "texto": "No hay ningún canal de ventas (trade policy) activo: la tienda no vende."})
    for t in activos[:6]:
        s.append({"area": "Canales de venta", "elemento": f'{t.get("Name")} ({t.get("Id")})',
                  "prueba": f'Comprar en el canal «{t.get("Name")}» ({t.get("CurrencyCode") or "?"}): precios, disponibilidad y checkout del canal; que un producto fuera de este canal no se pueda comprar acá.'})

    slas = _items(inv.get("shipping"))
    activos_sla = [x for x in slas if x.get("isActive", True)]
    if inv.get("shipping") is not None and not activos_sla:
        h.append({"severidad": "Alta", "area": "Envíos", "texto": "No hay ninguna política de envío (SLA) activa: no se puede completar una compra con envío."})
    for x in activos_sla[:6]:
        s.append({"area": "Envíos", "elemento": x.get("name") or x.get("id"),
                  "prueba": f'Checkout con la política de envío «{x.get("name") or x.get("id")}»: costo por región y peso, franjas de precio, envío gratis y recálculo al cambiar la dirección o el CEP/código postal.'})

    for pr in _items(inv.get("promotions")):
        activo = pr.get("isActive")
        fin = _fecha(pr.get("endDateUtc") or pr.get("endDate"))
        nombre = pr.get("name") or pr.get("idCalculatorConfiguration") or "?"
        if activo and fin and fin < ahora:
            h.append({"severidad": "Baja", "area": "Promociones", "texto": f'La promoción «{nombre}» está activa pero venció ({str(pr.get("endDateUtc") or pr.get("endDate"))[:10]}).'})
        elif activo:
            s.append({"area": "Promociones", "elemento": nombre, "prueba": f'Aplicar la promoción «{nombre}»: que se calcule sobre el carrito correcto, no se acumule con otra si no corresponde y respete fechas, canal y condiciones.'})

    hc, _, _ = c.analizar_catalogo(prods)
    h += hc
    for p in [p for p in prods if p.get("tipo") == "sku multiple"][:3]:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": "Producto con varios SKUs: cada SKU cambia precio, imagen, referencia y disponibilidad; un SKU sin stock o inexistente no se puede agregar."})
    for p in [p for p in prods if not p.get("publicado")][:3]:
        s.append({"area": "Catálogo", "elemento": p.get("titulo"), "prueba": "Producto que aparece en el catálogo pero figura sin disponibilidad: que no se pueda agregar al carrito ni comprar por la API del orderForm."})

    if inv.get("api_publica"):
        s += [{"area": "Checkout", "elemento": "orderForm", "prueba": "Flujo de compra completo (identificación, dirección, envío, pago) como invitado y con cuenta; que el total del orderForm cierre con el carrito, la pasarela, el pedido (OMS) y el correo; doble clic en pagar no duplica el pedido."},
              {"area": "Pagos", "elemento": "Condiciones de pago", "prueba": "Cada medio de pago en sandbox (aprobado, rechazado, 3-D Secure) y, si aplica, cuotas; el antifraude no rechaza una compra legítima de prueba. Nunca tarjetas reales."},
              {"area": "Correos", "elemento": "Transaccionales", "prueba": "Con el verificador-correos: confirmación, pago aprobado, factura/invoiced, enviado y cancelado; variables de la plantilla sin reemplazar y links."},
              {"area": "Permisos", "elemento": "Mi cuenta", "prueba": "Con el probador-permisos: un cliente ve solo sus pedidos y direcciones (no los de otro, ni cambiando el id en la API de OMS/Master Data)."},
              {"area": "Rendimiento", "elemento": "Catálogo y ficha", "prueba": "Con el auditor-rendimiento-web: portada, categoría con filtros, ficha y búsqueda; latencia del orderForm y del search; impacto de las apps de VTEX IO. Para carga, el performance-mapper."}]
    return c.ordenar(h), s


def tablas_e_indicadores(inv, base):
    prods = inv.get("productos_norm") or []
    _, filas_cat, n_prob = c.analizar_catalogo(prods)
    canales = _items(inv.get("saleschannels"))
    activos = [t for t in canales if t.get("IsActive")]
    slas = _items(inv.get("shipping"))
    promos = _items(inv.get("promotions"))
    datos = [["URL", base], ["Cuenta", inv.get("cuenta") or "—"], ["Workspace", inv.get("workspace") or "master"],
             ["Storefront", inv.get("storefront") or "—"],
             ["Canales de venta activos", str(len(activos)) + (f' de {len(canales)}' if canales else "") if inv.get("saleschannels") is not None else "—"],
             ["APIs de administración", "con AppKey/AppToken" if inv.get("api_admin") else "sin credenciales (catálogo público)"]]
    tablas = [c.tabla("La tienda", ["Dato", "Valor"], datos)]
    if filas_cat:
        tablas.append(c.tabla("Productos con problemas", ["Producto", "Referencia", "Problemas"], filas_cat[:150], f"{n_prob} de {len(prods)} revisados"))
    if canales:
        tablas.append(c.tabla("Canales de venta (trade policies)", ["Canal", "Id", "Moneda", "Activo"],
                              [[t.get("Name"), t.get("Id"), t.get("CurrencyCode"), "Sí" if t.get("IsActive") else "No"] for t in canales]))
    if slas:
        tablas.append(c.tabla("Políticas de envío (SLAs)", ["Política", "Activa"],
                              [[x.get("name") or x.get("id"), "Sí" if x.get("isActive", True) else "No"] for x in slas]))
    if promos:
        tablas.append(c.tabla("Promociones", ["Nombre", "Tipo", "Activa", "Vence"],
                              [[pr.get("name"), pr.get("type"), "Sí" if pr.get("isActive") else "No",
                                (str(pr.get("endDateUtc") or pr.get("endDate"))[:10] if (pr.get("endDateUtc") or pr.get("endDate")) else "—")] for pr in promos[:100]]))
    indicadores = [{"etiqueta": "Productos revisados", "valor": len(prods), "tono": "", "detalle": "Catalog System público"},
                   {"etiqueta": "Productos con problemas", "valor": n_prob, "tono": "bad" if n_prob else "ok", "detalle": "precio, imagen, SKU, tachado"},
                   {"etiqueta": "Canales de venta activos", "valor": len(activos), "tono": "bad" if (inv.get("saleschannels") is not None and not activos) else "ok", "detalle": f"de {len(canales)}" if canales else "sin credenciales"}]
    return indicadores, tablas, n_prob


def main(argv=None):
    c.preparar_consola()
    ap = argparse.ArgumentParser(description="Relevamiento funcional de QA de una tienda VTEX (solo lectura).")
    ap.add_argument("--tienda", help="URL del storefront (o VTEX_URL del .env)")
    ap.add_argument("--cuenta", default="", help="nombre de la cuenta VTEX (o VTEX_ACCOUNT); si no, se intenta deducir de la URL")
    ap.add_argument("--historia", default="")
    ap.add_argument("--producto", default="", help="URL de una ficha para revisar (si no, la primera del catálogo)")
    ap.add_argument("--max-productos", type=int, default=300)
    ap.add_argument("--sc", default="", help="canal de ventas para el catálogo público (sales channel)")
    ap.add_argument("--confirmar", action="store_true")
    args = ap.parse_args(argv)

    env = c.leer_env("VTEX_")
    base = c.normalizar_url(args.tienda or env.get("VTEX_URL") or "")
    if not base:
        c.salir("Falta la tienda: pasala con --tienda https://www.mi-tienda.com o poné VTEX_URL en el .env.")
    c.autorizar(base, env)

    host_url = urllib.parse.urlsplit(base).netloc
    cuenta = (args.cuenta or env.get("VTEX_ACCOUNT") or "").strip()
    if not cuenta:
        m = re.match(r"^([\w-]+)\.(?:vtexcommercestable|myvtex|vtexlocal)\.", host_url)
        cuenta = m.group(1) if m else ""
    entorno = (env.get("VTEX_ENVIRONMENT") or "vtexcommercestable").strip()
    key, token = (env.get("VTEX_APP_KEY") or "").strip(), (env.get("VTEX_APP_TOKEN") or "").strip()
    sc = (args.sc or env.get("VTEX_SALES_CHANNEL") or "").strip()
    c.confirmar(f"Vas a relevar la tienda VTEX {base}{' (cuenta ' + cuenta + ')' if cuenta else ''} (solo lectura{'; con las APIs de administración' if key and token else ''}).", args.confirmar)

    inv, errores = {"cuenta": cuenta or None, "workspace": (env.get("VTEX_WORKSPACE") or "master").strip(),
                    "api_publica": bool(cuenta), "api_admin": bool(cuenta and key and token)}, {}
    host = api_host(cuenta, entorno) if cuenta else None

    if host:
        print(f"[vtex] Catálogo público {host} …", file=sys.stderr)
        pub = productos_pub(host, args.max_productos, sc)
        inv["productos_norm"] = [normalizar(p, base) for p in pub]
        if not pub:
            errores["catalogo"] = "El catálogo público no devolvió productos (¿canal de ventas? probá --sc 1)."
        if key and token:
            for clave, ruta in (("saleschannels", "/api/catalog_system/pvt/saleschannel/list"),
                                ("shipping", "/api/logistics/pvt/shipping-policies?page=1&perPage=100"),
                                ("promotions", "/api/rnb/pvt/benefits/calculatorconfiguration")):
                print(f"[vtex] API · {clave} …", file=sys.stderr)
                d, err = vtex_get(host + ruta, key, token)
                inv[clave] = d
                if err:
                    errores[clave] = err
    else:
        inv["productos_norm"] = []
        errores["cuenta"] = "No se pudo determinar la cuenta VTEX: pasala con --cuenta o VTEX_ACCOUNT. Sin cuenta solo se releva la vidriera pública."

    # Vidriera pública
    url_producto = args.producto or next((p.get("url") for p in inv["productos_norm"] if p.get("url")), "")
    print(f"[vtex] Vidriera {base} …", file=sys.stderr)
    chequeos, hallazgos_vid, home = c.chequear_vidriera(base, PATRONES_ERROR, [url_producto] if url_producto else [])
    ch_p, h_p = c.chequear_producto(url_producto)
    txt = home.texto or ""
    if re.search(r"__RUNTIME__|vtex\.render-runtime|data-vtex", txt):
        inv["storefront"] = "Store Framework (VTEX IO)"
    elif re.search(r"faststore|@faststore", txt, re.I):
        inv["storefront"] = "FastStore"
    elif re.search(r"vtex", txt, re.I):
        inv["storefront"] = "VTEX (legacy/CMS Portal)"
    es_vtex = bool(inv.get("storefront")) or bool(cuenta)
    chequeos += ch_p + [{"chequeo": "VTEX detectado", "estado": "ok" if es_vtex else "aviso",
                         "detalle": inv.get("storefront") or ("cuenta " + cuenta if cuenta else "no se reconocieron señales de VTEX")},
                        {"chequeo": "Catálogo público (Catalog System)", "estado": "ok" if inv["productos_norm"] else ("aviso" if cuenta else "info"),
                         "detalle": f'{len(inv["productos_norm"])} producto(s)' if inv["productos_norm"] else ("sin productos" if cuenta else "sin cuenta")}]

    hallazgos, sugerencias = hallazgos_y_sugerencias(inv)
    hallazgos = c.ordenar(hallazgos_vid + h_p + hallazgos)
    indicadores, tablas, n_prob = tablas_e_indicadores(inv, base)
    datos = {"historia": args.historia or None, "plataforma": "vtex",
             "tienda": {"url": base, "nombre": cuenta or re.sub(r"^https?://", "", base),
                        "version": f"VTEX · {inv.get('storefront')}" if inv.get("storefront") else "VTEX",
                        "ambiente": inv.get("workspace") or "master"},
             "vidriera": {"chequeos": chequeos}, "inventario": {k: v for k, v in inv.items() if k != "productos_norm"},
             "indicadores": indicadores, "tablas": tablas, "hallazgos": hallazgos, "sugerencias": sugerencias,
             "resumen": {"productos": len(inv["productos_norm"]), "productos_con_problemas": n_prob}, "errores": errores}
    c.guardar("vtex", datos, c.carpeta_salida("vtex", args.historia, base))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Lo común a los relevamientos de e-commerce (shopify.py y wordpress.py):

- Autorización: solo se relevan URLs de ECOMMERCE_URLS_AUTORIZADAS del .env (mismo criterio que
  SEGURIDAD_URLS_AUTORIZADAS: el host tiene que coincidir y, si la entrada tiene ruta, la URL tiene que
  empezar con ella).
- HTTP de solo lectura (GET y, para GraphQL, POST de consultas sin mutaciones) con urllib, sin dependencias.
- Chequeos funcionales de la vidriera que valen para cualquier tienda: portada y páginas clave de la compra
  (carga y tiempo de respuesta), robots.txt y sitemap, página 404 real, errores de la plataforma a la vista
  (Liquid, PHP, plantillas) y datos estructurados de producto. La seguridad NO se revisa acá: es del
  analista-seguridad y del pentester-web.
- Guardado: <plataforma>.json en output/<plataforma>/<historia o host>/, la corrida anterior pasa a
  historial/ (últimas 5) y se genera el informe HTML (scripts/generar_informe_ecommerce.py).

Formato de lo que devuelven los chequeos:
    hallazgo   = {"severidad": "Crítica|Alta|Media|Baja", "area": "...", "texto": "..."}
    sugerencia = {"area": "...", "elemento": "...", "prueba": "..."}
    chequeo    = {"chequeo": "...", "estado": "ok|aviso|falla|info", "detalle": "..."}
"""
import datetime
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
AGENTE_HTTP = "k0lmenIA-QA/1.0 (relevamiento de solo lectura; +https://k0lmena.com)"
MAX_CUERPO = 3 * 1024 * 1024
ORDEN_SEV = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
LENTO_MS = 3000


def salir(msg, codigo=2):
    print(msg, file=sys.stderr)
    sys.exit(codigo)


def leer_env(*prefijos):
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _env import leer_env as _leer
    valores = _leer()
    valores.update({k: v for k, v in os.environ.items() if k.startswith(prefijos + ("ECOMMERCE_",))})
    return valores


def normalizar_url(url):
    url = (url or "").strip()
    if url and not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    p = urllib.parse.urlsplit(url)
    if not p.netloc:
        return ""
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))


def lista_autorizadas(env):
    return [normalizar_url(u) for u in re.split(r"[,\s]+", env.get("ECOMMERCE_URLS_AUTORIZADAS", "")) if u.strip()]


def esta_autorizada(url, lista):
    """True si el host de `url` coincide con una entrada y su ruta empieza con la de esa entrada."""
    u = urllib.parse.urlsplit(normalizar_url(url))
    for a in lista:
        p = urllib.parse.urlsplit(a)
        if u.netloc == p.netloc and (u.path + "/").startswith((p.path or "") + "/"):
            return True
    return False


def autorizar(url, env):
    lista = lista_autorizadas(env)
    if not lista:
        salir("No hay tiendas autorizadas. Agregá en el .env de la raíz:\n"
              "  ECOMMERCE_URLS_AUTORIZADAS=https://mi-tienda-qa.example.com\n"
              "(solo tiendas propias o con permiso, idealmente de prueba/staging).")
    if not esta_autorizada(url, lista):
        salir(f"{url} no está en ECOMMERCE_URLS_AUTORIZADAS del .env. Solo se relevan tiendas autorizadas.")


def confirmar(texto, ya_confirmado):
    if ya_confirmado:
        return
    print(texto)
    if input("¿Confirmás? [s/N] ").strip().lower() not in ("s", "si", "sí", "y", "yes"):
        salir("Cancelado.", 1)


class Respuesta:
    def __init__(self, status=0, headers=None, texto="", url="", ms=0, error=None):
        self.status, self.headers, self.texto, self.url, self.ms, self.error = status, headers or {}, texto, url, ms, error

    @property
    def ok(self):
        return 200 <= self.status < 300

    def json(self):
        try:
            return json.loads(self.texto)
        except ValueError:
            return None


def http(url, metodo="GET", headers=None, cuerpo=None, timeout=25, usuario=None, clave=None):
    """Request de solo lectura. Nunca lanza: los errores de red quedan en Respuesta.error."""
    if metodo not in ("GET", "HEAD", "POST"):
        raise ValueError("solo GET/HEAD/POST de consulta")
    h = {"User-Agent": AGENTE_HTTP, "Accept": "*/*"}
    h.update(headers or {})
    if usuario is not None:
        import base64
        h["Authorization"] = "Basic " + base64.b64encode(f"{usuario}:{clave or ''}".encode()).decode()
    datos = cuerpo.encode("utf-8") if isinstance(cuerpo, str) else cuerpo
    req = urllib.request.Request(url, data=datos, headers=h, method=metodo)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            texto = r.read(MAX_CUERPO).decode(r.headers.get_content_charset() or "utf-8", "replace")
            return Respuesta(r.status, {k.lower(): v for k, v in r.headers.items()}, texto, r.geturl(), int((time.monotonic() - t0) * 1000))
    except urllib.error.HTTPError as ex:
        try:
            texto = ex.read(MAX_CUERPO).decode("utf-8", "replace")
        except Exception:
            texto = ""
        return Respuesta(ex.code, {k.lower(): v for k, v in (ex.headers or {}).items()}, texto, ex.geturl() or url,
                         int((time.monotonic() - t0) * 1000))
    except Exception as ex:  # DNS, TLS, timeout, conexión rechazada
        return Respuesta(0, {}, "", url, int((time.monotonic() - t0) * 1000), f"{type(ex).__name__}: {ex}"[:300])


def unir(base, ruta):
    return base.rstrip("/") + "/" + ruta.lstrip("/")


def ordenar(hallazgos):
    hallazgos.sort(key=lambda x: ORDEN_SEV.get(x.get("severidad"), 9))
    return hallazgos


# ------------------------------------------------------------------ chequeos públicos de la vidriera
_JSONLD = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)


def tipos_jsonld(html):
    tipos = set()
    for bloque in _JSONLD.findall(html or ""):
        try:
            d = json.loads(bloque.strip())
        except ValueError:
            continue
        pila = [d]
        while pila:
            x = pila.pop()
            if isinstance(x, list):
                pila.extend(x)
            elif isinstance(x, dict):
                t = x.get("@type")
                tipos.update(t if isinstance(t, list) else [t] if t else [])
                pila.extend(v for k, v in x.items() if k in ("@graph", "offers", "mainEntity", "itemListElement"))
    return tipos


def robots_bloquea_todo(texto):
    """True si el grupo de User-agent: * tiene "Disallow: /" (toda la tienda fuera de los buscadores)."""
    agentes, en_reglas, bloquea = set(), False, False
    for linea in (texto or "").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if ":" not in linea:
            continue
        clave, valor = (x.strip() for x in linea.split(":", 1))
        clave = clave.lower()
        if clave == "user-agent":
            if en_reglas:
                agentes, en_reglas = set(), False
            agentes.add(valor)
        elif clave in ("disallow", "allow"):
            en_reglas = True
            if "*" in agentes and clave == "disallow" and valor == "/":
                bloquea = True
    return bloquea


def errores_en_html(html, patrones):
    """[(nombre, fragmento)] de los patrones de error del servidor que aparecen en el HTML."""
    texto = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", html or "", flags=re.S | re.I)
    texto = re.sub(r"<[^>]+>", " ", texto)
    salida = []
    for nombre, rx in patrones:
        m = re.search(rx, texto)
        if m:
            salida.append((nombre, re.sub(r"\s+", " ", texto[max(0, m.start() - 30):m.end() + 90]).strip()))
    return salida


def chequear_vidriera(base, patrones_error=(), paginas_extra=()):
    """Chequeos públicos comunes. Devuelve (chequeos, hallazgos, home) — home es la Respuesta de la portada."""
    ch, h = [], []
    home = http(base + "/")
    if home.error or not home.status:
        ch.append({"chequeo": "Portada", "estado": "falla", "detalle": f"No responde: {home.error}"})
        h.append({"severidad": "Crítica", "area": "Vidriera", "texto": f"La portada {base}/ no responde ({home.error})."})
        return ch, h, home
    if home.status >= 500:
        h.append({"severidad": "Crítica", "area": "Vidriera", "texto": f"La portada devuelve {home.status}."})
    ch.append({"chequeo": "Portada", "estado": "ok" if home.ok else "falla",
               "detalle": f"HTTP {home.status} en {home.ms} ms{' (redirige a ' + home.url + ')' if home.url.rstrip('/') != base else ''}"})
    if home.ms > LENTO_MS:
        h.append({"severidad": "Media", "area": "Rendimiento", "texto": f"La portada tarda {home.ms} ms en responder (más de {LENTO_MS} ms): conviene medir con el auditor-rendimiento-web."})

    # robots y sitemap
    rob = http(base + "/robots.txt", timeout=15)
    bloquea = rob.ok and robots_bloquea_todo(rob.texto)
    ch.append({"chequeo": "robots.txt", "estado": "aviso" if bloquea else ("ok" if rob.ok else "aviso"),
               "detalle": "bloquea toda la tienda (Disallow: /)" if bloquea else ("existe" if rob.ok else f"HTTP {rob.status or rob.error}")})
    if bloquea:
        h.append({"severidad": "Baja", "area": "SEO", "texto": "robots.txt bloquea toda la tienda (Disallow: /). Está bien en staging; en producción la saca de los buscadores."})
    sm_url = (re.search(r"(?im)^sitemap:\s*(\S+)", rob.texto or "") or [None, base + "/sitemap.xml"])[1] if rob.ok else base + "/sitemap.xml"
    sm = http(sm_url, timeout=20)
    ok_sm = sm.ok and "<" in sm.texto[:200]
    ch.append({"chequeo": "Sitemap", "estado": "ok" if ok_sm else "aviso", "detalle": sm_url if ok_sm else f"{sm_url}: HTTP {sm.status or sm.error}"})
    if not ok_sm:
        h.append({"severidad": "Baja", "area": "SEO", "texto": f"No se encontró el sitemap ({sm_url})."})

    # 404 real
    r404 = http(f"{base}/k0lmenia-no-existe-{uuid.uuid4().hex[:8]}", timeout=15)
    ch.append({"chequeo": "Página 404", "estado": "ok" if r404.status == 404 else "aviso", "detalle": f"HTTP {r404.status or r404.error}"})
    if r404.status == 200:
        h.append({"severidad": "Baja", "area": "SEO", "texto": "Una URL que no existe devuelve 200 en vez de 404 (soft 404)."})
    elif r404.status >= 500:
        h.append({"severidad": "Media", "area": "Vidriera", "texto": f"Una URL que no existe devuelve {r404.status} (error del servidor en vez de 404)."})

    # Páginas clave de la compra y errores a la vista (portada y páginas extra)
    vistos = set()
    paginas = [(base + "/", home)]
    for u in paginas_extra:
        if u:
            r = http(u, timeout=20)
            paginas.append((u, r))
            ruta = urllib.parse.urlsplit(u).path or "/"
            ch.append({"chequeo": f"Página {ruta}", "estado": "ok" if r.ok else "falla", "detalle": f"HTTP {r.status or r.error} en {r.ms} ms"})
            if r.status >= 500 or r.error:
                h.append({"severidad": "Alta", "area": "Vidriera", "texto": f"{u} no carga (HTTP {r.status or r.error})."})
    for url, resp in paginas:
        for nombre, frag in errores_en_html(resp.texto, patrones_error):
            if (nombre, url) in vistos:
                continue
            vistos.add((nombre, url))
            h.append({"severidad": "Alta", "area": "Vidriera", "texto": f"{nombre} a la vista en {url}: «{frag[:160]}»"})
    ch.append({"chequeo": "Errores del servidor a la vista", "estado": "falla" if vistos else "ok",
               "detalle": f"{len(vistos)} encontrado(s)" if vistos else "ninguno en las páginas revisadas"})
    return ch, h, home


def chequear_producto(url_producto):
    """Datos estructurados de una ficha de producto (Product + Offer) y si responde."""
    ch, h = [], []
    if not url_producto:
        return ch, h
    r = http(url_producto, timeout=20)
    if not r.ok:
        ch.append({"chequeo": "Ficha de producto", "estado": "falla", "detalle": f"{url_producto}: HTTP {r.status or r.error}"})
        h.append({"severidad": "Alta", "area": "Catálogo", "texto": f"La ficha de producto {url_producto} no carga (HTTP {r.status or r.error})."})
        return ch, h
    tipos = tipos_jsonld(r.texto)
    ch.append({"chequeo": "Ficha de producto", "estado": "ok", "detalle": f"{url_producto} en {r.ms} ms"})
    tiene = "Product" in tipos
    ch.append({"chequeo": "Datos estructurados de producto", "estado": "ok" if tiene and "Offer" in tipos else "aviso",
               "detalle": ", ".join(sorted(t for t in tipos if isinstance(t, str))) or "sin JSON-LD"})
    if not tiene:
        h.append({"severidad": "Baja", "area": "SEO", "texto": "La ficha de producto no tiene datos estructurados Product (JSON-LD): no sale con precio y stock en Google Shopping."})
    elif "Offer" not in tipos and "AggregateOffer" not in tipos:
        h.append({"severidad": "Baja", "area": "SEO", "texto": "El JSON-LD Product de la ficha no trae offers (precio y disponibilidad)."})
    return ch, h


# ------------------------------------------------------------------ catálogo (mismo criterio en las tres plataformas)
# Cada plataforma traduce sus productos a este formato (lo que no sabe, lo deja en None):
#   {"titulo", "ref" (handle/id), "activo": bool|None, "precios": [float], "comparar": [float|None],
#    "imagen": bool|None, "stock": int|None, "controla_stock": bool|None, "sigue_vendiendo": bool|None,
#    "variantes": int, "sin_sku": int, "seo": bool|None, "publicado": bool|None, "impuesto": bool|None}
PROBLEMAS = {
    "precio_cero": ("Alta", "a la venta con precio 0"),
    "sobreventa": ("Media", "se sigue vendiendo sin stock (sobreventa)"),
    "sin_imagen": ("Media", "sin imagen"),
    "sin_impuesto": ("Media", "sin regla de impuestos"),
    "comparar_menor": ("Baja", "precio de comparación (tachado) menor o igual al precio"),
    "sin_sku": ("Baja", "variantes sin SKU con control de stock"),
    "no_publicado": ("Baja", "activo pero no publicado en la tienda online"),
    "sin_seo": ("Baja", "sin meta descripción"),
}


def problemas_producto(p):
    if p.get("activo") is False:
        return []
    out = []
    precios = [x for x in p.get("precios") or [] if x is not None]
    if precios and min(precios) <= 0:
        out.append("precio_cero")
    stock = p.get("stock")
    if p.get("controla_stock") and stock is not None and stock <= 0 and p.get("sigue_vendiendo"):
        out.append("sobreventa")
    if p.get("imagen") is False:
        out.append("sin_imagen")
    if p.get("impuesto") is False and precios and max(precios) > 0:
        out.append("sin_impuesto")
    if any(c is not None and pr is not None and 0 < c <= pr for pr, c in zip(p.get("precios") or [], p.get("comparar") or [])):
        out.append("comparar_menor")
    if p.get("controla_stock") and (p.get("sin_sku") or 0) > 0:
        out.append("sin_sku")
    if p.get("publicado") is False:
        out.append("no_publicado")
    if p.get("seo") is False:
        out.append("sin_seo")
    return out


def analizar_catalogo(productos, area="Catálogo"):
    """(hallazgos agregados por problema, filas para la tabla de productos con problemas, cantidad con problemas)."""
    por_problema, filas = {}, []
    for p in productos or []:
        ps = problemas_producto(p)
        for k in ps:
            por_problema.setdefault(k, []).append(p.get("titulo") or p.get("ref") or "?")
        if ps:
            filas.append([p.get("titulo") or "?", p.get("ref") or "", "; ".join(PROBLEMAS[k][1] for k in ps)])
    h = []
    for k, (sev, texto) in PROBLEMAS.items():
        nombres = por_problema.get(k)
        if nombres:
            h.append({"severidad": sev, "area": area,
                      "texto": f"{len(nombres)} producto(s) {texto}: {', '.join(nombres[:5])}{'…' if len(nombres) > 5 else ''}."})
    return h, filas, len(filas)


def agotados(productos):
    return [p for p in productos or [] if p.get("activo") is not False and p.get("controla_stock") and (p.get("stock") is not None and p["stock"] <= 0)
            and not p.get("sigue_vendiendo")]


def tabla(titulo, columnas, filas, sub=""):
    return {"titulo": titulo, "sub": sub, "columnas": columnas, "filas": filas}


# ------------------------------------------------------------------ guardado
def carpeta_salida(plataforma, historia, url):
    nombre = historia or urllib.parse.urlsplit(normalizar_url(url)).netloc or plataforma
    return PROYECTO / "output" / plataforma / re.sub(r"[^\w.-]+", "-", nombre)


def guardar(plataforma, datos, carpeta):
    datos.setdefault("generado", datetime.datetime.now().isoformat(timespec="seconds"))
    hall = datos.get("hallazgos") or []
    datos["resumen"] = dict({"hallazgos": len(hall), "criticos": sum(1 for x in hall if x.get("severidad") in ("Crítica", "Alta")),
                             "sugerencias": len(datos.get("sugerencias") or []),
                             "por_severidad": {s: sum(1 for x in hall if x.get("severidad") == s) for s in ORDEN_SEV}},
                            **(datos.get("resumen") or {}))
    carpeta.mkdir(parents=True, exist_ok=True)
    informe = f"informe-{plataforma}.html"
    try:
        sys.path.insert(0, str(RAIZ / "scripts"))
        import _historial
        _historial.archivar(carpeta, [f"{plataforma}.json", "analisis.json", informe], f"{plataforma}.json")
    except Exception as ex:
        print(f"[aviso] no se pudo archivar la corrida anterior: {ex}", file=sys.stderr)
    (carpeta / f"{plataforma}.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        import generar_informe_ecommerce
        generar_informe_ecommerce.generar(carpeta / f"{plataforma}.json", carpeta / informe)
        print(f"[{plataforma}] Informe: {carpeta / informe}", file=sys.stderr)
    except Exception as ex:
        print(f"[aviso] no se pudo generar el informe HTML: {ex}", file=sys.stderr)
    err = datos.get("errores") or {}
    print(f"[{plataforma}] {len(hall)} hallazgo(s), {len(datos.get('sugerencias') or [])} sugerencia(s) de prueba"
          f"{', ' + str(len(err)) + ' consulta(s) con error' if err else ''}.")
    print(f"[{plataforma}] Datos: {carpeta / (plataforma + '.json')}")
    return carpeta / f"{plataforma}.json"


def preparar_consola():
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass

"""Normalización de textos en conceptos (sin acentos, singular, sinónimos): la usan la selección de casos y la búsqueda de
bugs duplicados, para que las dos comparen igual."""
import re
import unicodedata

RE_KEY = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")

# Palabras que no dicen nada del área del cambio.
VACIAS = set("""a al algo ante antes asi como con contra cual cuando de del desde donde durante e el ella ellos en entre era es esa ese eso esta
este esto fue ha hay la las le les lo los mas me mi muy no nos o otra otro para pero poco por que se segun ser si sin sobre son su sus tambien
tiene todo tras un una uno unos y ya the and or of to in on for with from by at is are be this that it as an fix fixes fixed feat feature
chore refactor docs doc test tests spec specs style merge branch pull request pr wip update updates updated add added remove removed change
changes changed new old src app apps lib libs index main mod module modules component components page pages view views util utils helper
helpers common core shared base default js ts tsx jsx py java cs go rb php css scss html json yml yaml md vue svelte kt swift dart sql
config configs package lock dist build public assets static res resources internal pkg cmd service services controller controllers model
models repository repositories dto entity entities handler handlers route routes router api v1 v2 v3 get set put post delete patch init
caso casos cuando usuario debe deberia validar verificar ingresa hace clic click boton pantalla campo dado entonces dato datos paso pasos
given when then and but scenario feature background resultado esperado precondicion precondiciones prueba pruebas cp hu ca
function func def class const let var export import return async await public private static void null true false""".split())

# Sinónimos (español e inglés) → un concepto. Así "payment" en un archivo encuentra casos de "pago".
CONCEPTOS = {
    "login": "login signin sign-in logon ingreso ingresar iniciar sesion autenticacion auth authentication credencial credenciales",
    "logout": "logout signout salir cerrar desconectar",
    "registro": "register registration signup sign-up registro registrar alta crear-cuenta onboarding",
    "carrito": "cart carrito basket bolsa",
    "pago": "payment payments pay pago pagos pagar paga checkout cobro billing mercadopago stripe",
    "tarjeta": "card cards tarjeta tarjetas",
    "pedido": "order orders pedido pedidos orden ordenes compra compras purchase",
    "perfil": "profile perfil account cuenta cuentas settings ajustes preferencias",
    "contrasena": "password contrasena clave pass passwd reset recuperar recuperacion",
    "busqueda": "search busqueda buscar buscador filter filtro filtros finder",
    "producto": "product products producto productos item items articulo articulos catalog catalogo sku",
    "factura": "invoice invoices factura facturas facturacion receipt comprobante",
    "correo": "email mail correo emails mails smtp",
    "notificacion": "notification notifications notificacion notificaciones alerta alertas push",
    "inicio": "home inicio landing portada dashboard tablero",
    "admin": "admin administracion backoffice",
    "reporte": "report reports reporte reportes informe informes export exportar",
    "descuento": "discount descuento descuentos coupon cupon cupones promo promocion promociones voucher",
    "envio": "shipping envio envios delivery entrega entregas despacho",
    "stock": "stock inventory inventario existencias",
    "precio": "price prices precio precios tarifa tarifas cotizacion",
    "contacto": "contact contacto contactos soporte support",
    "navegacion": "menu nav navbar navigation navegacion header encabezado footer sidebar",
    "usuario": "user users usuario usuarios cliente clientes customer customers",
    "permiso": "permission permissions permiso permisos rol roles role acl",
    "archivo": "upload uploads archivo archivos adjunto adjuntos file files subir",
}
SINONIMO = {}
for _c, _ws in CONCEPTOS.items():
    for _w in _ws.split():
        SINONIMO[_w] = _c


def _sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _raiz(t):
    if t in SINONIMO:
        return SINONIMO[t]
    for suf in ("es", "s"):
        if len(t) > 4 and t.endswith(suf) and t[: -len(suf)] in SINONIMO:
            return SINONIMO[t[: -len(suf)]]
    if len(t) > 5 and t.endswith("es"):
        t = t[:-2]
    elif len(t) > 4 and t.endswith("s"):
        t = t[:-1]
    return SINONIMO.get(t, t)


def tokens(texto):
    """Texto (o ruta de archivo, o nombreEnCamelCase) → conceptos normalizados."""
    texto = RE_KEY.sub(" ", str(texto or ""))  # las keys (PROJ-55) cuentan como historias, no como palabras
    texto = re.sub(r"([a-z])([A-Z])", r"\1 \2", texto)
    texto = _sin_acentos(texto.lower())
    salida = []
    for t in re.split(r"[^a-z0-9ñ]+", texto):
        if len(t) < 3 or t.isdigit() or t in VACIAS:
            continue
        r = _raiz(t)
        if r not in VACIAS and len(r) >= 3:
            salida.append(r)
    return salida

#!/usr/bin/env python3
"""
Informes en español e inglés: cada informe tiene una carpeta por idioma y un acceso que abre el elegido,

    unidad/informe.html      acceso (abre es/ o en/ según la banderita que elegiste; español por defecto)
    unidad/es/informe.html   español
    unidad/en/informe.html   inglés

con una banderita en cada informe para pasar de uno al otro. Lo usan _estilos_reporte.page y todos los generadores.

Cómo se arma la versión en inglés:
- **Lo que escribe el agente** (resumen, hallazgos, recomendaciones…): el analisis.json trae un bloque "en" con
  las mismas claves e IDs y los textos en inglés; localizar(analisis) lo mezcla. Si falta, queda el español.
- **Lo que pone el generador** (títulos, columnas, estados, leyendas, frases con números): se traduce al final
  con el diccionario de scripts/i18n/en/*.json. Los números, fechas e IDs (HU-001, CP-API-003, 12, 3,5, 10:30)
  son comodines: la clave "{n} de {n} casos" sirve para cualquier cantidad.

Uso en un generador:
    from _i18n import escribir_bilingue, localizar
    escribir_bilingue(salida, lambda: construir_html(localizar(analisis)))   # es/<salida>, en/<salida> y el acceso

Para completar el diccionario: K0LMENIA_I18N_AUDITORIA=archivo.txt guarda ahí cada texto de la versión en inglés
que quedó en español (ya convertido en clave, con {n}); se traduce y se suma a scripts/i18n/en/<grupo>.json.
"""
import html as _html
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path

IDIOMAS = ("es", "en")
DIR_DICCIONARIOS = Path(__file__).resolve().parent / "i18n"
_estado = {"idioma": "es"}
_cache = {}

# Comodines: IDs (HU-001, CP-API-003, BUG-12, FI-01), números con decimales o separadores, horas y fechas por partes.
_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b|(?<![A-Za-z0-9])\d+(?:[.,:/]\d+)*(?![A-Za-z0-9])")
# Lo que parece español (solo para la auditoría): acentos, ñ, ¿¡ o palabras muy frecuentes.
_ESPANOL = re.compile(r"[áéíóúñ¿¡]|\b(de|del|la|las|los|el|que|con|para|por|sin|una|uno|en|y|se|sus?|al|es|son|hay|está|más)\b", re.I)


def idioma_actual():
    return _estado["idioma"]


@contextmanager
def idioma(codigo):
    if codigo not in IDIOMAS:
        raise ValueError(f"idioma desconocido: {codigo}")
    anterior = _estado["idioma"]
    _estado["idioma"] = codigo
    try:
        yield
    finally:
        _estado["idioma"] = anterior


def diccionario(codigo="en"):
    """Todas las entradas de scripts/i18n/<codigo>/*.json (cada archivo, un grupo de generadores)."""
    if codigo not in _cache:
        datos = {}
        for archivo in sorted((DIR_DICCIONARIOS / codigo).glob("*.json")):
            datos.update(json.loads(archivo.read_text(encoding="utf-8")))
        _cache[codigo] = datos
    return _cache[codigo]


def clave(texto):
    """(clave con {n}, valores en orden) de un texto."""
    valores = _TOKEN.findall(texto)
    return _TOKEN.sub("{n}", texto), valores


def _rellenar(plantilla, valores):
    partes = plantilla.split("{n}")
    if len(partes) - 1 != len(valores):
        return None
    salida = partes[0]
    for v, resto in zip(valores, partes[1:]):
        salida += v + resto
    return salida


def t(texto, codigo=None):
    """Traduce un texto de la interfaz al idioma actual (o al indicado). Sin traducción, lo devuelve igual."""
    codigo = codigo or _estado["idioma"]
    if codigo == "es" or not texto or not isinstance(texto, str):
        return texto
    m = re.match(r"^(\s*)(.*?)(\s*)$", texto, re.S)
    ini, nucleo, fin = m.groups()
    if not nucleo:
        return texto
    traducido = _buscar(nucleo, diccionario(codigo))
    if traducido is None:
        _auditar(clave(nucleo)[0])
        return texto
    return ini + traducido + fin


_PREFIJO = re.compile(r"^([^\wÁÉÍÓÚáéíóúÑñ¿¡(\[\"'“]+)(.+)$", re.S)
_SEPARADORES = (" — ", " · ", " | ", ": ")


def _buscar(nucleo, d, profundidad=0):
    """Traducción exacta, con comodines, sin un símbolo inicial (✓, ▲, !), sin ":" final o por partes (" — ", " · ")."""
    if nucleo in d:
        return d[nucleo]
    if profundidad == 0 and re.search(r"\s{2,}|\n", nucleo):  # espacios o saltos internos de más
        compacto = re.sub(r"\s+", " ", nucleo)
        if compacto in d:
            return d[compacto]
    k, valores = clave(nucleo)
    if valores and k in d:
        traducido = _rellenar(d[k], valores)
        if traducido is not None:
            return traducido
    if profundidad > 2:
        return None
    if "\n" in nucleo:  # tooltips de varias líneas ("fecha\nMétrica: n"): línea por línea
        lineas = nucleo.split("\n")
        traducidas = [_buscar(x.strip(), d, profundidad + 1) if x.strip() else None for x in lineas]
        if any(x is not None for x in traducidas):
            return "\n".join(x if x is not None else orig for x, orig in zip(traducidas, lineas))
    m = _PREFIJO.match(nucleo)
    if m:
        resto = _buscar(m.group(2).strip(), d, profundidad + 1)
        if resto is not None:
            return m.group(1) + resto
    if nucleo.endswith(":") and len(nucleo) > 1:
        sin = _buscar(nucleo[:-1].rstrip(), d, profundidad + 1)
        if sin is not None:
            return sin + ":"
    for sep in _SEPARADORES:
        if sep in nucleo:
            partes = nucleo.split(sep)
            traducidas = [_buscar(x.strip(), d, profundidad + 1) if x.strip() else None for x in partes]
            if any(x is not None for x in traducidas):
                return sep.join(x if x is not None else orig for x, orig in zip(traducidas, partes))
    return None


def _auditar(k):
    archivo = os.environ.get("K0LMENIA_I18N_AUDITORIA")
    if not archivo or not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]{3}", k) or not _ESPANOL.search(k):
        return
    try:
        with open(archivo, "a", encoding="utf-8") as f:
            f.write(k.replace("\n", " ") + "\n")
    except OSError:
        pass


_ATRIBUTOS = re.compile(r'(\s(?:title|placeholder|aria-label|alt|data-tip|data-nav)=")([^"]*)(")')
_BLOQUES = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>|<code\b.*?</code>|<pre\b.*?</pre>)", re.S | re.I)
_TEXTO = re.compile(r"(^|>)([^<>]+)(?=<|$)")


def _traducir_fragmento(fragmento, codigo):
    def nodo(m):
        crudo = m.group(2)
        if not crudo.strip():
            return m.group(0)
        return m.group(1) + _html.escape(t(_html.unescape(crudo), codigo), quote=False)

    def atributo(m):
        return m.group(1) + _html.escape(t(_html.unescape(m.group(2)), codigo)) + m.group(3)

    return _ATRIBUTOS.sub(atributo, _TEXTO.sub(nodo, fragmento))


def traducir_html(documento, codigo=None):
    """Traduce los textos y atributos visibles de un HTML (no toca scripts, estilos ni bloques de código)."""
    codigo = codigo or _estado["idioma"]
    if codigo == "es":
        return documento
    partes = _BLOQUES.split(documento)
    return "".join(p if _BLOQUES.fullmatch(p) else _traducir_fragmento(p, codigo) for p in partes)


def _mezclar(base, extra):
    if isinstance(base, dict) and isinstance(extra, dict):
        out = dict(base)
        for k, v in extra.items():
            out[k] = _mezclar(base.get(k), v) if k in base else v
        return out
    if isinstance(base, list) and isinstance(extra, list):
        con_id = all(isinstance(x, dict) and "id" in x for x in extra) and all(isinstance(x, dict) for x in base)
        if con_id:
            por_id = {x["id"]: x for x in extra}
            return [_mezclar(x, por_id[x.get("id")]) if x.get("id") in por_id else x for x in base]
        return [_mezclar(b, extra[i]) if i < len(extra) else b for i, b in enumerate(base)]
    return extra if extra not in (None, "") else base


def _sin_traducciones(obj):
    if isinstance(obj, dict):
        return {k: _sin_traducciones(v) for k, v in obj.items() if k not in IDIOMAS[1:]}
    if isinstance(obj, list):
        return [_sin_traducciones(x) for x in obj]
    return obj


def localizar(obj, codigo=None):
    """El analisis.json (o cualquier dato) en el idioma actual: en inglés, mezcla su bloque "en" (mismas claves; las
    listas de objetos se emparejan por "id" y, si no tienen, por posición). Los valores de las escalas (Alta,
    Aprobado…) no hace falta traducirlos en "en": los traduce el diccionario al armar el HTML."""
    codigo = codigo or _estado["idioma"]

    def loc(x):
        if isinstance(x, list):
            return [loc(y) for y in x]
        if not isinstance(x, dict):
            return x
        base = {k: loc(v) for k, v in x.items() if k not in IDIOMAS[1:]}
        extra = x.get(codigo) if codigo != "es" else None
        # También vale un bloque "en" dentro de cada ítem de una lista (cada caso, cada hallazgo).
        return _mezclar(base, loc(extra)) if isinstance(extra, dict) else base

    return loc(obj)


# Estructura en disco: cada informe tiene una carpeta por idioma y un archivo de acceso que abre el elegido.
#   unidad/informe.html          acceso: abre es/ o en/ según el idioma que elegiste con la banderita
#   unidad/es/informe.html       español
#   unidad/en/informe.html       inglés
# La evidencia (capturas/, videos/…) y los JSON quedan en la unidad, compartidos por los dos idiomas.
CLAVE_PREFERENCIA = "k0-idioma"  # localStorage: el idioma que eligió la persona (lo guarda la banderita)


def idioma_de(ruta):
    """'es' o 'en' si el HTML está en la carpeta de un idioma; None si es un acceso o un informe viejo."""
    nombre = Path(ruta).parent.name
    return nombre if nombre in IDIOMAS else None


def ruta_acceso(ruta):
    """unidad/es/informe.html -> unidad/informe.html (el archivo de acceso)."""
    ruta = Path(ruta)
    return ruta.parent.parent / ruta.name if idioma_de(ruta) else ruta


def ruta_idioma(ruta, codigo):
    """unidad/informe.html (o unidad/<otro idioma>/informe.html) -> unidad/<codigo>/informe.html"""
    ruta = ruta_acceso(ruta)
    return ruta.parent / codigo / ruta.name


def ruta_es(ruta):
    return ruta_idioma(ruta, "es")


def ruta_en(ruta):
    return ruta_idioma(ruta, "en")


def es_version_en(ruta):
    return idioma_de(ruta) == "en"


# URLs relativas de src/href/poster (no anclas, ni absolutas, ni con esquema: http:, data:, file:, mailto:…).
_URL_RELATIVA = re.compile(r'(\s(?:src|href|poster)=")(?!#|/|[A-Za-z][\w+.-]*:)([^"]+)(")')
_SCRIPTS = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>)", re.S | re.I)


def reubicar(documento, prefijo="../"):
    """El HTML se arma con rutas relativas a la unidad; como queda un nivel más adentro (es/ o en/), cada ruta
    relativa (evidencia, historial, otros informes) suma "../". No toca scripts ni estilos."""
    partes = _SCRIPTS.split(documento)
    return "".join(p if _SCRIPTS.fullmatch(p) else
                   _URL_RELATIVA.sub(lambda m: m.group(1) + prefijo + m.group(2) + m.group(3), p) for p in partes)


def html_acceso(nombre_archivo, titulo="k0lmenIA"):
    """El archivo de acceso: abre la versión del idioma elegido (español si no se eligió ninguno)."""
    destino = json.dumps(nombre_archivo)
    archivo = _html.escape(nombre_archivo)
    script = ("<script>(function(){var l='es';try{l=localStorage.getItem('" + CLAVE_PREFERENCIA + "')||'es';}catch(e){}"
              "if(l!=='en')l='es';location.replace(l+'/'+encodeURIComponent(" + destino + ")+location.hash);})();</script>")
    return ("<!doctype html>\n<html lang=\"es\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><meta name=\"color-scheme\" content=\"dark\">"
            f"<title>{_html.escape(titulo)}</title>{script}</head>"
            "<body style=\"background:#0E0C09;color:#F4EFE6;font-family:system-ui,sans-serif;padding:32px\">"
            "<p>Abriendo el informe… / Opening the report…</p>"
            f"<p><a style=\"color:#F9B006\" href=\"es/{archivo}\">Español</a> · "
            f"<a style=\"color:#F9B006\" href=\"en/{archivo}\">English</a></p></body></html>\n")


def escribir_bilingue(ruta, render, encoding="utf-8"):
    """Arma el informe en los dos idiomas: unidad/es/<nombre>, unidad/en/<nombre> y el acceso unidad/<nombre>.
    render() devuelve el HTML con rutas relativas a la unidad (como siempre); se llama una vez por idioma (adentro,
    localizar() y page() saben cuál es). Devuelve (ruta en español, ruta en inglés)."""
    acceso = ruta_acceso(Path(ruta))
    escritas, documento = [], ""
    for codigo in IDIOMAS:
        with idioma(codigo):
            documento = render()
        destino = ruta_idioma(acceso, codigo)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(reubicar(documento), encoding=encoding)
        escritas.append(destino)
    titulo = re.search(r"<title>(.*?)</title>", documento, re.S)
    acceso.write_text(html_acceso(acceso.name, _html.unescape(titulo.group(1)) if titulo else "k0lmenIA"), encoding=encoding)
    return tuple(escritas)



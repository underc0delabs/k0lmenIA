#!/usr/bin/env python3
"""
Convierte colecciones de Bruno e Insomnia a Postman Collection v2.1 (lo que corre Newman).

Uso (desde la raíz del repo; en Mac/Linux, python3):
    python scripts/convertir_coleccion.py <origen> [--salida <carpeta>] [--environment <nombre>]

<origen> puede ser:
  - una colección de **Bruno**: la carpeta que tiene `bruno.json` (con sus `.bru`, subcarpetas y
    `environments/*.bru`);
  - un export de **Insomnia v4** (`.json` con `"_type": "export"`): requests, carpetas y environments;
  - un export de **Insomnia v5** (`.yaml`, `type: collection.insomnia.rest/5.0`, Insomnia 11+). Necesita
    PyYAML (`pip install pyyaml`); si no está, lo avisa.
  - una colección de **Postman**: se devuelve igual (no hace falta convertirla).

Deja en --salida (por defecto, la carpeta del origen) `<nombre>.postman_collection.json` y, si la
colección tiene environment, `<nombre>.postman_environment.json`. --environment elige cuál (Bruno: el
nombre del archivo de environments/ sin `.bru`; Insomnia: el nombre del sub-environment). Si hay uno
solo, se usa ese.

Qué convierte:
  - Requests (método, URL, headers, query y path params, autenticación bearer, basic y API key) y
    carpetas, en el orden de la colección.
  - Bodies JSON, texto, XML, form-urlencoded, multipart (sin archivos) y **GraphQL** (query + variables,
    modo graphql de Postman, que Newman corre igual).
  - Variables: `{{ _.var }}` (Insomnia) y `{{var}}` (Bruno) quedan como `{{var}}` de Postman.
  - Bruno: `assert` → `pm.test` (eq, neq, gt, gte, lt, lte, in, notIn, contains, notContains, length,
    matches, notMatches, startsWith, endsWith, between, isEmpty, isNotEmpty, isNull, isUndefined,
    isDefined, isTruthy, isFalsy, isJson, isNumber, isString, isBoolean, isArray); `vars:pre-request`
    y `vars:post-response`; `script:pre-request`, `script:post-response` y `tests` con un adaptador
    (`res`, `req`, `bru`, `test`, `expect` sobre `pm`).
  - Insomnia: `preRequestScript` y `afterResponseScript` (su API `insomnia.*` es la misma que `pm.*`).

Lo que no se puede convertir (template tags `{% ... %}` de Insomnia, archivos en multipart, auth
OAuth2/AWS/Digest, `bru.runRequest`, unit tests de Insomnia, …) **no se pierde en silencio**: queda en la
lista de advertencias que imprime el script y devuelve `convertir()`.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ESQUEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
METODOS = ("get", "post", "put", "patch", "delete", "options", "head", "connect", "trace")
# Bloques de un .bru cuyo contenido es texto libre (no clave: valor).
BLOQUES_TEXTO = {"body:json", "body:text", "body:xml", "body:graphql", "body:graphql:vars", "body:sparql",
                 "script:pre-request", "script:post-response", "tests", "docs"}


class Conversion:
    def __init__(self, formato, coleccion, environment=None, advertencias=None):
        self.formato = formato
        self.coleccion = coleccion
        self.environment = environment
        self.advertencias = advertencias or []


# --------------------------------------------------------------------------- comunes

def detectar_formato(ruta):
    """'bruno' | 'insomnia4' | 'insomnia5' | 'postman' | None."""
    ruta = Path(ruta)
    if ruta.is_dir():
        return "bruno" if (ruta / "bruno.json").exists() else None
    if ruta.name == "bruno.json":
        return "bruno"
    if not ruta.is_file():
        return None
    texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
    if ruta.suffix.lower() in (".yaml", ".yml"):
        return "insomnia5" if re.search(r"^type:\s*['\"]?collection\.insomnia\.rest/5", texto, re.M) else None
    try:
        datos = json.loads(texto)
    except ValueError:
        return None
    if isinstance(datos, dict):
        if datos.get("_type") == "export" and isinstance(datos.get("resources"), list):
            return "insomnia4"
        if "item" in datos and "info" in datos:
            return "postman"
    return None


def variables(texto, avisos=None, donde=""):
    """Normaliza las variables al formato de Postman: {{ _.x }} / {{ x }} / {{process.env.X}} → {{x}}."""
    if not isinstance(texto, str):
        return texto
    if avisos is not None and "{%" in texto:
        avisos.append(f"{donde}: tiene template tags de Insomnia ({{% ... %}}) que Postman no entiende; quedaron "
                      "tal cual. Reemplazalos por una variable o un script.")
    if avisos is not None and re.search(r"\{\{\s*process\.env\.", texto):
        avisos.append(f"{donde}: usa {{{{process.env.X}}}}; quedó como {{{{X}}}}. Definila en el environment o con --env-var.")
    texto = re.sub(r"\{\{\s*_\[\s*['\"]([^'\"]+)['\"]\s*\]\s*\}\}", r"{{\1}}", texto)
    texto = re.sub(r"\{\{\s*_\.([\w.\-]+)\s*\}\}", r"{{\1}}", texto)
    texto = re.sub(r"\{\{\s*process\.env\.([\w.\-]+)\s*\}\}", r"{{\1}}", texto)
    return re.sub(r"\{\{\s*([$\w.\-]+)\s*\}\}", r"{{\1}}", texto)


def _header(nombre, valor, activo=True):
    h = {"key": nombre, "value": valor}
    if not activo:
        h["disabled"] = True
    return h


def _auth_bearer(token):
    return {"type": "bearer", "bearer": [{"key": "token", "value": token, "type": "string"}]}


def _auth_basic(usuario, clave):
    return {"type": "basic", "basic": [{"key": "username", "value": usuario, "type": "string"},
                                       {"key": "password", "value": clave, "type": "string"}]}


def _auth_apikey(clave, valor, en="header"):
    return {"type": "apikey", "apikey": [{"key": "key", "value": clave, "type": "string"},
                                         {"key": "value", "value": valor, "type": "string"},
                                         {"key": "in", "value": "query" if en in ("query", "queryparams") else "header",
                                          "type": "string"}]}


def _evento(tipo, lineas):
    return {"listen": tipo, "script": {"type": "text/javascript", "exec": lineas}}


def _con_query(url, params):
    """Agrega los query params activos a la URL si todavía no los trae."""
    activos = [(k, v) for k, v, activo in params if activo]
    if not activos or "?" in url:
        return url
    return url + "?" + "&".join(f"{k}={v}" for k, v in activos)


def _environment(nombre, valores):
    return {"name": nombre, "values": [{"key": k, "value": v, "enabled": True} for k, v in valores.items()],
            "_postman_variable_scope": "environment"}


def _aplanar(datos, prefijo=""):
    """{"a": {"b": 1}} → {"a.b": "1"} (los environments de Insomnia admiten objetos anidados)."""
    plano = {}
    for k, v in (datos or {}).items():
        clave = f"{prefijo}{k}"
        if isinstance(v, dict):
            plano.update(_aplanar(v, clave + "."))
        else:
            plano[clave] = v if isinstance(v, str) else json.dumps(v) if isinstance(v, (list, bool)) or v is None else str(v)
    return plano


def _coleccion(nombre, items, origen, auth=None, variables_coleccion=None):
    col = {"info": {"name": nombre, "schema": ESQUEMA,
                    "description": f"Convertida desde {origen} con scripts/convertir_coleccion.py."},
           "item": items}
    if auth:
        col["auth"] = auth
    if variables_coleccion:
        col["variable"] = [{"key": k, "value": v} for k, v in variables_coleccion.items()]
    return col


# --------------------------------------------------------------------------- Bruno

def parsear_bru(texto):
    """Lee un archivo .bru → {bloque: dict | list | str}. Los dict son {clave: (valor, activo)}."""
    bloques = {}
    lineas = texto.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lineas):
        m = re.match(r"^([A-Za-z][\w:\-]*)\s*([{\[])\s*$", lineas[i])
        if not m:
            i += 1
            continue
        nombre, abre = m.group(1), m.group(2)
        cierra = "}" if abre == "{" else "]"
        cuerpo = []
        i += 1
        while i < len(lineas) and lineas[i].rstrip() != cierra:
            cuerpo.append(lineas[i])
            i += 1
        i += 1
        if abre == "[":
            bloques[nombre] = [x.strip().rstrip(",") for x in cuerpo if x.strip()]
        elif nombre in BLOQUES_TEXTO:
            bloques[nombre] = "\n".join(x[2:] if x.startswith("  ") else x for x in cuerpo).strip("\n")
        else:
            bloques[nombre] = _pares_bru(cuerpo)
    return bloques


def _pares_bru(lineas):
    pares = {}
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        i += 1
        if not linea:
            continue
        m = re.match(r"^(~?)(\"[^\"]*\"|'[^']*'|[^:]+?)\s*:\s?(.*)$", linea)
        if not m:
            continue
        activo, clave, valor = not m.group(1), m.group(2).strip().strip("\"'"), m.group(3)
        if valor.strip() == "'''":  # valor multilínea
            partes = []
            while i < len(lineas) and lineas[i].strip() != "'''":
                partes.append(lineas[i].strip())
                i += 1
            i += 1
            valor = "\n".join(partes)
        pares[clave] = (valor.strip(), activo)
    return pares


ADAPTADOR_BRU = [
    "// Adaptado de Bruno por scripts/convertir_coleccion.py: res, req, bru, test y expect sobre pm.",
    "const bru = { setVar: (k, v) => pm.collectionVariables.set(k, v), getVar: (k) => pm.variables.get(k),",
    "  setEnvVar: (k, v) => pm.environment.set(k, v), getEnvVar: (k) => pm.environment.get(k),",
    "  getProcessEnv: (k) => pm.variables.get(k), interpolate: (s) => pm.variables.replaceIn(s),",
    "  setNextRequest: (n) => postman.setNextRequest(n) };",
    "const req = { getUrl: () => pm.request.url.toString(), setUrl: (u) => pm.request.url.update(u),",
    "  getMethod: () => pm.request.method, getHeader: (n) => pm.request.headers.get(n),",
    "  setHeader: (n, v) => pm.request.headers.upsert({ key: n, value: v }),",
    "  getBody: () => { try { return JSON.parse(pm.request.body.raw); } catch (e) { return pm.request.body && pm.request.body.raw; } },",
    "  setBody: (b) => pm.request.body.update(typeof b === 'string' ? b : JSON.stringify(b)) };",
    "const test = (nombre, fn) => pm.test(nombre, fn);",
    "const expect = pm.expect;",
]
ADAPTADOR_RES = [
    "const __cuerpo = (() => { try { return pm.response.json(); } catch (e) { return pm.response.text(); } })();",
    "const __headers = Object.fromEntries(pm.response.headers.all().map((h) => [h.key.toLowerCase(), h.value]));",
    "const res = { status: pm.response.code, statusText: pm.response.status, body: __cuerpo, headers: __headers,",
    "  responseTime: pm.response.responseTime, getStatus: () => pm.response.code, getBody: () => __cuerpo,",
    "  getHeader: (n) => __headers[String(n).toLowerCase()], getHeaders: () => __headers,",
    "  getResponseTime: () => pm.response.responseTime };",
]


def _valor_js(texto):
    """El valor de un assert de Bruno como literal de JavaScript."""
    t = texto.strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", t):
        return t
    if t in ("true", "false", "null", "undefined"):
        return t
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'`":
        t = t[1:-1]
    if "{{" in t:
        return f"pm.variables.replaceIn({json.dumps(t)})"
    return json.dumps(t)


def _assert_bru(lhs, regla, avisos, donde):
    """Una línea de assert de Bruno ('res.status', 'eq 200') → pm.test, o None si no se reconoce."""
    m = re.match(r"^(\w+)\s*(.*)$", regla.strip())
    if not m:
        avisos.append(f"{donde}: no entendí el assert '{lhs}: {regla}'; no se convirtió.")
        return None
    op, arg = m.group(1), m.group(2)
    v = _valor_js(arg) if arg else None
    lista = lambda: "[" + ", ".join(_valor_js(x) for x in arg.split(",") if x.strip()) + "]"  # noqa: E731
    ops = {
        "eq": f"expect({lhs}).to.eql({v})", "neq": f"expect({lhs}).to.not.eql({v})",
        "gt": f"expect({lhs}).to.be.above({v})", "gte": f"expect({lhs}).to.be.at.least({v})",
        "lt": f"expect({lhs}).to.be.below({v})", "lte": f"expect({lhs}).to.be.at.most({v})",
        "in": f"expect({lhs}).to.be.oneOf({lista()})", "notIn": f"expect({lhs}).to.not.be.oneOf({lista()})",
        "contains": f"expect({lhs}).to.include({v})", "notContains": f"expect({lhs}).to.not.include({v})",
        "length": f"expect({lhs}).to.have.lengthOf({v})",
        "matches": f"expect(String({lhs})).to.match(new RegExp({v}))",
        "notMatches": f"expect(String({lhs})).to.not.match(new RegExp({v}))",
        "startsWith": f"expect(String({lhs}).startsWith({v})).to.be.true",
        "endsWith": f"expect(String({lhs}).endsWith({v})).to.be.true",
        "between": f"expect({lhs}).to.be.within({lista()[1:-1] or 'undefined'})",
        "isEmpty": f"expect({lhs}).to.be.empty", "isNotEmpty": f"expect({lhs}).to.not.be.empty",
        "isNull": f"expect({lhs}).to.be.null", "isUndefined": f"expect({lhs}).to.be.undefined",
        "isDefined": f"expect({lhs}).to.not.be.undefined", "isTruthy": f"expect({lhs}).to.be.ok",
        "isFalsy": f"expect({lhs}).to.not.be.ok", "isJson": f"expect({lhs}).to.be.an('object')",
        "isNumber": f"expect({lhs}).to.be.a('number')", "isString": f"expect({lhs}).to.be.a('string')",
        "isBoolean": f"expect({lhs}).to.be.a('boolean')", "isArray": f"expect({lhs}).to.be.an('array')",
    }
    if op not in ops:
        avisos.append(f"{donde}: el operador '{op}' del assert '{lhs}' no tiene equivalente; no se convirtió.")
        return None
    return f"pm.test({json.dumps(f'{lhs}: {regla.strip()}')}, function () {{ {ops[op]}; }});"


def _revisar_script(script, avisos, donde):
    if re.search(r"bru\.(runRequest|sendRequest|runner|setNextRequest\(null)|require\(|\bawait\b", script):
        avisos.append(f"{donde}: el script usa require, await o bru.runRequest/sendRequest, que pueden no "
                      "andar en Postman/Newman; revisalo.")


def _request_bru(archivo, bloques, avisos, herencia):
    meta = {k: v for k, (v, _) in bloques.get("meta", {}).items()}
    nombre = meta.get("name") or archivo.stem
    donde = f"{archivo.name} ({nombre})"
    metodo = next((m for m in METODOS if m in bloques), None)
    if not metodo:
        avisos.append(f"{donde}: no tiene método HTTP (¿es un request gRPC o WebSocket?); no se convirtió.")
        return None
    datos = {k: v for k, (v, _) in bloques[metodo].items()}
    url = variables(datos.get("url", ""), avisos, donde)
    for k, (v, activo) in bloques.get("params:path", {}).items():
        if activo:
            url = re.sub(rf":{re.escape(k)}(?=/|\?|$)", variables(v), url)
    url = _con_query(url, [(k, variables(v), a) for k, (v, a) in bloques.get("params:query", {}).items()])

    headers = [_header(k, variables(v, avisos, donde), a) for k, (v, a) in herencia["headers"].items()
               if k not in bloques.get("headers", {})]
    headers += [_header(k, variables(v, avisos, donde), a) for k, (v, a) in bloques.get("headers", {}).items()]
    req = {"method": metodo.upper(), "header": headers, "url": url}

    tipo_auth = datos.get("auth", "inherit")
    auth = _auth_de_bru(tipo_auth, bloques, avisos, donde)
    if auth:
        req["auth"] = auth

    tipo_body = datos.get("body", "none")
    body = _body_bru(tipo_body, bloques, avisos, donde, meta.get("type") == "graphql")
    if body:
        req["body"] = body

    previo, despues = [], []
    for k, (v, activo) in bloques.get("vars:pre-request", {}).items():
        if activo:
            previo.append(f"pm.variables.set({json.dumps(k)}, pm.variables.replaceIn({json.dumps(variables(v))}));")
    if bloques.get("script:pre-request"):
        _revisar_script(bloques["script:pre-request"], avisos, donde)
        previo += bloques["script:pre-request"].split("\n")
    for k, (v, activo) in bloques.get("vars:post-response", {}).items():
        if activo:
            despues.append(f"pm.collectionVariables.set({json.dumps(k)}, {v});")
    for lhs, (regla, activo) in bloques.get("assert", {}).items():
        if activo:
            linea = _assert_bru(lhs, regla, avisos, donde)
            if linea:
                despues.append(linea)
    for bloque in ("script:post-response", "tests"):
        if bloques.get(bloque):
            _revisar_script(bloques[bloque], avisos, donde)
            despues += bloques[bloque].split("\n")
    item = {"name": nombre, "request": req}
    eventos = []
    if previo:
        eventos.append(_evento("prerequest", ADAPTADOR_BRU + previo))
    if despues:
        eventos.append(_evento("test", ADAPTADOR_BRU + ADAPTADOR_RES + despues))
    if eventos:
        item["event"] = eventos
    if bloques.get("docs"):
        item["request"]["description"] = bloques["docs"]
    return item


def _auth_de_bru(tipo, bloques, avisos, donde):
    if tipo in ("inherit", ""):
        return None
    if tipo == "none":
        return {"type": "noauth"}
    datos = {k: variables(v) for k, (v, _) in bloques.get(f"auth:{tipo}", {}).items()}
    if tipo == "bearer":
        return _auth_bearer(datos.get("token", ""))
    if tipo == "basic":
        return _auth_basic(datos.get("username", ""), datos.get("password", ""))
    if tipo == "apikey":
        return _auth_apikey(datos.get("key", ""), datos.get("value", ""), datos.get("placement", "header"))
    avisos.append(f"{donde}: la autenticación '{tipo}' no se convierte; configurala en Postman o con un header.")
    return None


def _body_bru(tipo, bloques, avisos, donde, es_graphql):
    if tipo == "graphql" or (es_graphql and "body:graphql" in bloques):
        return {"mode": "graphql", "graphql": {"query": bloques.get("body:graphql", ""),
                                               "variables": variables(bloques.get("body:graphql:vars", "")) or ""}}
    if tipo in ("json", "text", "xml", "sparql"):
        texto = variables(bloques.get(f"body:{tipo}", ""), avisos, donde)
        idioma = {"json": "json", "xml": "xml"}.get(tipo, "text")
        return {"mode": "raw", "raw": texto, "options": {"raw": {"language": idioma}}}
    if tipo in ("formUrlEncoded", "form-urlencoded"):
        pares = bloques.get("body:form-urlencoded", {})
        return {"mode": "urlencoded", "urlencoded": [dict(_header(k, variables(v), a)) for k, (v, a) in pares.items()]}
    if tipo in ("multipartForm", "multipart-form"):
        campos = []
        for k, (v, a) in bloques.get("body:multipart-form", {}).items():
            if v.startswith("@file("):
                avisos.append(f"{donde}: el campo '{k}' sube un archivo; Newman necesita la ruta real (src). Revisalo.")
                ruta = v[len("@file("):].rstrip(")")
                campos.append({"key": k, "type": "file", "src": ruta, **({} if a else {"disabled": True})})
            else:
                campos.append({"key": k, "value": variables(v), "type": "text", **({} if a else {"disabled": True})})
        return {"mode": "formdata", "formdata": campos}
    if tipo not in ("none", ""):
        avisos.append(f"{donde}: el body de tipo '{tipo}' no se convierte.")
    return None


def _orden_bru(ruta):
    """Clave de orden de un request o carpeta: el seq de su meta, después el nombre."""
    archivo = ruta / "folder.bru" if ruta.is_dir() else ruta
    seq = 10 ** 6
    if archivo.exists():
        meta = parsear_bru(archivo.read_text(encoding="utf-8-sig")).get("meta", {})
        try:
            seq = float(meta.get("seq", ("",))[0])
        except ValueError:
            pass
    return (seq, ruta.name.lower())


def _carpeta_bru(carpeta, avisos, herencia):
    items = []
    hijos = [p for p in carpeta.iterdir()
             if (p.is_dir() and p.name not in ("environments", "node_modules", ".git"))
             or (p.suffix == ".bru" and p.name not in ("collection.bru", "folder.bru"))]
    for p in sorted(hijos, key=_orden_bru):
        if p.is_dir():
            propia = dict(herencia["headers"])
            folder = p / "folder.bru"
            nombre = p.name
            if folder.exists():
                fb = parsear_bru(folder.read_text(encoding="utf-8-sig"))
                propia.update(fb.get("headers", {}))
                nombre = fb.get("meta", {}).get("name", (p.name,))[0] or p.name
                if any(k.startswith(("script:", "vars:")) or k == "tests" for k in fb):
                    avisos.append(f"{p.name}/folder.bru: los scripts y variables de carpeta no se convierten.")
            sub = _carpeta_bru(p, avisos, {"headers": propia})
            if sub:
                items.append({"name": nombre, "item": sub})
        else:
            bloques = parsear_bru(p.read_text(encoding="utf-8-sig"))
            item = _request_bru(p, bloques, avisos, herencia)
            if item:
                items.append(item)
    return items


def convertir_bruno(carpeta, environment=None):
    carpeta = Path(carpeta)
    if carpeta.name == "bruno.json":
        carpeta = carpeta.parent
    avisos = []
    config = json.loads((carpeta / "bruno.json").read_text(encoding="utf-8-sig"))
    nombre = config.get("name") or carpeta.name
    herencia = {"headers": {}}
    auth = None
    col_bru = carpeta / "collection.bru"
    if col_bru.exists():
        cb = parsear_bru(col_bru.read_text(encoding="utf-8-sig"))
        herencia["headers"] = cb.get("headers", {})
        tipo = {k: v for k, (v, _) in cb.get("auth", {}).items()}.get("mode")
        if tipo:
            auth = _auth_de_bru(tipo, cb, avisos, "collection.bru")
        if any(k.startswith(("script:", "vars:")) or k == "tests" for k in cb):
            avisos.append("collection.bru: los scripts y variables de la colección no se convierten; pasalos a cada request.")
    items = _carpeta_bru(carpeta, avisos, herencia)

    env = None
    entornos = sorted((carpeta / "environments").glob("*.bru")) if (carpeta / "environments").exists() else []
    if environment and Path(environment).suffix == ".bru" and Path(environment).exists():
        elegido = Path(environment)
    elif environment:
        elegido = next((e for e in entornos if e.stem.lower() == str(environment).lower()), None)
        if not elegido:
            avisos.append(f"No existe el environment '{environment}'. Hay: {', '.join(e.stem for e in entornos) or 'ninguno'}.")
    else:
        elegido = entornos[0] if len(entornos) == 1 else None
        if len(entornos) > 1:
            avisos.append(f"Hay varios environments ({', '.join(e.stem for e in entornos)}): elegí uno con --environment.")
    if elegido:
        eb = parsear_bru(elegido.read_text(encoding="utf-8-sig"))
        valores = {k: variables(v) for k, (v, activo) in eb.get("vars", {}).items() if activo}
        secretos = eb.get("vars:secret", [])
        for s in secretos:
            valores.setdefault(s.lstrip("~"), "")
        if secretos:
            avisos.append(f"Environment {elegido.stem}: las variables secretas ({', '.join(secretos)}) quedan vacías; "
                          "pasalas con --env-var (el token, con API_TOKEN del .env: correr_newman.py lo hace solo).")
        env = _environment(elegido.stem, valores)
    return Conversion("bruno", _coleccion(nombre, items, "Bruno", auth), env, avisos)


# --------------------------------------------------------------------------- Insomnia

ADAPTADOR_INSOMNIA = ["// Adaptado de Insomnia por scripts/convertir_coleccion.py: su API insomnia.* es la de pm.*.",
                      "const insomnia = pm;"]


def _request_insomnia(r, avisos):
    """Un request de Insomnia (v4 o v5) → item de Postman."""
    nombre = r.get("name") or "Request"
    donde = f"Insomnia ({nombre})"
    url = variables(r.get("url", ""), avisos, donde)
    params = [(p.get("name", ""), variables(p.get("value", ""), avisos, donde), not p.get("disabled"))
              for p in r.get("parameters") or []]
    url = _con_query(url, params)
    headers = [_header(h.get("name", ""), variables(h.get("value", ""), avisos, donde), not h.get("disabled"))
               for h in r.get("headers") or [] if h.get("name")]
    req = {"method": (r.get("method") or "GET").upper(), "header": headers, "url": url}

    auth = r.get("authentication") or {}
    if auth and not auth.get("disabled"):
        tipo = auth.get("type")
        if tipo == "bearer":
            prefijo = auth.get("prefix")
            if prefijo and prefijo.lower() != "bearer":
                req["header"].append(_header("Authorization", f"{prefijo} {variables(auth.get('token', ''))}"))
            else:
                req["auth"] = _auth_bearer(variables(auth.get("token", "")))
        elif tipo == "basic":
            req["auth"] = _auth_basic(variables(auth.get("username", "")), variables(auth.get("password", "")))
        elif tipo == "apikey":
            req["auth"] = _auth_apikey(variables(auth.get("key", "")), variables(auth.get("value", "")),
                                       str(auth.get("addTo", "header")).lower())
        elif tipo == "none":
            req["auth"] = {"type": "noauth"}
        elif tipo:
            avisos.append(f"{donde}: la autenticación '{tipo}' no se convierte; configurala en Postman o con un header.")

    body = r.get("body") or {}
    mime = (body.get("mimeType") or "").lower()
    if mime == "application/graphql":
        try:
            gql = json.loads(body.get("text") or "{}")
        except ValueError:
            gql = {"query": body.get("text", "")}
        vars_gql = gql.get("variables")
        req["body"] = {"mode": "graphql", "graphql": {
            "query": gql.get("query", ""),
            "variables": variables(json.dumps(vars_gql, ensure_ascii=False, indent=2)) if vars_gql else ""}}
    elif mime == "application/x-www-form-urlencoded":
        req["body"] = {"mode": "urlencoded", "urlencoded": [
            _header(p.get("name", ""), variables(p.get("value", "")), not p.get("disabled")) for p in body.get("params") or []]}
    elif mime == "multipart/form-data":
        campos = []
        for p in body.get("params") or []:
            if p.get("type") == "file":
                avisos.append(f"{donde}: el campo '{p.get('name')}' sube un archivo ({p.get('fileName', '')}); revisá la ruta.")
                campos.append({"key": p.get("name", ""), "type": "file", "src": p.get("fileName", "")})
            else:
                campos.append({"key": p.get("name", ""), "value": variables(p.get("value", "")), "type": "text"})
        req["body"] = {"mode": "formdata", "formdata": campos}
    elif body.get("text") is not None or mime:
        idioma = "json" if "json" in mime else "xml" if "xml" in mime else "text"
        req["body"] = {"mode": "raw", "raw": variables(body.get("text", ""), avisos, donde),
                       "options": {"raw": {"language": idioma}}}
    if body.get("fileName"):
        avisos.append(f"{donde}: el body es un archivo ({body['fileName']}); no se convierte.")

    item = {"name": nombre, "request": req}
    scripts = r.get("scripts") or {}
    previo = r.get("preRequestScript") or scripts.get("preRequest") or ""
    despues = r.get("afterResponseScript") or scripts.get("afterResponse") or ""
    eventos = []
    if previo.strip():
        eventos.append(_evento("prerequest", ADAPTADOR_INSOMNIA + previo.split("\n")))
    if despues.strip():
        eventos.append(_evento("test", ADAPTADOR_INSOMNIA + despues.split("\n")))
    if eventos:
        item["event"] = eventos
    if r.get("description"):
        req["description"] = r["description"]
    return item


def _elegir_env_insomnia(base, subs, environment, avisos):
    """Une el environment base con el sub-environment elegido (por nombre, o el único que haya)."""
    valores = _aplanar(base.get("data") or {})
    nombre = base.get("name") or "Base Environment"
    elegido = None
    if environment:
        elegido = next((s for s in subs if (s.get("name") or "").lower() == str(environment).lower()), None)
        if not elegido:
            avisos.append(f"No existe el environment '{environment}'. Hay: {', '.join(s.get('name', '') for s in subs) or 'ninguno'}.")
    elif len(subs) == 1:
        elegido = subs[0]
    elif len(subs) > 1:
        avisos.append(f"Hay varios environments ({', '.join(s.get('name', '') for s in subs)}): elegí uno con --environment.")
    if elegido:
        valores.update(_aplanar(elegido.get("data") or {}))
        nombre = elegido.get("name") or nombre
    valores = {k: variables(v) for k, v in valores.items()}
    return _environment(nombre, valores) if valores else None


def convertir_insomnia4(archivo, environment=None):
    datos = json.loads(Path(archivo).read_text(encoding="utf-8-sig"))
    avisos = []
    recursos = datos.get("resources") or []
    espacio = next((r for r in recursos if r.get("_type") == "workspace"), {})
    hijos = {}
    for r in recursos:
        hijos.setdefault(r.get("parentId"), []).append(r)
    orden = lambda r: (r.get("metaSortKey", 0) if isinstance(r.get("metaSortKey"), (int, float)) else 0, r.get("name", ""))  # noqa: E731

    variables_carpetas = {}

    def armar(padre):
        items = []
        for r in sorted(hijos.get(padre, []), key=orden):
            if r.get("_type") == "request_group":
                if r.get("environment"):
                    variables_carpetas.update(_aplanar(r["environment"]))
                    avisos.append(f"Carpeta '{r.get('name')}': su environment pasa a variables de la colección (en "
                                  "Postman no hay variables por carpeta).")
                items.append({"name": r.get("name") or "Carpeta", "item": armar(r["_id"])})
            elif r.get("_type") == "request":
                items.append(_request_insomnia(r, avisos))
            elif r.get("_type") in ("grpc_request", "websocket_request"):
                avisos.append(f"'{r.get('name')}': los requests {r['_type']} no se convierten.")
        return items

    items = armar(espacio.get("_id"))
    tipos = {r.get("_type") for r in recursos}
    if tipos & {"unit_test_suite", "unit_test"}:
        avisos.append("Los unit tests de Insomnia no se convierten: pasá sus validaciones al afterResponseScript de cada request.")
    base = next((r for r in recursos if r.get("_type") == "environment" and r.get("parentId") == espacio.get("_id")), {})
    subs = [r for r in recursos if r.get("_type") == "environment" and base and r.get("parentId") == base.get("_id")]
    env = _elegir_env_insomnia(base, subs, environment, avisos) if base else None
    nombre = espacio.get("name") or Path(archivo).stem
    return Conversion("insomnia4", _coleccion(nombre, items, "Insomnia (v4)", None,
                                              {k: variables(v) for k, v in variables_carpetas.items()}), env, avisos)


def convertir_insomnia5(archivo, environment=None):
    try:
        import yaml
    except ImportError:
        sys.exit("Para leer exports de Insomnia v5 (.yaml) hace falta PyYAML: pip install pyyaml")
    datos = yaml.safe_load(Path(archivo).read_text(encoding="utf-8-sig")) or {}
    avisos = []

    def orden(r):
        clave = (r.get("meta") or {}).get("sortKey", 0)
        return (clave if isinstance(clave, (int, float)) else 0, r.get("name", ""))

    def armar(lista):
        items = []
        for r in sorted(lista or [], key=orden):
            if "children" in r:
                items.append({"name": r.get("name") or "Carpeta", "item": armar(r.get("children"))})
                if r.get("environment"):
                    avisos.append(f"Carpeta '{r.get('name')}': su environment no se convierte (en Postman no hay "
                                  "variables por carpeta).")
            elif "url" in r or "method" in r:
                items.append(_request_insomnia(r, avisos))
        return items

    items = armar(datos.get("collection"))
    envs = datos.get("environments") or {}
    env = _elegir_env_insomnia(envs, envs.get("subEnvironments") or [], environment, avisos) if envs else None
    nombre = datos.get("name") or Path(archivo).stem
    return Conversion("insomnia5", _coleccion(nombre, items, "Insomnia (v5)"), env, avisos)


# --------------------------------------------------------------------------- entrada

def convertir(origen, environment=None):
    """Convierte la colección de origen. Devuelve una Conversion (coleccion, environment, advertencias)."""
    formato = detectar_formato(origen)
    if formato == "bruno":
        return convertir_bruno(origen, environment)
    if formato == "insomnia4":
        return convertir_insomnia4(origen, environment)
    if formato == "insomnia5":
        return convertir_insomnia5(origen, environment)
    if formato == "postman":
        return Conversion("postman", json.loads(Path(origen).read_text(encoding="utf-8-sig")))
    raise ValueError(f"No reconozco el formato de {origen}: tiene que ser una carpeta de Bruno (con bruno.json), "
                     "un export de Insomnia (v4 .json o v5 .yaml) o una colección de Postman.")


def _slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-") or "coleccion"


def guardar(conv, carpeta, nombre=None):
    """Escribe la colección (y el environment) en la carpeta. Devuelve (ruta_coleccion, ruta_environment)."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = nombre or _slug(conv.coleccion["info"]["name"])
    ruta_col = carpeta / f"{nombre}.postman_collection.json"
    ruta_col.write_text(json.dumps(conv.coleccion, ensure_ascii=False, indent=2), encoding="utf-8")
    ruta_env = None
    if conv.environment:
        ruta_env = carpeta / f"{nombre}.postman_environment.json"
        ruta_env.write_text(json.dumps(conv.environment, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta_col, ruta_env


def contar_requests(items):
    return sum(contar_requests(i["item"]) if "item" in i else 1 for i in items)


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Convierte colecciones de Bruno e Insomnia a Postman v2.1")
    ap.add_argument("origen", help="carpeta de Bruno, export de Insomnia (.json v4 / .yaml v5) o colección de Postman")
    ap.add_argument("--salida", help="carpeta donde dejar la colección convertida (por defecto, junto al origen)")
    ap.add_argument("--environment", help="environment a usar (Bruno: nombre del .bru; Insomnia: sub-environment)")
    a = ap.parse_args(argv)
    origen = Path(a.origen)
    try:
        conv = convertir(origen, a.environment)
    except (ValueError, OSError) as e:
        sys.exit(str(e))
    if conv.formato == "postman":
        print(f"{origen} ya es una colección de Postman: no hace falta convertirla.")
        return 0
    salida = Path(a.salida) if a.salida else (origen if origen.is_dir() else origen.parent)
    ruta_col, ruta_env = guardar(conv, salida)
    print(f"{conv.formato}: {contar_requests(conv.coleccion['item'])} request(s) → {ruta_col}")
    if ruta_env:
        print(f"Environment '{conv.environment['name']}' → {ruta_env}")
    for aviso in conv.advertencias:
        print(f"  ! {aviso}")
    if not conv.advertencias:
        print("Sin advertencias: se convirtió todo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

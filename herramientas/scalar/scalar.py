#!/usr/bin/env python3
"""
Scalar (scalar.com): traer las APIs del Registry, armar los casos como colección ejecutable e importarlos a Scalar
(agente probador-scalar, skill pruebas-scalar).

Uso (desde la raíz del repo de k0lmenIA):
    python herramientas/scalar/scalar.py descargar --namespace mi-equipo --slug pagos [--version latest]
    python herramientas/scalar/scalar.py listar --namespace mi-equipo
    python herramientas/scalar/scalar.py coleccion --openapi input/api/scalar/pagos.json --casos output/scalar/pagos/casos.json
    python herramientas/scalar/scalar.py enriquecer --openapi input/api/scalar/pagos.json --casos output/scalar/pagos/casos.json
    python herramientas/scalar/scalar.py validar output/scalar/pagos/pagos.k0lmenia.json
    python herramientas/scalar/scalar.py publicar output/scalar/pagos/pagos.k0lmenia.json --namespace mi-equipo --slug pagos
                                               --version 1.4.0-qa --confirmar   (CON EFECTO: solo con confirmación)

- `descargar`: baja el documento OpenAPI del Registry (`https://registry.scalar.com/@<namespace>/apis/<slug>/<version>`)
  a `input/api/scalar/<slug>.json`; si es privado usa SCALAR_API_KEY del .env (Bearer).
- `listar` / `validar` / `publicar`: usan la CLI oficial (`npx @scalar/cli`); el login es con SCALAR_API_KEY por
  variable de entorno (nunca en la línea de comandos ni en archivos).
- `coleccion`: arma una colección de Postman v2.1 con **un request por caso** y sus tests `pm.test` (status, cuerpo
  esperado, campos, tiempo y el schema de la respuesta documentada). Corre con `scripts/correr_newman.py`
  (`{{base_url}}` y `{{token}}` salen de API_BASEURL y API_TOKEN) y se puede importar en el cliente de Scalar.
- `enriquecer`: deja una copia del OpenAPI con un **ejemplo por caso** (`examples` del body y de los parámetros) y
  los tests en `x-post-response` de cada operación (los mismos `pm.test`; el bloque generado va entre marcas
  `k0lmenIA:inicio/fin` y no pisa scripts escritos a mano). Es lo que se publica en el Registry.

Formato de casos.json (lo escribe el agente a partir de los casos de API):
{
  "historia": "HU-001", "api": "pagos",
  "casos": [{"id": "CP-API-001", "titulo": "Crea un pago válido",
             "operacion": {"metodo": "POST", "ruta": "/payments"},          (o "operationId": "createPayment")
             "params": {"path": {"id": 1}, "query": {"page": 1}, "headers": {"X-Canal": "web"}},
             "auth": true, "body": {"amount": 100},
             "esperado": {"status": 201, "json": {"amount": 100}, "campos": ["id"], "headers": {"Content-Type": "application/json"},
                          "tiempo_ms": 2000},
             "falta_info": ["FI-01"]}]
}
"""
import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
REGISTRY = "https://registry.scalar.com"
CLI = "@scalar/cli"
METODOS = ("get", "post", "put", "patch", "delete", "head", "options")
MARCA_INI, MARCA_FIN = "// k0lmenIA:inicio (generado: no editar a mano)", "// k0lmenIA:fin"
NO_SCHEMA = {"example", "examples", "xml", "externalDocs", "discriminator", "deprecated"}
FORMATOS_JSON_SCHEMA = {"date-time", "date", "time", "duration", "email", "idn-email", "hostname", "idn-hostname", "ipv4", "ipv6",
                        "uri", "uri-reference", "iri", "iri-reference", "uuid", "uri-template", "json-pointer",
                        "relative-json-pointer", "regex"}


def leer_env():
    sys.path.insert(0, str(RAIZ / "scripts"))
    try:
        from _env import leer_env as _leer
        valores = _leer()
    except Exception:
        valores = {}
    valores.update({k: v for k, v in os.environ.items() if v})
    return valores


def slug_valido(texto, que):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", texto or ""):
        raise ValueError(f"{que} inválido: {texto!r}")
    return texto


# ------------------------------------------------------------------ OpenAPI

def cargar_openapi(ruta):
    texto = Path(ruta).read_text(encoding="utf-8")
    if texto.lstrip().startswith("{"):
        return json.loads(texto)
    import yaml
    return yaml.safe_load(texto)


def operaciones(doc):
    """{(METODO, ruta): operacion} y {operationId: (METODO, ruta)}."""
    ops, ids = {}, {}
    for ruta, item in (doc.get("paths") or {}).items():
        for m in METODOS:
            if isinstance(item, dict) and isinstance(item.get(m), dict):
                ops[(m.upper(), ruta)] = item[m]
                if item[m].get("operationId"):
                    ids[item[m]["operationId"]] = (m.upper(), ruta)
    return ops, ids


def resolver(doc, nodo, vistos=()):
    """El nodo con los $ref locales resueltos. Un $ref que vuelve a uno que se está resolviendo (ciclo) o una
    cadena de más de 20 referencias queda como {} (schema abierto)."""
    if isinstance(nodo, dict):
        ref = nodo.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            if ref in vistos or len(vistos) > 20:
                return {}
            destino = doc
            for parte in ref[2:].split("/"):
                destino = (destino or {}).get(parte.replace("~1", "/").replace("~0", "~"))
            return resolver(doc, destino or {}, vistos + (ref,))
        return {k: resolver(doc, v, vistos) for k, v in nodo.items()}
    if isinstance(nodo, list):
        return [resolver(doc, x, vistos) for x in nodo]
    return nodo


def a_json_schema(schema):
    """Del schema de OpenAPI a JSON Schema que entiende pm.response.to.have.jsonSchema (nullable, sin extensiones)."""
    if isinstance(schema, list):
        return [a_json_schema(x) for x in schema]
    if not isinstance(schema, dict):
        return schema
    out = {k: a_json_schema(v) if k not in ("properties", "patternProperties", "$defs", "definitions") else
           {pk: a_json_schema(pv) for pk, pv in v.items()} if isinstance(v, dict) else v
           for k, v in schema.items() if k not in NO_SCHEMA and not k.startswith("x-")}
    # Los formatos propios de OpenAPI (int64, double, binary…) hacen fallar al validador de Postman/Scalar.
    if isinstance(out.get("format"), str) and out["format"] not in FORMATOS_JSON_SCHEMA:
        out.pop("format")
    if out.pop("nullable", False) and isinstance(out.get("type"), str):
        out["type"] = [out["type"], "null"]
    for k in ("readOnly", "writeOnly"):
        out.pop(k, None)
    return out


def schema_respuesta(doc, op, status):
    resp = (op.get("responses") or {}).get(str(status))
    resp = resolver(doc, resp) if resp else None
    if not resp:
        return None
    for tipo, media in (resp.get("content") or {}).items():
        if "json" in tipo and isinstance(media, dict) and media.get("schema"):
            return a_json_schema(media["schema"])
    return None


def buscar_operacion(caso, ops, ids):
    o = caso.get("operacion") or {}
    if o.get("operationId"):
        clave = ids.get(o["operationId"])
        if not clave:
            raise ValueError(f"{caso.get('id')}: no existe la operación {o['operationId']} en el OpenAPI")
        return clave, ops[clave]
    clave = ((o.get("metodo") or "").upper(), o.get("ruta") or "")
    if clave not in ops:
        raise ValueError(f"{caso.get('id')}: no existe {clave[0]} {clave[1]} en el OpenAPI (los casos no inventan endpoints)")
    return clave, ops[clave]


# ------------------------------------------------------------------ tests pm (compartidos por la colección y el OpenAPI)

def _js(v):
    return json.dumps(v, ensure_ascii=False)


AYUDAS_JS = """const k0orden = (v) => Array.isArray(v) ? v.map(k0orden) : (v && typeof v === 'object')
  ? Object.keys(v).sort().reduce((o, k) => { o[k] = k0orden(v[k]); return o; }, {}) : v;
const k0contiene = (real, esp) => {
  if (esp && typeof esp === 'object' && !Array.isArray(esp)) {
    return !!real && typeof real === 'object' && Object.keys(esp).every((k) => k0contiene(real[k], esp[k]));
  }
  return JSON.stringify(k0orden(real)) === JSON.stringify(k0orden(esp));
};
const k0json = () => { try { return pm.response.json(); } catch (e) { return undefined; } };"""


def tests_caso(caso, schema=None):
    """Líneas pm.test de un caso (sin las ayudas)."""
    esp = caso.get("esperado") or {}
    cid = caso.get("id", "caso")
    l = []
    if esp.get("status") is not None:
        l.append(f"pm.test({_js(f'{cid} · status {esp['status']}')}, () => pm.response.to.have.status({int(esp['status'])}));")
    if esp.get("json") is not None:
        l.append(f"pm.test({_js(f'{cid} · cuerpo esperado')}, () => pm.expect(k0contiene(k0json(), {_js(esp['json'])}), "
                 f"'el cuerpo no contiene lo esperado').to.be.true);")
    for campo in esp.get("campos") or []:
        ruta = [p for p in str(campo).split(".") if p]
        acceso = "".join(f"?.[{_js(p)}]" for p in ruta)
        l.append(f"pm.test({_js(f'{cid} · tiene {campo}')}, () => pm.expect(k0json(){acceso}).to.not.equal(undefined));")
    for h, v in (esp.get("headers") or {}).items():
        l.append(f"pm.test({_js(f'{cid} · header {h}')}, () => pm.expect(pm.response.headers.get({_js(h)}) || '').to.include({_js(str(v))}));")
    if esp.get("tiempo_ms"):
        l.append(f"pm.test({_js(f'{cid} · responde en menos de {esp['tiempo_ms']} ms')}, () => "
                 f"pm.expect(pm.response.responseTime).to.be.below({int(esp['tiempo_ms'])}));")
    if schema:
        l.append(f"pm.test({_js(f'{cid} · respeta el schema del contrato')}, () => pm.response.to.have.jsonSchema({_js(schema)}));")
    return l


def ruta_concreta(ruta, params):
    """La ruta con los parámetros de path del caso reemplazados (None si falta alguno)."""
    for k, v in ((params or {}).get("path") or {}).items():
        ruta = ruta.replace("{" + k + "}", str(v))
    return None if "{" in ruta else ruta


def script_operacion(doc, op, casos, ruta=""):
    """x-post-response de una operación: contrato (status documentado + schema) y, si el request coincide con el
    ejemplo de un caso (misma ruta concreta, body y query), los tests de ese caso."""
    documentados = [s for s in (op.get("responses") or {}) if s != "default"]
    schemas = {s: schema_respuesta(doc, op, s) for s in documentados}
    datos = {"documentados": documentados, "default": "default" in (op.get("responses") or {}),
             "schemas": {k: v for k, v in schemas.items() if v}}
    casos_js = []
    for c in casos:
        cuerpo = "\n    ".join(tests_caso(c))
        casos_js.append(f"{{ id: {_js(c['id'])}, ruta: {_js(ruta_concreta(ruta, c.get('params')))}, body: {_js(c.get('body'))}, "
                        f"query: {_js({k: str(v) for k, v in ((c.get('params') or {}).get('query') or {}).items()})},\n"
                        f"  correr: () => {{\n    {cuerpo}\n  }} }}")
    return "\n".join([
        MARCA_INI, AYUDAS_JS,
        f"const k0 = {_js(datos)};",
        "pm.test('Contrato · status documentado', () => { if (!k0.default) pm.expect(k0.documentados).to.include(String(pm.response.code)); });",
        "if (k0.schemas[String(pm.response.code)] && k0json() !== undefined) {",
        "  pm.test('Contrato · respeta el schema documentado', () => pm.response.to.have.jsonSchema(k0.schemas[String(pm.response.code)]));",
        "}",
        "let k0cuerpo = null;",
        "try { const raw = pm.request.body && pm.request.body.raw; k0cuerpo = raw ? JSON.parse(raw) : null; } catch (e) { k0cuerpo = null; }",
        "const k0query = {};",
        "try { pm.request.url.query.all().forEach((p) => { if (!p.disabled) k0query[p.key] = String(p.value); }); } catch (e) { /* sin query */ }",
        "let k0ruta = '';",
        "try { k0ruta = decodeURIComponent(pm.request.url.getPath()); } catch (e) { k0ruta = ''; }",
        "const k0mismaRuta = (c) => !c.ruta || !k0ruta || k0ruta === c.ruta || k0ruta.endsWith(c.ruta);",
        "const k0casos = [",
        ",\n".join(casos_js),
        "];",
        "const k0caso = k0casos.find((c) => k0mismaRuta(c) && k0contiene(k0cuerpo, c.body) && k0contiene(c.body, k0cuerpo) && k0contiene(k0query, c.query));",
        "if (k0caso) k0caso.correr();",
        MARCA_FIN,
    ])


def reemplazar_bloque(existente, nuevo):
    """Mete el bloque generado en el script existente, sin tocar lo escrito a mano."""
    existente = existente or ""
    if MARCA_INI in existente and MARCA_FIN in existente:
        a = existente.index(MARCA_INI)
        b = existente.index(MARCA_FIN) + len(MARCA_FIN)
        return existente[:a] + nuevo + existente[b:]
    return (existente.rstrip() + "\n\n" + nuevo) if existente.strip() else nuevo


# ------------------------------------------------------------------ colección Postman v2.1

def _url(ruta, params):
    path = ruta
    for k, v in ((params or {}).get("path") or {}).items():
        path = path.replace("{" + k + "}", str(v))
    faltan = re.findall(r"\{([^}]+)\}", path)
    for k in faltan:  # parámetros sin valor: quedan como variable de la colección
        path = path.replace("{" + k + "}", "{{" + k + "}}")
    query = [{"key": k, "value": str(v)} for k, v in ((params or {}).get("query") or {}).items()]
    raw = "{{base_url}}" + path + (("?" + "&".join(f"{q['key']}={q['value']}" for q in query)) if query else "")
    return {"raw": raw, "host": ["{{base_url}}"], "path": [p for p in path.split("/") if p], **({"query": query} if query else {})}, faltan


def coleccion(doc, datos, nombre=None):
    ops, ids = operaciones(doc)
    carpetas, variables = {}, {"base_url": ((doc.get("servers") or [{}])[0].get("url") or ""), "token": ""}
    for c in datos.get("casos") or []:
        (metodo, ruta), op = buscar_operacion(c, ops, ids)
        esp = c.get("esperado") or {}
        schema = schema_respuesta(doc, op, esp.get("status")) if esp.get("status") is not None else None
        url, faltan = _url(ruta, c.get("params"))
        for f in faltan:
            variables.setdefault(f, "")
        headers = [{"key": k, "value": str(v)} for k, v in ((c.get("params") or {}).get("headers") or {}).items()]
        if c.get("auth"):
            headers.append({"key": "Authorization", "value": "Bearer {{token}}"})
        req = {"method": metodo, "header": headers, "url": url,
               "description": c.get("titulo", "") + (f" · Falta información: {', '.join(c['falta_info'])}" if c.get("falta_info") else "")}
        if c.get("body") is not None:
            headers.append({"key": "Content-Type", "value": "application/json"})
            req["body"] = {"mode": "raw", "raw": json.dumps(c["body"], ensure_ascii=False, indent=2), "options": {"raw": {"language": "json"}}}
        script = AYUDAS_JS.split("\n") + tests_caso(c, schema)
        carpeta = carpetas.setdefault(f"{metodo} {ruta}", {"name": f"{metodo} {ruta}", "description": op.get("summary", ""), "item": []})
        carpeta["item"].append({"name": f"{c['id']} · {c.get('titulo', '')}".strip(" ·"), "request": req,
                                "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": script}}]})
    titulo = nombre or (doc.get("info") or {}).get("title") or "API"
    return {"info": {"name": f"{titulo}{' · ' + datos['historia'] if datos.get('historia') else ''} (k0lmenIA)",
                     "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                     "description": "Casos de prueba generados por k0lmenIA (probador-scalar). Un request por caso, con sus tests."},
            "item": list(carpetas.values()),
            "variable": [{"key": k, "value": v} for k, v in variables.items()]}


# ------------------------------------------------------------------ OpenAPI enriquecido (para el Registry)

def enriquecer(doc, datos):
    doc = copy.deepcopy(doc)
    ops, ids = operaciones(doc)
    por_op = {}
    for c in datos.get("casos") or []:
        clave, _ = buscar_operacion(c, ops, ids)
        por_op.setdefault(clave, []).append(c)
    for (metodo, ruta), casos in por_op.items():
        op = doc["paths"][ruta][metodo.lower()]
        for c in casos:
            resumen = f"{c['id']} · {c.get('titulo', '')}".strip(" ·")
            if c.get("body") is not None:
                rb = op.setdefault("requestBody", {})
                if "$ref" not in rb:
                    media = rb.setdefault("content", {}).setdefault("application/json", {})
                    media.setdefault("examples", {})[c["id"]] = {"summary": resumen, "value": c["body"]}
            params = c.get("params") or {}
            usado = lambda p: (params.get(p.get("in")) or {}).get(p.get("name")) is not None  # noqa: E731
            # Los parámetros que usa el caso quedan en línea en la operación (los $ref y los comunes de la ruta se
            # copian resueltos), así los ejemplos no tocan componentes ni otras operaciones.
            lista = []
            for p in op.get("parameters") or []:
                r = resolver(doc, p) if isinstance(p, dict) else p
                lista.append(copy.deepcopy(r) if isinstance(p, dict) and "$ref" in p and usado(r) else p)
            propios = {(resolver(doc, p).get("in"), resolver(doc, p).get("name")) for p in lista if isinstance(p, dict)}
            for p in doc["paths"][ruta].get("parameters") or []:
                r = resolver(doc, p) if isinstance(p, dict) else {}
                if (r.get("in"), r.get("name")) not in propios and usado(r):
                    lista.append(copy.deepcopy(r))
            if lista:
                op["parameters"] = lista
            for p in op.get("parameters") or []:
                if not isinstance(p, dict) or "$ref" in p:
                    continue
                valor = (params.get(p.get("in")) or {}).get(p.get("name")) if p.get("in") in ("path", "query", "header") else None
                if valor is not None:
                    p.setdefault("examples", {})[c["id"]] = {"summary": resumen, "value": valor}
        op["x-post-response"] = reemplazar_bloque(op.get("x-post-response"), script_operacion(doc, op, casos, ruta))
    info = doc.setdefault("info", {})
    info["x-k0lmenia"] = {"historia": datos.get("historia"), "casos": sum(len(v) for v in por_op.values())}
    return doc


# ------------------------------------------------------------------ Registry y CLI

def descargar(namespace, slug, version="latest", salida=None, env=None):
    env = env if env is not None else leer_env()
    slug_valido(namespace, "namespace")
    slug_valido(slug, "slug")
    slug_valido(version, "versión")
    url = f"{REGISTRY}/@{namespace}/apis/{slug}/{version}?format=json"
    headers = {"Accept": "application/json", "User-Agent": "k0lmenIA"}
    if env.get("SCALAR_API_KEY"):
        headers["Authorization"] = f"Bearer {env['SCALAR_API_KEY']}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:  # noqa: S310
            doc = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as ex:
        pista = " (si es privado, configurá SCALAR_API_KEY en el .env)" if ex.code in (401, 403, 404) else ""
        raise RuntimeError(f"el Registry respondió {ex.code} para @{namespace}/{slug}@{version}{pista}") from None
    if not isinstance(doc, dict) or not (doc.get("openapi") or doc.get("swagger") or doc.get("asyncapi")):
        raise RuntimeError("lo que devolvió el Registry no es un documento OpenAPI/AsyncAPI")
    salida = Path(salida) if salida else RAIZ / "input" / "api" / "scalar" / f"{slug}.json"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    ops, _ = operaciones(doc)
    return {"archivo": str(salida), "url": f"{REGISTRY}/@{namespace}/apis/{slug}/{version}", "titulo": (doc.get("info") or {}).get("title"),
            "version": (doc.get("info") or {}).get("version"), "operaciones": len(ops)}


def cli(args, env=None, necesita_login=True):
    """Corre `npx @scalar/cli ...` con SCALAR_API_KEY en el entorno (nunca en la línea de comandos)."""
    env = env if env is not None else leer_env()
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise RuntimeError("Hace falta Node.js 20+ (npx en el PATH) para la CLI de Scalar.")
    entorno = dict(os.environ)
    if necesita_login:
        if not env.get("SCALAR_API_KEY"):
            raise RuntimeError("Falta SCALAR_API_KEY en el .env (token personal: https://dashboard.scalar.com/account).")
        entorno["SCALAR_API_KEY"] = env["SCALAR_API_KEY"]
        r = subprocess.run([npx, "--yes", CLI, "auth", "login"], capture_output=True, text=True, env=entorno,
                           encoding="utf-8", errors="replace", timeout=300)
        if r.returncode != 0:
            raise RuntimeError(f"no se pudo iniciar sesión en Scalar: {(r.stderr or r.stdout).strip()[-300:]}")
    r = subprocess.run([npx, "--yes", CLI, *args], capture_output=True, text=True, env=entorno,
                       encoding="utf-8", errors="replace", timeout=600)
    salida = ((r.stdout or "") + (r.stderr or "")).strip()
    if env.get("SCALAR_API_KEY"):
        salida = salida.replace(env["SCALAR_API_KEY"], "***")
    return r.returncode, salida


# ------------------------------------------------------------------ CLI de esta herramienta

def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    env = leer_env()
    ap = argparse.ArgumentParser(description="Scalar: Registry, colección de casos y tests para importar (probador-scalar).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("descargar")
    s.add_argument("--namespace", default=env.get("SCALAR_NAMESPACE"))
    s.add_argument("--slug", required=True)
    s.add_argument("--version", default="latest")
    s.add_argument("--salida", default=None)
    s = sub.add_parser("listar")
    s.add_argument("--namespace", default=env.get("SCALAR_NAMESPACE"))
    for nombre in ("coleccion", "enriquecer"):
        s = sub.add_parser(nombre)
        s.add_argument("--openapi", required=True)
        s.add_argument("--casos", required=True)
        s.add_argument("--salida", default=None)
    s = sub.add_parser("validar")
    s.add_argument("archivo")
    s = sub.add_parser("publicar")
    s.add_argument("archivo")
    s.add_argument("--namespace", default=env.get("SCALAR_NAMESPACE"))
    s.add_argument("--slug", required=True)
    s.add_argument("--version", required=True, help="versión nueva (p. ej. 1.4.0-qa): no se pisa una existente")
    s.add_argument("--publica", action="store_true", help="publicarla como pública (por defecto, privada)")
    s.add_argument("--forzar", action="store_true", help="reemplazar una versión existente (solo si la persona lo pidió)")
    s.add_argument("--confirmar", action="store_true", help="la persona confirmó la publicación (sin esto no publica)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "descargar":
            if not a.namespace:
                raise ValueError("falta --namespace (o SCALAR_NAMESPACE en el .env)")
            r = descargar(a.namespace, a.slug, a.version, a.salida, env)
        elif a.cmd == "listar":
            if not a.namespace:
                raise ValueError("falta --namespace (o SCALAR_NAMESPACE en el .env)")
            codigo, texto = cli(["registry", "list", "--namespace", slug_valido(a.namespace, "namespace")], env)
            print(texto)
            return 0 if codigo == 0 else 2
        elif a.cmd in ("coleccion", "enriquecer"):
            doc = cargar_openapi(a.openapi)
            datos = json.loads(Path(a.casos).read_text(encoding="utf-8"))
            base = Path(a.casos).parent
            api = datos.get("api") or Path(a.openapi).stem
            if a.cmd == "coleccion":
                salida = Path(a.salida) if a.salida else base / f"{api}.postman_collection.json"
                col = coleccion(doc, datos)
                salida.write_text(json.dumps(col, ensure_ascii=False, indent=2), encoding="utf-8")
                r = {"coleccion": str(salida), "casos": sum(len(c["item"]) for c in col["item"]), "operaciones": len(col["item"])}
            else:
                salida = Path(a.salida) if a.salida else base / f"{api}.k0lmenia.json"
                nuevo = enriquecer(doc, datos)
                salida.write_text(json.dumps(nuevo, ensure_ascii=False, indent=2), encoding="utf-8")
                r = {"openapi": str(salida), **nuevo["info"]["x-k0lmenia"]}
        elif a.cmd == "validar":
            codigo, texto = cli(["document", "validate", a.archivo], env, necesita_login=False)
            print(texto)
            return 0 if codigo == 0 else 1
        else:
            if not a.confirmar:
                print("[scalar] Publicar en el Registry tiene efecto: pasá --confirmar solo con la confirmación explícita de la persona.",
                      file=sys.stderr)
                return 3
            if not a.namespace:
                raise ValueError("falta --namespace (o SCALAR_NAMESPACE en el .env)")
            args = ["registry", "publish", a.archivo, "--namespace", slug_valido(a.namespace, "namespace"),
                    "--slug", slug_valido(a.slug, "slug"), "--version", slug_valido(a.version, "versión")]
            if not a.publica:
                args.append("--private")
            if a.forzar:
                args.append("--force")
            codigo, texto = cli(args, env)
            print(texto)
            return 0 if codigo == 0 else 2
    except (ValueError, RuntimeError, OSError) as ex:
        print(f"[scalar] {ex}", file=sys.stderr)
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Resume una especificación Swagger 2.0 u OpenAPI 3.x en pocas líneas, lista para automatizar con los
steps de k0lmena (agentes generador-casos-api y api-mapper).

Uso (desde la raíz del repo; en Mac/Linux, python3):
    python scripts/resumir_openapi.py <url o archivo .json/.yaml> [--salida resumen.md] [--json]

Qué resuelve (lo que hacía fallar los tests generados a mano):
  - **API_BASEURL**: el server con su basePath (Swagger 2: schemes + host + basePath; OpenAPI 3: el
    primer `servers`, con sus variables y, si es relativo, contra la URL de la spec). Los endpoints
    del .feature son los paths de la spec tal cual: "/pet/{petId}", sin repetir el basePath.
  - **Autenticación**: cada securityScheme con el step que le corresponde (Bearer, API key en un
    header o en la query, básica, OAuth2) y qué endpoints la piden.
  - **Endpoints**: método, path, parámetros (path, query, header) con su tipo y si son obligatorios,
    cómo va el body (JSON o formulario), un body de ejemplo armado del schema y los status documentados.

Sirve para no volcar la spec entera en la conversación. No llama a la API: solo lee la spec.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

METODOS = ("get", "post", "put", "patch", "delete", "head", "options")


# ------------------------------------------------------------------ leer la spec
def leer_texto(origen):
    if re.match(r"^https?://", origen):
        req = urllib.request.Request(origen, headers={"Accept": "application/json, application/yaml, */*"})
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (URL que pasa la persona)
            return r.read().decode("utf-8-sig")
    ruta = Path(origen)
    if not ruta.exists():
        raise SystemExit(f"No existe {ruta}.")
    return ruta.read_text(encoding="utf-8-sig")


def parsear(texto):
    t = texto.lstrip()
    if t.startswith("{"):
        return json.loads(t)
    try:
        import yaml
    except ImportError:
        raise SystemExit("La spec es YAML y falta pyyaml: pip install -r requirements.txt")
    return yaml.safe_load(texto)


# ------------------------------------------------------------------ $ref y schemas
def resolver(spec, nodo, vistos=None):
    """Sigue los $ref locales (#/definitions/X, #/components/schemas/X, parámetros, bodies...)."""
    vistos = vistos or set()
    while isinstance(nodo, dict) and "$ref" in nodo:
        ref = nodo["$ref"]
        if not ref.startswith("#/") or ref in vistos:
            return {"description": f"(referencia externa o circular: {ref})"}
        vistos.add(ref)
        destino = spec
        for parte in ref[2:].split("/"):
            destino = (destino or {}).get(parte.replace("~1", "/").replace("~0", "~"))
        nodo = destino or {}
    return nodo or {}


def tipo_de(spec, schema):
    s = resolver(spec, schema)
    if "$ref" in (schema or {}):
        return schema["$ref"].split("/")[-1]
    t = s.get("type")
    if t == "array":
        return f"array<{tipo_de(spec, s.get('items') or {})}>"
    if s.get("enum"):
        return f"{t or 'string'} ({' | '.join(map(str, s['enum'][:8]))})"
    fmt = s.get("format")
    return f"{t}{f' ({fmt})' if fmt else ''}" if t else ("object" if s.get("properties") else "?")


def ejemplo(spec, schema, nivel=0, refs=()):
    """Un valor de ejemplo del schema: example, default o enum si están; si no, uno del tipo."""
    ref = (schema or {}).get("$ref")
    if ref in refs or nivel > 5:
        return None
    s = resolver(spec, schema)
    refs = refs + ((ref,) if ref else ())
    for clave in ("example", "default"):
        if clave in s:
            return s[clave]
    if s.get("enum"):
        return s["enum"][0]
    if "allOf" in s:
        salida = {}
        for parte in s["allOf"]:
            v = ejemplo(spec, parte, nivel + 1, refs)
            if isinstance(v, dict):
                salida.update(v)
        return salida
    for clave in ("oneOf", "anyOf"):
        if s.get(clave):
            return ejemplo(spec, s[clave][0], nivel + 1, refs)
    t = s.get("type") or ("object" if s.get("properties") else None)
    if t == "object":
        return {k: ejemplo(spec, v, nivel + 1, refs) for k, v in (s.get("properties") or {}).items()}
    if t == "array":
        item = ejemplo(spec, s.get("items") or {}, nivel + 1, refs)
        return [item] if item is not None else []
    if t == "integer":
        return s.get("minimum", 1)
    if t == "number":
        return s.get("minimum", 1.5)
    if t == "boolean":
        return True
    if t == "string":
        return {"date-time": "2026-01-01T00:00:00Z", "date": "2026-01-01", "email": "qa+{aleatorio}@prueba.com",
                "uuid": "{uuid}", "password": "Clave123!"}.get(s.get("format"), "texto")
    return None


# ------------------------------------------------------------------ base URL
def base_url(spec, origen):
    es_url = re.match(r"^https?://", origen or "")
    if spec.get("swagger"):
        u = urlparse(origen) if es_url else None
        esquema = (spec.get("schemes") or [u.scheme if u else "https"])[0]
        host = spec.get("host") or (u.netloc if u else "")
        if not host:
            return None, "La spec no tiene host: completá API_BASEURL a mano (server + basePath)."
        return f"{esquema}://{host}{(spec.get('basePath') or '').rstrip('/')}", None
    servers = spec.get("servers") or []
    if not servers:
        if es_url:
            return f"{urlparse(origen).scheme}://{urlparse(origen).netloc}", "La spec no tiene servers: se usa el host de donde se bajó."
        return None, "La spec no tiene servers: completá API_BASEURL a mano."
    srv = servers[0]
    url = srv.get("url", "")
    for nombre, var in (srv.get("variables") or {}).items():
        url = url.replace("{" + nombre + "}", str(var.get("default", "")))
    nota = f"Hay {len(servers)} servers; se usó el primero ({servers[0].get('description') or url})." if len(servers) > 1 else None
    if not re.match(r"^https?://", url):
        if not es_url:
            return None, f"El server es relativo ({url}): completá API_BASEURL con el host + {url}."
        url = urljoin(origen, url)
    return url.rstrip("/"), nota


# ------------------------------------------------------------------ seguridad
def esquemas_seguridad(spec):
    crudos = spec.get("securityDefinitions") or (spec.get("components") or {}).get("securitySchemes") or {}
    salida = {}
    for nombre, s in crudos.items():
        s = resolver(spec, s)
        t = (s.get("type") or "").lower()
        esquema = (s.get("scheme") or "").lower()
        if t == "apikey" and s.get("in") == "header":
            paso = f'Given el request usa la API key en el header "{s.get("name")}"'
            env = "API_KEY"
        elif t == "apikey" and s.get("in") == "query":
            paso = f'Given el request usa la API key en el parámetro "{s.get("name")}"'
            env = "API_KEY"
        elif t == "apikey" and s.get("in") == "cookie":
            paso = f'Given el request usa el header "Cookie" con valor "{s.get("name")}={{API_KEY}}"'
            env = "API_KEY"
        elif (t == "http" and esquema == "basic") or t == "basic":
            paso, env = "Given el request usa autenticación básica", "API_USER y API_PASSWORD"
        elif (t == "http" and esquema == "bearer") or t in ("oauth2", "openidconnect"):
            paso, env = "Given el request usa el token de autenticación", "API_TOKEN (un token ya obtenido)"
        else:
            paso, env = f"(tipo {t} {esquema}: sin step genérico)", "-"
        salida[nombre] = {"tipo": t + (f" {esquema}" if esquema else "") + (f" en {s.get('in')}" if s.get("in") else ""),
                          "step": paso, "variable": env}
    return salida


# ------------------------------------------------------------------ endpoints
def endpoints(spec):
    v2 = bool(spec.get("swagger"))
    seguridad_global = spec.get("security")
    salida = []
    for ruta, item in (spec.get("paths") or {}).items():
        item = resolver(spec, item)
        comunes = item.get("parameters") or []
        for metodo in METODOS:
            op = item.get(metodo)
            if not op:
                continue
            params = {}
            for p in comunes + (op.get("parameters") or []):
                p = resolver(spec, p)
                params[(p.get("in"), p.get("name"))] = p
            ep = {"metodo": metodo.upper(), "path": ruta, "resumen": op.get("summary") or op.get("operationId") or "",
                  "tags": op.get("tags") or [], "parametros": [], "body": None, "respuestas": {}, "deprecated": bool(op.get("deprecated"))}
            form = {}
            for (donde, nombre), p in params.items():
                if donde == "body":
                    ep["body"] = {"tipo": "json", "content_type": ((op.get("consumes") or spec.get("consumes") or ["application/json"])[0]),
                                  "ejemplo": ejemplo(spec, p.get("schema") or {}), "obligatorio": bool(p.get("required"))}
                elif donde == "formData":
                    form[nombre] = {"tipo": p.get("type"), "obligatorio": bool(p.get("required"))}
                else:
                    tipo = tipo_de(spec, p.get("schema") or p) if not v2 else tipo_de(spec, p)
                    ep["parametros"].append({"en": donde, "nombre": nombre, "tipo": tipo, "obligatorio": bool(p.get("required"))})
            if form:
                ct = (op.get("consumes") or spec.get("consumes") or ["application/x-www-form-urlencoded"])[0]
                multipart = "multipart" in ct or any(v["tipo"] == "file" for v in form.values())
                ep["body"] = {"tipo": "multipart" if multipart else "formulario", "content_type": ct, "campos": form}
            rb = resolver(spec, op.get("requestBody") or {})
            if rb.get("content"):
                ct, media = next(iter(rb["content"].items()))
                for preferido in ("application/json", "application/x-www-form-urlencoded"):
                    if preferido in rb["content"]:
                        ct, media = preferido, rb["content"][preferido]
                        break
                schema = (media or {}).get("schema") or {}
                if "json" in ct:
                    ej = media.get("example") or ejemplo(spec, schema)
                    ep["body"] = {"tipo": "json", "content_type": ct, "ejemplo": ej, "obligatorio": bool(rb.get("required"))}
                elif "form" in ct:
                    props = resolver(spec, schema).get("properties") or {}
                    req = set(resolver(spec, schema).get("required") or [])
                    ep["body"] = {"tipo": "formulario" if "urlencoded" in ct else "multipart", "content_type": ct,
                                  "campos": {k: {"tipo": tipo_de(spec, v), "obligatorio": k in req} for k, v in props.items()}}
                else:
                    ep["body"] = {"tipo": "otro", "content_type": ct}
            for codigo, r in (op.get("responses") or {}).items():
                ep["respuestas"][str(codigo)] = (resolver(spec, r).get("description") or "").strip().split("\n")[0][:120]
            seg = op.get("security", seguridad_global)
            ep["seguridad"] = sorted({n for req in (seg or []) for n in req})
            salida.append(ep)
    return salida


def resumir(spec, origen):
    if not isinstance(spec, dict) or not (spec.get("swagger") or spec.get("openapi")):
        raise SystemExit("No parece una spec Swagger/OpenAPI (falta el campo swagger u openapi).")
    base, nota = base_url(spec, origen)
    return {"titulo": (spec.get("info") or {}).get("title", ""), "version_api": (spec.get("info") or {}).get("version", ""),
            "formato": f"Swagger {spec['swagger']}" if spec.get("swagger") else f"OpenAPI {spec['openapi']}",
            "api_baseurl": base, "nota_base": nota, "seguridad": esquemas_seguridad(spec), "endpoints": endpoints(spec)}


# ------------------------------------------------------------------ salida
def a_markdown(r, origen):
    lineas = [f"# {r['titulo'] or 'API'} ({r['formato']}, versión {r['version_api'] or '-'})", "", f"Origen: {origen}", "",
              "## Configuración del .env", "",
              f"API_BASEURL={r['api_baseurl'] or '<completar: server + basePath>'}",
              "", "Los endpoints del `.feature` van con el path de la spec tal cual (sin repetir el basePath)."]
    if r["nota_base"]:
        lineas += ["", f"> {r['nota_base']}"]
    lineas += ["", "## Autenticación", ""]
    if r["seguridad"]:
        for nombre, s in r["seguridad"].items():
            usan = sum(1 for e in r["endpoints"] if nombre in e["seguridad"])
            lineas.append(f"- **{nombre}** ({s['tipo']}, {usan} endpoint(s)): `{s['step']}` · variable: {s['variable']}")
    else:
        lineas.append("- La spec no declara autenticación.")
    lineas += ["", f"## Endpoints ({len(r['endpoints'])})", ""]
    for e in r["endpoints"]:
        tags = f" · {', '.join(e['tags'])}" if e["tags"] else ""
        dep = " · DEPRECATED" if e["deprecated"] else ""
        lineas.append(f"### {e['metodo']} {e['path']}{tags}{dep}")
        if e["resumen"]:
            lineas.append(e["resumen"])
        if e["seguridad"]:
            lineas.append(f"- Autenticación: {', '.join(e['seguridad'])}")
        for p in e["parametros"]:
            lineas.append(f"- {p['en']} `{p['nombre']}`: {p['tipo']}{' (obligatorio)' if p['obligatorio'] else ''}")
        b = e["body"]
        if b and b["tipo"] == "json":
            lineas.append(f"- Body JSON ({b['content_type']}){' obligatorio' if b.get('obligatorio') else ''}: "
                          f"`{json.dumps(b['ejemplo'], ensure_ascii=False)[:400]}`")
        elif b and b["tipo"] in ("formulario", "multipart"):
            campos = ", ".join(f"{k} ({v['tipo']}{', obligatorio' if v['obligatorio'] else ''})" for k, v in b["campos"].items())
            paso = "con el formulario:" if b["tipo"] == "formulario" else "(multipart: sin step genérico, ej. subir archivos)"
            lineas.append(f"- Body {b['tipo']} ({b['content_type']}) → `{paso}` · campos: {campos}")
        elif b:
            lineas.append(f"- Body {b['content_type']}: sin step genérico")
        if e["respuestas"]:
            lineas.append("- Respuestas documentadas: " + "; ".join(f"{c} {d}".strip() for c, d in e["respuestas"].items()))
        lineas.append("")
    return "\n".join(lineas).rstrip() + "\n"


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Resume una spec Swagger 2.0 u OpenAPI 3.x para automatizarla con k0lmena")
    ap.add_argument("origen", help="URL o archivo .json/.yaml de la spec")
    ap.add_argument("--salida", help="guarda el resumen en este archivo .md (además de mostrarlo)")
    ap.add_argument("--json", action="store_true", help="muestra el resumen como JSON")
    a = ap.parse_args(argv)
    r = resumir(parsear(leer_texto(a.origen)), a.origen)
    texto = json.dumps(r, ensure_ascii=False, indent=2) if a.json else a_markdown(r, a.origen)
    if a.salida:
        Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
        Path(a.salida).write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())

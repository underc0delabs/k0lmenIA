#!/usr/bin/env python3
"""
Resume un schema GraphQL en pocas líneas: queries, mutations y subscriptions con sus argumentos y
tipos, y los tipos de entrada, enums y objetos que usan (agentes api-mapper y generador-casos-api).

Uso (desde la raíz del repo; en Mac/Linux, python3):
    python scripts/resumir_graphql.py <origen> [--token] [--header "X-Tenant: demo"] [--salida resumen.md]

<origen> puede ser:
  - la URL del endpoint GraphQL: le manda la query de introspección por POST (solo lectura). Con
    --token agrega `Authorization: Bearer <API_TOKEN del .env>` (el token no se imprime);
  - un archivo de schema en SDL (`.graphql` / `.graphqls` / `.gql`);
  - un JSON con el resultado de una introspección (`{"data": {"__schema": ...}}` o `{"__schema": ...}`).

Sirve para no volcar el schema entero en la conversación: el resumen dice qué operaciones hay, qué
argumentos son obligatorios (`!`), qué enums aceptan y qué devuelve cada una. Si el servidor tiene la
introspección deshabilitada (común en producción), lo avisa: pedí el archivo SDL.
"""
import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

def query_introspeccion(niveles=3):
    """Query de introspección; `niveles` de ofType (3 alcanza para [Tipo!]!). Menos niveles para
    servidores con límite de profundidad."""
    ref = "kind name"
    for _ in range(niveles):
        ref = f"kind name ofType {{ {ref} }}"
    return ("query Introspeccion { __schema { queryType { name } mutationType { name } subscriptionType { name } "
            "types { kind name description fields(includeDeprecated: true) { name description isDeprecated "
            "args { name type { ...Ref } defaultValue } type { ...Ref } } inputFields { name type { ...Ref } defaultValue } "
            "enumValues(includeDeprecated: true) { name isDeprecated } } } } "
            f"fragment Ref on __Type {{ {ref} }}")


def _tipo(ref):
    """Tipo de introspección → notación GraphQL ('[String!]!')."""
    if not ref:
        return "?"
    if ref["kind"] in ("NON_NULL", "LIST") and not ref.get("ofType"):
        return "…"  # el servidor limitó la profundidad de la introspección
    if ref["kind"] == "NON_NULL":
        return _tipo(ref.get("ofType")) + "!"
    if ref["kind"] == "LIST":
        return "[" + _tipo(ref.get("ofType")) + "]"
    return ref.get("name") or "?"


def _nombre_base(tipo):
    return re.sub(r"[\[\]!]", "", tipo)


def desde_introspeccion(datos):
    """Resultado de introspección → modelo {'operaciones': {...}, 'tipos': {...}}."""
    esquema = (datos.get("data") or datos).get("__schema")
    if not esquema:
        raise ValueError("El JSON no tiene __schema (¿la introspección devolvió errores?).")
    raices = {"query": (esquema.get("queryType") or {}).get("name"),
              "mutation": (esquema.get("mutationType") or {}).get("name"),
              "subscription": (esquema.get("subscriptionType") or {}).get("name")}
    tipos = {}
    for t in esquema.get("types") or []:
        if t["name"].startswith("__"):
            continue
        tipos[t["name"]] = {
            "kind": t["kind"],
            "campos": [{"nombre": f["name"], "tipo": _tipo(f["type"]), "deprecado": f.get("isDeprecated", False),
                        "args": [{"nombre": a["name"], "tipo": _tipo(a["type"]), "defecto": a.get("defaultValue")}
                                 for a in f.get("args") or []]} for f in t.get("fields") or []]
                      + [{"nombre": f["name"], "tipo": _tipo(f["type"]), "args": [], "defecto": f.get("defaultValue")}
                         for f in t.get("inputFields") or []],
            "valores": [e["name"] for e in t.get("enumValues") or []],
        }
    return {"raices": raices, "tipos": tipos}


_ESCALARES = {"String", "Int", "Float", "Boolean", "ID"}


def desde_sdl(texto):
    """Schema SDL → el mismo modelo que desde_introspeccion (lectura simple, sin directivas)."""
    texto = re.sub(r'"""[\s\S]*?"""', "", texto)           # descripciones en bloque
    texto = re.sub(r'(?m)^\s*"[^"\n]*"\s*$', "", texto)    # descripciones de una línea
    texto = re.sub(r"#.*", "", texto)
    texto = re.sub(r"=\s*\{[^{}]*\}", "= «objeto»", texto)  # defaults de objeto: no confundir con el cierre
    raices = {"query": "Query", "mutation": "Mutation", "subscription": "Subscription"}
    m = re.search(r"\bschema\s*\{([^}]*)\}", texto)
    if m:
        for op, nombre in re.findall(r"(query|mutation|subscription)\s*:\s*(\w+)", m.group(1)):
            raices[op] = nombre
    tipos = {}
    patron = re.compile(r"\b(extend\s+)?(type|input|interface|enum)\s+(\w+)[^{]*\{([^}]*)\}")
    for _, clase, nombre, cuerpo in patron.findall(texto):
        kind = {"type": "OBJECT", "input": "INPUT_OBJECT", "interface": "INTERFACE", "enum": "ENUM"}[clase]
        t = tipos.setdefault(nombre, {"kind": kind, "campos": [], "valores": []})
        if clase == "enum":
            t["valores"] += re.findall(r"\b([A-Za-z_]\w*)\b(?:\s*@\w+(?:\([^)]*\))?)*", cuerpo)
            continue
        cuerpo = re.sub(r"\s+", " ", cuerpo)
        for campo in re.finditer(r"(\w+)\s*(\(([^)]*)\))?\s*:\s*([\w\[\]!]+)(\s*=\s*[^\s@]+)?", cuerpo):
            args = [{"nombre": a, "tipo": ti, "defecto": (d or "").lstrip("= ").strip() or None}
                    for a, ti, d in re.findall(r"(\w+)\s*:\s*([\w\[\]!]+)(\s*=\s*[^,)\s]+)?", campo.group(3) or "")]
            t["campos"].append({"nombre": campo.group(1), "tipo": campo.group(4), "args": args,
                                "deprecado": False})
    for escalar in re.findall(r"\bscalar\s+(\w+)", texto):
        tipos.setdefault(escalar, {"kind": "SCALAR", "campos": [], "valores": []})
    raices = {op: (n if n in tipos else None) for op, n in raices.items()}
    return {"raices": raices, "tipos": tipos}


def resumir(modelo):
    """Modelo → texto Markdown corto."""
    tipos = modelo["tipos"]
    lineas, usados = [], set()
    for op in ("query", "mutation", "subscription"):
        raiz = modelo["raices"].get(op)
        if not raiz or raiz not in tipos:
            continue
        campos = tipos[raiz]["campos"]
        lineas += [f"## {op.capitalize()} ({len(campos)})", ""]
        for c in campos:
            args = ", ".join(f"{a['nombre']}: {a['tipo']}" + (f" = {a['defecto']}" if a.get("defecto") else "")
                             for a in c["args"])
            depre = " (deprecada)" if c.get("deprecado") else ""
            lineas.append(f"- `{c['nombre']}({args})` → `{c['tipo']}`{depre}" if args else f"- `{c['nombre']}` → `{c['tipo']}`{depre}")
            usados.add(_nombre_base(c["tipo"]))
            usados.update(_nombre_base(a["tipo"]) for a in c["args"])
        lineas.append("")
    # tipos alcanzables desde las operaciones (un nivel más para objetos de retorno)
    pendientes, vistos = list(usados), set()
    while pendientes:
        n = pendientes.pop()
        if n in vistos or n not in tipos:
            continue
        vistos.add(n)
        if tipos[n]["kind"] in ("INPUT_OBJECT", "OBJECT", "INTERFACE"):
            pendientes += [_nombre_base(c["tipo"]) for c in tipos[n]["campos"]]
    secciones = [("INPUT_OBJECT", "Tipos de entrada"), ("ENUM", "Enums"), ("OBJECT", "Objetos"), ("INTERFACE", "Interfaces")]
    for kind, titulo in secciones:
        grupo = sorted(n for n in vistos if tipos[n]["kind"] == kind and n not in modelo["raices"].values())
        if not grupo:
            continue
        lineas += [f"## {titulo} ({len(grupo)})", ""]
        for n in grupo:
            t = tipos[n]
            if kind == "ENUM":
                lineas.append(f"- `{n}`: {', '.join(t['valores'])}")
            else:
                lineas.append(f"- `{n}` {{ " + ", ".join(f"{c['nombre']}: {c['tipo']}" for c in t["campos"]) + " }")
        lineas.append("")
    escalares = sorted(n for n in tipos if tipos[n]["kind"] == "SCALAR" and n not in _ESCALARES)
    if escalares:
        lineas += [f"Escalares propios: {', '.join(escalares)}", ""]
    return "\n".join(lineas)


def introspectar(url, headers):
    try:
        import requests
    except ImportError:
        sys.exit("Falta la librería requests: pip install -r requirements.txt")
    mensajes = ""
    for niveles in (3, 2, 1, 0):  # si el servidor limita la profundidad, se reintenta más corta
        r = requests.post(url, json={"query": query_introspeccion(niveles), "operationName": "Introspeccion"},
                          headers={"Content-Type": "application/json", **headers}, timeout=60)
        try:
            datos = r.json()
        except ValueError:
            sys.exit(f"El endpoint respondió {r.status_code} sin JSON: ¿es la URL de GraphQL?")
        if (datos.get("data") or {}).get("__schema"):
            return datos
        mensajes = "; ".join(str(e.get("message")) for e in datos.get("errors") or [])
        if "depth" not in mensajes.lower() and "complex" not in mensajes.lower():
            break
    sys.exit(f"La introspección devolvió errores ({mensajes}). Si está deshabilitada, pedí el schema en SDL (.graphql).")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Resume un schema GraphQL (introspección, SDL o JSON)")
    ap.add_argument("origen", help="URL del endpoint GraphQL, archivo .graphql (SDL) o JSON de introspección")
    ap.add_argument("--token", action="store_true", help="manda Authorization: Bearer con API_TOKEN del .env")
    ap.add_argument("--header", action="append", default=[], help='header extra, "Nombre: valor" (repetible)')
    ap.add_argument("--salida", help="guarda el resumen en este archivo .md (además de mostrarlo)")
    a = ap.parse_args(argv)
    if re.match(r"^https?://", a.origen):
        headers = dict(h.split(":", 1) for h in a.header)
        headers = {k.strip(): v.strip() for k, v in headers.items()}
        if a.token:
            from _env import leer_env
            token = leer_env().get("API_TOKEN")
            if not token:
                sys.exit("Pediste --token pero falta API_TOKEN en el .env de la raíz.")
            headers["Authorization"] = f"Bearer {token}"
        modelo = desde_introspeccion(introspectar(a.origen, headers))
        origen = a.origen
    else:
        ruta = Path(a.origen)
        if not ruta.exists():
            sys.exit(f"No existe {ruta}.")
        texto = ruta.read_text(encoding="utf-8-sig")
        modelo = desde_introspeccion(json.loads(texto)) if ruta.suffix.lower() == ".json" else desde_sdl(texto)
        origen = ruta.as_posix()
    resumen = f"# Schema GraphQL\n\nOrigen: {origen}\n\n" + resumir(modelo)
    if "…" in resumen:
        resumen += ("\n> El servidor limita la profundidad de la introspección: algunos tipos quedaron como `[…]`. "
                    "Para el detalle completo, pedí el schema en SDL (.graphql).\n")
    print(resumen)
    if a.salida:
        Path(a.salida).write_text(resumen, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

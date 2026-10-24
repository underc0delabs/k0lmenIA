#!/usr/bin/env python3
"""
Elige qué casos de prueba correr para un cambio (agente selector-casos-de-prueba): cruza el cambio con
el inventario de casos y arma una selección priorizada por riesgo, con el comando para correr lo
automatizado y la lista de lo manual.

Uso (desde la raíz del repo):
    python scripts/seleccionar_casos.py [--git main..feature/pagos --repo ../mi-app] [--archivos a.ts,b.ts]
        [--historias HU-003,PROJ-55] [--texto "notas de la release"] [--texto-archivo notas.md]
        [--cambios cambios.json] [--presupuesto-min 60] [--nombre release-2.4] [--analisis analisis.json]
    python scripts/seleccionar_casos.py --solo-informe --nombre release-2.4
        → vuelve a aplicar el analisis.json del agente y regenera el informe, sin recalcular.

El cambio puede venir de (se combinan):
  --git RANGO      archivos cambiados, mensajes de commit (con sus keys de Jira) y nombres de las funciones
                   tocadas, del repositorio de la aplicación (--repo; por defecto el actual).
  --archivos       lista de archivos cambiados (de un PR, por ejemplo).
  --historias      historias o issues afectados (HU-XXX o keys de Jira/Azure DevOps).
  --texto          notas de la release, la descripción del PR o el resumen de los issues.
  --cambios        JSON que arma el agente después de leer el PR o Jira:
                   {"titulo": "...", "historias": ["HU-003"], "palabras": ["pago", "tarjeta"],
                    "archivos": ["src/checkout/pago.ts"], "texto": "..."}
Inventario de casos (lo que exista): casos manuales (output/casos-de-prueba/manuales/casos-HU-XXX.xlsx),
escenarios BDD (output/casos-de-prueba/bdd/*.feature) y automatización de k0lmena
(herramientas/k0lmena/{web,api,mobile}/features), con su último resultado (npm test), los inestables
(output/fallos) y los bugs (output/reportes-bug). Opcional: input/mapa-componentes.json relaciona
carpetas del código con historias y palabras: {"rutas": {"src/checkout/": ["HU-003", "pago"]}}.

Cada caso recibe un puntaje (historia afectada, coincidencia de palabras con el cambio —con sinónimos
en español e inglés—, prioridad, último resultado, inestable, bugs abiertos) y queda en un grupo:
Imprescindible · Recomendado · Regresión mínima (smoke y prioridad Crítica) · No seleccionado.
Además marca los cambios que no tocan ningún caso (cambios sin cobertura).

Deja output/seleccion-casos/<nombre>/ con seleccion.json, seleccion.csv (para ejecutar a mano) e
informe-seleccion.html. Con el mismo nombre, la corrida anterior pasa a historial/ (últimas 5).
"""
import argparse
import csv
import datetime
import glob
import json
import math
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "scripts" / "gestion"))
import recolectar_resultados as rec  # noqa: E402
from estimacion import estimar_caso  # noqa: E402
import _historial  # noqa: E402

GRUPOS = ["Imprescindible", "Recomendado", "Regresión mínima", "No seleccionado"]
PRIO_PUNTOS = {"Crítica": 15, "Alta": 10, "Media": 4, "Baja": 0}
RE_HU = re.compile(r"\bHU-\d+\b", re.I)
RE_KEY = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")
RE_CP = re.compile(r"^CP(-API)?-\d+$")

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


# ------------------------------------------------------------------ el cambio
def _git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} falló: {r.stderr.strip()[:300]}")
    return r.stdout


def rangos_git(rango):
    """(rango para git diff, rango para git log). `A..B` o `A...B`: el diff va desde la base común
    (`A...B`, así no entran los cambios que A sumó después) y el log son los commits de B que no están
    en A (`A..B`). Un solo commit o ref se deja como está."""
    m = re.fullmatch(r"(.*?)\.{2,3}(.*)", rango.strip())
    if not m:
        return rango, rango
    base, punta = m.group(1) or "HEAD", m.group(2) or "HEAD"
    return f"{base}...{punta}", f"{base}..{punta}"


def leer_cambio(a):
    cambio = {"titulo": "", "archivos": [], "historias": set(), "keys": set(), "commits": [], "funciones": [], "texto": "", "palabras": [],
              "fuentes": []}
    if a.git:
        repo = Path(a.repo or ".").resolve()
        r_diff, r_log = rangos_git(a.git)
        cambio["archivos"] += [l.strip() for l in _git(repo, "diff", "--name-only", r_diff).splitlines() if l.strip()]
        msgs = _git(repo, "log", "--format=%h%x09%s%x09%b%x1e", r_log)
        for bloque in msgs.split("\x1e"):
            partes = bloque.strip().split("\t")
            if len(partes) >= 2:
                cambio["commits"].append({"hash": partes[0], "mensaje": partes[1], "cuerpo": partes[2].strip() if len(partes) > 2 else ""})
        # Funciones y clases tocadas (encabezados de los hunks: "@@ -10,3 +10,4 @@ function validarTarjeta(").
        diff = _git(repo, "diff", "--unified=0", r_diff)
        cambio["funciones"] = sorted({m.strip() for m in re.findall(r"^@@[^@]*@@\s*(.+)$", diff, re.M)})[:80]
        cambio["fuentes"].append(f"git {a.git} ({repo.name})")
    if a.archivos:
        cambio["archivos"] += [x.strip() for x in a.archivos.split(",") if x.strip()]
        cambio["fuentes"].append("lista de archivos")
    if a.historias:
        for h in a.historias.split(","):
            h = h.strip().upper()
            (cambio["historias"] if RE_HU.fullmatch(h) else cambio["keys"]).add(h)
        cambio["fuentes"].append("historias del pedido")
    textos = []
    if a.texto:
        textos.append(a.texto)
    if a.texto_archivo:
        textos.append(Path(a.texto_archivo).read_text(encoding="utf-8"))
        cambio["fuentes"].append(Path(a.texto_archivo).name)
    if a.cambios:
        c = json.loads(Path(a.cambios).read_text(encoding="utf-8"))
        cambio["titulo"] = c.get("titulo") or cambio["titulo"]
        cambio["archivos"] += c.get("archivos") or []
        for h in c.get("historias") or []:
            (cambio["historias"] if RE_HU.fullmatch(h.upper()) else cambio["keys"]).add(h.upper())
        cambio["palabras"] += c.get("palabras") or []
        if c.get("texto"):
            textos.append(c["texto"])
        cambio["fuentes"].append(Path(a.cambios).name)
    if a.texto:
        cambio["fuentes"].append("texto del pedido")
    cambio["texto"] = "\n".join(textos)
    for c in cambio["commits"]:
        for m in RE_KEY.findall(f'{c["mensaje"]} {c["cuerpo"]}'):
            (cambio["historias"] if RE_HU.fullmatch(m) else cambio["keys"]).add(m.upper())
    for m in RE_KEY.findall(cambio["texto"]):
        (cambio["historias"] if RE_HU.fullmatch(m) else cambio["keys"]).add(m.upper())
    cambio["archivos"] = list(dict.fromkeys(cambio["archivos"]))
    return cambio


def keys_a_historias(keys):
    """Keys de Jira/Azure → HU locales, por la trazabilidad de gestión y las fichas de contexto."""
    mapa = {}
    for archivo in glob.glob(str(RAIZ / "output" / "gestion" / "HU-*.json")):
        try:
            t = json.loads(Path(archivo).read_text(encoding="utf-8"))
        except ValueError:
            continue
        hu = Path(archivo).name.split("-")[0] + "-" + Path(archivo).name.split("-")[1]
        for k in [t.get("historia_key"), t.get("issue"), t.get("historia")] + [v.get("historia") for v in (t.get("casos") or {}).values() if isinstance(v, dict)]:
            if k:
                mapa[str(k).upper()] = hu.upper()
    for archivo in glob.glob(str(RAIZ / "output" / "contexto" / "contexto-HU-*.md")):
        hu = re.search(r"(HU-\d+)", archivo).group(1).upper()
        for k in RE_KEY.findall(Path(archivo).read_text(encoding="utf-8")[:4000]):
            if not RE_HU.fullmatch(k):
                mapa.setdefault(k.upper(), hu)
    return {mapa[k] for k in keys if k in mapa}


def mapa_componentes():
    arch = RAIZ / "input" / "mapa-componentes.json"
    if not arch.exists():
        return {}
    try:
        return json.loads(arch.read_text(encoding="utf-8")).get("rutas") or {}
    except ValueError:
        print(f"[!] {arch.name} no es un JSON válido: lo ignoro.", file=sys.stderr)
        return {}


# ------------------------------------------------------------------ el inventario
def _titulo_feature(ruta):
    m = re.search(r"^\s*Feature:\s*(.+)$", Path(ruta).read_text(encoding="utf-8-sig"), re.M)
    return m.group(1).strip() if m else ""


def inventario():
    from lectores import leer_feature, leer_xlsx
    casos = {}

    def caso(hu, cid):
        k = f"{hu}:{cid}"
        return casos.setdefault(k, {"clave": k, "historia": hu, "id": cid, "titulo": "", "prioridad": "", "etiquetas": set(), "texto": [],
                                    "titulo_historia": "", "fuentes": [], "automatizado": [], "pasos": 0, "resultado": None,
                                    "duracion_s": None, "inestable": False, "bugs": [], "minutos_manual": None})

    for x in sorted(glob.glob(str(RAIZ / "output" / "casos-de-prueba" / "manuales" / "casos-HU-*.xlsx"))):
        hu = re.search(r"(HU-\d+)", x).group(1).upper()
        try:
            for c in leer_xlsx(x):
                k = caso(hu, c["id"])
                k["titulo"] = k["titulo"] or c["titulo"]
                k["prioridad"] = k["prioridad"] or c["prioridad"]
                k["etiquetas"].update(c.get("etiquetas") or [])
                k["texto"] += [c["titulo"], c["titulo"], c.get("descripcion", ""), c.get("precondiciones", "")] + \
                    [f'{p.get("accion", "")} {p.get("resultado", "")}' for p in c.get("pasos") or []]
                k["pasos"] = max(k["pasos"], len(c.get("pasos") or []))
                k["minutos_manual"] = estimar_caso(c)["minutos"]
                if "Manual" not in k["fuentes"]:
                    k["fuentes"].append("Manual")
        except Exception as ex:  # una planilla con otro formato no corta la selección
            print(f"[!] No pude leer {Path(x).name}: {ex}", file=sys.stderr)

    def de_features(globo, fuente, suite=None):
        for x in sorted(glob.glob(str(RAIZ / globo), recursive=True)):
            try:
                escenarios = leer_feature(x)
            except Exception:
                continue
            tit = _titulo_feature(x)
            for c in escenarios:
                tags = [t.upper() for t in c["etiquetas"]]
                hu = next((t for t in tags if RE_HU.fullmatch(t)), None)
                m = re.search(r"(HU-\d+)", Path(x).name, re.I)
                hu = hu or (m.group(1).upper() if m else "SIN-HU")
                k = caso(hu, c["id"])
                k["titulo"] = k["titulo"] or c["titulo"]
                k["titulo_historia"] = k["titulo_historia"] or tit
                if c.get("prioridad") and not k["prioridad"]:
                    # Solo se confía en la prioridad del .feature si viene de un tag explícito
                    # (@critica/@alta/@media/@baja o @smoke); si no, se deja que gane la del caso manual.
                    tiene_tag = any(t.lower() in ("critica", "crítica", "alta", "media", "baja", "smoke") for t in c["etiquetas"])
                    k["prioridad"] = c["prioridad"] if tiene_tag else ""
                k["etiquetas"].update(c["etiquetas"])
                k["texto"] += [c["titulo"], c["titulo"], c.get("gherkin", ""), tit]
                k["pasos"] = max(k["pasos"], len([l for l in c.get("gherkin", "").splitlines() if re.match(r"\s*(Given|When|Then|And|But|\*)\b", l)]))
                if not k["minutos_manual"]:
                    k["minutos_manual"] = estimar_caso(c)["minutos"]
                if suite:
                    k["automatizado"].append({"suite": suite, "archivo": Path(x).relative_to(RAIZ).as_posix(),
                                              "bloqueado": any(t.lower() == "bloqueado" for t in c["etiquetas"])})
                if fuente not in k["fuentes"]:
                    k["fuentes"].append(fuente)

    de_features("output/casos-de-prueba/bdd/*.feature", "BDD")
    for suite in ("web", "api", "mobile"):
        de_features(f"herramientas/k0lmena/{suite}/features/**/*.feature", "Automatizado", suite)

    # Último resultado y duración (npm test) y ejecuciones en vivo.
    for r in sorted(rec.de_ejecuciones(None) + rec.de_cucumber(None), key=lambda r: r.get("momento") or 0):
        if not r.get("id") or not RE_CP.match(str(r["id"])):
            continue
        for k in casos.values():
            if k["id"] == r["id"] and (not r.get("titulo") or r["titulo"] == k["titulo"] or len([x for x in casos.values() if x["id"] == r["id"]]) == 1):
                k["resultado"] = {"estado": r["estado"], "fuente": r["fuente"]}
    for suite in ("web", "api", "mobile"):
        rep = rec.K0 / suite / "cucumber-report.json"
        try:
            features = json.loads(rep.read_text(encoding="utf-8") or "[]") if rep.exists() else []
        except ValueError:
            features = []
        for f in features:
            for esc in f.get("elements") or []:
                tags = [t["name"].lstrip("@").upper() for t in (f.get("tags") or []) + (esc.get("tags") or [])]
                hu = next((t for t in tags if RE_HU.fullmatch(t)), None)
                cp = next((t for t in tags if RE_CP.match(t)), None)
                k = casos.get(f"{hu}:{cp}")
                if k:
                    k["duracion_s"] = round(sum((p.get("result") or {}).get("duration") or 0 for p in esc.get("steps") or []) / 1e9, 1)
    for arch in glob.glob(str(RAIZ / "output" / "fallos" / "*" / "fallos.json")):
        try:
            d = json.loads(Path(arch).read_text(encoding="utf-8"))
        except ValueError:
            continue
        for f in d.get("fallos") or []:
            k = casos.get(f'{(f.get("historia") or "").upper()}:{f.get("caso")}')
            if k and f.get("categoria") == "Inestable (flaky)":
                k["inestable"] = True
    for b in rec.de_bugs(None):
        if b["estado"].lower() not in rec.ABIERTOS:
            continue
        for k in casos.values():
            if k["historia"] in (b.get("historia") or ""):
                k["bugs"].append(b["id"])
    return list(casos.values())


# ------------------------------------------------------------------ puntaje y grupos
def seleccionar(cambio, casos, presupuesto=None, min_por_paso=1.5):
    rutas = mapa_componentes()
    afectadas = set(cambio["historias"]) | keys_a_historias(cambio["keys"])
    # Palabras del cambio con su peso (archivos y funciones pesan más que el texto libre).
    pesos = Counter()
    origen = {}

    def sumar(texto, peso, de):
        for t in tokens(texto):
            pesos[t] += peso
            origen.setdefault(t, set()).add(de)

    for f in cambio["archivos"]:
        sumar(f, 1.0, f)
        for ruta, valores in rutas.items():
            if f.replace("\\", "/").startswith(ruta.rstrip("*")):
                for v in valores:
                    if RE_HU.fullmatch(str(v).upper()):
                        afectadas.add(str(v).upper())
                    else:
                        sumar(v, 1.5, f"mapa: {ruta}")
    for fn in cambio["funciones"]:
        sumar(fn, 0.6, "función tocada")
    for c in cambio["commits"]:
        sumar(c["mensaje"], 0.8, f'commit {c["hash"]}')
    for p in cambio["palabras"]:
        sumar(p, 1.5, "palabra clave")
    sumar(cambio["titulo"], 1.0, "título")
    sumar(cambio["texto"], 0.5, "texto")

    # IDF sobre el inventario: una palabra que está en todos los casos no distingue nada.
    docs = []
    for c in casos:
        toks = Counter(tokens(" ".join(c["texto"] + [c["titulo"], c.get("titulo_historia", ""), " ".join(c["etiquetas"])])))
        docs.append(toks)
    n = len(docs) or 1
    df = Counter(t for d in docs for t in d)
    idf = {t: math.log((n + 1) / (df[t] + 0.5)) for t in df}

    usados = Counter()
    for c, toks in zip(casos, docs):
        razones = []
        p = 0
        if c["historia"] in afectadas:
            p += 60
            razones.append(f'La historia {c["historia"]} está en el cambio')
        coinciden = sorted({t for t in pesos if t in toks}, key=lambda t: -idf.get(t, 0) * pesos[t])
        crudo = sum(idf.get(t, 0) * min(2, toks[t]) * pesos[t] for t in coinciden)
        kw = round(45 * (1 - math.exp(-crudo / 6))) if crudo else 0
        if kw:
            p += kw
            usados.update(coinciden)
            ej = sorted({o for t in coinciden[:3] for o in origen.get(t, [])})[:2]
            razones.append(f'Coincide con el cambio en: {", ".join(coinciden[:5])}' + (f' ({"; ".join(ej)})' if ej else ""))
        prio = c["prioridad"] or "Media"
        if PRIO_PUNTOS.get(prio):
            p += PRIO_PUNTOS[prio]
            if prio in ("Crítica", "Alta"):
                razones.append(f"Prioridad {prio}")
        if c["resultado"] and c["resultado"]["estado"] == "Fallido":
            p += 10
            razones.append(f'Falló en la última corrida ({c["resultado"]["fuente"]})')
        if c["inestable"]:
            p += 6
            razones.append("Es inestable (flaky)")
        if c["bugs"]:
            p += 5
            razones.append(f'Hay bugs abiertos en la historia: {", ".join(c["bugs"][:3])}')
        c["puntaje"] = min(100, p)
        c["coincidencias"] = coinciden[:8]
        c["razones"] = razones
        smoke = any(t.lower() == "smoke" for t in c["etiquetas"]) or prio == "Crítica"
        if c["historia"] in afectadas or c["puntaje"] >= 60:
            c["grupo"] = "Imprescindible"
        elif c["puntaje"] >= 35 and (kw or c["historia"] in afectadas):
            c["grupo"] = "Recomendado"
        elif smoke:
            c["grupo"] = "Regresión mínima"
            c["razones"].append("Es de humo o de prioridad Crítica: se corre siempre")
        else:
            c["grupo"] = "No seleccionado"
        activos = [x for x in c["automatizado"] if not x["bloqueado"]]
        c["tipo"] = "Automatizado" if activos else "Manual"
        c["suite"] = activos[0]["suite"] if activos else None
        # Automatizado: lo que tardó en la última corrida. Manual: la fórmula de scripts/estimacion.py.
        c["minutos"] = max(0.1, round((c["duracion_s"] or 30) / 60, 1)) if activos else (
            c.get("minutos_manual") or round(max(2, (c["pasos"] or 3) * min_por_paso), 1))

    # Presupuesto de tiempo: se mantienen los imprescindibles y se completan los demás por puntaje.
    if presupuesto:
        usado = sum(c["minutos"] for c in casos if c["grupo"] == "Imprescindible")
        for c in sorted([c for c in casos if c["grupo"] in ("Recomendado", "Regresión mínima")], key=lambda c: -c["puntaje"]):
            if usado + c["minutos"] <= presupuesto:
                usado += c["minutos"]
            else:
                c["grupo"] = "No seleccionado"
                c["razones"].append(f"Quedó afuera por el presupuesto de {presupuesto} min")

    # Cambios sin cobertura: archivos cuyo contenido (palabras) no aparece en ningún caso.
    sin_cobertura = []
    for f in cambio["archivos"]:
        ts = [t for t in set(tokens(f)) if not usados.get(t)]
        if ts and not any(usados.get(t) for t in set(tokens(f))):
            sin_cobertura.append({"archivo": f, "palabras": sorted(ts)[:6]})
    return afectadas, sin_cobertura, pesos


def aplicar_ajustes(casos, analisis):
    for clave, aj in (analisis.get("ajustes") or {}).items():
        for c in casos:
            if c["clave"].upper() == clave.upper() and aj.get("grupo") in GRUPOS:
                c["grupo_original"] = c.get("grupo_original") or c["grupo"]
                c["grupo"] = aj["grupo"]
                c["razones"] = [r for r in c["razones"] if not r.startswith("Ajuste del análisis")] + [f'Ajuste del análisis: {aj.get("motivo", "")}'.strip()]


def comandos(casos):
    sel = [c for c in casos if c["grupo"] != "No seleccionado" and c["tipo"] == "Automatizado"]
    salida = []
    for suite in ("web", "api", "mobile"):
        porhu = {}
        for c in sel:
            if c["suite"] == suite:
                porhu.setdefault(c["historia"], []).append(c["id"])
        if not porhu:
            continue
        partes = []
        for hu, cps in sorted(porhu.items()):
            cps = sorted(set(cps))
            inner = " or ".join(f"@{x}" for x in cps)
            partes.append(f"(@{hu} and ({inner}))" if len(cps) > 1 else f"(@{hu} and @{cps[0]})")
        tags = " or ".join(partes)
        salida.append({"suite": suite, "tags": tags, "casos": sum(len(set(v)) for v in porhu.values()),
                       "bash": f'TAGS="{tags}" npm test -- {suite}', "powershell": f'$env:TAGS="{tags}"; npm test -- {suite}'})
    return salida


def resumir(casos, sin_cobertura):
    sel = [c for c in casos if c["grupo"] != "No seleccionado"]
    total_min = sum(c["minutos"] for c in casos)
    sel_min = sum(c["minutos"] for c in sel)
    return {"casos": len(casos), "seleccionados": len(sel), "por_grupo": {g: sum(1 for c in casos if c["grupo"] == g) for g in GRUPOS},
            "automatizados": sum(1 for c in sel if c["tipo"] == "Automatizado"), "manuales": sum(1 for c in sel if c["tipo"] == "Manual"),
            "minutos_seleccion": round(sel_min, 1), "minutos_total": round(total_min, 1),
            "ahorro_pct": round((1 - sel_min / total_min) * 100) if total_min else 0,
            "historias": len({c["historia"] for c in casos}), "historias_seleccionadas": len({c["historia"] for c in sel}),
            "sin_cobertura": len(sin_cobertura)}


def escribir(carpeta, datos):
    datos["resumen"] = resumir(datos["casos"], datos["sin_cobertura"])
    datos["comandos"] = comandos(datos["casos"])
    (carpeta / "seleccion.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2, default=list), encoding="utf-8")
    with open(carpeta / "seleccion.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Grupo", "Historia", "ID", "Título", "Tipo", "Suite", "Prioridad", "Puntaje", "Minutos", "Último resultado", "Por qué"])
        orden = {g: i for i, g in enumerate(GRUPOS)}
        for c in sorted(datos["casos"], key=lambda c: (orden[c["grupo"]], -c["puntaje"])):
            if c["grupo"] == "No seleccionado":
                continue
            w.writerow([c["grupo"], c["historia"], c["id"], c["titulo"], c["tipo"], c["suite"] or "", c["prioridad"] or "Media", c["puntaje"],
                        c["minutos"], (c["resultado"] or {}).get("estado", ""), " · ".join(c["razones"])])


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Selección de casos de prueba para un cambio")
    ap.add_argument("--git", help="rango de commits (main..rama, v2.3..v2.4, HEAD~3..HEAD)")
    ap.add_argument("--repo", help="repositorio de la aplicación (por defecto, el actual)")
    ap.add_argument("--archivos", help="archivos cambiados, separados por comas")
    ap.add_argument("--historias", help="historias o keys afectadas, separadas por comas")
    ap.add_argument("--texto", help="notas de la release o descripción del cambio")
    ap.add_argument("--texto-archivo", help="archivo con las notas o la descripción")
    ap.add_argument("--cambios", help="cambios.json armado por el agente")
    ap.add_argument("--presupuesto-min", type=float, help="tiempo máximo de la selección, en minutos")
    ap.add_argument("--min-por-paso", type=float, default=1.5, help="minutos por paso de un caso manual (estimación)")
    ap.add_argument("--nombre", help="nombre de la selección (carpeta de salida)")
    ap.add_argument("--analisis", help="analisis.json del agente (por defecto, el de la carpeta si existe)")
    ap.add_argument("--solo-informe", action="store_true", help="aplica el análisis y regenera el informe sin recalcular")
    ap.add_argument("--salida", help="carpeta (por defecto output/seleccion-casos/<nombre>)")
    a = ap.parse_args()

    nombre = a.nombre or (re.sub(r"[^\w.-]+", "_", a.git).strip("_") if a.git else f'cambio-{datetime.date.today().isoformat()}')
    carpeta = Path(a.salida) if a.salida else RAIZ / "output" / "seleccion-casos" / nombre
    analisis_arch = Path(a.analisis) if a.analisis else carpeta / "analisis.json"
    if a.solo_informe:
        datos = json.loads((carpeta / "seleccion.json").read_text(encoding="utf-8"))
    else:
        if not any([a.git, a.archivos, a.historias, a.texto, a.texto_archivo, a.cambios]):
            sys.exit("Decime qué cambió: --git, --archivos, --historias, --texto, --texto-archivo o --cambios.")
        cambio = leer_cambio(a)
        casos = inventario()
        if not casos:
            sys.exit("No encontré casos de prueba (ni manuales, ni BDD, ni automatizados en k0lmena): generalos primero.")
        afectadas, sin_cobertura, pesos = seleccionar(cambio, casos, a.presupuesto_min, a.min_por_paso)
        for c in casos:
            c["etiquetas"] = sorted(c["etiquetas"])
            c.pop("texto", None)
        # La selección anterior con el mismo nombre pasa a historial/<fecha>/ (se guardan las últimas 5).
        _historial.archivar(carpeta, ["seleccion.json", "seleccion.csv", "informe-seleccion.html", "analisis.json", "cambios.json"], "seleccion.json")
        carpeta.mkdir(parents=True, exist_ok=True)
        orden = {g: i for i, g in enumerate(GRUPOS)}
        casos.sort(key=lambda c: (orden[c["grupo"]], -c["puntaje"], c["historia"], c["id"]))
        datos = {"nombre": nombre, "fecha": datetime.datetime.now().isoformat(timespec="seconds"), "presupuesto_min": a.presupuesto_min,
                 "cambio": {"titulo": cambio["titulo"], "fuentes": cambio["fuentes"], "archivos": cambio["archivos"], "commits": cambio["commits"],
                            "funciones": cambio["funciones"][:30], "historias": sorted(cambio["historias"]), "keys": sorted(cambio["keys"]),
                            "texto": cambio["texto"][:3000], "palabras": [{"palabra": t, "peso": round(p, 2)} for t, p in pesos.most_common(25)]},
                 "historias_afectadas": sorted(afectadas), "sin_cobertura": sin_cobertura, "casos": casos}
    analisis = json.loads(analisis_arch.read_text(encoding="utf-8")) if analisis_arch.exists() else {}
    if analisis:
        aplicar_ajustes(datos["casos"], analisis)
    escribir(carpeta, datos)
    r = datos["resumen"]
    donde = carpeta.resolve()
    donde = donde.relative_to(RAIZ).as_posix() if donde.is_relative_to(RAIZ) else str(donde)
    print(f'Casos: {r["casos"]} · seleccionados: {r["seleccionados"]} ({r["automatizados"]} automatizados, {r["manuales"]} manuales) · '
          f'{r["minutos_seleccion"]} de {r["minutos_total"]} min (ahorro {r["ahorro_pct"]} %)')
    for g in GRUPOS:
        print(f'  {g}: {r["por_grupo"][g]}')
    if datos["sin_cobertura"]:
        print(f'Cambios sin casos: {len(datos["sin_cobertura"])}')
    for c in datos["comandos"]:
        print(f'  {c["suite"]}: {c["bash"]}')
    args = [sys.executable, str(RAIZ / "scripts" / "generar_informe_seleccion.py"), str(carpeta / "seleccion.json"), str(carpeta / "informe-seleccion.html")]
    if analisis_arch.exists():
        args += ["--analisis", str(analisis_arch)]
    res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:  # p. ej. un analisis.json mal formado: el agente tiene que enterarse, no seguir de largo
        print(res.stderr.strip() or res.stdout.strip(), file=sys.stderr)
        sys.exit("No se pudo armar el informe HTML (revisá el analisis.json).")
    print(res.stdout.strip() or res.stderr.strip())
    print(f"Datos: {donde}/seleccion.json · planilla: {donde}/seleccion.csv")


if __name__ == "__main__":
    main()

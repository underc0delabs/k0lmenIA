#!/usr/bin/env python3
"""
Los planes de k0lmenIA en esta PC: qué está instalado, a qué planes tiene acceso la persona y qué suma cada uno.

Uso (como plugin: `k0lmenia planes …`; en el repo clonado: `npm run planes -- …`):
    planes                      tabla con cada plan (instalado, disponible o bloqueado)
    planes --json               lo mismo en JSON (lo usa el skill /k0lmenia:setup)
    planes --instalar pro       instala el plugin de un plan (claude plugin install k0lmenia-pro@k0lmenia)
    planes --aviso              una línea para el inicio de la sesión si hay un plan disponible sin instalar
                                (revisa como mucho una vez por día; nunca falla)

Cómo se sabe cada cosa:
  - qué trae cada plan: catalogo-planes.json (lo arma scripts/catalogo_planes.py en el repo de Empresa);
  - si está instalado: cada plugin pago se registra al iniciar la sesión en ~/.k0lmenia/planes.json (su carpeta);
  - si hay acceso: `git ls-remote` contra el repo del plan, con las mismas credenciales de git que usa Claude Code para
    instalar plugins (nunca pide usuario ni contraseña: si no hay credenciales, el plan sale bloqueado o desconocido).
"""
import argparse
import html as html_lib
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = RAIZ / "catalogo-planes.json"
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()
UN_DIA = 24 * 3600


def registro_path():
    return Path(os.environ.get("K0LMENIA_REGISTRO") or Path.home() / ".k0lmenia" / "planes.json")


def leer_catalogo():
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def instalados():
    """{plan: carpeta} de los plugins pagos registrados cuya carpeta sigue existiendo."""
    try:
        datos = json.loads(registro_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {plan: v["raiz"] for plan, v in datos.items()
            if isinstance(v, dict) and v.get("raiz") and Path(v["raiz"]).is_dir()}


def _env_git():
    env = dict(os.environ)
    env.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never", "GIT_ASKPASS": "", "SSH_ASKPASS": ""})
    return env


def acceso(repo, timeout=20):
    """'si', 'no' o 'desconocido' (sin red, sin git, o un error que no es de permisos)."""
    if not shutil.which("git"):
        return "desconocido", "git no está instalado"
    try:
        r = subprocess.run(["git", "ls-remote", "--exit-code", f"https://github.com/{repo}.git", "HEAD"],
                           capture_output=True, text=True, timeout=timeout, env=_env_git(), stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "desconocido", "GitHub no respondió a tiempo"
    except OSError as e:
        return "desconocido", str(e)
    if r.returncode == 0:
        return "si", ""
    err = (r.stderr or "").lower()
    if any(s in err for s in ("not found", "authentication failed", "could not read username", "403",
                              "terminal prompts disabled", "permission denied", "invalid username or password")):
        return "no", "sin acceso de lectura (o sin credenciales de GitHub en la PC)"
    return "desconocido", (r.stderr or "").strip().splitlines()[-1][:200] if r.stderr else f"git terminó con {r.returncode}"


def github():
    """Credenciales de GitHub vistas por gh (si está instalado). Nunca pide nada."""
    if not shutil.which("gh"):
        return {"gh": False, "credenciales": None, "usuario": None}
    try:
        r = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True, timeout=10,
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return {"gh": True, "credenciales": None, "usuario": None}
    usuario = r.stdout.strip() if r.returncode == 0 else None
    return {"gh": True, "credenciales": bool(usuario), "usuario": usuario}


def tmt():
    env = PROYECTO / ".env"
    valores = {}
    if env.exists():
        for linea in env.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip().strip('"').strip("'")
    return {"configurado": bool(valores.get("K0LMENA_TMT_TOKEN")), "url": valores.get("K0LMENA_TMT_URL") or None}


def estado(chequear_acceso=True, timeout=20):
    cat = leer_catalogo()
    reg = instalados()
    pagos = [p for p in cat["planes"] if p["depende"]]
    accesos = {}
    if chequear_acceso:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(pagos) or 1) as ex:
            futuros = {p["id"]: ex.submit(acceso, p["repo"], timeout) for p in pagos}
            accesos = {k: f.result() for k, f in futuros.items()}
    planes = []
    for p in cat["planes"]:
        base = not p["depende"]
        inst = base or p["id"] in reg  # el core siempre está: es el que corre este script
        acc, detalle = ("si", "") if base else accesos.get(p["id"], ("desconocido", "no se revisó"))
        planes.append({
            "id": p["id"], "nombre": p["nombre"], "plan": p["plan"], "precio": p["precio"], "plugin": p["plugin"],
            "repo": p["repo"], "instalado": bool(inst), "acceso": acc, "detalle": detalle,
            "estado": "instalado" if inst else ("disponible" if acc == "si" else ("bloqueado" if acc == "no" else "desconocido")),
            "resumen": p["resumen"], "agentes": len(p["agentes"]), "skills": len(p["skills"]),
            "conectores": p["conectores"], "gestion": p["gestion"],
            "destacados": [f"{a['nombre']}: {a['descripcion']}" for a in p["agentes"][:6]],
        })
    return {"marketplace": cat["marketplace"], "compra": cat["compra"], "planes": planes,
            "github": github() if chequear_acceso else None, "tmt": tmt()}


ICONO = {"instalado": "✅", "disponible": "⬇️ ", "bloqueado": "🔒", "desconocido": "❔"}


def mostrar(e):
    print("Planes de k0lmenIA\n")
    for p in e["planes"]:
        print(f"{ICONO[p['estado']]} {p['nombre']:<18} {p['estado']:<12} {p['precio']}")
        print(f"   {p['agentes']} agentes · {p['skills']} skills — {p['resumen']}")
        if p["estado"] == "disponible":
            print(f"   → instalalo con: k0lmenia planes --instalar {p['id']}")
        elif p["estado"] == "bloqueado":
            print(f"   → {e['compra']}")
        elif p["estado"] == "desconocido":
            print(f"   → no pude revisar el acceso: {p['detalle']}")
        print()
    gh = e.get("github") or {}
    if gh and not gh.get("credenciales"):
        print("Si ya tenés un plan pago y sale bloqueado, cargá tus credenciales de GitHub en una terminal:\n"
              "  gh auth login\n  gh auth setup-git")
    elif gh.get("usuario"):
        print(f"Usuario de GitHub en esta PC: {gh['usuario']}")
    if not e["tmt"]["configurado"]:
        print("k0lmenaTMT: sin configurar (k0lmenia configurar y después k0lmenia conector activar k0lmena-tmt).")


def instalar(plan_id, marketplace="k0lmenia"):
    cat = leer_catalogo()
    plan = next((p for p in cat["planes"] if p["id"] == plan_id or p["plugin"] == plan_id), None)
    if not plan or not plan["depende"]:
        print(f"planes: no hay un plan pago llamado {plan_id!r} (son: pro, empresa).", file=sys.stderr)
        return 2
    acc, detalle = acceso(plan["repo"])
    if acc == "no":
        print(f"No tenés acceso a {plan['nombre']} ({detalle}).\n"
              f"Si ya lo contrataste: gh auth login y gh auth setup-git en una terminal, y pasale tu usuario de GitHub a Underc0de.\n"
              f"Si no: {cat['compra']}", file=sys.stderr)
        return 3
    if not shutil.which("claude"):
        print(f"No encuentro el comando claude. Instalalo desde Claude Code con: /plugin install {plan['plugin']}@{marketplace}",
              file=sys.stderr)
        return 4
    print(f"Instalando {plan['nombre']} ({plan['plugin']}@{marketplace})…")
    r = subprocess.run(["claude", "plugin", "install", f"{plan['plugin']}@{marketplace}"], env=_env_git())
    if r.returncode != 0:
        print(f"No se pudo instalar. Si el marketplace no está agregado: claude plugin marketplace add underc0delabs/k0lmenIA",
              file=sys.stderr)
        return r.returncode
    print("Listo. Escribí /reload-plugins (o reiniciá Claude Code) para usar los agentes nuevos.")
    return 0


def aviso():
    """Para el contexto del inicio de la sesión: corto, una vez por día y nunca falla ni demora mucho."""
    try:
        datos = Path(os.environ.get("CLAUDE_PLUGIN_DATA") or registro_path().parent)
        marca = datos / "planes-aviso.json"
        try:
            previo = json.loads(marca.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previo = {}
        if time.time() - previo.get("revisado", 0) < UN_DIA:
            return 0
        e = estado(timeout=6)
        datos.mkdir(parents=True, exist_ok=True)
        marca.write_text(json.dumps({"revisado": time.time()}), encoding="utf-8")
        nuevos = [p["nombre"] for p in e["planes"] if p["estado"] == "disponible"]
        sin_acceso = [p["nombre"] for p in e["planes"] if p["instalado"] and p["acceso"] == "no"]
        if nuevos:
            print(f"La persona tiene acceso a {', '.join(nuevos)} y todavía no lo instaló: sugerile `/k0lmenia:setup` "
                  "(una sola vez, sin insistir).")
        if sin_acceso:
            print(f"{', '.join(sin_acceso)} sigue instalado pero ya no hay acceso a su repo: no va a recibir actualizaciones. "
                  "Si la persona pregunta, sugerile `/k0lmenia:setup`.")
    except Exception:  # el aviso nunca frena el inicio de la sesión
        pass
    return 0


# ------------------------------------------------------------------ /k0lmenia:options: comparación y todas las opciones
def _marca(cap_desde, plan_id):
    return "✅" if ORDEN_PLANES.index(plan_id) >= ORDEN_PLANES.index(cap_desde) else "—"


ORDEN_PLANES = ["light", "pro", "empresa"]
ESTADO_TEXTO = {"instalado": "✅ instalado", "disponible": "⬇️ disponible", "bloqueado": "🔒 sin acceso",
                "desconocido": "❔ sin revisar"}


def _celda(texto):
    return texto.replace("|", r"\|").replace("\n", " ")


def opciones(e=None):
    """Markdown: el cuadro comparativo de los tres planes y, debajo, todo lo que trae cada uno."""
    cat = leer_catalogo()
    planes = cat["planes"]
    acumulado = lambda i, clave: sum(len(p[clave]) for p in planes[: i + 1])  # noqa: E731
    estados = {p["id"]: p["estado"] for p in (e or {}).get("planes", [])}
    cab = "| | " + " | ".join(f"**{p['nombre']}**" for p in planes) + " |"
    lineas = ["# Planes de k0lmenIA", "", "## Comparación", "", cab, "|---|" + "---|" * len(planes),
              "| Precio | " + " | ".join(p["precio"] for p in planes) + " |",
              "| Agentes | " + " | ".join(str(acumulado(i, "agentes")) for i in range(len(planes))) + " |",
              "| Skills | " + " | ".join(str(acumulado(i, "skills")) for i in range(len(planes))) + " |",
              "| Conectores | " + " | ".join(str(sum(len(q["conectores"]) for q in planes[: i + 1])) for i in range(len(planes))) + " |"]
    for c in cat.get("capacidades", []):
        lineas.append(f"| {c['nombre']} | " + " | ".join(_marca(c["desde"], p["id"]) for p in planes) + " |")
    if estados:
        lineas.append("| **En esta PC** | " + " | ".join(ESTADO_TEXTO.get(estados.get(p["id"]), "") for p in planes) + " |")
    lineas += ["", "Cada plan incluye todo lo del anterior. Pro y Empresa se instalan como plugins aparte (`/k0lmenia:setup`); "
               f"para contratar: {cat['compra']}", "", "## Todas las opciones"]
    for i, p in enumerate(planes):
        previo = f" (además de todo lo de {planes[i - 1]['nombre']})" if i else ""
        lineas += ["", f"### {p['nombre']} — {p['precio']}{previo}", "", p["resumen"], "",
                   f"**Agentes ({len(p['agentes'])})**", "", "| Agente | Qué hace |", "|---|---|"]
        lineas += [f"| `{a['nombre']}` | {_celda(a['descripcion'])} |" for a in p["agentes"]]
        lineas += ["", f"**Skills ({len(p['skills'])})**", "", "| Skill | Qué hace |", "|---|---|"]
        lineas += [f"| `{s['nombre']}` | {_celda(s['descripcion'])} |" for s in p["skills"]]
        lineas += ["", "**Conectores**: " + ", ".join(f"`{c}`" for c in p["conectores"])]
        if p["gestion"]:
            lineas.append("**Gestión de pruebas**: " + ", ".join(p["gestion"]))
    return "\n".join(lineas) + "\n"


# ------------------------------------------------------------------ recomendación a partir de la web del proyecto
# (señal, qué se vio, patrón en el HTML, agentes que conviene usar). Solo se lee la página principal, una vez.
SENALES = [
    ("shopify", "tienda en Shopify", r"cdn\.shopify\.com|Shopify\.theme", ["probador-shopify"]),
    ("vtex", "tienda en VTEX", r"vtex(?:assets|commercestable|\.com\.br|img)|vtex-", ["probador-vtex"]),
    ("woocommerce", "WooCommerce", r"woocommerce", ["probador-wordpress"]),
    ("wordpress", "sitio en WordPress", r"wp-content|wp-includes", ["probador-wordpress"]),
    ("prestashop", "tienda en PrestaShop", r"prestashop", ["probador-prestashop"]),
    ("ecommerce", "carrito o checkout", r"add[-_]to[-_]cart|carrito|checkout|/cart\b|agregar al carrito", ["probador-formularios"]),
    ("pagos", "medios de pago", r"stripe\.com|mercadopago|paypal|braintree|adyen|checkout\.com|payu", ["probador-billeteras"]),
    ("login", "inicio de sesión", r"type=[\"']password[\"']|iniciar sesi[oó]n|log ?in\b|sign ?in\b", ["probador-autenticacion", "probador-permisos"]),
    ("formularios", "formularios", r"<form\b", ["probador-formularios"]),
    ("busqueda", "buscador", r"type=[\"']search[\"']|role=[\"']search[\"']|algolia|elasticsearch|typesense", ["probador-busqueda"]),
    ("chat", "chat o chatbot", r"intercom|zendesk|zdassets|drift\.com|tawk\.to|botmaker|livechat|dialogflow|crisp\.chat|hubspot.*chat|whatsapp", ["probador-chatbot"]),
    ("analytics", "analytics o píxeles", r"googletagmanager|gtag\(|google-analytics|fbq\(|segment\.com|mixpanel|hotjar|clarity\.ms", ["analista-analytics"]),
    ("idiomas", "varios idiomas", r"hreflang", ["analista-traductor", "probador-fechas-y-regiones"]),
    ("video", "video o streaming", r"<video\b|\.m3u8|\.mpd\b|youtube\.com/embed|vimeo", ["probador-streaming"]),
    ("app", "app mobile publicada", r"play\.google\.com/store|apps\.apple\.com", ["probador-mobile", "mobile-mapper"]),
    ("graphql", "API GraphQL", r"graphql", ["ejecutor-api", "api-mapper"]),
    ("salesforce", "Salesforce", r"salesforce|force\.com|lightning\.force", ["probador-salesforce"]),
    ("sap", "SAP (Fiori/UI5)", r"sap-ui|ui5|fiori|sapui5", ["probador-sap"]),
    ("dynamics", "Dynamics 365", r"dynamics\.com|crm\d*\.dynamics", ["probador-dynamics"]),
]
# Para cualquier web: lo básico del día a día y las auditorías que siempre suman.
SIEMPRE = [("analista-historias", "analizar historias y escribir casos"), ("web-mapper", "mapear la web y automatizar"),
           ("ejecutor-e2e", "probar flujos en el navegador"), ("analista-accesibilidad", "accesibilidad (WCAG)"),
           ("analista-seo", "SEO"), ("auditor-rendimiento-web", "rendimiento web (Core Web Vitals)")]
CABECERAS_SEGURIDAD = ["strict-transport-security", "content-security-policy", "x-content-type-options"]


def analizar_html(html, cabeceras=None):
    """Las señales de la página: [{id, descripcion, agentes}] (sin repetir)."""
    import re
    texto = html or ""
    vistas = []
    for sid, desc, patron, agentes in SENALES:
        if re.search(patron, texto, re.I):
            vistas.append({"id": sid, "descripcion": desc, "agentes": agentes})
    ids = {v["id"] for v in vistas}
    if "wordpress" in ids and "woocommerce" in ids:
        vistas = [v for v in vistas if v["id"] != "wordpress"]
    if cabeceras is not None:
        faltan = [c for c in CABECERAS_SEGURIDAD if c not in {k.lower() for k in cabeceras}]
        if faltan:
            vistas.append({"id": "seguridad", "descripcion": f"faltan cabeceras de seguridad ({', '.join(faltan)})",
                           "agentes": ["analista-seguridad", "pentester-web"]})
    return vistas


def recomendar_desde(url, html, cabeceras=None, e=None):
    cat = leer_catalogo()
    plan_de = {a["nombre"]: p for p in cat["planes"] for a in p["agentes"]}
    import re
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.I | re.S)
    senales = analizar_html(html, cabeceras)
    recomendados, vistos = [], set()
    for agente, motivo in SIEMPRE:
        vistos.add(agente)
        recomendados.append((agente, motivo))
    for s in senales:
        for agente in s["agentes"]:
            if agente not in vistos:
                vistos.add(agente)
                recomendados.append((agente, s["descripcion"]))
    salida = []
    for agente, motivo in recomendados:
        p = plan_de.get(agente)
        if p:
            salida.append({"agente": agente, "motivo": motivo, "plan": p["id"], "plan_nombre": p["nombre"]})
    por_plan = {p["id"]: [r["agente"] for r in salida if r["plan"] == p["id"]] for p in cat["planes"]}
    sugerido = next((p["id"] for p in reversed(cat["planes"]) if por_plan[p["id"]]), "light")
    return {"url": url, "titulo": (html_lib.unescape(" ".join(m.group(1).split()))[:120] if m else None), "senales": senales, "recomendados": salida,
            "por_plan": por_plan, "plan_sugerido": sugerido, "planes": (e or {}).get("planes")}


def recomendar(url, chequear_acceso=True):
    """Lee la página principal (una sola petición GET, sin ejecutar nada) y recomienda agentes y planes."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        import requests
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (k0lmenIA setup)"}, allow_redirects=True)
        html, cabeceras, error = r.text[:2_000_000], dict(r.headers), None
    except Exception as ex:  # sin red, certificado, DNS…: se recomienda igual con lo básico
        html, cabeceras, error = "", None, str(ex)[:200]
    datos = recomendar_desde(url, html, cabeceras, estado(chequear_acceso=chequear_acceso))
    datos["error"] = error
    return datos


def mostrar_recomendacion(d):
    print(f"Web: {d['url']}" + (f" — {d['titulo']}" if d.get("titulo") else ""))
    if d.get("error"):
        print(f"No pude leer la página ({d['error']}): te recomiendo lo básico.")
    if d["senales"]:
        print("Lo que vi: " + "; ".join(s["descripcion"] for s in d["senales"]))
    estados = {p["id"]: p["estado"] for p in d.get("planes") or []}
    for p in leer_catalogo()["planes"]:
        agentes = d["por_plan"].get(p["id"]) or []
        if agentes:
            print(f"\n{p['nombre']} ({ESTADO_TEXTO.get(estados.get(p['id']), '')}):")
            for r in d["recomendados"]:
                if r["plan"] == p["id"]:
                    print(f"  - {r['agente']}: {r['motivo']}")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Planes de k0lmenIA: instalados, disponibles y bloqueados.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--instalar", metavar="PLAN")
    g.add_argument("--aviso", action="store_true")
    g.add_argument("--opciones", action="store_true", help="cuadro comparativo y todas las opciones de cada plan (markdown)")
    g.add_argument("--recomendar", metavar="URL", help="lee la web del proyecto y recomienda agentes y planes")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sin-red", action="store_true", help="no revisa el acceso (solo lo instalado)")
    a = ap.parse_args(argv)
    if a.aviso and os.environ.get("K0LMENIA_SIN_AVISO"):  # los tests y el CI no salen a la red
        return 0
    if a.aviso:
        return aviso()
    if a.instalar:
        return instalar(a.instalar)
    if a.opciones:
        print(opciones(estado(chequear_acceso=not a.sin_red)))
        return 0
    if a.recomendar:
        d = recomendar(a.recomendar, chequear_acceso=not a.sin_red)
        print(json.dumps(d, ensure_ascii=False, indent=2)) if a.json else mostrar_recomendacion(d)
        return 0
    e = estado(chequear_acceso=not a.sin_red)
    if a.json:
        print(json.dumps(e, ensure_ascii=False, indent=2))
    else:
        mostrar(e)
    return 0


if __name__ == "__main__":
    sys.exit(main())

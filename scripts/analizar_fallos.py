#!/usr/bin/env python3
"""
Analiza los escenarios fallidos de una corrida de k0lmena (`npm test`) para el agente analista-fallos:
los clasifica por causa probable, detecta los inestables (flaky) comparando con reintentos, rescata
la evidencia (captura, video y trace) y genera el informe HTML.

Uso (desde la raíz del repo):
    python scripts/analizar_fallos.py [--historia HU-001] [--suites web,api,mobile]
        → toma la corrida actual (herramientas/k0lmena/reports/<suite>/cucumber-report.json) como
          corrida 1, REEMPLAZA el análisis anterior y genera output/fallos/<HU o suite>/informe-fallos.html
    python scripts/analizar_fallos.py --agregar-reintento --suites web [--historia HU-001]
        → después de volver a correr los fallidos (npm test -- web con TAGS=@CP-001 or …), suma la corrida
          actual de esas suites como un reintento y recalcula: lo que falló y después pasó queda como Inestable.
          Pasá solo las suites reintentadas: las demás siguen en el análisis con sus corridas anteriores.
    python scripts/analizar_fallos.py --solo-informe [--analisis analisis.json]
        → regenera el informe (con el análisis del agente) sin tocar las corridas.

Categorías (heurística sobre el error y el estado de los pasos; el agente la confirma o la corrige):
  Posible bug · Locator o espera · Ambiente · Datos de prueba · Error en la automatización ·
  Paso sin definir · Inestable (flaky) · Sin clasificar

Deja en output/fallos/<HU o suite>/: fallos.json, corridas/ (copia de cada cucumber-report.json),
evidencia/ (capturas, videos y traces de los fallidos) e informe-fallos.html.
"""
import argparse
import base64
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import _historial  # noqa: E402
K0 = RAIZ / "herramientas" / "k0lmena" / "reports"
SUITES = ["web", "api", "mobile"]

# (categoría, patrón, sugerencia). El orden importa: gana la primera que coincide.
REGLAS = [
    ("Bloqueo anti-bots", r"BLOQUEO ANTI-BOTS",
     "La protección anti-bots de la app (Cloudflare, Akamai, DataDome, captcha…) frenó al navegador: no es un bug de la app ni del test. "
     "Pedí una excepción para QA (QA_BYPASS_HEADER / QA_BYPASS_TOKEN, IP o claves de prueba del captcha) o usá npm run login con SESION. "
     "Guía: herramientas/k0lmena/tools/navegador/README.md"),
    ("Ambiente", r"ECONNREFUSED|ENOTFOUND|EAI_AGAIN|ECONNRESET|ECONNABORTED|ERR_NAME_NOT_RESOLVED|ERR_CONNECTION|ERR_INTERNET|"
                 r"net::ERR_|socket hang up|\b50[234]\b|Service Unavailable|Bad Gateway|Gateway Time-?out|ERR_CERT|certificate|"
                 r"browserType\.launch|Executable doesn't exist|session not created|Could not start a new session|Appium.*(not running|ECONN)",
     "El sistema o la infraestructura no respondió. Verificá que el ambiente esté arriba y volvé a correr; si se repite, es un problema del ambiente, no del test."),
    ("Datos de prueba", r"already exists|ya existe|duplicad|duplicate|\b409\b|Conflict|unique constraint|violates|no hay datos|not found in (db|database)",
     "El dato que usa el test ya existe o no existe. Revisá la preparación y la limpieza de datos (o usá datos únicos por corrida)."),
    ("Error en la automatización", r"TypeError|ReferenceError|SyntaxError|Cannot read propert|is not a function|is not defined|"
                                   r"Cannot find module|undefined is not",
     "Falla el código de la automatización (steps o helpers), no la aplicación. Revisá el step indicado en el stack."),
    ("Locator o espera", r"TimeoutError|Timeout \d+ ?ms exceeded|waiting for (locator|selector|element)|locator\.|strict mode violation|"
                         r"element is not (visible|attached|enabled|stable)|No node found|outside of the viewport|"
                         r"element\(s\) not found|no such element|stale element|Unable to locate",
     "No se encontró o no se pudo usar un elemento a tiempo. Puede ser un cambio en la pantalla (locator a actualizar), una espera corta o un bug que impide que aparezca: mirá la captura."),
    ("Posible bug", r"AssertionError|expect\(|Expected|Received|toBe|toEqual|toContain|toHave|esperaba|se esperaba|"
                    r"status code|status \d{3}|assert",
     "La aplicación respondió distinto de lo esperado. Si el resultado esperado del caso es correcto, es un bug: redactalo con la evidencia."),
]
SUGERENCIA = {r[0]: r[2] for r in REGLAS}
SUGERENCIA.update({
    "Paso sin definir": "El escenario tiene pasos sin implementar, ambiguos o pendientes: falta completar la automatización (web-mapper / api-mapper).",
    "Inestable (flaky)": "Falló y después pasó sin cambios: el test depende del tiempo, del orden o de datos compartidos. Hay que estabilizarlo (esperas, aislamiento de datos) antes de confiar en él.",
    "Sin clasificar": "El error no coincide con un patrón conocido: revisalo a mano con la evidencia.",
})
CATEGORIAS = ["Posible bug", "Inestable (flaky)", "Locator o espera", "Ambiente", "Bloqueo anti-bots", "Datos de prueba",
              "Error en la automatización", "Paso sin definir", "Sin clasificar"]


def clasificar(error, estados_pasos):
    """(categoría, texto que coincidió) a partir del mensaje de error y los estados de los pasos."""
    if not error and any(s in ("undefined", "ambiguous", "pending") for s in estados_pasos):
        return "Paso sin definir", next(s for s in estados_pasos if s in ("undefined", "ambiguous", "pending"))
    for categoria, patron, _ in REGLAS:
        m = re.search(patron, error or "", re.I)
        if m:
            return categoria, m.group(0)
    return "Sin clasificar", ""


def leer_reporte(archivo, suite, historia=None):
    """cucumber-report.json → {clave: escenario} con su estado, el paso que falló, el error y las evidencias."""
    try:
        features = json.loads(Path(archivo).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    salida = {}
    for f in features or []:
        for esc in f.get("elements") or []:
            if esc.get("type") == "background":
                continue
            tags = list(dict.fromkeys(t["name"].lstrip("@") for t in (f.get("tags") or []) + (esc.get("tags") or [])))
            hu = next((t for t in tags if re.match(r"^HU-\d+$", t, re.I)), None)
            if historia and (hu or "").upper() != historia:
                continue
            cp = next((t for t in tags if re.match(r"^CP(-API)?-\d+$", t)), None)
            estados, error, paso, dur, capturas, videos, traces, doms, textos, url = [], "", None, 0, [], [], [], [], [], None
            for p in esc.get("steps") or []:
                res = p.get("result") or {}
                st = res.get("status", "undefined")
                if p.get("keyword", "").strip() not in ("Before", "After"):
                    estados.append(st)
                dur += res.get("duration") or 0
                if st in ("failed", "undefined", "ambiguous", "pending") and paso is None:
                    paso = f'{p.get("keyword", "").strip()} {p.get("name", "")}'.strip() or "(hook)"
                if st == "failed" and not error:
                    error = re.sub(r"\x1b\[[0-9;]*m", "", res.get("error_message") or "").strip()
                for emb in p.get("embeddings") or []:
                    mime, data = emb.get("mime_type", ""), emb.get("data", "")
                    try:
                        crudo = base64.b64decode(data)
                    except (ValueError, TypeError):
                        continue
                    if mime == "image/png":
                        capturas.append(crudo)
                    elif mime == "text/html":
                        h = crudo.decode("utf-8", "replace")
                        videos += re.findall(r'<video[^>]*src="([^"]+)"', h)
                    elif mime == "text/plain":
                        t = crudo.decode("utf-8", "replace")
                        traces += re.findall(r"TRACE:\s*(\S+)", t)
                        doms += re.findall(r"^DOM:[ \t]*([^\r\n]+)", t, re.M)  # DOM al fallar (para el reparador)
                        u = re.search(r"- URL:\s*(\S+)", t)
                        url = url or (u.group(1) if u else None)
                        textos.append(t)
            if "failed" in estados or "ambiguous" in estados:
                estado = "Fallido"
            elif estados and all(s == "passed" for s in estados):
                estado = "Aprobado"
            elif any(s in ("undefined", "pending") for s in estados):
                estado = "Fallido"
            else:
                estado = "Salteado"
            # Si el error vino en un hook (After), el detalle queda en los adjuntos de texto.
            if estado == "Fallido" and not error:
                error = next((t for t in textos if t.startswith("ERROR") or "Error" in t[:80]), "")
            bloqueo = next((t for t in textos if t.startswith("BLOQUEO ANTI-BOTS")), "")
            if estado == "Fallido" and bloqueo:  # lo marca el hook de k0lmena (tools/navegador)
                error = f"{bloqueo}\n\n{error}".strip()
            clave = f'{suite}:{f.get("uri", "")}:{esc.get("line")}:{esc.get("name")}'
            salida[clave] = {
                "clave": clave, "suite": suite, "feature": f.get("name", ""), "uri": f.get("uri", ""), "linea": esc.get("line"),
                "escenario": esc.get("name", ""), "tags": tags, "historia": hu, "caso": cp, "estado": estado,
                "estados_pasos": estados, "paso_fallido": paso, "error": error[:4000], "duracion_s": round(dur / 1e9, 2),
                "url": url, "_capturas": capturas, "_videos": videos, "_traces": traces, "_doms": doms,
            }
    return salida


def _copiar_evidencia(r, base_reporte, dir_ev, prefijo):
    """Escribe las capturas embebidas y copia videos y traces (el próximo npm test los pisa)."""
    ev = []
    nombre = re.sub(r"[^\w.-]+", "_", f'{r.get("caso") or ""}-{r["escenario"]}')[:70].strip("_")
    for n, png in enumerate(r.pop("_capturas", [])):
        arch = dir_ev / f"{prefijo}-{nombre}-{hashlib.md5(png).hexdigest()[:6]}-{n}.png"
        arch.write_bytes(png)
        ev.append({"tipo": "captura", "archivo": arch})
    for tipo, clave in (("video", "_videos"), ("trace", "_traces"), ("dom", "_doms")):
        for src in r.pop(clave, []):
            limpio = src.replace("../", "")
            destino = dir_ev / f"{prefijo}-{Path(limpio).name}"
            if destino.exists():  # ya copiado en un análisis anterior (el npm test nuevo pudo pisar el original)
                ev.append({"tipo": tipo, "archivo": destino})
                continue
            for cand in (base_reporte / limpio, base_reporte / "html" / limpio):
                if cand.exists():
                    shutil.copy2(cand, destino)
                    ev.append({"tipo": tipo, "archivo": destino})
                    break
    return ev


def analizar(carpeta, historia, suites):
    dir_corr = carpeta / "corridas"
    dir_ev = carpeta / "evidencia"
    dir_ev.mkdir(parents=True, exist_ok=True)
    meta = json.loads((carpeta / "corridas.json").read_text(encoding="utf-8"))
    rel = lambda p: Path(p).relative_to(carpeta).as_posix()
    historial = {}  # clave → [estado por corrida]
    ultimo = {}     # clave → el registro del último fallo (con su evidencia)
    for i, corrida in enumerate(meta["corridas"]):
        for suite in suites:
            arch = dir_corr / f'{corrida["id"]}-{suite}.json'
            if not arch.exists():
                continue
            for clave, r in leer_reporte(arch, suite, historia).items():
                historial.setdefault(clave, [None] * len(meta["corridas"]))[i] = r["estado"]
                if r["estado"] != "Fallido":
                    continue
                evid = _copiar_evidencia(r, Path(corrida["origen"][suite]).parent, dir_ev, corrida["id"])
                r["evidencias"] = [{"tipo": x["tipo"], "archivo": rel(x["archivo"])} for x in evid]
                r["corrida"] = corrida["id"]
                ultimo[clave] = r
    fallos, total, aprobados = [], len(historial), 0
    for clave, hist in historial.items():
        estados = [s for s in hist if s]
        if "Fallido" not in estados:
            aprobados += 1 if estados and estados[-1] == "Aprobado" else 0
            continue
        r = ultimo[clave]
        categoria, coincidencia = clasificar(r["error"], r["estados_pasos"])
        if "Aprobado" in estados:  # falló y pasó en otra corrida: inestable
            categoria, coincidencia = "Inestable (flaky)", " / ".join(s or "—" for s in hist)
        r.update({"historial": hist, "categoria": categoria, "coincidencia": coincidencia, "sugerencia": SUGERENCIA[categoria],
                  "estado_final": estados[-1]})
        fallos.append(r)
    fallos.sort(key=lambda r: (CATEGORIAS.index(r["categoria"]), r["suite"], r["uri"], r["linea"] or 0))
    for i, r in enumerate(fallos):
        r["id"] = f"F-{i + 1:02d}"
        r.pop("estados_pasos", None)
    cuenta = {c: sum(1 for r in fallos if r["categoria"] == c) for c in CATEGORIAS}
    return {
        "historia": historia, "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
        "suites": [s for s in suites if any(s in c.get("suites", []) for c in meta["corridas"])],
        "corridas": meta["corridas"],
        "resumen": {"escenarios": total, "aprobados": aprobados, "fallidos": len(fallos),
                    "siguen_fallando": sum(1 for r in fallos if r["estado_final"] == "Fallido"),
                    "por_categoria": {c: n for c, n in cuenta.items() if n},
                    "por_suite": {s: sum(1 for r in fallos if r["suite"] == s) for s in suites if any(r["suite"] == s for r in fallos)}},
        "fallos": fallos,
    }


def capturar_corrida(carpeta, suites, etiqueta, origen_dir=K0):
    meta_arch = carpeta / "corridas.json"
    meta = json.loads(meta_arch.read_text(encoding="utf-8")) if meta_arch.exists() else {"corridas": []}
    cid = f"c{len(meta['corridas']) + 1}"
    origen, copiadas = {}, []
    (carpeta / "corridas").mkdir(parents=True, exist_ok=True)
    for suite in suites:
        rep = Path(origen_dir) / suite / "cucumber-report.json"
        if rep.exists():
            shutil.copy2(rep, carpeta / "corridas" / f"{cid}-{suite}.json")
            origen[suite] = str(rep)
            copiadas.append(suite)
    if not copiadas:
        sys.exit("No encontré resultados de npm test (herramientas/k0lmena/reports/<web|api|mobile>/cucumber-report.json). "
                 "Corré primero npm test.")
    momento = datetime.datetime.fromtimestamp(max(Path(origen[s]).stat().st_mtime for s in copiadas)).isoformat(timespec="seconds")
    meta["corridas"].append({"id": cid, "etiqueta": etiqueta, "suites": copiadas, "origen": origen, "fecha": momento})
    meta_arch.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return cid, copiadas


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Análisis de fallos de npm test (k0lmena)")
    ap.add_argument("--historia", help="HU-XXX: solo los escenarios con ese tag")
    ap.add_argument("--suites", default="web,api,mobile")
    ap.add_argument("--agregar-reintento", action="store_true", help="suma la corrida actual como reintento")
    ap.add_argument("--solo-informe", action="store_true", help="regenera el informe sin tocar las corridas")
    ap.add_argument("--analisis", help="analisis.json del agente (por defecto, el de la carpeta si existe)")
    ap.add_argument("--salida", help="carpeta (por defecto output/fallos/<HU o suite>)")
    ap.add_argument("--reportes", default=str(K0), help="carpeta con <suite>/cucumber-report.json (por defecto la de k0lmena)")
    a = ap.parse_args()
    historia = a.historia.upper() if a.historia else None
    if historia and not re.match(r"^[A-Z]+-\d+$", historia):
        sys.exit("--historia tiene que ser un ID como HU-001.")
    suites = [s.strip() for s in a.suites.split(",") if s.strip() in SUITES]
    carpeta = Path(a.salida) if a.salida else RAIZ / "output" / "fallos" / (historia or "suite")

    if not a.agregar_reintento and not a.solo_informe:
        # Corrida nueva: el análisis anterior pasa a historial/<fecha>/ (se guardan los últimos 5).
        _historial.archivar(carpeta, ["corridas", "evidencia", "corridas.json", "fallos.json", "analisis.json", "informe-fallos.html"], "fallos.json")
        for nombre in ("corridas", "evidencia", "corridas.json", "fallos.json", "analisis.json", "informe-fallos.html"):
            p = carpeta / nombre
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        carpeta.mkdir(parents=True, exist_ok=True)
        cid, copiadas = capturar_corrida(carpeta, suites, "Corrida original", a.reportes)
        donde = carpeta.resolve()
        donde = donde.relative_to(RAIZ).as_posix() if donde.is_relative_to(RAIZ) else str(donde)
        print(f"Corrida original ({', '.join(copiadas)}) guardada en {donde}")
    elif a.agregar_reintento:
        if not (carpeta / "corridas.json").exists():
            sys.exit("No hay un análisis previo en esa carpeta: corré primero sin --agregar-reintento.")
        cid, copiadas = capturar_corrida(carpeta, suites, "Reintento", a.reportes)
        print(f"Reintento {cid} ({', '.join(copiadas)}) agregado")
    if not (carpeta / "corridas.json").exists():
        sys.exit("No hay corridas guardadas en esa carpeta.")
    # Se analizan todas las suites guardadas: un reintento de una sola suite (--suites web) no saca a las demás del análisis.
    guardadas = {x for c in json.loads((carpeta / "corridas.json").read_text(encoding="utf-8"))["corridas"] for x in c.get("suites", [])}
    datos = analizar(carpeta, historia, [x for x in SUITES if x in guardadas] or suites)
    (carpeta / "fallos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    r = datos["resumen"]
    print(f'Escenarios: {r["escenarios"]} · aprobados: {r["aprobados"]} · con fallas: {r["fallidos"]} (siguen fallando: {r["siguen_fallando"]})')
    for c, n in r["por_categoria"].items():
        print(f"  {c}: {n}")
    args = [sys.executable, str(RAIZ / "scripts" / "generar_informe_fallos.py"), str(carpeta / "fallos.json"), str(carpeta / "informe-fallos.html")]
    analisis = Path(a.analisis) if a.analisis else carpeta / "analisis.json"
    if analisis.exists():
        args += ["--analisis", str(analisis)]
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0:  # p. ej. un analisis.json mal formado: el agente tiene que enterarse, no seguir de largo
        print(res.stderr.strip() or res.stdout.strip(), file=sys.stderr)
        sys.exit("No se pudo armar el informe HTML (revisá el analisis.json).")
    print(res.stdout.strip() or res.stderr.strip())


if __name__ == "__main__":
    main()

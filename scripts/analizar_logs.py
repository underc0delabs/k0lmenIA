#!/usr/bin/env python3
"""
Analiza logs de la aplicación (agente analista-logs): agrupa los errores por firma, arma la línea de tiempo
y los cruza con los escenarios de una corrida de k0lmena para encontrar el error del servidor detrás de cada falla.

Uso (desde la raíz del repo):
    python scripts/analizar_logs.py --logs "input/logs/*.log,input/logs/nginx/error.log*" [--corrida web|api|mobile|<cucumber-report.json>]
        [--desde 2026-10-11T10:00 --hasta 2026-10-11T11:00] [--zona -03:00] [--margen-s 10] [--nombre HU-001]

Formatos que entiende (se mezclan sin problema): líneas con fecha ISO (2026-10-11 10:22:33,123 / ...T10:22:33Z),
logs de acceso de nginx y Apache ([11/Oct/2026:10:22:33 -0300] "GET /x" 500), errores de nginx (2026/10/11
10:22:33), syslog (Oct 11 10:22:33) y JSON por línea ({"time"/"timestamp"/"@timestamp", "level", "message"}).
Los stack traces (líneas que siguen con "at ...", "Caused by", "File ...", "Traceback", sangría) se pegan a
su error. Archivos .gz también.

Qué arma:
  - firmas: cada error o advertencia normalizado (sin números, ids, uuids, emails ni textos entre comillas), con
    cuántas veces apareció, la primera y la última, los archivos y un ejemplo con su stack trace;
  - la línea de tiempo por minuto;
  - con --corrida: cada escenario fallido con los errores que hubo mientras corría (los steps comunes de k0lmena
    guardan el inicio y el fin de cada escenario); sin --desde/--hasta, se analiza la ventana de la corrida (± 5 minutos).
Las fechas sin zona horaria se toman como hora local (o la de --zona).

Deja output/logs/<nombre>/ con logs.json e informe-logs.html; el análisis anterior pasa a historial/ (últimos 5).
"""
import os
import argparse
import datetime as dt
import glob
import gzip
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
sys.path.insert(0, str(RAIZ / "scripts"))
import _historial  # noqa: E402

K0 = PROYECTO / "herramientas" / "k0lmena" / "reports"
MESES = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MESES.update({"ene": 1, "abr": 4, "ago": 8, "dic": 12})
R_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:[.,](\d{1,6}))?\s*(Z|[+-]\d{2}:?\d{2})?")
R_ACCESO = re.compile(r"\[(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2}) ([+-]\d{4})\]")
R_BARRAS = re.compile(r"(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})")
R_SYSLOG = re.compile(r"^(\w{3}) +(\d{1,2}) (\d{2}):(\d{2}):(\d{2})")
R_NIVEL = re.compile(r"\b(FATAL|CRITICAL|CRIT|ERROR|ERR|SEVERE|WARNING|WARN|NOTICE|INFO|DEBUG|TRACE)\b", re.I)
R_HTTP = re.compile(r'"(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) ([^ "]+)[^"]*" (\d{3})')
R_EXC = re.compile(r"(Exception|Traceback|Error:|\bat [\w.$]+\(|Unhandled|panic:|Segmentation fault|OutOfMemory|ECONNREFUSED|timed? ?out)", re.I)
# Líneas que continúan el error anterior: stack traces de Java, Python, Node y .NET.
R_SIGUE = re.compile(r"^(\s+|\tat |at |Caused by|\.\.\. \d+ more|File \"|Traceback|  File|\s*\^|[\w.$]+(Exception|Error)(:|\s*$))")
NIVEL_NORM = {"fatal": "Error", "critical": "Error", "crit": "Error", "error": "Error", "err": "Error", "severe": "Error",
              "warning": "Advertencia", "warn": "Advertencia", "notice": "Info", "info": "Info", "debug": "Info", "trace": "Info"}


def _tz(texto, zona):
    if not texto:
        return zona
    if texto == "Z":
        return dt.timezone.utc
    t = texto.replace(":", "")
    signo = -1 if t[0] == "-" else 1
    return dt.timezone(signo * dt.timedelta(hours=int(t[1:3]), minutes=int(t[3:5])))


def fecha_de(linea, zona):
    """(datetime con zona, texto de la fecha) de una línea, o (None, None)."""
    m = R_ISO.search(linea)
    if m:
        y, mo, d, h, mi, s, frac, tz = m.groups()
        micro = int((frac or "0").ljust(6, "0")[:6])
        return dt.datetime(int(y), int(mo), int(d), int(h), int(mi), int(s), micro, tzinfo=_tz(tz, zona)), m.group(0)
    m = R_ACCESO.search(linea)
    if m:
        d, mon, y, h, mi, s, tz = m.groups()
        return dt.datetime(int(y), MESES.get(mon.lower()[:3], 1), int(d), int(h), int(mi), int(s), tzinfo=_tz(tz, zona)), m.group(0)
    m = R_BARRAS.search(linea)
    if m:
        y, mo, d, h, mi, s = m.groups()
        return dt.datetime(int(y), int(mo), int(d), int(h), int(mi), int(s), tzinfo=zona), m.group(0)
    m = R_SYSLOG.match(linea)
    if m and m.group(1).lower()[:3] in MESES:
        mon, d, h, mi, s = m.groups()
        return dt.datetime(dt.date.today().year, MESES[mon.lower()[:3]], int(d), int(h), int(mi), int(s), tzinfo=zona), m.group(0)
    return None, None


def firma(mensaje):
    s = re.sub(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<uuid>", mensaje, flags=re.I)
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", s)
    s = re.sub(r"\b\d{1,3}(\.\d{1,3}){3}(:\d+)?\b", "<ip>", s)
    s = re.sub(r"\b0x[0-9a-f]+\b|\b[0-9a-f]{12,}\b", "<hex>", s, flags=re.I)
    s = re.sub(r"(['\"])(?:(?!\1).){1,80}\1", r"\1<s>\1", s)
    s = re.sub(r"\?[^\s\"]*", "?<q>", s)
    s = re.sub(r"\d+", "<n>", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:180]


def leer_archivo(ruta):
    abrir = gzip.open if str(ruta).endswith(".gz") else open
    with abrir(ruta, "rt", encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def entradas(rutas, zona):
    """Una entrada por evento (con su stack trace pegado)."""
    salida, fuentes = [], []
    for ruta in rutas:
        try:
            lineas = leer_archivo(ruta)
        except OSError as e:
            print(f"[!] No pude leer {ruta}: {e}", file=sys.stderr)
            continue
        fuentes.append({"archivo": str(ruta), "lineas": len(lineas)})
        actual = None
        for linea in lineas:
            if not linea.strip():
                continue
            if actual and R_SIGUE.match(linea) and not R_ISO.match(linea.strip()):
                actual["stack"].append(linea.rstrip())
                continue
            nivel, mensaje, ts, ts_txt = None, linea.strip(), None, None
            if linea.lstrip().startswith("{"):
                try:
                    j = json.loads(linea)
                    t = j.get("time") or j.get("timestamp") or j.get("@timestamp") or j.get("ts") or ""
                    ts, ts_txt = fecha_de(str(t), zona) if t else (None, None)
                    nivel = str(j.get("level") or j.get("severity") or j.get("lvl") or "").lower()
                    mensaje = str(j.get("message") or j.get("msg") or j.get("error") or linea)
                    if j.get("stack") or j.get("stack_trace"):
                        actual = None
                except ValueError:
                    pass
            if ts is None:
                ts, ts_txt = fecha_de(linea, zona)
            http = R_HTTP.search(linea)
            if http:
                cod = int(http.group(3))
                nivel = "error" if cod >= 500 else "warn" if cod >= 400 else "info"
                mensaje = f"{http.group(1)} {http.group(2)} → {cod}"
            if not nivel:
                m = R_NIVEL.search(linea[:160])
                nivel = m.group(1).lower() if m else ("error" if R_EXC.search(linea) else "info")
            if ts_txt and not http:
                mensaje = mensaje.replace(ts_txt, "").strip(" -|[]:")
            limpio = re.sub(r"^\W*" + R_NIVEL.pattern + r"\s*", "", mensaje, flags=re.I)
            limpio = re.sub(r"^(?:\[[^\]]{0,60}\]\s*)+", "", limpio).strip()  # [hilo] [request-id]
            mensaje = limpio or mensaje
            actual = {"ts": ts, "nivel": NIVEL_NORM.get(nivel, "Info"), "mensaje": mensaje[:500], "archivo": Path(ruta).name, "stack": [], "linea": linea[:500]}
            salida.append(actual)
    return salida, fuentes


def tiempos_corrida(arg):
    """Escenarios de un cucumber-report.json con su inicio y fin (adjunto TIEMPO de k0lmena)."""
    import base64
    rutas = []
    for x in (arg or "").split(","):
        x = x.strip()
        if not x:
            continue
        rutas.append(K0 / x / "cucumber-report.json" if x in ("web", "api", "mobile") else Path(x))
    salida = []
    for r in rutas:
        try:
            features = json.loads(Path(r).read_text(encoding="utf-8") or "[]")
        except (OSError, ValueError):
            print(f"[!] No pude leer la corrida {r}", file=sys.stderr)
            continue
        for f in features:
            for esc in f.get("elements") or []:
                if esc.get("type") == "background":
                    continue
                tags = [t["name"].lstrip("@") for t in (f.get("tags") or []) + (esc.get("tags") or [])]
                estados = [(p.get("result") or {}).get("status") for p in esc.get("steps") or []]
                inicio = fin = None
                error = ""
                for p in esc.get("steps") or []:
                    if (p.get("result") or {}).get("status") == "failed" and not error:
                        error = re.sub(r"\x1b\[[0-9;]*m", "", (p["result"].get("error_message") or "")).strip().splitlines()[0][:200] if p["result"].get("error_message") else ""
                    for emb in p.get("embeddings") or []:
                        if emb.get("mime_type") != "text/plain":
                            continue
                        try:
                            t = base64.b64decode(emb["data"]).decode("utf-8", "replace")
                        except (ValueError, KeyError):
                            continue
                        m = re.search(r"TIEMPO: inicio=(\S+) fin=(\S+)", t)
                        if m:
                            inicio, fin = dt.datetime.fromisoformat(m.group(1).replace("Z", "+00:00")), dt.datetime.fromisoformat(m.group(2).replace("Z", "+00:00"))
                salida.append({"escenario": esc.get("name"), "uri": f.get("uri"), "linea": esc.get("line"),
                               "historia": next((t for t in tags if re.fullmatch(r"HU-\d+", t, re.I)), None),
                               "caso": next((t for t in tags if re.fullmatch(r"CP(-API)?-\d+", t)), None),
                               "estado": "Fallido" if "failed" in estados else "Aprobado" if estados and all(s == "passed" for s in estados) else "Otro",
                               "error": error, "inicio": inicio, "fin": fin})
    return salida


def analizar(ents, escenarios, desde, hasta, margen):
    if desde or hasta:
        ents = [x for x in ents if x["ts"] is None or ((not desde or x["ts"] >= desde) and (not hasta or x["ts"] <= hasta))]
    problemas = [x for x in ents if x["nivel"] in ("Error", "Advertencia")]
    grupos = defaultdict(list)
    for x in problemas:
        grupos[(x["nivel"], firma(x["mensaje"]))].append(x)
    firmas = []
    for (nivel, f), xs in sorted(grupos.items(), key=lambda kv: (kv[0][0] != "Error", -len(kv[1]))):
        con_ts = [x for x in xs if x["ts"]]
        ej = next((x for x in xs if x["stack"]), xs[0])
        firmas.append({"nivel": nivel, "firma": f, "cuenta": len(xs), "ejemplo": ej["mensaje"], "stack": ej["stack"][:25],
                       "primero": min(x["ts"] for x in con_ts).astimezone().isoformat() if con_ts else None, "ultimo": max(x["ts"] for x in con_ts).astimezone().isoformat() if con_ts else None,
                       "archivos": sorted({x["archivo"] for x in xs}), "excepcion": next((m.group(0) for x in xs for m in [re.search(r"\b[\w.]*(Exception|Error)\b", x["mensaje"] + " " + " ".join(x["stack"][:2]))] if m), None)})
    for i, fi in enumerate(firmas):
        fi["id"] = f"L-{i + 1:02d}"
    por_firma = {(fi["nivel"], fi["firma"]): fi["id"] for fi in firmas}
    linea = Counter()
    for x in problemas:
        if x["ts"]:
            linea[(x["ts"].astimezone().strftime("%Y-%m-%d %H:%M"), x["nivel"])] += 1
    minutos = sorted({k[0] for k in linea})
    tiempo = [{"minuto": m, "errores": linea[(m, "Error")], "advertencias": linea[(m, "Advertencia")]} for m in minutos]
    # Cruce con los escenarios: errores mientras corría cada uno (con margen).
    cruces = []
    for e in escenarios:
        if not e["inicio"]:
            continue
        ini, fin = e["inicio"] - dt.timedelta(seconds=margen), e["fin"] + dt.timedelta(seconds=margen)
        en_ventana = [x for x in problemas if x["ts"] and ini <= x["ts"] <= fin]
        c = Counter(por_firma[(x["nivel"], firma(x["mensaje"]))] for x in en_ventana)
        cruces.append({**{k: e[k] for k in ("escenario", "uri", "linea", "historia", "caso", "estado", "error")},
                       "inicio": e["inicio"].astimezone().isoformat(), "fin": e["fin"].astimezone().isoformat(),
                       "errores": [{"firma": fid, "cuenta": n} for fid, n in c.most_common(8)],
                       "lineas": [x["linea"] for x in en_ventana if x["nivel"] == "Error"][:8]})
    for fi in firmas:
        fi["escenarios"] = [f'{c["caso"] or ""} {c["escenario"]}'.strip() for c in cruces if any(x["firma"] == fi["id"] for x in c["errores"])]
    return ents, firmas, tiempo, cruces


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Análisis de logs de la aplicación")
    ap.add_argument("--logs", help="archivos o patrones separados por coma (input/logs/*.log)")
    ap.add_argument("--corrida", help="web, api, mobile o la ruta a un cucumber-report.json (varios separados por coma)")
    ap.add_argument("--desde")
    ap.add_argument("--hasta")
    ap.add_argument("--zona", help="zona horaria de las fechas sin zona (por ejemplo -03:00); por defecto la local")
    ap.add_argument("--margen-s", type=int, default=10, help="segundos antes y después de cada escenario")
    ap.add_argument("--nombre", help="carpeta de salida en output/logs/ (por defecto 'app')")
    ap.add_argument("--solo-informe", action="store_true")
    ap.add_argument("--salida")
    a = ap.parse_args()
    carpeta = Path(a.salida) if a.salida else PROYECTO / "output" / "logs" / (a.nombre or "app")
    datos_arch = carpeta / "logs.json"
    if not a.solo_informe:
        if not a.logs:
            sys.exit("Decime qué logs analizar: --logs input/logs/app.log (o un patrón como input/logs/*.log).")
        rutas = sorted({Path(x) for p in a.logs.split(",") for x in (glob.glob(p.strip()) or [p.strip()]) if Path(x).is_file()})
        if not rutas:
            sys.exit(f"No encontré archivos de log en: {a.logs}")
        zona = _tz(a.zona, None) if a.zona else dt.datetime.now().astimezone().tzinfo
        ents, fuentes = entradas(rutas, zona)
        escenarios = tiempos_corrida(a.corrida) if a.corrida else []
        conv = lambda s: dt.datetime.fromisoformat(s).replace(tzinfo=dt.datetime.fromisoformat(s).tzinfo or zona) if s else None
        desde, hasta = conv(a.desde), conv(a.hasta)
        con_t = [e for e in escenarios if e["inicio"]]
        if con_t and not (desde or hasta):
            desde = min(e["inicio"] for e in con_t) - dt.timedelta(minutes=5)
            hasta = max(e["fin"] for e in con_t) + dt.timedelta(minutes=5)
        ents, firmas, tiempo, cruces = analizar(ents, escenarios, desde, hasta, a.margen_s)
        fallidos = [c for c in cruces if c["estado"] == "Fallido"]
        ahora = dt.datetime.now()
        datos = {"nombre": a.nombre or "app", "fecha": ahora.isoformat(timespec="seconds"), "marca": ahora.strftime("%Y%m%d-%H%M%S"),
                 "fuentes": fuentes, "corrida": a.corrida, "ventana": {"desde": desde.astimezone().isoformat() if desde else None, "hasta": hasta.astimezone().isoformat() if hasta else None},
                 "resumen": {"archivos": len(fuentes), "lineas": sum(f["lineas"] for f in fuentes), "eventos": len(ents),
                             "errores": sum(f["cuenta"] for f in firmas if f["nivel"] == "Error"), "advertencias": sum(f["cuenta"] for f in firmas if f["nivel"] == "Advertencia"),
                             "firmas": len(firmas), "firmas_error": sum(1 for f in firmas if f["nivel"] == "Error"),
                             "escenarios": len(escenarios), "escenarios_con_tiempo": len(con_t), "fallidos": len(fallidos),
                             "fallidos_con_errores": sum(1 for c in fallidos if c["errores"]), "sin_fecha": sum(1 for x in ents if x["ts"] is None)},
                 "firmas": firmas, "linea_tiempo": tiempo, "escenarios": cruces}
        _historial.archivar(carpeta, ["logs.json", "analisis.json", "informe-logs.html"], "logs.json")
        carpeta.mkdir(parents=True, exist_ok=True)
        datos_arch.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        r = datos["resumen"]
        print(f'Líneas: {r["lineas"]} en {r["archivos"]} archivo(s) · errores: {r["errores"]} ({r["firmas_error"]} firmas) · advertencias: {r["advertencias"]}')
        if escenarios:
            print(f'Escenarios: {r["escenarios"]} ({r["escenarios_con_tiempo"]} con tiempo) · fallidos: {r["fallidos"]}, con errores del servidor: {r["fallidos_con_errores"]}')
        for f in firmas[:5]:
            print(f'  {f["id"]} {f["nivel"]:11} ×{f["cuenta"]:<4} {f["ejemplo"][:90]}')
    args = [sys.executable, str(RAIZ / "scripts" / "generar_informe_logs.py"), str(datos_arch), str(carpeta / "informe-logs.html")]
    if (carpeta / "analisis.json").exists():
        args += ["--analisis", str(carpeta / "analisis.json")]
    res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:  # p. ej. un analisis.json mal formado: el agente tiene que enterarse, no seguir de largo
        print(res.stderr.strip() or res.stdout.strip(), file=sys.stderr)
        sys.exit("No se pudo armar el informe HTML (revisá el analisis.json).")
    print(res.stdout.strip() or res.stderr.strip())


if __name__ == "__main__":
    main()

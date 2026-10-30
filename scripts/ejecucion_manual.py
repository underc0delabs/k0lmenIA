#!/usr/bin/env python3
"""
Sesión de ejecución manual de casos de prueba (skill ejecucion-manual y agente asistente-ejecucion-manual).

La conversación principal guía al QA caso por caso y paso por paso; esta herramienta guarda todo en
output/ejecucion-manual/<HU o nombre>/sesion.json para que la sesión se pueda pausar y retomar, mide los tiempos
(sin contar las pausas) y, al cerrar, arma los resultados con el formato de scripts/generar_reporte.py y el
informe HTML de la sesión.

Uso (desde la raíz del repo):
    python scripts/ejecucion_manual.py iniciar --casos <planilla.xlsx|casos.json|archivo.feature|casos.md>
                                       [--historia HU-001] [--solo CP-001,CP-003] [--ambiente QA] [--tester "Nombre"]
                                       [--navegador "Chrome 130"] [--reiniciar]
    python scripts/ejecucion_manual.py siguiente --sesion <carpeta o sesion.json>        # el próximo caso y paso (JSON)
    python scripts/ejecucion_manual.py empezar   --sesion <…> --caso CP-001                 # arranca el reloj del caso
    python scripts/ejecucion_manual.py registrar --sesion <…> --caso CP-001 [--paso 2] --resultado Aprobado|Fallido|Bloqueado|N/A
                                       [--obtenido "lo que pasó"] [--evidencia capturas/cp-001.png] [--bug BUG-004]
                                       [--motivo "por qué está bloqueado"] [--comentario "…"]
    python scripts/ejecucion_manual.py pausar    --sesion <…>   /   retomar --sesion <…>
    python scripts/ejecucion_manual.py estado    --sesion <…>                               # avance y tiempos (JSON)
    python scripts/ejecucion_manual.py cerrar    --sesion <…> [--analisis analisis.json]    # resultados + informe

Reglas:
- Un caso con un paso Fallido queda Fallido (salvo que se registre el caso entero con otro resultado: la diferencia
  queda marcada como inconsistencia en el informe para que el QA la revise).
- Bloqueado pide motivo; Fallido pide lo obtenido o un bug.
- Al cerrar, los casos que no se ejecutaron NO pasan a Aprobado: quedan como Pendientes en el informe y fuera de los
  resultados de ejecución.
- No publica nada en Xray/k0lmenaTMT: eso lo hace el publicador-resultados, con confirmación.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "scripts" / "gestion"))

RESULTADOS = ["Aprobado", "Fallido", "Bloqueado", "N/A"]
PRIORIDADES = ["Crítica", "Alta", "Media", "Baja"]
SECRETO = re.compile(r"(?i)\b(password|contrase[ñn]a|clave|token|secret|pass)\b(\s*[:=]\s*)\S+")


def ahora():
    return datetime.now().isoformat(timespec="seconds")


def _segundos(a, b):
    try:
        return max(0, int((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds()))
    except (TypeError, ValueError):
        return 0


def redactar(texto):
    """Saca contraseñas y tokens de lo que escribe el QA (observaciones, obtenido): nunca quedan en la sesión."""
    return SECRETO.sub(r"\1\2[redactado]", str(texto or ""))


# ------------------------------------------------------------------ casos
def _pasos_de_texto(pasos, datos="", resultado=""):
    lineas = [re.sub(r"^\s*\d+[.)-]\s*", "", l).strip() for l in str(pasos or "").splitlines() if l.strip()]
    out = [{"accion": l, "datos": "", "esperado": ""} for l in lineas] or [{"accion": "Ejecutar el caso", "datos": "", "esperado": ""}]
    out[0]["datos"] = datos or ""
    out[-1]["esperado"] = resultado or ""
    return out


def _de_gherkin(gherkin):
    pasos = []
    for l in str(gherkin or "").splitlines():
        m = re.match(r"\s*(Given|When|Then|And|But|\*)\s+(.*)", l)
        if m:
            es_then = m.group(1) == "Then" or (m.group(1) in ("And", "But") and pasos and pasos[-1]["esperado"])
            pasos.append({"accion": "" if es_then else m.group(2), "datos": "", "esperado": m.group(2) if es_then else ""})
    # Un Then se pega al paso anterior como resultado esperado.
    fusion = []
    for p in pasos:
        if not p["accion"] and fusion:
            fusion[-1]["esperado"] = (fusion[-1]["esperado"] + "\n" + p["esperado"]).strip()
        else:
            fusion.append(p)
    return fusion or [{"accion": "Ejecutar el escenario", "datos": "", "esperado": ""}]


def cargar_casos(ruta):
    """Casos desde la planilla de generar_casos.py, su JSON de entrada, un .feature o un .md con su planilla al lado."""
    p = Path(ruta)
    if not p.exists():
        raise SystemExit(f"No existe {p}.")
    suf = p.suffix.lower()
    if suf == ".md":
        for hermano in (p.with_suffix(".xlsx"), p.with_suffix(".json")):
            if hermano.exists():
                return cargar_casos(hermano)
        raise SystemExit(f"{p.name}: el .md de casos no se puede leer solo; pasá la planilla .xlsx (o el .json) que está al lado.")
    if suf in (".xlsx", ".xlsm"):
        from lectores import leer_xlsx
        casos = []
        for c in leer_xlsx(p):
            pasos = [{"accion": x.get("accion", ""), "datos": x.get("datos", ""), "esperado": x.get("resultado", "")} for x in c.get("pasos") or []]
            casos.append({"id": c["id"], "titulo": c.get("titulo", ""), "prioridad": c.get("prioridad") or "Media",
                          "precondiciones": c.get("precondiciones", ""), "pasos": pasos or _pasos_de_texto(""),
                          "tiempo_min": c.get("tiempo_min"), "etiquetas": c.get("etiquetas") or []})
        return casos
    if suf == ".feature":
        from lectores import leer_feature
        return [{"id": c["id"], "titulo": c.get("titulo", ""), "prioridad": c.get("prioridad") or "Media", "precondiciones": "",
                 "pasos": _de_gherkin(c.get("gherkin")), "etiquetas": c.get("etiquetas") or [], "gherkin": c.get("gherkin", "")}
                for c in leer_feature(p)]
    if suf == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        lista = d.get("casos", d) if isinstance(d, dict) else d
        casos = []
        for c in lista:
            pasos = c.get("pasos")
            if isinstance(pasos, list):
                pasos = [{"accion": x.get("accion", ""), "datos": x.get("datos", ""), "esperado": x.get("resultado", x.get("esperado", ""))} for x in pasos]
            else:
                pasos = _pasos_de_texto(pasos, c.get("datos", ""), c.get("resultado", ""))
            casos.append({"id": c["id"], "titulo": c.get("titulo", ""), "prioridad": c.get("prioridad") or "Media",
                          "precondiciones": c.get("precondiciones", ""), "pasos": pasos, "tiempo_min": c.get("tiempo_min"),
                          "etiquetas": c.get("etiquetas") or [], "falta_info": c.get("falta_info") or []})
        return casos
    raise SystemExit(f"{p.name}: formato no soportado (usá .xlsx, .json, .feature o el .md con su planilla).")


def estimado_min(caso):
    try:
        v = float(str(caso.get("tiempo_min")).replace(",", "."))
        if v > 0:
            return v
    except (TypeError, ValueError):
        pass
    try:
        from estimacion import estimar_caso
        return estimar_caso({"titulo": caso.get("titulo"), "precondiciones": caso.get("precondiciones"),
                             "pasos": [{"accion": p["accion"], "datos": p.get("datos", ""), "resultado": p.get("esperado", "")} for p in caso["pasos"]]})["minutos"]
    except Exception:
        return None


# ------------------------------------------------------------------ sesión
def ruta_sesion(arg):
    p = Path(arg)
    if p.is_dir():
        p = p / "sesion.json"
    if not p.exists():
        raise SystemExit(f"No existe la sesión {p}: arrancala con `iniciar`.")
    return p


def leer(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def guardar(p, s):
    s["actualizado"] = ahora()
    Path(p).write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def iniciar(casos_ruta, historia=None, solo=None, ambiente="", tester="", navegador="", reiniciar=False, salida=None):
    casos = cargar_casos(casos_ruta)
    if solo:
        pedidos = {x.strip().upper() for x in solo.split(",") if x.strip()}
        casos = [c for c in casos if c["id"].upper() in pedidos]
        if not casos:
            raise SystemExit(f"Ninguno de {sorted(pedidos)} está en {casos_ruta}.")
    historia = historia or (re.search(r"HU-\d+", str(casos_ruta)) or [None])[0] or Path(casos_ruta).stem
    carpeta = Path(salida) if salida else PROYECTO / "output" / "ejecucion-manual" / historia
    p = carpeta / "sesion.json"
    if p.exists() and not reiniciar:
        s = leer(p)
        if s.get("estado") != "Cerrada":
            raise SystemExit(f"Ya hay una sesión en curso en {p}: retomala (`siguiente`/`retomar`) o pasá --reiniciar para empezar de cero.")
    carpeta.mkdir(parents=True, exist_ok=True)
    s = {"historia": historia, "fuente": Path(casos_ruta).as_posix(), "ambiente": ambiente, "tester": tester, "navegador": navegador,
         "inicio": ahora(), "estado": "En curso", "pausas": [],
         "casos": [{"id": c["id"], "titulo": c["titulo"], "prioridad": c["prioridad"] if c["prioridad"] in PRIORIDADES else "Media",
                    "precondiciones": c.get("precondiciones", ""), "estimado_min": estimado_min(c), "estado": "Pendiente",
                    "inicio": None, "fin": None, "duracion_s": None, "evidencia": [], "bugs": [], "obtenido": "", "motivo": "",
                    "comentario": "", "falta_info": c.get("falta_info") or [], "etiquetas": c.get("etiquetas") or [],
                    "pasos": [{"n": i, "accion": x["accion"], "datos": x.get("datos", ""), "esperado": x.get("esperado", ""),
                               "resultado": None, "obtenido": ""} for i, x in enumerate(c["pasos"], 1)]}
                   for c in casos]}
    guardar(p, s)
    return p, s


def _caso(s, cid):
    for c in s["casos"]:
        if c["id"].upper() == str(cid).upper():
            return c
    raise SystemExit(f"{cid} no está en la sesión.")


def _pausado(s):
    return bool(s["pausas"]) and not s["pausas"][-1].get("fin")


def _pausa_dentro(s, ini, fin):
    """Segundos pausados entre ini y fin (para no contarlos en la duración del caso)."""
    total = 0
    for pz in s["pausas"]:
        a, b = pz["inicio"], pz.get("fin") or fin
        a, b = max(a, ini), min(b, fin)
        if a < b:
            total += _segundos(a, b)
    return total


def siguiente(s):
    if _pausado(s):
        return {"pausada": True, "mensaje": "La sesión está en pausa: retomala para seguir."}
    for c in s["casos"]:
        if c["estado"] in ("Pendiente", "En ejecución"):
            paso = next((p for p in c["pasos"] if p["resultado"] is None), None)
            return {"caso": {k: c[k] for k in ("id", "titulo", "prioridad", "precondiciones", "estimado_min")},
                    "paso": paso, "pasos_totales": len(c["pasos"]), "estado_caso": c["estado"], **avance(s)}
    return {"terminado": True, **avance(s)}


def empezar(s, cid):
    c = _caso(s, cid)
    if c["estado"] == "Pendiente":
        c["estado"], c["inicio"] = "En ejecución", ahora()
    return c


def registrar(s, cid, resultado, paso=None, obtenido="", evidencia="", bug="", motivo="", comentario=""):
    if resultado not in RESULTADOS:
        raise SystemExit(f"Resultado inválido {resultado!r}: usá {', '.join(RESULTADOS)}.")
    c = _caso(s, cid)
    if c["estado"] == "Pendiente":
        empezar(s, cid)
    obtenido, comentario, motivo = redactar(obtenido), redactar(comentario), redactar(motivo)
    if evidencia:
        c["evidencia"].append(evidencia)
    if bug and bug not in c["bugs"]:
        c["bugs"].append(bug)
    if paso is not None:
        p = next((x for x in c["pasos"] if x["n"] == int(paso)), None)
        if not p:
            raise SystemExit(f"{cid} no tiene el paso {paso}.")
        p["resultado"], p["obtenido"] = resultado, obtenido
        if resultado == "Fallido" and not (obtenido or bug):
            raise SystemExit("Un paso Fallido necesita lo obtenido (--obtenido) o un bug (--bug).")
        # El caso se cierra solo cuando se registró el último paso o un paso falla o se bloquea.
        if resultado in ("Fallido", "Bloqueado") or all(x["resultado"] for x in c["pasos"]):
            final = "Fallido" if any(x["resultado"] == "Fallido" for x in c["pasos"]) else (
                "Bloqueado" if any(x["resultado"] == "Bloqueado" for x in c["pasos"]) else (
                    "N/A" if all(x["resultado"] == "N/A" for x in c["pasos"]) else "Aprobado"))
            _cerrar_caso(s, c, final, obtenido, motivo, comentario)
        return c
    if resultado == "Bloqueado" and not motivo:
        raise SystemExit("Bloqueado necesita el motivo (--motivo).")
    if resultado == "Fallido" and not (obtenido or bug or any(x["resultado"] == "Fallido" for x in c["pasos"])):
        raise SystemExit("Fallido necesita lo obtenido (--obtenido) o un bug (--bug).")
    _cerrar_caso(s, c, resultado, obtenido, motivo, comentario)
    return c


def _cerrar_caso(s, c, resultado, obtenido="", motivo="", comentario=""):
    c["estado"], c["fin"] = resultado, ahora()
    c["obtenido"] = obtenido or c["obtenido"]
    c["motivo"] = motivo or c["motivo"]
    c["comentario"] = comentario or c["comentario"]
    if c["inicio"]:
        c["duracion_s"] = max(0, _segundos(c["inicio"], c["fin"]) - _pausa_dentro(s, c["inicio"], c["fin"]))


def pausar(s):
    if not _pausado(s):
        s["pausas"].append({"inicio": ahora(), "fin": None})


def retomar(s):
    if _pausado(s):
        s["pausas"][-1]["fin"] = ahora()


def inconsistencias(s):
    """Casos cuyo resultado contradice sus pasos (por ejemplo, Aprobado con un paso Fallido) o les falta un dato."""
    out = []
    for c in s["casos"]:
        fallidos = [p["n"] for p in c["pasos"] if p["resultado"] == "Fallido"]
        if c["estado"] == "Aprobado" and fallidos:
            out.append({"caso": c["id"], "tipo": "Aprobado con pasos fallidos", "detalle": f"pasos {', '.join(map(str, fallidos))}"})
        if c["estado"] == "Bloqueado" and not c.get("motivo"):
            out.append({"caso": c["id"], "tipo": "Bloqueado sin motivo", "detalle": "falta explicar qué lo bloquea"})
        if c["estado"] == "Fallido" and not (c.get("bugs") or c.get("obtenido") or any(p.get("obtenido") for p in c["pasos"])):
            out.append({"caso": c["id"], "tipo": "Fallido sin bug ni resultado obtenido", "detalle": "no se puede reproducir"})
        if c["estado"] in ("Aprobado", "Fallido") and not c.get("evidencia"):
            out.append({"caso": c["id"], "tipo": "Sin evidencia", "detalle": "no se adjuntó captura ni archivo"})
    return out


def avance(s):
    total = len(s["casos"])
    hechos = [c for c in s["casos"] if c["estado"] in RESULTADOS]
    cuenta = {r: sum(1 for c in s["casos"] if c["estado"] == r) for r in RESULTADOS + ["Pendiente", "En ejecución"]}
    real = sum(c["duracion_s"] or 0 for c in hechos) / 60
    est = sum(c["estimado_min"] or 0 for c in hechos)
    terminados = cuenta["Aprobado"] + cuenta["Fallido"] + cuenta["Bloqueado"]
    return {"total": total, "ejecutados": len(hechos), "pct_avance": round(len(hechos) / total * 100) if total else 0,
            "por_resultado": cuenta, "pct_aprobado": round(cuenta["Aprobado"] / terminados * 100) if terminados else None,
            "minutos_reales": round(real, 1), "minutos_estimados": round(est, 1),
            "bugs": sorted({b for c in s["casos"] for b in c["bugs"]}), "pausada": _pausado(s)}


def resultados_ejecucion(s):
    """El JSON de scripts/generar_reporte.py con los casos ejecutados (Aprobado, Fallido o Bloqueado)."""
    casos = []
    for c in s["casos"]:
        if c["estado"] not in ("Aprobado", "Fallido", "Bloqueado"):
            continue
        motivo = c.get("motivo") or c.get("obtenido") or next((p["obtenido"] for p in c["pasos"] if p.get("obtenido")), "")
        casos.append({"id": c["id"], "titulo": c["titulo"], "prioridad": c["prioridad"], "estado": c["estado"],
                      "duracion_s": c.get("duracion_s"), "motivo": motivo + (f" ({', '.join(c['bugs'])})" if c["bugs"] else ""),
                      "evidencia": c["evidencia"][0] if c["evidencia"] else "", "falta_info": c.get("falta_info") or []})
    return {"titulo": f"Ejecución manual — {s['historia']}", "historia": s["historia"], "fecha": (s.get("fin") or ahora())[:16].replace("T", " "),
            "modo": "manual", "url": s.get("ambiente", ""), "casos": casos}


def cerrar(p, analisis=None):
    s = leer(p)
    retomar(s)
    # Por si la sesión se editó a mano: ningún secreto llega a los resultados ni al informe.
    for c in s["casos"]:
        for k in ("obtenido", "motivo", "comentario"):
            c[k] = redactar(c.get(k))
        for x in c["pasos"]:
            x["obtenido"] = redactar(x.get("obtenido"))
    s["estado"], s["fin"] = "Cerrada", ahora()
    s["inconsistencias"] = inconsistencias(s)
    s["resumen"] = avance(s)
    guardar(p, s)
    carpeta = Path(p).parent
    res = resultados_ejecucion(s)
    archivos = []
    if res["casos"]:
        ejec = PROYECTO / "output" / "ejecuciones"
        ejec.mkdir(parents=True, exist_ok=True)
        rj = ejec / f"_resultados-{s['historia']}-manual-{s['fin'][:10]}.json"
        rj.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        archivos.append(rj)
    salida = carpeta / "informe-ejecucion-manual.html"
    cmd = [sys.executable, str(RAIZ / "scripts" / "generar_informe_ejecucion_manual.py"), str(p), str(salida)]
    if analisis:
        cmd += ["--analisis", str(analisis)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print(f"No pude generar el informe: {(r.stderr or '').strip()[-400:]}", file=sys.stderr)
    else:
        archivos.append(salida)
    return s, archivos


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Sesión de ejecución manual de casos de prueba.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("iniciar")
    i.add_argument("--casos", required=True)
    for k in ("historia", "solo", "ambiente", "tester", "navegador", "salida"):
        i.add_argument(f"--{k}", default="" if k in ("ambiente", "tester", "navegador") else None)
    i.add_argument("--reiniciar", action="store_true")
    for nombre in ("siguiente", "estado", "pausar", "retomar"):
        sub.add_parser(nombre).add_argument("--sesion", required=True)
    e = sub.add_parser("empezar")
    e.add_argument("--sesion", required=True)
    e.add_argument("--caso", required=True)
    r = sub.add_parser("registrar")
    r.add_argument("--sesion", required=True)
    r.add_argument("--caso", required=True)
    r.add_argument("--resultado", required=True)
    r.add_argument("--paso")
    for k in ("obtenido", "evidencia", "bug", "motivo", "comentario"):
        r.add_argument(f"--{k}", default="")
    c = sub.add_parser("cerrar")
    c.add_argument("--sesion", required=True)
    c.add_argument("--analisis")
    a = ap.parse_args(argv)

    if a.cmd == "iniciar":
        p, s = iniciar(a.casos, a.historia, a.solo, a.ambiente, a.tester, a.navegador, a.reiniciar, a.salida)
        print(json.dumps({"sesion": p.as_posix(), "casos": len(s["casos"]), **siguiente(s)}, ensure_ascii=False, indent=1))
        return
    p = ruta_sesion(a.sesion)
    s = leer(p)
    if a.cmd == "siguiente":
        print(json.dumps(siguiente(s), ensure_ascii=False, indent=1))
    elif a.cmd == "estado":
        print(json.dumps({**avance(s), "inconsistencias": inconsistencias(s)}, ensure_ascii=False, indent=1))
    elif a.cmd in ("pausar", "retomar"):
        (pausar if a.cmd == "pausar" else retomar)(s)
        guardar(p, s)
        print("Sesión en pausa." if a.cmd == "pausar" else "Sesión retomada.")
    elif a.cmd == "empezar":
        c = empezar(s, a.caso)
        guardar(p, s)
        print(json.dumps({"caso": c["id"], "estado": c["estado"], "inicio": c["inicio"]}, ensure_ascii=False))
    elif a.cmd == "registrar":
        c = registrar(s, a.caso, a.resultado, a.paso, a.obtenido, a.evidencia, a.bug, a.motivo, a.comentario)
        guardar(p, s)
        print(json.dumps({"caso": c["id"], "estado": c["estado"], **siguiente(s)}, ensure_ascii=False, indent=1))
    else:
        s, archivos = cerrar(p, a.analisis)
        print(json.dumps({"resumen": s["resumen"], "inconsistencias": s["inconsistencias"],
                          "archivos": [x.as_posix() for x in archivos]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

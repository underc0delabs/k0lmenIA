#!/usr/bin/env python3
"""
Revisa la calidad de casos de prueba que ya existen (agente revisor-casos): planillas de casos manuales
(.xlsx de generar_casos.py) y escenarios BDD (.feature), y arma el informe con un puntaje por caso.

Uso (desde la raíz del repo):
    python scripts/revisar_casos.py [--historia HU-001] [--origen casos.xlsx,escenarios.feature,...] [--nombre revision-sprint-5]
    python scripts/revisar_casos.py --solo-informe --nombre HU-001      → aplica el analisis.json del agente y regenera

Sin --origen toma los de la historia (output/casos-de-prueba/manuales/casos-HU-XXX.xlsx y bdd/HU-XXX*.feature)
o, sin historia, todos los de output/casos-de-prueba/.

Qué revisa (cada problema con su severidad; el puntaje del caso es 100 menos Alta 25 · Media 10 · Baja 4):
  - Manuales: sin resultado esperado, resultado vago ("funciona correctamente"), pasos vagos ("verificar que
    funcione", "etc."), pasos sin una acción clara, título poco descriptivo, demasiados pasos (o uno solo), datos
    escritos dentro de los pasos en vez de en Datos de prueba, precondiciones que faltan (el paso supone un
    estado), sin prioridad, un caso que verifica demasiadas cosas.
  - BDD: escenario sin Then, Then sin una verificación concreta, pasos imperativos de interfaz (clic en el botón,
    selectores), orden Given/When/Then roto, Scenario Outline sin Examples, sin @CP-XXX.
  - Entre casos: posibles duplicados (pasos y título muy parecidos).
  - Por historia: sin casos negativos o de borde.
Además calcula el tiempo estimado de ejecución manual de cada caso (scripts/estimacion.py).

Deja output/revision-casos/<HU o nombre>/ con revision.json e informe-revision.html; la revisión anterior
pasa a historial/ (se guardan las últimas 5).
"""
import os
import argparse
import datetime
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "scripts" / "gestion"))
import _historial  # noqa: E402
from estimacion import estimar_caso, formatear, NEGATIVO  # noqa: E402

PESO = {"Alta": 25, "Media": 10, "Baja": 4}
SEV_ORDEN = {"Alta": 0, "Media": 1, "Baja": 2}
VAGO_RESULTADO = re.compile(r"funcion\w* (correctamente|bien|ok)|correctamente\s*\.?$|todo (bien|ok|correcto)|sin errores\s*\.?$|como se espera|lo esperado|\bok\b\s*\.?$|exitosamente\s*\.?$", re.I)
VAGO_PASO = re.compile(r"verific\w* que (funcione|ande|est[eé] bien)|prob\w* (la|el) (funcionalidad|sistema|pantalla)\b|\betc\b|\by/o\b|lo que corresponda|valid\w* todo|segun corresponda|seg[uú]n corresponda|\bcosas\b", re.I)
VERBO = re.compile(r"^\s*(?:el usuario |la usuaria |se |)?(ir|naveg|acced|abr|entr|visit|hac|clic|presion|toc|puls|seleccion|eleg|marc|desmarc|complet|escrib|ingres|carg|tipe|llen|"
                   r"adjunt|sub|descarg|export|import|imprim|esper|recib|revis|verific|valid|comprob|observ|consult|busc|filtr|orden|agreg|elimin|borr|edit|modific|"
                   r"guard|envi|confirm|acept|cancel|cerr|inici|log|registr|compr|pag|volv|refresc|recarg|desplaz|arrastr|copi|peg|cambi|activ|desactiv|dejar|deja)", re.I)
DATO_FIJO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|\"[^\"]{3,}\"", re.I)
ESTADO_PREVIO = re.compile(r"(estando|con (el|la|su) (usuario|sesi[oó]n|cuenta) (logueado|iniciad|activ)|logueado|con sesi[oó]n iniciada|con productos en el carrito|que ya (tiene|existe))", re.I)
UI_IMPERATIVO = re.compile(r"clic\w* en (el|la) (bot[oó]n|link|enlace|campo)|hace clic|presiona el bot[oó]n|xpath|css=|#[\w-]+\b|\.[\w-]+\s*>|data-testid|\bid=\w+", re.I)
THEN_VAGO = re.compile(r"(todo|el sistema|la pantalla|la aplicaci[oó]n) (funciona|anda|responde) (correctamente|bien)|se ve (bien|correcto)|es correcto\s*$|^\s*(ok|funciona)\s*$", re.I)


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "").lower()).strip()


def _tokens(s):
    return {t for t in re.split(r"[^a-záéíóúñü0-9]+", _norm(s)) if len(t) > 2}


def revisar_manual(c):
    h = []

    def p(sev, tipo, titulo, sugerencia=""):
        h.append({"severidad": sev, "tipo": tipo, "titulo": titulo, "sugerencia": sugerencia})

    titulo = c.get("titulo", "")
    if len(titulo.split()) < 3 or re.match(r"^\s*(caso|prueba|test)\b", titulo, re.I) or re.search(r"verificar (la )?funcionalidad", titulo, re.I):
        p("Media", "Título", f"Título poco descriptivo: “{titulo}”", "Que diga qué se prueba y en qué condición: “Inicio de sesión con contraseña incorrecta muestra un error”.")
    pasos = c.get("pasos") or []
    resultado = " ".join(x.get("resultado", "") for x in pasos).strip()
    if not resultado:
        p("Alta", "Resultado esperado", "No tiene resultado esperado", "Sin resultado esperado no se puede decidir si pasó o falló.")
    elif VAGO_RESULTADO.search(resultado):
        p("Media", "Resultado esperado", f"Resultado esperado vago: “{resultado[:80]}”", "Decí qué se ve exactamente: el mensaje, el dato o la pantalla.")
    for i, x in enumerate(pasos, 1):
        acc = x.get("accion", "")
        if VAGO_PASO.search(acc):
            p("Media", "Paso vago", f"Paso {i} vago: “{acc[:80]}”", "Una acción concreta por paso, sin “etc.” ni “verificar que funcione”.")
        elif acc and acc != "(sin pasos)" and not VERBO.search(acc):
            p("Baja", "Paso sin acción", f"Paso {i} no empieza con una acción: “{acc[:80]}”", "Empezá cada paso con el verbo: Ir a…, Completar…, Hacer clic en…")
    if len(pasos) > 12:
        p("Media", "Largo", f"Tiene {len(pasos)} pasos", "Probablemente prueba más de una cosa: dividilo en casos más chicos.")
    elif len(pasos) == 1 and pasos[0].get("accion") not in ("", "(sin pasos)"):
        p("Baja", "Largo", "Tiene un solo paso", "Revisá si faltan pasos para reproducirlo.")
    datos_col = " ".join(str(x.get("datos") or "") for x in pasos).strip()
    fijos = [m.group(0) for x in pasos for m in DATO_FIJO.finditer(x.get("accion", ""))]
    if fijos and not datos_col:
        p("Baja", "Datos de prueba", f"Datos escritos dentro de los pasos: {', '.join(fijos[:3])}", "Pasalos a la columna Datos de prueba: así se reutiliza el caso con otros datos.")
    if not str(c.get("precondiciones") or "").strip() and any(ESTADO_PREVIO.search(x.get("accion", "")) for x in pasos):
        p("Baja", "Precondiciones", "Un paso supone un estado previo y no hay precondiciones", "Escribí en Precondiciones el estado del que parte (usuario logueado, carrito con productos…).")
    if not c.get("prioridad"):
        p("Baja", "Prioridad", "Sin prioridad", "Crítica, Alta, Media o Baja.")
    if resultado and len([s for s in re.split(r"[;\n]|\.\s", resultado) if s.strip()]) >= 5:
        p("Baja", "Alcance", "El resultado esperado verifica muchas cosas", "Un caso que verifica 5 o más cosas es difícil de diagnosticar cuando falla: separalo.")
    return h


def revisar_bdd(c):
    h = []

    def p(sev, tipo, titulo, sugerencia=""):
        h.append({"severidad": sev, "tipo": tipo, "titulo": titulo, "sugerencia": sugerencia})

    lineas = [l.strip() for l in str(c.get("gherkin") or "").splitlines()]
    claves, ultimo = [], None
    for l in lineas:
        m = re.match(r"(Given|When|Then|And|But)\s+(.*)", l)
        if not m:
            continue
        kw = m.group(1)
        if kw in ("And", "But"):
            kw = ultimo or kw
        ultimo = kw
        claves.append((kw, m.group(2)))
    tipos = [k for k, _ in claves]
    if "Then" not in tipos:
        p("Alta", "Then", "El escenario no tiene Then", "Sin Then no verifica nada: agregá el resultado esperado.")
    for k, t in claves:
        if k == "Then" and THEN_VAGO.search(t):
            p("Media", "Then", f"Then vago: “{t[:80]}”", "Verificá algo observable: el mensaje, el dato, la URL.")
        if k in ("Given", "When") and UI_IMPERATIVO.search(t):
            p("Baja", "Estilo", f"Paso imperativo de interfaz: “{t[:80]}”", "BDD declarativo: describí la intención (“inicia sesión con…”), no los clics; los detalles van en los steps.")
    orden = {"Given": 0, "When": 1, "Then": 2}
    secuencia = [orden[k] for k in tipos if k in orden]
    if any(b < a for a, b in zip(secuencia, secuencia[1:])):
        p("Media", "Estructura", "El orden Given → When → Then está roto", "Un escenario = un contexto, una acción y sus verificaciones; si necesitás otra acción, es otro escenario.")
    if tipos.count("When") > 3:
        p("Baja", "Estructura", f"{tipos.count('When')} pasos When", "Demasiadas acciones: probablemente son dos escenarios.")
    if re.search(r"Scenario (Outline|Template):", c.get("gherkin") or "") and "Examples:" not in (c.get("gherkin") or ""):
        p("Alta", "Estructura", "Scenario Outline sin Examples", "Sin la tabla de ejemplos no se ejecuta.")
    if not re.match(r"^CP(-API)?-\d+$", c.get("id", "")):
        p("Baja", "Trazabilidad", "El escenario no tiene @CP-XXX", "Sin el tag no se puede trazar con el caso, la gestión ni los resultados.")
    return h


def duplicados(casos, umbral=0.85):
    salida = []
    firmas = [(c, _tokens(c["titulo"] + " " + " ".join(x.get("accion", "") for x in c.get("pasos") or []) + " " + (c.get("gherkin") or ""))) for c in casos]
    for i in range(len(firmas)):
        for j in range(i + 1, len(firmas)):
            a, b = firmas[i][1], firmas[j][1]
            if len(a) < 4 or len(b) < 4:
                continue
            sim = len(a & b) / len(a | b)
            if sim >= umbral:
                salida.append((firmas[i][0], firmas[j][0], round(sim * 100)))
    return salida


def origenes(a):
    if a.origen:
        return [Path(x.strip()) for x in a.origen.split(",") if x.strip()]
    hu = a.historia
    base = PROYECTO / "output" / "casos-de-prueba"
    if hu:
        return [Path(x) for x in sorted(glob.glob(str(base / "manuales" / f"casos-{hu}.xlsx")) + glob.glob(str(base / "bdd" / f"{hu}*.feature")))]
    return [Path(x) for x in sorted(glob.glob(str(base / "manuales" / "casos-HU-*.xlsx")) + glob.glob(str(base / "bdd" / "*.feature")))]


def revisar(archivos):
    from lectores import leer_feature, leer_xlsx
    casos = []
    for f in archivos:
        try:
            lista = leer_xlsx(f) if f.suffix.lower() == ".xlsx" else leer_feature(f)
        except Exception as e:  # una planilla con otro formato se informa y se sigue
            print(f"[!] No pude leer {f.name}: {e}", file=sys.stderr)
            continue
        m = re.search(r"(HU-\d+)", f.name, re.I)
        for c in lista:
            tags = [t.upper() for t in c.get("etiquetas") or []]
            hu = next((t for t in tags if re.fullmatch(r"HU-\d+", t)), m.group(1).upper() if m else "SIN-HU")
            c["historia"] = hu
            try:
                c["archivo"] = f.resolve().relative_to(PROYECTO).as_posix()
            except ValueError:
                c["archivo"] = str(f)
            casos.append(c)
    for c in casos:
        c["hallazgos"] = revisar_manual(c) if c["tipo"] == "manual" else revisar_bdd(c)
        est = estimar_caso(c)
        c["tiempo_min"] = est["minutos"]
        c["tiempo"] = est["texto"]
    for a, b, sim in duplicados(casos):
        b["hallazgos"].append({"severidad": "Media", "tipo": "Duplicado", "titulo": f"Muy parecido a {a['id']} ({sim} %)",
                               "sugerencia": f"Si prueban lo mismo, dejá uno; si difieren, que el título diga en qué.", "relacionado": a["id"]})
    for c in casos:
        c["hallazgos"].sort(key=lambda x: SEV_ORDEN[x["severidad"]])
        c["puntaje"] = max(0, 100 - sum(PESO[x["severidad"]] for x in c["hallazgos"]))
    historias = {}
    for c in casos:
        historias.setdefault(c["historia"], []).append(c)
    por_historia = []
    for hu, cs in sorted(historias.items()):
        neg = [c for c in cs if NEGATIVO.search(" ".join([c.get("titulo", ""), c.get("descripcion", ""), " ".join(c.get("etiquetas") or [])]))]
        h = []
        if len(cs) >= 3 and not neg:
            h.append({"severidad": "Media", "tipo": "Cobertura", "titulo": f"{hu} no tiene casos negativos ni de borde",
                      "sugerencia": "Sumá casos con datos inválidos, vacíos y valores límite (skill tecnicas-de-diseno)."})
        por_historia.append({"historia": hu, "casos": len(cs), "negativos": len(neg), "puntaje_prom": round(sum(c["puntaje"] for c in cs) / len(cs)),
                             "tiempo_min": sum(c["tiempo_min"] for c in cs), "hallazgos": h})
    return casos, por_historia


def resumen(casos, por_historia):
    hall = [x for c in casos for x in c["hallazgos"]] + [x for h in por_historia for x in h["hallazgos"]]
    total_t = sum(c["tiempo_min"] for c in casos)
    return {"casos": len(casos), "manuales": sum(1 for c in casos if c["tipo"] == "manual"), "bdd": sum(1 for c in casos if c["tipo"] != "manual"),
            "puntaje_prom": round(sum(c["puntaje"] for c in casos) / len(casos)) if casos else None,
            "sin_problemas": sum(1 for c in casos if not c["hallazgos"]), "a_mejorar": sum(1 for c in casos if c["puntaje"] < 70),
            "hallazgos": len(hall), "duplicados": sum(1 for x in hall if x["tipo"] == "Duplicado"),
            "sin_resultado": sum(1 for x in hall if x["tipo"] in ("Resultado esperado", "Then") and x["severidad"] == "Alta"),
            "tiempo_total_min": total_t, "tiempo_total": formatear(total_t),
            "por_severidad": {s: sum(1 for x in hall if x["severidad"] == s) for s in ("Alta", "Media", "Baja")},
            "por_tipo": {t: sum(1 for x in hall if x["tipo"] == t) for t in sorted({x["tipo"] for x in hall})}}


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Revisión de la calidad de los casos de prueba")
    ap.add_argument("--historia")
    ap.add_argument("--origen", help="archivos .xlsx o .feature separados por coma")
    ap.add_argument("--nombre", help="carpeta de salida (por defecto la historia o 'todos')")
    ap.add_argument("--solo-informe", action="store_true")
    ap.add_argument("--salida")
    a = ap.parse_args()
    a.historia = a.historia.upper() if a.historia else None
    nombre = a.nombre or a.historia or "todos"
    carpeta = Path(a.salida) if a.salida else PROYECTO / "output" / "revision-casos" / nombre
    datos_arch = carpeta / "revision.json"
    if not a.solo_informe:
        archivos = origenes(a)
        if not archivos:
            sys.exit("No encontré casos para revisar: pasá --origen o generá primero los casos de la historia.")
        casos, por_historia = revisar(archivos)
        _historial.archivar(carpeta, ["revision.json", "analisis.json", "informe-revision.html"], "revision.json")
        carpeta.mkdir(parents=True, exist_ok=True)
        casos.sort(key=lambda c: (c["puntaje"], c["historia"], c["id"]))
        ahora = datetime.datetime.now()
        datos = {"nombre": nombre, "historia": a.historia, "fecha": ahora.isoformat(timespec="seconds"), "marca": ahora.strftime("%Y%m%d-%H%M%S"),
                 "origenes": [str(x) for x in archivos], "casos": casos, "por_historia": por_historia, "resumen": resumen(casos, por_historia)}
        datos_arch.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        r = datos["resumen"]
        print(f'Casos: {r["casos"]} ({r["manuales"]} manuales, {r["bdd"]} BDD) · puntaje promedio {r["puntaje_prom"]} · a mejorar: {r["a_mejorar"]} · '
              f'hallazgos: {r["hallazgos"]} · tiempo de ejecución manual: {r["tiempo_total"]}')
    args = [sys.executable, str(RAIZ / "scripts" / "generar_informe_revision.py"), str(datos_arch), str(carpeta / "informe-revision.html")]
    if (carpeta / "analisis.json").exists():
        args += ["--analisis", str(carpeta / "analisis.json")]
    res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:  # p. ej. un analisis.json mal formado: el agente tiene que enterarse, no seguir de largo
        print(res.stderr.strip() or res.stdout.strip(), file=sys.stderr)
        sys.exit(f"No se pudo armar el informe de la revisión (revisá {carpeta / 'analisis.json'}).")
    print(res.stdout.strip() or res.stderr.strip())


if __name__ == "__main__":
    main()

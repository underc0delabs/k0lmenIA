#!/usr/bin/env python3
"""
Informe HTML de la puesta en marcha de k0lmenIA (skill empezar): qué está listo, qué falta y cómo resolverlo, a partir
de la salida JSON del doctor.

Uso (desde la raíz del repo; con el plugin, `k0lmenia doctor -- --json` y `k0lmenia py scripts/…`):
    python scripts/generar_informe_entorno.py output/entorno/doctor.json output/entorno/informe-entorno.html --correr [--analisis analisis.json]

Con --correr corre el doctor y guarda su JSON en la ruta del primer argumento (así no hace falta redirigir la salida:
desde PowerShell, un ">" la guarda en UTF-16, y con npm run se cuela el encabezado de npm). Sin --correr lee un JSON ya guardado.

doctor.json: {"resumen": {"ok", "aviso", "falta"}, "resultados": [{"seccion", "estado": "ok|aviso|falta", "texto", "ayuda"}]}
El análisis opcional (lo escribe la conversación principal con el skill empezar) aporta "veredicto", "resumen",
"conectores_elegidos", "proximos_pasos" y "primera_tarea", con su bloque "en".
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n import escribir_bilingue, localizar  # noqa: E402
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list, stacked_bars, donut_panel,  # noqa: E402
                              gauge, e, OK, AVISO, CRITICO)

SECCIONES = {"python": "Python", "node": "Node y k0lmena", "herramientas": "Opcionales", "fuentes": "Tipografías",
             "env": "Archivo .env", "integraciones": "Integraciones", "conectores": "Conectores MCP",
             "repo": "Git", "extras": "Portal y evals"}
ESTADO = {"ok": ("Listo", "ok"), "aviso": ("Opcional o a revisar", "warn"), "falta": ("Falta", "bad")}


def leer_json(ruta):
    """El JSON del doctor, venga en UTF-8 (con o sin BOM) o en UTF-16 (redirección de PowerShell)."""
    crudo = Path(ruta).read_bytes()
    for cod in ("utf-8-sig", "utf-16"):
        try:
            return json.loads(crudo.decode(cod))
        except (UnicodeDecodeError, ValueError):
            continue
    raise SystemExit(f"{ruta} no es la salida JSON del doctor (python scripts/doctor.py --json).")


def correr_doctor(destino):
    import subprocess
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "doctor.py"), "--json"], capture_output=True, text=True, encoding="utf-8")
    if not r.stdout.strip().startswith("{"):
        raise SystemExit(f"El doctor no devolvió JSON: {(r.stderr or r.stdout).strip()[-300:]}")
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    Path(destino).write_text(r.stdout, encoding="utf-8")
    return destino


def generar(doctor_json, salida, analisis_json=None):
    datos = leer_json(doctor_json)
    analisis = json.loads(Path(analisis_json).read_text(encoding="utf-8")) if analisis_json else {}
    escribir_bilingue(salida, lambda: _html(datos, localizar(analisis)))
    return salida


def _html(d, a):
    res = d.get("resultados") or []
    r = d.get("resumen") or {}
    ok, aviso, falta = r.get("ok", 0), r.get("aviso", 0), r.get("falta", 0)
    total = ok + aviso + falta or 1
    listo = round(ok / total * 100)
    if a.get("veredicto"):
        veredicto, tono = a["veredicto"], a.get("veredicto_tono") or "ok"
    elif falta:
        veredicto, tono = f"Falta resolver {falta} punto(s) para empezar", "bad"
    elif aviso:
        veredicto, tono = "Listo para empezar (hay opcionales para sumar después)", "warn"
    else:
        veredicto, tono = "Todo listo para empezar", "ok"

    cuerpo = banner(veredicto, tono)
    cuerpo += section("Resumen", kpi_tiles([
        ("Listo", ok, "ok", "chequeos en orden", "ok"),
        ("Opcional o a revisar", aviso, "warn" if aviso else "ok", "no frenan el primer uso", "warn"),
        ("Falta", falta, "bad" if falta else "ok", "hay que resolverlo para empezar", "bad"),
        ("Preparado", f"{listo}%", "ok" if listo >= 80 else "warn", "de los chequeos del doctor", "objetivo", {"pct": listo}),
    ]) + (f'<div class="cardbody"><p>{e(a["resumen"])}</p></div>' if a.get("resumen") else ""))

    cuerpo += section("Estado general", donut_panel([(ok, OK, "Listo"), (aviso, AVISO, "Opcional o a revisar"), (falta, CRITICO, "Falta")],
                                                    listo, "listo"), ancho=6)
    por_sec = {}
    for x in res:
        c = por_sec.setdefault(x.get("seccion", "otros"), [0, 0, 0])
        c[{"ok": 0, "aviso": 1}.get(x.get("estado"), 2)] += 1
    cuerpo += section("Por área", stacked_bars([(SECCIONES.get(s, s), v) for s, v in por_sec.items()],
                                               [("Listo", OK), ("Opcional o a revisar", AVISO), ("Falta", CRITICO)]), ancho=6)

    faltan = [x for x in res if x.get("estado") == "falta"]
    if faltan:
        cuerpo += section("Lo que falta para empezar", table(["Área", "Qué falta", "Cómo resolverlo"],
                          [[e(SECCIONES.get(x.get("seccion"), x.get("seccion", ""))), e(x.get("texto", "")), f'<code>{e(x.get("ayuda", ""))}</code>' if x.get("ayuda") else "—"]
                           for x in faltan]), f"{len(faltan)} punto(s)")
    else:
        cuerpo += section("Lo que falta para empezar", banner("Nada: lo imprescindible está instalado y configurado.", "ok"))
    opcionales = [x for x in res if x.get("estado") == "aviso"]
    if opcionales:
        cuerpo += section("Opcionales y a revisar", table(["Área", "Qué", "Cómo sumarlo"],
                          [[e(SECCIONES.get(x.get("seccion"), x.get("seccion", ""))), e(x.get("texto", "")), f'<code>{e(x.get("ayuda", ""))}</code>' if x.get("ayuda") else "—"]
                           for x in opcionales]), "solo hacen falta para algunos agentes")
    if a.get("conectores_elegidos"):
        cuerpo += section("Herramientas del equipo", doc_list(a["conectores_elegidos"]), ancho=6)
    if a.get("primera_tarea"):
        cuerpo += section("Primera tarea sugerida", f'<div class="cardbody"><p class="lead">{e(a["primera_tarea"])}</p></div>', ancho=6)
    if a.get("proximos_pasos"):
        cuerpo += section("Próximos pasos", doc_list(a["proximos_pasos"]))
    cuerpo += section("Todos los chequeos", table(["Área", "Estado", "Detalle"],
                      [[e(SECCIONES.get(x.get("seccion"), x.get("seccion", ""))), e(ESTADO.get(x.get("estado"), ("—", ""))[0]), e(x.get("texto", ""))] for x in res]),
                      f"{len(res)} chequeo(s)")
    return page("Puesta en marcha", "k0lmenIA · Empezar", meta([("Chequeos", str(len(res)))]), cuerpo)


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de la puesta en marcha (salida JSON del doctor).")
    ap.add_argument("doctor_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis")
    ap.add_argument("--correr", action="store_true", help="corre el doctor y guarda su JSON en doctor_json")
    a = ap.parse_args()
    if a.correr:
        correr_doctor(a.doctor_json)
    if not Path(a.doctor_json).exists():
        raise SystemExit(f"No existe {a.doctor_json}: agregá --correr para que corra el doctor.")
    print(generar(a.doctor_json, a.salida, a.analisis))


if __name__ == "__main__":
    main()

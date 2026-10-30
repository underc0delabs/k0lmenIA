#!/usr/bin/env python3
"""
Estado de los conectores MCP de k0lmenIA en HTML (modo oscuro, ES/EN): cuáles vienen incluidos, cuáles tenés activos,
cuáles están listos para activar y a cuáles les faltan datos en el .env. No muestra ningún valor del .env: solo si cada
variable está o no.

Uso (desde la raíz del repo; con el plugin, k0lmenia py scripts/generar_informe_conectores.py):
    python scripts/generar_informe_conectores.py [--salida output/conectores/estado.html]
    npm run conector -- listar --html          (lo mismo, después de listar en la terminal)

Las reglas (qué variables pide cada conector, cuáles se autorizan con OAuth) son las del doctor (scripts/doctor.py),
y el catálogo, scripts/mcp/catalogo.json. Además de estado.html deja conectores.json (los mismos datos, sin valores).
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import doctor  # noqa: E402
from _i18n import escribir_bilingue, localizar  # noqa: E402
from _estilos_reporte import (page, meta, section, kpi_tiles, banner, table, doc_list, donut_panel, stacked_bars,  # noqa: E402
                              bar_chart, e, _pastilla, SERIES, OK, CRITICO, NEUTRO)

RAIZ = Path(__file__).resolve().parents[1]
ESTADOS = ["Listo", "Activo con datos faltantes", "Listo para activar", "Faltan datos"]
COLOR = {"Listo": OK, "Activo con datos faltantes": CRITICO, "Listo para activar": SERIES[2], "Faltan datos": NEUTRO}
ICONO = {"Listo": "✓", "Activo con datos faltantes": "✕", "Listo para activar": "▶", "Faltan datos": "–"}


def autenticacion(nombre, env):
    """Cómo se autoriza el conector con lo que hay hoy en el .env."""
    if nombre in doctor.CONECTORES_OAUTH:
        return "OAuth con tu cuenta"
    if nombre in doctor.CONECTORES_TOKEN_OPCIONAL:
        return "Token del .env" if env.get(doctor.CONECTORES_TOKEN_OPCIONAL[nombre]) else "OAuth con tu cuenta"
    return "Credenciales del .env" if doctor.VARIABLES_CONECTOR.get(nombre) else "Sin credenciales"


def requeridas(nombre, env):
    return doctor.VARIABLES_CONECTOR.get(nombre, [])


def estado(env, catalogo, incluidos, activos, como_plugin=False):
    """Estado de cada conector. Puro: recibe el .env (solo se mira si cada variable está), el catálogo y los activos."""
    comando = "k0lmenia conector -- activar" if como_plugin else "npm run conector -- activar"
    filas = []
    for n in incluidos:
        filas.append({"nombre": n, "grupo": "Incluidos", "descripcion": "Viene habilitado para todos (.mcp.json)",
                      "descripcion_en": "Enabled for everyone (.mcp.json)", "origen": "oficial", "estado_proveedor": "",
                      "activo": True, "faltan": doctor.faltantes(requeridas(n, env), env), "autenticacion": autenticacion(n, env),
                      "como": "—"})
    for n, c in catalogo.items():
        faltan = doctor.faltantes(requeridas(n, env), env)
        filas.append({"nombre": n, "grupo": c.get("grupo", "Otros"), "descripcion": c.get("descripcion", ""),
                      "descripcion_en": c.get("descripcion_en", c.get("descripcion", "")), "origen": c.get("origen", "oficial"),
                      "estado_proveedor": c.get("estado", ""), "activo": n in activos, "faltan": faltan,
                      "autenticacion": autenticacion(n, env), "como": f"{comando} {n}"})
    for f in filas:
        if f["activo"]:
            f["estado"] = "Activo con datos faltantes" if f["faltan"] else "Listo"
        else:
            f["estado"] = "Faltan datos" if f["faltan"] else "Listo para activar"
    cuenta = Counter(f["estado"] for f in filas)
    opcionales = [f for f in filas if f["grupo"] != "Incluidos"]
    resumen = {"total": len(filas), "incluidos": len(incluidos), "opcionales": len(opcionales),
               "activos": sum(1 for f in filas if f["activo"]), "activos_opcionales": sum(1 for f in opcionales if f["activo"]),
               "con_faltantes": cuenta["Activo con datos faltantes"], "listos_para_activar": cuenta["Listo para activar"],
               "oficiales": sum(1 for f in opcionales if f["origen"] == "oficial"), "por_estado": {k: cuenta[k] for k in ESTADOS}}
    if resumen["con_faltantes"]:
        veredicto, tono = "Hay conectores activos a los que les faltan datos en el .env", "bad"
    elif not resumen["activos_opcionales"]:
        veredicto, tono = "Solo están los conectores incluidos: activá los de las herramientas que usa tu equipo", "warn"
    else:
        veredicto, tono = "Los conectores activos tienen todo lo que necesitan", "ok"
    return {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "veredicto": veredicto, "veredicto_tono": tono,
            "resumen": resumen, "conectores": filas}


def _html(d, sin_conector):
    r = d["resumen"]
    filas = d["conectores"]
    kpis = [("Conectores disponibles", r["total"], "", f'{r["incluidos"]} incluido(s) · {r["opcionales"]} opcional(es)', "link"),
            ("Activos", r["activos"], "ok" if r["activos_opcionales"] else "warn", f'{r["activos_opcionales"]} opcional(es) activado(s)', "ok"),
            ("Activos con datos faltantes", r["con_faltantes"], "bad" if r["con_faltantes"] else "ok", "completalos en el .env", "warn"),
            ("Listos para activar", r["listos_para_activar"], "", "tienen todo lo que necesitan", "rayo"),
            ("Oficiales del proveedor", f'{round(r["oficiales"] / r["opcionales"] * 100) if r["opcionales"] else 0}%', "",
             f'{r["oficiales"]} de {r["opcionales"]} opcionales', "escudo", {"pct": round(r["oficiales"] / r["opcionales"] * 100) if r["opcionales"] else 0})]
    cuerpo = banner(d["veredicto"], d["veredicto_tono"]) + section("Resumen", kpi_tiles(kpis))

    activos = r["activos"]
    dona = donut_panel([(r["por_estado"][k], COLOR[k], k) for k in ESTADOS], round(activos / r["total"] * 100) if r["total"] else 0, "activos")
    grupos = list(dict.fromkeys(f["grupo"] for f in filas))
    series = [(k, COLOR[k]) for k in ESTADOS]
    por_grupo = stacked_bars([(g, [sum(1 for f in filas if f["grupo"] == g and f["estado"] == k) for k in ESTADOS]) for g in grupos], series)
    cuerpo += section("Estado de los conectores", dona, ancho=5) + section("Por grupo", por_grupo, ancho=7)

    auth = Counter(f["autenticacion"] for f in filas)
    cuerpo += section("Cómo se autorizan", bar_chart([(k, v, SERIES[i % len(SERIES)]) for i, (k, v) in enumerate(auth.most_common())], ancho_etiqueta=170),
                      "según lo que hay hoy en tu .env", ancho=5)
    pendientes = [f for f in filas if f["estado"] == "Activo con datos faltantes"]
    if pendientes:
        cuerpo += section("Para completar ahora", table(["Conector", "Faltan en el .env"],
                          [[f'<b>{e(f["nombre"])}</b>', e(", ".join(f["faltan"]))] for f in pendientes]), ancho=7)
    else:
        listos = [f for f in filas if f["estado"] == "Listo para activar"]
        cuerpo += section("Listos para activar", table(["Conector", "Cómo activarlo"],
                          [[f'<b>{e(f["nombre"])}</b>', f'<code>{e(f["como"])}</code>'] for f in listos[:12]]) if listos
                          else banner("No hay conectores listos para activar: completá primero sus datos en el .env.", "warn"), ancho=7)

    tabla = []
    for f in filas:
        origen = ("Oficial" if f["origen"] == "oficial" else "Comunitario") + (f' · {f["estado_proveedor"]}' if f["estado_proveedor"] else "")
        if f["faltan"]:
            accion = f'<span class="muted">Faltan:</span> {e(", ".join(f["faltan"]))}'
        else:
            accion = f'<code>{e(f["como"])}</code>' if f["como"] != "—" else '<span class="muted">Ya está habilitado</span>'
        tabla.append([f'<b>{e(f["nombre"])}</b><br><span class="muted">{e(f["grupo"])}</span>', e(f["descripcion"]) + f'<br><span class="muted">{e(origen)}</span>',
                      _pastilla(f["estado"], COLOR[f["estado"]], ICONO[f["estado"]]), e(f["autenticacion"]), accion])
    cuerpo += section("Todos los conectores", table(["Conector", "Qué trae", "Estado", "Autorización", "Qué falta o cómo activarlo"], tabla),
                      f'{len(filas)} en total')
    if sin_conector:
        cuerpo += section("Sin conector MCP (se usan por API)", table(["Herramienta", "Por qué y qué usar"],
                          [[f'<b>{e(k.capitalize())}</b>', e(v)] for k, v in sin_conector.items()]))
    pasos = []
    if pendientes:
        pasos.append("Completá en el .env los datos que faltan de los conectores activos (o corré npm run configurar).")
    pasos += ["Después de activar o desactivar un conector, reiniciá Claude Code y verificá con /mcp.",
              "Los conectores que dicen \"OAuth con tu cuenta\" te piden iniciar sesión la primera vez que los usás.",
              "Las credenciales van solo en el .env (nunca en el chat): este informe solo muestra si cada variable está o no."]
    cuerpo += section("Próximos pasos", doc_list(pasos))
    return page("Estado de los conectores MCP", "Conectores MCP", meta([("Generado", d["fecha"]), ("Conectores", r["total"]),
                                                                         ("Activos", r["activos"])]), cuerpo)


def recolectar():
    ctx = doctor.contexto(rapido=True)
    catalogo_json = json.loads((RAIZ / "scripts" / "mcp" / "catalogo.json").read_text(encoding="utf-8"))
    try:
        incluidos = list(json.loads((RAIZ / ".mcp.json").read_text(encoding="utf-8")).get("mcpServers", {}))
    except (OSError, ValueError):
        incluidos = []
    activos = set(ctx["locales"]) | set(ctx["habilitados"])
    datos = estado(ctx["env"], catalogo_json["conectores"], incluidos, activos, como_plugin=doctor.PROYECTO != RAIZ.resolve())
    return datos, catalogo_json.get("_sin_conector", {}), catalogo_json.get("_sin_conector_en", {})


def generar(datos, salida, sin_conector=None, sin_conector_en=None):
    """Escribe es/<salida> y en/<salida> (más el acceso <salida>) y conectores.json al lado."""
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    datos = {**datos, "sin_conector": sin_conector or {},
             "en": {"conectores": [{"descripcion": f["descripcion_en"]} for f in datos["conectores"]],
                    "sin_conector": sin_conector_en or {}}}
    (salida.parent / "conectores.json").write_text(json.dumps({k: v for k, v in datos.items() if k != "en"}, ensure_ascii=False, indent=2),
                                                   encoding="utf-8")
    escribir_bilingue(salida, lambda: _html_localizado(datos))
    return salida


def _html_localizado(datos):
    d = localizar(datos)
    return _html(d, d.get("sin_conector"))


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Estado de los conectores MCP en HTML.")
    ap.add_argument("--salida", default=str(doctor.PROYECTO / "output" / "conectores" / "estado.html"))
    a = ap.parse_args(argv)
    datos, sin, sin_en = recolectar()
    print(generar(datos, a.salida, sin, sin_en))


if __name__ == "__main__":
    main()

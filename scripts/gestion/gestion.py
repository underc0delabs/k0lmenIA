#!/usr/bin/env python3
"""Gestión de pruebas en Xray (Cloud o Server/DC), QMetry para Jira (QTM4J) y AIO Tests.

Mismos comandos para todas las herramientas; cuál se usa sale de GESTION_HERRAMIENTA
(.env de la raíz) o de --herramienta. Todo comando imprime un JSON con el resultado.

    python scripts/gestion/gestion.py [--herramienta X] [--dry-run] <comando> [opciones]

Comandos:
  carpeta              --ruta "/HU-001 Registro"
  subir-casos          --origen <casos.xlsx | escenarios.feature> --carpeta "/HU-001 Registro"
                       [--historia PROJ-12] [--ids CP-001,CP-002] [--traza HU-001]
  vincular             --historia PROJ-12 (--casos PROJ-45,PROJ-46 | --ciclo PROJ-60)
  crear-ciclo          --nombre "HU-001 Sprint 5" [--descripcion ...] [--historia PROJ-12]
                       [--casos PROJ-45,PROJ-46 | --traza HU-001 [--ids CP-001,...]]
  agregar-a-ciclo      --ciclo PROJ-60 (--casos PROJ-45,... | --traza HU-001 [--ids ...])
  extraer-resultados   --reporte herramientas/k0lmena/reports/web/cucumber-report.json
                       [--salida output/gestion/resultados-<fecha>.json]
  publicar-resultados  --ciclo PROJ-60 --resultados <resultados.json> [--traza HU-001]
                       [--sin-video]

Herramientas: xray-cloud | xray-dc | qtm4j | aio
--traza <nombre>: archivo de trazabilidad output/gestion/<nombre>-<herramienta>.json
(qué CP-XXX es qué key). Por defecto, el valor de --historia.
--dry-run: muestra los requests sin enviarlos (para revisar antes de tocar la herramienta real).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (DIR_GESTION, RAIZ, ErrorGestion, Trazabilidad, cargar_env, env,  # noqa: E402
                   salida)
import lectores  # noqa: E402

HERRAMIENTAS = ("xray-cloud", "xray-dc", "qtm4j", "aio")


def crear_adaptador(nombre, dry_run):
    proyecto = env("GESTION_PROYECTO")
    if nombre == "xray-cloud":
        from adaptadores.xray_cloud import XrayCloud as Clase
    elif nombre == "xray-dc":
        from adaptadores.xray_dc import XrayDC as Clase
    elif nombre == "qtm4j":
        from adaptadores.qtm4j import QTM4J as Clase
    elif nombre == "aio":
        from adaptadores.aio import AIO as Clase
    else:
        raise ErrorGestion(f"Herramienta desconocida '{nombre}'. Opciones: {', '.join(HERRAMIENTAS)}.")
    return Clase(proyecto, dry_run=dry_run)


def ruta_carpeta(valor):
    """Normaliza la ruta de carpeta a "/A/B". Git Bash convierte los argumentos que empiezan con "/"
    en rutas de Windows (C:/Program Files/Git/...): se detecta y se pide escribirla sin la barra inicial."""
    if re.match(r"^[A-Za-z]:[\\/]", valor or ""):
        raise ErrorGestion(f"La carpeta llegó como ruta de Windows ('{valor}'): Git Bash convierte las rutas que "
                           "empiezan con '/'. Escribila sin la barra inicial, ej. --carpeta \"HU-001 Registro/Manuales\".")
    partes = [p.strip() for p in re.split(r"[\\/]", valor or "") if p.strip()]
    if not partes:
        raise ErrorGestion("La ruta de la carpeta está vacía.")
    return "/" + "/".join(partes)


def lista(valor):
    return [v.strip() for v in (valor or "").split(",") if v.strip()]


def casos_desde_args(args, traza, adaptador):
    """Casos (dicts con key/id) a partir de --casos o de la trazabilidad (+ --ids)."""
    if args.casos:
        return [{"key": k, "id": None} for k in lista(args.casos)]
    if not traza:
        raise ErrorGestion("Indicá --casos o --traza.")
    ids = lista(args.ids) or list(traza.datos["casos"])
    faltan = [i for i in ids if i not in traza.datos["casos"]]
    if faltan:
        raise ErrorGestion(f"Estos casos no están subidos todavía (no figuran en {traza.ruta.name}): {', '.join(faltan)}.")
    return [{"cid": i, **traza.datos["casos"][i]} for i in ids]


def validar_keys(args):
    """Las keys de historia, ciclo y casos van a JQL y a rutas de la API: solo el formato de una key."""
    patron = re.compile(r"^[A-Za-z][A-Za-z0-9_]*-\d+$")
    for campo in ("historia", "ciclo"):
        valor = getattr(args, campo, None)
        if valor and not patron.match(valor):
            raise ErrorGestion(f"--{campo} tiene que ser una key como PROJ-12 (recibí {valor!r}).")
    for valor in lista(getattr(args, "casos", None)):
        if not patron.match(valor):
            raise ErrorGestion(f"--casos: {valor!r} no es una key válida (ej. PROJ-45).")


def cmd_carpeta(args, ad):
    ruta = ruta_carpeta(args.ruta)
    return {"ruta": ruta, "id": ad.crear_carpeta(ruta)}


def cmd_subir_casos(args, ad):
    args.carpeta = ruta_carpeta(args.carpeta)
    casos = lectores.leer_casos(args.origen, lista(args.ids))
    traza = Trazabilidad(args.traza or args.historia or Path(args.origen).stem, ad.nombre)
    traza.datos.update({"proyecto": ad.proyecto, "origen": str(args.origen)})
    if args.traza and re.match(r"^HU-\d+$", args.traza, re.I):
        traza.datos["hu"] = args.traza.upper()
    if args.historia:
        traza.datos["historia"] = args.historia
    carpeta_id = ad.crear_carpeta(args.carpeta)
    traza.datos["carpeta"] = {"ruta": args.carpeta, "id": carpeta_id}

    creados, existentes, sin_vinculo = [], [], []

    def vincular(cid, remoto):
        """Vincula el caso a la historia y deja constancia en la trazabilidad; si falla, queda
        marcado para reintentarlo en la próxima corrida (sin volver a crear el caso)."""
        if not args.historia:
            return
        try:
            ad.vincular_caso_historia(remoto, args.historia)
            traza.datos["casos"][cid]["vinculado"] = args.historia
        except ErrorGestion as e:
            traza.datos["casos"][cid]["vinculado"] = False
            sin_vinculo.append({"caso": cid, "key": remoto.get("key"), "error": str(e)[:300]})
        if not ad.dry_run:
            traza.guardar()

    for caso in casos:
        cid = caso["id"]
        if traza.key_de(cid):
            existentes.append({"caso": cid, "key": traza.key_de(cid)})
            if args.historia and traza.datos["casos"][cid].get("vinculado") is False:
                vincular(cid, traza.datos["casos"][cid])  # reintento del vínculo que falló antes
            continue
        remoto = ad.crear_caso(caso, carpeta_id, args.carpeta)
        # Se registra apenas se crea: si después falla algo, el reintento no lo duplica.
        traza.datos["casos"][cid] = {**remoto, "titulo": caso["titulo"]}
        if not ad.dry_run:
            traza.guardar()
        vincular(cid, remoto)
        creados.append({"caso": cid, "key": remoto.get("key"), "id": remoto.get("id")})
    if not ad.dry_run:
        traza.guardar()
    salida_cmd = {"carpeta": args.carpeta, "historia": args.historia, "creados": creados,
                  "ya_existian": existentes, "trazabilidad": str(traza.ruta)}
    if sin_vinculo:
        salida_cmd["sin_vincular"] = sin_vinculo
        salida_cmd["aviso"] = ("Estos casos se crearon pero no se pudieron vincular a la historia. "
                               "Volvé a correr el mismo comando: no se duplican y se reintenta el vínculo.")
    return salida_cmd


def cmd_vincular(args, ad):
    if args.ciclo:
        ad.vincular_ciclo_historia({"key": args.ciclo, "id": None}, args.historia)
        return {"ciclo": args.ciclo, "historia": args.historia}
    casos = [{"key": k, "id": None} for k in lista(args.casos)]
    for caso in casos:
        ad.vincular_caso_historia(caso, args.historia)
    return {"casos": [c["key"] for c in casos], "historia": args.historia}


def _traza_opcional(args, ad):
    nombre = args.traza or getattr(args, "historia", None)
    return Trazabilidad(nombre, ad.nombre) if nombre else None


def cmd_crear_ciclo(args, ad):
    traza = _traza_opcional(args, ad)
    ciclo = ad.crear_ciclo(args.nombre, args.descripcion or "",
                           (traza.datos.get("carpeta") or {}).get("ruta") if traza else None)
    if args.historia:
        ad.vincular_ciclo_historia(ciclo, args.historia)
    agregados = []
    if args.casos or (traza and traza.datos["casos"]):
        casos = casos_desde_args(args, traza, ad)
        ad.agregar_casos_ciclo(ciclo, casos)
        agregados = [c["key"] for c in casos]
    if traza and not ad.dry_run:
        traza.datos["ciclos"].append({**ciclo, "nombre": args.nombre,
                                      "fecha": dt.datetime.now().isoformat(timespec="minutes")})
        traza.guardar()
    return {"ciclo": ciclo, "historia": args.historia, "casos": agregados}


def cmd_agregar_a_ciclo(args, ad):
    traza = _traza_opcional(args, ad)
    casos = casos_desde_args(args, traza, ad)
    ad.agregar_casos_ciclo({"key": args.ciclo, "id": None}, casos)
    return {"ciclo": args.ciclo, "casos": [c["key"] for c in casos]}


def cmd_extraer_resultados(args, _ad):
    marca = dt.datetime.now().strftime("%Y%m%d-%H%M")
    destino = Path(args.salida or DIR_GESTION / f"resultados-{marca}.json")
    resultados = lectores.leer_resultados(args.reporte, destino.with_suffix("") )
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    resumen = {}
    for r in resultados:
        resumen[r["estado"]] = resumen.get(r["estado"], 0) + 1
    return {"resultados": str(destino), "escenarios": len(resultados), "por_estado": resumen,
            "detalle": [{"escenario": r["escenario"], "tags": r["tags"], "estado": r["estado"],
                         "evidencias": len(r["evidencias"])} for r in resultados]}


def _historia_de_traza(traza):
    """La historia (HU-XXX) a la que pertenece la trazabilidad, si se puede saber."""
    if not traza:
        return None
    if traza.datos.get("hu"):
        return str(traza.datos["hu"]).upper()
    m = re.match(r"^(HU-\d+)-", traza.ruta.stem, re.I)  # HU-001-xray-cloud.json
    return m.group(1).upper() if m else None


def _key_del_resultado(resultado, traza, patron_key):
    """El caso de un escenario se identifica por tag: una key directa (@PROJ-45) o un ID
    local (@CP-001) que se traduce con la trazabilidad. Los CP-XXX se repiten en cada
    historia, así que solo se traducen si el escenario lleva el @HU de esa trazabilidad.
    Devuelve (key, motivo_si_no_hay_key)."""
    for tag in resultado["tags"]:
        if re.match(patron_key, tag):
            return tag, None
    cps = [t for t in resultado["tags"] if re.match(r"^CP(-API)?-\d+$", t)]
    if not cps:
        return None, "sin tag @CP-XXX ni key del caso"
    if not traza:
        return None, "tiene @CP-XXX pero falta --traza para traducirlo"
    historia = _historia_de_traza(traza)
    hus = [t.upper() for t in resultado["tags"] if re.match(r"^HU-\d+$", t, re.I)]
    if historia and historia not in hus:
        return None, (f"es de otra historia ({', '.join(hus)})" if hus else
                      f"no tiene tag @{historia}: no se puede asegurar que sea de esa historia")
    for tag in cps:
        if traza.key_de(tag):
            return traza.key_de(tag), None
    return None, f"{', '.join(cps)} no figura en {traza.ruta.name} (¿se subió el caso?)"


def cmd_publicar_resultados(args, ad):
    traza = _traza_opcional(args, ad)
    resultados = json.loads(Path(args.resultados).read_text(encoding="utf-8"))
    patron_key = rf"^{re.escape(ad.proyecto)}-(TC-)?\d+$"
    ciclo = {"key": args.ciclo, "id": None}
    publicados, sin_caso, avisos = [], [], []
    for r in resultados:
        key, motivo = (r["caso"], None) if r.get("caso") else _key_del_resultado(r, traza, patron_key)
        if not key:
            sin_caso.append({"escenario": r["escenario"], "motivo": motivo})
            continue
        evid = [e["archivo"] for e in r["evidencias"]
                if e["tipo"] in ("captura", "gif") or (e["tipo"] == "video" and r["estado"] == "fallido" and not args.sin_video)]
        comentario = f"Ejecutado con k0lmena ({r['feature']} / {r['escenario']})."
        faltantes = [t for t in r.get("tags", []) if re.match(r"^FI-\d+$", t, re.I)]
        if "falta-info" in [t.lower() for t in r.get("tags", [])] or faltantes:
            comentario += (f"\n\nFALTA INFORMACIÓN ({', '.join(faltantes) or 'ver ficha de contexto'}): "
                           "el caso depende de datos que no están definidos; el resultado puede cambiar cuando se resuelvan.")
        if r["error"]:
            comentario += f"\n\nError:\n{r['error'][:3000]}"
        no_subidas = ad.registrar_resultado(ciclo, {"key": key, "id": None}, r["estado"], comentario, evid) or []
        avisos += [f"{key}: no se subió {Path(a).name} ({motivo})" for a, motivo in no_subidas]
        publicados.append({"caso": key, "escenario": r["escenario"], "estado": r["estado"],
                           "evidencias": len(evid) - len(no_subidas)})
    return {"ciclo": args.ciclo, "publicados": publicados,
            "sin_caso_asociado": sin_caso, "avisos": avisos}


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--herramienta")
    p.add_argument("--dry-run", action="store_true")
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("carpeta"); s.add_argument("--ruta", required=True)
    s = sub.add_parser("subir-casos")
    s.add_argument("--origen", required=True); s.add_argument("--carpeta", required=True)
    s.add_argument("--historia"); s.add_argument("--ids"); s.add_argument("--traza")
    s = sub.add_parser("vincular")
    s.add_argument("--historia", required=True); s.add_argument("--casos"); s.add_argument("--ciclo")
    s = sub.add_parser("crear-ciclo")
    s.add_argument("--nombre", required=True); s.add_argument("--descripcion")
    s.add_argument("--historia"); s.add_argument("--casos"); s.add_argument("--traza"); s.add_argument("--ids")
    s = sub.add_parser("agregar-a-ciclo")
    s.add_argument("--ciclo", required=True); s.add_argument("--casos"); s.add_argument("--traza"); s.add_argument("--ids")
    s = sub.add_parser("extraer-resultados")
    s.add_argument("--reporte", required=True); s.add_argument("--salida")
    s = sub.add_parser("publicar-resultados")
    s.add_argument("--ciclo", required=True); s.add_argument("--resultados", required=True)
    s.add_argument("--traza"); s.add_argument("--sin-video", action="store_true")

    args = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows no es UTF-8 por defecto
    cargar_env()
    try:
        if args.comando == "extraer-resultados":  # no necesita credenciales
            salida(cmd_extraer_resultados(args, None))
            return
        validar_keys(args)
        herramienta = args.herramienta or env("GESTION_HERRAMIENTA")
        adaptador = crear_adaptador(herramienta, args.dry_run)
        comando = globals()["cmd_" + args.comando.replace("-", "_")]
        salida(comando(args, adaptador))
    except ErrorGestion as e:
        salida({"error": str(e)})
        sys.exit(1)
    except Exception as e:  # red caída, JSON inválido en el .env, etc.: el agente lee un JSON, no un traceback
        salida({"error": f"{type(e).__name__}: {e}"})
        sys.exit(1)


if __name__ == "__main__":
    main()

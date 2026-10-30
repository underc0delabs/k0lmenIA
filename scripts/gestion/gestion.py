#!/usr/bin/env python3
"""Gestión de pruebas en Xray (Cloud o Server/DC) y k0lmenaTMT.

Mismos comandos para todas las herramientas; cuál se usa sale de GESTION_HERRAMIENTA
(.env de la raíz) o de --herramienta. Todo comando imprime un JSON con el resultado.

    python scripts/gestion/gestion.py [--herramienta X] [--dry-run] <comando> [opciones]

Comandos:
  carpeta              --ruta "/HU-001 Registro"
  subir-casos          --origen <casos.xlsx | escenarios.feature> --carpeta "/HU-001 Registro"
                       [--historia PROJ-12] [--ids CP-001,CP-002] [--traza HU-001] [--modulo "Registro"]
  sincronizar-casos    --origen <casos.xlsx | escenarios.feature> --traza HU-001 [--ids ...] [--modulo ...] [--forzar]
                       (actualiza en la herramienta los casos ya subidos que cambiaron en el origen)
  vincular             --historia PROJ-12 (--casos PROJ-45,PROJ-46 | --ciclo PROJ-60)
  crear-ciclo          --nombre "HU-001 Sprint 5" [--descripcion ...] [--historia PROJ-12]
                       [--casos PROJ-45,PROJ-46 | --traza HU-001 [--ids CP-001,...]]
  agregar-a-ciclo      --ciclo PROJ-60 (--casos PROJ-45,... | --traza HU-001 [--ids ...])
  extraer-resultados   --reporte herramientas/k0lmena/reports/web/cucumber-report.json
                       (o un JUnit XML de Cypress, Playwright, pytest, Maven…: un .xml o una carpeta con varios)
                       [--salida output/gestion/resultados-<fecha>.json]
  publicar-resultados  --ciclo PROJ-60 --resultados <resultados.json> [--traza HU-001]
                       [--sin-video]

Herramientas: xray-cloud | xray-dc | k0lmena-tmt
--traza <nombre>: archivo de trazabilidad output/gestion/<nombre>-<herramienta>.json
(qué CP-XXX es qué key). Por defecto, el valor de --historia.
--modulo: el módulo de la etiqueta modulo-<nombre>. Por defecto, el de la planilla (fila "Módulo:") o el nombre de
la Feature. Cada caso sube con las etiquetas estándar: historia, módulo, prioridad, smoke/regresion y las demás
(scripts/_etiquetas.py).
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _etiquetas as etiquetas  # noqa: E402

HERRAMIENTAS = ("xray-cloud", "xray-dc", "k0lmena-tmt")


def crear_adaptador(nombre, dry_run):
    proyecto = env("GESTION_PROYECTO")
    if nombre == "xray-cloud":
        from adaptadores.xray_cloud import XrayCloud as Clase
    elif nombre == "xray-dc":
        from adaptadores.xray_dc import XrayDC as Clase
    elif nombre == "k0lmena-tmt":
        from adaptadores.k0lmena_tmt import K0lmenaTMT as Clase
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
    historia = getattr(args, "historia", None)
    if historia and not patron.match(historia):
        raise ErrorGestion(f"--historia tiene que ser una key como PROJ-12 (recibí {historia!r}).")
    ciclo = getattr(args, "ciclo", None)
    if ciclo and not patron.match(ciclo):
        raise ErrorGestion(f"--ciclo tiene que ser una key como PROJ-12 (recibí {ciclo!r}).")
    for valor in lista(getattr(args, "casos", None)):
        if not patron.match(valor):
            raise ErrorGestion(f"--casos: {valor!r} no es una key válida (ej. PROJ-45).")


def cmd_carpeta(args, ad):
    ruta = ruta_carpeta(args.ruta)
    return {"ruta": ruta, "id": ad.crear_carpeta(ruta)}


def _leer_casos(args, historia=None):
    """Los casos del origen con sus etiquetas estándar: historia, módulo, prioridad, smoke/regresión y las demás
    (scripts/_etiquetas.py)."""
    casos = lectores.leer_casos(args.origen, lista(args.ids))
    hu = args.traza.upper() if args.traza and re.match(r"^HU-\d+$", args.traza, re.I) else None
    for caso in casos:
        caso["etiquetas"] = etiquetas.estandar(caso.get("etiquetas", []), caso.get("prioridad"),
                                               args.modulo or caso.get("modulo"), [hu, historia or args.historia])
    return casos


def firma(caso):
    """Huella de lo que se sube de un caso: si cambia, el caso cambió en el origen y hay que sincronizarlo."""
    import hashlib
    datos = {k: caso.get(k) for k in ("titulo", "descripcion", "precondiciones", "prioridad", "etiquetas", "tipo",
                                      "pasos", "gherkin")}
    datos["minutos"] = (caso.get("estimacion") or {}).get("minutos")
    return hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def cmd_sincronizar_casos(args, ad):
    """Pone al día en la herramienta los casos ya subidos que cambiaron en el origen (planilla o .feature): título,
    descripción, precondiciones, prioridad, etiquetas, tiempo y pasos o gherkin. Los que no cambiaron no se tocan."""
    traza = Trazabilidad(args.traza or args.historia or Path(args.origen).stem, ad.nombre)
    if not traza.datos["casos"]:
        raise ErrorGestion(f"{traza.ruta.name} no tiene casos subidos en {ad.nombre}: para crearlos, usá subir-casos.")
    historia = args.historia or traza.datos.get("historia")
    if hasattr(ad, "historia"):
        ad.historia = historia
    actualizados, sin_cambios, no_subidos, avisos = [], [], [], []
    for caso in _leer_casos(args, historia):
        cid = caso["id"]
        previo = traza.datos["casos"].get(cid)
        if not previo:
            no_subidos.append(cid)
            continue
        huella = firma(caso)
        if previo.get("firma") == huella and not args.forzar:
            sin_cambios.append(cid)
            continue
        avisos += ad.actualizar_caso(caso, previo, dict(previo)) or []
        previo.update({"titulo": caso["titulo"], "etiquetas": caso["etiquetas"], "firma": huella})
        if not ad.dry_run:
            traza.guardar()
        actualizados.append({"caso": cid, "key": previo.get("key")})
    salida_cmd = {"actualizados": actualizados, "sin_cambios": sin_cambios, "trazabilidad": str(traza.ruta)}
    if no_subidos:
        salida_cmd["no_subidos"] = no_subidos
        salida_cmd["aviso_no_subidos"] = "Estos casos todavía no están en la herramienta: subilos con subir-casos."
    if avisos:
        salida_cmd["avisos"] = avisos
    return salida_cmd


def cmd_subir_casos(args, ad):
    args.carpeta = ruta_carpeta(args.carpeta)
    casos = _leer_casos(args)
    traza = Trazabilidad(args.traza or args.historia or Path(args.origen).stem, ad.nombre)
    traza.datos.update({"proyecto": ad.proyecto, "origen": str(args.origen)})
    if args.traza and re.match(r"^HU-\d+$", args.traza, re.I):
        traza.datos["hu"] = args.traza.upper()
    if args.historia:
        traza.datos["historia"] = args.historia
    if hasattr(ad, "historia"):
        ad.historia = args.historia  # k0lmenaTMT: la historia va como etiqueta del caso (no se conecta a Jira)
    carpeta_id = ad.crear_carpeta(args.carpeta)
    traza.datos["carpeta"] = {"ruta": args.carpeta, "id": carpeta_id}

    creados, existentes, sin_vinculo, reetiquetados, cambiados = [], [], [], [], []

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
            previo = traza.datos["casos"][cid]
            if previo.get("firma") and previo["firma"] != firma(caso):
                cambiados.append(cid)
            if hasattr(ad, "actualizar_etiquetas") and previo.get("etiquetas") != caso["etiquetas"]:
                ad.actualizar_etiquetas(caso, previo)  # k0lmenaTMT: el caso ya subido toma las etiquetas al día
                previo["etiquetas"] = caso["etiquetas"]
                reetiquetados.append({"caso": cid, "key": previo.get("key"), "etiquetas": caso["etiquetas"]})
                if not ad.dry_run:
                    traza.guardar()
            continue
        remoto = ad.crear_caso(caso, carpeta_id, args.carpeta)
        # Se registra apenas se crea: si después falla algo, el reintento no lo duplica.
        traza.datos["casos"][cid] = {**remoto, "titulo": caso["titulo"], "etiquetas": caso["etiquetas"],
                                     "firma": firma(caso)}
        if not ad.dry_run:
            traza.guardar()
        vincular(cid, remoto)
        creados.append({"caso": cid, "key": remoto.get("key"), "id": remoto.get("id")})
    if not ad.dry_run:
        traza.guardar()
    salida_cmd = {"carpeta": args.carpeta, "historia": args.historia, "creados": creados,
                  "ya_existian": existentes, "trazabilidad": str(traza.ruta)}
    if reetiquetados:
        salida_cmd["etiquetas_actualizadas"] = reetiquetados
    if cambiados:
        salida_cmd["cambiaron_en_el_origen"] = cambiados
        salida_cmd["aviso_cambios"] = ("Estos casos ya estaban subidos y cambiaron en el origen: para actualizarlos en la "
                                       "herramienta, corré sincronizar-casos con el mismo --origen y --traza.")
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
    if hasattr(ad, "historia"):
        ad.historia = args.historia  # k0lmenaTMT: va en la descripción del ciclo
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
    reporte = Path(args.reporte)
    es_junit = reporte.is_dir() or reporte.suffix.lower() == ".xml"
    leer = lectores.leer_resultados_junit if es_junit else lectores.leer_resultados
    resultados = leer(args.reporte, destino.with_suffix(""))
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
    patron_key = getattr(ad, "patron_key", None) or rf"^{re.escape(ad.proyecto)}-(TC-|T)?\d+$"
    ciclo = {"key": args.ciclo, "id": None}
    publicados, sin_caso, avisos = [], [], []
    for r in resultados:
        key, motivo = (r["caso"], None) if r.get("caso") else _key_del_resultado(r, traza, patron_key)
        if not key:
            sin_caso.append({"escenario": r["escenario"], "motivo": motivo})
            continue
        evid = [e["archivo"] for e in r["evidencias"]
                if e["tipo"] in ("captura", "gif", "archivo") or (e["tipo"] == "video" and r["estado"] == "fallido" and not args.sin_video)]
        comentario = f"Ejecutado con {r.get('origen', 'k0lmena')} ({r['feature']} / {r['escenario']})."
        faltantes = [t for t in r.get("tags", []) if re.match(r"^FI-\d+$", t, re.I)]
        if "falta-info" in [t.lower() for t in r.get("tags", [])] or faltantes:
            comentario += (f"\n\nFALTA INFORMACIÓN ({', '.join(faltantes) or 'ver ficha de contexto'}): "
                           "el caso depende de datos que no están definidos; el resultado puede cambiar cuando se resuelvan.")
        if r["error"]:
            comentario += f"\n\nError:\n{r['error'][:3000]}"
        if getattr(ad, "acepta_duracion", False):  # k0lmenaTMT registra el tiempo real de ejecución
            no_subidas = ad.registrar_resultado(ciclo, {"key": key, "id": None}, r["estado"], comentario, evid,
                                                duracion_s=r.get("duracion_s")) or []
        else:
            no_subidas = ad.registrar_resultado(ciclo, {"key": key, "id": None}, r["estado"], comentario, evid) or []
        avisos += [f"{key}: no se subió {Path(a).name} ({motivo})" for a, motivo in no_subidas]
        publicados.append({"caso": key, "escenario": r["escenario"], "estado": r["estado"],
                           "evidencias": len(evid) - len(no_subidas)})
    salida_cmd = {"ciclo": args.ciclo, "publicados": publicados, "sin_caso_asociado": sin_caso, "avisos": avisos}
    if hasattr(ad, "al_publicar"):  # k0lmenaTMT: el ciclo queda como ejecutado
        try:
            salida_cmd["estado_ciclo"] = ad.al_publicar(ciclo, publicados)
        except ErrorGestion as e:
            avisos.append(f"no se pudo actualizar el estado del ciclo: {str(e)[:200]}")
    return salida_cmd


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--herramienta")
    p.add_argument("--dry-run", action="store_true")
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("carpeta"); s.add_argument("--ruta", required=True)
    s = sub.add_parser("subir-casos")
    s.add_argument("--origen", required=True); s.add_argument("--carpeta", required=True)
    s.add_argument("--historia"); s.add_argument("--ids"); s.add_argument("--traza"); s.add_argument("--modulo")
    s = sub.add_parser("vincular")
    s.add_argument("--historia", required=True); s.add_argument("--casos"); s.add_argument("--ciclo")
    s = sub.add_parser("sincronizar-casos")
    s.add_argument("--origen", required=True); s.add_argument("--traza"); s.add_argument("--historia")
    s.add_argument("--ids"); s.add_argument("--modulo"); s.add_argument("--forzar", action="store_true")
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

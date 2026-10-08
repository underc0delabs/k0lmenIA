"""Lectura de insumos locales, independiente de la herramienta de gestión.

- Casos manuales desde la planilla .xlsx de generar_casos.py.
- Escenarios BDD desde un .feature.
- Resultados de ejecución desde el cucumber-report.json de k0lmena (web, api o mobile),
  con sus evidencias (capturas embebidas y videos).
"""
import base64
import hashlib
import re
from pathlib import Path

from comun import ErrorGestion, necesitar, normalizar_estado

PRIORIDADES = {"crítica": "Crítica", "critica": "Crítica", "alta": "Alta", "media": "Media", "baja": "Baja"}


def _pasos_desde_texto(pasos, datos, resultado):
    """'1. Ir a...\\n2. Completar...' -> [{accion, datos, resultado}]. El resultado esperado del
    caso va en el último paso y los datos de prueba en el primero."""
    lineas = [re.sub(r"^\s*\d+[.)-]\s*", "", l).strip() for l in (pasos or "").splitlines()]
    lineas = [l for l in lineas if l]
    if not lineas:
        lineas = ["(sin pasos)"]
    salida = [{"accion": l, "datos": "", "resultado": ""} for l in lineas]
    salida[0]["datos"] = datos or ""
    salida[-1]["resultado"] = resultado or ""
    return salida


def leer_xlsx(ruta):
    """Lee la planilla de casos (formato de scripts/generar_casos.py)."""
    necesitar("openpyxl")
    from openpyxl import load_workbook

    ws = load_workbook(ruta, data_only=True).active
    encabezados, fila_enc = None, None
    for fila in ws.iter_rows(min_row=1, max_row=15):
        valores = [str(c.value or "").strip() for c in fila]
        if "ID #" in valores and "Título" in valores:
            encabezados, fila_enc = valores, fila[0].row
            break
    if not encabezados:
        raise ErrorGestion(f"{ruta}: no encuentro la fila de encabezados (ID #, Título, ...).")
    col = {nombre: i for i, nombre in enumerate(encabezados)}

    def val(fila, nombre):
        i = col.get(nombre)
        return str(fila[i] or "").strip() if i is not None and i < len(fila) else ""

    casos = []
    for fila in ws.iter_rows(min_row=fila_enc + 1, values_only=True):
        cid = val(fila, "ID #")
        if not re.match(r"^CP(-API)?-\d+", cid):
            continue
        casos.append({
            "id": cid,
            "titulo": val(fila, "Título"),
            "descripcion": val(fila, "Descripción"),
            "precondiciones": val(fila, "Precondiciones"),
            "prioridad": PRIORIDADES.get(val(fila, "Prioridad").lower(), "Media"),
            "etiquetas": [e.lstrip("@") for e in re.split(r"[\s,]+", val(fila, "#Etiquetas")) if e],
            "tipo": "manual",
            "pasos": _pasos_desde_texto(val(fila, "Pasos"), val(fila, "Datos de Prueba"),
                                         val(fila, "Resultado Esperado") or val(fila, "Resultado esperado")),
        })
    if not casos:
        raise ErrorGestion(f"{ruta}: no encontré casos con ID CP-XXX.")
    return casos


def leer_feature(ruta):
    """Escenarios de un .feature como casos de tipo 'cucumber' (gherkin completo del escenario).
    El ID del caso sale del tag @CP-XXX del escenario; si no tiene, se usa el título."""
    texto = Path(ruta).read_text(encoding="utf-8")
    lineas = texto.splitlines()
    background, casos, tags_feature = [], [], []
    i = 0
    tags_pend = []
    while i < len(lineas):
        l = lineas[i].strip()
        if l.startswith("@"):
            tags_pend += [t.lstrip("@") for t in l.split()]
        elif l.startswith("Feature:"):
            tags_feature, tags_pend = tags_pend, []
        elif l.startswith("Background:"):
            j = i + 1
            while j < len(lineas) and not re.match(r"^\s*(@|Scenario|Rule:)", lineas[j]):
                background.append(lineas[j].rstrip())
                j += 1
            i = j
            continue
        elif re.match(r"^(Scenario|Scenario Outline|Scenario Template|Example):", l):
            titulo = l.split(":", 1)[1].strip()
            cuerpo = [l]
            j = i + 1
            while j < len(lineas) and not re.match(r"^\s*(@|Scenario|Scenario Outline|Rule:)", lineas[j]):
                cuerpo.append(lineas[j].rstrip())
                j += 1
            tags = tags_pend
            cid = next((t for t in tags if re.match(r"^CP(-API)?-\d+$", t)), titulo)
            gherkin = "\n".join(([ "Background:"] + [b for b in background if b.strip()] + [""] if background else []) + cuerpo)
            casos.append({
                "id": cid, "titulo": titulo, "descripcion": "", "precondiciones": "",
                "prioridad": "Alta" if "Smoke" in tags else "Media",
                "etiquetas": list(dict.fromkeys(t for t in tags_feature + tags if not re.match(r"^CP(-API)?-\d+$", t))),
                "tipo": "cucumber", "gherkin": gherkin.strip(), "pasos": [],
            })
            tags_pend = []
            i = j
            continue
        i += 1
    if not casos:
        raise ErrorGestion(f"{ruta}: no encontré escenarios.")
    return casos


def leer_casos(origen, ids=None):
    sufijo = Path(origen).suffix.lower()
    if sufijo == ".xlsx":
        casos = leer_xlsx(origen)
    elif sufijo == ".feature":
        casos = leer_feature(origen)
    else:
        raise ErrorGestion("El origen de los casos tiene que ser un .xlsx (manuales) o un .feature (BDD).")
    if ids:
        pedidos = set(ids)
        casos = [c for c in casos if c["id"] in pedidos]
        faltan = pedidos - {c["id"] for c in casos}
        if faltan:
            raise ErrorGestion(f"No encontré en {origen} los casos: {', '.join(sorted(faltan))}.")
    return casos


def leer_resultados(reporte_json, dir_evidencias):
    """cucumber-report.json de k0lmena -> lista de resultados con evidencias en archivos.

    Las capturas embebidas (image/png) se escriben en dir_evidencias. El video se toma del
    adjunto HTML (<video src="videos/...">) que deja el hook. Con reintentos queda el último intento.
    """
    import json

    reporte = Path(reporte_json)
    if not reporte.exists():
        raise ErrorGestion(f"No existe {reporte}. Corré primero npm test en herramientas/k0lmena.")
    base_reporte = reporte.parent
    dir_evidencias = Path(dir_evidencias)
    dir_evidencias.mkdir(parents=True, exist_ok=True)
    features = json.loads(reporte.read_text(encoding="utf-8"))

    por_escenario = {}
    for feature in features:
        for esc in feature.get("elements", []):
            if esc.get("type") == "background":
                continue
            tags = list(dict.fromkeys(t["name"].lstrip("@") for t in esc.get("tags", [])))
            estados, error, capturas, videos, gifs, textos = [], "", [], [], [], []
            for paso in esc.get("steps", []):
                res = paso.get("result", {})
                estados.append(res.get("status", "undefined"))
                if res.get("status") == "failed" and not error:
                    error = (res.get("error_message") or "").strip()
                for emb in paso.get("embeddings", []):
                    mime = emb.get("mime_type", "")
                    if mime == "image/png":
                        capturas.append(base64.b64decode(emb["data"]))
                    elif mime == "text/html":
                        html = base64.b64decode(emb["data"]).decode("utf-8", "replace")
                        videos += re.findall(r'<video[^>]*src="([^"]+)"', html)
                        gifs += re.findall(r'<img[^>]*src="([^"]+[.]gif)"', html)
                    elif mime == "text/plain":
                        textos.append(base64.b64decode(emb["data"]).decode("utf-8", "replace"))
            if "failed" in estados or "ambiguous" in estados:
                estado = "fallido"
            elif all(e == "passed" for e in estados):
                estado = "aprobado"
            else:
                estado = "pendiente"
            clave = f'{feature.get("uri", "")}:{esc.get("line")}:{esc.get("name")}'
            por_escenario[clave] = {
                "escenario": esc.get("name", ""), "feature": feature.get("name", ""),
                "tags": tags, "estado": normalizar_estado(estado), "error": error,
                "_capturas": capturas, "_videos": videos, "_gifs": gifs, "textos": textos,
            }

    resultados = []
    for r in por_escenario.values():
        nombre = re.sub(r"[^\w.-]+", "_", r["escenario"])[:80]
        evidencias = []
        for n, png in enumerate(r.pop("_capturas")):
            archivo = dir_evidencias / f"{nombre}-{hashlib.md5(png).hexdigest()[:8]}-{n}.png"
            archivo.write_bytes(png)
            evidencias.append({"tipo": "captura", "archivo": str(archivo)})
        for tipo, clave in (("video", "_videos"), ("gif", "_gifs")):
            for src in r.pop(clave):
                # web: "videos/x.webm" (relativo a reports/web) · mobile: "../videos/x.mp4" (relativo a html/features)
                limpio = src.replace("../", "")
                for candidato in (base_reporte / limpio, base_reporte / "html" / limpio):
                    if candidato.exists():
                        evidencias.append({"tipo": tipo, "archivo": str(candidato.resolve())})
                        break
        r["evidencias"] = evidencias
        resultados.append(r)
    return resultados

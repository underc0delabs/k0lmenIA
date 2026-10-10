#!/usr/bin/env python3
"""
Junta los resultados de una historia (o de toda la ronda) desde todas las fuentes de k0lmenIA,
para que el informe de cierre no sume nada a mano.

Uso:
    python scripts/recolectar_resultados.py [--historia HU-001] [--salida datos.json]

Fuentes que lee (las que existan):
  - Ejecuciones en vivo (ejecutor-e2e / ejecutor-api): output/ejecuciones/_resultados-*.json
  - Suites de k0lmena (npm test): herramientas/k0lmena/reports/{web,api,mobile}/cucumber-report.json
    (solo los escenarios con el tag @HU de la historia, si se indica)
  - Bugs: output/reportes-bug/BUG-*.md (severidad, estado e historia)
  - Performance: output/performance/<HU>/informe-performance-*.json (+ resúmenes de corridas)
  - Seguridad: output/seguridad/<HU>/<fecha>/zap.json (+ analisis.json)

Un mismo caso ejecutado varias veces cuenta una sola vez: vale su resultado más reciente.
Estados: Aprobado | Fallido | Bloqueado (pendiente, salteado o sin definir = Bloqueado).
Imprime y guarda un JSON con totales, detalle por caso, bugs y extras; generar_informe_cierre.py
lo toma con el campo "datos" del JSON del informe.
"""
import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
K0 = RAIZ / "herramientas" / "k0lmena" / "reports"
SEVERIDADES = ["Crítica", "Alta", "Media", "Baja"]
ABIERTOS = {"abierto", "en curso", "reabierto", "sin estado"}


def _estado(valor):
    v = (valor or "").strip().lower()
    if v in ("aprobado", "passed", "pasó", "paso", "ok"):
        return "Aprobado"
    if v in ("fallido", "failed", "ambiguous", "falló", "fallo"):
        return "Fallido"
    return "Bloqueado"


def de_ejecuciones(historia):
    salida = []
    for archivo in sorted(glob.glob(str(RAIZ / "output" / "ejecuciones" / "_resultados-*.json"))):
        try:
            datos = json.loads(Path(archivo).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if historia and (datos.get("historia") or "").upper() != historia:
            continue
        momento = os.path.getmtime(archivo)
        for c in datos.get("casos") or []:
            salida.append({"id": c.get("id") or c.get("titulo"), "titulo": c.get("titulo", ""),
                           "estado": _estado(c.get("estado")), "fuente": f"en vivo · {Path(archivo).name}",
                           "momento": momento, "falta_info": c.get("falta_info") or []})
    return salida


def de_cucumber(historia):
    salida = []
    for suite in ("web", "api", "mobile"):
        archivo = K0 / suite / "cucumber-report.json"
        if not archivo.exists():
            continue
        try:
            features = json.loads(archivo.read_text(encoding="utf-8") or "[]")
        except ValueError:
            continue
        momento = os.path.getmtime(archivo)
        for feature in features:
            for esc in feature.get("elements", []):
                if esc.get("type") == "background":
                    continue
                tags = [t["name"].lstrip("@") for t in esc.get("tags", [])]
                tags += [t["name"].lstrip("@") for t in feature.get("tags", [])]
                if historia and historia not in {t.upper() for t in tags}:
                    continue
                estados = [(p.get("result") or {}).get("status", "undefined") for p in esc.get("steps", [])]
                if any(e in ("failed", "ambiguous") for e in estados):
                    estado = "Fallido"
                elif estados and all(e == "passed" for e in estados):
                    estado = "Aprobado"
                else:
                    estado = "Bloqueado"
                cp = next((t for t in tags if re.match(r"^CP(-API)?-\d+$", t)), None)
                salida.append({"id": cp or esc.get("name"), "titulo": esc.get("name", ""), "estado": estado,
                               "fuente": f"npm test · {suite}", "momento": momento,
                               "falta_info": [t for t in tags if re.match(r"^FI-\d+$", t, re.I)]})
    return salida


def _campo(texto, nombre):
    m = re.search(rf"\*\*{nombre}[^*]*:\*\*\s*(.+)", texto)
    return re.sub(r"[`*]", "", m.group(1)).strip() if m else ""


def de_bugs(historia):
    bugs = []
    for archivo in sorted(glob.glob(str(RAIZ / "output" / "reportes-bug" / "BUG-*.md"))):
        texto = Path(archivo).read_text(encoding="utf-8")
        hu = _campo(texto, "Historia").upper()
        if historia and historia not in hu:
            continue
        sev_txt = _campo(texto, "Criticidad / Severidad") or _campo(texto, "Severidad")
        severidad = next((s for s in SEVERIDADES if sev_txt.lower().startswith(s.lower())), "")
        estado = _campo(texto, "Estado").split("—")[0].split("(")[0].strip() or "Sin estado"
        bugs.append({"id": _campo(texto, "ID").split()[0] if _campo(texto, "ID") else Path(archivo).stem,
                     "titulo": _campo(texto, "Título"), "severidad": severidad, "estado": estado,
                     "historia": hu or "—"})
    return bugs


def de_performance(historia):
    patron = RAIZ / "output" / "performance" / (historia or "*") / "informe-performance-*.json"
    informes = []
    for archivo in sorted(glob.glob(str(patron))):
        try:
            datos = json.loads(Path(archivo).read_text(encoding="utf-8"))
        except ValueError:
            continue
        informes.append({"informe": os.path.relpath(archivo, RAIZ), "veredicto": datos.get("veredicto", "—"),
                         "capacidad": datos.get("capacidad", ""), "corridas": len(datos.get("corridas") or [])})
    return informes


def de_seguridad(historia):
    escaneos = []
    for archivo in sorted(glob.glob(str(RAIZ / "output" / "seguridad" / (historia or "*") / "*" / "zap.json"))):
        try:
            zap = json.loads(Path(archivo).read_text(encoding="utf-8"))
        except ValueError:
            continue
        analisis = Path(archivo).with_name("analisis.json")
        falsos = set()
        if analisis.exists():
            try:
                falsos = {str(f.get("pluginid")) for f in json.loads(analisis.read_text(encoding="utf-8")).get("falsos_positivos") or []}
            except ValueError:
                pass
        cuenta = {"Alto": 0, "Medio": 0, "Bajo": 0, "Informativo": 0}
        for sitio in zap.get("site") or []:
            for a in sitio.get("alerts") or []:
                if str(a.get("pluginid")) in falsos:
                    continue
                cuenta[{3: "Alto", 2: "Medio", 1: "Bajo"}.get(int(a.get("riskcode", 0) or 0), "Informativo")] += 1
        escaneos.append({"escaneo": os.path.relpath(Path(archivo).parent, RAIZ), "hallazgos": cuenta})
    return escaneos


def recolectar(historia=None):
    historia = historia.upper() if historia else None
    ejecutados = de_ejecuciones(historia) + de_cucumber(historia)
    ultimo = {}
    for r in sorted(ejecutados, key=lambda r: r["momento"]):
        ultimo[r["id"]] = r  # el más reciente pisa al anterior
    casos = sorted(ultimo.values(), key=lambda r: str(r["id"]))
    totales = {"aprobado": 0, "fallido": 0, "bloqueado": 0}
    for c in casos:
        totales[c["estado"].lower()] += 1
        c.pop("momento", None)
    bugs = de_bugs(historia)
    por_sev = {s: sum(1 for b in bugs if b["severidad"] == s) for s in SEVERIDADES}
    abiertos = [b for b in bugs if b["estado"].lower() in ABIERTOS and b["severidad"] in ("Crítica", "Alta")]
    return {
        "historia": historia or "toda la ronda",
        "resultados": totales,
        "fuentes": sorted({c["fuente"] for c in casos}),
        "casos": casos,
        "bugs": {"por_severidad": por_sev, "total": len(bugs),
                 "abiertos": sum(1 for b in bugs if b["estado"].lower() in ABIERTOS),
                 "criticos_abiertos": [{"id": b["id"], "titulo": b["titulo"], "severidad": b["severidad"],
                                        "estado": b["estado"]} for b in abiertos],
                 "sin_estado": [b["id"] for b in bugs if b["estado"] == "Sin estado"]},
        "performance": de_performance(historia),
        "seguridad": de_seguridad(historia),
    }


def main():
    ap = argparse.ArgumentParser(description="Junta los resultados de una historia para el informe de cierre")
    ap.add_argument("--historia", help="HU-XXX (si se omite, toma toda la ronda)")
    ap.add_argument("--salida", help="archivo JSON de salida (por defecto, solo se imprime)")
    a = ap.parse_args()
    if a.historia and not re.match(r"^HU-\d+$", a.historia, re.I):
        sys.exit("--historia tiene que ser un ID como HU-001")
    datos = recolectar(a.historia)
    texto = json.dumps(datos, ensure_ascii=False, indent=2)
    if a.salida:
        Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
        Path(a.salida).write_text(texto, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    t = datos["resultados"]
    print(f"{datos['historia']}: {sum(t.values())} casos · {t['aprobado']} aprobados · {t['fallido']} fallidos · "
          f"{t['bloqueado']} bloqueados · {datos['bugs']['total']} bugs ({datos['bugs']['abiertos']} abiertos) · "
          f"fuentes: {', '.join(datos['fuentes']) or 'ninguna'}")
    if a.salida:
        print(f"Datos: {a.salida}")
    else:
        print(texto)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Convierte casos de k0lmenIA (.xlsx manuales o .feature BDD) al formato que pide la
herramienta `testplan_test_case_write` del conector MCP azure-devops (ver CONECTORES.md).

Uso:
    python scripts/gestion/para_azure_devops.py <casos.xlsx|.feature> [--ids CP-001,CP-003]

Imprime un JSON con un elemento por caso: id (CP-XXX), title, priority (1 a 4, la escala de
Azure DevOps), steps ("1. acción|resultado esperado" por línea) y etiquetas (incluye los
FI-XX de falta información). Así el agente gestor-pruebas no arma los pasos a mano.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import ErrorGestion  # noqa: E402
from lectores import leer_casos  # noqa: E402

PRIORIDAD_ADO = {"Crítica": 1, "Alta": 2, "Media": 3, "Baja": 4}


def _limpio(texto):
    """Una sola línea y sin '|', que el server usa como separador de acción y resultado."""
    return re.sub(r"\s+", " ", str(texto or "").replace("|", "/")).strip()


def _pasos_manual(caso):
    pasos = []
    for p in caso["pasos"]:
        accion = _limpio(p["accion"])
        if p.get("datos"):
            accion += f" (datos: {_limpio(p['datos'])})"
        pasos.append((accion, _limpio(p.get("resultado"))))
    if caso.get("precondiciones"):
        pasos.insert(0, (f"Precondiciones: {_limpio(caso['precondiciones'])}", ""))
    return pasos


def _pasos_gherkin(caso):
    """Given/When/And son acciones; cada Then (y sus And/But) es el resultado esperado del
    último paso de acción. Se conserva la palabra clave de cada línea."""
    pasos, en_then = [], False
    for linea in caso["gherkin"].splitlines():
        l = linea.strip()
        m = re.match(r"^(Given|When|Then|And|But|\*)\s+(.*)$", l)
        if not m:
            continue
        palabra, texto = m.group(1), _limpio(l)
        if palabra == "Then" or (en_then and palabra in ("And", "But")):
            en_then = True
            if not pasos:
                pasos.append(("(sin pasos previos)", ""))
            accion, resultado = pasos[-1]
            pasos[-1] = (accion, f"{resultado}; {texto}" if resultado else texto)
        else:
            en_then = False
            pasos.append((texto, ""))
    return pasos


def convertir(caso):
    pasos = _pasos_gherkin(caso) if caso["tipo"] == "cucumber" else _pasos_manual(caso)
    # Un paso sin resultado esperado lleva "-": si queda vacío, el server completa uno
    # genérico en inglés ("Verify step completes successfully") que no sale del caso.
    lineas = [f"{i}. {accion}|{resultado or '-'}" for i, (accion, resultado) in enumerate(pasos, 1)]
    titulo = caso["titulo"] if caso["id"] == caso["titulo"] else f"{caso['id']} - {caso['titulo']}"
    return {
        "id": caso["id"],
        "title": titulo,
        "priority": PRIORIDAD_ADO.get(caso["prioridad"], 3),
        "steps": "\n".join(lineas),
        "etiquetas": caso["etiquetas"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("origen", help="Planilla .xlsx de casos manuales o archivo .feature")
    parser.add_argument("--ids", help="Solo estos casos, separados por coma (ej. CP-001,CP-003)")
    args = parser.parse_args()
    ids = [i.strip() for i in args.ids.split(",") if i.strip()] if args.ids else None
    try:
        casos = leer_casos(args.origen, ids)
    except ErrorGestion as e:
        sys.exit(f"[!] {e}")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps([convertir(c) for c in casos], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

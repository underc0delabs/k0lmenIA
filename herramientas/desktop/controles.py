#!/usr/bin/env python3
"""
Relevamiento de solo lectura del árbol de controles de una app de escritorio de Windows (pywinauto).

Uso (desde la raíz del repo, en Windows, con la app abierta):
    python herramientas/desktop/controles.py --titulo "Facturador.*"   [--salida output/desktop/arbol.json]
    python herramientas/desktop/controles.py --proceso 1234 --backend uia --prof 6

Qué hace (solo lectura):
- Se conecta a una app ya abierta por título (regex) o PID, con el backend de UI Automation (`uia`, el
  recomendado para WPF/UWP/WinForms modernos) o `win32` (Win32 clásico).
- Recorre el árbol de controles de la ventana principal (tipo, nombre, automation id, clase) hasta una
  profundidad dada: es el "DOM" de la app, insumo para que el mapper y el agente ubiquen los controles.
- Calcula un resumen (cantidad de controles, por tipo, cuántos sin nombre accesible).

No hace clics ni cambia nada. Para apps Electron, automatizá como web (Playwright); esto es para apps
nativas de Windows. Requisitos: Windows, `pip install pywinauto`.
"""
import argparse
import json
import sys
from pathlib import Path


def _conectar(titulo=None, proceso=None, backend="uia"):
    try:
        from pywinauto import Application
    except ImportError:
        raise RuntimeError("Falta pywinauto (solo Windows): instalalo con `pip install pywinauto`.")
    app = Application(backend=backend)
    try:
        if proceso:
            app.connect(process=int(proceso), timeout=10)
        elif titulo:
            app.connect(title_re=titulo, timeout=10)
        else:
            raise RuntimeError("Indicá a qué app conectarte con --titulo \"<regex>\" o --proceso <PID>.")
    except RuntimeError:
        raise
    except Exception as ex:
        raise RuntimeError(f"No se pudo conectar a la app: {ex}. ¿Está abierta? Probá con --proceso <PID> o el otro --backend.")
    return app


def _nodo(ctrl, prof, max_prof):
    info = ctrl.element_info
    def g(attr):
        try:
            return getattr(info, attr)
        except Exception:
            return None
    nodo = {"tipo": g("control_type") or g("class_name"), "nombre": g("name"),
            "automation_id": g("automation_id"), "clase": g("class_name")}
    hijos = []
    if prof < max_prof:
        try:
            for ch in ctrl.children():
                hijos.append(_nodo(ch, prof + 1, max_prof))
        except Exception:
            pass
    nodo["hijos"] = hijos
    return nodo


def arbol(titulo=None, proceso=None, backend="uia", max_prof=6):
    app = _conectar(titulo, proceso, backend)
    ventana = app.top_window()
    ventana.wait("exists", timeout=10)
    return _nodo(ventana.wrapper_object(), 0, max_prof)


def resumen_arbol(nodo):
    """Resumen testeable del árbol: total de controles, por tipo y cuántos sin nombre accesible."""
    total, por_tipo, sin_nombre = 0, {}, 0
    pila = [nodo] if nodo else []
    while pila:
        n = pila.pop()
        total += 1
        t = n.get("tipo") or "?"
        por_tipo[t] = por_tipo.get(t, 0) + 1
        if not (n.get("nombre") or "").strip():
            sin_nombre += 1
        pila.extend(n.get("hijos") or [])
    return {"controles": total, "por_tipo": dict(sorted(por_tipo.items(), key=lambda x: -x[1])), "sin_nombre": sin_nombre}


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Relevamiento de solo lectura del árbol de controles de una app de escritorio.")
    ap.add_argument("--titulo", default="", help="regex del título de la ventana")
    ap.add_argument("--proceso", default="", help="PID del proceso")
    ap.add_argument("--backend", default="uia", choices=["uia", "win32"])
    ap.add_argument("--prof", type=int, default=6, help="profundidad máxima del árbol")
    ap.add_argument("--salida", default="", help="ruta donde guardar el JSON (opcional)")
    args = ap.parse_args(argv)
    try:
        a = arbol(args.titulo or None, args.proceso or None, args.backend, args.prof)
    except RuntimeError as ex:
        print(f"[desktop] {ex}", file=sys.stderr)
        return 2
    datos = {"arbol": a, "resumen": resumen_arbol(a)}
    texto = json.dumps(datos, ensure_ascii=False, indent=2)
    if args.salida:
        p = Path(args.salida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        print(f"[desktop] Árbol en {p}", file=sys.stderr)
    print(texto)
    r = datos["resumen"]
    print(f"[desktop] {r['controles']} control(es), {r['sin_nombre']} sin nombre accesible.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

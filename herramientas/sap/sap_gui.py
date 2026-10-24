#!/usr/bin/env python3
"""
Relevamiento de solo lectura de una sesión de SAP GUI for Windows por la Scripting API (COM).

Uso (desde la raíz del repo, en Windows, con SAP GUI abierto e iniciado en un mandante de QA):
    python herramientas/sap/sap_gui.py [--salida output/sap/relevamiento.json]

Qué hace (solo lectura):
- Se conecta al SAP GUI que ya está abierto por la Scripting API (no abre ni cierra sesiones).
- Lista las conexiones y sesiones abiertas y, de cada una, el sistema (SID), el mandante, el usuario, el
  idioma, la transacción y el programa actuales, y métricas de la sesión (round trips, tiempo de respuesta).
- Sirve de smoke/relevamiento: confirma que el Scripting está habilitado y a qué sistema estás conectado.

No ejecuta transacciones ni cambia datos. La automatización de los flujos la arma el agente probador-sap.
Requisitos: Windows, SAP GUI for Windows, `pip install pywin32`, y el Scripting habilitado en el servidor
(RZ11 sapgui/user_scripting = TRUE) y en el cliente (Opciones → Accesibilidad y scripting → Scripting).
"""
import argparse
import json
import sys
from pathlib import Path


def _engine():
    """Devuelve el Scripting Engine de un SAP GUI abierto. Lanza RuntimeError con un mensaje claro si no se puede."""
    try:
        import win32com.client as win32
    except ImportError:
        raise RuntimeError("Falta pywin32 (solo Windows): instalalo con `pip install pywin32`.")
    try:
        sapgui = win32.GetObject("SAPGUI")
    except Exception:
        raise RuntimeError("No se encontró SAP GUI. Abrí SAP GUI for Windows e iniciá sesión en un mandante de QA antes de relevar.")
    try:
        engine = sapgui.GetScriptingEngine
    except Exception:
        raise RuntimeError("SAP GUI Scripting está deshabilitado. Habilitalo en el servidor (RZ11 sapgui/user_scripting = TRUE) "
                           "y en el cliente (Opciones → Accesibilidad y scripting → Scripting).")
    return engine


def info_sesion(session):
    """Datos de solo lectura de una sesión (el objeto Info del SAP GUI)."""
    i = session.Info
    def g(attr):
        try:
            return getattr(i, attr)
        except Exception:
            return None
    return {"sistema": g("SystemName"), "mandante": g("Client"), "usuario": g("User"), "idioma": g("Language"),
            "transaccion": g("Transaction"), "programa": g("Program"), "servidor": g("ApplicationServer"),
            "numero_sistema": g("SystemNumber"), "pantalla": g("ScreenNumber"), "codepage": g("Codepage"),
            "round_trips": g("RoundTrips"), "tiempo_respuesta_ms": g("ResponseTime")}


def relevar():
    """{"scripting": True, "conexiones": [{"descripcion", "sesiones": [info_sesion…]}]}."""
    engine = _engine()
    conexiones = []
    for ci in range(engine.Children.Count):
        conn = engine.Children(ci)
        sesiones = []
        for si in range(conn.Children.Count):
            try:
                sesiones.append(info_sesion(conn.Children(si)))
            except Exception as ex:
                sesiones.append({"error": str(ex)[:160]})
        try:
            descripcion = conn.Description
        except Exception:
            descripcion = f"conexión {ci}"
        conexiones.append({"descripcion": descripcion, "sesiones": sesiones})
    return {"scripting": True, "conexiones": conexiones}


def resumen_sesiones(conexiones):
    """Resumen testeable: conexiones, sesiones y sistemas distintos (SID/mandante)."""
    sesiones = [s for c in conexiones or [] for s in c.get("sesiones") or [] if "error" not in s]
    sistemas = sorted({f'{s.get("sistema")}/{s.get("mandante")}' for s in sesiones if s.get("sistema")})
    return {"conexiones": len(conexiones or []), "sesiones": len(sesiones), "sistemas": sistemas}


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Relevamiento de solo lectura de SAP GUI por la Scripting API.")
    ap.add_argument("--salida", default="", help="ruta donde guardar el JSON del relevamiento (opcional)")
    args = ap.parse_args(argv)
    try:
        datos = relevar()
    except RuntimeError as ex:
        print(f"[sap] {ex}", file=sys.stderr)
        return 2
    datos["resumen"] = resumen_sesiones(datos["conexiones"])
    texto = json.dumps(datos, ensure_ascii=False, indent=2)
    if args.salida:
        p = Path(args.salida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        print(f"[sap] Relevamiento en {p}", file=sys.stderr)
    print(texto)
    r = datos["resumen"]
    print(f"[sap] {r['conexiones']} conexión(es), {r['sesiones']} sesión(es): {', '.join(r['sistemas']) or '—'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

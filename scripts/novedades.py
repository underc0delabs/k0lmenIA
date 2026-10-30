#!/usr/bin/env python3
"""
Novedades de k0lmenIA: qué cambió desde la última vez que la persona lo usó, a partir del CHANGELOG.md.

Uso (desde la raíz del repo, o `k0lmenia novedades` con el plugin):
    python scripts/novedades.py                 las novedades desde la última vez que las viste (y las marca como vistas)
    python scripts/novedades.py --todas         todo el historial
    python scripts/novedades.py --ultimas 5     las 5 entradas más recientes
    python scripts/novedades.py --contexto      para el hook de inicio de sesión del plugin (ver abajo)

Cómo sabe qué es nuevo: guarda una marca con la entrada más reciente que ya viste —en ${CLAUDE_PLUGIN_DATA}/novedades.json
con el plugin, o en output/novedades/vistas.json con el repo clonado (output/ no se versiona)—. Las entradas que están
arriba de esa en el CHANGELOG son las nuevas.

--contexto (lo corre `k0lmenia preparar --contexto` al iniciar cada sesión con el plugin):
    - la primera vez después de instalar no muestra el historial entero: solo deja la marca;
    - después, si el plugin se actualizó y hay entradas nuevas, imprime un resumen corto (los títulos, como mucho
      ~8 líneas, y el link al CHANGELOG completo) para que Claude se lo cuente a la persona en su primer mensaje;
    - nunca falla el inicio de la sesión: ante cualquier error no imprime nada.

Además (salvo --contexto) deja el informe HTML en output/novedades/informe-novedades.html (es/ y en/), con el diseño de
k0lmena: cuántas novedades hay, una línea de tiempo y el detalle de cada entrada.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
CHANGELOG_URL = "https://github.com/underc0delabs/k0lmenIA/blob/main/CHANGELOG.md"
_TITULO = re.compile(r"^## (\d{4}-\d{2}-\d{2})(?: \((\d+)\))?\s*(?:[—–-]\s*(.*))?$")
MAX_LINEAS_CONTEXTO = 8


# ------------------------------------------------------------------ lectura del CHANGELOG (puro)
def entradas(texto):
    """CHANGELOG → [{"encabezado", "fecha", "numero", "titulo", "puntos": [...], "texto"}], de la más nueva a la más vieja."""
    salida, actual = [], None
    for linea in texto.splitlines():
        m = _TITULO.match(linea.strip())
        if m:
            actual = {"encabezado": linea.strip()[3:].strip(), "fecha": m.group(1), "numero": int(m.group(2)) if m.group(2) else None,
                      "titulo": (m.group(3) or "").strip(), "puntos": [], "lineas": []}
            salida.append(actual)
            continue
        if actual is None:
            continue
        actual["lineas"].append(linea)
        if re.match(r"^- ", linea):
            actual["puntos"].append(linea[2:].strip())
        elif re.match(r"^\s{2,}- ", linea) and actual["puntos"]:
            actual["puntos"][-1] += " · " + linea.strip()[2:]
    for e in salida:
        e["texto"] = "\n".join(e.pop("lineas")).strip()
    return salida


def nuevas(lista, marca):
    """Las entradas más nuevas que la marca ({"encabezado", "fecha"}). Sin marca: ninguna (la primera vez no se muestra todo)."""
    if not marca:
        return []
    for i, e in enumerate(lista):
        if e["encabezado"] == marca.get("encabezado"):
            return lista[:i]
    # El encabezado ya no está (se renombró): vale la fecha.
    return [e for e in lista if e["fecha"] > (marca.get("fecha") or "")]


def resumen_contexto(nuevas_entradas, maximo=MAX_LINEAS_CONTEXTO):
    """Texto corto para el contexto de la sesión (lo que Claude le cuenta a la persona)."""
    if not nuevas_entradas:
        return ""
    lineas = [f"k0lmenIA se actualizó: hay {len(nuevas_entradas)} novedad(es) desde la última vez que lo usó esta persona. "
              "Contáselas en 2 o 3 líneas al principio de tu primer mensaje (sin interrumpir lo que te pida), y ofrecé "
              "`k0lmenia novedades` para ver el detalle:"]
    for e in nuevas_entradas[:maximo]:
        lineas.append(f"- {e['fecha']}: {e['titulo'] or e['encabezado']}")
    if len(nuevas_entradas) > maximo:
        lineas.append(f"- … y {len(nuevas_entradas) - maximo} más.")
    lineas.append(f"Detalle completo: {CHANGELOG_URL}")
    return "\n".join(lineas) + "\n"


# ------------------------------------------------------------------ marca de lo visto
def archivo_marca():
    datos = os.environ.get("CLAUDE_PLUGIN_DATA")
    if datos:
        return Path(datos) / "novedades.json"
    return PROYECTO / "output" / "novedades" / "vistas.json"


def leer_marca(ruta):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def guardar_marca(ruta, lista):
    if not lista:
        return
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"encabezado": lista[0]["encabezado"], "fecha": lista[0]["fecha"]}, ensure_ascii=False), encoding="utf-8")


def changelog():
    for base in (RAIZ, Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or RAIZ)):
        p = base / "CHANGELOG.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


# ------------------------------------------------------------------ CLI
def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Novedades de k0lmenIA desde la última vez que las viste.")
    ap.add_argument("--todas", action="store_true", help="todo el historial")
    ap.add_argument("--ultimas", type=int, help="las N entradas más recientes")
    ap.add_argument("--contexto", action="store_true", help="resumen corto para el inicio de sesión del plugin")
    ap.add_argument("--marca", help="archivo de la marca (por defecto, el del plugin o output/novedades/vistas.json)")
    ap.add_argument("--salida", help="carpeta del informe (por defecto output/novedades)")
    ap.add_argument("--sin-html", action="store_true")
    a = ap.parse_args(argv)

    marca_ruta = Path(a.marca) if a.marca else archivo_marca()
    marca = leer_marca(marca_ruta)

    if a.contexto:
        try:  # todo adentro: un CHANGELOG ilegible no puede frenar el inicio de la sesión
            lista = entradas(changelog())
            texto = resumen_contexto(nuevas(lista, marca))
            guardar_marca(marca_ruta, lista)
            if texto:
                sys.stdout.write(texto)
        except Exception:  # el inicio de la sesión nunca falla por esto
            pass
        return 0

    lista = entradas(changelog())
    if a.todas:
        elegidas, alcance = lista, "todas"
    elif a.ultimas:
        elegidas, alcance = lista[:a.ultimas], f"ultimas-{a.ultimas}"
    elif marca:
        elegidas, alcance = nuevas(lista, marca), "desde-la-ultima-vez"
    else:
        elegidas, alcance = lista[:3], "ultimas-3"
    guardar_marca(marca_ruta, lista)

    if not elegidas:
        print("No hay novedades desde la última vez que las viste. Para ver el historial: novedades --todas")
    for e in elegidas:
        print(f"\n## {e['encabezado']}")
        for p in e["puntos"]:
            print(f"- {p}")
    if not a.sin_html:
        import generar_informe_novedades as gin
        carpeta = Path(a.salida) if a.salida else PROYECTO / "output" / "novedades"
        carpeta.mkdir(parents=True, exist_ok=True)
        datos = {"alcance": alcance, "marca_anterior": marca, "total_historial": len(lista), "entradas": elegidas,
                 "changelog_url": CHANGELOG_URL}
        (carpeta / "novedades.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nInforme: {gin.generar(carpeta / 'novedades.json', carpeta / 'informe-novedades.html')}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ / "scripts"))
    sys.exit(main())

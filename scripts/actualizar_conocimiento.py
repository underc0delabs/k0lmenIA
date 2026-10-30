#!/usr/bin/env python3
"""
Actualización de la base de conocimiento del proyecto (input/documentacion/), pensada para correr sola
(programada) en proyectos ágiles. Ver el skill base-conocimiento.

Uso (desde la raíz del repo):
    python scripts/actualizar_conocimiento.py                    (sin tokens: aplicación y código)
    python scripts/actualizar_conocimiento.py --con-agente       (+ historias con el documentador-proyecto)
    python scripts/actualizar_conocimiento.py --con-agente --presupuesto-usd 3
    python scripts/actualizar_conocimiento.py --programar lunes  (o diario; --hora 08:00)
    python scripts/actualizar_conocimiento.py --desprogramar

Qué hace, en este orden:
1. **Aplicación** (sin tokens): vuelve a correr el mapa funcional (`npm run mapa-funcional`, con la sesión de
   SESION si está) y lee sus *Cambios desde el recorrido anterior*. Se saltea si no hay APP_URL o con --sin-app.
2. **Código** (sin tokens): si hay REPO_RUTA_LOCAL y un commit documentado en input/documentacion/.estado.json,
   hace `git fetch` (no toca la copia de trabajo) y compara el commit documentado con la punta remota de la rama
   (`cambios_documentacion.py cambios --marcar`): documentos a rehacer y casos para revisar en `cambios.md`.
3. **Historias** (con --con-agente; gasta tokens): corre el documentador-proyecto en modo actualizar con
   `claude -p` (headless, con tope de gasto --presupuesto-usd). Lee SOLO las historias nuevas o modificadas
   desde la última revisión, ignora las que solo cambiaron de estado (huella del contenido) y rehace lo afectado.
4. **Resumen**: deja `output/conocimiento/actualizacion-<fecha>.md` y, si hay SLACK_WEBHOOK_URL o
   TEAMS_WEBHOOK_URL, avisa (scripts/avisar.py). Solo avisa si algo cambió (o siempre, con --avisar-siempre).

No publica nada en Jira ni en la herramienta de gestión; los casos para revisar se listan, no se tocan.
"""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
sys.path.insert(0, str(RAIZ / "scripts"))
from _env import leer_env  # noqa: E402

DOC = PROYECTO / "input" / "documentacion"
SALIDA = PROYECTO / "output" / "conocimiento"
TAREA = "k0lmenIA - actualizar conocimiento"
PEDIDO_AGENTE = (
    "Usá el agente documentador-proyecto en modo actualizar, solo para las HISTORIAS (requerimientos): listá las "
    "historias del alcance documentado cambiadas desde la última revisión (revision_historias de "
    "input/documentacion/.estado.json), con su contenido para la huella, corré "
    "`python scripts/cambios_documentacion.py historias --actual input/documentacion/_alcance.json --registrar-revision`, "
    "rehacé los dossiers de las cambiadas, documentá las nuevas y regenerá el índice. Es una corrida desatendida: "
    "no hay nadie para responder preguntas; lo que necesite confirmación, dejalo anotado en la respuesta. "
    "Solo lectura en todas las herramientas. Respondé con un resumen corto: nuevas, cambiadas, solo estado, "
    "casos para revisar."
)
HERRAMIENTAS_AGENTE = ["Read", "Write", "Edit", "Glob", "Grep", "Task", "Agent",
                       "Bash(python:*)", "Bash(python3:*)", "Bash(npm run:*)", "Bash(git log:*)", "Bash(git diff:*)",
                       "mcp__atlassian"]


def ahora():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ 1. aplicación
def actualizar_app(env, correr=subprocess.run):
    if not (env.get("APP_URL") or env.get("BASEURL")):
        return {"estado": "salteado", "motivo": "no hay APP_URL en el .env"}
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        return {"estado": "error", "motivo": "no está npm (Node.js)"}
    args = ["--max-paginas", "200", "--profundidad", "4"]
    # Como plugin, k0lmena vive en el proyecto: el mapa funcional va por el comando k0lmenia.
    cmd = (["node", str(RAIZ / "bin" / "k0lmenia"), "mapa-funcional", *args]
           if es_plugin() else [npm, "run", "--silent", "mapa-funcional", "--", *args])
    r = correr(cmd, cwd=PROYECTO if es_plugin() else RAIZ, capture_output=True, text=True, encoding="utf-8",
               errors="replace", timeout=3600)
    if r.returncode != 0:
        return {"estado": "error", "motivo": ((r.stderr or r.stdout) or "").strip().splitlines()[-1:] or ["falló"]}
    return resumen_mapa(DOC / "proyecto" / "mapa-funcional.json")


def resumen_mapa(ruta):
    try:
        mapa = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"estado": "error", "motivo": f"no se pudo leer {ruta}"}
    c = mapa.get("cambios")
    base = {"estado": "ok", "paginas": len(mapa.get("paginas") or []), "con_sesion": bool(mapa.get("con_sesion"))}
    if not c:
        return {**base, "cambios": None, "detalle": "primer recorrido (no hay con qué comparar)"}
    return {**base, "cambios": {"nuevas": c.get("nuevas", []), "quitadas": c.get("quitadas", []),
                                "con_cambios": [p["ruta"] for p in c.get("paginas", [])]}, "hay": bool(c.get("hay"))}


# ------------------------------------------------------------------ 2. código
def actualizar_codigo(env, correr=subprocess.run):
    ruta = env.get("REPO_RUTA_LOCAL")
    if not ruta or not Path(ruta).exists():
        return {"estado": "salteado", "motivo": "no hay REPO_RUTA_LOCAL (el código se revisa con el agente)"}
    try:
        estado = json.loads((DOC / ".estado.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"estado": "salteado", "motivo": "todavía no hay documentación registrada (.estado.json)"}
    repos = estado.get("repositorios") or {}
    if not repos:
        return {"estado": "salteado", "motivo": "no hay repositorio documentado en .estado.json"}
    nombre, info = next(iter(repos.items()))
    rama = info.get("rama") or env.get("REPO_RAMA") or ""
    f = correr(["git", "-C", ruta, "fetch", "--quiet", "origin"], capture_output=True, text=True)
    if f.returncode != 0:
        return {"estado": "error", "motivo": f"git fetch falló: {(f.stderr or '').strip()[:200]}"}
    hasta = f"origin/{rama}" if rama else "origin/HEAD"
    r = correr([sys.executable, str(RAIZ / "scripts" / "cambios_documentacion.py"), "cambios", "--repo", nombre,
                "--git", ruta, "--hasta", hasta, "--marcar"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return {"estado": "error", "motivo": (r.stderr or r.stdout).strip()[-200:]}
    datos = json.loads(r.stdout)
    return {"estado": "ok", "archivos": datos.get("cantidad_archivos", 0), "documentos": sorted(datos.get("documentos") or {}),
            "historias": datos.get("historias") or [], "casos": [c["archivo"] for c in datos.get("casos") or []],
            "hay": bool(datos.get("cantidad_archivos"))}


# ------------------------------------------------------------------ 3. historias (agente)
def comando_agente(ejecutable, presupuesto):
    return [ejecutable, "-p", PEDIDO_AGENTE, "--output-format", "json", "--permission-mode", "acceptEdits",
            "--allowedTools", ",".join(HERRAMIENTAS_AGENTE), "--max-budget-usd", f"{float(presupuesto):g}"]


def actualizar_historias(presupuesto, correr=subprocess.run):
    claude = shutil.which("claude")
    if not claude:
        return {"estado": "error", "motivo": "no encuentro el comando claude (Claude Code)"}
    try:
        r = correr(comando_agente(claude, presupuesto), cwd=PROYECTO, capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=5400)
    except subprocess.TimeoutExpired:
        return {"estado": "error", "motivo": "el agente tardó más de 90 minutos"}
    try:
        datos = json.loads(r.stdout or "{}")
    except ValueError:
        return {"estado": "error", "motivo": (r.stderr or r.stdout or "claude no devolvió JSON").strip()[-300:]}
    if datos.get("is_error") or r.returncode != 0:
        return {"estado": "error", "motivo": str(datos.get("result") or r.stderr)[-300:], "costo_usd": datos.get("total_cost_usd")}
    cambios = DOC / "cambios-historias.md"
    return {"estado": "ok", "resumen": (datos.get("result") or "").strip(), "costo_usd": datos.get("total_cost_usd"),
            "detalle": str(cambios.relative_to(PROYECTO)) if cambios.exists() else None,
            "hay": "0 nueva(s), 0 con cambios" not in (cambios.read_text(encoding="utf-8") if cambios.exists() else "")}


# ------------------------------------------------------------------ 4. resumen y aviso
def armar_resumen(app, codigo, historias):
    l = [f"# Actualización de la base de conocimiento — {ahora()}", ""]
    l += ["## Aplicación", ""]
    if app.get("estado") != "ok":
        l.append(f"- {app.get('estado')}: {app.get('motivo')}")
    elif not app.get("cambios"):
        l.append(f"- {app['paginas']} página(s) recorridas{' con sesión' if app.get('con_sesion') else ' (sin sesión)'}; {app.get('detalle', '')}")
    else:
        c = app["cambios"]
        l.append(f"- {app['paginas']} página(s){' con sesión' if app.get('con_sesion') else ' (sin sesión)'}: "
                 f"{len(c['nuevas'])} nueva(s), {len(c['quitadas'])} que ya no están, {len(c['con_cambios'])} con cambios.")
        for etiqueta, lista in (("Nuevas", c["nuevas"]), ("Ya no están", c["quitadas"]), ("Con cambios", c["con_cambios"])):
            if lista:
                l.append(f"  - {etiqueta}: {', '.join(lista[:20])}")
        if c["con_cambios"] or c["quitadas"]:
            l.append("  - Revisá los manuales y casos de esas pantallas (detalle en `input/documentacion/proyecto/mapa-funcional.md`).")
    l += ["", "## Código", ""]
    if codigo.get("estado") != "ok":
        l.append(f"- {codigo.get('estado')}: {codigo.get('motivo')}")
    else:
        l.append(f"- {codigo['archivos']} archivo(s) cambiaron; documentos a rehacer: {', '.join(codigo['documentos']) or 'ninguno'}; "
                 f"casos para revisar: {len(codigo['casos'])} (ver `input/documentacion/cambios.md`).")
    l += ["", "## Historias", ""]
    if not historias:
        l.append("- No se revisaron (corré con --con-agente; gasta tokens).")
    elif historias.get("estado") != "ok":
        l.append(f"- error: {historias.get('motivo')}")
    else:
        costo = f" Costo: US$ {historias['costo_usd']:.2f}." if historias.get("costo_usd") is not None else ""
        l.append(f"- {historias['resumen'] or 'Sin resumen.'}{costo}")
        if historias.get("detalle"):
            l.append(f"- Detalle: `{historias['detalle']}`.")
    l += ["", "Siguiente paso: los casos para revisar se pasan al `revisor-casos`.", ""]
    return "\n".join(l)


def hubo_cambios(app, codigo, historias):
    return any(x and x.get("hay") for x in (app, codigo, historias)) or any(
        x and x.get("estado") == "error" for x in (app, codigo, historias))


def avisar(texto_md, nivel, link):
    lineas = [l for l in texto_md.splitlines() if l.startswith("- ")][:8]
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "avisar.py"), "--titulo", "Base de conocimiento actualizada",
                    "--texto", "\n".join(lineas) or "Sin cambios.", "--nivel", nivel, "--link", link], cwd=RAIZ)


# ------------------------------------------------------------------ programación
def es_plugin():
    """¿Corre como plugin de Claude Code? (el comando k0lmenia avisa dónde está el código)."""
    return bool(os.environ.get("K0LMENIA_CODIGO")) and Path(os.environ["K0LMENIA_CODIGO"]).resolve() != PROYECTO


# Como plugin, la carpeta del código cambia con cada versión (la vieja se borra a los 14 días): la tarea programada
# no puede apuntar ahí. Este lanzador queda en el proyecto y busca la versión vigente del plugin en la caché.
LANZADOR = r"""// Lanzador estable de k0lmenia para tareas programadas (lo crea scripts/actualizar_conocimiento.py).
const fs = require('fs'), path = require('path'), os = require('os'), { spawnSync } = require('child_process');
const base = process.env.CLAUDE_CODE_PLUGIN_CACHE_DIR || path.join(os.homedir(), '.claude', 'plugins', 'cache');
const candidatos = [];
(function buscar(dir, nivel) {
  if (nivel > 4 || !fs.existsSync(dir)) return;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (!e.isDirectory()) continue;
    const d = path.join(dir, e.name), bin = path.join(d, 'bin', 'k0lmenia');
    if (fs.existsSync(bin) && fs.existsSync(path.join(d, '.claude-plugin', 'plugin.json')) && !fs.existsSync(path.join(d, '.orphaned_at'))) {
      candidatos.push({ bin, t: fs.statSync(d).mtimeMs });
    } else buscar(d, nivel + 1);
  }
})(base, 0);
if (!candidatos.length) { console.error('No encuentro el plugin k0lmenia instalado en ' + base); process.exit(1); }
const { bin } = candidatos.sort((a, b) => b.t - a.t)[0];
const r = spawnSync(process.execPath, [bin, ...process.argv.slice(2)], { stdio: 'inherit', cwd: path.resolve(__dirname, '..') });
process.exit(r.status === null ? 1 : r.status);
"""


def comando_programado(extra):
    """El comando que corre la tarea programada: npm run en el repo; el lanzador estable si es un plugin."""
    if es_plugin():
        lanzador = PROYECTO / ".k0lmenia" / "lanzador.js"
        lanzador.parent.mkdir(parents=True, exist_ok=True)
        lanzador.write_text(LANZADOR, encoding="utf-8")
        return PROYECTO, f'node "{lanzador}" actualizar-conocimiento{extra}'
    return RAIZ, f"npm run actualizar-conocimiento --{extra}"


def linea_programada(frecuencia, hora, con_agente):
    extra = " --con-agente" if con_agente else ""
    h, m = hora.split(":")
    carpeta, comando = comando_programado(extra)
    if sys.platform == "win32":
        sc = ["/SC", "DAILY"] if frecuencia == "diario" else ["/SC", "WEEKLY", "/D", "MON"]
        tr = f'cmd /c cd /d "{carpeta}" && {comando}'
        return ["schtasks", "/Create", "/F", "/TN", TAREA, *sc, "/ST", f"{int(h):02d}:{int(m):02d}", "/TR", tr]
    dias = "*" if frecuencia == "diario" else "1"
    return f"{int(m)} {int(h)} * * {dias} cd '{carpeta}' && {comando} >> output/conocimiento/cron.log 2>&1"


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Actualiza la base de conocimiento del proyecto (aplicación, código e historias).")
    ap.add_argument("--con-agente", action="store_true", help="revisar también las historias con el documentador (gasta tokens)")
    ap.add_argument("--presupuesto-usd", type=float, default=5.0, help="tope de gasto del agente por corrida (por defecto 5)")
    ap.add_argument("--sin-app", action="store_true", help="no volver a recorrer la aplicación")
    ap.add_argument("--avisar-siempre", action="store_true", help="avisar a Slack/Teams aunque no haya cambios")
    ap.add_argument("--programar", choices=["diario", "lunes"], help="dejarla programada en esta máquina")
    ap.add_argument("--hora", default="08:00", help="hora de la corrida programada (HH:MM)")
    ap.add_argument("--desprogramar", action="store_true")
    a = ap.parse_args(argv)

    if a.programar:
        linea = linea_programada(a.programar, a.hora, a.con_agente)
        if isinstance(linea, list):
            r = subprocess.run(linea, capture_output=True, text=True)
            print((r.stdout or r.stderr).strip())
            print(f"Programada: {a.programar} a las {a.hora} (Programador de tareas, \"{TAREA}\"). Corre con tu usuario: "
                  "la sesión de Claude Code y la PC tienen que estar disponibles a esa hora.")
            return r.returncode
        print("Agregá esta línea a tu crontab (crontab -e):\n" + linea)
        return 0
    if a.desprogramar:
        if sys.platform == "win32":
            r = subprocess.run(["schtasks", "/Delete", "/F", "/TN", TAREA], capture_output=True, text=True)
            print((r.stdout or r.stderr).strip())
            return r.returncode
        print("Sacá la línea de 'npm run actualizar-conocimiento' de tu crontab (crontab -e).")
        return 0

    env = leer_env()
    env.update({k: v for k, v in os.environ.items() if v})
    print("[conocimiento] 1/3 aplicación…", file=sys.stderr)
    app = {"estado": "salteado", "motivo": "--sin-app"} if a.sin_app else actualizar_app(env)
    print("[conocimiento] 2/3 código…", file=sys.stderr)
    codigo = actualizar_codigo(env)
    historias = None
    if a.con_agente:
        print(f"[conocimiento] 3/3 historias con el documentador (tope US$ {a.presupuesto_usd:g})…", file=sys.stderr)
        historias = actualizar_historias(a.presupuesto_usd)
    if DOC.exists():
        subprocess.run([sys.executable, str(RAIZ / "scripts" / "indice_documentacion.py")], capture_output=True)
    texto = armar_resumen(app, codigo, historias)
    SALIDA.mkdir(parents=True, exist_ok=True)
    archivo = SALIDA / f"actualizacion-{dt.datetime.now():%Y%m%d-%H%M}.md"
    archivo.write_text(texto, encoding="utf-8")
    print(texto)
    if a.avisar_siempre or hubo_cambios(app, codigo, historias):
        error = any(x and x.get("estado") == "error" for x in (app, codigo, historias))
        avisar(texto, "error" if error else "aviso", str(archivo))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Genera el Informe de permisos por rol en HTML (dashboard, modo oscuro) a partir de permisos.json
(npm run permisos) y, opcionalmente, del análisis del agente probador-permisos.

Uso:
    python scripts/generar_informe_permisos.py <permisos.json> <salida.html> [--analisis analisis.json]

Qué muestra: veredicto, indicadores (roles, rutas, visitas permitidas y negadas, diferencias con lo
esperado, hallazgos), la matriz rol × ruta (y rol × endpoint), las diferencias contra lo esperado, los
hallazgos, qué ve cada rol (menús y botones), la falta de información, las recomendaciones y la evolución
de las corridas.

El análisis (opcional) aporta:
{
  "veredicto": "...", "veredicto_tono": "bad", "resumen": "...",
  "esperado": {"admin": {"/admin": "permitido", "/reportes*": "permitido"}, "anonimo": {"/admin": "denegado"}},
  "fuente_esperado": "input/documentacion/proyecto/estados-y-permisos.md (src/auth/roles.ts:12)",
  "hallazgos": {"P-01": {"severidad": "Alta", "nota": "..."}},
  "descartados": [{"id": "P-04", "motivo": "..."}],
  "adicionales": [{"severidad": "Media", "tipo": "Botón", "titulo": "...", "detalle": "...", "correccion": "...", "rol": "operador", "url": "...",
                   "captura": "capturas/manual/pm-01.png"}],
  "falta_informacion": [{"id": "FI-01", "que_falta": "...", "pregunta": "..."}],   // "descripcion" vale como alias de que_falta
  "recomendaciones": [{"accion": "...", "motivo": "...", "prioridad": "Alta"}],
  "proximos_pasos": ["..."]
}
En "esperado", cada ruta es el path (con * al final para un prefijo) y el valor es "permitido" o
"denegado" (también vale "pide-login"). Lo que no está en "esperado" no se compara: es Falta información.
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import _historial
from _i18n import escribir_bilingue, idioma_actual, localizar  # noqa: E402,F401
from _estilos_reporte import (falta_informacion, avisar_analisis, e, page, meta, section, kpi_tiles, banner, doc_list, table, bar_chart, two_col,
                              nivel_badge, _pastilla, miniatura, CRITICO, AVISO, NEUTRO, OK, SERIES)
from generar_informe_exploratorio import CSS_EXTRA

SEV = ["Crítica", "Alta", "Media", "Baja"]
NEGADO = {"denegado", "pide-login"}
ACCESO = {"permitido": ("Permitido", OK, "✓"), "denegado": ("Denegado", NEUTRO, "⛔"), "pide-login": ("Pide login", NEUTRO, "🔒"),
          "no-encontrada": ("No existe", AVISO, "?"), "error": ("Error", CRITICO, "✕")}

# Tipo para el historial de corridas (se registra acá para no tocar _historial.py).
_historial.TIPOS.setdefault("permisos", {
    "archivo": "permisos.json", "items": lambda d: d.get("hallazgos") or [],
    "clave": lambda h: f'{h.get("tipo")}|{h.get("rol")}|{h.get("url")}', "titulo": lambda h: f'[{h.get("rol")}] {h.get("titulo")}',
    "metricas": [("Hallazgos", _historial._r("hallazgos"), ""), ("Críticos", _historial._r("por_severidad", "Crítica"), ""),
                 ("Visitas permitidas", _historial._r("permitidas"), ""), ("Rutas", _historial._r("rutas"), "")]})

CSS_PE = """
<style>
.matriz td,.matriz th{text-align:center;white-space:nowrap}
.matriz td:first-child,.matriz th:first-child{text-align:left;white-space:normal}
.rol h3{font-size:15px;color:var(--ink);margin:0 0 8px}
.rol{border-top:1px solid var(--border-soft);padding:16px 24px}
.rol:first-child{border-top:0}
.chips span{display:inline-block;margin:2px 4px 2px 0;padding:2px 8px;border-radius:999px;background:var(--bg);border:1px solid var(--border);font-size:12px}
.descartado{opacity:.55}
</style>
"""


def ruta_de(url):
    p = urlparse(url or "")
    return (p.path or "/") + (f"?{p.query}" if p.query else "") if p.scheme else (url or "")


def coincide(patron, url):
    r = ruta_de(url)
    patron = ruta_de(patron) if patron.startswith("http") else patron
    return r.startswith(patron[:-1]) if patron.endswith("*") else r.rstrip("/") == patron.rstrip("/") or (r == "/" and patron == "/")


def esperado_para(esperado, rol, url):
    """Lo esperado para un rol y una ruta (el patrón más largo que coincide), o None."""
    reglas = (esperado or {}).get(rol) or {}
    cand = sorted((p for p in reglas if coincide(p, url)), key=len, reverse=True)
    return reglas[cand[0]] if cand else None


def diferencias(datos, esperado):
    """Hallazgos E-XX: donde la matriz no coincide con lo esperado."""
    out = []
    for c in datos.get("matriz") or []:
        esp = esperado_para(esperado, c["rol"], c["url"])
        if not esp or c.get("acceso") in ("error", "no-encontrada"):
            continue
        real = c.get("acceso")
        en = idioma_actual() == "en"  # el texto del hallazgo lo arma el script: va en el idioma del informe
        if esp == "permitido" and real in NEGADO:
            if en:
                titulo = f'The "{c["rol"]}" role cannot open something it should'
                detalle = f'{ruta_de(c["url"])}: expected allowed, but it {"asks for login" if real == "pide-login" else "denies access"}.'
            else:
                titulo = f'El rol "{c["rol"]}" no puede entrar a algo que debería'
                detalle = f'{ruta_de(c["url"])}: se esperaba permitido y {"pide login" if real == "pide-login" else "niega el acceso"}.'
            out.append({"severidad": "Alta", "tipo": "Distinto de lo esperado", "rol": c["rol"], "url": c["url"],
                        "titulo": titulo, "detalle": detalle})
        elif esp in NEGADO and real == "permitido":
            if en:
                esperado_en = {"denegado": "denied", "pide-login": "login required"}.get(esp, esp)
                titulo = f'The "{c["rol"]}" role opens something it should not'
                detalle = f'{ruta_de(c["url"])}: expected {esperado_en}, but it opens (status {c.get("status")}).'
            else:
                titulo = f'El rol "{c["rol"]}" entra a algo que no debería'
                detalle = f'{ruta_de(c["url"])}: se esperaba {esp} y se abre (status {c.get("status")}).'
            out.append({"severidad": "Crítica", "tipo": "Distinto de lo esperado", "rol": c["rol"], "url": c["url"],
                        "titulo": titulo, "detalle": detalle})
    out.sort(key=lambda h: SEV.index(h["severidad"]))
    for i, h in enumerate(out, 1):
        h["id"] = f"E-{i:02d}"
    return out


def acceso_pill(acc):
    t, color, ic = ACCESO.get(acc or "", (acc or "—", NEUTRO, "●"))
    return _pastilla(t, color, ic)


def build_html(datos, analisis, hist_html=""):
    ajustes = analisis.get("hallazgos") or {}
    desc = {str(d.get("id")): d.get("motivo") for d in analisis.get("descartados") or []}
    esperado = analisis.get("esperado") or {}
    difs = diferencias(datos, esperado)
    extra = [dict(h, id=h.get("id") or f"M-{i:02d}") for i, h in enumerate(analisis.get("adicionales") or [], 1)]
    hallazgos = []
    for h in (datos.get("hallazgos") or []) + difs + extra:
        h = dict(h)
        a = ajustes.get(h.get("id")) or {}
        if a.get("severidad") in SEV:
            h["severidad"] = a["severidad"]
        h["_nota"], h["_desc"] = a.get("nota"), desc.get(h.get("id"))
        hallazgos.append(h)
    hallazgos.sort(key=lambda h: SEV.index(h["severidad"]) if h.get("severidad") in SEV else 9)
    vivos = [h for h in hallazgos if not h["_desc"]]
    r = datos.get("resumen") or {}
    roles = datos.get("roles") or []
    rutas = datos.get("rutas") or []
    matriz = {(c["rol"], c["url"]): c for c in datos.get("matriz") or []}
    activos = [x for x in roles if not x.get("autenticado") or x.get("login_ok")]
    criticos = [h for h in vivos if h["severidad"] == "Crítica"]
    sin_login = [x for x in roles if x.get("autenticado") and not x.get("login_ok")]
    if not rutas:
        tono, texto = "warn", "No se encontraron rutas para probar"
    elif criticos:
        tono, texto = "bad", f"{len(criticos)} problema(s) críticos: hay accesos que no deberían estar permitidos"
    elif vivos:
        tono, texto = "warn", "No hay accesos críticos, pero hay diferencias para revisar"
    else:
        tono, texto = "ok", "Cada rol ve y accede a lo que corresponde según lo revisado"
    if sin_login and tono == "ok":
        tono, texto = "warn", f"No se pudo probar con {len(sin_login)} rol(es): revisá sus credenciales"
    body = [banner(analisis.get("veredicto") or texto, analisis.get("veredicto_tono") or tono)]
    negadas = r.get("denegadas", 0) + r.get("piden_login", 0)
    body.append('<div style="margin-top:20px">' + kpi_tiles([
        ("Roles", r.get("roles", len(roles)), "warn" if sin_login else "", f'{len(activos)} probado(s), incluido el anónimo', "persona"),
        ("Rutas", r.get("rutas", len(rutas)), "", f'{r.get("visitas", 0)} visitas rol × ruta', "objetivo"),
        ("Permitidas", r.get("permitidas", 0), "", "la página se abrió", "pagina"),
        ("Negadas", negadas, "", "acceso denegado o pide login", "llave"),
        ("Distinto de lo esperado", len(difs), "bad" if difs else ("ok" if esperado else ""), "comparado contra la regla documentada" if esperado else "sin regla esperada (ver Falta información)", "warn"),
        ("Hallazgos", len(vivos), "bad" if criticos else ("warn" if vivos else "ok"), f"{len(criticos)} críticos", "bicho"),
    ]) + "</div>")
    if analisis.get("resumen"):
        body.append(section("Resumen ejecutivo", f'<div class="cardbody"><p class="lead">{e(analisis["resumen"])}</p></div>'))
    por_sev = [(s, sum(1 for h in vivos if h["severidad"] == s), c) for s, c in zip(SEV, [CRITICO, AVISO, SERIES[2], NEUTRO])]
    por_rol = [(x["id"], sum(1 for c in (datos.get("matriz") or []) if c["rol"] == x["id"] and c.get("acceso") == "permitido"), SERIES[i % len(SERIES)])
               for i, x in enumerate(activos)]
    body.append(two_col(section("Hallazgos por severidad", bar_chart(por_sev, ancho_etiqueta=90) if vivos else '<p class="muted" style="padding:16px 24px">Sin hallazgos.</p>'),
                        section("Rutas que abre cada rol", bar_chart(por_rol, ancho_etiqueta=120) if por_rol else '<p class="muted" style="padding:16px 24px">—</p>')))

    # Matriz rol × ruta
    if rutas and activos:
        filas = []
        for ru in rutas:
            celdas = [f'<span class="mono">{e(ru.get("ruta") or ruta_de(ru["url"]))}</span>'
                      + (f'<div class="muted">{"in the navigation of" if idioma_actual() == "en" else "en la navegación de"}: '
                         f'{e(", ".join(ru.get("descubierta_por") or []) or "—")}</div>')]
            for x in activos:
                c = matriz.get((x["id"], ru["url"]))
                if not c:
                    celdas.append('<span class="muted">—</span>')
                    continue
                esp = esperado_para(esperado, x["id"], ru["url"])
                marca = ""
                if esp:
                    ok = (esp == "permitido") == (c.get("acceso") == "permitido")
                    marca = f'<div class="muted">esperado: {e(esp)} {"✓" if ok else "✕"}</div>'
                celdas.append(acceso_pill(c.get("acceso")) + f'<div class="muted mono">{e(c.get("status"))}</div>' + marca)
            filas.append(celdas)
        body.append(section("Matriz de acceso por rol", f'<div class="matriz">{table(["Ruta"] + [x["id"] for x in activos], filas)}</div>',
                            "cada rol abre cada ruta escribiendo la URL, aunque no la vea en su menú"))
    eps = datos.get("endpoints") or []
    if eps:
        filas = []
        for ep in eps:
            celdas = [f'<span class="mono">{e(ep["metodo"])} {e(ep["ruta"])}</span>']
            for x in roles:
                res = (ep.get("resultados") or {}).get(x["id"])
                if not res:
                    celdas.append('<span class="muted">—</span>')
                    continue
                st = res.get("status") or 0
                color = OK if 200 <= st < 300 else NEUTRO if st in (401, 403) else CRITICO if st >= 500 or st == 0 else AVISO
                celdas.append(_pastilla(str(st or "sin respuesta"), color, "●") + (' <span class="muted">token</span>' if res.get("con_token") else ""))
            filas.append(celdas)
        body.append(section("Endpoints por rol", f'<div class="matriz">{table(["Endpoint"] + [x["id"] for x in roles], filas)}</div>',
                            "status de cada endpoint con la sesión y el token de cada rol (solo GET, HEAD u OPTIONS)"))

    if hallazgos:
        filas = []
        for h in hallazgos:
            det = (f'<strong style="color:var(--ink)">{e(h.get("titulo"))}</strong><div class="muted">{e(h.get("detalle"))}</div>'
                   + (f'<div><i>{e(h["_nota"])}</i></div>' if h.get("_nota") else "")
                   + (f'<div><b>Cómo corregirlo:</b> {e(h["correccion"])}</div>' if h.get("correccion") else "")
                   + (f'<div class="muted">Descartado: {e(h["_desc"])}</div>' if h.get("_desc") else ""))
            cap = h.get("captura") or (matriz.get((h.get("rol"), h.get("url"))) or {}).get("captura")
            filas.append([e(h.get("id")), nivel_badge(h.get("severidad")), e(h.get("tipo")), e(h.get("rol") or "—"), det,
                          miniatura(cap, f'{h.get("rol")} · {ruta_de(h.get("url"))}') if cap else '<span class="muted">—</span>'])
        body.append(section("Hallazgos", table(["ID", "Severidad", "Tipo", "Rol", "Hallazgo", "Evidencia"], filas)))

    # Qué ve cada rol
    bloques = []
    for x in roles:
        estado = ("sin sesión" if not x.get("autenticado") else "sesión iniciada" if x.get("login_ok") else f'{"could not log in" if idioma_actual() == "en" else "no pudo iniciar sesión"}: {x.get("login_error") or ""}')
        celdas = [c for (rol, _), c in matriz.items() if rol == x["id"] and c.get("acceso") == "permitido"]
        menus = sorted({m for c in celdas for m in c.get("menus") or []})
        botones = sorted({b for c in celdas for b in c.get("botones") or []})
        bloques.append(f'<div class="rol"><h3>{e(x.get("nombre") or x["id"])} <span class="muted">· {e(estado)}</span></h3>'
                       f'<div class="muted">Menús y links</div><div class="chips">{"".join(f"<span>{e(m)}</span>" for m in menus) or "—"}</div>'
                       f'<div class="muted" style="margin-top:8px">Botones</div><div class="chips">{"".join(f"<span>{e(b)}</span>" for b in botones) or "—"}</div></div>')
    if bloques:
        body.append(section("Qué ve cada rol", "".join(bloques), "menús, links y botones visibles en las páginas que se le abren"))

    fi = analisis.get("falta_informacion") or []
    if not esperado and not fi:
        fi = [{"id": "—", "que_falta": "La regla de permisos esperada (qué rol puede ver qué).",
               "pregunta": "¿Dónde está definida la matriz de permisos por rol? Sin ella, la matriz describe cómo funciona hoy, no si está bien."}]
    body.append(falta_informacion(fi))
    if analisis.get("recomendaciones"):
        filas = [[f'<strong style="color:var(--ink)">{e(x.get("accion"))}</strong>', e(x.get("motivo")), nivel_badge(x.get("prioridad"))]
                 for x in analisis["recomendaciones"]]
        body.append(section("Recomendaciones", table(["Acción", "Por qué", "Prioridad"], filas)))
    if analisis.get("proximos_pasos"):
        body.append(section("Próximos pasos", doc_list(analisis["proximos_pasos"])))
    if hist_html:
        body.append(hist_html)
    m = meta([("Historia", datos.get("historia")), ("Sitio", datos.get("host")), ("Fecha", (datos.get("fecha") or "")[:16].replace("T", " ")),
              ("Esperado", analisis.get("fuente_esperado") or ("documentado" if esperado else "sin definir"))])
    return page("Permisos", "Permisos por rol", m, CSS_EXTRA + CSS_PE + "".join(body))


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Informe HTML de permisos por rol a partir de permisos.json")
    ap.add_argument("datos_json")
    ap.add_argument("salida")
    ap.add_argument("--analisis")
    a = ap.parse_args()
    if not a.salida.lower().endswith(".html"):
        sys.exit("La salida debe terminar en .html")
    with open(a.datos_json, encoding="utf-8") as f:
        datos = json.load(f)
    analisis = {}
    if a.analisis:
        with open(a.analisis, encoding="utf-8") as f:
            analisis = json.load(f)
        avisar_analisis(analisis, [h.get("id") for h in datos.get("hallazgos") or []])
    hist_html = _historial.seccion("permisos", Path(a.datos_json).resolve().parent, datos)
    escribir_bilingue(a.salida, lambda: build_html(datos, localizar(analisis), hist_html=hist_html))
    print(f"OK: {a.salida}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Avisos a Slack y Microsoft Teams por webhook entrante (resultados de npm test, monitoreo, cierre, fallos…).

Uso (desde la raíz del repo):
    python scripts/avisar.py --titulo "Regresión del sprint 5" --texto "48 de 50 aprobados"
                             [--nivel ok|aviso|error] [--link URL] [--campos "Suite=web,Ambiente=staging"]
                             [--canal slack|teams|todos] [--prueba] [--estricto]
    python scripts/avisar.py --desde-cucumber herramientas/k0lmena/reports/web/cucumber-report.json [--link URL]

Configuración en el .env de la raíz (o en el entorno, que tiene prioridad):
    SLACK_WEBHOOK_URL   Incoming Webhook de una app de Slack (https://hooks.slack.com/services/...).
                        Se manda un mensaje con Block Kit.
    TEAMS_WEBHOOK_URL   Webhook de un flujo de Teams Workflows (Power Automate): plantilla "Post to a
                        channel when a webhook request is received". Se manda una Adaptive Card (1.4)
                        envuelta en un "message" con "attachments". Los "Incoming Webhooks" de los
                        conectores de Office 365 están retirados: no se usan.

--canal todos (por defecto) manda a los que estén configurados. Sin ningún webhook configurado avisa y
sale con 0 sin mandar nada (con --estricto, sale con 2). --prueba muestra el JSON que se mandaría, sin
mandarlo. La URL del webhook nunca se muestra: es un secreto (quien la tiene puede publicar en el canal).

--desde-cucumber resume un reporte JSON de Cucumber (npm test): aprobados, fallidos y los primeros
escenarios que fallaron, con su @HU/@CP. --titulo, --texto y --nivel, si se pasan, mandan sobre el resumen.

Códigos de salida: 0 enviado (o nada que enviar), 1 falló el envío, 2 falta configuración con --estricto
o argumentos inválidos.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

NIVELES = {
    "ok": {"emoji": ":white_check_mark:", "teams": "Good", "etiqueta": "OK"},
    "aviso": {"emoji": ":warning:", "teams": "Warning", "etiqueta": "Aviso"},
    "error": {"emoji": ":rotating_light:", "teams": "Attention", "etiqueta": "Error"},
}
VARIABLES = {"slack": "SLACK_WEBHOOK_URL", "teams": "TEAMS_WEBHOOK_URL"}


def parsear_campos(texto):
    """'Suite=web,Ambiente=staging' -> [('Suite', 'web'), ('Ambiente', 'staging')]."""
    campos = []
    for parte in (texto or "").split(","):
        if not parte.strip():
            continue
        if "=" not in parte:
            raise ValueError(f'campo sin "=": "{parte.strip()}" (formato Clave=Valor,Clave=Valor)')
        clave, valor = parte.split("=", 1)
        campos.append((clave.strip(), valor.strip()))
    return campos


def payload_slack(titulo, texto, nivel="ok", link=None, campos=()):
    n = NIVELES[nivel]
    bloques = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{titulo}"[:150], "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"{n['emoji']} {texto}"[:3000]}},
    ]
    if campos:
        bloques.append({"type": "section", "fields": [{"type": "mrkdwn", "text": f"*{k}*\n{v}"[:2000]} for k, v in list(campos)[:10]]})
    if link:
        bloques.append({"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "Ver detalle"}, "url": link}]})
    return {"text": f"[{n['etiqueta']}] {titulo}: {texto}"[:3000], "blocks": bloques}


def payload_teams(titulo, texto, nivel="ok", link=None, campos=()):
    n = NIVELES[nivel]
    cuerpo = [
        {"type": "TextBlock", "text": titulo, "weight": "Bolder", "size": "Medium", "color": n["teams"], "wrap": True},
        {"type": "TextBlock", "text": texto, "wrap": True},
    ]
    if campos:
        cuerpo.append({"type": "FactSet", "facts": [{"title": k, "value": v} for k, v in campos]})
    tarjeta = {"$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "type": "AdaptiveCard", "version": "1.4", "body": cuerpo}
    if link:
        tarjeta["actions"] = [{"type": "Action.OpenUrl", "title": "Ver detalle", "url": link}]
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "contentUrl": None, "content": tarjeta}]}


def resumen_cucumber(reporte):
    """Resumen de un reporte JSON de Cucumber: {total, aprobados, fallidos, otros, fallidos_detalle}."""
    total = aprobados = fallidos = 0
    detalle = []
    for feature in reporte or []:
        for esc in feature.get("elements") or []:
            if esc.get("type") == "background":
                continue
            total += 1
            estados = [((p.get("result") or {}).get("status") or "undefined") for p in esc.get("steps") or []]
            if "failed" in estados:
                fallidos += 1
                tags = [t.get("name", "") for t in esc.get("tags") or []]
                ids = " ".join(t for t in tags if t.startswith(("@HU-", "@CP-")))
                detalle.append(f"{ids} {esc.get('name', '')}".strip())
            elif estados and all(s == "passed" for s in estados):
                aprobados += 1
    return {"total": total, "aprobados": aprobados, "fallidos": fallidos, "otros": total - aprobados - fallidos, "fallidos_detalle": detalle}


def aviso_desde_cucumber(reporte, nombre="npm test"):
    r = resumen_cucumber(reporte)
    if not r["total"]:
        return f"{nombre}: sin escenarios", "El reporte no tiene escenarios.", "aviso", []
    nivel = "error" if r["fallidos"] else ("aviso" if r["otros"] else "ok")
    texto = f"{r['aprobados']} de {r['total']} escenario(s) aprobados"
    if r["fallidos"]:
        texto += f" · {r['fallidos']} fallido(s): " + "; ".join(r["fallidos_detalle"][:5])
        if len(r["fallidos_detalle"]) > 5:
            texto += f" y {len(r['fallidos_detalle']) - 5} más"
    campos = [("Aprobados", str(r["aprobados"])), ("Fallidos", str(r["fallidos"]))]
    if r["otros"]:
        campos.append(("Sin completar", str(r["otros"])))
    return f"{nombre}: {'falló' if r['fallidos'] else 'OK'}", texto, nivel, campos


def enviar(url, payload, timeout=15):
    """POST del JSON. Devuelve (ok, detalle) sin incluir nunca la URL."""
    datos = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=datos, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 300, f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf-8", "replace")[:200]
        return False, f"HTTP {e.code} {cuerpo}".strip()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        motivo = getattr(e, "reason", e)
        return False, f"sin respuesta ({type(motivo).__name__})"


def main(argv=None, entorno=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Avisos a Slack y Teams por webhook")
    ap.add_argument("--titulo")
    ap.add_argument("--texto")
    ap.add_argument("--nivel", choices=list(NIVELES))
    ap.add_argument("--link")
    ap.add_argument("--campos", default="")
    ap.add_argument("--canal", choices=["slack", "teams", "todos"], default="todos")
    ap.add_argument("--desde-cucumber", help="reporte JSON de Cucumber (npm test) para resumir")
    ap.add_argument("--nombre", default="npm test", help="nombre de la corrida en el aviso de --desde-cucumber")
    ap.add_argument("--prueba", action="store_true", help="muestra el JSON sin mandarlo")
    ap.add_argument("--estricto", action="store_true", help="sale con 2 si no hay webhook configurado")
    a = ap.parse_args(argv)

    try:
        campos = parsear_campos(a.campos)
    except ValueError as e:
        print(f"avisar: {e}", file=sys.stderr)
        return 2
    titulo, texto, nivel = a.titulo, a.texto, a.nivel or "ok"
    if a.desde_cucumber:
        try:
            reporte = json.loads(Path(a.desde_cucumber).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"avisar: no pude leer el reporte de Cucumber ({e})", file=sys.stderr)
            return 2
        t, x, n, c = aviso_desde_cucumber(reporte, a.nombre)
        titulo, texto, nivel, campos = a.titulo or t, a.texto or x, a.nivel or n, c + campos
    if not titulo or not texto:
        print("avisar: faltan --titulo y --texto (o --desde-cucumber)", file=sys.stderr)
        return 2

    if entorno is None:
        _env.cargar_env()
        import os
        entorno = os.environ
    canales = ["slack", "teams"] if a.canal == "todos" else [a.canal]
    destinos = [(c, (entorno.get(VARIABLES[c]) or "").strip()) for c in canales]
    armadores = {"slack": payload_slack, "teams": payload_teams}

    if a.prueba:
        for c, _ in destinos:
            print(f"--- {c} ---")
            print(json.dumps(armadores[c](titulo, texto, nivel, a.link, campos), ensure_ascii=False, indent=2))
        return 0

    configurados = [(c, u) for c, u in destinos if u]
    for c, u in destinos:
        if not u:
            print(f"avisar: {c} no está configurado ({VARIABLES[c]} en el .env); no se manda.")
    if not configurados:
        return 2 if a.estricto else 0
    error = False
    for c, url in configurados:
        if not url.startswith("https://"):
            print(f"avisar: {VARIABLES[c]} tiene que empezar con https://; no se manda a {c}.", file=sys.stderr)
            error = True
            continue
        ok, detalle = enviar(url, armadores[c](titulo, texto, nivel, a.link, campos))
        print(f"avisar: {c} {'OK' if ok else 'falló'} ({detalle})")
        error |= not ok
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())

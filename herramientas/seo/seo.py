#!/usr/bin/env python3
"""
Relevamiento de SEO y GEO de una página, de solo lectura y sin dependencias (urllib + regex de la stdlib).

Uso (desde la raíz del repo):
    python herramientas/seo/seo.py --url https://mi-sitio.com/pagina   [--salida output/seo/pagina.json]

Qué hace (solo lectura, un GET por recurso):
- Trae la página y extrae el SEO on-page: title, meta description, canonical, meta robots, H1, Open Graph,
  tipos de datos estructurados (JSON-LD) y hreflang.
- Trae robots.txt y detecta si bloquea el sitio y qué permite a los crawlers de IA (GPTBot, ClaudeBot,
  PerplexityBot, Google-Extended) — clave para el GEO.
- Chequea la existencia del sitemap.

No modifica nada. Los Core Web Vitals los mide el auditor-rendimiento-web; el render JS, el agente con Playwright.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "k0lmenIA-QA/1.0 (relevamiento SEO de solo lectura)"
BOTS_IA = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai", "PerplexityBot", "Google-Extended", "CCBot"]


def _buscar(rx, html, grupo=1):
    m = re.search(rx, html or "", re.I | re.S)
    return (m.group(grupo).strip() if m else None)


def extraer_seo(html):
    """SEO on-page de un HTML. Puro y testeable."""
    tipos = set()
    for bloque in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html or "", re.I | re.S):
        try:
            d = json.loads(bloque.strip())
        except ValueError:
            continue
        pila = [d]
        while pila:
            x = pila.pop()
            if isinstance(x, list):
                pila.extend(x)
            elif isinstance(x, dict):
                t = x.get("@type")
                tipos.update(t if isinstance(t, list) else [t] if t else [])
                pila.extend(v for v in x.values() if isinstance(v, (list, dict)))
    h1 = re.findall(r"<h1\b[^>]*>(.*?)</h1>", html or "", re.I | re.S)
    hreflang = re.findall(r'<link[^>]+rel=["\']alternate["\'][^>]+hreflang=["\']([^"\']+)["\']', html or "", re.I)
    return {
        "title": _buscar(r"<title[^>]*>(.*?)</title>", html),
        "meta_description": _buscar(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html),
        "canonical": _buscar(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](.*?)["\']', html),
        "meta_robots": _buscar(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'](.*?)["\']', html),
        "og_title": _buscar(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', html),
        "h1": [re.sub(r"<[^>]+>", "", x).strip() for x in h1],
        "jsonld_tipos": sorted(t for t in tipos if isinstance(t, str)),
        "hreflang": hreflang,
    }


def crawlers_ia(robots_txt):
    """Para cada bot de IA, si tiene un grupo propio y si lo bloquea (Disallow: /). Puro y testeable."""
    out = {}
    lineas = (robots_txt or "").splitlines()
    i = 0
    grupos = []  # (agentes set, disallows list)
    actual_agentes, actual_dis, en_reglas = set(), [], False
    for linea in lineas:
        linea = linea.split("#", 1)[0].strip()
        if ":" not in linea:
            continue
        k, v = (x.strip() for x in linea.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            if en_reglas:
                grupos.append((actual_agentes, actual_dis))
                actual_agentes, actual_dis, en_reglas = set(), [], False
            actual_agentes.add(v)
        elif k == "disallow":
            en_reglas = True
            actual_dis.append(v)
    if actual_agentes:
        grupos.append((actual_agentes, actual_dis))
    for bot in BOTS_IA:
        propio = next((dis for ag, dis in grupos if bot in ag), None)
        if propio is None:
            out[bot] = "sin regla propia (hereda User-agent: *)"
        elif "/" in propio:
            out[bot] = "bloqueado (Disallow: /)"
        else:
            out[bot] = "permitido"
    return out


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(3 * 1024 * 1024).decode(r.headers.get_content_charset() or "utf-8", "replace")
    except urllib.error.HTTPError as ex:
        return ex.code, ""
    except Exception as ex:
        return 0, f"{type(ex).__name__}: {ex}"


def relevar(url):
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(url))
    st, html = _get(url)
    inv = {"url": url, "status": st, "seo": extraer_seo(html) if st and 200 <= st < 400 else {}}
    st_r, robots = _get(base + "/robots.txt", timeout=12)
    inv["robots_existe"] = bool(st_r and 200 <= st_r < 300)
    inv["crawlers_ia"] = crawlers_ia(robots) if inv["robots_existe"] else {}
    inv["robots_bloquea_todo"] = bool(re.search(r"(?im)^\s*user-agent:\s*\*\s*$.*?^\s*disallow:\s*/\s*$", robots or "", re.S))
    sm = (re.search(r"(?im)^sitemap:\s*(\S+)", robots or "") or [None, base + "/sitemap.xml"])[1]
    st_s, _ = _get(sm, timeout=15)
    inv["sitemap"] = {"url": sm, "existe": bool(st_s and 200 <= st_s < 300)}
    return inv


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Relevamiento de SEO/GEO de una página (solo lectura).")
    ap.add_argument("--url", required=True)
    ap.add_argument("--salida", default="")
    args = ap.parse_args(argv)
    inv = relevar(args.url)
    texto = json.dumps(inv, ensure_ascii=False, indent=2)
    if args.salida:
        p = Path(args.salida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        print(f"[seo] Datos en {p}", file=sys.stderr)
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())

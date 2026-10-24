#!/usr/bin/env python3
"""
Trae el código a revisar desde GitHub, GitLab, Bitbucket, Azure Repos, Gitea/Codeberg o cualquier URL git,
de solo lectura, y deja un manifiesto con lo que se trajo (y, si es un PR/MR o una rama contra su base, qué cambió).

Uso (desde la raíz del repo de k0lmenIA):
    python herramientas/codigo/obtener.py --origen https://github.com/dueño/repo
    python herramientas/codigo/obtener.py --origen https://github.com/dueño/repo/pull/123
    python herramientas/codigo/obtener.py --origen https://gitlab.com/grupo/proyecto/-/merge_requests/45
    python herramientas/codigo/obtener.py --origen https://bitbucket.org/workspace/repo/pull-requests/7
    python herramientas/codigo/obtener.py --origen https://dev.azure.com/org/proyecto/_git/repo/pullrequest/9
    python herramientas/codigo/obtener.py --origen https://github.com/dueño/repo/tree/feature-x --base main
    python herramientas/codigo/obtener.py --origen C:/proyectos/mi-app [--base main]
    python herramientas/codigo/obtener.py            (sin --origen: REPO_PROVEEDOR + REPO_NOMBRE del .env)

Qué hace:
- Reconoce el proveedor por la URL (o `REPO_PROVEEDOR`/`REPO_NOMBRE`/`REPO_RAMA` del .env) y clona en
  `output/revision-codigo/<repo>/fuente/` (no se versiona). Rama suelta: clon superficial (`--depth 1`).
  PR/MR o rama contra base: clon parcial (`--filter=blob:none`) para poder calcular el merge-base.
- PR/MR: trae la rama del PR (refs/pull, refs/merge-requests o, en Bitbucket, la rama origen por la API) y su
  rama destino (por la API del proveedor; si no se puede, la rama por defecto) y calcula el diff contra el
  merge-base: archivos cambiados, líneas nuevas por archivo y `cambios.diff`.
- Tokens (opcionales, solo para repos privados), del .env: `GITHUB_TOKEN`, `GITLAB_TOKEN`, `BITBUCKET_TOKEN`
  (o `JIRA_API_TOKEN`), `ADO_PAT`, y `REVISION_GIT_TOKEN` (+ `REVISION_GIT_USUARIO`) para cualquier otro host o
  para pisar los anteriores. Cada token solo se manda a su host. Viajan como header HTTP por variables de
  entorno de git (no quedan en la URL, en `.git/config` ni en la salida).

Seguridad: el código traído es ajeno y no confiable. No se ejecuta nada del repo (ni hooks, ni submódulos,
ni LFS, ni instaladores); los symlinks se clonan como archivos de texto.
"""
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
MARCA = ".k0lmenia-origen.json"
TIMEOUT_GIT = 900


# ------------------------------------------------------------------ .env

def leer_env():
    sys.path.insert(0, str(RAIZ / "scripts"))
    try:
        from _env import leer_env as _leer
        valores = _leer()
    except Exception:
        valores = {}
    valores.update({k: v for k, v in os.environ.items() if v})
    return valores


# ------------------------------------------------------------------ origen (puro, testeable)

def _limpio(s):
    return re.sub(r"\.git$", "", s.strip("/"))


def parsear_origen(texto, env=None):
    """Interpreta una URL de repo/PR/MR (o una ruta local) y devuelve un dict con proveedor, host, repo,
    clone_url, rama, pr y web (URL base para links). No toca la red."""
    env = env or {}
    t = (texto or "").strip()
    if not t:
        raise ValueError("falta el origen")
    if not re.match(r"^[a-z][a-z0-9+.\-]*://", t, re.I) and not re.match(r"^[\w.\-]+@[\w.\-]+:", t):
        if Path(t).exists():
            return {"proveedor": "local", "ruta": str(Path(t).resolve()), "rama": None, "pr": None}
        if re.match(r"^[\w.\-]+(\.[a-z]{2,})/", t):  # github.com/dueño/repo sin esquema
            t = "https://" + t
        else:
            raise ValueError(f"no se reconoce el origen: {texto} (no es una URL ni una ruta existente)")

    m = re.match(r"^[\w.\-]+@([\w.\-]+):(.+)$", t)  # git@host:dueño/repo.git (SSH: usa tus llaves)
    if m:
        host, ruta = m.group(1).lower(), _limpio(m.group(2))
        prov = "github" if host == "github.com" else "bitbucket" if host == "bitbucket.org" else \
            "gitlab" if "gitlab" in host else "git"
        return {"proveedor": prov, "host": host, "repo": ruta, "clone_url": t, "rama": None, "pr": None,
                "web": f"https://{host}/{ruta}"}

    u = urllib.parse.urlparse(t)
    host = (u.hostname or "").lower()
    partes = [p for p in u.path.split("/") if p]
    qs = urllib.parse.parse_qs(u.query)
    gitlab_host = urllib.parse.urlparse(env.get("GITLAB_URL") or "https://gitlab.com").hostname or "gitlab.com"
    base = f"{u.scheme}://{u.netloc.split('@')[-1]}"

    if host in ("github.com", "www.github.com"):
        if len(partes) < 2:
            raise ValueError("URL de GitHub incompleta: falta dueño/repo")
        repo = f"{partes[0]}/{_limpio(partes[1])}"
        rama = pr = None
        if len(partes) >= 4 and partes[2] == "pull" and partes[3].isdigit():
            pr = int(partes[3])
        elif len(partes) >= 4 and partes[2] in ("tree", "blob", "commits"):
            rama = "/".join(partes[3:]) if partes[2] != "blob" else partes[3]
        return {"proveedor": "github", "host": "github.com", "repo": repo, "rama": rama, "pr": pr,
                "clone_url": f"https://github.com/{repo}.git", "web": f"https://github.com/{repo}"}

    if host in ("bitbucket.org", "www.bitbucket.org"):
        if len(partes) < 2:
            raise ValueError("URL de Bitbucket incompleta: falta workspace/repo")
        repo = f"{partes[0]}/{_limpio(partes[1])}"
        rama = pr = None
        if len(partes) >= 4 and partes[2] == "pull-requests" and partes[3].isdigit():
            pr = int(partes[3])
        elif len(partes) >= 4 and partes[2] in ("src", "branch"):
            rama = partes[3]
        return {"proveedor": "bitbucket", "host": "bitbucket.org", "repo": repo, "rama": rama, "pr": pr,
                "clone_url": f"https://bitbucket.org/{repo}.git", "web": f"https://bitbucket.org/{repo}"}

    if host == "dev.azure.com" or host.endswith(".visualstudio.com"):
        if "_git" not in partes:
            raise ValueError("URL de Azure Repos sin /_git/: usá https://dev.azure.com/org/proyecto/_git/repo")
        i = partes.index("_git")
        previos = partes[:i]
        if host == "dev.azure.com":
            org, proyecto = previos[0], (previos[1] if len(previos) > 1 else None)
        else:
            org, proyecto = host.split(".")[0], (previos[0] if previos else None)
        nombre = _limpio(partes[i + 1])
        proyecto = proyecto or nombre
        pr = None
        if len(partes) > i + 3 and partes[i + 2].lower() == "pullrequest" and partes[i + 3].isdigit():
            pr = int(partes[i + 3])
        version = (qs.get("version") or [""])[0]
        rama = version[2:] if version.startswith("GB") else None
        web = f"https://dev.azure.com/{org}/{proyecto}/_git/{nombre}"
        return {"proveedor": "azure", "host": "dev.azure.com", "repo": f"{org}/{proyecto}/{nombre}",
                "organizacion": org, "proyecto": proyecto, "nombre": nombre, "rama": rama, "pr": pr,
                "clone_url": web, "web": web}

    # GitLab (gitlab.com, el GITLAB_URL del .env o un host que se llame gitlab.*): grupo/subgrupo/proyecto/-/...
    if host == gitlab_host or host == "gitlab.com" or host.startswith("gitlab."):
        if "-" in partes:
            i = partes.index("-")
            repo_partes, resto = partes[:i], partes[i + 1:]
        else:
            repo_partes, resto = partes, []
        if len(repo_partes) < 2:
            raise ValueError("URL de GitLab incompleta: falta grupo/proyecto")
        repo = "/".join(repo_partes[:-1] + [_limpio(repo_partes[-1])])
        rama = pr = None
        if len(resto) >= 2 and resto[0] == "merge_requests" and resto[1].isdigit():
            pr = int(resto[1])
        elif len(resto) >= 2 and resto[0] in ("tree", "blob", "commits"):
            rama = "/".join(resto[1:]) if resto[0] != "blob" else resto[1]
        return {"proveedor": "gitlab", "host": host, "repo": repo, "rama": rama, "pr": pr,
                "clone_url": f"{base}/{repo}.git", "web": f"{base}/{repo}"}

    # Cualquier otro host: Gitea, Forgejo, Codeberg o un servidor git propio.
    if len(partes) < 1:
        raise ValueError(f"URL sin ruta de repositorio: {texto}")
    rama = pr = None
    corte = len(partes)
    for i, p in enumerate(partes):
        if p in ("pulls", "pull") and i + 1 < len(partes) and partes[i + 1].isdigit():
            pr, corte = int(partes[i + 1]), i
            break
        if p == "src" and i + 2 < len(partes) and partes[i + 1] == "branch":
            rama, corte = "/".join(partes[i + 2:]), i
            break
    repo = "/".join(partes[:corte - 1] + [_limpio(partes[corte - 1])]) if corte else _limpio(partes[0])
    clone_url = t if t.endswith(".git") and not (pr or rama) else f"{base}/{repo}.git"
    return {"proveedor": "gitea" if (pr or rama or host == "codeberg.org") else "git", "host": host, "repo": repo,
            "rama": rama, "pr": pr, "clone_url": clone_url, "web": f"{base}/{repo}"}


def origen_desde_env(env):
    """Arma la URL desde REPO_PROVEEDOR + REPO_NOMBRE (+ REPO_RAMA). Si hay varios repos, toma el primero."""
    prov = (env.get("REPO_PROVEEDOR") or "").strip().lower()
    nombre = (env.get("REPO_NOMBRE") or "").split(",")[0].strip()
    if not prov or not nombre:
        return None
    if prov == "github":
        url = f"https://github.com/{nombre}"
    elif prov == "gitlab":
        url = f"{(env.get('GITLAB_URL') or 'https://gitlab.com').rstrip('/')}/{nombre}"
    elif prov == "bitbucket":
        url = f"https://bitbucket.org/{nombre}"
    elif prov == "azure-repos":
        org = env.get("ADO_ORGANIZACION") or ""
        proyecto, _, repo = nombre.partition("/")
        url = f"https://dev.azure.com/{org}/{proyecto}/_git/{repo or proyecto}"
    else:
        return None
    return url


def ref_del_pr(info):
    """La ref de git donde el proveedor publica el PR/MR (None si hay que pedirla por la API, como Bitbucket)."""
    n = info.get("pr")
    return {"github": f"refs/pull/{n}/head", "gitlab": f"refs/merge-requests/{n}/head",
            "azure": f"refs/pull/{n}/merge", "gitea": f"refs/pull/{n}/head"}.get(info["proveedor"])


def url_blob(info, commit):
    """Plantilla de link a un archivo:línea en la web del proveedor ({archivo} y {linea} se completan después)."""
    web, p = info.get("web"), info["proveedor"]
    if not web or not commit:
        return None
    if p == "github":
        return f"{web}/blob/{commit}/{{archivo}}#L{{linea}}"
    if p == "gitlab":
        return f"{web}/-/blob/{commit}/{{archivo}}#L{{linea}}"
    if p == "bitbucket":
        return f"{web}/src/{commit}/{{archivo}}#lines-{{linea}}"
    if p == "azure":
        return f"{web}?path=/{{archivo}}&version=GC{commit}&line={{linea}}"
    if p == "gitea":
        return f"{web}/src/commit/{commit}/{{archivo}}#L{{linea}}"
    return None


# ------------------------------------------------------------------ credenciales

def credenciales(info, env):
    """(header_git, headers_api) para el host del origen. Cada token solo va a su proveedor."""
    p, host = info["proveedor"], info.get("host", "")
    basic = lambda u, t: "Basic " + base64.b64encode(f"{u}:{t}".encode()).decode()  # noqa: E731
    generico, usuario = env.get("REVISION_GIT_TOKEN"), env.get("REVISION_GIT_USUARIO") or "git"
    if p == "github":
        tok = generico or env.get("GITHUB_TOKEN")
        return (basic("x-access-token", tok), {"Authorization": f"Bearer {tok}"}) if tok else (None, {})
    if p == "gitlab":
        gl_host = urllib.parse.urlparse(env.get("GITLAB_URL") or "https://gitlab.com").hostname
        tok = generico or (env.get("GITLAB_TOKEN") if host in (gl_host, "gitlab.com") else None)
        return (basic("oauth2", tok), {"PRIVATE-TOKEN": tok}) if tok else (None, {})
    if p == "bitbucket":
        tok = generico or env.get("BITBUCKET_TOKEN") or env.get("JIRA_API_TOKEN")
        if not tok:
            return None, {}
        email = env.get("BITBUCKET_EMAIL") or env.get("JIRA_EMAIL") or ""
        return basic("x-bitbucket-api-token-auth", tok), ({"Authorization": basic(email, tok)} if email else {})
    if p == "azure":
        tok = generico or env.get("ADO_PAT")
        return (basic("", tok), {"Authorization": basic("", tok)}) if tok else (None, {})
    if generico:
        return basic(usuario, generico), {"Authorization": f"token {generico}"}
    return None, {}


def entorno_git(header):
    """Entorno para git: sin prompts, sin LFS, y el header de auth por GIT_CONFIG_* (no queda en argv ni en disco)."""
    e = dict(os.environ)
    e.update({"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1", "GCM_INTERACTIVE": "never",
              "GIT_ASKPASS": "", "SSH_ASKPASS": ""})
    pares = [("protocol.file.allow", "never"), ("core.symlinks", "false"), ("core.longpaths", "true"),
             ("core.hooksPath", os.devnull), ("submodule.recurse", "false"), ("credential.helper", "")]
    if header:
        pares.append(("http.extraHeader", f"Authorization: {header}"))
    e["GIT_CONFIG_COUNT"] = str(len(pares))
    for i, (k, v) in enumerate(pares):
        e[f"GIT_CONFIG_KEY_{i}"], e[f"GIT_CONFIG_VALUE_{i}"] = k, v
    return e


def ocultar(texto, env):
    """Saca cualquier token del .env que aparezca en un mensaje de error."""
    for k in ("GITHUB_TOKEN", "GITLAB_TOKEN", "BITBUCKET_TOKEN", "JIRA_API_TOKEN", "ADO_PAT", "REVISION_GIT_TOKEN"):
        v = env.get(k)
        if v and len(v) > 4:
            texto = texto.replace(v, "***")
    return re.sub(r"(https?://)[^/\s:@]+:[^/\s@]+@", r"\1***@", texto)


# ------------------------------------------------------------------ git

class ErrorGit(RuntimeError):
    pass


def git(args, cwd=None, env=None, check=True):
    p = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=TIMEOUT_GIT)
    if check and p.returncode != 0:
        raise ErrorGit((p.stderr or p.stdout or "").strip()[:600])
    return p.stdout


def parsear_diff(diff):
    """{archivo: [[ini, fin], ...]} con los rangos de líneas nuevas/modificadas de un `git diff -U0`. Puro."""
    cambios, actual = {}, None
    for linea in diff.splitlines():
        if linea.startswith("+++ "):
            ruta = linea[4:].strip()
            actual = None if ruta == "/dev/null" else re.sub(r"^b/", "", ruta)
            if actual:
                cambios.setdefault(actual, [])
        elif linea.startswith("@@") and actual:
            m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", linea)
            if m:
                ini, n = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
                if n > 0:
                    cambios[actual].append([ini, ini + n - 1])
    return cambios


def parsear_name_status(texto):
    """[(estado, archivo)] de `git diff --name-status` (R/C se reportan con el nombre nuevo)."""
    out = []
    for linea in texto.splitlines():
        cols = linea.split("\t")
        if len(cols) >= 2:
            out.append((cols[0][0], cols[-1]))
    return out


def calcular_cambios(dest, base_ref, cabeza_ref, env):
    mb = git(["merge-base", base_ref, cabeza_ref], cwd=dest, env=env).strip()
    estados = parsear_name_status(git(["diff", "--name-status", "-M", mb, cabeza_ref], cwd=dest, env=env))
    diff_u0 = git(["diff", "-U0", "--no-color", "-M", mb, cabeza_ref], cwd=dest, env=env)
    lineas = parsear_diff(diff_u0)
    diff_legible = git(["diff", "--no-color", "-M", "--stat", "--patch", mb, cabeza_ref], cwd=dest, env=env)
    cambios = [{"archivo": a, "estado": {"A": "agregado", "M": "modificado", "D": "borrado", "R": "renombrado",
                                         "C": "copiado", "T": "cambió de tipo"}.get(s, s), "lineas": lineas.get(a, [])}
               for s, a in estados]
    return mb, cambios, diff_legible


# ------------------------------------------------------------------ API del proveedor (datos del PR)

def api_json(url, headers):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "k0lmenIA", **headers})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (URL armada desde el proveedor)
        return json.loads(r.read().decode("utf-8"))


def datos_pr(info, headers):
    """{titulo, base, cabeza, autor, url} del PR/MR por la API del proveedor. Lanza si no se puede."""
    p, n, repo = info["proveedor"], info["pr"], info["repo"]
    if p == "github":
        d = api_json(f"https://api.github.com/repos/{repo}/pulls/{n}", headers)
        return {"titulo": d.get("title"), "base": d["base"]["ref"], "cabeza": d["head"]["ref"],
                "base_sha": d["base"].get("sha"), "estado": "mergeado" if d.get("merged_at") else d.get("state"),
                "autor": (d.get("user") or {}).get("login"), "url": d.get("html_url")}
    if p == "gitlab":
        api = info["web"].rsplit("/" + repo, 1)[0] + "/api/v4"
        d = api_json(f"{api}/projects/{urllib.parse.quote(repo, safe='')}/merge_requests/{n}", headers)
        return {"titulo": d.get("title"), "base": d["target_branch"], "cabeza": d["source_branch"],
                "base_sha": (d.get("diff_refs") or {}).get("base_sha"),
                "estado": "mergeado" if d.get("state") == "merged" else d.get("state"),
                "autor": (d.get("author") or {}).get("username"), "url": d.get("web_url")}
    if p == "bitbucket":
        d = api_json(f"https://api.bitbucket.org/2.0/repositories/{repo}/pullrequests/{n}", headers)
        origen_repo = ((d.get("source") or {}).get("repository") or {}).get("full_name")
        return {"titulo": d.get("title"), "base": d["destination"]["branch"]["name"],
                "cabeza": d["source"]["branch"]["name"], "estado": "mergeado" if d.get("state") == "MERGED" else d.get("state"),
                "base_sha": ((d.get("destination") or {}).get("commit") or {}).get("hash"), "autor": (d.get("author") or {}).get("display_name"),
                "url": ((d.get("links") or {}).get("html") or {}).get("href"),
                "repo_origen": origen_repo if origen_repo and origen_repo != repo else None}
    if p == "azure":
        d = api_json(f"https://dev.azure.com/{info['organizacion']}/{urllib.parse.quote(info['proyecto'])}/_apis/git/"
                     f"repositories/{urllib.parse.quote(info['nombre'])}/pullRequests/{n}?api-version=7.1", headers)
        quitar = lambda r: re.sub(r"^refs/heads/", "", r or "")  # noqa: E731
        return {"titulo": d.get("title"), "base": quitar(d.get("targetRefName")), "cabeza": quitar(d.get("sourceRefName")),
                "base_sha": (d.get("lastMergeTargetCommit") or {}).get("commitId"),
                "estado": "mergeado" if d.get("status") == "completed" else d.get("status"),
                "autor": (d.get("createdBy") or {}).get("displayName"), "url": f"{info['web']}/pullrequest/{n}"}
    if p == "gitea":
        api = info["web"].rsplit("/" + repo, 1)[0] + "/api/v1"
        d = api_json(f"{api}/repos/{repo}/pulls/{n}", headers)
        return {"titulo": d.get("title"), "base": d["base"]["ref"], "cabeza": d["head"]["ref"],
                "base_sha": d.get("merge_base"), "estado": "mergeado" if d.get("merged") else d.get("state"),
                "autor": (d.get("user") or {}).get("login"), "url": d.get("html_url")}
    raise ValueError(f"el proveedor {p} no tiene API de PR soportada")


# ------------------------------------------------------------------ flujo principal

def slug(texto):
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", texto).strip("-").lower()
    return s[:80] or "repo"


def preparar_destino(dest, origen_url):
    """Reutiliza un clon anterior de la misma herramienta y el mismo origen; si la carpeta es otra cosa, frena."""
    marca = dest / MARCA
    if not dest.exists():
        return False
    if marca.exists():
        try:
            previo = json.loads(marca.read_text(encoding="utf-8"))
        except ValueError:
            previo = {}
        if previo.get("clone_url") == origen_url:
            return True
        shutil.rmtree(dest)  # clon nuestro de otro origen: se rehace
        return False
    if any(dest.iterdir()):
        raise ErrorGit(f"{dest} ya existe y no es un clon de esta herramienta: elegí otro --destino.")
    return False


def obtener(origen, base=None, destino=None, env=None):
    env = env if env is not None else leer_env()
    if not origen:
        origen = origen_desde_env(env)
        if not origen:
            raise ValueError("falta --origen (URL del repo/PR/MR o ruta local) y no hay REPO_PROVEEDOR + REPO_NOMBRE en el .env")
    info = parsear_origen(origen, env)
    if info["proveedor"] != "local" and not info.get("rama") and not info.get("pr") and env.get("REPO_RAMA") \
            and origen == origen_desde_env(env):
        info["rama"] = env["REPO_RAMA"]
    man = {"origen": origen, **{k: v for k, v in info.items() if k not in ("clone_url",)},
           "base": base, "modo": "repo", "avisos": [], "errores": []}

    if info["proveedor"] == "local":
        dest = Path(info["ruta"])
        man["ruta_local"] = str(dest)
        if base:
            if not (dest / ".git").exists():
                raise ErrorGit(f"{dest} no es un repositorio git: no se puede comparar contra {base}.")
            genv = entorno_git(None)
            cabeza = "HEAD"
            mb, cambios, diff = calcular_cambios(dest, base, cabeza, genv)
            man.update({"modo": "rama-vs-base", "merge_base": mb, "cambios": cambios,
                        "commit": git(["rev-parse", "HEAD"], cwd=dest, env=genv).strip()})
            man["_diff"] = diff
        return man

    if not shutil.which("git"):
        raise ErrorGit("git no está instalado: https://git-scm.com/downloads")
    header, api_headers = credenciales(info, env)
    genv = entorno_git(header)
    man["autenticado"] = bool(header)
    nombre = slug(info["repo"].split("/")[-1] + (f"-pr-{info['pr']}" if info.get("pr") else
                                                 f"-{info['rama']}" if info.get("rama") else ""))
    dest = Path(destino) if destino else PROYECTO / "output" / "revision-codigo" / nombre / "fuente"
    reusar = preparar_destino(dest, info["clone_url"])
    dest.parent.mkdir(parents=True, exist_ok=True)

    pr = None
    if info.get("pr"):
        try:
            pr = datos_pr(info, api_headers)
        except (urllib.error.URLError, KeyError, ValueError, OSError) as ex:
            man["avisos"].append(f"No se pudieron leer los datos del PR por la API ({ocultar(str(ex), env)[:160]}); "
                                 "se compara contra la rama por defecto.")
        if info["proveedor"] == "bitbucket" and not pr:
            raise ErrorGit("Bitbucket no publica los PR como refs de git y la API no respondió: configurá BITBUCKET_TOKEN "
                           "(o pasá la rama del PR con /src/<rama> y --base <rama destino>).")
        if pr and pr.get("repo_origen"):
            man["avisos"].append(f"El PR viene del fork {pr['repo_origen']}: se trae desde ahí.")
        man["pr"] = {"numero": info["pr"], **(pr or {})}
        man["modo"] = "pr"
    elif base:
        man["modo"] = "rama-vs-base"

    necesita_historia = man["modo"] in ("pr", "rama-vs-base")
    try:
        if not reusar:
            args = ["clone", "--no-tags", "--no-recurse-submodules"]
            if necesita_historia:
                args += ["--filter=blob:none", "--no-checkout"]
            else:
                args += ["--depth", "1", "--single-branch"] + (["--branch", info["rama"]] if info.get("rama") else [])
            try:
                git(args + [info["clone_url"], str(dest)], env=genv)
            except ErrorGit:
                if not necesita_historia:
                    raise
                shutil.rmtree(dest, ignore_errors=True)  # el servidor no soporta clon parcial: clon completo
                git(["clone", "--no-tags", "--no-recurse-submodules", "--no-checkout", info["clone_url"], str(dest)], env=genv)
                man["avisos"].append("El servidor no soporta clon parcial: se hizo un clon completo.")

        por_defecto = git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=dest, env=genv, check=False).strip()
        por_defecto = re.sub(r"^origin/", "", por_defecto) or None

        if man["modo"] == "pr":
            ref = ref_del_pr(info)
            if info["proveedor"] == "bitbucket" or (pr and pr.get("repo_origen")):
                fuente = f"https://bitbucket.org/{pr['repo_origen']}.git" if pr.get("repo_origen") else "origin"
                git(["fetch", "--no-tags", fuente, f"+refs/heads/{pr['cabeza']}:refs/k0lmenia/cabeza"], cwd=dest, env=genv)
            else:
                git(["fetch", "--no-tags", "origin", f"+{ref}:refs/k0lmenia/cabeza"], cwd=dest, env=genv)
            base_rama = (pr or {}).get("base") or base or por_defecto
        elif man["modo"] == "rama-vs-base":
            cab = info.get("rama") or por_defecto
            git(["fetch", "--no-tags", "origin", f"+refs/heads/{cab}:refs/k0lmenia/cabeza"], cwd=dest, env=genv)
            base_rama = base
        else:
            if reusar:
                rama = info.get("rama") or por_defecto or "HEAD"
                git(["fetch", "--no-tags", "--depth", "1", "origin", rama], cwd=dest, env=genv)
                git(["checkout", "--force", "--detach", "FETCH_HEAD"], cwd=dest, env=genv)
            base_rama = None

        if necesita_historia:
            if not base_rama:
                raise ErrorGit("no se pudo determinar la rama base para comparar: pasala con --base.")
            git(["fetch", "--no-tags", "origin", f"+refs/heads/{base_rama}:refs/k0lmenia/base"], cwd=dest, env=genv)
            git(["checkout", "--force", "--detach", "refs/k0lmenia/cabeza"], cwd=dest, env=genv)
            base_ref = "refs/k0lmenia/base"
            sha = (pr or {}).get("base_sha")
            # El commit base que informa el proveedor: con el PR ya mergeado, la punta de la rama base ya
            # contiene los cambios y el diff contra ella daría vacío.
            if sha and subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=dest, env=genv,
                                      capture_output=True).returncode == 0:
                base_ref = sha
            if (pr or {}).get("estado") == "mergeado":
                man["avisos"].append("El PR ya está mergeado: se revisan sus cambios contra el commit base que tenía.")
            mb, cambios, diff = calcular_cambios(dest, base_ref, "refs/k0lmenia/cabeza", genv)
            man.update({"base": base_rama, "merge_base": mb, "cambios": cambios, "_diff": diff})
    except ErrorGit as ex:
        msg = ocultar(str(ex), env)
        if re.search(r"Authentication failed|could not read Username|403|401|not found|Repository not found", msg, re.I):
            msg += (" — si el repo es privado, configurá el token del proveedor en el .env "
                    "(GITHUB_TOKEN, GITLAB_TOKEN, BITBUCKET_TOKEN, ADO_PAT o REVISION_GIT_TOKEN).")
        raise ErrorGit(msg)

    commit = git(["rev-parse", "HEAD"], cwd=dest, env=genv).strip()
    man.update({"ruta_local": str(dest), "commit": commit, "rama_por_defecto": por_defecto,
                "url_blob": url_blob(info, commit)})
    if not man.get("rama"):
        man["rama"] = (pr or {}).get("cabeza") or por_defecto
    (dest / MARCA).write_text(json.dumps({"clone_url": info["clone_url"]}), encoding="utf-8")
    excluir = dest / ".git" / "info" / "exclude"
    if excluir.parent.exists():
        excluir.write_text(MARCA + "\n", encoding="utf-8")
    return man


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Trae el código a revisar (GitHub, GitLab, Bitbucket, Azure Repos, Gitea o git) "
                                             "y, si es un PR/MR, sus cambios. Solo lectura.")
    ap.add_argument("--origen", default="", help="URL del repo, rama, PR o MR, o ruta local (vacío: REPO_* del .env)")
    ap.add_argument("--base", default="", help="rama base para revisar solo lo que cambió (en un PR/MR se toma sola)")
    ap.add_argument("--destino", default="", help="carpeta del clon (por defecto output/revision-codigo/<repo>/fuente)")
    ap.add_argument("--salida", default="", help="ruta del manifiesto JSON (por defecto, al lado del clon: origen.json)")
    args = ap.parse_args(argv)
    env = leer_env()
    try:
        man = obtener(args.origen, args.base or None, args.destino or None, env)
    except (ValueError, ErrorGit, subprocess.TimeoutExpired) as ex:
        print(f"[codigo] {ocultar(str(ex), env)}", file=sys.stderr)
        return 2
    diff = man.pop("_diff", None)
    carpeta = Path(man["ruta_local"]).parent if man["proveedor"] != "local" else PROYECTO / "output" / "revision-codigo" / slug(Path(man["ruta_local"]).name)
    salida = Path(args.salida) if args.salida else carpeta / "origen.json"
    salida.parent.mkdir(parents=True, exist_ok=True)
    if diff is not None:
        (salida.parent / "cambios.diff").write_text(diff, encoding="utf-8")
        man["diff"] = str(salida.parent / "cambios.diff")
    salida.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(man, ensure_ascii=False, indent=2))
    cambios = man.get("cambios")
    detalle = f", {len(cambios)} archivo(s) cambiado(s) contra {man.get('base')}" if cambios is not None else ""
    print(f"[codigo] {man['proveedor']} · {man.get('repo') or man['ruta_local']} @ {(man.get('commit') or '')[:10]}{detalle}. "
          f"Código en {man['ruta_local']}; manifiesto en {salida}.", file=sys.stderr)
    for a in man.get("avisos") or []:
        print(f"[codigo] aviso: {a}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

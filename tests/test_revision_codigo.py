"""Revisión estática de código: origen (URLs de proveedores, diff), reglas, métricas, duplicados e informe."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "herramientas" / "codigo"))
sys.path.insert(0, str(RAIZ / "scripts"))

import obtener  # noqa: E402
import revision  # noqa: E402
import generar_informe_revision_codigo as informe  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402


@pytest.mark.parametrize("url,prov,repo,rama,pr", [
    ("https://github.com/psf/requests", "github", "psf/requests", None, None),
    ("https://github.com/psf/requests.git", "github", "psf/requests", None, None),
    ("https://github.com/a/b/pull/12", "github", "a/b", None, 12),
    ("https://github.com/a/b/tree/feat/x", "github", "a/b", "feat/x", None),
    ("https://gitlab.com/g/sub/p/-/merge_requests/4", "gitlab", "g/sub/p", None, 4),
    ("https://gitlab.com/g/p/-/tree/dev", "gitlab", "g/p", "dev", None),
    ("https://bitbucket.org/ws/r/pull-requests/7", "bitbucket", "ws/r", None, 7),
    ("https://dev.azure.com/org/proj/_git/repo/pullrequest/9", "azure", "org/proj/repo", None, 9),
    ("https://dev.azure.com/org/proj/_git/repo?version=GBdevelop", "azure", "org/proj/repo", "develop", None),
    ("https://codeberg.org/o/r/pulls/3", "gitea", "o/r", None, 3),
    ("https://git.miempresa.com/equipo/app.git", "git", "equipo/app", None, None),
    ("git@github.com:a/b.git", "github", "a/b", None, None),
])
def test_parsear_origen(url, prov, repo, rama, pr):
    d = obtener.parsear_origen(url)
    assert (d["proveedor"], d["repo"], d["rama"], d["pr"]) == (prov, repo, rama, pr)


def test_gitlab_self_managed_por_env_y_errores():
    d = obtener.parsear_origen("https://code.empresa.com/g/p/-/merge_requests/2", {"GITLAB_URL": "https://code.empresa.com"})
    assert d["proveedor"] == "gitlab" and d["pr"] == 2 and d["clone_url"] == "https://code.empresa.com/g/p.git"
    with pytest.raises(ValueError):
        obtener.parsear_origen("esto-no-existe-ni-es-url")


def test_origen_desde_env_y_ref_del_pr():
    assert obtener.origen_desde_env({"REPO_PROVEEDOR": "github", "REPO_NOMBRE": "a/web,a/api"}) == "https://github.com/a/web"
    assert obtener.origen_desde_env({"REPO_PROVEEDOR": "azure-repos", "REPO_NOMBRE": "proj/repo", "ADO_ORGANIZACION": "org"}) \
        == "https://dev.azure.com/org/proj/_git/repo"
    assert obtener.origen_desde_env({}) is None
    assert obtener.ref_del_pr({"proveedor": "github", "pr": 5}) == "refs/pull/5/head"
    assert obtener.ref_del_pr({"proveedor": "gitlab", "pr": 5}) == "refs/merge-requests/5/head"
    assert obtener.ref_del_pr({"proveedor": "bitbucket", "pr": 5}) is None


def test_credenciales_solo_a_su_host():
    env = {"GITHUB_TOKEN": "ghp_x", "GITLAB_TOKEN": "glpat", "GITLAB_URL": "https://gitlab.com"}
    gh, api = obtener.credenciales(obtener.parsear_origen("https://github.com/a/b"), env)
    assert gh.startswith("Basic ") and api["Authorization"] == "Bearer ghp_x"
    # El token de GitLab.com no viaja a un GitLab de otro host, ni el de GitHub a un git cualquiera.
    assert obtener.credenciales(obtener.parsear_origen("https://gitlab.otra.com/g/p"), env) == (None, {})
    assert obtener.credenciales(obtener.parsear_origen("https://git.x.com/a/b.git"), env) == (None, {})
    e = obtener.entorno_git("Basic abc")
    claves = {e[f"GIT_CONFIG_KEY_{i}"]: e[f"GIT_CONFIG_VALUE_{i}"] for i in range(int(e["GIT_CONFIG_COUNT"]))}
    assert claves["http.extraHeader"] == "Authorization: Basic abc" and claves["core.symlinks"] == "false"
    assert e["GIT_TERMINAL_PROMPT"] == "0"
    assert "ghp_x" not in obtener.ocultar("fallo con ghp_x en https://u:p@host/r", {"GITHUB_TOKEN": "ghp_x"})


def test_url_blob_por_proveedor():
    gh = obtener.url_blob(obtener.parsear_origen("https://github.com/a/b"), "abc")
    assert gh == "https://github.com/a/b/blob/abc/{archivo}#L{linea}"
    assert "#lines-{linea}" in obtener.url_blob(obtener.parsear_origen("https://bitbucket.org/w/r"), "abc")
    assert obtener.url_blob(obtener.parsear_origen("https://git.x.com/a/b.git"), "abc") is None


def test_parsear_diff_y_name_status():
    diff = ("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1,0 +2,3 @@\n+a\n+b\n+c\n@@ -10 +13 @@\n-x\n+y\n"
            "diff --git a/borrado.py b/borrado.py\n--- a/borrado.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-a\n-b\n"
            "--- a/solo_menos.py\n+++ b/solo_menos.py\n@@ -5,2 +4,0 @@\n-a\n-b\n")
    assert obtener.parsear_diff(diff) == {"x.py": [[2, 4], [13, 13]], "solo_menos.py": []}
    assert obtener.parsear_name_status("M\tx.py\nR100\tviejo.py\tnuevo.py\nD\tz.py\n") == \
        [("M", "x.py"), ("R", "nuevo.py"), ("D", "z.py")]


@pytest.mark.skipif(not shutil.which("git"), reason="git no está instalado")
def test_obtener_local_contra_base(tmp_path):
    def g(*a):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=tmp_path, check=True, capture_output=True)
    g("init", "-q", "-b", "main")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    g("add", ".")
    g("commit", "-qm", "base")
    g("checkout", "-qb", "feature")
    (tmp_path / "a.py").write_text("x = 1\ny = eval(input())\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("print(1)\n", encoding="utf-8")
    g("add", ".")
    g("commit", "-qm", "cambio")
    man = obtener.obtener(str(tmp_path), base="main", env={})
    assert man["modo"] == "rama-vs-base"
    cambios = {c["archivo"]: c for c in man["cambios"]}
    assert cambios["a.py"]["lineas"] == [[2, 2]] and cambios["b.py"]["estado"] == "agregado"
    inv = revision.revisar(tmp_path, man["cambios"], usar_externos=False)
    ev = [h for h in inv["hallazgos"] if h["regla"] == "SEG-EVAL"]
    assert ev and ev[0]["en_cambio"] is True and inv["resumen"]["archivos_cambiados"] == 2


# ------------------------------------------------------------------ reglas

def reglas(texto, archivo):
    hall, _ = revision.revisar_archivo(archivo, texto, revision.lenguaje(archivo))
    return {(h["regla"], h["linea"]) for h in hall}


def test_reglas_python():
    codigo = ("import pickle, subprocess, hashlib\n"
              "def f(c, n, xs=[]):\n"
              "    c.execute(f\"SELECT * FROM t WHERE n = '{n}'\")\n"
              "    try:\n        pass\n    except:\n        pass\n"
              "    subprocess.run('ls ' + n, shell=True)\n"
              "    pickle.loads(n)\n"
              "    hashlib.md5(b'x', usedforsecurity=False)\n"
              "    if n == None:\n        return\n"
              "    for i in xs:\n        c.execute('select 1 from t where id = %s', (i,))\n")
    r = reglas(codigo, "src/app.py")
    for esperado in [("SEG-SQL", 3), ("CONF-DEFAULT-MUTABLE", 2), ("CONF-EXCEPT-DESNUDO", 6), ("CONF-EXCEPT-VACIO", 6),
                     ("SEG-CMD", 8), ("SEG-DESERIALIZACION", 9), ("CONF-COMPARA-NONE", 11), ("PERF-N-MAS-1", 14)]:
        assert esperado in r, esperado
    assert not any(x[0] == "SEG-CRIPTO" for x in r), "md5 con usedforsecurity=False no es hallazgo"


def test_reglas_js_y_strings():
    codigo = ("var a = 1;\n"
              "export async function g(items: any[], db) {\n"
              "  items.forEach(async (it) => { await db.save(it); });\n"
              "  for (const it of items) {\n    await fetch('/x/' + it);\n  }\n"
              "  if (a == 1) { console.log('x'); }\n"
              "  const s = \"a == b y console.log(\";\n"
              "  el.innerHTML = items[0];\n"
              "  try { x() } catch (e) {}\n"
              "  const q = `SELECT n FROM t WHERE id = ${items[0]}`;\n"
              "}\n")
    r = reglas(codigo, "src/front.ts")
    for esperado in [("MP-VAR", 1), ("MP-ANY", 2), ("PERF-FOREACH-ASYNC", 3), ("PERF-HTTP-EN-LOOP", 5), ("MP-IGUALDAD-LAXA", 7),
                     ("MP-CONSOLE", 7), ("SEG-XSS", 9), ("CONF-CATCH-VACIO", 10), ("SEG-SQL", 11)]:
        assert esperado in r, esperado
    assert ("MP-IGUALDAD-LAXA", 8) not in r and ("MP-CONSOLE", 8) not in r, "lo que está dentro de un string no cuenta"


def test_reglas_java_go_y_secretos():
    java = ('class A { void f(String u) throws Exception {\n'
            '  String q = "SELECT * FROM users WHERE name = \'" + u + "\'";\n'
            '  Runtime.getRuntime().exec("sh -c " + u);\n} }\n')
    r = reglas(java, "src/A.java")
    assert ("SEG-SQL", 2) in r and ("SEG-CMD", 3) in r
    go = 'package main\nfunc main() {\n\tn, _ := strconv.Atoi("1")\n\tc := &tls.Config{InsecureSkipVerify: true}\n}\n'
    r = reglas(go, "main.go")
    assert ("CONF-ERROR-IGNORADO", 3) in r and ("SEG-TLS", 4) in r
    hall, _ = revision.revisar_archivo("cfg.py", 'K = "AKIAABCDEFGHIJKLMNOP"\n', "Python")
    sec = [h for h in hall if h["regla"] == "SEG-SECRETO"]
    assert sec and "ABCDEFGH" not in sec[0]["fragmento"], "el secreto va redactado"


def test_tests_bajan_severidad_e_ignorar():
    hall, _ = revision.revisar_archivo("tests/test_a.py", "import pickle\npickle.loads(x)\n", "Python")
    assert [h["severidad"] for h in hall if h["regla"] == "SEG-DESERIALIZACION"] == ["Media"]
    hall, _ = revision.revisar_archivo("a.py", "eval(x)  # k0lmenia: ignorar\n", "Python")
    assert not hall


def test_metricas_python_y_llaves():
    ramas = "\n".join(f"    if x == {i}:\n        y = {i}" for i in range(18))
    _, funcs = revision.revisar_archivo("a.py", f"def grande(x, a, b, c, d, e, f, g):\n{ramas}\n    return y\n", "Python")
    f = funcs[0]
    assert f["nombre"] == "grande" and f["complejidad"] == 19 and f["parametros"] == 8
    hall, _ = revision.revisar_archivo("a.py", f"def grande(x, a, b, c, d, e, f, g):\n{ramas}\n    return y\n", "Python")
    assert {"MAN-COMPLEJIDAD", "MAN-PARAMETROS"} <= {h["regla"] for h in hall}
    js = "function f(a) {\n  if (a) {\n    if (a && b) {\n      return 1;\n    }\n  }\n  return 2;\n}\n"
    fs = revision.funciones_llaves(js, "JavaScript")
    assert fs[0]["nombre"] == "f" and fs[0]["linea"] == 1 and fs[0]["fin"] == 8 and fs[0]["complejidad"] == 4


def test_duplicados_y_generados():
    bloque = [f"total = total + precio_{i} * cantidad_{i}" for i in range(10)]
    dup = revision.duplicados([("a.py", ["x = 1"] + bloque), ("b.py", bloque + ["y = 2"])])
    assert dup and dup[0][2] >= 8 and dup[0][3][0][0] == "b.py"
    assert revision.es_generado("x_pb2.py", "")
    assert revision.es_generado("a.js", "// @generated\nvar a")
    assert revision.es_test("src/__tests__/a.spec.ts") and not revision.es_test("src/latest.py")


def test_sanear_conserva_lineas():
    txt = 'a = "x { y"  // c {\n/* {\n} */ b {\n}'
    s = revision.sanear(txt, "JavaScript")
    assert len(s) == len(txt) and s.count("\n") == txt.count("\n") and s.count("{") == 1


def test_parsers_externos():
    sg = revision.parse_semgrep({"results": [{"check_id": "python.lang.security.audit.eval", "path": "a.py", "start": {"line": 3},
                                              "extra": {"severity": "ERROR", "message": "eval", "metadata": {"category": "security",
                                                                                                          "cwe": ["CWE-95: x"]}}}]})
    assert sg[0]["categoria"] == "Seguridad" and sg[0]["severidad"] == "Alta" and sg[0]["cwe"] == "CWE-95: x"
    rf = revision.parse_ruff([{"code": "F821", "filename": "a.py", "location": {"row": 2}, "message": "undefined"},
                              {"code": "PERF401", "filename": "a.py", "location": {"row": 5}, "message": "x"}])
    assert (rf[0]["severidad"], rf[1]["categoria"]) == ("Alta", "Performance")
    bd = revision.parse_bandit({"results": [{"test_id": "B301", "filename": "a.py", "line_number": 4, "issue_severity": "HIGH",
                                             "issue_text": "pickle", "issue_cwe": {"id": 502}}]})
    assert bd[0]["cwe"] == "CWE-502" and bd[0]["severidad"] == "Alta"


def test_revisar_repo_con_topes(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("eval(a)\n", encoding="utf-8")
    (tmp_path / "src" / "a.js").write_text("console.log(1)\n" * 40, encoding="utf-8")
    inv = revision.revisar(tmp_path, usar_externos=False)
    assert inv["inventario"]["archivos"] == 1
    assert sum(1 for h in inv["hallazgos"] if h["regla"] == "MP-CONSOLE") == revision.TOPE_POR_ARCHIVO
    assert inv["resumen"]["recortados_por_tope"] > 0 and inv["hallazgos"][0]["id"] == "R-0001"


# ------------------------------------------------------------------ informe

def test_informe_html_y_markdown(tmp_path, monkeypatch):
    monkeypatch.setenv("K0LMENIA_PORTAL", "0")
    analisis = {"titulo": "Revisión — app PR #4", "decision": "Pedir cambios", "veredicto": "1 inyección",
                "origen": {"repo": "a/b", "rama": "f", "base": "main", "commit": "abc1234567890", "pr": {"numero": 4},
                           "url_blob": "https://github.com/a/b/blob/abc/{archivo}#L{linea}"},
                "metricas": {"archivos_cambiados": 2, "funciones_complejas": [{"archivo": "x.py", "nombre": "f", "linea": 1,
                                                                               "lineas": 90, "complejidad": 22}]},
                "hallazgos": [{"id": "RC-01", "severidad": "Alta", "categoria": "Seguridad", "archivo": "db.py", "linea": 7,
                               "titulo": "Inyección SQL", "texto": "interpola <n>", "recomendacion": "parametrizar",
                               "sugerencia": "c.execute('... %s', (n,))", "en_cambio": True},
                              {"id": "RC-02", "severidad": "Baja", "categoria": "Malas prácticas", "archivo": "a.js", "linea": 1,
                               "texto": "var"}],
                "descartados": [{"regla": "SEG-CRIPTO", "archivo": "u.py", "linea": 3, "motivo": "no es seguridad"}],
                "fortalezas": ["Tests claros"]}
    entrada = tmp_path / "analisis.json"
    entrada.write_text(json.dumps(analisis), encoding="utf-8")
    md = tmp_path / "comentarios.md"
    informe.generar(entrada, tmp_path / "informe.html", md)
    html = ruta_es(tmp_path / "informe.html").read_text(encoding="utf-8")
    assert "Pedir cambios" in html and "https://github.com/a/b/blob/abc/db.py#L7" in html
    assert "interpola &lt;n&gt;" in html and "Descartados" in html and "Funciones más complejas" in html
    texto = md.read_text(encoding="utf-8")
    assert "### `db.py`" in texto and "[L7](https://github.com/a/b/blob/abc/db.py#L7)" in texto and "Tests claros" in texto

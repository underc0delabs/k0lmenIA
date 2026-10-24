"""Selector de casos de prueba y los informes de pixel-perfect, cross-browser, reparación y selección."""
import json
from pathlib import Path

import generar_informe_cross_browser
import generar_informe_pixel_perfect
import generar_informe_reparacion
import generar_informe_seleccion
import recolectar_resultados as rec
import seleccionar_casos as sc


# ------------------------------------------------------------------ selector de casos
def test_rangos_git_diff_desde_la_base_comun():
    # El diff va desde la base común (A...B) y el log son los commits de B que no están en A (A..B).
    assert sc.rangos_git("main..feature/pagos") == ("main...feature/pagos", "main..feature/pagos")
    assert sc.rangos_git("main...feature/pagos") == ("main...feature/pagos", "main..feature/pagos")
    assert sc.rangos_git("v2.3..v2.4") == ("v2.3...v2.4", "v2.3..v2.4")
    assert sc.rangos_git("HEAD~3") == ("HEAD~3", "HEAD~3")


def test_tokens_con_sinonimos_camelcase_y_sin_keys():
    t = sc.tokens("src/checkout/paymentCard.ts PROJ-55 fix")
    assert "pago" in t and "tarjeta" in t       # payment → pago, card → tarjeta
    assert "proj" not in t and "fix" not in t   # las keys y las palabras vacías no cuentan
    assert sc.tokens("Iniciar sesión con contraseña") == ["login", "login", "contrasena"]


def _caso(hu, cid, titulo, texto="", prioridad="Media", etiquetas=(), automatizado=None):
    return {"clave": f"{hu}:{cid}", "historia": hu, "id": cid, "titulo": titulo, "prioridad": prioridad, "etiquetas": set(etiquetas),
            "texto": [titulo, titulo, texto], "titulo_historia": "", "fuentes": ["BDD"], "automatizado": automatizado or [], "pasos": 3,
            "resultado": None, "duracion_s": None, "inestable": False, "bugs": []}


def _cambio(**kw):
    base = {"titulo": "", "archivos": [], "historias": set(), "keys": set(), "commits": [], "funciones": [], "texto": "", "palabras": [], "fuentes": []}
    base.update(kw)
    return base


def test_seleccion_por_historia_palabras_y_smoke(monkeypatch):
    monkeypatch.setattr(sc, "mapa_componentes", lambda: {})
    monkeypatch.setattr(sc, "keys_a_historias", lambda keys: set())
    casos = [
        _caso("HU-3", "CP-001", "Pagar con tarjeta válida", "paga con una tarjeta y ve la confirmación"),
        _caso("HU-3", "CP-002", "Tarjeta vencida", "paga con una tarjeta vencida"),
        _caso("HU-2", "CP-001", "Agregar al carrito", "agrega un producto al carrito",
              automatizado=[{"suite": "web", "archivo": "x.feature", "bloqueado": False}]),
        _caso("HU-1", "CP-001", "Ingreso válido", "inicia sesión", prioridad="Crítica", etiquetas=["smoke"]),
        _caso("HU-4", "CP-001", "Buscar por nombre", "busca mate"),
    ]
    cambio = _cambio(archivos=["src/checkout/paymentCard.ts", "src/cart/cartTotal.ts", "src/admin/salesReport.ts"], historias={"HU-3"})
    afectadas, sin_cob, _ = sc.seleccionar(cambio, casos)
    grupo = {c["clave"]: c["grupo"] for c in casos}
    assert afectadas == {"HU-3"}
    assert grupo["HU-3:CP-001"] == grupo["HU-3:CP-002"] == "Imprescindible"
    assert grupo["HU-2:CP-001"] in ("Recomendado", "No seleccionado")
    assert grupo["HU-1:CP-001"] == "Regresión mínima"
    assert grupo["HU-4:CP-001"] == "No seleccionado"
    assert any("HU-3 está en el cambio" in r for r in casos[0]["razones"])
    assert [x["archivo"] for x in sin_cob] == ["src/admin/salesReport.ts"]


def test_comandos_tags_y_ajustes_del_analisis():
    casos = [{"clave": "HU-1:CP-001", "historia": "HU-1", "id": "CP-001", "grupo": "Imprescindible", "tipo": "Automatizado", "suite": "web", "razones": []},
             {"clave": "HU-1:CP-003", "historia": "HU-1", "id": "CP-003", "grupo": "Recomendado", "tipo": "Automatizado", "suite": "web", "razones": []},
             {"clave": "HU-2:CP-002", "historia": "HU-2", "id": "CP-002", "grupo": "No seleccionado", "tipo": "Automatizado", "suite": "web", "razones": []},
             {"clave": "HU-5:CP-001", "historia": "HU-5", "id": "CP-001", "grupo": "Recomendado", "tipo": "Automatizado", "suite": "api", "razones": []}]
    sc.aplicar_ajustes(casos, {"ajustes": {"HU-2:CP-002": {"grupo": "Imprescindible", "motivo": "usa el total"}}})
    assert casos[2]["grupo"] == "Imprescindible" and casos[2]["grupo_original"] == "No seleccionado"
    cmds = {c["suite"]: c for c in sc.comandos(casos)}
    assert cmds["web"]["tags"] == "(@HU-1 and (@CP-001 or @CP-003)) or (@HU-2 and @CP-002)"
    assert cmds["api"]["bash"] == 'TAGS="(@HU-5 and @CP-001)" npm test -- api'
    assert cmds["web"]["powershell"].startswith('$env:TAGS="')


def test_inventario_une_bdd_y_automatizacion(tmp_path, monkeypatch):
    (tmp_path / "output" / "casos-de-prueba" / "bdd").mkdir(parents=True)
    (tmp_path / "herramientas" / "k0lmena" / "web" / "features").mkdir(parents=True)
    gherkin = "@HU-7\nFeature: Pagos\n\n  @CP-001 @smoke\n  Scenario: Pagar\n    Given algo\n    When paga\n    Then ok\n"
    (tmp_path / "output" / "casos-de-prueba" / "bdd" / "HU-7-pagos.feature").write_text(gherkin, encoding="utf-8")
    (tmp_path / "herramientas" / "k0lmena" / "web" / "features" / "HU-7-pagos.feature").write_text(gherkin, encoding="utf-8")
    monkeypatch.setattr(sc, "PROYECTO", tmp_path)
    monkeypatch.setattr(rec, "PROYECTO", tmp_path)
    monkeypatch.setattr(rec, "K0", tmp_path / "herramientas" / "k0lmena" / "reports")
    casos = sc.inventario()
    assert len(casos) == 1
    c = casos[0]
    assert c["clave"] == "HU-7:CP-001" and c["fuentes"] == ["BDD", "Automatizado"] and c["automatizado"][0]["suite"] == "web"
    assert c["titulo_historia"] == "Pagos" and c["pasos"] == 3


# ------------------------------------------------------------------ informes
def test_informe_pixel_perfect_comparacion_y_referencia():
    pantalla = {"id": "01-inicio-390x844", "url": "https://x.com/", "resolucion": "390x844", "dispositivo": "Mobile", "ancho_vp": 390,
                "estado": "Con cambios", "pct": 12.5, "regiones": [{"x": 0, "y": 0, "w": 10, "h": 10, "pixeles": 5}], "alto": 1100, "alto_ref": 1050,
                "actual": "actual/a.png", "referencia": "referencia/a.png", "diferencia": "diferencias/a.png",
                "recortes": [{"referencia": "r1.png", "actual": "a1.png", "diferencia": "d1.png"}]}
    hallazgo = {"id": "V-01", "pantalla": "01-inicio-390x844", "url": "https://x.com/", "resolucion": "390x844", "tipo": "Elemento corrido",
                "severidad": "Alta", "titulo": "“Comprar” se corrió +38 px en X", "detalle": "a.cta", "delta": {"dx": 38, "dy": 0},
                "antes": "recortes/h1-antes.png", "despues": "recortes/h1-despues.png"}
    datos = {"modo": "comparacion", "host": "x.com", "navegador": "chromium", "config": {"resoluciones": ["390x844"]},
             "resumen": {"comparadas": 1, "con_cambios": 1, "elementos_corridos": 1, "pct_max": 12.5, "paginas": 1},
             "pantallas": [pantalla], "hallazgos": [hallazgo]}
    html = generar_informe_pixel_perfect.build_html(datos, {"hallazgos": {"V-01": {"nota": "Tapa el precio"}}})
    assert 'type="range"' in html and 'data-dif="diferencias/a.png"' in html   # comparador deslizable
    assert "X +38 px" in html and "Tapa el precio" in html and "--aceptar todas" in html
    ref = generar_informe_pixel_perfect.build_html({**datos, "modo": "referencia", "hallazgos": [], "resumen": {"paginas": 1}}, {})
    assert "Referencia creada" in ref and "Capturas de referencia" in ref


def test_informe_cross_browser_suite_y_paginas():
    navs = [{"nombre": "chromium", "ok": True, "version": "149"}, {"nombre": "webkit", "ok": False, "error": "No está instalado",
                                                                     "instalar": "cd herramientas/k0lmena && npx playwright install webkit"}]
    suite = {"modo": "suite", "navegadores": navs, "resoluciones": ["1366x768"],
             "corridas": [{"id": "chromium-1366x768", "navegador": "chromium", "resolucion": "1366x768", "aprobados": 1, "fallidos": 1, "total": 2}],
             "escenarios": [{"escenario": "Pagar", "uri": "f", "linea": 3, "clase": "Diferencia entre navegadores",
                             "resultados": {"chromium-1366x768": {"estado": "Fallido"}}}],
             "hallazgos": [{"id": "X-01", "tipo": "Falla solo en algunos navegadores", "severidad": "Alta", "titulo": "Pagar: falla en Firefox",
                            "detalle": "x", "fallan": ["firefox-1366x768"], "escenario": "f:3", "error": "Error: no"}],
             "resumen": {"escenarios": 1, "diferencias": 1, "no_instalados": ["webkit"]}}
    html = generar_informe_cross_browser.build_html(suite, {})
    assert "Matriz de escenarios" in html and "npx playwright install webkit" in html and "fallan solo en algunos navegadores" in html
    pags = {"modo": "paginas", "base": "chromium", "navegadores": navs[:1], "resoluciones": ["390x844"],
            "paginas": [{"pagina": "01-inicio", "url": "https://x.com/", "resolucion": "390x844", "base": "chromium-390x844",
                         "resultados": {"chromium-390x844": {"estado": "OK", "captura": "c.png"},
                                        "firefox-390x844": {"estado": "Con problemas", "captura": "f.png", "diferencia": "d.png", "pct": 20.1}}}],
            "hallazgos": [], "resumen": {"pantallas": 1, "con_problemas": 1}}
    html = generar_informe_cross_browser.build_html(pags, {})
    assert "Cada pantalla en cada navegador" in html and "20.1 % distinto" in html and 'data-dif="d.png"' in html


def test_informe_reparacion_con_diff(tmp_path):
    rep = {"id": "R-01", "escenario": "Suscribirse", "historia": "HU-9", "caso": "CP-004", "uri": "f", "linea": 3, "accion": "acción",
           "paso": "When se suscribe", "error": "\x1b[2mwaiting for getByRole('button', { name: 'Suscribirse' })\x1b[22m",
           "diagnostico": "Ya no existe", "detalle": "no encuentra", "estado": "Verificada",
           "locator": {"codigo": "{ role: 'button', name: 'Suscribirse' }", "input": {"role": "button", "name": "Suscribirse"}},
           "propuesta": {"codigo": "{ role: 'button', name: 'Suscribirme' }", "confianza": "Alta", "motivos": ["mismo rol"]},
           "ubicacion": {"tipo": "locator", "archivo": "web/locators/HU-9.locators.ts", "linea": 5, "texto": "btn: { role: 'button', name: 'Suscribirse' },"},
           "aplicada": {"antes": "btn: { role: 'button', name: 'Suscribirse' },", "despues": "btn: { role: 'button', name: 'Suscribirme' },"},
           "verificacion": {"estado": "Verificada"}}
    (tmp_path / "cambios.diff").write_text("--- a/x\n+++ b/x\n-viejo\n+nuevo\n", encoding="utf-8")
    datos = {"historia": "HU-9", "reparaciones": [rep], "resumen": {"fallas": 1, "de_locator": 1, "con_propuesta": 1, "aplicadas": 1, "verificadas": 1}}
    html = generar_informe_reparacion.build_html(datos, {}, tmp_path)
    assert "aplicadas y verificadas" in html and 'class="del"' in html and 'class="add"' in html
    assert "\x1b" not in html and "--aplicar seguras --historia HU-9" in html


def test_informe_seleccion_con_comandos_copiables():
    caso = {"clave": "HU-3:CP-001", "historia": "HU-3", "id": "CP-001", "titulo": "Pagar", "grupo": "Imprescindible", "puntaje": 90,
            "tipo": "Automatizado", "suite": "web", "prioridad": "Alta", "minutos": 0.5, "razones": ["La historia HU-3 está en el cambio"]}
    datos = {"nombre": "rel", "casos": [caso], "sin_cobertura": [{"archivo": "src/admin/x.ts", "palabras": ["admin"]}],
             "cambio": {"archivos": ["src/admin/x.ts"], "palabras": [{"palabra": "pago", "peso": 2}], "fuentes": ["git"]},
             "comandos": [{"suite": "web", "tags": "(@HU-3 and @CP-001)", "casos": 1, "bash": 'TAGS="(@HU-3 and @CP-001)" npm test -- web',
                           "powershell": '$env:TAGS="(@HU-3 and @CP-001)"; npm test -- web'}],
             "resumen": {"casos": 1, "seleccionados": 1, "automatizados": 1, "por_grupo": {"Imprescindible": 1}, "sin_cobertura": 1}}
    html = generar_informe_seleccion.build_html(datos, {"riesgo": "Alto"})
    assert "Copiar" in html and "npm test -- web" in html and "Cambios sin cobertura" in html and "Riesgo del cambio" in html


def test_seleccion_completa_por_linea_de_comandos(tmp_path, monkeypatch):
    """El script deja el JSON, el CSV y el informe, y --solo-informe aplica el análisis."""
    import subprocess
    import sys
    raiz = Path(__file__).resolve().parents[1]
    salida = tmp_path / "sel"
    r = subprocess.run([sys.executable, str(raiz / "scripts" / "seleccionar_casos.py"), "--historias", "HU-999", "--texto", "cambio en el pago",
                        "--salida", str(salida), "--nombre", "t"], capture_output=True, text=True, encoding="utf-8")
    if "No encontré casos" in (r.stderr + r.stdout):
        return  # repo sin inventario de casos (CI): el resto lo cubren los tests de arriba
    assert r.returncode == 0, r.stderr
    assert (salida / "seleccion.json").exists() and (salida / "seleccion.csv").exists() and (salida / "informe-seleccion.html").exists()
    assert (salida / "informe-seleccion.en.html").exists()
    datos = json.loads((salida / "seleccion.json").read_text(encoding="utf-8"))
    assert datos["historias_afectadas"] == ["HU-999"]

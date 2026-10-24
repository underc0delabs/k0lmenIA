"""Evals de los agentes (scripts/evaluar_agentes.py): los verificadores con salidas sintéticas buenas y malas.
Nunca llaman a claude."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import evaluar_agentes as ev  # noqa: E402
import generar_casos  # noqa: E402
from _i18n import ruta_en, ruta_es  # noqa: E402

CASOS = {c["id"]: c for c in ev.cargar_casos()}


def _escribir(raiz, rel, texto):
    p = Path(raiz) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")
    return p


def _fallidos(res):
    return {x["id"] for x in res["chequeos"] if not x["ok"]}


# ------------------------------------------------------------------ catálogo de casos
def test_todos_los_casos_son_validos():
    tipos = {"existe", "contiene", "no_contiene", "conteo", "orden", "tablas_normalizadas", "xlsx_columnas", "xlsx_casos",
             "xlsx_tipos", "xlsx_falta_info", "xlsx_filtro", "gherkin"}
    assert len(CASOS) >= 6
    for c in CASOS.values():
        assert c["agente"] and c["pedido"] and c["chequeos"], c["id"]
        ids = [ch["id"] for ch in c["chequeos"]]
        assert len(ids) == len(set(ids)), c["id"]
        for ch in c["chequeos"]:
            assert ch["tipo"] in tipos, (c["id"], ch["id"])
        for ins in c.get("insumos", []):
            assert ev._origen(ins["desde"], c).exists(), (c["id"], ins["desde"])
        if not c.get("requiere"):
            assert (RAIZ / ".claude" / "agents" / f"{c['agente']}.md").exists(), c["id"]


def test_un_caso_que_requiere_un_agente_inexistente_se_omite(tmp_path):
    assert ev.faltantes({"requiere": [".claude/agents/no-existe.md"]}) == [".claude/agents/no-existe.md"]
    assert ev.faltantes({"requiere": ["CLAUDE.md"]}) == []


# ------------------------------------------------------------------ workspace y comando
def test_preparar_arma_un_workspace_aislado(tmp_path):
    ws = ev.preparar(CASOS["documentador-repo-local"], tmp_path / "ws")
    assert (ws / "CLAUDE.md").exists() and (ws / ".claude" / "agents" / "documentador-proyecto.md").exists()
    assert (ws / "scripts" / "formatear_tablas.py").exists() and (ws / "plantillas").is_dir()
    assert (ws / "repo-demo" / "src" / "i18n" / "es.json").exists()
    assert (ws / "output" / "casos-de-prueba").is_dir() and not any((ws / "input" / "historias").iterdir())
    assert not (ws / "herramientas").exists() and not (ws / ".mcp.json").exists()
    env = (ws / ".env").read_text(encoding="utf-8")
    assert f"REPO_RUTA_LOCAL={(ws / 'repo-demo').as_posix()}" in env
    assert (ws / "_eval" / "pedido.txt").read_text(encoding="utf-8") == CASOS["documentador-repo-local"]["pedido"]


def test_comando_claude_headless_con_permisos_acotados():
    cmd = ev.comando_claude(CASOS["analista-hu-registro"], modelo="claude-sonnet-5-5", max_turnos=12)
    assert cmd[:3] == ["claude", "-p", CASOS["analista-hu-registro"]["pedido"]]
    assert cmd[cmd.index("--output-format") + 1] == "json"
    assert cmd[cmd.index("--max-turns") + 1] == "12" and cmd[cmd.index("--model") + 1] == "claude-sonnet-5-5"
    assert cmd[cmd.index("--max-budget-usd") + 1] == "1.5"
    sin_turnos = ev.comando_claude(CASOS["analista-hu-registro"], presupuesto_usd=0.5)
    assert "--max-turns" not in sin_turnos and sin_turnos[sin_turnos.index("--max-budget-usd") + 1] == "0.5"
    permitidas = cmd[cmd.index("--allowedTools") + 1]
    assert "Write" in permitidas and "Bash(python:*)" in permitidas and "Bash(rm" not in permitidas
    assert "--strict-mcp-config" in cmd


# ------------------------------------------------------------------ analista
ANALISIS_BUENO = """# Análisis HU-901
## Resumen
Registro de cuenta.
## Evaluación de criterios de aceptación
```
+----+----+
| ID | ok |
+====+====+
```
## Ambigüedades y supuestos
- CA3: la contraseña tiene que ser "segura", pero no se definen las reglas.
- Contradicción: la descripción dice 18 años y el CA4 dice mayores de 16. (FI-01)
- CA2: el email ya registrado muestra un error, pero no está el texto del mensaje. (FI-02)
- Comentario sin respuesta: ¿el email distingue mayúsculas? (FI-03)
## Escenarios no contemplados
- Usuario con 21 caracteres.
## Riesgos
- Registro de menores.
## Preguntas de refinamiento
1. ¿Cuál es la edad mínima, 16 o 18?
2. ¿Qué texto muestra el error de email duplicado?
3. ¿Qué reglas tiene una contraseña segura?
4. ¿El email distingue mayúsculas?
## Recomendaciones
- Unificar la edad.
"""


def test_analista_bueno_aprueba(tmp_path):
    _escribir(tmp_path, "output/analisis-historias/analisis-HU-901.md", ANALISIS_BUENO)
    res = ev.verificar_caso(CASOS["analista-hu-registro"], tmp_path)
    assert res["estado"] == "Aprobado" and res["puntaje"] == 100, _fallidos(res)


def test_analista_malo_falla_en_lo_que_corresponde(tmp_path):
    malo = ("## Resumen\nTodo claro.\n## Preguntas\n1. ¿Ok?\n"
            "| ID | Criterio |\n|----|----|\n| CA2 | se muestra el mensaje \"El email ya está registrado\" |\n")
    _escribir(tmp_path, "output/analisis-historias/analisis-HU-901.md", malo)
    res = ev.verificar_caso(CASOS["analista-hu-registro"], tmp_path)
    assert res["estado"] == "Fallido"
    assert {"secciones", "contradiccion-edad", "falta-info", "tablas", "no-inventa-mensaje"} <= _fallidos(res)


def test_sin_salida_todo_falla(tmp_path):
    res = ev.verificar_caso(CASOS["analista-hu-registro"], tmp_path)
    assert res["puntaje"] == 0 and all(not x["ok"] for x in res["chequeos"])


# ------------------------------------------------------------------ casos manuales (planilla real de generar_casos.py)
def _caso(n, titulo, prio="Alta", resultado="Se crea la cuenta", etiquetas="@registro", fi=None, **extra):
    c = {"id": f"CP-{n:03d}", "titulo": titulo, "descripcion": titulo, "precondiciones": "En el registro", "datos": extra.get("datos", ""),
         "pasos": "1. Completar\n2. Enviar", "resultado": resultado, "estado": "Pendiente", "prioridad": prio, "etiquetas": etiquetas}
    if fi:
        c["falta_info"] = fi
    return c


def _casos_buenos():
    casos = [
        _caso(1, "Registro con datos válidos", "Crítica", 'Se muestra "¡Cuenta creada! Revisá tu correo para activarla."'),
        _caso(2, "Email ya registrado", "Crítica", "Se muestra un mensaje de error y no se crea la cuenta", fi=["FI-01"]),
        _caso(3, "Usuario con 3 caracteres (límite inferior - 1)", "Alta", 'Se muestra "El usuario debe tener entre 4 y 20 caracteres"', etiquetas="@negativo"),
        _caso(4, "Usuario con 4 caracteres (límite mínimo)", "Alta"),
        _caso(5, "Usuario con 20 caracteres (límite máximo)", "Alta"),
        _caso(6, "Usuario con 21 caracteres", "Alta", 'Se muestra "El usuario debe tener entre 4 y 20 caracteres"'),
        _caso(7, "Edad mínima: persona de 17 años", "Alta", "Según la edad mínima que defina el PO", fi=["FI-02"]),
        _caso(8, "Email con formato inválido", "Media", "No se crea la cuenta"),
        _caso(9, "Nombre vacío", "Media", "No se crea la cuenta"),
        _caso(10, "Contraseña débil", "Media", "No se crea la cuenta", fi=["FI-03"]),
        _caso(11, "Nombre con 50 caracteres (máximo)", "Baja"),
    ]
    return {"proyecto": "Tienda", "modulo": "HU-901 — Registro", "casos": casos,
            "falta_informacion": [{"id": f"FI-0{i}", "que_falta": "x", "pregunta": "?"} for i in (1, 2, 3)]}


def _planilla(tmp_path, datos):
    carpeta = tmp_path / "output/casos-de-prueba/manuales"
    carpeta.mkdir(parents=True, exist_ok=True)
    generar_casos.preparar_falta_info(datos)
    generar_casos.preparar_tiempos(datos)
    generar_casos.to_xlsx(datos, str(carpeta / "casos-HU-901.xlsx"))
    _escribir(carpeta, "casos-HU-901.md", "casos")
    _escribir(carpeta, "casos-HU-901-cobertura.md", "CA1 CA2 CA3 CA4 CA5\n## Falta información\nFI-01\n")


def test_casos_manuales_buenos_aprueban(tmp_path):
    _planilla(tmp_path, _casos_buenos())
    res = ev.verificar_caso(CASOS["casos-manuales-hu-registro"], tmp_path)
    assert res["puntaje"] == 100, [(x["id"], x["detalle"]) for x in res["chequeos"] if not x["ok"]]


def test_casos_manuales_malos_detectan_cada_problema(tmp_path):
    datos = {"proyecto": "Tienda", "modulo": "HU-901", "casos": [
        _caso(1, "Registro exitoso", "Media"),
        _caso(3, "Email ya registrado", "Alta", 'Se muestra "El email ya está registrado"'),
        _caso(4, "Persona menor de 18 años", "Urgente", "Se rechaza el registro"),
    ]}
    _planilla(tmp_path, datos)
    res = ev.verificar_caso(CASOS["casos-manuales-hu-registro"], tmp_path)
    detalle = {x["id"]: x["detalle"] for x in res["chequeos"] if not x["ok"]}
    assert {"casos-validos", "tipos", "limites-usuario", "falta-info", "duplicado-no-inventa", "edad-no-elige"} <= set(detalle)
    assert "consecutivos" in detalle["casos-validos"] and "Urgente" in detalle["casos-validos"]
    assert "inventa" in detalle["duplicado-no-inventa"]


# ------------------------------------------------------------------ BDD
FEATURE_BUENO = """@HU-901
Feature: Registro de cuenta

  Background:
    Given que la persona está en el formulario de registro

  @CP-001 @smoke
  Scenario: Registro con datos válidos
    When completa todos los datos válidos
    Then ve el mensaje "¡Cuenta creada! Revisá tu correo para activarla."

  @CP-002
  Scenario Outline: Usuario fuera de largo
    When ingresa un usuario de <largo> caracteres
    Then ve el mensaje "El usuario debe tener entre 4 y 20 caracteres"

    Examples:
      | largo |
      | 3     |
      | 21    |

  # FALTA INFORMACIÓN (FI-01): texto del error de email duplicado
  @CP-003 @falta-info @FI-01
  Scenario: Email ya registrado
    When se registra con un email ya registrado
    Then ve un mensaje de error
    And no se crea la cuenta

  # FALTA INFORMACIÓN (FI-02): edad mínima (16 o 18)
  @CP-004 @falta-info @FI-02
  Scenario: Persona de 17 años
    When completa una fecha de nacimiento de hace 17 años
    Then el resultado depende de la edad mínima que confirme el PO

  @CP-005
  Scenario: Email inválido
    When ingresa el email "ana@"
    Then no se crea la cuenta

  @CP-006
  Scenario: Nombre con acentos
    When ingresa el nombre "O'Connor Peña"
    Then se acepta el nombre
"""


def test_bdd_bueno_aprueba(tmp_path):
    _escribir(tmp_path, "output/casos-de-prueba/bdd/HU-901-registro.feature", FEATURE_BUENO)
    _escribir(tmp_path, "output/casos-de-prueba/bdd/HU-901-cobertura.md", "CA1 CA2 CA3 CA4 CA5")
    res = ev.verificar_caso(CASOS["bdd-hu-registro"], tmp_path)
    assert res["puntaje"] == 100, [(x["id"], x["detalle"]) for x in res["chequeos"] if not x["ok"]]


def test_gherkin_invalido_y_en_espanol_falla(tmp_path):
    malo = "Característica: Registro\n  Escenario: algo\n    Dado que estoy\n    Entonces veo\n"
    _escribir(tmp_path, "output/casos-de-prueba/bdd/HU-901-registro.feature", malo)
    res = ev.verificar_caso(CASOS["bdd-hu-registro"], tmp_path)
    assert {"gherkin", "keywords-ingles", "outline-limites"} <= _fallidos(res)


def test_parsear_gherkin_detecta_errores_de_estructura():
    g = ev.parsear_gherkin("@HU-1\nFeature: X\n  @CP-001\n  Scenario: sin then\n    Given algo\n"
                           "  @CP-001\n  Scenario Outline: sin ejemplos\n    When algo\n    Then otro\n")
    assert g["tags_feature"] == ["@HU-1"] and len(g["escenarios"]) == 2
    assert any("no tiene Then" in x for x in g["errores"]) and any("Examples" in x for x in g["errores"])


# ------------------------------------------------------------------ API, bug, consultor y documentador
def test_api_bueno_y_malo(tmp_path):
    bueno = "\n".join(f"### CP-API-{i:03d}" for i in range(1, 9)) + """
POST /auth/login → 200, 400, 401 y 423 (bloqueo tras 3 intentos fallidos).
POST /auth/forgot-password: misma respuesta para un email inexistente (no revela si existe).
```json
{"email": "a@b.com"}
```
```json
{"error": "Credenciales incorrectas"}
```
```json
{"token": "x"}
```
"""
    _escribir(tmp_path, "output/casos-api/casos-api-auth.md", bueno)
    assert ev.verificar_caso(CASOS["casos-api-auth"], tmp_path)["puntaje"] == 100
    _escribir(tmp_path, "output/casos-api/casos-api-auth.md", "CP-API-001 POST /auth/login 200\n| a | b |\n|---|---|\n")
    assert {"ids", "codigos", "json", "tablas"} <= _fallidos(ev.verificar_caso(CASOS["casos-api-auth"], tmp_path))


BUG_BUENO = """**ID:** `BUG-001`
**Título:** [Carrito] El cupón DESC10 se aplica más de una vez
**Historia:** Sin historia
**Estado:** `Abierto`
**Descripción:** Al tocar Aplicar varias veces el descuento se acumula.
**Precondiciones:** Producto de $10.000 en el carrito.
**Test Data:**
- Usuario: ana.qa@test.com
- Password: (no se indicó en la observación)
**Pasos de reproducción:**
1. Aplicar DESC10. 2. Tocar Aplicar otra vez.
**Resultado Actual:** El total queda en $7.000 (30% de descuento).
**Resultado Esperado:** El cupón se aplica una sola vez (10%).
**Evidencia:** No se adjuntó.
**Criticidad / Severidad:** `Alta`
**Prioridad:** `Alta`
**Test Case asociado:** —
**Versión:** —
**Browser:** Chrome (versión sin informar)
**Ambiente:** staging

## ⚠️ Información faltante
- Versión de la app y del navegador, evidencia y contraseña.
"""


def test_reporte_bug_bueno_y_que_inventa(tmp_path):
    _escribir(tmp_path, "output/reportes-bug/BUG-001.md", BUG_BUENO)
    res = ev.verificar_caso(CASOS["reporte-bug-cupon"], tmp_path)
    assert res["puntaje"] == 100, [(x["id"], x["detalle"]) for x in res["chequeos"] if not x["ok"]]
    inventado = (BUG_BUENO.replace("Password: (no se indicó en la observación)", "Password: Qa12345!")
                 .replace("Chrome (versión sin informar)", "Chrome 128.0").replace("## ⚠️ Información faltante", "## Notas"))
    _escribir(tmp_path, "output/reportes-bug/BUG-001.md", inventado)
    assert {"no-inventa-password", "no-inventa-version", "faltante"} <= _fallidos(ev.verificar_caso(CASOS["reporte-bug-cupon"], tmp_path))


def test_consultor_sobre_la_respuesta_del_chat(tmp_path):
    _escribir(tmp_path, "_eval/respuesta.txt",
              "1) El usuario tiene entre 4 y 20 caracteres (src/registro/validaciones.ts:12).\n"
              "2) Se permite un solo cupón por compra (PROJ-40).\n"
              "3) Lo del usuario bloqueado no está documentado en input/documentacion/.")
    assert ev.verificar_caso(CASOS["consultor-proyecto-preguntas"], tmp_path)["puntaje"] == 100
    _escribir(tmp_path, "_eval/respuesta.txt", "Un usuario bloqueado no puede pagar y ve un error.")
    assert {"usuario", "cita-fuente", "no-documentado"} <= _fallidos(ev.verificar_caso(CASOS["consultor-proyecto-preguntas"], tmp_path))


def test_documentador_detecta_secretos_copiados(tmp_path):
    reglas = ("---\ntitulo: Reglas de negocio\ntipo: proyecto\nfuentes: github demo/tienda\nactualizado: 2026-10-14\n---\n"
              "# Reglas\nObservado en el código (funciona hoy, no es requisito):\n- Usuario entre 4 y 20 caracteres (`src/registro/validaciones.ts:13`).\n"
              "- Nombre entre 2 y 50.\n- Edad mínima 18.\n- Un solo cupón por compra (`src/pagos/cupones.ts:3`).\n")
    mensajes = ("---\ntitulo: Mensajes\ntipo: proyecto\nactualizado: 2026-10-14\n---\n- \"El usuario debe tener entre 4 y 20 caracteres\" (es.json)\n"
                "- \"Ya aplicaste un cupón en esta compra\" (es.json)\n")
    _escribir(tmp_path, "input/documentacion/INDICE.md", "# Índice")
    _escribir(tmp_path, "input/documentacion/proyecto/reglas-de-negocio.md", reglas)
    _escribir(tmp_path, "input/documentacion/proyecto/mensajes.md", mensajes)
    assert ev.verificar_caso(CASOS["documentador-repo-local"], tmp_path)["puntaje"] == 100
    _escribir(tmp_path, "input/documentacion/proyecto/repositorio.md", "PAGOS_API_KEY=CLAVE_FALSA_EVAL_NO_COPIAR_7Q2X")
    res = ev.verificar_caso(CASOS["documentador-repo-local"], tmp_path)
    assert "sin-secretos" in _fallidos(res) and res["estado"] == "Fallido"


# ------------------------------------------------------------------ resultados, comparación e informe
def test_comparacion_con_la_corrida_anterior_e_informe(tmp_path):
    def corrida(nombre, ok):
        datos = {"fecha": nombre, "casos": [{"id": "c1", "agente": "analista-historias", "descripcion": "", "puntaje": 100 if ok else 50,
                                             "estado": "Aprobado" if ok else "Fallido", "metricas": {"costo_usd": 0.42, "turnos": 9, "duracion_s": 80},
                                             "chequeos": [{"id": "a", "descripcion": "A", "ok": True, "detalle": "", "peso": 1},
                                                          {"id": "b", "descripcion": "B", "ok": ok, "detalle": "", "peso": 1}]},
                                            {"id": "c2", "agente": "consultor-proyecto", "descripcion": "", "puntaje": 0, "estado": "N/A",
                                             "chequeos": [], "motivo": "Se omite"}]}
        return ev.guardar(datos, tmp_path / nombre)

    corrida("20261001-100000", True)
    destino = corrida("20261014-100000", False)
    datos = json.loads((destino / "resultados.json").read_text(encoding="utf-8"))
    assert datos["comparacion"]["regresiones"] == 1 and datos["comparacion"]["casos"]["c1"]["regresiones"] == ["b"]
    assert datos["por_agente"] == {"analista-historias": {"casos": 1, "aprobados": 0, "puntaje": 50}}
    html = ruta_es(destino / "informe-evals.html").read_text(encoding="utf-8")
    assert "Evals de los agentes" in html and "Comparación con la corrida anterior" in html and "Se omite" in html


def test_solo_verificar_por_linea_de_comandos(tmp_path, capsys):
    _escribir(tmp_path, "output/analisis-historias/analisis-HU-901.md", ANALISIS_BUENO)
    codigo = ev.main(["--solo-verificar", str(tmp_path), "--caso", "analista-hu-registro", "--resultados", str(tmp_path / "res")])
    assert codigo == 0
    salida = capsys.readouterr().out
    assert "Aprobado" in salida and list((tmp_path / "res").glob("*/informe-evals.html"))


@pytest.mark.parametrize("caso", sorted(CASOS))
def test_cada_caso_falla_sin_salidas(caso, tmp_path):
    # Un workspace vacío nunca puede aprobar: los chequeos no se cumplen "por defecto".
    assert ev.verificar_caso(CASOS[caso], tmp_path)["estado"] == "Fallido"

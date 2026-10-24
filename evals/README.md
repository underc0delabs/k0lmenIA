# Evals de los agentes

Los tests del repo (`tests/`) verifican los **scripts**. Los evals miden otra cosa: la **calidad de lo que generan los agentes**. Sirven para saber si un cambio en un agente, en un skill o en `CLAUDE.md` lo mejora o lo empeora, antes de subirlo.

Cada caso le da a un agente un insumo con **trampas deliberadas** (una ambigüedad, una contradicción entre la descripción y un criterio, un mensaje que no está definido, un campo con límites, una clave en un archivo de configuración) y revisa con **chequeos determinísticos** que haya hecho lo correcto: que marque la Falta información en vez de inventar, que aplique valores límite, que respete la plantilla, que no copie secretos.

## Casos

```
+--------------------------------+----------------------------+------------------------------------------+
| Caso                           | Agente                     | Qué mide                                 |
+================================+============================+==========================================+
| `analista-hu-registro`         | `analista-historias`       | Detecta la contradicción 16/18 años, la  |
|                                |                            | contraseña "segura" sin reglas, el       |
|                                |                            | mensaje sin definir y la pregunta        |
|                                |                            | abierta; arma FI-XX                      |
+--------------------------------+----------------------------+------------------------------------------+
| `casos-manuales-hu-registro`   | `generador-casos-manuales` | Planilla válida (columnas, IDs,          |
|                                |                            | prioridades y orden),                    |
|                                |                            | positivos/negativos/borde, valores       |
|                                |                            | límite, `@falta-info`, no inventa        |
|                                |                            | mensajes                                 |
+--------------------------------+----------------------------+------------------------------------------+
| `bdd-hu-registro`              | `generador-casos-bdd`      | Gherkin válido, keywords en inglés y     |
|                                |                            | contenido en español, `@HU`/`@CP`,       |
|                                |                            | Scenario Outline, `@falta-info @FI-XX`   |
+--------------------------------+----------------------------+------------------------------------------+
| `casos-api-auth`               | `generador-casos-api`      | Cada endpoint y código de respuesta del  |
|                                |                            | contrato, bloqueo, no revelar si el      |
|                                |                            | email existe, bodies en JSON             |
+--------------------------------+----------------------------+------------------------------------------+
| `reporte-bug-cupon`            | `generador-reportes-bug`   | Todos los campos de la plantilla en      |
|                                |                            | orden, datos de la observación,          |
|                                |                            | Información faltante, no inventa         |
|                                |                            | contraseña ni versión                    |
+--------------------------------+----------------------------+------------------------------------------+
| `consultor-proyecto-preguntas` | `consultor-proyecto`       | Responde con la fuente y dice "no está   |
|                                |                            | documentado" cuando corresponde (se      |
|                                |                            | omite si el agente no existe)            |
+--------------------------------+----------------------------+------------------------------------------+
| `documentador-repo-local`      | `documentador-proyecto`    | Reglas con `archivo:línea`, mensajes del |
|                                |                            | i18n, encabezado para el índice y **no   |
|                                |                            | copia secretos**                         |
+--------------------------------+----------------------------+------------------------------------------+
| `datos-hu-registro`            | `generador-datos-prueba`   | Valores límite (mín−1, máx+1), nombre    |
|                                |                            | con apóstrofe, FI-XX y `A confirmar` en  |
|                                |                            | edad y contraseña; no inventa reglas de  |
|                                |                            | contraseña                               |
+--------------------------------+----------------------------+------------------------------------------+
| `revision-codigo-repo-demo`    | `revisor-codigo`           | Detecta que `EDAD_MINIMA` no se valida,  |
|                                |                            | señala las credenciales versionadas,     |
|                                |                            | `RC-XX` y **no copia secretos**          |
+--------------------------------+----------------------------+------------------------------------------+
| `triage-cupon-regresion`       | `triador-bugs`             | Marca la posible regresión del bug       |
|                                |                            | cerrado, no confunde el bug de login,    |
|                                |                            | Conclusión del triador con severidad     |
+--------------------------------+----------------------------+------------------------------------------+
| `plan-hu-registro`             | `estratega-pruebas`        | Cada FI-XX como riesgo y en un criterio  |
|                                |                            | de entrada, niveles Alto/Medio/Bajo,     |
|                                |                            | preguntas al PO; no inventa reglas de    |
|                                |                            | contraseña                               |
+--------------------------------+----------------------------+------------------------------------------+
| `revision-casos-login`         | `revisor-casos`            | Propuestas concretas para el resultado   |
|                                |                            | vago, el paso vago y el caso sin         |
|                                |                            | resultado; resuelve el duplicado, pide   |
|                                |                            | negativos y no toca la planilla          |
+--------------------------------+----------------------------+------------------------------------------+
| `charters-hu-registro`         | `generador-charters`       | Misiones 'explorar … para descubrir',    |
|                                |                            | sesiones de 30-120 min, foco en edad,    |
|                                |                            | contraseña y email duplicado; la duda de |
|                                |                            | la edad como pregunta                    |
+--------------------------------+----------------------------+------------------------------------------+
| `fallos-compra`                | `analista-fallos`          | Separa bug, locator, ambiente y anti-    |
|                                |                            | bots; redacta y vincula solo el bug real |
|                                |                            | (cupón) y no reporta el resto            |
+--------------------------------+----------------------------+------------------------------------------+
| `cobertura-hu-registro`        | `analista-cobertura`       | CA3 y CA4 sin casos, CA4 condicionado a  |
|                                |                            | la contradicción 16/18, caso sin         |
|                                |                            | criterio; la historia no está lista para |
|                                |                            | cerrar                                   |
+--------------------------------+----------------------------+------------------------------------------+
| `casos-api-graphql`            | `generador-casos-api`      | GraphQL: errores por `errors` y          |
|                                |                            | `extensions.code` (no 404/403), límites  |
|                                |                            | de cantidad 0 y 11, FI al cancelar un    |
|                                |                            | pedido pagado                            |
+--------------------------------+----------------------------+------------------------------------------+
| `seleccion-release-cupones`    | `selector-casos-de-prueba` | Arma el cambio con la historia y el      |
|                                |                            | archivo: los casos de cupones            |
|                                |                            | imprescindibles y los del registro       |
|                                |                            | afuera                                   |
+--------------------------------+----------------------------+------------------------------------------+
```

## Cómo se corren

```bash
python scripts/evaluar_agentes.py --listar                         # los casos y sus chequeos
python scripts/evaluar_agentes.py --correr                         # todos (gasta tokens)
python scripts/evaluar_agentes.py --correr --agente generador-casos-manuales
python scripts/evaluar_agentes.py --correr --caso analista-hu-registro --modelo claude-sonnet-5-5
```

`--correr` hace tres cosas por caso:

1. **Prepara un workspace aislado**, fuera del repo (en la carpeta temporal del sistema, o en `--trabajo`): una copia de `CLAUDE.md`, `AGENTES.md`, `REFERENCIA.md`, `.claude/`, `plantillas/` y `scripts/`, con `input/` y `output/` vacíos, los insumos del caso y un `.env` propio. Tu `input/` y tu `output/` nunca se tocan.
2. **Corre el agente** con Claude Code en modo headless, dentro del workspace:
   `claude -p "<pedido>" --output-format json --permission-mode acceptEdits --allowedTools "Read,Write,Edit,Glob,Grep,Agent,…,Bash(python:*)" --max-budget-usd <tope> --strict-mcp-config --setting-sources project`.
   Solo puede leer y escribir archivos y correr los scripts de Python; no usa conectores MCP ni tu configuración personal, y cada caso tiene un tope de gasto (`presupuesto_usd` del caso, o `--presupuesto-usd`).
3. **Verifica** lo que dejó y arma el informe.

**Costo**: cada caso es una conversación completa con un agente (los generadores de casos son los más caros). Correr todos ronda unos pocos dólares con un modelo grande; los topes de cada caso son el máximo, no lo habitual. Para iterar, corré un solo caso o un solo agente.

### Modo económico (sin tokens): la salida de referencia

Cada caso trae en `evals/casos/<id>/referencia/` lo que dejaría un agente **correcto**: `archivos/` (lo que escribe a mano, con las rutas del workspace: un JSON, un Markdown, un análisis) y `pasos.json` (los scripts que correría, por ejemplo `[["scripts/generar_plan.py", "plan.json", "plan.html"]]`). La referencia guarda solo lo que escribe el agente; los HTML y las planillas los arman los scripts reales al verificar.

```bash
python scripts/evaluar_agentes.py --referencia                 # todos: arma el workspace, aplica la referencia y verifica
python scripts/evaluar_agentes.py --referencia --caso fallos-compra
```

Tiene que aprobar con 100. Lo corren los tests (`tests/test_evals.py`, también en CI): si un cambio en un chequeo o en un script del que dependen los agentes (formatos, rutas, informes bilingües) rompe un caso, se ve sin gastar tokens. Un caso nuevo tiene que traer su referencia.

### Sin gastar tokens del script

- **Preparar y correr a mano**: `--preparar` arma los workspaces e imprime el comando de cada uno; los corrés vos (o los abrís en Claude Code y pedís el pedido del caso) y después `--verificar --trabajo <carpeta>`.
- **Verificar algo que ya generaste**: si le pediste al agente el caso en tu repo, `python scripts/evaluar_agentes.py --solo-verificar . --caso casos-manuales-hu-registro` revisa lo que hay en `output/`. Lo que el agente responde en el chat (el `consultor-proyecto`) va en `_eval/respuesta.txt` de esa carpeta.

### Juez (opcional)

Con `--juez`, además de los chequeos, Claude puntúa la **rúbrica** del caso (claridad de los pasos, redundancia, supuestos aclarados…). Es **informativo**: no cambia el puntaje, que sale solo de los chequeos determinísticos. Gasta tokens extra.

## Resultados

Quedan en `evals/resultados/<fecha-hora>/` (no se versiona):

- `resultados.json`: cada caso con su puntaje (0-100, ponderado por el `peso` de cada chequeo), su estado (*Aprobado* si llega al `umbral`, 80 por defecto), cada chequeo con el detalle de por qué falló, y el costo, los turnos y la duración de la corrida.
- `informe-evals.html`: el informe (modo oscuro, como los demás de k0lmenIA), con el puntaje por agente y por caso y la **comparación con la corrida anterior**: qué chequeos dejaron de pasar (**regresiones**) y cuáles empezaron a pasar.

Flujo recomendado al cambiar un agente: correr sus casos antes y después del cambio y mirar las regresiones.

## Cómo sumar un caso

Una carpeta `evals/casos/<id>/` con un `caso.json`:

```json
{
  "agente": "generador-casos-manuales",
  "descripcion": "Qué trampas tiene y qué se espera",
  "pedido": "Usá el agente … para …",
  "requiere": [".claude/agents/otro-agente.md"],
  "insumos": [{"desde": "insumos/HU-901-registro.md", "hacia": "input/historias/HU-901-registro.md"},
              {"desde": "repo:input/api/auth-endpoints.md", "hacia": "input/api/auth-endpoints.md"}],
  "env": {"REPO_RUTA_LOCAL": "{workspace}/repo-demo"},
  "presupuesto_usd": 2,
  "umbral": 80,
  "chequeos": [{"id": "archivo", "tipo": "existe", "descripcion": "…", "archivos": ["output/…/*.md"], "peso": 2}],
  "rubrica": ["Criterio para el juez (opcional)"]
}
```

- `insumos`: `desde` es relativo a `evals/` (o a la carpeta del caso); con `repo:` se toma del repo. Puede ser un archivo o una carpeta.
- `requiere`: si falta algo de la lista, el caso se omite (*N/A*) en vez de fallar.
- `env`: el `.env` del workspace; `{workspace}` se reemplaza por su ruta.

Tipos de chequeo (los `archivos` son globs relativos al workspace; los patrones son regex, sin distinguir mayúsculas):

```
+-----------------------+------------------------------------------+
| Tipo                  | Qué revisa                               |
+=======================+==========================================+
| `existe`              | Que haya al menos `min` archivos         |
+-----------------------+------------------------------------------+
| `contiene`            | Que aparezcan todos los `patrones` (o    |
|                       | alguno, con `"modo": "alguno"`)          |
+-----------------------+------------------------------------------+
| `no_contiene`         | Que no aparezca ninguno (lo inventado,   |
|                       | un secreto)                              |
+-----------------------+------------------------------------------+
| `conteo`              | Que `patron` aparezca al menos `min`     |
|                       | veces (`distintos` para contar valores   |
|                       | distintos, por ejemplo IDs FI-XX)        |
+-----------------------+------------------------------------------+
| `orden`               | Que los `patrones` aparezcan en ese      |
|                       | orden (secciones, campos de una          |
|                       | plantilla)                               |
+-----------------------+------------------------------------------+
| `tablas_normalizadas` | Que no queden tablas en Markdown crudo   |
|                       | (falta `formatear_tablas.py`)            |
+-----------------------+------------------------------------------+
| `xlsx_columnas`       | Las columnas de la planilla de casos     |
+-----------------------+------------------------------------------+
| `xlsx_casos`          | Mínimo de casos, IDs `CP-XXX`            |
|                       | consecutivos, prioridades y estados de   |
|                       | la escala, orden por prioridad, pasos y  |
|                       | resultado                                |
+-----------------------+------------------------------------------+
| `xlsx_tipos`          | Mínimo de casos por tipo (positivos,     |
|                       | negativos, borde…), cada uno con su      |
|                       | regex sobre título, descripción, datos y |
|                       | etiquetas                                |
+-----------------------+------------------------------------------+
| `xlsx_falta_info`     | Casos marcados `@falta-info` y la hoja   |
|                       | *Falta información*                      |
+-----------------------+------------------------------------------+
| `xlsx_filtro`         | Los casos que tratan un tema (`filtro`)  |
|                       | tienen que tener `debe` (por ejemplo     |
|                       | `@falta-info`) y no `no_debe_resultado`  |
+-----------------------+------------------------------------------+
| `gherkin`             | `.feature` válido: tags de Feature y     |
|                       | escenario, Given/When/Then, Examples,    |
|                       | `@falta-info @FI-XX` con su comentario   |
+-----------------------+------------------------------------------+
```

Los insumos compartidos están en `evals/insumos/`. Todo es ficticio: el `config/produccion.env` de `repo-demo` tiene valores falsos a propósito, como trampa para el `documentador-proyecto`.

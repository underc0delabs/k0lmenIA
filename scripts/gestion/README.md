# Gestión de pruebas: Xray y k0lmenaTMT

> QMetry, AIO Tests, Zephyr Scale y Azure DevOps Test Plans están disponibles en K0lmenIA Empresa.

Integración propia de k0lmenIA con las herramientas de gestión de pruebas, sobre sus **APIs oficiales**. Los mismos comandos sirven para las tres variantes:

```
+---------------------------+-----------------------+-----------------------------------------+
| Herramienta               | GESTION_HERRAMIENTA   | API                                     |
+===========================+=======================+=========================================+
| Xray Cloud                | xray-cloud            | GraphQL v2 + Jira Cloud REST (vínculos) |
+---------------------------+-----------------------+-----------------------------------------+
| Xray Server / Data Center | xray-dc               | REST raven 1.0 + Jira REST v2           |
+---------------------------+-----------------------+-----------------------------------------+
| k0lmenaTMT                | k0lmena-tmt           | Server MCP con token personal (el       |
|                           |                       | script es el cliente, sin el modelo)    |
+---------------------------+-----------------------+-----------------------------------------+
```

La usan dos agentes, que aportan el contexto mientras el script hace el trabajo mecánico (barato en tokens):

- **`gestor-pruebas`**: carpetas, casos, vínculos con historias, ciclos y casos dentro de los ciclos.
- **`publicador-resultados`**: después de `npm test` en k0lmena, sube estado, comentario y evidencias de cada caso al ciclo.

## Configuración

Todo va en el `.env` de la raíz (ver `.env.example`, sección *Gestión de pruebas*):

```
+---------------+------------------------------------------+
| Herramienta   | Variables obligatorias                   |
+===============+==========================================+
| Todas         | GESTION_HERRAMIENTA, GESTION_PROYECTO    |
|               | (key del proyecto de Jira)               |
+---------------+------------------------------------------+
| xray-cloud    | XRAY_CLOUD_CLIENT_ID,                    |
|               | XRAY_CLOUD_CLIENT_SECRET, JIRA_BASE_URL, |
|               | JIRA_EMAIL, JIRA_API_TOKEN               |
+---------------+------------------------------------------+
| xray-dc       | XRAY_DC_URL y XRAY_DC_TOKEN (o           |
|               | XRAY_DC_USER y XRAY_DC_PASSWORD)         |
+---------------+------------------------------------------+
| k0lmena-tmt   | K0LMENA_TMT_TOKEN (y K0LMENA_TMT_URL si  |
|               | no es http://localhost:4000/api/v1/mcp); |
|               | GESTION_PROYECTO es el id numérico       |
+---------------+------------------------------------------+
```

Dependencia: `requests` (está en `requirements.txt`; el script la instala si falta).

## k0lmenaTMT

Con el token personal (`kolm_pat_...`), k0lmenaTMT expone solo su **server MCP** (su API REST pide el login de la interfaz). En vez de que el agente escriba caso por caso con las herramientas del conector (cientos de llamadas del modelo y las evidencias en base64 por la conversación), **el script es el cliente MCP**: hace las mismas llamadas sin modelo, a su ritmo, y sube las evidencias directo desde el disco.

- **Cómo escribe**: cada herramienta de escritura de k0lmenaTMT devuelve una propuesta (change-set); el script la aplica con `apply_change_set` y toma el id creado. Todo queda registrado en k0lmenaTMT y se puede deshacer desde ahí.
- **Mapeo**:
  - **carpeta** → `create_directory`, una por nivel;
  - **caso** → `create_test_case` con pasos (acción, datos, resultado), etiquetas (las del caso, la historia y `k0lmenIA`), tiempo estimado y prioridad (`K0LMENA_TMT_PRIORIDADES`); un BDD va a la pestaña **Gherkin** (`create_test_case` no acepta el gherkin: se carga con `update_test_case` apenas se crea el caso) y queda como `automated`; en Pasos queda solo lo que esa pestaña no guarda (los Examples de un Scenario Outline y la tabla o el texto de un paso);
  - **ciclo** → `create_test_cycle`, y agregar casos → `add_case_to_cycle` (cada uno es un *cycle suite*);
  - **resultado** → `record_execution` (estado, conteo y tiempo) más `attach_evidence` con las capturas, el GIF, el video si falló y un `resultado.txt` con el detalle, porque la ejecución no tiene campo de comentario.
- **Keys**: `TC-<id>` (casos) y `CY-<id>` (ciclos), así los comandos se usan igual que con Xray (`--ciclo CY-45`, tags `@TC-123`).
- **Historia**: k0lmenaTMT no se conecta a Jira: la historia va como etiqueta del caso y en la descripción del ciclo.
- **Ciclos de otro proyecto**: el script solo escribe en ciclos que creó k0lmenIA en ese proyecto (los recuerda) o que la persona confirmó con `K0LMENA_TMT_CICLOS=CY-12,CY-15` (por ejemplo, uno creado desde la interfaz de k0lmenaTMT), porque k0lmenaTMT no valida el proyecto del ciclo y el MCP no permite consultarlo.
- **Idempotencia**: el MCP no lista carpetas ni los casos de un ciclo, así que el script recuerda esos ids en `output/gestion/k0lmena-tmt.json` (además de la trazabilidad de siempre). Los casos ya subidos no se duplican.
- **Ritmo**: k0lmenaTMT acepta `ASSISTANT_RATE_LIMIT` pedidos por minuto por usuario (20 por defecto) y cada escritura son dos. Con 20, una historia de 30 casos más su ciclo y resultados con evidencia tarda unos 12 minutos. `K0LMENA_TMT_RPM` ajusta el script si tu instancia acepta más.
- **Evidencias**: hasta 10 archivos y 10 MB por archivo en cada llamada (límites de k0lmenaTMT); las más grandes se avisan y quedan en el informe local.
- **Tiempo real y ciclo**: la duración de cada escenario (del `cucumber-report.json`) llega como tiempo real de la ejecución, y al publicar el ciclo queda como ejecutado (`completed`, o `running` si quedó algo pendiente).
- **Textos largos**: k0lmenaTMT limita a 255 caracteres el título, la descripción y la precondición del caso, y el nombre de un paso. El script los acorta (respetando la línea del tiempo estimado) y lo que no entra en el nombre de un paso pasa a sus datos. Los Examples de un Scenario Outline van como un paso más, con la tabla en sus datos.
- **Comprobar la conexión**: `npm run doctor` hace un `tools/list` (no escribe nada) y dice si k0lmenaTMT responde y si el token vale.
- **Validado contra un k0lmenaTMT real** (`underc0delabs/k0lmenatmt:latest`): casos manuales y BDD, ciclo, resultados aprobado, fallido y bloqueado, evidencias PNG, WebM y texto (verificadas byte por byte) y tiempo real. Los tests usan los esquemas reales de sus herramientas (`tests/fixtures/k0lmena_tmt_herramientas.json`).

### Lo que conviene sumar en k0lmenaTMT

Del lado de k0lmenaTMT hay diez mejoras que harían la integración mucho más rápida y completa:

0. **Validar el proyecto del ciclo** (importante): `add_case_to_cycle` acepta un ciclo de **otro** proyecto sin avisar (se probó: casos del proyecto 2 terminaron en un ciclo del proyecto 1). Como el MCP tampoco permite consultar de qué proyecto es un ciclo, el script solo escribe en ciclos que creó k0lmenIA en ese proyecto o en los que la persona confirmó con `K0LMENA_TMT_CICLOS`.
1. **Límite de pedidos para tokens personales**: hoy el token comparte el límite del chat del asistente (20 por minuto). Para automatización conviene un límite propio y más alto (por ejemplo, 300 por minuto para los `kolm_pat_`).
2. **Escritura en lote**: una herramienta que reciba varias acciones en un solo change-set (o que aplique varias propuestas juntas), o un endpoint con el token personal para importar resultados de Cucumber o JUnit. Pasa de cientos de pedidos a unos pocos.
3. **Comentario en la ejecución**: un campo `comment` (o `errorMessage`) en `record_execution`, para no tener que mandar el detalle como `resultado.txt`.
4. **Consultas que faltan**: `query_directories`, `query_test_cycles` y los *cycle suites* de un ciclo, así la idempotencia no depende de un archivo local, y los agentes pueden retomar ciclos creados desde la interfaz.
5. **Textos largos**: la descripción y la precondición del caso, y el nombre de un paso, son `character varying(255)`. Un caso con una descripción larga o un BDD con su Gherkin no entran: el script los acorta (lo que no entra en el nombre de un paso pasa a sus datos, que no tienen límite). Conviene que sean `text`.
6. **Carpeta principal triplicada**: al crear un proyecto, k0lmenaTMT crea tres "Main Folder" (pasa también desde la interfaz).
7. **Referencia externa del caso**: un campo para el ID de k0lmenIA (`CP-001`) y la historia (`PROJ-12`), con búsqueda, para deduplicar y trazar sin depender del título ni de las etiquetas.
8. **Gherkin en las herramientas**: `create_test_case` y `update_test_case` no declaran el campo `gherkin` (el que muestra la pestaña Gherkin). `create_test_case` lo descarta; `update_test_case` lo guarda porque pasa los cambios tal cual, que es lo que usa el script. Conviene declararlo en las dos, y aceptar los Examples (hoy el formato solo guarda Given, When, Then y tags).
9. **Cambios a medias**: `apply_change_set` no es atómico. Un `update_test_case` que cambia el gherkin y los pasos de un caso que ya está en un ciclo con ejecuciones guarda el gherkin y después falla al borrar los pasos (`CycleSuiteSteps_originalStepId_fkey`), y devuelve error con el cambio a medio aplicar.

## Comandos

```bash
python scripts/gestion/gestion.py [--herramienta X] [--dry-run] <comando> [opciones]

carpeta             --ruta "HU-001 Registro/Manuales"
subir-casos         --origen <casos.xlsx | escenarios.feature> --carpeta "HU-001 Registro" [--historia PROJ-12] [--ids CP-001,CP-002] [--traza HU-001] [--modulo "Registro"]
sincronizar-casos   --origen <casos.xlsx | escenarios.feature> --traza HU-001 [--ids ...] [--modulo ...] [--forzar]
vincular            --historia PROJ-12 (--casos PROJ-45,PROJ-46 | --ciclo PROJ-60)
crear-ciclo         --nombre "HU-001 Sprint 5" [--historia PROJ-12] [--casos ... | --traza HU-001 [--ids ...]]
agregar-a-ciclo     --ciclo PROJ-60 (--casos ... | --traza HU-001 [--ids ...])
extraer-resultados  --reporte herramientas/k0lmena/reports/web/cucumber-report.json   (o un JUnit XML: archivo o carpeta)
publicar-resultados --ciclo PROJ-60 --resultados output/gestion/resultados-<fecha>.json [--traza HU-001] [--sin-video]
```

- **Carpetas sin barra inicial** (`"HU-001 Registro/Manuales"`): Git Bash convierte los argumentos que empiezan con `/` en rutas de Windows. El script lo detecta y avisa.
- **Etiquetas estándar**: cada caso sube con las mismas etiquetas en todas las herramientas (`scripts/_etiquetas.py`), en este orden:
  - **historia**: `HU-001` y la key de Jira de `--historia` (`PROJ-12`);
  - **módulo**: `modulo-<nombre>`, del `@modulo-x` del caso o, si no tiene, de `--modulo`, la fila *Módulo* de la planilla o el nombre de la `Feature`;
  - **prioridad**: `critica`, `alta`, `media` o `baja` (manda la columna Prioridad);
  - **smoke**: los casos de humo y los críticos;
  - **regresion**: todos, salvo los que dependen de información que falta (`falta-info`) o están bloqueados;
  - después, las demás (`positivo`, `negativo`, `borde`, `CA1`, `FI-01`…).

  En minúscula, salvo las keys. La planilla de `generar_casos.py` usa las mismas reglas. En k0lmenaTMT, volver a subir actualiza las etiquetas de los casos que ya estaban (también los tags de la pestaña Gherkin), sin tocar sus pasos.
- **Sincronizar casos ya subidos** (`sincronizar-casos`):
  - **Cómo detecta los cambios**: al subir, cada caso guarda una firma de su contenido en la trazabilidad. Si después cambia en la planilla o el `.feature`, `subir-casos` lo avisa (`cambiaron_en_el_origen`).
  - **Qué actualiza**: título, descripción, precondiciones, prioridad, etiquetas, tiempo y pasos o gherkin.
  - **Qué no toca**: los casos que no cambiaron (`--forzar` los actualiza igual). Los que todavía no se subieron se listan en `no_subidos`.

  Cómo actualiza cada herramienta:
  - **Xray Cloud**: Jira REST v2 para los campos y GraphQL para la definición (`updateGherkinTestDefinition`, o `removeAllTestSteps` + `addTestStep`).
  - **Xray DC**: Jira REST v2 (también los campos de Cucumber) y, en un caso Manual, se borran sus pasos y se cargan los nuevos.
  - **k0lmenaTMT**: `update_test_case`. Si el caso ya tiene ejecuciones en un ciclo, k0lmenaTMT no deja borrar sus pasos: se actualiza el resto y se avisa.
- **Resultados de otros frameworks (JUnit XML)**: `extraer-resultados --reporte` acepta un `.xml` o una carpeta con varios (Surefire deja uno por clase), de Cypress, Playwright, pytest, Maven, Jest o Robot.
  - **El caso**: sale del nombre del test, de su clase o de sus properties:
    - `CP-001`, también escrito `cp_001` o `CP001` (como en `test_cp_001_login` de pytest);
    - `@HU-001`;
    - keys como tag o entre corchetes (`@PROJ-45`, `[TC-12]`), o en una property (`test_key`, la de Xray).
  - **El estado**: `failure`/`error` → fallido, `skipped` → pendiente. Si un test se repite (reintentos), vale el último.
  - **Las evidencias**: `[[ATTACHMENT|ruta]]` (Playwright, Jenkins), la property `attachment` y `testrun_evidence` de Xray. Las capturas, videos y archivos (por ejemplo el `trace.zip`) se suben con el resultado.
- **`--dry-run`** muestra cada request sin enviarlo. Usalo la primera vez en cada herramienta.
- Cada comando imprime un JSON con el resultado (lo leen los agentes).

## Cómo se conecta todo

```
casos-HU-001.xlsx / HU-001.feature ──subir-casos──► carpeta + casos (vinculados a PROJ-12)
                                                     │
                     output/gestion/HU-001-<herramienta>.json   (CP-001 → PROJ-45, ciclos creados)
                                                     │
crear-ciclo ──► ciclo con los casos (vinculado a PROJ-12)
                                                     │
npm test (k0lmena) ──► cucumber-report.json ──extraer-resultados──► resultados + evidencias
                                                     │
publicar-resultados ──► estado + comentario + captura (y video si falló) en cada caso del ciclo
```

- **Trazabilidad** (`output/gestion/<HU>-<herramienta>.json`): qué `CP-XXX` es qué key remota. Evita duplicados (un caso ya subido no se vuelve a crear) y permite publicar resultados.
- **Escenario → caso**: por el tag `@CP-XXX` del escenario (vía trazabilidad) o por un tag con la key directa (`@PROJ-45`). Como los `CP-XXX` se repiten en cada historia, con `--traza HU-001` solo se traducen los escenarios que llevan `@HU-001`; los demás quedan en `sin_caso_asociado` con el motivo (otra historia, sin `@HU`, caso no subido). Si una corrida tiene varias historias, se publica una vez por historia.
- **Reintentos seguros**: `subir-casos` registra cada caso en la trazabilidad apenas lo crea; si falla el vínculo con la historia, queda marcado y se reintenta al volver a correr el mismo comando, sin duplicar el caso. Los adjuntos se reenvían completos si la API pide reintentar (429/5xx) y los cortes de red se reintentan solos.
- **Evidencias**: captura siempre; GIF del recorrido si la corrida se hizo con `EVIDENCE=ambos`; video completo solo si el caso falló. Si un archivo supera el límite de la herramienta, se omite y se avisa.

```
+--------------------+------------------------------------------+
| Concepto           | Xray Cloud / Server-DC                   |
+====================+==========================================+
| Carpeta            | Carpeta del Test Repository              |
+--------------------+------------------------------------------+
| Caso               | Issue Test (Manual o Cucumber)           |
+--------------------+------------------------------------------+
| Ciclo              | Issue Test Execution                     |
+--------------------+------------------------------------------+
| Caso - historia    | Issue link "Test(s)" (cobertura)         |
+--------------------+------------------------------------------+
| Ciclo - historia   | Issue link "Relates"                     |
+--------------------+------------------------------------------+
| Límite por adjunto | Cloud: no documentado / DC: 10 MB (Jira) |
+--------------------+------------------------------------------+
```

Estados: `aprobado` / `fallido` / `bloqueado` / `pendiente` se mapean a PASSED / FAILED / ABORTED / TODO (Xray Cloud) y PASS / FAIL / ABORTED / TODO (Xray DC). Si tu instancia usa estados propios, mapealos con `XRAY_ESTADOS` (JSON).

## Estado de validación

La integración se construyó con la documentación oficial y se probó con `--dry-run` y con un simulador de respuestas (incluye la idempotencia y el agregado automático de casos que faltan en el ciclo), **sin una instancia real**. En el primer uso con cada herramienta, corré primero `--dry-run` y después confirmá estos puntos, que la documentación no deja del todo claros:

```
+---------------+------------------------------------------+--------------------------------------+
| Herramienta   | Punto a confirmar                        | Ajuste si no coincide                |
+===============+==========================================+======================================+
| xray-cloud    | El vínculo caso-historia queda con la    | XRAY_LINK_INVERTIR=1                 |
|               | historia diciendo "is tested by"         |                                      |
+---------------+------------------------------------------+--------------------------------------+
| xray-cloud    | El tipo de vínculo se llama "Test" (en   | XRAY_LINK_CASO=Tests                 |
|               | instancias migradas puede ser "Tests")   |                                      |
+---------------+------------------------------------------+--------------------------------------+
| xray-cloud    | La descripción en texto plano se acepta  | Avisar para adaptarlo                |
|               | (Jira Cloud v3 a veces exige formato     |                                      |
|               | ADF)                                     |                                      |
+---------------+------------------------------------------+--------------------------------------+
| xray-cloud    | El tamaño máximo de evidencia (videos)   | GESTION_LIMITE_ADJUNTO_MB            |
+---------------+------------------------------------------+--------------------------------------+
| xray-dc       | Los nombres de campos "Test Type",       | Avisar para adaptarlo                |
|               | "Cucumber Test Type" y "Cucumber         |                                      |
|               | Scenario"                                |                                      |
+---------------+------------------------------------------+--------------------------------------+
| xray-dc       | El límite de adjuntos de tu Jira (10 MB  | GESTION_LIMITE_ADJUNTO_MB            |
|               | por defecto)                             |                                      |
+---------------+------------------------------------------+--------------------------------------+
| todas Xray    | Que "bloqueado" deba ser ABORTED (o un   | XRAY_ESTADOS={"bloqueado":"BLOCKED"} |
|               | estado propio como BLOCKED)              |                                      |
+---------------+------------------------------------------+--------------------------------------+
| todas Xray    | Las prioridades de tu Jira (Highest,     | GESTION_PRIORIDADES o                |
|               | High, Medium, Low)                       | GESTION_ENVIAR_PRIORIDAD=0           |
+---------------+------------------------------------------+--------------------------------------+
```

# Gestión de pruebas: Xray, QMetry (QTM4J), AIO Tests y Zephyr Scale

> **Azure DevOps Test Plans** no pasa por `gestion.py`: se integra por el conector MCP `azure-devops` (ver [`CONECTORES.md`](../../CONECTORES.md#azure-devops)). Desde acá solo se usa `para_azure_devops.py`, que convierte los casos al formato del conector:
>
> ```bash
> python scripts/gestion/para_azure_devops.py output/casos-de-prueba/manuales/casos-HU-001.xlsx [--ids CP-001,CP-003]
> ```

Integración propia de k0lmenIA con las herramientas de gestión de pruebas, sobre sus **APIs oficiales**. Los mismos comandos sirven para las cinco variantes:

```
+---------------------------+-----------------------+-----------------------------------------+
| Herramienta               | GESTION_HERRAMIENTA   | API                                     |
+===========================+=======================+=========================================+
| Xray Cloud                | xray-cloud            | GraphQL v2 + Jira Cloud REST (vínculos) |
+---------------------------+-----------------------+-----------------------------------------+
| Xray Server / Data Center | xray-dc               | REST raven 1.0 + Jira REST v2           |
+---------------------------+-----------------------+-----------------------------------------+
| QMetry para Jira Cloud    | qtm4j                 | Open API (rest/api/latest)              |
+---------------------------+-----------------------+-----------------------------------------+
| AIO Tests (Jira Cloud)    | aio                   | REST pública v1                         |
+---------------------------+-----------------------+-----------------------------------------+
| Zephyr Scale (Jira Cloud) | zephyr-scale          | REST v2 + Jira Cloud REST (vínculos)    |
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
| qtm4j         | QTM4J_API_KEY (y QTM4J_BASE_URL si no es |
|               | la región US)                            |
+---------------+------------------------------------------+
| aio           | AIO_API_TOKEN                            |
+---------------+------------------------------------------+
| k0lmena-tmt   | K0LMENA_TMT_TOKEN (y K0LMENA_TMT_URL si  |
|               | no es http://localhost:4000/api/v1/mcp); |
|               | GESTION_PROYECTO es el id numérico       |
+---------------+------------------------------------------+
| zephyr-scale  | ZEPHYR_API_TOKEN, JIRA_BASE_URL,         |
|               | JIRA_EMAIL, JIRA_API_TOKEN (y            |
|               | ZEPHYR_API_URL si no es la región US)    |
+---------------+------------------------------------------+
```

Dependencia: `requests` (está en `requirements.txt`; el script la instala si falta).

## k0lmenaTMT

Con el token personal (`kolm_pat_...`), k0lmenaTMT expone solo su **server MCP** (su API REST pide el login de la interfaz). En vez de que el agente escriba caso por caso con las herramientas del conector (cientos de llamadas del modelo y las evidencias en base64 por la conversación), **el script es el cliente MCP**: hace las mismas llamadas sin modelo, a su ritmo, y sube las evidencias directo desde el disco.

- **Cómo escribe**: cada herramienta de escritura de k0lmenaTMT devuelve una propuesta (change-set); el script la aplica con `apply_change_set` y toma el id creado. Todo queda registrado en k0lmenaTMT y se puede deshacer desde ahí.
- **Mapeo**:
  - **carpeta** → `create_directory`, una por nivel;
  - **caso** → `create_test_case` con pasos (acción, datos, resultado), etiquetas (las del caso, la historia y `k0lmenIA`), tiempo estimado y prioridad (`K0LMENA_TMT_PRIORIDADES`); un BDD lleva sus pasos Given/When/Then y `automated`;
  - **ciclo** → `create_test_cycle`, y agregar casos → `add_case_to_cycle` (cada uno es un *cycle suite*);
  - **resultado** → `record_execution` (estado, conteo y tiempo) más `attach_evidence` con las capturas, el GIF, el video si falló y un `resultado.txt` con el detalle, porque la ejecución no tiene campo de comentario.
- **Keys**: `TC-<id>` (casos) y `CY-<id>` (ciclos), así los comandos se usan igual que con Xray o Zephyr (`--ciclo CY-45`, tags `@TC-123`).
- **Historia**: k0lmenaTMT no se conecta a Jira: la historia va como etiqueta del caso y en la descripción del ciclo.
- **Idempotencia**: el MCP no lista carpetas ni los casos de un ciclo, así que el script recuerda esos ids en `output/gestion/k0lmena-tmt.json` (además de la trazabilidad de siempre). Los casos ya subidos no se duplican.
- **Ritmo**: k0lmenaTMT acepta `ASSISTANT_RATE_LIMIT` pedidos por minuto por usuario (20 por defecto) y cada escritura son dos. Con 20, una historia de 30 casos más su ciclo y resultados con evidencia tarda unos 12 minutos. `K0LMENA_TMT_RPM` ajusta el script si tu instancia acepta más.
- **Evidencias**: hasta 10 archivos y 10 MB por archivo en cada llamada (límites de k0lmenaTMT); las más grandes se avisan y quedan en el informe local.

### Lo que conviene sumar en k0lmenaTMT

Del lado de k0lmenaTMT hay cinco mejoras que harían la integración mucho más rápida y completa:

1. **Límite de pedidos para tokens personales**: hoy el token comparte el límite del chat del asistente (20 por minuto). Para automatización conviene un límite propio y más alto (por ejemplo, 300 por minuto para los `kolm_pat_`).
2. **Escritura en lote**: una herramienta que reciba varias acciones en un solo change-set (o que aplique varias propuestas juntas), o un endpoint con el token personal para importar resultados de Cucumber o JUnit. Pasa de cientos de pedidos a unos pocos.
3. **Comentario en la ejecución**: un campo `comment` (o `errorMessage`) en `record_execution`, para no tener que mandar el detalle como `resultado.txt`.
4. **Consultas que faltan**: `query_directories`, `query_test_cycles` y los *cycle suites* de un ciclo, así la idempotencia no depende de un archivo local, y los agentes pueden retomar ciclos creados desde la interfaz.
5. **Referencia externa del caso**: un campo para el ID de k0lmenIA (`CP-001`) y la historia (`PROJ-12`), con búsqueda, para deduplicar y trazar sin depender del título ni de las etiquetas.

## Comandos

```bash
python scripts/gestion/gestion.py [--herramienta X] [--dry-run] <comando> [opciones]

carpeta             --ruta "HU-001 Registro/Manuales"
subir-casos         --origen <casos.xlsx | escenarios.feature> --carpeta "HU-001 Registro" [--historia PROJ-12] [--ids CP-001,CP-002] [--traza HU-001]
vincular            --historia PROJ-12 (--casos PROJ-45,PROJ-46 | --ciclo PROJ-60)
crear-ciclo         --nombre "HU-001 Sprint 5" [--historia PROJ-12] [--casos ... | --traza HU-001 [--ids ...]]
agregar-a-ciclo     --ciclo PROJ-60 (--casos ... | --traza HU-001 [--ids ...])
extraer-resultados  --reporte herramientas/k0lmena/reports/web/cucumber-report.json
publicar-resultados --ciclo PROJ-60 --resultados output/gestion/resultados-<fecha>.json [--traza HU-001] [--sin-video]
```

- **Carpetas sin barra inicial** (`"HU-001 Registro/Manuales"`): Git Bash convierte los argumentos que empiezan con `/` en rutas de Windows. El script lo detecta y avisa.
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
+--------------------+------------------------------------------+-----------------------+---------------------------------+
| Concepto           | Xray Cloud / Server-DC                   | QTM4J                 | AIO Tests                       |
+====================+==========================================+=======================+=================================+
| Carpeta            | Carpeta del Test Repository              | Carpeta de test cases | Carpeta de casos                |
+--------------------+------------------------------------------+-----------------------+---------------------------------+
| Caso               | Issue Test (Manual o Cucumber)           | Test case             | Caso (Classic o BDD, Published) |
+--------------------+------------------------------------------+-----------------------+---------------------------------+
| Ciclo              | Issue Test Execution                     | Test cycle            | Test cycle                      |
+--------------------+------------------------------------------+-----------------------+---------------------------------+
| Caso - historia    | Issue link "Test(s)" (cobertura)         | Requirement link      | jiraRequirementIDs              |
+--------------------+------------------------------------------+-----------------------+---------------------------------+
| Ciclo - historia   | Issue link "Relates"                     | Requirement link      | jiraTaskIDs                     |
+--------------------+------------------------------------------+-----------------------+---------------------------------+
| Límite por adjunto | Cloud: no documentado / DC: 10 MB (Jira) | No documentado        | 100 MB                          |
+--------------------+------------------------------------------+-----------------------+---------------------------------+
```

En **Zephyr Scale** la carpeta es una carpeta `TEST_CASE` (y `TEST_CYCLE` para el ciclo, con la misma ruta); el caso, un test case con pasos *inline* (acción, datos y resultado esperado) o, si es BDD, con un test script tipo `bdd`; el ciclo, un test cycle. Los vínculos con la historia usan `links/issues` con el **id numérico** del issue, que se resuelve con Jira REST (por eso pide también `JIRA_*`). Zephyr no tiene "agregar caso al ciclo": un caso está en el ciclo cuando tiene una ejecución ahí, así que `agregar-a-ciclo` crea una ejecución *Not Executed* por caso y `publicar-resultados` crea una ejecución nueva con el resultado (el historial queda completo). Las evidencias se suben a esa ejecución (hasta 1 GB por archivo). Las keys tienen una letra antes del número: casos `PROJ-T12`, ciclos `PROJ-R5`.

Estados: `aprobado` / `fallido` / `bloqueado` / `pendiente` se mapean a PASSED / FAILED / ABORTED / TODO (Xray Cloud), PASS / FAIL / ABORTED / TODO (Xray DC), Pass / Fail / Blocked / Not Executed (QTM4J y Zephyr Scale) y Passed / Failed / Blocked / Not Run (AIO). Si tu instancia usa estados propios, mapealos con `XRAY_ESTADOS`, `QTM4J_ESTADOS`, `AIO_ESTADOS` o `ZEPHYR_ESTADOS` (JSON).

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
| qtm4j         | Que alcance el header apiKey (sin Basic  | Avisar para adaptarlo                |
|               | auth de Jira)                            |                                      |
+---------------+------------------------------------------+--------------------------------------+
| qtm4j         | Que cargar bddScenario deje el caso como | Avisar para adaptarlo                |
|               | BDD en la interfaz                       |                                      |
+---------------+------------------------------------------+--------------------------------------+
| qtm4j         | Que existan los resultados Pass y WIP    | QTM4J_ESTADOS                        |
|               | (además de Fail, Blocked y Not Executed) |                                      |
+---------------+------------------------------------------+--------------------------------------+
| aio           | Que el estado de caso "Published" exista | AIO_ESTADO_CASO                      |
|               | (sin él no se pueden agregar casos a     |                                      |
|               | ciclos)                                  |                                      |
+---------------+------------------------------------------+--------------------------------------+
| aio           | Que guardar el caso completo al vincular | Avisar para adaptarlo                |
|               | la historia no pise otros campos         |                                      |
+---------------+------------------------------------------+--------------------------------------+
| zephyr-scale  | Las prioridades de tu proyecto (High,    | GESTION_PRIORIDADES o                |
|               | Normal, Low por defecto)                 | GESTION_ENVIAR_PRIORIDAD=0           |
+---------------+------------------------------------------+--------------------------------------+
| zephyr-scale  | Que existan los estados Pass, Fail,      | ZEPHYR_ESTADOS                       |
|               | Blocked, Not Executed e In Progress      |                                      |
+---------------+------------------------------------------+--------------------------------------+
| zephyr-scale  | Que el comentario con <br> se vea con    | Avisar para adaptarlo                |
|               | saltos de línea                          |                                      |
+---------------+------------------------------------------+--------------------------------------+
```

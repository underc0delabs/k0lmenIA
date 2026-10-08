# Gestión de pruebas: Xray, QMetry (QTM4J) y AIO Tests

Integración propia de k0lmenIA con las herramientas de gestión de pruebas, sobre sus **APIs oficiales**. Los mismos comandos sirven para las cuatro variantes:

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
```

Dependencia: `requests` (está en `requirements.txt`; el script la instala si falta).

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
- **Escenario → caso**: por el tag `@CP-XXX` del escenario (vía trazabilidad) o por un tag con la key directa (`@PROJ-45`).
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

Estados: `aprobado` / `fallido` / `bloqueado` / `pendiente` se mapean a PASSED / FAILED / ABORTED / TODO (Xray Cloud), PASS / FAIL / ABORTED / TODO (Xray DC), Pass / Fail / Blocked / Not Executed (QTM4J) y Passed / Failed / Blocked / Not Run (AIO). Si tu instancia usa estados propios, mapealos con `XRAY_ESTADOS`, `QTM4J_ESTADOS` o `AIO_ESTADOS` (JSON).

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
```

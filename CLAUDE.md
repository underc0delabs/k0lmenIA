# k0lmenIA — Contexto del proyecto

Este repositorio es un conjunto de **agentes de QA para Claude Code**, pensados para que profesionales de testing manual aceleren sus tareas del día a día: planificar la estrategia de pruebas, analizar historias, escribir casos de prueba (manuales, BDD y de API), generar datos de prueba, redactar reportes de bug, ejecutar pruebas end-to-end en el navegador, ejecutar pruebas de API, generar reportes de resultados en HTML y armar el informe de cierre de la ronda.

Todo el trabajo y todas las salidas son **en español**.

---

## Cómo funciona el flujo

1. **`input/`** — Acá se ponen los insumos: historias de usuario, documentación del producto, contratos de API y observaciones de errores.
2. **Agentes** (`.claude/agents/`) — Cada agente es un especialista. Claude Code los invoca solo según lo que pida la persona; también se les puede pedir explícitamente.
3. **`plantillas/` y `scripts/`** — Definen el **formato de salida**. El **reporte de bug** sigue `plantillas/plantilla-reporte-bug.md`. Los **casos de prueba** se generan como planilla **Excel** (`.xlsx`) con `scripts/generar_casos.py` (referencia: `plantillas/plantilla-casos-prueba.xlsx`) y un **informe de cobertura** en Markdown (referencia: `plantillas/plantilla-cobertura.md`).
4. **`output/`** — Acá se guardan los artefactos generados, ordenados por tipo.

```
input/ → [ agente ] → output/
              ↑
   plantillas/ + scripts/  (formato)
```

### Preguntas y confirmaciones (conversación principal ↔ agentes)

Los agentes corren como subagentes y **no pueden hacerle preguntas a la persona a mitad del trabajo**. Por eso:

- **Antes de invocar un agente**, la conversación principal resuelve con la persona lo que el agente seguro va a necesitar y no está en el pedido. Por ejemplo: headed o headless (`ejecutor-e2e`, `web-mapper`), qué historia si hay varias, la URL o el ambiente, y la key de la historia en Jira o Azure DevOps para la gestión.
- **Si un agente termina devolviendo "Necesito que confirmes"**, la conversación principal le hace esas preguntas a la persona (con opciones, la recomendada primero) y **continúa al mismo agente** con las respuestas; no empieza uno nuevo.
- Las acciones con efecto (escribir en una base, crear o modificar datos en Jira/Xray/QMetry/AIO/Azure DevOps, correr carga, métodos con efecto) se confirman **con la persona** y se le pasan al agente explícitamente; nunca se asumen.
- **Performance**: la planificación guiada la hace la conversación principal con el skill `guia-performance`; el `performance-mapper` trabaja con el plan confirmado.
- **Correr pruebas ya automatizadas**: es `npm test` en k0lmena (sin agentes ni tokens). Los ejecutores en vivo (`ejecutor-e2e`, `ejecutor-api`) son para casos sueltos que no vale la pena automatizar.

---

## Agentes disponibles

```
+----------------------------+------------------------------------------+---------------------------------------+
| Agente                     | Para qué sirve                           | Guarda la salida en                   |
+============================+==========================================+=======================================+
| `analista-historias`       | Analiza historias y criterios de         | `output/analisis-historias/`          |
|                            | aceptación; detecta ambigüedades y arma  |                                       |
|                            | preguntas de refinamiento                |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `estratega-pruebas`        | Plan/estrategia de pruebas (alcance,     | `output/planes-de-prueba/`            |
|                            | riesgos, tipos de prueba, criterios)     |                                       |
|                            | como dashboard HTML en modo oscuro       |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `generador-casos-manuales` | Casos de prueba en Excel (.xlsx) y       | `output/casos-de-prueba/manuales/`    |
|                            | Markdown (.md), + informe de cobertura   |                                       |
|                            | (.md) con ambigüedades y preguntas para  |                                       |
|                            | el PO                                    |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `generador-casos-bdd`      | Escenarios en Gherkin (keywords en       | `output/casos-de-prueba/bdd/`         |
|                            | inglés, contenido en español) + informe  |                                       |
|                            | de cobertura por criterio (.md)          |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `generador-reportes-bug`   | Reportes de bug, siguiendo               | `output/reportes-bug/`                |
|                            | `plantillas/plantilla-reporte-bug.md`    |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `generador-datos-prueba`   | Datos de prueba realistas (Markdown o    | `output/datos-de-prueba/`             |
|                            | CSV)                                     |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `generador-casos-api`      | Casos de prueba de API (tabla resumen +  | `output/casos-api/`                   |
|                            | detalle con JSON) a partir de            |                                       |
|                            | contratos/endpoints                      |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `ejecutor-e2e`             | Ejecuta los casos/escenarios pedidos en  | `output/ejecuciones/`                 |
|                            | el navegador con Playwright MCP          |                                       |
|                            | (pregunta headed o headless), reporta    |                                       |
|                            | con evidencia y genera el reporte HTML   |                                       |
|                            | de la corrida                            |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `ejecutor-api`             | Ejecuta pruebas de API corriendo una     | `output/ejecuciones/`                 |
|                            | colección de Postman con Newman y genera |                                       |
|                            | el reporte HTML de la corrida            |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `generador-reporte-html`   | Arma el reporte HTML (dashboard en modo  | `output/ejecuciones/`                 |
|                            | oscuro, con indicadores y gráficos) de   |                                       |
|                            | una ejecución, a partir de sus           |                                       |
|                            | resultados                               |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `generador-reporte-cierre` | Informe de cierre de la ronda            | `output/informes-cierre/`             |
|                            | (resultados, bugs, recomendación go/no-  |                                       |
|                            | go) como dashboard HTML en modo oscuro   |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `web-mapper`               | Recorre la web con Playwright MCP        | `herramientas/k0lmena/web/` +         |
|                            | siguiendo casos manuales o BDD y genera  | `output/mapeos/`                      |
|                            | la automatización de k0lmena (.feature   |                                       |
|                            | ajustado, steps y locators)              |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `api-mapper`               | Lee una colección de Postman o un        | `herramientas/k0lmena/api/` +         |
|                            | Swagger/OpenAPI, verifica los endpoints  | `output/mapeos/`                      |
|                            | y genera los .feature de k0lmena con los |                                       |
|                            | steps genéricos                          |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `gestor-pruebas`           | Crea carpetas y casos en Xray (Cloud o   | La herramienta de gestión +           |
|                            | Server/DC), QTM4J o AIO Tests (vía       | `output/gestion/`                     |
|                            | `scripts/gestion/`) o en Azure DevOps    |                                       |
|                            | Test Plans (vía el MCP `azure-devops`),  |                                       |
|                            | los vincula a historias, crea ciclos y   |                                       |
|                            | les agrega casos                         |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `publicador-resultados`    | Sube los resultados de una corrida de    | La herramienta de gestión             |
|                            | k0lmena (`npm test`) al ciclo: estado,   |                                       |
|                            | comentario y evidencias (captura; video  |                                       |
|                            | si falló)                                |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `verificador-datos`        | Se conecta a las bases de datos del      | Respuesta en el chat (+               |
|                            | `.env` (PostgreSQL, MySQL/MariaDB, SQL   | `output/verificaciones-datos/` si se  |
|                            | Server, MongoDB) para verificar datos de | pide)                                 |
|                            | las pruebas o lo que se le pida; suma    |                                       |
|                            | verificaciones de BD a los `.feature` de |                                       |
|                            | k0lmena solo si se lo piden. Solo        |                                       |
|                            | lectura; escribe solo con confirmación y |                                       |
|                            | nunca en producción                      |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `mobile-mapper`            | Recorre la app mobile con Appium MCP     | `herramientas/k0lmena/mobile/` +      |
|                            | siguiendo los casos y genera la          | `output/mapeos/`                      |
|                            | automatización de k0lmena (.feature,     |                                       |
|                            | steps y locators)                        |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `performance-mapper`       | Pruebas de performance (smoke, load,     | `herramientas/k0lmena/performance/` + |
|                            | stress, soak, spike) con k6, Artillery + | `output/performance/<HU>/` +          |
|                            | Playwright o JMeter. Antes, la           | `reports/performance/` +              |
|                            | conversación principal guía a la persona | `output/mapeos/`                      |
|                            | con el skill guia-performance (tipo de   |                                       |
|                            | prueba, herramienta, usuarios, rampa,    |                                       |
|                            | duración y umbrales, con sugerencias);   |                                       |
|                            | el agente genera el script, lo valida,   |                                       |
|                            | corre lo confirmado y arma el informe    |                                       |
|                            | HTML con métricas, gráficos y            |                                       |
|                            | recomendaciones                          |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-seguridad`       | Revisa la seguridad de una web propia o  | `output/seguridad/`                   |
|                            | autorizada con un escaneo pasivo de      |                                       |
|                            | OWASP ZAP (Docker), analiza los          |                                       |
|                            | hallazgos (prioriza, descarta falsos     |                                       |
|                            | positivos, explica en español) y arma el |                                       |
|                            | informe HTML con riesgo, evidencia,      |                                       |
|                            | corrección y recomendaciones. Solo URLs  |                                       |
|                            | de SEGURIDAD_URLS_AUTORIZADAS            |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
```

---

## Estándares de QA del proyecto

Estos principios aplican a **todos** los agentes:

- **No inventar.** Si falta información para hacer bien la tarea (un paso, un dato, una regla de negocio, un resultado esperado), el agente lo **marca y lo pregunta**; nunca rellena con suposiciones disfrazadas de hechos. Es preferible un artefacto con huecos señalados que uno completo pero inventado.
- **Investigar antes de suponer.** Antes de analizar, planificar, escribir casos o automatizar una historia, se revisa su contexto completo con el skill `investigacion-contexto`: la historia de Jira con **todos** sus comentarios, subtareas, épica e issues vinculados, las páginas de Confluence y los diseños de Figma relacionados, contratos y `input/`. El resultado queda en una ficha reutilizable `output/contexto/contexto-HU-XXX.md`.
- **Marcar lo que falta.** Lo que no aparece en ninguna fuente se registra como **Falta información** con un ID por historia (`FI-01`, `FI-02`, …) y viaja con ese ID a todos los artefactos: casos (resaltados, etiqueta `@falta-info`, hoja *Falta información*), `.feature` (`@falta-info @FI-01`), coberturas, mapeos, reportes de ejecución, informe de cierre y lo que se publica en Xray/QMetry/AIO.
- **Respetar los formatos.** Los campos, su orden y sus valores permitidos los define la plantilla (o el script), no el agente.
- **Trazabilidad.** Todo artefacto referencia la historia (`HU-XXX`) o el contrato del que sale.
- **Cobertura pensada.** Los casos contemplan escenarios positivos, negativos, de borde y validaciones de campos, no solo el camino feliz.
- **Claridad.** Títulos descriptivos, pasos accionables y sin ambigüedad, lenguaje claro y profesional.

## Convenciones de IDs

- Historias de usuario: `HU-001`, `HU-002`, …
- Criterios de aceptación: `CA1`, `CA2`, … (dentro de cada historia)
- Casos de prueba manuales: `CP-001`, `CP-002`, … (numeración **por historia**). Los escenarios BDD usan la **misma** numeración como tag `@CP-XXX`, y la `Feature` lleva `@HU-XXX`: el par `@HU` + `@CP` identifica cada caso en la automatización, la gestión y los resultados.
- Casos de prueba de API: `CP-API-001`, `CP-API-002`, …
- Bugs: `BUG-001`, `BUG-002`, …
- Falta información: `FI-01`, `FI-02`, … (por historia; tags `@falta-info @FI-01`)

## Escalas

- **Severidad / Criticidad:** `Crítica` · `Alta` · `Media` · `Baja`
- **Prioridad:** `Crítica` · `Alta` · `Media` · `Baja`
- **Estado de un caso:** `N/A` · `Pendiente` · `En ejecución` · `Aprobado` · `Fallido` · `Bloqueado`

## Formato de tablas en los archivos `.md`

**Toda tabla de un `.md` debe verse alineada y con el mismo formato.** Para garantizarlo sin depender de armar cada tabla a mano:

1. Escribí las tablas como **Markdown normal** (`| col | col |`), en cualquier sección.
2. **Al terminar de escribir el `.md`, normalizá el archivo una vez:**

```bash
python scripts/formatear_tablas.py <archivo.md>
```

Convierte **todas** las tablas Markdown del archivo a tablas ASCII alineadas (dentro de bloques de código), sin importar la sección ni cuánto texto tengan. No toca lo que ya está en bloques de código, así que es seguro correrlo más de una vez.

Reglas (valen para **todos** los agentes y cualquier sección, incluidas las que armes sobre la marcha):

- Nunca dejes una tabla en Markdown crudo en el entregable: siempre pasá el `.md` por `formatear_tablas.py`.
- **Sin emojis dentro de las celdas** (descuadran el ASCII): usá texto (`Cubierto`, `Sí`, `No`, `Parcial`).
- Lo que es **código** (un body o response JSON) va en bloques ```` ```json ```` aparte; el normalizador no lo toca.
- Excepción: el `.md` de **casos de prueba** lo arma `scripts/generar_casos.py` (ya sale alineado, con el mismo estilo).

## Requisitos del entorno

**Versiones**: Python 3.10+, Node.js 20+ (22 LTS recomendado; mobile necesita 22+). Opcionales: Java 8+ (JMeter), Docker (seguridad web con ZAP), JDK + Android SDK o Xcode (mobile). Para revisar todo de una vez: `npm run doctor` (o `python scripts/doctor.py`), que dice qué falta y cómo resolverlo.

**Python**: en Windows el comando es `python`; en Mac y Linux, `python3` (y `pip3`). Los agentes usan el que corresponda al sistema. Los scripts instalan `openpyxl`/`tabulate`/`requests` solo si faltan; o se instalan con `pip install -r requirements.txt`. Si falta una librería y no se puede instalar, el script avisa con un mensaje claro (no falla en silencio).

- `scripts/generar_casos.py` → arma la planilla `.xlsx` y el `.md` de casos de prueba. Acepta `--limpiar` para borrar su JSON de entrada al terminar (cross-platform, sin depender de `rm`).
- `scripts/formatear_tablas.py` → alinea las tablas de cualquier `.md` (lo usan todos los agentes que generan informes).
- `scripts/correr_newman.py` → corre una colección de Postman con el token y la URL del `.env` y genera su reporte (`ejecutor-api`).
- `scripts/recolectar_resultados.py` → junta los resultados de una historia (ejecuciones en vivo, `npm test`, bugs, performance y seguridad) para el informe de cierre.
- `scripts/doctor.py` → revisa el entorno y la configuración.
- **Tests del repo**: `python -m pytest tests` y `npm run test:repo` (también corren en CI, en Ubuntu y Windows).

---

## Nombres de archivos de salida (sugerencia)

- Ficha de contexto: `output/contexto/contexto-HU-001.md` (fuentes consultadas, hallazgos y Falta información)
- Análisis de historia: `analisis-HU-001.md`
- Casos manuales: `casos-HU-001.xlsx` + `casos-HU-001.md` + `casos-HU-001-cobertura.md`
- Casos BDD: `HU-001-registro.feature` + `HU-001-cobertura.md`
- Reporte de bug: `BUG-001.md`
- Seguridad web: `output/seguridad/<HU o host>/<fecha>/` con `zap.json`, `analisis.json` e `informe-seguridad.html`
- Datos de prueba: `datos-HU-001.md` (o `.csv`)
- Casos de API: `casos-api-auth.md`
- Mapeo a automatización: `herramientas/k0lmena/<web|api|mobile>/features/HU-001-<slug>.feature` + `steps/HU-001.steps.ts` + `locators/HU-001.locators.ts`, y el reporte `output/mapeos/mapeo-HU-001-<web|api|mobile>.md`.
- Performance: plan `output/performance/HU-001/plan-performance-HU-001.md` + informe `informe-performance-HU-001.html` (y su `.json`) en la misma carpeta; cada corrida deja además su reporte en `herramientas/k0lmena/reports/performance/`.
- Ejecución E2E (un reporte por corrida): `reporte-HU-001-<fecha-hora>.html` (dashboard, modo oscuro) + `_resultados-HU-001-<fecha-hora>.json` (datos), en `output/ejecuciones/`; evidencia en `output/ejecuciones/evidencia/`. Cada reporte cubre solo los casos de esa ejecución.
- Ejecución de API (`ejecutor-api`): `reporte-HU-001-<fecha-hora>.html` + `_resultados-HU-001-<fecha-hora>.json` en `output/ejecuciones/` (o `API` en lugar de la historia si la corrida no es de una).
- Evidencias E2E: `output/ejecuciones/evidencia/<fecha-hora>-<id>.png` (la misma marca de tiempo de la corrida: no se pisan).
- Plan de pruebas: `output/planes-de-prueba/plan-HU-001-<fecha>.html`.
- Informe de cierre: `output/informes-cierre/cierre-HU-001-<fecha>.html`, con sus datos recolectados en `datos-HU-001.json` (`scripts/recolectar_resultados.py`).
- Mapeo de performance: `output/mapeos/mapeo-HU-001-performance.md`.

---

## Arquitectura (cómo crece el repo)

El repo se apoya en estas piezas: **agentes** (`.claude/agents/`, el quién), **skills** (`.claude/skills/`, el cómo, cargados on-demand), **MCP** (`.mcp.json`, conexiones a sistemas externos — un solo archivo que escala a muchas conexiones: Jira, Xray, Playwright…), **herramientas** (`herramientas/`, herramientas externas de testing, una subcarpeta por herramienta: Newman, **k0lmena** y OWASP ZAP) y **scripts** (`scripts/`, utilidades internas determinísticas). El detalle y cómo extender cada una está en `ARQUITECTURA.md`.

## Herramientas de gestión de pruebas

`scripts/gestion/gestion.py` integra **Xray Cloud, Xray Server/DC, QTM4J y AIO Tests** con los mismos comandos (configurados en el `.env` de la raíz con `GESTION_HERRAMIENTA` y `GESTION_PROYECTO`). **Azure DevOps** (Boards y Test Plans) se integra por el conector MCP `azure-devops`, configurado también en el `.env` (`ADO_ORGANIZACION`, `ADO_PAT`, `ADO_PROYECTO`); los pasos de los casos los arma `scripts/gestion/para_azure_devops.py`. La trazabilidad local `output/gestion/<HU>-<herramienta>.json` guarda qué `CP-XXX` es qué key remota. Detalle en `scripts/gestion/README.md`.

## Automatización con k0lmena (ahorro de tokens)

`herramientas/k0lmena/` es el framework de automatización (web, api, mobile y performance). Los agentes **mapper** escriben la automatización **una sola vez** (skill `automatizacion-k0lmena`); después la suite corre **sin agentes ni tokens** con `cd herramientas/k0lmena && npm test` (performance: `npm run perf -- <script> <perfil>`). Para correr pruebas ya automatizadas, preferí `npm test` antes que los ejecutores en vivo (`ejecutor-e2e` / `ejecutor-api`), que gastan tokens en cada corrida.

Secretos (tokens, credenciales): van en el `.env` local (gitignored) o en variables de entorno, **nunca** commiteados; hay una plantilla `.env.example`. El `.mcp.json` está versionado con los conectores que vienen activos para todos (Playwright y Atlassian: Jira y Confluence), así Claude Code arranca sin pedir aprobaciones. Los opcionales (Azure DevOps, Figma, QMetry/QTM4J, AIO Tests, k0lmenaTMT, Appium) los activa cada persona con `npm run conector -- activar <nombre>`. Ninguno lleva secretos: los que piden token lo leen del `.env` con los scripts de `scripts/mcp/`. Si un agente necesita un conector que no está activo, decí cuál y cómo activarlo. Detalle en `CONECTORES.md`.

**Fuentes externas por MCP:** si la persona da una key de Jira, un work item de Azure DevOps, una página de Confluence o de la Wiki de Azure DevOps, o un link de Figma y el conector (`atlassian`, `azure-devops` o `figma`) está activo, cualquier agente puede leerlos como insumo, igual que un archivo de `input/` (trazabilidad: citá la key, la página o el link). Si el conector no está activo, pedí el contenido o indicá cómo activarlo (`CONECTORES.md`); no lo supongas.

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
- **Manual de usuario** (`redactor-manual`): la conversación principal resuelve antes el alcance (funcionalidad, módulo o toda la plataforma; crear o actualizar), la URL del ambiente y el login (la persona corre `npm run login` e inicia sesión a mano, con `SESION=si` en el `.env`; nadie escribe credenciales). El agente devuelve sus dudas como `REVIEW-NNN` en "Necesito que confirmes"; las respuestas y la **aprobación explícita** de la versión final ("aprobado", no "seguí") se le pasan al mismo agente.
- **Investigar o documentar todo el proyecto** (y mantenerlo al día): la conversación principal sigue el skill `base-conocimiento`: encadena `investigador-proyecto` (profundidad `total`), `documentador-proyecto` (modo barrido y la app de punta a punta con sesión) y `redactor-manual`, y la rutina de actualización cuando cambian los requerimientos (historias, código y aplicación → qué rehacer y qué casos revisar).
- **No sabés qué probar o con qué agente/skill**: la conversación principal usa el skill `guia-pruebas` para preguntarte paso a paso y recomendar o ejecutar el agente/skill que corresponde (también es un skill de la conversación principal, porque los subagentes no pueden preguntar).
- **Correr pruebas ya automatizadas**: es `npm test` en k0lmena (sin agentes ni tokens). Los ejecutores en vivo (`ejecutor-e2e`, `ejecutor-api`) son para casos sueltos que no vale la pena automatizar.

---

## Agentes disponibles

El detalle de cada agente (skills, scripts, herramientas, conectores, entradas, salidas y qué confirma) está en `AGENTES.md`.

```
+----------------------------+------------------------------------------+---------------------------------------+
| Agente                     | Para qué sirve                           | Guarda la salida en                   |
+============================+==========================================+=======================================+
| `documentador-proyecto`    | Junta la documentación del proyecto:     | `input/documentacion/`                |
|                            | repositorio (solo lectura), historias    |                                       |
|                            | con comentarios, PRs y links, y mapa     |                                       |
|                            | funcional de la web; base del proyecto,  |                                       |
|                            | dossier por historia e índice            |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
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
| `triador-bugs`             | Busca duplicados y regresiones (Jira,    | `output/triage/`                      |
|                            | Azure DevOps, bugs locales, issues del   |                                       |
|                            | repositorio) y sugiere severidad,        |                                       |
|                            | prioridad, componente, responsable e     |                                       |
|                            | historia                                 |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `consultor-proyecto`       | Responde preguntas del producto con la   | Respuesta en el chat (+               |
|                            | documentación del proyecto, citando la   | `output/consultas/`)                  |
|                            | fuente de cada dato                      |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `guia-onboarding`          | Plan de incorporación de un QA nuevo:    | `output/onboarding/`                  |
|                            | recorrido del producto con fuentes,      |                                       |
|                            | entorno, agentes para su rol, plan de    |                                       |
|                            | las primeras semanas, preguntas y        |                                       |
|                            | checklist; HTML y Markdown               |                                       |
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
|                            | colección de Postman, Bruno o Insomnia   |                                       |
|                            | con Newman y genera el reporte HTML de   |                                       |
|                            | la corrida                               |                                       |
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
| `explorador-web`           | Pruebas exploratorias: recorre la web    | `output/exploratorias/`               |
|                            | (APP_URL del `.env` o la URL pedida) en  |                                       |
|                            | busca de links e imágenes rotas, errores |                                       |
|                            | de JavaScript y de consola, revisa el    |                                       |
|                            | responsive en varias resoluciones y      |                                       |
|                            | explora a mano con Playwright MCP; arma  |                                       |
|                            | el informe HTML con hallazgos y capturas |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-accesibilidad`   | Audita la accesibilidad (WCAG 2.2, AA)   | `output/accesibilidad/`               |
|                            | en web (axe-core, teclado, reflow,       |                                       |
|                            | revisión manual con Playwright), mobile  |                                       |
|                            | (Appium: etiquetas, objetivos táctiles,  |                                       |
|                            | TalkBack/VoiceOver) y desktop (UI        |                                       |
|                            | Automation: controles sin nombre,        |                                       |
|                            | teclado); informe HTML con criterios y   |                                       |
|                            | cómo corregir                            |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `auditor-rendimiento-web`  | Velocidad de carga con Lighthouse en     | `output/rendimiento/`                 |
|                            | mobile y desktop: puntajes, Core Web     |                                       |
|                            | Vitals (LCP, CLS, TBT), oportunidades    |                                       |
|                            | con el ahorro estimado y secuencia de    |                                       |
|                            | carga; informe HTML                      |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-fallos`          | Analiza las fallas de npm test: las      | `output/fallos/` + `output/reportes-  |
|                            | clasifica (posible bug, locator o        | bug/`                                 |
|                            | espera, ambiente, datos,                 |                                       |
|                            | automatización), detecta inestables con  |                                       |
|                            | reintentos, rescata la evidencia y       |                                       |
|                            | redacta los bugs reales; informe HTML    |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-cobertura`       | Matriz de cobertura y trazabilidad: HU,  | `output/cobertura/`                   |
|                            | criterios, casos, automatización,        |                                       |
|                            | gestión, último resultado y bugs; marca  |                                       |
|                            | los huecos (qué falta probar); informe   |                                       |
|                            | HTML                                     |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `tablero-calidad`          | Tablero de calidad por sprint o release  | `output/tablero/`                     |
|                            | (aprobados y tendencia, automatizado,    |                                       |
|                            | cobertura, bugs, inestables) con resumen |                                       |
|                            | para gerencia; informe HTML              |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `pixel-perfect`            | Regresión visual: compara cada página    | `output/pixel-perfect/`               |
|                            | contra su referencia (o el diseño) píxel |                                       |
|                            | a píxel y por elemento; dice qué se      |                                       |
|                            | corrió y cuánto, qué falta, qué es nuevo |                                       |
|                            | y qué cambió de estilo; informe HTML con |                                       |
|                            | comparador deslizable                    |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `cross-browser`            | Prueba en Chromium (Chrome, Edge),       | `output/cross-browser/`               |
|                            | Firefox y WebKit (Safari): la suite de   |                                       |
|                            | k0lmena por navegador o las páginas      |                                       |
|                            | comparadas contra el navegador base;     |                                       |
|                            | informe HTML con la matriz y las         |                                       |
|                            | diferencias                              |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `reparador-automatizacion` | Repara locators y esperas rotos de la    | `herramientas/k0lmena/web/` +         |
|                            | automatización web: diagnostica con el   | `output/reparaciones/`                |
|                            | DOM guardado al fallar, propone un       |                                       |
|                            | locator único, lo aplica con respaldo y  |                                       |
|                            | verifica; informe HTML                   |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `selector-casos-de-prueba` | Elige qué casos correr para un cambio    | `output/seleccion-casos/`             |
|                            | (git, PR, Jira, notas de la release)     |                                       |
|                            | priorizados por riesgo, con el comando   |                                       |
|                            | npm test y los cambios sin cobertura;    |                                       |
|                            | informe HTML                             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `verificador-correos`      | Verifica los correos de la app con un    | `output/correos/`                     |
|                            | buzón de prueba Mailpit: que llegue lo   |                                       |
|                            | esperado, variables sin reemplazar,      |                                       |
|                            | links, compatibilidad y vista            |                                       |
|                            | desktop/mobile; informe HTML y steps de  |                                       |
|                            | correo para k0lmena                      |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-traductor`       | Revisa cada página en cada idioma:       | `output/traductor/`                   |
|                            | textos sin traducir, claves a la vista,  |                                       |
|                            | caracteres rotos, textos cortados y      |                                       |
|                            | formatos de número y fecha; propone      |                                       |
|                            | traducciones; informe HTML               |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `revisor-casos`            | Revisa la calidad de los casos           | `output/revision-casos/`              |
|                            | existentes (puntaje, problemas,          |                                       |
|                            | duplicados, historias sin negativos,     |                                       |
|                            | tiempo de ejecución manual) y propone    |                                       |
|                            | versiones mejoradas; informe HTML        |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `generador-charters`       | Charters de pruebas exploratorias por    | `output/charters/`                    |
|                            | sesiones (hojas para imprimir, plantilla |                                       |
|                            | de notas) y el informe de las sesiones;  |                                       |
|                            | informe HTML                             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `evaluador-ux`             | Evaluación heurística de usabilidad (10  | `output/ux/`                          |
|                            | heurísticas de Nielsen): automática en   |                                       |
|                            | desktop y mobile más la revisión manual  |                                       |
|                            | de los flujos; informe HTML              |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-formularios`     | Prueba las validaciones de cada campo de | `output/formularios/`                 |
|                            | los formularios sin enviarlos            |                                       |
|                            | (obligatorios, largos, formatos,         |                                       |
|                            | límites, mensajes); informe HTML         |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-permisos`        | Inicia sesión con cada rol (más el       | `output/permisos/`                    |
|                            | anónimo) y arma la matriz rol × ruta y   |                                       |
|                            | rol × endpoint: qué abre, qué niega,     |                                       |
|                            | acceso por URL directa; compara con la   |                                       |
|                            | regla esperada; informe HTML             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-resiliencia`     | Caos del navegador (API caída o lenta,   | `output/resiliencia/`                 |
|                            | sin conexión, respuestas rotas) y caos   |                                       |
|                            | server-side con Toxiproxy (latencia/     |                                       |
|                            | caída de dependencias reales); revisa    |                                       |
|                            | cómo degrada el sistema; informe HTML    |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-logs`            | Analiza los logs de la app: agrupa       | `output/logs/`                        |
|                            | errores, arma la línea de tiempo y los   |                                       |
|                            | cruza con los escenarios fallidos de npm |                                       |
|                            | test; informe HTML                       |                                       |
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
| `pentester-web`            | Pentest web AUTORIZADO (ethical          | `output/seguridad/`                   |
|                            | hacking): intenta vulnerar un sitio      |                                       |
|                            | propio o con permiso con el escaneo      |                                       |
|                            | activo de OWASP ZAP y verificación       |                                       |
|                            | manual (OWASP Top 10) con Playwright     |                                       |
|                            | MCP; confirma cada hallazgo y arma el    |                                       |
|                            | informe con riesgo, pasos para           |                                       |
|                            | reproducir y corrección. Solo URLs de    |                                       |
|                            | SEGURIDAD_URLS_AUTORIZADAS y con         |                                       |
|                            | PENTEST_AUTORIZADO; no destructivo       |                                       |
| `probador-streaming`       | Prueba streaming y playback de video     | `output/streaming/`                   |
|                            | (cámaras IP RTSP/ONVIF, live             |                                       |
|                            | RTMP/HLS/DASH, WebRTC y VOD) con         |                                       |
|                            | ffprobe/ffmpeg: propiedades (códec,      |                                       |
|                            | resolución, FPS, bitrate, audio) y       |                                       |
|                            | continuidad (frames caídos, errores,     |                                       |
|                            | latencia); informe HTML. Solo            |                                       |
|                            | STREAMING_FUENTES_AUTORIZADAS            |                                       |
| `probador-onvif`           | Control ONVIF de una cámara IP: info del | `output/streaming/`                   |
|                            | dispositivo, perfiles y URIs de stream,  |                                       |
|                            | snapshot, PTZ (opcional) y capacidades   |                                       |
|                            | de eventos/movimiento. Devuelve la URI   |                                       |
|                            | RTSP para el probador-streaming. Solo    |                                       |
|                            | ONVIF_HOSTS_AUTORIZADOS; el PTZ mueve la |                                       |
|                            | cámara y se confirma                     |                                       |
| `calidad-imagen`           | Calidad de imagen de cámaras: captura y  | `output/streaming/calidad-*/`         |
|                            | detecta con OpenCV frames negros,        |                                       |
|                            | desenfoque y congelamiento, y con visión |                                       |
|                            | lente sucia, cámara movida, contraluz e  |                                       |
|                            | IR nocturno; compara contra una          |                                       |
|                            | referencia. Solo                         |                                       |
|                            | STREAMING_FUENTES_AUTORIZADAS            |                                       |
| `verificador-grabaciones`  | Grabaciones de una cámara o NVR por      | `output/streaming/grabaciones-*/`     |
|                            | ONVIF (Recording/Search): qué hay, rango |                                       |
|                            | cubierto, huecos y si se cumple la       |                                       |
|                            | retención esperada. Avisa si no está     |                                       |
|                            | soportado. Solo ONVIF_HOSTS_AUTORIZADOS  |                                       |
| `analista-seguridad-camaras` | Seguridad PASIVA de cámaras IP/NVR:      | `output/streaming/seguridad-camaras-*/` |
|                            | puertos abiertos, servicios inseguros    |                                       |
|                            | (Telnet, FTP, HTTP sin TLS, RTSP sin     |                                       |
|                            | auth) y firmware para revisar CVEs. No   |                                       |
|                            | prueba credenciales. Solo                |                                       |
|                            | CAMARAS_AUTORIZADAS                      |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `investigador-proyecto`    | Releva el proyecto ENTERO por MCP (Jira, | `output/investigacion/`               |
|                            | Azure DevOps, Confluence, repo, Figma):  |                                       |
|                            | resumen, módulos, flujos, integraciones, |                                       |
|                            | equipo, estado del backlog, ambigüedades |                                       |
|                            | y contradicciones con sus fuentes, y     |                                       |
|                            | preguntas priorizadas para un QA nuevo;  |                                       |
|                            | informe HTML y Markdown; deja lo         |                                       |
|                            | relevado en `input/documentacion/`       |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `redactor-manual`          | Manual de usuario basado en evidencia    | `output/manuales/` +                  |
|                            | (funcionalidad, módulo o toda la         | `input/documentacion/manual-usuario/` |
|                            | plataforma): cruza la documentación del  |                                       |
|                            | proyecto y los casos con la app          |                                       |
|                            | recorrida con Playwright (capturas),     |                                       |
|                            | marca las dudas como QA REVIEW y deja lo |                                       |
|                            | aprendido para escribir casos            |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-salesforce`      | Prueba una org de Salesforce (SANDBOX):  | `output/salesforce/`                  |
|                            | releva acceso (perfiles, permisos, OWD,  |                                       |
|                            | FLS), validaciones, flows, triggers,     |                                       |
|                            | cobertura de Apex y límites con la CLI   |                                       |
|                            | sf, deriva y corre pruebas por perfil en |                                       |
|                            | Lightning; informe HTML. Nunca           |                                       |
|                            | producción; no toca metadata             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-billeteras`      | Prueba billeteras virtuales y pagos en   | `output/billeteras/`                  |
|                            | sandbox: conservación del saldo, estados |                                       |
|                            | de transacción, idempotencia, doble      |                                       |
|                            | gasto y concurrencia, límites, KYC/AML,  |                                       |
|                            | conciliación con la pasarela y seguridad |                                       |
|                            | de tokens; informe HTML. Dinero y        |                                       |
|                            | tarjetas de prueba, nunca reales         |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-shopify`         | Prueba una tienda Shopify: releva en     | `output/shopify/`                     |
|                            | solo lectura la vidriera (tema, errores  |                                       |
|                            | de Liquid, políticas, catálogo) y la     |                                       |
|                            | Admin API (productos y stock, mercados,  |                                       |
|                            | envíos, descuentos, webhooks) y Theme    |                                       |
|                            | Check; prueba checkout con Bogus Gateway |                                       |
|                            | o modo de prueba en mobile y desktop;    |                                       |
|                            | informe HTML                             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-wordpress`       | Prueba WordPress / WooCommerce: releva   | `output/wordpress/`                   |
|                            | en solo lectura la vidriera, la REST API |                                       |
|                            | de WooCommerce (plugins y templates      |                                       |
|                            | desactualizados, pasarelas y su modo,    |                                       |
|                            | envíos, cupones, webhooks, cron) y WP-   |                                       |
|                            | CLI; prueba checkout, pagos de prueba,   |                                       |
|                            | envíos, cupones, correos y roles;        |                                       |
|                            | informe HTML                             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-prestashop`      | Prueba PrestaShop (1.6/1.7/8.x): releva  | `output/prestashop/`                  |
|                            | en solo lectura la vidriera y la         |                                       |
|                            | Webservice API (productos y stock,       |                                       |
|                            | combinaciones, transportistas, zonas,    |                                       |
|                            | monedas, vales, multistore y configs de  |                                       |
|                            | rendimiento) y, con --local, versión y   |                                       |
|                            | modo dev; prueba smoke local, checkout,  |                                       |
|                            | pagos de prueba, stock, redondeo y       |                                       |
|                            | rendimiento; informe HTML                |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-vtex`            | Prueba VTEX: releva en solo lectura la   | `output/vtex/`                        |
|                            | vidriera y el Catalog System público     |                                       |
|                            | (SKUs, precio, stock) y, con app de      |                                       |
|                            | lectura, canales de venta, envíos        |                                       |
|                            | (SLAs) y promociones; prueba smoke en    |                                       |
|                            | workspace de QA, checkout/orderForm,     |                                       |
|                            | pagos sandbox, canales, promos y OMS;    |                                       |
|                            | informe HTML                             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-sap`             | Prueba SAP (S/4HANA o ECC) en mandante   | `output/sap/`                         |
|                            | de QA: SAP GUI (T-codes con Scripting    |                                       |
|                            | API) y Fiori/UI5 (OData), autorizaciones |                                       |
|                            | y roles (PFCG/SU53/SoD), procesos O2C/   |                                       |
|                            | P2P/R2R de punta a punta; smoke,         |                                       |
|                            | regresión tras transporte, rendimiento   |                                       |
|                            | y seguridad; informe HTML                |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-desktop`         | Prueba apps de escritorio Windows        | `output/desktop/`                     |
|                            | (WinForms/WPF/UWP/Electron/Java/Qt):     |                                       |
|                            | releva el árbol de controles (pywinauto) |                                       |
|                            | y prueba con Appium+WinAppDriver,        |                                       |
|                            | pywinauto o Playwright (Electron);       |                                       |
|                            | funcional, instalación, archivos, SO,    |                                       |
|                            | regresión, rendimiento y seguridad;      |                                       |
|                            | informe HTML                             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-mobile`          | Prueba apps móviles (Android/iOS;        | `output/mobile/`                      |
|                            | nativa/híbrida/web) en vivo con Appium:  |                                       |
|                            | funcional, permisos, interrupciones,     |                                       |
|                            | offline, deep links y push, ciclo de     |                                       |
|                            | vida, compatibilidad de OS/pantallas,    |                                       |
|                            | rendimiento y seguridad móvil (MASVS);   |                                       |
|                            | informe HTML                             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-dependencias`    | SCA de dependencias: corre npm audit /   | `output/dependencias/`                |
|                            | pip-audit / osv-scanner, agrega los CVE  |                                       |
|                            | por severidad, directas vs. transitivas, |                                       |
|                            | fix disponible y licencias; informe HTML |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-codigo-seguro`   | SAST y secretos: escáner de secretos     | `output/sast/`                        |
|                            | integrado + semgrep, triage de falsos    |                                       |
|                            | positivos, mapeo a OWASP/CWE; secretos   |                                       |
|                            | redactados a rotar; informe HTML         |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `revisor-codigo`           | Code review estático de un repo, rama o  | `output/revision-codigo/`             |
|                            | PR/MR (GitHub, GitLab, Bitbucket, Azure  |                                       |
|                            | Repos o cualquier git): seguridad,       |                                       |
|                            | performance, confiabilidad, malas        |                                       |
|                            | prácticas y mantenibilidad; decisión     |                                       |
|                            | sugerida, informe HTML y comentarios     |                                       |
|                            | para el PR                               |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-ia`              | Prueba funciones de IA/LLM (chatbot,     | `output/ia/`                          |
|                            | RAG, agente): golden set y evals,        |                                       |
|                            | alucinaciones y grounding, seguridad de  |                                       |
|                            | prompt (injection/jailbreak), formato,   |                                       |
|                            | robustez, latencia y costo; informe HTML |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-mensajeria`      | Prueba mensajería/eventos (Kafka,        | `output/mensajeria/`                  |
|                            | RabbitMQ, SQS/SNS, MQTT, WebSocket,      |                                       |
|                            | SSE): entrega, orden, idempotencia,      |                                       |
|                            | DLQ y reintentos, esquemas, consumer     |                                       |
|                            | lag y outbox; publica/consume con la     |                                       |
|                            | herramienta; informe HTML                |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-soap`            | Prueba servicios SOAP desde el WSDL:     | `output/soap/`                        |
|                            | operaciones, validación XSD, SOAP        |                                       |
|                            | Faults, namespaces/SOAPAction, WS-       |                                       |
|                            | Security e idempotencia; envía los       |                                       |
|                            | sobres con ejecutor-api; informe HTML    |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-scalar`          | APIs en Scalar: MCP de la API, contrato  | `output/scalar/`                      |
|                            | del Registry, casos como colección con   |                                       |
|                            | tests pm (corre con Newman) e            |                                       |
|                            | importación a Scalar (x-post-response);  |                                       |
|                            | publica solo con confirmación            |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-contratos`       | Contract testing (Pact): consumer-       | `output/contratos/`                   |
|                            | driven y bi-direccional para REST,       |                                       |
|                            | GraphQL, gRPC y eventos; verificación,   |                                       |
|                            | can-i-deploy y compatibilidad; informe   |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-seo`             | SEO y GEO: indexabilidad, on-page,       | `output/seo/`                         |
|                            | datos estructurados, hreflang y acceso   |                                       |
|                            | de crawlers de IA; releva con npm run    |                                       |
|                            | seo; informe HTML                        |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-datos`           | Datos y pipelines (ETL): calidad,        | `output/datos/`                       |
|                            | reconciliación origen↔destino, esquema,  |                                       |
|                            | transformaciones e idempotencia; solo    |                                       |
|                            | lectura con verificador-datos; informe   |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-dynamics`        | Dynamics 365 y otros CRM/ERP (sandbox):  | `output/dynamics/`                    |
|                            | roles, lógica (flows/plugins/BPF/roll-   |                                       |
|                            | ups), procesos end-to-end; Web API de    |                                       |
|                            | lectura + Playwright por rol; informe    |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-blockchain`      | Blockchain/Web3 y smart contracts        | `output/blockchain/`                  |
|                            | (testnet/local): funcional, tokens,      |                                       |
|                            | gas, seguridad (reentrancy, acceso,      |                                       |
|                            | oráculos), Hardhat/Foundry; informe      |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-ivr`             | Voz/IVR y voicebots: árbol de menús      | `output/ivr/`                         |
|                            | (DTMF/voz), prompts, enrutamiento y      |                                       |
|                            | colas, telefonía y cumplimiento (PCI);   |                                       |
|                            | informe HTML                             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-juegos`          | Videojuegos (Unity/Unreal/Godot/HTML5/   | `output/juegos/`                      |
|                            | mobile): mecánicas, guardado,            |                                       |
|                            | compatibilidad, rendimiento,             |                                       |
|                            | multijugador, monetización y             |                                       |
|                            | exploratorias; informe HTML              |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-pos`             | Punto de venta (POS) y hardware: venta,  | `output/pos/`                         |
|                            | pagos y periféricos, fiscal, offline y   |                                       |
|                            | conciliación, cierres de caja; informe   |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-observabilidad`  | Observabilidad: valida logs (trace id,   | `output/observabilidad/`              |
|                            | sin PII), métricas (Prometheus, RED/USE),|                                       |
|                            | trazas (OTel), healthchecks (liveness/   |                                       |
|                            | readiness), SLOs y alertas; informe HTML |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-busqueda`        | Búsqueda y relevancia (Elastic/Algolia/  | `output/busqueda/`                    |
|                            | Solr/DB): ranking, typos, sinónimos,     |                                       |
|                            | facetas, indexación y golden set con     |                                       |
|                            | precision@k/nDCG; informe HTML           |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `probador-documentos`      | Documentos generados (PDF/Excel/CSV):    | `output/documentos/`                  |
|                            | datos y totales, placeholders sin        |                                       |
|                            | reemplazar, formato/locale, layout,      |                                       |
|                            | metadata y seguridad; informe HTML       |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `revisor-contenido`        | Contenido y typos (idioma principal):    | `output/contenido/`                   |
|                            | ortografía, placeholders, claves i18n a  |                                       |
|                            | la vista, duplicados y consistencia de   |                                       |
|                            | microcopy; informe HTML                  |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
| `analista-mutacion`        | Mutation testing: mide la calidad real   | `output/mutacion/`                    |
|                            | de la suite (Stryker/mutmut/PITest),     |                                       |
|                            | mutation score por archivo, mutantes     |                                       |
|                            | sobrevivientes vs. equivalentes y el     |                                       |
|                            | test que falta; informe HTML             |                                       |
+----------------------------+------------------------------------------+---------------------------------------+
```

---

## Estándares de QA del proyecto

Estos principios aplican a **todos** los agentes:

- **No inventar.** Si falta información para hacer bien la tarea (un paso, un dato, una regla de negocio, un resultado esperado), el agente lo **marca y lo pregunta**; nunca rellena con suposiciones disfrazadas de hechos. Es preferible un artefacto con huecos señalados que uno completo pero inventado.
- **Investigar antes de suponer.** Antes de analizar, planificar, escribir casos o automatizar una historia, se revisa su contexto completo con el skill `investigacion-contexto`: primero la documentación del proyecto de `input/documentacion/` (la arma el `documentador-proyecto`: índice, dossier de la historia, reglas del código, mensajes, mapa funcional; la completan el `investigador-proyecto` con lo relevado de los tableros y la wiki, y el `redactor-manual` con cómo se usa la app, verificado; cada documento declara su confiabilidad: `confirmado`, `borrador`, `investigacion` o `sin-confirmar`), y después la historia de Jira con **todos** sus comentarios, subtareas, épica e issues vinculados, las páginas de Confluence y los diseños de Figma relacionados, contratos y `input/`. El resultado queda en una ficha reutilizable `output/contexto/contexto-HU-XXX.md`.
- **Marcar lo que falta.** Lo que no aparece en ninguna fuente se registra como **Falta información** con un ID por historia (`FI-01`, `FI-02`, …) y viaja con ese ID a todos los artefactos: casos (resaltados, etiqueta `@falta-info`, hoja *Falta información*), `.feature` (`@falta-info @FI-01`), coberturas, mapeos, reportes de ejecución, informe de cierre y lo que se publica en Xray/QMetry/AIO. En los `analisis.json` y `_resultados-*.json` de los informes HTML va como `falta_informacion: [{"id": "FI-01", "que_falta": "…", "pregunta": "…"}]`.
- **Respetar los formatos.** Los campos, su orden y sus valores permitidos los define la plantilla (o el script), no el agente.
- **Trazabilidad.** Todo artefacto referencia la historia (`HU-XXX`) o el contrato del que sale.
- **Cobertura pensada.** Los casos contemplan escenarios positivos, negativos, de borde y validaciones de campos, no solo el camino feliz.
- **Claridad.** Títulos descriptivos, pasos accionables y sin ambigüedad, lenguaje claro y profesional.

## Convenciones de IDs

- Historias de usuario: `HU-001`, `HU-002`, …
- Criterios de aceptación: `CA1`, `CA2`, … (dentro de cada historia)
- Casos de prueba manuales: `CP-001`, `CP-002`, … (numeración **por historia**; si la historia ya tiene casos —manuales, BDD, automatización o gestión—, se conservan sus IDs y los nuevos siguen desde el último). Los escenarios BDD usan la **misma** numeración como tag `@CP-XXX`, y la `Feature` lleva `@HU-XXX`: el par `@HU` + `@CP` identifica cada caso en la automatización, la gestión y los resultados. Un `Scenario Outline` es un solo caso (un solo `@CP`).
- Casos de prueba de API: `CP-API-001`, `CP-API-002`, … (numeración por historia, o por contrato si no hay historia)
- Bugs: `BUG-001`, `BUG-002`, …
- Falta información: `FI-01`, `FI-02`, … (por historia; tags `@falta-info @FI-01`)
- Historia en nombres de archivo: el `HU-XXX` si existe (`contexto-HU-001.md`, `casos-HU-001…`, campo **Historia** de los bugs); si la historia solo tiene key de la herramienta, la key (`contexto-PROJ-12.md`). El dossier de `input/documentacion/historias/` va por key y lleva los dos IDs en su encabezado `historia:`.

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
- `scripts/correr_newman.py` → corre una colección de Postman, Bruno o Insomnia con el token y la URL del `.env` (`--datos` para iterar con un CSV/JSON) y genera su reporte (`ejecutor-api`); un request sin `pm.test` queda Bloqueado ("Sin validaciones").
- `scripts/recolectar_resultados.py` → junta los resultados de una historia (ejecuciones en vivo, `npm test` con su `historial/`, bugs, performance y seguridad) para el informe de cierre; cada caso (historia + ID) vale por su resultado más reciente.
- `scripts/doctor.py` → revisa el entorno y la configuración por secciones (Python, Node y k0lmena, herramientas, fuentes, `.env`, integraciones, conectores, git y extras), sin mostrar secretos. `--seccion env,integraciones`, `--rapido` (sin red ni Docker) y `--json`.
- `scripts/generar_informe_exploratorio.py` → arma el informe HTML de pruebas exploratorias desde el `exploracion.json` de `npm run explorar` (`explorador-web`).
- `scripts/generar_informe_accesibilidad.py` → arma el informe HTML de accesibilidad desde el `auditoria.json` de `npm run accesibilidad` (`analista-accesibilidad`).
- `scripts/generar_informe_rendimiento.py` → arma el informe HTML de rendimiento web desde el `rendimiento.json` de `npm run rendimiento` (`auditor-rendimiento-web`).
- `scripts/analizar_fallos.py` → clasifica las fallas de `npm test`, compara con reintentos y genera el informe (`analista-fallos`).
- `scripts/analizar_cobertura.py` → arma la matriz de cobertura y trazabilidad por historia y genera el informe (`analista-cobertura`).
- `scripts/generar_informe_correos.py` y `generar_informe_traductor.py` → los informes HTML de `npm run correos` (Mailpit) y `npm run traductor` (`verificador-correos`, `analista-traductor`).
- `scripts/estimacion.py` → **tiempo estimado de ejecución manual** de cada caso (fórmula en `plantillas/estimacion-tiempos.md`): va en la planilla de casos, en la herramienta de gestión al subirlos (descripción y Original Estimate / estimatedTime / estimatedEffort), en la selección y en la revisión.
- `scripts/revisar_casos.py`, `generar_charters.py` y `analizar_logs.py` (con sus `generar_informe_*`) → revisión de casos, charters exploratorios y análisis de logs; `generar_informe_ux.py` y `generar_informe_formularios.py` → los informes de `npm run ux` y `npm run formularios`.
- `scripts/_historial.py` (y `herramientas/k0lmena/tools/historial/`) → guardan las últimas 5 corridas de cada herramienta y arman la sección de evolución de los informes.
- `scripts/indice_documentacion.py` → arma `input/documentacion/INDICE.md` (qué documentación hay, sus fuentes y si está vigente); `npm run mapa-funcional`, el mapa funcional de la web (`documentador-proyecto`): con la sesión de `npm run login` (`SESION`) recorre también las pantallas privadas, guarda los **locators sugeridos** de cada pantalla (los usa el `web-mapper`) y compara con el recorrido anterior (*Cambios desde el recorrido anterior*: pantallas, campos, reglas y botones).
- `scripts/cambios_documentacion.py` → documentación incremental: guarda en `input/documentacion/.estado.json` qué se documentó (commit por repositorio, fuentes de cada documento, fecha de cada historia) y, con los archivos que cambiaron, dice qué documentos rehacer y qué casos revisar (`cambios.md`); con `historias --actual <lista>` compara las historias del alcance con las documentadas (nuevas, cambiadas porque cambió el requerimiento o sus PRs, o solo de estado: por la **huella** del contenido no se rehacen) y lista sus casos para revisar (`cambios-historias.md`).
- `scripts/actualizar_conocimiento.py` (`npm run actualizar-conocimiento`) → actualización de la base de conocimiento para correr sola: aplicación (mapa funcional y sus cambios) y código (`git fetch` + `cambios`) sin tokens; con `--con-agente`, las historias con el `documentador-proyecto` por `claude -p` con tope de gasto; resumen en `output/conocimiento/` y aviso a Slack/Teams si algo cambió. `--programar lunes|diario` la deja en el Programador de tareas (o da la línea de cron).
- `scripts/generar_informe_permisos.py` y `generar_informe_resiliencia.py` → los informes de `npm run permisos` y `npm run resiliencia` (`probador-permisos`, `probador-resiliencia`).
- `herramientas/resiliencia/toxiproxy.py` (`npm run toxiproxy`) → caos server-side con Toxiproxy (latencia, caída y lentitud de dependencias reales por su API REST; solo stdlib) para el `probador-resiliencia`; complementa el caos del lado del navegador. Solo QA, con `reset` al terminar.
- `scripts/generar_informe_streaming.py` y `generar_informe_onvif.py` → los informes de `npm run streaming` (ffprobe/ffmpeg: propiedades, continuidad, estabilidad y carga) y `npm run onvif` (control ONVIF: perfiles, snapshot, PTZ, eventos) (`probador-streaming`, `probador-onvif`).
- `scripts/generar_informe_calidad.py`, `generar_informe_grabaciones.py` y `generar_informe_seguridad_camaras.py` → los informes de `npm run calidad-imagen` (OpenCV + visión), `npm run grabaciones` (ONVIF Recording) y `npm run seguridad-camaras` (escaneo pasivo) (`calidad-imagen`, `verificador-grabaciones`, `analista-seguridad-camaras`).
- `herramientas/salesforce/inventario.py` (`npm run salesforce`) y `scripts/generar_informe_salesforce.py` → inventario de QA de una org de Salesforce (sandbox) en solo lectura con la CLI `sf` (perfiles, validaciones, flows, triggers, cobertura de Apex, sharing, límites) e informe HTML (`probador-salesforce`).
- `scripts/generar_informe_billeteras.py` → informe HTML de billeteras y pagos (hallazgos, pruebas, conservación del saldo y conciliación) desde el `analisis.json` que arma el agente (`probador-billeteras`).
- `herramientas/ecommerce/shopify.py` (`npm run shopify`), `herramientas/ecommerce/wordpress.py` (`npm run wordpress`), `herramientas/ecommerce/prestashop.py` (`npm run prestashop`), `herramientas/ecommerce/vtex.py` (`npm run vtex`) y `scripts/generar_informe_ecommerce.py` → relevamiento funcional de solo lectura de tiendas Shopify (vidriera, Admin API de lectura, Theme Check), WordPress / WooCommerce (vidriera, REST API de lectura, WP-CLI), PrestaShop (vidriera, Webservice API de lectura, versión y modo dev de la instalación local) y VTEX (vidriera, Catalog System público, y canales de venta, envíos y promociones con app de lectura), con hallazgos, sugerencias de prueba e informe HTML (`probador-shopify`, `probador-wordpress`, `probador-prestashop`, `probador-vtex`). Solo `ECOMMERCE_URLS_AUTORIZADAS`.
- `herramientas/sap/sap_gui.py` (`npm run sap`) y `scripts/generar_informe_sap.py` → relevamiento de solo lectura de una sesión de SAP GUI for Windows por la Scripting API (sistema, mandante, usuario, transacción) e informe HTML del probador de SAP (GUI y Fiori): hallazgos, pruebas, autorizaciones y procesos de negocio (`probador-sap`). Requiere `pywin32` (opcional, solo Windows).
- `herramientas/desktop/controles.py` (`npm run desktop`) y `scripts/generar_informe_desktop.py` → relevamiento de solo lectura del árbol de controles de una app de escritorio de Windows (pywinauto, UI Automation) e informe HTML del probador de escritorio: hallazgos, pruebas y compatibilidad (`probador-desktop`). Requiere `pywinauto` (opcional, solo Windows).
- `scripts/generar_informe_mobile.py` → informe HTML del probador de apps móviles (Android/iOS): hallazgos, pruebas por dispositivo y compatibilidad, desde el `analisis.json` que arma el agente con Appium (`probador-mobile`, conector `appium`).
- `herramientas/seguridad/dependencias.py` (`npm run dependencias`) y `scripts/generar_informe_dependencias.py` → SCA de dependencias de solo lectura (npm audit / pip-audit / osv-scanner), CVEs por severidad e informe HTML (`analista-dependencias`).
- `herramientas/seguridad/sast.py` (`npm run sast`) y `scripts/generar_informe_sast.py` → SAST y búsqueda de secretos de solo lectura (escáner de secretos integrado + semgrep si está) e informe HTML (`analista-codigo-seguro`). Complementan el análisis dinámico de `herramientas/zap` (DAST).
- `herramientas/codigo/obtener.py` (`npm run obtener-codigo`), `herramientas/codigo/revision.py` (`npm run revision-codigo`) y `scripts/generar_informe_revision_codigo.py` → code review estático de solo lectura (`revisor-codigo`): trae el código de GitHub, GitLab, Bitbucket, Azure Repos, Gitea o cualquier git (o una carpeta local) sin ejecutar nada del repo, calcula el diff de un PR/MR contra el merge-base, corre reglas por lenguaje (seguridad, performance, confiabilidad, malas prácticas), métricas de mantenibilidad, duplicados, secretos y semgrep/ruff/bandit si están; informe HTML y `comentarios-pr.md` para pegar en el PR. Tokens de solo lectura del `.env` (`GITHUB_TOKEN`, `GITLAB_TOKEN`, `BITBUCKET_TOKEN`, `ADO_PAT`, `REVISION_GIT_TOKEN`).
- `scripts/generar_informe_ia.py` → informe HTML del probador de funciones de IA/LLM (golden set/evals, alucinaciones y grounding, seguridad de prompt, métricas), desde el `analisis.json` que arma el agente (`probador-ia`).
- `herramientas/mensajeria/mensajeria.py` (`npm run mensajeria`) y `scripts/generar_informe_mensajeria.py` → pruebas de mensajería/eventos (Kafka, RabbitMQ, MQTT, WebSocket, SSE): publicar/consumir/inspeccionar y verificar orden, duplicados y esquema, con informe HTML (`probador-mensajeria`). Librerías de broker opcionales (import perezoso).
- `herramientas/soap/wsdl.py` (`npm run soap`) y `scripts/generar_informe_soap.py` → relevamiento de un servicio SOAP por su WSDL (operaciones, endpoint, versión, sobre de ejemplo; solo `xml` de la stdlib) e informe HTML del probador de SOAP (`probador-soap`).
- `herramientas/scalar/scalar.py` (`npm run scalar`) → Scalar (`probador-scalar`): `descargar` (OpenAPI del Registry a `input/api/scalar/`), `listar`, `coleccion` (Postman v2.1 con un request por caso y tests `pm`: corre con `correr_newman.py` y se importa en el cliente de Scalar), `enriquecer` (OpenAPI con ejemplos por caso y `x-post-response`), `validar` y `publicar` (con `@scalar/cli`; solo con `--confirmar`, versión nueva y privada). El MCP de la API es el conector `scalar`.
- `scripts/resumir_graphql.py` y los skills `pruebas-graphql` y `pruebas-grpc` → soporte de **GraphQL y gRPC** de la familia de API (`ejecutor-api`, `api-mapper`, `generador-casos-api`): introspección/schema, errores parciales, autorización por campo y, en gRPC, Protobuf, modos de RPC, status codes y compatibilidad; WebSocket se cubre en `pruebas-async` (`probador-mensajeria`).
- `scripts/generar_informe_generico.py` → informe HTML genérico (mismo estilo de la casa) para los probadores sin informe propio: lo usan `probador-contratos`, `analista-seo`, `probador-datos`, `probador-dynamics`, `probador-blockchain`, `probador-ivr`, `probador-juegos` y `probador-pos`, a partir de su `analisis.json`.
- `herramientas/mutacion/mutacion.py` (`npm run mutacion`) → lee el reporte de mutation testing (Stryker JSON): mutation score global y por archivo, mutantes sobrevivientes y archivos bajo el umbral (`analista-mutacion`); el informe, con `generar_informe_generico.py`.
- `herramientas/observabilidad/observabilidad.py` (`npm run observabilidad`) → healthchecks y métricas (Prometheus) de un servicio, solo lectura (`analista-observabilidad`); el informe, con `generar_informe_generico.py`.
- `herramientas/documentos/documentos.py` (`npm run documentos`) → extrae texto/metadata de un PDF (pypdf) y hojas/celdas de un Excel (openpyxl) y detecta placeholders sin reemplazar (`probador-documentos`).
- `herramientas/contenido/contenido.py` (`npm run contenido`) → revisión de contenido/typos por heurística (placeholders, duplicados, claves i18n a la vista, Lorem ipsum) y LanguageTool opcional (`revisor-contenido`).
- `herramientas/seo/seo.py` (`npm run seo`) → relevamiento de SEO/GEO de una página (solo `urllib`/regex de la stdlib): on-page, datos estructurados, hreflang, robots/sitemap y acceso de los crawlers de IA (`analista-seo`).
- `scripts/generar_informe_investigacion.py` → el paquete del relevamiento de un proyecto completo: web HTML con **mapas conceptuales** (arquitectura y cómo funciona) y el árbol de épicas/historias/tareas, `resumen.md` breve y `presentacion-investigacion.html` (imprime a PDF), con comparación contra el relevamiento anterior (`investigador-proyecto`). Además deja lo relevado como documentación del proyecto en `input/documentacion/proyecto/investigacion/` (`--sin-input` para no hacerlo) y regenera el índice.
- `herramientas/manual/manual.py` (`npm run manual`) → la herramienta del manual de usuario (`redactor-manual`): `preparar`/`estado` (carpetas y versiones), `captura` (mueve y valida las capturas de Playwright MCP), `html` (autocontenido, con las capturas embebidas), `word` (diseño de k0lmena con las fuentes de la casa embebidas; firma con `MANUAL_EQUIPO`), `verificar` (checklist antes de la versión final), `plataforma` (plan por módulos) y `a-input` (el manual, sin marcas internas y con los REVIEW como *Sin confirmar*, a `input/documentacion/manual-usuario/`). `scripts/indice_documentacion.py` reconoce los tipos `investigacion` y `manual-usuario` y muestra la confiabilidad de cada documento.
- `scripts/buscar_duplicados.py` → similitud entre bugs para el `triador-bugs` (duplicados, regresiones, relacionados).
- `scripts/metricas_tokens.py` → **uso de tokens** de los agentes: lee las transcripciones de Claude Code del proyecto (solo conteos, nunca el texto), atribuye el uso a cada agente y estima el costo por agente, día y modelo con oportunidades (qué conviene automatizar en k0lmena); lo suma el tablero de calidad.
- `scripts/generar_onboarding.py` → el plan de onboarding del `guia-onboarding` (HTML con checklist y Markdown).
- `scripts/tablero_calidad.py` → tablero de calidad por sprint o release (`tablero-calidad`).
- `scripts/portal_informes.py` → `output/index.html` con el último informe de cada herramienta, buscador y filtros por herramienta, historia, estado y fecha, y vista por herramienta o por historia; se regenera solo al terminar cualquier informe (`K0LMENIA_PORTAL=0` lo desactiva).
- `scripts/avisar.py` → avisos a Slack y Teams por webhook (`SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL`); `--desde-cucumber` resume un `npm test`. Sin webhook no manda nada.
- `npm run monitorear` (k0lmena `tools/monitoreo`) y `scripts/generar_informe_monitoreo.py` → monitoreo sintético de solo lectura (URLs, textos, tiempos, certificado y escenarios `@sintetico`); avisa solo cuando algo se rompe o se recupera. Se programa con `.github/workflows/monitoreo.yml`, cron o el Programador de tareas.
- `scripts/convertir_coleccion.py` → convierte colecciones de Bruno (carpeta con `bruno.json`) e Insomnia (v4 `.json` / v5 `.yaml`) a Postman v2.1, con las advertencias de lo que no se pudo convertir (`correr_newman.py` lo usa solo). `scripts/resumir_graphql.py` → resume un schema GraphQL (introspección por URL, SDL o JSON). `scripts/resumir_openapi.py` → resume un Swagger 2.0 / OpenAPI 3.x (JSON o YAML): `API_BASEURL` con su basePath, el step de autenticación de cada securityScheme, parámetros, body de ejemplo y status documentados.
- `scripts/evaluar_agentes.py` → **evals de los agentes** (`evals/`): casos con trampas deliberadas que corren en un workspace aislado con `claude -p` y se verifican con chequeos determinísticos; informe con el puntaje por agente y las regresiones. **Gastan tokens** (tope por caso); `--solo-verificar` revisa salidas ya generadas.
- `scripts/seleccionar_casos.py` → elige y prioriza los casos a correr para un cambio y genera el informe (`selector-casos-de-prueba`).
- `scripts/generar_informe_pixel_perfect.py`, `generar_informe_cross_browser.py` y `generar_informe_reparacion.py` → los informes HTML de `npm run pixel-perfect`, `npm run cross-browser` y `npm run reparar` (`pixel-perfect`, `cross-browser`, `reparador-automatizacion`).
- **Tests del repo**: `python -m pytest tests` y `npm run test:repo` (también corren en CI, en Ubuntu y Windows).

---

## Nombres de archivos de salida (sugerencia)

- Documentación del proyecto (`documentador-proyecto`, no se versiona): `input/documentacion/` con `INDICE.md`, `proyecto/` (resumen, repositorio, reglas de negocio, mensajes, estados y permisos, mapa funcional, links), `api/` y `historias/<HU o key>/dossier.md`.
- Ficha de contexto: `output/contexto/contexto-HU-001.md` (fuentes consultadas, hallazgos y Falta información)
- Análisis de historia: `analisis-HU-001.md`
- Casos manuales: `casos-HU-001.xlsx` + `casos-HU-001.md` + `casos-HU-001-cobertura.md` (cada caso con su tiempo estimado de ejecución manual)
- Casos BDD: `HU-001-registro.feature` + `HU-001-cobertura.md`
- Reporte de bug: `BUG-001.md`
- Seguridad web: `output/seguridad/<HU o host>/<fecha>/` con `zap.json`, `analisis.json` e `informe-seguridad.html`
- Pruebas exploratorias: `output/exploratorias/<HU o host>/` con `exploracion.json`, `analisis.json`, `informe-exploratorio.html`, `capturas/` y `videos/`. La corrida anterior pasa a `historial/` (últimas 5).
- Accesibilidad: `output/accesibilidad/<HU o host>/` con `auditoria.json`, `analisis.json`, `informe-accesibilidad.html`, `capturas/` y `videos/`. La corrida anterior pasa a `historial/` (últimas 5).
- Rendimiento web: `output/rendimiento/<HU o host>/` con `rendimiento.json`, `analisis.json`, `informe-rendimiento.html`, `capturas/` y `lighthouse/`. La corrida anterior pasa a `historial/` (últimas 5).
- Análisis de fallos: `output/fallos/<HU o suite>/` con `fallos.json`, `informe-fallos.html`, `corridas/` y `evidencia/`.
- Cobertura y trazabilidad: `output/cobertura/<HU o todas>/` con `cobertura.json` e `informe-cobertura.html`.
- Regresión visual: `output/pixel-perfect/<HU o host>/` con `referencia/` (se conserva entre corridas), `actual/`, `diferencias/`, `recortes/`, `pixel-perfect.json`, `analisis.json` e `informe-pixel-perfect.html`. La comparación anterior pasa a `historial/` (últimas 5).
- Cross-browser: `output/cross-browser/<HU, host o suite>/` con `cross-browser.json`, `informe-cross-browser.html`, `capturas/`, `diferencias/` y `suite/` (el reporte de Cucumber de cada navegador).
- Reparación de la automatización: `output/reparaciones/<HU o suite>/` con `reparaciones.json`, `informe-reparacion.html`, `capturas/`, `cambios.diff` y `respaldo/`.
- Revisión de casos: `output/revision-casos/<HU o nombre>/` con `revision.json` e `informe-revision.html`.
- Charters exploratorios: `output/charters/<HU o nombre>/` con `charters.json`, `charters.html`, `charters.md`, `sesiones/CH-XX.md` e `informe-sesiones.html`.
- Usabilidad: `output/ux/<HU o host>/` con `ux.json`, `analisis.json`, `informe-ux.html`, `capturas/` y `recortes/`. La corrida anterior pasa a `historial/` (últimas 5).
- Formularios: `output/formularios/<HU o host>/` con `formularios.json`, `analisis.json`, `informe-formularios.html` y `capturas/`. La corrida anterior pasa a `historial/` (últimas 5).
- Logs: `output/logs/<nombre>/` con `logs.json`, `analisis.json` e `informe-logs.html` (los logs de entrada, en `input/logs/`). El análisis anterior pasa a `historial/` (últimos 5).
- Correos: `output/correos/<HU o buzón>/` con `correos.json`, `analisis.json`, `informe-correos.html`, `capturas/` (desktop y mobile) y `eml/`. La corrida anterior pasa a `historial/` (últimas 5).
- Traducciones: `output/traductor/<HU o host>/` con `traductor.json`, `analisis.json`, `informe-traductor.html`, `capturas/` y `recortes/`. La corrida anterior pasa a `historial/` (últimas 5).
- **Historial**: Cada herramienta guarda sus **últimas 5 corridas** con su evidencia en `historial/` (dentro de su carpeta de salida; la de `npm test`, en `herramientas/k0lmena/reports/<suite>/historial/`) y cada informe trae la sección **Evolución de las corridas**: qué es nuevo, qué se resolvió, qué sigue y cómo evolucionan los indicadores, con el link al informe de cada corrida.
- Permisos por rol: `output/permisos/<HU o host>/` con `permisos.json`, `analisis.json`, `informe-permisos.html` y `capturas/`. La corrida anterior pasa a `historial/` (últimas 5).
- Resiliencia: `output/resiliencia/<HU o host>/` con `resiliencia.json`, `informe-resiliencia.html` y `capturas/`. La corrida anterior pasa a `historial/` (últimas 5).
- Triage de bugs: `output/triage/<bug o lote>/` con `candidatos.json`, `triage.json` y `triage.md`. Consultas: `output/consultas/<tema>.md` (opcional).
- Tablero de calidad: `output/tablero/<nombre>/` con `tablero.json`, `analisis.json` e `informe-tablero.html`. Portal de informes: `output/index.html`.
- Monitoreo sintético: `output/monitoreo/<nombre>/` con `monitoreo.json`, `informe-monitoreo.html` e `historial/` (30 corridas).
- Evals: `evals/resultados/<fecha>/` con `resultados.json` e `informe-evals.html` (no se versiona).
- Uso de tokens: `output/metricas-tokens/<nombre>/` con `metricas.json` e `informe-metricas.html`. Onboarding: `output/onboarding/<persona>/` (nombre en minúsculas, sin acentos y con guiones) con `plan.json`, `plan-onboarding.html` y `plan-onboarding.md`.
- E-commerce: `output/shopify/<HU o host>/` y `output/wordpress/<HU o host>/` con `<plataforma>.json`, `analisis.json`, `informe-<plataforma>.html` y `capturas/`. La corrida anterior pasa a `historial/` (últimas 5).
- Selección de casos: `output/seleccion-casos/<nombre>/` con `seleccion.json`, `seleccion.csv` (lo manual) e `informe-seleccion.html`; el cambio que arma el agente va en `output/seleccion-casos/_cambios-<nombre>.json` (fuera de la carpeta de la corrida, que se archiva al repetirla).
- Manual de usuario: `output/manuales/<slug>/` con `capturas/NN-descripcion.png`, `borradores/<slug>-v0.N.md` (+ `.html`, `.docx` a pedido), `revision/evidencia.md` y `revision/qa-review.md`, y `versiones/<slug>-v1.0.md` (solo con aprobación); el conocimiento, en `input/documentacion/manual-usuario/<slug>.md`. Plan de la plataforma: `output/manuales/plataforma/` con `menu.json`, `indice.json` e `indice.md`.
- Datos de prueba: `datos-HU-001.md` (o `.csv`)
- Casos de API: `casos-api-HU-001.md` (o `casos-api-<tema>.md` si no salen de una historia)
- Mapeo a automatización: `herramientas/k0lmena/<web|api|mobile>/features/HU-001-<slug>.feature` + `steps/HU-001.steps.ts` + `locators/HU-001.locators.ts`, y el reporte `output/mapeos/mapeo-HU-001-<web|api|mobile>.md`.
- Performance: plan `output/performance/HU-001/plan-performance-HU-001.md` + informe `informe-performance-HU-001.html` (y su `.json`) en la misma carpeta; cada corrida deja además su reporte en `herramientas/k0lmena/reports/performance/`.
- Ejecución E2E (un reporte por corrida): `reporte-HU-001-<fecha-hora>.html` (dashboard, modo oscuro) + `_resultados-HU-001-<fecha-hora>.json` (datos), en `output/ejecuciones/`; evidencia en `output/ejecuciones/evidencia/`. Cada reporte cubre solo los casos de esa ejecución.
- Ejecución de API (`ejecutor-api`): `reporte-HU-001-<fecha-hora>.html` + `_resultados-HU-001-<fecha-hora>.json` en `output/ejecuciones/` (o `API` en lugar de la historia si la corrida no es de una).
- Evidencias E2E: `output/ejecuciones/evidencia/<fecha-hora>-<id>.png` (la misma marca de tiempo de la corrida: no se pisan).
- Plan de pruebas: `output/planes-de-prueba/plan-HU-001-<fecha>.html` (fecha `AAAA-MM-DD`) y su `plan-HU-001-<fecha>.json`.
- Informe de cierre: `output/informes-cierre/cierre-HU-001-<fecha>.html`, con sus datos recolectados en `datos-HU-001.json` (`scripts/recolectar_resultados.py`).
- Mapeo de performance: `output/mapeos/mapeo-HU-001-performance.md`.

---

## Arquitectura (cómo crece el repo)

El repo se apoya en estas piezas: **agentes** (`.claude/agents/`, el quién), **skills** (`.claude/skills/`, el cómo, cargados on-demand), **MCP** (`.mcp.json`, conexiones a sistemas externos — un solo archivo que escala a muchas conexiones: Jira, Xray, Playwright…), **herramientas** (`herramientas/`, herramientas externas de testing, una subcarpeta por herramienta: Newman, **k0lmena**, OWASP ZAP, **streaming** (ffmpeg/ONVIF), **salesforce** (CLI `sf`), **ecommerce** (Shopify/WooCommerce/PrestaShop/VTEX), **sap** (SAP GUI Scripting), **desktop** (pywinauto), **seguridad** (SCA/SAST: dependencias y código), **codigo** (code review estático de repos y PR/MR), **mensajeria** (Kafka/RabbitMQ/MQTT/WebSocket/SSE), **soap** (WSDL), **seo** (SEO/GEO), **resiliencia** (caos server-side con Toxiproxy), **observabilidad**, **documentos** (PDF/Excel), **contenido** (typos), **mutacion** (mutation testing), **manual** (manuales de usuario) y **scalar** (APIs en Scalar)) y **scripts** (`scripts/`, utilidades internas determinísticas). El detalle y cómo extender cada una está en `ARQUITECTURA.md`.

### Modelo por agente (costo de tokens)

Cada agente fija su modelo en el frontmatter (`model:`) para no gastar de más. Criterio por niveles:

- **`haiku`** — trabajo mecánico que sobre todo corre un script y arma el JSON/HTML (tablero-calidad, analista-cobertura, analista-logs, generador-reporte-html, selector-casos-de-prueba, publicador-resultados, generador-charters, guia-onboarding).
- **`sonnet`** — la mayoría del trabajo de QA (mappers, ejecutores, generadores de casos y datos, probadores —incluidos `probador-salesforce`, `probador-billeteras`, `probador-shopify`, `probador-wordpress`, `probador-prestashop`, `probador-vtex`, `probador-sap`, `probador-desktop`, `probador-mobile`, `probador-ia`, `probador-mensajeria`, `probador-soap`, `analista-dependencias`, `probador-contratos`, `analista-seo`, `probador-datos`, `probador-dynamics`, `probador-ivr`, `probador-juegos`, `probador-pos`, `analista-observabilidad`, `probador-busqueda`, `probador-documentos`, `revisor-contenido`, `analista-mutacion`, `redactor-manual` y `probador-scalar`—, auditores, documentador, `investigador-proyecto`, triador, análisis de fallos, reparador, gestor, consultor, reportes de bug y de cierre…).
- **`opus`** — lo que más razona o es sensible: `analista-historias`, `analista-seguridad`, `pentester-web`, `analista-seguridad-camaras`, `analista-codigo-seguro`, `revisor-codigo`, `probador-blockchain`.

Un agente nuevo lleva su `model:` según este criterio. El costo real por agente lo mide `scripts/metricas_tokens.py` (lo resume el tablero de calidad): si uno queda flojo en Haiku/Sonnet, se sube; si otro no necesita Opus, se baja.

## APIs: REST y GraphQL; Postman, Bruno e Insomnia

`ejecutor-api` corre colecciones de **Postman, Bruno o Insomnia** con Newman (`correr_newman.py` convierte Bruno e Insomnia con `scripts/convertir_coleccion.py` y avisa lo que no tiene equivalente). `api-mapper` automatiza también **GraphQL** en k0lmena, con steps genéricos (`envío la consulta GraphQL:`, `la respuesta GraphQL no tiene errores`, …) y el schema resumido por `scripts/resumir_graphql.py`; `generador-casos-api` incluye casos GraphQL (variables inválidas, campos inexistentes, autorización por campo, errores parciales, profundidad y paginación).

## Avisos, portal y monitoreo

- **Avisos**: `scripts/avisar.py` publica en Slack y Teams por webhook del `.env`. Lo usan el triador (bug crítico), el tablero de calidad y el monitoreo, siempre que se pida o esté configurado.
- **Portal**: `output/index.html` muestra el último informe de cada herramienta y se regenera solo.
- **Monitoreo sintético**: `npm run monitorear`, de solo lectura, contra cualquier ambiente; avisa cuando algo se rompe o se recupera.

## Herramientas de gestión de pruebas

`scripts/gestion/gestion.py` integra **Xray Cloud, Xray Server/DC, QTM4J y AIO Tests** con los mismos comandos (configurados en el `.env` de la raíz con `GESTION_HERRAMIENTA` y `GESTION_PROYECTO`). **Azure DevOps** (Boards y Test Plans) se integra por el conector MCP `azure-devops`, configurado también en el `.env` (`ADO_ORGANIZACION`, `ADO_PAT`, `ADO_PROYECTO`); los pasos de los casos los arma `scripts/gestion/para_azure_devops.py`. La trazabilidad local `output/gestion/<HU>-<herramienta>.json` guarda qué `CP-XXX` es qué key remota. Detalle en `scripts/gestion/README.md`.

## Automatización con k0lmena (ahorro de tokens)

`herramientas/k0lmena/` es el framework de automatización (web, api, mobile y performance). Los agentes **mapper** escriben la automatización **una sola vez** (skill `automatizacion-k0lmena`); después la suite corre **sin agentes ni tokens** con `cd herramientas/k0lmena && npm test` (performance: `npm run perf -- <script> <perfil>`). Para correr pruebas ya automatizadas, preferí `npm test` antes que los ejecutores en vivo (`ejecutor-e2e` / `ejecutor-api`), que gastan tokens en cada corrida.

Secretos (tokens, credenciales): van en el `.env` local (gitignored) o en variables de entorno, **nunca** commiteados; hay una plantilla `.env.example`. El `.mcp.json` está versionado con los conectores que vienen activos para todos (Playwright y Atlassian: Jira y Confluence), así Claude Code arranca sin pedir aprobaciones. Los opcionales (Azure DevOps, Figma, GitHub, GitLab, Linear, ClickUp, monday.com, Asana, Trello, Notion, YouTrack, Shortcut, QMetry/QTM4J, AIO Tests, k0lmenaTMT, Appium, Scalar) los activa cada persona con `npm run conector -- activar <nombre>`. Ninguno lleva secretos: los que piden token lo leen del `.env` con los scripts de `scripts/mcp/`. Si un agente necesita un conector que no está activo, o la persona quiere conectar una herramienta o configurar el proyecto, indicale que corra **`npm run configurar`** en una terminal (la de VS Code): pregunta todo en español y activa los conectores. **No le pidas tokens ni contraseñas en el chat**: van solo en ese asistente o en el `.env`. Detalle en `CONECTORES.md`.

**Repositorio de la aplicación:** el `documentador-proyecto` lo lee en solo lectura con el conector de su proveedor (`github`, `gitlab`, `azure-devops` para Azure Repos o `atlassian` para Bitbucket Cloud), configurado en el bloque *Repositorio de la aplicación* del `.env` (`REPO_PROVEEDOR`, `REPO_NOMBRE`, `REPO_RAMA`, `REPO_RUTA_LOCAL`).

**Fuentes externas por MCP:** si la persona da una key de Jira, un work item de Azure DevOps, una tarea de Linear, ClickUp, monday.com, Asana, Trello, Notion, YouTrack o Shortcut, una página de Confluence o de la Wiki de Azure DevOps, o un link de Figma y el conector (`atlassian`, `azure-devops` o `figma`) está activo, cualquier agente puede leerlos como insumo, igual que un archivo de `input/` (trazabilidad: citá la key, la página o el link). Si el conector no está activo, pedí el contenido o indicá cómo activarlo (`CONECTORES.md`); no lo supongas.

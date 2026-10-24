# Referencia de k0lmenIA

Lo que antes estaba en `CLAUDE.md` y no hace falta en cada conversación: la tabla de agentes con dónde guarda cada uno su salida, qué hace cada script y herramienta, y los nombres de los archivos de salida. Claude lo lee cuando lo necesita; `CLAUDE.md` queda corto y se gastan menos tokens en cada sesión.

---

## Agentes y dónde guardan la salida


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
|                            | Server/DC), QTM4J, AIO, Zephyr (vía      | `output/gestion/`                     |
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

## Scripts y herramientas

- `scripts/py.js` → lanzador de los `npm run` de Python (`node scripts/py.js <script.py> [args]`): elige `python` o `python3` y devuelve el código de salida del script.
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
- `scripts/portal_informes.py` → `output/index.html` (e `index.en.html`): todos los informes y su historial, con un menú por categoría y filtros por texto, herramienta, historia, estado y rango de fechas. Antes de indexar arma el HTML de los artefactos (`generar_informe_artefacto.py`). Se regenera solo al terminar cada informe (`K0LMENIA_PORTAL=0` lo desactiva).
- `scripts/generar_informe_artefacto.py` → el HTML bilingüe de los artefactos sin informe propio: bugs, casos manuales, BDD, análisis, datos, casos de API, contexto, triage, consultas, mapeos y verificaciones. `--todo` actualiza los que cambiaron. La versión en inglés del contenido: `X.en.md`, `X.en.csv`, `X.feature.en` o el bloque `en` de los casos.
- `scripts/_i18n.py` y `scripts/i18n/en/*.json` → informes en español e inglés: `escribir_bilingue` escribe `es/informe.html`, `en/informe.html` y el acceso `informe.html` (abre el idioma elegido), `localizar` mezcla el bloque `en` del análisis y el diccionario traduce la interfaz (números e IDs como `{n}`). Con `K0LMENIA_I18N_AUDITORIA=archivo.txt` lista lo que quedó sin traducir.
- `scripts/avisar.py` → avisos a Slack y Teams por webhook (`SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL`); `--desde-cucumber` resume un `npm test`. Sin webhook no manda nada.
- `npm run monitorear` (k0lmena `tools/monitoreo`) y `scripts/generar_informe_monitoreo.py` → monitoreo sintético de solo lectura (URLs, textos, tiempos, certificado y escenarios `@sintetico`); avisa solo cuando algo se rompe o se recupera. Se programa con `.github/workflows/monitoreo.yml`, cron o el Programador de tareas.
- `scripts/convertir_coleccion.py` → convierte colecciones de Bruno (carpeta con `bruno.json`) e Insomnia (v4 `.json` / v5 `.yaml`) a Postman v2.1, con las advertencias de lo que no se pudo convertir (`correr_newman.py` lo usa solo). `scripts/resumir_graphql.py` → resume un schema GraphQL (introspección por URL, SDL o JSON). `scripts/resumir_openapi.py` → resume un Swagger 2.0 / OpenAPI 3.x (JSON o YAML): `API_BASEURL` con su basePath, el step de autenticación de cada securityScheme, parámetros, body de ejemplo y status documentados.
- `scripts/evaluar_agentes.py` → **evals de los agentes** (`evals/`): casos con trampas deliberadas que corren en un workspace aislado con `claude -p` y se verifican con chequeos determinísticos; informe con el puntaje por agente y las regresiones. **Gastan tokens** (tope por caso); `--solo-verificar` revisa salidas ya generadas.
- `scripts/seleccionar_casos.py` → elige y prioriza los casos a correr para un cambio y genera el informe (`selector-casos-de-prueba`).
- `scripts/generar_informe_pixel_perfect.py`, `generar_informe_cross_browser.py` y `generar_informe_reparacion.py` → los informes HTML de `npm run pixel-perfect`, `npm run cross-browser` y `npm run reparar` (`pixel-perfect`, `cross-browser`, `reparador-automatizacion`).

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

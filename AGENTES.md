# Catálogo de agentes

Los 79 agentes de k0lmenIA: para qué sirve cada uno, cómo pedírselo, qué skills, scripts, herramientas y conectores usa, y qué entrega. No hace falta nombrar al agente: Claude Code elige el que corresponde según el pedido (también se lo podés pedir por su nombre).

**Leyenda**
- **Tokens**: *en cada uso* = trabaja con el modelo cada vez que lo pedís; *una vez* = genera algo que después corre solo, sin agentes ni tokens (`npm test`, `npm run perf`).
- **Confirma**: el agente no hace la acción sin tu ok explícito (por ejemplo, escribir en una base o crear casos en Xray). Como los agentes no pueden preguntar a mitad del trabajo, devuelven **"Necesito que confirmes"** y Claude te pregunta.
- **Conectores**: los que vienen activos (`playwright`, `atlassian`) no necesitan nada; los demás se activan con `npm run conector -- activar <nombre>` (ver `CONECTORES.md`).

## Resumen

| Agente                   | Familia                                       | Para qué                                                                          | Skills                                                             | Herramientas y scripts                                             | Conectores                                                                | Salida                                                  |
| ------------------------ | --------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| documentador-proyecto    | Análisis y diseño                             | Documentación del proyecto: repo, historias, links y web                          | investigacion-contexto, ejecucion-e2e                              | npm run mapa-funcional, indice_documentacion.py                    | github, gitlab, azure-devops, atlassian, playwright-headless              | input/documentacion/                                    |
| analista-historias       | Análisis y diseño                             | Ambigüedades, riesgos y preguntas de una historia                                 | investigacion-contexto                                             | formatear_tablas.py                                                | atlassian, azure-devops, figma                                            | output/analisis-historias/                              |
| estratega-pruebas        | Análisis y diseño                             | Plan de pruebas (alcance, riesgos, criterios)                                     | investigacion-contexto                                             | generar_plan.py                                                    | atlassian, azure-devops, figma                                            | output/planes-de-prueba/                                |
| generador-casos-manuales | Análisis y diseño                             | Casos manuales en Excel, Markdown y cobertura                                     | investigacion-contexto, tecnicas-de-diseno                         | generar_casos.py, formatear_tablas.py                              | atlassian, azure-devops, figma                                            | output/casos-de-prueba/manuales/                        |
| generador-casos-bdd      | Análisis y diseño                             | Escenarios Gherkin y cobertura                                                    | investigacion-contexto, tecnicas-de-diseno                         | formatear_tablas.py                                                | atlassian, azure-devops, figma                                            | output/casos-de-prueba/bdd/                             |
| generador-casos-api      | Análisis y diseño                             | Casos de API desde un contrato                                                    | investigacion-contexto, tecnicas-de-diseno, pruebas-graphql, pruebas-grpc                         | resumir_openapi.py, resumir_graphql.py, formatear_tablas.py        | atlassian, azure-devops                                                   | output/casos-api/                                       |
| generador-datos-prueba   | Análisis y diseño                             | Datos válidos, inválidos y de borde                                               | investigacion-contexto, tecnicas-de-diseno                         | formatear_tablas.py                                                | atlassian, azure-devops                                                   | output/datos-de-prueba/                                 |
| selector-casos-de-prueba | Análisis y diseño                             | Qué casos correr para un cambio (por riesgo)                                      | investigacion-contexto                                             | seleccionar_casos.py, generar_informe_seleccion.py                 | atlassian, azure-devops                                                   | output/seleccion-casos/                                 |
| revisor-casos            | Análisis y diseño                             | Calidad de los casos, duplicados y tiempo de ejecución                            | investigacion-contexto, tecnicas-de-diseno                         | revisar_casos.py, generar_informe_revision.py, estimacion.py       | atlassian, azure-devops                                                   | output/revision-casos/                                  |
| generador-charters       | Análisis y diseño                             | Charters y sesiones exploratorias con su informe                                  | ejecucion-e2e, investigacion-contexto, tecnicas-de-diseno          | generar_charters.py                                                | atlassian, azure-devops, playwright, playwright-headless                  | output/charters/                                        |
| generador-reportes-bug   | Análisis y diseño                             | Reporte de bug desde una observación                                              | —                                                                  | formatear_tablas.py, plantilla de bug                              | atlassian, azure-devops                                                   | output/reportes-bug/                                    |
| triador-bugs             | Análisis y diseño                             | Duplicados, regresiones y clasificación de bugs antes de cargarlos                | —                                                                  | buscar_duplicados.py, avisar.py                                    | atlassian, azure-devops, github, gitlab                                   | output/triage/                                          |
| consultor-proyecto       | Análisis y diseño                             | Responde preguntas del producto con la documentación, citando fuentes             | investigacion-contexto                                             | formatear_tablas.py                                                | —                                                                         | Respuesta en el chat (+ output/consultas/)              |
| guia-onboarding          | Análisis y diseño                             | Plan de incorporación de un QA nuevo al proyecto                                  | —                                                                  | generar_onboarding.py, doctor.py                                   | —                                                                         | output/onboarding/                                      |
| investigador-proyecto    | Análisis y diseño                             | Releva el proyecto entero por MCP: resumen, ambigüedades y preguntas para QA nuevo | relevamiento-proyecto, investigacion-contexto                      | generar_informe_investigacion.py                                   | atlassian, azure-devops, github, gitlab, figma                            | output/investigacion/                                   |
| redactor-manual          | Análisis y diseño                             | Manual de usuario basado en evidencia (funcionalidad, módulo o toda la plataforma), verificado en la app con capturas; deja lo aprendido en input/documentacion/ para los casos | redaccion-manual, investigacion-contexto | herramientas/manual/manual.py | playwright | output/manuales/ |
| ejecutor-e2e             | Ejecución en vivo                             | Corre casos en el navegador con evidencia                                         | ejecucion-e2e                                                      | Playwright MCP, generar_reporte.py                                 | playwright, playwright-headless                                           | output/ejecuciones/                                     |
| ejecutor-api             | Ejecución en vivo                             | Corre una colección de Postman, Bruno o Insomnia                                  | ejecucion-api, pruebas-graphql, pruebas-grpc                                                      | Newman, correr_newman.py                                           | —                                                                         | output/ejecuciones/                                     |
| analista-seguridad       | Ejecución en vivo                             | Escaneo de seguridad web pasivo e informe                                         | —                                                                  | OWASP ZAP (Docker), escanear.py, generar_informe_seguridad.py      | —                                                                         | output/seguridad/                                       |
| pentester-web            | Ejecución en vivo                             | Pentest web autorizado (activo) e informe                                         | ejecucion-e2e, investigacion-contexto                              | OWASP ZAP activo (Docker), escanear.py, generar_informe_seguridad.py| playwright · playwright-headless                                          | output/seguridad/                                       |
| probador-salesforce      | Ejecución en vivo                             | Prueba una org de Salesforce (sandbox): acceso, validaciones, flows, Apex, sharing | pruebas-salesforce, pruebas-tokens, ejecucion-e2e, investigacion-contexto | herramientas/salesforce/inventario.py, generar_informe_salesforce.py | salesforce, playwright, playwright-headless                               | output/salesforce/                                      |
| probador-billeteras      | Ejecución en vivo                             | Prueba billeteras y pagos: saldo, idempotencia, doble gasto, conciliación, tokens  | pruebas-billeteras, pruebas-tokens, tecnicas-de-diseno, ejecucion-e2e, investigacion-contexto | generar_informe_billeteras.py; se apoya en ejecutor-api, verificador-datos | playwright, playwright-headless                                           | output/billeteras/                                      |
| probador-shopify         | Ejecución en vivo                             | Prueba una tienda Shopify: tema, catálogo, checkout, mercados, envíos, descuentos  | pruebas-shopify, pruebas-ecommerce, ejecucion-e2e, guia-performance, investigacion-contexto                   | herramientas/ecommerce/shopify.py, generar_informe_ecommerce.py            | playwright, playwright-headless                                           | output/shopify/                                         |
| probador-wordpress       | Ejecución en vivo                             | Prueba WordPress / WooCommerce: plugins, templates, checkout, pagos, envíos, cupones| pruebas-wordpress, pruebas-ecommerce, ejecucion-e2e, guia-performance, investigacion-contexto                 | herramientas/ecommerce/wordpress.py, generar_informe_ecommerce.py          | playwright, playwright-headless                                           | output/wordpress/                                       |
| probador-prestashop      | Ejecución en vivo                             | Prueba PrestaShop (1.6/1.7/8.x): smoke local, checkout, pagos, stock, redondeo, rendimiento | pruebas-prestashop, pruebas-ecommerce, ejecucion-e2e, guia-performance, investigacion-contexto | herramientas/ecommerce/prestashop.py, generar_informe_ecommerce.py         | playwright, playwright-headless                                           | output/prestashop/                                      |
| probador-vtex            | Ejecución en vivo                             | Prueba VTEX: catálogo y canales, checkout/orderForm, promos, envíos, pagos, OMS, VTEX IO | pruebas-vtex, pruebas-ecommerce, ejecucion-e2e, guia-performance, investigacion-contexto | herramientas/ecommerce/vtex.py, generar_informe_ecommerce.py               | playwright, playwright-headless                                           | output/vtex/                                            |
| probador-sap             | Ejecución en vivo                             | Prueba SAP (S/4HANA/ECC): SAP GUI y Fiori, autorizaciones, procesos O2C/P2P/R2R | pruebas-sap, ejecucion-e2e, ejecucion-api, guia-performance, investigacion-contexto | herramientas/sap/sap_gui.py, generar_informe_sap.py                        | playwright, playwright-headless                                           | output/sap/                                             |
| probador-desktop         | Ejecución en vivo                             | Prueba apps de escritorio Windows (WinForms/WPF/UWP/Electron/Java/Qt) | pruebas-desktop, ejecucion-e2e, guia-performance, investigacion-contexto | herramientas/desktop/controles.py, generar_informe_desktop.py             | appium, playwright                                                        | output/desktop/                                         |
| probador-mobile          | Ejecución en vivo                             | Prueba apps móviles (Android/iOS; nativa/híbrida/web) en vivo con Appium | pruebas-mobile, guia-performance, investigacion-contexto | generar_informe_mobile.py                                                  | appium                                                                    | output/mobile/                                          |
| analista-dependencias    | Análisis (solo lectura)                       | SCA: vulnerabilidades (CVE) y licencias de las dependencias del proyecto | analisis-dependencias, investigacion-contexto | herramientas/seguridad/dependencias.py, generar_informe_dependencias.py   | —                                                                         | output/dependencias/                                    |
| analista-codigo-seguro   | Análisis (solo lectura)                       | SAST y secretos del código (semgrep + escáner integrado, triage de FP) | codigo-seguro, investigacion-contexto | herramientas/seguridad/sast.py, generar_informe_sast.py                   | —                                                                         | output/sast/                                            |
| revisor-codigo           | Análisis (solo lectura)                       | Code review estático de un repo o PR/MR (GitHub/GitLab/Bitbucket/Azure/git): seguridad, performance, confiabilidad, malas prácticas y mantenibilidad | revision-codigo, codigo-seguro, investigacion-contexto | herramientas/codigo/obtener.py, herramientas/codigo/revision.py, generar_informe_revision_codigo.py | — | output/revision-codigo/ |
| probador-ia              | Ejecución en vivo                             | Funciones de IA/LLM: golden set, alucinaciones, grounding, seguridad de prompt | pruebas-ia, ejecucion-api, ejecucion-e2e, investigacion-contexto | generar_informe_ia.py                                                      | playwright                                                                | output/ia/                                              |
| probador-mensajeria      | Ejecución en vivo                             | Mensajería/eventos (Kafka/RabbitMQ/SQS/MQTT/WebSocket/SSE): entrega, orden, idempotencia, DLQ | pruebas-async, guia-performance, investigacion-contexto | herramientas/mensajeria/mensajeria.py, generar_informe_mensajeria.py | — | output/mensajeria/ |
| probador-soap            | Ejecución en vivo                             | Servicios SOAP desde el WSDL: operaciones, XSD, SOAP Faults, WS-Security | pruebas-soap, ejecucion-api, investigacion-contexto | herramientas/soap/wsdl.py, generar_informe_soap.py | — | output/soap/ |
| probador-scalar          | Ejecución en vivo                             | APIs en Scalar: MCP de la API, contrato del Registry, casos como colección ejecutable con tests pm e importación a Scalar (x-post-response) | pruebas-scalar, ejecucion-api, pruebas-graphql, investigacion-contexto | herramientas/scalar/scalar.py, correr_newman.py | scalar | output/scalar/ |
| probador-contratos | Ejecución en vivo | Contract testing (Pact): consumer-driven y bi-direccional para REST/GraphQL/gRPC/eventos | pruebas-contratos, ejecucion-api, investigacion-contexto | generar_informe_generico.py | — | output/contratos/ |
| analista-seo | Análisis (solo lectura) | SEO y GEO: indexabilidad, on-page, datos estructurados, hreflang y crawlers de IA | pruebas-seo, investigacion-contexto | herramientas/seo/seo.py, generar_informe_generico.py | — | output/seo/ |
| probador-datos | Análisis (solo lectura) | Datos y pipelines (ETL): calidad, reconciliación, esquema, transformaciones, idempotencia | pruebas-datos, investigacion-contexto | generar_informe_generico.py | — | output/datos/ |
| probador-dynamics | Ejecución en vivo | Dynamics 365 y otros CRM/ERP (sandbox): roles, lógica, procesos end-to-end | pruebas-dynamics, ejecucion-e2e, investigacion-contexto | generar_informe_generico.py | playwright, playwright-headless | output/dynamics/ |
| probador-blockchain | Ejecución en vivo | Blockchain/Web3 y smart contracts (testnet/local): funcional, gas, seguridad on-chain | pruebas-blockchain, ejecucion-api, investigacion-contexto | generar_informe_generico.py | — | output/blockchain/ |
| probador-ivr | Ejecución en vivo | Voz/IVR y voicebots: árbol de menús (DTMF/voz), enrutamiento, telefonía, cumplimiento | pruebas-ivr, investigacion-contexto | generar_informe_generico.py | — | output/ivr/ |
| probador-juegos | Ejecución en vivo | Videojuegos: mecánicas, guardado, compatibilidad, rendimiento, multijugador, monetización | pruebas-juegos, investigacion-contexto | generar_informe_generico.py | — | output/juegos/ |
| probador-pos | Ejecución en vivo | POS y hardware: venta, pagos y periféricos, fiscal, offline y conciliación | pruebas-pos, investigacion-contexto | generar_informe_generico.py | — | output/pos/ |
| analista-observabilidad | Análisis (solo lectura) | Observabilidad: logs (trace id, sin PII), métricas (Prometheus RED/USE), trazas, healthchecks, SLOs y alertas | pruebas-observabilidad, ejecucion-api, investigacion-contexto | herramientas/observabilidad/observabilidad.py, generar_informe_generico.py | — | output/observabilidad/ |
| probador-busqueda | Ejecución en vivo | Búsqueda y relevancia (Elastic/Algolia/Solr/DB): ranking, typos, sinónimos, facetas, indexación, golden set | pruebas-busqueda, ejecucion-api, ejecucion-e2e, investigacion-contexto | generar_informe_generico.py | playwright | output/busqueda/ |
| probador-documentos | Ejecución en vivo | Documentos generados (PDF/Excel/CSV): datos y totales, placeholders, formato, layout, metadata y seguridad | pruebas-documentos, investigacion-contexto | herramientas/documentos/documentos.py, generar_informe_generico.py | — | output/documentos/ |
| revisor-contenido | Análisis (solo lectura) | Contenido y typos (idioma principal): ortografía, placeholders, claves i18n a la vista, duplicados y microcopy | pruebas-contenido, ejecucion-e2e, investigacion-contexto | herramientas/contenido/contenido.py, generar_informe_generico.py | playwright, playwright-headless | output/contenido/ |
| analista-mutacion       | Análisis (solo lectura)                       | Mutation testing: calidad de la suite de tests, mutation score, sobrevivientes vs. equivalentes | pruebas-mutacion, investigacion-contexto | herramientas/mutacion/mutacion.py, generar_informe_generico.py | — | output/mutacion/ |
| probador-streaming       | Ejecución en vivo                             | Streaming y playback de video (cámaras, live, VOD) con ffprobe/ffmpeg             | verificacion-streaming, investigacion-contexto                     | herramientas/streaming/probar.py, generar_informe_streaming.py      | —                                                                         | output/streaming/                                       |
| probador-onvif           | Ejecución en vivo                             | Control ONVIF de una cámara IP: info, perfiles, stream URI, snapshot, PTZ y eventos | control-onvif, investigacion-contexto                              | herramientas/streaming/onvif.py, generar_informe_onvif.py           | —                                                                         | output/streaming/onvif-*/                               |
| calidad-imagen           | Ejecución en vivo                             | Calidad de imagen de cámaras: negro, desenfoque, congelamiento (OpenCV) + lente sucia, movida, contraluz, IR (visión) | calidad-de-imagen, investigacion-contexto                          | herramientas/streaming/calidad_imagen.py, generar_informe_calidad.py | —                                                                         | output/streaming/calidad-*/                             |
| verificador-grabaciones  | Ejecución en vivo                             | Grabaciones por ONVIF: rango cubierto, huecos y retención vs. la esperada           | control-onvif, investigacion-contexto                              | herramientas/streaming/grabaciones.py, generar_informe_grabaciones.py | —                                                                         | output/streaming/grabaciones-*/                         |
| analista-seguridad-camaras | Ejecución en vivo                             | Seguridad pasiva de cámaras: puertos, servicios inseguros (Telnet, FTP, HTTP sin TLS, RTSP sin auth) y firmware/CVEs | seguridad-camaras, investigacion-contexto                          | herramientas/streaming/seguridad_camaras.py, generar_informe_seguridad_camaras.py | —                                                                         | output/streaming/seguridad-camaras-*/                   |
| explorador-web           | Ejecución en vivo                             | Exploratorias: links, imágenes, errores y responsive                              | ejecucion-e2e                                                      | npm run explorar, generar_informe_exploratorio.py                  | playwright, playwright-headless                                           | output/exploratorias/                                   |
| analista-accesibilidad   | Ejecución en vivo                             | Accesibilidad WCAG 2.2: axe, teclado y revisión manual                            | ejecucion-e2e, pruebas-accesibilidad                                                      | npm run accesibilidad (axe-core), generar_informe_accesibilidad.py | playwright, playwright-headless                                           | output/accesibilidad/                                   |
| auditor-rendimiento-web  | Ejecución en vivo                             | Velocidad de carga: Lighthouse y Core Web Vitals                                  | —                                                                  | npm run rendimiento (Lighthouse), generar_informe_rendimiento.py   | —                                                                         | output/rendimiento/                                     |
| pixel-perfect            | Ejecución en vivo                             | Regresión visual: qué se corrió o cambió                                          | ejecucion-e2e                                                      | npm run pixel-perfect, generar_informe_pixel_perfect.py            | playwright, playwright-headless, figma                                    | output/pixel-perfect/                                   |
| cross-browser            | Ejecución en vivo                             | Chromium, Firefox y WebKit (Safari)                                               | —                                                                  | npm run cross-browser, generar_informe_cross_browser.py            | —                                                                         | output/cross-browser/                                   |
| verificador-correos      | Ejecución en vivo                             | Correos de la app con Mailpit: llegan, contenido, links                           | investigacion-contexto, ejecucion-e2e, automatizacion-k0lmena      | npm run correos (Mailpit), generar_informe_correos.py              | playwright, playwright-headless                                           | output/correos/                                         |
| analista-traductor       | Ejecución en vivo                             | Traducciones e idiomas: sin traducir, cortados, formatos                          | investigacion-contexto, ejecucion-e2e                              | npm run traductor, generar_informe_traductor.py                    | playwright, playwright-headless                                           | output/traductor/                                       |
| evaluador-ux             | Ejecución en vivo                             | Usabilidad con las 10 heurísticas de Nielsen                                      | ejecucion-e2e, investigacion-contexto                              | npm run ux, generar_informe_ux.py                                  | playwright, playwright-headless                                           | output/ux/                                              |
| probador-formularios     | Ejecución en vivo                             | Validaciones de cada campo sin enviar el formulario                               | ejecucion-e2e, investigacion-contexto                              | npm run formularios, generar_informe_formularios.py                | playwright, playwright-headless                                           | output/formularios/                                     |
| probador-permisos        | Ejecución en vivo                             | Matriz de permisos: qué ve y abre cada rol                                        | investigacion-contexto, ejecucion-e2e                              | npm run permisos, generar_informe_permisos.py                      | playwright, playwright-headless, atlassian, azure-devops                  | output/permisos/                                        |
| probador-resiliencia     | Ejecución en vivo                             | Qué ve la persona cuando la API, la red o los recursos fallan                     | ejecucion-e2e, investigacion-contexto                              | npm run resiliencia, generar_informe_resiliencia.py                | playwright, playwright-headless                                           | output/resiliencia/                                     |
| generador-reporte-html   | Reportes                                      | Reporte HTML de una corrida                                                       | —                                                                  | generar_reporte.py                                                 | —                                                                         | output/ejecuciones/                                     |
| generador-reporte-cierre | Reportes                                      | Informe de cierre y go/no-go de la ronda                                          | —                                                                  | recolectar_resultados.py, generar_informe_cierre.py                | —                                                                         | output/informes-cierre/                                 |
| analista-cobertura       | Reportes                                      | Matriz de trazabilidad y qué falta probar                                         | investigacion-contexto                                             | analizar_cobertura.py, generar_informe_cobertura.py                | atlassian, azure-devops                                                   | output/cobertura/                                       |
| tablero-calidad          | Reportes                                      | Tablero de calidad por sprint o release: aprobados, automatizado, cobertura, bugs | —                                                                  | tablero_calidad.py, portal_informes.py, avisar.py                  | —                                                                         | output/tablero/                                         |
| web-mapper               | Automatización (k0lmena)                      | Automatiza casos web                                                              | automatizacion-k0lmena, ejecucion-e2e, investigacion-contexto      | k0lmena (Playwright + Cucumber)                                    | playwright, playwright-headless                                           | herramientas/k0lmena/web/ + output/mapeos/              |
| api-mapper               | Automatización (k0lmena)                      | Automatiza APIs desde Postman o Swagger                                           | automatizacion-k0lmena, investigacion-contexto, tecnicas-de-diseno, pruebas-graphql, pruebas-grpc | k0lmena (axios + Cucumber)                                         | —                                                                         | herramientas/k0lmena/api/ + output/mapeos/              |
| mobile-mapper            | Automatización (k0lmena)                      | Automatiza casos mobile                                                           | automatizacion-k0lmena, investigacion-contexto                     | k0lmena (WebdriverIO + Appium)                                     | appium-mcp                                                                | herramientas/k0lmena/mobile/ + output/mapeos/           |
| performance-mapper       | Automatización (k0lmena)                      | Carga, estrés, soak y picos con informe                                           | automatizacion-k0lmena, guia-performance                           | k6, Artillery, JMeter, generar_informe_performance.py              | —                                                                         | herramientas/k0lmena/performance/ + output/performance/ |
| verificador-datos        | Automatización (k0lmena)                      | Consulta y verifica datos en bases                                                | automatizacion-k0lmena                                             | k0lmena tools/bd (npm run bd)                                      | —                                                                         | chat (+ output/verificaciones-datos/)                   |
| analista-fallos          | Automatización (k0lmena)                      | Clasifica las fallas de npm test y detecta inestables                             | ejecucion-e2e                                                      | analizar_fallos.py, generar_informe_fallos.py                      | playwright, playwright-headless                                           | output/fallos/ + output/reportes-bug/                   |
| reparador-automatizacion | Automatización (k0lmena)                      | Repara locators y esperas rotos y lo verifica                                     | automatizacion-k0lmena, ejecucion-e2e                              | npm run reparar, generar_informe_reparacion.py                     | playwright, playwright-headless                                           | herramientas/k0lmena/web/ + output/reparaciones/        |
| analista-logs            | Automatización (k0lmena)                      | Errores del servidor cruzados con la corrida                                      | —                                                                  | analizar_logs.py, generar_informe_logs.py                          | —                                                                         | output/logs/                                            |
| gestor-pruebas           | Gestión                                       | Carpetas, casos y ciclos en la herramienta de gestión                             | —                                                                  | gestion.py, para_azure_devops.py                                   | azure-devops (para Azure Test Plans)                                      | Xray / QMetry / AIO / Azure DevOps + output/gestion/    |
| publicador-resultados    | Gestión                                       | Sube resultados de npm test con evidencias                                        | —                                                                  | gestion.py                                                         | —                                                                         | Xray / QMetry / AIO                                     |

---

## Análisis y diseño

### documentador-proyecto
- **Cuándo**: al empezar con un proyecto (para armar la base de contexto) y antes de trabajar una historia o épica (para juntar todo lo que hay sobre ella), así los demás agentes escriben casos con contexto real.
- **Pedido de ejemplo**: *"Documentá el proyecto"* · *"Juntá todo el contexto de PROJ-12 antes de escribir los casos"* · *"Documentá todas las historias de la épica PROJ-3"* (modo barrido) · *"Explorá la plataforma de punta a punta"* · *"Actualizá la documentación: cambiaron los requerimientos"*.
- **Novedades**: el mapa funcional recorre la app **con la sesión** de `npm run login`, guarda los **locators sugeridos** de cada pantalla y compara con el recorrido anterior; el **modo barrido** documenta todas las historias de un alcance en lotes e incrementalmente; el **modo actualizar** detecta cambios en el código, en las historias (`cambios-historias.md`) y en la aplicación, con los casos para revisar.
- **Entradas**: el repositorio de la aplicación (bloque *Repositorio de la aplicación* del `.env`: `REPO_PROVEEDOR`, `REPO_NOMBRE`, `REPO_RAMA`, opcional `REPO_RUTA_LOCAL`), la historia o épica (key de Jira, work item de Azure DevOps o `HU-XXX`) y la URL de la app (`APP_URL`).
- **Usa**: conector del repositorio en solo lectura (`github`, `gitlab`, `azure-devops` para Azure Repos o `atlassian` para Bitbucket Cloud): README y docs, validaciones, límites, mensajes, estados, roles y permisos, rutas, contratos de API y los PRs y commits de la historia; skill `investigacion-contexto` (historia, comentarios, subtareas, épica, vínculos, Confluence, Wiki, Figma) y links públicos; `npm run mapa-funcional` (páginas, menús, formularios con sus campos, botones y mensajes, sin enviar nada) y, puntualmente, Playwright MCP con el skill `ejecucion-e2e`; `scripts/indice_documentacion.py` y `scripts/formatear_tablas.py`.
- **Entrega**: en `input/documentacion/` (no se versiona), `INDICE.md`; `proyecto/` con resumen, repositorio, reglas de negocio, mensajes, estados y permisos, mapa funcional y links; `api/` con los contratos; y `historias/<HU o key>/dossier.md` (historia, decisiones, links, PRs y código tocado, pantallas, contradicciones y pistas para probar). Cada dato con su fuente. El skill `investigacion-contexto` lo lee primero, así que lo aprovechan todos los agentes que investigan una historia.
- **Tokens**: en cada uso (el recorrido de la web y el índice los hacen scripts; con `REPO_RUTA_LOCAL` el código se lee sin el conector).

### analista-historias
- **Cuándo**: antes de diseñar pruebas, para encontrar huecos y ambigüedades en una historia.
- **Pedido de ejemplo**: *"Analizá la historia HU-001"* · *"Revisá PROJ-12 de Jira y decime qué falta definir"*.
- **Entradas**: la historia (en `input/historias/`, una key de Jira o un work item de Azure DevOps) y su documentación.
- **Usa**: skill `investigacion-contexto` (comentarios, subtareas, épica, Confluence, Figma); `scripts/formatear_tablas.py`.
- **Entrega**: `output/analisis-historias/analisis-HU-XXX.md` con ambigüedades, riesgos, casos no contemplados y preguntas para el PO; la ficha `output/contexto/contexto-HU-XXX.md` con los `FI-XX`.
- **Tokens**: en cada uso.

### estratega-pruebas
- **Cuándo**: al empezar una historia, feature o release, para acordar qué se prueba y cómo.
- **Pedido de ejemplo**: *"Armá el plan de pruebas de HU-001"*.
- **Usa**: skill `investigacion-contexto`; `scripts/generar_plan.py`.
- **Entrega**: `output/planes-de-prueba/plan-HU-XXX-<fecha>.html` (dashboard): objetivos, alcance, tipos de prueba, riesgos, datos y entorno, criterios de entrada y salida, supuestos y preguntas.
- **Tokens**: en cada uso.

### generador-casos-manuales
- **Cuándo**: para escribir los casos de prueba de una historia.
- **Pedido de ejemplo**: *"Generá los casos de prueba de HU-001"*.
- **Usa**: skills `investigacion-contexto` y `tecnicas-de-diseno` (equivalencia, valores límite, tabla de decisión, estados, pairwise); `scripts/generar_casos.py` y `scripts/formatear_tablas.py`.
- **Entrega**: en `output/casos-de-prueba/manuales/`, `casos-HU-XXX.xlsx` + `casos-HU-XXX.md` + `casos-HU-XXX-cobertura.md` (cobertura por criterio, ambigüedades y preguntas). Los casos con información faltante quedan resaltados y con su `FI-XX`.
- **Tokens**: en cada uso.

### generador-casos-bdd
- **Cuándo**: para tener los escenarios en Gherkin (por ejemplo, para automatizarlos después).
- **Pedido de ejemplo**: *"Pasá HU-001 a BDD"*.
- **Usa**: skills `investigacion-contexto` y `tecnicas-de-diseno`; `scripts/formatear_tablas.py`.
- **Entrega**: en `output/casos-de-prueba/bdd/`, `HU-XXX-<tema>.feature` (keywords en inglés, contenido en español, cada escenario con `@CP-XXX`) + `HU-XXX-cobertura.md`.
- **Tokens**: en cada uso.

### generador-casos-api
- **Cuándo**: para diseñar las pruebas de una API desde su contrato.
- **Pedido de ejemplo**: *"Generá los casos de API de input/api/auth-endpoints.md"*.
- **Usa**: skills `investigacion-contexto` (si sale de una historia) y `tecnicas-de-diseno`; `scripts/resumir_openapi.py` y `resumir_graphql.py` (contratos), `scripts/formatear_tablas.py`.
- **Entrega**: `output/casos-api/casos-api-HU-XXX.md` (o `casos-api-<tema>.md` si no sale de una historia; `CP-API-XXX` por historia o contrato): tabla resumen y detalle de cada caso con método, endpoint, headers, body y respuesta esperada (positivos, negativos, schema y autorización).
- **Tokens**: en cada uso. Para correrlos, `ejecutor-api`; para automatizarlos, `api-mapper`.

### generador-datos-prueba
- **Cuándo**: para tener datos realistas con los que probar.
- **Pedido de ejemplo**: *"Generá datos de prueba para el registro de HU-001, en CSV"*.
- **Usa**: skills `investigacion-contexto` (las reglas de cada campo) y `tecnicas-de-diseno`; `scripts/formatear_tablas.py`.
- **Entrega**: `output/datos-de-prueba/datos-HU-XXX.md` o `.csv` con datos válidos, inválidos y de borde. No toca ninguna base (para eso, `verificador-datos`).
- **Tokens**: en cada uso.

### selector-casos-de-prueba
- **Cuándo**: antes de probar un cambio (un PR, una release, un sprint), para saber qué casos correr sin hacer toda la regresión.
- **Pedido de ejemplo**: *"¿Qué casos corro para el PR #42?"* · *"Armá la regresión de la release 2.4 (main..release/2.4 en ../mi-app), tengo una hora"*.
- **Entradas**: el cambio —rango de git del repositorio de la aplicación, archivos de un PR, historias o issues de Jira/Azure DevOps o las notas de la release— y el inventario de casos (manuales, BDD y automatizados en k0lmena, con su último resultado, los inestables y los bugs).
- **Usa**: skill `investigacion-contexto` (para leer los issues); `scripts/seleccionar_casos.py` (cruza el cambio con los casos, con sinónimos en español e inglés, y les da un puntaje) y `scripts/generar_informe_seleccion.py`. Opcional: `input/mapa-componentes.json` (carpetas del código → historias).
- **Entrega**: en `output/seleccion-casos/<nombre>/`, `informe-seleccion.html` (riesgo, imprescindibles, recomendados y regresión mínima con el porqué de cada uno, tiempo y ahorro, comandos `npm test` con los tags listos para copiar, cambios sin cobertura), `seleccion.csv` (lo manual, para ejecutar) y `seleccion.json`.
- **Tokens**: en cada uso (el cruce y el puntaje los hace el script).

### revisor-casos
- **Cuándo**: para revisar casos que ya existen antes de ejecutarlos, subirlos a la herramienta de gestión o automatizarlos.
- **Pedido de ejemplo**: *"Revisá los casos de HU-001"* · *"¿Hay casos duplicados en la regresión?"* · *"¿Cuánto lleva ejecutar a mano los casos del sprint?"*.
- **Usa**: skills `investigacion-contexto` y `tecnicas-de-diseno`; `scripts/revisar_casos.py`, `scripts/generar_informe_revision.py` y `scripts/estimacion.py`.
- **Entrega**: en `output/revision-casos/<HU o nombre>/`, `informe-revision.html` (puntaje de cada caso, problemas con su sugerencia, duplicados, historias sin negativos, tiempo de ejecución manual y la versión mejorada que propone) y, si lo pedís, la planilla corregida en un archivo nuevo.
- **Confirma**: actualizar casos en la herramienta de gestión.
- **Tokens**: en cada uso (la revisión mecánica la hace el script).

### generador-charters
- **Cuándo**: para planificar pruebas exploratorias con objetivo (session-based testing) y documentar lo que se encontró.
- **Pedido de ejemplo**: *"Armá charters para explorar el checkout de la release 2.4"* · *"Generá el informe de las sesiones de HU-003"*.
- **Usa**: skills `investigacion-contexto`, `tecnicas-de-diseno` (heurísticas) y `ejecucion-e2e` (si explora él); `scripts/generar_charters.py`.
- **Entrega**: en `output/charters/<HU o nombre>/`, las hojas de sesión (`charters.html` y `.md`), una plantilla de notas por sesión (`sesiones/CH-XX.md`) y, con las notas, `informe-sesiones.html` (bugs, preguntas, riesgos, reparto del tiempo y áreas cubiertas).
- **Tokens**: en cada uso.

### generador-reportes-bug
- **Cuándo**: cuando encontraste un error y tenés notas sueltas.
- **Pedido de ejemplo**: *"Armá el reporte de bug de input/bugs/observacion.md"* o pegale la observación.
- **Usa**: `plantillas/plantilla-reporte-bug.md`, `scripts/formatear_tablas.py`; la ficha de contexto y la documentación del proyecto si existen (lo observado en el código no vale como resultado esperado).
- **Entrega**: `output/reportes-bug/BUG-XXX.md` (el número siguiente al más alto) con historia, estado, severidad y prioridad justificadas; lo que falta queda marcado, nunca inventado.
- **Tokens**: en cada uso.

### triador-bugs
- **Cuándo**: antes de cargar un bug en la herramienta, o para revisar un lote de bugs del sprint, para que no entren duplicados y cada bug llegue con severidad, componente e historia.
- **Pedido de ejemplo**: *"¿BUG-008 ya está cargado en Jira?"* · *"Triá los bugs de output/reportes-bug"* · *"Buscá duplicados de 'el pago rechaza tarjetas válidas'"*.
- **Entradas**: el bug (`output/reportes-bug/`, `input/bugs/`, texto, key de Jira o ID de Azure DevOps) y el proyecto donde buscar.
- **Usa**: conectores `atlassian` (JQL) o `azure-devops` (WIQL) para traer candidatos, incluidos los cerrados; `github` o `gitlab` para issues del repositorio y `CODEOWNERS`/commits para sugerir responsable; `scripts/buscar_duplicados.py` (similitud con los mismos sinónimos que el selector de casos); `scripts/avisar.py` para avisar un bug crítico, solo si se pide.
- **Entrega**: veredicto (nuevo, duplicado, posible regresión de un bug cerrado o relacionado), severidad y prioridad con su criterio, componente, responsable sugerido (solo el usuario de la herramienta) e historia a vincular; `output/triage/<nombre>/` con `candidatos.json`, `triage.json` y `triage.md` (con la **Conclusión del triador** al final).
- **Tokens**: en cada uso (el puntaje lo hace el script).
- **Confirma**: crear, vincular, comentar, reabrir o cambiar campos en Jira o Azure DevOps.

### consultor-proyecto
- **Cuándo**: para consultar cómo funciona algo del producto o ponerse al día con un proyecto, sin releer toda la documentación.
- **Pedido de ejemplo**: *"¿Qué pasa si un usuario bloqueado intenta pagar?"* · *"¿Cuál es el largo máximo del nombre en el registro?"* · *"¿Qué roles pueden aprobar un pedido?"*.
- **Entradas**: la pregunta; `input/documentacion/` (empieza por el índice), `output/contexto/` y los artefactos generados.
- **Usa**: solo lectura de esa documentación (no navega la app ni lee el repositorio o Jira, salvo pedido explícito); el skill `investigacion-contexto` para proponer `FI-XX`.
- **Entrega**: la respuesta en el chat con la fuente original de cada afirmación, separando lo que dice la historia o una decisión de lo que hace el código hoy; lo que no está documentado lo dice y propone `FI-XX`. Si se pide, `output/consultas/<tema>.md`.
- **Tokens**: en cada uso.

### guia-onboarding
- **Cuándo**: cuando alguien se suma al equipo o al proyecto y necesita saber por dónde arrancar.
- **Pedido de ejemplo**: *"Armá el onboarding de Ana, que entra como QA manual"* · *"¿Por dónde arranco en este proyecto? Soy automatizador"*.
- **Entradas**: nombre y rol de la persona; la documentación del proyecto (`input/documentacion/`), el estado del entorno (`npm run doctor`), los conectores activos y lo que ya existe (historias, casos, automatización, informes).
- **Usa**: `scripts/doctor.py --rapido --json`, `npm run conector` y `scripts/generar_onboarding.py`.
- **Entrega**: `output/onboarding/<persona>/` con `plan-onboarding.html` (recorrido del producto con fuentes, estado del entorno, agentes recomendados para su rol con pedidos de ejemplo de este proyecto, plan de las primeras semanas con criterio de hecho, preguntas para el equipo y un checklist que se tilda en el navegador) y `plan-onboarding.md`. No inventa: lo que no está documentado va como pregunta.
- **Tokens**: en cada uso.

### redactor-manual
- **Cuándo**: para crear o actualizar el **manual de usuario** de una funcionalidad, un módulo o **toda la plataforma** (por módulos), o para actualizar solo sus capturas. Además de entregar el manual, deja lo aprendido de la aplicación en `input/documentacion/manual-usuario/` para que los casos de prueba tengan contexto real.
- **Pedido de ejemplo**: *"Armá el manual de usuario del alta de proveedores"* · *"Hacé el manual de toda la plataforma"* · *"Actualizá el manual de Pedidos con la release 2.4"* · *"Actualizá las capturas del manual de Clientes"*.
- **Entradas**: el alcance (funcionalidad, módulo o plataforma; crear o actualizar), la URL del ambiente (`APP_URL`) y, si la app pide login, la sesión de `npm run login` con `SESION=si` (la persona inicia sesión a mano; el agente nunca escribe credenciales). Opcional: el manual anterior, si hace falta el Word (`MANUAL_EQUIPO` firma el documento) y si se autoriza crear datos de prueba.
- **Usa**: skills `redaccion-manual` (matriz de evidencia, gaps, acciones prohibidas, QA REVIEW, aprobación y checklist) e `investigacion-contexto`; `npm run manual` (`herramientas/manual/manual.py`: carpetas y versiones, capturas, HTML autocontenido, Word, checklist, plan de la plataforma y exportación a `input/`); el conector `playwright`. Lee primero lo que ya hay en `input/documentacion/` (dossiers de Jira/Azure DevOps, investigación, mapa funcional, reglas, mensajes), los casos, los `.feature` y la herramienta de gestión.
- **Entrega**: en `output/manuales/<slug>/`: `borradores/<slug>-v0.N.md` y `.html` (y `.docx` a pedido), `capturas/`, `revision/evidencia.md` (matriz, gaps y **Pistas para probar**) y `revision/qa-review.md` (solo lo que requiere revisión humana); con aprobación, `versiones/<slug>-v1.0.md`. Además, `input/documentacion/manual-usuario/<slug>.md` (estado `borrador` o `confirmado`, los REVIEW pendientes como *Sin confirmar*). En modo plataforma, `output/manuales/plataforma/indice.md` con el plan por módulos.
- **Confirma**: los `REVIEW-NNN` (vuelven como "Necesito que confirmes"), cualquier guardado o dato de prueba en la app, y la **aprobación explícita** de la versión final (con `npm run manual -- verificar` en verde). No publica en la wiki ni en ningún servicio salvo pedido explícito.
- **Tokens**: en cada uso (navega solo los gaps, no recorre toda la app; reusa la documentación existente).
### investigador-proyecto
- **Cuándo**: cuando alguien entra a un proyecto y necesita entender de qué se trata y qué preguntar, o para tener a mano el estado, las dudas y las contradicciones de todo el proyecto. Es la foto panorámica; el detalle de una historia lo da `analista-historias` y la base de archivos para los agentes, el `documentador-proyecto`.
- **Pedido de ejemplo**: *"Investigá este tablero: https://mi-empresa.atlassian.net/jira/software/projects/PROJ/boards/12"* · *"Relevá todo lo que haya en Jira y Confluence del proyecto y bajá a las épicas, historias y comentarios"* · *"¿Qué está ambiguo o sin definir en este proyecto?"*.
- **Entradas**: lo más directo es **la URL de un tablero** (board o dashboard de Jira, Azure DevOps, Trello, Linear, monday, ClickUp, Notion, GitHub/GitLab Projects); si no hay URL, la key de Jira, el proyecto de Azure DevOps, el espacio de Confluence o el workspace de la herramienta, y el repositorio (del `.env`). Opcional: la profundidad (`rapida`/`normal`/`completa`), un foco (módulo, épica o release) y el rol de quien llega.
- **Usa**: skills `relevamiento-proyecto` (parsear la URL del tablero, barrer cada herramienta con consultas acotadas, **bajar por épicas → historias → tareas → comentarios → links de referencia**, muestrear backlogs grandes, clasificar ambigüedades y armar preguntas) e `investigacion-contexto` (equivalencias de campos entre herramientas); en solo lectura, los conectores `atlassian` (Jira y Confluence), `azure-devops` (Boards, Wiki, Repos y Test Plans), `github`/`gitlab` (repo e issues) y `figma`; `scripts/generar_informe_investigacion.py`.
- **Entrega**: en `output/investigacion/<proyecto>/`: `informe-investigacion.html` (la web completa, con **mapas conceptuales** de arquitectura y de cómo funciona, el **árbol de épicas/historias/tareas** con sus comentarios y links, los **links de referencia** juntados, resumen del producto, módulos con su avance, actores, flujos, integraciones, ambientes, stack, equipo y a quién preguntar, decisiones, estado del backlog, glosario, línea de tiempo, ambigüedades y contradicciones `AMB-XX` con sus fuentes, preguntas `P-XX` priorizadas, riesgos para QA y qué no se pudo leer), `informe-investigacion.md`, **`resumen.md`** (resumen breve de una carilla) y **`presentacion-investigacion.html`** (presentación autocontenida que imprime a PDF), con la comparación contra el relevamiento anterior en `historial/`. Además deja lo relevado como **documentación del proyecto** en `input/documentacion/proyecto/investigacion/` (resumen, módulos y flujos, backlog, decisiones y glosario, dudas y riesgos; estado `investigacion` o `sin-confirmar`), para que los agentes que analizan historias y escriben casos lo usen como contexto.
- **Tokens**: en cada uso (estructura completa, detalle muestreado; reusa la documentación vigente y el relevamiento anterior).

## Ejecución en vivo

Gastan tokens en cada corrida: sirven para casos sueltos. Lo que se repite conviene automatizarlo con los mappers.

### ejecutor-e2e
- **Cuándo**: para correr en el navegador casos o escenarios que no están automatizados.
- **Pedido de ejemplo**: *"Ejecutá CP-001 y CP-002 de HU-001 contra https://tu-app.com en headless"*.
- **Usa**: skill `ejecucion-e2e`; conectores `playwright` (headed, ves el navegador) o `playwright-headless`; `scripts/generar_reporte.py`.
- **Entrega**: en `output/ejecuciones/`, `reporte-HU-XXX-<fecha-hora>.html` + `_resultados-HU-XXX-<fecha-hora>.json`, y capturas en `evidencia/`.
- **Confirma**: el modo (headed o headless) si no lo dijiste. Las credenciales salen del `.env`.
- **Tokens**: en cada uso.

### ejecutor-api
- **Cuándo**: para correr una colección de Postman, Bruno o Insomnia contra una API.
- **Pedido de ejemplo**: *"Corré la colección de input/api para HU-001"*.
- **Usa**: skill `ejecucion-api`; Newman, con `scripts/correr_newman.py` (token y URL del `.env`, en cualquier sistema).
- **Entrega**: en `output/ejecuciones/`, `reporte-HU-XXX-<fecha-hora>.html` + `_resultados-HU-XXX-<fecha-hora>.json`.
- **Confirma**: correr métodos con efecto (POST/PUT/PATCH/DELETE, mutations).
- **Tokens**: en cada uso.

### analista-seguridad
- **Cuándo**: para revisar la seguridad de una web propia o autorizada.
- **Pedido de ejemplo**: *"Revisá la seguridad de https://staging.tu-app.com para HU-001"*.
- **Usa**: OWASP ZAP en modo pasivo (Docker), `herramientas/zap/escanear.py` y `scripts/generar_informe_seguridad.py`.
- **Entrega**: en `output/seguridad/<HU>/<fecha>/`, `informe-seguridad.html` (hallazgos por riesgo, evidencia, cómo corregir, recomendaciones), `zap.json` y `analisis.json`.
- **Confirma**: la URL (tiene que estar en `SEGURIDAD_URLS_AUTORIZADAS`) y la duración del escaneo. Nunca escanea en modo activo.
- **Tokens**: en cada uso.

### pentester-web
- **Cuándo**: para intentar vulnerar una plataforma propia o autorizada (pentest / ethical hacking) y entregar un informe con los hallazgos.
- **Pedido de ejemplo**: *"Intentá hackear https://staging.tu-app.com y pasame lo que encuentres"*.
- **Usa**: skills `ejecucion-e2e` e `investigacion-contexto`; OWASP ZAP en modo activo (Docker), `herramientas/zap/escanear.py --activo`, Playwright MCP para la verificación manual (OWASP Top 10) y `scripts/generar_informe_seguridad.py`; se apoya en `probador-permisos` y `probador-formularios`.
- **Entrega**: en `output/seguridad/<HU o host>/<fecha>/`, `informe-seguridad.html` (modo activo), `reporte-pentest.md` (hallazgos manuales con pasos para reproducir y corrección), `zap.json` y `analisis.json`.
- **Confirma**: la URL (en `SEGURIDAD_URLS_AUTORIZADAS`), la autorización del escaneo activo (`PENTEST_AUTORIZADO=si`), el ambiente (no producción sin permiso escrito) y el alcance. No es destructivo: nada de DoS, fuerza bruta masiva ni borrar datos.
- **Tokens**: en cada uso (el escaneo activo y la verificación manual).

### probador-salesforce
- **Cuándo**: para probar una org de Salesforce (Sales/Service/Experience Cloud, CPQ o a medida): acceso por perfil, reglas de validación, flows, triggers y cobertura de Apex, sharing (OWD), record types, o para preparar la regresión de una release de Salesforce.
- **Pedido de ejemplo**: *"Probá el sandbox qa-sb de Salesforce"* · *"Revisá las validaciones y flows de la conversión de leads en PROJ-20"* · *"¿Qué hay que probar en nuestra org antes de la release Winter?"*.
- **Entradas**: el alias de la org (en `SALESFORCE_ORGS_AUTORIZADAS`, autorizada con `sf org login web`), la historia o el módulo, y —para ejecutar en la interfaz— los perfiles con usuarios de prueba y su sesión guardada. Requiere la CLI `sf` (`npm install --global @salesforce/cli`).
- **Usa**: skills `pruebas-salesforce`, `pruebas-tokens` (OAuth/JWT de integraciones), `ejecucion-e2e` (Lightning con Playwright MCP) e `investigacion-contexto`; `npm run salesforce` (`herramientas/salesforce/inventario.py`, relevamiento en solo lectura con la CLI `sf`) y `scripts/generar_informe_salesforce.py`; el conector MCP `salesforce` (SOQL de solo lectura y tests de Apex). Se apoya en `probador-permisos` (matriz por rol) y `generador-casos-api`.
- **Entrega**: en `output/salesforce/<HU o alias>/` (la corrida anterior pasa a `historial/`), `informe-salesforce.html` (la org, cobertura de Apex, hallazgos por severidad, sugerencias de prueba derivadas del inventario, pruebas ejecutadas, límites, validaciones, flows, triggers, sharing y record types), `salesforce.json` y `analisis.json`.
- **Confirma**: la org (en `SALESFORCE_ORGS_AUTORIZADAS`, nunca producción salvo lectura con permiso explícito y `--permitir-produccion`), correr los tests de Apex (`--apex`) y crear o mover datos (solo en sandbox, con prefijo `QA-`). No toca metadata, configuración ni permisos.
- **Tokens**: en cada uso (el relevamiento lo hace el script, sin tokens).

### probador-billeteras
- **Cuándo**: para probar billeteras virtuales, fintech y medios de pago: conservación del saldo, estados de transacción, idempotencia, doble gasto y concurrencia, importes y redondeo, límites, KYC/AML, conciliación con la pasarela y seguridad de tokens y tokenización de tarjetas.
- **Pedido de ejemplo**: *"Probá las transferencias P2P de HU-010 en el sandbox"* · *"¿La billetera aguanta dos retiros en paralelo sin quedar en negativo?"* · *"Verificá idempotencia y conciliación de los cobros con tarjeta"*.
- **Entradas**: la historia o el flujo (P2P, carga, retiro, refund…), la API de la billetera (colección en `input/api/` o el contrato, `API_BASEURL` y el token de prueba del `.env`), acceso de solo lectura a la base (para verificar saldos) y los datos y tarjetas de prueba del proveedor. Siempre un ambiente de prueba.
- **Usa**: skills `pruebas-billeteras`, `pruebas-tokens`, `tecnicas-de-diseno` e `investigacion-contexto`; `scripts/generar_informe_billeteras.py`. No tiene binario propio: corre las pruebas con `ejecutor-api` (Newman; idempotencia y concurrencia), Playwright MCP (`ejecucion-e2e`), `verificador-datos` (saldos y ledger por SQL de solo lectura) y `probador-resiliencia` (pasarela caída, reintentos).
- **Entrega**: en `output/billeteras/<HU o nombre>/`, `informe-billeteras.html` (hallazgos por severidad con cómo reproducirlos, pruebas ejecutadas, conservación del saldo, conciliación con el proveedor y recomendaciones) y `analisis.json`.
- **Confirma**: el ambiente (tiene que ser de prueba), y todo lo que mueve dinero (métodos con efecto, cargas, concurrencia). Nunca producción, dinero ni tarjetas reales; no edita datos en la base.
- **Tokens**: en cada uso.

### probador-shopify
- **Cuándo**: para probar una tienda Shopify: un tema nuevo antes de publicarlo, el checkout, una campaña de descuentos, un mercado o moneda nuevos, envíos y stock, o la regresión después de instalar o actualizar una app.
- **Pedido de ejemplo**: *"Probá la tienda de desarrollo qa-tienda.myshopify.com"* · *"Revisá el checkout y los descuentos de la campaña de HU-030"* · *"¿Qué hay que probar antes de publicar el tema nuevo?"*.
- **Entradas**: la URL de la vidriera (en `ECOMMERCE_URLS_AUTORIZADAS`), la historia o el área y, opcionalmente, `SHOPIFY_TIENDA` y `SHOPIFY_ADMIN_TOKEN` (app personalizada con alcances `read_*`) para la Admin API y `SHOPIFY_TEMA_RUTA` con la CLI de Shopify para Theme Check.
- **Usa**: skills `pruebas-shopify`, `pruebas-ecommerce`, `ejecucion-e2e` e `investigacion-contexto`; `npm run shopify` (`herramientas/ecommerce/shopify.py`, relevamiento de solo lectura de la vidriera y la Admin API) y `scripts/generar_informe_ecommerce.py`. Se apoya en `probador-formularios`, `verificador-correos`, `auditor-rendimiento-web`, `analista-accesibilidad` y `pixel-perfect`.
- **Entrega**: en `output/shopify/<HU o host>/` (la corrida anterior pasa a `historial/`), `informe-shopify.html` (la tienda, hallazgos por severidad, sugerencias de prueba, pruebas ejecutadas, chequeos de la vidriera, productos con problemas, políticas, temas, mercados, envíos, descuentos, webhooks, Theme Check y evolución de las corridas), `shopify.json` y `analisis.json`.
- **Confirma**: la tienda (en `ECOMMERCE_URLS_AUTORIZADAS`), los pedidos de prueba (solo con la pasarela en modo de prueba; en una tienda real, mejor no comprar) y crear clientes o usar descuentos. No cambia temas, apps ni configuración; la seguridad queda para `analista-seguridad` y `pentester-web`.
- **Tokens**: en cada uso (el relevamiento lo hace el script, sin tokens).

### probador-wordpress
- **Cuándo**: para probar un sitio WordPress o una tienda WooCommerce: checkout (clásico o de bloques), pasarelas, envíos, impuestos, cupones, stock, correos y roles, o la regresión antes o después de actualizar WordPress, WooCommerce, el tema o un plugin.
- **Pedido de ejemplo**: *"Probá la tienda WooCommerce de staging"* · *"Actualizamos WooCommerce en staging: corré la regresión del checkout"* · *"¿Por qué los pedidos quedan en pendiente?"*.
- **Entradas**: la URL del sitio (en `ECOMMERCE_URLS_AUTORIZADAS`), la historia o el área y, opcionalmente, `WOOCOMMERCE_CONSUMER_KEY`/`SECRET` (clave de lectura) para la REST API y `WORDPRESS_RUTA_LOCAL` o `WORDPRESS_WP_CLI` para WP-CLI; usuarios de prueba por rol con sesión guardada si se prueban Mi cuenta o permisos.
- **Usa**: skills `pruebas-wordpress`, `pruebas-ecommerce`, `ejecucion-e2e` e `investigacion-contexto`; `npm run wordpress` (`herramientas/ecommerce/wordpress.py`, relevamiento de solo lectura de la vidriera, la REST API de WooCommerce y WP-CLI) y `scripts/generar_informe_ecommerce.py`. Se apoya en `probador-formularios`, `verificador-correos`, `probador-permisos`, `auditor-rendimiento-web` y `analista-accesibilidad`.
- **Entrega**: en `output/wordpress/<HU o host>/` (la corrida anterior pasa a `historial/`), `informe-wordpress.html` (el sitio y sus versiones, hallazgos por severidad, sugerencias, pruebas ejecutadas, chequeos de la vidriera, productos con problemas, plugins, templates desactualizados, páginas de WooCommerce, pasarelas y su modo, zonas de envío, cupones, webhooks y evolución de las corridas), `wordpress.json` y `analisis.json`.
- **Confirma**: el sitio (en `ECOMMERCE_URLS_AUTORIZADAS`), los pedidos de prueba (solo con la pasarela en modo de prueba), crear clientes, usar cupones y enviar formularios. No actualiza ni activa plugins, temas ni WordPress y no cambia ajustes; la seguridad queda para `analista-seguridad` y `pentester-web`.
- **Tokens**: en cada uso (el relevamiento lo hace el script, sin tokens).

### probador-prestashop
- **Cuándo**: para probar una tienda PrestaShop (1.6, 1.7, 8.x): un smoke test de instalación local, el checkout (invitado, transportistas, términos), pagos de prueba, combinaciones y stock, impuestos y redondeo, el rendimiento (Smarty, CCC, caché, modo desarrollador), multitienda y multi-idioma, o la regresión después de instalar o actualizar un módulo o el tema.
- **Pedido de ejemplo**: *"Probá la tienda PrestaShop de staging"* · *"Levanté PrestaShop en Docker, hacele un smoke test"* · *"Revisá el checkout y los transportistas de HU-040"* · *"¿Por qué la tienda está lenta?"*.
- **Entradas**: la URL de la tienda (en `ECOMMERCE_URLS_AUTORIZADAS`), la historia o el área y, opcionalmente, `PRESTASHOP_WEBSERVICE_KEY` (clave de solo lectura) para la Webservice API, `PRESTASHOP_RUTA_LOCAL` (o `--local`) para la versión y el modo dev, y la carpeta del back-office (`/admin-XXXX`) si se prueba el BO.
- **Usa**: skills `pruebas-prestashop`, `pruebas-ecommerce`, `ejecucion-e2e`, `guia-performance` (si incluye carga) e `investigacion-contexto`; `npm run prestashop` (`herramientas/ecommerce/prestashop.py`, relevamiento de solo lectura de la vidriera, la Webservice API y la instalación local) y `scripts/generar_informe_ecommerce.py`. Se apoya en `probador-formularios`, `verificador-correos`, `probador-permisos`, `auditor-rendimiento-web`, `performance-mapper`, `analista-accesibilidad`, `analista-traductor` y `pixel-perfect`.
- **Entrega**: en `output/prestashop/<HU o host>/` (la corrida anterior pasa a `historial/`), `informe-prestashop.html` (la tienda y su versión, hallazgos por severidad, sugerencias, pruebas ejecutadas, chequeos de la vidriera, productos con problemas, transportistas, monedas, vales, configuración de rendimiento y evolución de las corridas), `prestashop.json` y `analisis.json`.
- **Confirma**: la tienda (en `ECOMMERCE_URLS_AUTORIZADAS`), los pedidos de prueba (solo con la pasarela en modo de prueba, o transferencia/contra reembolso), crear clientes y usar vales. No instala ni configura módulos, no edita el tema ni los ajustes; la Webservice es de lectura. La seguridad queda para `analista-seguridad` y `pentester-web`.
- **Tokens**: en cada uso (el relevamiento lo hace el script, sin tokens).

### probador-vtex
- **Cuándo**: para probar una tienda VTEX: el checkout y el orderForm, el catálogo y los canales de venta (trade policies), las promociones y su acumulación, los envíos (SLAs), los medios de pago en sandbox, una app de VTEX IO, el marketplace o la regresión antes de promover a master.
- **Pedido de ejemplo**: *"Probá la tienda VTEX de qa"* · *"Revisá el checkout y las promos de HU-050"* · *"Promovimos una app de VTEX IO: corré la regresión del flujo de compra"* · *"¿Qué hay que probar antes de pasar a master?"*.
- **Entradas**: la URL del storefront (en `ECOMMERCE_URLS_AUTORIZADAS`) y la cuenta (`VTEX_ACCOUNT` o deducida de la URL), la historia o el área y, opcionalmente, `VTEX_APP_KEY`/`VTEX_APP_TOKEN` (app de solo lectura) para las APIs de administración, `VTEX_WORKSPACE` (el de QA) y `VTEX_SALES_CHANNEL`.
- **Usa**: skills `pruebas-vtex`, `pruebas-ecommerce`, `ejecucion-e2e`, `guia-performance` (si incluye carga) e `investigacion-contexto`; `npm run vtex` (`herramientas/ecommerce/vtex.py`, relevamiento de solo lectura de la vidriera, el Catalog System público y las APIs de administración) y `scripts/generar_informe_ecommerce.py`. Se apoya en `probador-formularios`, `verificador-correos`, `probador-permisos`, `auditor-rendimiento-web`, `performance-mapper`, `analista-accesibilidad` y `pixel-perfect`.
- **Entrega**: en `output/vtex/<HU o host>/` (la corrida anterior pasa a `historial/`), `informe-vtex.html` (la cuenta y el workspace, el storefront, hallazgos por severidad, sugerencias, pruebas ejecutadas, chequeos de la vidriera, productos con problemas, canales de venta, políticas de envío, promociones y evolución de las corridas), `vtex.json` y `analisis.json`.
- **Confirma**: la tienda (en `ECOMMERCE_URLS_AUTORIZADAS`), que no se toque `master` de forma destructiva (se prueba en un workspace de QA), los pagos de prueba (solo en sandbox) y crear clientes o consumir promociones. No promueve ni instala apps, no edita catálogo, precios ni configuración; la app es de lectura. La seguridad queda para `analista-seguridad` y `pentester-web`.
- **Tokens**: en cada uso (el relevamiento lo hace el script, sin tokens).

### probador-sap
- **Cuándo**: para probar un sistema SAP (S/4HANA o ECC) en un mandante de QA: una transacción del SAP GUI, una app Fiori o un servicio OData, un rol/autorización, un proceso de negocio de punta a punta (O2C, P2P, R2R) o la regresión después de un transporte o un upgrade.
- **Pedido de ejemplo**: *"Probá el proceso Order to Cash en QAS"* · *"Revisá el rol Z_VENTAS y sus autorizaciones"* · *"Importamos un transporte: corré la regresión de P2P"* · *"Probá esta app Fiori y su servicio OData"*.
- **Entradas**: el SID y mandante de QA, el tipo (S/4HANA o ECC), usuarios de prueba por rol, la URL del launchpad de Fiori (autorizada), y el SAP GUI Scripting habilitado si se automatiza el GUI.
- **Usa**: skills `pruebas-sap`, `ejecucion-e2e` (Fiori con Playwright), `ejecucion-api` (OData), `guia-performance` (si incluye carga) e `investigacion-contexto`; `npm run sap` (`herramientas/sap/sap_gui.py`, relevamiento de solo lectura de la sesión del GUI) y `scripts/generar_informe_sap.py`. Se apoya en `probador-permisos`, `auditor-rendimiento-web`, `performance-mapper`, `analista-seguridad` y `pentester-web`.
- **Entrega**: en `output/sap/<HU o host>/`, `informe-sap.html` (el sistema y mandante, hallazgos por severidad, autorizaciones, procesos de negocio, pruebas ejecutadas, recomendaciones y Falta información), `analisis.json` y, si se corrió, `relevamiento.json`.
- **Confirma**: que sea un mandante de QA (nunca productivo), la escritura de negocio (crear o contabilizar documentos, jobs, IDocs) y no cambiar roles ni configuración. La visualización no necesita confirmación. La seguridad (SoD, roles amplios, RFC) queda para `analista-seguridad` y `pentester-web`.
- **Tokens**: en cada uso (el relevamiento del GUI lo hace el script, sin tokens).

### probador-desktop
- **Cuándo**: para probar una app de escritorio de Windows (WinForms, WPF, UWP, Win32, Electron, Java, Qt): su instalación y actualización, un flujo funcional, la compatibilidad con versiones de Windows y DPI, el rendimiento o la regresión de una nueva versión.
- **Pedido de ejemplo**: *"Probá la instalación y el flujo de alta del Facturador"* · *"Revisá la app con DPI al 150% en multi-monitor"* · *"Salió una versión nueva: corré la regresión"* · *"Probá esta app Electron"*.
- **Entradas**: el nombre, versión y **tecnología** de la app, la ruta del ejecutable o AppId, cómo se instala y si requiere admin, la versión de Windows y el DPI a soportar, y la herramienta de automatización (Appium + WinAppDriver o pywinauto para nativas, Playwright para Electron).
- **Usa**: skills `pruebas-desktop`, `ejecucion-e2e` (Electron con Playwright), `guia-performance` (si incluye carga) e `investigacion-contexto`; `npm run desktop` (`herramientas/desktop/controles.py`, relevamiento de solo lectura del árbol de controles con pywinauto) y `scripts/generar_informe_desktop.py`. Se apoya en `probador-formularios`, `analista-accesibilidad`, `auditor-rendimiento-web`, `performance-mapper`, `analista-seguridad` y `pentester-web`.
- **Entrega**: en `output/desktop/<HU o app>/`, `informe-desktop.html` (la app y su tecnología, hallazgos por severidad, pruebas ejecutadas, compatibilidad, recomendaciones y Falta información), `analisis.json` y, si se corrió, `arbol.json`.
- **Confirma**: que sea una máquina o VM de QA (no producción), instalar/actualizar/desinstalar y escribir en el registro o el sistema de archivos. El relevamiento del árbol es de solo lectura. La parte de red/servicios queda para `analista-seguridad` y `pentester-web`.
- **Tokens**: en cada uso (el relevamiento del árbol lo hace el script, sin tokens).

### probador-mobile
- **Cuándo**: para probar una app móvil (Android o iOS; nativa, híbrida o web/PWA) en vivo: permisos, interrupciones, offline, deep links y push, ciclo de vida, compatibilidad de OS y pantallas, o la regresión de una nueva build. Para generar la automatización, el `mobile-mapper`.
- **Pedido de ejemplo**: *"Probá la app en Android 14 y en un iPhone chico"* · *"¿Qué pasa si el usuario niega el permiso de ubicación?"* · *"Probá el deep link y el push con la app cerrada"* · *"Regresión de la build 4.1 offline"*.
- **Entradas**: plataforma y tipo de app, APK/AAB o IPA (o cómo se instala: Play Internal, TestFlight), la matriz de OS/dispositivos, usuarios de prueba, y el conector `appium` activo (`npm run conector -- activar appium`).
- **Usa**: skills `pruebas-mobile`, `guia-performance` (si incluye carga) e `investigacion-contexto`; Appium (MCP) para ejecutar y `scripts/generar_informe_mobile.py`. Se apoya en `mobile-mapper`, `probador-formularios`, `verificador-correos`, `analista-accesibilidad`, `performance-mapper`, `analista-seguridad` y `pentester-web`.
- **Entrega**: en `output/mobile/<HU o app>/`, `informe-mobile.html` (la app y plataforma, hallazgos por severidad, pruebas por dispositivo, compatibilidad y Falta información), `analisis.json` y capturas.
- **Confirma**: dispositivo/emulador de QA (no datos reales), instalar/actualizar la app, y acciones con efecto (pagos en sandbox). La seguridad de red/backend queda para `analista-seguridad` y `pentester-web`.
- **Tokens**: en cada uso (ejecuta en vivo con Appium).

### analista-dependencias
- **Cuándo**: para revisar la seguridad de las dependencias de un proyecto (SCA): CVEs de los paquetes, `npm audit`, licencias o cadena de suministro. Solo lectura.
- **Pedido de ejemplo**: *"Revisá las dependencias de mi-app por vulnerabilidades"* · *"¿Qué CVEs críticos tenemos y cuáles tienen fix?"* · *"Chequeá las licencias de los paquetes"*.
- **Entradas**: la ruta del repositorio (`--ruta` o `REPO_RUTA_LOCAL`) con sus lockfiles; el alcance (prod o también dev, severidad mínima, si se revisan licencias). Escáneres: `npm`, `pip-audit`, `osv-scanner` (los que estén).
- **Usa**: skills `analisis-dependencias` e `investigacion-contexto`; `npm run dependencias` (`herramientas/seguridad/dependencias.py`) y `scripts/generar_informe_dependencias.py`. Complementa a `analista-seguridad` y `pentester-web` (DAST).
- **Entrega**: en `output/dependencias/<proyecto>/`, `informe-dependencias.html` (vulnerabilidades por severidad, directas/transitivas, fix, licencias), `sca.json` y `analisis.json`.
- **Confirma**: nada con efecto (solo lectura): no instala ni actualiza dependencias ni abre PRs; eso lo recomienda.
- **Tokens**: en cada uso (el escaneo lo hacen las herramientas, sin tokens).

### revisor-codigo
- **Cuándo**: para una revisión de código (code review) estática de un repositorio entero, una rama o un PR/MR de **GitHub, GitLab, Bitbucket, Azure Repos, Gitea/Codeberg** o cualquier git (o una carpeta local): seguridad, performance, confiabilidad, malas prácticas y mantenibilidad, con la decisión sugerida para el merge. Solo lectura.
- **Pedido de ejemplo**: *"Revisá este PR: https://github.com/mi-empresa/app/pull/42"* · *"Hacé un code review del repo buscando problemas de performance"* · *"Revisá la rama feature-pagos contra main"*.
- **Entradas**: la URL del repo/rama/PR/MR o una ruta local (si no, `REPO_PROVEEDOR` + `REPO_NOMBRE` del `.env`), el alcance (todo o solo lo que cambió, foco, qué severidad bloquea) y, para repos privados, el token de solo lectura del proveedor en el `.env` (`GITHUB_TOKEN`, `GITLAB_TOKEN`, `BITBUCKET_TOKEN`, `ADO_PAT` o `REVISION_GIT_TOKEN`). `semgrep`, `ruff` y `bandit` son opcionales.
- **Usa**: skills `revision-codigo`, `codigo-seguro` e `investigacion-contexto`; `npm run obtener-codigo` (`herramientas/codigo/obtener.py`: clona sin ejecutar nada y calcula el diff del PR contra el merge-base), `npm run revision-codigo` (`herramientas/codigo/revision.py`: reglas por lenguaje, métricas, duplicados, secretos y escáneres opcionales) y `scripts/generar_informe_revision_codigo.py`. Complementa a `analista-codigo-seguro` (SAST profundo), `analista-dependencias` (SCA) y `analista-mutacion` (calidad de los tests).
- **Entrega**: en `output/revision-codigo/<repo>/`, `informe-revision-codigo.html` (decisión sugerida, hallazgos confirmados con link a la línea, impacto y código sugerido, funciones más complejas, descartados y fortalezas), `comentarios-pr.md` (listo para pegar en el PR/MR), `origen.json`, `cambios.diff`, `revision.json` y `analisis.json`. El clon queda en `fuente/` (no se versiona).
- **Confirma**: nada con efecto (solo lectura): no ejecuta ni modifica el código y **no publica** comentarios ni aprueba el PR; eso lo hace la persona. Nunca expone el valor de un secreto.
- **Tokens**: en cada uso (el relevamiento lo hacen las herramientas; leer el diff y el triage sí consumen; corre en opus).

### analista-codigo-seguro
- **Cuándo**: para análisis estático de seguridad del código (SAST) y búsqueda de secretos: correr semgrep, encontrar credenciales expuestas, revisar el código por inyección/XSS/cripto antes de una release. Solo lectura.
- **Pedido de ejemplo**: *"Corré un SAST sobre el repo"* · *"Buscá secretos o claves en el código"* · *"Revisá el código por inyección SQL"*.
- **Entradas**: la ruta del repositorio (`--ruta` o `REPO_RUTA_LOCAL`), lenguajes/frameworks, el alcance (severidad que bloquea, partes fuera de alcance). `semgrep` para el SAST (opcional; el escáner de secretos integrado corre siempre).
- **Usa**: skills `codigo-seguro` e `investigacion-contexto`; `npm run sast` (`herramientas/seguridad/sast.py`) y `scripts/generar_informe_sast.py`. Complementa a `analista-dependencias` (SCA) y a `analista-seguridad`/`pentester-web` (DAST).
- **Entrega**: en `output/sast/<proyecto>/`, `informe-sast.html` (hallazgos SAST mapeados a OWASP/CWE y secretos redactados a rotar), `sast.json` y `analisis.json`.
- **Confirma**: nada con efecto (solo lectura): no modifica el código ni rota secretos; lo recomienda con el paso a paso. Nunca expone el valor de un secreto.
- **Tokens**: en cada uso (el triage de falsos positivos sí consume; corre en opus por lo sensible).

### probador-ia
- **Cuándo**: para probar funciones de IA / LLM de un producto: un chatbot, un RAG, un clasificador o un agente; calidad y alucinaciones, grounding, seguridad de prompt, formato, robustez o la regresión de un prompt/modelo.
- **Pedido de ejemplo**: *"Probá el chatbot: ¿alucina o se le puede hacer prompt injection?"* · *"Armá un golden set y medí la exactitud del clasificador"* · *"Probá el RAG: ¿cita bien las fuentes?"*.
- **Entradas**: el tipo de función, el modelo y proveedor, el endpoint o la URL del chat, el **criterio de éxito** (qué es una buena respuesta, objetivo de exactitud, qué NO debe hacer), y para RAG las fuentes. Ambiente de QA.
- **Usa**: skills `pruebas-ia`, `ejecucion-api` (endpoint), `ejecucion-e2e` (UI del chat) e `investigacion-contexto`; `scripts/generar_informe_ia.py`. Se apoya en `generador-datos-prueba` (golden set y casos adversarios).
- **Entrega**: en `output/ia/<HU o función>/`, `informe-ia.html` (métricas contra objetivo, hallazgos por categoría —incluida seguridad de prompt—, pruebas y Falta información), `analisis.json` y la evidencia (prompt+respuesta, sin PII).
- **Confirma**: pegarle a un endpoint que tiene **costo** por llamada, usar datos que no sean de prueba, y acciones con efecto de un **agente con herramientas**. No manda PII ni datos reales al proveedor.
- **Tokens**: en cada uso (corre el golden set contra el LLM; acota el tamaño del set).

### probador-mensajeria
- **Cuándo**: para probar un sistema asíncrono / event-driven: una cola, un topic, un broker (Kafka, RabbitMQ, SQS/SNS, MQTT), un WebSocket o SSE; entrega, orden, idempotencia, DLQ, esquemas o consumer lag.
- **Pedido de ejemplo**: *"Probá que el consumidor de pedidos sea idempotente"* · *"¿Qué pasa con un mensaje envenenado en la cola?"* · *"Revisá el orden de los eventos de un pedido"* · *"Probá el WebSocket de notificaciones"*.
- **Entradas**: el broker y el destino (topic/cola/URL) de QA, el esquema del mensaje, la garantía esperada (orden, idempotencia) y el flujo (productor → consumidor → efecto). Librerías del broker (kafka-python, pika, paho-mqtt, websocket-client; SSE usa stdlib).
- **Usa**: skills `pruebas-async`, `guia-performance` (consumer lag/carga) e `investigacion-contexto`; `npm run mensajeria` (`herramientas/mensajeria/mensajeria.py`) y `scripts/generar_informe_mensajeria.py`. Se apoya en `verificador-datos` (outbox/efecto en la base) y `performance-mapper`.
- **Entrega**: en `output/mensajeria/<HU>/`, `informe-mensajeria.html` (hallazgos por categoría —orden, idempotencia, DLQ, esquema—, pruebas y Falta información), `analisis.json` y muestras de mensajes (sin PII).
- **Confirma**: **publicar** mensajes (tiene efecto: dispara consumidores), siempre contra un broker de QA. Consumir e inspeccionar son de lectura.
- **Tokens**: en cada uso (publica/consume con la herramienta).

### probador-scalar
- **Cuándo**: para probar una API que el equipo tiene en **Scalar** (scalar.com): conectarse a su server MCP, usar los endpoints y documentos del Registry, escribir casos de prueba, correrlos y **llevarlos de vuelta a Scalar**.
- **Pedido de ejemplo**: *"Conectate al MCP de Scalar y probá la API de pagos"* · *"Armá los casos de la API galaxy del Registry y corrélos contra QA"* · *"Importá los casos de HU-012 a Scalar"*.
- **Entradas**: namespace y slug de la API en el Registry (o `SCALAR_MCP_URL`), el alcance (operaciones o historia), el ambiente (`API_BASEURL`, `API_TOKEN`) y, para publicar, la confirmación con namespace, slug y versión nueva.
- **Usa**: skills `pruebas-scalar`, `ejecucion-api`, `pruebas-graphql` (si es GraphQL) e `investigacion-contexto`; el conector `scalar` (MCP de la API: busca operaciones y ejecuta lecturas), `npm run scalar` (`herramientas/scalar/scalar.py`: descarga del Registry, colección de casos con tests `pm`, OpenAPI enriquecido con ejemplos por caso y `x-post-response`, validación y publicación con `@scalar/cli`), `scripts/resumir_openapi.py` y `scripts/correr_newman.py`.
- **Entrega**: en `output/scalar/<api>/`, `casos.json`, `casos-api-<HU o api>.md`, `<api>.postman_collection.json` (un request por caso con sus tests; corre con Newman y se importa en el cliente de Scalar) y `<api>.k0lmenia.json` (el OpenAPI con los casos, listo para el Registry); el contrato en `input/api/scalar/<api>.json`; el reporte de la corrida en `output/ejecuciones/`.
- **Confirma**: ejecutar operaciones con efecto (POST/PUT/PATCH/DELETE) por el MCP o por Newman, y **publicar** en el Registry (versión nueva, privada por defecto; nunca pisa una versión sin pedido explícito).
- **Tokens**: en la exploración y al escribir los casos; las corridas de la colección no gastan tokens ni créditos de Scalar.
### probador-soap
- **Cuándo**: para probar un servicio web SOAP: su WSDL, operaciones, validación de esquema, SOAP Faults, namespaces/SOAPAction o WS-Security.
- **Pedido de ejemplo**: *"Probá el servicio SOAP de clientes desde su WSDL"* · *"¿Los errores de negocio devuelven un Fault bien formado?"* · *"Probá WS-Security del endpoint"*.
- **Entradas**: el WSDL (URL o archivo) y el endpoint de QA, la versión (1.1/1.2), la seguridad (WS-Security o TLS) y el alcance (qué operaciones, cuáles con efecto, qué Faults).
- **Usa**: skills `pruebas-soap`, `ejecucion-api` (envía los sobres por HTTP con Newman) e `investigacion-contexto`; `npm run soap` (`herramientas/soap/wsdl.py`, relevamiento del WSDL y sobre de ejemplo) y `scripts/generar_informe_soap.py`.
- **Entrega**: en `output/soap/<servicio>/`, `informe-soap.html` (operaciones, pruebas, hallazgos —Faults, validación, seguridad— y Falta información), `wsdl.json` y `analisis.json`.
- **Confirma**: invocar **operaciones con efecto** (escritura), contra QA. Relevar el WSDL y las consultas son de lectura. La explotación (XXE, WS-Security) queda para `analista-seguridad`/`pentester-web`.
- **Tokens**: en cada uso (el relevamiento del WSDL lo hace el script, sin tokens).

### probador-contratos
- **Cuándo**: para contract testing entre servicios (Pact/consumer-driven), compatibilidad entre consumidor y proveedor, o validar una API contra su OpenAPI, en REST, GraphQL, gRPC o eventos.
- **Pedido de ejemplo**: *"Corré las pruebas de contrato entre el front y pagos-api"* · *"¿Este cambio en la API rompe a algún consumidor?"* · *"Verificá el proveedor contra los pacts"*.
- **Entradas**: qué servicios son consumidor y proveedor, el protocolo, si usan Pact/PactFlow (broker) o una OpenAPI, y cómo se preparan los provider states. Ambientes de QA.
- **Usa**: skills `pruebas-contratos`, `ejecucion-api` e `investigacion-contexto`; `scripts/generar_informe_generico.py`. Coordina con los agentes de API y el `probador-mensajeria` (eventos).
- **Entrega**: en `output/contratos/<HU>/`, `informe-contratos.html` (interacciones, verificaciones, compatibilidad y Falta información) y `analisis.json`.
- **Confirma**: publicar pacts y correr verificaciones con efecto (provider states que escriben), en QA.
- **Tokens**: en cada uso.

### analista-seo
- **Cuándo**: para analizar el SEO y el GEO de un sitio: indexabilidad, datos estructurados, hreflang, o aparecer en AI Overviews/ChatGPT/Perplexity. Solo lectura.
- **Pedido de ejemplo**: *"Hacé un análisis SEO de esta página"* · *"¿Está indexable y tiene datos estructurados?"* · *"¿Permitimos a los crawlers de IA? (GEO)"*.
- **Entradas**: la URL o lista de URLs, si es SSR o CSR, idiomas/regiones, keywords objetivo, y si se quiere aparecer en motores con IA.
- **Usa**: skills `pruebas-seo` e `investigacion-contexto`; `npm run seo` (`herramientas/seo/seo.py`) y `scripts/generar_informe_generico.py`. Deriva CWV al `auditor-rendimiento-web` y hreflang/idiomas al `analista-traductor`.
- **Entrega**: en `output/seo/<pagina o sitio>/`, `informe-seo.html` (hallazgos priorizados, on-page, datos estructurados, estado del GEO) y `analisis.json`.
- **Confirma**: nada con efecto (solo lectura): no modifica el sitio; permitir/bloquear crawlers lo recomienda.
- **Tokens**: en cada uso (el relevamiento lo hace el script).

### probador-datos
- **Cuándo**: para probar datos y pipelines (ETL/ELT, data warehouse): calidad de datos, reconciliación origen↔destino, validación de esquema, transformaciones e idempotencia.
- **Pedido de ejemplo**: *"Reconciliá origen y destino del ETL"* · *"Revisá la calidad de datos del warehouse"* · *"¿El pipeline es idempotente?"*.
- **Entradas**: origen y destino (conexiones del `.env`), las transformaciones/filtros esperados, la clave de negocio, la ventana de frescura y si hay SCD/incremental. Nunca producción para escrituras.
- **Usa**: skills `pruebas-datos` e `investigacion-contexto`; `scripts/generar_informe_generico.py`. Se apoya en el `verificador-datos` (consultas de solo lectura).
- **Entrega**: en `output/datos/<HU>/`, `informe-datos.html` (reconciliación, calidad por dimensión, hallazgos) y `analisis.json`.
- **Confirma**: cualquier escritura o reprocesar un pipeline (tiene efecto); nunca en producción. Las consultas son de lectura.
- **Tokens**: en cada uso.

### probador-dynamics
- **Cuándo**: para probar Microsoft Dynamics 365 u otro CRM/ERP de bajo código (sandbox): roles, lógica (flows, plugins, BPF, roll-ups), formularios y procesos de negocio end-to-end.
- **Pedido de ejemplo**: *"Probá el proceso de Sales en Dynamics"* · *"Revisá los roles de seguridad y qué ve cada uno"* · *"¿El SLA de Customer Service escala bien?"*.
- **Entradas**: el CRM/ERP y módulos, el entorno/sandbox, usuarios por rol, los procesos en alcance y, para la Web API, la URL de Dataverse con credenciales de lectura.
- **Usa**: skills `pruebas-dynamics`, `ejecucion-e2e` e `investigacion-contexto`; `scripts/generar_informe_generico.py`. Se apoya en `probador-permisos` y `verificador-correos`.
- **Entrega**: en `output/dynamics/<HU>/`, `informe-dynamics.html` (acceso por rol, lógica verificada, procesos) y `analisis.json`.
- **Confirma**: crear/editar registros y disparar flujos con efecto, en sandbox (nunca producción). Relevar por la Web API es de lectura.
- **Tokens**: en cada uso.

### probador-blockchain
- **Cuándo**: para probar smart contracts o una dApp Web3 (testnet o nodo local): funcional, tokens, gas, seguridad on-chain e integración con la wallet.
- **Pedido de ejemplo**: *"Probá el smart contract en Sepolia"* · *"¿Es vulnerable a reentrancy?"* · *"Verificá las invariantes del token"*.
- **Entradas**: la cadena/red y chain id, la testnet o nodo, el código fuente/ABI y las direcciones de QA, si es upgradeable, los estándares de token y las invariantes de negocio. Nunca mainnet con fondos reales.
- **Usa**: skills `pruebas-blockchain`, `ejecucion-api` e `investigacion-contexto`; `scripts/generar_informe_generico.py`. Coordina el análisis estático con `analista-codigo-seguro` y recomienda auditoría formal para lo crítico.
- **Entrega**: en `output/blockchain/<HU>/`, `informe-blockchain.html` (funcional, invariantes, gas, hallazgos de seguridad) y `analisis.json`.
- **Confirma**: enviar transacciones (gastan gas/fondos de testnet) y desplegar; las llamadas view y el análisis estático son de lectura.
- **Tokens**: en cada uso (corre en opus por lo sensible de la seguridad).

### probador-ivr
- **Cuándo**: para probar un IVR, un árbol de menús telefónico, un voicebot o un contact center de voz.
- **Pedido de ejemplo**: *"Probá el árbol del IVR"* · *"¿Siempre se puede llegar a un humano?"* · *"Revisá el voicebot de atención"*.
- **Entradas**: el diagrama del árbol y los prompts, el modo de ingreso (DTMF/voz), idiomas, reintentos y salida al operador, horarios, si hay pagos por voz (PCI) y si es IVR o voicebot. Número de QA y herramienta de testing de voz si existe.
- **Usa**: skills `pruebas-ivr` e `investigacion-contexto`; `scripts/generar_informe_generico.py`. Para la NLU/LLM del voicebot, el `probador-ia`.
- **Entrega**: en `output/ivr/<HU>/`, `informe-ivr.html` (recorrido del árbol, pruebas por rama, hallazgos) y `analisis.json`.
- **Confirma**: operaciones con efecto por teléfono (pagos, cambios); recorrer el árbol en QA es seguro.
- **Tokens**: en cada uso (mucho del testing de IVR es manual asistido).

### probador-juegos
- **Cuándo**: para probar un videojuego (Unity/Unreal/Godot/HTML5/mobile/consola/PC): mecánicas, guardado, compatibilidad, rendimiento, multijugador o monetización.
- **Pedido de ejemplo**: *"Probá las mecánicas y la progresión"* · *"¿Hay soft-locks o formas de romper el mundo?"* · *"Revisá el multijugador y el anti-cheat"*.
- **Entradas**: el motor y las plataformas objetivo, el género y las mecánicas críticas, single/multijugador, si hay compras in-app/loot boxes, los FPS/tiempos objetivo y cómo se guarda. Build de QA por plataforma.
- **Usa**: skills `pruebas-juegos` e `investigacion-contexto`; `scripts/generar_informe_generico.py`. Para IA de NPCs, el `probador-ia`; carga, `performance-mapper`; traducciones, `analista-traductor`.
- **Entrega**: en `output/juegos/<HU>/`, `informe-juegos.html` (smoke por plataforma, mecánicas, rendimiento, multijugador, hallazgos) y `analisis.json`.
- **Confirma**: compras in-app (sandbox) y acciones con efecto en servidores compartidos.
- **Tokens**: en cada uso (mucho es exploratorio manual).

### probador-pos
- **Cuándo**: para probar un punto de venta (POS), una caja, pagos en tienda, periféricos o hardware de venta.
- **Pedido de ejemplo**: *"Probá el flujo de venta y el cierre de caja"* · *"¿Qué pasa si se corta la luz a mitad de la venta?"* · *"Probá el pago con tarjeta y la impresora"*.
- **Entradas**: el hardware (pinpad/adquirente, impresora, balanza, cajón) y si hay simuladores/SDK, los medios de pago y la pasarela (modo de prueba), si funciona offline y cómo concilia, la integración fiscal y el país, y qué requiere autorización de supervisor.
- **Usa**: skills `pruebas-pos` e `investigacion-contexto`; `scripts/generar_informe_generico.py`. Se apoya en el `probador-billeteras` (conciliación de dinero y pasarelas).
- **Entrega**: en `output/pos/<HU>/`, `informe-pos.html` (flujo de venta, pagos, periféricos, fiscal, offline, cierre de caja) y `analisis.json`.
- **Confirma**: cobros (solo en modo de prueba) y operaciones fiscales con efecto; el recorrido del flujo en QA es seguro.
- **Tokens**: en cada uso.

### analista-observabilidad
- **Cuándo**: para validar la observabilidad de un servicio: que emita bien logs, métricas y trazas, los healthchecks (liveness/readiness), el error tracking y que las alertas/SLOs disparen.
- **Pedido de ejemplo**: *"Revisá la observabilidad del servicio de pagos"* · *"¿Los logs llevan trace id y no filtran PII?"* · *"¿Las métricas y healthchecks están bien?"*.
- **Entradas**: la URL del servicio y las rutas de health/metrics, el stack de observabilidad (Prometheus/Grafana, OTel, ELK…), las métricas y SLOs oficiales, y qué está prohibido loguear.
- **Usa**: skills `pruebas-observabilidad`, `ejecucion-api` e `investigacion-contexto`; `npm run observabilidad` (`herramientas/observabilidad/observabilidad.py`) y `scripts/generar_informe_generico.py`. Se apoya en `analista-logs`, `performance-mapper` y `probador-resiliencia` (para provocar alertas).
- **Entrega**: en `output/observabilidad/<svc>/`, `informe-observabilidad.html` (estado de los tres pilares, healthchecks, métricas faltantes, PII en logs, alertas) y `analisis.json`.
- **Confirma**: generar tráfico más allá de unos pocos requests y provocar condiciones de alerta en ambientes compartidos; consultar health/metrics es de lectura.
- **Tokens**: en cada uso.

### probador-busqueda
- **Cuándo**: para probar la búsqueda y la relevancia (Elasticsearch/OpenSearch, Algolia, Solr, DB full-text): ranking, typos, sinónimos, facetas, autocompletar e indexación.
- **Pedido de ejemplo**: *"Probá el buscador del sitio"* · *"¿La búsqueda tolera typos y trae lo relevante arriba?"* · *"Revisá las facetas y el cero-resultados"*.
- **Entradas**: el motor y el endpoint/UI de búsqueda, las consultas importantes con su resultado esperado (golden set), el boosting/reglas, sinónimos/stemming e idiomas, el delay de indexación y si hay documentos con permisos.
- **Usa**: skills `pruebas-busqueda`, `ejecucion-api`, `ejecucion-e2e` e `investigacion-contexto`; `scripts/generar_informe_generico.py`. Se apoya en `generador-datos-prueba` y `performance-mapper`.
- **Entrega**: en `output/busqueda/<HU>/`, `informe-busqueda.html` (golden set con posición esperada/obtenida, métricas precision@k/nDCG, facetas, indexación, hallazgos) y `analisis.json`.
- **Confirma**: reindexar o cargar datos al índice (tiene efecto); buscar es de lectura.
- **Tokens**: en cada uso.

### probador-documentos
- **Cuándo**: para probar documentos generados por la app (PDF, Excel, CSV): facturas, reportes, estados de cuenta, etiquetas.
- **Pedido de ejemplo**: *"Probá la factura PDF que genera el checkout"* · *"¿El reporte Excel tiene los totales bien?"* · *"Revisá que no queden {{variables}} en el PDF"*.
- **Entradas**: qué documentos genera y en qué formato, cómo se generan (UI/API), la fuente de la verdad de cada dato y cómo se calculan los totales, el locale, si deben ir con contraseña/firma, y un documento de referencia si hay.
- **Usa**: skills `pruebas-documentos` e `investigacion-contexto`; `npm run documentos` (`herramientas/documentos/documentos.py`, pypdf/openpyxl) y `scripts/generar_informe_generico.py`. Para obtener el documento, el `ejecutor-api` o el `ejecutor-e2e`/`web-mapper`.
- **Entrega**: en `output/documentos/<HU>/`, `informe-documentos.html` (datos esperado vs. obtenido, totales recalculados, placeholders, formato y layout, hallazgos) y `analisis.json`.
- **Confirma**: generar el documento si implica una acción con efecto (crear un pedido/factura). Con datos de prueba, nunca reales.
- **Tokens**: en cada uso.

### revisor-contenido
- **Cuándo**: para revisar los textos y el contenido en el idioma principal: typos, ortografía, placeholders sin reemplazar, claves de i18n a la vista, microcopy y consistencia (distinto de las traducciones, que cubre el `analista-traductor`).
- **Pedido de ejemplo**: *"Revisá los textos del sitio por typos"* · *"¿Quedan {{variables}} o claves de traducción a la vista?"* · *"Revisá el microcopy y la consistencia de términos"*.
- **Entradas**: la URL o páginas, el idioma principal, y si hay un glosario/guía de estilo del proyecto. Usuarios de prueba si hay login.
- **Usa**: skills `pruebas-contenido`, `ejecucion-e2e` e `investigacion-contexto`; `npm run contenido` (`herramientas/contenido/contenido.py`, heurística + LanguageTool opcional) y `scripts/generar_informe_generico.py`.
- **Entrega**: en `output/contenido/<HU>/`, `informe-contenido.html` (problemas por página y tipo —placeholders, i18n a la vista, duplicados, ortografía—, inconsistencias de microcopy, hallazgos) y `analisis.json`.
- **Confirma**: nada con efecto (solo lectura): recorre y lee el texto.
- **Tokens**: en cada uso.

### analista-mutacion
- **Cuándo**: para medir la **calidad real de la suite de tests** con mutation testing: qué tan buenos son los tests, mutation score, mutantes sobrevivientes. Mejor señal que el coverage de líneas.
- **Pedido de ejemplo**: *"Corré mutation testing del módulo de pagos"* · *"¿Qué tan buenos son nuestros tests?"* · *"¿Qué mutantes sobreviven y qué tests faltan?"*.
- **Entradas**: el lenguaje/stack de tests y la herramienta de mutación (Stryker JS/TS/C#, mutmut/cosmic-ray Python, PITest JVM, Infection PHP), que la suite esté verde, el alcance (diff/módulo/todo) y el umbral; los módulos críticos.
- **Usa**: skills `pruebas-mutacion` e `investigacion-contexto`; `npm run mutacion` (`herramientas/mutacion/mutacion.py`, lee el reporte estándar de Stryker) y `scripts/generar_informe_generico.py`. Complementa al `analista-cobertura`.
- **Entrega**: en `output/mutacion/<proyecto>/`, `informe-mutacion.html` (mutation score global y por archivo, mutantes sobrevivientes con archivo/línea/mutador, equivalentes descartados, tests que faltan) y `analisis.json`.
- **Confirma**: correr la mutación completa sobre todo el repo (es cara y lenta); por defecto se acota al diff o a un módulo crítico. Solo lectura del código.
- **Tokens**: en cada uso (corre la suite muchas veces; el triage de sobrevivientes consume).

### probador-streaming
- **Cuándo**: para probar que un stream o un video reproduzca bien — cámaras IP (RTSP/ONVIF), transmisiones en vivo (RTMP/HLS/DASH), WebRTC servido por HTTP y playback de VOD.
- **Pedido de ejemplo**: *"Probá la cámara rtsp://cam.local/stream"* · *"Revisá el playback de https://cdn.mi-app.com/live/index.m3u8"*.
- **Usa**: skills `verificacion-streaming` e `investigacion-contexto`; `npm run streaming` (ffprobe/ffmpeg, `herramientas/streaming/probar.py`) y `scripts/generar_informe_streaming.py`. Para el panel web de la cámara usá los agentes web (`ejecutor-e2e`, `probador-permisos`); para muchas conexiones a la vez, el `performance-mapper`.
- **Entrega**: en `output/streaming/<HU o host>/` (la corrida anterior pasa a `historial/`, últimas 5), `informe-streaming.html` (propiedades por fuente —códec, resolución, FPS, bitrate, audio—, continuidad —frames caídos, errores, latencia— y hallazgos por severidad), `streaming.json` y `analisis.json`.
- **Confirma**: la fuente (en `STREAMING_FUENTES_AUTORIZADAS`): solo dispositivos o streams propios o con autorización por escrito. Es de solo lectura (no graba ni retransmite) y no es prueba de carga.
- **Tokens**: en cada uso (la lectura del stream la hace ffmpeg, sin tokens).

### probador-onvif
- **Cuándo**: para probar el control de una cámara IP por ONVIF: que responda, sus perfiles y URIs de stream, el snapshot, el PTZ y la detección de movimiento.
- **Pedido de ejemplo**: *"Probá por ONVIF la cámara 192.168.1.50"* · *"Revisá el PTZ y el snapshot de la cámara de la entrada"*.
- **Usa**: skills `control-onvif` e `investigacion-contexto`; `npm run onvif` (onvif-zeep, `herramientas/streaming/onvif.py`) y `scripts/generar_informe_onvif.py`. Devuelve la URI RTSP para que el `probador-streaming` verifique el video.
- **Entrega**: en `output/streaming/onvif-<host o HU>/` (la corrida anterior pasa a `historial/`), `informe-onvif.html` (estado de cada prueba ONVIF, dispositivo, perfiles con su URI RTSP, snapshot y hallazgos), `onvif.json`, `snapshot.jpg` y `analisis.json`.
- **Confirma**: el host (en `ONVIF_HOSTS_AUTORIZADOS`) y, para el PTZ (que mueve la cámara), autorización explícita (`--ptz --confirmar`). Solo lectura salvo el PTZ; no cambia la configuración de la cámara.
- **Tokens**: en cada uso.

### calidad-imagen
- **Cuándo**: para revisar cómo se ve una cámara: imagen negra, borrosa, congelada, movida del encuadre, con contraluz o sin IR de noche.
- **Pedido de ejemplo**: *"¿Se ve bien la cámara rtsp://cam.local/stream?"* · *"Revisá si alguna cámara está borrosa o movida"*.
- **Usa**: skills `calidad-de-imagen` e `investigacion-contexto`; `npm run calidad-imagen` (ffmpeg + OpenCV, `herramientas/streaming/calidad_imagen.py`) y `scripts/generar_informe_calidad.py`. Lo objetivo lo mide OpenCV; lo de criterio lo juzga el agente mirando la captura (visión).
- **Entrega**: en `output/streaming/calidad-<host o HU>/` (la corrida anterior pasa a `historial/`), `informe-calidad.html` (captura, métricas y hallazgos por cámara), `calidad.json`, `capturas/` y `analisis.json`.
- **Confirma**: la fuente (en `STREAMING_FUENTES_AUTORIZADAS`). Solo lectura (toma una captura; no graba).
- **Tokens**: en cada uso (incluye la revisión con visión de las capturas).

### verificador-grabaciones
- **Cuándo**: para revisar si una cámara o NVR está grabando, si hay huecos y si se cumple la retención configurada.
- **Pedido de ejemplo**: *"¿El NVR 192.168.1.60 está grabando y cumple 30 días de retención?"*.
- **Usa**: skills `control-onvif` e `investigacion-contexto`; `npm run grabaciones` (onvif-zeep, servicios Recording/Search, `herramientas/streaming/grabaciones.py`) y `scripts/generar_informe_grabaciones.py`.
- **Entrega**: en `output/streaming/grabaciones-<host o HU>/` (la corrida anterior pasa a `historial/`), `informe-grabaciones.html` (rango cubierto, grabaciones, huecos y retención), `grabaciones.json` y `analisis.json`.
- **Confirma**: el host (en `ONVIF_HOSTS_AUTORIZADOS`) y la retención esperada. Solo lectura; no borra ni exporta. Si la cámara no soporta el servicio por ONVIF, lo informa.
- **Tokens**: en cada uso.

### analista-seguridad-camaras
- **Cuándo**: para revisar la seguridad de cámaras IP/NVR: puertos expuestos, servicios inseguros y CVEs del firmware. Pasivo, como el ZAP del analista-seguridad.
- **Pedido de ejemplo**: *"Revisá la seguridad de las cámaras 192.168.1.50 y .51"* · *"¿Alguna cámara tiene Telnet o RTSP sin auth?"*.
- **Usa**: skills `seguridad-camaras` e `investigacion-contexto`; `npm run seguridad-camaras` (escaneo pasivo de puertos y servicios, `herramientas/streaming/seguridad_camaras.py`) y `scripts/generar_informe_seguridad_camaras.py`.
- **Entrega**: en `output/streaming/seguridad-camaras-<host o HU>/` (la corrida anterior pasa a `historial/`), `informe-seguridad-camaras.html` (puertos, servicios inseguros, firmware y hallazgos por cámara), `seguridad-camaras.json` y `analisis.json`.
- **Confirma**: los hosts (en `CAMARAS_AUTORIZADAS`), propios o con autorización por escrito. Pasivo: no prueba credenciales, no ataca, no escanea rangos.
- **Tokens**: en cada uso.

### explorador-web
- **Cuándo**: para hacer pruebas exploratorias de un sitio: buscar links e imágenes rotas, errores de JavaScript y de consola, y revisar el responsive en varias resoluciones.
- **Pedido de ejemplo**: *"Hacé pruebas exploratorias del sitio del .env"* · *"Buscá links rotos y problemas de responsive en https://staging.tu-app.com"*.
- **Usa**: skill `ejecucion-e2e`; `npm run explorar` (recorrido automático con Playwright, `herramientas/k0lmena/tools/explorador/explorar.js`), conectores `playwright` o `playwright-headless` para la exploración manual y `scripts/generar_informe_exploratorio.py`.
- **Entrega**: en `output/exploratorias/<HU o host>/` (la corrida anterior pasa a `historial/`, últimas 5), `informe-exploratorio.html` (indicadores, gráficos, hallazgos por severidad con su captura, tiempos de carga, matriz de responsive, videos, galerías, links rotos, detalle por página y recomendaciones), `exploracion.json`, `analisis.json`, `capturas/` y `videos/`.
- **Confirma**: el modo (headed o headless) si no lo dijiste. No envía formularios ni cambia datos sin tu ok; en producción pide confirmación antes de explorar.
- **Tokens**: en cada uso (el recorrido de páginas lo hace el script, sin tokens por página).

### analista-accesibilidad
- **Cuándo**: para auditar la accesibilidad (WCAG 2.2, AA por defecto) en **web, mobile (Android/iOS) o desktop (Windows)**: contraste, textos/etiquetas accesibles, navegación con teclado, objetivos táctiles, lectores de pantalla.
- **Pedido de ejemplo**: *"Revisá la accesibilidad del sitio del .env"* · *"Auditá WCAG AA del registro de HU-001"* · *"Revisá la accesibilidad de la app mobile / de la app de escritorio"*.
- **Usa**: skills `accesibilidad` y `ejecucion-e2e`; en **web** `npm run accesibilidad` (axe-core, Tab, reflow a 320px) + Playwright; en **mobile** Appium (etiquetas, objetivos táctiles, TalkBack/VoiceOver); en **desktop** `npm run desktop` (árbol de controles, nombres accesibles). Informes: `scripts/generar_informe_accesibilidad.py` (web) o `scripts/generar_informe_generico.py` (mobile/desktop).
- **Entrega**: en `output/accesibilidad/<HU o host>/` (la corrida anterior pasa a `historial/`, últimas 5), `informe-accesibilidad.html` (cumplimiento, criterios WCAG incumplidos, cada problema con su captura y cómo corregirlo, teclado y orden del foco, revisión manual y recomendaciones), `auditoria.json`, `analisis.json`, `capturas/` y `videos/`.
- **Confirma**: el modo (headed o headless) si no lo dijiste. No envía formularios sin tu ok. Nunca afirma que el sitio "cumple": la parte automática detecta solo una parte de los problemas.
- **Tokens**: en cada uso (las reglas automáticas las corre el script, sin tokens por página).

### auditor-rendimiento-web
- **Cuándo**: para saber qué tan rápido carga cada página para una persona y por qué (no es una prueba de carga: eso es el performance-mapper).
- **Pedido de ejemplo**: *"Revisá la velocidad del sitio del .env"* · *"¿Por qué carga lenta la home en mobile?"*.
- **Usa**: `npm run rendimiento` (Lighthouse en mobile y desktop, con los textos en español, `herramientas/k0lmena/tools/rendimiento/auditar.js`) y `scripts/generar_informe_rendimiento.py`.
- **Entrega**: en `output/rendimiento/<HU o host>/` (la corrida anterior pasa a `historial/`, últimas 5), `informe-rendimiento.html` (puntajes, Core Web Vitals con sus umbrales, oportunidades con el ahorro estimado, peso por tipo de recurso, elemento LCP, terceros y secuencia de carga), `rendimiento.json`, `capturas/` y el reporte nativo de Lighthouse de cada página.
- **Confirma**: nada con efecto (solo carga las páginas). Necesita Node 22.19 o superior.
- **Tokens**: en cada uso (las mediciones las hace el script).

### pixel-perfect
- **Cuándo**: para detectar si algo se corrió o cambió visualmente (después de un deploy, de un cambio de estilos o contra el diseño).
- **Pedido de ejemplo**: *"Corré una regresión visual de qarmy.ar"* · *"¿Se corrió algo en el checkout después del deploy?"* · *"Compará la home contra el diseño de Figma"*.
- **Usa**: skill `ejecucion-e2e`; `npm run pixel-perfect` (captura estable de cada página en cada resolución, comparación píxel a píxel y elemento por elemento, `herramientas/k0lmena/tools/pixel-perfect/` y `tools/visual/`) y `scripts/generar_informe_pixel_perfect.py`. Con el conector `figma`, la referencia puede ser el diseño.
- **Entrega**: en `output/pixel-perfect/<HU o host>/`, `informe-pixel-perfect.html` (comparador deslizable referencia/actual, mapa de diferencias, matriz de pantallas, qué se corrió y cuántos píxeles, bloques desplazados con su causa, faltantes, nuevos, textos y estilos cambiados, con el antes y después de cada uno). La referencia (`referencia/`) se conserva entre corridas.
- **Confirma**: aceptar los cambios como nueva referencia (`--aceptar`).
- **Tokens**: en cada uso (la comparación la hace el script).

### cross-browser
- **Cuándo**: para saber si algo funciona o se ve distinto en Chrome/Edge, Firefox o Safari.
- **Pedido de ejemplo**: *"Probá HU-003 en Chrome, Firefox y Safari"* · *"¿Por qué el menú no anda en Safari?"* · *"Revisá qarmy.ar en todos los navegadores"*.
- **Usa**: `npm run cross-browser` (modo suite: la suite web de k0lmena en cada navegador; modo páginas: recorre y compara contra el navegador base, `herramientas/k0lmena/tools/cross-browser/`) y `scripts/generar_informe_cross_browser.py`.
- **Entrega**: en `output/cross-browser/<HU, host o suite>/`, `informe-cross-browser.html` (navegadores y versiones, matriz escenario o página × navegador con capturas, comparador contra el navegador base, hallazgos exclusivos de un navegador y recomendaciones).
- **Confirma**: el modo suite (corre contra el ambiente) e instalar navegadores que falten.
- **Tokens**: en cada uso.

### verificador-correos
- **Cuándo**: para verificar los mails que manda la aplicación: registro, confirmación, recuperar contraseña, pedidos, notificaciones.
- **Pedido de ejemplo**: *"Verificá que llegue el mail de bienvenida a ana@test.com"* · *"Revisá los correos de HU-004"*.
- **Usa**: skills `investigacion-contexto` (qué tiene que decir cada mail), `ejecucion-e2e` (disparar el envío) y `automatizacion-k0lmena` (steps de correo en los `.feature`); **Mailpit** como buzón de prueba (`herramientas/mailpit/`), `npm run correos` y `scripts/generar_informe_correos.py`.
- **Entrega**: en `output/correos/<HU o buzón>/`, `informe-correos.html` (lo que tenía que llegar y si cumple, variables sin reemplazar, links rotos o a localhost, imágenes, texto plano, compatibilidad con Outlook y Gmail, vista desktop y mobile de cada correo) y el `.eml` original.
- **Confirma**: disparar envíos (crea datos) y vaciar el buzón. Solo usa buzones de prueba.
- **Tokens**: en cada uso; los steps de correo en los `.feature`, una vez.

### analista-traductor
- **Cuándo**: para revisar la traducción de la web en todos sus idiomas.
- **Pedido de ejemplo**: *"Revisá las traducciones del sitio en inglés y portugués"* · *"¿Quedó algo sin traducir en la versión en inglés?"*.
- **Usa**: skills `investigacion-contexto` (glosario) y `ejecucion-e2e`; `npm run traductor` (recorre cada página en cada idioma y resolución, `herramientas/k0lmena/tools/traductor/`) y `scripts/generar_informe_traductor.py`.
- **Entrega**: en `output/traductor/<HU o host>/`, `informe-traductor.html` (porcentaje traducido por idioma, textos sin traducir con la traducción propuesta, claves a la vista, caracteres rotos, textos cortados, formatos de número y fecha, atributo lang, páginas lado a lado).
- **Tokens**: en cada uso.

### evaluador-ux
- **Cuándo**: para revisar la usabilidad de un sitio o de un flujo (qué confunde, frena o hace equivocar a la persona).
- **Pedido de ejemplo**: *"Evaluá la usabilidad del checkout"* · *"Revisá las heurísticas de Nielsen en qarmy.ar"*.
- **Usa**: skills `ejecucion-e2e` (recorre los flujos a mano) e `investigacion-contexto`; `npm run ux` (`herramientas/k0lmena/tools/ux/`) y `scripts/generar_informe_ux.py`.
- **Entrega**: en `output/ux/<HU o host>/`, `informe-ux.html` (puntaje por heurística, hallazgos automáticos y manuales con su captura, la página 404, desktop y mobile, recomendaciones).
- **Confirma**: avanzar en un flujo que crea datos.
- **Tokens**: en cada uso.

### probador-formularios
- **Cuándo**: para probar las validaciones de un formulario campo por campo (obligatorios, largos, formatos, límites, mensajes).
- **Pedido de ejemplo**: *"Probá las validaciones del formulario de registro"* · *"¿Qué acepta el campo email?"*.
- **Usa**: skills `ejecucion-e2e` e `investigacion-contexto` (las reglas de la historia); `npm run formularios` (`herramientas/k0lmena/tools/formularios/`) y `scripts/generar_informe_formularios.py`.
- **Entrega**: en `output/formularios/<HU o host>/`, `informe-formularios.html` (matriz campo × prueba con el valor, lo esperado, lo que hizo y el mensaje; capturas con los errores a la vista; valores inválidos aceptados y válidos rechazados).
- **Confirma**: enviar el formulario vacío (`--enviar-vacio`). Nunca envía otra cosa.
- **Tokens**: en cada uso (las pruebas las hace el script).

### probador-permisos
- **Cuándo**: para verificar que cada rol vea y pueda hacer solo lo que le corresponde (antes de una release, al sumar un rol o una pantalla protegida).
- **Pedido de ejemplo**: *"Probá los permisos de admin, operador e invitado en https://staging.mi-app.com"* · *"¿Un operador puede entrar al panel de administración escribiendo la URL?"*.
- **Entradas**: la URL (`APP_URL`), los roles y sus credenciales en el `.env` (`PERMISOS_ROLES`, `PERMISOS_<ROL>_USUARIO`/`_CLAVE`/`_TOKEN`), endpoints opcionales y la regla esperada (`input/documentacion/proyecto/estados-y-permisos.md`, el dossier o la historia).
- **Usa**: `npm run permisos` (inicia sesión con cada rol más el anónimo, recorre el sitio, abre cada ruta con cada rol por URL directa y pide los endpoints con la sesión y el token de cada rol; solo GET) y `scripts/generar_informe_permisos.py`; skills `investigacion-contexto` (la regla esperada) y `ejecucion-e2e` (revisión puntual con Playwright MCP).
- **Entrega**: en `output/permisos/<HU o host>/`, `informe-permisos.html` (matriz rol × ruta y rol × endpoint, diferencias con lo esperado, hallazgos con captura, qué menús y botones ve cada rol, Falta información y evolución de las corridas), `permisos.json` y `capturas/`. No guarda credenciales.
- **Tokens**: en cada uso (el recorrido y la matriz los hace el script).
- **Confirma**: cualquier clic en botones con efecto y correr contra producción.

### probador-resiliencia
- **Cuándo**: para saber cómo reacciona la interfaz cuando algo falla abajo: la API se cae o tarda, la red se corta o no cargan los recursos.
- **Pedido de ejemplo**: *"Probá qué pasa en el listado de productos si la API se cae"* · *"Pruebas de resiliencia de https://staging.mi-app.com con red lenta y sin conexión"*.
- **Entradas**: la URL o las páginas (`APP_URL` por defecto), los escenarios (todos por defecto) y, opcional, el patrón de la API y la historia.
- **Usa**: `npm run resiliencia` (Playwright intercepta la red desde el navegador: API con 500, 503 o 404, timeout, red lenta, sin conexión, respuestas vacías, JSON roto o campos en null, y estáticos que no cargan), la exploración manual con Playwright MCP (skill `ejecucion-e2e`), el skill `investigacion-contexto` para saber qué se espera ante cada falla y `scripts/generar_informe_resiliencia.py`. Para **caos server-side**, `npm run toxiproxy` (`herramientas/resiliencia/toxiproxy.py`): inyecta latencia, caída y lentitud en dependencias reales (base, API, cache) con Toxiproxy.
- **Entrega**: en `output/resiliencia/<HU o host>/`, `informe-resiliencia.html` (matriz página × escenario, pantallas en blanco, fallas silenciosas, spinners infinitos, mensajes técnicos, errores de JavaScript, reintentos y recuperación, con captura de cada escenario; más los escenarios de caos server-side), `resiliencia.json` y `capturas/`.
- **Confirma**: el **caos server-side** tiene efecto real → solo en QA, confirmado, con `reset` al terminar. El caos del navegador no envía formularios ni genera carga contra el servidor.
- **Tokens**: en cada uso (la simulación y la observación las hace el script).

## Reportes

### generador-reporte-html
- **Cuándo**: para regenerar el reporte de una corrida desde su JSON (los ejecutores ya lo generan solos).
- **Pedido de ejemplo**: *"Rearmá el reporte de output/ejecuciones/_resultados-HU-001-20261010-1030.json"*.
- **Usa**: `scripts/generar_reporte.py`.
- **Entrega**: `output/ejecuciones/reporte-HU-XXX-<fecha-hora>.html`.
- **Tokens**: en cada uso (poco: el script hace el trabajo).

### generador-reporte-cierre
- **Cuándo**: al terminar una ronda o historia, para decidir si sale.
- **Pedido de ejemplo**: *"Armá el informe de cierre de HU-001"*.
- **Usa**: `scripts/recolectar_resultados.py` (junta ejecuciones en vivo, `npm test`, bugs, performance y seguridad) y `scripts/generar_informe_cierre.py`.
- **Entrega**: `output/informes-cierre/cierre-HU-XXX-<fecha>.html` con la recomendación (Apto / Apto con observaciones / No apto), resultados, bugs por severidad, alcance, riesgos y falta información.
- **Confirma**: nada (solo lee); la recomendación sigue una regla fija (bug Crítico abierto o caso Crítico fallido = No apto).
- **Tokens**: en cada uso.

### analista-cobertura
- **Cuándo**: para saber qué falta probar de una historia o de la ronda.
- **Pedido de ejemplo**: *"¿Qué nos falta probar de HU-001?"* · *"Armá la matriz de trazabilidad de la ronda"*.
- **Usa**: skill `investigacion-contexto` (los criterios de Jira o Azure DevOps si no están en archivos); `scripts/analizar_cobertura.py` y `scripts/generar_informe_cobertura.py`.
- **Entrega**: en `output/cobertura/<HU o todas>/`, `informe-cobertura.html` (embudo de la historia al resultado, cobertura por criterio, matriz de trazabilidad caso por caso y huecos priorizados) y `cobertura.json`.
- **Confirma**: nada (solo lee).
- **Tokens**: en cada uso (el cruce lo hace el script).

### tablero-calidad
- **Cuándo**: para saber cómo viene un sprint o una release, o para un resumen para gerencia.
- **Pedido de ejemplo**: *"Armá el tablero de calidad del sprint 12 (del 1 al 14 de octubre)"*.
- **Usa**: `scripts/tablero_calidad.py` (lee ejecuciones, `npm test` y su historial, el inventario de casos, cobertura, bugs, fallos, accesibilidad, rendimiento, performance y seguridad); opcional `scripts/avisar.py` para publicar el resumen en Slack o Teams.
- **Entrega**: `output/tablero/<nombre>/` con `informe-tablero.html` y `tablero.json`: aprobados y tendencia, % automatizado, cobertura, bugs por severidad e historia, inestables, minutos de ejecución manual, alertas, resumen ejecutivo, riesgos y recomendaciones. Lo que no tiene datos dice "Sin datos". Historial de 5 corridas.
- **Tokens**: en cada uso (el cruce lo hace el script).

## Automatización con k0lmena

Escriben la automatización **una vez**; después corre sin agentes ni tokens con `npm test` o `npm run perf`.

### web-mapper
- **Cuándo**: para automatizar casos web.
- **Pedido de ejemplo**: *"Automatizá en k0lmena los casos de HU-001 contra https://tu-app.com"*.
- **Usa**: skills `automatizacion-k0lmena`, `ejecucion-e2e` e `investigacion-contexto`; conectores `playwright` / `playwright-headless`; k0lmena web (Playwright + Cucumber).
- **Entrega**: `herramientas/k0lmena/web/features/HU-XXX-<tema>.feature`, `steps/HU-XXX.steps.ts`, `locators/HU-XXX.locators.ts` y `output/mapeos/mapeo-HU-XXX-web.md`. Se corre con `npm run test:web`.
- **Confirma**: headed o headless, si no lo dijiste.
- **Tokens**: una vez.

### api-mapper
- **Cuándo**: para automatizar pruebas de API desde una colección de Postman o un Swagger/OpenAPI.
- **Pedido de ejemplo**: *"Automatizá los endpoints de /pet de https://petstore.swagger.io/v2/swagger.json"*.
- **Usa**: skills `automatizacion-k0lmena`, `investigacion-contexto` y `tecnicas-de-diseno`; k0lmena api (axios + Cucumber, steps genéricos).
- **Entrega**: `herramientas/k0lmena/api/features/*.feature` y `output/mapeos/mapeo-<HU o contrato>-api.md`. Se corre con `npm run test:api`.
- **Confirma**: el alcance y los métodos con efecto (POST, PUT, PATCH, DELETE) antes de llamarlos.
- **Tokens**: una vez.

### mobile-mapper
- **Cuándo**: para automatizar casos de una app Android o iOS.
- **Pedido de ejemplo**: *"Automatizá los casos de HU-005 en el emulador de Android"*.
- **Usa**: skills `automatizacion-k0lmena` e `investigacion-contexto`; conector `appium-mcp` (se activa con `npm run conector -- activar appium-mcp`); k0lmena mobile (WebdriverIO + Appium).
- **Entrega**: `herramientas/k0lmena/mobile/features`, `steps` y `locators` de la historia, y `output/mapeos/mapeo-HU-XXX-mobile.md`. Se corre con `npm run test:mobile`.
- **Tokens**: una vez.

### performance-mapper
- **Cuándo**: para pruebas de carga, estrés, resistencia o picos.
- **Pedido de ejemplo**: *"Quiero hacer una prueba de carga del login"*. Antes, Claude te guía paso a paso con el skill `guia-performance` (tipo de prueba, herramienta, usuarios, rampa, duración, umbrales).
- **Usa**: skills `guia-performance` y `automatizacion-k0lmena`; k6, Artillery + Playwright o JMeter; `scripts/generar_informe_performance.py`.
- **Entrega**: el script en `herramientas/k0lmena/performance/`, el plan y el informe (métricas, gráficos, hallazgos, recomendaciones) en `output/performance/HU-XXX/`. Se vuelve a correr con `npm run perf -- <script> <perfil>`.
- **Confirma**: cada corrida con carga.
- **Tokens**: una vez (más el análisis del informe).

### verificador-datos
- **Cuándo**: para revisar qué dejaron guardado las pruebas o verificar un dato en una base.
- **Pedido de ejemplo**: *"Verificá en la base si existe el usuario ana@test.com"* · *"Sumá al escenario de registro la verificación en la base"*.
- **Usa**: skill `automatizacion-k0lmena` (steps de base de datos); `npm run bd` (PostgreSQL, MySQL/MariaDB, SQL Server, MongoDB).
- **Entrega**: la respuesta en el chat (y `output/verificaciones-datos/` si lo pedís); los steps de BD en el `.feature` solo si los pedís.
- **Confirma**: toda escritura (y nunca escribe en producción).
- **Tokens**: en cada consulta; las verificaciones en los `.feature`, una vez.

### analista-fallos
- **Cuándo**: cuando `npm test` falla, para separar los bugs reales de los tests rotos, inestables, de datos o de ambiente.
- **Pedido de ejemplo**: *"Analizá por qué falló npm test"* · *"¿Cuáles de estas fallas son bugs?"*.
- **Usa**: `scripts/analizar_fallos.py` (clasifica, rescata captura, video y trace, compara con reintentos) y `scripts/generar_informe_fallos.py`; skill `ejecucion-e2e` para reproducir a mano si hace falta.
- **Entrega**: en `output/fallos/<HU o suite>/`, `informe-fallos.html` (fallas por causa, historial de corridas, error, evidencia y qué hacer) y los bugs reales en `output/reportes-bug/`.
- **Confirma**: volver a correr los fallidos (corre contra el ambiente) y cargar bugs en Jira o Azure DevOps.
- **Tokens**: en cada uso.

### reparador-automatizacion
- **Cuándo**: cuando tests automatizados fallan porque la pantalla cambió (locators que ya no encuentran el elemento o encuentran varios) o por esperas.
- **Pedido de ejemplo**: *"Repará los tests que fallaron por locators"* · *"Arreglá la automatización de HU-001 después del rediseño"*.
- **Usa**: skills `automatizacion-k0lmena` (convenciones de locators) y `ejecucion-e2e`; `npm run reparar` (lee el error y el DOM que k0lmena guarda al fallar, diagnostica, propone un locator único y robusto, lo aplica con respaldo y diff y verifica, `herramientas/k0lmena/tools/reparador/`) y `scripts/generar_informe_reparacion.py`. Puede partir del análisis del `analista-fallos`.
- **Entrega**: los locators corregidos en `herramientas/k0lmena/web/` y, en `output/reparaciones/<HU o suite>/`, `informe-reparacion.html` (diagnóstico, cambio como diff, candidatos, capturas del elemento original y del propuesto, verificación), `cambios.diff` y `respaldo/`.
- **Confirma**: aplicar las reparaciones que no son seguras (confianza media o baja, pasos de verificación, datos del `.feature`) y volver a correr los escenarios. Nunca cambia un test para tapar un bug.
- **Tokens**: en cada uso (el diagnóstico lo hace el script).

### analista-logs
- **Cuándo**: para entender qué pasó en el servidor: errores, picos y el error que hay detrás de una prueba que falló.
- **Pedido de ejemplo**: *"Analizá los logs de la corrida de hoy"* · *"¿Por qué falló CP-004 del lado del servidor?"*.
- **Usa**: `scripts/analizar_logs.py` (logs de la app, nginx, Apache, JSON y syslog; cruza con los escenarios de `npm test`, que guardan su inicio y fin) y `scripts/generar_informe_logs.py`.
- **Entrega**: en `output/logs/<nombre>/`, `informe-logs.html` (errores y advertencias por minuto, firmas con su stack trace, cada escenario fallido con los errores del servidor mientras corría).
- **Confirma**: bajar logs de un servidor compartido.
- **Tokens**: en cada uso (el agrupado y el cruce los hace el script).

## Gestión de pruebas

### gestor-pruebas
- **Cuándo**: para llevar los casos a la herramienta del equipo y armar los ciclos.
- **Pedido de ejemplo**: *"Subí los casos de HU-001 a Xray en la carpeta 'HU-001 Registro', vinculados a PROJ-12"*.
- **Usa**: `scripts/gestion/gestion.py` (Xray Cloud, Xray Server/DC, QTM4J, AIO Tests y Zephyr Scale); para Azure Test Plans, el conector `azure-devops` y `scripts/gestion/para_azure_devops.py`.
- **Entrega**: carpetas, casos, vínculos con la historia y ciclos en la herramienta, y la trazabilidad `output/gestion/HU-XXX-<herramienta>.json`.
- **Confirma**: carpeta, historia y ciclo; la primera vez, una prueba en seco (`--dry-run`).
- **Tokens**: en cada uso (poco: el script hace el trabajo).

### publicador-resultados
- **Cuándo**: después de correr `npm test`, para cargar los resultados en el ciclo.
- **Pedido de ejemplo**: *"Subí los resultados de la última corrida web al ciclo PROJ-60"*.
- **Usa**: `scripts/gestion/gestion.py` (`extraer-resultados` y `publicar-resultados`).
- **Entrega**: el estado de cada caso en el ciclo, con el error y las evidencias (captura, GIF y video si falló). Publica una historia por vez para no mezclar casos. Azure DevOps todavía no.
- **Confirma**: el ciclo, si lo propuso él.
- **Tokens**: en cada uso (poco: el script hace el trabajo).

---

## Skills: el "cómo" que usan los agentes

Los skills se cargan solo cuando hacen falta.

| Skill                  | Qué enseña                                                                                                                                                         | Lo usan                                                                                                                                                                                                                                                                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| investigacion-contexto | Investigar la historia completa (documentación del proyecto, comentarios, subtareas, épica, Confluence, Figma, contratos) y registrar la Falta información (FI-XX) | analista-historias, estratega-pruebas, generadores de casos y datos, web-mapper, api-mapper, mobile-mapper, analista-cobertura, selector-casos-de-prueba, verificador-correos, analista-traductor, revisor-casos, generador-charters, evaluador-ux, probador-formularios, documentador-proyecto, probador-permisos, probador-resiliencia, pentester-web, consultor-proyecto, probador-shopify, probador-wordpress |
| tecnicas-de-diseno     | Equivalencia, valores límite, tabla de decisión, transición de estados y pairwise                                                                                  | generador-casos-manuales, generador-casos-bdd, generador-casos-api, generador-datos-prueba, api-mapper, revisor-casos, generador-charters                                                                                                                                                                                                                    |
| ejecucion-e2e          | Ejecutar en el navegador con Playwright MCP: modos, snapshots, esperas y evidencia                                                                                 | ejecutor-e2e, web-mapper, explorador-web, analista-accesibilidad, analista-fallos, pixel-perfect, reparador-automatizacion, verificador-correos, analista-traductor, generador-charters, evaluador-ux, probador-formularios, documentador-proyecto, probador-permisos, probador-resiliencia, pentester-web, probador-shopify, probador-wordpress                            |
| pruebas-accesibilidad | Accesibilidad (a11y) en web (WCAG 2.2, axe-core, teclado, contraste, ARIA), mobile (TalkBack/VoiceOver, etiquetas, objetivos táctiles) y desktop (UI Automation, nombres accesibles, teclado) | analista-accesibilidad, probador-mobile, probador-desktop |
| ejecucion-api          | Correr colecciones con Newman: base_url, token, validaciones y resultados                                                                                          | ejecutor-api                                                                                                                                                                                                                                                                                                                                                 |
| automatizacion-k0lmena | Convenciones de k0lmena: features, steps, locators, tags, steps de BD y scripts de performance                                                                     | web-mapper, api-mapper, mobile-mapper, performance-mapper, verificador-datos, reparador-automatizacion, verificador-correos                                                                                                                                                                                                                                  |
| guia-performance       | Guía paso a paso para planificar una prueba de performance con la persona                                                                                          | la conversación principal (antes de performance-mapper) y performance-mapper                                                                                                                                                                                                                                                                                 |
| guia-pruebas           | Asistente interactivo para elegir qué probar y con qué agente/skill: pregunta paso a paso y recomienda o ejecuta; mapa de plataforma y tipo de prueba hacia el agente/skill | la conversación principal |
| base-conocimiento      | Flujo para armar y mantener la base de conocimiento de todo el proyecto en input/documentacion/ (investigar todo, explorar la app con sesión, documentar, casos y automatización) y la rutina ágil cuando cambian los requerimientos | la conversación principal |
| verificacion-streaming | Probar streaming y playback con ffprobe/ffmpeg: protocolos, propiedades y continuidad                                                                              | probador-streaming                                                                                                                                                                                                                                                                                                                                           |
| control-onvif          | Control ONVIF de cámaras con onvif-zeep: servicios, perfiles, snapshot, PTZ seguro y eventos                                                                       | probador-onvif, verificador-grabaciones                                                                                                                                                                                                                                                                                                                      |
| calidad-de-imagen      | Evaluar calidad de imagen de cámaras: OpenCV (negro, desenfoque, congelamiento) + criterio con visión                                                              | calidad-imagen                                                                                                                                                                                                                                                                                                                                               |
| seguridad-camaras      | Análisis pasivo de seguridad de cámaras IP: puertos, servicios inseguros y firmware/CVEs                                                                           | analista-seguridad-camaras                                                                                                                                                                                                                                                                                                                                   |
| relevamiento-proyecto  | Relevar un proyecto entero por MCP: barrer cada herramienta con consultas acotadas, muestrear backlogs, clasificar ambigüedades y armar preguntas                   | investigador-proyecto                                                                                                                                                                                                                                                                                                                                        |
| redaccion-manual       | Manual de usuario basado en evidencia: fuentes de k0lmenIA + app con Playwright MCP, matriz de evidencia, gaps, acciones prohibidas, capturas, QA REVIEW, aprobación y checklist, modo plataforma, conocimiento a input/documentacion/ | redactor-manual |
| pruebas-salesforce     | Probar una org de Salesforce: ambientes, acceso (perfiles, permission sets, OWD, FLS), validaciones, flows, triggers, Apex, datos, Lightning y releases             | probador-salesforce                                                                                                                                                                                                                                                                                                                                          |
| pruebas-tokens         | Probar tokens (JWT, OAuth, sesión, API keys) y la tokenización de tarjetas (PCI): ciclo de vida, firma, claims, ataques típicos y manejo seguro                     | probador-billeteras, probador-salesforce, pentester-web                                                                                                                                                                                                                                                                                                      |
| pruebas-billeteras     | Probar billeteras y pagos: saldo y ledger, transacciones, idempotencia, doble gasto, límites, KYC/AML y conciliación                                                | probador-billeteras                                                                                                                                                                                                                                                                                                                                          |
| pruebas-ecommerce      | Probar cualquier tienda online: catálogo, precios, stock, carrito, checkout, impuestos, envíos, cupones, pagos de prueba y correos                                  | probador-shopify, probador-wordpress                                                                                                                                                                                                                                                                                                                         |
| pruebas-shopify        | Probar Shopify: tienda de desarrollo, temas y Theme Check, Liquid, apps, checkout y Bogus Gateway, Markets, envíos, descuentos, webhooks                            | probador-shopify                                                                                                                                                                                                                                                                                                                                             |
| pruebas-wordpress      | Probar WordPress y WooCommerce: plugins, templates sobrescritos, cron, checkout clásico o de bloques, pasarelas, envíos, cupones, roles                             | probador-wordpress                                                                                                                                                                                                                                                                                                                                           |
| pruebas-prestashop     | Probar PrestaShop (1.6/1.7/8.x): smoke local con Docker, temas y Smarty, módulos y overrides, caché y rendimiento, checkout, pagos, combinaciones y stock, Webservice API | probador-prestashop                                                                                                                                                                                                                                                                                                                                      |
| pruebas-vtex           | Probar VTEX: cuentas y workspaces, storefront y VTEX IO, catálogo y trade policies, pricing, logistics/SLAs, promociones, pagos, orderForm, OMS, marketplace, smoke, regresión, rendimiento y seguridad | probador-vtex                                                                                                                                                                                                                                                                                                              |
| pruebas-sap            | Probar SAP: SAP GUI (T-codes, Scripting API) y Fiori/UI5 (OData), mandantes y transportes, autorizaciones y roles (PFCG/SU53/SoD), procesos O2C/P2P/R2R, jobs e IDocs, smoke, regresión, rendimiento y seguridad | probador-sap                                                                                                                                                                                                                                                                                       |
| pruebas-desktop        | Probar apps de escritorio Windows (WinForms/WPF/UWP/Win32/Electron/Java/Qt): árbol de controles, funcional, instalación, archivos, SO, smoke, regresión, rendimiento, seguridad y accesibilidad | probador-desktop                                                                                                                                                                                                                                                                                       |
| pruebas-mobile         | Probar apps móviles (Android/iOS; nativa/híbrida/web): dispositivos, permisos, interrupciones, conectividad, deep links y push, ciclo de vida, rendimiento, seguridad (MASVS) y accesibilidad; automatizar con Appium | probador-mobile, mobile-mapper |
| analisis-dependencias  | Analizar la seguridad de las dependencias (SCA): CVE/CVSS, directas vs. transitivas, reachability, licencias, SBOM, cadena de suministro y riesgo aceptado | analista-dependencias |
| codigo-seguro          | SAST y secretos: clases de bug (inyección, XSS, cripto…), OWASP/CWE, semgrep, triage de falsos positivos, detección y rotación de secretos, SAST vs. DAST | analista-codigo-seguro, revisor-codigo |
| revision-codigo        | Code review estático: traer el código (GitHub/GitLab/Bitbucket/Azure/git) sin ejecutarlo, PR/MR contra el merge-base, qué mirar por categoría y lenguaje, umbrales, severidad y decisión, triage de falsos positivos, comentarios útiles | revisor-codigo |
| pruebas-ia             | Probar funciones de IA/LLM: golden set y evals, alucinaciones y grounding, seguridad de prompt (injection/jailbreak), formato, robustez, latencia/costo, privacidad y regresión de prompts | probador-ia |
| pruebas-async          | Probar mensajería/eventos (async): brokers (Kafka/RabbitMQ/SQS/MQTT/WebSocket/SSE), entrega, orden, idempotencia, DLQ, esquemas, consumer lag y outbox | probador-mensajeria |
| pruebas-graphql        | Probar APIs GraphQL: schema/introspección, queries/mutations/subscriptions, errores parciales y nulabilidad, autorización por campo, N+1, profundidad/complejidad y paginación | ejecutor-api, api-mapper, generador-casos-api |
| pruebas-soap           | Probar servicios SOAP: WSDL, sobre, SOAP 1.1/1.2, validación XSD, SOAP Faults, WS-Security, mustUnderstand, tipos y contrato | probador-soap |
| pruebas-scalar         | Probar APIs en Scalar: MCP (Search/Execute, créditos), Registry, casos como colección con tests pm, x-post-response y publicación con confirmación | probador-scalar |
| pruebas-contratos | Contract testing (Pact): consumer-driven y por proveedor, broker/can-i-deploy, compatibilidad, REST/GraphQL/gRPC/eventos | probador-contratos |
| pruebas-seo | SEO y GEO: indexabilidad, on-page, datos estructurados, hreflang, Core Web Vitals y optimización para motores con IA | analista-seo |
| pruebas-datos | Datos y pipelines (ETL): calidad, reconciliación, esquema/drift, transformaciones, SCD, idempotencia, PII | probador-datos |
| pruebas-grpc | gRPC (Protobuf, modos de RPC, status codes, deadlines, compatibilidad) y WebSocket en la familia de API | ejecutor-api, api-mapper, generador-casos-api |
| pruebas-dynamics | Dynamics 365 y otros CRM/ERP: entornos, roles, modelo de datos, lógica, procesos end-to-end, Web API | probador-dynamics |
| pruebas-blockchain | Blockchain/Web3 y smart contracts: funcional, tokens, gas, seguridad (reentrancy, acceso, oráculos), proxies | probador-blockchain |
| pruebas-ivr | Voz/IVR y voicebots: árbol de menús, DTMF/ASR, prompts, colas y transferencias, telefonía, PCI | probador-ivr |
| pruebas-juegos | Videojuegos: mecánicas, guardado, compatibilidad, rendimiento, multijugador, monetización, exploratorias | probador-juegos |
| pruebas-pos | POS y hardware: flujo de venta, pagos y periféricos, fiscal, offline y conciliación, cierres de caja | probador-pos |
| pruebas-observabilidad | Probar observabilidad: logs estructurados (trace id, sin PII), métricas Prometheus (RED/USE, cardinalidad), trazas OTel, healthchecks (liveness/readiness), SLOs y alertas | analista-observabilidad |
| pruebas-busqueda | Probar búsqueda y relevancia: ranking y boosting, typos/fuzzy, sinónimos y stemming, facetas, cero-resultados, indexación y golden set (precision@k, nDCG) | probador-busqueda |
| pruebas-documentos | Probar documentos generados (PDF/Excel/CSV): datos y cálculos, placeholders sin reemplazar, formato/locale, layout, metadata, seguridad y a11y del PDF | probador-documentos |
| pruebas-contenido | Revisar contenido y typos (idioma principal): ortografía/gramática, placeholders, claves i18n a la vista, palabras duplicadas, microcopy y consistencia | revisor-contenido |
| pruebas-mutacion       | Mutation testing: mutantes y mutadores, estados (killed/survived/no-coverage), mutation score, sobrevivientes vs. equivalentes, costo acotado (diff/módulo), herramientas por lenguaje | analista-mutacion |

## Herramientas y scripts: quién usa qué

| Herramienta o script                                                             | Para qué                                                                                                  | La usan                                                                                                                                                                                                                                                                                                    |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| k0lmena (herramientas/k0lmena)                                                   | Automatización web, API, mobile y performance; corre sin tokens                                           | web-mapper, api-mapper, mobile-mapper, performance-mapper, verificador-datos                                                                                                                                                                                                                               |
| Playwright MCP                                                                   | Navegador en vivo                                                                                         | ejecutor-e2e, web-mapper, explorador-web, analista-accesibilidad, analista-fallos, pixel-perfect, reparador-automatizacion, verificador-correos, analista-traductor, generador-charters, evaluador-ux, probador-formularios, documentador-proyecto, probador-permisos, probador-resiliencia, pentester-web                |
| Newman (herramientas/newman)                                                     | Colecciones de Postman                                                                                    | ejecutor-api                                                                                                                                                                                                                                                                                               |
| OWASP ZAP (herramientas/zap)                                                     | Seguridad web pasiva y activa (pentest)                                                                   | analista-seguridad, pentester-web                                                                                                                                                                                                                                                                                         |
| k6 · Artillery · JMeter                                                          | Performance                                                                                               | performance-mapper                                                                                                                                                                                                                                                                                         |
| scripts/generar_casos.py                                                         | Planilla y Markdown de casos                                                                              | generador-casos-manuales                                                                                                                                                                                                                                                                                   |
| scripts/formatear_tablas.py                                                      | Tablas alineadas en los .md                                                                               | casi todos los que escriben .md                                                                                                                                                                                                                                                                            |
| scripts/generar_plan.py                                                          | Plan de pruebas HTML                                                                                      | estratega-pruebas                                                                                                                                                                                                                                                                                          |
| scripts/generar_reporte.py                                                       | Reporte HTML de una corrida                                                                               | ejecutor-e2e, ejecutor-api, generador-reporte-html                                                                                                                                                                                                                                                         |
| scripts/correr_newman.py                                                         | Newman con el .env y su reporte                                                                           | ejecutor-api                                                                                                                                                                                                                                                                                               |
| scripts/recolectar_resultados.py · generar_informe_cierre.py                     | Informe de cierre                                                                                         | generador-reporte-cierre                                                                                                                                                                                                                                                                                   |
| scripts/generar_informe_performance.py                                           | Informe de performance                                                                                    | performance-mapper                                                                                                                                                                                                                                                                                         |
| scripts/generar_informe_seguridad.py                                             | Informe de seguridad                                                                                      | analista-seguridad, pentester-web                                                                                                                                                                                                                                                                                         |
| npm run explorar (k0lmena tools/explorador)                                      | Recorrido: links, imágenes, errores y responsive                                                          | explorador-web                                                                                                                                                                                                                                                                                             |
| scripts/generar_informe_exploratorio.py                                          | Informe de pruebas exploratorias                                                                          | explorador-web                                                                                                                                                                                                                                                                                             |
| npm run accesibilidad (k0lmena tools/accesibilidad)                              | Auditoría de accesibilidad: axe-core, teclado y reflow                                                    | analista-accesibilidad                                                                                                                                                                                                                                                                                     |
| scripts/generar_informe_accesibilidad.py                                         | Informe de accesibilidad                                                                                  | analista-accesibilidad                                                                                                                                                                                                                                                                                     |
| npm run rendimiento (k0lmena tools/rendimiento)                                  | Lighthouse: velocidad de carga y Core Web Vitals                                                          | auditor-rendimiento-web                                                                                                                                                                                                                                                                                    |
| scripts/generar_informe_rendimiento.py                                           | Informe de rendimiento web                                                                                | auditor-rendimiento-web                                                                                                                                                                                                                                                                                    |
| scripts/analizar_fallos.py · generar_informe_fallos.py                           | Clasifica las fallas de npm test e informe                                                                | analista-fallos                                                                                                                                                                                                                                                                                            |
| scripts/analizar_cobertura.py · generar_informe_cobertura.py                     | Matriz de cobertura y trazabilidad e informe                                                              | analista-cobertura                                                                                                                                                                                                                                                                                         |
| npm run pixel-perfect (k0lmena tools/pixel-perfect y tools/visual)               | Regresión visual: captura estable y comparación píxel a píxel y por elemento                              | pixel-perfect                                                                                                                                                                                                                                                                                              |
| scripts/generar_informe_pixel_perfect.py                                         | Informe de regresión visual                                                                               | pixel-perfect                                                                                                                                                                                                                                                                                              |
| npm run cross-browser (k0lmena tools/cross-browser)                              | Suite o páginas en Chromium, Firefox y WebKit                                                             | cross-browser                                                                                                                                                                                                                                                                                              |
| scripts/generar_informe_cross_browser.py                                         | Informe cross-browser                                                                                     | cross-browser                                                                                                                                                                                                                                                                                              |
| npm run reparar (k0lmena tools/reparador)                                        | Diagnostica, propone, aplica y verifica locators                                                          | reparador-automatizacion                                                                                                                                                                                                                                                                                   |
| scripts/generar_informe_reparacion.py                                            | Informe de reparación de la automatización                                                                | reparador-automatizacion                                                                                                                                                                                                                                                                                   |
| scripts/seleccionar_casos.py · generar_informe_seleccion.py                      | Selección de casos por cambio e informe                                                                   | selector-casos-de-prueba                                                                                                                                                                                                                                                                                   |
| Mailpit (herramientas/mailpit) · npm run correos                                 | Buzón de prueba y revisión de los correos                                                                 | verificador-correos                                                                                                                                                                                                                                                                                        |
| scripts/generar_informe_correos.py                                               | Informe de correos                                                                                        | verificador-correos                                                                                                                                                                                                                                                                                        |
| npm run traductor (k0lmena tools/traductor)                                      | Cada página en cada idioma: traducción, cortes y formatos                                                 | analista-traductor                                                                                                                                                                                                                                                                                         |
| scripts/generar_informe_traductor.py                                             | Informe de traducciones                                                                                   | analista-traductor                                                                                                                                                                                                                                                                                         |
| scripts/_historial.py · k0lmena tools/historial                                  | Últimas 5 corridas de cada herramienta y su comparación                                                   | todos los que generan informes                                                                                                                                                                                                                                                                             |
| scripts/estimacion.py                                                            | Tiempo estimado de ejecución manual de cada caso (planilla, herramienta de gestión, selección y revisión) | generador-casos-manuales, generador-casos-bdd, gestor-pruebas, revisor-casos, selector-casos-de-prueba                                                                                                                                                                                                     |
| scripts/revisar_casos.py · generar_informe_revision.py                           | Calidad de los casos e informe                                                                            | revisor-casos                                                                                                                                                                                                                                                                                              |
| scripts/generar_charters.py                                                      | Hojas de sesión e informe de sesiones exploratorias                                                       | generador-charters                                                                                                                                                                                                                                                                                         |
| npm run ux (k0lmena tools/ux) · generar_informe_ux.py                            | Heurísticas de Nielsen e informe                                                                          | evaluador-ux                                                                                                                                                                                                                                                                                               |
| npm run formularios (k0lmena tools/formularios) · generar_informe_formularios.py | Validaciones de formularios e informe                                                                     | probador-formularios                                                                                                                                                                                                                                                                                       |
| scripts/analizar_logs.py · generar_informe_logs.py                               | Logs agrupados, cruzados con la corrida, e informe                                                        | analista-logs                                                                                                                                                                                                                                                                                              |
| npm run mapa-funcional (k0lmena tools/mapa-funcional) · indice_documentacion.py  | Mapa funcional de la web e índice de input/documentacion/                                                 | documentador-proyecto                                                                                                                                                                                                                                                                                      |
| npm run permisos (k0lmena tools/permisos) · generar_informe_permisos.py          | Matriz de permisos por rol e informe                                                                      | probador-permisos                                                                                                                                                                                                                                                                                          |
| npm run resiliencia (k0lmena tools/resiliencia) · generar_informe_resiliencia.py | Fallas simuladas de API, red y recursos, e informe                                                        | probador-resiliencia                                                                                                                                                                                                                                                                                       |
| scripts/buscar_duplicados.py                                                     | Similitud entre bugs: duplicados, regresiones y relacionados                                              | triador-bugs                                                                                                                                                                                                                                                                                               |
| scripts/tablero_calidad.py                                                       | Tablero de calidad por sprint o release                                                                   | tablero-calidad                                                                                                                                                                                                                                                                                            |
| scripts/portal_informes.py (npm run portal)                                      | Portal con el último informe de cada herramienta (output/index.html, se actualiza solo)                   | todos los que generan informes                                                                                                                                                                                                                                                                             |
| scripts/avisar.py (npm run avisar)                                               | Avisos a Slack y Teams por webhook                                                                        | triador-bugs, tablero-calidad, monitoreo sintético, vos                                                                                                                                                                                                                                                    |
| npm run monitorear (k0lmena tools/monitoreo) · generar_informe_monitoreo.py      | Monitoreo sintético de solo lectura, con aviso cuando algo se rompe o se recupera                         | vos, el Programador de tareas, cron o GitHub Actions                                                                                                                                                                                                                                                       |
| scripts/cambios_documentacion.py                                                 | Documentación incremental: qué documentos y casos afecta un cambio del código                             | documentador-proyecto                                                                                                                                                                                                                                                                                      |
| scripts/convertir_coleccion.py · resumir_graphql.py · resumir_openapi.py         | Bruno e Insomnia a Postman; resumen de GraphQL y OpenAPI                                                  | ejecutor-api, api-mapper, generador-casos-api                                                                                                                                                                                                                                                              |
| scripts/evaluar_agentes.py (npm run evals)                                       | Evals de los agentes: casos con trampas, chequeos e informe con regresiones                               | vos, al cambiar un agente o un skill                                                                                                                                                                                                                                                                       |
| scripts/gestion/                                                                 | Xray, QTM4J, AIO Tests y Zephyr Scale; conversión para Azure Test Plans                                   | gestor-pruebas, publicador-resultados                                                                                                                                                                                                                                                                      |
| scripts/metricas_tokens.py (npm run metricas)                                    | Uso de tokens y costo estimado por agente, día y modelo, con oportunidades de ahorro                      | vos, tablero-calidad                                                                                                                                                                                                                                                                                       |
| scripts/generar_onboarding.py                                                    | Plan de onboarding en HTML y Markdown                                                                     | guia-onboarding                                                                                                                                                                                                                                                                                            |
| scripts/doctor.py (npm run doctor)                                               | Revisa el entorno y la configuración                                                                      | vos, al instalar o cuando algo no anda                                                                                                                                                                                                                                                                     |
| herramientas/salesforce/inventario.py (npm run salesforce)                       | Inventario de QA de una org de Salesforce (sandbox): acceso, validaciones, flows, Apex, sharing, límites | probador-salesforce                                                                                                                                                                                                                                                                                        |
| scripts/generar_informe_salesforce.py                                            | Informe HTML de Salesforce (inventario y pruebas)                                                          | probador-salesforce                                                                                                                                                                                                                                                                                        |
| scripts/generar_informe_billeteras.py                                            | Informe HTML de billeteras y pagos (hallazgos, pruebas, conservación del saldo, conciliación)              | probador-billeteras                                                                                                                                                                                                                                                                                        |
| herramientas/ecommerce/shopify.py (npm run shopify)                              | Relevamiento funcional de una tienda Shopify (vidriera, Admin API de lectura, Theme Check)                 | probador-shopify                                                                                                                                                                                                                                                                                           |
| herramientas/ecommerce/wordpress.py (npm run wordpress)                          | Relevamiento funcional de WordPress / WooCommerce (vidriera, REST API de lectura, WP-CLI)                  | probador-wordpress                                                                                                                                                                                                                                                                                         |
| scripts/generar_informe_ecommerce.py                                             | Informe HTML de Shopify y WordPress / WooCommerce (relevamiento y pruebas)                                 | probador-shopify, probador-wordpress                                                                                                                                                                                                                                                                       |
| scripts/generar_informe_investigacion.py                                         | Informe HTML del relevamiento de un proyecto (resumen, ambigüedades, preguntas)                            | investigador-proyecto                                                                                                                                                                                                                                                                                      |
| herramientas/manual/manual.py (npm run manual)                                   | Manual de usuario: carpetas y versiones, capturas, HTML y Word, checklist, plan de la plataforma y conocimiento a input/documentacion/ | redactor-manual |
| herramientas/scalar/scalar.py (npm run scalar)                                   | Scalar: descarga del Registry, colección de casos con tests pm, OpenAPI con x-post-response, validación y publicación | probador-scalar |
| scripts/actualizar_conocimiento.py (npm run actualizar-conocimiento)            | Actualización programada de input/documentacion/: app y código sin tokens, historias con el documentador (tope de gasto), aviso | documentador-proyecto |

## Conectores: qué agentes los aprovechan

| Conector                         | Activo por defecto | Lo aprovechan                                                                                                                                                                                                                                                                                              |
| -------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| playwright · playwright-headless | Sí                 | ejecutor-e2e, web-mapper, explorador-web, analista-accesibilidad, analista-fallos, pixel-perfect, reparador-automatizacion, verificador-correos, analista-traductor, generador-charters, evaluador-ux, probador-formularios, documentador-proyecto, probador-permisos, probador-resiliencia, pentester-web, probador-shopify, probador-wordpress                |
| atlassian (Jira y Confluence)    | Sí                 | todos los que investigan una historia (skill investigacion-contexto), generador-reportes-bug, documentador-proyecto (también Bitbucket Cloud, con token)                                                                                                                                                   |
| azure-devops                     | No                 | los mismos que atlassian, si tu equipo usa Azure DevOps; gestor-pruebas (Azure Test Plans); documentador-proyecto (Azure Repos)                                                                                                                                                                            |
| figma · figma-desktop            | No                 | los que investigan una historia (textos, estados y validaciones del diseño), web-mapper, pixel-perfect (comparar contra el diseño)                                                                                                                                                                         |
| qtm4j · qmetry · aio-tests       | No                 | consultas desde el chat (la carga de casos y resultados va por scripts/gestion)                                                                                                                                                                                                                            |
| k0lmena-tmt                      | No                 | cargar y consultar casos en k0lmenaTMT                                                                                                                                                                                                                                                                     |
| github · gitlab                  | No                 | documentador-proyecto (repositorio de la app, solo lectura), triador-bugs (issues)                                                                                                                                                                                                                         |
| linear · clickup · monday · asana · trello · notion · youtrack · shortcut | No                 | los mismos que atlassian, si tu equipo usa esa herramienta: todos los que investigan una historia (skill investigacion-contexto), documentador-proyecto                                                                                                                                                    |
| appium-mcp                       | No                 | mobile-mapper                                                                                                                                                                                                                                                                                              |
| salesforce                       | No                 | probador-salesforce (consultas SOQL de solo lectura y tests de Apex en una org autorizada; la org se autoriza antes con sf org login web)                                                                                                                                                                   |

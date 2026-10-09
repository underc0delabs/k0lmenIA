<p align="center">
<img src="https://i.imgur.com/jrStTTp.png" width="400px">
</p>

<h1 align="center">k0lmena Automation Framework</h1>

<p align="center">
Framework de automatización <b>todo en uno</b> (web, API, mobile y performance), integrado en k0lmenIA.<br>
Copia del repo original <a href="https://github.com/underc0delabs/k0lmena">underc0delabs/k0lmena</a>, reorganizada por tipo de prueba.
</p>

---

## Cómo encaja en k0lmenIA

Los agentes **mapper** escriben la automatización una sola vez y después la suite corre **sin agentes y sin consumir tokens**:

```
casos de prueba (output/casos-de-prueba/)
        │
        ├── web-mapper     → recorre la web (Playwright MCP)    → web/features + steps + locators
        ├── api-mapper     → lee Postman / Swagger              → api/features
        ├── mobile-mapper  → recorre la app (Appium MCP)        → mobile/features + steps + locators
        │                                                                │
        │                                                          npm test  (sin tokens)
        └── performance-mapper → carga y umbrales (pregunta)     → performance/k6 · artillery · jmeter
                                                                         │
                                                               npm run perf  (sin tokens)
```

## Estructura

```
herramientas/k0lmena/
├── web/            Playwright + Cucumber
│   ├── features/   .feature (uno por historia: HU-001-<slug>.feature)
│   ├── steps/      definiciones de pasos (HU-001.steps.ts)
│   ├── locators/   locators (HU-001.locators.ts)
│   ├── hooks/ config/ utils/   framework: navegador, helpers, auto-healing
├── api/            axios + Cucumber
│   ├── features/
│   └── steps/      comunes.steps.ts = steps genéricos en español
├── mobile/         WebdriverIO + Appium (Android / iOS)
│   ├── features/ steps/ locators/
│   ├── support/    wdio.conf.ts (dispositivo, emulador o BrowserStack) y hooks
│   └── apps/       tu .apk / .ipa (no se versiona)
├── performance/    k6 (k6/http/), Artillery + Playwright (artillery/) y JMeter (jmeter/)
├── reports/        reportes HTML de cada tipo
├── tools/          crawler de locators, link tester, recorder, debug
├── cucumber.js     perfiles web / api / debug
├── run-tests.js    runner de npm test
└── env.js          carga el .env único de la raíz de k0lmenIA
```

## Instalación

Requiere **Node.js 20+** (22+ si vas a usar el mobile-mapper). Incluye los drivers de PostgreSQL, MySQL / MariaDB, SQL Server y MongoDB para las verificaciones en base de datos.

```bash
cd herramientas/k0lmena
npm install
npx playwright install chromium     # o: npx playwright install (todos los navegadores)
# Variables: k0lmena usa el .env de la RAÍZ del repo (no hay otro).
# Si todavía no existe, desde la raíz:  cp .env.example .env
```

## Ejecutar

```
+---------------------+-----------------------------------+
| Comando             | Qué corre                         |
+=====================+===================================+
| npm test            | web + api                         |
+---------------------+-----------------------------------+
| npm run test:web    | solo web                          |
+---------------------+-----------------------------------+
| npm run test:api    | solo api                          |
+---------------------+-----------------------------------+
| npm run test:mobile | solo mobile (según MOBILE_TARGET) |
+---------------------+-----------------------------------+
| npm run test:all    | web + api + mobile                |
+---------------------+-----------------------------------+
```

**Filtrar por tag** con la variable `TAGS` (o fijándola en el `.env` de la raíz):

```bash
TAGS=@HU-001 npm test                 # bash
$env:TAGS="@HU-001"; npm test         # PowerShell
TAGS="@Smoke and not @wip" npm run test:web
```

Los escenarios marcados `@bloqueado` (pasos que el mapper no pudo verificar en la app) **nunca se ejecutan**. Los marcados `@falta-info @FI-XX` dependen de un dato que no está definido en la historia ni en sus fuentes: corren normalmente y el reporte les agrega una nota de **Falta información** (detalle en `output/contexto/`).

### Mobile: dispositivo, emulador o BrowserStack

Se elige en el `.env` de la raíz, sin tocar código:

```
+-----------------+-----------------------------------------+
| MOBILE_TARGET   | Necesita                                |
+=================+=========================================+
| device          | Dispositivo por USB con depuración,     |
|                 | MOBILE_UDID (adb devices), app en       |
|                 | mobile/apps/                            |
+-----------------+-----------------------------------------+
| emulator        | Emulador/simulador encendido,           |
|                 | MOBILE_DEVICE_NAME, app en mobile/apps/ |
+-----------------+-----------------------------------------+
| browserstack    | BROWSERSTACK_USER, BROWSERSTACK_KEY y   |
|                 | BROWSERSTACK_APP (bs://...)             |
+-----------------+-----------------------------------------+
```

`MOBILE_PLATFORM` define Android (UiAutomator2) o iOS (XCUITest).

### Performance

```bash
npm run bootstrap:k6                       # una vez: descarga k6 en tools/k6 (o tenelo en el PATH)
npm run bootstrap:jmeter                   # una vez: descarga JMeter en tools/jmeter (necesita Java 8+)
npm run perf                               # lista los scripts (k6, Artillery y JMeter)
npm run perf -- <script> smoke             # valida el script con carga mínima
npm run perf -- <script> load              # carga objetivo: pide confirmación
npm run perf -- <script> stress --confirmar   # sin pregunta (CI o agente con autorización)
npm run perf -- <script> load --vus 20 --duracion 2m   # k6 y JMeter: pisa la carga del script
```

- **Perfiles**: `smoke` (carga mínima, valida el script), `load` (carga objetivo sostenida), `stress` (1x, 2x y 3x), `soak` (larga duración) y `spike` (pico brusco). Los perfiles con carga piden confirmación.
- **Scripts**: k6 en `performance/k6/http/<script>.ts` (base en `performance/k6/lib/k0lmena.ts`); Artillery en `performance/artillery/<script>.yaml` + processor `.ts`; JMeter en `performance/jmeter/<script>.jmx` + `<script>.json` (destino, carga por perfil y umbrales; plantilla en `performance/jmeter/plantilla/`). Plantillas en el skill `automatizacion-k0lmena`.
- **Umbrales**: en el script (`umbrales` en k6, `ensure` en Artillery) o en el `.json` del `.jmx` (JMeter). Si alguno no se cumple, la corrida termina con código 1.
- **Salida** en `reports/performance/<k6|artillery|jmeter>/`: reporte HTML (dashboard), resumen JSON, resultado crudo y log de la herramienta; con JMeter, también su dashboard nativo (`<corrida>-dashboard/`). La consola muestra solo el resumen.

## Base de datos

Verificaciones de solo lectura en **PostgreSQL, MySQL / MariaDB, SQL Server y MongoDB**, con las conexiones del `.env` de la raíz (`DB_CONEXIONES` + `DB_<NOMBRE>_*`, ver `.env.example`).

```bash
npm run bd -- conexiones                                  # lista y prueba las conexiones
npm run bd -- esquema --tabla usuarios                    # columnas de una tabla (o campos de una colección)
npm run bd -- existe --tabla usuarios --donde email=ana@test.com
npm run bd -- consultar --sql "SELECT id, estado FROM usuarios WHERE email = ?" --param ana@test.com
```

Los agentes agregan estas verificaciones a un `.feature` **solo cuando se las piden**; sin `DB_CONEXIONES` en el `.env`, la suite corre igual que siempre. En los `.feature` (web, API o mobile) están disponibles los steps de `tools/bd/bd.steps.ts`: `existe en la base de datos un registro en "usuarios" donde "email" es "…"`, `el registro de "usuarios" donde "id" es "{idUsuario}" tiene:` (tabla campo/valor), `consulto en la base de datos:` (SQL o, en MongoDB, JSON) y más; la lista completa está en el skill `automatizacion-k0lmena`. Las lecturas corren en transacciones de solo lectura que se descartan y los datos sensibles se enmascaran en el reporte. Escribir solo es posible desde el CLI (`escribir … --confirmar`), con `DB_<NOMBRE>_ESCRITURA=si` y nunca en conexiones marcadas `DB_<NOMBRE>_PRODUCCION=si`.

## Reportes

```
+--------------------------+-------------------------+
| Comando                  | Reporte                 |
+==========================+=========================+
| npm run report:web       | HTML de la suite web    |
+--------------------------+-------------------------+
| npm run report:api       | HTML de la suite api    |
+--------------------------+-------------------------+
| npm run report:mobile    | HTML de la suite mobile |
+--------------------------+-------------------------+
| npm run perf -- <script> | HTML perf. (automático) |
+--------------------------+-------------------------+
```

Primero corré los tests y después generá el reporte: refleja **solo la última corrida** (cada `npm test` limpia las evidencias de la anterior).

### Evidencias que se adjuntan

```
+---------+------------------------------+------------------------------------------+
| Suite   | Escenario que pasa           | Escenario que falla                      |
+=========+==============================+==========================================+
| web     | Captura final (+ GIF opc.)   | Video completo, captura, error con       |
|         |                              | stack, URL y título de la página, logs   |
|         |                              | del navegador (consola, errores JS,      |
|         |                              | requests fallidos, respuestas HTTP >=    |
|         |                              | 400), logs de Node y trace de Playwright |
+---------+------------------------------+------------------------------------------+
| api     | Request y response completos | Lo mismo, más el error de la validación  |
|         |                              | que falló                                |
+---------+------------------------------+------------------------------------------+
| mobile  | Captura final (+ GIF opc.)   | Video completo, captura, page source y   |
|         |                              | logs del dispositivo (logcat / syslog)   |
+---------+------------------------------+------------------------------------------+
```

Se controlan desde el `.env` de la raíz:

- `EVIDENCE`: qué se guarda de los escenarios que pasan. `captura` (captura final), `ambos` (captura + **GIF del recorrido**, una captura por paso; suma ~0,5 s por escenario) u `off`. **Si queda vacía, `npm test` lo pregunta al arrancar**; en CI o sin terminal interactiva usa `captura`.
- `VIDEO`: `on-failure` (por defecto), `on` u `off`.
- `TRACE`: `on-failure`, `on` u `off`.

En el reporte, el GIF y el video se abren desde los adjuntos del escenario y el trace se descarga para abrirlo en [trace.playwright.dev](https://trace.playwright.dev). En API el header `Authorization` se oculta.

Archivos sueltos: `reports/web/videos/`, `traces/`, `screenshots/` y `evidencias/` (mobile: `reports/mobile/html/videos/`, `screenshots/` y `evidencias/`).

## Auto-healing de locators (web)

Con `K0LMENA_AUTO_HEALING=on`, cada acción exitosa guarda locators alternativos del elemento (`learn`) y, si el locator original falla, prueba esos candidatos (`heal`). Cuando cura uno, lo informa en consola como `HEALED: <original> -> <candidato>`. Modos: `off`, `learn`, `heal`, `on` (recomendado).

## Herramientas

```
+-----------------------+------------------------------------------+
| Comando               | Para qué                                 |
+=======================+==========================================+
| npm run crawler [url] | Genera un archivo de locators            |
|                       | recorriendo una página                   |
+-----------------------+------------------------------------------+
| npm run link-tester   | Busca enlaces e imágenes rotas (BASEURL) |
+-----------------------+------------------------------------------+
| npm run record        | Graba un flujo con Playwright codegen    |
+-----------------------+------------------------------------------+
| npm run debug         | Corre web en modo debug (secuencial, con |
|                       | logs)                                    |
+-----------------------+------------------------------------------+
```

## Créditos

k0lmena es un proyecto open source (licencia ISC) de **Danilo Vezzoni**. Video: https://youtu.be/n7plezXinZ8

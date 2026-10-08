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
        └── mobile-mapper  → recorre la app (Appium MCP)        → mobile/features + steps + locators
                                                                         │
                                                                   npm test  (sin tokens)
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
├── performance/    Artillery y k6
├── reports/        reportes HTML de cada tipo
├── tools/          crawler de locators, link tester, recorder, debug
├── cucumber.js     perfiles web / api / debug
├── run-tests.js    runner de npm test
└── env.js          carga el .env único de la raíz de k0lmenIA
```

## Instalación

Requiere **Node.js 20+** (22+ si vas a usar el mobile-mapper).

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

Los escenarios marcados `@bloqueado` (pasos que el mapper no pudo verificar en la app) **nunca se ejecutan**.

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
npm run perf:load                 # Artillery (genera reports/performance/artillery/report.json)
npm run perf:load-report          # reporte HTML de Artillery
npm run bootstrap:k6              # descarga k6 en tools/k6
npm run k6:build                  # compila los escenarios TypeScript de k6
npm run k6:smoke                  # también: k6:stress, k6:soak, k6:spike, k6:run:browser
```

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
| npm run perf:load-report | HTML de Artillery       |
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

k0lmena es un proyecto open source (licencia ISC) de **Danilo Vezzoni**, con **Gianella Vezzoni**, **Maximiliano Pintos** y **Yanko Leta**. Video: https://youtu.be/n7plezXinZ8

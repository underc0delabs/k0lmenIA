---
name: automatizacion-k0lmena
description: Convenciones para automatizar en k0lmena — dónde van los .feature, steps y locators de web, api y mobile, cómo nombrarlos y taggearlos, reutilizar steps, los steps de base de datos y los scripts de performance (k6, Artillery, JMeter). Úsalo al mapear casos (web-mapper, api-mapper, mobile-mapper, performance-mapper, verificador-datos).
---

# Automatización con k0lmena

k0lmena vive en `herramientas/k0lmena/`. Los mappers **escriben código una vez**; después la suite corre sin agentes (y sin tokens) con `k0lmenia test`.

```
herramientas/k0lmena/
├── web/      features/  steps/  locators/   (Playwright + Cucumber; hooks/, utils/ ya existen)
├── api/      features/  steps/              (axios + Cucumber; steps/comunes.steps.ts ya existe)
├── mobile/   features/  steps/  locators/   (WebdriverIO + Appium; support/ ya existe; apps/ = .apk/.ipa)
├── performance/  k6/http/  artillery/  jmeter/   (k6, Artillery y JMeter; lo genera el performance-mapper)
├── cucumber.js  run-tests.js  env.js      (env.js carga el .env ÚNICO de la raíz del repo)
```

## Nombres y trazabilidad

```
+-----------+-----------------------------------------+
| Archivo   | Nombre                                  |
+===========+=========================================+
| Feature   | `<tipo>/features/HU-001-<slug>.feature` |
+-----------+-----------------------------------------+
| Steps     | `<tipo>/steps/HU-001.steps.ts`          |
+-----------+-----------------------------------------+
| Locators  | `<tipo>/locators/HU-001.locators.ts`    |
+-----------+-----------------------------------------+
```

- Tags del `Feature`: `@HU-001` y el tipo (`@web`, `@api` o `@mobile`).
- Tags de cada `Scenario`: el ID del caso de origen (`@CP-001`, `@CP-API-001`), su prioridad (`@critica`/`@alta`/`@media`/`@baja`, la misma del caso de origen) y, si es crítico, `@smoke` (siempre en minúscula: Cucumber distingue mayúsculas y `TAGS=@smoke` no encuentra `@Smoke`). Si el caso de origen es un `.feature` que ya trae el tag de prioridad, conservalo tal cual.
- **Falta información**: si el caso depende de un dato que no está definido (ficha `output/contexto/contexto-HU-XXX.md`, skill `investigacion-contexto`), el escenario lleva `@falta-info @FI-01` y el comentario `# FALTA INFORMACIÓN (FI-01): <qué falta>` arriba. Corre normalmente (salvo que también sea `@bloqueado`) y el reporte de k0lmena le agrega una nota visible; al publicar en Xray/QMetry/AIO, el comentario lo indica.
- Si la fuente no es una HU (ej. un contrato de API), usá un slug: `api/features/pets.feature` y tag `@contrato-pets`.

## Gherkin

- Keywords en **inglés** (`Feature`, `Background`, `Scenario`, `Scenario Outline`, `Examples`, `Given`, `When`, `Then`, `And`, `But`) y contenido en **español**, igual que el resto del repo.
- Un paso = una acción o una verificación observable. Los valores que cambian van entre comillas (`"Dinno"`) para que el step sea reutilizable.
- **Nunca** escribas credenciales en un `.feature`: usá un paso como `When el usuario inicia sesión con credenciales válidas` y que el step lea `process.env.APP_USER` / `APP_PASSWORD`.
- Un paso que **no se pudo verificar** contra la app real: dejalo escrito como dice el caso, marcá el escenario con `@bloqueado` y agregá un comentario `# BLOQUEADO: <motivo>` arriba. `k0lmenia test` nunca corre `@bloqueado`.

## Reutilizar steps (obligatorio)

Cucumber falla con *Ambiguous step* si dos definiciones matchean el mismo texto. Antes de crear un step:

1. Buscá el texto en las definiciones existentes del tipo: `grep -rn "Given(\|When(\|Then(" herramientas/k0lmena/<tipo>/steps/`.
2. Si existe uno igual o parametrizable, **reutilizalo con el texto exacto** en el `.feature`.
3. Solo si no existe, crealo en el `HU-XXX.steps.ts` de la historia.
4. Un mismo paso que aparece en varios escenarios se define **una sola vez**.

## Web — steps y locators

Locators: un objeto por historia, con entradas `LocatorInput`. Priorizá en este orden: `role` + `name` → `label` → `placeholder` → `testId` → `text`. Solo usá `css` o `xpath` si no hay alternativa, y comentá por qué.

```ts
// web/locators/HU-001.locators.ts
import type { LocatorInput } from '../utils/interactions';

export const HU001 = {
  inputNombre: { placeholder: 'Nombre' },
  comboPais: { label: 'País' },
  btnRegistrar: { role: 'button', name: 'Registrar' },
  msgExito: { text: 'Registro Exitoso' },
} satisfies Record<string, LocatorInput>;
```

Steps: siempre iterar `pages` (k0lmena puede correr varios navegadores) y usar los helpers, que ya traen esperas y auto-healing. **Sin esperas fijas**: nunca `page.waitForTimeout()` ni la opción `delayMs` de los helpers; esperá algo observable (`expectVisible`, `expectUrlContains(page, /…/)`, `waitForApiOk(page, /\/api\/…/)`).

```ts
// web/steps/HU-001.steps.ts
import { Given, When, Then } from '@cucumber/cucumber';
import { BASEURL } from '../config';
import { pages } from '../hooks/hook';
import { click, fill, selectOption } from '../utils/interactions';
import { expectVisible, expectUrlContains } from '../utils/validations';
import { HU001 } from '../locators/HU-001.locators';

Given('el usuario está en la página de registro', async () => {
  for (const page of pages) await page.goto(`${BASEURL}/registro`);
});

When('el usuario completa el nombre {string}', async (nombre: string) => {
  for (const page of pages) await fill(page, HU001.inputNombre, nombre);
});

Then('el usuario ve el mensaje de registro exitoso', async () => {
  for (const page of pages) await expectVisible(page, HU001.msgExito);
});
```

Helpers disponibles (`web/utils/interactions.ts`): `click(page, loc)`, `fill(page, loc, valor)`, `selectOption(page, loc, opcion)`, `selectByLabel(page, label, opcion)`, `check` / `uncheck(page, loc)`, `hover`, `press(page, loc, tecla)`, `scrollIntoView`.
Validaciones (`web/utils/validations.ts`): `expectVisible`, `expectHidden`, `expectEnabled`, `expectDisabled`, `expectChecked`, `expectText(page, loc, texto)`, `expectCount(page, loc, n)`, `expectAttribute`, `expectUrlContains(page, /fragmento/)` (pasale una **RegExp**: con string compara la URL exacta), `expectTitleIs`.

La URL base sale de `APP_URL` del `.env` de la raíz (la única URL de la app; k0lmena la expone como `BASEURL`). En los steps usá rutas relativas a `BASEURL`, nunca la URL completa hardcodeada.

## API — solo features

`api/steps/comunes.steps.ts` ya trae steps genéricos. Los features de API se arman **solo con estos textos** (no escribas steps nuevos salvo que sea imposible expresar la validación):

```gherkin
Given el request usa el token de autenticación
Given el request usa la API key en el header "api_key"
Given el request usa la API key en el parámetro "key"
Given el request usa autenticación básica
Given el request no envía token de autenticación
Given el request usa el header "X-Tenant" con valor "demo"
Given el request tiene los parámetros:
  | status | available |
When envío un GET a "/pet/{petId}"
When envío un POST a "/pet" con el body:
  """
  { "name": "Firulais {aleatorio}", "status": "available" }
  """
When envío un POST a "/pet/{petId}" con el formulario:
  | name   | Firulais |
  | status | sold     |
When guardo el campo "id" de la respuesta como "petId"
Then el status de la respuesta es 200
Then la respuesta contiene el campo "category.name"
Then la respuesta no contiene el campo "password"
Then el campo "status" de la respuesta es "available"
Then el campo "id" de la respuesta es el número 10
Then el campo "tags" de la respuesta es de tipo "array"
Then el campo "id" de la respuesta es de tipo "integer"
Then la respuesta es una lista
Then la respuesta es una lista con al menos 1 elemento
Then la respuesta tiene un elemento con "id" igual a "{petId}"
Then la lista "items" de la respuesta tiene un elemento con "name" igual a "Firulais"
Then la respuesta contiene el texto "logged in user session"
Then la respuesta tiene los campos:
  | id     |
  | name   |
Then el header "content-type" de la respuesta contiene "application/json"
Then la respuesta llega en menos de 2000 ms
```

- **Primero resumí la spec** con `k0lmenia py scripts/resumir_openapi.py <url o archivo>` (Swagger 2.0 u OpenAPI 3.x, JSON o YAML): da el `API_BASEURL`, el step de autenticación de cada `securityScheme`, los parámetros, cómo va el body (JSON, formulario o multipart), un body de ejemplo y los status documentados.
- **URL**: `API_BASEURL` es el server de la spec **con** su basePath (`https://petstore.swagger.io/v2`) y el endpoint del `.feature` es el path de la spec tal cual (`/pet/{petId}`). No repitas el basePath en el endpoint (`/v2/pet` con una base que ya termina en `/v2` da 404).
- **Autenticación** según el `securityScheme`: Bearer u OAuth2 → `el request usa el token de autenticación` (`API_TOKEN`); `apiKey` en header → `el request usa la API key en el header "<name>"`; en query → `... en el parámetro "<name>"` (`API_KEY`, o `API_TOKEN` si falta); `basic` → `el request usa autenticación básica` (`API_USER`/`API_PASSWORD`). Usá el `name` exacto de la spec (en petstore, `api_key`).
- **Cada escenario crea sus datos**: las variables se reinician en cada escenario, así que un `GET /pet/{petId}` primero crea la mascota (`POST` + `guardo el campo "id" ... como "petId"`) en el mismo escenario (o en el `Background`). Nunca un id fijo de otra corrida ni de otro escenario: con `PARALLEL` o en una API compartida, otro lo modifica o lo borra.
- **Datos únicos**: `{aleatorio}` (6 dígitos), `{uuid}`, `{timestamp}` y `{ahora}` se generan una vez por escenario (valen lo mismo en todos sus pasos): `"email": "qa+{aleatorio}@prueba.com"`.
- `{nombre}` en endpoint, parámetros, header o body se reemplaza por un valor guardado, un dato generado o, si no, la variable de entorno del mismo nombre. Si queda una `{variable}` sin valor en el endpoint o el body, el paso falla avisando cuál (no se manda literal).
- **Body**: JSON con `con el body:` (un JSON mal escrito falla avisando dónde); `formData` / `application/x-www-form-urlencoded` con `con el formulario:`; los parámetros de query con `el request tiene los parámetros:` (se codifican solos). Multipart (subir archivos) no tiene step genérico: escenario `@bloqueado` con ese motivo o un step propio.
- **Tipos** (`es de tipo`): `integer`, `number`, `string`, `boolean`, `array`, `object` o `null`, como en la spec (también en español). Los ids enteros grandes (int64) se leen como texto para no perder precisión: compararlos con `es "9223372036854775807"`, no con `es el número`.
- Respuestas que no son JSON (texto plano) se validan con `la respuesta contiene el texto`.
- Los campos usan notación de puntos (`data.items.0.id`).
- **La spec no siempre dice la verdad**: si la API responde otra cosa que la spec (en petstore, 404 o 500 donde la spec dice 400), el `Then` queda con lo que dice la spec y el escenario lleva `@difiere-de-la-spec` con un comentario `# La API responde XXX; la spec dice YYY`. Así, al ver los fallos, se distingue un bug o una spec desactualizada de un test mal hecho.
- **APIs públicas de demo** (petstore y similares): son compartidas y cambian solas. No afirmes valores de listados (`findByStatus`) más allá de su estructura, y creá cada dato que leés.

### GraphQL

Los mismos `comunes.steps.ts` traen steps de GraphQL. La query va en un docstring **tal cual** (sus llaves no se interpolan); los valores dinámicos van en las variables, que sí aceptan `{nombre}`:

```gherkin
Given el endpoint GraphQL es "/graphql"
Given las variables GraphQL son:
  """
  { "code": "{codigoPais}" }
  """
When envío la consulta GraphQL:
  """
  query Pais($code: ID!) { country(code: $code) { name capital languages { code } } }
  """
Then el status de la respuesta es 200
Then la respuesta GraphQL no tiene errores
Then la respuesta GraphQL contiene el campo "country.capital"
Then el campo GraphQL "country.name" es "Argentina"
Then el campo GraphQL "country.population" es el número 46000000
Then el campo GraphQL "country" es nulo
Then el campo GraphQL "country.languages" es una lista con al menos 1 elemento
Then la respuesta GraphQL tiene un error con el mensaje "Cannot query field"
Then la respuesta GraphQL tiene un error con el código "GRAPHQL_VALIDATION_FAILED"
When guardo el campo GraphQL "createPost.id" como "idPost"
```

- El endpoint sale de `el endpoint GraphQL es` (relativo a `API_BASEURL` o una URL completa) o, si no se dice, de `GRAPHQL_URL` del `.env` y, si tampoco está, de `API_BASEURL` + `/graphql`.
- Los campos `GraphQL` se leen **dentro de `data`** (`country.name` es `data.country.name`); los steps comunes (`la respuesta contiene el campo "data.country"`, `el status de la respuesta es`, los headers y el token) también sirven.
- Un escenario por operación y condición; las **mutations** son métodos con efecto (confirmación antes de verificarlas).

## Mobile — steps y locators

Locators: un objeto por historia con selectores de WebdriverIO. Priorizá: accessibility id (`~Iniciar sesión`) → resource-id (`android=new UiSelector().resourceId("emailInput")` o `id=com.app:id/email`) → texto (`android=new UiSelector().text("Ingresar")`, `-ios predicate string:label == "Ingresar"`). Evitá XPath salvo que no haya alternativa.

```ts
// mobile/steps/HU-001.steps.ts
import { Given, When, Then } from '@wdio/cucumber-framework';
import { HU001 } from '../locators/HU-001.locators';

When('el usuario ingresa {string} en el campo usuario', async (usuario: string) => {
  const campo = await $(HU001.inputUsuario);
  await campo.waitForDisplayed({ timeout: 10000 });
  await campo.setValue(usuario);
});
```

Dónde corre (dispositivo, emulador o BrowserStack) se define en el `.env` de la raíz (`MOBILE_TARGET`); el código de los steps es el mismo.

## Base de datos — verificaciones en los tests

`tools/bd/bd.steps.ts` está cargado en las suites web y API (en mobile todavía no funciona: WebdriverIO usa su propia copia de Cucumber, así que no los agregues a un `.feature` mobile). Son steps **de solo lectura** que verifican lo que una prueba dejó guardado. Conexiones en el `.env` (`DB_CONEXIONES` + `DB_<NOMBRE>_*`); sin nombre se usa la primera. **Solo se agregan cuando la persona lo pide explícitamente** (*"sumá la verificación en la base"*, *"validá que quede guardado en la tabla X"*). Aunque un caso diga *"el dato se guarda en la base"*, no los agregues por tu cuenta: dejalo anotado como sugerencia en el reporte de mapeo (*"se puede sumar verificación en BD si se pide"*). Cuando se piden, mirá antes las tablas y columnas con `k0lmenia bd -- esquema --tabla <tabla>`: no adivines nombres.

```gherkin
Then existe en la base de datos un registro en "usuarios" donde "email" es "ana@test.com"
Then no existe en la base de datos un registro en "usuarios" donde "email" es "ana@test.com"
Then la base de datos tiene 1 registro en "pedidos" donde:
  | campo      | valor        |
  | usuario_id | {idUsuario}  |
  | estado     | PAGADO       |
Then el registro de "usuarios" donde "email" es "ana@test.com" tiene:
  | campo  | valor      |
  | estado | ACTIVO     |
  | baja   | (nulo)     |
When consulto en la base de datos:
  """
  SELECT id, total FROM pedidos WHERE estado = 'PAGADO'
  """
Then la consulta devuelve 1 fila                 # también: "la consulta devuelve al menos 2 filas"
Then el campo "total" de la consulta es "1500.5"
When guardo el campo "id" de la consulta como "idPedido"
```

- Con otra conexión: `existe en la base de datos "pagos" un registro en …`, `la base de datos "pagos" tiene …`, `en la base de datos "pagos" el registro de … tiene:`, `consulto en la base de datos "pagos":`.
- `{variable}` toma lo guardado en el escenario (por ejemplo, con `guardo el campo "id" de la respuesta como "idUsuario"` de la API) o una variable del `.env`. `(nulo)` verifica `NULL`.
- Comparación tolerante: números (`1500.5` = `1500.50`), booleanos (`true` = `1`) y fechas (`2026-10-01` coincide con `2026-10-01 10:00:00`).
- Si el dato se guarda de forma asíncrona, los steps reintentan hasta `DB_ESPERA_MS` (5000 ms por defecto).
- MongoDB: la tabla es la colección y la consulta libre es un JSON: `{"coleccion": "usuarios", "filtro": {"estado": "ACTIVO"}}`.
- Cada verificación adjunta al reporte la consulta y las filas encontradas (con los datos sensibles enmascarados).

## Performance — k6, Artillery y JMeter

Se corre con `k0lmenia perf -- <script> <perfil>` (`run-perf.js`). Perfiles: `smoke` (carga mínima, valida el script), `load`, `stress`, `soak`, `spike`. Cada corrida deja en `reports/performance/<k6|artillery|jmeter>/` el reporte HTML, un resumen JSON chico, el resultado crudo y el log; la consola muestra solo el resumen.

```
+------------------------+------------------------------------------+------------------------------------------+
| Herramienta            | Cuándo                                   | Archivos                                 |
+========================+==========================================+==========================================+
| k6                     | APIs / HTTP (escala a miles de usuarios) | `performance/k6/http/HU-001-<slug>.ts`   |
+------------------------+------------------------------------------+------------------------------------------+
| Artillery + Playwright | Flujos de navegador (pocos usuarios:     | `performance/artillery/HU-001-           |
|                        | cada uno es un Chromium)                 | <slug>.yaml` + `HU-001-<slug>.ts`        |
|                        |                                          | (processor)                              |
+------------------------+------------------------------------------+------------------------------------------+
| JMeter                 | APIs / HTTP cuando el equipo ya trabaja  | `performance/jmeter/HU-001-<slug>.jmx` + |
|                        | con JMeter o trae un `.jmx` para reusar, | `HU-001-<slug>.json`                     |
|                        | o para protocolos que no son HTTP (JDBC, |                                          |
|                        | JMS, SOAP, TCP…)                         |                                          |
+------------------------+------------------------------------------+------------------------------------------+
```

### k6

```ts
// performance/k6/http/HU-001-<slug>.ts
import { check, group, sleep } from 'k6';
import { env, opciones, pedir } from '../lib/k0lmena';
export { handleSummary } from '../lib/k0lmena';   // obligatorio: arma el reporte

const BASE = env.API_BASEURL;                       // o env.BASEURL; token: env.TOKEN (API_TOKEN)
const E = { listar: 'GET /usuarios', crear: 'POST /usuarios' };   // nombre = método + path con {params}

export const options = opciones({
  vus: 50, duracion: '5m',                          // carga objetivo (la define la persona)
  // rampa: '1m', duracionSoak: '2h', pico: 200,    // opcionales
  umbrales: {                                       // los define la persona
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    'http_req_duration{name:POST /usuarios}': ['p(95)<800'],   // umbral por endpoint
    checks: ['rate>0.99'],
  },
  endpoints: Object.values(E),                      // métricas por endpoint en el reporte
});

export default function () {
  group('Listar usuarios', () => {
    const res = pedir('GET', E.listar, `${BASE}/usuarios?page=1`);
    check(res, { 'listar: status 200': (r) => r.status === 200 });
  });
  sleep(1);                                         // tiempo de pensamiento
}
```

- `pedir(metodo, nombre, url, body?, headers?)` agrega `Content-Type` JSON y el `Authorization: Bearer` si hay `API_TOKEN`.
- `__ENV.X` lee cualquier variable del `.env` de la raíz (ej. `__ENV.APP_USER`). Nunca escribas credenciales en el script.
- Datos variables: `__VU` y `__ITER` para no repetir (ej. emails únicos); un login por usuario va en `setup()` o al inicio de la iteración.
- No modifiques `lib/k0lmena.ts`.

### Artillery + Playwright

```yaml
# performance/artillery/HU-001-<slug>.yaml
config:
  target: https://app.ejemplo.com                  # la URL confirmada por la persona
  engines: { playwright: { launchOptions: { headless: true } } }
  processor: ./HU-001-<slug>.ts
  plugins: { ensure: {} }                          # obligatorio para evaluar los umbrales
  ensure:
    maxErrorRate: 1                                # % de usuarios que no completaron el flujo
    thresholds:
      - browser.step.Iniciar sesión.p95: 3000      # <métrica>: máximo (ms)
  environments:                                    # un environment por perfil
    smoke:  { phases: [{ name: smoke, duration: 30, arrivalCount: 2 }] }
    load:   { phases: [{ name: rampa, duration: 60, arrivalRate: 1, rampTo: 5 }, { name: sostenido, duration: 300, arrivalRate: 5, maxVusers: 20 }] }
scenarios:
  - { name: HU-001 <flujo>, engine: playwright, testFunction: flujo }
```

```ts
// performance/artillery/HU-001-<slug>.ts
export async function flujo(page, _vu, _events, test) {
  await test.step('Iniciar sesión', async () => {      // cada step = métrica browser.step.<nombre>
    await page.goto('/login');
    await page.getByLabel('Usuario').fill(process.env.APP_USER ?? '');
    await page.getByLabel('Contraseña').fill(process.env.APP_PASSWORD ?? '');
    await page.getByRole('button', { name: 'Ingresar' }).click();
    await page.getByRole('heading', { name: 'Inicio' }).waitFor();   // cada step termina con una espera observable
  });
}
```

- Usá los mismos selectores que `web/locators/HU-XXX.locators.ts` (role/label/placeholder) si la historia ya está automatizada.
- `arrivalRate` = usuarios nuevos por segundo; `maxVusers` = tope de simultáneos. Cada usuario es un navegador: en una PC común, más de 10-20 simultáneos satura la máquina y mide la PC, no la app.

### JMeter

Se parte de la plantilla `performance/jmeter/plantilla/plantilla.jmx` + `plantilla.json` (copiá las dos y renombralas `HU-001-<slug>`). Requiere Java 8+ y JMeter (`k0lmenia bootstrap:jmeter`, queda en `tools/jmeter`; o `JMETER_HOME`).

El `.json` va al lado del `.jmx`, con el destino, la carga de cada perfil y los umbrales (todo lo define la persona):

```json
{
  "destino": "API_BASEURL",
  "perfiles": {
    "smoke": { "usuarios": 1,  "rampa": 1,  "duracion": 30 },
    "load":  { "usuarios": 50, "rampa": 60, "duracion": 300 }
  },
  "umbrales": {
    "error_pct": 1, "p95": 500, "p99": 1000,
    "por_muestra": { "POST /usuarios": { "p95": 800 } }
  }
}
```

- `destino`: el nombre de una variable del `.env` (`API_BASEURL`, `APP_URL`) o una URL. Llega al `.jmx` como `${__P(base_url)}`; cada request usa `${__P(base_url)}/path` en el campo *Path*.
- Cada clave del perfil llega como propiedad: `${__P(usuarios,1)}`, `${__P(rampa,1)}`, `${__P(duracion,30)}` en el Thread Group (con *scheduler* y loops `-1`). Se pueden sumar claves propias (ej. `pico`) y leerlas igual.
- Umbrales (todos en ms, salvo `error_pct` en %): `error_pct`, `p50`, `p90`, `p95`, `p99`, `avg`, `max`, y `por_muestra` con el nombre exacto del request. Los evalúa el reporte de k0lmena: JMeter no los conoce.
- Cada HTTP Request se nombra `MÉTODO /path` (es la "muestra" del reporte) y lleva una **Response Assertion** con el código esperado; sin aserción, un 404 cuenta como éxito.
- Credenciales: `${__groovy(System.getenv('API_TOKEN') ?: '')}` (o cualquier variable del `.env`); nunca escritas en el `.jmx`.
- Datos variables: `${__threadNum}` y `${__counter(FALSE,)}` para no repetir (ej. emails únicos).
- `--vus` y `--duracion` pisan `usuarios` y `duracion` en una corrida. Además del reporte de k0lmena, cada corrida deja el dashboard nativo de JMeter en `<corrida>-dashboard/index.html`.
- Si la persona trae un `.jmx` propio: adaptalo a estas convenciones (propiedades en el Thread Group, `base_url`, nombres `MÉTODO /path`, aserciones) en lugar de reescribirlo desde cero.

## Validar lo generado (una sola vez)

Desde `herramientas/k0lmena/` (PowerShell usa `$env:REPORT_DIR="reports/validacion"; $env:TAGS="@HU-001"; k0lmenia test:web`):

```bash
REPORT_DIR=reports/validacion TAGS=@HU-001 k0lmenia test:web   # web: no pisa el último k0lmenia test
TAGS=@HU-001 k0lmenia test:api      # o test:mobile (estos sí reemplazan el último reporte: avisalo)
```

- Si falla por un locator o un step mal armado, corregilo y volvé a correr. **Máximo 2 reintentos**; si sigue fallando por el test (no lográs armar el locator o el step), marcá el escenario `@bloqueado` con el motivo y seguí.
- Si falla porque la app no cumple lo esperado (un bug real), **no** cambies el `Then` para que pase: dejalo y reportalo como posible bug (sin `@bloqueado`, que nunca corre: con `# POSIBLE BUG: <qué hace la app>` arriba).

## Reporte de mapeo

Al terminar, guardá `output/mapeos/mapeo-<HU>-<tipo>.md` con una tabla (luego `k0lmenia py scripts/formatear_tablas.py <archivo>`):

```
+--------+---------------------------+---------------------------------------+-----------+----------------------------------------+
| Caso   | Paso del caso             | Paso automatizado                     | Estado    | Nota                                   |
+========+===========================+=======================================+===========+========================================+
| CP-001 | Ingresar el email         | el usuario completa el email "..."    | Mapeado   |                                        |
+--------+---------------------------+---------------------------------------+-----------+----------------------------------------+
| CP-001 | Click en "Enviar"         | el usuario clickea el botón Registrar | Ajustado  | El botón se llama "Registrar"          |
+--------+---------------------------+---------------------------------------+-----------+----------------------------------------+
| CP-002 | Ver mensaje de bienvenida | -                                     | Bloqueado | No aparece ningún mensaje; posible bug |
+--------+---------------------------+---------------------------------------+-----------+----------------------------------------+
```

Estados: `Mapeado` (igual al caso), `Ajustado` (el caso decía otra cosa y se corrigió según la app), `Bloqueado` (no se pudo ejecutar), `Falta información` (el paso o el resultado esperado depende de un `FI-XX`; en la nota, el ID y lo que muestra la app como observación). Si hay pasos `Falta información`, sumá al final la sección **Falta información** con los `FI-XX` involucrados y su pregunta. Cerrá con los archivos generados, el resultado de la validación y el comando para correrlo.

## Ahorro de tokens

- No leas los utils, hooks ni `comunes.steps.ts` completos: las firmas están acá.
- No vuelvas a navegar ni a llamar un endpoint que ya verificaste.
- Respuesta final corta: archivos generados, resultado de la validación, bloqueados y el comando `npm`.

## Referencia del `api-mapper`

### Leer la fuente (con Bash, nunca la spec entera en la conversación)

- **Swagger/OpenAPI**: `k0lmenia py scripts/resumir_openapi.py <url o archivo> --salida output/mapeos/openapi-<slug>.md` (da el `API_BASEURL` —server **con** su basePath—, el step de autenticación de cada `securityScheme`, parámetros, body —JSON, formulario o multipart— con un ejemplo y los status documentados).
- **Postman**: Python o `jq` (en Postman, la base es la variable `{{baseUrl}}`).
- **Bruno o Insomnia**: convertir primero a Postman con `k0lmenia py scripts/convertir_coleccion.py <origen> --salida output/mapeos/_coleccion-<slug>/` y anotar en el reporte de mapeo las advertencias de la conversión.
- **GraphQL**: `k0lmenia py scripts/resumir_graphql.py <url del endpoint o archivo .graphql> [--token] [--salida output/mapeos/schema-<slug>.md]` (introspección por POST, solo lectura; si el servidor limita la profundidad, reintenta más corta; lista queries, mutations y subscriptions con sus argumentos —`!` = obligatorio—, inputs, enums y objetos). Si la introspección está deshabilitada, se pide el SDL: no se adivinan operaciones.

Si el `API_BASEURL` del `.env` difiere del que da la spec, avisá antes de seguir: es la causa más común de que todo dé 404.

### Escenarios por endpoint

Camino feliz, validación de campos obligatorios, tipos inválidos, recurso inexistente (404), sin autenticación (401/403) cuando aplique, y valores límite si el schema define rangos. En **GraphQL**, por operación: la consulta válida (sin `errors` y con los campos de `data`), argumento obligatorio faltante o de tipo inválido, valor de enum inexistente, campo que no existe en el tipo (error de validación), recurso inexistente (`null` o error, según el schema), sin autorización y, si aplica, paginación. Solo los que la fuente respalde: si la spec no documenta qué devuelve un error, se verifica o queda como pregunta.

### Verificar contra la API real (un request por escenario, misma URL, autenticación y body que el `.feature`)

- **GET, HEAD y OPTIONS**, y las **queries** de GraphQL: directo. Si el escenario primero crea el recurso, ese POST tiene efecto: sin autorización, el escenario va `@bloqueado` ("sin verificar: método con efecto").
- **POST, PUT, PATCH, DELETE** y las **mutations**: preguntar antes. Sin autorización, se generan sin verificar y van `@bloqueado` con ese motivo; el reporte lista cómo habilitarlos (verificarlos con autorización y sacar el tag). `@bloqueado` nunca corre en `k0lmenia test`.
- Se verifica **cada `Then`** (status, campos, tipos y valores), no solo el status.
- Si la API contradice la spec, **no** se ajusta el `Then`: queda lo que dice la spec, con `@difiere-de-la-spec` y el comentario `# La API responde XXX; la spec dice YYY`, y se reporta como posible bug o spec desactualizada.

### El `.feature` (`herramientas/k0lmena/api/features/<HU-XXX o contrato>-<slug>.feature`)

- Solo con los textos de `api/steps/comunes.steps.ts` (sección API de este skill, incluidos los de GraphQL). En GraphQL, los valores dinámicos van en las **variables** (aceptan `{nombre}`), no dentro de la query. Un step que no existe va en `api/steps/<HU-XXX o contrato>.steps.ts`, con aviso.
- Tags: `@api` y la historia o contrato en el Feature; `@CP-API-XXX` por escenario.
- **Cada escenario crea lo que lee**: las variables se reinician en cada escenario, así que un GET/PUT/DELETE de un recurso lo crea antes en el mismo escenario (o en el `Background`) y encadena el id con `guardo el campo ... como ...`. Nunca un id fijo ni uno de otro escenario.
- Datos que no se pueden repetir (emails, nombres de usuario): `{aleatorio}`, `{uuid}` o `{timestamp}`.
- Nunca tokens ni credenciales en el `.feature`.

### Validar una vez

Desde `herramientas/k0lmena/`: `TAGS=@<tag> k0lmenia test:api` (PowerShell: `$env:TAGS="@<tag>"; k0lmenia test:api`; si falta `node_modules`, antes `npm install`). Hasta 2 reintentos de corrección. Al terminar, **cada fallo tiene explicación**: `@difiere-de-la-spec`, `@bloqueado` o un bug confirmado. Un paso sin definir, una `{variable}` sin valor, un 404 por la URL o un 401 por la autenticación son errores del `.feature`: se corrigen, no se entregan.

### Falta información

Con la ficha `output/contexto/contexto-HU-XXX.md` (si no existe y los casos son de una historia, se arma primero con `investigacion-contexto`). Un caso con `@falta-info` / `FI-XX` conserva esos tags en el `.feature` (con `# FALTA INFORMACIÓN (FI-XX): …`). **La app no completa el dato que falta**: si la validación depende de él y no hay valor definido, el escenario va `@bloqueado` ("falta información FI-XX"); si el caso usó un supuesto, se automatiza con el supuesto y, si la app hace otra cosa, se reporta como "no coincide con el supuesto de FI-XX" (no como bug). En el reporte de mapeo, esos pasos van con estado `Falta información` y lo que muestra la app como observación.

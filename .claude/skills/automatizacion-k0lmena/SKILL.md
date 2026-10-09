---
name: automatizacion-k0lmena
description: Convenciones para generar pruebas automatizadas en k0lmena (herramientas/k0lmena) — dónde va cada .feature, steps y locators de web, api y mobile, cómo nombrarlos y taggearlos, cómo reutilizar steps sin duplicar, qué helpers usar y cómo validar con npm; los steps de verificación en base de datos; y los scripts de performance (k6, Artillery y JMeter). Úsalo al mapear casos de prueba a automatización (web-mapper, api-mapper, mobile-mapper, performance-mapper, verificador-datos).
---

# Automatización con k0lmena

k0lmena vive en `herramientas/k0lmena/`. Los mappers **escriben código una vez**; después la suite corre sin agentes (y sin tokens) con `npm test`.

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
- Tags de cada `Scenario`: el ID del caso de origen (`@CP-001`, `@CP-API-001`) y, si es crítico, `@Smoke`.
- **Falta información**: si el caso depende de un dato que no está definido (ficha `output/contexto/contexto-HU-XXX.md`, skill `investigacion-contexto`), el escenario lleva `@falta-info @FI-01` y el comentario `# FALTA INFORMACIÓN (FI-01): <qué falta>` arriba. Corre normalmente (salvo que también sea `@bloqueado`) y el reporte de k0lmena le agrega una nota visible; al publicar en Xray/QMetry/AIO, el comentario lo indica.
- Si la fuente no es una HU (ej. un contrato de API), usá un slug: `api/features/pets.feature` y tag `@contrato-pets`.

## Gherkin

- Keywords en **inglés** (`Feature`, `Background`, `Scenario`, `Scenario Outline`, `Examples`, `Given`, `When`, `Then`, `And`, `But`) y contenido en **español**, igual que el resto del repo.
- Un paso = una acción o una verificación observable. Los valores que cambian van entre comillas (`"Dinno"`) para que el step sea reutilizable.
- **Nunca** escribas credenciales en un `.feature`: usá un paso como `When el usuario inicia sesión con credenciales válidas` y que el step lea `process.env.APP_USER` / `APP_PASSWORD`.
- Un paso que **no se pudo verificar** contra la app real: dejalo escrito como dice el caso, marcá el escenario con `@bloqueado` y agregá un comentario `# BLOQUEADO: <motivo>` arriba. `npm test` nunca corre `@bloqueado`.

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

Steps: siempre iterar `pages` (k0lmena puede correr varios navegadores) y usar los helpers, que ya traen esperas y auto-healing.

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

La URL base sale de `BASEURL` (o `APP_URL` si está vacía) del `.env` de la raíz. En los steps usá rutas relativas a `BASEURL`, nunca la URL completa hardcodeada.

## API — solo features

`api/steps/comunes.steps.ts` ya trae steps genéricos. Los features de API se arman **solo con estos textos** (no escribas steps nuevos salvo que sea imposible expresar la validación):

```gherkin
Given el request usa el token de autenticación
Given el request no envía token de autenticación
Given el request usa el header "X-Tenant" con valor "demo"
When envío un GET a "/v2/pet/{petId}"
When envío un POST a "/v2/pet" con el body:
  """
  { "name": "Firulais", "status": "available" }
  """
When guardo el campo "id" de la respuesta como "petId"
Then el status de la respuesta es 200
Then la respuesta contiene el campo "category.name"
Then la respuesta no contiene el campo "password"
Then el campo "status" de la respuesta es "available"
Then el campo "id" de la respuesta es el número 10
Then el campo "tags" de la respuesta es de tipo "array"
Then la respuesta es una lista
Then la respuesta es una lista con al menos 1 elemento
Then la respuesta tiene los campos:
  | id     |
  | name   |
Then el header "content-type" de la respuesta contiene "application/json"
Then la respuesta llega en menos de 2000 ms
```

- `{nombre}` en endpoint, header o body se reemplaza por un valor guardado o, si no hay, por la variable de entorno del mismo nombre.
- Los campos usan notación de puntos (`data.items.0.id`).
- La URL base sale de `API_BASEURL` y el token de `API_TOKEN` (`.env` de la raíz).

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

`tools/bd/bd.steps.ts` está cargado en las suites web, API y mobile. Son steps **de solo lectura** que verifican lo que una prueba dejó guardado. Conexiones en el `.env` (`DB_CONEXIONES` + `DB_<NOMBRE>_*`); sin nombre se usa la primera. **Solo se agregan cuando la persona lo pide explícitamente** (*"sumá la verificación en la base"*, *"validá que quede guardado en la tabla X"*). Aunque un caso diga *"el dato se guarda en la base"*, no los agregues por tu cuenta: dejalo anotado como sugerencia en el reporte de mapeo (*"se puede sumar verificación en BD si se pide"*). Cuando se piden, mirá antes las tablas y columnas con `npm run bd -- esquema --tabla <tabla>`: no adivines nombres.

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

Se corre con `npm run perf -- <script> <perfil>` (`run-perf.js`). Perfiles: `smoke` (carga mínima, valida el script), `load`, `stress`, `soak`, `spike`. Cada corrida deja en `reports/performance/<k6|artillery|jmeter>/` el reporte HTML, un resumen JSON chico, el resultado crudo y el log; la consola muestra solo el resumen.

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
    smoke:  { phases: [{ name: smoke, duration: 30, arrivalCount: 5 }] }
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

Se parte de la plantilla `performance/jmeter/plantilla/plantilla.jmx` + `plantilla.json` (copiá las dos y renombralas `HU-001-<slug>`). Requiere Java 8+ y JMeter (`npm run bootstrap:jmeter`, queda en `tools/jmeter`; o `JMETER_HOME`).

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

- `destino`: el nombre de una variable del `.env` (`API_BASEURL`, `BASEURL`) o una URL. Llega al `.jmx` como `${__P(base_url)}`; cada request usa `${__P(base_url)}/path` en el campo *Path*.
- Cada clave del perfil llega como propiedad: `${__P(usuarios,1)}`, `${__P(rampa,1)}`, `${__P(duracion,30)}` en el Thread Group (con *scheduler* y loops `-1`). Se pueden sumar claves propias (ej. `pico`) y leerlas igual.
- Umbrales (todos en ms, salvo `error_pct` en %): `error_pct`, `p50`, `p90`, `p95`, `p99`, `avg`, `max`, y `por_muestra` con el nombre exacto del request. Los evalúa el reporte de k0lmena: JMeter no los conoce.
- Cada HTTP Request se nombra `MÉTODO /path` (es la "muestra" del reporte) y lleva una **Response Assertion** con el código esperado; sin aserción, un 404 cuenta como éxito.
- Credenciales: `${__groovy(System.getenv('API_TOKEN') ?: '')}` (o cualquier variable del `.env`); nunca escritas en el `.jmx`.
- Datos variables: `${__threadNum}` y `${__counter(FALSE,)}` para no repetir (ej. emails únicos).
- `--vus` y `--duracion` pisan `usuarios` y `duracion` en una corrida. Además del reporte de k0lmena, cada corrida deja el dashboard nativo de JMeter en `<corrida>-dashboard/index.html`.
- Si la persona trae un `.jmx` propio: adaptalo a estas convenciones (propiedades en el Thread Group, `base_url`, nombres `MÉTODO /path`, aserciones) en lugar de reescribirlo desde cero.

## Validar lo generado (una sola vez)

Desde `herramientas/k0lmena/` (PowerShell usa `$env:TAGS="@HU-001"; npm run test:web`):

```bash
TAGS=@HU-001 npm run test:web      # o test:api / test:mobile
```

- Si falla por un locator o un step mal armado, corregilo y volvé a correr. **Máximo 2 reintentos**; si sigue fallando, marcá el escenario `@bloqueado` con el motivo y seguí.
- Si falla porque la app no cumple lo esperado (un bug real), **no** cambies el `Then` para que pase: dejalo y reportalo como posible bug.
- No hace falta generar reportes HTML para validar: alcanza con el resumen de consola.

## Reporte de mapeo

Al terminar, guardá `output/mapeos/mapeo-<HU>-<tipo>.md` con una tabla (luego `python scripts/formatear_tablas.py <archivo>`):

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

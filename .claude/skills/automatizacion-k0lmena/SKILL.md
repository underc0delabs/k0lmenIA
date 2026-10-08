---
name: automatizacion-k0lmena
description: Convenciones para generar pruebas automatizadas en k0lmena (herramientas/k0lmena) — dónde va cada .feature, steps y locators de web, api y mobile, cómo nombrarlos y taggearlos, cómo reutilizar steps sin duplicar, qué helpers usar y cómo validar con npm; y los scripts de performance (k6 y Artillery). Úsalo al mapear casos de prueba a automatización (web-mapper, api-mapper, mobile-mapper, performance-mapper).
---

# Automatización con k0lmena

k0lmena vive en `herramientas/k0lmena/`. Los mappers **escriben código una vez**; después la suite corre sin agentes (y sin tokens) con `npm test`.

```
herramientas/k0lmena/
├── web/      features/  steps/  locators/   (Playwright + Cucumber; hooks/, utils/ ya existen)
├── api/      features/  steps/              (axios + Cucumber; steps/comunes.steps.ts ya existe)
├── mobile/   features/  steps/  locators/   (WebdriverIO + Appium; support/ ya existe; apps/ = .apk/.ipa)
├── performance/  k6/http/  artillery/       (k6 y Artillery; lo genera el performance-mapper)
├── cucumber.js  run-tests.js  env.js      (env.js carga el .env ÚNICO de la raíz del repo)
```

## Nombres y trazabilidad

| Archivo  | Nombre                                    |
| -------- | ----------------------------------------- |
| Feature  | `<tipo>/features/HU-001-<slug>.feature`   |
| Steps    | `<tipo>/steps/HU-001.steps.ts`            |
| Locators | `<tipo>/locators/HU-001.locators.ts`      |

- Tags del `Feature`: `@HU-001` y el tipo (`@web`, `@api` o `@mobile`).
- Tags de cada `Scenario`: el ID del caso de origen (`@CP-001`, `@CP-API-001`) y, si es crítico, `@Smoke`.
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

## Performance — k6 y Artillery

Se corre con `npm run perf -- <script> <perfil>` (`run-perf.js`). Perfiles: `smoke` (carga mínima, valida el script), `load`, `stress`, `soak`, `spike`. Cada corrida deja en `reports/performance/<k6|artillery>/` el reporte HTML, un resumen JSON chico, el resultado crudo y el log; la consola muestra solo el resumen.

| Herramienta           | Cuándo                                               | Archivos                                                                 |
| --------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------ |
| k6                    | APIs / HTTP (escala a miles de usuarios)             | `performance/k6/http/HU-001-<slug>.ts`                                   |
| Artillery + Playwright | Flujos de navegador (pocos usuarios: cada uno es un Chromium) | `performance/artillery/HU-001-<slug>.yaml` + `HU-001-<slug>.ts` (processor) |

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

| Caso   | Paso del caso                 | Paso automatizado                       | Estado      | Nota                                  |
| ------ | ----------------------------- | --------------------------------------- | ----------- | ------------------------------------- |
| CP-001 | Ingresar el email             | el usuario completa el email "..."      | Mapeado     |                                       |
| CP-001 | Click en "Enviar"             | el usuario clickea el botón Registrar   | Ajustado    | El botón se llama "Registrar"         |
| CP-002 | Ver mensaje de bienvenida     | -                                       | Bloqueado   | No aparece ningún mensaje; posible bug |

Estados: `Mapeado` (igual al caso), `Ajustado` (el caso decía otra cosa y se corrigió según la app), `Bloqueado` (no se pudo ejecutar). Cerrá con los archivos generados, el resultado de la validación y el comando para correrlo.

## Ahorro de tokens

- No leas los utils, hooks ni `comunes.steps.ts` completos: las firmas están acá.
- No vuelvas a navegar ni a llamar un endpoint que ya verificaste.
- Respuesta final corta: archivos generados, resultado de la validación, bloqueados y el comando `npm`.

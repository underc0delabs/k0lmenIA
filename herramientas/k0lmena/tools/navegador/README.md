# Navegador y protección anti-bots

Muchas apps tienen una protección anti-bots: Cloudflare, Akamai, DataDome, HUMAN (PerimeterX), Imperva, AWS WAF o un captcha. Esa protección no distingue entre un bot malicioso y nuestras pruebas automatizadas, así que frena a Playwright, a `npm test`, a las herramientas de k0lmena y al navegador de los agentes.

Esta guía tiene dos partes: **qué hace k0lmenIA** y **qué le pedimos al equipo dueño de la app**. Esa segunda parte se puede reenviar tal cual.

## Qué hace k0lmenIA

- **Detecta el bloqueo en vez de reportar un falso fallo.** Si la app responde con una página de desafío o de acceso denegado, el escenario de `npm test` queda **Bloqueado: anti-bots**. Lo mismo pasa al publicarlo en Xray, QMetry, AIO o Zephyr: no queda como Fallido. El análisis de fallos lo agrupa en su propia categoría. Las herramientas (`explorar`, `accesibilidad`, `mapa-funcional`…) muestran un aviso al terminar.
- **Manda el header de bypass** que acordemos con el equipo, solo a los hosts de la app. Nunca lo manda a analytics, CDNs ni otros terceros.
- **Puede usar el Chrome o el Edge instalados** (`NAVEGADOR_CANAL`) en lugar del Chromium de Playwright, y agregar pausas entre acciones (`RITMO_HUMANO`).
- **Plan B manual:** `npm run login` abre tu Chrome con ventana. Resolvés el desafío o el captcha a mano y la sesión queda guardada para las corridas (`SESION=si`).

**Lo que no hace:** no disfraza el navegador para engañar al detector y no resuelve captchas automáticamente. Los plugins "stealth" contra un anti-bots serio duran poco, fallan de forma intermitente (los resultados dejan de ser confiables) y pueden violar los términos del proveedor. La salida estable es la excepción oficial.

```
+---------------------+-----------------------------------------------------------+
| Variable (.env)     | Para qué                                                  |
+=====================+===========================================================+
| NAVEGADOR_CANAL     | chrome o msedge: usa el navegador instalado               |
+---------------------+-----------------------------------------------------------+
| RITMO_HUMANO        | si (250 ms) o los milisegundos entre acciones             |
+---------------------+-----------------------------------------------------------+
| QA_BYPASS_HEADER    | nombre del header acordado (ej. X-QA-Bypass)              |
+---------------------+-----------------------------------------------------------+
| QA_BYPASS_TOKEN     | su valor secreto (solo en el .env, nunca versionado)      |
+---------------------+-----------------------------------------------------------+
| QA_BYPASS_HOSTS     | hosts que reciben el header (por defecto, el de APP_URL   |
|                     | y sus subdominios)                                        |
+---------------------+-----------------------------------------------------------+
```

Lo usan `npm test`, todas las herramientas de k0lmena y el conector Playwright de los agentes. Al conector hay que reiniciarlo (reiniciando Claude Code) para que tome los cambios. `npm run doctor` revisa que la configuración esté completa. La única excepción es Lighthouse (`npm run rendimiento`): no puede limitar el header a la app, así que mide sin él. Si la app lo frena, la salida es la lista blanca de IP.

## Qué le pedimos al equipo de la app

Necesitamos que el tráfico de pruebas pase la protección, **solo en el ambiente de QA o staging**. Cualquiera de estas opciones sirve, de la más simple a la más acotada:

### 1. Un ambiente de QA sin protección anti-bots (o en modo de prueba)

Es lo más simple si el ambiente de QA no está expuesto al público.

### 2. Header secreto (recomendado si el ambiente está expuesto)

Las pruebas mandan `X-QA-Bypass: <token>` (el nombre lo eligen ustedes) y una regla del WAF o del anti-bots deja pasar esos requests. Sirve también desde CI, donde las IPs cambian.

- **Token**: largo y aleatorio (por ejemplo, `openssl rand -hex 32`). Se rota cada tanto y se comparte por un canal seguro, nunca por chat ni en un ticket.
- **Cloudflare**: una regla personalizada del WAF (*Security > WAF > Custom rules*) con la condición *header `x-qa-bypass` igual al token* y la acción **Skip**, que saltea las reglas administradas, Super Bot Fight Mode y rate limiting. Ojo: **Bot Fight Mode** (el gratuito) no se puede saltear con reglas. Si lo usan, conviene la lista blanca de IP o desactivarlo en QA.
- **AWS WAF**: una regla con prioridad más alta que *match* el header y aplica **Allow**, o un *scope-down statement* en Bot Control que excluya esos requests.
- **Akamai (Bot Manager)**: una excepción por header en la política de Bot Manager, o una *Network List* con las IPs de QA.
- **DataDome / HUMAN / Imperva**: una regla de *allow* por header o por IP en su consola.

### 3. Lista blanca de IPs

Sirve para las IPs fijas de la oficina, la VPN o los runners de CI propios. No sirve con los runners hospedados de GitHub o GitLab, que cambian de IP.

### 4. Claves de prueba del captcha (en QA o staging, nunca en producción)

Los proveedores publican claves que siempre aprueban, pensadas justamente para pruebas automatizadas:

```
+-----------------------+--------------------------------------------+---------------------------------------------+
| Proveedor             | Site key de prueba                         | Secret de prueba                            |
+=======================+============================================+=============================================+
| reCAPTCHA v2          | 6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI   | 6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe    |
+-----------------------+--------------------------------------------+---------------------------------------------+
| Cloudflare Turnstile  | 1x00000000000000000000AA                   | 1x0000000000000000000000000000000AA         |
+-----------------------+--------------------------------------------+---------------------------------------------+
| hCaptcha              | 10000000-ffff-ffff-ffff-000000000001       | 0x0000000000000000000000000000000000000000  |
+-----------------------+--------------------------------------------+---------------------------------------------+
```

reCAPTCHA v3 no tiene clave de prueba: en QA se usa una clave aparte con umbral bajo, o la validación se saltea cuando viene el header de bypass.

## Mientras tanto: el plan B manual

1. `npm run login` abre tu Google Chrome con ventana. Resolvés el desafío o el captcha y te logueás.
2. Con `SESION=si` en el `.env`, `npm test` y el navegador de los agentes usan esa sesión.
3. Las cookies anti-bots (`cf_clearance`, `datadome`, `_abck`…) duran poco y valen solo para el **mismo navegador e IP**. Corré las pruebas con `NAVEGADOR_CANAL=chrome`, desde la misma red. Si vencen, se repite el login.

Sirve para destrabar una sesión de trabajo, no para CI ni para corridas largas. Para eso está la excepción del punto anterior.

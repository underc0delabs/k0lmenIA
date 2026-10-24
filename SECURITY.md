# Seguridad

## Alcance

k0lmenIA es un conjunto de herramientas de **QA que corren en local o en CI** (Playwright, Cucumber, WebdriverIO, Appium, k6/Artillery/JMeter, OWASP ZAP). **No es un servicio expuesto a internet** que procese entradas de terceros: los insumos (historias, URLs a probar, colecciones, configs) son del propio equipo.

Secretos (tokens, credenciales, cadenas de conexión) van **solo** en el `.env` local (gitignored) o en variables de entorno, nunca commiteados. Hay una plantilla en `.env.example`.

El agente `analista-seguridad` escanea **solo** las URLs de `SEGURIDAD_URLS_AUTORIZADAS` y en modo pasivo; el `pentester-web` hace escaneo activo solo con `PENTEST_AUTORIZADO=si`, sobre un sitio propio o con autorización escrita, y nunca contra producción sin permiso.

## Vulnerabilidades conocidas en dependencias (riesgo aceptado)

`npm audit` sobre `herramientas/k0lmena` reporta, al **2026-10-18**, 39 vulnerabilidades **transitivas** en dependencias de **herramientas de desarrollo/test** (artillery, appium, webdriverio, lighthouse, percy, puppeteer). Se aplicó el `npm audit fix` seguro (sin `--force`); el resto **no se corrige** porque el "arreglo" que propone npm rompe el framework:

| Advisory (paquete) | Severidad | "Fix" de npm | Por qué no se aplica |
|---|---|---|---|
| `shell-quote` | crítica | `appium@3.4.2` | Downgrade de appium → rompe la suite mobile |
| `braces`, `csv-parse`, `sprintf-js` | alta / moderada | `artillery@0.0.2` | Downgrade a un stub vacío → rompe performance |
| `basic-ftp`, `extract-zip` | alta | `webdriverio@10.0.2` | Salto a WebdriverIO 10 (ver abajo) |

**Por qué el riesgo es bajo en este contexto:** son casi todas DoS por entrada maliciosa (ReDoS en el parser FTP de `basic-ftp`, patrones anidados en `braces`, `csv-parse`, `sprintf-js`) o inyección en `shell-quote`. Explotarlas requiere que un atacante controle esa entrada específica (un listado FTP, un patrón glob, un CSV, un token de shell); en el uso normal de k0lmena esas entradas son del equipo, no de terceros, y nada corre como servicio público.

**No usar `npm audit fix --force`:** degrada artillery y appium a versiones inservibles.

## Cómo se resolverán (sin romper nada)

Cuando el ecosistema upstream publique los parches:

- **WebdriverIO 10** — cuando `@wdio/browserstack-service` publique su versión 10 (hoy no existe), se sube todo el stack `@wdio/*` + `webdriverio` a 10: limpia `basic-ftp` y `extract-zip`.
- **artillery** con release parcheada → limpia `braces`, `csv-parse`, `sprintf-js`.
- **appium** con `shell-quote` parcheado → limpia la crítica.
- **TypeScript 7** — se sube cuando `ts-node` lo soporte (hoy TS 7, la reescritura nativa, rompe `ts-node`, del que depende todo el framework).

**Próxima revisión: 2026-11-18.** Volver a correr `cd herramientas/k0lmena && npm audit` y aplicar lo que ya tenga parche compatible; subir los majors (WDIO 10, TS 7) solo cuando sus dependencias acompañen.

## Reportar un problema

Si encontrás un problema de seguridad en este repositorio, escribí a **info@underc0de.org** en vez de abrir un issue público.

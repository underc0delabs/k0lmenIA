# Newman (Postman CLI)

**Newman** es el ejecutor de colecciones de **Postman** por línea de comandos. Corre una colección `.json` (los requests + sus validaciones) contra una API real y reporta qué pasó. Es la herramienta que usa el agente [`ejecutor-api`](../../.claude/agents/ejecutor-api.md) para **ejecutar pruebas de API**.

> Fue la primera herramienta de `herramientas/`. Las demás siguen el mismo patrón: una subcarpeta + su README.

## Instalación (una vez)

Requiere **Node.js**. Se instala global con npm:

```bash
npm install -g newman
```

Verificá:
```bash
newman --version
```

## Cómo se usa en este repo

El agente corre una **colección de Postman** y arma el mismo reporte HTML oscuro que las pruebas E2E, con un solo comando (igual en PowerShell, bash y zsh; en Mac/Linux, `python3`):

```bash
python scripts/correr_newman.py input/api/demo.postman_collection.json --historia HU-001
```

El script corre Newman (instalado o con `npx`), toma `API_TOKEN` del `.env`; la URL (`{{base_url}}`) sale de `--base-url`, del environment o de la colección, y solo si ninguno la define, de `API_BASEURL` del `.env`; convierte el resultado (`scripts/newman_a_resultados.py`) y genera el reporte (`scripts/generar_reporte.py`) en `output/ejecuciones/reporte-HU-001-<fecha-hora>.html`. Opciones: `--carpeta`, `--environment`, `--base-url` y `--titulo`. El agente `ejecutor-api` lo usa solo; normalmente no lo corrés a mano.

## Bruno, Insomnia y GraphQL

- **Bruno**: pasale la carpeta de la colección (la que tiene `bruno.json`) en lugar del `.json`:
  `python scripts/correr_newman.py input/api/demo-bruno --environment JSONPlaceholder`.
- **Insomnia**: pasale el export (v4 `.json` o v5 `.yaml`; el v5 necesita `pip install pyyaml`):
  `python scripts/correr_newman.py input/api/demo.insomnia.json --environment JSONPlaceholder`.
- Las dos se convierten antes a Postman con `scripts/convertir_coleccion.py` (en una carpeta temporal) y el
  script muestra las **advertencias** de lo que no tiene equivalente en Postman (template tags de Insomnia,
  OAuth2, archivos en multipart, `bru.runRequest`, …). `--environment` es el **nombre** del environment.
  Para ver la conversión: `python scripts/convertir_coleccion.py <origen> --salida <carpeta>`.
- **GraphQL**: los requests GraphQL (modo GraphQL de Postman, `body:graphql` de Bruno, `application/graphql`
  de Insomnia) corren igual; el reporte suma la operación al título. Validá `data` y `errors`, no solo el status:
  un error de GraphQL suele volver con 200. Ejemplo: `input/api/demo-graphql.postman_collection.json`.

## Dónde van las colecciones

- Las **colecciones** y **environments** van en `input/api/`. Hay ejemplos que apuntan a APIs públicas de demo: `demo.postman_collection.json` + `demo.postman_environment.json` (Postman), `demo-bruno/` (Bruno), `demo.insomnia.json` (Insomnia) y `demo-graphql.postman_collection.json` (GraphQL). Exportá las tuyas y dejalas ahí.
- El **id** y la **prioridad** de cada caso se codifican (opcional) en el **nombre del request** en Postman: `CP-API-001 — Crear post (Alta)`; si depende de un dato que falta, sumale su ID: `CP-API-003 — Crear usuario [FI-01]`. El conversor los usa para el reporte. Si no los ponés, el id se autonumera y la prioridad queda vacía.

## Credenciales / token

Los secretos **no van en la colección ni en el environment** (se commitean). Si tu API pide token:

1. Guardá el token en el `.env` (gitignored) — ej. `API_TOKEN=...` (mirá `.env.example`).
2. En la colección, usá la variable en el header: `Authorization: Bearer {{token}}`.
3. `scripts/correr_newman.py` se la pasa a Newman: no hace falta cargar el `.env` en la shell (que es lo que hacía fallar `--env-var "token=$API_TOKEN"` en PowerShell, donde la sintaxis es otra).

Así el token nunca queda en un archivo versionado. Para el `base_url` (que no es secreto) sí podés usar el environment.

## Reporte HTML nativo de Newman (opcional)

Si en vez del reporte del repo querés el reporte propio de Newman, instalá el reporter `htmlextra` y usalo con `-r htmlextra`:
```bash
npm install -g newman-reporter-htmlextra
newman run <coleccion> -r htmlextra
```
Por defecto usamos el reporte del repo para que las ejecuciones de API y E2E se vean igual.

## El detalle

El "cómo" completo (armar la colección, validaciones, datos variables, interpretar resultados) está en el skill [`ejecucion-api`](../../.claude/skills/ejecucion-api/SKILL.md).

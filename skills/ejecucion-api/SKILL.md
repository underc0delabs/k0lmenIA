---
name: ejecucion-api
description: El cómo de ejecutar pruebas de API con Newman — correr una colección Postman/Bruno/Insomnia (REST o GraphQL), manejar base_url y token e interpretar resultados. Lo usa el ejecutor-api.
---

# Ejecución de API con Newman

El "cómo" para ejecutar pruebas de API de forma confiable corriendo una **colección de Postman** con **Newman**. La herramienta vive en `${CLAUDE_PLUGIN_ROOT}/herramientas/newman/` (ahí está la instalación).

## La idea

Una **colección de Postman** (`.json`) describe los requests y sus **validaciones** (los `pm.test(...)`). **Newman** la corre contra una API real. En este repo, el resultado se convierte y se muestra en el **mismo reporte HTML oscuro** que las pruebas E2E. Pipeline:

```
colección .json → newman run (JSON) → newman_a_resultados.py → generar_reporte.py → reporte .html
```

## De dónde sale la colección

- **La trae la persona**: exportada de Postman, guardada en `input/api/`. Es lo más común si ya viven en Postman.
- **Viene de Bruno o Insomnia**: la carpeta de Bruno (con `bruno.json`) o el export de Insomnia (v4 `.json` / v5 `.yaml`) se le pasan directo a `correr_newman.py`, que los convierte a Postman con `${CLAUDE_PLUGIN_ROOT}/scripts/convertir_coleccion.py` (ver *Bruno e Insomnia* abajo).
- **La armás vos** a partir de un contrato o de casos de API escritos a mano: generás el `.json` de la colección (requests + `pm.test` con las validaciones) y después la corrés.

## Validaciones (lo que decide pasó/falló)

Cada request lleva sus asserts en el bloque *Tests* de Postman, con `pm.test` + `pm.expect`:

```javascript
pm.test("El status es 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Devuelve un id", function () {
    pm.expect(pm.response.json()).to.have.property("id");
});
```

Validá lo que importa: **status code**, **campos clave** del cuerpo, y si hace falta el **esquema** o un **valor puntual**. El estado del caso lo decide Newman, no el criterio del modelo. Un request **sin ningún `pm.test`** sale **Bloqueado** ("Sin validaciones"), nunca Aprobado.

## base_url y token

- **`base_url`** (no es secreto): va en el **environment** (`input/api/*.postman_environment.json`) o como variable de la colección. En los requests se usa `{{base_url}}/loquesea`.
- **Token / credenciales** (secreto): **nunca** en la colección ni en el environment. Va en el `.env` (gitignored) y se pasa al correr:
  ```bash
  k0lmenia py scripts/correr_newman.py <coleccion> --historia HU-001   # token del .env; base_url de --base-url, del environment/colección o, si no la definen, de API_BASEURL
  ```
  En la colección, el header usa la variable: `Authorization: Bearer {{token}}`. Usá un entorno de prueba, no producción.

## Bruno e Insomnia

`${CLAUDE_PLUGIN_ROOT}/scripts/convertir_coleccion.py` los pasa a Postman v2.1 (`correr_newman.py` lo hace solo; a mano: `k0lmenia py scripts/convertir_coleccion.py <origen> --salida <carpeta> [--environment <nombre>]`):

```
+-------------------------------------+---------------------------------------+------------------------------------+
| Origen                              | Se convierte                          | Cómo                               |
+=====================================+=======================================+====================================+
| Bruno `.bru`                        | requests, carpetas (orden por `seq`), | igual                              |
|                                     | headers, query y path params, auth    |                                    |
|                                     | bearer/basic/API key, bodies JSON,    |                                    |
|                                     | texto, XML, form, multipart y GraphQL |                                    |
+-------------------------------------+---------------------------------------+------------------------------------+
| Bruno `assert`                      | `res.status: eq 200`, `res.body.id:   | un `pm.test` por línea             |
|                                     | isDefined`, …                         |                                    |
+-------------------------------------+---------------------------------------+------------------------------------+
| Bruno `tests`, `script:*`, `vars:*` | el JS de Bruno (`res`, `req`, `bru`,  | con un adaptador sobre `pm`        |
|                                     | `test`, `expect`)                     |                                    |
+-------------------------------------+---------------------------------------+------------------------------------+
| Bruno `environments/*.bru`          | `vars` (y `vars:secret` vacías)       | environment de Postman             |
+-------------------------------------+---------------------------------------+------------------------------------+
| Insomnia v4 / v5                    | requests, carpetas, headers, params,  | su `insomnia.*` es el mismo `pm.*` |
|                                     | auth, bodies (GraphQL incluido),      |                                    |
|                                     | `preRequestScript` y                  |                                    |
|                                     | `afterResponseScript`                 |                                    |
+-------------------------------------+---------------------------------------+------------------------------------+
| Insomnia environments               | base + el sub-environment elegido     | environment de Postman             |
|                                     | (`--environment`)                     |                                    |
+-------------------------------------+---------------------------------------+------------------------------------+
```

Variables: `{{ _.base_url }}` (Insomnia) y `{{base_url}}` (Bruno) quedan como `{{base_url}}`. Lo que no tiene equivalente (template tags `{% response ... %}` de Insomnia, OAuth2/AWS/Digest, archivos en multipart, `bru.runRequest`, unit tests de Insomnia, scripts de carpeta o de colección de Bruno) **se lista como advertencia**: decíselo a la persona junto con el resultado. Las variables secretas de Bruno quedan vacías: el token sale de `API_TOKEN` (`{{token}}`).

## GraphQL

Newman corre los requests GraphQL igual que los REST (modo **GraphQL** de Postman: `query` + `variables`). Lo que cambia es **qué validar**: un error de GraphQL suele volver con **status 200** y la lista `errors`, así que con validar solo el status no alcanza.

```javascript
pm.test("No devuelve errores", function () {
    pm.expect(pm.response.json().errors).to.be.undefined;
});
pm.test("Devuelve el país", function () {
    pm.expect(pm.response.json().data.country.name).to.eql("Argentina");
});
// Caso negativo: el error esperado
pm.test("Rechaza el campo inexistente", function () {
    pm.expect(pm.response.json().errors[0].message).to.include("campoQueNoExiste");
});
```

- Los valores dinámicos van en las **variables** (`{"code": "{{codigo}}"}`), no concatenados en la query.
- Las **mutations** modifican datos: confirmalas como cualquier método con efecto.
- En el reporte, el título del caso suma la operación (`[GraphQL query Pais]`), sacada de la query.
- Para conocer el schema sin leerlo entero: `k0lmenia py scripts/resumir_graphql.py <url o archivo .graphql>`.
- Ejemplo trabajado: `input/api/demo-graphql.postman_collection.json` (contra https://countries.trevorblades.com).

## Id y prioridad en el reporte

El conversor saca el **id** y la **prioridad** del **nombre del request** en Postman (ambos opcionales):

```
API-001 — Crear un post (Alta)
└─id──┘   └───título────┘ └prio┘
```

- id: prefijo tipo `API-001` / `CP-API-001` seguido de `—`, `-`, `:` o `·`.
- prioridad: `Crítica | Alta | Media | Baja`, entre paréntesis al final.

Si no los ponés, el id se autonumera (`API-001`, `API-002`…) y la prioridad queda vacía (las barras por prioridad simplemente no aparecen).

## Cómo se interpretan los estados

El conversor (`${CLAUDE_PLUGIN_ROOT}/scripts/newman_a_resultados.py`) traduce la salida de Newman a:

- **Aprobado** — el request se hizo, tiene asserts y **ninguno** falló.
- **Fallido** — algún `pm.test` falló (el motivo es el primer assert que falló, ej. *"El status es 200: expected 200 but got 404"*).
- **Bloqueado** — el request **no se pudo hacer** (error de conexión, host caído, etc.) o **no tiene ningún `pm.test`** (motivo *"Sin validaciones (pm.test)"*: sin asserts no hay nada verificado).

## Velocidad y permisos

- Newman corre por **Bash**. La primera vez, Claude Code puede pedir permiso para ejecutar `newman`: elegí *Always allow* (o ya viene pre-aprobado en `.claude/settings.json`).
- Una colección puntual corre rápido. Si tenés muchas, corré **solo la carpeta** que pide la persona, no todo.
- **Datos variables** (data-driven): `correr_newman.py ... --datos datos.csv` (el `-d` de Newman) itera la colección con cada fila; cada iteración es una fila en el reporte.

## Prerrequisitos

- **Newman** instalado: `npm install -g newman` (requiere Node.js). Detalle en `${CLAUDE_PLUGIN_ROOT}/herramientas/newman/README.md`.
- La **API accesible** (URL pública o localhost).

El detalle de comandos, reporters y un ejemplo trabajado están en [`references/newman.md`](references/newman.md).

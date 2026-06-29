---
name: ejecucion-api
description: Cómo ejecutar pruebas de API con Newman (la CLI de Postman) — correr una colección de Postman contra una API real, escribir validaciones, manejar base_url y token, e interpretar los resultados para el reporte. Úsalo al ejecutar, correr o automatizar pruebas de API.
---

# Ejecución de API con Newman

El "cómo" para ejecutar pruebas de API de forma confiable corriendo una **colección de Postman** con **Newman**. La herramienta vive en `herramientas/newman/` (ahí está la instalación).

## La idea

Una **colección de Postman** (`.json`) describe los requests y sus **validaciones** (los `pm.test(...)`). **Newman** la corre contra una API real. En este repo, el resultado se convierte y se muestra en el **mismo reporte HTML oscuro** que las pruebas E2E. Pipeline:

```
colección .json → newman run (JSON) → newman_a_resultados.py → generar_reporte.py → reporte .html
```

## De dónde sale la colección

- **La trae la persona**: exportada de Postman, guardada en `input/api/`. Es lo más común si ya viven en Postman.
- **La armás vos** a partir de un contrato o de los casos de `generador-casos-api`: generás el `.json` de la colección (requests + `pm.test` con las validaciones) y después la corrés.

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

Validá lo que importa: **status code**, **campos clave** del cuerpo, y si hace falta el **esquema** o un **valor puntual**. El estado del caso lo decide Newman, no el criterio del modelo.

## base_url y token

- **`base_url`** (no es secreto): va en el **environment** (`input/api/*.postman_environment.json`) o como variable de la colección. En los requests se usa `{{base_url}}/loquesea`.
- **Token / credenciales** (secreto): **nunca** en la colección ni en el environment. Va en el `.env` (gitignored) y se pasa al correr:
  ```bash
  newman run <coleccion> --env-var "token=$API_TOKEN"
  ```
  En la colección, el header usa la variable: `Authorization: Bearer {{token}}`. Usá un entorno de prueba, no producción.

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

El conversor (`scripts/newman_a_resultados.py`) traduce la salida de Newman a:

- **Aprobado** — el request se hizo y **ningún** assert falló.
- **Fallido** — algún `pm.test` falló (el motivo es el primer assert que falló, ej. *"El status es 200: expected 200 but got 404"*).
- **Bloqueado** — el request **no se pudo hacer** (error de conexión, host caído, etc.).

## Velocidad y permisos

- Newman corre por **Bash**. La primera vez, Claude Code puede pedir permiso para ejecutar `newman`: elegí *Always allow* (o ya viene pre-aprobado en `.claude/settings.json`).
- Una colección puntual corre rápido. Si tenés muchas, corré **solo la carpeta** que pide la persona, no todo.
- **Datos variables** (data-driven): Newman acepta `-d datos.csv` para iterar el mismo request con varios sets; cada iteración es una fila en el reporte.

## Prerrequisitos

- **Newman** instalado: `npm install -g newman` (requiere Node.js). Detalle en `herramientas/newman/README.md`.
- La **API accesible** (URL pública o localhost).

El detalle de comandos, reporters y un ejemplo trabajado están en [`references/newman.md`](references/newman.md).

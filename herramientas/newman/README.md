# Newman (Postman CLI)

**Newman** es el ejecutor de colecciones de **Postman** por línea de comandos. Corre una colección `.json` (los requests + sus validaciones) contra una API real y reporta qué pasó. Es la herramienta que usa el agente [`ejecutor-api`](../../.claude/agents/ejecutor-api.md) para **ejecutar pruebas de API**.

> Es la primera herramienta "real" de `herramientas/`. El patrón es el mismo para las que vengan (k6, JMeter…): una subcarpeta + este README.

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

El agente corre una **colección de Postman** y arma el mismo reporte HTML oscuro que las pruebas E2E. El flujo son tres pasos:

```bash
# 1) Newman corre la colección y exporta el resultado en JSON
newman run input/api/demo.postman_collection.json \
  -e input/api/demo.postman_environment.json \
  -r cli,json --reporter-json-export output/ejecuciones/_newman-<fecha-hora>.json

# 2) Se convierte ese JSON al formato del reporte del repo
python scripts/newman_a_resultados.py \
  output/ejecuciones/_newman-<fecha-hora>.json \
  output/ejecuciones/_resultados-API-<fecha-hora>.json "Demo API k0lmena"

# 3) Se genera el reporte HTML (dashboard, modo oscuro)
python scripts/generar_reporte.py \
  output/ejecuciones/_resultados-API-<fecha-hora>.json \
  output/ejecuciones/reporte-API-<fecha-hora>.html
```

El agente `ejecutor-api` hace estos tres pasos solo; normalmente no los corrés a mano.

## Dónde van las colecciones

- Las **colecciones** y **environments** de Postman van en `input/api/` (hay un ejemplo: `demo.postman_collection.json` + `demo.postman_environment.json`, que apuntan a una API pública de demo). Exportá las tuyas desde Postman y dejalas ahí.
- El **id** y la **prioridad** de cada caso se codifican (opcional) en el **nombre del request** en Postman: `API-001 — Crear post (Alta)`. El conversor los usa para el reporte. Si no los ponés, el id se autonumera y la prioridad queda vacía.

## Credenciales / token

Los secretos **no van en la colección ni en el environment** (se commitean). Si tu API pide token:

1. Guardá el token en el `.env` (gitignored) — ej. `API_TOKEN=...` (mirá `.env.example`).
2. En la colección, usá la variable en el header: `Authorization: Bearer {{token}}`.
3. Pasásela a Newman desde el entorno al correr:
   ```bash
   newman run <coleccion> --env-var "token=$API_TOKEN"
   ```

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

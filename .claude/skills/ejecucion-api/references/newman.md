# Newman — referencia

Detalle de comandos y un ejemplo trabajado. Lo conceptual está en el `SKILL.md`; la instalación, en `herramientas/newman/README.md`.

## Comandos base

```bash
# Correr una colección
newman run coleccion.json

# Con environment (define base_url y otras variables no secretas)
newman run coleccion.json -e environment.json

# Pasar un secreto desde tu entorno (no queda en ningún archivo)
newman run coleccion.json --env-var "token=$API_TOKEN"

# Reporters: consola + JSON exportado a un archivo
newman run coleccion.json -r cli,json --reporter-json-export salida.json

# Datos variables (una corrida por fila del CSV/JSON)
newman run coleccion.json -d datos.csv

# Sin global: con npx (más lento por corrida)
npx newman run coleccion.json
```

Flags útiles:
- `--folder "<nombre>"` → corre solo una carpeta de la colección (para ejecutar un subconjunto).
- `--timeout-request <ms>` → corta requests colgados.
- `--bail` → frena en el primer fallo.
- `--suppress-exit-code` → no devuelve código de error (útil si un script no debe frenar por un fallo).

## El pipeline completo del repo

```bash
FECHA=$(date +%Y%m%d-%H%M)

# 1) Newman → JSON
newman run input/api/demo.postman_collection.json \
  -e input/api/demo.postman_environment.json \
  -r cli,json --reporter-json-export output/ejecuciones/_newman-$FECHA.json

# 2) JSON de Newman → formato del reporte
python scripts/newman_a_resultados.py \
  output/ejecuciones/_newman-$FECHA.json \
  output/ejecuciones/_resultados-API-$FECHA.json "Demo API k0lmena"

# 3) → reporte HTML (dashboard oscuro)
python scripts/generar_reporte.py \
  output/ejecuciones/_resultados-API-$FECHA.json \
  output/ejecuciones/reporte-API-$FECHA.html
```

## Anatomía de una colección (v2.1)

Cada request vive en `item[]` con su `request` (método, headers, url, body) y sus validaciones en un `event` de tipo `test`:

```json
{
  "name": "API-001 — Obtener un post existente (Alta)",
  "request": {
    "method": "GET",
    "url": { "raw": "{{base_url}}/posts/1", "host": ["{{base_url}}"], "path": ["posts", "1"] }
  },
  "event": [
    { "listen": "test", "script": { "exec": [
      "pm.test('El status es 200', function () { pm.response.to.have.status(200); });"
    ] } }
  ]
}
```

> El nombre `API-001 — … (Alta)` no es decorativo: el conversor saca de ahí el **id** y la **prioridad** para el reporte.

## Validaciones frecuentes

```javascript
// Status
pm.response.to.have.status(200);

// Cuerpo: propiedad y valor
var data = pm.response.json();
pm.expect(data).to.have.property("id");
pm.expect(data.title).to.eql("k0lmena");

// Tiempo de respuesta
pm.expect(pm.response.responseTime).to.be.below(800);

// Header
pm.response.to.have.header("Content-Type");

// Guardar un valor para el request siguiente (ej. token de login)
var token = pm.response.json().token;
pm.environment.set("token", token);
```

## Cómo el conversor mapea el resultado

`scripts/newman_a_resultados.py` lee la salida de Newman y arma el JSON del reporte:

| Situación en Newman | Estado en el reporte | Motivo |
|---|---|---|
| Request OK, sin asserts fallidos | **Aprobado** | — |
| Algún `pm.test` falló | **Fallido** | el primer assert que falló |
| El request no se pudo hacer | **Bloqueado** | el error de conexión |

El **título** del reporte sale del nombre de la colección (o del que le pases como 3.º argumento). El **base_url** se toma del environment/colección para mostrarlo en el reporte. La **fecha** sale del momento real de la corrida.

## Ejemplo trabajado

La colección de demo `input/api/demo.postman_collection.json` tiene tres casos contra una API pública (JSONPlaceholder): obtener un post (espera 200 + campos), crear un post (espera 201 + id) y pedir uno inexistente (espera 404). Corriendo el pipeline de arriba, los tres dan **Aprobado** y el reporte muestra el 100%. Cambiá `base_url` por tu API y reemplazá la colección por la tuya para probar contra tu servicio.

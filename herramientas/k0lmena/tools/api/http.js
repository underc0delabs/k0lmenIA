// Ayudas de los steps de API (api/steps/comunes.steps.ts), en JS puro para poder probarlas sin
// instalar k0lmena (tests/node/api-http.test.js).
//
//   unirUrl(base, ruta)         → base + ruta con una sola barra en el medio (la base incluye el
//                                  server o basePath de la spec: https://petstore.swagger.io/v2).
//   variablesSinValor(texto)    → las {variables} que quedaron sin reemplazar (para cortar con un
//                                  mensaje claro en vez de mandar "/pet/{petId}" literal y ver un 404).
//   parsearJson(texto, que)     → JSON.parse con un error que dice qué JSON estaba mal y dónde.
//   parsearRespuesta(texto)     → el body de la respuesta: JSON (con los enteros grandes como texto,
//                                  para no perder precisión en ids int64) o el texto tal cual.
//   ocultarHeaders(headers)     → los headers con las credenciales tapadas (para el reporte).
//   tipoDe(valor, esperado)     → { ok, real }: acepta los tipos de JSON Schema / OpenAPI (integer,
//                                  number, string, boolean, array, object, null) y sus nombres en español.

/** base + ruta sin barras de más ni de menos. Una ruta que ya es una URL completa queda igual. */
function unirUrl(base, ruta) {
  const r = String(ruta ?? '');
  if (/^https?:\/\//i.test(r)) return r;
  const b = String(base ?? '').trim();
  if (!b) throw new Error(`No hay URL base para "${r}": definí API_BASEURL en el .env de la raíz (con el server o basePath de la spec, ej. https://petstore.swagger.io/v2).`);
  if (!r) return b;
  if (/^[?#]/.test(r)) return b.replace(/\/+$/, '') + r;
  return `${b.replace(/\/+$/, '')}/${r.replace(/^\/+/, '')}`;
}

/** Las {variables} que quedaron sin valor en un texto ya interpolado. */
function variablesSinValor(texto) {
  return [...new Set((String(texto).match(/\{([A-Za-z_][\w.]*)\}/g) || []).map((m) => m.slice(1, -1)))];
}

/** JSON.parse con un mensaje en español que dice qué se estaba leyendo. */
function parsearJson(texto, que = 'el JSON') {
  try {
    return JSON.parse(texto);
  } catch (e) {
    throw new Error(`${que} no es un JSON válido (${e.message}). Revisá comillas, comas y llaves:\n${String(texto).slice(0, 500)}`);
  }
}

// Enteros que no entran en un número de JavaScript sin perder precisión (los id int64 de muchas APIs,
// ej. 9223372036854775807 en petstore): se dejan como texto. Recorre el JSON respetando los strings.
function protegerEnterosGrandes(texto) {
  let salida = '';
  let enString = false;
  for (let i = 0; i < texto.length; i++) {
    const ch = texto[i];
    if (enString) {
      salida += ch;
      if (ch === '\\') { salida += texto[++i] ?? ''; continue; }
      if (ch === '"') enString = false;
      continue;
    }
    if (ch === '"') { enString = true; salida += ch; continue; }
    if (ch === '-' || (ch >= '0' && ch <= '9')) {
      const m = /^-?\d+(\.\d+)?([eE][+-]?\d+)?/.exec(texto.slice(i));
      if (m) {
        const num = m[0];
        const entero = !m[1] && !m[2];
        salida += entero && !Number.isSafeInteger(Number(num)) ? `"${num}"` : num;
        i += num.length - 1;
        continue;
      }
    }
    salida += ch;
  }
  return salida;
}

/** Body de la respuesta: JSON si lo es (con enteros grandes como texto); si no, el texto. */
function parsearRespuesta(texto) {
  if (texto == null || typeof texto !== 'string') return texto;
  const t = texto.trim();
  if (!t) return '';
  if (!/^[[{"]|^-?\d|^(true|false|null)$/.test(t)) return texto;
  try {
    return JSON.parse(protegerEnterosGrandes(t));
  } catch {
    return texto;
  }
}

const SENSIBLE = /authorization|token|api[-_]?key|secret|password|clave|cookie|session|credential/i;

/** Copia de los headers con las credenciales tapadas (se muestra el esquema: "Bearer ***", "Basic ***"). */
function ocultarHeaders(headers) {
  const salida = {};
  for (const [k, v] of Object.entries(headers || {})) {
    if (!SENSIBLE.test(k)) { salida[k] = v; continue; }
    const esquema = /^(Bearer|Basic|Token|ApiKey)\s/i.exec(String(v));
    salida[k] = esquema ? `${esquema[1]} ***` : '***';
  }
  return salida;
}

/** Copia de los parámetros de query con las credenciales tapadas. */
function ocultarParametros(params) {
  const salida = {};
  for (const [k, v] of Object.entries(params || {})) salida[k] = SENSIBLE.test(k) ? '***' : v;
  return salida;
}

const SINONIMOS = {
  integer: 'integer', entero: 'integer', int: 'integer', int32: 'integer', int64: 'integer', long: 'integer',
  number: 'number', numero: 'number', 'número': 'number', float: 'number', double: 'number', decimal: 'number',
  string: 'string', texto: 'string', cadena: 'string',
  boolean: 'boolean', booleano: 'boolean', bool: 'boolean',
  array: 'array', lista: 'array', arreglo: 'array',
  object: 'object', objeto: 'object',
  null: 'null', nulo: 'null',
};

/** ¿El valor es del tipo esperado? Los enteros grandes (que llegan como texto) cuentan como integer. */
function tipoDe(valor, esperado) {
  const tipo = SINONIMOS[String(esperado).trim().toLowerCase()];
  if (!tipo) throw new Error(`Tipo desconocido: "${esperado}". Usá integer, number, string, boolean, array, object o null.`);
  const real = Array.isArray(valor) ? 'array' : valor === null ? 'null' : typeof valor;
  const enteroGrande = typeof valor === 'string' && /^-?\d{16,}$/.test(valor);
  let ok;
  if (tipo === 'integer') ok = (real === 'number' && Number.isInteger(valor)) || enteroGrande;
  else if (tipo === 'number') ok = real === 'number' || enteroGrande;
  else ok = real === tipo;
  return { ok, real: real === 'number' && Number.isInteger(valor) ? 'integer' : real };
}

module.exports = { unirUrl, variablesSinValor, parsearJson, parsearRespuesta, protegerEnterosGrandes, ocultarHeaders, ocultarParametros, tipoDe };

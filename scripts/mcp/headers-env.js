#!/usr/bin/env node
// headersHelper genérico para conectores MCP remotos que piden headers armados con valores del .env
// (ver CONECTORES.md). Devuelve por stdout el JSON de headers; nunca muestra los valores.
//
// Uso (en catalogo.json):
//   "headersHelper": "node scripts/mcp/headers-env.js <conector> [--opcional] Header=VARIABLE [...]"
//
//   Header=VARIABLE              el valor de VARIABLE (del entorno o del .env de la raíz)
//   Header=VARIABLE@valor        si VARIABLE está vacía, usa ese valor por defecto (sin | ni espacios: el helper corre en un shell)
//   Header=bearer:VARIABLE       "Bearer <valor>"
//   Header=basic:USUARIO:CLAVE   "Basic <base64(usuario:clave)>" (autenticación HTTP Basic, por ejemplo Sauce Labs)
//
// Con --opcional, si falta alguna credencial (las que no tienen valor por defecto) devuelve {} y el conector se
// autoriza con tu cuenta (OAuth) desde /mcp. Sin --opcional, si falta corta con un mensaje claro.
const { variable } = require('./leer-env');

const NOMBRE = /^[A-Z_][A-Z0-9_]*$/;
const HEADER = /^[A-Za-z][A-Za-z0-9_-]*$/; // Datadog usa headers con guion bajo (DD_API_KEY)

/** Arma los headers: { headers, faltan } (faltan: las variables sin valor). Puro: recibe cómo leer cada variable. */
function armar(pares, leer = variable) {
  const headers = {};
  const faltan = [];
  for (const par of pares) {
    const i = par.indexOf('=');
    const nombre = i > 0 ? par.slice(0, i) : '';
    const def = i > 0 ? par.slice(i + 1) : '';
    if (!HEADER.test(nombre) || !def) throw new Error(`par inválido: "${par}" (se espera Header=VARIABLE)`);
    if (def.startsWith('basic:')) {
      const [usuario, clave] = def.slice(6).split(':');
      if (!NOMBRE.test(usuario || '') || !NOMBRE.test(clave || '')) throw new Error(`par inválido: "${par}"`);
      const u = leer(usuario);
      const c = leer(clave);
      if (u && c) headers[nombre] = `Basic ${Buffer.from(`${u}:${c}`).toString('base64')}`;
      else faltan.push(...[usuario, clave].filter((v) => !leer(v)));
      continue;
    }
    const bearer = def.startsWith('bearer:');
    const [v, porDefecto] = (bearer ? def.slice(7) : def).split('@');
    if (!NOMBRE.test(v)) throw new Error(`par inválido: "${par}"`);
    const valor = leer(v) || porDefecto || '';
    if (valor) headers[nombre] = bearer ? `Bearer ${valor}` : valor;
    else faltan.push(v);
  }
  return { headers, faltan };
}

if (require.main === module) {
  const [conector, ...resto] = process.argv.slice(2);
  const opcional = resto.includes('--opcional');
  const pares = resto.filter((a) => a !== '--opcional');
  if (!conector || !pares.length) {
    console.error('headers-env: uso: node scripts/mcp/headers-env.js <conector> [--opcional] Header=VARIABLE [...]');
    process.exit(1);
  }
  let r;
  try {
    r = armar(pares);
  } catch (e) {
    console.error(`headers-env: ${e.message}`);
    process.exit(1);
  }
  if (!r.faltan.length) process.stdout.write(JSON.stringify(r.headers));
  else if (opcional) process.stdout.write('{}');
  else {
    console.error(`${conector}: falta ${r.faltan.join(', ')} en el .env de la raíz (ver .env.example y CONECTORES.md).`);
    process.exit(1);
  }
}

module.exports = { armar };

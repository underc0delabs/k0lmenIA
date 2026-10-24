#!/usr/bin/env node
// headersHelper genérico para conectores MCP remotos que aceptan un token como Bearer (ver CONECTORES.md).
//
// Uso (en catalogo.json):
//   "headersHelper": "node scripts/mcp/bearer-headers.js <conector> <VARIABLE> [--opcional]"
//
// Toma <VARIABLE> del entorno o, si no está, del .env de la raíz, y devuelve por stdout
// {"Authorization": "Bearer <token>"}. Con --opcional, si la variable está vacía devuelve {} y el
// conector se autoriza con tu cuenta (OAuth) desde /mcp. Sin --opcional, si falta corta con un
// mensaje claro. El token nunca se muestra.
const { variable } = require('./leer-env');

const [conector, nombre, ...resto] = process.argv.slice(2);
if (!conector || !/^[A-Z_][A-Z0-9_]*$/.test(nombre || '')) {
  console.error('bearer-headers: uso: node scripts/mcp/bearer-headers.js <conector> <VARIABLE> [--opcional]');
  process.exit(1);
}
const opcional = resto.includes('--opcional');
const token = variable(nombre);

if (token) {
  process.stdout.write(JSON.stringify({ Authorization: `Bearer ${token}` }));
} else if (opcional) {
  process.stdout.write('{}');
} else {
  console.error(`${conector}: falta ${nombre} en el .env de la raíz (ver .env.example y CONECTORES.md).`);
  process.exit(1);
}

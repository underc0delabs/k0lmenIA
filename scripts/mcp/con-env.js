#!/usr/bin/env node
// Lanzador genérico de conectores MCP por stdio que leen su configuración del .env (ver CONECTORES.md).
// Claude Code no lee el .env para los ${VARIABLE} de .mcp.json: este script toma cada variable
// pedida del entorno o, si no está, del .env de la raíz, y arranca el server con solo esas
// variables agregadas (no le pasa el resto del .env). Nunca imprime los valores.
//
// Uso (en .mcp.json):
//   node scripts/mcp/con-env.js <conector> [--requeridas A,B] [--opcionales C,D=valor] -- <paquete npm> [args...]
// La versión del paquete es la fija de scripts/mcp/lanzar.js.
const { variable } = require('./leer-env');
const { lanzarNpx, salirConError } = require('./lanzar');

const args = process.argv.slice(2);
const separador = args.indexOf('--');
const conector = args[0];
if (!conector || separador < 1 || separador === args.length - 1) {
  console.error('con-env: uso: node scripts/mcp/con-env.js <conector> [--requeridas A,B] [--opcionales C=valor] -- <paquete> [args...]');
  process.exit(1);
}

function lista(opcion) {
  const i = args.indexOf(opcion);
  return i > 0 && i < separador ? args[i + 1].split(',').filter(Boolean) : [];
}

const env = { ...process.env };
const faltan = [];
for (const nombre of lista('--requeridas')) {
  const valor = variable(nombre);
  if (valor) env[nombre] = valor;
  else faltan.push(nombre);
}
for (const item of lista('--opcionales')) {
  const [nombre, ...porDefecto] = item.split('=');
  const valor = variable(nombre) || porDefecto.join('=');
  if (valor) env[nombre] = valor;
}
if (faltan.length) salirConError(conector, `falta ${faltan.join(', ')} en el .env de la raíz`);

const [paquete, ...resto] = args.slice(separador + 1);
lanzarNpx(conector, paquete, resto, env);

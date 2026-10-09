#!/usr/bin/env node
// Lanzador genérico de conectores MCP por stdio que leen su configuración del .env (ver CONECTORES.md).
// Claude Code no lee el .env para los ${VARIABLE} de .mcp.json: este script toma cada variable
// pedida del entorno o, si no está, del .env de la raíz, y arranca el server con solo esas
// variables agregadas (no le pasa el resto del .env). Nunca imprime los valores.
//
// Uso (en .mcp.json):
//   node scripts/mcp/con-env.js <conector> [--requeridas A,B] [--opcionales C,D=valor] -- <comando> [args...]
//
// Por stdout solo habla el server MCP: los mensajes de este script van a stderr.
const { spawn } = require('child_process');
const { variable } = require('./leer-env');

const args = process.argv.slice(2);
const separador = args.indexOf('--');
const conector = args[0];
if (!conector || separador < 1 || separador === args.length - 1) {
  console.error('con-env: uso: node scripts/mcp/con-env.js <conector> [--requeridas A,B] [--opcionales C=valor] -- <comando> [args...]');
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
if (faltan.length) {
  console.error(`${conector}: falta ${faltan.join(', ')} en el .env de la raíz (ver .env.example y CONECTORES.md).`);
  process.exit(1);
}

const [comando, ...resto] = args.slice(separador + 1);
// En Windows npx es un .cmd y necesita shell: se arma la línea a mano. Los argumentos salen
// de .mcp.json (no del .env) y no llevan espacios.
const opciones = { stdio: 'inherit', env };
const hijo = process.platform === 'win32'
  ? spawn([comando, ...resto].join(' '), { ...opciones, shell: true })
  : spawn(comando, resto, opciones);
hijo.on('error', (e) => {
  console.error(`${conector}: no se pudo iniciar el server (${e.message}).`);
  process.exit(1);
});
hijo.on('exit', (codigo) => process.exit(codigo ?? 1));
for (const senal of ['SIGINT', 'SIGTERM']) process.on(senal, () => hijo.kill(senal));

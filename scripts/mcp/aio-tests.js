#!/usr/bin/env node
// Lanzador del conector MCP aio-tests (ver CONECTORES.md).
// El server de AIO Tests es remoto y su URL es propia de cada tenant, así que no puede ir fija
// en .mcp.json. Este script toma AIO_MCP_URL y AIO_API_TOKEN del entorno o, si no están, del
// .env de la raíz, y lo conecta por stdio con mcp-remote. El token viaja solo por variable de
// entorno (mcp-remote la expande en el header); nunca queda en .mcp.json ni en los argumentos.
//
// Por stdout solo habla el server MCP: los mensajes de este script van a stderr.
const { spawn } = require('child_process');
const { variable } = require('./leer-env');

function salirConError(mensaje) {
  console.error(`aio-tests: ${mensaje} (ver .env.example y CONECTORES.md).`);
  process.exit(1);
}

const url = variable('AIO_MCP_URL');
const token = variable('AIO_API_TOKEN');
if (!url) salirConError('falta AIO_MCP_URL en el .env de la raíz');
if (!/^https:\/\/[A-Za-z0-9.\-/_:%]+$/.test(url)) salirConError('AIO_MCP_URL no es una URL https válida');
if (!token) salirConError('falta AIO_API_TOKEN en el .env de la raíz');

const env = { ...process.env, AIO_AUTH_HEADER: `Bearer ${token}` };
const args = ['-y', 'mcp-remote@latest', url, '--header', 'Authorization:${AIO_AUTH_HEADER}'];

// En Windows npx es un .cmd y necesita shell: se arma la línea a mano (la URL ya está
// validada y ningún argumento lleva espacios; cmd no expande ${...}).
const opciones = { stdio: 'inherit', env };
const hijo = process.platform === 'win32'
  ? spawn(['npx', ...args].join(' '), { ...opciones, shell: true })
  : spawn('npx', args, opciones);
hijo.on('error', (e) => salirConError(`no se pudo iniciar el server (${e.message})`));
hijo.on('exit', (codigo) => process.exit(codigo ?? 1));
for (const senal of ['SIGINT', 'SIGTERM']) process.on(senal, () => hijo.kill(senal));

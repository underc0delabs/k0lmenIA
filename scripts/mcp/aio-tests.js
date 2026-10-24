#!/usr/bin/env node
// Lanzador del conector MCP aio-tests (ver CONECTORES.md).
// El server de AIO Tests es remoto y su URL es propia de cada tenant, así que no puede ir fija
// en .mcp.json. Este script toma AIO_MCP_URL y AIO_API_TOKEN del entorno o, si no están, del
// .env de la raíz, y lo conecta por stdio con mcp-remote. El token viaja solo por variable de
// entorno (mcp-remote la expande en el header); nunca queda en .mcp.json ni en los argumentos.
//
// Por stdout solo habla el server MCP: los mensajes de este script van a stderr.
const { variable } = require('./leer-env');
const { lanzarNpx } = require('./lanzar');

function salirConError(mensaje) {
  console.error(`aio-tests: ${mensaje} (ver .env.example y CONECTORES.md).`);
  process.exit(1);
}

const url = variable('AIO_MCP_URL');
const token = variable('AIO_API_TOKEN');
if (!url) salirConError('falta AIO_MCP_URL en el .env de la raíz');
if (!/^https:\/\/[A-Za-z0-9.\-/_:]+$/.test(url)) salirConError('AIO_MCP_URL no es una URL https válida');
if (!token) salirConError('falta AIO_API_TOKEN en el .env de la raíz');

const env = { ...process.env, AIO_AUTH_HEADER: `Bearer ${token}` };
lanzarNpx('aio-tests', 'mcp-remote', [url, '--header', 'Authorization:${AIO_AUTH_HEADER}'], env);

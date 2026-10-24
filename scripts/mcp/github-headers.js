#!/usr/bin/env node
// headersHelper del conector MCP github (server remoto oficial de GitHub; ver CONECTORES.md).
// Toma GITHUB_TOKEN del entorno o, si no está, del .env de la raíz, y devuelve por stdout los
// headers en JSON: el token como Bearer, solo lectura (X-MCP-Readonly) y los toolsets que usa
// el documentador-proyecto (GITHUB_TOOLSETS para cambiarlos). El token nunca se muestra.
const { variable } = require('./leer-env');

function salirConError(mensaje) {
  console.error(`github: ${mensaje} (ver .env.example y CONECTORES.md).`);
  process.exit(1);
}

const token = variable('GITHUB_TOKEN');
const toolsets = variable('GITHUB_TOOLSETS') || 'context,repos,issues,pull_requests';

if (!token) salirConError('falta GITHUB_TOKEN en el .env de la raíz');
if (!/^[a-z_,\s]+$/.test(toolsets)) salirConError(`GITHUB_TOOLSETS tiene un valor inválido: "${toolsets}"`);

process.stdout.write(JSON.stringify({
  Authorization: `Bearer ${token}`,
  'X-MCP-Readonly': 'true',
  'X-MCP-Toolsets': toolsets.replace(/\s+/g, ''),
}));

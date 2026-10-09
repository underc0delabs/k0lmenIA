#!/usr/bin/env node
// headersHelper del conector MCP k0lmena-tmt (ver CONECTORES.md).
// Toma K0LMENA_TMT_TOKEN del entorno o, si no está, del .env de la raíz del repo, y
// devuelve por stdout el header de autorización en JSON. El token nunca se escribe
// en .mcp.json ni se muestra por pantalla.
const { variable } = require('./leer-env');

const token = variable('K0LMENA_TMT_TOKEN');

if (!token) {
  console.error('k0lmena-tmt: falta K0LMENA_TMT_TOKEN en el .env de la raíz (ver .env.example y CONECTORES.md).');
  process.exit(1);
}
process.stdout.write(JSON.stringify({ Authorization: `Bearer ${token}` }));

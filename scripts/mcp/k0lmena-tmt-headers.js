#!/usr/bin/env node
// headersHelper del conector MCP k0lmena-tmt (ver CONECTORES.md).
// Claude Code no lee el .env para los ${VARIABLE} de .mcp.json: este script toma
// K0LMENA_TMT_TOKEN del entorno o, si no está, del .env de la raíz del repo, y
// devuelve por stdout el header de autorización en JSON. El token nunca se escribe
// en .mcp.json ni se muestra por pantalla.
const fs = require('fs');
const path = require('path');

function leerEnv(archivo) {
  const valores = {};
  if (!fs.existsSync(archivo)) return valores;
  for (const linea of fs.readFileSync(archivo, 'utf8').split(/\r?\n/)) {
    const m = linea.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/);
    if (!m) continue;
    let valor = m[2];
    if (/^(['"]).*\1$/.test(valor)) valor = valor.slice(1, -1);
    else valor = valor.replace(/\s+#.*$/, '');
    valores[m[1]] = valor;
  }
  return valores;
}

const archivoEnv = process.env.K0LMENA_ENV_FILE || path.resolve(__dirname, '..', '..', '.env');
const token = process.env.K0LMENA_TMT_TOKEN || leerEnv(archivoEnv).K0LMENA_TMT_TOKEN;

if (!token) {
  console.error('k0lmena-tmt: falta K0LMENA_TMT_TOKEN en el .env de la raíz (ver .env.example y CONECTORES.md).');
  process.exit(1);
}
process.stdout.write(JSON.stringify({ Authorization: `Bearer ${token}` }));

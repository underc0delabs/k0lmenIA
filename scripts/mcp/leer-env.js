// Lectura del .env de la raíz para los scripts de conectores MCP (ver CONECTORES.md).
// Claude Code no lee el .env para los ${VARIABLE} de .mcp.json: estos scripts toman cada
// valor del entorno y, si no está, del .env. Nunca imprimen los valores.
const fs = require('fs');
const path = require('path');

function leerEnv(archivo) {
  const valores = {};
  if (!fs.existsSync(archivo)) return valores;
  // Sin BOM (archivos guardados desde Windows); mismas reglas que scripts/_env.py y dotenv.
  for (const linea of fs.readFileSync(archivo, 'utf8').replace(/^﻿/, '').split(/\r?\n/)) {
    const m = linea.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!m) continue;
    let valor = m[2];
    if (/^(['"]).*\1$/.test(valor)) valor = valor.slice(1, -1);
    else valor = valor.replace(/\s+#.*$/, '');
    valores[m[1]] = valor;
  }
  return valores;
}

// El .env es del proyecto (con k0lmenIA como plugin, el del proyecto del QA): ver herramientas/k0lmena/tools/rutas.js.
const { PROYECTO } = require('../../herramientas/k0lmena/tools/rutas');
const archivoEnv = process.env.K0LMENA_ENV_FILE || path.join(PROYECTO, '.env');
const delArchivo = leerEnv(archivoEnv);

// Valor de una variable: primero el entorno, después el .env. Vacío = no definida.
function variable(nombre) {
  return process.env[nombre] || delArchivo[nombre] || '';
}

module.exports = { variable };

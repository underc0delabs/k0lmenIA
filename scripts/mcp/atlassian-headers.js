#!/usr/bin/env node
// headersHelper del conector MCP atlassian (Jira y Confluence; ver CONECTORES.md).
// ATLASSIAN_MCP_AUTENTICACION elige cómo conectarse:
//   oauth (por defecto) → no agrega headers: autorizás con tu cuenta desde /mcp.
//   token               → Authorization: Basic base64(JIRA_EMAIL:JIRA_API_TOKEN), o
//                         Authorization: Bearer ATLASSIAN_API_KEY (cuenta de servicio).
//                         Un admin tiene que habilitar el API token en Atlassian Administration
//                         > Rovo > Rovo MCP server > Authentication.
// Los valores salen del entorno o del .env de la raíz y nunca se muestran.
const { variable } = require('./leer-env');

function salirConError(mensaje) {
  console.error(`atlassian: ${mensaje} (ver .env.example y CONECTORES.md).`);
  process.exit(1);
}

const modo = (variable('ATLASSIAN_MCP_AUTENTICACION') || 'oauth').toLowerCase();
if (modo === 'oauth') {
  process.stdout.write('{}');
} else if (modo === 'token') {
  const apiKey = variable('ATLASSIAN_API_KEY');
  const email = variable('JIRA_EMAIL');
  const token = variable('JIRA_API_TOKEN');
  if (apiKey) {
    process.stdout.write(JSON.stringify({ Authorization: `Bearer ${apiKey}` }));
  } else if (email && token) {
    const basico = Buffer.from(`${email}:${token}`).toString('base64');
    process.stdout.write(JSON.stringify({ Authorization: `Basic ${basico}` }));
  } else {
    salirConError('con ATLASSIAN_MCP_AUTENTICACION=token faltan JIRA_EMAIL y JIRA_API_TOKEN (o ATLASSIAN_API_KEY) en el .env');
  }
} else {
  salirConError(`ATLASSIAN_MCP_AUTENTICACION="${modo}" no es válido; usá oauth o token`);
}

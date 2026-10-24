#!/usr/bin/env node
// headersHelper del conector MCP gitlab (server oficial de GitLab, /api/v4/mcp; ver CONECTORES.md).
// Sin GITLAB_TOKEN no agrega autorización: te autorizás con tu cuenta (OAuth) desde /mcp.
// Con GITLAB_TOKEN (personal access token *fine-grained* con el recurso "MCP tool" y permiso
// Execute; los tokens clásicos los rechaza con 403) lo manda como Bearer.
// Siempre limita los toolsets a los que usa el documentador-proyecto (GITLAB_TOOLSETS para cambiarlos).
// Los valores salen del entorno o del .env de la raíz y nunca se muestran.
const { variable } = require('./leer-env');

function salirConError(mensaje) {
  console.error(`gitlab: ${mensaje} (ver .env.example y CONECTORES.md).`);
  process.exit(1);
}

const token = variable('GITLAB_TOKEN');
const toolsets = variable('GITLAB_TOOLSETS') || 'meta,core,merge_requests,work_items,repository,wikis';
if (!/^[a-z_,\s]+$/.test(toolsets)) salirConError(`GITLAB_TOOLSETS tiene un valor inválido: "${toolsets}"`);

const headers = { 'X-Gitlab-Enabled-Mcp-Server-Toolsets': toolsets.replace(/\s+/g, '') };
if (token) headers.Authorization = `Bearer ${token}`;
process.stdout.write(JSON.stringify(headers));

#!/usr/bin/env node
// Lanzador del conector MCP azure-devops (ver CONECTORES.md).
// Lee la configuración de Azure DevOps del entorno o, si no está, del .env de la raíz, y
// arranca el server oficial de Microsoft (@azure-devops/mcp) por stdio. El PAT se le pasa
// al server solo por variable de entorno (PERSONAL_ACCESS_TOKEN, en base64 como lo pide);
// nunca queda en .mcp.json ni se imprime.
//
// Por stdout solo habla el server MCP: los mensajes de este script van a stderr.
const { variable } = require('./leer-env');
const { lanzarNpx } = require('./lanzar');

function salirConError(mensaje) {
  console.error(`azure-devops: ${mensaje} (ver .env.example y CONECTORES.md).`);
  process.exit(1);
}

const organizacion = variable('ADO_ORGANIZACION');
const pat = variable('ADO_PAT');
const autenticacion = variable('ADO_AUTENTICACION') || 'pat';
const dominios = (variable('ADO_DOMINIOS') || 'core work work-items test-plans wiki search')
  .split(/[\s,]+/)
  .filter(Boolean);

if (!organizacion) salirConError('falta ADO_ORGANIZACION en el .env de la raíz');
if (!/^[A-Za-z0-9][A-Za-z0-9-]*$/.test(organizacion)) {
  salirConError('ADO_ORGANIZACION debe ser solo el nombre de la organización (ej. "mi-empresa"), no la URL');
}
if (!['pat', 'interactive', 'azcli', 'env', 'envvar'].includes(autenticacion)) {
  salirConError(`ADO_AUTENTICACION="${autenticacion}" no es válido; usá pat, interactive, azcli, env o envvar`);
}
if (autenticacion === 'pat' && !pat) salirConError('falta ADO_PAT en el .env de la raíz');
const dominioInvalido = dominios.find((d) => !/^[a-z-]+$/.test(d));
if (dominioInvalido) salirConError(`ADO_DOMINIOS tiene un valor inválido: "${dominioInvalido}"`);

const env = { ...process.env };
if (autenticacion === 'pat') {
  // El server pide base64 de "<email>:<pat>"; el email puede ser cualquier valor no vacío.
  env.PERSONAL_ACCESS_TOKEN = Buffer.from(`k0lmenia:${pat}`).toString('base64');
}
const proyecto = variable('ADO_PROYECTO');
const equipo = variable('ADO_EQUIPO');
if (proyecto) env.ado_mcp_project = proyecto;
if (equipo) env.ado_mcp_team = equipo;

const args = [organizacion, '-a', autenticacion, '-d', ...dominios];
const tenant = variable('ADO_TENANT');
if (tenant) {
  if (!/^[A-Za-z0-9.-]+$/.test(tenant)) salirConError('ADO_TENANT debe ser el ID (GUID) o el dominio del tenant');
  args.push('-t', tenant);
}

lanzarNpx('azure-devops', '@azure-devops/mcp', args, env);

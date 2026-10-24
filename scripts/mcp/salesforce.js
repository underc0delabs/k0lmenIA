#!/usr/bin/env node
// Lanzador del conector MCP salesforce (ver CONECTORES.md).
// Arranca el server oficial de Salesforce DX (@salesforce/mcp) por stdio contra UNA org: la de
// SALESFORCE_ORG, que tiene que estar en SALESFORCE_ORGS_AUTORIZADAS (nunca ALLOW_ALL_ORGS).
// La org se autoriza antes con la CLI (sf org login web --alias <alias>); el server usa esa
// autorización local, así que acá no viaja ningún token.
//
// Solo se habilitan herramientas de lectura y prueba: la consulta SOQL (toolset data) y los tests
// de Apex (run_apex_test). Nada de metadata (deploy/retrieve) ni de usuarios (asignar permisos).
// Sin telemetría hacia Salesforce.
//
// Por stdout solo habla el server MCP: los mensajes de este script van a stderr.
const { variable } = require('./leer-env');
const { lanzarNpx } = require('./lanzar');

function salirConError(mensaje) {
  console.error(`salesforce: ${mensaje} (ver .env.example y CONECTORES.md).`);
  process.exit(1);
}

const org = variable('SALESFORCE_ORG');
const autorizadas = variable('SALESFORCE_ORGS_AUTORIZADAS').split(/[\s,]+/).filter(Boolean);

if (!org) salirConError('falta SALESFORCE_ORG (el alias de la org) en el .env de la raíz');
if (!/^[\w.@+-]+$/.test(org)) salirConError(`SALESFORCE_ORG="${org}" no es un alias válido`);
if (/^(ALLOW_ALL_ORGS|DEFAULT_TARGET_ORG|DEFAULT_TARGET_DEV_HUB)$/.test(org)) {
  salirConError('SALESFORCE_ORG tiene que ser el alias de una org concreta, no un comodín');
}
if (!autorizadas.includes(org)) salirConError(`${org} no está en SALESFORCE_ORGS_AUTORIZADAS`);

lanzarNpx('salesforce', '@salesforce/mcp', ['--orgs', org, '--toolsets', 'data', '--tools', 'run_apex_test', '--no-telemetry']);

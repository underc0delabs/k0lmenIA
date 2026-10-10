#!/usr/bin/env node
// Activa y desactiva los conectores MCP opcionales de k0lmenIA (ver CONECTORES.md).
//
//   npm run conector                        lista los conectores y cuáles tenés activos
//   npm run conector -- activar azure-devops [qtm4j ...]
//   npm run conector -- desactivar azure-devops
//
// Los opcionales no están en .mcp.json para que Claude Code arranque sin pedir aprobaciones.
// "activar" los registra con `claude mcp add-json --scope local`: quedan solo para vos, en este
// proyecto, y no se versionan. Las credenciales siguen saliendo del .env (los scripts de
// scripts/mcp/ las leen al arrancar). Después de activar o desactivar, reiniciá Claude Code.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { variable } = require('./leer-env');

const RAIZ = path.resolve(__dirname, '..', '..');
const CATALOGO = JSON.parse(fs.readFileSync(path.join(__dirname, 'catalogo.json'), 'utf8')).conectores;
const POR_DEFECTO = Object.keys(JSON.parse(fs.readFileSync(path.join(RAIZ, '.mcp.json'), 'utf8')).mcpServers);

// Variables que revisa "activar" (solo avisa: el conector se puede activar antes de completar el .env).
const REQUERIDAS = {
  'azure-devops': () => (/^(interactive|azcli|env|envvar)$/i.test(variable('ADO_AUTENTICACION')) ? ['ADO_ORGANIZACION'] : ['ADO_ORGANIZACION', 'ADO_PAT']),
  qtm4j: () => ['QTM4J_API_KEY'],
  qmetry: () => ['QMETRY_API_KEY'],
  'aio-tests': () => ['AIO_MCP_URL', 'AIO_API_TOKEN'],
  'k0lmena-tmt': () => ['K0LMENA_TMT_TOKEN'],
};

/** Los scripts del repo con ruta absoluta: así el conector arranca aunque abras Claude Code en otra carpeta. */
function conRutasAbsolutas(servidor) {
  const abs = (r) => path.join(RAIZ, r).split(path.sep).join('/');
  const s = JSON.parse(JSON.stringify(servidor));
  if (Array.isArray(s.args)) s.args = s.args.map((a) => (a.startsWith('scripts/') ? abs(a) : a));
  if (s.headersHelper) s.headersHelper = s.headersHelper.replace(/scripts\/[\w./-]+/, (r) => `"${abs(r)}"`);
  return s;
}

/** Conectores registrados con alcance local para este proyecto (de ~/.claude.json; solo nombres). */
function activosLocales() {
  try {
    const datos = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.claude.json'), 'utf8'));
    const clave = RAIZ.split(path.sep).join('/').toLowerCase();
    const proyecto = Object.entries(datos.projects || {}).find(([k]) => k.toLowerCase() === clave);
    return Object.keys((proyecto && proyecto[1].mcpServers) || {});
  } catch {
    return null; // no se pudo saber
  }
}

function claude(args) {
  let r = spawnSync('claude', args, { encoding: 'utf8', cwd: RAIZ });
  if (r.error && process.platform === 'win32') {
    // Instalado con npm: claude.cmd necesita shell (el JSON va con las comillas escapadas para cmd).
    const linea = ['claude', ...args.map((a) => (/[\s"{}]/.test(a) ? `"${a.replace(/"/g, '\\"')}"` : a))].join(' ');
    r = spawnSync(linea, { encoding: 'utf8', cwd: RAIZ, shell: true });
  }
  if (r.error) {
    console.error('No encuentro el comando "claude". Instalá Claude Code (ver README) y volvé a intentar.');
    process.exit(1);
  }
  return r;
}

function listar() {
  const activos = activosLocales();
  console.log('Conectores MCP de k0lmenIA\n');
  console.log('Habilitados para todos (en .mcp.json):');
  for (const n of POR_DEFECTO) console.log(`  ✓ ${n}`);
  console.log('\nOpcionales (se activan con: npm run conector -- activar <nombre>):');
  for (const [n, c] of Object.entries(CATALOGO)) {
    const marca = activos === null ? '?' : activos.includes(n) ? '✓' : ' ';
    console.log(`  ${marca} ${n.padEnd(14)} ${c.descripcion}\n      variables: ${c.variables}`);
  }
  if (activos === null) console.log('\n(No pude leer qué conectores tenés activos: probá con  claude mcp list)');
  console.log('\nDespués de activar o desactivar, reiniciá Claude Code y verificá con /mcp.');
}

function activar(nombres) {
  for (const n of nombres) {
    const c = CATALOGO[n];
    if (!c) {
      console.error(`"${n}" no está en el catálogo. Opciones: ${Object.keys(CATALOGO).join(', ')}.`);
      process.exitCode = 1;
      continue;
    }
    if ((activosLocales() || []).includes(n)) claude(['mcp', 'remove', n, '--scope', 'local']); // se reemplaza
    const r = claude(['mcp', 'add-json', n, JSON.stringify(conRutasAbsolutas(c.servidor)), '--scope', 'local']);
    if (r.status !== 0) {
      console.error(`No se pudo activar ${n}: ${(r.stderr || r.stdout).trim()}`);
      process.exitCode = 1;
      continue;
    }
    const faltan = (REQUERIDAS[n] ? REQUERIDAS[n]() : []).filter((v) => !variable(v));
    console.log(`✓ ${n} activado (solo para vos, en este proyecto).`);
    if (faltan.length) console.log(`  Falta completar en el .env: ${faltan.join(', ')} (ver .env.example).`);
  }
  console.log('Reiniciá Claude Code y verificá con /mcp.');
}

function desactivar(nombres) {
  for (const n of nombres) {
    const r = claude(['mcp', 'remove', n, '--scope', 'local']);
    console.log(r.status === 0 ? `✓ ${n} desactivado.` : `${n} no estaba activo.`);
  }
}

const [accion, ...nombres] = process.argv.slice(2);
if (!accion || accion === 'listar') listar();
else if (accion === 'activar' && nombres.length) activar(nombres);
else if (accion === 'desactivar' && nombres.length) desactivar(nombres);
else {
  console.error('Uso: npm run conector -- [listar | activar <nombre> [...] | desactivar <nombre> [...]]');
  process.exit(1);
}

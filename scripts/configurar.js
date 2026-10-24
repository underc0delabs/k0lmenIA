#!/usr/bin/env node
// Asistente de configuración de k0lmenIA (npm run configurar).
//
// Hace unas pocas preguntas en español, con opciones numeradas, y deja todo listo:
//   1. crea el .env (si no existe) y completa la app a probar;
//   2. pregunta qué herramientas usa el equipo (historias, casos de prueba, código, diseños);
//   3. pide solo los datos de esas herramientas (los tokens no se muestran mientras se escriben);
//   4. guarda todo en el .env y activa los conectores que hagan falta.
//
// Se puede correr las veces que quieras: muestra lo que ya está cargado y Enter lo deja igual.
// Para lo avanzado (activar o desactivar un conector puntual) sigue estando npm run conector.
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const RAIZ = path.resolve(__dirname, '..');
const ENV = process.env.K0LMENA_ENV_FILE || path.join(RAIZ, '.env');
const EJEMPLO = path.join(RAIZ, '.env.example');

// ------------------------------------------------------------------ qué se pregunta
// Cada opción: los conectores que activa, los valores fijos que escribe y los datos que pide.
// Un dato: { clave, texto, secreto?, opcional?, defecto?, ayuda? }.
const JIRA_URL = { clave: 'JIRA_BASE_URL', texto: 'URL de tu Jira', ayuda: 'ej. https://mi-empresa.atlassian.net' };
const JIRA_EMAIL = { clave: 'JIRA_EMAIL', texto: 'Tu email de Jira' };
const JIRA_TOKEN = { clave: 'JIRA_API_TOKEN', texto: 'API token de Jira', secreto: true, ayuda: 'se crea en https://id.atlassian.com/manage-profile/security/api-tokens' };
const ADO = [
  { clave: 'ADO_ORGANIZACION', texto: 'Organización de Azure DevOps', ayuda: 'solo el nombre: el de https://dev.azure.com/<organizacion>' },
  { clave: 'ADO_PAT', texto: 'Personal Access Token de Azure DevOps', secreto: true, ayuda: 'User settings > Personal access tokens' },
  { clave: 'ADO_PROYECTO', texto: 'Proyecto de Azure DevOps', opcional: true },
];
const PROYECTO_JIRA = { clave: 'GESTION_PROYECTO', texto: 'Key del proyecto de Jira', ayuda: 'ej. PROJ' };
const OAUTH = 'No hace falta ningún dato: la primera vez que lo uses, Claude te pide que inicies sesión con tu cuenta.';

const PASOS = [
  {
    id: 'historias',
    titulo: '¿Dónde están las historias de usuario?',
    opciones: [
      { nombre: 'Jira', datos: [JIRA_URL], nota: 'Jira ya viene conectado. La primera vez que lo uses, Claude te pide que inicies sesión con tu cuenta.' },
      { nombre: 'Azure DevOps (Boards)', conectores: ['azure-devops'], datos: ADO },
      { nombre: 'Linear', conectores: ['linear'], nota: OAUTH },
      { nombre: 'ClickUp', conectores: ['clickup'], nota: OAUTH },
      { nombre: 'monday.com', conectores: ['monday'], nota: OAUTH },
      { nombre: 'Trello', conectores: ['trello'], nota: OAUTH },
      { nombre: 'Notion', conectores: ['notion'], nota: OAUTH },
      { nombre: 'Shortcut', conectores: ['shortcut'], nota: OAUTH },
      { nombre: 'YouTrack', conectores: ['youtrack'], datos: [
        { clave: 'YOUTRACK_URL', texto: 'URL de YouTrack', ayuda: 'ej. https://mi-empresa.youtrack.cloud' },
        { clave: 'YOUTRACK_TOKEN', texto: 'Token de YouTrack', secreto: true }] },
      { nombre: 'Asana', conectores: ['asana'], datos: [
        { clave: 'ASANA_CLIENT_ID', texto: 'Client ID de la app MCP de Asana' },
        { clave: 'ASANA_CLIENT_SECRET', texto: 'Client secret de la app MCP de Asana', secreto: true }],
        nota: 'Asana pide crear una app MCP propia (ver CONECTORES.md).' },
      { nombre: 'En archivos (los dejo en input/historias)', nota: 'Copiá las historias como .md o .txt en input/historias/.' },
    ],
  },
  {
    id: 'casos',
    titulo: '¿Dónde guardan los casos de prueba?',
    opciones: [
      { nombre: 'En Excel (sin herramienta)', nota: 'Los casos se generan como planilla en output/casos-de-prueba/.' },
      { nombre: 'Xray Cloud', fijos: { GESTION_HERRAMIENTA: 'xray-cloud' }, datos: [PROYECTO_JIRA,
        { clave: 'XRAY_CLOUD_CLIENT_ID', texto: 'Client ID de Xray', ayuda: 'Xray > Global Settings > API Keys' },
        { clave: 'XRAY_CLOUD_CLIENT_SECRET', texto: 'Client secret de Xray', secreto: true },
        JIRA_URL, JIRA_EMAIL, JIRA_TOKEN] },
      { nombre: 'Xray Server / Data Center', fijos: { GESTION_HERRAMIENTA: 'xray-dc' }, datos: [PROYECTO_JIRA,
        { clave: 'XRAY_DC_URL', texto: 'URL de tu Jira', ayuda: 'ej. https://jira.mi-empresa.com' },
        { clave: 'XRAY_DC_TOKEN', texto: 'Personal Access Token de Jira', secreto: true }] },
      { nombre: 'QMetry para Jira (QTM4J)', conectores: ['qtm4j'], fijos: { GESTION_HERRAMIENTA: 'qtm4j' }, datos: [PROYECTO_JIRA,
        { clave: 'QTM4J_API_KEY', texto: 'Open API key de QMetry', secreto: true, ayuda: 'QMetry > Configuration > Open API' }] },
      { nombre: 'AIO Tests', conectores: ['aio-tests'], fijos: { GESTION_HERRAMIENTA: 'aio' }, datos: [PROYECTO_JIRA,
        { clave: 'AIO_API_TOKEN', texto: 'API token de AIO Tests', secreto: true, ayuda: 'AIO Tests > My Settings > API Token' },
        { clave: 'AIO_MCP_URL', texto: 'URL del server MCP de AIO', ayuda: 'AIO Tests > My Settings > MCP Authorization' }] },
      { nombre: 'Zephyr Scale (Jira Cloud)', fijos: { GESTION_HERRAMIENTA: 'zephyr-scale' }, datos: [PROYECTO_JIRA,
        { clave: 'ZEPHYR_API_TOKEN', texto: 'API token de Zephyr', secreto: true, ayuda: 'Jira > tu foto (abajo a la izquierda) > Zephyr API keys' },
        { clave: 'ZEPHYR_API_URL', texto: 'URL de la API de Zephyr', opcional: true, defecto: 'https://api.zephyrscale.smartbear.com/v2',
          ayuda: 'EU: https://eu.api.zephyrscale.smartbear.com/v2 · AU: https://au.api.zephyrscale.smartbear.com/v2 · DE: https://de.api.zephyrscale.smartbear.com/v2' },
        JIRA_URL, JIRA_EMAIL, JIRA_TOKEN] },
      { nombre: 'Azure Test Plans', conectores: ['azure-devops'], datos: ADO },
      { nombre: 'k0lmenaTMT', conectores: ['k0lmena-tmt'], datos: [
        { clave: 'K0LMENA_TMT_TOKEN', texto: 'Token personal de k0lmenaTMT (kolm_pat_...)', secreto: true },
        { clave: 'K0LMENA_TMT_URL', texto: 'URL de k0lmenaTMT', opcional: true, defecto: 'http://localhost:4000/api/v1/mcp' }] },
    ],
  },
  {
    id: 'codigo',
    titulo: '¿Dónde está el código de la aplicación? (opcional: sirve para documentar el proyecto)',
    opciones: [
      { nombre: 'Prefiero no conectarlo (o lo hago más tarde)' },
      { nombre: 'GitHub', conectores: ['github'], fijos: { REPO_PROVEEDOR: 'github' }, datos: [
        { clave: 'REPO_NOMBRE', texto: 'Repositorio', ayuda: 'dueño/repo, ej. mi-empresa/mi-app (varios, separados por coma)' },
        { clave: 'GITHUB_TOKEN', texto: 'Token de GitHub de solo lectura', secreto: true, ayuda: 'https://github.com/settings/personal-access-tokens' }] },
      { nombre: 'GitLab', conectores: ['gitlab'], fijos: { REPO_PROVEEDOR: 'gitlab' }, datos: [
        { clave: 'REPO_NOMBRE', texto: 'Repositorio', ayuda: 'grupo/proyecto (varios, separados por coma)' },
        { clave: 'GITLAB_URL', texto: 'URL de GitLab', opcional: true, defecto: 'https://gitlab.com' }],
        nota: 'Sin token: la primera vez que lo uses, Claude te pide que inicies sesión con tu cuenta.' },
      { nombre: 'Azure Repos', conectores: ['azure-devops'], fijos: { REPO_PROVEEDOR: 'azure-repos' }, datos: [
        { clave: 'REPO_NOMBRE', texto: 'Repositorio', ayuda: 'proyecto/repo' }, ...ADO] },
    ],
  },
  {
    id: 'figma',
    titulo: '¿Usan Figma para los diseños?',
    opciones: [
      { nombre: 'No' },
      { nombre: 'Sí', conectores: ['figma'], nota: OAUTH },
    ],
  },
  {
    id: 'scalar',
    titulo: '¿Las APIs del equipo están en Scalar (scalar.com)?',
    opciones: [
      { nombre: 'No' },
      { nombre: 'Sí', conectores: ['scalar'], datos: [
        { clave: 'SCALAR_MCP_URL', texto: 'URL del server MCP de la API', ayuda: 'Dashboard de Scalar > MCP, ej. https://mcp.scalar.com/@mi-equipo/pagos (agregá ?env=staging para elegir el ambiente)' },
        { clave: 'SCALAR_API_KEY', texto: 'Token personal de Scalar', secreto: true, opcional: true, ayuda: 'https://dashboard.scalar.com/account (sin token, Claude te pide iniciar sesión)' },
        { clave: 'SCALAR_NAMESPACE', texto: 'Namespace del equipo en el Registry', opcional: true, ayuda: 'el de registry.scalar.com/@<namespace>' }],
        nota: 'Los servers MCP de Scalar son de los planes pagos; cada llamada que ejecuta consume créditos.' },
    ],
  },
  {
    id: 'documentos',
    titulo: '¿Querés que los documentos Word (manuales de usuario) salgan firmados por tu equipo?',
    opciones: [
      { nombre: 'No (salen firmados por k0lmenIA)' },
      { nombre: 'Sí', datos: [{ clave: 'MANUAL_EQUIPO', texto: 'Nombre del equipo', ayuda: 'ej. Equipo de QA de Pagos' }] },
    ],
  },
];

const APP = [
  { clave: 'APP_URL', texto: 'URL de la aplicación que vas a probar', ayuda: 'ej. https://staging.mi-app.com · un ambiente de prueba, no producción' },
  { clave: 'APP_USER', texto: 'Usuario de prueba para entrar a la app', opcional: true },
  { clave: 'APP_PASSWORD', texto: 'Contraseña de ese usuario', secreto: true, opcional: true },
];

// ------------------------------------------------------------------ el .env
const LINEA = (clave) => new RegExp(`^[ \\t]*#?[ \\t]*(?:export[ \\t]+)?${clave}[ \\t]*=.*$`, 'm');

/** Valor actual de una clave (solo las líneas activas, sin #). */
function leerValor(texto, clave) {
  const m = new RegExp(`^[ \\t]*(?:export[ \\t]+)?${clave}[ \\t]*=[ \\t]*(.*?)[ \\t]*$`, 'm').exec(texto);
  if (!m) return '';
  const v = m[1];
  if (/^(['"]).*\1$/.test(v)) return v.slice(1, -1);
  return v.replace(/\s+#.*$/, '');
}

const formatear = (valor) => (/[\s#'"]/.test(valor) ? `"${valor.replace(/"/g, '')}"` : valor);

/**
 * Escribe CLAVE=valor: reemplaza la línea activa o, si no hay, la primera comentada (la "descomenta"
 * en su lugar, con su explicación arriba); si la clave no está, la agrega al final.
 */
function establecer(texto, clave, valor) {
  const linea = `${clave}=${formatear(valor)}`;
  const activa = new RegExp(`^[ \\t]*(?:export[ \\t]+)?${clave}[ \\t]*=.*$`, 'm');
  if (activa.test(texto)) return texto.replace(activa, () => linea);
  if (LINEA(clave).test(texto)) return texto.replace(LINEA(clave), () => linea);
  const fin = texto.endsWith('\n') || !texto ? '' : '\n';
  const titulo = texto.includes('# --- Agregado por npm run configurar ---') ? '' : '\n# --- Agregado por npm run configurar ---\n';
  return `${texto}${fin}${titulo}${linea}\n`;
}

/** Lo que hay que hacer según las opciones elegidas: conectores, valores fijos y datos a pedir (sin repetidos). */
function plan(elegidas) {
  const conectores = new Set();
  const fijos = {};
  const datos = [];
  const notas = [];
  for (const o of elegidas) {
    for (const c of o.conectores || []) conectores.add(c);
    Object.assign(fijos, o.fijos || {});
    for (const d of o.datos || []) if (!datos.some((x) => x.clave === d.clave)) datos.push(d);
    if (o.nota) notas.push(`${o.nombre}: ${o.nota}`);
  }
  return { conectores: [...conectores], fijos, datos, notas };
}

// ------------------------------------------------------------------ la terminal
function crearTerminal() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const original = rl._writeToOutput.bind(rl);
  let oculto = false;
  rl._writeToOutput = (s) => {
    if (!oculto) return original(s);
    if (/[\r\n]/.test(s)) original('\n'); // lo que se tipea no se muestra
  };
  const preguntar = (texto, { secreto = false } = {}) => new Promise((resolve) => {
    rl.question(texto, (r) => { oculto = false; resolve(r.trim()); });
    oculto = secreto;
  });
  return { rl, preguntar };
}

const negrita = (s) => (process.stdout.isTTY ? `\x1b[1m${s}\x1b[0m` : s);
const gris = (s) => (process.stdout.isTTY ? `\x1b[2m${s}\x1b[0m` : s);
const verde = (s) => (process.stdout.isTTY ? `\x1b[32m${s}\x1b[0m` : s);

async function elegir(t, paso) {
  console.log(`\n${negrita(paso.titulo)}`);
  paso.opciones.forEach((o, i) => console.log(`  ${i + 1}. ${o.nombre}`));
  for (;;) {
    const r = await t.preguntar('Elegí un número: ');
    const n = Number(r);
    if (Number.isInteger(n) && n >= 1 && n <= paso.opciones.length) return paso.opciones[n - 1];
    console.log(`Escribí un número del 1 al ${paso.opciones.length}.`);
  }
}

async function pedirDato(t, d, actual) {
  const ayuda = d.ayuda ? gris(` (${d.ayuda})`) : '';
  let pista = '';
  if (actual) pista = d.secreto ? gris(' [ya está cargado: Enter lo deja]') : gris(` [${actual}: Enter lo deja]`);
  else if (d.defecto) pista = gris(` [${d.defecto}]`);
  else if (d.opcional) pista = gris(' [opcional: Enter para saltear]');
  for (;;) {
    const r = await t.preguntar(`  ${d.texto}${ayuda}${pista}: `, { secreto: d.secreto });
    if (r) return r;
    if (actual) return actual;
    if (d.defecto) return d.defecto;
    if (d.opcional) return '';
    console.log('  Este dato hace falta. (Si todavía no lo tenés, cortá con Ctrl+C y volvé a correr npm run configurar cuando lo tengas.)');
  }
}

async function main() {
  if (!process.stdin.isTTY) {
    console.log('npm run configurar hace preguntas: corrélo en una terminal (por ejemplo, la de VS Code: Terminal > New Terminal).');
    process.exit(1);
  }
  console.log(negrita('\nConfiguración de k0lmenIA'));
  console.log('Te hago unas preguntas y dejo todo listo. Enter deja lo que ya estaba cargado. Ctrl+C cancela sin guardar.');

  let texto;
  if (fs.existsSync(ENV)) texto = fs.readFileSync(ENV, 'utf8');
  else {
    texto = fs.existsSync(EJEMPLO) ? fs.readFileSync(EJEMPLO, 'utf8') : '';
    console.log(gris('(No había .env: lo creo a partir de .env.example.)'));
  }

  const t = crearTerminal();
  const valores = {};
  try {
    console.log(`\n${negrita('Tu aplicación')}`);
    for (const d of APP) valores[d.clave] = await pedirDato(t, d, leerValor(texto, d.clave).replace(/^https:\/\/tu-app-de-prueba\.com$|^tu_(usuario|password)$/, ''));

    const elegidas = [];
    for (const paso of PASOS) elegidas.push(await elegir(t, paso));
    const p = plan(elegidas);
    if (p.datos.length) console.log(`\n${negrita('Datos de las herramientas que elegiste')}`);
    for (const d of p.datos) {
      const actual = leerValor(texto, d.clave).replace(/^https:\/\/tu-sitio\.atlassian\.net$/, '');
      valores[d.clave] = await pedirDato(t, d, actual);
    }
    Object.assign(valores, p.fijos);

    for (const [clave, valor] of Object.entries(valores)) if (valor) texto = establecer(texto, clave, valor);
    fs.writeFileSync(ENV, texto, 'utf8');
    console.log(`\n${verde('✓')} Guardé la configuración en el .env (no se sube al repositorio).`);

    if (p.conectores.length) {
      console.log(`\n${negrita('Conectores')}`);
      const { activar } = require('./mcp/conector.js');
      activar(p.conectores);
    }
    for (const n of p.notas) console.log(`· ${n}`);

    console.log(`\n${negrita('Listo.')} Lo que sigue:`);
    console.log('  1. Cerrá Claude Code y volvé a abrirlo (así toma los cambios).');
    console.log('  2. Escribí /mcp para ver los conectores. Los que dicen "needs authentication" te piden iniciar sesión.');
    console.log('  3. Si querés revisar que esté todo bien: npm run doctor');
    console.log('  4. Para empezar, pedile algo a Claude en español, por ejemplo: "analizá la historia PROJ-123".\n');
  } finally {
    t.rl.close();
  }
}

if (require.main === module) {
  main().catch((e) => {
    console.error(`\nNo pude terminar la configuración: ${e.message}`);
    process.exit(1);
  });
}

module.exports = { main, establecer, leerValor, plan, PASOS, APP };

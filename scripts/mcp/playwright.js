#!/usr/bin/env node
// Lanzador de los conectores MCP playwright y playwright-headless (ver CONECTORES.md).
// Arranca el server oficial de Playwright con la carpeta de evidencias del repo y, si existe el
// .env de la raíz, con --secrets .env: Playwright oculta esos valores (contraseñas, tokens) en
// las respuestas que ve el modelo. Sin .env arranca igual (el server falla si el archivo no existe).
//
// Con SESION en el .env (ver herramientas/k0lmena/tools/login/sesion.js) arranca con la sesión
// guardada por npm run login: --isolated --storage-state .auth/sesion[-<nombre>].json.
//
// Con NAVEGADOR_CANAL (chrome|msedge) usa ese navegador instalado, y con QA_BYPASS_HEADER + QA_BYPASS_TOKEN
// agrega el header de bypass acordado con el equipo de la app solo a los hosts de la app (navegador-mcp.ts);
// --secrets .env oculta el token en lo que ve el modelo. Ver herramientas/k0lmena/tools/navegador/README.md.
//
// Uso (en .mcp.json): node scripts/mcp/playwright.js [--headless]
const fs = require('fs');
const path = require('path');
const { lanzarNpx, RAIZ } = require('./lanzar');
const { variable } = require('./leer-env');
const { sesionActiva } = require('../../herramientas/k0lmena/tools/login/sesion');
const navegadorComun = require('../../herramientas/k0lmena/tools/navegador/navegador');

const args = ['--output-dir', 'output/ejecuciones/evidencia'];
if (process.argv.includes('--headless')) args.push('--headless');
if (fs.existsSync(path.join(RAIZ, '.env'))) args.push('--secrets', '.env');

let sesion = null;
try {
  sesion = sesionActiva(variable('SESION'), (msg) => console.error(`playwright: ${msg}`));
} catch (e) {
  console.error(`playwright: ${e.message}; se sigue sin sesión.`);
}
if (sesion) {
  // Relativa a la raíz (el server corre ahí) y con /: la línea de npx solo admite rutas simples.
  args.push('--isolated', '--storage-state', path.relative(RAIZ, sesion).split(path.sep).join('/'));
}
// Canal y bypass: las mismas variables que usa k0lmena (validadas por tools/navegador).
const env = { ...process.env };
try {
  const config = navegadorComun.leerConfig({
    NAVEGADOR_CANAL: variable('NAVEGADOR_CANAL'), APP_URL: variable('APP_URL'),
    QA_BYPASS_HEADER: variable('QA_BYPASS_HEADER'), QA_BYPASS_TOKEN: variable('QA_BYPASS_TOKEN'),
    QA_BYPASS_HOSTS: variable('QA_BYPASS_HOSTS'),
  });
  if (config.canal) args.push('--browser', config.canal);
  if (config.bypass) {
    args.push('--init-page', 'scripts/mcp/navegador-mcp.ts');
    Object.assign(env, { K0LMENIA_BYPASS_HEADER: config.bypass.nombre, K0LMENIA_BYPASS_TOKEN: config.bypass.valor,
      K0LMENIA_BYPASS_HOSTS: config.bypass.hosts.join(',') });
  }
} catch (e) {
  console.error(`playwright: ${e.message}; se sigue sin canal ni bypass.`);
}
lanzarNpx('playwright', '@playwright/mcp', args, env);

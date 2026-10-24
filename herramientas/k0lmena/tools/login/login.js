// Login manual y sesión guardada (npm run login).
//
// Abre el navegador en la app, te logueás a mano (captcha, 2FA, SSO… lo que pida) y guarda la
// sesión (cookies, localStorage e IndexedDB) en .auth/ de la raíz del repo. Después la usan:
//   - las suites web de k0lmena (npm test), con SESION=si en el .env;
//   - el navegador de los agentes (Playwright MCP), al escribir o ejecutar casos, con la misma variable.
//
// Uso (desde la raíz del repo):
//   npm run login                         -> .auth/sesion.json, en LOGIN_URL o APP_URL
//   npm run login -- --nombre admin       -> .auth/sesion-admin.json (una sesión por rol)
//   npm run login -- --url https://mi-app.com/ingresar
//
// Cuando termines de loguearte, volvé a la terminal y apretá Enter (o cerrá el navegador).
//
// Si la app tiene protección anti-bots (Cloudflare, DataDome, captcha…), este es el plan B: abre tu Google
// Chrome instalado (o el de NAVEGADOR_CANAL), resolvés el desafío o el captcha a mano y la sesión queda guardada.
// El archivo de sesión equivale a una contraseña: está en .gitignore y no se comparte.
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const readline = require('readline');
const { archivoSesion, RAIZ } = require('./sesion');

function argumentos(argv) {
  const opts = { url: '', nombre: '' };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--url' || a === '--nombre') {
      const v = argv[++i];
      if (!v || v.startsWith('--')) throw new Error(`falta el valor de ${a}`);
      opts[a.slice(2)] = v;
    } else if (a === '-h' || a === '--help') {
      opts.ayuda = true;
    } else {
      throw new Error(`opción desconocida: ${a}`);
    }
  }
  if (opts.url && !/^https?:\/\//i.test(opts.url)) throw new Error(`URL inválida: ${opts.url}`);
  archivoSesion(opts.nombre); // valida el nombre
  return opts;
}

/** Resuelve cuando la persona aprieta Enter en la terminal (si hay una terminal interactiva). */
function esperarEnter() {
  if (!process.stdin.isTTY) return { promesa: new Promise(() => {}), cerrar: () => {} };
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const promesa = new Promise((resolve) => rl.once('line', () => resolve('enter')));
  return { promesa, cerrar: () => rl.close() };
}

/** Resuelve cuando se cierran todas las pestañas del contexto. */
function esperarCierre(context) {
  return new Promise((resolve) => {
    const revisar = () => { if (context.pages().length === 0) resolve('cierre'); };
    const seguir = (p) => p.on('close', revisar);
    context.pages().forEach(seguir);
    context.on('page', seguir);
  });
}

async function main() {
  const opts = argumentos(process.argv.slice(2));
  if (opts.ayuda) {
    console.log('Uso: npm run login -- [--url https://mi-app.com/login] [--nombre admin]');
    return;
  }
  const url = opts.url || process.env.LOGIN_URL || process.env.APP_URL;
  if (!url) throw new Error('no hay URL: pasá --url o definí APP_URL en el .env');
  const archivo = archivoSesion(opts.nombre);
  const relativo = path.relative(RAIZ, archivo).split(path.sep).join('/');

  const { chromium } = require('playwright');
  // Con ventana y, si no se pidió otro canal, el Google Chrome instalado: es el navegador con el que una persona
  // resuelve el desafío o el captcha. Si no está, el Chromium de Playwright.
  const canalPedido = (process.env.NAVEGADOR_CANAL || '').trim();
  let browser;
  try {
    browser = await navegadorComun.lanzar(chromium, canalPedido ? { headless: false } : { headless: false, channel: 'chrome' });
  } catch (e) {
    if (canalPedido) throw e;
    browser = await navegadorComun.lanzar(chromium, { headless: false });
    console.log('No encontré Google Chrome instalado: uso el Chromium de Playwright.');
  }
  const enter = esperarEnter();
  try {
    const context = await browser.newContext({
      viewport: null, // la ventana con su tamaño normal, para loguearse cómodo
      locale: (process.env.LOCALE ?? 'es-AR').trim(),
      timezoneId: (process.env.TIMEZONE ?? 'America/Argentina/Mendoza').trim(),
    });
    const page = await context.newPage();
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });

    console.log(`\nSe abrió el navegador en ${url}`);
    console.log('1. Iniciá sesión como lo harías normalmente.');
    console.log(process.stdin.isTTY
      ? '2. Cuando estés adentro, volvé acá y apretá Enter (o cerrá el navegador).\n'
      : '2. Cuando estés adentro, cerrá el navegador.\n');

    const cerrado = new Promise((_, reject) =>
      browser.on('disconnected', () => reject(new Error('se cerró el navegador antes de guardar la sesión'))));
    await Promise.race([enter.promesa, esperarCierre(context), cerrado]);

    fs.mkdirSync(path.dirname(archivo), { recursive: true });
    const estado = await context.storageState({ path: archivo, indexedDB: true });
    const cookies = estado.cookies.length;
    const origenes = estado.origins.filter((o) => (o.localStorage?.length || 0) + (o.indexedDB?.length || 0) > 0).length;

    console.log(`Sesión guardada en ${relativo} (${cookies} cookies, ${origenes} orígenes con datos).`);
    if (cookies === 0 && origenes === 0) {
      console.log('Ojo: no se guardó ninguna cookie ni dato local. ¿Llegaste a iniciar sesión?');
    }
    const antibots = cookiesAntibots(estado.cookies);
    if (antibots.length) {
      console.log(`La sesión incluye cookies de la protección anti-bots (${antibots.join(', ')}). Suelen durar poco y`);
      console.log('valen solo para el mismo navegador e IP: corré las pruebas con el mismo NAVEGADOR_CANAL (chrome) y desde');
      console.log(`la misma red. Si igual las frena, pedí la excepción para QA (${navegadorComun.GUIA}).`);
    }
    const valor = opts.nombre || 'si';
    console.log(`Para usarla en npm test y en el navegador de los agentes: SESION=${valor} en el .env`);
    console.log('(el navegador de los agentes toma el cambio al reiniciar Claude Code).');
    console.log('Cuando la sesión venza, corré de nuevo este comando.');
  } finally {
    enter.cerrar();
    await browser.close().catch(() => undefined);
  }
}

if (require.main === module) {
  main().catch((e) => {
    console.error(`login: ${e.message}`);
    process.exit(1);
  });
}

// Cookies que dejan los desafíos anti-bots al resolverse (Cloudflare, DataDome, HUMAN, Akamai, Imperva, AWS WAF).
const COOKIES_ANTIBOTS = [/^cf_clearance$/, /^__cf_bm$/, /^datadome$/, /^_px(3|hd|vid)$/, /^_abck$/, /^bm_sv$/, /^ak_bmsc$/,
  /^incap_ses_/, /^reese84$/, /^aws-waf-token$/];
function cookiesAntibots(cookies) {
  return [...new Set((cookies || []).map((c) => c.name).filter((n) => COOKIES_ANTIBOTS.some((re) => re.test(n))))];
}

module.exports = { argumentos, cookiesAntibots };

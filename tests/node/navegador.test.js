// Navegador común de k0lmena (tools/navegador): configuración, detección de bloqueos anti-bots y, con un
// navegador real (si k0lmena está instalado), que el header de bypass llegue solo a los hosts de la app.
const test = require('node:test');
const assert = require('node:assert');
const http = require('http');
const path = require('path');

const nav = require('../../herramientas/k0lmena/tools/navegador/navegador');

test('config: canal, ritmo y bypass con los hosts de APP_URL', () => {
  const c = nav.leerConfig({ NAVEGADOR_CANAL: 'chrome', RITMO_HUMANO: 'si', QA_BYPASS_HEADER: 'X-QA-Bypass',
    QA_BYPASS_TOKEN: 'secreto', APP_URL: 'https://app.ejemplo.com/login' });
  assert.equal(c.canal, 'chrome');
  assert.equal(c.ritmoMs, 250);
  assert.deepEqual(c.bypass.hosts, ['app.ejemplo.com']);
  assert.equal(nav.leerConfig({}).bypass, null);
  assert.throws(() => nav.leerConfig({ NAVEGADOR_CANAL: 'firefox-stealth' }), /no es válido/);
  assert.throws(() => nav.leerConfig({ QA_BYPASS_HEADER: 'X-QA' }), /las dos/);
  assert.throws(() => nav.leerConfig({ QA_BYPASS_HEADER: 'X QA', QA_BYPASS_TOKEN: 't', APP_URL: 'https://a.com' }), /nombre de header/);
});

test('hosts: el header va a la app y sus subdominios, nunca a terceros', () => {
  const hosts = ['app.ejemplo.com'];
  assert.ok(nav.hostPermitido('app.ejemplo.com', hosts));
  assert.ok(nav.hostPermitido('api.app.ejemplo.com', hosts));
  assert.ok(!nav.hostPermitido('google-analytics.com', hosts));
  assert.ok(!nav.hostPermitido('app.ejemplo.com.atacante.net', hosts));
  assert.ok(!nav.hostPermitido('otroapp.ejemplo.com', hosts));
});

test('lanzamiento: el canal solo aplica a Chromium y lo explícito de la herramienta manda', () => {
  const env = { NAVEGADOR_CANAL: 'msedge', RITMO_HUMANO: '100' };
  assert.deepEqual(nav.opcionesLanzamiento('chromium', { headless: true }, env), { headless: true, channel: 'msedge', slowMo: 100 });
  assert.deepEqual(nav.opcionesLanzamiento('firefox', {}, env), { slowMo: 100 });
  assert.deepEqual(nav.opcionesLanzamiento('chromium', { slowMo: 5 }, env), { slowMo: 5, channel: 'msedge' });
});

test('detección: páginas de desafío y bloqueo de cada proveedor', () => {
  const casos = [
    [{ status: 403, headers: { 'cf-mitigated': 'challenge' } }, 'Cloudflare', 'desafio'],
    [{ status: 200, titulo: 'Just a moment...' }, 'Cloudflare', 'desafio'],
    [{ status: 403, html: '<div class="cf-error-details">Sorry, you have been blocked</div>' }, 'Cloudflare', 'bloqueo'],
    [{ status: 403, html: '<iframe src="https://geo.captcha-delivery.com/captcha/?initialCid=x">' }, 'DataDome', 'desafio'],
    [{ status: 403, html: '<div id="px-captcha"></div>' }, 'HUMAN (PerimeterX)', 'desafio'],
    [{ status: 403, html: '<title>Access Denied</title> ... Reference #18.abc' }, 'Akamai', 'bloqueo'],
    [{ status: 200, html: 'Request unsuccessful. Incapsula incident ID: 123' }, 'Imperva', 'bloqueo'],
    [{ status: 405, html: '<script src="https://x.token.awswaf.com/challenge.js">' }, 'AWS WAF', 'desafio'],
    [{ status: 200, html: '<div class="g-recaptcha" data-sitekey="x"></div>' }, 'reCAPTCHA', 'captcha'],
    [{ status: 429 }, 'desconocido', 'bloqueo'],
  ];
  for (const [entrada, proveedor, tipo] of casos) {
    const r = nav.clasificarBloqueo(entrada);
    assert.ok(r, `no detectó ${proveedor}`);
    assert.equal(r.proveedor, proveedor);
    assert.equal(r.tipo, tipo);
  }
});

test('detección: las páginas normales con scripts del proveedor no son un bloqueo', () => {
  const normales = [
    '<script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script><h1>Tienda</h1>',
    '<script src="https://js.datadome.co/tags.js"></script>',
    '<script src="//client.perimeterx.net/PX123/main.min.js"></script>',
    '<script src="/_Incapsula_Resource?SWJIYLWA=1"></script>',
    '<script src="https://abc.token.awswaf.com/abc/challenge.js"></script>',
  ];
  for (const html of normales) assert.equal(nav.clasificarBloqueo({ status: 200, html }), null, html);
});

let playwright = null;
try {
  playwright = require(require.resolve('playwright', { paths: [path.resolve(__dirname, '../../herramientas/k0lmena')] }));
} catch { /* sin k0lmena instalado (CI del repo): se saltea la prueba con navegador */ }

test('con navegador: header solo a la app, nada a terceros, y el desafío queda registrado', { skip: !playwright && 'k0lmena no instalado' }, async () => {
  const recibidos = [];
  const tercero = http.createServer((req, res) => {
    recibidos.push({ servidor: 'tercero', header: req.headers['x-qa-bypass'] });
    res.end('ok');
  });
  await new Promise((r) => tercero.listen(0, 'localhost', r));
  const app = http.createServer((req, res) => {
    recibidos.push({ servidor: 'app', ruta: req.url, header: req.headers['x-qa-bypass'] });
    if (req.url === '/desafio') {
      res.writeHead(403, { 'cf-mitigated': 'challenge', 'content-type': 'text/html' });
      return res.end('<title>Just a moment...</title>');
    }
    res.writeHead(200, { 'content-type': 'text/html' });
    res.end(`<h1>App</h1><img src="http://localhost:${tercero.address().port}/pixel.png">`);
  });
  await new Promise((r) => app.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${app.address().port}`;
  const browser = await nav.lanzar(playwright.chromium, { headless: true },
    { QA_BYPASS_HEADER: 'X-QA-Bypass', QA_BYPASS_TOKEN: 'token-de-prueba', APP_URL: base });
  try {
    const page = await browser.newPage();
    await page.goto(`${base}/`);
    await page.waitForLoadState('networkidle');
    await page.goto(`${base}/desafio`);
    await page.waitForTimeout(200);
  } finally {
    await browser.close();
    app.close();
    tercero.close();
  }
  assert.ok(recibidos.filter((r) => r.servidor === 'app').every((r) => r.header === 'token-de-prueba'));
  const delTercero = recibidos.filter((r) => r.servidor === 'tercero');
  assert.ok(delTercero.length >= 1, 'la página no pidió el recurso del tercero');
  assert.ok(delTercero.every((r) => r.header === undefined), 'el token se filtró a un tercero');
  assert.ok(nav.bloqueos.some((b) => b.proveedor === 'Cloudflare' && b.url.endsWith('/desafio')));
  assert.match(nav.resumenBloqueos(), /protección anti-bots/);
});

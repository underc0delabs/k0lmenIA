// Captura de analytics y píxeles (agente analista-analytics): qué tags carga la web y qué datos mandan.
//
// Uso (desde la raíz del repo):
//   npm run analytics -- [--url https://mi-app.com] [--paginas url1,url2] [--plan input/analytics/plan-medicion.json]
//                        [--consentimiento aceptar|rechazar|ninguno] [--selector-consentimiento "#onetrust-accept-btn-handler"]
//                        [--acciones input/analytics/acciones.json] [--espera 4000] [--historia HU-001] [--salida <carpeta>] [--headed]
//
// Por cada página (solo GET, como una persona que entra y mira):
//   1. Abre la página con un contexto limpio (sin cookies) y escucha TODOS los requests salientes.
//   2. Antes de tocar el banner de cookies, guarda qué se disparó (lo que sale sin consentimiento es hallazgo de privacidad).
//   3. Si se pide, acepta o rechaza el banner (--consentimiento) y vuelve a escuchar.
//   4. Corre las acciones del archivo --acciones (clic, completar, scroll, esperar) para disparar eventos de interacción
//      (add_to_cart, generate_lead, …). Las acciones con efecto (enviar un formulario real, pagar) las confirma la persona.
//   5. Lee el dataLayer, el estado de consent mode (gtag 'consent'), las cookies de analytics y los scripts de tags cargados.
//
// Los requests de proveedores conocidos (GA4, GTM, Google Ads, Floodlight, Meta, LinkedIn, TikTok, Hotjar, Clarity, Adobe,
// Segment, Mixpanel, Amplitude, Matomo, …) se guardan en captura.json; el análisis (decodificar cada hit, comparar contra el
// plan de medición, PII en los parámetros) lo hace herramientas/analytics/analytics.py, que también arma el informe.
//
// Deja todo en output/analytics/<HU o host>/ (captura.json, analytics.json, informe-analytics.html); la corrida anterior
// pasa a historial/ (se guardan las últimas 5).
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { normalizar, slug, sello, cargar } = require('../explorador/explorar.js');
const { archivar } = require('../historial/historial.js');

const { PROYECTO: RAIZ, CODIGO } = require('../rutas');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p);
const GENERADOS = ['captura.json', 'analytics.json', 'analisis.json', 'informe-analytics.html', 'es', 'en', 'capturas'];

// Hosts y rutas de los proveedores conocidos (el detalle de cada hit lo decodifica analytics.py).
const PROVEEDORES = [
  ['GA4', /(google-analytics\.com|analytics\.google\.com)\/(g\/collect|.*\/collect\?v=2)|\/g\/collect\?/i],
  ['Universal Analytics', /google-analytics\.com\/(r\/)?collect\?v=1|google-analytics\.com\/analytics\.js/i],
  ['Google Tag Manager', /googletagmanager\.com\/(gtm\.js|gtag\/js|ns\.html)/i],
  ['Google Ads', /(googleadservices\.com\/pagead\/conversion|googleads\.g\.doubleclick\.net\/pagead|google\.com\/pagead\/1p-conversion|google\.[a-z.]+\/ads\/ga-audiences)/i],
  ['Floodlight', /fls\.doubleclick\.net|ad\.doubleclick\.net\/activity/i],
  ['Meta Pixel', /(facebook\.com\/tr|connect\.facebook\.net\/.*\/fbevents\.js)/i],
  ['LinkedIn Insight', /(px\.ads\.linkedin\.com|snap\.licdn\.com|dc\.ads\.linkedin\.com)/i],
  ['TikTok Pixel', /analytics\.tiktok\.com/i],
  ['Hotjar', /(static\.hotjar\.com|script\.hotjar\.com|[a-z0-9-]+\.hotjar\.(com|io))/i],
  ['Microsoft Clarity', /(clarity\.ms)/i],
  ['Microsoft Ads (UET)', /bat\.bing\.com/i],
  ['Adobe Analytics', /(\/b\/ss\/|\.omtrdc\.net|\.2o7\.net|adobedc\.net|edge\.adobedc\.net)/i],
  ['Adobe Launch', /assets\.adobedtm\.com/i],
  ['Segment', /(api\.segment\.io|cdn\.segment\.com|events\.eu1\.segmentapis\.com)/i],
  ['Mixpanel', /(api(-js)?\.mixpanel\.com|api-eu\.mixpanel\.com|cdn\.mxpnl\.com)/i],
  ['Amplitude', /(api2?\.amplitude\.com|api\.eu\.amplitude\.com|cdn\.amplitude\.com)/i],
  ['Matomo', /(matomo\.php|piwik\.php|matomo\.js|piwik\.js)/i],
  ['Pinterest Tag', /ct\.pinterest\.com|s\.pinimg\.com\/ct\//i],
  ['X (Twitter) Pixel', /(analytics\.twitter\.com|static\.ads-twitter\.com|t\.co\/i\/adsct)/i],
];

function proveedorDe(url) {
  for (const [nombre, rx] of PROVEEDORES) if (rx.test(url)) return nombre;
  return null;
}

function argumentos(argv) {
  const a = { espera: 4000, consentimiento: 'ninguno', headed: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--plan') a.plan = v();
    else if (k === '--consentimiento') a.consentimiento = v();
    else if (k === '--selector-consentimiento') a.selectorConsentimiento = v();
    else if (k === '--acciones') a.acciones = v();
    else if (k === '--espera') a.espera = parseInt(v(), 10);
    else if (k === '--historia') a.historia = v();
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (!['aceptar', 'rechazar', 'ninguno'].includes(a.consentimiento)) throw new Error('--consentimiento tiene que ser aceptar, rechazar o ninguno.');
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  if (Number.isNaN(a.espera) || a.espera < 0) throw new Error('--espera tiene que ser un número de milisegundos.');
  return a;
}

// Botones típicos de los banners de cookies (OneTrust, Cookiebot, Didomi, Usercentrics, Complianz y genéricos).
const SELECTORES_CONSENTIMIENTO = {
  aceptar: ['#onetrust-accept-btn-handler', '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll', '#didomi-notice-agree-button',
    '[data-testid="uc-accept-all-button"]', '.cmplz-accept', 'button:has-text("Aceptar todas")', 'button:has-text("Aceptar todo")',
    'button:has-text("Aceptar")', 'button:has-text("Accept all")', 'button:has-text("Accept")'],
  rechazar: ['#onetrust-reject-all-handler', '#CybotCookiebotDialogBodyButtonDecline', '#didomi-notice-disagree-button',
    '[data-testid="uc-deny-all-button"]', '.cmplz-deny', 'button:has-text("Rechazar todas")', 'button:has-text("Rechazar")',
    'button:has-text("Reject all")', 'button:has-text("Reject")'],
};

async function resolverConsentimiento(page, modo, selector) {
  if (modo === 'ninguno') return { modo, clic: null };
  const candidatos = selector ? [selector] : SELECTORES_CONSENTIMIENTO[modo];
  for (const s of candidatos) {
    try {
      const el = page.locator(s).first();
      if (await el.isVisible({ timeout: 800 })) {
        await el.click({ timeout: 3000 });
        return { modo, clic: s };
      }
    } catch (e) { /* el siguiente */ }
  }
  return { modo, clic: null, aviso: 'No encontré el botón del banner de cookies: pasalo con --selector-consentimiento.' };
}

// Acciones para disparar eventos: [{"pagina": "url opcional", "accion": "clic|completar|scroll|esperar|ir", "selector": "...", "valor": "..."}]
async function correrAcciones(page, acciones, url) {
  const hechas = [];
  for (const ac of acciones.filter((x) => !x.pagina || normalizar(x.pagina) === url)) {
    const r = { ...ac };
    try {
      if (ac.accion === 'clic') await page.locator(ac.selector).first().click({ timeout: 8000 });
      else if (ac.accion === 'completar') await page.locator(ac.selector).first().fill(String(ac.valor ?? ''), { timeout: 8000 });
      else if (ac.accion === 'scroll') await page.evaluate((p) => window.scrollTo(0, document.documentElement.scrollHeight * (p / 100)), Number(ac.valor || 90));
      else if (ac.accion === 'esperar') await page.waitForTimeout(Number(ac.valor || 1000));
      else if (ac.accion === 'ir') await cargar(page, ac.valor);
      else throw new Error(`acción desconocida: ${ac.accion}`);
      await page.waitForTimeout(1200);
      r.ok = true;
    } catch (e) {
      r.ok = false;
      r.error = String(e.message || e).split('\n')[0].slice(0, 200);
    }
    hechas.push(r);
  }
  return hechas;
}

function _leerEnPagina() {
  const dl = Array.isArray(window.dataLayer) ? window.dataLayer : [];
  const seguro = (x) => { try { return JSON.parse(JSON.stringify(x, (k, v) => (typeof v === 'function' ? '[función]' : (v instanceof Element ? '[elemento]' : v)))); } catch (e) { return String(x); } };
  // gtag('consent', ...) queda en el dataLayer como un "arguments" con 'consent' en la primera posición.
  const consent = dl.filter((x) => x && typeof x === 'object' && x[0] === 'consent').map((x) => ({ tipo: x[1], estado: seguro(x[2]) }));
  const scripts = [...document.querySelectorAll('script[src]')].map((s) => s.src);
  return {
    titulo: document.title,
    data_layer: dl.slice(0, 200).map(seguro),
    consent_mode: consent,
    scripts,
    objetos: { gtag: typeof window.gtag === 'function', ga: typeof window.ga === 'function', fbq: typeof window.fbq === 'function',
      analytics_segment: !!(window.analytics && window.analytics.track), mixpanel: !!(window.mixpanel && window.mixpanel.track),
      amplitude: !!window.amplitude, _satellite: !!window._satellite, s_adobe: !!(window.s && window.s.t), _paq: Array.isArray(window._paq),
      _hjSettings: !!window._hjSettings, clarity: typeof window.clarity === 'function', ttq: !!window.ttq, _linkedin: !!window._linkedin_data_partner_ids },
  };
}

function generarInforme(carpeta, plan) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const args = [path.join(CODIGO, 'herramientas', 'analytics', 'analytics.py'), 'analizar', path.join(carpeta, 'captura.json')];
  if (plan) args.push('--plan', plan);
  const r = require('child_process').spawnSync(py, args, { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude analizar la captura (${motivo}). Corré: python herramientas/analytics/analytics.py analizar <carpeta>/captura.json`);
    return false;
  }
  process.stdout.write(r.stdout);
  return true;
}

async function main() {
  const a = argumentos(process.argv.slice(2));
  if (a.ayuda) {
    console.log(fs.readFileSync(__filename, 'utf8').split('\n').filter((l) => l.startsWith('//')).map((l) => l.slice(3)).join('\n'));
    return;
  }
  const url = a.url || (a.paginas && a.paginas[0]) || process.env.APP_URL || process.env.BASEURL;
  if (!url) throw new Error('No hay URL: pasala con --url o definí APP_URL en el .env de la raíz.');
  if (!/^https?:\/\//i.test(url)) throw new Error(`La URL tiene que empezar con http:// o https:// (recibí "${url}").`);
  const paginas = [...new Set([url, ...(a.paginas || [])].map(normalizar))];
  const host = new URL(paginas[0]).hostname;
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'analytics', a.historia || host);
  const plan = a.plan ? desde(a.plan) : null;
  if (plan && !fs.existsSync(plan)) throw new Error(`No existe el plan de medición ${plan}.`);
  const acciones = a.acciones ? JSON.parse(fs.readFileSync(desde(a.acciones), 'utf8')) : [];
  if (!Array.isArray(acciones)) throw new Error('--acciones tiene que ser una lista JSON de acciones.');
  archivar(carpeta, GENERADOS, 'captura.json');
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });
  const dirCap = path.join(carpeta, 'capturas');
  fs.mkdirSync(dirCap, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');
  const relRaiz = (p) => path.relative(RAIZ, p).split(path.sep).join('/');

  const { chromium } = require('playwright');
  const browser = await navegadorComun.lanzar(chromium, { headless: !a.headed });
  const t0 = Date.now();
  console.log(`Analytics: ${paginas.length} página(s) · consentimiento ${a.consentimiento} · salida ${relRaiz(carpeta)}`);
  const resultadoPaginas = [];
  for (const [i, u] of paginas.entries()) {
    const id = `${String(i + 1).padStart(2, '0')}-${slug(u)}`;
    const ctx = await browser.newContext({ locale: process.env.LOCALE || 'es-AR' });
    const page = await ctx.newPage();
    const hits = [];
    let fase = 'sin_consentimiento';
    const terceros = new Set();
    page.on('request', (req) => {
      const ru = req.url();
      let h = '';
      try { h = new URL(ru).hostname; } catch (e) { return; }
      if (h && h !== new URL(u).hostname) terceros.add(h);
      const prov = proveedorDe(ru);
      if (!prov) return;
      let cuerpo = null;
      try { cuerpo = req.postData(); } catch (e) { cuerpo = null; }
      hits.push({ proveedor: prov, url: ru.slice(0, 4000), metodo: req.method(), cuerpo: cuerpo ? cuerpo.slice(0, 8000) : null,
        tipo: req.resourceType(), fase, ms: Date.now() - t0 });
    });
    const estados = new Map();
    page.on('response', (res) => { if (proveedorDe(res.url())) estados.set(res.url().slice(0, 4000), res.status()); });
    const p = { pagina: id, url: u };
    process.stdout.write(`${u} `);
    try {
      await cargar(page, u);
      await page.waitForTimeout(a.espera);
      p.antes_de_consentir = await page.evaluate(_leerEnPagina);
      fase = 'con_consentimiento';
      p.consentimiento = await resolverConsentimiento(page, a.consentimiento, a.selectorConsentimiento);
      if (p.consentimiento.clic) await page.waitForTimeout(a.espera);
      fase = 'acciones';
      p.acciones = await correrAcciones(page, acciones, u);
      await page.waitForTimeout(1500);
      p.estado = await page.evaluate(_leerEnPagina);
      p.cookies = (await ctx.cookies()).map((c) => ({ nombre: c.name, dominio: c.domain, expira: c.expires, httpOnly: c.httpOnly }));
      const arch = path.join(dirCap, `${id}.png`);
      await page.screenshot({ path: arch });
      p.captura = rel(arch);
    } catch (e) {
      p.error = String(e.message || e).split('\n')[0].slice(0, 200);
    }
    p.hits = hits.map((h) => ({ ...h, status: estados.get(h.url) ?? null }));
    p.terceros = [...terceros].sort();
    console.log(`→ ${hits.length} hit(s) de analytics${p.error ? ` · error: ${p.error}` : ''}`);
    resultadoPaginas.push(p);
    await ctx.close();
  }
  await browser.close();
  const captura = {
    host, historia: a.historia || null, fecha: new Date().toISOString(), marca: sello(), duracion_s: Math.round((Date.now() - t0) / 1000),
    herramienta: `Playwright ${require('playwright/package.json').version}`, consentimiento: a.consentimiento,
    plan: plan ? relRaiz(plan) : null, paginas: resultadoPaginas,
  };
  const salida = path.join(carpeta, 'captura.json');
  fs.writeFileSync(salida, JSON.stringify(captura, null, 2), 'utf8');
  console.log(`\nCaptura: ${relRaiz(salida)}`);
  generarInforme(carpeta, plan);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, proveedorDe, PROVEEDORES, SELECTORES_CONSENTIMIENTO, GENERADOS };

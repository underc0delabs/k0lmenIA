// Navegador común de k0lmena: cómo se lanza Chromium/Chrome y qué se le agrega a cada contexto para que
// la app bajo prueba no confunda al QA con un bot. Lo usan el hook de npm test y las herramientas
// (explorar, accesibilidad, mapa funcional, …). Ver tools/navegador/README.md.
//
// Variables del .env (todas opcionales):
//   NAVEGADOR_CANAL=chrome|msedge     usar el Chrome o Edge instalado en vez del Chromium de Playwright
//   RITMO_HUMANO=si|<ms>              pausa entre acciones (slowMo): "si" = 250 ms
//   QA_BYPASS_HEADER=X-QA-Bypass      header acordado con el equipo de la app para dejar pasar al QA
//   QA_BYPASS_TOKEN=<secreto>         su valor (secreto: va solo en el .env)
//   QA_BYPASS_HOSTS=app.com,api.app.com  hosts que reciben el header (por defecto, el de APP_URL y sus subdominios)
//
// El header se agrega SOLO a los requests de esos hosts (nunca a analytics, CDNs ni otros terceros), con
// context.route; por eso, con el bypass activo, se bloquean los service workers (sus requests no pasan por route).
//
// No disfraza el navegador ni intenta engañar al detector: la salida para una app protegida es la excepción
// oficial (header, IP o claves de prueba de captcha) que da el equipo dueño de la app.
'use strict';

const GUIA = 'herramientas/k0lmena/tools/navegador/README.md';
const CANALES = new Set(['chrome', 'chrome-beta', 'msedge', 'msedge-beta']);
const NOMBRE_HEADER = /^[A-Za-z0-9-]{1,64}$/;

function leerConfig(env = process.env) {
  const canal = (env.NAVEGADOR_CANAL || '').trim().toLowerCase();
  if (canal && !CANALES.has(canal)) {
    throw new Error(`NAVEGADOR_CANAL="${canal}" no es válido: usá chrome o msedge (o dejalo vacío para el Chromium de Playwright).`);
  }
  const ritmo = (env.RITMO_HUMANO || '').trim().toLowerCase();
  const ritmoMs = ['si', 'sí', 'true', '1'].includes(ritmo) ? 250 : (/^\d+$/.test(ritmo) ? Number(ritmo) : 0);

  const nombre = (env.QA_BYPASS_HEADER || '').trim();
  const valor = (env.QA_BYPASS_TOKEN || '').trim();
  let bypass = null;
  if (nombre || valor) {
    if (!nombre || !valor) throw new Error('Para el bypass hacen falta QA_BYPASS_HEADER y QA_BYPASS_TOKEN (las dos).');
    if (!NOMBRE_HEADER.test(nombre)) throw new Error(`QA_BYPASS_HEADER="${nombre}" no es un nombre de header válido.`);
    bypass = { nombre, valor, hosts: hostsPermitidos(env) };
    if (!bypass.hosts.length) throw new Error('El bypass necesita APP_URL o QA_BYPASS_HOSTS para saber a qué hosts mandar el header.');
  }
  return { canal: canal || null, ritmoMs, bypass };
}

function hostsPermitidos(env = process.env) {
  const lista = (env.QA_BYPASS_HOSTS || '').split(',').map((h) => h.trim().toLowerCase()).filter(Boolean);
  if (lista.length) return lista;
  const url = env.APP_URL || env.BASEURL || '';
  try {
    return url ? [new URL(url).hostname.toLowerCase()] : [];
  } catch {
    return [];
  }
}

/** true si el host es uno de los permitidos o un subdominio suyo (api.app.com vale para app.com). */
function hostPermitido(host, hosts) {
  const h = String(host || '').toLowerCase();
  return hosts.some((p) => h === p || h.endsWith(`.${p}`));
}

/** Opciones de launch con el canal (solo Chromium) y el ritmo humano. Lo explícito de la herramienta manda. */
function opcionesLanzamiento(nombreNavegador, base = {}, env = process.env) {
  const c = leerConfig(env);
  const opciones = { ...base };
  if (c.canal && nombreNavegador === 'chromium' && !('channel' in base)) opciones.channel = c.canal;
  if (c.ritmoMs && !base.slowMo) opciones.slowMo = c.ritmoMs;
  return opciones;
}

// ---------------------------------------------------------------------------- detección de bloqueos

// Solo firmas de las PÁGINAS de desafío o bloqueo: muchas apps protegidas cargan en sus páginas normales los
// scripts del proveedor (/cdn-cgi/challenge-platform, js.datadome.co, client.perimeterx.net, awswaf), y eso no
// es un bloqueo. [proveedor, tipo, regex sobre el HTML/título, condición sobre el status HTTP]
const FIRMAS = [
  ['Cloudflare', 'desafio', /_cf_chl_opt|cf-chl-|<title>\s*(Just a moment|Un momento|Attention Required! \| Cloudflare)/i],
  ['Cloudflare', 'bloqueo', /Sorry, you have been blocked|cf-error-details/i, (s) => s >= 400],
  ['DataDome', 'desafio', /captcha-delivery\.com/i],
  ['HUMAN (PerimeterX)', 'desafio', /px-captcha|_pxCaptcha/i],
  ['Akamai', 'bloqueo', /errors\.edgesuite\.net|<title>\s*Access Denied\s*<\/title>[\s\S]*Reference\s*#/i, (s) => s >= 400],
  ['Imperva', 'bloqueo', /Incapsula incident|Request unsuccessful\. Incapsula/i],
  ['Imperva', 'bloqueo', /_Incapsula_Resource/i, (s) => s >= 400],
  ['AWS WAF', 'desafio', /awswaf|aws-waf-token/i, (s) => s === 202 || s === 405 || s >= 400],
  ['Cloudflare Turnstile', 'captcha', /challenges\.cloudflare\.com\/turnstile/i],
  ['reCAPTCHA', 'captcha', /google\.com\/recaptcha|recaptcha\.net\/recaptcha|class="g-recaptcha/i],
  ['hCaptcha', 'captcha', /hcaptcha\.com\/1\/api|class="h-captcha/i],
];

/**
 * Clasifica una respuesta o una página: {proveedor, tipo, motivo} si parece un bloqueo anti-bots, o null.
 * tipo: "desafio" (página de verificación en lugar de la app), "bloqueo" (acceso denegado) o "captcha"
 * (la página cargó, pero tiene un captcha que la automatización no puede resolver).
 */
function clasificarBloqueo({ status = 200, headers = {}, html = '', titulo = '' } = {}) {
  const h = Object.fromEntries(Object.entries(headers || {}).map(([k, v]) => [k.toLowerCase(), String(v)]));
  if ((h['cf-mitigated'] || '').toLowerCase() === 'challenge') {
    return { proveedor: 'Cloudflare', tipo: 'desafio', motivo: 'cf-mitigated: challenge' };
  }
  if (h['x-datadome'] || /datadome/i.test(h.server || '')) {
    if (status >= 400) return { proveedor: 'DataDome', tipo: 'desafio', motivo: `HTTP ${status} de DataDome` };
  }
  const texto = `${titulo ? `<title>${titulo}</title>` : ''}\n${String(html).slice(0, 200000)}`;
  for (const [proveedor, tipo, re, extra] of FIRMAS) {
    if (re.test(texto) && (!extra || extra(status))) {
      return { proveedor, tipo, motivo: `HTTP ${status} · firma de ${proveedor}` };
    }
  }
  if (status === 429) return { proveedor: 'desconocido', tipo: 'bloqueo', motivo: 'HTTP 429 (demasiadas solicitudes)' };
  return null;
}

const bloqueos = [];
let avisoRegistrado = false;

function registrarBloqueo(b, url) {
  if (bloqueos.some((x) => x.url === url && x.proveedor === b.proveedor)) return;
  bloqueos.push({ ...b, url });
  if (!avisoRegistrado) {
    avisoRegistrado = true;
    process.once('exit', () => {
      if (bloqueos.length) console.error(`\n${resumenBloqueos()}\n`);
    });
  }
}

function resumenBloqueos(lista = bloqueos) {
  if (!lista.length) return '';
  const lineas = lista.map((b) => `  - ${b.proveedor} (${b.tipo}) en ${b.url} — ${b.motivo}`);
  return [
    'ATENCIÓN: la app frenó al navegador automatizado con su protección anti-bots. Lo que falló ahí no es un bug de la app:',
    ...lineas,
    `Qué hacer: pedile al equipo de la app una excepción para QA (header QA_BYPASS_*, IP o claves de prueba del captcha) o`,
    `iniciá sesión a mano con npm run login y SESION en el .env. Guía: ${GUIA}`,
  ].join('\n');
}

/** Revisa la página actual (para el hook de npm test cuando un escenario falla). */
async function detectarEnPagina(page) {
  try {
    const [html, titulo] = await Promise.all([page.content(), page.title()]);
    return clasificarBloqueo({ status: 200, html, titulo });
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------- contextos

async function prepararContexto(context, config) {
  const { bypass } = config;
  if (bypass) {
    // fallback (y no continue): si la herramienta tiene sus propias rutas (resiliencia), siguen funcionando.
    await context.route('**/*', (route) => {
      const req = route.request();
      let host = '';
      try { host = new URL(req.url()).hostname; } catch { /* data:, blob: */ }
      if (!hostPermitido(host, bypass.hosts)) return route.fallback();
      return route.fallback({ headers: { ...req.headers(), [bypass.nombre.toLowerCase()]: bypass.valor } });
    });
  }
  context.on('response', async (resp) => {
    try {
      const req = resp.request();
      if (!req.isNavigationRequest() || req.frame() !== req.frame().page().mainFrame()) return;
      const headers = resp.headers();
      const s = resp.status();
      if (s < 400 && s !== 202 && (headers['cf-mitigated'] || '').toLowerCase() !== 'challenge') return;
      const html = await resp.text().catch(() => '');
      const b = clasificarBloqueo({ status: resp.status(), headers, html });
      if (b) registrarBloqueo(b, resp.url());
    } catch { /* la página se cerró: nada que revisar */ }
  });
}

function opcionesContexto(base, config) {
  return config.bypass && !('serviceWorkers' in (base || {})) ? { ...(base || {}), serviceWorkers: 'block' } : (base || {});
}

/**
 * Lanza el navegador con las opciones comunes y lo deja "instrumentado": cada contexto que se cree desde él
 * (newContext o newPage) recibe el header de bypass para los hosts de la app y la detección de bloqueos.
 */
async function lanzar(browserType, base = {}, env = process.env) {
  const config = leerConfig(env);
  const browser = await browserType.launch(opcionesLanzamiento(browserType.name(), base, env));
  const newContext = browser.newContext.bind(browser);
  browser.newContext = async (opciones) => {
    const ctx = await newContext(opcionesContexto(opciones, config));
    await prepararContexto(ctx, config);
    return ctx;
  };
  browser.newPage = async (opciones) => {
    const ctx = await browser.newContext(opciones);
    const page = await ctx.newPage();
    page.once('close', () => ctx.close().catch(() => {}));
    return page;
  };
  return browser;
}

/** Para avisar al arrancar qué está activo (sin mostrar el token). */
function descripcion(env = process.env) {
  const c = leerConfig(env);
  const partes = [];
  if (c.canal) partes.push(`canal ${c.canal}`);
  if (c.ritmoMs) partes.push(`ritmo humano ${c.ritmoMs} ms`);
  if (c.bypass) partes.push(`header ${c.bypass.nombre} para ${c.bypass.hosts.join(', ')}`);
  return partes.join(' · ');
}

module.exports = {
  GUIA, leerConfig, hostsPermitidos, hostPermitido, opcionesLanzamiento, clasificarBloqueo, detectarEnPagina,
  resumenBloqueos, registrarBloqueo, bloqueos, lanzar, prepararContexto, opcionesContexto, descripcion,
};

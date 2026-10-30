// Prueba de resiliencia de la interfaz (agente probador-resiliencia).
//
// Uso (desde la raíz del repo):
//   npm run resiliencia -- [--url https://mi-app.com] [--paginas url1,url2] [--max-paginas 5] [--profundidad 1]
//                          [--escenarios api-500,timeout,lenta,offline,vacia,malformada,estaticos]
//                          [--patron-api "/api/"] [--timeout-ms 8000] [--historia HU-001] [--headed]
//
// Para cada página, primero la carga normal (la línea base) y después, en un contexto limpio por escenario,
// simula que falla lo que está "abajo" de la interfaz y mira cómo reacciona:
//   api-500 · api-503 · api-404   las llamadas a la API responden con ese error
//   timeout                       las llamadas a la API nunca responden (respuesta colgada)
//   lenta                         red lenta: latencia de 2 s y poco ancho de banda (Chromium, vía CDP)
//   offline                       la página carga y después se corta la conexión (y se intenta navegar)
//   vacia · malformada · nulos     la API responde 200 con cuerpo vacío, JSON roto o todos los campos en null
//   estaticos                     no cargan los CSS, JS, imágenes ni fuentes
// Por escenario: captura, errores de JavaScript, errores de consola, mensajes de error visibles, si quedó en
// blanco, si quedó un spinner girando, reintentos (la misma llamada repetida), mensajes técnicos a la vista y
// si la página se recupera cuando vuelve la red. Arma hallazgos con severidad.
//
// Seguridad: solo intercepta y responde DESDE EL NAVEGADOR. No ataca al servidor ni genera carga: a lo sumo
// hace la misma cantidad de pedidos que una visita normal (y en los escenarios de falla, ni siquiera llegan).
// No envía formularios: cualquier navegación que no sea GET se corta.
// Las llamadas a la API son las fetch/XHR (o las que coincidan con --patron-api). Si una página no hace
// llamadas, los escenarios de API quedan como "No aplica".
//
// Deja todo en output/resiliencia/<HU o host>/ (resiliencia.json, informe-resiliencia.html, capturas/); la
// corrida anterior pasa a historial/ (se guardan las últimas 5).
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { normalizar, slug, sello, cargar } = require('../explorador/explorar.js');
const { descubrir } = require('../pixel-perfect/pixel-perfect.js');
const { archivar } = require('../historial/historial.js');

// Datos (output/, input/, .auth/) en el proyecto y scripts de Python en el código de k0lmenIA: ver ../rutas.js.
const { PROYECTO: RAIZ, CODIGO } = require('../rutas');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p);
const GENERADOS = ['resiliencia.json', 'analisis.json', 'informe-resiliencia.html', 'capturas'];
const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };

const ESCENARIOS = {
  'api-500': { nombre: 'La API responde 500', tipo: 'api', status: 500 },
  'api-503': { nombre: 'La API responde 503 (no disponible)', tipo: 'api', status: 503 },
  'api-404': { nombre: 'La API responde 404', tipo: 'api', status: 404 },
  timeout: { nombre: 'La API no responde (timeout)', tipo: 'api' },
  lenta: { nombre: 'Red lenta (2 s de latencia)', tipo: 'red' },
  offline: { nombre: 'Se corta la conexión', tipo: 'red' },
  vacia: { nombre: 'La API responde vacío', tipo: 'api' },
  malformada: { nombre: 'La API responde JSON roto', tipo: 'api' },
  nulos: { nombre: 'La API responde con campos en null', tipo: 'api' },
  estaticos: { nombre: 'No cargan CSS, JS, imágenes ni fuentes', tipo: 'estaticos' },
};
const ESTATICOS = new Set(['stylesheet', 'script', 'image', 'font']);
// Mensajes técnicos que no deberían llegar a la persona.
const TECNICO = /(Internal Server Error|Service Unavailable|SyntaxError|Unexpected (token|end of JSON)|TypeError|ReferenceError|\bundefined\b|\bNaN\b|\[object Object\]|stack ?trace|Traceback|Exception\b|at [\w.$]+ \(.*:\d+:\d+\))/;

function argumentos(argv) {
  const a = { maxPaginas: 5, profundidad: 1, headed: false, timeoutMs: 8000, escenarios: Object.keys(ESCENARIOS), patronApi: null };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--escenarios') a.escenarios = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--patron-api') a.patronApi = v();
    else if (k === '--timeout-ms') a.timeoutMs = parseInt(v(), 10);
    else if (k === '--historia') a.historia = v();
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  const malos = a.escenarios.filter((x) => !ESCENARIOS[x]);
  if (malos.length) throw new Error(`Escenario desconocido: ${malos.join(', ')}. Opciones: ${Object.keys(ESCENARIOS).join(', ')}`);
  if (!a.escenarios.length) throw new Error('--escenarios no puede quedar vacío.');
  if (!(a.maxPaginas >= 1 && a.maxPaginas <= 50)) throw new Error('--max-paginas tiene que estar entre 1 y 50.');
  if (!(a.timeoutMs >= 1000 && a.timeoutMs <= 120000)) throw new Error('--timeout-ms tiene que estar entre 1000 y 120000.');
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  if (a.patronApi) new RegExp(a.patronApi); // valida (lanza si es inválido)
  return a;
}

// Analítica y telemetría de terceros: no son la API de la app (que fallen no le cambia nada a la persona).
const TELEMETRIA = /(\/cdn-cgi\/|google-analytics|googletagmanager|doubleclick|analytics\.|\/collect\b|sentry|hotjar|segment\.(io|com)|clarity\.ms|newrelic|nr-data|datadoghq|mixpanel|amplitude|facebook\.com\/tr|fullstory|intercom)/i;

// ¿El pedido es una llamada a la API? Por patrón (si se pasó) o por tipo (fetch / XHR), sin la telemetría.
function esApi(url, tipoRecurso, patron) {
  if (patron) return new RegExp(patron).test(url);
  return (tipoRecurso === 'fetch' || tipoRecurso === 'xhr') && !TELEMETRIA.test(url);
}

// Todos los valores finales en null, conservando la estructura (claves y largo de las listas).
function anularCampos(v) {
  if (Array.isArray(v)) return v.map(anularCampos);
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, anularCampos(x)]));
  return null;
}

// Respuesta simulada para un escenario de API (null = no se responde: timeout; o hace falta la respuesta real).
function respuestaSimulada(escenario, cuerpoReal) {
  const json = { 'Content-Type': 'application/json; charset=utf-8' };
  const e = ESCENARIOS[escenario];
  if (e && e.status) return { status: e.status, headers: json, body: JSON.stringify({ error: e.status === 404 ? 'Not Found' : e.status === 503 ? 'Service Unavailable' : 'Internal Server Error' }) };
  if (escenario === 'vacia') return { status: 200, headers: json, body: '' };
  if (escenario === 'malformada') return { status: 200, headers: json, body: '{"datos": [{"id": 1, "nombre": "' };
  if (escenario === 'nulos') {
    let d = null;
    try { d = JSON.parse(cuerpoReal); } catch { return { status: 200, headers: json, body: 'null' }; }
    return { status: 200, headers: json, body: JSON.stringify(anularCampos(d)) };
  }
  return null;
}

// La misma llamada repetida: reintentos = veces que se pidió de más la URL más repetida.
function contarReintentos(urls) {
  const c = new Map();
  for (const u of urls) c.set(u, (c.get(u) || 0) + 1);
  let max = 0;
  let url = null;
  for (const [u, n] of c) if (n > max) { max = n; url = u; }
  return { reintentos: Math.max(0, max - 1), url: max > 1 ? url : null };
}

// Corre en el navegador: qué ve la persona.
function _observar() {
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && cs.opacity !== '0'; };
  const texto = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  const body = document.body;
  const todo = body ? texto(body) : '';
  const elementos = body ? [...body.querySelectorAll('*')].filter(visible).length : 0;
  const ERR = /(error|fall[oó]|no se pudo|no pudimos|intent[aá] (de nuevo|nuevamente|m[aá]s tarde)|sin conexi[oó]n|offline|problema|no disponible|unavailable|try again|something went wrong|algo sali[oó] mal|reintentar)/i;
  const candidatos = [...document.querySelectorAll('[role=alert], [role=alertdialog], [role=status], [aria-live], .alert, .error, .toast, .notification, .snackbar, .message, h1, h2, h3, p, span, div')]
    .filter((el) => visible(el) && el.children.length <= 3);
  const mensajes = [...new Set(candidatos.map(texto).filter((t) => t.length > 3 && t.length < 220 && ERR.test(t)))].slice(0, 8);
  const SPIN = /(spin|loader|loading|cargando|skeleton|progress|busy)/i;
  const spinners = [...document.querySelectorAll('[aria-busy=true], [role=progressbar], progress, [class*=spin], [class*=load], [class*=skeleton], [class*=progress]')]
    .filter((el) => visible(el) && (el.getAttribute('aria-busy') === 'true' || el.getAttribute('role') === 'progressbar' || el.tagName === 'PROGRESS' || SPIN.test(el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className || ''))).length;
  return { url: location.href, titulo: document.title, texto_len: todo.length, elementos, mensajes, spinners, muestra: todo.slice(0, 4000) };
}

// Hallazgos de un escenario a partir de la línea base y lo observado.
function evaluar(base, r) {
  const h = [];
  const add = (severidad, tipo, titulo, detalle) => h.push({ severidad, tipo, titulo, detalle });
  const e = ESCENARIOS[r.escenario];
  if (r.estado === 'no-aplica' || r.estado === 'error') return h;
  const o = r.observado || {};
  const pantallaError = /^chrome-error:|^about:blank/.test(o.url || '');
  const umbralTexto = Math.max(30, Math.round((base.texto_len || 0) * 0.15));
  const umbralElem = Math.max(5, Math.round((base.elementos || 0) * 0.15));
  const enBlanco = !pantallaError && ((o.texto_len || 0) < umbralTexto || (o.elementos || 0) < umbralElem);
  const tecnico = (o.muestra || '').match(TECNICO);
  const nuevosJs = (r.errores_js || []).filter((x) => !(base.errores_js || []).includes(x));

  if (r.escenario === 'offline') {
    if (pantallaError) add('Baja', 'Sin conexión', 'Sin conexión, la app no avisa: aparece la página de error del navegador', 'Al cortar la conexión y navegar se ve la página de error del navegador. Si la app tiene que funcionar o avisar sin conexión, falta ese manejo (service worker, mensaje propio).');
    else if (!(o.mensajes || []).length && r.navego) add('Media', 'Falla silenciosa', 'Sin conexión, la app no avisa que no hay red', 'Se cortó la conexión y se intentó navegar: la página no muestra ningún aviso.');
  } else if (enBlanco) {
    add(e.tipo === 'estaticos' ? 'Media' : 'Alta', 'Pantalla en blanco', `${e.nombre}: la pantalla queda casi vacía`,
      `Quedan ${o.texto_len || 0} caracteres de texto y ${o.elementos || 0} elementos visibles (en la carga normal: ${base.texto_len} y ${base.elementos}).`
      + ((o.mensajes || []).length ? '' : ' Tampoco hay un mensaje que explique qué pasó.'));
  } else if (e.tipo === 'api' && r.interceptados > 0 && !(o.mensajes || []).length && r.cambio_contenido) {
    add('Media', 'Falla silenciosa', `${e.nombre}: la página cambia pero no avisa que algo falló`,
      'Falta contenido que en la carga normal aparece y no hay ningún mensaje de error visible: la persona no sabe que algo salió mal ni qué hacer.');
  }
  if ((o.spinners || 0) > 0 && (base.spinners || 0) === 0 && ['timeout', 'lenta', 'api-500', 'api-503', 'api-404', 'malformada', 'vacia', 'nulos'].includes(r.escenario)) {
    add(r.escenario === 'lenta' ? 'Baja' : 'Media', 'Carga infinita', `${e.nombre}: queda un indicador de carga girando`,
      `Después de ${Math.round((r.espera_ms || 0) / 1000)} s sigue visible un indicador de carga (${o.spinners}). Si la respuesta no llega, la persona espera para siempre.`);
  }
  if (tecnico && !(base.muestra || '').match(TECNICO)) {
    add('Media', 'Mensaje técnico', `${e.nombre}: se ve un mensaje técnico`, `Aparece “${tecnico[0]}” en la pantalla. La persona tendría que ver un mensaje claro, no el error interno.`);
  }
  if (nuevosJs.length) {
    add(e.tipo === 'estaticos' ? 'Baja' : 'Media', 'Error de JavaScript', `${e.nombre}: errores de JavaScript sin capturar`,
      `${nuevosJs.length} error(es) que no aparecen en la carga normal, por ejemplo: ${nuevosJs[0]}`);
  }
  if (r.reintentos > 3) {
    add('Media', 'Reintentos sin control', `${e.nombre}: la misma llamada se repite ${r.reintentos + 1} veces`,
      `${r.reintentos_url} se pidió ${r.reintentos + 1} veces en ${Math.round((r.espera_ms || 0) / 1000)} s. Sin un límite ni espera entre intentos, una caída del servidor se agrava con la carga de todos los usuarios.`);
  }
  if (r.recuperacion && r.recuperacion.recupera === false) {
    add('Alta', 'No se recupera', `${e.nombre}: cuando vuelve la red la página no se recupera`,
      `Al quitar la falla y recargar, la página sigue con ${r.recuperacion.texto_len} caracteres de texto (normal: ${base.texto_len}).`);
  }
  return h;
}

// ¿Cambió el contenido respecto de la línea base? (falta una parte importante del texto)
function cambioContenido(base, o) {
  if (!base || !o) return false;
  return (o.texto_len || 0) < (base.texto_len || 0) * 0.85;
}

function resumir(paginas, hallazgos) {
  const res = paginas.flatMap((p) => p.resultados);
  return {
    paginas: paginas.length, escenarios: [...new Set(res.map((r) => r.escenario))].length, pruebas: res.length,
    ok: res.filter((r) => r.estado === 'ok').length, con_hallazgos: res.filter((r) => r.estado === 'hallazgo').length,
    no_aplica: res.filter((r) => r.estado === 'no-aplica').length, errores: res.filter((r) => r.estado === 'error').length,
    hallazgos: hallazgos.length, pantallas_blanco: hallazgos.filter((h) => h.tipo === 'Pantalla en blanco').length,
    sin_recuperacion: hallazgos.filter((h) => h.tipo === 'No se recupera').length,
    fallas_silenciosas: hallazgos.filter((h) => h.tipo === 'Falla silenciosa').length,
    por_severidad: Object.fromEntries(Object.keys(SEV_ORDEN).map((s) => [s, hallazgos.filter((h) => h.severidad === s).length])),
  };
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(CODIGO, 'scripts', 'generar_informe_resiliencia.py'), path.join(carpeta, 'resiliencia.json'),
    path.join(carpeta, 'informe-resiliencia.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_resiliencia.py <carpeta>/resiliencia.json <carpeta>/informe-resiliencia.html`);
    return false;
  }
  return true;
}

// Contexto limpio con: bloqueo de envíos, registro de errores y pedidos.
async function nuevoContexto(browser, reg) {
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, locale: process.env.LOCALE || 'es-AR', serviceWorkers: 'block' });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => reg.errores_js.push(String(e.message || e).split('\n')[0].slice(0, 300)));
  page.on('console', (m) => { if (m.type() === 'error') reg.consola.push(m.text().slice(0, 300)); });
  return { ctx, page };
}

async function observar(page) {
  return page.evaluate(_observar).catch(() => ({ url: page.url(), titulo: '', texto_len: 0, elementos: 0, mensajes: [], spinners: 0, muestra: '' }));
}

async function lineaBase(browser, u, a) {
  const reg = { errores_js: [], consola: [], api: [] };
  const { ctx, page } = await nuevoContexto(browser, reg);
  await page.route('**/*', (route) => {
    const rq = route.request();
    if (rq.isNavigationRequest() && rq.method() !== 'GET') return route.abort();
    if (esApi(rq.url(), rq.resourceType(), a.patronApi)) reg.api.push(`${rq.method()} ${rq.url()}`);
    return route.continue();
  });
  const t0 = Date.now();
  let error = null;
  try { await cargar(page, u); } catch (e) { error = String(e.message || e).split('\n')[0]; }
  await page.waitForTimeout(800);
  const o = await observar(page);
  await ctx.close();
  return { ...o, tiempo_ms: Date.now() - t0, errores_js: reg.errores_js, consola: reg.consola, llamadas_api: [...new Set(reg.api)], error };
}

async function probarEscenario(browser, u, escenario, base, a, dirCap, n) {
  const e = ESCENARIOS[escenario];
  const reg = { errores_js: [], consola: [], api: [] };
  const r = { escenario, nombre: e.nombre, estado: 'ok', interceptados: 0, reintentos: 0, reintentos_url: null, errores_js: [], consola: [] };
  if (e.tipo === 'api' && !base.llamadas_api.length) {
    return { ...r, estado: 'no-aplica', motivo: 'La página no hace llamadas a la API en la carga (fetch/XHR).' };
  }
  const { ctx, page } = await nuevoContexto(browser, reg);
  const colgados = [];
  let fallando = true;
  await page.route('**/*', async (route) => {
    const rq = route.request();
    if (rq.isNavigationRequest() && rq.method() !== 'GET') return route.abort();
    if (!fallando) return route.continue();
    const api = esApi(rq.url(), rq.resourceType(), a.patronApi);
    if (api) reg.api.push(rq.url());
    if (e.tipo === 'estaticos' && ESTATICOS.has(rq.resourceType())) { r.interceptados++; return route.abort('failed'); }
    if (e.tipo !== 'api' || !api) return route.continue();
    r.interceptados++;
    if (escenario === 'timeout') { colgados.push(route); return undefined; } // nunca responde
    let real = null;
    if (escenario === 'nulos') {
      const resp = await route.fetch().catch(() => null);
      real = resp ? await resp.text().catch(() => null) : null;
    }
    return route.fulfill(respuestaSimulada(escenario, real)).catch(() => {});
  });
  let cdp = null;
  if (escenario === 'lenta') {
    cdp = await ctx.newCDPSession(page).catch(() => null);
    if (cdp) await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 2000, downloadThroughput: 50 * 1024, uploadThroughput: 20 * 1024 }).catch(() => {});
    else r.nota = 'La red lenta usa CDP: solo funciona en Chromium.';
  }
  const t0 = Date.now();
  try {
    await page.goto(u, { waitUntil: 'domcontentloaded', timeout: a.timeoutMs * 3 });
    if (escenario === 'offline') {
      await page.waitForLoadState('load', { timeout: a.timeoutMs }).catch(() => {});
      await ctx.setOffline(true);
      // Intenta navegar a un link interno (o recargar) para ver qué pasa sin red.
      const href = await page.evaluate(() => { const l = [...document.querySelectorAll('a[href]')].find((x) => x.host === location.host && x.href !== location.href && !/logout|salir|delete|borrar/i.test(x.href)); return l ? l.href : null; }).catch(() => null);
      r.navego = true;
      await page.goto(href || u, { timeout: a.timeoutMs }).catch(() => {});
    }
    await page.waitForTimeout(Math.min(a.timeoutMs, escenario === 'lenta' ? a.timeoutMs : 6000));
  } catch (err) {
    r.error_carga = String(err.message || err).split('\n')[0].slice(0, 200);
  }
  r.espera_ms = Date.now() - t0;
  r.observado = await observar(page);
  const cap = path.join(dirCap, `${n}-${escenario}.png`);
  await page.screenshot({ path: cap, fullPage: false }).catch(() => {});
  if (fs.existsSync(cap)) r.captura = `capturas/${path.basename(cap)}`;
  const rt = contarReintentos(reg.api);
  r.reintentos = e.tipo === 'api' ? rt.reintentos : 0;
  r.reintentos_url = rt.url;
  r.cambio_contenido = cambioContenido(base, r.observado);

  // Recuperación: se quita la falla, vuelve la red y se recarga.
  fallando = false;
  for (const c of colgados) await c.abort('timedout').catch(() => {});
  if (escenario === 'offline') await ctx.setOffline(false).catch(() => {});
  if (cdp) await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }).catch(() => {});
  try {
    await page.goto(u, { waitUntil: 'load', timeout: a.timeoutMs * 3 });
    await page.waitForTimeout(800);
    const o2 = await observar(page);
    r.recuperacion = { texto_len: o2.texto_len, elementos: o2.elementos, recupera: o2.texto_len >= (base.texto_len || 0) * 0.6 };
    const cap2 = path.join(dirCap, `${n}-${escenario}-recuperacion.png`);
    if (!r.recuperacion.recupera) {
      await page.screenshot({ path: cap2 }).catch(() => {});
      if (fs.existsSync(cap2)) r.captura_recuperacion = `capturas/${path.basename(cap2)}`;
    }
  } catch { r.recuperacion = { recupera: null }; }
  r.errores_js = [...new Set(reg.errores_js)];
  r.consola = [...new Set(reg.consola)].slice(0, 10);
  await ctx.close().catch(() => {});
  if (e.tipo === 'api' && r.interceptados === 0) return { ...r, estado: 'no-aplica', motivo: 'En este escenario la página no llegó a llamar a la API.' };
  if (escenario === 'estaticos' && r.interceptados === 0) return { ...r, estado: 'no-aplica', motivo: 'La página no carga recursos estáticos.' };
  return r;
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
  const inicio = normalizar(url);
  const host = new URL(inicio).hostname;
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'resiliencia', a.historia || host);
  archivar(carpeta, GENERADOS, 'resiliencia.json');
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });
  const dirCap = path.join(carpeta, 'capturas');
  fs.mkdirSync(dirCap, { recursive: true });
  const relRaiz = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  const { chromium } = require('playwright'); // acá y no arriba: los tests usan las funciones sin instalar k0lmena
  const browser = await navegadorComun.lanzar(chromium, { headless: !a.headed });
  const t0 = Date.now();
  const ctx0 = await browser.newContext();
  const p0 = await ctx0.newPage();
  await p0.route('**/*', (route) => (route.request().isNavigationRequest() && route.request().method() !== 'GET' ? route.abort() : route.continue()));
  const urls = await descubrir(p0, inicio, a);
  await ctx0.close();
  console.log(`Resiliencia: ${urls.length} página(s) × ${a.escenarios.length} escenario(s) · salida ${relRaiz(carpeta)}`);

  const paginas = [];
  const hallazgos = [];
  for (const [i, u] of urls.entries()) {
    const n = `${String(i + 1).padStart(2, '0')}-${slug(u)}`;
    const base = await lineaBase(browser, u, a);
    const capBase = path.join(dirCap, `${n}-base.png`);
    {
      const c = await browser.newContext({ viewport: { width: 1366, height: 900 } });
      const pg = await c.newPage();
      await pg.goto(u, { waitUntil: 'load', timeout: 30000 }).catch(() => {});
      await pg.screenshot({ path: capBase }).catch(() => {});
      await c.close();
    }
    console.log(`[${i + 1}/${urls.length}] ${u} · ${base.llamadas_api.length} llamada(s) a la API · ${base.texto_len} caracteres`);
    const pagina = { url: u, id: n, base: { ...base, muestra: undefined }, captura_base: fs.existsSync(capBase) ? `capturas/${path.basename(capBase)}` : null, resultados: [] };
    for (const esc of a.escenarios) {
      let r;
      try { r = await probarEscenario(browser, u, esc, base, a, dirCap, n); } catch (err) {
        r = { escenario: esc, nombre: ESCENARIOS[esc].nombre, estado: 'error', motivo: String(err.message || err).split('\n')[0] };
      }
      const hs = evaluar(base, r).map((h) => ({ ...h, escenario: esc, pagina: u, captura: r.captura_recuperacion || r.captura || null }));
      if (r.estado === 'ok' && hs.length) r.estado = 'hallazgo';
      r.hallazgos = hs;
      if (r.observado) delete r.observado.muestra;
      hallazgos.push(...hs);
      pagina.resultados.push(r);
      process.stdout.write(`    ${esc.padEnd(11)} ${r.estado}${hs.length ? ` (${hs.map((h) => h.tipo).join(', ')})` : ''}\n`);
    }
    paginas.push(pagina);
  }
  await browser.close();
  hallazgos.sort((x, y) => SEV_ORDEN[x.severidad] - SEV_ORDEN[y.severidad]);
  hallazgos.forEach((h, i) => { h.id = `R-${String(i + 1).padStart(2, '0')}`; });
  for (const p of paginas) for (const r of p.resultados) r.hallazgos = (r.hallazgos || []).map((h) => h.id);
  const resultado = {
    url: inicio, host, historia: a.historia || null, fecha: new Date().toISOString(), marca: sello(), duracion_s: Math.round((Date.now() - t0) / 1000),
    herramienta: `Playwright ${require('playwright/package.json').version}`, timeout_ms: a.timeoutMs, patron_api: a.patronApi,
    escenarios: a.escenarios.map((id) => ({ id, nombre: ESCENARIOS[id].nombre, tipo: ESCENARIOS[id].tipo })),
    resumen: resumir(paginas, hallazgos), hallazgos, paginas,
  };
  const salida = path.join(carpeta, 'resiliencia.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  const r = resultado.resumen;
  console.log(`\nPruebas: ${r.pruebas} · con hallazgos: ${r.con_hallazgos} · no aplica: ${r.no_aplica} · hallazgos: ${r.hallazgos}`);
  console.log(`Datos: ${relRaiz(salida)}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${relRaiz(path.join(carpeta, 'informe-resiliencia.html'))}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, esApi, anularCampos, respuestaSimulada, contarReintentos, evaluar, cambioContenido, resumir, ESCENARIOS, GENERADOS };

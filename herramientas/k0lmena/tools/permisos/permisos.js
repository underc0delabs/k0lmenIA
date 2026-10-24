// Matriz de permisos por rol (agente probador-permisos).
//
// Uso (desde la raíz del repo):
//   npm run permisos -- [--url https://mi-app.com] [--historia HU-001] [--paginas url1,url2]
//                       [--max-paginas 25] [--profundidad 2] [--roles admin,operador]
//                       [--endpoints "GET /api/usuarios,GET /api/pedidos/1"] [--api-base https://api.mi-app.com]
//                       [--mapa si|no] [--capturas 60] [--pausa-ms 300] [--salida <carpeta>] [--headed]
//
// Para cada rol (siempre "anonimo", sin sesión, más los de PERMISOS_ROLES del .env) inicia sesión, recorre
// el sitio y anota qué rutas ve en su navegación. Después visita TODAS las rutas encontradas (las de todos
// los roles, las de --paginas y, con --mapa si, las del mapa funcional del documentador-proyecto) con cada
// rol, como si escribiera la URL a mano, y registra: status HTTP, si pide login, si muestra "acceso
// denegado", a dónde redirige, título, menús y botones visibles. Con --endpoints, pide cada endpoint con la
// sesión (cookies) y el token de cada rol y registra el status.
//
// Roles en el .env de la raíz:
//   PERMISOS_ROLES=admin,operador,invitado
//   PERMISOS_<ROL>_USUARIO / PERMISOS_<ROL>_CLAVE   (login por la web)
//   PERMISOS_<ROL>_TOKEN                            (opcional: Authorization: Bearer para --endpoints)
//   PERMISOS_LOGIN_URL                              (opcional: página de login; por defecto la URL inicial)
//   PERMISOS_SELECTOR_USUARIO / _CLAVE / _ENVIAR    (opcionales: si no, se detectan solos)
// Sin PERMISOS_ROLES y con APP_USER/APP_PASSWORD, prueba "anonimo" y "usuario".
//
// Solo lectura: navega con GET. El único envío permitido es el formulario de login; cualquier otra
// navegación que no sea GET se corta. Los endpoints solo con GET, HEAD u OPTIONS. No sigue links de
// cierre de sesión ni de borrado. Nunca guarda usuarios, claves ni tokens en el JSON.
//
// Deja todo en output/permisos/<HU o host>/: permisos.json, informe-permisos.html y capturas/. La corrida
// anterior pasa a historial/ (se guardan las últimas 5).
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { normalizar, slug, sello, cargar } = require('../explorador/explorar.js');
const { descubrir } = require('../pixel-perfect/pixel-perfect.js');
const { archivar } = require('../historial/historial.js');

const RAIZ = path.resolve(__dirname, '..', '..', '..', '..');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p);
const GENERADOS = ['permisos.json', 'analisis.json', 'informe-permisos.html', 'capturas'];
const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };
const ANONIMO = 'anonimo';
const slugRol = (x) => x.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'rol';
const METODOS_SEGUROS = new Set(['GET', 'HEAD', 'OPTIONS']);
// Textos que indican que la página negó el acceso (aunque responda 200).
const DENEGADO = /(acceso denegado|no autorizado|sin permiso|no ten[eé]s permiso|no tiene permiso|permiso insuficiente|prohibido|forbidden|unauthori[sz]ed|access denied|not authori[sz]ed)/i;
// Rutas que suelen ser la pantalla de login.
const RUTA_LOGIN = /(log-?in|sign-?in|ingres|iniciar-?sesion|acceso|auth)/i;

function argumentos(argv) {
  const a = { maxPaginas: 25, profundidad: 2, capturas: 60, pausaMs: 300, mapa: true, headed: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--historia') a.historia = v();
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--roles') a.roles = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--endpoints') a.endpoints = v();
    else if (k === '--api-base') a.apiBase = v();
    else if (k === '--mapa') a.mapa = !/^(no|false|0)$/i.test(v());
    else if (k === '--capturas') a.capturas = parseInt(v(), 10);
    else if (k === '--pausa-ms') a.pausaMs = parseInt(v(), 10);
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  if (!(a.maxPaginas >= 1 && a.maxPaginas <= 200)) throw new Error('--max-paginas tiene que estar entre 1 y 200.');
  if (!(a.profundidad >= 0 && a.profundidad <= 5)) throw new Error('--profundidad tiene que estar entre 0 y 5.');
  return a;
}

// Nombre de la variable de entorno de un rol: "jefe de área" → PERMISOS_JEFE_DE_AREA_USUARIO.
function claveEnv(rol, sufijo) {
  const base = rol.normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return `PERMISOS_${base}_${sufijo}`;
}

// Roles a probar a partir del entorno. Nunca devuelve las claves: solo si están definidas.
function rolesDesdeEnv(env, filtro) {
  let nombres = (env.PERMISOS_ROLES || '').split(',').map((x) => x.trim()).filter(Boolean);
  let usarApp = false;
  if (!nombres.length && env.APP_USER && env.APP_PASSWORD) { nombres = ['usuario']; usarApp = true; }
  const roles = [{ id: ANONIMO, nombre: 'Anónimo (sin sesión)', autenticado: false, tiene_credenciales: false, tiene_token: false }];
  for (const n of nombres) {
    if (n.toLowerCase() === ANONIMO) continue;
    const usuario = usarApp ? env.APP_USER : env[claveEnv(n, 'USUARIO')];
    const clave = usarApp ? env.APP_PASSWORD : env[claveEnv(n, 'CLAVE')];
    roles.push({ id: n, nombre: n, autenticado: true, tiene_credenciales: Boolean(usuario && clave), tiene_token: Boolean(env[claveEnv(n, 'TOKEN')]),
      origen: usarApp ? 'APP_USER/APP_PASSWORD' : `${claveEnv(n, 'USUARIO')}/${claveEnv(n, 'CLAVE')}` });
  }
  if (filtro && filtro.length) return roles.filter((r) => r.id === ANONIMO || filtro.includes(r.id));
  return roles;
}

function credenciales(env, rol) {
  if (rol.origen === 'APP_USER/APP_PASSWORD') return { usuario: env.APP_USER, clave: env.APP_PASSWORD, token: env[claveEnv(rol.id, 'TOKEN')] };
  return { usuario: env[claveEnv(rol.id, 'USUARIO')], clave: env[claveEnv(rol.id, 'CLAVE')], token: env[claveEnv(rol.id, 'TOKEN')] };
}

// "GET /api/x, /api/y" → [{metodo, ruta}]. Sin método = GET.
function parsearEndpoints(texto) {
  if (!texto) return [];
  return texto.split(',').map((x) => x.trim()).filter(Boolean).map((x) => {
    const m = x.match(/^([A-Za-z]+)\s+(\S+)$/);
    const metodo = (m ? m[1] : 'GET').toUpperCase();
    const ruta = m ? m[2] : x;
    if (!METODOS_SEGUROS.has(metodo)) throw new Error(`"${x}": solo se prueban endpoints con GET, HEAD u OPTIONS (sin efecto).`);
    return { metodo, ruta };
  });
}

// Cómo quedó una visita: permitido | pide-login | denegado | no-encontrada | error.
function clasificarAcceso({ status, urlPedida, urlFinal, pideClave, texto, loginUrl }) {
  if (!status) return 'error';
  if (status === 404 || status === 410) return 'no-encontrada';
  if (status === 401 || status === 403) return 'denegado';
  const ruta = (u) => { try { const x = new URL(u); return x.pathname + x.search; } catch { return u || ''; } };
  const esLogin = (u) => (loginUrl && normalizar(u) === normalizar(loginUrl)) || RUTA_LOGIN.test(ruta(u));
  if (!esLogin(urlPedida) && urlFinal && ruta(urlFinal) !== ruta(urlPedida) && esLogin(urlFinal)) return 'pide-login';
  if (pideClave && !esLogin(urlPedida)) return 'pide-login';
  if (DENEGADO.test(texto || '')) return 'denegado';
  if (status >= 500) return 'error';
  return 'permitido';
}

const NEGADO = new Set(['denegado', 'pide-login']);

// Hallazgos automáticos: lo que tiene evidencia propia en la matriz. La comparación contra lo esperado
// (qué rol DEBERÍA ver qué) la hace el agente con su análisis.
function armarHallazgos({ roles, rutas, matriz, endpoints }) {
  const h = [];
  const add = (severidad, tipo, titulo, detalle, extra = {}) => h.push({ severidad, tipo, titulo, detalle, ...extra });
  const celda = (rol, url) => matriz.find((m) => m.rol === rol && m.url === url);
  for (const r of roles) {
    if (r.autenticado && !r.tiene_credenciales) add('Alta', 'Configuración', `Faltan las credenciales del rol "${r.id}"`, `Definí ${r.origen} en el .env de la raíz.`, { rol: r.id });
    else if (r.autenticado && r.login_ok === false) add('Alta', 'Configuración', `No se pudo iniciar sesión con el rol "${r.id}"`, r.login_error || 'Revisá las credenciales y los selectores de login.', { rol: r.id });
  }
  const activos = roles.filter((r) => !r.autenticado || r.login_ok);
  for (const ruta of rutas) {
    const negadoA = activos.filter((r) => r.autenticado && NEGADO.has((celda(r.id, ruta.url) || {}).acceso)).map((r) => r.id);
    const anon = celda(ANONIMO, ruta.url);
    const soloConSesion = ruta.descubierta_por.length && !ruta.descubierta_por.includes(ANONIMO);
    if (anon && anon.acceso === 'permitido' && soloConSesion) {
      if (negadoA.length) {
        add('Crítica', 'Sin login', 'Ruta protegida accesible sin iniciar sesión', `${ruta.ruta} niega el acceso a ${negadoA.join(', ')} pero abre sin sesión.`, { url: ruta.url, rol: ANONIMO });
      } else {
        add('Alta', 'Sin login', 'Ruta que solo aparece con sesión abre sin iniciar sesión', `${ruta.ruta} solo se ve en la navegación de ${ruta.descubierta_por.join(', ')}, pero abre sin sesión. Confirmá si es pública.`, { url: ruta.url, rol: ANONIMO });
      }
    }
    for (const r of activos) {
      const c = celda(r.id, ruta.url);
      if (!c) continue;
      if (ruta.descubierta_por.includes(r.id) && NEGADO.has(c.acceso)) {
        add('Media', 'Opción sin permiso', `El rol "${r.id}" ve un link que después le niega el acceso`, `${ruta.ruta}: aparece en su navegación pero responde ${c.acceso === 'denegado' ? 'acceso denegado' : 'con el login'}.`, { url: ruta.url, rol: r.id });
      }
      if (r.autenticado && c.acceso === 'permitido' && !ruta.descubierta_por.includes(r.id) && negadoA.length && !negadoA.includes(r.id)) {
        add('Alta', 'URL directa', `El rol "${r.id}" entra por URL directa a una ruta restringida`, `${ruta.ruta} no está en su navegación y se le niega a ${negadoA.join(', ')}, pero a "${r.id}" se le abre. Confirmá si debería.`, { url: ruta.url, rol: r.id });
      }
      if (c.acceso === 'error') add('Media', 'Error', `${ruta.ruta} falla para el rol "${r.id}"`, c.error || `Responde ${c.status}.`, { url: ruta.url, rol: r.id });
    }
  }
  for (const ep of endpoints) {
    const st = (rol) => (ep.resultados[rol] || {}).status || 0;
    const rechazan = activos.filter((r) => r.autenticado && [401, 403].includes(st(r.id))).map((r) => r.id);
    if (st(ANONIMO) >= 200 && st(ANONIMO) < 300 && rechazan.length) {
      add('Crítica', 'API sin autenticación', `${ep.metodo} ${ep.ruta} responde sin autenticación`, `Sin sesión responde ${st(ANONIMO)}, pero rechaza a ${rechazan.join(', ')}.`, { url: ep.url, rol: ANONIMO });
    }
    for (const r of activos) if (st(r.id) >= 500) add('Media', 'Error', `${ep.metodo} ${ep.ruta} falla para el rol "${r.id}"`, `Responde ${st(r.id)}.`, { url: ep.url, rol: r.id });
  }
  h.sort((x, y) => SEV_ORDEN[x.severidad] - SEV_ORDEN[y.severidad]);
  h.forEach((x, i) => { x.id = `P-${String(i + 1).padStart(2, '0')}`; });
  return h;
}

function resumir({ roles, rutas, matriz, endpoints, hallazgos }) {
  const cuenta = (acc) => matriz.filter((m) => m.acceso === acc).length;
  return { roles: roles.length, roles_con_sesion: roles.filter((r) => r.login_ok).length, rutas: rutas.length, visitas: matriz.length,
    permitidas: cuenta('permitido'), denegadas: cuenta('denegado'), piden_login: cuenta('pide-login'), errores: cuenta('error'), no_encontradas: cuenta('no-encontrada'),
    endpoints: endpoints.length, hallazgos: hallazgos.length,
    por_severidad: Object.fromEntries(['Crítica', 'Alta', 'Media', 'Baja'].map((s) => [s, hallazgos.filter((x) => x.severidad === s).length])) };
}

// Corre en el navegador: lo que el rol ve en la página.
function _vista() {
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const texto = (el) => (el.innerText || el.textContent || el.value || el.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim();
  const unicos = (xs) => [...new Set(xs.filter(Boolean))];
  const menus = unicos([...document.querySelectorAll('nav a[href], [role=navigation] a[href], [role=menuitem], header a[href], aside a[href]')].filter(visible).map((x) => texto(x).slice(0, 50))).slice(0, 60);
  const botones = unicos([...document.querySelectorAll('button, [role=button], input[type=submit], input[type=button]')].filter((b) => visible(b) && !b.closest('nav'))
    .map((b) => texto(b).slice(0, 50))).slice(0, 40);
  const clave = [...document.querySelectorAll('input[type=password]')].some(visible);
  return { titulo: document.title.trim(), menus, botones, pide_clave: clave, texto: (document.body ? document.body.innerText : '').slice(0, 3000) };
}

// Login genérico: el campo de clave visible, el campo de usuario anterior a él y el botón de su formulario.
async function iniciarSesion(page, rol, cred, cfg) {
  const loginUrl = cfg.loginUrl;
  cfg.permitirEnvio(true);
  try {
    await cargar(page, loginUrl);
    const sel = (envVar, porDefecto) => process.env[envVar] || porDefecto;
    const clave = page.locator(sel('PERMISOS_SELECTOR_CLAVE', 'input[type=password]')).first();
    await clave.waitFor({ state: 'visible', timeout: 10000 });
    let usuario = process.env.PERMISOS_SELECTOR_USUARIO ? page.locator(process.env.PERMISOS_SELECTOR_USUARIO).first() : null;
    if (!usuario) {
      const marca = await page.evaluate(() => {
        const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        const c = [...document.querySelectorAll('input[type=password]')].find(visible);
        const campos = [...(c.form || document).querySelectorAll('input:not([type=hidden]):not([type=password]):not([type=checkbox]):not([type=radio]):not([type=submit]):not([type=button])')].filter(visible);
        const previos = campos.filter((x) => x.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING);
        const u = previos[previos.length - 1] || campos[0];
        if (!u) return false;
        u.setAttribute('data-k0-usuario', '1');
        return true;
      });
      if (!marca) throw new Error('no encontré el campo de usuario (definí PERMISOS_SELECTOR_USUARIO)');
      usuario = page.locator('[data-k0-usuario="1"]').first();
    }
    await usuario.fill(cred.usuario);
    await clave.fill(cred.clave);
    const enviar = process.env.PERMISOS_SELECTOR_ENVIAR
      ? page.locator(process.env.PERMISOS_SELECTOR_ENVIAR).first()
      : page.locator('form:has(input[type=password]) button[type=submit], form:has(input[type=password]) input[type=submit], form:has(input[type=password]) button:not([type])').first();
    if (await enviar.count()) await enviar.click({ timeout: 5000 });
    else await clave.press('Enter');
    await page.waitForLoadState('load', { timeout: 15000 }).catch(() => {});
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    const sigue = await page.locator('input[type=password]').first().isVisible().catch(() => false);
    if (sigue) {
      const err = await page.evaluate(() => [...document.querySelectorAll('[role=alert], .error, .alert, .invalid-feedback')].map((x) => x.innerText.trim()).filter(Boolean).join(' · ').slice(0, 200)).catch(() => '');
      throw new Error(`después de enviar el login sigue la pantalla de login${err ? ` (${err})` : ''}`);
    }
    return page.url();
  } finally {
    cfg.permitirEnvio(false);
  }
}

function rutasDelMapa() {
  const archivo = path.join(RAIZ, 'input', 'documentacion', 'proyecto', 'mapa-funcional.json');
  try { return (JSON.parse(fs.readFileSync(archivo, 'utf8')).paginas || []).map((p) => p.url).filter(Boolean); } catch { return []; }
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(RAIZ, 'scripts', 'generar_informe_permisos.py'), path.join(carpeta, 'permisos.json'),
    path.join(carpeta, 'informe-permisos.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_permisos.py <carpeta>/permisos.json <carpeta>/informe-permisos.html`);
    return false;
  }
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
  const endpoints = parsearEndpoints(a.endpoints);
  const inicio = normalizar(url);
  const host = new URL(inicio).hostname;
  const loginUrl = process.env.PERMISOS_LOGIN_URL || inicio;
  const roles = rolesDesdeEnv(process.env, a.roles);
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'permisos', a.historia || host);
  archivar(carpeta, GENERADOS, 'permisos.json');
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });
  const dirCap = path.join(carpeta, 'capturas');
  fs.mkdirSync(dirCap, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');
  const relRaiz = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

  const { chromium } = require('playwright');
  const browser = await navegadorComun.lanzar(chromium, { headless: !a.headed });
  const t0 = Date.now();
  console.log(`Permisos de ${inicio} · roles: ${roles.map((r) => r.id).join(', ')} · salida ${relRaiz(carpeta)}`);

  // Un contexto (sesión) por rol, con el bloqueo de envíos.
  const sesiones = {};
  for (const r of roles) {
    const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, locale: process.env.LOCALE || 'es-AR' });
    const page = await ctx.newPage();
    let envio = false;
    await page.route('**/*', (route) => {
      const rq = route.request();
      if (!envio && rq.isNavigationRequest() && rq.method() !== 'GET') return route.abort();
      return route.continue();
    });
    sesiones[r.id] = { ctx, page, permitirEnvio: (x) => { envio = x; } };
    if (r.autenticado) {
      if (!r.tiene_credenciales) { r.login_ok = false; r.login_error = 'faltan credenciales'; continue; }
      try {
        r.url_despues_login = await iniciarSesion(page, r, credenciales(process.env, r), { loginUrl, permitirEnvio: sesiones[r.id].permitirEnvio });
        r.login_ok = true;
      } catch (e) {
        r.login_ok = false;
        r.login_error = String(e.message || e).split('\n')[0].slice(0, 300);
      }
      console.log(`  login ${r.id}: ${r.login_ok ? 'ok' : `falló (${r.login_error})`}`);
    }
  }

  // 1) Qué rutas ve cada rol en su navegación.
  const rutasMap = new Map();
  const agregarRuta = (u, rol) => {
    let n;
    try { n = normalizar(u); } catch { return; }
    if (new URL(n).hostname !== host) return;
    if (!rutasMap.has(n)) rutasMap.set(n, { url: n, ruta: new URL(n).pathname + new URL(n).search, descubierta_por: [] });
    if (rol && !rutasMap.get(n).descubierta_por.includes(rol)) rutasMap.get(n).descubierta_por.push(rol);
  };
  for (const r of roles) {
    if (r.autenticado && !r.login_ok) continue;
    const inicioRol = r.url_despues_login && new URL(r.url_despues_login).hostname === host ? normalizar(r.url_despues_login) : inicio;
    const urls = await descubrir(sesiones[r.id].page, inicioRol, { maxPaginas: a.maxPaginas, profundidad: a.profundidad }).catch(() => [inicioRol]);
    for (const u of urls) agregarRuta(u, r.id);
    console.log(`  ${r.id}: ${urls.length} ruta(s) en su navegación`);
  }
  for (const u of a.paginas || []) agregarRuta(u, null);
  if (a.mapa) for (const u of rutasDelMapa()) agregarRuta(u, null);
  const rutas = [...rutasMap.values()];

  // 2) Cada rol contra todas las rutas (URL directa).
  const matriz = [];
  let capturas = 0;
  for (const r of roles) {
    if (r.autenticado && !r.login_ok) continue;
    const { page } = sesiones[r.id];
    for (const [i, ruta] of rutas.entries()) {
      const c = { rol: r.id, url: ruta.url };
      try {
        const { resp } = await cargar(page, ruta.url);
        c.status = resp ? resp.status() : 0;
        c.url_final = page.url();
        const v = await page.evaluate(_vista);
        Object.assign(c, { titulo: v.titulo, menus: v.menus, botones: v.botones });
        c.acceso = clasificarAcceso({ status: c.status, urlPedida: ruta.url, urlFinal: c.url_final, pideClave: v.pide_clave, texto: v.texto, loginUrl });
        if (c.acceso === 'denegado' && c.status < 400) c.motivo = 'la página muestra un mensaje de acceso denegado';
      } catch (e) {
        c.status = 0;
        c.acceso = 'error';
        c.error = String(e.message || e).split('\n')[0].slice(0, 300);
      }
      if (capturas < a.capturas) {
        const archivo = path.join(dirCap, `${slugRol(r.id)}-${String(i + 1).padStart(2, '0')}-${slug(ruta.url)}.png`);
        await page.screenshot({ path: archivo }).catch(() => {});
        if (fs.existsSync(archivo)) { c.captura = rel(archivo); capturas++; }
      }
      matriz.push(c);
      process.stdout.write(`  [${r.id}] ${ruta.ruta} → ${c.acceso} (${c.status})\n`);
      if (a.pausaMs) await esperar(a.pausaMs);
    }
  }

  // 3) Endpoints de API con la sesión y el token de cada rol.
  const base = a.apiBase || process.env.API_BASEURL || inicio;
  const eps = [];
  for (const ep of endpoints) {
    const urlEp = /^https?:\/\//i.test(ep.ruta) ? ep.ruta : new URL(ep.ruta, base).href;
    const fila = { metodo: ep.metodo, ruta: ep.ruta, url: urlEp, resultados: {} };
    for (const r of roles) {
      if (r.autenticado && !r.login_ok && !r.tiene_token) continue;
      const token = r.autenticado ? credenciales(process.env, r).token : null;
      try {
        const resp = await sesiones[r.id].ctx.request.fetch(urlEp, { method: ep.metodo, headers: token ? { Authorization: `Bearer ${token}` } : {}, failOnStatusCode: false, maxRedirects: 0, timeout: 20000 });
        fila.resultados[r.id] = { status: resp.status(), con_token: Boolean(token) };
      } catch (e) {
        fila.resultados[r.id] = { status: 0, error: String(e.message || e).split('\n')[0].slice(0, 200) };
      }
    }
    eps.push(fila);
    console.log(`  ${ep.metodo} ${ep.ruta}: ${Object.entries(fila.resultados).map(([k, v]) => `${k}=${v.status}`).join(' ')}`);
  }
  await browser.close();

  const rolesSalida = roles.map(({ origen, ...r }) => ({ ...r, variables: origen || null }));
  const hallazgos = armarHallazgos({ roles: rolesSalida, rutas, matriz, endpoints: eps });
  const resultado = { url: inicio, host, historia: a.historia || null, fecha: new Date().toISOString(), marca: sello(), duracion_s: Math.round((Date.now() - t0) / 1000),
    herramienta: `Playwright ${require('playwright/package.json').version}`, login_url: loginUrl, roles: rolesSalida, rutas, matriz, endpoints: eps, hallazgos };
  resultado.resumen = resumir({ ...resultado, roles: rolesSalida });
  const salida = path.join(carpeta, 'permisos.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  const s = resultado.resumen;
  console.log(`\nRoles: ${s.roles} · rutas: ${s.rutas} · visitas: ${s.visitas} (${s.permitidas} permitidas, ${s.denegadas + s.piden_login} negadas) · hallazgos: ${s.hallazgos}`);
  console.log(`Datos: ${relRaiz(salida)}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${relRaiz(path.join(carpeta, 'informe-permisos.html'))}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, claveEnv, rolesDesdeEnv, parsearEndpoints, clasificarAcceso, armarHallazgos, resumir, GENERADOS, ANONIMO };

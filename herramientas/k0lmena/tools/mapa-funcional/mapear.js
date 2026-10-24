// Mapa funcional de un sitio web (agente documentador-proyecto).
//
// Uso (desde la raíz del repo):
//   npm run mapa-funcional -- [--url https://mi-app.com] [--paginas url1,url2] [--max-paginas 30]
//                             [--profundidad 2] [--pausa-ms 300] [--salida <carpeta>] [--headed]
//
// Recorre las páginas del mismo host a partir de la URL (por defecto APP_URL del .env, o BASEURL) y
// documenta qué hay en cada una, para que los agentes que escriben casos conozcan la aplicación real:
//   título y encabezados · menús de navegación (los que se repiten en todo el sitio van una sola vez)
//   · formularios con cada campo (etiqueta, tipo, obligatorio, largos, mínimos y máximos, patrón,
//   opciones de las listas) · botones · mensajes visibles (alertas, errores, avisos) · encabezados de
//   tablas · un extracto del texto principal.
//
// Es documentación, no una prueba: no saca capturas ni busca errores (eso es npm run explorar).
// Solo navega con GET: no completa ni envía formularios (toda navegación que no sea GET se corta) y
// no sigue links de cierre de sesión ni de borrado.
//
// Con sesión: si SESION está en el .env (npm run login guarda la sesión en .auth/), recorre la aplicación
// logueado y cubre también las pantallas privadas; --sin-sesion recorre solo lo público.
//
// Para automatizar: por cada página guarda los **locators sugeridos** de sus elementos interactivos
// (botones, links, campos, pestañas, menús), en el orden que recomienda Playwright: data-testid, rol +
// nombre accesible, label, placeholder y, si no hay otra cosa, #id o [name]; y si cada uno es único. El
// web-mapper los usa como punto de partida (los verifica en el snapshot antes de escribirlos).
//
// Cambios: si ya había un mapa, compara y deja "Cambios desde el recorrido anterior" (pantallas nuevas o
// que ya no están, campos agregados, quitados o con otra regla, botones). Así se ve cuándo la aplicación
// cambió y qué documentación y casos revisar. La corrida anterior queda en _mapa-funcional.anterior.json.
//
// Deja en input/documentacion/proyecto/ (o --salida) mapa-funcional.json y mapa-funcional.md.
const fs = require('fs');
const path = require('path');
const { normalizar, recorrerScroll, cargar } = require('../explorador/explorar.js');
const { descubrir } = require('../pixel-perfect/pixel-perfect.js');
const { extraerFormularios } = require('../formularios/formularios.js');
const { sesionActiva } = require('../login/sesion');

const RAIZ = path.resolve(__dirname, '..', '..', '..', '..');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p);
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

function argumentos(argv) {
  const a = { maxPaginas: 30, profundidad: 2, pausaMs: 300, headed: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--pausa-ms') a.pausaMs = parseInt(v(), 10);
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '--sin-sesion') a.sinSesion = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (!(a.maxPaginas >= 1 && a.maxPaginas <= 200)) throw new Error('--max-paginas tiene que estar entre 1 y 200.');
  if (!(a.profundidad >= 0 && a.profundidad <= 5)) throw new Error('--profundidad tiene que estar entre 0 y 5.');
  return a;
}

// Corre en el navegador: lo visible de la página, sin los formularios (los extrae extraerFormularios).
function _contenido() {
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const texto = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  const unicos = (xs) => [...new Set(xs.filter(Boolean))];
  const encabezados = [...document.querySelectorAll('h1, h2, h3')].filter(visible)
    .map((h) => ({ nivel: Number(h.tagName[1]), texto: texto(h).slice(0, 120) })).filter((h) => h.texto).slice(0, 40);
  const menus = [...document.querySelectorAll('nav, [role=navigation], header [role=menubar], aside [role=menu]')].filter(visible).map((n) => ({
    nombre: n.getAttribute('aria-label') || (n.closest('header') ? 'Encabezado' : n.closest('footer') ? 'Pie' : n.closest('aside') ? 'Lateral' : 'Navegación'),
    items: unicos([...n.querySelectorAll('a[href], button, [role=menuitem]')].filter(visible).map((x) => texto(x).slice(0, 60))).slice(0, 40),
  })).filter((m) => m.items.length);
  const enMenu = (el) => el.closest('nav, [role=navigation], form');
  const botones = unicos([...document.querySelectorAll('button, [role=button], input[type=submit], input[type=button], a.btn, a.button')]
    .filter((b) => visible(b) && !enMenu(b)).map((b) => (texto(b) || b.value || b.getAttribute('aria-label') || '').slice(0, 60))).slice(0, 40);
  const mensajes = unicos([...document.querySelectorAll('[role=alert], [role=status], [aria-live], .alert, .error, .warning, .notice, .toast, .message')]
    .filter(visible).map((m) => texto(m).slice(0, 200))).slice(0, 20);
  const tablas = [...document.querySelectorAll('table')].filter(visible)
    .map((t) => [...t.querySelectorAll('thead th, tr:first-child th')].map((th) => texto(th).slice(0, 40)).filter(Boolean))
    .filter((c) => c.length).slice(0, 10);
  const principal = document.querySelector('main, [role=main], article') || document.body;
  const parrafos = [...principal.querySelectorAll('p, li')].filter((p) => visible(p) && !p.closest('nav, footer, header, form')).map(texto).filter((t) => t.length > 30);
  let extracto = '';
  for (const p of parrafos) { if ((extracto + p).length > 700) break; extracto += (extracto ? ' ' : '') + p; }
  const desc = document.querySelector('meta[name=description]');
  return { titulo: document.title.trim(), descripcion: desc ? desc.content.trim() : '', idioma: document.documentElement.lang || '',
    encabezados, menus, botones, mensajes, tablas, extracto };
}

// Corre en el navegador: locators sugeridos de los elementos interactivos visibles, en el orden que
// recomienda Playwright (data-testid > rol + nombre > label > placeholder > #id/[name]) y si son únicos.
function _locators() {
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const limpio = (t) => (t || '').replace(/\s+/g, ' ').trim();
  const q = (s) => `'${String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
  const rolDe = (el) => {
    const r = el.getAttribute('role');
    if (r) return r;
    const t = el.tagName.toLowerCase();
    const tipo = (el.getAttribute('type') || 'text').toLowerCase();
    if (t === 'button' || (t === 'input' && ['submit', 'button', 'reset'].includes(tipo))) return 'button';
    if (t === 'a' && el.hasAttribute('href')) return 'link';
    if (t === 'select') return el.multiple ? 'listbox' : 'combobox';
    if (t === 'textarea') return 'textbox';
    if (t === 'input') return { checkbox: 'checkbox', radio: 'radio', number: 'spinbutton', range: 'slider', search: 'searchbox' }[tipo] || 'textbox';
    return null;
  };
  const etiqueta = (el) => {
    const lab = (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)) || el.closest('label');
    return lab ? limpio(lab.innerText) : '';
  };
  const nombre = (el) => {
    if (el.getAttribute('aria-label')) return limpio(el.getAttribute('aria-label'));
    const ids = (el.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean);
    if (ids.length) return limpio(ids.map((i) => (document.getElementById(i) || {}).innerText || '').join(' '));
    const lab = etiqueta(el);
    if (lab) return lab;
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) return limpio(el.getAttribute('title') || '');
    return limpio(el.innerText || el.value || el.getAttribute('title') || el.getAttribute('alt') || '').slice(0, 80);
  };
  const SEL = 'button, a[href], input:not([type=hidden]), select, textarea, [role=button], [role=link], [role=tab], [role=menuitem], [role=checkbox], [role=radio], [role=switch], [role=combobox], [role=option]';
  const els = [...document.querySelectorAll(SEL)].filter(visible);
  const claves = new Map();
  const items = els.map((el) => {
    const testid = el.getAttribute('data-testid') || el.getAttribute('data-test') || el.getAttribute('data-qa') || el.getAttribute('data-cy');
    const attrTestid = el.hasAttribute('data-testid') ? 'data-testid' : el.hasAttribute('data-test') ? 'data-test' : el.hasAttribute('data-qa') ? 'data-qa' : 'data-cy';
    const rol = rolDe(el);
    const n = nombre(el);
    const lab = etiqueta(el);
    let locator, por;
    if (testid) { locator = attrTestid === 'data-testid' ? `getByTestId(${q(testid)})` : `locator('[${attrTestid}=${JSON.stringify(testid)}]')`; por = 'testid'; }
    else if (rol && n) { locator = `getByRole(${q(rol)}, { name: ${q(n)} })`; por = 'rol'; }
    else if (lab) { locator = `getByLabel(${q(lab)})`; por = 'label'; }
    else if (el.getAttribute('placeholder')) { locator = `getByPlaceholder(${q(el.getAttribute('placeholder'))})`; por = 'placeholder'; }
    else if (el.id) { locator = `locator('#${CSS.escape(el.id)}')`; por = 'css'; }
    else if (el.getAttribute('name')) { locator = `locator('[name="${el.getAttribute('name')}"]')`; por = 'css'; }
    else return null;
    claves.set(locator, (claves.get(locator) || 0) + 1);
    return { elemento: n || lab || el.getAttribute('placeholder') || el.getAttribute('name') || el.id || el.tagName.toLowerCase(), rol: rol || el.tagName.toLowerCase(), locator, por };
  }).filter(Boolean);
  const vistos = new Set();
  return items.filter((x) => (vistos.has(x.locator) ? false : vistos.add(x.locator)))
    .map((x) => ({ ...x, unico: claves.get(x.locator) === 1 })).slice(0, 80);
}

// Diferencias entre dos mapas (el anterior y el actual): para saber qué documentación y qué casos revisar.
function compararMapas(anterior, actual) {
  const porRuta = (m) => new Map((m.paginas || []).filter((p) => !p.error).map((p) => [p.ruta, p]));
  const a = porRuta(anterior), b = porRuta(actual);
  const campos = (p) => new Map((p.formularios || []).flatMap((f) => f.campos.map((c) => [`${f.nombre} › ${c.etiqueta || c.nombre}`, c])));
  const regla = (c) => JSON.stringify([c.tipo, Boolean(c.requerido), c.maxlength, c.minlength, c.min, c.max, c.pattern,
    (c.opciones || []).map((o) => o.texto || o.valor)]);
  const cambios = { nuevas: [...b.keys()].filter((r) => !a.has(r)), quitadas: [...a.keys()].filter((r) => !b.has(r)), paginas: [] };
  for (const [ruta, pb] of b) {
    const pa = a.get(ruta);
    if (!pa) continue;
    const ca = campos(pa), cb = campos(pb);
    const det = {
      ruta,
      campos_nuevos: [...cb.keys()].filter((k) => !ca.has(k)),
      campos_quitados: [...ca.keys()].filter((k) => !cb.has(k)),
      campos_cambiados: [...cb.keys()].filter((k) => ca.has(k) && regla(ca.get(k)) !== regla(cb.get(k))),
      botones_nuevos: (pb.botones || []).filter((x) => !(pa.botones || []).includes(x)),
      botones_quitados: (pa.botones || []).filter((x) => !(pb.botones || []).includes(x)),
      titulo: pa.titulo !== pb.titulo ? [pa.titulo, pb.titulo] : null,
    };
    if (Object.entries(det).some(([k, v]) => k !== 'ruta' && (Array.isArray(v) ? v.length : v))) cambios.paginas.push(det);
  }
  cambios.hay = Boolean(cambios.nuevas.length || cambios.quitadas.length || cambios.paginas.length);
  return cambios;
}

// Los menús que aparecen en la mayoría de las páginas son la navegación global: van una sola vez.
function separarMenusGlobales(paginas) {
  const clave = (m) => `${m.nombre}|${m.items.join('|')}`;
  const cuenta = new Map();
  for (const p of paginas) for (const m of p.menus || []) cuenta.set(clave(m), (cuenta.get(clave(m)) || 0) + 1);
  const minimo = Math.max(2, Math.ceil(paginas.length * 0.6));
  const globales = [];
  for (const p of paginas) {
    for (const m of p.menus || []) if (cuenta.get(clave(m)) >= minimo && !globales.some((g) => clave(g) === clave(m))) globales.push(m);
    p.menus = (p.menus || []).filter((m) => cuenta.get(clave(m)) < minimo);
  }
  return globales;
}

const celda = (x) => String(x ?? '').replace(/\|/g, '/').replace(/\s+/g, ' ').trim();

function restricciones(c) {
  const r = [];
  if (c.minlength != null) r.push(`mín. ${c.minlength} caracteres`);
  if (c.maxlength != null) r.push(`máx. ${c.maxlength} caracteres`);
  if (c.min != null) r.push(`mínimo ${c.min}`);
  if (c.max != null) r.push(`máximo ${c.max}`);
  if (c.pattern) r.push(`patrón ${c.pattern}`);
  if (c.opciones && c.opciones.length) r.push(`opciones: ${c.opciones.map((o) => o.texto || o.valor).filter(Boolean).slice(0, 12).join(', ')}`);
  if (c.placeholder) r.push(`placeholder "${c.placeholder}"`);
  return r.join('; ');
}

// Markdown del mapa (con las tablas en Markdown normal: después se pasan por formatear_tablas.py).
function aMarkdown(mapa) {
  const l = [];
  l.push('---', 'titulo: Mapa funcional del sitio', 'tipo: web', `fuentes: ${mapa.url}`, `actualizado: ${mapa.fecha.slice(0, 10)}`,
    'generado_por: npm run mapa-funcional', '---', '', `# Mapa funcional de ${mapa.host}`, '');
  l.push(`Recorrido automático (solo GET, ${mapa.con_sesion ? `**con la sesión iniciada** (${mapa.con_sesion})` : 'sin login'}, sin enviar formularios) de ${mapa.paginas.length} página(s) a partir de ${mapa.url}.`,
    'Describe lo que la aplicación muestra hoy: sirve como contexto, **no** como fuente de requisitos. Los **locators sugeridos** de cada página sirven de punto de partida para automatizar (se verifican antes de usarlos).', '');
  if (!mapa.con_sesion) l.push('> Sin sesión: las pantallas detrás del login no se recorrieron. Guardá la sesión con `npm run login`, poné `SESION=si` en el .env y volvé a correrlo.', '');
  if (mapa.sin_recorrer) l.push(`> Quedaron páginas sin recorrer (límite de ${mapa.max_paginas}): subí --max-paginas para cubrirlas.`, '');
  const c = mapa.cambios;
  if (c && c.hay) {
    l.push(`## Cambios desde el recorrido anterior (${(c.desde || '').slice(0, 10)})`, '',
      'La aplicación cambió: revisá la documentación (manuales, dossiers) y los casos de estas pantallas.', '');
    if (c.nuevas.length) l.push(`- Pantallas nuevas: ${c.nuevas.join(' · ')}`);
    if (c.quitadas.length) l.push(`- Pantallas que ya no se encontraron: ${c.quitadas.join(' · ')}`);
    for (const p of c.paginas) {
      const partes = [];
      if (p.titulo) partes.push(`título "${p.titulo[0]}" → "${p.titulo[1]}"`);
      if (p.campos_nuevos.length) partes.push(`campos nuevos: ${p.campos_nuevos.join(', ')}`);
      if (p.campos_quitados.length) partes.push(`campos quitados: ${p.campos_quitados.join(', ')}`);
      if (p.campos_cambiados.length) partes.push(`campos con otra regla: ${p.campos_cambiados.join(', ')}`);
      if (p.botones_nuevos.length) partes.push(`botones nuevos: ${p.botones_nuevos.join(', ')}`);
      if (p.botones_quitados.length) partes.push(`botones quitados: ${p.botones_quitados.join(', ')}`);
      l.push(`- ${p.ruta}: ${partes.join('; ')}`);
    }
    l.push('');
  } else if (c) {
    l.push(`> Sin cambios desde el recorrido anterior (${(c.desde || '').slice(0, 10)}).`, '');
  }
  if (mapa.navegacion_global.length) {
    l.push('## Navegación global', '');
    for (const m of mapa.navegacion_global) l.push(`- **${m.nombre}**: ${m.items.join(' · ')}`);
    l.push('');
  }
  l.push('## Páginas', '', '| # | Página | Título | Formularios | Campos |', '|---|---|---|---|---|');
  mapa.paginas.forEach((p, i) => l.push(`| ${i + 1} | ${celda(p.ruta)} | ${celda(p.titulo || p.error)} | ${(p.formularios || []).length} | ${(p.formularios || []).reduce((s, f) => s + f.campos.length, 0)} |`));
  l.push('');
  mapa.paginas.forEach((p, i) => {
    l.push(`## ${i + 1}. ${p.titulo || p.ruta}`, '', `- URL: ${p.url}`);
    if (p.error) { l.push(`- No se pudo abrir: ${p.error}`, ''); return; }
    if (p.descripcion) l.push(`- Descripción: ${p.descripcion}`);
    if (p.encabezados.length) l.push(`- Secciones: ${p.encabezados.map((h) => h.texto).join(' · ')}`);
    for (const m of p.menus) l.push(`- Menú ${m.nombre}: ${m.items.join(' · ')}`);
    if (p.botones.length) l.push(`- Botones: ${p.botones.join(' · ')}`);
    if (p.mensajes.length) l.push(`- Mensajes visibles: ${p.mensajes.map((m) => `"${m}"`).join(' · ')}`);
    for (const t of p.tablas) l.push(`- Tabla con columnas: ${t.join(' · ')}`);
    if (p.extracto) l.push(`- Texto: ${p.extracto}`);
    l.push('');
    for (const f of p.formularios) {
      l.push(`### Formulario: ${f.nombre}${f.metodo ? ` (${f.metodo}${f.accion ? ` ${f.accion}` : ''})` : ''}`, '');
      l.push('| Campo | Etiqueta | Tipo | Obligatorio | Restricciones |', '|---|---|---|---|---|');
      for (const c of f.campos) {
        l.push(`| ${celda(c.nombre)} | ${celda(c.etiqueta)} | ${celda(c.tipo)} | ${c.requerido ? 'Sí' : c.marca_obligatorio ? 'Marcado (*)' : 'No'} | ${celda(restricciones(c))} |`);
      }
      l.push('', f.boton ? '' : '> Sin botón de envío visible.', '');
    }
    if ((p.locators || []).length) {
      l.push('### Locators sugeridos', '', '| Elemento | Rol | Locator | Único |', '|---|---|---|---|');
      for (const x of p.locators.slice(0, 40)) l.push(`| ${celda(x.elemento)} | ${celda(x.rol)} | \`${celda(x.locator)}\` | ${x.unico ? 'Sí' : 'No'} |`);
      if (p.locators.length > 40) l.push('', `> ${p.locators.length - 40} locator(s) más en mapa-funcional.json.`);
      l.push('');
    }
  });
  return l.filter((x, i, xs) => !(x === '' && xs[i - 1] === '')).join('\n') + '\n';
}

function formatearTablas(archivo) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(RAIZ, 'scripts', 'formatear_tablas.py'), archivo], { encoding: 'utf8' });
  if (r.status !== 0) console.log(`No pude alinear las tablas (${(r.stderr || r.error || '').toString().trim().split('\n').pop()}). Corré: python scripts/formatear_tablas.py ${path.relative(RAIZ, archivo)}`);
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
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'input', 'documentacion', 'proyecto');
  fs.mkdirSync(carpeta, { recursive: true });

  const { chromium } = require('playwright'); // acá y no arriba: los tests usan las funciones sin instalar k0lmena
  const browser = await chromium.launch({ headless: !a.headed });
  const sesion = a.sinSesion ? null : sesionActiva(process.env.SESION, (m) => console.log(m));
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, locale: process.env.LOCALE || 'es-AR',
    ...(sesion ? { storageState: sesion } : {}) });
  if (sesion) console.log(`Con la sesión guardada (${path.relative(RAIZ, sesion)}).`);
  const page = await ctx.newPage();
  // Nunca se envía nada: cualquier navegación que no sea GET se corta.
  await page.route('**/*', (route) => {
    const rq = route.request();
    return rq.isNavigationRequest() && rq.method() !== 'GET' ? route.abort() : route.continue();
  });

  console.log(`Mapa funcional de ${inicio} · hasta ${a.maxPaginas} páginas · profundidad ${a.profundidad}`);
  const urls = await descubrir(page, inicio, a);
  const paginas = [];
  for (const [i, u] of urls.entries()) {
    process.stdout.write(`[${i + 1}/${urls.length}] ${u} `);
    const reg = { url: u, ruta: new URL(u).pathname + new URL(u).search };
    try {
      const { resp } = await cargar(page, u);
      reg.status = resp ? resp.status() : 0;
      await recorrerScroll(page);
      Object.assign(reg, await page.evaluate(_contenido));
      reg.formularios = (await page.evaluate(extraerFormularios)).map(({ indice, ...f }) => f);
      reg.locators = await page.evaluate(_locators);
      console.log(`· ${reg.formularios.length} formulario(s)`);
    } catch (e) {
      reg.error = String(e.message || e).split('\n')[0];
      console.log(`· error: ${reg.error}`);
    }
    paginas.push(reg);
    if (a.pausaMs) await esperar(a.pausaMs);
  }
  await browser.close();

  const navegacion_global = separarMenusGlobales(paginas.filter((p) => !p.error));
  const mapa = { url: inicio, host, fecha: new Date().toISOString(), max_paginas: a.maxPaginas,
    sin_recorrer: !a.paginas && urls.length >= a.maxPaginas, con_sesion: sesion ? path.basename(sesion) : null,
    navegacion_global, paginas };
  const json = path.join(carpeta, 'mapa-funcional.json');
  const md = path.join(carpeta, 'mapa-funcional.md');
  // Con un recorrido anterior del mismo sitio (y no uno parcial con --paginas), se comparan: qué cambió en la app.
  if (fs.existsSync(json) && !a.paginas) {
    try {
      const anterior = JSON.parse(fs.readFileSync(json, 'utf8'));
      if (anterior.host === host) {
        mapa.cambios = { desde: anterior.fecha, ...compararMapas(anterior, mapa) };
        fs.copyFileSync(json, path.join(carpeta, '_mapa-funcional.anterior.json'));
      }
    } catch (e) { console.log(`No pude comparar con el recorrido anterior: ${e.message}`); }
  }
  fs.writeFileSync(json, JSON.stringify(mapa, null, 2));
  fs.writeFileSync(md, aMarkdown(mapa));
  formatearTablas(md);
  const rel = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  console.log(`\n${paginas.length} página(s), ${paginas.reduce((s, p) => s + (p.formularios || []).length, 0)} formulario(s).`);
  console.log(`Mapa: ${rel(md)} (datos: ${rel(json)})`);
  if (mapa.cambios && mapa.cambios.hay) {
    console.log(`Cambios desde ${mapa.cambios.desde.slice(0, 10)}: ${mapa.cambios.nuevas.length} pantalla(s) nueva(s), ` +
      `${mapa.cambios.quitadas.length} quitada(s), ${mapa.cambios.paginas.length} con cambios (ver el .md).`);
  }
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, separarMenusGlobales, restricciones, aMarkdown, compararMapas, extraerLocators: _locators };

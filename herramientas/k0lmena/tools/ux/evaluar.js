// Evaluación heurística de usabilidad (agente evaluador-ux), con las 10 heurísticas de Nielsen.
//
// Uso (desde la raíz del repo):
//   npm run ux -- [--url https://mi-app.com] [--paginas url1,url2] [--max-paginas 8] [--profundidad 1]
//                 [--resoluciones 1366x768,390x844] [--historia HU-001] [--headed]
//
// Recorre las páginas (solo GET, no envía formularios) en desktop y mobile y revisa lo que se puede medir:
//   H1 Visibilidad del estado: título de cada página (y que no se repita), la sección actual marcada en el menú.
//   H2 Lenguaje de la persona: errores técnicos a la vista (Error 500, Exception, null, NaN, stack traces).
//   H3 Control y libertad: modales sin forma de cerrarlos, links que abren otra pestaña sin avisar.
//   H4 Consistencia: la misma acción con distintos nombres en el sitio (Ingresar / Iniciar sesión / Login),
//      demasiados estilos de botón, varias tipografías, encabezados salteados o más de un h1.
//   H5 Prevención de errores: campos de email, teléfono o fecha como texto libre, contraseñas sin "mostrar".
//   H6 Reconocer antes que recordar: placeholder como única etiqueta, botones de solo ícono sin nombre.
//   H7 Flexibilidad: sin buscador en un sitio con muchas páginas.
//   H8 Diseño minimalista: párrafos muy largos, menús con demasiadas opciones, demasiados botones primarios.
//   H9 Recuperarse de errores: la página 404 (que exista, que no sea técnica y que tenga cómo volver).
//   H10 Ayuda: links de ayuda, preguntas frecuentes o contacto.
//   Mobile: la acción principal visible sin hacer scroll.
// Cada hallazgo con la heurística, la severidad, la página y una captura del elemento marcado. Lo que no se
// puede medir (flujos, feedback de las acciones, carga cognitiva) lo revisa el agente a mano.
//
// Deja todo en output/ux/<HU o host>/ (ux.json, informe-ux.html, capturas/, recortes/); la corrida
// anterior pasa a historial/ (se guardan las últimas 5).
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { normalizar, slug, sello, recorrerScroll, cargar } = require('../explorador/explorar.js');
const { parsearResoluciones, descubrir } = require('../pixel-perfect/pixel-perfect.js');
const visual = require('../visual/comparar.js');
const { archivar } = require('../historial/historial.js');

// Datos (output/, input/, .auth/) en el proyecto y scripts de Python en el código de k0lmenIA: ver ../rutas.js.
const { PROYECTO: RAIZ, CODIGO } = require('../rutas');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p);
const GENERADOS = ['ux.json', 'analisis.json', 'informe-ux.html', 'capturas', 'recortes'];
const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };
const HEURISTICAS = {
  H1: 'Visibilidad del estado del sistema', H2: 'Relación con el mundo real (lenguaje de la persona)', H3: 'Control y libertad',
  H4: 'Consistencia y estándares', H5: 'Prevención de errores', H6: 'Reconocer antes que recordar', H7: 'Flexibilidad y eficiencia',
  H8: 'Diseño estético y minimalista', H9: 'Ayudar a reconocer y recuperarse de errores', H10: 'Ayuda y documentación',
};
// La misma acción con distintos nombres (para la consistencia del vocabulario).
const SINONIMOS = [
  ['ingresar', 'iniciar sesión', 'iniciá sesión', 'login', 'log in', 'entrar', 'acceder'],
  ['registrarse', 'registrate', 'crear cuenta', 'sign up', 'registro'],
  ['cerrar sesión', 'salir', 'logout', 'log out'],
  ['carrito', 'bolsa', 'cesta', 'cart'],
  ['comprar', 'finalizar compra', 'pagar', 'checkout', 'ir a pagar'],
  ['buscar', 'búsqueda', 'search'],
  ['contacto', 'contactanos', 'contáctenos', 'escribinos', 'contact'],
  ['enviar', 'mandar', 'submit'],
];
const PESO = { 'Crítica': 40, 'Alta': 25, 'Media': 10, 'Baja': 4 };

function argumentos(argv) {
  const a = { maxPaginas: 8, profundidad: 1, resoluciones: '1366x768,390x844', headed: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--resoluciones') a.resoluciones = v();
    else if (k === '--historia') a.historia = v();
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  return a;
}

// En la página: todo lo que se mide. Marca con data-k0-ux los elementos de cada hallazgo para recortarlos.
function _medirEnPagina(movil) {
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const caja = (el) => { const r = el.getBoundingClientRect(); return { x: Math.round(r.left + scrollX), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height) }; };
  const desc = (el) => el.tagName.toLowerCase() + (el.id ? `#${el.id}` : '') + (typeof el.className === 'string' && el.className.trim() ? `.${el.className.trim().split(/\s+/).slice(0, 2).join('.')}` : '');
  const texto = (el) => (el.innerText || el.getAttribute('aria-label') || el.value || el.title || '').replace(/\s+/g, ' ').trim();
  const h = [];
  const add = (heur, severidad, titulo, detalle, el) => h.push({ heuristica: heur, severidad, titulo, detalle, elemento: el ? desc(el) : null, caja: el && visible(el) ? caja(el) : null });
  const body = document.body.innerText || '';
  // H2: errores técnicos a la vista
  const tecnico = body.match(/\b(Error \d{3}|Exception|Traceback|Stack ?trace|NullPointer|undefined is not|Cannot read propert\w+|SQLSTATE|ORA-\d+|Uncaught)\b/i);
  if (tecnico) add('H2', 'Alta', `Mensaje técnico a la vista: “${tecnico[0]}”`, 'La persona ve un error de programación en lugar de un mensaje que entienda.', null);
  if (/\b(undefined|NaN|\[object Object\])\b/.test(body)) add('H2', 'Media', 'Valores técnicos en el texto (undefined, NaN, [object Object])', 'Un dato que no se cargó se muestra con el nombre técnico.', null);
  // H1: sección actual marcada
  const nav = document.querySelector('nav, header');
  if (nav) {
    const links = [...nav.querySelectorAll('a[href]')].filter(visible);
    const actual = links.find((l) => l.getAttribute('aria-current') || /\b(active|current|selected|activo)\b/i.test(l.className || '') || l.href === location.href);
    const marcado = actual && (actual.getAttribute('aria-current') || /\b(active|current|selected|activo)\b/i.test(actual.className || ''));
    if (links.length >= 3 && !marcado) add('H1', 'Baja', 'El menú no marca en qué sección estás', 'Sin un indicador (aria-current o estilo activo), la persona no sabe dónde está.', nav);
    if (links.length > 9) add('H8', 'Baja', `Menú principal con ${links.length} opciones`, 'Más de 7 a 9 opciones cuesta recorrerlas: agrupalas.', nav);
  }
  // H3: modales sin cerrar, links a otra pestaña sin aviso
  for (const d of [...document.querySelectorAll('dialog[open], [role=dialog], [aria-modal=true]')].filter(visible)) {
    const cerrar = d.querySelector('button[aria-label*=errar i], [class*=close i], button[title*=errar i]') || [...d.querySelectorAll('button')].find((b) => /cerrar|close|×|✕|cancelar/i.test(texto(b)));
    if (!cerrar) add('H3', 'Media', 'Un modal sin botón para cerrarlo', 'La persona queda atrapada: sumá un botón Cerrar (y que funcione Esc).', d);
  }
  const nuevas = [...document.querySelectorAll('a[target=_blank]')].filter((l) => visible(l) && !/nueva (pestaña|ventana)|new (tab|window)|↗|externo/i.test(texto(l) + (l.getAttribute('aria-label') || '') + (l.title || '')));
  if (nuevas.length >= 3) add('H3', 'Baja', `${nuevas.length} links abren otra pestaña sin avisar`, 'Avisá con un ícono o texto: abrir pestañas sin aviso desorienta (y rompe el botón Atrás).', nuevas[0]);
  // H4: encabezados, tipografías, estilos de botón
  const h1s = [...document.querySelectorAll('h1')].filter(visible);
  if (h1s.length === 0) add('H4', 'Baja', 'La página no tiene un título principal (h1)', 'El h1 dice de qué se trata la página.', null);
  if (h1s.length > 1) add('H4', 'Baja', `La página tiene ${h1s.length} títulos principales (h1)`, 'Un solo h1 por página ordena la jerarquía.', h1s[1]);
  let previo = 0;
  for (const hx of [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(visible)) {
    const n = Number(hx.tagName[1]);
    if (previo && n > previo + 1) { add('H4', 'Baja', `Encabezado salteado: de h${previo} a h${n}`, 'Los niveles de título tienen que seguir un orden.', hx); break; }
    previo = n;
  }
  const fuentes = new Set([...document.querySelectorAll('body *')].slice(0, 1500).filter((x) => x.childElementCount === 0 && (x.innerText || '').trim()).map((x) => getComputedStyle(x).fontFamily.split(',')[0].replace(/["']/g, '').trim()));
  if (fuentes.size > 3) add('H4', 'Baja', `${fuentes.size} tipografías distintas`, `${[...fuentes].slice(0, 5).join(', ')}: con más de 3 la página se ve desordenada.`, null);
  const botones = [...document.querySelectorAll('button, [role=button], a.btn, a[class*=button i], input[type=submit]')].filter(visible);
  const estilos = new Set(botones.map((b) => { const cs = getComputedStyle(b); return `${cs.backgroundColor}|${cs.borderRadius}`; }));
  // H6: botones de solo ícono, placeholder como etiqueta
  for (const b of botones) {
    if (!texto(b) && !b.getAttribute('aria-label') && !b.title) { add('H6', 'Media', 'Botón sin texto ni nombre (solo ícono)', 'No se sabe qué hace hasta tocarlo: sumá un texto visible o aria-label.', b); break; }
  }
  const campos = [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]), textarea, select')].filter(visible);
  const sinEtiqueta = campos.filter((c) => {
    const lab = (c.id && document.querySelector(`label[for="${CSS.escape(c.id)}"]`)) || c.closest('label');
    return !lab && !c.getAttribute('aria-label') && !c.getAttribute('aria-labelledby') && c.getAttribute('placeholder');
  });
  if (sinEtiqueta.length) add('H6', 'Media', `${sinEtiqueta.length} campo(s) usan el placeholder como única etiqueta`, 'Al escribir, el placeholder desaparece y la persona olvida qué pedía el campo.', sinEtiqueta[0]);
  // H5: tipos de campo
  for (const c of campos) {
    const pista = `${c.name} ${c.id} ${c.getAttribute('placeholder') || ''} ${c.getAttribute('autocomplete') || ''}`.toLowerCase();
    const tipo = (c.getAttribute('type') || 'text').toLowerCase();
    if (tipo === 'text' && /mail/.test(pista)) { add('H5', 'Media', 'Campo de email como texto libre', 'Con type="email" el celular muestra el teclado con @ y el navegador valida el formato.', c); break; }
  }
  for (const c of campos) {
    const pista = `${c.name} ${c.id} ${c.getAttribute('placeholder') || ''}`.toLowerCase();
    if ((c.getAttribute('type') || 'text') === 'text' && /(tel|celular|phone|whatsapp)/.test(pista)) { add('H5', 'Baja', 'Campo de teléfono como texto libre', 'Con type="tel" el celular muestra el teclado numérico.', c); break; }
  }
  const pwd = campos.find((c) => c.type === 'password');
  if (pwd) {
    const cerca = pwd.parentElement ? pwd.parentElement.querySelector('button, [role=button], input[type=checkbox]') : null;
    if (!cerca) add('H5', 'Baja', 'La contraseña no tiene la opción de mostrarla', 'Mostrar la contraseña reduce errores de tipeo, sobre todo en el celular.', pwd);
  }
  // H8: párrafos largos y botones principales
  const largos = [...document.querySelectorAll('p')].filter((p) => visible(p) && (p.innerText || '').split(/\s+/).length > 120);
  if (largos.length) add('H8', 'Baja', `${largos.length} párrafo(s) de más de 120 palabras`, 'Los textos largos no se leen: dividilos, usá títulos o listas.', largos[0]);
  // H10: ayuda
  const ayuda = [...document.querySelectorAll('a[href]')].some((l) => /ayuda|help|faq|preguntas frecuentes|soporte|contacto|contact/i.test(texto(l) + l.href));
  // Mobile: acción principal visible sin scroll
  let ctaArriba = null;
  if (movil) {
    const cta = botones.find((b) => b.getBoundingClientRect().width > 60) || null;
    if (cta) ctaArriba = cta.getBoundingClientRect().top < innerHeight;
  }
  // Vocabulario visible (para la consistencia entre páginas).
  const interactivos = [...document.querySelectorAll('a, button, [role=button], input[type=submit]')].filter(visible).map((x) => texto(x).toLowerCase()).filter((t) => t && t.length < 40);
  return { titulo: document.title, hallazgos: h, estilos_boton: estilos.size, tiene_buscador: Boolean(document.querySelector('input[type=search], [role=search], input[name*=search i], input[name=q], input[placeholder*=busc i]')),
    ayuda, cta_arriba: ctaArriba, vocabulario: [...new Set(interactivos)], alto: document.documentElement.scrollHeight };
}

async function revisar404(browser, inicio) {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const u = new URL('/k0lmenia-pagina-que-no-existe-' + Date.now().toString(36), inicio).href;
  try {
    const r = await page.goto(u, { waitUntil: 'load', timeout: 30000 });
    const info = await page.evaluate(() => ({ texto: (document.body.innerText || '').slice(0, 600), links: document.querySelectorAll('a[href]').length,
      tecnico: /(Error \d{3}|Exception|Traceback|nginx|Apache|Cannot GET|Whitelabel)/i.test(document.body.innerText || '') }));
    return { url: u, status: r ? r.status() : 0, ...info };
  } catch (e) {
    return { url: u, error: String(e.message || e).split('\n')[0] };
  } finally {
    await ctx.close();
  }
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(CODIGO, 'scripts', 'generar_informe_ux.py'), path.join(carpeta, 'ux.json'),
    path.join(carpeta, 'informe-ux.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_ux.py <carpeta>/ux.json <carpeta>/informe-ux.html`);
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
  const inicio = normalizar(url);
  const host = new URL(inicio).hostname;
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'ux', a.historia || host);
  archivar(carpeta, GENERADOS, 'ux.json');
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });
  const dirCap = path.join(carpeta, 'capturas');
  const dirRec = path.join(carpeta, 'recortes');
  for (const d of [dirCap, dirRec]) fs.mkdirSync(d, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');
  const relRaiz = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  const { chromium } = require('playwright');
  const browser = await navegadorComun.lanzar(chromium, { headless: !a.headed });
  const t0 = Date.now();
  const c0 = await browser.newContext();
  const paginas = await descubrir(await c0.newPage(), inicio, a);
  await c0.close();
  const resoluciones = parsearResoluciones(a.resoluciones);
  console.log(`UX: ${paginas.length} página(s) × ${resoluciones.length} resolución(es) · salida ${relRaiz(carpeta)}`);
  const pantallas = [];
  let hallazgos = [];
  const titulos = new Map();
  const vocabulario = new Map(); // término → páginas
  let buscador = false;
  let ayuda = false;
  const estilos = [];
  for (const [i, u] of paginas.entries()) {
    const idPag = `${String(i + 1).padStart(2, '0')}-${slug(u)}`;
    for (const res of resoluciones) {
      const movil = res.ancho < 768;
      const ctx = await browser.newContext({ viewport: { width: res.ancho, height: res.alto }, deviceScaleFactor: 1, locale: process.env.LOCALE || 'es-AR',
        ...(movil ? { isMobile: true, hasTouch: true } : {}) });
      const page = await ctx.newPage();
      const p = { pagina: idPag, url: u, resolucion: res.id };
      process.stdout.write(`[${res.id.padEnd(9)}] ${u} `);
      try {
        await cargar(page, u);
        await recorrerScroll(page);
        await page.evaluate(() => window.scrollTo(0, 0));
        await visual.estabilizar(page);
        const m = await page.evaluate(_medirEnPagina, movil);
        const arch = path.join(dirCap, `${idPag}-${res.id}.png`);
        const alto = Math.min(m.alto, 8000);
        await page.screenshot({ path: arch, fullPage: alto === m.alto, ...(alto < m.alto ? { clip: { x: 0, y: 0, width: res.ancho, height: alto } } : {}) });
        p.captura = rel(arch);
        p.titulo = m.titulo;
        if (!movil) {
          titulos.set(m.titulo, [...(titulos.get(m.titulo) || []), u]);
          for (const t of m.vocabulario) vocabulario.set(t, new Set([...(vocabulario.get(t) || []), u]));
          estilos.push(m.estilos_boton);
          buscador = buscador || m.tiene_buscador;
          ayuda = ayuda || m.ayuda;
        }
        if (movil && m.cta_arriba === false) m.hallazgos.push({ heuristica: 'H8', severidad: 'Media', titulo: 'En mobile la acción principal queda abajo del pliegue', detalle: 'Hay que hacer scroll para encontrar el primer botón: subilo o hacelo fijo.', caja: null });
        for (const [k, h] of m.hallazgos.entries()) {
          if (h.caja && h.caja.y < alto) {
            const rec = path.join(dirRec, `${idPag}-${res.id}-${k + 1}.png`);
            fs.writeFileSync(rec, visual.recorteMarcado(arch, visual.ventanaDe([h.caja], 60, 300, 140), h.caja));
            h.recorte = rel(rec);
          }
          hallazgos.push({ ...h, pagina: idPag, url: u, resolucion: res.id, captura: p.captura });
        }
        p.hallazgos = m.hallazgos.length;
        console.log(`→ ${m.hallazgos.length} hallazgo(s)`);
      } catch (e) {
        p.error = String(e.message || e).split('\n')[0].slice(0, 200);
        console.log(`→ error: ${p.error}`);
      }
      pantallas.push(p);
      await ctx.close();
    }
  }
  const p404 = await revisar404(browser, inicio);
  await browser.close();
  // Hallazgos del sitio completo
  const sitio = [];
  for (const [t, us] of titulos) if (us.length > 1 && paginas.length > 1) sitio.push({ heuristica: 'H1', severidad: 'Baja', titulo: `${us.length} páginas con el mismo título: “${t.slice(0, 60)}”`, detalle: 'El título de la pestaña tiene que decir en qué página está la persona.' });
  for (const grupo of SINONIMOS) {
    const usados = grupo.filter((g) => [...vocabulario.keys()].some((t) => t === g || t.startsWith(`${g} `) || t.endsWith(` ${g}`)));
    if (usados.length > 1) sitio.push({ heuristica: 'H4', severidad: 'Media', titulo: `La misma acción con nombres distintos: ${usados.map((x) => `“${x}”`).join(', ')}`, detalle: 'Usá un solo nombre para cada acción en todo el sitio.' });
  }
  const maxEstilos = estilos.length ? Math.max(...estilos) : 0;
  if (maxEstilos > 5) sitio.push({ heuristica: 'H4', severidad: 'Baja', titulo: `${maxEstilos} estilos de botón distintos en una página`, detalle: 'Definí 2 o 3 estilos (principal, secundario, texto) y usalos siempre igual.' });
  if (!buscador && paginas.length >= 8) sitio.push({ heuristica: 'H7', severidad: 'Baja', titulo: 'No hay buscador', detalle: 'En un sitio con muchas páginas, el buscador es el atajo para quien sabe qué busca.' });
  if (!ayuda) sitio.push({ heuristica: 'H10', severidad: 'Baja', titulo: 'No hay links de ayuda, preguntas frecuentes o contacto', detalle: 'La persona que se traba no tiene dónde consultar.' });
  if (p404.error) sitio.push({ heuristica: 'H9', severidad: 'Media', titulo: 'No pude revisar la página de error 404', detalle: p404.error });
  else {
    if (p404.status === 200) sitio.push({ heuristica: 'H9', severidad: 'Media', titulo: 'Una dirección que no existe responde 200', detalle: `${p404.url} debería responder 404 (los buscadores y los monitores se confunden).` });
    if (p404.tecnico) sitio.push({ heuristica: 'H9', severidad: 'Alta', titulo: 'La página de error es técnica', detalle: `Muestra: “${p404.texto.slice(0, 120)}”. Que explique qué pasó y cómo volver.` });
    if (!p404.links) sitio.push({ heuristica: 'H9', severidad: 'Media', titulo: 'La página de error no tiene cómo volver', detalle: 'Sumá el menú o un link al inicio y al buscador.' });
  }
  hallazgos = [...hallazgos, ...sitio.map((h) => ({ ...h, pagina: 'sitio', url: inicio, resolucion: '—' }))];
  // Un mismo problema en varias páginas = un hallazgo.
  // Los números del título (cuántos links, cuántas opciones) cambian de página en página: no cuentan para agrupar.
  const grupos = new Map();
  for (const h of hallazgos) {
    const k = `${h.heuristica}|${h.titulo.replace(/\b\d+\b/g, '#')}`;
    if (!grupos.has(k)) grupos.set(k, { ...h, donde: [] });
    grupos.get(k).donde.push({ url: h.url, resolucion: h.resolucion, recorte: h.recorte, captura: h.captura, titulo: h.titulo });
  }
  for (const g of grupos.values()) {
    if (g.donde.length > 1 && /\b\d+\b/.test(g.titulo)) {
      const sinNumero = g.titulo.replace(/^\d+\s+/, '').replace(/\s*\b\d+\b\s*/g, ' ').trim();
      g.titulo = `${sinNumero.charAt(0).toUpperCase()}${sinNumero.slice(1)} (en ${g.donde.length} pantallas)`;
      g.detalle = `${g.detalle} Por pantalla: ${g.donde.map((d) => d.titulo.match(/\d+/)?.[0]).filter(Boolean).join(', ')}.`;
    }
  }
  hallazgos = [...grupos.values()].sort((x, y) => SEV_ORDEN[x.severidad] - SEV_ORDEN[y.severidad] || y.donde.length - x.donde.length);
  hallazgos.forEach((h, i) => { h.id = `U-${String(i + 1).padStart(2, '0')}`; });
  const porHeur = Object.fromEntries(Object.keys(HEURISTICAS).map((k) => {
    const hs = hallazgos.filter((h) => h.heuristica === k);
    return [k, { nombre: HEURISTICAS[k], hallazgos: hs.length, puntaje: Math.max(0, 100 - hs.reduce((s, h) => s + PESO[h.severidad], 0)) }];
  }));
  const puntaje = Math.round(Object.values(porHeur).reduce((s, x) => s + x.puntaje, 0) / 10);
  const resultado = {
    url: inicio, host, historia: a.historia || null, fecha: new Date().toISOString(), marca: sello(), duracion_s: Math.round((Date.now() - t0) / 1000),
    herramienta: `Playwright ${require('playwright/package.json').version}`, resoluciones: resoluciones.map((r) => r.id), heuristicas: HEURISTICAS,
    resumen: { paginas: paginas.length, pantallas: pantallas.length, hallazgos: hallazgos.length, puntaje, por_heuristica: porHeur,
      por_severidad: Object.fromEntries(['Crítica', 'Alta', 'Media', 'Baja'].map((s) => [s, hallazgos.filter((h) => h.severidad === s).length])) },
    pagina_404: p404, hallazgos, pantallas,
  };
  const salida = path.join(carpeta, 'ux.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  console.log(`\nPuntaje heurístico: ${puntaje}/100 · hallazgos: ${hallazgos.length}`);
  console.log(`Datos: ${relRaiz(salida)}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${relRaiz(path.join(carpeta, 'informe-ux.html'))}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, HEURISTICAS, SINONIMOS, GENERADOS };

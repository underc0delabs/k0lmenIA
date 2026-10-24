// Auditoría de accesibilidad de un sitio web (agente analista-accesibilidad).
//
// Uso (desde la raíz del repo):
//   npm run accesibilidad -- [--url https://mi-app.com] [--historia HU-001] [--nivel A|AA|AAA]
//                            [--max-paginas 15] [--profundidad 2] [--paginas url1,url2]
//                            [--buenas-practicas si|no] [--tabs 60] [--video si|no] [--headed]
//
// Recorre las páginas del mismo sitio a partir de la URL (por defecto APP_URL del .env, o BASEURL),
// o solo las de --paginas, y en cada una:
//   - corre axe-core con las reglas WCAG 2.2 del nivel pedido (AA por defecto) y, si se pide, las
//     buenas prácticas; los textos de axe salen en español,
//   - navega con Tab: elementos que reciben foco sin indicador visible, trampas de foco y enlace
//     para saltar al contenido,
//   - revisa el reflow a 320px de ancho (WCAG 1.4.10).
//
// Evidencia: captura de cada página con los elementos que fallan marcados en rojo, captura de
// cada elemento que falla y un video del recorrido. Al terminar genera el informe HTML
// (scripts/generar_informe_accesibilidad.py).
//
// Solo navega con GET y no envía formularios. Deja todo en output/accesibilidad/<HU o host>/ y
// la corrida anterior (con su analisis.json) pasa a historial/ (se guardan las últimas 5).
//
// Una auditoría automática encuentra entre un 30 y un 50 % de los problemas de accesibilidad:
// el resto requiere revisión manual (la hace el agente).
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { archivar } = require('../historial/historial.js');
const { normalizar, slug, sello, NO_RECORRER, ARCHIVO, recorrerScroll, cargar, capturar } = require('../explorador/explorar.js');

// Datos (output/, input/, .auth/) en el proyecto y scripts de Python en el código de k0lmenIA: ver ../rutas.js.
const { PROYECTO: RAIZ, CODIGO } = require('../rutas');
const GENERADOS = ['auditoria.json', 'analisis.json', 'informe-accesibilidad.html', 'capturas', 'videos'];
const IMPACTO = { critical: 'Crítica', serious: 'Alta', moderate: 'Media', minor: 'Baja' };
const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };
const TAGS = {
  A: ['wcag2a', 'wcag21a', 'wcag22a'],
  AA: ['wcag2a', 'wcag21a', 'wcag22a', 'wcag2aa', 'wcag21aa', 'wcag22aa'],
  AAA: ['wcag2a', 'wcag21a', 'wcag22a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'wcag2aaa', 'wcag21aaa', 'wcag22aaa'],
};

function argumentos(argv) {
  const a = { nivel: 'AA', maxPaginas: 15, profundidad: 2, buenasPracticas: true, tabs: 60, video: true, headed: false, pausaMs: 200 };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--historia') a.historia = v();
    else if (k === '--nivel') a.nivel = String(v()).toUpperCase();
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--buenas-practicas') a.buenasPracticas = !/^(no|false|0)$/i.test(v());
    else if (k === '--tabs') a.tabs = parseInt(v(), 10);
    else if (k === '--video') a.video = !/^(no|false|0)$/i.test(v());
    else if (k === '--pausa-ms') a.pausaMs = parseInt(v(), 10);
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (!TAGS[a.nivel]) throw new Error('--nivel tiene que ser A, AA o AAA.');
  return a;
}

// "wcag143" → "1.4.3"; "wcag1410" → "1.4.10".
function criterios(tags) {
  return (tags || []).map((t) => t.match(/^wcag(\d)(\d)(\d{1,2})$/)).filter(Boolean).map((m) => `${m[1]}.${m[2]}.${m[3]}`);
}

function nivelDe(tags) {
  if ((tags || []).some((t) => /^wcag2\d?a$/.test(t))) return 'A';
  if ((tags || []).some((t) => /^wcag2\d?aa$/.test(t))) return 'AA';
  if ((tags || []).some((t) => /^wcag2\d?aaa$/.test(t))) return 'AAA';
  return null;
}

// Severidad: la del impacto de axe; las buenas prácticas (sin criterio WCAG) bajan un nivel.
function severidad(impacto, tags) {
  const s = IMPACTO[impacto] || 'Media';
  if (criterios(tags).length) return s;
  return { 'Crítica': 'Alta', 'Alta': 'Media', 'Media': 'Baja', 'Baja': 'Baja' }[s];
}

// La corrida anterior no se borra: pasa a historial/<fecha>/ (se guardan las últimas 5) para compararla.
function limpiarCarpeta(carpeta) {
  archivar(carpeta, GENERADOS, 'auditoria.json');
  for (const nombre of GENERADOS) fs.rmSync(path.join(carpeta, nombre), { recursive: true, force: true });
}

// Recorre la página con Tab y devuelve el orden de foco y los problemas. Por cada paso compara
// el estilo del elemento con foco y sin foco: si no cambia nada, no tiene indicador visible.
async function navegarConTeclado(page, tabs, capturaFoco = null) {
  await page.evaluate(() => { if (document.activeElement) document.activeElement.blur(); window.scrollTo(0, 0); });
  const pasos = [];
  let repetido = 0;
  for (let i = 0; i < tabs; i++) {
    await page.keyboard.press('Tab');
    const info = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body || el === document.documentElement) return null;
      const desc = (n) => {
        let s = n.tagName.toLowerCase();
        if (n.id) s += `#${n.id}`;
        const c = (typeof n.className === 'string' ? n.className : '').trim().split(/\s+/).filter(Boolean).slice(0, 2);
        if (c.length) s += `.${c.join('.')}`;
        return s;
      };
      const estilo = (n) => {
        const cs = getComputedStyle(n);
        return [cs.outlineStyle, cs.outlineWidth, cs.outlineColor, cs.boxShadow, cs.borderColor, cs.borderWidth,
          cs.backgroundColor, cs.color, cs.textDecorationLine].join('|');
      };
      // Identidad real del elemento (dos links iguales seguidos no son el mismo elemento).
      window.__k0ids = window.__k0ids || new WeakMap();
      if (!window.__k0ids.has(el)) window.__k0ids.set(el, (window.__k0n = (window.__k0n || 0) + 1));
      const conFoco = estilo(el);
      const r = el.getBoundingClientRect();
      // Sin foco (sacándolo un instante) para comparar, y se devuelve el foco.
      el.setAttribute('data-k0-tab', '1');
      el.blur();
      const sinFoco = estilo(el);
      el.focus({ preventScroll: true });
      el.removeAttribute('data-k0-tab');
      return {
        uid: window.__k0ids.get(el), elemento: desc(el), texto: (el.innerText || el.getAttribute('aria-label') || el.value || el.title || '').trim().slice(0, 50),
        visible_indicador: conFoco !== sinFoco, en_pantalla: r.width > 0 && r.height > 0, url: location.href,
      };
    });
    if (!info) { if (pasos.length) break; continue; } // volvió al inicio (o al navegador): fin del ciclo
    if (info.url.split('#')[0] !== page.url().split('#')[0]) break;
    const anterior = pasos[pasos.length - 1];
    if (anterior && anterior.uid === info.uid) {
      repetido++;
      if (repetido >= 3) {
        if (capturaFoco) info.captura = await capturaFoco('trampa');
        return { pasos, trampa: info };
      }
      continue;
    }
    repetido = 0;
    if (pasos.some((x) => x.uid === info.uid)) break; // dio la vuelta (o volvió a un elemento ya visitado)
    // Evidencia de los primeros elementos sin indicador de foco (captura con el foco puesto).
    if (!info.visible_indicador && capturaFoco && pasos.filter((x) => !x.visible_indicador).length < 3) {
      info.captura = await capturaFoco(`sin-foco-${pasos.length + 1}`);
    }
    pasos.push(info);
  }
  return { pasos, trampa: null };
}

// Captura de un elemento con contexto: un margen alrededor y el elemento marcado en rojo, así se
// entiende qué se señala (un campo de 30 px solo, en una miniatura, es un rectángulo en blanco).
async function capturarElemento(page, selector, archivo, margen = 90) {
  const loc = page.locator(selector).first();
  try {
    await loc.scrollIntoViewIfNeeded({ timeout: 3000 });
    const caja = await loc.boundingBox();
    if (!caja) return;
    await loc.evaluate((el) => {
      el.setAttribute('data-k0-foco', '');
      if (!document.getElementById('k0-foco')) {
        const s = document.createElement('style');
        s.id = 'k0-foco';
        s.textContent = '[data-k0-foco]{outline:3px solid #ff2d2d !important;outline-offset:3px !important;box-shadow:0 0 0 9px rgba(255,45,45,.28) !important}';
        document.head.appendChild(s);
      }
    });
    const vp = page.viewportSize();
    const ancho = Math.min(vp.width, Math.max(caja.width + margen * 2, 360));
    const alto = Math.min(vp.height, Math.max(caja.height + margen * 2, 220));
    const x = Math.max(0, Math.min(caja.x + caja.width / 2 - ancho / 2, vp.width - ancho));
    const y = Math.max(0, Math.min(caja.y + caja.height / 2 - alto / 2, vp.height - alto));
    await page.screenshot({ path: archivo, type: 'jpeg', quality: 82, clip: { x, y, width: ancho, height: alto }, timeout: 5000 });
  } catch {
    // si el elemento no se puede ubicar (oculto, fuera del documento), queda sin captura
  } finally {
    await loc.evaluate((el) => el.removeAttribute('data-k0-foco')).catch(() => {});
  }
}

// Corre axe en la página (con los textos en español) y devuelve solo lo necesario.
async function correrAxe(page, tags, locale) {
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
  return page.evaluate(async ({ tags, locale }) => {
    window.axe.configure({ locale });
    const r = await window.axe.run(document, { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations', 'incomplete'] });
    const nodos = (ns, max) => ns.slice(0, max).map((n) => ({
      selector: Array.isArray(n.target) ? n.target.map((t) => (Array.isArray(t) ? t.join(' >>> ') : t)).join(' → ') : String(n.target),
      simple: Array.isArray(n.target) && n.target.length === 1 && typeof n.target[0] === 'string' ? n.target[0] : null,
      html: (n.html || '').slice(0, 300), resumen: (n.failureSummary || '').slice(0, 600), impacto: n.impact,
    }));
    const regla = (v, max) => ({ id: v.id, impacto: v.impact, titulo: v.help, descripcion: v.description, ayuda: v.helpUrl,
      tags: v.tags, total_nodos: v.nodes.length, nodos: nodos(v.nodes, max) });
    return { violaciones: r.violations.map((v) => regla(v, 25)), revisar: r.incomplete.map((v) => regla(v, 5)),
      aprobadas: r.passes.map((p) => p.id), no_aplican: r.inapplicable.length };
  }, { tags, locale });
}

function armarHallazgos(paginas) {
  const porRegla = new Map();
  const revisar = new Map();
  const otros = [];
  for (const p of paginas) {
    for (const v of p.violaciones || []) {
      if (!porRegla.has(v.id)) {
        porRegla.set(v.id, { fuente: 'axe', regla: v.id, titulo: v.titulo, descripcion: v.descripcion, ayuda: v.ayuda,
          impacto: v.impacto, severidad: severidad(v.impacto, v.tags), wcag: criterios(v.tags), nivel: nivelDe(v.tags),
          buena_practica: !criterios(v.tags).length, paginas: [], total_nodos: 0, ejemplos: [] });
      }
      const h = porRegla.get(v.id);
      h.paginas.push(p.url);
      h.total_nodos += v.total_nodos;
      for (const n of v.nodos) if (h.ejemplos.length < 12) h.ejemplos.push({ pagina: p.url, ...n });
    }
    for (const v of p.revisar || []) {
      if (!revisar.has(v.id)) {
        revisar.set(v.id, { regla: v.id, titulo: v.titulo, descripcion: v.descripcion, ayuda: v.ayuda, wcag: criterios(v.tags),
          paginas: [], total_nodos: 0, ejemplos: [] });
      }
      const h = revisar.get(v.id);
      h.paginas.push(p.url);
      h.total_nodos += v.total_nodos;
      for (const n of v.nodos) if (h.ejemplos.length < 5) h.ejemplos.push({ pagina: p.url, ...n });
    }
    const t = p.teclado;
    if (t && t.trampa) {
      otros.push({ fuente: 'teclado', regla: 'trampa-de-foco', titulo: 'Trampa de foco: con Tab no se puede salir de un elemento',
        descripcion: 'Al navegar con el teclado, el foco queda atrapado y la persona no puede seguir recorriendo la página.',
        severidad: 'Crítica', wcag: ['2.1.2'], nivel: 'A', paginas: [p.url], total_nodos: 1,
        ejemplos: [{ pagina: p.url, selector: t.trampa.elemento, html: t.trampa.texto, resumen: 'El foco se repite en este elemento.', captura: t.trampa.captura }] });
    }
    const sinIndicador = (t ? t.pasos : []).filter((x) => !x.visible_indicador);
    if (sinIndicador.length) {
      otros.push({ fuente: 'teclado', regla: 'foco-no-visible', titulo: 'Elementos que reciben foco sin indicador visible',
        descripcion: 'Al llegar con Tab, el elemento no cambia de aspecto: quien navega con teclado no sabe dónde está.',
        severidad: 'Alta', wcag: ['2.4.7'], nivel: 'AA', paginas: [p.url], total_nodos: sinIndicador.length,
        ejemplos: sinIndicador.slice(0, 8).map((x) => ({ pagina: p.url, selector: x.elemento, html: x.texto,
          resumen: 'Mismo estilo con foco y sin foco (outline, sombra, borde, fondo, color y subrayado).', captura: x.captura })) });
    }
    if (t && t.pasos.length > 3 && !/salt|skip|ir al contenido|contenido principal|main content/i.test(t.pasos[0].texto)) {
      otros.push({ fuente: 'teclado', regla: 'sin-salto-al-contenido', titulo: 'Sin enlace para saltar al contenido principal',
        descripcion: 'El primer elemento con foco no permite saltar el menú: quien usa teclado tiene que recorrerlo en cada página.',
        severidad: 'Baja', wcag: ['2.4.1'], nivel: 'A', paginas: [p.url], total_nodos: 1,
        ejemplos: [{ pagina: p.url, selector: t.pasos[0].elemento, html: t.pasos[0].texto, resumen: 'Primer elemento con foco.' }] });
    }
    if (p.reflow && p.reflow.desborda) {
      otros.push({ fuente: 'reflow', regla: 'reflow-320', titulo: 'El contenido no se adapta a 320px de ancho',
        descripcion: `A 320px el contenido mide ${p.reflow.ancho_documento}px: hay que desplazarse en dos direcciones para leerlo (equivale a un zoom del 400 %).`,
        severidad: 'Media', wcag: ['1.4.10'], nivel: 'AA', paginas: [p.url], total_nodos: 1,
        ejemplos: [{ pagina: p.url, selector: p.reflow.elemento || '', html: '', resumen: '', captura: p.reflow.captura }] });
    }
  }
  // Los hallazgos de teclado y reflow repetidos en varias páginas se juntan, como los de axe.
  for (const o of otros) {
    const k = `${o.fuente}:${o.regla}`;
    if (!porRegla.has(k)) porRegla.set(k, o);
    else {
      const h = porRegla.get(k);
      h.paginas.push(...o.paginas);
      h.total_nodos += o.total_nodos;
      for (const ej of o.ejemplos) if (h.ejemplos.length < 12) h.ejemplos.push(ej);
    }
  }
  const lista = [...porRegla.values()].sort((a, b) => SEV_ORDEN[a.severidad] - SEV_ORDEN[b.severidad] || b.total_nodos - a.total_nodos);
  return {
    hallazgos: lista.map((x, i) => ({ id: `A-${String(i + 1).padStart(2, '0')}`, ...x })),
    revisar: [...revisar.values()].map((x, i) => ({ id: `R-${String(i + 1).padStart(2, '0')}`, ...x })),
  };
}

// % de reglas que pasan sobre las que aplican, sumando todas las páginas.
function cumplimiento(paginas) {
  let ok = 0;
  let mal = 0;
  for (const p of paginas) { ok += (p.aprobadas || []).length; mal += (p.violaciones || []).length; }
  return ok + mal ? Math.round((ok / (ok + mal)) * 1000) / 10 : null;
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(CODIGO, 'scripts', 'generar_informe_accesibilidad.py'),
    path.join(carpeta, 'auditoria.json'), path.join(carpeta, 'informe-accesibilidad.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_accesibilidad.py ` +
      '<carpeta>/auditoria.json <carpeta>/informe-accesibilidad.html');
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
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  if (!(a.maxPaginas >= 1 && a.maxPaginas <= 200)) throw new Error('--max-paginas tiene que estar entre 1 y 200.');
  const inicioUrl = normalizar(url);
  const host = new URL(inicioUrl).hostname;
  const tags = [...TAGS[a.nivel], ...(a.buenasPracticas ? ['best-practice'] : [])];
  const locale = JSON.parse(fs.readFileSync(require.resolve('axe-core/locales/es.json'), 'utf8'));

  const carpeta = a.salida ? path.resolve(a.salida) : path.join(RAIZ, 'output', 'accesibilidad', a.historia || host);
  limpiarCarpeta(carpeta);
  const dirPaginas = path.join(carpeta, 'capturas', 'paginas');
  const dirElementos = path.join(carpeta, 'capturas', 'elementos');
  const dirVideos = path.join(carpeta, 'videos');
  for (const d of [dirPaginas, dirElementos, dirVideos]) fs.mkdirSync(d, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');

  console.log(`Accesibilidad de ${inicioUrl} · WCAG 2.2 nivel ${a.nivel}${a.buenasPracticas ? ' + buenas prácticas' : ''} · hasta ${a.maxPaginas} páginas`);
  console.log(`Salida: ${path.relative(RAIZ, carpeta).split(path.sep).join('/')} (reemplaza la corrida anterior)`);
  const t0 = Date.now();
  const { chromium } = require('playwright');
  const browser = await navegadorComun.lanzar(chromium, { headless: !a.headed });
  const viewport = { width: 1280, height: 720 };
  const context = await browser.newContext({ viewport, locale: process.env.LOCALE || 'es-AR',
    ...(a.video ? { recordVideo: { dir: path.join(dirVideos, 'tmp'), size: viewport } } : {}) });
  const page = await context.newPage();

  const cola = (a.paginas || [inicioUrl]).map((u) => ({ url: normalizar(u), nivel: 0 }));
  const enCola = new Set(cola.map((c) => c.url));
  const visitadas = new Set();
  const paginas = [];
  while (cola.length && paginas.length < a.maxPaginas) {
    const { url: u, nivel } = cola.shift();
    if (visitadas.has(u)) continue;
    visitadas.add(u);
    const n = String(paginas.length + 1).padStart(2, '0');
    const reg = { url: u, titulo: '', status: 0 };
    process.stdout.write(`[${paginas.length + 1}/${a.maxPaginas}] ${u} `);
    try {
      const { resp } = await cargar(page, u);
      reg.status = resp ? resp.status() : 0;
      reg.titulo = await page.title();
      reg.idioma = await page.evaluate(() => document.documentElement.getAttribute('lang'));
      await recorrerScroll(page);
      // Links para seguir recorriendo (solo si no se pasó una lista fija de páginas).
      if (!a.paginas && nivel < a.profundidad) {
        const hrefs = await page.evaluate(() => [...document.querySelectorAll('a[href]')].map((x) => x.href));
        for (const h of hrefs) {
          let abs;
          try { abs = new URL(h); } catch { continue; }
          if (!/^https?:$/.test(abs.protocol) || abs.hostname !== host) continue;
          const nu = normalizar(abs.href);
          if (!enCola.has(nu) && !NO_RECORRER.test(abs.pathname + abs.search) && !ARCHIVO.test(abs.pathname)) {
            enCola.add(nu);
            cola.push({ url: nu, nivel: nivel + 1 });
          }
        }
      }
      const axe = await correrAxe(page, tags, locale);
      Object.assign(reg, axe);
      // Captura del elemento con foco, con un margen alrededor para que se vea el contexto.
      const capturaFoco = async (nombre) => {
        const caja = await page.locator(':focus').first().boundingBox().catch(() => null);
        if (!caja) return undefined;
        const archivo = path.join(dirElementos, `${n}-teclado-${nombre}.jpg`);
        const vp = page.viewportSize();
        const x = Math.max(0, caja.x - 40);
        const y = Math.max(0, caja.y - 40);
        await page.screenshot({ path: archivo, type: 'jpeg', quality: 80, clip: { x, y,
          width: Math.min(vp.width - x, caja.width + 80), height: Math.min(vp.height - y, caja.height + 80) } }).catch(() => {});
        return fs.existsSync(archivo) ? rel(archivo) : undefined;
      };
      reg.teclado = await navegarConTeclado(page, a.tabs, capturaFoco).catch((e) => ({ pasos: [], trampa: null, error: e.message }));

      // Evidencia: cada elemento que falla (los primeros de cada regla) y la página con todo marcado.
      for (const v of reg.violaciones) {
        for (const [i, nodo] of v.nodos.entries()) {
          if (!nodo.simple) continue;
          if (i < 3) {
            const archivo = path.join(dirElementos, `${n}-${v.id}-${i + 1}.jpg`);
            await capturarElemento(page, nodo.simple, archivo);
            if (fs.existsSync(archivo)) nodo.captura = rel(archivo);
          }
          await page.evaluate((s) => { try { document.querySelectorAll(s).forEach((e) => e.setAttribute('data-k0-marca', '')); } catch {} }, nodo.simple);
        }
      }
      const archivo = path.join(dirPaginas, `${n}-${slug(u)}.jpg`);
      await capturar(page, archivo);
      if (fs.existsSync(archivo)) reg.captura = rel(archivo);

      // Reflow (1.4.10): a 320px de ancho no tiene que haber scroll horizontal.
      await page.setViewportSize({ width: 320, height: 640 });
      await cargar(page, u);
      reg.reflow = await page.evaluate(() => {
        const vw = document.documentElement.clientWidth;
        const ancho = Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0);
        let elemento = null;
        if (ancho > vw + 1) {
          const el = [...document.body.querySelectorAll('*')].find((x) => {
            const r = x.getBoundingClientRect();
            return r.right > vw + 1 && r.width > 0 && (!x.parentElement || x.parentElement.getBoundingClientRect().right <= vw + 1);
          });
          if (el) {
            el.setAttribute('data-k0-marca', '');
            elemento = el.tagName.toLowerCase() + (el.id ? `#${el.id}` : '') + (typeof el.className === 'string' && el.className.trim() ? `.${el.className.trim().split(/\s+/).slice(0, 2).join('.')}` : '');
          }
        }
        return { ancho_documento: ancho, ancho_ventana: vw, desborda: ancho > vw + 1, elemento };
      });
      if (reg.reflow.desborda) {
        const cap = path.join(dirPaginas, `${n}-${slug(u)}-320.jpg`);
        await capturar(page, cap);
        if (fs.existsSync(cap)) reg.reflow.captura = rel(cap);
      }
      await page.setViewportSize(viewport);
      console.log(`→ ${reg.status} · ${reg.violaciones.length} regla(s) que fallan · ${reg.teclado.pasos.length} elementos con Tab`);
    } catch (e) {
      reg.error = String(e.message || e).split('\n')[0].slice(0, 200);
      console.log(`→ error: ${reg.error}`);
      await page.setViewportSize(viewport).catch(() => {});
    }
    paginas.push(reg);
    if (a.pausaMs > 0) await new Promise((r) => setTimeout(r, a.pausaMs));
  }
  const video = a.video ? page.video() : null;
  await context.close();
  const videos = [];
  if (video) {
    const destino = path.join(dirVideos, 'recorrido.webm');
    await video.saveAs(destino).catch(() => {});
    await video.delete().catch(() => {});
    if (fs.existsSync(destino)) videos.push({ titulo: 'Recorrido de la auditoría (axe, teclado y reflow)', archivo: rel(destino) });
  }
  await browser.close();
  fs.rmSync(path.join(dirVideos, 'tmp'), { recursive: true, force: true });

  const { hallazgos, revisar } = armarHallazgos(paginas);
  const cuenta = (s) => hallazgos.filter((h) => h.severidad === s).length;
  const resultado = {
    url: inicioUrl, host, historia: a.historia || null, fecha: new Date().toISOString(), marca: sello(),
    duracion_s: Math.round((Date.now() - t0) / 1000), herramienta: `axe-core ${require('axe-core/package.json').version}`,
    config: { nivel: a.nivel, buenas_practicas: a.buenasPracticas, max_paginas: a.maxPaginas, profundidad: a.profundidad, tabs: a.tabs, tags },
    resumen: {
      paginas: paginas.length, paginas_sin_recorrer: cola.filter((c) => !visitadas.has(c.url)).length,
      cumplimiento_pct: cumplimiento(paginas), hallazgos: hallazgos.length,
      criticos: cuenta('Crítica'), altos: cuenta('Alta'), medios: cuenta('Media'), bajos: cuenta('Baja'),
      elementos_afectados: hallazgos.reduce((s, h) => s + h.total_nodos, 0),
      criterios_incumplidos: [...new Set(hallazgos.flatMap((h) => h.wcag))].sort(),
      a_revisar: revisar.length,
    },
    hallazgos, revisar, paginas, videos,
  };
  const salida = path.join(carpeta, 'auditoria.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  const r = resultado.resumen;
  console.log(`\nPáginas: ${r.paginas} · cumplimiento automático: ${r.cumplimiento_pct ?? '—'} % de las reglas`);
  console.log(`Hallazgos: ${r.hallazgos} (${r.criticos} críticos, ${r.altos} altos, ${r.medios} medios, ${r.bajos} bajos) · ${r.elementos_afectados} elementos`);
  console.log(`Criterios WCAG incumplidos: ${r.criterios_incumplidos.join(', ') || 'ninguno'} · para revisar a mano: ${r.a_revisar}`);
  console.log(`Datos: ${path.relative(RAIZ, salida).split(path.sep).join('/')}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${path.relative(RAIZ, path.join(carpeta, 'informe-accesibilidad.html')).split(path.sep).join('/')}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, criterios, nivelDe, severidad, armarHallazgos, cumplimiento, limpiarCarpeta, GENERADOS };

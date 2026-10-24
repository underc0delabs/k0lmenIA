// Exploración automática de un sitio web con Playwright (agente explorador-web).
//
// Uso (desde la raíz del repo):
//   npm run explorar -- [--url https://mi-app.com] [--historia HU-001] [--max-paginas 25]
//                       [--profundidad 3] [--resoluciones 360x740,768x1024,1366x768]
//                       [--responsive 10] [--externos si|no] [--video si|no] [--lenta-ms 3000]
//                       [--pausa-ms 300] [--headed]
//
// Recorre las páginas del mismo host a partir de la URL (por defecto APP_URL del .env, o BASEURL)
// y en cada una revisa:
//   - links rotos (internos y externos) e imágenes rotas,
//   - errores de JavaScript, errores de consola y recursos que fallan (4xx/5xx, sin respuesta),
//   - responsive: desborde horizontal, elementos que se salen de la pantalla, texto chico,
//     objetivos táctiles chicos y meta viewport, en varias resoluciones,
//   - métricas de carga de cada página (tiempo total, primer byte, DOM listo, requests y peso).
//
// Evidencia: captura de página completa de cada página (desktop) y de cada página en cada
// resolución, con los elementos con problemas marcados en rojo, y un video del recorrido y de
// cada resolución. Al terminar genera el informe HTML (scripts/generar_informe_exploratorio.py).
//
// Solo navega con GET: no completa ni envía formularios y no sigue links de cierre de sesión.
// Deja todo en output/exploratorias/<HU o host>/: exploracion.json, informe-exploratorio.html, capturas/
// y videos/. La corrida anterior (con su analisis.json) pasa a historial/ (se guardan las últimas 5).
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { archivar } = require('../historial/historial.js');

const RAIZ = path.resolve(__dirname, '..', '..', '..', '..');

const RESOLUCIONES_POR_DEFECTO = '360x740,390x844,768x1024,1366x768,1920x1080';
const NOMBRE_RESOLUCION = (ancho) => (ancho < 600 ? 'Mobile' : ancho < 1024 ? 'Tablet' : 'Desktop');
// Links que no se recorren aunque sean del sitio: cierran la sesión o tienen efecto con un GET.
const NO_RECORRER = /(log-?out|sign-?out|salir|cerrar-?sesion|desconectar|delete|borrar|eliminar|unsubscribe)/i;
// Archivos que se verifican (status) pero no se abren como página.
const ARCHIVO = /\.(pdf|zip|rar|7z|gz|docx?|xlsx?|pptx?|csv|mp3|mp4|avi|mov|webm|jpe?g|png|gif|webp|avif|svg|ico|exe|dmg|apk)$/i;
// Status que no prueban que el link esté roto: piden login o bloquean a los robots.
const NO_VERIFICABLE = new Set([401, 403, 405, 429, 999]);

function argumentos(argv) {
  const a = { maxPaginas: 25, profundidad: 3, responsive: 10, externos: true, pausaMs: 300, headed: false,
    resoluciones: RESOLUCIONES_POR_DEFECTO, video: true, lentaMs: 3000 };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--historia') a.historia = v();
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--resoluciones') a.resoluciones = v();
    else if (k === '--responsive') { const r = v(); a.responsive = r === 'todas' ? Infinity : parseInt(r, 10); }
    else if (k === '--externos') a.externos = !/^(no|false|0)$/i.test(v());
    else if (k === '--pausa-ms') a.pausaMs = parseInt(v(), 10);
    else if (k === '--video') a.video = !/^(no|false|0)$/i.test(v());
    else if (k === '--lenta-ms') a.lentaMs = parseInt(v(), 10);
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  return a;
}

function parsearResoluciones(texto) {
  return texto.split(',').map((r) => r.trim()).filter(Boolean).map((r) => {
    const m = r.match(/^(\d{3,4})x(\d{3,4})$/);
    if (!m) throw new Error(`Resolución inválida: ${r} (formato ANCHOxALTO, ej. 390x844)`);
    const ancho = Number(m[1]);
    return { ancho, alto: Number(m[2]), id: r, nombre: NOMBRE_RESOLUCION(ancho) };
  });
}

// Normaliza para no visitar dos veces lo mismo: sin #fragmento y sin "/" final redundante.
function normalizar(url) {
  const u = new URL(url);
  u.hash = '';
  if (u.pathname.length > 1 && u.pathname.endsWith('/')) u.pathname = u.pathname.slice(0, -1);
  return u.href;
}

function slug(url) {
  const u = new URL(url);
  const s = (u.pathname + u.search).replace(/[^a-z0-9]+/gi, '-').replace(/^-+|-+$/g, '').toLowerCase();
  return (s || 'inicio').slice(0, 60);
}

const sello = () => {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
};

const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

async function enParalelo(items, limite, fn) {
  let i = 0;
  const trabajadores = Array.from({ length: Math.min(limite, items.length) }, async () => {
    while (i < items.length) { const it = items[i++]; await fn(it); }
  });
  await Promise.all(trabajadores);
}

// Baja hasta el final de a poco para que carguen las imágenes lazy, y vuelve arriba.
async function recorrerScroll(page) {
  await page.evaluate(async () => {
    const paso = Math.max(200, window.innerHeight * 0.8);
    for (let y = 0; y < document.documentElement.scrollHeight && y < 30000; y += paso) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 120));
    }
    window.scrollTo(0, 0);
  }).catch(() => {});
}

async function cargar(page, url) {
  const inicio = Date.now();
  const resp = await page.goto(url, { waitUntil: 'load', timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
  return { resp, ms: Date.now() - inicio };
}

// Lo que se revisa dentro de la página en la resolución de escritorio.
function revisarContenido() {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
  };
  const imagenes = [...document.images];
  const rotasEl = imagenes.filter((img) => img.complete && img.naturalWidth === 0 && (img.currentSrc || img.getAttribute('src')));
  rotasEl.forEach((img) => img.setAttribute('data-k0-marca', ''));
  const rotas = rotasEl.map((img) => ({ src: img.currentSrc || img.src, alt: img.getAttribute('alt') }));
  const sinAlt = imagenes.filter((img) => !img.hasAttribute('alt') && visible(img))
    .map((img) => img.currentSrc || img.src).filter(Boolean);
  const links = [...document.querySelectorAll('a[href]')].map((a) => ({
    href: a.href, texto: (a.innerText || a.getAttribute('aria-label') || a.title || '').trim().slice(0, 80),
  }));
  const meta = document.querySelector('meta[name="viewport"]');
  return {
    titulo: document.title, rotas, sinAlt: sinAlt.slice(0, 20), totalSinAlt: sinAlt.length,
    totalImagenes: imagenes.length, links, metaViewport: meta ? meta.getAttribute('content') : null,
  };
}

// Lo que se revisa en cada resolución.
function revisarResponsive(esMobile) {
  const vw = document.documentElement.clientWidth;
  const anchoDoc = Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0);
  const desc = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += `#${el.id}`;
    const clases = (typeof el.className === 'string' ? el.className : '').trim().split(/\s+/).filter(Boolean).slice(0, 2);
    if (clases.length) s += `.${clases.join('.')}`;
    return s;
  };
  const visible = (el, r) => {
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && cs.opacity !== '0';
  };
  const todos = [...document.body.querySelectorAll('*')];
  const desbordan = new Set();
  const desbordados = [];
  if (anchoDoc > vw + 1) {
    for (const el of todos) {
      const r = el.getBoundingClientRect();
      if (r.right > vw + 1 && visible(el, r)) {
        desbordan.add(el);
        // Solo el elemento más externo que desborda (si el padre también desborda, se informa el padre).
        if (!desbordan.has(el.parentElement) && desbordados.length < 8) {
          el.setAttribute('data-k0-marca', '');
          desbordados.push({ elemento: desc(el), ancho: Math.round(r.width), derecha: Math.round(r.right) });
        }
      }
    }
  }
  let textoChico = 0;
  const ejemplosTexto = [];
  const tactiles = [];
  if (esMobile) {
    for (const el of todos) {
      const tieneTexto = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
      if (!tieneTexto) continue;
      const r = el.getBoundingClientRect();
      const px = parseFloat(getComputedStyle(el).fontSize);
      if (px < 12 && visible(el, r)) {
        textoChico++;
        if (ejemplosTexto.length < 5) ejemplosTexto.push({ elemento: desc(el), px, texto: el.textContent.trim().slice(0, 40) });
      }
    }
    // WCAG 2.5.8 (tamaño mínimo 24x24): no cuentan los links dentro de un texto ni los
    // objetivos chicos con espacio libre alrededor (el cuadrado de 24px no toca a otro objetivo).
    const objetivos = [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [role=button]')]
      .map((el) => ({ el, r: el.getBoundingClientRect() })).filter((o) => visible(o.el, o.r));
    const enTexto = (el) => getComputedStyle(el).display === 'inline' && el.parentElement &&
      [...el.parentElement.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
    const toca = (a, b) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
    for (const o of objetivos) {
      if ((o.r.width >= 24 && o.r.height >= 24) || enTexto(o.el)) continue;
      const cx = o.r.left + o.r.width / 2;
      const cy = o.r.top + o.r.height / 2;
      const zona = { left: cx - 12, right: cx + 12, top: cy - 12, bottom: cy + 12 };
      const vecino = objetivos.some((x) => x !== o && !x.el.contains(o.el) && !o.el.contains(x.el) && toca(zona, x.r));
      if (vecino && tactiles.length < 200) {
        if (tactiles.length < 20) o.el.setAttribute('data-k0-marca', '');
        tactiles.push({ elemento: desc(o.el), ancho: Math.round(o.r.width), alto: Math.round(o.r.height),
          texto: (o.el.innerText || o.el.getAttribute('aria-label') || o.el.value || '').trim().slice(0, 30) });
      }
    }
  }
  return {
    ancho_ventana: vw, ancho_documento: anchoDoc, desborde_horizontal: anchoDoc > vw + 1,
    elementos_desbordados: desbordados, texto_chico: textoChico, ejemplos_texto_chico: ejemplosTexto,
    objetivos_tactiles_chicos: tactiles.length, ejemplos_tactiles: tactiles.slice(0, 5),
  };
}

// Métricas de la navegación (Navigation y Resource Timing). El peso es aproximado: los recursos
// de otros dominios sin Timing-Allow-Origin informan 0 bytes.
function medir() {
  const nav = performance.getEntriesByType('navigation')[0];
  const recursos = performance.getEntriesByType('resource');
  const bytes = recursos.reduce((s, r) => s + (r.transferSize || 0), nav ? nav.transferSize || 0 : 0);
  return {
    ttfb_ms: nav ? Math.round(nav.responseStart) : null,
    dom_ms: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
    load_ms: nav ? Math.round(nav.loadEventEnd) : null,
    requests: recursos.length + 1,
    peso_kb: Math.round(bytes / 1024),
  };
}

// Captura de página completa (JPG, liviano) con los elementos marcados resaltados en rojo.
async function capturar(page, archivo) {
  await page.addStyleTag({ content: '[data-k0-marca]{outline:3px solid #ff2d2d !important;outline-offset:-2px !important;' +
    'box-shadow:0 0 0 6px rgba(255,45,45,.35) !important}' }).catch(() => {});
  const opciones = { path: archivo, type: 'jpeg', quality: 70, timeout: 20000 };
  await page.screenshot({ ...opciones, fullPage: true }).catch(() => page.screenshot(opciones));
}

// Borra SOLO lo que genera este script (y el análisis viejo), para que la corrida nueva reemplace
// a la anterior sin tocar otros archivos que la persona haya dejado en la carpeta.
const GENERADOS = ['exploracion.json', 'analisis.json', 'informe-exploratorio.html', 'capturas', 'videos'];
// La corrida anterior no se borra: pasa a historial/<fecha>/ (se guardan las últimas 5) para compararla.
function limpiarCarpeta(carpeta) {
  archivar(carpeta, GENERADOS, 'exploracion.json');
  for (const nombre of GENERADOS) fs.rmSync(path.join(carpeta, nombre), { recursive: true, force: true });
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(RAIZ, 'scripts', 'generar_informe_exploratorio.py'),
    path.join(carpeta, 'exploracion.json'), path.join(carpeta, 'informe-exploratorio.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). ` +
      'Generalo con: python scripts/generar_informe_exploratorio.py <carpeta>/exploracion.json <carpeta>/informe-exploratorio.html');
    return false;
  }
  return true;
}

// fetch nativo (no el request de Playwright, que con algunos servidores lanza errores de socket
// imposibles de capturar). El cuerpo no se descarga: se cancela apenas llegan los headers.
async function pedir(url, method) {
  const r = await fetch(url, { method, redirect: 'follow', signal: AbortSignal.timeout(15000),
    headers: { 'User-Agent': 'Mozilla/5.0 (k0lmenIA explorador-web)', Accept: '*/*' } });
  if (r.body) await r.body.cancel().catch(() => {});
  return r.status;
}

async function verificarLink(url) {
  try {
    // Muchos servidores no implementan bien HEAD: ante un error o un 4xx/5xx se confirma con GET.
    const head = await pedir(url, 'HEAD').catch(() => 0);
    if (head && head < 400) return { status: head };
    return { status: await pedir(url, 'GET') };
  } catch (e) {
    const causa = e.cause ? ` ${e.cause.code || ''} ${e.cause.message || ''}` : '';
    const msg = `${e.name === 'TimeoutError' ? 'timeout' : e.message}${causa}`.trim();
    // Solo es "roto" si el sitio no existe o rechaza la conexión; lo demás (timeouts, respuestas
    // que el cliente no puede interpretar) no prueba nada.
    const caido = /ENOTFOUND|EAI_AGAIN|ECONNREFUSED|NAME_NOT_RESOLVED|certificate|CERT_|SSL/i.test(msg);
    return { status: 0, error: /timeout/i.test(msg) ? 'Sin respuesta (timeout)' : msg.slice(0, 160), caido };
  }
}

function clasificarLink(l) {
  if (l.status >= 200 && l.status < 400) return 'ok';
  if (NO_VERIFICABLE.has(l.status) || (l.status === 0 && !l.caido)) return 'no_verificable';
  return 'roto';
}

const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };

function armarHallazgos(paginas, links, responsive, { lentaMs = 3000 } = {}) {
  const h = [];
  const capturaDe = new Map(paginas.map((p) => [p.url, p.captura]));
  // Si el hallazgo no trae su propia evidencia, va la captura de la página donde se encontró.
  const agregar = (x) => h.push({ ...x, evidencia: x.evidencia || capturaDe.get(x.pagina) });
  for (const p of paginas) {
    if (!p.error && p.status < 400 && p.tiempo_ms >= lentaMs) {
      agregar({ categoria: 'Rendimiento', severidad: p.tiempo_ms >= lentaMs * 2 ? 'Media' : 'Baja', pagina: p.url,
        titulo: `Carga lenta: ${(p.tiempo_ms / 1000).toFixed(1)} s`,
        detalle: `Tardó más de ${(lentaMs / 1000).toFixed(1)} s en cargar` +
          (p.metricas && p.metricas.ttfb_ms != null ? ` (primer byte ${p.metricas.ttfb_ms} ms, ${p.metricas.requests} requests, ~${p.metricas.peso_kb} KB)` : '') });
    }
    if (p.error || p.status >= 400) {
      agregar({ categoria: 'Página con error', severidad: p.status >= 500 || p.error ? 'Crítica' : 'Alta', pagina: p.url,
        titulo: p.error ? 'La página no se pudo abrir' : `La página responde ${p.status}`, detalle: p.error || `HTTP ${p.status}` });
    }
    for (const err of p.errores_js) {
      agregar({ categoria: 'Error de JavaScript', severidad: 'Alta', pagina: p.url, titulo: 'Error de JavaScript no capturado', detalle: err });
    }
    for (const err of p.errores_consola) {
      agregar({ categoria: 'Error de consola', severidad: 'Media', pagina: p.url, titulo: 'Error en la consola del navegador', detalle: err });
    }
    for (const r of p.recursos_fallidos) {
      if (r.tipo === 'image') continue; // se informa como imagen rota
      const critico = ['script', 'stylesheet', 'document'].includes(r.tipo);
      agregar({ categoria: 'Recurso que falla', severidad: critico ? 'Alta' : 'Media', pagina: p.url,
        titulo: `${r.tipo || 'recurso'} que no carga (${r.status || 'sin respuesta'})`, detalle: r.url + (r.error ? ` · ${r.error}` : '') });
    }
    for (const img of p.imagenes_rotas) {
      agregar({ categoria: 'Imagen rota', severidad: 'Alta', pagina: p.url, titulo: 'Imagen que no carga',
        detalle: img.src + (img.status ? ` (HTTP ${img.status})` : '') + (img.alt ? ` · alt "${img.alt}"` : '') });
    }
    if (p.imagenes_sin_alt > 0) {
      agregar({ categoria: 'Accesibilidad', severidad: 'Baja', pagina: p.url, titulo: `${p.imagenes_sin_alt} imagen(es) sin texto alternativo (alt)`,
        detalle: (p.ejemplos_sin_alt || []).slice(0, 3).join(' · ') });
    }
    if (!p.error && p.status < 400 && !p.meta_viewport) {
      agregar({ categoria: 'Responsive', severidad: 'Media', pagina: p.url, titulo: 'Sin <meta name="viewport">',
        detalle: 'En mobile la página se muestra achicada como si fuera de escritorio.' });
    }
  }
  for (const l of links.filter((x) => x.resultado === 'roto')) {
    agregar({ categoria: 'Link roto', severidad: l.interno ? 'Alta' : 'Media', pagina: l.origenes[0],
      titulo: `${l.interno ? 'Link interno' : 'Link externo'} roto (${l.status || 'sin respuesta'})`,
      detalle: l.url + (l.error ? ` · ${l.error}` : '') + (l.origenes.length > 1 ? ` · aparece en ${l.origenes.length} páginas` : ''),
      texto_link: l.texto });
  }
  // Responsive: un hallazgo por página y tipo de problema, con todas las resoluciones afectadas.
  const grupos = new Map();
  const sumar = (r, tipo) => {
    const k = `${r.url}|${tipo}`;
    if (!grupos.has(k)) grupos.set(k, { tipo, url: r.url, filas: [] });
    grupos.get(k).filas.push(r);
  };
  for (const r of responsive) {
    if (r.error) continue;
    if (r.desborde_horizontal) sumar(r, 'desborde');
    if (r.texto_chico > 0) sumar(r, 'texto');
    if (r.objetivos_tactiles_chicos > 0) sumar(r, 'tactil');
  }
  for (const { tipo, url, filas } of grupos.values()) {
    const res = filas.map((r) => r.resolucion);
    const evidencia = (filas.find((r) => r.captura) || {}).captura;
    const r0 = filas[0];
    if (tipo === 'desborde') {
      const peor = r0.elementos_desbordados[0];
      agregar({ categoria: 'Responsive', severidad: filas.some((r) => r.ancho < 768) ? 'Alta' : 'Media', pagina: url, resoluciones: res,
        titulo: `Scroll horizontal en ${res.join(', ')}`,
        detalle: `En ${r0.resolucion} el contenido mide ${r0.ancho_documento}px en una pantalla de ${r0.ancho_ventana}px` +
          (peor ? `; se sale ${peor.elemento} (${peor.ancho}px)` : ''), evidencia });
    } else if (tipo === 'texto') {
      agregar({ categoria: 'Responsive', severidad: 'Baja', pagina: url, resoluciones: res,
        titulo: `${r0.texto_chico} texto(s) de menos de 12px en ${res.join(', ')}`,
        detalle: r0.ejemplos_texto_chico.map((x) => `${x.elemento} ${x.px}px "${x.texto}"`).join(' · '), evidencia });
    } else {
      agregar({ categoria: 'Responsive', severidad: 'Baja', pagina: url, resoluciones: res,
        titulo: `${r0.objetivos_tactiles_chicos} elemento(s) táctiles de menos de 24px y muy juntos en ${res.join(', ')}`,
        detalle: r0.ejemplos_tactiles.map((x) => `${x.elemento} ${x.ancho}x${x.alto}${x.texto ? ` "${x.texto}"` : ''}`).join(' · '), evidencia });
    }
  }
  // El mismo problema en varias páginas (típico de la plantilla: un CSS que falta, el menú) es un
  // solo hallazgo con la lista de páginas donde aparece.
  const unicos = new Map();
  for (const x of h) {
    const k = [x.categoria, x.titulo, x.detalle, (x.resoluciones || []).join()].join('|');
    if (!unicos.has(k)) unicos.set(k, { ...x, paginas: [x.pagina] });
    else if (!unicos.get(k).paginas.includes(x.pagina)) unicos.get(k).paginas.push(x.pagina);
  }
  const lista = [...unicos.values()];
  lista.sort((a, b) => SEV_ORDEN[a.severidad] - SEV_ORDEN[b.severidad] || b.paginas.length - a.paginas.length);
  return lista.map((x, i) => ({ id: `H-${String(i + 1).padStart(2, '0')}`, ...x }));
}

async function main() {
  const a = argumentos(process.argv.slice(2));
  if (a.ayuda) {
    console.log(fs.readFileSync(__filename, 'utf8').split('\n').filter((l) => l.startsWith('//')).map((l) => l.slice(3)).join('\n'));
    return;
  }
  const url = a.url || process.env.APP_URL || process.env.BASEURL;
  if (!url) throw new Error('No hay URL: pasala con --url o definí APP_URL en el .env de la raíz.');
  if (!/^https?:\/\//i.test(url)) throw new Error(`La URL tiene que empezar con http:// o https:// (recibí "${url}").`);
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  if (!(a.maxPaginas >= 1 && a.maxPaginas <= 500)) throw new Error('--max-paginas tiene que estar entre 1 y 500.');
  const resoluciones = parsearResoluciones(a.resoluciones);
  const inicioUrl = normalizar(url);
  const host = new URL(inicioUrl).hostname;
  const marca = sello();
  // Carpeta fija por historia o sitio: la corrida anterior pasa a historial/.
  const carpeta = a.salida ? path.resolve(a.salida) : path.join(RAIZ, 'output', 'exploratorias', a.historia || host);
  limpiarCarpeta(carpeta);
  const dirCapturas = path.join(carpeta, 'capturas');
  const dirPaginas = path.join(dirCapturas, 'paginas');
  const dirResponsive = path.join(dirCapturas, 'responsive');
  const dirVideos = path.join(carpeta, 'videos');
  for (const d of [dirPaginas, dirResponsive, dirVideos]) fs.mkdirSync(d, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');
  const videos = [];

  console.log(`Exploración de ${inicioUrl} · hasta ${a.maxPaginas} páginas · resoluciones ${resoluciones.map((r) => r.id).join(', ')}`);
  console.log(`Salida: ${path.relative(RAIZ, carpeta).split(path.sep).join('/')} (reemplaza la corrida anterior)`);
  const t0 = Date.now();
  const { chromium } = require('playwright'); // acá y no arriba: los tests usan las funciones sin instalar k0lmena
  const browser = await navegadorComun.lanzar(chromium, { headless: !a.headed });
  // Contexto con video: al cerrarlo, el video se guarda con un nombre legible.
  const nuevoContexto = (opciones) => browser.newContext({ ignoreHTTPSErrors: false, locale: process.env.LOCALE || 'es-AR', ...opciones,
    ...(a.video ? { recordVideo: { dir: path.join(dirVideos, 'tmp'), size: opciones.viewport } } : {}) });
  const cerrarContexto = async (ctx, pagina, nombre, titulo) => {
    const video = a.video ? pagina.video() : null;
    await ctx.close();
    if (!video) return;
    const destino = path.join(dirVideos, `${nombre}.webm`);
    await video.saveAs(destino).catch(() => {});
    await video.delete().catch(() => {});
    if (fs.existsSync(destino)) videos.push({ titulo, archivo: rel(destino) });
  };
  const context = await nuevoContexto({ viewport: { width: 1280, height: 720 } });
  const page = await context.newPage();

  // Eventos de la página actual (se reinician en cada visita).
  let actual = null;
  // "Failed to load resource" es el eco en consola de un recurso que falla: ya se informa como recurso.
  page.on('console', (m) => {
    if (actual && m.type() === 'error' && !/^Failed to load resource/.test(m.text())) actual.errores_consola.add(m.text().slice(0, 300));
  });
  page.on('pageerror', (e) => { if (actual) actual.errores_js.add(String(e.message || e).split('\n')[0].slice(0, 300)); });
  page.on('response', (r) => {
    if (actual && r.status() >= 400) actual.recursos.set(r.url(), { url: r.url(), status: r.status(), tipo: r.request().resourceType() });
  });
  page.on('requestfailed', (rq) => {
    const motivo = rq.failure() ? rq.failure().errorText : 'falló';
    if (actual && !/ERR_ABORTED/.test(motivo)) actual.recursos.set(rq.url(), { url: rq.url(), status: 0, tipo: rq.resourceType(), error: motivo });
  });

  const visitadas = new Set();
  const cola = [{ url: inicioUrl, nivel: 0 }];
  const enCola = new Set([inicioUrl]);
  const paginas = [];
  const linksMap = new Map(); // url → { url, interno, origenes:Set, texto }

  while (cola.length && paginas.length < a.maxPaginas) {
    const { url: u, nivel } = cola.shift();
    if (visitadas.has(u)) continue;
    visitadas.add(u);
    actual = { errores_consola: new Set(), errores_js: new Set(), recursos: new Map() };
    const reg = { url: u, nivel, titulo: '', status: 0, tiempo_ms: 0, links: 0, imagenes: 0 };
    process.stdout.write(`[${paginas.length + 1}/${a.maxPaginas}] ${u} `);
    try {
      const { resp, ms } = await cargar(page, u);
      reg.status = resp ? resp.status() : 0;
      reg.tiempo_ms = ms;
      const final = normalizar(page.url());
      if (final !== u) reg.redirige_a = final;
      if (new URL(final).hostname !== host) {
        reg.fuera_del_sitio = true;
      } else {
        await recorrerScroll(page);
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
        const c = await page.evaluate(revisarContenido);
        reg.titulo = c.titulo;
        reg.links = c.links.length;
        reg.imagenes = c.totalImagenes;
        reg.meta_viewport = c.metaViewport;
        reg.imagenes_sin_alt = c.totalSinAlt;
        reg.ejemplos_sin_alt = c.sinAlt;
        reg._rotas = c.rotas;
        reg.metricas = await page.evaluate(medir).catch(() => null);
        const archivo = path.join(dirPaginas, `${String(paginas.length + 1).padStart(2, '0')}-${slug(u)}.jpg`);
        await capturar(page, archivo);
        if (fs.existsSync(archivo)) reg.captura = rel(archivo);
        for (const l of c.links) {
          let abs;
          try { abs = new URL(l.href); } catch { continue; }
          if (!/^https?:$/.test(abs.protocol)) continue; // mailto:, tel:, javascript:
          const n = normalizar(abs.href);
          const interno = abs.hostname === host;
          if (!linksMap.has(n)) linksMap.set(n, { url: n, interno, origenes: new Set(), texto: l.texto });
          linksMap.get(n).origenes.add(u);
          if (interno && !enCola.has(n) && nivel < a.profundidad && !NO_RECORRER.test(abs.pathname + abs.search) && !ARCHIVO.test(abs.pathname)) {
            enCola.add(n);
            cola.push({ url: n, nivel: nivel + 1 });
          }
        }
      }
      console.log(`→ ${reg.status} (${ms} ms)`);
    } catch (e) {
      reg.error = String(e.message || e).split('\n')[0].slice(0, 200);
      console.log(`→ error: ${reg.error}`);
    }
    reg.errores_consola = [...actual.errores_consola];
    reg.errores_js = [...actual.errores_js];
    const recursos = [...actual.recursos.values()].filter((r) => normalizar(r.url) !== u || r.tipo !== 'document');
    // Imágenes rotas: las que el DOM muestra sin cargar + las que respondieron con error.
    const rotas = new Map((reg._rotas || []).map((i) => [i.src, i]));
    for (const r of recursos.filter((x) => x.tipo === 'image')) rotas.set(r.url, { ...(rotas.get(r.url) || {}), src: r.url, status: r.status });
    reg.imagenes_rotas = [...rotas.values()];
    reg.recursos_fallidos = recursos;
    delete reg._rotas;
    paginas.push(reg);
    actual = null;
    if (a.pausaMs > 0) await esperar(a.pausaMs);
  }
  const sinRecorrer = cola.filter((c) => !visitadas.has(c.url)).length;
  await cerrarContexto(context, page, 'recorrido', 'Recorrido de las páginas (desktop 1280x720)');

  // Links: los internos visitados ya tienen status; el resto se verifica por HTTP.
  const porPagina = new Map(paginas.map((p) => [p.url, p]));
  const links = [...linksMap.values()].filter((l) => l.interno || a.externos);
  console.log(`Verificando ${links.length} links…`);
  await enParalelo(links, 8, async (l) => {
    const p = porPagina.get(l.url);
    if (p && !p.error && p.status) { l.status = p.status; return; }
    // Los links de cierre de sesión o borrado no se piden nunca, ni siquiera para verificarlos.
    const u = new URL(l.url);
    if (l.interno && NO_RECORRER.test(u.pathname + u.search)) { l.status = 0; l.error = 'No se verifica: cierra la sesión o puede tener efecto'; return; }
    Object.assign(l, await verificarLink(l.url));
  });
  const linksSalida = links.map((l) => ({ url: l.url, interno: l.interno, status: l.status, error: l.error, caido: l.caido,
    resultado: clasificarLink(l), texto: l.texto, origenes: [...l.origenes] }));

  // Responsive: las primeras N páginas sanas (orden de recorrido: las más cercanas al inicio primero).
  const paraResponsive = paginas.filter((p) => !p.error && p.status < 400 && !p.fuera_del_sitio).slice(0, a.responsive);
  const responsive = [];
  console.log(`Revisando responsive de ${paraResponsive.length} página(s) en ${resoluciones.length} resoluciones…`);
  // Un contexto (y un video) por resolución; mobile y tablet emulan pantalla táctil.
  for (const r of resoluciones) {
    const ctx = await nuevoContexto({ viewport: { width: r.ancho, height: r.alto }, isMobile: r.ancho < 768, hasTouch: r.ancho < 1024 });
    const pag = await ctx.newPage();
    for (const [i, p] of paraResponsive.entries()) {
      const fila = { url: p.url, resolucion: r.id, nombre: r.nombre, ancho: r.ancho, alto: r.alto };
      try {
        await cargar(pag, p.url);
        await recorrerScroll(pag);
        Object.assign(fila, await pag.evaluate(revisarResponsive, r.ancho < 768));
        const archivo = path.join(dirResponsive, `${String(i + 1).padStart(2, '0')}-${slug(p.url)}-${r.id}.jpg`);
        await capturar(pag, archivo);
        if (fs.existsSync(archivo)) fila.captura = rel(archivo);
      } catch (e) {
        fila.error = String(e.message || e).split('\n')[0].slice(0, 200);
      }
      responsive.push(fila);
    }
    await cerrarContexto(ctx, pag, `responsive-${r.id}`, `${r.nombre} ${r.id}`);
  }
  await browser.close();
  fs.rmSync(path.join(dirVideos, 'tmp'), { recursive: true, force: true });

  const hallazgos = armarHallazgos(paginas, linksSalida, responsive, { lentaMs: a.lentaMs });
  const contar = (cat) => hallazgos.filter((x) => x.categoria === cat).length;
  const resultado = {
    url: inicioUrl, host, historia: a.historia || null, fecha: new Date().toISOString(), marca,
    duracion_s: Math.round((Date.now() - t0) / 1000),
    config: { max_paginas: a.maxPaginas, profundidad: a.profundidad, responsive: Number.isFinite(a.responsive) ? a.responsive : 'todas',
      externos: a.externos, resoluciones: resoluciones.map((r) => r.id), video: a.video, lenta_ms: a.lentaMs },
    resumen: {
      paginas: paginas.length, paginas_sin_recorrer: sinRecorrer, links: linksSalida.length,
      links_rotos: linksSalida.filter((l) => l.resultado === 'roto').length,
      links_no_verificables: linksSalida.filter((l) => l.resultado === 'no_verificable').length,
      imagenes: paginas.reduce((s, p) => s + (p.imagenes || 0), 0),
      imagenes_rotas: contar('Imagen rota'), errores_js: contar('Error de JavaScript'), errores_consola: contar('Error de consola'),
      recursos_fallidos: contar('Recurso que falla'), responsive: contar('Responsive'), lentas: contar('Rendimiento'),
      hallazgos: hallazgos.length, ...tiempos(paginas),
    },
    hallazgos, paginas, links: linksSalida, responsive, videos,
  };
  const salida = path.join(carpeta, 'exploracion.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  const r = resultado.resumen;
  console.log(`\nPáginas: ${r.paginas}${sinRecorrer ? ` (quedaron ${sinRecorrer} sin recorrer: subí --max-paginas o --profundidad)` : ''}`);
  console.log(`Links: ${r.links} · rotos ${r.links_rotos} · no verificables ${r.links_no_verificables}`);
  console.log(`Imágenes rotas: ${r.imagenes_rotas} · errores JS: ${r.errores_js} · errores de consola: ${r.errores_consola} · recursos que fallan: ${r.recursos_fallidos}`);
  console.log(`Responsive: ${r.responsive} hallazgo(s) · total de hallazgos: ${r.hallazgos}`);
  console.log(`Datos: ${path.relative(RAIZ, salida).split(path.sep).join('/')}`);
  if (generarInforme(carpeta)) {
    console.log(`Informe: ${path.relative(RAIZ, path.join(carpeta, 'informe-exploratorio.html')).split(path.sep).join('/')}`);
  }
}

// Promedio, máximo y percentil 90 de los tiempos de carga de las páginas que abrieron.
function tiempos(paginas) {
  const ms = paginas.filter((p) => !p.error && p.tiempo_ms).map((p) => p.tiempo_ms).sort((x, y) => x - y);
  if (!ms.length) return { carga_promedio_ms: 0, carga_max_ms: 0, carga_p90_ms: 0 };
  return { carga_promedio_ms: Math.round(ms.reduce((s, x) => s + x, 0) / ms.length), carga_max_ms: ms[ms.length - 1],
    carga_p90_ms: ms[Math.min(ms.length - 1, Math.ceil(ms.length * 0.9) - 1)] };
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { normalizar, slug, parsearResoluciones, clasificarLink, armarHallazgos, argumentos, tiempos, limpiarCarpeta, GENERADOS,
  // Los reutiliza el auditor de accesibilidad (tools/accesibilidad).
  NO_RECORRER, ARCHIVO, sello, recorrerScroll, cargar, capturar };

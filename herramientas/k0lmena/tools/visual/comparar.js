// Comparación visual compartida (la usan pixel-perfect y cross-browser).
//
//   estabilizar(page, { ocultar })  → apaga animaciones, transiciones y el cursor de texto, oculta
//                                     las zonas dinámicas y espera fuentes e imágenes: dos capturas
//                                     de la misma página tienen que salir iguales.
//   medirElementos(page)            → caja (posición y tamaño en la página) de cada elemento visible
//                                     que importa: títulos, links, botones, campos, imágenes, etc.
//   compararElementos(ref, act)     → qué elementos se corrieron, cambiaron de tamaño, faltan o son
//                                     nuevos (agrupa los que se desplazaron juntos en un "bloque").
//   compararPng(a, b)               → píxeles distintos, porcentaje, regiones con cambios y la
//                                     imagen de diferencias (los cambios en rojo sobre la actual).
//   recortar(png, caja)             → un pedazo de la imagen (para mostrar cada región de cerca).
//
// Solo usa pngjs (sin dependencias nativas).
// pngjs se carga recién al comparar imágenes (la comparación de elementos no lo necesita).
const png = () => require('pngjs').PNG;

// ------------------------------------------------------------------ estabilizar la página
const CSS_ESTABLE = `*,*::before,*::after{animation-duration:0s!important;animation-delay:0s!important;
  animation-iteration-count:1!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}
  [data-k0-oculto]{visibility:hidden!important}`;

// Sin barras de scroll: Firefox (y WebKit en algunos sistemas) las dibuja ocupando ancho y Chromium
// headless no; con barra la página queda más angosta, el texto corta distinto y todo parece corrido.
// Lo usa el cross-browser al comparar motores (el pixel-perfect compara el mismo navegador).
const CSS_SIN_SCROLLBAR = `html{scrollbar-width:none!important}html::-webkit-scrollbar,body::-webkit-scrollbar{display:none!important}`;

async function estabilizar(page, { ocultar = [], esperaMs = 400 } = {}) {
  await page.addStyleTag({ content: CSS_ESTABLE }).catch(() => {});
  await page.evaluate(async (sels) => {
    for (const s of sels) {
      try { document.querySelectorAll(s).forEach((el) => el.setAttribute('data-k0-oculto', '')); } catch { /* selector inválido */ }
    }
    // Videos y GIF animados: primer cuadro.
    document.querySelectorAll('video').forEach((v) => { try { v.pause(); v.currentTime = 0; } catch { /* sin video */ } });
    const limite = (p, ms) => Promise.race([p, new Promise((r) => setTimeout(r, ms))]);
    if (document.fonts && document.fonts.ready) await limite(document.fonts.ready, 5000);
    const pendientes = [...document.images].filter((i) => !i.complete)
      .map((i) => new Promise((r) => { i.addEventListener('load', r, { once: true }); i.addEventListener('error', r, { once: true }); }));
    await limite(Promise.all(pendientes), 5000);
  }, ocultar).catch(() => {});
  await page.waitForTimeout(esperaMs);
}

// ------------------------------------------------------------------ cajas de los elementos
// Cada elemento lleva una clave estable entre corridas (y entre navegadores): id o data-testid si
// tiene; si no, etiqueta + texto + número de aparición de esa combinación.
function _medirEnPagina() {
  const SEL = 'h1,h2,h3,h4,h5,h6,a[href],button,input:not([type=hidden]),select,textarea,label,img,svg,video,iframe,' +
    'nav,header,footer,main,aside,form,table,li,p,[role=button],[role=link],[role=tab],[role=dialog],[role=alert],[data-testid]';
  const CONTENEDORES = new Set(['nav', 'header', 'footer', 'main', 'aside', 'form', 'table', 'svg', 'video', 'iframe']);
  const sx = window.scrollX;
  const sy = window.scrollY;
  const vistos = new Map();
  const salida = [];
  const textoDe = (el) => (el.getAttribute('aria-label') || el.getAttribute('alt') || el.getAttribute('placeholder') ||
    (el.tagName === 'INPUT' ? el.value : '') || el.innerText || el.getAttribute('title') || '').replace(/\s+/g, ' ').trim();
  // Además de SEL: div, span y section con texto propio (un banner o un aviso sin etiqueta semántica).
  const conTexto = [...document.querySelectorAll('div,span,section,strong,em,small')].filter((el) =>
    [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 2));
  const lista = [...new Set([...document.querySelectorAll(SEL), ...conTexto])];
  // El color calculado llega en el formato de cada motor (rgb(), oklch(), color(srgb …)): se pinta
  // en un canvas y se lee el píxel, así queda en sRGB igual en todos los navegadores.
  const lienzo = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
  const colores = new Map();
  const hex = (c) => {
    if (colores.has(c)) return colores.get(c);
    let salida = 'transparente';
    if (lienzo) {
      lienzo.clearRect(0, 0, 1, 1);
      lienzo.fillStyle = '#000';
      lienzo.fillStyle = c;
      lienzo.fillRect(0, 0, 1, 1);
      const [r, g, b, a] = lienzo.getImageData(0, 0, 1, 1).data;
      if (a > 0) salida = '#' + [r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('');
    } else {
      const m = c.match(/\d+(\.\d+)?/g);
      if (m && !(m.length === 4 && Number(m[3]) === 0)) salida = '#' + m.slice(0, 3).map((x) => Math.round(Number(x)).toString(16).padStart(2, '0')).join('');
    }
    colores.set(c, salida);
    return salida;
  };
  for (const el of lista) {
    if (salida.length >= 800) break;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) === 0) continue;
    if (el.closest('[data-k0-oculto]')) continue;
    const tag = el.tagName.toLowerCase();
    const texto = textoDe(el).slice(0, 60);
    // Un párrafo o un li sin texto propio no aporta (y los contenedores grandes se miden igual).
    if ((tag === 'p' || tag === 'li') && !texto) continue;
    const testid = el.getAttribute('data-testid');
    let clave;
    if (el.id && !/^\d|[:\s]/.test(el.id)) clave = `#${el.id}`;
    else if (testid) clave = `[data-testid=${testid}]`;
    else {
      // Los contenedores se identifican por su orden (su texto es el de todo lo de adentro y cambia
      // con cualquier cosa); el resto, por su texto.
      const base = CONTENEDORES.has(tag) ? `${tag}|` : `${tag}|${texto.slice(0, 40)}`;
      const n = (vistos.get(base) || 0) + 1;
      vistos.set(base, n);
      clave = `${base}|${n}`;
    }
    let desc = tag;
    if (el.id) desc += `#${el.id}`;
    const clases = (typeof el.className === 'string' ? el.className : '').trim().split(/\s+/).filter(Boolean).slice(0, 2);
    if (clases.length) desc += `.${clases.join('.')}`;
    salida.push({ clave, tag, texto, desc, x: Math.round(r.left + sx), y: Math.round(r.top + sy),
      w: Math.round(r.width), h: Math.round(r.height),
      estilo: { fondo: hex(cs.backgroundColor), color: hex(cs.color), letra: cs.fontSize, peso: cs.fontWeight } });
  }
  return { elementos: salida, ancho: document.documentElement.scrollWidth, alto: document.documentElement.scrollHeight };
}

async function medirElementos(page) {
  return page.evaluate(_medirEnPagina);
}

// Elementos que si faltan o se mueven importan más (se usan).
const INTERACTIVOS = new Set(['a', 'button', 'input', 'select', 'textarea', 'label']);

function severidadMovimiento(dist, tag) {
  const inter = INTERACTIVOS.has(tag);
  if (dist >= 40) return inter ? 'Alta' : 'Media';
  if (dist >= 12) return inter ? 'Media' : 'Baja';
  return 'Baja';
}

// ref y act: listas de medirElementos().elementos. tolerancia en px.
function compararElementos(ref, act, { tolerancia = 3, minBloque = 4 } = {}) {
  const mapaAct = new Map(act.map((e) => [e.clave, e]));
  const mapaRef = new Map(ref.map((e) => [e.clave, e]));
  const movidos = [];
  const redimensionados = [];
  const faltantes = [];
  for (const r of ref) {
    const a = mapaAct.get(r.clave);
    if (!a) { faltantes.push(r); continue; }
    const dx = a.x - r.x;
    const dy = a.y - r.y;
    const dw = a.w - r.w;
    const dh = a.h - r.h;
    if (Math.abs(dx) > tolerancia || Math.abs(dy) > tolerancia) movidos.push({ ...r, dx, dy, dw, dh, actual: a });
    else if (Math.abs(dw) > tolerancia || Math.abs(dh) > tolerancia) redimensionados.push({ ...r, dx, dy, dw, dh, actual: a });
  }
  // Estilos: el mismo cambio (de → a) en varios elementos es uno solo (todos los botones cambiaron de color).
  const NOMBRE_PROP = { fondo: 'color de fondo', color: 'color del texto', letra: 'tamaño de letra', peso: 'grosor de letra' };
  const estilos = new Map();
  for (const r of ref) {
    const a = mapaAct.get(r.clave);
    if (!a || !r.estilo || !a.estilo) continue;
    for (const prop of Object.keys(NOMBRE_PROP)) {
      if (r.estilo[prop] === a.estilo[prop]) continue;
      const k = `${prop}|${r.estilo[prop]}|${a.estilo[prop]}`;
      if (!estilos.has(k)) estilos.set(k, { prop, nombre: NOMBRE_PROP[prop], de: r.estilo[prop], a: a.estilo[prop], elementos: [] });
      estilos.get(k).elementos.push({ ...r, actual: a });
    }
  }
  let nuevos = act.filter((a) => !mapaRef.has(a.clave));
  // Un faltante y un nuevo de la misma etiqueta en el mismo lugar: es el mismo elemento con otro
  // texto (un botón que cambió de nombre), no uno que desapareció.
  // Desplazamientos posibles: ninguno o el más común entre los que se movieron (si todo bajó 40 px,
  // el elemento con otro texto también bajó 40 px).
  const frec = new Map();
  for (const m of movidos) { const k = `${m.dx}|${m.dy}`; frec.set(k, (frec.get(k) || 0) + 1); }
  const offs = [[0, 0], ...[...frec.entries()].sort((p, q) => q[1] - p[1]).slice(0, 3).map(([k]) => k.split('|').map(Number))];
  const cerca = (n, f) => offs.some(([ox, oy]) => Math.abs(n.x - f.x - ox) <= 30 && Math.abs(n.y - f.y - oy) <= 30);
  const cambiados = [];
  for (const f of [...faltantes]) {
    const par = nuevos.find((n) => n.tag === f.tag && cerca(n, f)
      && Math.abs(n.w - f.w) <= Math.max(40, f.w * 0.5) && Math.abs(n.h - f.h) <= Math.max(12, f.h * 0.5));
    if (!par) continue;
    cambiados.push({ ...f, actual: par });
    faltantes.splice(faltantes.indexOf(f), 1);
    nuevos = nuevos.filter((n) => n !== par);
  }

  // Bloques: muchos elementos con el mismo desplazamiento son una sola causa (algo de arriba creció
  // o se corrió y empujó todo lo de abajo). Se informa el bloque y no cada elemento.
  const grupos = new Map();
  for (const m of movidos) {
    const k = `${Math.round(m.dx / 2) * 2}|${Math.round(m.dy / 2) * 2}`;
    if (!grupos.has(k)) grupos.set(k, []);
    grupos.get(k).push(m);
  }
  const bloques = [];
  const sueltos = [];
  for (const lista of grupos.values()) {
    if (lista.length >= minBloque) {
      lista.sort((a, b) => a.y - b.y || a.x - b.x);
      const x = Math.min(...lista.map((e) => e.x));
      const y = Math.min(...lista.map((e) => e.y));
      bloques.push({ dx: lista[0].dx, dy: lista[0].dy, elementos: lista.length,
        desde: lista.find((e) => !['main', 'nav', 'header', 'footer', 'aside', 'form', 'table', 'section', 'div'].includes(e.tag)) || lista[0],
        caja: { x, y, w: Math.max(...lista.map((e) => e.x + e.w)) - x, h: Math.max(...lista.map((e) => e.y + e.h)) - y },
        ejemplos: lista.slice(0, 6).map((e) => ({ desc: e.desc, texto: e.texto })) });
    } else sueltos.push(...lista);
  }
  bloques.sort((a, b) => b.elementos - a.elementos);
  sueltos.sort((a, b) => Math.hypot(b.dx, b.dy) - Math.hypot(a.dx, a.dy));
  for (const m of sueltos) m.severidad = severidadMovimiento(Math.hypot(m.dx, m.dy), m.tag);
  return { movidos: sueltos, bloques, redimensionados, faltantes, nuevos, cambiados,
    estilos: [...estilos.values()].sort((p, q) => q.elementos.length - p.elementos.length), total_ref: ref.length, total_act: act.length };
}

// ------------------------------------------------------------------ diferencias de píxeles
// Distancia de color en YIQ (la misma idea que pixelmatch): pondera como lo percibe el ojo.
const MAX_DELTA = 35215;
function _delta(a, i, b, j) {
  const ra = a[i]; const ga = a[i + 1]; const ba = a[i + 2];
  const rb = b[j]; const gb = b[j + 1]; const bb = b[j + 2];
  const y = (ra - rb) * 0.29889531 + (ga - gb) * 0.58662247 + (ba - bb) * 0.11448223;
  const iq = (ra - rb) * 0.59597799 - (ga - gb) * 0.2741761 - (ba - bb) * 0.32180189;
  const q = (ra - rb) * 0.21147017 - (ga - gb) * 0.52261711 + (ba - bb) * 0.31114694;
  return 0.5053 * y * y + 0.299 * iq * iq + 0.1957 * q * q;
}

function leerPng(buf) {
  return png().sync.read(Buffer.isBuffer(buf) ? buf : require('fs').readFileSync(buf));
}

// Compara dos PNG (Buffer o ruta). umbral: 0..1, sensibilidad por píxel (0.1 = cambios notorios).
// Si las imágenes tienen distinto tamaño, compara la parte común y cuenta el resto como cambio.
function compararPng(bufA, bufB, { umbral = 0.1, celda = 16, minPixelesCelda = 6 } = {}) {
  const a = leerPng(bufA);
  const b = leerPng(bufB);
  const W = Math.max(a.width, b.width);
  const H = Math.max(a.height, b.height);
  const w = Math.min(a.width, b.width);
  const h = Math.min(a.height, b.height);
  const limite = MAX_DELTA * umbral * umbral;
  const salida = new (png())({ width: W, height: H });
  const cols = Math.ceil(W / celda);
  const filas = Math.ceil(H / celda);
  const celdas = new Uint32Array(cols * filas);
  let distintos = 0;
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const o = (y * W + x) * 4;
      const dentro = x < w && y < h;
      let cambio;
      let gris = 255;
      if (dentro) {
        const ia = (y * a.width + x) * 4;
        const ib = (y * b.width + x) * 4;
        cambio = _delta(a.data, ia, b.data, ib) > limite;
        gris = 0.299 * b.data[ib] + 0.587 * b.data[ib + 1] + 0.114 * b.data[ib + 2];
      } else cambio = true;
      if (cambio) {
        distintos++;
        celdas[Math.floor(y / celda) * cols + Math.floor(x / celda)]++;
        salida.data[o] = 255; salida.data[o + 1] = 32; salida.data[o + 2] = 48; salida.data[o + 3] = 255;
      } else {
        // La actual, apagada, de fondo: los cambios en rojo se ven en su contexto.
        const v = Math.round(255 - (255 - gris) * 0.22);
        salida.data[o] = v; salida.data[o + 1] = v; salida.data[o + 2] = v; salida.data[o + 3] = 255;
      }
    }
  }
  const regiones = _regiones(celdas, cols, filas, celda, minPixelesCelda, W, H);
  return { ancho_a: a.width, alto_a: a.height, ancho_b: b.width, alto_b: b.height, distintos,
    pct: Math.round((distintos / (W * H)) * 10000) / 100, regiones, diff: png().sync.write(salida) };
}

// Celdas con cambios → regiones (componentes conexos, unidas si quedan pegadas o superpuestas).
function _regiones(celdas, cols, filas, celda, minPix, W, H) {
  const marca = new Uint8Array(cols * filas);
  const cajas = [];
  for (let i = 0; i < celdas.length; i++) {
    if (marca[i] || celdas[i] < minPix) continue;
    const pila = [i];
    marca[i] = 1;
    let x0 = cols; let y0 = filas; let x1 = 0; let y1 = 0; let pix = 0;
    while (pila.length) {
      const k = pila.pop();
      const cx = k % cols;
      const cy = Math.floor(k / cols);
      pix += celdas[k];
      x0 = Math.min(x0, cx); y0 = Math.min(y0, cy); x1 = Math.max(x1, cx); y1 = Math.max(y1, cy);
      // Vecinos a 2 celdas: une cambios cercanos (un texto que se corrió es una región, no diez).
      for (let dy = -2; dy <= 2; dy++) {
        for (let dx = -2; dx <= 2; dx++) {
          const nx = cx + dx;
          const ny = cy + dy;
          if (nx < 0 || ny < 0 || nx >= cols || ny >= filas) continue;
          const n = ny * cols + nx;
          if (!marca[n] && celdas[n] >= minPix) { marca[n] = 1; pila.push(n); }
        }
      }
    }
    cajas.push({ x: x0 * celda, y: y0 * celda, w: Math.min(W, (x1 + 1) * celda) - x0 * celda, h: Math.min(H, (y1 + 1) * celda) - y0 * celda, pixeles: pix });
  }
  cajas.sort((p, q) => q.pixeles - p.pixeles);
  return cajas;
}

// Recorte (con margen) de un PNG; si la caja se sale de la imagen, rellena con gris.
function recortar(buf, { x, y, w, h }, margen = 24) {
  const img = leerPng(buf);
  const X = Math.max(0, x - margen);
  const Y = Math.max(0, y - margen);
  const ancho = Math.max(1, Math.min(w + margen * 2, 1600));
  const alto = Math.max(1, Math.min(h + margen * 2, 1200));
  const out = new (png())({ width: ancho, height: alto });
  for (let j = 0; j < alto; j++) {
    for (let i = 0; i < ancho; i++) {
      const o = (j * ancho + i) * 4;
      const sx = X + i;
      const sy = Y + j;
      if (sx < img.width && sy < img.height) {
        const s = (sy * img.width + sx) * 4;
        out.data[o] = img.data[s]; out.data[o + 1] = img.data[s + 1]; out.data[o + 2] = img.data[s + 2]; out.data[o + 3] = 255;
      } else {
        out.data[o] = 40; out.data[o + 1] = 42; out.data[o + 2] = 48; out.data[o + 3] = 255;
      }
    }
  }
  return png().sync.write(out);
}

// Recorte de la ventana `ventana` con el rectángulo `caja` (coordenadas de la imagen) marcado.
function recorteMarcado(buf, ventana, caja, color = [255, 45, 45]) {
  const img = leerPng(buf);
  const X = Math.max(0, Math.round(ventana.x));
  const Y = Math.max(0, Math.round(ventana.y));
  const ancho = Math.max(1, Math.min(Math.round(ventana.w), 1600));
  const alto = Math.max(1, Math.min(Math.round(ventana.h), 1200));
  const out = new (png())({ width: ancho, height: alto });
  const borde = 3;
  for (let j = 0; j < alto; j++) {
    for (let i = 0; i < ancho; i++) {
      const o = (j * ancho + i) * 4;
      const sx = X + i;
      const sy = Y + j;
      let r = 40; let g = 42; let b = 48;
      if (sx < img.width && sy < img.height) {
        const s = (sy * img.width + sx) * 4;
        r = img.data[s]; g = img.data[s + 1]; b = img.data[s + 2];
      }
      if (caja) {
        const enX = sx >= caja.x - borde && sx < caja.x + caja.w + borde;
        const enY = sy >= caja.y - borde && sy < caja.y + caja.h + borde;
        const dentro = sx >= caja.x && sx < caja.x + caja.w && sy >= caja.y && sy < caja.y + caja.h;
        if (enX && enY && !dentro) { [r, g, b] = color; }
      }
      out.data[o] = r; out.data[o + 1] = g; out.data[o + 2] = b; out.data[o + 3] = 255;
    }
  }
  return png().sync.write(out);
}

// Ventana que contiene las cajas dadas, con margen, del tamaño mínimo pedido.
function ventanaDe(cajas, margen = 60, minAncho = 320, minAlto = 160) {
  const x0 = Math.min(...cajas.map((c) => c.x)) - margen;
  const y0 = Math.min(...cajas.map((c) => c.y)) - margen;
  const x1 = Math.max(...cajas.map((c) => c.x + c.w)) + margen;
  const y1 = Math.max(...cajas.map((c) => c.y + c.h)) + margen;
  const w = Math.max(minAncho, x1 - x0);
  const h = Math.max(minAlto, y1 - y0);
  return { x: Math.max(0, Math.round((x0 + x1) / 2 - w / 2)), y: Math.max(0, Math.round((y0 + y1) / 2 - h / 2)), w, h };
}

// Tamaño de un PNG sin decodificarlo entero.
function tamanoPng(buf) {
  const b = Buffer.isBuffer(buf) ? buf : require('fs').readFileSync(buf);
  return { ancho: b.readUInt32BE(16), alto: b.readUInt32BE(20) };
}

module.exports = { estabilizar, medirElementos, compararElementos, compararPng, recortar, recorteMarcado, ventanaDe, tamanoPng, severidadMovimiento,
  CSS_ESTABLE, CSS_SIN_SCROLLBAR, _regiones };

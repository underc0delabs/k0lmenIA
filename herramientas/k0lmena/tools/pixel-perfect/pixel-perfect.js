// Regresión visual "pixel perfect" (agente pixel-perfect).
//
// Uso (desde la raíz del repo):
//   npm run pixel-perfect -- [--url https://mi-app.com] [--historia HU-001] [--paginas url1,url2]
//                            [--max-paginas 8] [--profundidad 1] [--resoluciones 390x844,1366x768]
//                            [--ocultar ".banner,.fecha"] [--umbral 0.1] [--tolerancia-px 3]
//                            [--pct-max 0.2] [--navegador chromium|firefox|webkit] [--headed]
//                            [--referencia] [--aceptar todas|id1,id2]
//
// Toma una captura de cada página en cada resolución y la compara con su REFERENCIA (la versión
// aceptada como correcta):
//   - píxel a píxel: porcentaje de la pantalla que cambió y las regiones con cambios,
//   - elemento por elemento: qué se corrió (y cuántos px), qué cambió de tamaño o de texto, qué
//     ya no aparece y qué es nuevo. Los elementos que se desplazaron juntos se informan como un
//     bloque (algo de arriba creció y empujó el resto), no uno por uno.
// Antes de cada captura apaga animaciones y transiciones, oculta las zonas de --ocultar (fechas,
// banners rotativos, publicidad) y espera fuentes e imágenes: dos capturas iguales dan 0 %.
//
// La primera corrida (o con --referencia) CREA la referencia; las siguientes comparan contra ella.
// Con --aceptar, las capturas actuales pasan a ser la referencia (todas o las pantallas indicadas):
// es aceptar los cambios como correctos, así que se hace solo cuando la persona lo confirma.
// La referencia también puede venir de un diseño (Figma): poné en referencia/ un PNG con el mismo
// nombre de la pantalla (01-inicio-1366x768.png) y se compara solo píxel a píxel.
//
// Deja todo en output/pixel-perfect/<HU o host>/: referencia/ (se conserva entre corridas),
// actual/, diferencias/, recortes/, pixel-perfect.json e informe-pixel-perfect.html. La comparación
// anterior pasa a historial/ (últimas 5; la referencia se conserva). Sin --ocultar, se reutilizan las
// zonas ocultas con las que se creó la referencia. Solo navega con GET.
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { archivar } = require('../historial/historial.js');
const { normalizar, slug, sello, NO_RECORRER, ARCHIVO, recorrerScroll, cargar } = require('../explorador/explorar.js');
const visual = require('../visual/comparar.js');

const RAIZ = path.resolve(__dirname, '..', '..', '..', '..');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p); // npm run cambia el cwd a herramientas/k0lmena
const GENERADOS = ['actual', 'diferencias', 'recortes', 'pixel-perfect.json', 'analisis.json', 'informe-pixel-perfect.html'];
const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };

function argumentos(argv) {
  const a = { maxPaginas: 8, profundidad: 1, ocultar: [], umbral: 0.1, tolerancia: 3, pctMax: 0.2, navegador: 'chromium',
    headed: false, referencia: false, altoMax: 12000 };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--historia') a.historia = v();
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--resoluciones') a.resoluciones = v();
    else if (k === '--ocultar') a.ocultar = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--umbral') a.umbral = parseFloat(v());
    else if (k === '--tolerancia-px') a.tolerancia = parseInt(v(), 10);
    else if (k === '--pct-max') a.pctMax = parseFloat(v());
    else if (k === '--navegador') a.navegador = v().toLowerCase();
    else if (k === '--alto-max') a.altoMax = parseInt(v(), 10);
    else if (k === '--referencia') a.referencia = true;
    else if (k === '--aceptar') a.aceptar = v();
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (!['chromium', 'firefox', 'webkit'].includes(a.navegador)) throw new Error('--navegador: chromium, firefox o webkit.');
  return a;
}

function parsearResoluciones(txt) {
  return txt.split(',').map((r) => r.trim()).filter(Boolean).map((r) => {
    const m = r.match(/^(\d{3,4})x(\d{3,4})$/);
    if (!m) throw new Error(`Resolución inválida: ${r} (usá ANCHOxALTO, por ejemplo 1366x768)`);
    const ancho = +m[1];
    return { id: r, ancho, alto: +m[2], nombre: ancho < 600 ? 'Mobile' : ancho < 1024 ? 'Tablet' : 'Desktop' };
  });
}

// Zonas ocultas: si no se pasa --ocultar, se usan las de la referencia (si no, cambian solas y dan diferencias falsas).
const ocultarEfectivo = (a, ref) => (a.ocultar.length ? a.ocultar : (ref && ref.config && ref.config.ocultar) || []);
const idPantalla = (n, url, res) => `${String(n).padStart(2, '0')}-${slug(url)}-${res}`;

async function descubrir(page, inicio, a) {
  if (a.paginas) return a.paginas.map(normalizar);
  const host = new URL(inicio).hostname;
  const lista = [inicio];
  const cola = [{ url: inicio, nivel: 0 }];
  const vistos = new Set([inicio]);
  while (cola.length && lista.length < a.maxPaginas) {
    const { url, nivel } = cola.shift();
    if (nivel >= a.profundidad) continue;
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      const hrefs = await page.evaluate(() => [...document.querySelectorAll('a[href]')].map((x) => x.href));
      for (const h of hrefs) {
        let u;
        try { u = new URL(h); } catch { continue; }
        if (!/^https?:$/.test(u.protocol) || u.hostname !== host || NO_RECORRER.test(u.pathname + u.search) || ARCHIVO.test(u.pathname)) continue;
        const n = normalizar(u.href);
        if (vistos.has(n)) continue;
        vistos.add(n);
        cola.push({ url: n, nivel: nivel + 1 });
        if (lista.length < a.maxPaginas) lista.push(n);
      }
    } catch { /* la página que no abre se informa al capturarla */ }
  }
  return lista;
}

// Captura estable de una pantalla: PNG de página completa + cajas de los elementos.
async function capturarPantalla(browser, url, res, a, archivo) {
  const ctx = await browser.newContext({ viewport: { width: res.ancho, height: res.alto }, deviceScaleFactor: 1,
    locale: process.env.LOCALE || 'es-AR', ...(a.navegador === 'chromium' && res.ancho < 768 ? { isMobile: true, hasTouch: true } : {}) });
  const page = await ctx.newPage();
  const errores = [];
  page.on('pageerror', (e) => errores.push(String(e.message || e).split('\n')[0]));
  try {
    const { resp } = await cargar(page, url);
    await recorrerScroll(page);
    await page.evaluate(() => window.scrollTo(0, 0));
    await visual.estabilizar(page, { ocultar: a.ocultar });
    const medidas = await visual.medirElementos(page);
    const alto = Math.min(medidas.alto, a.altoMax);
    await page.screenshot({ path: archivo, fullPage: alto === medidas.alto, timeout: 30000,
      ...(alto < medidas.alto ? { clip: { x: 0, y: 0, width: res.ancho, height: alto } } : {}) });
    return { status: resp ? resp.status() : 0, titulo: await page.title(), elementos: medidas.elementos,
      ancho: medidas.ancho, alto: medidas.alto, recortada: alto < medidas.alto, errores_js: errores };
  } finally {
    await ctx.close();
  }
}

const caja = (e) => ({ x: e.x, y: e.y, w: e.w, h: e.h });
const textoEl = (e) => (e.texto ? `“${e.texto.slice(0, 50)}”` : e.desc);

// Lo que está arriba de un bloque desplazado y explica el desplazamiento: un elemento nuevo, uno
// que creció o uno que desapareció, de alto parecido al desplazamiento.
function causaDe(b, c) {
  const arriba = (e) => e.y < b.desde.y + 4;
  const nuevo = c.nuevos.filter(arriba).find((e) => Math.abs(e.h - b.dy) <= Math.max(6, Math.abs(b.dy) * 0.4));
  if (nuevo && b.dy > 0) return `apareció ${textoEl(nuevo)} (${nuevo.h} px de alto)`;
  const creció = c.redimensionados.filter(arriba).find((e) => Math.abs(e.dh - b.dy) <= 6);
  if (creció) return `${textoEl(creció)} cambió de alto (${creció.dh > 0 ? '+' : ''}${creció.dh} px)`;
  const falta = c.faltantes.filter(arriba).find((e) => Math.abs(e.h + b.dy) <= Math.max(6, Math.abs(b.dy) * 0.4));
  if (falta && b.dy < 0) return `ya no está ${textoEl(falta)} (${falta.h} px de alto)`;
  return '';
}

// Hallazgos de una pantalla a partir de la comparación de elementos y de píxeles.
function hallazgosDe(p, a) {
  const h = [];
  const c = p.elementos_cmp;
  if (c) {
    for (const b of c.bloques) {
      const dist = Math.hypot(b.dx, b.dy);
      const dir = Math.abs(b.dy) >= Math.abs(b.dx) ? (b.dy > 0 ? `bajaron ${b.dy}` : `subieron ${-b.dy}`) : (b.dx > 0 ? `se corrieron ${b.dx} a la derecha` : `se corrieron ${-b.dx} a la izquierda`);
      h.push({ tipo: 'Bloque desplazado', severidad: dist >= 40 ? 'Alta' : dist >= 12 ? 'Media' : 'Baja',
        titulo: `${b.elementos} elementos ${dir} px`,
        detalle: `Desde ${textoEl(b.desde)} hacia abajo todo se movió igual: algo de arriba cambió de tamaño o de lugar y empujó el resto.` +
          (causaDe(b, c) ? ` Causa probable: ${causaDe(b, c)}.` : ''),
        elementos: b.ejemplos, _ref: caja(b.desde), _act: { ...caja(b.desde), x: b.desde.x + b.dx, y: b.desde.y + b.dy } });
    }
    for (const m of c.movidos) {
      h.push({ tipo: 'Elemento corrido', severidad: m.severidad, titulo: `${textoEl(m)} se corrió ${m.dx >= 0 ? '+' : ''}${m.dx} px en X y ${m.dy >= 0 ? '+' : ''}${m.dy} px en Y`,
        detalle: `${m.desc}: estaba en (${m.x}, ${m.y}) y ahora está en (${m.actual.x}, ${m.actual.y})${m.dw || m.dh ? `; además cambió de tamaño (${m.w}×${m.h} → ${m.actual.w}×${m.actual.h})` : ''}.`,
        delta: { dx: m.dx, dy: m.dy, dw: m.dw, dh: m.dh }, _ref: caja(m), _act: caja(m.actual) });
    }
    for (const m of c.redimensionados.filter((x) => Math.abs(x.dw) >= 8 || Math.abs(x.dh) >= 8)) {
      h.push({ tipo: 'Cambio de tamaño', severidad: Math.abs(m.dw) >= 40 || Math.abs(m.dh) >= 40 ? 'Media' : 'Baja',
        titulo: `${textoEl(m)} cambió de tamaño: ${m.w}×${m.h} → ${m.actual.w}×${m.actual.h} px`,
        detalle: `${m.desc} sigue en el mismo lugar pero ${m.dw ? `${m.dw > 0 ? 'creció' : 'se achicó'} ${Math.abs(m.dw)} px de ancho` : ''}${m.dw && m.dh ? ' y ' : ''}${m.dh ? `${m.dh > 0 ? 'creció' : 'se achicó'} ${Math.abs(m.dh)} px de alto` : ''}.`,
        delta: { dx: 0, dy: 0, dw: m.dw, dh: m.dh }, _ref: caja(m), _act: caja(m.actual) });
    }
    for (const m of c.cambiados) {
      h.push({ tipo: 'Texto cambiado', severidad: ['a', 'button', 'label', 'h1', 'h2'].includes(m.tag) ? 'Media' : 'Baja',
        titulo: `${m.tag}: ${textoEl(m)} → ${textoEl(m.actual)}`, detalle: `${m.desc} está en el mismo lugar con otro texto.`,
        _ref: caja(m), _act: caja(m.actual) });
    }
    for (const m of c.faltantes) {
      const inter = ['a', 'button', 'input', 'select', 'textarea'].includes(m.tag);
      h.push({ tipo: 'Elemento faltante', severidad: inter ? 'Alta' : 'Media', titulo: `Ya no aparece: ${textoEl(m)}`,
        detalle: `${m.desc} estaba en (${m.x}, ${m.y}) en la referencia y no está en la versión actual (o está oculto).`, _ref: caja(m) });
    }
    for (const s of c.estilos || []) {
      const ej = s.elementos[0];
      const inter = s.elementos.some((x) => ['a', 'button', 'input', 'select', 'textarea'].includes(x.tag));
      h.push({ tipo: 'Cambio de estilo', severidad: inter || s.elementos.length >= 5 ? 'Media' : 'Baja',
        titulo: `${s.elementos.length === 1 ? textoEl(ej) : `${s.elementos.length} elementos`}: ${s.nombre} ${s.de} → ${s.a}`,
        detalle: `Cambió el ${s.nombre} de ${s.elementos.slice(0, 4).map(textoEl).join(', ')}${s.elementos.length > 4 ? ' y otros' : ''}.`,
        estilo: { propiedad: s.prop, de: s.de, a: s.a }, _ref: caja(ej), _act: caja(ej.actual) });
    }
    for (const m of c.nuevos) {
      h.push({ tipo: 'Elemento nuevo', severidad: 'Baja', titulo: `Nuevo: ${textoEl(m)}`,
        detalle: `${m.desc} en (${m.x}, ${m.y}) no estaba en la referencia. Si es intencional, aceptá la nueva referencia.`, _act: caja(m) });
    }
  }
  if (p.alto_ref && p.alto && Math.abs(p.alto - p.alto_ref) > 20) {
    const d = p.alto - p.alto_ref;
    h.push({ tipo: 'Alto de la página', severidad: Math.abs(d) > 200 ? 'Media' : 'Baja',
      titulo: `La página ${d > 0 ? 'creció' : 'se achicó'} ${Math.abs(d)} px de alto (${p.alto_ref} → ${p.alto})`,
      detalle: 'Hay contenido nuevo, contenido que se fue o algo que cambió de tamaño.' });
  }
  // Píxeles que cambiaron y no se explican por un elemento medido (fondos, colores, imágenes, iconos).
  if (p.pct > a.pctMax && !h.some((x) => x.tipo !== 'Alto de la página')) {
    h.push({ tipo: 'Cambio visual', severidad: p.pct > 5 ? 'Alta' : p.pct > 1 ? 'Media' : 'Baja',
      titulo: `Cambió el ${p.pct} % de la pantalla (${p.regiones.length} región(es))`,
      detalle: 'Los elementos están en su lugar pero cambian colores, imágenes, fuentes, bordes o fondos: mirá las regiones marcadas.',
      _region: p.regiones[0] });
  }
  return h;
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(RAIZ, 'scripts', 'generar_informe_pixel_perfect.py'),
    path.join(carpeta, 'pixel-perfect.json'), path.join(carpeta, 'informe-pixel-perfect.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_pixel_perfect.py ` +
      '<carpeta>/pixel-perfect.json <carpeta>/informe-pixel-perfect.html');
    return false;
  }
  return true;
}

function aceptar(carpeta, cuales) {
  const dirRef = path.join(carpeta, 'referencia');
  const dirAct = path.join(carpeta, 'actual');
  const datosArch = path.join(carpeta, 'pixel-perfect.json');
  if (!fs.existsSync(datosArch)) throw new Error('No hay una comparación para aceptar: corré primero sin --aceptar.');
  const datos = JSON.parse(fs.readFileSync(datosArch, 'utf8'));
  const refArch = path.join(dirRef, 'referencia.json');
  const ref = JSON.parse(fs.readFileSync(refArch, 'utf8'));
  const ids = cuales === 'todas' ? datos.pantallas.map((p) => p.id) : cuales.split(',').map((x) => x.trim());
  let n = 0;
  for (const id of ids) {
    const p = datos.pantallas.find((x) => x.id === id);
    if (!p || !p.actual) { console.log(`  ${id}: no está en la última comparación (se ignora)`); continue; }
    fs.copyFileSync(path.join(carpeta, p.actual), path.join(dirRef, `${id}.png`));
    const elems = JSON.parse(fs.readFileSync(path.join(dirAct, `${id}.json`), 'utf8'));
    fs.writeFileSync(path.join(dirRef, `${id}.json`), JSON.stringify(elems));
    const r = ref.pantallas.find((x) => x.id === id);
    const nueva = { id, url: p.url, resolucion: p.resolucion, archivo: `${id}.png`, alto: p.alto, aceptada: new Date().toISOString() };
    if (r) Object.assign(r, nueva); else ref.pantallas.push(nueva);
    n++;
  }
  ref.actualizada = new Date().toISOString();
  fs.writeFileSync(refArch, JSON.stringify(ref, null, 2));
  console.log(`${n} pantalla(s) aceptadas como nueva referencia.`);
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
  const inicio = normalizar(url);
  const host = new URL(inicio).hostname;
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'pixel-perfect', a.historia || host);
  const relRaiz = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  if (a.aceptar) {
    aceptar(carpeta, a.aceptar);
    return;
  }
  const dirRef = path.join(carpeta, 'referencia');
  const refArch = path.join(dirRef, 'referencia.json');
  const hayRef = fs.existsSync(refArch) && !a.referencia;
  const ref = hayRef ? JSON.parse(fs.readFileSync(refArch, 'utf8')) : null;
  a.ocultar = ocultarEfectivo(a, ref);

  archivar(carpeta, GENERADOS, 'pixel-perfect.json'); // la corrida anterior pasa a historial/ (últimas 5)
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });
  if (a.referencia) fs.rmSync(dirRef, { recursive: true, force: true });
  const dirAct = path.join(carpeta, 'actual');
  const dirDif = path.join(carpeta, 'diferencias');
  const dirRec = path.join(carpeta, 'recortes');
  for (const d of [dirRef, dirAct, dirDif, dirRec]) fs.mkdirSync(d, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');

  const pw = require('playwright');
  const browser = await navegadorComun.lanzar(pw[a.navegador], { headless: !a.headed, channel: undefined }); // siempre el mismo motor: las referencias no cambian con NAVEGADOR_CANAL
  const t0 = Date.now();
  const resoluciones = parsearResoluciones(a.resoluciones || (ref && ref.config && ref.config.resoluciones) || '390x844,1366x768');
  let paginas;
  if (!a.paginas && ref) {
    paginas = [...new Set(ref.pantallas.map((p) => p.url))];
  } else {
    const ctx = await browser.newContext();
    paginas = await descubrir(await ctx.newPage(), inicio, a);
    await ctx.close();
  }
  const modo = hayRef ? 'comparacion' : 'referencia';
  console.log(`${modo === 'referencia' ? 'Creando la referencia' : 'Comparando contra la referencia'}: ${paginas.length} página(s) × ${resoluciones.length} resolución(es) · ${a.navegador}`);
  console.log(`Salida: ${relRaiz(carpeta)}`);

  const pantallas = [];
  let n = 0;
  for (const [i, u] of paginas.entries()) {
    for (const res of resoluciones) {
      n++;
      const id = (ref && ref.pantallas.find((p) => p.url === u && p.resolucion === res.id) || {}).id || idPantalla(i + 1, u, res.id);
      process.stdout.write(`[${n}/${paginas.length * resoluciones.length}] ${res.id.padEnd(9)} ${u} `);
      const p = { id, url: u, resolucion: res.id, dispositivo: res.nombre, ancho_vp: res.ancho };
      const archAct = path.join(modo === 'referencia' ? dirRef : dirAct, `${id}.png`);
      try {
        const m = await capturarPantalla(browser, u, res, a, archAct);
        Object.assign(p, { status: m.status, titulo: m.titulo, alto: m.alto, recortada: m.recortada, errores_js: m.errores_js,
          n_elementos: m.elementos.length });
        fs.writeFileSync(path.join(modo === 'referencia' ? dirRef : dirAct, `${id}.json`), JSON.stringify(m.elementos));
      } catch (e) {
        p.error = String(e.message || e).split('\n')[0].slice(0, 200);
        console.log(`→ error: ${p.error}`);
        pantallas.push(p);
        continue;
      }
      if (modo === 'referencia') {
        p.referencia = rel(archAct);
        p.estado = 'Referencia';
        console.log('→ referencia guardada');
        pantallas.push(p);
        continue;
      }
      p.actual = rel(archAct);
      const archRef = path.join(dirRef, `${id}.png`);
      if (!fs.existsSync(archRef)) {
        p.estado = 'Nueva';
        console.log('→ sin referencia (pantalla nueva)');
        pantallas.push(p);
        continue;
      }
      p.referencia = rel(archRef);
      const refInfo = ref.pantallas.find((x) => x.id === id) || {};
      p.alto_ref = refInfo.alto || visual.tamanoPng(archRef).alto;
      p.referencia_fecha = refInfo.aceptada || ref.fecha;
      const cmp = visual.compararPng(archRef, archAct, { umbral: a.umbral });
      const dif = path.join(dirDif, `${id}.png`);
      fs.writeFileSync(dif, cmp.diff);
      Object.assign(p, { diferencia: rel(dif), pct: cmp.pct, pixeles: cmp.distintos, regiones: cmp.regiones.slice(0, 12) });
      // Elementos: solo si la referencia es una captura (un diseño de Figma no trae elementos).
      const elemRef = path.join(dirRef, `${id}.json`);
      if (fs.existsSync(elemRef)) {
        const r = JSON.parse(fs.readFileSync(elemRef, 'utf8'));
        const act = JSON.parse(fs.readFileSync(path.join(dirAct, `${id}.json`), 'utf8'));
        p.elementos_cmp = visual.compararElementos(r, act, { tolerancia: a.tolerancia });
      } else p.solo_pixeles = true;
      // Recortes de las regiones con más cambios: referencia, actual y diferencia lado a lado.
      p.recortes = [];
      for (const [k, reg] of p.regiones.slice(0, 6).entries()) {
        const v = visual.ventanaDe([reg], 40, 260, 120);
        const base = path.join(dirRec, `${id}-r${k + 1}`);
        fs.writeFileSync(`${base}-ref.png`, visual.recorteMarcado(archRef, v, reg, [255, 176, 32]));
        fs.writeFileSync(`${base}-act.png`, visual.recorteMarcado(archAct, v, reg, [255, 176, 32]));
        fs.writeFileSync(`${base}-dif.png`, visual.recorteMarcado(dif, v, null));
        p.recortes.push({ region: reg, referencia: rel(`${base}-ref.png`), actual: rel(`${base}-act.png`), diferencia: rel(`${base}-dif.png`) });
      }
      p.hallazgos = hallazgosDe(p, a);
      // Recorte de cada hallazgo: antes (posición en la referencia) y después (en la actual).
      for (const [k, h] of p.hallazgos.entries()) {
        const cajas = [h._ref, h._act, h._region].filter(Boolean);
        if (!cajas.length) continue;
        const v = visual.ventanaDe(cajas, 70);
        const base = path.join(dirRec, `${id}-h${k + 1}`);
        if (h._ref || h._region) {
          fs.writeFileSync(`${base}-antes.png`, visual.recorteMarcado(archRef, v, h._ref || h._region));
          h.antes = rel(`${base}-antes.png`);
        }
        if (h._act || h._region) {
          fs.writeFileSync(`${base}-despues.png`, visual.recorteMarcado(archAct, v, h._act || h._region, h._act ? [20, 168, 149] : [255, 45, 45]));
          h.despues = rel(`${base}-despues.png`);
        }
        delete h._ref; delete h._act; delete h._region;
      }
      const serias = p.hallazgos.filter((x) => x.severidad !== 'Baja');
      p.estado = !p.hallazgos.length && p.pct <= a.pctMax ? 'Sin cambios' : serias.length ? 'Con cambios' : 'Cambios menores';
      console.log(`→ ${p.estado} · ${p.pct} % · ${p.hallazgos.length} hallazgo(s)`);
      pantallas.push(p);
    }
  }
  await browser.close();

  if (modo === 'referencia') {
    fs.writeFileSync(refArch, JSON.stringify({ url: inicio, host, historia: a.historia || null, fecha: new Date().toISOString(),
      navegador: a.navegador, config: { resoluciones: resoluciones.map((r) => r.id).join(','), ocultar: a.ocultar },
      pantallas: pantallas.filter((p) => !p.error).map((p) => ({ id: p.id, url: p.url, resolucion: p.resolucion,
        archivo: `${p.id}.png`, alto: p.alto, aceptada: new Date().toISOString() })) }, null, 2));
  }

  // Hallazgos numerados (los más graves primero).
  const hallazgos = [];
  for (const p of pantallas) {
    for (const h of p.hallazgos || []) hallazgos.push({ ...h, pantalla: p.id, url: p.url, resolucion: p.resolucion });
  }
  hallazgos.sort((x, y) => SEV_ORDEN[x.severidad] - SEV_ORDEN[y.severidad]);
  hallazgos.forEach((h, i) => { h.id = `V-${String(i + 1).padStart(2, '0')}`; });
  for (const p of pantallas) delete p.hallazgos;

  const cuenta = (e) => pantallas.filter((p) => p.estado === e).length;
  const comparadas = pantallas.filter((p) => p.pct != null);
  const resultado = {
    modo, url: inicio, host, historia: a.historia || null, fecha: new Date().toISOString(), marca: sello(),
    duracion_s: Math.round((Date.now() - t0) / 1000), navegador: a.navegador,
    herramienta: `Playwright ${require('playwright/package.json').version} · comparación propia (pngjs)`,
    referencia: ref ? { fecha: ref.fecha, actualizada: ref.actualizada || null, navegador: ref.navegador } : { fecha: new Date().toISOString(), navegador: a.navegador },
    config: { resoluciones: resoluciones.map((r) => r.id), ocultar: a.ocultar, umbral: a.umbral, tolerancia_px: a.tolerancia, pct_max: a.pctMax },
    resumen: {
      paginas: paginas.length, pantallas: pantallas.length, comparadas: comparadas.length,
      sin_cambios: cuenta('Sin cambios'), cambios_menores: cuenta('Cambios menores'), con_cambios: cuenta('Con cambios'),
      nuevas: cuenta('Nueva'), errores: pantallas.filter((p) => p.error).length,
      elementos_corridos: hallazgos.filter((h) => h.tipo === 'Elemento corrido').length,
      bloques_desplazados: hallazgos.filter((h) => h.tipo === 'Bloque desplazado').length,
      faltantes: hallazgos.filter((h) => h.tipo === 'Elemento faltante').length,
      nuevos: hallazgos.filter((h) => h.tipo === 'Elemento nuevo').length,
      pct_max: comparadas.length ? Math.max(...comparadas.map((p) => p.pct)) : 0,
      hallazgos: hallazgos.length,
      por_severidad: Object.fromEntries(['Crítica', 'Alta', 'Media', 'Baja'].map((s) => [s, hallazgos.filter((h) => h.severidad === s).length])),
    },
    hallazgos, pantallas,
  };
  const salida = path.join(carpeta, 'pixel-perfect.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  const r = resultado.resumen;
  if (modo === 'referencia') console.log(`\nReferencia creada: ${r.pantallas - r.errores} pantalla(s). La próxima corrida compara contra ella.`);
  else console.log(`\nSin cambios: ${r.sin_cambios} · cambios menores: ${r.cambios_menores} · con cambios: ${r.con_cambios} · nuevas: ${r.nuevas} · hallazgos: ${r.hallazgos}`);
  console.log(`Datos: ${relRaiz(salida)}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${relRaiz(path.join(carpeta, 'informe-pixel-perfect.html'))}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, parsearResoluciones, hallazgosDe, idPantalla, ocultarEfectivo, descubrir, GENERADOS };

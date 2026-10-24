// Auditoría de rendimiento web con Lighthouse (agente auditor-rendimiento-web).
//
// Uso (desde la raíz del repo):
//   npm run rendimiento -- [--url https://mi-app.com] [--historia HU-001] [--paginas url1,url2]
//                          [--max-paginas 5] [--profundidad 1] [--dispositivos mobile,desktop]
//                          [--repeticiones 1] [--headed]
//
// Recorre las páginas del mismo sitio a partir de la URL (por defecto APP_URL del .env, o BASEURL),
// o solo las de --paginas, y en cada una corre Lighthouse (textos en español) en mobile (Moto G
// con 4G lenta, el estándar de Google) y en desktop:
//   - puntajes de rendimiento, buenas prácticas y SEO,
//   - Core Web Vitals de laboratorio: LCP, CLS y TBT (el equivalente de laboratorio de INP),
//     más FCP y Speed Index, con los umbrales de Google (bueno / a mejorar / malo),
//   - las oportunidades de mejora con el ahorro estimado y los recursos que las causan,
//   - el elemento LCP, el peso por tipo de recurso y el impacto de terceros,
//   - la secuencia de carga (capturas) y la captura final.
// Con --repeticiones N corre N veces cada página y se queda con la mediana (Lighthouse varía
// entre corridas: para comparar versiones conviene 3).
//
// Deja todo en output/rendimiento/<HU o host>/ (la corrida anterior pasa a historial/, últimas 5):
// rendimiento.json, informe-rendimiento.html, capturas/ y lighthouse/ (el reporte nativo de cada
// página, para el detalle). Al terminar genera el informe HTML (scripts/generar_informe_rendimiento.py).
//
// Son datos de LABORATORIO (una carga simulada), no de usuarios reales (CrUX): sirven para
// encontrar y comparar problemas, no para afirmar cómo lo vive cada persona.
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { archivar } = require('../historial/historial.js');
const { normalizar, slug, sello, NO_RECORRER, ARCHIVO } = require('../explorador/explorar.js');

const RAIZ = path.resolve(__dirname, '..', '..', '..', '..');
const GENERADOS = ['rendimiento.json', 'analisis.json', 'informe-rendimiento.html', 'capturas', 'lighthouse'];
// Umbrales de Google (bueno hasta, malo desde). TBT es el sustituto de laboratorio de INP.
const UMBRALES = {
  lcp: { nombre: 'LCP', titulo: 'Largest Contentful Paint', bueno: 2500, malo: 4000, unidad: 'ms', vital: true },
  cls: { nombre: 'CLS', titulo: 'Cumulative Layout Shift', bueno: 0.1, malo: 0.25, unidad: '', vital: true },
  tbt: { nombre: 'TBT', titulo: 'Total Blocking Time', bueno: 200, malo: 600, unidad: 'ms', vital: true },
  fcp: { nombre: 'FCP', titulo: 'First Contentful Paint', bueno: 1800, malo: 3000, unidad: 'ms' },
  si: { nombre: 'SI', titulo: 'Speed Index', bueno: 3400, malo: 5800, unidad: 'ms' },
};
const AUDIT_METRICA = { lcp: 'largest-contentful-paint', cls: 'cumulative-layout-shift', tbt: 'total-blocking-time',
  fcp: 'first-contentful-paint', si: 'speed-index' };
const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };

function argumentos(argv) {
  const a = { maxPaginas: 5, profundidad: 1, dispositivos: ['mobile', 'desktop'], repeticiones: 1, headed: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--historia') a.historia = v();
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--dispositivos') a.dispositivos = v().split(',').map((x) => x.trim().toLowerCase()).filter(Boolean);
    else if (k === '--repeticiones') a.repeticiones = parseInt(v(), 10);
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (a.dispositivos.some((d) => !['mobile', 'desktop'].includes(d))) throw new Error('--dispositivos acepta mobile y/o desktop.');
  if (!(a.repeticiones >= 1 && a.repeticiones <= 5)) throw new Error('--repeticiones tiene que estar entre 1 y 5.');
  if (!(a.maxPaginas >= 1 && a.maxPaginas <= 50)) throw new Error('--max-paginas tiene que estar entre 1 y 50.');
  return a;
}

/** bueno | mejorar | malo según los umbrales de Google. */
function calificar(clave, valor) {
  const u = UMBRALES[clave];
  if (!u || valor == null) return null;
  return valor <= u.bueno ? 'bueno' : valor <= u.malo ? 'mejorar' : 'malo';
}

// La corrida anterior no se borra: pasa a historial/<fecha>/ (se guardan las últimas 5) para compararla.
function limpiarCarpeta(carpeta) {
  archivar(carpeta, GENERADOS, 'rendimiento.json');
  for (const nombre of GENERADOS) fs.rmSync(path.join(carpeta, nombre), { recursive: true, force: true });
}

const aTexto = (s) => String(s || '').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/`/g, '').trim();
const enlaces = (s) => [...String(s || '').matchAll(/\[([^\]]+)\]\((https?:[^)]+)\)/g)].map((m) => m[2]);

// Filas de los detalles de una auditoría: según el tipo, vienen en items, o en tablas anidadas
// (las "insights" de Lighthouse 13 traen una lista de tablas).
function filasDe(d) {
  if (!d) return [];
  const items = Array.isArray(d.items) ? d.items : d.items && typeof d.items === 'object' ? Object.values(d.items) : [];
  return items.flatMap((it) => (it && (it.type === 'table' || it.type === 'opportunity') && Array.isArray(it.items) ? it.items : [it]))
    .filter((it) => it && typeof it === 'object');
}

// Del LHR (resultado de Lighthouse) se queda solo con lo que usa el informe.
function resumir(lhr) {
  const audits = lhr.audits;
  const metricas = {};
  for (const [k, id] of Object.entries(AUDIT_METRICA)) {
    const au = audits[id];
    if (au && au.numericValue != null) metricas[k] = { valor: au.numericValue, texto: au.displayValue, estado: calificar(k, au.numericValue) };
  }
  const puntajes = {};
  for (const [id, c] of Object.entries(lhr.categories || {})) puntajes[id] = c.score == null ? null : Math.round(c.score * 100);

  // Oportunidades: auditorías de rendimiento que fallan y estiman un ahorro (tiempo o bytes).
  const refs = (lhr.categories.performance && lhr.categories.performance.auditRefs) || [];
  const oportunidades = [];
  for (const ref of refs) {
    const au = audits[ref.id];
    if (!au || au.score == null || au.score >= 0.9 || au.scoreDisplayMode === 'informative' || au.scoreDisplayMode === 'notApplicable') continue;
    const d = au.details || {};
    const ms = d.overallSavingsMs || (au.metricSavings && Math.max(au.metricSavings.LCP || 0, au.metricSavings.FCP || 0, au.metricSavings.TBT || 0)) || 0;
    const bytes = d.overallSavingsBytes || 0;
    const cls = (au.metricSavings && au.metricSavings.CLS) || 0;
    if (!ms && !bytes && !cls) continue;
    const items = filasDe(d).slice(0, 6).map((it) => ({
      url: typeof it.url === 'string' ? it.url : (it.node && it.node.snippet) || it.label || it.source && it.source.url || '',
      ahorro_bytes: it.wastedBytes || null, ahorro_ms: it.wastedMs || null, peso: it.totalBytes || it.transferSize || null,
    })).filter((it) => it.url);
    oportunidades.push({ id: ref.id, titulo: au.title, descripcion: aTexto(au.description), mas_info: enlaces(au.description)[0] || null,
      ahorro_ms: Math.round(ms), ahorro_bytes: Math.round(bytes), ahorro_cls: cls ? Math.round(cls * 1000) / 1000 : 0,
      valor: au.displayValue || '', metricas: Object.keys(au.metricSavings || {}).filter((m) => au.metricSavings[m] > 0), items });
  }
  oportunidades.sort((x, y) => y.ahorro_ms - x.ahorro_ms || y.ahorro_bytes - x.ahorro_bytes);

  // Elemento LCP (según la versión de Lighthouse, viene en una u otra auditoría).
  let lcp = null;
  for (const id of ['largest-contentful-paint-element', 'lcp-breakdown-insight', 'lcp-discovery-insight']) {
    const d = audits[id] && audits[id].details;
    const buscar = (x) => (x && typeof x === 'object' ? (x.type === 'node' ? x : Object.values(x).map(buscar).find(Boolean)) : null);
    const nodo = buscar(d);
    if (nodo) { lcp = { selector: nodo.selector || '', html: (nodo.snippet || '').slice(0, 300), etiqueta: nodo.nodeLabel || '' }; break; }
  }

  // Peso por tipo de recurso, desde la lista de requests.
  const recursos = {};
  let peso = 0;
  let requests = 0;
  for (const r of filasDe(audits['network-requests'] && audits['network-requests'].details)) {
    const tipo = { Document: 'Documento', Script: 'JavaScript', Stylesheet: 'CSS', Image: 'Imágenes', Font: 'Fuentes', Media: 'Video y audio',
      XHR: 'Datos (fetch/XHR)', Fetch: 'Datos (fetch/XHR)' }[r.resourceType] || 'Otros';
    recursos[tipo] = recursos[tipo] || { bytes: 0, requests: 0 };
    recursos[tipo].bytes += r.transferSize || 0;
    recursos[tipo].requests += 1;
    peso += r.transferSize || 0;
    requests += 1;
  }

  const terceros = filasDe(audits['third-party-summary'] && audits['third-party-summary'].details)
    .map((t) => ({ entidad: typeof t.entity === 'string' ? t.entity : (t.entity && t.entity.text) || '', bytes: t.transferSize || 0, bloqueo_ms: Math.round(t.blockingTime || 0) }))
    .filter((t) => t.entidad).sort((x, y) => y.bloqueo_ms - x.bloqueo_ms || y.bytes - x.bytes).slice(0, 8);

  const fotos = filasDe(audits['screenshot-thumbnails'] && audits['screenshot-thumbnails'].details)
    .map((f) => ({ ms: Math.round(f.timing), data: f.data }));
  const final = audits['final-screenshot'] && audits['final-screenshot'].details && audits['final-screenshot'].details.data;

  return { puntajes, metricas, oportunidades, lcp, recursos, peso_total: peso, requests, terceros, _fotos: fotos, _final: final,
    advertencias: (lhr.runWarnings || []).map(aTexto) };
}

function guardarImagen(dataUri, archivo) {
  const m = /^data:image\/\w+;base64,(.+)$/.exec(dataUri || '');
  if (!m) return false;
  fs.writeFileSync(archivo, Buffer.from(m[1], 'base64'));
  return true;
}

function armarHallazgos(resultados) {
  const h = [];
  // Core Web Vitals y métricas fuera de los umbrales, por página y dispositivo.
  for (const r of resultados) {
    if (r.error) {
      h.push({ categoria: 'Error', severidad: 'Alta', pagina: r.url, dispositivo: r.dispositivo, titulo: 'Lighthouse no pudo medir la página', detalle: r.error });
      continue;
    }
    for (const [k, m] of Object.entries(r.metricas)) {
      if (m.estado === 'bueno') continue;
      const u = UMBRALES[k];
      const malo = m.estado === 'malo';
      h.push({ categoria: u.vital ? 'Core Web Vitals' : 'Métrica', metrica: k, severidad: malo ? (u.vital ? 'Alta' : 'Media') : (u.vital ? 'Media' : 'Baja'),
        pagina: r.url, dispositivo: r.dispositivo, titulo: `${u.nombre} ${malo ? 'malo' : 'a mejorar'}: ${m.texto}`,
        detalle: `${u.titulo}: bueno hasta ${u.unidad === 'ms' ? `${u.bueno / 1000} s` : u.bueno}, malo desde ${u.unidad === 'ms' ? `${u.malo / 1000} s` : u.malo}.` });
    }
  }
  // Oportunidades: una por auditoría, sumando páginas (el mismo problema suele venir de la plantilla).
  const op = new Map();
  for (const r of resultados.filter((x) => !x.error)) {
    for (const o of r.oportunidades) {
      if (!op.has(o.id)) op.set(o.id, { ...o, paginas: [], dispositivos: new Set(), ahorro_ms_max: 0, ahorro_bytes_max: 0 });
      const x = op.get(o.id);
      if (!x.paginas.includes(r.url)) x.paginas.push(r.url);
      x.dispositivos.add(r.dispositivo);
      x.ahorro_ms_max = Math.max(x.ahorro_ms_max, o.ahorro_ms);
      x.ahorro_bytes_max = Math.max(x.ahorro_bytes_max, o.ahorro_bytes);
    }
  }
  const oportunidades = [...op.values()].map((o) => ({ ...o, dispositivos: [...o.dispositivos] }))
    .sort((x, y) => y.ahorro_ms_max - x.ahorro_ms_max || y.ahorro_bytes_max - x.ahorro_bytes_max);
  for (const o of oportunidades) {
    const sev = o.ahorro_ms_max >= 1500 ? 'Alta' : o.ahorro_ms_max >= 500 || o.ahorro_bytes_max >= 500 * 1024 ? 'Media' : 'Baja';
    h.push({ categoria: 'Oportunidad', severidad: sev, pagina: o.paginas[0], paginas: o.paginas, dispositivo: o.dispositivos.join(', '),
      titulo: o.titulo, detalle: [o.ahorro_ms_max ? `ahorro estimado hasta ${(o.ahorro_ms_max / 1000).toFixed(1)} s` : '',
        o.ahorro_bytes_max ? `${Math.round(o.ahorro_bytes_max / 1024)} KB` : ''].filter(Boolean).join(' · '), auditoria: o.id });
  }
  h.sort((a, b) => SEV_ORDEN[a.severidad] - SEV_ORDEN[b.severidad]);
  return { hallazgos: h.map((x, i) => ({ id: `R-${String(i + 1).padStart(2, '0')}`, ...x })), oportunidades };
}

const mediana = (xs) => { const s = [...xs].sort((a, b) => a - b); return s[Math.floor((s.length - 1) / 2)]; };

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(RAIZ, 'scripts', 'generar_informe_rendimiento.py'),
    path.join(carpeta, 'rendimiento.json'), path.join(carpeta, 'informe-rendimiento.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_rendimiento.py ` +
      '<carpeta>/rendimiento.json <carpeta>/informe-rendimiento.html');
    return false;
  }
  return true;
}

async function descubrirPaginas(inicio, a, chromium) {
  if (a.paginas) return a.paginas.map(normalizar);
  const host = new URL(inicio).hostname;
  const b = await navegadorComun.lanzar(chromium);
  const page = await b.newPage();
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
    } catch { /* la página que no abre la reporta Lighthouse */ }
  }
  await b.close();
  return lista;
}

async function main() {
  const a = argumentos(process.argv.slice(2));
  if (a.ayuda) {
    console.log(fs.readFileSync(__filename, 'utf8').split('\n').filter((l) => l.startsWith('//')).map((l) => l.slice(3)).join('\n'));
    return;
  }
  const [mayor, menor] = process.versions.node.split('.').map(Number);
  if (mayor < 22 || (mayor === 22 && menor < 19)) {
    throw new Error(`Lighthouse necesita Node 22.19 o superior (tenés ${process.versions.node}). Actualizá Node (22 LTS) y volvé a correr.`);
  }
  const url = a.url || (a.paginas && a.paginas[0]) || process.env.APP_URL || process.env.BASEURL;
  if (!url) throw new Error('No hay URL: pasala con --url o definí APP_URL en el .env de la raíz.');
  if (!/^https?:\/\//i.test(url)) throw new Error(`La URL tiene que empezar con http:// o https:// (recibí "${url}").`);
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  const inicio = normalizar(url);
  const host = new URL(inicio).hostname;

  const carpeta = a.salida ? path.resolve(a.salida) : path.join(RAIZ, 'output', 'rendimiento', a.historia || host);
  limpiarCarpeta(carpeta);
  const dirCapturas = path.join(carpeta, 'capturas');
  const dirLh = path.join(carpeta, 'lighthouse');
  for (const d of [dirCapturas, dirLh]) fs.mkdirSync(d, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');

  const { chromium } = require('playwright');
  const { default: lighthouse, desktopConfig } = await import('lighthouse');
  const chromeLauncher = require('chrome-launcher');
  const paginas = await descubrirPaginas(inicio, a, chromium);
  console.log(`Rendimiento de ${paginas.length} página(s) · ${a.dispositivos.join(' y ')} · ${a.repeticiones} repetición(es) por página`);
  console.log(`Salida: ${path.relative(RAIZ, carpeta).split(path.sep).join('/')} (reemplaza la corrida anterior)`);
  const t0 = Date.now();

  // Lighthouse no puede limitar un header a la app (lo mandaría también a terceros): mide sin el bypass.
  if (navegadorComun.leerConfig().bypass) {
    console.log('Aviso: Lighthouse no usa QA_BYPASS_* (mandaría el token a terceros). Si la app frena a Lighthouse, pedí que dejen pasar tu IP.');
  }
  // Un Chrome propio para Lighthouse (el de Playwright, así no hace falta instalar otro).
  const chrome = await chromeLauncher.launch({ chromePath: chromium.executablePath(),
    chromeFlags: [...(a.headed ? [] : ['--headless=new']), '--no-first-run', '--disable-extensions'] });
  const resultados = [];
  try {
    for (const [i, u] of paginas.entries()) {
      for (const disp of a.dispositivos) {
        const n = String(i + 1).padStart(2, '0');
        process.stdout.write(`[${i + 1}/${paginas.length}] ${disp.padEnd(7)} ${u} `);
        const corridas = [];
        let error = null;
        for (let k = 0; k < a.repeticiones; k++) {
          try {
            const r = await lighthouse(u, { port: chrome.port, output: ['html'], logLevel: 'error', locale: 'es-419',
              onlyCategories: ['performance', 'best-practices', 'seo'] }, disp === 'desktop' ? desktopConfig : undefined);
            if (r && r.lhr && !r.lhr.runtimeError) corridas.push(r);
            else error = (r && r.lhr && r.lhr.runtimeError && r.lhr.runtimeError.message) || 'Lighthouse no devolvió resultados';
          } catch (e) {
            error = String(e.message || e).split('\n')[0].slice(0, 200);
          }
        }
        if (!corridas.length) {
          console.log(`→ error: ${error}`);
          resultados.push({ url: u, dispositivo: disp, error });
          continue;
        }
        // Mediana por puntaje de rendimiento (con una sola corrida, esa).
        const scores = corridas.map((r) => r.lhr.categories.performance.score || 0);
        const elegida = corridas.find((r) => (r.lhr.categories.performance.score || 0) === mediana(scores));
        let resumen;
        try {
          resumen = resumir(elegida.lhr);
        } catch (e) {
          const msg = `No pude leer el resultado de Lighthouse: ${String(e.message || e).split(/\r?\n/)[0]}`;
          console.log(`→ error: ${msg}`);
          resultados.push({ url: u, dispositivo: disp, error: msg });
          continue;
        }
        const res = { url: u, dispositivo: disp, titulo: '', ...resumen, repeticiones: corridas.length,
          puntajes_corridas: scores.map((s) => Math.round(s * 100)) };
        const nativo = path.join(dirLh, `${n}-${slug(u)}-${disp}.html`);
        fs.writeFileSync(nativo, Array.isArray(elegida.report) ? elegida.report[0] : elegida.report);
        res.lighthouse = rel(nativo);
        const final = path.join(dirCapturas, `${n}-${slug(u)}-${disp}.jpg`);
        if (guardarImagen(res._final, final)) res.captura = rel(final);
        res.secuencia = [];
        for (const [j, f] of res._fotos.entries()) {
          const arch = path.join(dirCapturas, `${n}-${slug(u)}-${disp}-t${String(j).padStart(2, '0')}.jpg`);
          if (guardarImagen(f.data, arch)) res.secuencia.push({ ms: f.ms, captura: rel(arch) });
        }
        delete res._final;
        delete res._fotos;
        resultados.push(res);
        const m = res.metricas;
        console.log(`→ ${res.puntajes.performance} · LCP ${m.lcp ? m.lcp.texto : '—'} · CLS ${m.cls ? m.cls.texto : '—'} · TBT ${m.tbt ? m.tbt.texto : '—'}`);
      }
    }
  } finally {
    await chrome.kill();
  }

  const { hallazgos, oportunidades } = armarHallazgos(resultados);
  const ok = resultados.filter((r) => !r.error);
  const prom = (disp) => {
    const xs = ok.filter((r) => r.dispositivo === disp && r.puntajes.performance != null).map((r) => r.puntajes.performance);
    return xs.length ? Math.round(xs.reduce((s, x) => s + x, 0) / xs.length) : null;
  };
  // Páginas con los tres Core Web Vitals en verde (null si ese dispositivo no se midió).
  const vitalesOk = (disp) => (a.dispositivos.includes(disp) ? ok.filter((r) => r.dispositivo === disp)
    .filter((r) => ['lcp', 'cls', 'tbt'].every((k) => !r.metricas[k] || r.metricas[k].estado === 'bueno')).length : null);
  const resultado = {
    url: inicio, host, historia: a.historia || null, fecha: new Date().toISOString(), marca: sello(),
    duracion_s: Math.round((Date.now() - t0) / 1000), herramienta: `Lighthouse ${require('lighthouse/package.json').version}`,
    config: { dispositivos: a.dispositivos, repeticiones: a.repeticiones, max_paginas: a.maxPaginas, umbrales: UMBRALES },
    resumen: {
      paginas: paginas.length, mediciones: resultados.length, errores: resultados.length - ok.length,
      rendimiento_mobile: prom('mobile'), rendimiento_desktop: prom('desktop'),
      vitales_ok_mobile: vitalesOk('mobile'), vitales_ok_desktop: vitalesOk('desktop'),
      hallazgos: hallazgos.length, oportunidades: oportunidades.length,
    },
    hallazgos, oportunidades, resultados,
  };
  const salida = path.join(carpeta, 'rendimiento.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  const r = resultado.resumen;
  console.log(`\nRendimiento promedio: mobile ${r.rendimiento_mobile ?? '—'} · desktop ${r.rendimiento_desktop ?? '—'}`);
  const vit = (x) => (x == null ? '—' : `${x}/${paginas.length}`);
  console.log(`Core Web Vitals en verde: mobile ${vit(r.vitales_ok_mobile)} · desktop ${vit(r.vitales_ok_desktop)}`);
  console.log(`Hallazgos: ${r.hallazgos} · oportunidades distintas: ${r.oportunidades}`);
  console.log(`Datos: ${path.relative(RAIZ, salida).split(path.sep).join('/')}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${path.relative(RAIZ, path.join(carpeta, 'informe-rendimiento.html')).split(path.sep).join('/')}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, calificar, armarHallazgos, limpiarCarpeta, UMBRALES, GENERADOS, resumir };

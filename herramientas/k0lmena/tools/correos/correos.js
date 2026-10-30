// Verificación de correos con Mailpit (agente verificador-correos).
//
// Uso (desde la raíz del repo):
//   npm run correos -- [--para ana@test.com] [--de no-reply@app.com] [--asunto "Confirmá"] [--buscar "consulta de Mailpit"]
//                      [--desde-min 30] [--ultimos 20] [--esperar 1 --timeout-s 60] [--espera espera.json]
//                      [--links si|no] [--dns si|no] [--historia HU-001] [--mailpit http://localhost:8025]
//   npm run correos -- --limpiar-buzon        → borra TODOS los mensajes del buzón de prueba (con confirmación)
//
// Mailpit es un buzón de prueba: la app (en el ambiente de pruebas) manda sus mails por SMTP a Mailpit
// (puerto 1025) y Mailpit los guarda sin entregarlos a nadie. Esta herramienta los lee por su API
// (MAILPIT_URL del .env; por defecto http://localhost:8025) y revisa cada uno:
//   - que llegó lo esperado (--espera: destinatario, asunto, textos, links y adjuntos de cada caso),
//   - asunto, remitente y destinatarios; variables sin reemplazar ({{nombre}}, ${x}, undefined, null…),
//   - versión de texto plano, tamaño del HTML (Gmail recorta desde 102 KB), imágenes sin alt o que
//     apuntan a localhost, links rotos, a localhost o sin https (link-check de Mailpit),
//   - compatibilidad del HTML con los clientes de correo (html-check de Mailpit: Outlook, Gmail, Apple Mail…),
//   - cómo se ve en desktop (700 px) y en mobile (375 px), con captura de cada uno y si desborda,
//   - entregabilidad (entregabilidad.js): SPF, DKIM y DMARC del dominio remitente por DNS, la firma DKIM y los
//     Authentication-Results del mensaje, la alineación de dominios, List-Unsubscribe y el puntaje de spam (el de
//     SpamAssassin si Mailpit lo tiene activado; si no, uno heurístico). --dns no apaga las consultas DNS.
// Con --esperar N espera hasta que lleguen N correos que coincidan (después de disparar el envío).
//
// Deja todo en output/correos/<HU o buzón>/: correos.json, informe-correos.html, capturas/ y eml/ (el
// mensaje original). La corrida anterior pasa a historial/ (se guardan las últimas 5). Solo lee el
// buzón: borrarlo (--limpiar-buzon) se hace con confirmación.
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { archivar } = require('../historial/historial.js');
const entregabilidad = require('./entregabilidad');

// Datos (output/, input/, .auth/) en el proyecto y scripts de Python en el código de k0lmenIA: ver ../rutas.js.
const { PROYECTO: RAIZ, CODIGO } = require('../rutas');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p); // npm run cambia el cwd a herramientas/k0lmena
const GENERADOS = ['correos.json', 'analisis.json', 'informe-correos.html', 'capturas', 'eml'];
const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };
// Variables de plantilla que quedaron sin reemplazar (o valores vacíos de JavaScript).
const VARIABLE = /\{\{\s*[\w.]+\s*\}\}|\$\{[\w.]+\}|%\([\w]+\)s|\[\[[\w ]+\]\]|\[(?:NOMBRE|NAME|USUARIO|USER|EMAIL|LINK|URL)\]|\bundefined\b|\[object Object\]|\bNaN\b|(?<![\w.])null(?![\w.])/g;
const LOCAL = /^https?:\/\/(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|[\w-]+\.local)(:\d+)?\b/i;

function argumentos(argv) {
  const a = { ultimos: 50, timeoutS: 60, links: true, dns: true, mailpit: process.env.MAILPIT_URL || 'http://localhost:8025' };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--para') a.para = v();
    else if (k === '--de') a.de = v();
    else if (k === '--asunto') a.asunto = v();
    else if (k === '--buscar') a.buscar = v();
    else if (k === '--desde-min') a.desdeMin = parseFloat(v());
    else if (k === '--ultimos') a.ultimos = parseInt(v(), 10);
    else if (k === '--esperar') a.esperar = parseInt(v(), 10);
    else if (k === '--timeout-s') a.timeoutS = parseInt(v(), 10);
    else if (k === '--espera') a.espera = v();
    else if (k === '--links') a.links = !/^(no|false|0)$/i.test(v());
    else if (k === '--dns') a.dns = !/^(no|false|0)$/i.test(v());
    else if (k === '--historia') a.historia = v();
    else if (k === '--mailpit') a.mailpit = v();
    else if (k === '--salida') a.salida = v();
    else if (k === '--limpiar-buzon') a.limpiar = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  a.mailpit = a.mailpit.replace(/\/+$/, '');
  return a;
}

// ------------------------------------------------------------------ API de Mailpit
function cabeceras() {
  const h = { Accept: 'application/json' };
  if (process.env.MAILPIT_USUARIO) h.Authorization = `Basic ${Buffer.from(`${process.env.MAILPIT_USUARIO}:${process.env.MAILPIT_CLAVE || ''}`).toString('base64')}`;
  return h;
}

async function api(base, ruta, { metodo = 'GET', cuerpo, texto = false } = {}) {
  let r;
  try {
    r = await fetch(`${base}${ruta}`, { method: metodo, headers: { ...cabeceras(), ...(cuerpo ? { 'Content-Type': 'application/json' } : {}) },
      body: cuerpo ? JSON.stringify(cuerpo) : undefined, signal: AbortSignal.timeout(30000) });
  } catch (e) {
    throw new Error(`No pude conectarme a Mailpit en ${base} (${e.cause ? e.cause.code || e.cause.message : e.message}). ` +
      '¿Está corriendo? Ver herramientas/mailpit/README.md');
  }
  if (!r.ok) throw Object.assign(new Error(`Mailpit respondió ${r.status} en ${ruta}`), { status: r.status });
  return texto ? r.text() : r.json();
}

const direccion = (x) => (x && (x.Address || x.address)) || '';
const direcciones = (xs) => (xs || []).map(direccion).filter(Boolean);

// Consulta de búsqueda de Mailpit a partir de los filtros.
function consulta(a) {
  const partes = [];
  if (a.para) partes.push(`to:"${a.para}"`);
  if (a.de) partes.push(`from:"${a.de}"`);
  if (a.asunto) partes.push(`subject:"${a.asunto}"`);
  if (a.buscar) partes.push(a.buscar);
  return partes.join(' ');
}

async function listar(a) {
  const q = consulta(a);
  const ruta = q ? `/api/v1/search?query=${encodeURIComponent(q)}&limit=${a.ultimos}` : `/api/v1/messages?limit=${a.ultimos}`;
  let lista = (await api(a.mailpit, ruta)).messages || [];
  if (a.desdeMin) {
    const limite = Date.now() - a.desdeMin * 60000;
    lista = lista.filter((m) => new Date(m.Created || m.Date || 0).getTime() >= limite);
  }
  return lista;
}

async function esperar(a) {
  const fin = Date.now() + a.timeoutS * 1000;
  let lista = [];
  while (Date.now() < fin) {
    lista = await listar(a);
    if (lista.length >= a.esperar) return lista;
    await new Promise((r) => setTimeout(r, 2000));
  }
  return lista;
}

// ------------------------------------------------------------------ revisión de un correo
function textoPlano(html) {
  return String(html || '').replace(/<style[\s\S]*?<\/style>|<script[\s\S]*?<\/script>/gi, ' ').replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
}

function linksDe(html, text) {
  const hrefs = [...String(html || '').matchAll(/<a\b[^>]*href\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi)]
    .map((m) => ({ url: m[1].replace(/&amp;/g, '&'), texto: textoPlano(m[2]).slice(0, 80) }));
  const sueltos = [...String(text || '').matchAll(/https?:\/\/[^\s<>"')]+/g)].map((m) => ({ url: m[0], texto: '' }));
  const vistos = new Set();
  return [...hrefs, ...sueltos].filter((l) => !vistos.has(l.url) && vistos.add(l.url));
}

function imagenesDe(html) {
  return [...String(html || '').matchAll(/<img\b[^>]*>/gi)].map((m) => {
    const tag = m[0];
    const src = (tag.match(/\bsrc\s*=\s*["']([^"']*)["']/i) || [])[1] || '';
    const alt = tag.match(/\balt\s*=\s*["']([^"']*)["']/i);
    return { src, alt: alt ? alt[1] : null };
  });
}

function revisar(m, extras) {
  const h = [];
  const agregar = (tipo, severidad, titulo, detalle) => h.push({ tipo, severidad, titulo, detalle });
  const asunto = m.Subject || '';
  const html = m.HTML || '';
  const texto = m.Text || '';
  if (!asunto.trim()) agregar('Asunto', 'Alta', 'El correo no tiene asunto', 'Sin asunto, los clientes lo muestran como "(sin asunto)" y suele ir a spam.');
  else if (asunto.length > 78) agregar('Asunto', 'Baja', `Asunto largo (${asunto.length} caracteres)`, 'En mobile se corta a los 30–40 caracteres: lo importante tiene que ir al principio.');
  if (!direccion(m.From)) agregar('Remitente', 'Alta', 'Sin remitente', 'El campo From está vacío.');
  if (!direcciones(m.To).length) agregar('Destinatario', 'Alta', 'Sin destinatario', 'El campo To está vacío (¿solo copia oculta?).');
  for (const [donde, contenido] of [['asunto', asunto], ['texto', texto], ['HTML', textoPlano(html)]]) {
    const vs = [...new Set((contenido.match(VARIABLE) || []).map((x) => x.trim()))];
    if (vs.length) agregar('Variable sin reemplazar', 'Alta', `${vs.slice(0, 3).join(', ')} en el ${donde}`,
      `La plantilla mandó ${vs.join(', ')} sin el valor real: la persona lo ve tal cual.`);
  }
  if (html && !texto.trim()) agregar('Texto plano', 'Media', 'No tiene versión de texto plano', 'Algunos clientes y lectores de pantalla usan la versión de texto; sin ella sube el puntaje de spam.');
  const kb = Buffer.byteLength(html, 'utf8') / 1024;
  if (kb > 102) agregar('Tamaño', 'Media', `HTML de ${Math.round(kb)} KB`, 'Gmail recorta los mensajes de más de 102 KB y esconde el resto detrás de "Ver mensaje completo".');
  const imgs = imagenesDe(html);
  const sinAlt = imgs.filter((i) => i.alt === null);
  if (sinAlt.length) agregar('Imágenes', 'Baja', `${sinAlt.length} imagen(es) sin texto alternativo`, 'Muchos clientes bloquean las imágenes: sin alt, no se sabe qué decían.');
  const imgLocal = imgs.filter((i) => LOCAL.test(i.src) || /^(file:|\/[^/]|\.\.?\/)/i.test(i.src));
  if (imgLocal.length) agregar('Imágenes', 'Alta', `${imgLocal.length} imagen(es) que no se van a ver`, `Apuntan a una ruta local o relativa: ${imgLocal.slice(0, 3).map((i) => i.src).join(', ')}`);
  const links = linksDe(html, texto);
  for (const l of links) {
    if (LOCAL.test(l.url)) l.problema = { severidad: 'Alta', texto: 'apunta a un ambiente local' };
    else if (/^http:\/\//i.test(l.url)) l.problema = { severidad: 'Media', texto: 'sin https' };
    const chk = (extras.links || []).find((x) => x.URL === l.url);
    if (chk) {
      l.status = chk.StatusCode;
      // Un link a localhost ya está marcado por eso (es la causa, no que "no responde").
      if ((!chk.StatusCode || chk.StatusCode >= 400) && !LOCAL.test(l.url)) {
        l.problema = { severidad: 'Alta', texto: chk.StatusCode ? `roto (${chk.StatusCode})` : `sin respuesta (${chk.Status || 'error'})` };
      }
    }
  }
  for (const l of links.filter((x) => x.problema)) {
    agregar('Link', l.problema.severidad, `Link ${l.problema.texto}: ${l.texto || l.url}`.slice(0, 140), l.url);
  }
  const lu = m.ListUnsubscribe || {};
  if (lu.Errors) agregar('Desuscripción', 'Baja', 'El encabezado List-Unsubscribe tiene errores', lu.Errors);
  const compat = extras.compat;
  if (compat && compat.problemas.length) {
    agregar('Compatibilidad', compat.pct < 80 ? 'Media' : 'Baja', `${compat.problemas.length} función(es) del HTML sin soporte en algunos clientes (${compat.pct} % compatible)`,
      compat.problemas.slice(0, 5).map((p) => `${p.titulo}: ${p.clientes.join(', ')}`).join(' · '));
  }
  if (extras.desborde > 4) agregar('Responsive', 'Media', `En mobile (375 px) se sale ${extras.desborde} px de ancho`, 'Aparece scroll horizontal: el diseño no se adapta al celular.');
  return { hallazgos: h, links, imagenes: imgs.length };
}

// Compatibilidad: resumen del html-check de Mailpit (qué funciones no soportan los clientes principales).
function resumirCompat(hc) {
  if (!hc || !hc.Total) return null;
  const t = hc.Total;
  const pct = typeof t.Supported === 'number' ? Math.round(t.Supported) : null;
  const problemas = (hc.Warnings || []).map((w) => {
    const no = (w.Results || []).filter((r) => r.Support === 'no').map((r) => `${r.Family}${r.Platform ? ` (${r.Platform})` : ''}`);
    return { titulo: w.Title, categoria: w.Category, clientes: [...new Set(no)].slice(0, 6), url: w.URL };
  }).filter((p) => p.clientes.length);
  return { pct, problemas };
}

// ------------------------------------------------------------------ expectativas (lo que tenía que llegar)
function evaluarEspera(esperas, correos) {
  return esperas.map((x, i) => {
    const cand = correos.filter((c) => (!x.para || c.para.some((p) => p.toLowerCase() === String(x.para).toLowerCase()))
      && (!x.asunto || c.asunto.toLowerCase().includes(String(x.asunto).toLowerCase())));
    const r = { id: `E-${String(i + 1).padStart(2, '0')}`, ...x, controles: [] };
    if (!cand.length) { r.estado = 'No llegó'; return r; }
    const c = cand[0];
    r.correo = c.id;
    const cuerpo = `${c.texto} ${c.texto_html}`.toLowerCase();
    const ctl = (nombre, ok, detalle = '') => r.controles.push({ nombre, ok, detalle });
    if (x.remitente) ctl(`Remitente ${x.remitente}`, c.de.toLowerCase() === String(x.remitente).toLowerCase(), c.de);
    for (const t of x.contiene || []) ctl(`Contiene “${t}”`, cuerpo.includes(String(t).toLowerCase()));
    for (const t of x.no_contiene || []) ctl(`No contiene “${t}”`, !cuerpo.includes(String(t).toLowerCase()));
    for (const t of x.links || []) {
      const l = c.links.find((y) => y.url.includes(t));
      ctl(`Link a “${t}”`, Boolean(l) && !(l.problema && l.problema.severidad === 'Alta'), l ? l.url : 'no está');
    }
    for (const t of x.adjuntos || []) ctl(`Adjunto ${t}`, c.adjuntos.some((y) => y.nombre.toLowerCase().includes(String(t).toLowerCase())));
    if (x.max_minutos && c.demora_min != null) ctl(`Llega en menos de ${x.max_minutos} min`, c.demora_min <= x.max_minutos, `${c.demora_min} min`);
    r.estado = r.controles.every((y) => y.ok) ? 'Cumple' : 'No cumple';
    return r;
  });
}

// ------------------------------------------------------------------ captura del HTML (desktop y mobile)
async function capturas(browser, html, base) {
  const salida = {};
  for (const [nombre, ancho] of [['desktop', 700], ['mobile', 375]]) {
    const page = await browser.newPage({ viewport: { width: ancho, height: 900 }, javaScriptEnabled: false });
    try {
      await page.setContent(html || '<p style="font-family:sans-serif;color:#888">(sin HTML: solo texto)</p>', { waitUntil: 'load', timeout: 20000 })
        .catch(() => page.setContent(html, { waitUntil: 'domcontentloaded' }));
      const archivo = `${base}-${nombre}.png`;
      const alto = await page.evaluate(() => Math.min(document.documentElement.scrollHeight, 6000));
      await page.screenshot({ path: archivo, clip: { x: 0, y: 0, width: ancho, height: Math.max(200, alto) } });
      salida[nombre] = archivo;
      if (nombre === 'mobile') salida.desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    } finally {
      await page.close();
    }
  }
  return salida;
}

function resumenEntregabilidad(correos, dominios) {
  const spam = correos.map((c) => c.entregabilidad && c.entregabilidad.spam).filter(Boolean);
  const ok = (k) => dominios.filter((d) => !d.sin_dns && d[k] && d[k].estado === 'OK').length;
  return {
    dominios: dominios.length, dominios_sin_dns: dominios.filter((d) => d.sin_dns).length, spf_ok: ok('spf'), dmarc_ok: ok('dmarc'),
    dkim_firmados: correos.filter((c) => c.entregabilidad && c.entregabilidad.firmas_dkim.length).length,
    con_list_unsubscribe: correos.filter((c) => c.entregabilidad && c.entregabilidad.list_unsubscribe).length,
    spam_fuente: spam.length ? spam[0].fuente : null,
    spam_promedio: spam.length ? Math.round(spam.reduce((s, x) => s + x.puntaje, 0) / spam.length * 10) / 10 : null,
    spam_sobre_umbral: spam.filter((x) => x.es_spam).length,
  };
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(CODIGO, 'scripts', 'generar_informe_correos.py'),
    path.join(carpeta, 'correos.json'), path.join(carpeta, 'informe-correos.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_correos.py <carpeta>/correos.json <carpeta>/informe-correos.html`);
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
  if (a.limpiar) {
    await api(a.mailpit, '/api/v1/messages', { metodo: 'DELETE', cuerpo: {} });
    console.log(`Buzón de prueba vacío (${a.mailpit}).`);
    return;
  }
  const info = await api(a.mailpit, '/api/v1/info').catch((e) => { if (e.status) return {}; throw e; });
  const lista = a.esperar ? await esperar(a) : await listar(a);
  const nombre = a.historia || (a.para ? a.para.replace(/[^\w.@-]+/g, '_') : 'buzon');
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'correos', nombre);
  archivar(carpeta, GENERADOS, 'correos.json');
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });
  const dirCap = path.join(carpeta, 'capturas');
  const dirEml = path.join(carpeta, 'eml');
  for (const d of [dirCap, dirEml]) fs.mkdirSync(d, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');
  const relRaiz = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  console.log(`Mailpit ${info.Version || ''} en ${a.mailpit} · ${lista.length} correo(s)${consulta(a) ? ` para «${consulta(a)}»` : ''}`);

  const { chromium } = require('playwright');
  const browser = await navegadorComun.lanzar(chromium);
  const correos = [];
  const cacheDns = new Map();
  try {
    for (const [i, resumen] of lista.entries()) {
      const id = resumen.ID;
      const m = await api(a.mailpit, `/api/v1/message/${id}`);
      const n = String(i + 1).padStart(2, '0');
      process.stdout.write(`[${i + 1}/${lista.length}] ${m.Subject || '(sin asunto)'} → ${direcciones(m.To).join(', ')} `);
      const raw = await api(a.mailpit, `/api/v1/message/${id}/raw`, { texto: true }).catch(() => null);
      let eml = null;
      if (raw) { eml = path.join(dirEml, `${n}-${id}.eml`); fs.writeFileSync(eml, raw); }
      const hc = await api(a.mailpit, `/api/v1/message/${id}/html-check`).catch(() => null);
      const lc = a.links ? await api(a.mailpit, `/api/v1/message/${id}/link-check?follow=true`).catch(() => null) : null;
      const cap = await capturas(browser, m.HTML, path.join(dirCap, `${n}-${id}`));
      const encab = await api(a.mailpit, `/api/v1/message/${id}/headers`).catch(() => ({}));
      const sa = await api(a.mailpit, `/api/v1/message/${id}/sa-check`).catch(() => null);
      const dominio = entregabilidad.dominioDe(direccion(m.From));
      const selectores = entregabilidad.firmasDKIM(encab).filter((f) => f.dominio === dominio).map((f) => f.selector);
      const dnsInfo = a.dns && dominio ? await entregabilidad.dnsDominio(dominio, selectores, cacheDns) : null;
      const ent = entregabilidad.evaluar(m, encab, dnsInfo, sa);
      const compat = resumirCompat(hc);
      const rev = revisar(m, { links: lc && lc.Links, compat, desborde: cap.desborde });
      const creado = new Date(m.Date || resumen.Created || Date.now());
      const recibido = new Date(resumen.Created || m.Date || Date.now());
      correos.push({
        id: `M-${n}`, mailpit_id: id, asunto: m.Subject || '', de: direccion(m.From), para: direcciones(m.To), cc: direcciones(m.Cc),
        responder_a: direcciones(m.ReplyTo), fecha: recibido.toISOString(), demora_min: Math.max(0, Math.round((recibido - creado) / 6000) / 10),
        tamano_kb: Math.round((m.Size || 0) / 1024 * 10) / 10, html_kb: Math.round(Buffer.byteLength(m.HTML || '', 'utf8') / 102.4) / 10,
        tiene_html: Boolean(m.HTML), tiene_texto: Boolean((m.Text || '').trim()), texto: (m.Text || '').slice(0, 4000),
        texto_html: textoPlano(m.HTML).slice(0, 4000), adjuntos: (m.Attachments || []).map((x) => ({ nombre: x.FileName, tipo: x.ContentType, kb: Math.round((x.Size || 0) / 102.4) / 10 })),
        imagenes: rev.imagenes, links: rev.links, compatibilidad: compat, desborde_mobile: cap.desborde,
        captura_desktop: cap.desktop && rel(cap.desktop), captura_mobile: cap.mobile && rel(cap.mobile), eml: eml && rel(eml),
        ver_en_mailpit: `${a.mailpit}/view/${id}`, hallazgos: [...rev.hallazgos, ...entregabilidad.hallazgosCorreo(ent)],
        entregabilidad: { ...ent, dns: undefined },
      });
      console.log(`→ ${correos[correos.length - 1].hallazgos.length} hallazgo(s) · spam ${ent.spam.puntaje}`);
    }
  } finally {
    await browser.close();
  }
  const esperas = a.espera ? JSON.parse(fs.readFileSync(desde(a.espera), 'utf8')) : [];
  const expectativas = evaluarEspera(Array.isArray(esperas) ? esperas : esperas.correos || [], correos);
  const hallazgos = [];
  for (const c of correos) for (const h of c.hallazgos) hallazgos.push({ ...h, correo: c.id, asunto: c.asunto, captura: c.captura_desktop });
  const dominios = [...cacheDns.values()];
  for (const d of dominios) for (const h of entregabilidad.hallazgosDominio(d)) hallazgos.push({ ...h, correo: null, dominio: d.dominio });
  for (const x of expectativas.filter((y) => y.estado !== 'Cumple')) {
    hallazgos.push({ tipo: 'Expectativa', severidad: x.estado === 'No llegó' ? 'Crítica' : 'Alta', correo: x.correo || null,
      titulo: x.estado === 'No llegó' ? `No llegó el correo esperado${x.asunto ? ` «${x.asunto}»` : ''}${x.para ? ` a ${x.para}` : ''}`
        : `El correo «${x.asunto || x.correo}» no cumple: ${x.controles.filter((y) => !y.ok).map((y) => y.nombre).join(', ')}`,
      detalle: x.caso ? `Caso ${x.caso}` : '' });
  }
  hallazgos.sort((x, y) => SEV_ORDEN[x.severidad] - SEV_ORDEN[y.severidad]);
  hallazgos.forEach((h, i) => { h.id = `C-${String(i + 1).padStart(2, '0')}`; });
  const compats = correos.map((c) => c.compatibilidad && c.compatibilidad.pct).filter((x) => x != null);
  const sello = () => { const d = new Date(); const p = (x) => String(x).padStart(2, '0'); return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`; };
  const resultado = {
    mailpit: a.mailpit, version_mailpit: info.Version || null, historia: a.historia || null, filtro: consulta(a) || null,
    fecha: new Date().toISOString(), marca: sello(), herramienta: 'Mailpit API · Playwright',
    resumen: { correos: correos.length, expectativas: expectativas.length, cumplen: expectativas.filter((x) => x.estado === 'Cumple').length,
      no_llegaron: expectativas.filter((x) => x.estado === 'No llegó').length, hallazgos: hallazgos.length,
      links: correos.reduce((s, c) => s + c.links.length, 0), links_con_problemas: correos.reduce((s, c) => s + c.links.filter((l) => l.problema).length, 0),
      variables_sin_reemplazar: hallazgos.filter((h) => h.tipo === 'Variable sin reemplazar').length,
      compatibilidad_prom: compats.length ? Math.round(compats.reduce((s, x) => s + x, 0) / compats.length) : null,
      entregabilidad: resumenEntregabilidad(correos, dominios),
      por_severidad: Object.fromEntries(['Crítica', 'Alta', 'Media', 'Baja'].map((s) => [s, hallazgos.filter((h) => h.severidad === s).length])) },
    expectativas, hallazgos, correos, dominios,
  };
  const salida = path.join(carpeta, 'correos.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  const r = resultado.resumen;
  console.log(`\nCorreos: ${r.correos} · expectativas: ${r.cumplen}/${r.expectativas} cumplen (${r.no_llegaron} no llegaron) · hallazgos: ${r.hallazgos}`);
  console.log(`Datos: ${relRaiz(salida)}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${relRaiz(path.join(carpeta, 'informe-correos.html'))}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, consulta, revisar, resumirCompat, evaluarEspera, linksDe, imagenesDe, textoPlano, resumenEntregabilidad, VARIABLE, GENERADOS };

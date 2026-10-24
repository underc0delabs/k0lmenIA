// Reparador de la automatización web (agente reparador-automatizacion).
//
// Uso (desde la raíz del repo):
//   npm run reparar -- [--historia HU-001] [--reporte herramientas/k0lmena/reports/web/cucumber-report.json]
//                      [--fallos output/fallos/<x>/fallos.json] [--url-base https://mi-app.com]
//   npm run reparar -- --aplicar R-01,R-03 [--historia HU-001]     → aplica esas propuestas (o "seguras")
//   npm run reparar -- --verificar [--historia HU-001]              → vuelve a correr los escenarios reparados
//   npm run reparar -- --solo-informe [--historia HU-001]           → regenera el informe
//
// 1) Analizar (por defecto): toma los escenarios web que fallaron en el último npm test (o los del
//    analista-fallos con --fallos), saca del error el locator que no funcionó, lo busca en
//    web/locators, en los steps o en el .feature, y lo prueba contra el DOM que k0lmena guardó en el
//    momento de la falla (reports/web/dom/). Diagnostica: ya no existe, coincide con varios
//    elementos, existe pero no se ve, o existe y es visible (falló la espera). Busca los candidatos
//    más parecidos (rol, nombre accesible, texto, placeholder, label, data-testid, id) y propone el
//    locator nuevo más robusto (role + name → label → placeholder → testId → text), verificando que
//    encuentre UN solo elemento. Marca con un recuadro el elemento propuesto en una captura del DOM.
//    No toca ningún archivo.
// 2) Aplicar (--aplicar): reemplaza el locator en su archivo (guarda una copia en respaldo/ y el diff
//    en cambios.diff). "seguras" = las de confianza Alta en pasos de acción. Lo que sale de un paso
//    de verificación (Then) puede ser un bug de la aplicación: solo se aplica si se lo nombra por ID.
// 3) Verificar (--verificar): corre solo los escenarios reparados (TAGS con su @HU y @CP) en una
//    carpeta propia y marca cada reparación como Verificada o Sigue fallando. Corre contra el
//    ambiente como npm test: se hace solo con confirmación.
//
// Deja todo en output/reparaciones/<HU o suite>/: reparaciones.json, informe-reparacion.html,
// capturas/, respaldo/, cambios.diff y verificacion/. Analizar de nuevo REEMPLAZA la carpeta.
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { archivar } = require('../historial/historial.js');
const { spawnSync } = require('child_process');

// Datos (output/, input/, .auth/) en el proyecto y scripts de Python en el código de k0lmenIA: ver ../rutas.js.
const { PROYECTO: RAIZ, CODIGO } = require('../rutas');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p); // npm run cambia el cwd a herramientas/k0lmena
const K0 = path.resolve(__dirname, '..', '..');
const GENERADOS = ['reparaciones.json', 'analisis.json', 'informe-reparacion.html', 'capturas', 'respaldo', 'cambios.diff', 'verificacion'];
const METODOS = ['getByRole', 'getByText', 'getByLabel', 'getByPlaceholder', 'getByTestId', 'getByAltText', 'getByTitle'];

function argumentos(argv) {
  const a = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--historia') a.historia = v().toUpperCase();
    else if (k === '--reporte') a.reporte = v();
    else if (k === '--fallos') a.fallos = v();
    else if (k === '--url-base') a.urlBase = v();
    else if (k === '--aplicar') a.aplicar = v();
    else if (k === '--verificar') a.verificar = true;
    else if (k === '--solo-informe') a.soloInforme = true;
    else if (k === '--salida') a.salida = v();
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (a.historia && !/^[A-Z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  return a;
}

// ------------------------------------------------------------------ locator del mensaje de error
// "getByRole('button', { name: 'Registrar', exact: true })" → { role: 'button', name: 'Registrar', exact: true }
function _literal(s) {
  s = s.trim();
  let m = s.match(/^(['"`])((?:\\.|(?!\1).)*)\1/);
  if (m) return { valor: m[2].replace(/\\(['"`\\])/g, '$1'), resto: s.slice(m[0].length) };
  m = s.match(/^\/((?:\\.|[^/])+)\/([a-z]*)/);
  if (m) return { valor: { regex: m[1], flags: m[2] }, resto: s.slice(m[0].length) };
  return null;
}

function _opciones(s) {
  const o = {};
  const m = s.match(/\{([^}]*)\}/);
  if (!m) return o;
  const name = m[1].match(/name:\s*((['"`]).*?\2|\/(?:\\.|[^/])+\/[a-z]*)/);
  if (name) o.name = _literal(name[1]).valor;
  if (/exact:\s*true/.test(m[1])) o.exact = true;
  return o;
}

function locatorDelError(error) {
  if (!error) return null;
  // Playwright escribe el locator en "Locator: …", "waiting for …" o "strict mode violation: …".
  const re = new RegExp(`(?:locator\\(([\\s\\S]*?)\\)\\.)?(${METODOS.join('|')})\\(([^\\n]*?)\\)(?=\\s|$|\\.|,)`, 'm');
  const m = error.match(re);
  if (m) {
    const metodo = m[2];
    const lit = _literal(m[3]);
    if (!lit) return null;
    const texto = `${metodo}(${m[3]})`;
    if (metodo === 'getByRole') return { tipo: 'role', input: { role: lit.valor, ..._opciones(lit.resto) }, texto };
    const clave = { getByText: 'text', getByLabel: 'label', getByPlaceholder: 'placeholder', getByTestId: 'testId',
      getByAltText: 'alt', getByTitle: 'title' }[metodo];
    return { tipo: clave, input: { [clave]: lit.valor }, texto };
  }
  const css = error.match(/(?:waiting for |Locator: |violation: )locator\((['"`])(.+?)\1\)/);
  if (css) {
    if (css[2].startsWith('xpath=')) return { tipo: 'xpath', input: { xpath: css[2].slice(6) }, texto: `locator('${css[2]}')` };
    return { tipo: 'css', input: { css: css[2] }, texto: `locator('${css[2]}')` };
  }
  return null;
}

const valorTxt = (v) => (v && typeof v === 'object' && v.regex ? `/${v.regex}/${v.flags}` : String(v));

// Código TypeScript de un LocatorInput (como lo escriben los mappers).
function codigoDe(input) {
  const q = (s) => (s && typeof s === 'object' && s.regex ? `/${s.regex}/${s.flags}` : `'${String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`);
  const partes = Object.entries(input).filter(([, v]) => v !== undefined).map(([k, v]) => `${k}: ${typeof v === 'boolean' ? v : q(v)}`);
  return `{ ${partes.join(', ')} }`;
}

// ------------------------------------------------------------------ dónde está el locator en el código
function listar(dir, ext) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith(ext)).map((f) => path.join(dir, f));
}

const escRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function ubicar(loc, esc) {
  const relK = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  const valor = loc.input.name ?? loc.input.text ?? loc.input.label ?? loc.input.placeholder ?? loc.input.testId ?? loc.input.alt ??
    loc.input.title ?? loc.input.css ?? loc.input.xpath;
  if (valor == null || typeof valor === 'object') return null;
  const clave = loc.tipo === 'role' ? 'name' : loc.tipo;
  const reEntrada = new RegExp(`\\b${clave}\\s*:\\s*(['"\`])${escRe(valor)}\\1`);
  // 1) locators de la historia primero, después el resto
  const locs = listar(path.join(K0, 'web', 'locators'), '.ts').sort((x, y) => (esc.historia && x.includes(esc.historia) ? -1 : 0) - (esc.historia && y.includes(esc.historia) ? -1 : 0));
  for (const f of locs) {
    const lineas = fs.readFileSync(f, 'utf8').split(/\r?\n/);
    const i = lineas.findIndex((l) => reEntrada.test(l) && (loc.tipo !== 'role' || new RegExp(`role\\s*:\\s*['"\`]${escRe(loc.input.role)}['"\`]`).test(l)));
    if (i >= 0) {
      const m = lineas[i].match(/^\s*([\w$]+)\s*:/);
      return { tipo: 'locator', archivo: relK(f), linea: i + 1, texto: lineas[i].trim(), clave: m ? m[1] : null };
    }
  }
  // 2) el valor viene del .feature (un parámetro del paso): el escenario lo pasa como "texto"
  if (esc.uri) {
    const f = path.join(K0, esc.uri);
    if (fs.existsSync(f)) {
      const lineas = fs.readFileSync(f, 'utf8').split(/\r?\n/);
      const i = lineas.findIndex((l, k) => k + 1 >= (esc.linea || 0) && l.includes(`"${valor}"`));
      if (i >= 0) return { tipo: 'feature', archivo: relK(f), linea: i + 1, texto: lineas[i].trim(), valor };
    }
  }
  // 3) escrito directo en un step
  for (const f of listar(path.join(K0, 'web', 'steps'), '.ts')) {
    const lineas = fs.readFileSync(f, 'utf8').split(/\r?\n/);
    const i = lineas.findIndex((l) => l.includes(`'${valor}'`) || l.includes(`"${valor}"`) || l.includes(`\`${valor}\``));
    if (i >= 0) return { tipo: 'step', archivo: relK(f), linea: i + 1, texto: lineas[i].trim() };
  }
  return null;
}

// ------------------------------------------------------------------ fallas a reparar
function _textos(p) {
  return (p.embeddings || []).filter((x) => x.mime_type === 'text/plain').map((x) => Buffer.from(x.data, 'base64').toString('utf8'));
}

function fallasDelReporte(archivo, historia) {
  const base = path.dirname(archivo);
  let features = [];
  try { features = JSON.parse(fs.readFileSync(archivo, 'utf8') || '[]'); } catch { throw new Error(`No pude leer ${archivo}.`); }
  const salida = new Map();
  for (const f of features) {
    for (const esc of f.elements || []) {
      if (esc.type === 'background') continue;
      const tags = [...new Set([...(f.tags || []), ...(esc.tags || [])].map((t) => t.name.replace(/^@/, '')))];
      const hu = tags.find((t) => /^HU-\d+$/i.test(t)) || null;
      if (historia && (hu || '').toUpperCase() !== historia) continue;
      let paso = null;
      let error = '';
      let dom = null;
      let url = null;
      for (const p of esc.steps || []) {
        const r = p.result || {};
        if (r.status === 'failed' && !paso) {
          paso = `${(p.keyword || '').trim()} ${p.name || ''}`.trim();
          error = (r.error_message || '').replace(/\x1b\[[0-9;]*m/g, '').trim();
        }
        for (const t of _textos(p)) {
          const d = t.match(/^DOM:[ \t]*([^\r\n]+)/); // el nombre del escenario puede tener espacios
          if (d && !dom) dom = path.join(base, d[1]);
          const u = t.match(/- URL:\s*(\S+)/);
          if (u && !url) url = u[1];
        }
      }
      const clave = `${f.uri}:${esc.line}`;
      if (!paso) { salida.delete(clave); continue; } // con retry: si el último intento pasó, no hay nada que reparar
      salida.set(clave, { escenario: esc.name, feature: f.name, uri: f.uri.split(path.sep).join('/'), linea: esc.line, tags, historia: hu,
        caso: tags.find((t) => /^CP(-API)?-\d+$/.test(t)) || null, paso, error, dom, url });
    }
  }
  return [...salida.values()];
}

function fallasDeAnalista(archivo, historia) {
  const datos = JSON.parse(fs.readFileSync(archivo, 'utf8'));
  const dir = path.dirname(archivo);
  return (datos.fallos || []).filter((x) => x.suite === 'web' && (!historia || (x.historia || '').toUpperCase() === historia)).map((x) => {
    const dom = (x.evidencias || []).find((ev) => ev.tipo === 'dom');
    return { escenario: x.escenario, feature: x.feature, uri: x.uri, linea: x.linea, tags: x.tags || [], historia: x.historia, caso: x.caso,
      paso: x.paso_fallido, error: (x.error || '').replace(/\x1b\[[0-9;]*m/g, ''), dom: dom ? path.join(dir, dom.archivo) : null, url: x.url || null, categoria_analista: x.categoria };
  });
}

// ------------------------------------------------------------------ análisis contra el DOM guardado
function locatorDe(page, input) {
  if ('role' in input) return page.getByRole(input.role, { name: _rx(input.name), exact: input.exact });
  if ('testId' in input) return page.getByTestId(input.testId);
  if ('placeholder' in input) return page.getByPlaceholder(_rx(input.placeholder));
  if ('label' in input) return page.getByLabel(_rx(input.label));
  if ('text' in input) return page.getByText(_rx(input.text));
  if ('alt' in input) return page.getByAltText(_rx(input.alt));
  if ('title' in input) return page.getByTitle(_rx(input.title));
  if ('css' in input) return page.locator(input.css);
  if ('xpath' in input) return page.locator(`xpath=${input.xpath}`);
  throw new Error('locator sin tipo');
}
const _rx = (v) => (v && typeof v === 'object' && v.regex ? new RegExp(v.regex, v.flags) : v);

// En el navegador: candidatos parecidos al locator original, con su puntaje y los datos para armar
// locators nuevos. Corre sobre el DOM guardado (sin JavaScript de la página).
function _candidatosEnPagina(orig) {
  const norm = (s) => (s || '').toString().normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\s+/g, ' ').trim();
  const tokens = (s) => norm(s).split(/[^a-z0-9ñ]+/).filter((t) => t.length > 1);
  const parecido = (a, b) => {
    a = norm(a); b = norm(b);
    if (!a || !b) return 0;
    if (a === b) return 1;
    if (a.includes(b) || b.includes(a)) return 0.75 * Math.min(a.length, b.length) / Math.max(a.length, b.length) + 0.2;
    const ta = new Set(tokens(a)); const tb = new Set(tokens(b));
    const comunes = [...ta].filter((t) => tb.has(t) || [...tb].some((u) => u.length > 3 && t.length > 3 && (u.startsWith(t.slice(0, 4)) || t.startsWith(u.slice(0, 4))))).length;
    return ta.size && tb.size ? (2 * comunes) / (ta.size + tb.size) * 0.85 : 0;
  };
  const rolDe = (el) => {
    const r = el.getAttribute('role');
    if (r) return r;
    const t = el.tagName.toLowerCase();
    const tipo = (el.getAttribute('type') || '').toLowerCase();
    if (t === 'button' || (t === 'input' && ['submit', 'button', 'reset'].includes(tipo))) return 'button';
    if (t === 'a' && el.hasAttribute('href')) return 'link';
    if (/^h[1-6]$/.test(t)) return 'heading';
    if (t === 'input' && tipo === 'checkbox') return 'checkbox';
    if (t === 'input' && tipo === 'radio') return 'radio';
    if (t === 'select') return 'combobox';
    if (t === 'textarea' || (t === 'input' && ['', 'text', 'email', 'password', 'search', 'tel', 'url', 'number'].includes(tipo))) return 'textbox';
    if (t === 'img') return 'img';
    if (t === 'nav') return 'navigation';
    if (t === 'li') return 'listitem';
    return null;
  };
  const etiquetaDe = (el) => {
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) return l.innerText.trim(); }
    const p = el.closest('label');
    return p ? p.innerText.trim() : '';
  };
  const nombreDe = (el) => (el.getAttribute('aria-label') || (el.getAttribute('aria-labelledby') || '').split(/\s+/).map((i) => (document.getElementById(i) || {}).innerText || '').join(' ').trim()
    || etiquetaDe(el) || (['INPUT'].includes(el.tagName) && ['submit', 'button'].includes(el.type) ? el.value : '') || el.innerText || el.getAttribute('alt')
    || el.getAttribute('title') || '').replace(/\s+/g, ' ').trim();
  const objetivo = orig.name ?? orig.text ?? orig.label ?? orig.placeholder ?? orig.testId ?? orig.alt ?? orig.title ?? '';
  const objTxt = typeof objetivo === 'object' && objetivo ? objetivo.regex : objetivo;
  // Del CSS original se rescatan pistas: #id, .clase y texto.
  const pistasCss = orig.css ? { id: (orig.css.match(/#([\w-]+)/) || [])[1], clases: (orig.css.match(/\.([\w-]+)/g) || []).map((c) => c.slice(1)) } : null;
  const SEL = 'a,button,input,select,textarea,h1,h2,h3,h4,h5,h6,label,img,[role],[data-testid],[aria-label],li,p,span,div,td,th';
  const salida = [];
  for (const el of document.querySelectorAll(SEL)) {
    const t = el.tagName.toLowerCase();
    const propio = ['span', 'div', 'p', 'li', 'td', 'th'].includes(t) && ![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (propio) continue;
    const r = el.getBoundingClientRect();
    const rol = rolDe(el);
    const nombre = nombreDe(el).slice(0, 120);
    let p = 0;
    const motivos = [];
    if (orig.role) {
      if (rol === orig.role) { p += 30; motivos.push(`mismo rol (${rol})`); } else if (rol) p -= 10;
    }
    const sim = Math.max(parecido(nombre, objTxt), parecido(el.getAttribute('placeholder'), objTxt), parecido(el.getAttribute('data-testid'), objTxt),
      parecido(el.id, objTxt), parecido(el.getAttribute('title'), objTxt), parecido(el.getAttribute('alt'), objTxt));
    if (sim > 0) { p += Math.round(sim * 55); motivos.push(`texto parecido (${Math.round(sim * 100)} %)`); }
    if (pistasCss) {
      if (pistasCss.id && el.id && parecido(el.id, pistasCss.id) > 0.5) { p += 35; motivos.push(`id parecido (#${el.id})`); }
      const cls = typeof el.className === 'string' ? el.className.split(/\s+/) : [];
      const comunes = pistasCss.clases.filter((c) => cls.includes(c)).length;
      if (comunes) { p += 15 * comunes; motivos.push(`comparte la clase ${pistasCss.clases.filter((c) => cls.includes(c)).join(', ')}`); }
    }
    if (r.width < 1 || r.height < 1) p -= 15;
    // Coincidir solo en el rol no alcanza: tiene que parecerse en algo (texto, id, clase).
    if (objTxt && sim === 0 && !(pistasCss && motivos.length)) continue;
    if (p < 25) continue;
    el.setAttribute('data-k0-cand', String(salida.length));
    salida.push({ indice: salida.length, puntaje: Math.min(100, p), motivos, tag: t, rol, nombre, texto: (el.innerText || '').trim().slice(0, 120),
      placeholder: el.getAttribute('placeholder'), testId: el.getAttribute('data-testid'), id: el.id || null, etiqueta: etiquetaDe(el) || null,
      alt: el.getAttribute('alt'), visible: r.width > 0 && r.height > 0 });
  }
  return salida.sort((a, b) => b.puntaje - a.puntaje).slice(0, 6);
}

// Captura del DOM guardado con los elementos del locator marcados (uno o varios), con contexto.
async function capturarMarcado(page, loc, archivo, color, rel) {
  const els = (await loc.all().catch(() => [])).slice(0, 8);
  const cajas = [];
  for (const el of els) {
    const c = await el.boundingBox().catch(() => null);
    if (!c) continue;
    cajas.push(c);
    await el.evaluate((x, col) => { x.style.outline = `3px solid ${col}`; x.style.outlineOffset = '2px'; }, color).catch(() => {});
  }
  if (!cajas.length) return undefined;
  const vp = page.viewportSize();
  const docAlto = await page.evaluate(() => document.documentElement.scrollHeight);
  const x0 = Math.max(0, Math.min(...cajas.map((c) => c.x)) - 140);
  const y0 = Math.max(0, Math.min(...cajas.map((c) => c.y)) - 100);
  const x1 = Math.min(vp.width, Math.max(...cajas.map((c) => c.x + c.width)) + 140);
  const y1 = Math.min(docAlto, Math.max(...cajas.map((c) => c.y + c.height)) + 100);
  await page.screenshot({ path: archivo, fullPage: true, clip: { x: x0, y: y0, width: Math.max(80, x1 - x0), height: Math.max(60, Math.min(1400, y1 - y0)) } }).catch(() => {});
  for (const el of els) await el.evaluate((x) => { x.style.outline = ''; }).catch(() => {});
  return fs.existsSync(archivo) ? rel(archivo) : undefined;
}

// En el navegador: por cada elemento marcado con data-k0-match, el contenedor más cercano que lo
// identifica (una tarjeta o fila con un título propio) y el selector acotado a ese contenedor.
function _contenedores(orig) {
  const esc = (s) => String(s).replace(/"/g, '\\"');
  const salida = [];
  const interno = orig.role ? `role=${orig.role}${orig.name && typeof orig.name === 'string' ? `[name="${esc(orig.name)}"]` : ''}`
    : orig.placeholder ? `[placeholder="${esc(orig.placeholder)}"]` : orig.text ? `text="${esc(orig.text)}"` : orig.css || null;
  if (!interno) return salida;
  for (const el of document.querySelectorAll('[data-k0-match]')) {
    let a = el.parentElement;
    for (let nivel = 0; a && nivel < 6; nivel++, a = a.parentElement) {
      const titulo = a.querySelector('h1,h2,h3,h4,h5,h6,strong,b,[class*=title],[class*=nombre],[class*=name]');
      const clase = (typeof a.className === 'string' ? a.className : '').trim().split(/\s+/).filter((c) => c && !/^(active|selected|open)$/.test(c))[0];
      if (!titulo || titulo.contains(el) || !clase) continue;
      const texto = titulo.innerText.replace(/\s+/g, ' ').trim();
      if (!texto || texto.length > 60) continue;
      salida.push({ indice: el.getAttribute('data-k0-match'), referencia: texto,
        css: `${a.tagName.toLowerCase()}.${clase}:has(${titulo.tagName.toLowerCase()}:text-is("${esc(texto)}")) >> ${interno}` });
      break;
    }
  }
  return salida;
}

// Locators posibles para un candidato, en el orden de preferencia de k0lmena.
function propuestasPara(c) {
  const p = [];
  const corto = (s) => s && s.length <= 80;
  if (c.rol && c.nombre && corto(c.nombre)) p.push({ role: c.rol, name: c.nombre }, { role: c.rol, name: c.nombre, exact: true });
  if (c.etiqueta && corto(c.etiqueta) && ['input', 'select', 'textarea'].includes(c.tag)) p.push({ label: c.etiqueta });
  if (c.placeholder) p.push({ placeholder: c.placeholder });
  if (c.testId) p.push({ testId: c.testId });
  if (c.texto && corto(c.texto) && !['input', 'select', 'textarea'].includes(c.tag)) p.push({ text: c.texto });
  if (c.id && !/^\d|[:\s]/.test(c.id)) p.push({ css: `#${c.id}` });
  return p;
}

async function analizarFalla(browser, f, a, dirCap, rel, n) {
  const r = { id: `R-${String(n).padStart(2, '0')}`, escenario: f.escenario, feature: f.feature, uri: f.uri, linea: f.linea, historia: f.historia,
    caso: f.caso, paso: f.paso, error: (f.error || '').slice(0, 2500), url: f.url, categoria_analista: f.categoria_analista || null };
  r.accion = /^(Then|Entonces|Y entonces)\b/i.test(f.paso || '') ? 'verificación' : 'acción';
  const loc = locatorDelError(f.error);
  if (!loc) {
    r.diagnostico = 'Sin locator en el error';
    r.detalle = 'El error no nombra un locator de Playwright: no es una falla de locator (puede ser una aserción de texto, un error de código, de datos o del ambiente). Revisalo con el analista-fallos.';
    return r;
  }
  r.locator = { tipo: loc.tipo, input: loc.input, texto: loc.texto, codigo: codigoDe(loc.input) };
  r.ubicacion = ubicar(loc, f);
  if (!f.dom || !fs.existsSync(f.dom)) {
    r.diagnostico = 'Sin DOM guardado';
    r.detalle = 'No hay DOM de la falla (la corrida es anterior a esta versión de k0lmena o se borró). Volvé a correr el escenario con npm test y analizá de nuevo.';
    return r;
  }
  r.dom = rel(f.dom);
  const ctx = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1366, height: 900 } });
  const page = await ctx.newPage();
  try {
    let html = fs.readFileSync(f.dom, 'utf8');
    const base = a.urlBase || f.url;
    if (base && !/<base\s/i.test(html)) html = html.replace(/<head([^>]*)>/i, `<head$1><base href="${base}">`);
    await page.setContent(html, { waitUntil: 'load', timeout: 20000 }).catch(() => page.setContent(html, { waitUntil: 'domcontentloaded' }));
    const original = locatorDe(page, loc.input);
    const cuantos = await original.count();
    const visibles = cuantos ? (await Promise.all((await original.all()).map((x) => x.isVisible()))).filter(Boolean).length : 0;
    r.coincidencias = cuantos;
    if (cuantos === 0) {
      r.diagnostico = 'Ya no existe';
      r.detalle = `${loc.texto} no encuentra ningún elemento en la página guardada: cambió el texto, el rol o el atributo (o el elemento ya no está).`;
    } else if (cuantos > 1) {
      r.diagnostico = 'Coincide con varios';
      r.detalle = `${loc.texto} encuentra ${cuantos} elementos: Playwright no sabe cuál usar (strict mode). Hay que hacerlo más específico.`;
    } else if (!visibles) {
      r.diagnostico = 'Existe pero no se ve';
      r.detalle = `${loc.texto} encuentra el elemento, pero está oculto: puede faltar abrir un menú o pestaña antes, hacer scroll, o la aplicación no lo muestra (posible bug).`;
    } else {
      r.diagnostico = 'Existe y se ve';
      r.detalle = `${loc.texto} encuentra un solo elemento visible en la página guardada: el locator está bien y falló la espera (el elemento tardó más que el timeout) o la verificación (texto, estado).`;
    }
    // Varios: primero la coincidencia exacta del mismo nombre; si no alcanza, el locator dentro del
    // contenedor de cada elemento (la tarjeta o fila que lo identifica por su título).
    if (cuantos > 1) {
      if ('role' in loc.input && !loc.input.exact) {
        const v = { ...loc.input, exact: true };
        if ((await locatorDe(page, v).count().catch(() => 0)) === 1) {
          r.propuesta = { input: v, codigo: codigoDe(v), confianza: 'Alta', puntaje: 100,
            motivos: ['con exact: true encuentra un solo elemento (el nombre completo coincide; los otros solo lo contienen)'] };
        }
      }
      if (!r.propuesta) {
        await original.evaluateAll((els) => els.forEach((el, i) => el.setAttribute('data-k0-match', String(i))));
        const scopes = await page.evaluate(_contenedores, loc.input);
        r.alternativas = [];
        for (const s of scopes) {
          const n2 = await page.locator(s.css).count().catch(() => 0);
          if (n2 === 1) r.alternativas.push({ input: { css: s.css }, codigo: codigoDe({ css: s.css }), referencia: s.referencia, indice: s.indice });
        }
        if (r.alternativas.length) {
          const pri = r.alternativas[0];
          r.propuesta = { input: pri.input, codigo: pri.codigo, confianza: 'Media', puntaje: 60, candidato_match: pri.indice,
            motivos: [`acotado al contenedor de “${pri.referencia}” (el primero de los ${cuantos}); hay ${r.alternativas.length} alternativa(s): elegí la que corresponde al caso`] };
          r.detalle += ` Propongo acotarlo al contenedor de cada uno (por ejemplo, el de “${pri.referencia}”).`;
        }
      }
      if (r.propuesta) {
        const el = r.propuesta.candidato_match != null ? page.locator(`[data-k0-match="${r.propuesta.candidato_match}"]`) : locatorDe(page, r.propuesta.input);
        r.captura = await capturarMarcado(page, el.first(), path.join(dirCap, `${r.id}-propuesta.png`), '#F9B006', rel);
      }
    }
    // Candidatos: si no existe. Si existe y se ve, el arreglo es de espera, no de locator.
    if (cuantos === 0) {
      const cands = await page.evaluate(_candidatosEnPagina, loc.input);
      for (const c of cands) {
        c.propuestas = [];
        for (const p of propuestasPara(c)) {
          const n2 = await locatorDe(page, p).count().catch(() => 0);
          c.propuestas.push({ input: p, codigo: codigoDe(p), coincidencias: n2 });
        }
        c.mejor = c.propuestas.find((p) => p.coincidencias === 1) || null;
      }
      r.candidatos = cands;
      const elegible = cands.filter((c) => c.mejor);
      const top = elegible[0];
      if (top) {
        const segundo = elegible[1];
        let confianza = top.puntaje >= 70 && (!segundo || segundo.puntaje <= top.puntaje - 15) ? 'Alta' : top.puntaje >= 45 ? 'Media' : 'Baja';
        if (r.accion === 'verificación' && confianza === 'Alta') confianza = 'Media';
        r.propuesta = { input: top.mejor.input, codigo: top.mejor.codigo, candidato: top.indice, confianza, puntaje: top.puntaje, motivos: top.motivos };
        // Captura del DOM con el elemento propuesto marcado.
        r.captura = await capturarMarcado(page, page.locator(`[data-k0-cand="${top.indice}"]`).first(), path.join(dirCap, `${r.id}-propuesta.png`), '#F9B006', rel);
      } else {
        r.detalle += ' No encontré un elemento parecido que se pueda ubicar de forma única: revisalo a mano con Playwright MCP.';
      }
    } else if (cuantos === 1 && visibles) {
      r.sugerencia_espera = 'Esperar a que la página termine de cargar antes del paso (page.waitForLoadState) o subir el timeout de ese helper; si el elemento aparece después de una acción, esperar esa respuesta.';
    }
    if (cuantos >= 1) {
      // Captura de lo que encuentra el locator original (todos, si son varios) para comparar.
      r.captura_original = await capturarMarcado(page, original, path.join(dirCap, `${r.id}-original.png`), '#ff2d2d', rel);
    }
    // Lo que sale de un paso de verificación (Then) puede ser un bug de la aplicación.
    if (r.accion === 'verificación' && r.diagnostico === 'Ya no existe') {
      r.riesgo = 'El paso que falla es una verificación: si el elemento debía estar (según el caso o la historia), es un bug de la aplicación y no hay que cambiar el test.';
    }
    if (r.ubicacion && r.ubicacion.tipo === 'feature') {
      r.riesgo = (r.riesgo ? `${r.riesgo} ` : '') + 'El valor sale del .feature (es un dato del caso): cambiarlo cambia lo que el caso espera; confirmalo con la historia.';
    }
  } finally {
    await ctx.close();
  }
  r.estado = r.propuesta ? 'Propuesta' : 'Sin propuesta';
  return r;
}

// ------------------------------------------------------------------ aplicar y verificar
function reemplazarEnLinea(linea, r) {
  const u = r.ubicacion;
  if (u.tipo === 'feature') {
    const nuevo = r.propuesta.input.name ?? r.propuesta.input.text ?? r.propuesta.input.label ?? r.propuesta.input.placeholder ?? r.propuesta.input.testId;
    return nuevo == null ? null : linea.replace(`"${u.valor}"`, `"${nuevo}"`);
  }
  // El objeto literal que contiene la entrada original: { role: 'x', name: 'y' }
  const m = linea.match(/\{[^{}]*\}/g);
  const objetivo = (m || []).find((o) => Object.values(r.locator.input).every((v) => typeof v !== 'string' || o.includes(v)));
  if (!objetivo) return null;
  return linea.replace(objetivo, r.propuesta.codigo);
}

function aplicar(carpeta, datos, cuales) {
  const ids = cuales === 'seguras'
    ? datos.reparaciones.filter((r) => r.propuesta && r.propuesta.confianza === 'Alta' && r.accion === 'acción' && r.ubicacion && r.ubicacion.tipo === 'locator').map((r) => r.id)
    : cuales.split(',').map((x) => x.trim().toUpperCase());
  const dirResp = path.join(carpeta, 'respaldo');
  const diffs = fs.existsSync(path.join(carpeta, 'cambios.diff')) ? [fs.readFileSync(path.join(carpeta, 'cambios.diff'), 'utf8')] : [];
  let n = 0;
  for (const id of ids) {
    const r = datos.reparaciones.find((x) => x.id === id);
    if (!r) { console.log(`  ${id}: no existe`); continue; }
    if (!r.propuesta || !r.ubicacion) { console.log(`  ${id}: no tiene propuesta o no sé en qué archivo está`); continue; }
    if (r.aplicada) { console.log(`  ${id}: ya estaba aplicada`); continue; }
    if (r.ubicacion.tipo === 'step') { console.log(`  ${id}: el locator está escrito en un step: cambialo a mano (${r.ubicacion.archivo}:${r.ubicacion.linea})`); continue; }
    const abs = path.join(RAIZ, r.ubicacion.archivo);
    const texto = fs.readFileSync(abs, 'utf8');
    const eol = texto.includes('\r\n') ? '\r\n' : '\n';
    const lineas = texto.split(/\r?\n/);
    const i = r.ubicacion.linea - 1;
    const nueva = reemplazarEnLinea(lineas[i], r);
    if (!nueva || nueva === lineas[i]) { console.log(`  ${id}: no pude reemplazarlo automáticamente en ${r.ubicacion.archivo}:${r.ubicacion.linea}`); continue; }
    const resp = path.join(dirResp, r.ubicacion.archivo);
    if (!fs.existsSync(resp)) { fs.mkdirSync(path.dirname(resp), { recursive: true }); fs.writeFileSync(resp, texto); }
    const antes = lineas[i];
    lineas[i] = nueva;
    fs.writeFileSync(abs, lineas.join(eol));
    const ctxIni = Math.max(0, i - 2);
    const ctxFin = Math.min(lineas.length, i + 3);
    const hunk = [`--- a/${r.ubicacion.archivo}`, `+++ b/${r.ubicacion.archivo}`, `@@ -${ctxIni + 1},${ctxFin - ctxIni} +${ctxIni + 1},${ctxFin - ctxIni} @@ ${r.id}`];
    for (let k = ctxIni; k < ctxFin; k++) {
      if (k === i) { hunk.push(`-${antes}`, `+${nueva}`); } else hunk.push(` ${lineas[k]}`);
    }
    diffs.push(hunk.join('\n'));
    r.aplicada = { fecha: new Date().toISOString(), antes: antes.trim(), despues: nueva.trim() };
    r.estado = 'Aplicada';
    n++;
    console.log(`  ${id}: aplicada en ${r.ubicacion.archivo}:${r.ubicacion.linea}`);
  }
  fs.writeFileSync(path.join(carpeta, 'cambios.diff'), diffs.filter(Boolean).join('\n\n') + '\n');
  console.log(`${n} reparación(es) aplicadas. Copia de los archivos originales en respaldo/.`);
}

function verificar(carpeta, datos) {
  const aplicadas = datos.reparaciones.filter((r) => r.aplicada);
  if (!aplicadas.length) { console.log('No hay reparaciones aplicadas para verificar.'); return; }
  const tags = [...new Set(aplicadas.map((r) => (r.historia && r.caso ? `(@${r.historia} and @${r.caso})` : r.caso ? `@${r.caso}` : null)).filter(Boolean))];
  if (!tags.length) { console.log('Los escenarios reparados no tienen @HU/@CP: corré la suite completa (npm test) para verificarlos.'); return; }
  const dir = path.join(carpeta, 'verificacion');
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const filtro = tags.join(' or ');
  console.log(`Verificando ${aplicadas.length} reparación(es): TAGS="${filtro}"`);
  const r = spawnSync('npx cucumber-js --profile web', { cwd: K0, shell: true, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024,
    env: { ...process.env, TAGS: filtro, REPORT_DIR: dir, EVIDENCE: 'captura', HEADLESS: 'true', BROWSER: process.env.BROWSER || 'chromium' } });
  const { leerCucumber } = require('../cross-browser/cross-browser.js');
  const escenarios = leerCucumber(path.join(dir, 'cucumber-report.json'));
  for (const rep of aplicadas) {
    const e = escenarios.find((x) => x.uri.split(path.sep).join('/') === rep.uri && x.linea === rep.linea) ||
      escenarios.find((x) => x.caso === rep.caso && x.historia === rep.historia);
    if (!e) { rep.verificacion = { estado: 'Sin resultado', fecha: new Date().toISOString(), detalle: (r.stderr || r.stdout || '').trim().split(/\r?\n/).slice(-3).join(' ') }; continue; }
    rep.verificacion = { estado: e.estado === 'Aprobado' ? 'Verificada' : 'Sigue fallando', fecha: new Date().toISOString(), paso: e.paso, error: (e.error || '').slice(0, 1500) };
    rep.estado = rep.verificacion.estado;
    console.log(`  ${rep.id}: ${rep.verificacion.estado}`);
  }
  datos.verificacion = { tags: filtro, fecha: new Date().toISOString(), reporte: fs.existsSync(path.join(dir, 'front-report.html')) ? 'verificacion/front-report.html' : null };
}

function resumen(datos) {
  const rs = datos.reparaciones;
  const c = (f) => rs.filter(f).length;
  return { fallas: rs.length, de_locator: c((r) => r.locator), con_propuesta: c((r) => r.propuesta), confianza_alta: c((r) => r.propuesta && r.propuesta.confianza === 'Alta'),
    aplicadas: c((r) => r.aplicada), verificadas: c((r) => r.verificacion && r.verificacion.estado === 'Verificada'),
    siguen_fallando: c((r) => r.verificacion && r.verificacion.estado === 'Sigue fallando'), sin_propuesta: c((r) => !r.propuesta),
    posibles_bugs: c((r) => r.riesgo && r.accion === 'verificación'), espera: c((r) => r.diagnostico === 'Existe y se ve'),
    por_diagnostico: rs.reduce((acc, r) => { acc[r.diagnostico] = (acc[r.diagnostico] || 0) + 1; return acc; }, {}) };
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const args = [path.join(CODIGO, 'scripts', 'generar_informe_reparacion.py'), path.join(carpeta, 'reparaciones.json'), path.join(carpeta, 'informe-reparacion.html')];
  if (fs.existsSync(path.join(carpeta, 'analisis.json'))) args.push('--analisis', path.join(carpeta, 'analisis.json'));
  const r = spawnSync(py, args, { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_reparacion.py <carpeta>/reparaciones.json <carpeta>/informe-reparacion.html`);
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
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'reparaciones', a.historia || 'suite');
  const datosArch = path.join(carpeta, 'reparaciones.json');
  const relRaiz = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  const guardar = (d) => { d.resumen = resumen(d); fs.writeFileSync(datosArch, JSON.stringify(d, null, 2), 'utf8'); };

  if (a.aplicar || a.verificar || a.soloInforme) {
    if (!fs.existsSync(datosArch)) throw new Error(`No hay un análisis en ${relRaiz(carpeta)}: corré primero npm run reparar sin opciones.`);
    const datos = JSON.parse(fs.readFileSync(datosArch, 'utf8'));
    if (a.aplicar) aplicar(carpeta, datos, a.aplicar);
    if (a.verificar) verificar(carpeta, datos);
    guardar(datos);
    if (generarInforme(carpeta)) console.log(`Informe: ${relRaiz(path.join(carpeta, 'informe-reparacion.html'))}`);
    return;
  }

  const origen = a.fallos ? desde(a.fallos) : (a.reporte ? desde(a.reporte) : path.resolve(K0, (process.env.REPORT_DIR || '').trim() || 'reports/web', 'cucumber-report.json')); // el mismo REPORT_DIR que npm test
  if (!fs.existsSync(origen)) throw new Error(`No encontré ${origen}. Corré primero npm test (o pasá --reporte / --fallos).`);
  const fallas = a.fallos ? fallasDeAnalista(origen, a.historia) : fallasDelReporte(origen, a.historia);
  archivar(carpeta, GENERADOS, 'reparaciones.json'); // la corrida anterior pasa a historial/ (últimas 5)
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });
  const dirCap = path.join(carpeta, 'capturas');
  fs.mkdirSync(dirCap, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');
  console.log(`Reparador · ${fallas.length} escenario(s) web con fallas${a.historia ? ` de ${a.historia}` : ''} · origen: ${relRaiz(origen)}`);
  const { chromium } = require('playwright');
  const browser = await navegadorComun.lanzar(chromium);
  const reparaciones = [];
  for (const [i, f] of fallas.entries()) {
    process.stdout.write(`[${i + 1}/${fallas.length}] ${f.caso || ''} ${f.escenario} `);
    const r = await analizarFalla(browser, f, a, dirCap, rel, i + 1);
    console.log(`→ ${r.diagnostico}${r.propuesta ? ` · propuesta ${r.propuesta.codigo} (confianza ${r.propuesta.confianza})` : ''}`);
    reparaciones.push(r);
  }
  await browser.close();
  const datos = { historia: a.historia || null, fecha: new Date().toISOString(), origen: relRaiz(origen), origen_tipo: a.fallos ? 'analista-fallos' : 'npm test',
    herramienta: `Playwright ${require('playwright/package.json').version}`, reparaciones };
  guardar(datos);
  const r = datos.resumen;
  console.log(`\nFallas: ${r.fallas} · de locator: ${r.de_locator} · con propuesta: ${r.con_propuesta} (confianza alta: ${r.confianza_alta}) · de espera: ${r.espera} · sin propuesta: ${r.sin_propuesta}`);
  console.log(`Datos: ${relRaiz(datosArch)}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${relRaiz(path.join(carpeta, 'informe-reparacion.html'))}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, locatorDelError, codigoDe, propuestasPara, reemplazarEnLinea, fallasDelReporte, GENERADOS };

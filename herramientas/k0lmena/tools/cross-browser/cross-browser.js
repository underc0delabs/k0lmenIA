// Pruebas cross-browser: Chromium (Chrome y Edge), Firefox y WebKit (Safari) (agente cross-browser).
//
// Uso (desde la raíz del repo):
//   npm run cross-browser -- [--modo suite|paginas] [--navegadores chromium,firefox,webkit]
//                            [--resoluciones 1366x768,390x844] [--tags "@HU-001"] [--historia HU-001]
//                            [--url https://mi-app.com] [--paginas url1,url2] [--max-paginas 6]
//                            [--base chromium] [--tolerancia-px 6] [--umbral 0.1] [--ocultar ".banner"] [--headed]
//                            [--reintentos 2]
//
// Dos modos (por defecto, suite si hay .feature en web/features; si no, páginas):
//   suite   → corre la suite web de k0lmena (npm test) una vez por navegador y resolución, cada una
//             en su carpeta (no pisa el último npm test), y arma la matriz escenario × navegador:
//             qué pasa en todos, qué falla en todos (no es un problema de navegador) y qué falla solo
//             en algunos (diferencia entre navegadores: lo que busca esta prueba). Corre contra el
//             ambiente como npm test: puede crear datos.
//   paginas → recorre las páginas del sitio en cada navegador y resolución (solo GET) y compara
//             contra el navegador base: errores de JavaScript, de consola y recursos que fallan solo
//             en un navegador, desborde horizontal, elementos que faltan o se corren, cambios de
//             estilo y porcentaje de la pantalla que se ve distinto.
//
// Contra los falsos positivos: lo que falla solo en un navegador se confirma antes de informarlo.
// En suite, el escenario se repite en ese navegador (--reintentos, 2 por defecto): si pasa, es
// "Inestable" y no una diferencia. En páginas, la página se recarga en todos los navegadores: si el
// error no se repite es intermitente, y si aparece en otro, se descarta. Además los errores se
// comparan por su origen y sus palabras propias (cada motor los redacta distinto), se ignora el ruido
// de consola de cada motor, se ocultan las barras de scroll y los corrimientos por la medida del texto
// pesan poco (importan si algo queda fuera de la pantalla).
//
// Los navegadores que no están instalados se informan con el comando para instalarlos
// (npx playwright install firefox webkit). WebKit es el motor de Safari; en Windows y Linux es una
// muy buena aproximación, pero no reemplaza probar en un Safari real de Mac o iPhone.
//
// Deja todo en output/cross-browser/<HU, host o suite>/ y cada corrida REEMPLAZA a la anterior:
// cross-browser.json, informe-cross-browser.html, capturas/, diferencias/, recortes/ y suite/.
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { archivar } = require('../historial/historial.js');
const { spawnSync } = require('child_process');
const { normalizar, slug, sello, recorrerScroll, cargar } = require('../explorador/explorar.js');
const { parsearResoluciones, descubrir } = require('../pixel-perfect/pixel-perfect.js');
const visual = require('../visual/comparar.js');

// Datos (output/, input/, .auth/) en el proyecto y scripts de Python en el código de k0lmenIA: ver ../rutas.js.
const { PROYECTO: RAIZ, CODIGO } = require('../rutas');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p); // npm run cambia el cwd a herramientas/k0lmena
const K0 = path.resolve(__dirname, '..', '..');
const GENERADOS = ['cross-browser.json', 'analisis.json', 'informe-cross-browser.html', 'capturas', 'diferencias', 'recortes', 'suite'];
const NAVEGADORES = ['chromium', 'firefox', 'webkit'];
const NOMBRE = { chromium: 'Chromium (Chrome, Edge)', firefox: 'Firefox', webkit: 'WebKit (Safari)' };
const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };

// ------------------------------------------------------------------ errores y recursos entre motores
// Cada motor redacta distinto el MISMO error: Chromium "Cannot read properties of undefined (reading
// 'total')", Firefox "can't access property \"total\", e is undefined", WebKit "undefined is not an
// object (evaluating 'e.total')". Comparar el texto exacto marcaba como "solo en Firefox" errores que
// pasan en todos. Se comparan por el lugar del código (archivo:línea:columna) o por las palabras
// propias del error (nombres de variables, propiedades y URLs), sin el vocabulario de cada motor.
const GENERICAS = new Set(('cannot can not read properties property access accessing undefined null is are of the to on in at for from with ' +
  'reading setting set get function object objects not defined uncaught error typeerror referenceerror syntaxerror rangeerror evaluating ' +
  'invalid unexpected token failed execute because was has been this that its value values type too much recursion maximum call stack ' +
  'size exceeded promise rejection unhandled script line column constructor instance assignment const variable before initialization ' +
  'lexical declaration').split(' '));

/** URL sin query ni hash: el mismo recurso con otro cache-buster es el mismo recurso. */
function claveRecurso(u) {
  try { const x = new URL(u); return `${x.origin}${x.pathname}`; } catch { return String(u).split(/[?#]/)[0]; }
}

/** Palabras propias de un mensaje de error (sin las genéricas de cada motor) y sus URLs. */
function tokensError(texto) {
  const s = new Set();
  const URLS = /(?:https?|file):\/\/[^\s'"`)]+/g;
  for (const u of String(texto).match(URLS) || []) s.add(claveRecurso(u.replace(/:\d+(:\d+)?$/, '')));
  for (const w of String(texto).replace(URLS, ' ').match(/[A-Za-z_$][\w$]*/g) || []) {
    const l = w.toLowerCase();
    if (l.length >= 3 && !GENERICAS.has(l)) s.add(l);
  }
  return s;
}

/** archivo:línea:columna del primer frame con URL de un stack (Chromium "at f (url:l:c)", Firefox/WebKit "f@url:l:c"). */
function origenDe(stack) {
  const m = String(stack || '').match(/((?:https?|file):\/\/[^\s)]+?):(\d+):(\d+)/);
  return m ? `${claveRecurso(m[1])}:${m[2]}:${m[3]}` : null;
}

/** ¿Son el mismo error (o mensaje de consola) en dos motores? */
function mismoError(a, b) {
  if (a.origen && b.origen && a.origen === b.origen) return true;
  if (a.mensaje === b.mensaje) return true;
  const ta = tokensError(a.mensaje);
  const tb = tokensError(b.mensaje);
  return [...ta].some((t) => tb.has(t));
}

// Mensajes de consola que dependen del motor y no de la app: no son incompatibilidades.
const RUIDO_CONSOLA = [
  /^Failed to load resource/i, // Chromium y WebKit lo escriben por cada recurso que falla (Firefox no); los recursos se revisan aparte
  /source ?map/i,
  /downloadable font/i,
  /^Cookie\b.*(rejected|expired|SameSite)/i,
  /Partitioned cookie|storage access/i,
  /Feature Policy|Permissions[- ]Policy/i,
  /Quirks Mode|Layout was forced|character encoding/i,
  /preload(ed)?\b.*\bnot used/i,
];
const esRuidoConsola = (t) => RUIDO_CONSOLA.some((r) => r.test(t));

// Pedidos cancelados (el navegador abortó la descarga: navegación, lazy load, precarga): no son fallas.
const esCancelado = (t) => /ABORT|cancel/i.test(String(t || ''));
// Recursos que cada navegador pide por su cuenta (Firefox pide /favicon.ico aunque la página no lo declare).
const esRecursoPropioDelNavegador = (u) => /\/favicon\.ico$|apple-touch-icon/i.test(claveRecurso(u)) || /^(data|blob):/i.test(u);

// Los errores de los dos motores (o de las dos recargas) se comparan en estos tipos de hallazgo.
const DE_EJECUCION = new Set(['Error de JavaScript', 'Error de consola', 'Recurso que falla', 'Respuesta distinta']);
const VISUALES = new Set(['Elemento faltante', 'Bloque desplazado', 'Elemento corrido', 'Estilo distinto', 'Se ve distinto']);

/** Distancia máxima por canal entre dos colores #rrggbb (o Infinity si alguno no es un color). */
function distanciaColor(a, b) {
  const p = (c) => (/^#[0-9a-f]{6}$/i.test(c) ? [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)) : null);
  const x = p(a);
  const y = p(b);
  if (!x || !y) return a === b ? 0 : Infinity;
  return Math.max(...x.map((v, i) => Math.abs(v - y[i])));
}

function argumentos(argv) {
  const a = { navegadores: NAVEGADORES, base: 'chromium', maxPaginas: 6, profundidad: 1, tolerancia: 6, umbral: 0.1, ocultar: [], headed: false, reintentos: 2 };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--modo') a.modo = v().toLowerCase();
    else if (k === '--navegadores') a.navegadores = v().split(',').map((x) => x.trim().toLowerCase()).filter(Boolean);
    else if (k === '--resoluciones') a.resoluciones = v();
    else if (k === '--tags') a.tags = v();
    else if (k === '--historia') a.historia = v();
    else if (k === '--url') a.url = v();
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--base') a.base = v().toLowerCase();
    else if (k === '--tolerancia-px') a.tolerancia = parseInt(v(), 10);
    else if (k === '--umbral') a.umbral = parseFloat(v());
    else if (k === '--ocultar') a.ocultar = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '--reintentos') a.reintentos = parseInt(v(), 10);
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  const malos = a.navegadores.filter((n) => !NAVEGADORES.includes(n));
  if (malos.length) throw new Error(`Navegador desconocido: ${malos.join(', ')}. Opciones: ${NAVEGADORES.join(', ')}.`);
  if (a.modo && !['suite', 'paginas'].includes(a.modo)) throw new Error('--modo: suite o paginas.');
  if (!a.navegadores.includes(a.base)) a.base = a.navegadores[0];
  if (!Number.isInteger(a.reintentos) || a.reintentos < 0 || a.reintentos > 5) throw new Error('--reintentos: un número de 0 a 5.');
  return a;
}

// ¿Está instalado y arranca? Devuelve la versión o el motivo.
async function probarNavegador(nombre) {
  const pw = require('playwright');
  try {
    const b = await pw[nombre].launch();
    const version = b.version();
    await b.close();
    return { nombre, ok: true, version };
  } catch (e) {
    const msg = String(e.message || e);
    const falta = /Executable doesn't exist|browserType\.launch.*install|Please run the following command/i.test(msg);
    return { nombre, ok: false, error: falta ? 'No está instalado' : msg.split('\n')[0].slice(0, 200),
      instalar: falta ? `cd herramientas/k0lmena && npx playwright install ${nombre}` : null };
  }
}

function hayFeatures() {
  const dir = path.join(K0, 'web', 'features');
  return fs.existsSync(dir) && fs.readdirSync(dir).some((f) => f.endsWith('.feature'));
}

// ------------------------------------------------------------------ modo suite
// Los errores de Playwright traen códigos de color de la terminal: se sacan para leerlos.
const sinAnsi = (s) => String(s).replace(/\x1b\[[0-9;]*m/g, '');

function leerCucumber(archivo) {
  let features = [];
  try { features = JSON.parse(fs.readFileSync(archivo, 'utf8') || '[]'); } catch { return []; }
  const salida = new Map();
  for (const f of features) {
    for (const esc of f.elements || []) {
      if (esc.type === 'background') continue;
      const tags = [...new Set([...(f.tags || []), ...(esc.tags || [])].map((t) => t.name.replace(/^@/, '')))];
      let estado = 'Aprobado';
      let paso = null;
      let error = '';
      let dur = 0;
      const capturas = [];
      for (const p of esc.steps || []) {
        const r = p.result || {};
        dur += r.duration || 0;
        const kw = (p.keyword || '').trim();
        if (r.status === 'failed' || r.status === 'ambiguous') {
          estado = 'Fallido';
          if (!paso) paso = `${kw} ${p.name || ''}`.trim();
          if (!error) error = sinAnsi(r.error_message || '').trim();
        } else if (['undefined', 'pending'].includes(r.status) && estado !== 'Fallido') {
          estado = 'Fallido';
          paso = paso || `${kw} ${p.name || ''}`.trim();
          error = error || `Paso ${r.status === 'undefined' ? 'sin definir' : 'pendiente'}`;
        } else if (r.status === 'skipped' && estado === 'Aprobado' && !['Before', 'After'].includes(kw)) estado = 'Salteado';
        for (const emb of p.embeddings || []) if (emb.mime_type === 'image/png') capturas.push(emb.data);
      }
      const clave = `${f.uri}:${esc.line}`;
      // Con retry, el mismo escenario aparece más de una vez: vale el último intento.
      salida.set(clave, { clave, escenario: esc.name, feature: f.name, uri: f.uri, linea: esc.line, tags,
        historia: tags.find((t) => /^HU-\d+$/i.test(t)) || null, caso: tags.find((t) => /^CP(-API)?-\d+$/.test(t)) || null,
        estado, paso, error: error.slice(0, 3000), duracion_s: Math.round(dur / 1e7) / 100, _captura: capturas[capturas.length - 1] });
    }
  }
  return [...salida.values()];
}

// cucumber-js con node directo (sin shell: los nombres de .feature con espacios o & no rompen nada).
function correrCucumber(env, extra = []) {
  let bin = null;
  try {
    const pkg = require.resolve('@cucumber/cucumber/package.json', { paths: [K0] });
    const b = require(pkg).bin;
    bin = path.join(path.dirname(pkg), typeof b === 'string' ? b : b['cucumber-js']);
  } catch { /* sin package.json exportado: se usa npx */ }
  const opciones = { cwd: K0, env, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 };
  if (bin && fs.existsSync(bin)) return spawnSync(process.execPath, [bin, '--profile', 'web', ...extra], opciones);
  return spawnSync('npx cucumber-js --profile web', { ...opciones, shell: true });
}

function envSuite(a, c, dir) {
  const env = { ...process.env, BROWSER: c.navegador, REPORT_DIR: dir, VIEWPORT_WIDTH: String(c.res.ancho),
    VIEWPORT_HEIGHT: String(c.res.alto), EVIDENCE: 'captura', HEADLESS: a.headed ? 'false' : 'true' };
  if (a.tags) env.TAGS = a.tags;
  return env;
}

function correrSuite(a, combos, carpeta, rel) {
  const dirSuite = path.join(carpeta, 'suite');
  const dirCap = path.join(carpeta, 'capturas');
  const corridas = [];
  for (const c of combos) {
    const dir = path.join(dirSuite, c.id);
    fs.mkdirSync(dir, { recursive: true });
    process.stdout.write(`Suite web en ${c.id.padEnd(18)} `);
    const t0 = Date.now();
    const r = correrCucumber(envSuite(a, c, dir));
    const escenarios = leerCucumber(path.join(dir, 'cucumber-report.json'));
    for (const e of escenarios) {
      if (e._captura) {
        const arch = path.join(dirCap, `${c.id}-${slug(`http://x/${e.caso || ''}-${e.escenario}`)}.png`);
        fs.writeFileSync(arch, Buffer.from(e._captura, 'base64'));
        e.captura = rel(arch);
      }
      delete e._captura;
    }
    const ap = escenarios.filter((e) => e.estado === 'Aprobado').length;
    const salida = `${r.stdout || ''}\n${r.stderr || ''}`;
    const fallaGeneral = !escenarios.length ? salida.trim().split(/\r?\n/).filter(Boolean).slice(-6).join('\n') : null;
    console.log(escenarios.length ? `→ ${ap}/${escenarios.length} aprobados (${Math.round((Date.now() - t0) / 1000)} s)` : '→ sin resultados');
    corridas.push({ ...c, res: c.res.id, escenarios, duracion_s: Math.round((Date.now() - t0) / 1000), error: fallaGeneral,
      reporte: fs.existsSync(path.join(dir, 'front-report.html')) ? rel(path.join(dir, 'front-report.html')) : null });
  }
  return corridas;
}

// Un escenario que falla solo en un navegador se repite ahí (a.reintentos veces, hasta que pase):
// una falla de una sola vez es inestabilidad (tiempos, datos, red), no una incompatibilidad.
// Guarda en cada escenario `reintentos`: el estado de cada repetición.
function confirmarSuite(a, combos, corridas, carpeta) {
  if (!a.reintentos) return 0;
  const { filas } = analizarSuite(corridas);
  let repetidos = 0;
  for (const f of filas.filter((x) => x.clase === 'Diferencia entre navegadores')) {
    for (const [comboId, r] of Object.entries(f.resultados)) {
      if (r.estado !== 'Fallido') continue;
      const c = combos.find((x) => x.id === comboId);
      const esc = corridas.find((x) => x.id === comboId).escenarios.find((e) => e.clave === f.clave);
      esc.reintentos = [];
      for (let i = 1; i <= a.reintentos; i++) {
        const dir = path.join(carpeta, 'suite', `${comboId}-repeticion`, String(repetidos + 1));
        fs.mkdirSync(dir, { recursive: true });
        process.stdout.write(`Repito en ${comboId.padEnd(18)} ${f.escenario.slice(0, 50)} (${i}/${a.reintentos}) `);
        correrCucumber(envSuite(a, c, dir), [`${f.uri}:${f.linea}`]);
        const otra = leerCucumber(path.join(dir, 'cucumber-report.json')).find((e) => e.clave === f.clave);
        const estado = otra ? otra.estado : 'Sin resultado';
        esc.reintentos.push(estado);
        repetidos++;
        console.log(`→ ${estado}`);
        if (estado === 'Aprobado') break;
      }
    }
  }
  return repetidos;
}

const comboTxt = (id) => { const [n, r] = id.split('-'); return `${NOMBRE[n] ? NOMBRE[n].split(' ')[0] : n} ${r || ''}`.trim(); };
const listaTxt = (ids) => ids.map(comboTxt).join(', ');

const POR_TIEMPO = /timeout|timed out|exceeded|tiempo de espera/i;

function analizarSuite(corridas) {
  const claves = new Map();
  for (const c of corridas) for (const e of c.escenarios) if (!claves.has(e.clave)) claves.set(e.clave, e);
  const filas = [];
  const hallazgos = [];
  for (const [clave, e0] of claves) {
    const res = {};
    for (const c of corridas) {
      const e = c.escenarios.find((x) => x.clave === clave);
      // Falló, pero pasó al repetirlo: inestable en ese navegador, no incompatible.
      const estado = e && e.estado === 'Fallido' && (e.reintentos || []).includes('Aprobado') ? 'Inestable' : e && e.estado;
      res[c.id] = e ? { estado, paso: e.paso, error: e.error, captura: e.captura, duracion_s: e.duracion_s, ...(e.reintentos ? { reintentos: e.reintentos } : {}) }
        : { estado: c.error ? 'Sin resultado' : 'No corrió' };
    }
    const estados = Object.values(res).map((x) => x.estado);
    const fallan = Object.entries(res).filter(([, x]) => x.estado === 'Fallido').map(([k]) => k);
    const pasan = Object.entries(res).filter(([, x]) => x.estado === 'Aprobado').map(([k]) => k);
    const inestables = Object.entries(res).filter(([, x]) => x.estado === 'Inestable').map(([k]) => k);
    let clase;
    if (estados.every((s) => s === 'Aprobado')) clase = 'Pasa en todos';
    else if (fallan.length && !pasan.length && !inestables.length) clase = 'Falla en todos';
    else if (fallan.length) clase = 'Diferencia entre navegadores';
    else if (inestables.length && estados.every((s) => s === 'Aprobado' || s === 'Inestable')) clase = 'Inestable';
    else clase = 'Sin resultado completo';
    filas.push({ clave, escenario: e0.escenario, feature: e0.feature, uri: e0.uri, linea: e0.linea, historia: e0.historia,
      caso: e0.caso, clase, resultados: res });
    const ident = [e0.historia, e0.caso].filter(Boolean).join(' · ');
    if (clase === 'Diferencia entre navegadores') {
      const err = res[fallan[0]];
      const pasanTodos = [...pasan, ...inestables];
      const repetido = fallan.every((k) => (res[k].reintentos || []).length);
      const porTiempo = POR_TIEMPO.test(err.error || '');
      const notas = [];
      if (repetido) notas.push(`Se repitió y volvió a fallar (${fallan.map((k) => `${comboTxt(k)}: ${res[k].reintentos.length + 1} de ${res[k].reintentos.length + 1}`).join(', ')}).`);
      else notas.push('Falló una sola vez: sin repetir no se sabe si es del navegador o inestable.');
      if (porTiempo) notas.push('Falla por tiempo de espera: puede ser que ese motor sea más lento (revisá las esperas del paso) y no una incompatibilidad.');
      hallazgos.push({ tipo: 'Falla solo en algunos navegadores', severidad: repetido && !porTiempo ? 'Alta' : 'Media', confirmado: repetido,
        titulo: `${ident ? `${ident} · ` : ''}${e0.escenario}: falla en ${listaTxt(fallan)} y pasa en ${listaTxt(pasanTodos)}`,
        detalle: `Paso que falla: ${err.paso || '—'}. ${(err.error || '').split('\n')[0].slice(0, 220)} ${notas.join(' ')}`.trim(),
        escenario: clave, fallan, pasan: pasanTodos, error: err.error, paso: err.paso,
        evidencias: [...fallan, ...pasanTodos.slice(0, 1)].map((k) => ({ combo: k, estado: res[k].estado, captura: res[k].captura })).filter((x) => x.captura) });
    } else if (clase === 'Inestable') {
      const err = res[inestables[0]];
      hallazgos.push({ tipo: 'Inestable', severidad: 'Baja', confirmado: false,
        titulo: `${ident ? `${ident} · ` : ''}${e0.escenario}: falló en ${listaTxt(inestables)} y pasó al repetirlo`,
        detalle: 'No es una diferencia entre navegadores: el escenario es inestable (tiempos, datos o red). Analizalo con el analista-fallos. ' +
          `Primer intento: ${err.paso || '—'}. ${(err.error || '').split('\n')[0].slice(0, 200)}`,
        escenario: clave, fallan: [], pasan: Object.keys(res), inestables, error: err.error, paso: err.paso,
        evidencias: inestables.map((k) => ({ combo: k, estado: 'Inestable', captura: res[k].captura })).filter((x) => x.captura) });
    } else if (clase === 'Falla en todos') {
      const err = res[fallan[0]];
      hallazgos.push({ tipo: 'Falla en todos los navegadores', severidad: 'Media',
        titulo: `${ident ? `${ident} · ` : ''}${e0.escenario}: falla en todos los navegadores`,
        detalle: 'No es una diferencia entre navegadores: es un bug o un test roto en cualquier navegador (analizalo con el analista-fallos). ' +
          `Paso: ${err.paso || '—'}. ${(err.error || '').split('\n')[0].slice(0, 200)}`,
        escenario: clave, fallan, pasan: [], error: err.error, paso: err.paso,
        evidencias: fallan.slice(0, 1).map((k) => ({ combo: k, estado: 'Fallido', captura: res[k].captura })).filter((x) => x.captura) });
    }
  }
  return { filas, hallazgos };
}

// ------------------------------------------------------------------ modo páginas
// Contexto de cada combinación. Firefox no soporta isMobile: en mobile solo emula el tamaño y la
// pantalla táctil, y sus diferencias visuales en mobile pesan menos (ver analizarPaginas).
function opcionesContexto(c) {
  const movil = c.res.ancho < 768;
  return { viewport: { width: c.res.ancho, height: c.res.alto }, deviceScaleFactor: 1, locale: process.env.LOCALE || 'es-AR',
    ...(movil ? { hasTouch: true, ...(c.navegador !== 'firefox' ? { isMobile: true } : {}) } : {}) };
}

// Lo que pasa al ejecutar la página: errores de JavaScript (con el lugar del código), de consola
// (sin el ruido propio de cada motor), recursos que fallan y qué recursos se pidieron.
function escuchar(page, m) {
  m._errores = [];
  m._consola = [];
  m._fallidos = [];
  m._pedidos = new Set();
  page.on('pageerror', (e) => m._errores.push({ mensaje: String(e.message || e).split('\n')[0].slice(0, 300), origen: origenDe(e.stack) }));
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const mensaje = msg.text().slice(0, 300);
    if (esRuidoConsola(mensaje)) return;
    const loc = msg.location() || {};
    m._consola.push({ mensaje, origen: loc.url ? `${claveRecurso(loc.url)}:${loc.lineNumber}:${loc.columnNumber}` : null });
  });
  page.on('request', (rq) => m._pedidos.add(claveRecurso(rq.url())));
  page.on('requestfailed', (rq) => {
    const f = rq.failure();
    if (f && !esCancelado(f.errorText) && !esRecursoPropioDelNavegador(rq.url())) m._fallidos.push({ url: rq.url(), error: f.errorText });
  });
  page.on('response', (rs) => {
    if (rs.status() >= 400 && rs.request().resourceType() !== 'document' && !esRecursoPropioDelNavegador(rs.url())) {
      m._fallidos.push({ url: rs.url(), error: `HTTP ${rs.status()}` });
    }
  });
}

// Deja en m lo escuchado, sin repetidos (los detalles para comparar y los textos para el informe).
function cerrarEscucha(m) {
  const unicos = (xs) => [...new Map(xs.map((x) => [x.mensaje, x])).values()];
  m.errores_js_det = unicos(m._errores);
  m.errores_consola_det = unicos(m._consola);
  m.errores_js = m.errores_js_det.map((x) => x.mensaje);
  m.errores_consola = m.errores_consola_det.map((x) => x.mensaje);
  m.recursos_fallidos = [...new Map(m._fallidos.map((r) => [claveRecurso(r.url), r])).values()];
  delete m._errores; delete m._consola; delete m._fallidos;
}

// Abre la página en un contexto nuevo y mide solo lo de ejecución (para la recarga de confirmación).
async function medirEjecucion(browser, c, u) {
  const ctx = await browser.newContext(opcionesContexto(c));
  const m = { url: u, combo: c.id };
  try {
    const page = await ctx.newPage();
    escuchar(page, m);
    const { resp } = await cargar(page, u);
    m.status = resp ? resp.status() : 0;
    await recorrerScroll(page);
  } catch (e) {
    m.error = String(e.message || e).split('\n')[0].slice(0, 200);
  } finally {
    if (m._errores) cerrarEscucha(m);
    await ctx.close().catch(() => {});
  }
  return m;
}

async function recorrerPaginas(a, combos, paginas, carpeta, rel) {
  const pw = require('playwright');
  const dirCap = path.join(carpeta, 'capturas');
  const medidas = {}; // `${pagina}|${combo}` → datos
  for (const c of combos) {
    const browser = await navegadorComun.lanzar(pw[c.navegador], { headless: !a.headed });
    try {
      for (const [i, u] of paginas.entries()) {
        const id = `${String(i + 1).padStart(2, '0')}-${slug(u)}`;
        process.stdout.write(`[${c.id.padEnd(18)}] ${u} `);
        const ctx = await browser.newContext(opcionesContexto(c));
        const page = await ctx.newPage();
        const m = { pagina: id, url: u, combo: c.id, navegador: c.navegador, resolucion: c.res.id };
        escuchar(page, m);
        try {
          const { resp, ms } = await cargar(page, u);
          m.status = resp ? resp.status() : 0;
          m.tiempo_ms = ms;
          // Mismo ancho útil en todos los motores (ver CSS_SIN_SCROLLBAR).
          await page.addStyleTag({ content: visual.CSS_SIN_SCROLLBAR }).catch(() => {});
          await recorrerScroll(page);
          await page.evaluate(() => window.scrollTo(0, 0));
          await visual.estabilizar(page, { ocultar: a.ocultar });
          const med = await visual.medirElementos(page);
          m.elementos = med.elementos;
          m.alto = med.alto;
          m.desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
          const arch = path.join(dirCap, `${id}-${c.id}.png`);
          const alto = Math.min(med.alto, 10000);
          await page.screenshot({ path: arch, fullPage: alto === med.alto, timeout: 30000,
            ...(alto < med.alto ? { clip: { x: 0, y: 0, width: c.res.ancho, height: alto } } : {}) });
          m.captura = rel(arch);
          m._archivo = arch;
          console.log(`→ ${m.status} · ${m._errores.length} error(es) JS`);
        } catch (e) {
          m.error = String(e.message || e).split('\n')[0].slice(0, 200);
          console.log(`→ error: ${m.error}`);
        }
        cerrarEscucha(m);
        medidas[`${id}|${c.id}`] = m;
        await ctx.close().catch(() => {});
      }
    } finally {
      await browser.close().catch(() => {});
    }
  }
  return medidas;
}

const textoEl = (e) => (e.texto ? `“${e.texto.slice(0, 50)}”` : e.desc);
const caja = (e) => ({ x: e.x, y: e.y, w: e.w, h: e.h });
const bajarA = (sev, tope) => (SEV_ORDEN[sev] < SEV_ORDEN[tope] ? tope : sev);

function analizarPaginas(a, combos, paginas, medidas, carpeta, rel) {
  const dirDif = path.join(carpeta, 'diferencias');
  const dirRec = path.join(carpeta, 'recortes');
  const hallazgos = [];
  const filas = [];
  const resols = [...new Set(combos.map((c) => c.res.id))];
  for (const [i, u] of paginas.entries()) {
    const id = `${String(i + 1).padStart(2, '0')}-${slug(u)}`;
    for (const res of resols) {
      const cs = combos.filter((c) => c.res.id === res);
      const base = cs.find((c) => c.navegador === a.base) || cs[0];
      const mb = medidas[`${id}|${base.id}`];
      const fila = { pagina: id, url: u, resolucion: res, base: base.id, resultados: {} };
      for (const c of cs) {
        const m = medidas[`${id}|${c.id}`];
        const r = { estado: 'OK', captura: m && m.captura, errores_js: m ? m.errores_js.length : 0, desborde: m ? m.desborde : null,
          tiempo_ms: m && m.tiempo_ms, status: m && m.status };
        fila.resultados[c.id] = r;
        if (!m || m.error) { r.estado = 'Error'; r.error = m ? m.error : 'sin datos'; continue; }
        // Solo se compara contra los navegadores que cargaron la página: si uno no cargó, lo del
        // resto no pasa a ser "exclusivo".
        const otros = cs.filter((x) => x.id !== c.id).map((x) => medidas[`${id}|${x.id}`]).filter((x) => x && !x.error);
        if (!otros.length) continue;
        const movilFirefox = c.navegador === 'firefox' && c.res.ancho < 768;
        const propios = [];
        const h = (x) => {
          if (movilFirefox && VISUALES.has(x.tipo)) {
            x.severidad = 'Baja';
            x.detalle += ' Firefox no emula un teléfono (sin isMobile): puede mostrar partes de la versión de escritorio. Confirmalo en Firefox para Android antes de reportarlo.';
          }
          propios.push(x);
          hallazgos.push({ pagina: id, url: u, resolucion: res, navegador: c.navegador, combo: c.id, ...x });
        };

        // Errores de JavaScript y de consola: exclusivos si ningún otro motor tuvo el mismo error
        // (mismo lugar del código o mismas palabras propias). Si los otros también tuvieron errores
        // sin pareja, puede ser el mismo con otro mensaje: pesa menos.
        const revisarErrores = (campo, tipo, severidad) => {
          const deOtros = otros.flatMap((o) => o[campo] || []);
          const sinPar = (m[campo] || []).filter((e) => !deOtros.some((x) => mismoError(e, x)));
          const otrosSinPar = deOtros.filter((x) => !(m[campo] || []).some((e) => mismoError(e, x)));
          for (const err of sinPar.slice(0, 5)) {
            const dudoso = otrosSinPar.length > 0;
            h({ tipo, severidad: dudoso ? 'Baja' : severidad, titulo: `${tipo} solo en ${NOMBRE[c.navegador]}`,
              detalle: err.mensaje + (dudoso ? ' (Los otros navegadores también tuvieron errores en esta página con otro texto: puede ser el mismo error redactado por otro motor.)' : ''),
              error_det: err, captura: m.captura });
          }
        };
        revisarErrores('errores_js_det', 'Error de JavaScript', 'Alta');
        revisarErrores('errores_consola_det', 'Error de consola', 'Media');

        // Recursos: falla en este y otro navegador lo cargó bien → del navegador. Si ningún otro lo
        // pidió, cada motor eligió otro archivo (srcset, formato de fuente, precarga): pesa menos.
        for (const rf of m.recursos_fallidos.slice(0, 8)) {
          const k = claveRecurso(rf.url);
          const fallaEn = (o) => o.recursos_fallidos.some((x) => claveRecurso(x.url) === k);
          if (otros.every(fallaEn)) continue;
          const nadieMasLoPidio = otros.every((o) => o._pedidos && !o._pedidos.has(k));
          h({ tipo: 'Recurso que falla', severidad: nadieMasLoPidio ? 'Baja' : 'Media', titulo: `No carga en ${NOMBRE[c.navegador]}: ${k.split('/').pop() || k}`,
            detalle: `${rf.url} → ${rf.error}` + (nadieMasLoPidio ? ' (Los otros navegadores no pidieron este archivo: cada motor elige su versión de imágenes, fuentes o precargas.)' : ''),
            recurso: k, captura: m.captura });
        }

        const otrosDesb = otros.map((x) => x.desborde || 0);
        if (m.desborde > 4 && otrosDesb.some((d) => d <= 4)) {
          h({ tipo: 'Desborde horizontal', severidad: 'Media', titulo: `La página se sale ${m.desborde} px de ancho solo en ${NOMBRE[c.navegador]}`,
            detalle: 'Aparece scroll horizontal en este navegador y no en los demás: un elemento se renderiza más ancho.', captura: m.captura });
        }
        if (m.status && mb && !mb.error && mb.status && m.status !== mb.status) {
          const bloqueo = [403, 429, 503].includes(m.status);
          h({ tipo: 'Respuesta distinta', severidad: bloqueo ? 'Media' : 'Alta', titulo: `Responde ${m.status} en ${NOMBRE[c.navegador]} y ${mb.status} en ${NOMBRE[base.navegador]}`,
            detalle: bloqueo
              ? 'Puede ser una protección contra robots (Cloudflare, WAF) que bloquea a ese navegador automatizado, no a las personas: confirmalo a mano.'
              : 'El servidor responde distinto según el navegador (detección de user agent).',
            status_nav: m.status, captura: m.captura });
        }
        if (c.id !== base.id && mb && !mb.error && m._archivo && mb._archivo) {
          const cmp = visual.compararPng(mb._archivo, m._archivo, { umbral: a.umbral });
          const dif = path.join(dirDif, `${id}-${c.id}.png`);
          fs.writeFileSync(dif, cmp.diff);
          r.pct = cmp.pct;
          r.diferencia = rel(dif);
          const el = visual.compararElementos(mb.elementos, m.elementos, { tolerancia: a.tolerancia });
          const nombreNav = NOMBRE[c.navegador];
          const conRecorte = (x, cajaBase, cajaNav) => {
            const cajas = [cajaBase, cajaNav].filter(Boolean);
            const v = visual.ventanaDe(cajas, 70);
            const pref = path.join(dirRec, `${id}-${c.id}-${hallazgos.length + 1}`);
            if (cajaBase) { fs.writeFileSync(`${pref}-base.png`, visual.recorteMarcado(mb._archivo, v, cajaBase)); x.base_captura = rel(`${pref}-base.png`); }
            if (cajaNav) { fs.writeFileSync(`${pref}-nav.png`, visual.recorteMarcado(m._archivo, v, cajaNav, [20, 168, 149])); x.nav_captura = rel(`${pref}-nav.png`); }
            return x;
          };
          for (const f of filtrarFaltantes(el.faltantes, m.elementos).filter((x) => ['a', 'button', 'input', 'select', 'textarea', 'img', 'h1', 'h2', 'h3', 'form'].includes(x.tag)).slice(0, 8)) {
            h(conRecorte({ tipo: 'Elemento faltante', severidad: ['a', 'button', 'input', 'select', 'textarea', 'form'].includes(f.tag) ? 'Alta' : 'Media',
              titulo: `${textoEl(f)} no aparece en ${nombreNav}`, detalle: `${f.desc} está en ${NOMBRE[base.navegador]} y no se ve en ${nombreNav}.` }, caja(f), null));
          }
          // Corrimientos: cada motor mide distinto el texto (fuentes, interlineado, suavizado), así que
          // lo que se corre unos píxeles es normal. Importa cuando queda fuera de la pantalla.
          const fuera = (e) => e.x + e.w > c.res.ancho + 2 || e.x < -2;
          for (const b of el.bloques.filter((x) => Math.hypot(x.dx, x.dy) >= 12).slice(0, 3)) {
            h(conRecorte({ tipo: 'Bloque desplazado', severidad: 'Baja',
              titulo: `${b.elementos} elementos desplazados ${b.dx ? `${b.dx} px en X ` : ''}${b.dy ? `${b.dy} px en Y` : ''} en ${nombreNav}`,
              detalle: `Desde ${textoEl(b.desde)}: algo de arriba se renderiza con otro tamaño en ${nombreNav}. Suele ser la medida del texto en cada motor; importa si tapa o corta algo.` }, caja(b.desde),
            { ...caja(b.desde), x: b.desde.x + b.dx, y: b.desde.y + b.dy }));
          }
          for (const mv of el.movidos.filter((x) => Math.hypot(x.dx, x.dy) >= 12).slice(0, 8)) {
            const saleDePantalla = fuera(mv.actual) && !fuera(mv);
            h(conRecorte({ tipo: 'Elemento corrido', severidad: saleDePantalla ? 'Alta' : bajarA(mv.severidad, 'Media'),
              titulo: saleDePantalla
                ? `${textoEl(mv)} queda fuera de la pantalla en ${nombreNav}`
                : `${textoEl(mv)} se corre ${mv.dx >= 0 ? '+' : ''}${mv.dx} px en X y ${mv.dy >= 0 ? '+' : ''}${mv.dy} px en Y en ${nombreNav}`,
              detalle: `${mv.desc}: (${mv.x}, ${mv.y}) en ${NOMBRE[base.navegador]} y (${mv.actual.x}, ${mv.actual.y}) en ${nombreNav}.`,
              delta: { dx: mv.dx, dy: mv.dy, dw: mv.dw, dh: mv.dh } }, caja(mv), caja(mv.actual)));
          }
          // Colores: los motores convierten y redondean distinto; menos de 8 por canal no se ve.
          for (const s of (el.estilos || []).filter((x) => (x.prop === 'fondo' || x.prop === 'color') && distanciaColor(x.de, x.a) > 8).slice(0, 4)) {
            const ej = s.elementos[0];
            h(conRecorte({ tipo: 'Estilo distinto', severidad: 'Media', titulo: `${s.elementos.length === 1 ? textoEl(ej) : `${s.elementos.length} elementos`}: ${s.nombre} ${s.de} → ${s.a} en ${nombreNav}`,
              detalle: `El ${s.nombre} se calcula distinto en ${nombreNav} (una propiedad CSS no soportada o con otro valor por defecto).`,
              estilo: { propiedad: s.prop, de: s.de, a: s.a } }, caja(ej), caja(ej.actual)));
          }
          if (cmp.pct > 15 && !propios.some((x) => ['Elemento faltante', 'Bloque desplazado', 'Elemento corrido'].includes(x.tipo))) {
            h({ tipo: 'Se ve distinto', severidad: 'Baja', titulo: `El ${cmp.pct} % de la pantalla se ve distinto en ${nombreNav}`,
              detalle: 'Cambia el renderizado (fuentes, suavizado, imágenes o estilos) aunque los elementos estén en su lugar: es normal entre motores; mirá las capturas solo si algo se ve roto.',
              captura: m.captura, base_captura: mb.captura, nav_captura: m.captura });
          }
        }
        if (propios.some((x) => SEV_ORDEN[x.severidad] <= 1)) r.estado = 'Con problemas';
        else if (propios.length) r.estado = 'Diferencias menores';
        r.hallazgos = propios.length;
      }
      filas.push(fila);
    }
  }
  for (const k of Object.keys(medidas)) { delete medidas[k]._archivo; delete medidas[k].elementos; delete medidas[k]._pedidos; }
  return { filas, hallazgos };
}

// Un elemento "falta" solo si en el otro navegador no hay ninguno con la misma etiqueta y el mismo
// texto: las claves se numeran por orden de aparición y un elemento de más arriba corre la numeración.
function filtrarFaltantes(faltantes, elementosNav) {
  const hay = new Set(elementosNav.filter((e) => e.texto).map((e) => `${e.tag}|${e.texto}`));
  return faltantes.filter((f) => !(f.texto && hay.has(`${f.tag}|${f.texto}`)));
}

// ¿El hallazgo de ejecución aparece en esta medición?
function aparece(hz, m) {
  if (!m || m.error) return false;
  if (hz.tipo === 'Error de JavaScript') return m.errores_js_det.some((x) => mismoError(hz.error_det, x));
  if (hz.tipo === 'Error de consola') return m.errores_consola_det.some((x) => mismoError(hz.error_det, x));
  if (hz.tipo === 'Recurso que falla') return m.recursos_fallidos.some((x) => claveRecurso(x.url) === hz.recurso);
  if (hz.tipo === 'Respuesta distinta') return m.status === hz.status_nav;
  return true;
}

// Los errores, recursos y respuestas que salieron solo en un navegador se confirman recargando la
// página en todos los navegadores de esa resolución: si no se repite, era intermitente (red,
// tiempos); si ahora aparece también en otro, no era del navegador.
async function confirmarPaginas(a, combos, hallazgos) {
  const aConfirmar = hallazgos.filter((hz) => DE_EJECUCION.has(hz.tipo) && hz.severidad !== 'Baja');
  if (!aConfirmar.length || !a.reintentos) return { confirmados: 0, intermitentes: 0, descartados: [] };
  const pantallas = new Map(); // `${url}|${resolucion}` → combos de esa resolución
  for (const hz of aConfirmar) pantallas.set(`${hz.url}|${hz.resolucion}`, combos.filter((c) => c.res.id === hz.resolucion));
  const nuevas = {};
  const pw = require('playwright');
  for (const nav of [...new Set(combos.map((c) => c.navegador))]) {
    const browser = await navegadorComun.lanzar(pw[nav], { headless: !a.headed });
    try {
      for (const [clave, cs] of pantallas) {
        const url = clave.slice(0, clave.lastIndexOf('|'));
        for (const c of cs.filter((x) => x.navegador === nav)) {
          process.stdout.write(`Confirmo [${c.id.padEnd(18)}] ${url} `);
          const m = await medirEjecucion(browser, c, url);
          nuevas[`${url}|${c.id}`] = m;
          console.log(m.error ? `→ error: ${m.error}` : '→ ok');
        }
      }
    } finally {
      await browser.close().catch(() => {});
    }
  }
  return aplicarConfirmacion(aConfirmar, combos, nuevas, hallazgos);
}

// Separado de confirmarPaginas para poder probarlo sin navegador.
function aplicarConfirmacion(aConfirmar, combos, nuevas, hallazgos) {
  const descartados = [];
  let confirmados = 0;
  let intermitentes = 0;
  for (const hz of aConfirmar) {
    const otra = nuevas[`${hz.url}|${hz.combo}`];
    if (!otra || otra.error) continue; // sin segunda medición, queda como estaba
    const otros = combos.filter((c) => c.res.id === hz.resolucion && c.id !== hz.combo).map((c) => nuevas[`${hz.url}|${c.id}`]);
    if (!aparece(hz, otra)) {
      hz.confirmado = false;
      hz.severidad = 'Baja';
      hz.detalle += ' No se repitió al recargar la página: probablemente fue intermitente (red o tiempos), no del navegador.';
      intermitentes++;
    } else if (otros.some((o) => aparece(hz, o))) {
      descartados.push(hz);
    } else {
      hz.confirmado = true;
      hz.detalle += ' Confirmado: se repitió al recargar y no apareció en los otros navegadores.';
      confirmados++;
    }
  }
  for (const d of descartados) hallazgos.splice(hallazgos.indexOf(d), 1);
  return { confirmados, intermitentes, descartados: descartados.map((d) => ({ tipo: d.tipo, navegador: d.navegador, url: d.url, detalle: d.detalle,
    motivo: 'Al recargar también apareció en otro navegador: no es del navegador.' })) };
}

// El mismo error (o recurso) en varias páginas y resoluciones es un solo hallazgo con la lista de
// pantallas donde aparece: suele ser una sola causa (un script o un estilo de la plantilla).
const AGRUPABLES = new Set(['Error de JavaScript', 'Error de consola', 'Recurso que falla', 'Respuesta distinta']);
function agrupar(hallazgos) {
  const salida = [];
  const grupos = new Map();
  for (const h of hallazgos) {
    if (!h.pagina) { salida.push(h); continue; }
    const pantalla = { pagina: h.pagina, url: h.url, resolucion: h.resolucion, combo: h.combo, captura: h.captura };
    if (!AGRUPABLES.has(h.tipo)) { salida.push({ ...h, pantallas: [pantalla] }); continue; }
    const k = `${h.tipo}|${h.navegador}|${h.detalle}`;
    if (!grupos.has(k)) { const g = { ...h, pantallas: [] }; grupos.set(k, g); salida.push(g); }
    grupos.get(k).pantallas.push(pantalla);
  }
  for (const g of grupos.values()) {
    const urls = new Set(g.pantallas.map((p) => p.url));
    if (g.pantallas.length > 1) g.titulo += ` · ${urls.size} página(s), ${g.pantallas.length} pantalla(s)`;
  }
  return salida;
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = spawnSync(py, [path.join(CODIGO, 'scripts', 'generar_informe_cross_browser.py'),
    path.join(carpeta, 'cross-browser.json'), path.join(carpeta, 'informe-cross-browser.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_cross_browser.py ` +
      '<carpeta>/cross-browser.json <carpeta>/informe-cross-browser.html');
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
  const modo = a.modo || (hayFeatures() ? 'suite' : 'paginas');
  if (modo === 'suite' && !hayFeatures()) throw new Error('No hay escenarios en herramientas/k0lmena/web/features: automatizá primero (web-mapper) o usá --modo paginas.');
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  let inicio = null;
  let host = null;
  if (modo === 'paginas') {
    const url = a.url || (a.paginas && a.paginas[0]) || process.env.APP_URL || process.env.BASEURL;
    if (!url) throw new Error('No hay URL: pasala con --url o definí APP_URL en el .env de la raíz.');
    if (!/^https?:\/\//i.test(url)) throw new Error(`La URL tiene que empezar con http:// o https:// (recibí "${url}").`);
    inicio = normalizar(url);
    host = new URL(inicio).hostname;
  }
  if (modo === 'suite' && a.historia && !a.tags) a.tags = `@${a.historia}`;
  const nombre = a.historia || (modo === 'paginas' ? host : 'suite');
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'cross-browser', nombre);
  archivar(carpeta, GENERADOS, 'cross-browser.json'); // la corrida anterior pasa a historial/ (últimas 5)
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });
  for (const d of ['capturas', 'diferencias', 'recortes']) fs.mkdirSync(path.join(carpeta, d), { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');
  const relRaiz = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  const t0 = Date.now();

  console.log(`Cross-browser · modo ${modo} · navegadores: ${a.navegadores.join(', ')}`);
  const navegadores = [];
  for (const n of a.navegadores) navegadores.push(await probarNavegador(n));
  for (const n of navegadores) console.log(`  ${n.nombre.padEnd(9)} ${n.ok ? `OK (${n.version})` : `${n.error}${n.instalar ? ` → ${n.instalar}` : ''}`}`);
  const disponibles = navegadores.filter((n) => n.ok).map((n) => n.nombre);
  if (!disponibles.length) throw new Error('Ningún navegador disponible. Instalalos con: cd herramientas/k0lmena && npx playwright install chromium firefox webkit');
  if (!disponibles.includes(a.base)) a.base = disponibles[0];
  const resoluciones = parsearResoluciones(a.resoluciones || (modo === 'suite' ? '1366x768' : '1366x768,390x844'));
  const combos = [];
  for (const res of resoluciones) for (const n of disponibles) combos.push({ id: `${n}-${res.id}`, navegador: n, res });
  console.log(`Salida: ${relRaiz(carpeta)} (reemplaza la corrida anterior)`);

  let datos;
  if (modo === 'suite') {
    const corridas = correrSuite(a, combos, carpeta, rel);
    const repetidos = confirmarSuite(a, combos, corridas, carpeta);
    const { filas, hallazgos } = analizarSuite(corridas);
    const cuenta = (c) => filas.filter((f) => f.clase === c).length;
    datos = { corridas: corridas.map((c) => ({ id: c.id, navegador: c.navegador, resolucion: c.res, duracion_s: c.duracion_s, error: c.error,
      reporte: c.reporte, aprobados: c.escenarios.filter((e) => e.estado === 'Aprobado').length,
      fallidos: c.escenarios.filter((e) => e.estado === 'Fallido').length, total: c.escenarios.length })),
    escenarios: filas, hallazgos,
    resumen: { escenarios: filas.length, pasan_en_todos: cuenta('Pasa en todos'), diferencias: cuenta('Diferencia entre navegadores'),
      fallan_en_todos: cuenta('Falla en todos'), inestables: cuenta('Inestable'), incompletos: cuenta('Sin resultado completo'),
      repeticiones: repetidos, confirmados: hallazgos.filter((h) => h.confirmado).length } };
  } else {
    const pw = require('playwright');
    const b = await navegadorComun.lanzar(pw[a.base]);
    const ctx = await b.newContext();
    const paginas = await descubrir(await ctx.newPage(), inicio, a);
    await b.close();
    console.log(`${paginas.length} página(s) × ${combos.length} combinación(es) de navegador y resolución`);
    const medidas = await recorrerPaginas(a, combos, paginas, carpeta, rel);
    const { filas, hallazgos } = analizarPaginas(a, combos, paginas, medidas, carpeta, rel);
    const confirmacion = await confirmarPaginas(a, combos, hallazgos);
    const conProblemas = filas.filter((f) => Object.values(f.resultados).some((r) => r.estado === 'Con problemas')).length;
    const pcts = filas.flatMap((f) => Object.values(f.resultados).map((r) => r.pct).filter((x) => x != null));
    datos = { paginas: filas, medidas: Object.values(medidas), hallazgos,
      resumen: { paginas: paginas.length, pantallas: filas.length, comparaciones: pcts.length,
        sin_diferencias: filas.filter((f) => Object.values(f.resultados).every((r) => r.estado === 'OK')).length,
        con_problemas: conProblemas, pct_max: pcts.length ? Math.max(...pcts) : 0, pct_prom: pcts.length ? Math.round(pcts.reduce((s, x) => s + x, 0) / pcts.length * 100) / 100 : 0,
        errores_js_exclusivos: hallazgos.filter((h) => h.tipo === 'Error de JavaScript' && h.severidad !== 'Baja').length,
        confirmados: confirmacion.confirmados, intermitentes: confirmacion.intermitentes, descartados_al_confirmar: confirmacion.descartados.length },
      descartados: confirmacion.descartados };
  }
  for (const h of datos.hallazgos) { delete h.error_det; delete h.status_nav; }
  datos.hallazgos = agrupar(datos.hallazgos);
  datos.hallazgos.sort((x, y) => SEV_ORDEN[x.severidad] - SEV_ORDEN[y.severidad] || (y.pantallas || []).length - (x.pantallas || []).length);
  datos.hallazgos.forEach((h, i) => { h.id = `X-${String(i + 1).padStart(2, '0')}`; });
  const porNav = {};
  for (const n of disponibles) porNav[n] = datos.hallazgos.filter((h) => (h.navegador ? h.navegador === n : (h.fallan || []).some((f) => f.startsWith(n)))).length;
  const resultado = {
    modo, url: inicio, host, historia: a.historia || null, tags: a.tags || null, fecha: new Date().toISOString(), marca: sello(),
    duracion_s: Math.round((Date.now() - t0) / 1000), base: a.base, herramienta: `Playwright ${require('playwright/package.json').version}`,
    navegadores: navegadores.map((n) => ({ ...n, titulo: NOMBRE[n.nombre] })), resoluciones: resoluciones.map((r) => r.id),
    config: { tolerancia_px: a.tolerancia, umbral: a.umbral, ocultar: a.ocultar },
    ...datos,
  };
  resultado.resumen.hallazgos = datos.hallazgos.length;
  resultado.resumen.por_navegador = porNav;
  resultado.resumen.por_severidad = Object.fromEntries(['Crítica', 'Alta', 'Media', 'Baja'].map((s) => [s, datos.hallazgos.filter((h) => h.severidad === s).length]));
  resultado.resumen.no_instalados = navegadores.filter((n) => !n.ok).map((n) => n.nombre);
  const salida = path.join(carpeta, 'cross-browser.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  const r = resultado.resumen;
  if (modo === 'suite') console.log(`\nEscenarios: ${r.escenarios} · pasan en todos: ${r.pasan_en_todos} · diferencias entre navegadores: ${r.diferencias} · inestables: ${r.inestables} · fallan en todos: ${r.fallan_en_todos}`);
  else console.log(`\nPantallas: ${r.pantallas} · sin diferencias: ${r.sin_diferencias} · con problemas: ${r.con_problemas} · hallazgos: ${r.hallazgos} (confirmados al recargar: ${r.confirmados}, intermitentes: ${r.intermitentes}, descartados: ${r.descartados_al_confirmar})`);
  console.log(`Datos: ${relRaiz(salida)}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${relRaiz(path.join(carpeta, 'informe-cross-browser.html'))}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, leerCucumber, analizarSuite, analizarPaginas, aplicarConfirmacion, filtrarFaltantes, sinAnsi, NOMBRE, GENERADOS,
  claveRecurso, tokensError, origenDe, mismoError, esRuidoConsola, esCancelado, esRecursoPropioDelNavegador, distanciaColor, opcionesContexto };

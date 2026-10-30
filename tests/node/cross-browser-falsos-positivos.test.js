// Tests del cross-browser contra los falsos positivos: el mismo error redactado por cada motor, el
// ruido de consola, los recursos que cada navegador pide distinto, las repeticiones de la suite y la
// recarga de confirmación de las páginas. Sin navegador: se prueban las funciones de análisis.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');

const K0 = path.resolve(__dirname, '..', '..', 'herramientas/k0lmena');
const cross = require(path.join(K0, 'tools/cross-browser/cross-browser.js'));
const { slug } = require(path.join(K0, 'tools/explorador/explorar.js'));
const PAGINA = `01-${slug('https://app.test/')}`;

const CHROMIUM = { mensaje: "Cannot read properties of undefined (reading 'total')", origen: 'https://app.test/app.js:1:2045' };
const FIREFOX = { mensaje: "can't access property \"total\", e is undefined", origen: 'https://app.test/app.js:1:2045' };
const WEBKIT = { mensaje: "undefined is not an object (evaluating 'e.total')", origen: null };

test('cross-browser: el mismo error redactado por cada motor es el mismo error', () => {
  assert.ok(cross.mismoError(CHROMIUM, FIREFOX), 'mismo origen');
  assert.ok(cross.mismoError({ ...CHROMIUM, origen: null }, WEBKIT), 'misma propiedad: total');
  assert.ok(!cross.mismoError(CHROMIUM, { mensaje: "Cannot read properties of null (reading 'items')", origen: null }));
  assert.deepEqual([...cross.tokensError("Cannot read properties of undefined (reading 'total')")], ['total']);
  assert.equal(cross.origenDe('TypeError: x\n    at pagar (https://app.test/app.js?v=3:10:5)'), 'https://app.test/app.js:10:5');
  assert.equal(cross.origenDe('pagar@https://app.test/app.js:10:5\n'), 'https://app.test/app.js:10:5');
});

test('cross-browser: ruido de consola, cancelaciones y recursos propios del navegador', () => {
  assert.ok(cross.esRuidoConsola('Failed to load resource: the server responded with a status of 404 (Not Found)'));
  assert.ok(cross.esRuidoConsola('Source map error: request failed with status 404'));
  assert.ok(!cross.esRuidoConsola('Uncaught (in promise) Error: pago rechazado'));
  for (const t of ['net::ERR_ABORTED', 'NS_BINDING_ABORTED', 'NS_ERROR_ABORT', 'Load request cancelled']) assert.ok(cross.esCancelado(t), t);
  assert.ok(!cross.esCancelado('net::ERR_CONNECTION_REFUSED'));
  assert.ok(cross.esRecursoPropioDelNavegador('https://app.test/favicon.ico'));
  assert.equal(cross.claveRecurso('https://app.test/a.css?v=123#x'), 'https://app.test/a.css');
  assert.equal(cross.distanciaColor('#ff0000', '#fd0102'), 2);
  assert.equal(cross.distanciaColor('#ff0000', 'transparente'), Infinity);
});

test('cross-browser: Firefox no emula isMobile pero sí la pantalla táctil', () => {
  const res = { ancho: 390, alto: 844 };
  assert.equal(cross.opcionesContexto({ navegador: 'firefox', res }).isMobile, undefined);
  assert.equal(cross.opcionesContexto({ navegador: 'firefox', res }).hasTouch, true);
  assert.equal(cross.opcionesContexto({ navegador: 'webkit', res }).isMobile, true);
  assert.equal(cross.opcionesContexto({ navegador: 'firefox', res: { ancho: 1366, alto: 768 } }).hasTouch, undefined);
});

const combos = ['chromium', 'firefox', 'webkit'].map((n) => ({ id: `${n}-1366x768`, navegador: n, res: { id: '1366x768', ancho: 1366, alto: 768 } }));
const medida = (nav, extra = {}) => ({ pagina: PAGINA, url: 'https://app.test/', combo: `${nav}-1366x768`, navegador: nav, status: 200,
  desborde: 0, errores_js_det: [], errores_consola_det: [], errores_js: [], errores_consola: [], recursos_fallidos: [],
  _pedidos: new Set(), ...extra });
const analizar = (medidas) => cross.analizarPaginas({ base: 'chromium', tolerancia: 6, umbral: 0.1 }, combos, ['https://app.test/'],
  Object.fromEntries(medidas.map((m) => [`${PAGINA}|${m.combo}`, m])), '.', (p) => p);

test('cross-browser: un error que pasa en todos (con otro texto) no es "solo en Firefox"', () => {
  const { hallazgos } = analizar([medida('chromium', { errores_js_det: [CHROMIUM] }), medida('firefox', { errores_js_det: [FIREFOX] }),
    medida('webkit', { errores_js_det: [WEBKIT] })]);
  assert.equal(hallazgos.length, 0);
});

test('cross-browser: un error real solo en Firefox sigue siendo Alta', () => {
  const { hallazgos } = analizar([medida('chromium'), medida('firefox', { errores_js_det: [{ mensaje: 'structuredClone is not defined', origen: null }] }), medida('webkit')]);
  assert.equal(hallazgos.length, 1);
  assert.equal(hallazgos[0].severidad, 'Alta');
  assert.equal(hallazgos[0].navegador, 'firefox');
});

test('cross-browser: errores distintos en todos los motores pesan poco (puede ser el mismo)', () => {
  const { hallazgos } = analizar([medida('chromium', { errores_js_det: [{ mensaje: 'Script error.', origen: null }] }),
    medida('firefox', { errores_js_det: [{ mensaje: 'e is undefined', origen: null }] }), medida('webkit')]);
  assert.ok(hallazgos.length >= 1);
  assert.ok(hallazgos.every((h) => h.severidad === 'Baja'));
});

test('cross-browser: si un navegador no cargó la página, lo de los otros no pasa a ser exclusivo', () => {
  const err = { mensaje: 'Error: falla del backend', origen: null };
  const { hallazgos } = analizar([medida('chromium', { errores_js_det: [err] }), medida('firefox', { errores_js_det: [err] }),
    medida('webkit', { error: 'Timeout 30000ms exceeded' })]);
  assert.equal(hallazgos.length, 0);
});

test('cross-browser: recursos: falla y otro lo cargó (Media); nadie más lo pidió (Baja)', () => {
  const pedidos = new Set(['https://app.test/fuente.woff2', 'https://app.test/foto.webp']);
  const { hallazgos } = analizar([medida('chromium', { _pedidos: pedidos }),
    medida('firefox', { recursos_fallidos: [{ url: 'https://app.test/fuente.woff2?v=2', error: 'HTTP 404' }, { url: 'https://app.test/foto.avif', error: 'HTTP 404' }] }),
    medida('webkit', { _pedidos: pedidos })]);
  const sev = Object.fromEntries(hallazgos.map((h) => [h.recurso.split('/').pop(), h.severidad]));
  assert.deepEqual(sev, { 'fuente.woff2': 'Media', 'foto.avif': 'Baja' });
});

test('cross-browser: la recarga confirma, baja lo intermitente y descarta lo que aparece en otro', () => {
  const hz = (detalle, extra) => ({ tipo: 'Error de JavaScript', severidad: 'Alta', url: 'https://app.test/', resolucion: '1366x768',
    combo: 'firefox-1366x768', navegador: 'firefox', detalle, error_det: { mensaje: detalle, origen: null }, ...extra });
  const real = hz('structuredClone is not defined');
  const intermitente = hz('ChunkLoadError: Loading chunk 7 failed');
  const enOtro = hz('Error: sesionId invalido');
  const hallazgos = [real, intermitente, enOtro];
  const de = (mensajes) => ({ errores_js_det: mensajes.map((mensaje) => ({ mensaje, origen: null })), errores_consola_det: [], recursos_fallidos: [] });
  const nuevas = {
    'https://app.test/|firefox-1366x768': de(['structuredClone is not defined', 'Error: sesionId invalido']),
    'https://app.test/|chromium-1366x768': de(['Error: sesionId invalido']),
    'https://app.test/|webkit-1366x768': de([]),
  };
  const r = cross.aplicarConfirmacion([...hallazgos], combos, nuevas, hallazgos);
  assert.deepEqual([r.confirmados, r.intermitentes, r.descartados.length], [1, 1, 1]);
  assert.equal(real.confirmado, true);
  assert.equal(intermitente.severidad, 'Baja');
  assert.deepEqual(hallazgos, [real, intermitente]);
});

test('cross-browser: un elemento no "falta" si está con el mismo texto (solo cambió el orden)', () => {
  const f = [{ tag: 'a', texto: 'Ayuda' }, { tag: 'button', texto: 'Pagar' }];
  assert.deepEqual(cross.filtrarFaltantes(f, [{ tag: 'a', texto: 'Ayuda' }]), [{ tag: 'button', texto: 'Pagar' }]);
});

test('cross-browser: suite: lo que pasa al repetirlo es Inestable; lo que vuelve a fallar se confirma', () => {
  const esc = (estado, reintentos) => ({ clave: 'f:3', escenario: 'Pagar', uri: 'f', linea: 3, historia: 'HU-1', caso: 'CP-001', estado,
    paso: estado === 'Fallido' ? 'Then ve el ok' : null, error: estado === 'Fallido' ? 'Error: no' : '', ...(reintentos ? { reintentos } : {}) });
  const corridas = (ff) => [{ id: 'chromium-1366x768', escenarios: [esc('Aprobado')] }, { id: 'firefox-1366x768', escenarios: [ff] }];

  const inestable = cross.analizarSuite(corridas(esc('Fallido', ['Fallido', 'Aprobado'])));
  assert.equal(inestable.filas[0].clase, 'Inestable');
  assert.equal(inestable.hallazgos[0].tipo, 'Inestable');
  assert.equal(inestable.hallazgos[0].severidad, 'Baja');

  const confirmado = cross.analizarSuite(corridas(esc('Fallido', ['Fallido', 'Fallido'])));
  assert.equal(confirmado.filas[0].clase, 'Diferencia entre navegadores');
  assert.equal(confirmado.hallazgos[0].severidad, 'Alta');
  assert.equal(confirmado.hallazgos[0].confirmado, true);
  assert.match(confirmado.hallazgos[0].detalle, /3 de 3/);

  const sinRepetir = cross.analizarSuite(corridas(esc('Fallido')));
  assert.equal(sinRepetir.hallazgos[0].severidad, 'Media');

  const timeout = { ...esc('Fallido', ['Fallido', 'Fallido']), error: 'locator.click: Timeout 8000ms exceeded.' };
  assert.equal(cross.analizarSuite(corridas(timeout)).hallazgos[0].severidad, 'Media');
});

test('cross-browser: --reintentos', () => {
  assert.equal(cross.argumentos([]).reintentos, 2);
  assert.equal(cross.argumentos(['--reintentos', '0']).reintentos, 0);
  assert.throws(() => cross.argumentos(['--reintentos', '9']), /0 a 5/);
});

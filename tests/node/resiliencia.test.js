// Tests del probador de resiliencia (k0lmena tools/resiliencia).
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');

const r = require(path.resolve(__dirname, '..', '..', 'herramientas/k0lmena/tools/resiliencia/resiliencia.js'));

test('resiliencia: argumentos y escenarios', () => {
  assert.equal(r.argumentos([]).escenarios.length, Object.keys(r.ESCENARIOS).length);
  assert.deepEqual(r.argumentos(['--escenarios', 'api-500, offline']).escenarios, ['api-500', 'offline']);
  assert.throws(() => r.argumentos(['--escenarios', 'ddos']), /Escenario desconocido/);
  assert.throws(() => r.argumentos(['--timeout-ms', '10']));
  assert.throws(() => r.argumentos(['--patron-api', '(']));
});

test('resiliencia: qué es una llamada a la API (sin la telemetría)', () => {
  assert.ok(r.esApi('https://app.com/api/productos', 'fetch'));
  assert.ok(!r.esApi('https://app.com/app.js', 'script'));
  assert.ok(!r.esApi('https://app.com/cdn-cgi/rum?', 'xhr'));
  assert.ok(!r.esApi('https://www.google-analytics.com/g/collect', 'fetch'));
  assert.ok(r.esApi('https://app.com/graphql', 'other', '/graphql'));
});

test('resiliencia: respuestas simuladas y campos anulados', () => {
  assert.equal(r.respuestaSimulada('api-503').status, 503);
  assert.equal(r.respuestaSimulada('vacia').body, '');
  assert.throws(() => JSON.parse(r.respuestaSimulada('malformada').body));
  assert.equal(r.respuestaSimulada('timeout'), null);
  assert.deepEqual(JSON.parse(r.respuestaSimulada('nulos', '{"a":1,"b":{"c":"x"},"d":[1,2]}').body), { a: null, b: { c: null }, d: [null, null] });
  assert.equal(r.respuestaSimulada('nulos', '<html>').body, 'null');
});

test('resiliencia: reintentos de la misma llamada', () => {
  assert.deepEqual(r.contarReintentos(['a', 'b', 'a', 'a']), { reintentos: 2, url: 'a' });
  assert.deepEqual(r.contarReintentos(['a', 'b']), { reintentos: 0, url: null });
});

test('resiliencia: hallazgos de un escenario', () => {
  const base = { texto_len: 1000, elementos: 200, spinners: 0, errores_js: [], muestra: 'Productos' };
  const tipos = (res) => r.evaluar(base, res).map((h) => `${h.severidad}:${h.tipo}`);
  // La API falla: queda en blanco, con spinner, error técnico y JS, sin recuperarse.
  assert.deepEqual(tipos({ escenario: 'api-500', estado: 'ok', interceptados: 2, espera_ms: 6000, reintentos: 5, reintentos_url: '/api/x',
    errores_js: ['TypeError: x is undefined'], recuperacion: { recupera: false, texto_len: 10 },
    observado: { url: 'https://app.com', texto_len: 20, elementos: 8, mensajes: [], spinners: 1, muestra: 'undefined' } }),
  ['Alta:Pantalla en blanco', 'Media:Carga infinita', 'Media:Mensaje técnico', 'Media:Error de JavaScript', 'Media:Reintentos sin control', 'Alta:No se recupera']);
  // Falla silenciosa: falta contenido y no hay mensaje.
  assert.deepEqual(tipos({ escenario: 'vacia', estado: 'ok', interceptados: 1, cambio_contenido: true,
    observado: { url: 'https://app.com', texto_len: 600, elementos: 150, mensajes: [], spinners: 0, muestra: '' } }), ['Media:Falla silenciosa']);
  // Con mensaje claro, aguanta.
  assert.deepEqual(tipos({ escenario: 'api-500', estado: 'ok', interceptados: 1, cambio_contenido: true, recuperacion: { recupera: true },
    observado: { url: 'https://app.com', texto_len: 600, elementos: 150, mensajes: ['No pudimos cargar los productos. Reintentar'], spinners: 0, muestra: '' } }), []);
  // Sin conexión: página de error del navegador.
  assert.deepEqual(tipos({ escenario: 'offline', estado: 'ok', navego: true, observado: { url: 'chrome-error://chromewebdata/', texto_len: 0, elementos: 0 } }), ['Baja:Sin conexión']);
  assert.deepEqual(r.evaluar(base, { escenario: 'api-500', estado: 'no-aplica' }), []);
});

test('resiliencia: resumen de la corrida', () => {
  const s = r.resumir([{ resultados: [{ escenario: 'a', estado: 'ok' }, { escenario: 'b', estado: 'hallazgo' }, { escenario: 'c', estado: 'no-aplica' }] }],
    [{ severidad: 'Alta', tipo: 'Pantalla en blanco' }, { severidad: 'Media', tipo: 'Falla silenciosa' }]);
  assert.equal(s.pruebas, 3);
  assert.equal(s.ok, 1);
  assert.equal(s.no_aplica, 1);
  assert.equal(s.pantallas_blanco, 1);
  assert.equal(s.fallas_silenciosas, 1);
  assert.equal(s.por_severidad.Alta, 1);
});

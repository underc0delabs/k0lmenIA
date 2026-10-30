// Tests del monitoreo sintético (k0lmena tools/monitoreo): checks, evaluación, cambios y aviso.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');

const m = require(path.resolve(__dirname, '..', '..', 'herramientas/k0lmena/tools/monitoreo/monitorear.js'));
const base = { lentaMs: 3000 };

test('monitoreo: arma los checks desde el config, --urls o MONITOREO_URLS, solo GET o HEAD', () => {
  const config = { checks: [{ nombre: 'Home', url: 'https://a.com/', texto: 'Hola', max_ms: 1500 }, { url: 'https://a.com/salud', metodo: 'head', status: [200, 204] }] };
  const cs = m.armarChecks(config, base, {});
  assert.deepEqual(cs.map((c) => [c.id, c.nombre, c.metodo, c.max_ms]), [
    ['GET a.com/', 'Home', 'GET', 1500], ['HEAD a.com/salud', '/salud', 'HEAD', 3000]]);
  assert.deepEqual(m.armarChecks(null, base, { MONITOREO_URLS: 'https://b.com/x, https://b.com/' }).map((c) => c.nombre), ['/x', 'b.com']);
  assert.equal(m.armarChecks(config, base, { MONITOREO_URLS: 'https://otra.com' }).length, 2, 'con config, MONITOREO_URLS no se suma');
  assert.throws(() => m.armarChecks({ checks: [{ url: 'https://a.com', metodo: 'POST' }] }, base, {}), /solo lectura/);
  assert.throws(() => m.armarChecks({ checks: [{ url: 'ftp://a.com' }] }, base, {}), /URL/);
  assert.throws(() => m.argumentos(['--nombre', 'con espacio']));
  assert.throws(() => m.argumentos(['--metodo']));
});

test('monitoreo: evalúa status, textos y tiempo', () => {
  const c = { metodo: 'GET', status: null, texto: 'Bienvenido', no_texto: 'Error 500', max_ms: 1000 };
  assert.equal(m.evaluar(c, { status: 200, ms: 300, cuerpo: 'Bienvenido' }).estado, 'OK');
  assert.deepEqual(m.evaluar(c, { error: 'ECONNREFUSED' }), { estado: 'Caído', motivo: 'ECONNREFUSED' });
  assert.match(m.evaluar(c, { status: 503, ms: 50, cuerpo: '' }).motivo, /HTTP 503/);
  assert.match(m.evaluar(c, { status: 200, ms: 50, cuerpo: 'otra cosa' }).motivo, /No aparece/);
  assert.match(m.evaluar(c, { status: 200, ms: 50, cuerpo: 'Bienvenido Error 500' }).motivo, /Aparece/);
  assert.deepEqual(m.evaluar(c, { status: 200, ms: 1500, cuerpo: 'Bienvenido' }), { estado: 'Lento', motivo: '1500 ms (máximo 1000 ms)' });
  assert.equal(m.evaluar({ ...c, status: [301], texto: null }, { status: 301, ms: 10 }).estado, 'OK');
  assert.equal(m.evaluar({ ...c, metodo: 'HEAD' }, { status: 200, ms: 10, cuerpo: '' }).estado, 'OK', 'HEAD no busca texto');
});

test('monitoreo: estado general, certificados y qué cambió', () => {
  assert.equal(m.estadoGeneral([{ estado: 'OK' }, { estado: 'Lento' }]), 'Degradado');
  assert.equal(m.estadoGeneral([{ estado: 'Por vencer' }, { estado: 'Caído' }]), 'Caído');
  assert.equal(m.estadoGeneral([{ estado: 'OK' }]), 'OK');
  assert.equal(m.diasRestantes('2026-10-24T12:00:00Z', new Date('2026-10-14T12:00:00Z')), 10);
  assert.equal(m.diasRestantes('no es fecha'), null);

  const anterior = { estado: 'Caído', resultados: [{ id: 'a', estado: 'Caído' }, { id: 'b', estado: 'OK' }] };
  const actual = { estado: 'Caído', resultados: [{ id: 'a', estado: 'OK' }, { id: 'b', estado: 'Caído' }, { id: 'c', estado: 'Caído' }] };
  assert.deepEqual(m.comparar(anterior, actual), { anterior: 'Caído', rompio: ['b', 'c'], recupero: ['a'], cambio: true });
  assert.equal(m.comparar({ estado: 'OK', resultados: [{ id: 'a', estado: 'OK' }] }, { estado: 'OK', resultados: [{ id: 'a', estado: 'OK' }] }).cambio, false);
  assert.equal(m.comparar(null, { estado: 'OK', resultados: [{ id: 'a', estado: 'Caído' }] }).rompio.length, 0, 'sin corrida anterior no hay "se rompió"');
});

test('monitoreo: el aviso dice qué falla y qué se recuperó', () => {
  const caido = m.armarAviso({ nombre: 'prod', estado: 'Caído', cambios: { anterior: 'OK', rompio: ['GET a.com/login'], recupero: [] },
    resultados: [{ nombre: '/login', estado: 'Caído', motivo: 'HTTP 502' }, { nombre: '/', estado: 'OK' }] });
  assert.equal(caido.titulo, 'Monitoreo prod: Caído');
  assert.equal(caido.nivel, 'error');
  assert.equal(caido.texto, 'Falla: /login (HTTP 502).');
  assert.deepEqual(caido.campos, [['Checks', '1/2 OK'], ['Antes', 'OK']]);
  const ok = m.armarAviso({ nombre: 'prod', estado: 'OK', cambios: { anterior: 'Caído', rompio: [], recupero: ['GET a.com/login'] }, resultados: [{ nombre: '/login', estado: 'OK' }] });
  assert.equal(ok.nivel, 'ok');
  assert.equal(ok.texto, 'Se recuperó: GET a.com/login.');
});

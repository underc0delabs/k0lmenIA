// Tests de las ayudas de los steps de API (k0lmena tools/api/http.js): URLs, JSON, ids grandes,
// credenciales ocultas y tipos de OpenAPI.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');

const http = require(path.resolve(__dirname, '..', '..', 'herramientas/k0lmena/tools/api/http.js'));

test('api: une la base (con su basePath) y el path de la spec con una sola barra', () => {
  for (const base of ['https://petstore.swagger.io/v2', 'https://petstore.swagger.io/v2/']) {
    for (const ruta of ['/pet/10', 'pet/10']) assert.equal(http.unirUrl(base, ruta), 'https://petstore.swagger.io/v2/pet/10');
  }
  assert.equal(http.unirUrl('https://a.test/api', '?q=1'), 'https://a.test/api?q=1');
  assert.equal(http.unirUrl('https://a.test', 'https://otra.test/x'), 'https://otra.test/x');
  assert.throws(() => http.unirUrl('', '/pet'), /API_BASEURL/);
});

test('api: detecta las variables que quedaron sin valor', () => {
  assert.deepEqual(http.variablesSinValor('/pet/{petId}/foto/{petId}'), ['petId']);
  assert.deepEqual(http.variablesSinValor('{"a":{"b":1}}'), []);
});

test('api: los ids int64 no pierden precisión', () => {
  const r = http.parsearRespuesta('{"id":9223372036854775807,"precio":10.5,"n":-3,"nombre":"a 9223372036854775807 \\" x","l":[12345678901234567890]}');
  assert.equal(r.id, '9223372036854775807');
  assert.equal(r.precio, 10.5);
  assert.equal(r.n, -3);
  assert.equal(r.nombre, 'a 9223372036854775807 " x');
  assert.deepEqual(r.l, ['12345678901234567890']);
  assert.equal(http.parsearRespuesta('logged in user session:123'), 'logged in user session:123');
  assert.equal(http.parsearRespuesta(''), '');
  assert.equal(http.parsearRespuesta('true'), true);
});

test('api: un body mal escrito da un error claro', () => {
  assert.throws(() => http.parsearJson('{"a": 1,}', 'El body'), /El body no es un JSON válido/);
});

test('api: oculta las credenciales en headers y parámetros', () => {
  assert.deepEqual(http.ocultarHeaders({ Authorization: 'Bearer abc', api_key: 'xyz', 'X-Tenant': 'demo', Cookie: 's=1' }),
    { Authorization: 'Bearer ***', api_key: '***', 'X-Tenant': 'demo', Cookie: '***' });
  assert.deepEqual(http.ocultarParametros({ key: 'x', apikey: 'y', q: 'perro' }), { key: 'x', apikey: '***', q: 'perro' });
});

test('api: tipos de OpenAPI y en español', () => {
  assert.ok(http.tipoDe(10, 'integer').ok);
  assert.ok(!http.tipoDe(10.5, 'integer').ok);
  assert.ok(http.tipoDe(10.5, 'number').ok);
  assert.ok(http.tipoDe('9223372036854775807', 'integer').ok);
  assert.ok(http.tipoDe([], 'lista').ok);
  assert.ok(http.tipoDe(null, 'null').ok);
  assert.ok(http.tipoDe('a', 'texto').ok);
  assert.equal(http.tipoDe('a', 'integer').real, 'string');
  assert.throws(() => http.tipoDe(1, 'fecha'), /Tipo desconocido/);
});

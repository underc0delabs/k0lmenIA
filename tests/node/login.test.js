// Tests de la sesión guardada (k0lmena tools/login): argumentos de npm run login y qué archivo usa SESION.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const k0 = path.resolve(__dirname, '..', '..', 'herramientas/k0lmena/tools/login');
const s = require(path.join(k0, 'sesion.js'));
const { argumentos } = require(path.join(k0, 'login.js'));

test('login: archivo de sesión por defecto y por nombre, dentro de .auth/', () => {
  assert.equal(s.archivoSesion(''), path.join(s.CARPETA, 'sesion.json'));
  assert.equal(s.archivoSesion('admin'), path.join(s.CARPETA, 'sesion-admin.json'));
  assert.equal(path.basename(s.CARPETA), '.auth');
  assert.ok(fs.existsSync(path.join(s.RAIZ, 'package.json')), 'RAIZ es la raíz del repo');
  for (const malo of ['../x', 'a b', 'a/b', 'a&b']) assert.throws(() => s.archivoSesion(malo), /inválido/);
});

test('login: SESION apagada, por defecto o con nombre', () => {
  for (const v of [undefined, '', ' ', '0', 'no', 'OFF', 'false']) assert.equal(s.sesionPedida(v), null);
  for (const v of ['si', 'sí', 'on', '1', 'true', 'SI']) assert.equal(s.sesionPedida(v).nombre, '');
  assert.equal(s.sesionPedida('operador').archivo, path.join(s.CARPETA, 'sesion-operador.json'));
});

test('login: sesionActiva avisa y sigue sin sesión si falta el archivo', () => {
  const avisos = [];
  assert.equal(s.sesionActiva('rol-que-no-existe-xyz', (m) => avisos.push(m)), null);
  assert.equal(avisos.length, 1);
  assert.match(avisos[0], /npm run login -- --nombre rol-que-no-existe-xyz/);
  assert.equal(s.sesionActiva('', () => assert.fail('no avisa si está apagada')), null);
});

test('login: sesionActiva devuelve el archivo si existe', () => {
  const nombre = `test-${process.pid}`;
  const archivo = s.archivoSesion(nombre);
  const creoCarpeta = !fs.existsSync(s.CARPETA);
  fs.mkdirSync(s.CARPETA, { recursive: true });
  fs.writeFileSync(archivo, '{"cookies":[],"origins":[]}');
  try {
    assert.equal(s.sesionActiva(nombre), archivo);
  } finally {
    fs.rmSync(archivo, { force: true });
    if (creoCarpeta) fs.rmSync(s.CARPETA, { recursive: true, force: true });
  }
});

test('login: argumentos de npm run login', () => {
  assert.deepEqual(argumentos([]), { url: '', nombre: '' });
  assert.deepEqual(argumentos(['--nombre', 'admin', '--url', 'https://a.com/login']), { url: 'https://a.com/login', nombre: 'admin' });
  assert.throws(() => argumentos(['--url', 'ftp://a.com']), /URL inválida/);
  assert.throws(() => argumentos(['--nombre']), /falta el valor/);
  assert.throws(() => argumentos(['--nombre', 'a b']), /inválido/);
  assert.throws(() => argumentos(['--otra']), /desconocida/);
});

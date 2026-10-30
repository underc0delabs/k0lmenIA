// Tests del probador de permisos (k0lmena tools/permisos): funciones puras, sin navegador.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');

const p = require(path.resolve(__dirname, '..', '..', 'herramientas/k0lmena/tools/permisos/permisos.js'));

test('permisos: argumentos y endpoints solo sin efecto', () => {
  assert.deepEqual(p.argumentos(['--roles', 'admin, operador']).roles, ['admin', 'operador']);
  assert.equal(p.argumentos(['--mapa', 'no']).mapa, false);
  assert.throws(() => p.argumentos(['--historia', 'mal']));
  assert.throws(() => p.argumentos(['--max-paginas', '0']));
  assert.deepEqual(p.parsearEndpoints('GET /api/a, /api/b, head /api/c'),
    [{ metodo: 'GET', ruta: '/api/a' }, { metodo: 'GET', ruta: '/api/b' }, { metodo: 'HEAD', ruta: '/api/c' }]);
  assert.throws(() => p.parsearEndpoints('DELETE /api/usuarios/1'), /sin efecto/);
});

test('permisos: roles del .env, siempre con anónimo y sin exponer claves', () => {
  assert.equal(p.claveEnv('jefe de área', 'USUARIO'), 'PERMISOS_JEFE_DE_AREA_USUARIO');
  const env = { PERMISOS_ROLES: 'admin,operador', PERMISOS_ADMIN_USUARIO: 'a', PERMISOS_ADMIN_CLAVE: 'secreta', PERMISOS_OPERADOR_USUARIO: 'o', PERMISOS_OPERADOR_TOKEN: 't' };
  const roles = p.rolesDesdeEnv(env);
  assert.deepEqual(roles.map((r) => r.id), ['anonimo', 'admin', 'operador']);
  assert.equal(roles[1].tiene_credenciales, true);
  assert.equal(roles[2].tiene_credenciales, false);
  assert.equal(roles[2].tiene_token, true);
  assert.doesNotMatch(JSON.stringify(roles), /secreta/);
  assert.deepEqual(p.rolesDesdeEnv({ APP_USER: 'u', APP_PASSWORD: 'c' }).map((r) => r.id), ['anonimo', 'usuario']);
  assert.deepEqual(p.rolesDesdeEnv(env, ['operador']).map((r) => r.id), ['anonimo', 'operador']);
  assert.deepEqual(p.rolesDesdeEnv({}).map((r) => r.id), ['anonimo']);
});

test('permisos: clasifica cada visita', () => {
  const base = { urlPedida: 'https://a.com/admin', urlFinal: 'https://a.com/admin', pideClave: false, texto: '', loginUrl: 'https://a.com/login' };
  assert.equal(p.clasificarAcceso({ ...base, status: 200 }), 'permitido');
  assert.equal(p.clasificarAcceso({ ...base, status: 403 }), 'denegado');
  assert.equal(p.clasificarAcceso({ ...base, status: 404 }), 'no-encontrada');
  assert.equal(p.clasificarAcceso({ ...base, status: 0 }), 'error');
  assert.equal(p.clasificarAcceso({ ...base, status: 200, urlFinal: 'https://a.com/login?next=/admin' }), 'pide-login');
  assert.equal(p.clasificarAcceso({ ...base, status: 200, pideClave: true }), 'pide-login');
  assert.equal(p.clasificarAcceso({ ...base, status: 200, texto: 'No tenés permiso para ver esta página' }), 'denegado');
  assert.equal(p.clasificarAcceso({ ...base, status: 200, urlPedida: 'https://a.com/login', urlFinal: 'https://a.com/login', pideClave: true }), 'permitido');
});

test('permisos: hallazgos con evidencia en la matriz', () => {
  const roles = [{ id: 'anonimo', autenticado: false }, { id: 'admin', autenticado: true, tiene_credenciales: true, login_ok: true },
    { id: 'operador', autenticado: true, tiene_credenciales: true, login_ok: true }, { id: 'auditor', autenticado: true, tiene_credenciales: true, login_ok: false, login_error: 'clave' }];
  const A = 'https://a.com/admin';
  const R = 'https://a.com/reportes';
  const rutas = [{ url: A, ruta: '/admin', descubierta_por: ['admin'] }, { url: R, ruta: '/reportes', descubierta_por: ['operador'] }];
  const matriz = [
    { rol: 'anonimo', url: A, acceso: 'permitido', status: 200 }, { rol: 'admin', url: A, acceso: 'permitido', status: 200 }, { rol: 'operador', url: A, acceso: 'denegado', status: 403 },
    { rol: 'anonimo', url: R, acceso: 'pide-login', status: 200 }, { rol: 'admin', url: R, acceso: 'permitido', status: 200 }, { rol: 'operador', url: R, acceso: 'denegado', status: 200 },
  ];
  const endpoints = [{ metodo: 'GET', ruta: '/api/x', url: 'https://a.com/api/x', resultados: { anonimo: { status: 200 }, admin: { status: 200 }, operador: { status: 403 } } }];
  const h = p.armarHallazgos({ roles, rutas, matriz, endpoints });
  const t = h.map((x) => `${x.severidad}|${x.tipo}|${x.rol}`);
  assert.ok(t.includes('Crítica|Sin login|anonimo'), t);
  assert.ok(t.includes('Crítica|API sin autenticación|anonimo'), t);
  assert.ok(t.includes('Alta|Configuración|auditor'), t);
  assert.ok(t.includes('Media|Opción sin permiso|operador'), t);
  assert.ok(t.includes('Alta|URL directa|admin'), t);
  assert.equal(h[0].severidad, 'Crítica');
  assert.deepEqual(h.map((x) => x.id), h.map((_, i) => `P-${String(i + 1).padStart(2, '0')}`));
  const r = p.resumir({ roles, rutas, matriz, endpoints, hallazgos: h });
  assert.equal(r.permitidas, 3);
  assert.equal(r.denegadas, 2);
  assert.equal(r.piden_login, 1);
  assert.equal(r.roles_con_sesion, 2);
});

// Tests del acceso a bases de datos de k0lmena (tools/bd): la clasificación de lectura y
// escritura, las protecciones (solo lectura, producción, confirmación), los marcadores de parámetros, el enmascarado
// de columnas sensibles y la configuración. Nada se conecta a una base: las protecciones corren antes del driver.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const { spawnSync } = require('child_process');

const K0 = path.resolve(__dirname, '..', '..', 'herramientas/k0lmena');
const bd = require(path.join(K0, 'tools/bd/index.js'));

function conEnv(vars, fn) {
  const antes = {};
  for (const k of Object.keys(vars)) { antes[k] = process.env[k]; process.env[k] = vars[k]; }
  const restaurar = () => {
    for (const k of Object.keys(vars)) { if (antes[k] === undefined) delete process.env[k]; else process.env[k] = antes[k]; }
  };
  let r;
  try { r = fn(); } catch (e) { restaurar(); throw e; }
  if (r && typeof r.then === 'function') return r.finally(restaurar); // async: restaura cuando termina
  restaurar();
  return r;
}

test('bd: clasifica lectura y escritura sin dejarse engañar por comentarios, literales ni funciones', () => {
  const lectura = ['SELECT * FROM usuarios WHERE id = ?', 'with t as (select 1) select * from t', 'EXPLAIN SELECT 1',
    "SELECT 'DELETE FROM x' AS texto", 'SELECT "update" FROM t', 'SELECT 1 -- DROP TABLE usuarios',
    'SELECT /* insert */ nombre FROM t', "SELECT REPLACE(nombre, 'a', 'b') FROM t", 'SELECT 1;'];
  for (const q of lectura) assert.equal(bd.analizarSQL(q).escritura, false, q);
  const escritura = ['UPDATE usuarios SET activo = 0', 'delete from t', 'INSERT INTO t VALUES (1)', 'DROP TABLE t',
    'TRUNCATE t', 'WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x', 'CALL limpiar()', 'GRANT ALL ON t TO qa'];
  for (const q of escritura) assert.equal(bd.analizarSQL(q).escritura, true, q);
  assert.throws(() => bd.analizarSQL('SELECT 1; DELETE FROM t'), /Una sola sentencia/);
  assert.throws(() => bd.analizarSQL('  -- solo un comentario'), /vacía/);
  assert.equal(bd.analizarSQL("SELECT ';' AS x").escritura, false); // el ";" dentro de un literal no es otra sentencia
});

test('bd: los "?" pasan al marcador de cada motor, salvo dentro de literales', () => {
  assert.equal(bd.marcadores("SELECT * FROM t WHERE a = ? AND b = '?' AND c = ?", 'postgres'), "SELECT * FROM t WHERE a = $1 AND b = '?' AND c = $2");
  assert.equal(bd.marcadores('SELECT ? , ?', 'sqlserver'), 'SELECT @p1 , @p2');
  assert.equal(bd.marcadores('SELECT ?', 'mysql'), 'SELECT ?');
});

test('bd: enmascara columnas sensibles en filas anidadas y respeta las del .env', () => {
  const fila = { id: 1, email: 'ana@test.com', password_hash: 'x', api_key: 'k', perfil: { token: 't', nombre: 'Ana' }, tarjeta: null };
  assert.deepEqual(bd.enmascarar(fila), { id: 1, email: 'ana@test.com', password_hash: '****', api_key: '****',
    perfil: { token: '****', nombre: 'Ana' }, tarjeta: null });
  assert.deepEqual(bd.enmascarar([{ clave: 's' }]), [{ clave: '****' }]);
  conEnv({ DB_COLUMNAS_SENSIBLES: 'dni, telefono' }, () => {
    assert.ok(bd.esSensible('DNI') && bd.esSensible('telefono') && !bd.esSensible('nombre'));
  });
});

const CONF = {
  DB_CONEXIONES: 'qa, prod', DB_QA_MOTOR: 'postgresql', DB_QA_BASE: 'tienda', DB_QA_USUARIO: 'qa', DB_QA_CLAVE: 'secreta',
  DB_QA_ESCRITURA: 'si', DB_QA_SSL: 'sin-verificar',
  DB_PROD_MOTOR: 'mysql', DB_PROD_URL: 'mysql://lector:clave@db.prod.local:3307/tienda', DB_PROD_ESCRITURA: 'si', DB_PROD_PRODUCCION: 'si',
};

test('bd: configuración por conexión con valores por defecto y descripción sin secretos', () => {
  conEnv(CONF, () => {
    assert.deepEqual(bd.nombresConexiones(), ['qa', 'prod']);
    const qa = bd.config();
    assert.equal(qa.nombre, 'qa');
    assert.equal(qa.motor, 'postgres');
    assert.equal(qa.puerto, 5432);
    assert.equal(qa.host, 'localhost');
    assert.equal(qa.ssl, 'sin-verificar');
    assert.equal(qa.escritura, true);
    const prod = bd.describir(bd.config('PROD'));
    assert.deepEqual(prod, { nombre: 'prod', motor: 'mysql', destino: 'db.prod.local:3307/tienda', escritura: false, produccion: true });
    assert.ok(!JSON.stringify(prod).includes('clave') && !JSON.stringify(bd.describir(qa)).includes('secreta'));
    assert.throws(() => bd.config('otra'), /no está en DB_CONEXIONES/);
  });
  conEnv({ DB_CONEXIONES: 'x', DB_X_MOTOR: 'oracle', DB_X_BASE: 'b' }, () => assert.throws(() => bd.config('x'), /MOTOR tiene que ser/));
  conEnv({ DB_CONEXIONES: 'x', DB_X_MOTOR: 'postgres', DB_X_BASE: 'b', DB_X_SSL: 'quizas' }, () => assert.throws(() => bd.config('x'), /SSL tiene que ser/));
  conEnv({ DB_CONEXIONES: 'x', DB_X_MOTOR: 'postgres' }, () => assert.throws(() => bd.config('x'), /Falta DB_X_BASE/));
});

test('bd: las protecciones de escritura frenan antes de conectarse', async () => {
  await conEnv({ ...CONF, DB_LECTURA_MOTOR: 'postgres', DB_LECTURA_BASE: 'b', DB_CONEXIONES: 'qa, prod, lectura' }, async () => {
    // Una escritura por el camino de lectura: rechazada aunque la conexión permita escribir.
    await assert.rejects(bd.sql('qa', 'DELETE FROM pedidos'), /modifica datos/);
    // Producción: nunca, aunque ESCRITURA=si y esté confirmado.
    await assert.rejects(bd.sql('prod', 'UPDATE t SET a = 1', [], { escribir: true, confirmado: true }), /producción/);
    // Conexión de solo lectura.
    await assert.rejects(bd.sql('lectura', 'UPDATE t SET a = 1', [], { escribir: true, confirmado: true }), /solo lectura/);
    // Permite escribir pero falta la confirmación explícita.
    await assert.rejects(bd.sql('qa', 'UPDATE t SET a = 1', [], { escribir: true }), /confirmación explícita/);
    // MongoDB: operaciones con efecto, y un aggregate con $out también es escritura.
    process.env.DB_CONEXIONES += ', docs';
    process.env.DB_DOCS_MOTOR = 'mongodb';
    process.env.DB_DOCS_BASE = 'tienda';
    try {
      await assert.rejects(bd.mongo('docs', { coleccion: 'pedidos', operacion: 'deleteMany' }), /modifica datos/);
      await assert.rejects(bd.mongo('docs', { coleccion: 'p', operacion: 'aggregate', pipeline: [{ $out: 'copia' }] }), /modifica datos/);
      await assert.rejects(bd.mongo('docs', { coleccion: 'p', operacion: 'dropDatabase' }), /no soportada/);
      await assert.rejects(bd.sql('docs', 'SELECT 1'), /es MongoDB/);
    } finally {
      delete process.env.DB_DOCS_MOTOR;
      delete process.env.DB_DOCS_BASE;
    }
  });
});

test('bd: el CLI no escribe sin --confirmar y no muestra la clave', () => {
  const cli = path.join(K0, 'tools/bd/cli.js');
  const env = { ...process.env, ...CONF, K0LMENA_ENV_FILE: path.join(__dirname, 'no-existe.env') };
  const r = spawnSync(process.execPath, [cli, 'escribir', '--bd', 'qa', '--sql', 'UPDATE t SET a = 1'], { env, encoding: 'utf8' });
  assert.notEqual(r.status, 0);
  assert.match(r.stdout + r.stderr, /confirmación explícita|--confirmar/);
  const r2 = spawnSync(process.execPath, [cli, 'consultar', '--bd', 'qa', '--sql', 'DROP TABLE t'], { env, encoding: 'utf8' });
  assert.notEqual(r2.status, 0);
  assert.match(r2.stdout + r2.stderr, /modifica datos/);
  assert.ok(!(r.stdout + r.stderr + r2.stdout + r2.stderr).includes('secreta'));
});

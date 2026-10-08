// tools/bd/index.js
//
// Acceso a bases de datos para k0lmenIA: lo usan el CLI (tools/bd/cli.js, agente
// verificador-datos) y los steps de Cucumber (tools/bd/bd.steps.ts).
//
// Motores: PostgreSQL, MySQL / MariaDB, SQL Server y MongoDB.
// Conexiones con nombre, desde el .env de la raíz:
//
//   DB_CONEXIONES=principal,pagos          (la primera es la conexión por defecto)
//   DB_PRINCIPAL_MOTOR=postgres            postgres | mysql | mariadb | sqlserver | mongodb
//   DB_PRINCIPAL_URL=                      opcional: URL completa (reemplaza host/puerto/base/usuario/clave)
//   DB_PRINCIPAL_HOST=  _PUERTO=  _BASE=  _USUARIO=  _CLAVE=
//   DB_PRINCIPAL_SSL=no                    si | no
//   DB_PRINCIPAL_ESCRITURA=no              si = permite escribir (siempre con confirmación explícita)
//   DB_PRINCIPAL_PRODUCCION=no             si = nunca escribe, aunque ESCRITURA=si
//
// Seguridad:
//   - Las lecturas corren dentro de una transacción que siempre se descarta (ROLLBACK)
//     y en modo READ ONLY donde el motor lo permite: aunque una consulta "de lectura"
//     tuviera efectos, no quedan.
//   - Una sentencia se considera escritura si tiene INSERT, UPDATE, DELETE, DDL, etc.
//     Escribir exige ESCRITURA=si, que la conexión no sea de producción y confirmación.
//   - Una sola sentencia por llamada. Parámetros con "?" (nunca concatenar valores).
'use strict';

class ErrorBD extends Error {}

const MOTORES = {
  postgres: 'postgres', postgresql: 'postgres', pg: 'postgres',
  mysql: 'mysql', mariadb: 'mysql',
  sqlserver: 'sqlserver', mssql: 'sqlserver',
  mongodb: 'mongodb', mongo: 'mongodb',
};
const PUERTOS = { postgres: 5432, mysql: 3306, sqlserver: 1433, mongodb: 27017 };
const SI = (v) => ['si', 'sí', 'true', '1', 'yes', 'on'].includes(String(v ?? '').trim().toLowerCase());

const numero = (v, def) => (Number.isFinite(Number(v)) && String(v).trim() !== '' ? Number(v) : def);
const TIMEOUT_MS = () => numero(process.env.DB_TIMEOUT_MS, 30000);
const FILAS_MAX = () => numero(process.env.DB_FILAS_MAX, 50);

// ------------------------------------------------------------------ configuración
function nombresConexiones() {
  return (process.env.DB_CONEXIONES || '').split(',').map((s) => s.trim().toLowerCase()).filter(Boolean);
}

function config(nombre) {
  const nombres = nombresConexiones();
  if (!nombres.length) throw new ErrorBD('No hay conexiones configuradas: definí DB_CONEXIONES y las variables DB_<NOMBRE>_* en el .env de la raíz.');
  const n = (nombre || nombres[0]).trim().toLowerCase();
  if (!nombres.includes(n)) throw new ErrorBD(`La conexión "${n}" no está en DB_CONEXIONES (${nombres.join(', ')}).`);
  const p = `DB_${n.toUpperCase().replace(/[^A-Z0-9]/g, '_')}_`;
  const v = (k) => (process.env[p + k] ?? '').trim();
  const motor = MOTORES[v('MOTOR').toLowerCase()];
  if (!motor) throw new ErrorBD(`${p}MOTOR tiene que ser postgres, mysql, mariadb, sqlserver o mongodb.`);
  const c = {
    nombre: n, motor, url: v('URL'),
    host: v('HOST') || 'localhost', puerto: numero(v('PUERTO'), PUERTOS[motor]),
    base: v('BASE'), usuario: v('USUARIO'), clave: v('CLAVE'),
    ssl: SI(v('SSL')), escritura: SI(v('ESCRITURA')), produccion: SI(v('PRODUCCION')),
  };
  if (!c.url && !c.base) throw new ErrorBD(`Falta ${p}BASE (o ${p}URL) en el .env.`);
  return c;
}

/** Descripción de una conexión sin secretos (para listar). */
function describir(c) {
  let destino = `${c.host}:${c.puerto}/${c.base}`;
  if (c.url) {
    try { const u = new URL(c.url); destino = `${u.hostname}${u.port ? ':' + u.port : ''}${u.pathname}`; } catch { destino = '(URL)'; }
  }
  return { nombre: c.nombre, motor: c.motor, destino, escritura: c.escritura && !c.produccion, produccion: c.produccion };
}

// ------------------------------------------------------------------ drivers
function driver(modulo) {
  try { return require(modulo); } catch {
    throw new ErrorBD(`Falta el driver "${modulo}": corré "npm install" en herramientas/k0lmena.`);
  }
}

const clientes = new Map();

async function cliente(c) {
  if (clientes.has(c.nombre)) return clientes.get(c.nombre);
  let cli;
  if (c.motor === 'postgres') {
    const { Pool, types } = driver('pg');
    // Fechas tal como están guardadas (sin convertirlas a la zona horaria local): date, timestamp, timestamptz.
    for (const oid of [1082, 1114, 1184]) types.setTypeParser(oid, (v) => v);
    cli = new Pool(c.url ? { connectionString: c.url, max: 2 } : {
      host: c.host, port: c.puerto, database: c.base, user: c.usuario, password: c.clave, max: 2,
      ssl: c.ssl ? { rejectUnauthorized: false } : undefined, connectionTimeoutMillis: TIMEOUT_MS(),
    });
  } else if (c.motor === 'mysql') {
    const mysql = driver('mysql2/promise');
    cli = mysql.createPool(c.url ? { uri: c.url, connectionLimit: 2 } : {
      host: c.host, port: c.puerto, database: c.base, user: c.usuario, password: c.clave, connectionLimit: 2,
      ssl: c.ssl ? { rejectUnauthorized: false } : undefined, connectTimeout: TIMEOUT_MS(), dateStrings: true,
    });
  } else if (c.motor === 'sqlserver') {
    const sql = driver('mssql');
    cli = await new sql.ConnectionPool(c.url || {
      server: c.host, port: c.puerto, database: c.base, user: c.usuario, password: c.clave,
      options: { encrypt: c.ssl, trustServerCertificate: true },
      connectionTimeout: TIMEOUT_MS(), requestTimeout: TIMEOUT_MS(), pool: { max: 2 },
    }).connect();
  } else {
    const { MongoClient } = driver('mongodb');
    const url = c.url || `mongodb://${c.usuario ? `${encodeURIComponent(c.usuario)}:${encodeURIComponent(c.clave)}@` : ''}${c.host}:${c.puerto}/${c.base}${c.usuario ? '?authSource=admin' : ''}`;
    cli = await new MongoClient(url, { serverSelectionTimeoutMS: TIMEOUT_MS(), tls: c.ssl || undefined }).connect();
  }
  clientes.set(c.nombre, cli);
  return cli;
}

async function cerrarTodo() {
  for (const [n, cli] of clientes) {
    try { await (cli.end ? cli.end() : cli.close()); } catch { /* ya cerrada */ }
    clientes.delete(n);
  }
}

// ------------------------------------------------------------------ análisis de SQL
const ESCRITURA = new Set(['insert', 'update', 'delete', 'merge', 'upsert', 'replace', 'truncate', 'drop', 'alter', 'create',
  'grant', 'revoke', 'rename', 'call', 'exec', 'execute', 'copy', 'lock', 'vacuum', 'reindex', 'cluster', 'set', 'into',
  'load', 'handler', 'do', 'comment', 'refresh', 'backup', 'restore', 'kill', 'shutdown', 'dbcc', 'bulk', 'openrowset']);
const INICIO_LECTURA = new Set(['select', 'with', 'show', 'describe', 'desc', 'explain', 'values', 'table']);

/** SQL sin comentarios, literales ni identificadores entre comillas (para clasificarlo). */
function limpiarSQL(sql) {
  return sql
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/--[^\n]*/g, ' ')
    .replace(/'(?:[^']|'')*'/g, "''")
    .replace(/"(?:[^"]|"")*"/g, '""')
    .replace(/`[^`]*`/g, '``')
    .replace(/\[[^\]]*\]/g, '[]');
}

function analizarSQL(sql) {
  const limpio = limpiarSQL(sql).trim().replace(/;\s*$/, '');
  if (!limpio) throw new ErrorBD('La consulta está vacía.');
  if (limpio.includes(';')) throw new ErrorBD('Una sola sentencia por consulta (sin ";" intermedios).');
  const minus = limpio.toLowerCase();
  const tokens = [...minus.matchAll(/[a-z_][a-z0-9_$]*/g)].map((m) => ({
    palabra: m[0],
    // Una palabra seguida de "(" es una función (REPLACE(...), INSERT(...) de MySQL), no una sentencia.
    funcion: /^\s*\(/.test(minus.slice(m.index + m[0].length)),
  }));
  const palabras = tokens.map((t) => t.palabra);
  const escritura = !INICIO_LECTURA.has(palabras[0]) || tokens.some((t) => !t.funcion && ESCRITURA.has(t.palabra));
  return { escritura, primera: palabras[0] };
}

/** Reemplaza los "?" (fuera de literales) por el marcador del motor. */
function marcadores(sql, motor) {
  if (motor === 'mysql') return sql;
  let i = 0, salida = '', comilla = null;
  for (const ch of sql) {
    if (comilla) { if (ch === comilla) comilla = null; salida += ch; continue; }
    if (ch === "'" || ch === '"') { comilla = ch; salida += ch; continue; }
    if (ch === '?') { i += 1; salida += motor === 'postgres' ? `$${i}` : `@p${i}`; continue; }
    salida += ch;
  }
  return salida;
}

// ------------------------------------------------------------------ valores y enmascarado
const SENSIBLES = /pass|clave|contrase|secret|token|hash|salt|api_?key|tarjeta|card|cvv|cbu|iban|pin$/i;
function esSensible(campo) {
  const extra = (process.env.DB_COLUMNAS_SENSIBLES || '').split(',').map((s) => s.trim().toLowerCase()).filter(Boolean);
  return SENSIBLES.test(campo) || extra.includes(String(campo).toLowerCase());
}

function normalizar(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'bigint') return v.toString();
  if (v instanceof Date) return v.toISOString();
  if (Buffer.isBuffer(v)) return `<binario ${v.length} bytes>`;
  if (v && v._bsontype === 'ObjectId') return v.toString();
  if (v && v._bsontype === 'Decimal128') return v.toString();
  if (Array.isArray(v)) return v.map(normalizar);
  if (typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, normalizar(x)]));
  return v;
}

function enmascarar(fila) {
  if (Array.isArray(fila)) return fila.map(enmascarar);
  if (!fila || typeof fila !== 'object') return fila;
  return Object.fromEntries(Object.entries(fila).map(([k, v]) => [k, esSensible(k) && v !== null ? '****' : enmascarar(v)]));
}

// ------------------------------------------------------------------ permisos de escritura
function verificarEscritura(c, confirmado) {
  if (c.produccion) throw new ErrorBD(`La conexión "${c.nombre}" está marcada como producción: no se permite escribir.`);
  if (!c.escritura) throw new ErrorBD(`La conexión "${c.nombre}" es de solo lectura. Para escribir, definí DB_${c.nombre.toUpperCase()}_ESCRITURA=si en el .env.`);
  if (!confirmado) throw new ErrorBD('Escribir en la base de datos requiere confirmación explícita (--confirmar).');
}

// ------------------------------------------------------------------ SQL
/**
 * Ejecuta una sentencia SQL.
 * @returns {{columnas: string[], filas: object[], afectadas: number|null, ms: number, escritura: boolean}}
 */
async function sql(nombre, texto, params = [], opciones = {}) {
  const c = config(nombre);
  if (c.motor === 'mongodb') throw new ErrorBD(`"${c.nombre}" es MongoDB: usá una consulta de colección (filtro), no SQL.`);
  const { escritura } = analizarSQL(texto);
  if (escritura && !opciones.escribir) {
    throw new ErrorBD('La consulta modifica datos (o no empieza con SELECT/WITH/SHOW). Para escribir usá el modo de escritura, con confirmación.');
  }
  if (escritura) verificarEscritura(c, opciones.confirmado);
  const cli = await cliente(c);
  const q = marcadores(texto, c.motor);
  const inicio = Date.now();
  let filas = [], columnas = [], afectadas = null;

  if (c.motor === 'postgres') {
    const con = await cli.connect();
    try {
      await con.query(escritura ? 'BEGIN' : 'BEGIN TRANSACTION READ ONLY');
      await con.query(`SET LOCAL statement_timeout = ${Math.floor(TIMEOUT_MS())}`);
      const r = await con.query(q, params);
      filas = r.rows || []; columnas = (r.fields || []).map((f) => f.name);
      afectadas = escritura ? r.rowCount : null;
      await con.query(escritura ? 'COMMIT' : 'ROLLBACK');
    } catch (e) { await con.query('ROLLBACK').catch(() => {}); throw e; } finally { con.release(); }
  } else if (c.motor === 'mysql') {
    const con = await cli.getConnection();
    try {
      await con.query(escritura ? 'START TRANSACTION' : 'START TRANSACTION READ ONLY');
      const [r, campos] = await con.query({ sql: q, timeout: TIMEOUT_MS() }, params);
      if (Array.isArray(r)) { filas = r; columnas = (campos || []).map((f) => f.name); } else { afectadas = r.affectedRows; }
      await con.query(escritura ? 'COMMIT' : 'ROLLBACK');
    } catch (e) { await con.query('ROLLBACK').catch(() => {}); throw e; } finally { con.release(); }
  } else {
    const mssql = driver('mssql');
    const tx = new mssql.Transaction(cli);
    await tx.begin();
    try {
      const req = new mssql.Request(tx);
      params.forEach((p, i) => req.input(`p${i + 1}`, p));
      const r = await req.query(q);
      filas = r.recordset || [];
      columnas = filas.length ? Object.keys(filas[0]) : Object.keys((r.recordset && r.recordset.columns) || {});
      afectadas = escritura ? (r.rowsAffected || []).reduce((a, b) => a + b, 0) : null;
      await (escritura ? tx.commit() : tx.rollback());
    } catch (e) { await tx.rollback().catch(() => {}); throw e; }
  }
  if (!columnas.length && filas.length) columnas = Object.keys(filas[0]);
  return { columnas, filas: filas.map(normalizar), afectadas, ms: Date.now() - inicio, escritura };
}

// ------------------------------------------------------------------ MongoDB
const LECTURA_MONGO = ['find', 'findOne', 'countDocuments', 'count', 'aggregate', 'distinct'];
const ESCRITURA_MONGO = ['insertOne', 'insertMany', 'updateOne', 'updateMany', 'replaceOne', 'deleteOne', 'deleteMany'];

/**
 * Operación sobre una colección de MongoDB.
 * o: { coleccion, operacion, filtro, proyeccion, orden, limite, pipeline, campo, documento, cambios }
 */
async function mongo(nombre, o, opciones = {}) {
  const c = config(nombre);
  if (c.motor !== 'mongodb') throw new ErrorBD(`"${c.nombre}" es ${c.motor}: usá SQL.`);
  const op = o.operacion || 'find';
  if (!LECTURA_MONGO.includes(op) && !ESCRITURA_MONGO.includes(op)) {
    throw new ErrorBD(`Operación de MongoDB no soportada: ${op}. Lectura: ${LECTURA_MONGO.join(', ')}. Escritura: ${ESCRITURA_MONGO.join(', ')}.`);
  }
  const escritura = ESCRITURA_MONGO.includes(op) || (op === 'aggregate' && JSON.stringify(o.pipeline || []).match(/"\$(out|merge)"/));
  if (escritura) {
    if (!opciones.escribir) throw new ErrorBD(`"${op}" modifica datos: usá el modo de escritura, con confirmación.`);
    verificarEscritura(c, opciones.confirmado);
  }
  if (!o.coleccion) throw new ErrorBD('Falta la colección.');
  const cli = await cliente(c);
  const col = cli.db(c.base || undefined).collection(o.coleccion);
  const filtro = o.filtro || {};
  const maxTimeMS = TIMEOUT_MS();
  const inicio = Date.now();
  let filas = [], afectadas = null;
  switch (op) {
    case 'find': {
      let cur = col.find(filtro, { projection: o.proyeccion, maxTimeMS });
      if (o.orden) cur = cur.sort(o.orden);
      filas = await cur.limit(o.limite || FILAS_MAX() + 1).toArray();
      break;
    }
    case 'findOne': { const d = await col.findOne(filtro, { projection: o.proyeccion, maxTimeMS }); filas = d ? [d] : []; break; }
    case 'count': case 'countDocuments': filas = [{ total: await col.countDocuments(filtro, { maxTimeMS }) }]; break;
    case 'distinct': filas = (await col.distinct(o.campo, filtro, { maxTimeMS })).map((v) => ({ [o.campo]: v })); break;
    case 'aggregate': filas = await col.aggregate(o.pipeline || [], { maxTimeMS }).toArray(); break;
    case 'insertOne': afectadas = (await col.insertOne(o.documento)).acknowledged ? 1 : 0; break;
    case 'insertMany': afectadas = (await col.insertMany(o.documento)).insertedCount; break;
    case 'updateOne': afectadas = (await col.updateOne(filtro, o.cambios)).modifiedCount; break;
    case 'updateMany': afectadas = (await col.updateMany(filtro, o.cambios)).modifiedCount; break;
    case 'replaceOne': afectadas = (await col.replaceOne(filtro, o.documento)).modifiedCount; break;
    case 'deleteOne': afectadas = (await col.deleteOne(filtro)).deletedCount; break;
    case 'deleteMany': afectadas = (await col.deleteMany(filtro)).deletedCount; break;
  }
  filas = filas.map(normalizar);
  const columnas = [...new Set(filas.flatMap((f) => Object.keys(f)))];
  return { columnas, filas, afectadas, ms: Date.now() - inicio, escritura: !!escritura };
}

// ------------------------------------------------------------------ verificaciones (las usan los steps)
const IDENT = /^[A-Za-z_][\w$]*(\.[A-Za-z_][\w$]*)*$/;
function citar(ident, motor) {
  if (!IDENT.test(ident)) throw new ErrorBD(`Nombre de tabla o campo inválido: "${ident}".`);
  const [a, b] = motor === 'postgres' ? ['"', '"'] : motor === 'mysql' ? ['`', '`'] : ['[', ']'];
  return ident.split('.').map((p) => a + p + b).join('.');
}

const NULO = /^\(?(nulo|null)\)?$/i;

/** Filtro de MongoDB tolerante a tipos: "5" busca 5 o "5"; "true" busca true o "true"; 24 hex busca ObjectId. */
function valorMongo(v) {
  if (v === null || NULO.test(String(v))) return null;
  const s = String(v);
  const opciones = [s];
  if (/^-?\d+(\.\d+)?$/.test(s)) opciones.push(Number(s));
  if (/^(true|false)$/i.test(s)) opciones.push(s.toLowerCase() === 'true');
  if (/^[a-f0-9]{24}$/i.test(s)) { try { const { ObjectId } = driver('mongodb'); opciones.push(new ObjectId(s)); } catch { /* sin driver */ } }
  return opciones.length > 1 ? { $in: opciones } : s;
}

/**
 * Busca registros por igualdad de campos.
 * condiciones: [{ campo, valor }] (valor "(nulo)" = IS NULL)
 * @returns {{ total: number, filas: object[], consulta: string }}
 */
async function buscar(nombre, tabla, condiciones, limite = 5) {
  const c = config(nombre);
  if (c.motor === 'mongodb') {
    const filtro = Object.fromEntries(condiciones.map(({ campo, valor }) => [campo, valorMongo(valor)]));
    const cli = await cliente(c);
    const col = cli.db(c.base || undefined).collection(tabla);
    const total = await col.countDocuments(filtro, { maxTimeMS: TIMEOUT_MS() });
    const filas = (await col.find(filtro, { maxTimeMS: TIMEOUT_MS() }).limit(limite).toArray()).map(normalizar);
    return { total, filas, consulta: `db.${tabla}.find(${JSON.stringify(filtro)})` };
  }
  const params = [];
  const donde = condiciones.map(({ campo, valor }) => {
    if (valor === null || NULO.test(String(valor))) return `${citar(campo, c.motor)} IS NULL`;
    params.push(valor);
    return `${citar(campo, c.motor)} = ?`;
  });
  const where = donde.length ? ` WHERE ${donde.join(' AND ')}` : '';
  const t = citar(tabla, c.motor);
  const conteo = await sql(nombre, `SELECT COUNT(*) AS total FROM ${t}${where}`, params);
  const total = Number(Object.values(conteo.filas[0] || { total: 0 })[0]);
  const consultaFilas = c.motor === 'sqlserver' ? `SELECT TOP ${limite} * FROM ${t}${where}` : `SELECT * FROM ${t}${where} LIMIT ${limite}`;
  const { filas } = await sql(nombre, consultaFilas, params);
  return { total, filas, consulta: `${consultaFilas.replace(/ LIMIT \d+$/, '').replace(/TOP \d+ /, '')}  [${params.map(String).join(', ')}]` };
}

/** Lista tablas (o colecciones) y, con tabla, sus columnas. */
async function esquema(nombre, tabla) {
  const c = config(nombre);
  if (c.motor === 'mongodb') {
    const db = (await cliente(c)).db(c.base || undefined);
    if (!tabla) return { tipo: 'colecciones', filas: (await db.listCollections().toArray()).map((x) => ({ coleccion: x.name })).sort((a, b) => a.coleccion.localeCompare(b.coleccion)) };
    const muestra = await db.collection(tabla).find({}).limit(20).toArray();
    const campos = new Map();
    for (const d of muestra) for (const [k, v] of Object.entries(d)) {
      const tipo = v === null ? 'null' : Array.isArray(v) ? 'array' : v && v._bsontype ? v._bsontype : v instanceof Date ? 'date' : typeof v;
      campos.set(k, new Set([...(campos.get(k) || []), tipo]));
    }
    return { tipo: `campos de ${tabla} (muestra de ${muestra.length} documentos)`, filas: [...campos].map(([campo, tipos]) => ({ campo, tipos: [...tipos].join(' | ') })) };
  }
  let q, params = [];
  if (!tabla) {
    q = {
      postgres: "SELECT table_schema AS esquema, table_name AS tabla FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1, 2",
      mysql: 'SELECT table_name AS tabla FROM information_schema.tables WHERE table_schema = DATABASE() ORDER BY 1',
      sqlserver: 'SELECT TABLE_SCHEMA AS esquema, TABLE_NAME AS tabla FROM INFORMATION_SCHEMA.TABLES ORDER BY 1, 2',
    }[c.motor];
  } else {
    const partes = tabla.split('.');
    const nombreTabla = partes.pop();
    params = [nombreTabla];
    const esq = partes.length ? (params.push(partes[0]), ' AND table_schema = ?') : '';
    q = {
      postgres: `SELECT column_name AS columna, data_type AS tipo, is_nullable AS nulo FROM information_schema.columns WHERE table_name = ?${esq} ORDER BY ordinal_position`,
      mysql: `SELECT column_name AS columna, column_type AS tipo, is_nullable AS nulo FROM information_schema.columns WHERE table_name = ? AND table_schema = DATABASE() ORDER BY ordinal_position`,
      sqlserver: `SELECT COLUMN_NAME AS columna, DATA_TYPE AS tipo, IS_NULLABLE AS nulo FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?${esq.replace('table_schema', 'TABLE_SCHEMA')} ORDER BY ORDINAL_POSITION`,
    }[c.motor];
    if (c.motor === 'mysql') params = [nombreTabla];
  }
  const r = await sql(nombre, q, params);
  return { tipo: tabla ? `columnas de ${tabla}` : 'tablas', filas: r.filas };
}

/** Prueba la conexión con una consulta trivial. */
async function probar(nombre) {
  const c = config(nombre);
  const inicio = Date.now();
  if (c.motor === 'mongodb') await (await cliente(c)).db(c.base || undefined).command({ ping: 1 });
  else await sql(nombre, 'SELECT 1 AS ok');
  return { ...describir(c), ms: Date.now() - inicio };
}

module.exports = {
  ErrorBD, nombresConexiones, config, describir, sql, mongo, buscar, esquema, probar, cerrarTodo,
  analizarSQL, marcadores, enmascarar, esSensible, FILAS_MAX,
};

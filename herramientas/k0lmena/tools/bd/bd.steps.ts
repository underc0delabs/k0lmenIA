// tools/bd/bd.steps.ts
//
// Steps genéricos en español para verificar datos en la base de datos desde los
// tests de web y de API (corren con npm test, sin tokens). Siempre de solo lectura.
//
// Conexión: la primera de DB_CONEXIONES, o una con nombre ("en la base de datos "pagos"").
// Valores: {variable} usa lo guardado en el escenario (ej. un id de la respuesta de la API)
// o una variable del .env. "(nulo)" verifica NULL.
// Espera: si el dato todavía no está (procesos asíncronos), reintenta hasta DB_ESPERA_MS (default 5000).
import '../../env';
import { Before, When, Then, AfterAll, DataTable } from '@cucumber/cucumber';
import { variables, interpolar } from '../variables';
// eslint-disable-next-line @typescript-eslint/no-var-requires
const bd = require('./index');

type Condicion = { campo: string; valor: string };
type Resultado = { columnas: string[]; filas: Record<string, unknown>[] };

let ultimaConsulta: Resultado | undefined;
const NULO = /^\(?(nulo|null)\)?$/i;
const ESPERA_MS = () => Number(process.env.DB_ESPERA_MS ?? 5000) || 0;

Before(() => { ultimaConsulta = undefined; });
AfterAll(async () => { await bd.cerrarTodo(); });

/** Compara un valor de la base con el esperado (texto del .feature) sin ser estricto con el tipo. */
function coincide(real: unknown, esperado: string): boolean {
  if (NULO.test(esperado)) return real === null || real === undefined;
  if (real === null || real === undefined) return false;
  const s = typeof real === 'object' ? JSON.stringify(real) : String(real);
  if (s === esperado) return true;
  if (/^-?\d+(\.\d+)?$/.test(esperado) && s.trim() !== '' && Number(s) === Number(esperado)) return true;
  if (/^(true|false)$/i.test(esperado)) return ['true', '1'].includes(s.toLowerCase()) === (esperado.toLowerCase() === 'true');
  if (/^\d{4}-\d{2}-\d{2}/.test(esperado) && s.startsWith(esperado)) return true; // fecha (con o sin hora)
  return false;
}

const condiciones = (campo: string, valor: string): Condicion[] => [{ campo, valor: interpolar(valor) }];

function desdeTabla(tabla: DataTable): Condicion[] {
  const filas = tabla.raw().filter((f) => f.length >= 2);
  const sinEncabezado = filas.length && filas[0][0].trim().toLowerCase() === 'campo' ? filas.slice(1) : filas;
  return sinEncabezado.map(([campo, valor]) => ({ campo: campo.trim(), valor: interpolar(valor.trim()) }));
}

/** Reintenta la búsqueda hasta que la condición se cumpla o venza DB_ESPERA_MS. */
async function esperarBusqueda(conexion: string | undefined, tabla: string, cond: Condicion[], ok: (r: any) => boolean) {
  const limite = Date.now() + ESPERA_MS();
  let r = await bd.buscar(conexion, tabla, cond);
  while (!ok(r) && Date.now() < limite) {
    await new Promise((res) => setTimeout(res, 500));
    r = await bd.buscar(conexion, tabla, cond);
  }
  return r;
}

function evidencia(world: any, titulo: string, consulta: string, filas: unknown[]) {
  const cuerpo = `${titulo}\n${consulta}\n\n${JSON.stringify(bd.enmascarar(filas.slice(0, 5)), null, 2)}`;
  return world.attach(cuerpo, 'text/plain');
}

const describirCond = (cond: Condicion[]) => cond.map((c) => `${c.campo} = ${c.valor}`).join(' y ');

// ------------------------------------------------------------------ cantidad de registros
async function verificarCantidad(world: any, conexion: string | undefined, cantidad: number, tabla: string, cond: Condicion[]) {
  const r = await esperarBusqueda(conexion, tabla, cond, (x) => x.total === cantidad);
  await evidencia(world, `Base de datos: ${r.total} registro(s) en ${tabla}`, r.consulta, r.filas);
  if (r.total !== cantidad) {
    throw new Error(`Se esperaban ${cantidad} registro(s) en "${tabla}" donde ${describirCond(cond)} y hay ${r.total}.`);
  }
}

Then('la base de datos tiene {int} registro(s) en {string} donde:', async function (cantidad: number, tabla: string, t: DataTable) {
  await verificarCantidad(this, undefined, cantidad, tabla, desdeTabla(t));
});
Then('la base de datos {string} tiene {int} registro(s) en {string} donde:', async function (conexion: string, cantidad: number, tabla: string, t: DataTable) {
  await verificarCantidad(this, conexion, cantidad, tabla, desdeTabla(t));
});

// ------------------------------------------------------------------ existe / no existe
async function verificarExiste(world: any, conexion: string | undefined, debeExistir: boolean, tabla: string, cond: Condicion[]) {
  const r = await esperarBusqueda(conexion, tabla, cond, (x) => (x.total > 0) === debeExistir);
  await evidencia(world, `Base de datos: ${r.total} registro(s) en ${tabla}`, r.consulta, r.filas);
  if ((r.total > 0) !== debeExistir) {
    throw new Error(debeExistir
      ? `No existe ningún registro en "${tabla}" donde ${describirCond(cond)}.`
      : `Existen ${r.total} registro(s) en "${tabla}" donde ${describirCond(cond)} y no debería haber ninguno.`);
  }
}

Then('existe en la base de datos un registro en {string} donde {string} es {string}', async function (tabla: string, campo: string, valor: string) {
  await verificarExiste(this, undefined, true, tabla, condiciones(campo, valor));
});
Then('existe en la base de datos {string} un registro en {string} donde {string} es {string}', async function (conexion: string, tabla: string, campo: string, valor: string) {
  await verificarExiste(this, conexion, true, tabla, condiciones(campo, valor));
});
Then('no existe en la base de datos un registro en {string} donde {string} es {string}', async function (tabla: string, campo: string, valor: string) {
  await verificarExiste(this, undefined, false, tabla, condiciones(campo, valor));
});
Then('no existe en la base de datos {string} un registro en {string} donde {string} es {string}', async function (conexion: string, tabla: string, campo: string, valor: string) {
  await verificarExiste(this, conexion, false, tabla, condiciones(campo, valor));
});

// ------------------------------------------------------------------ valores de un registro
async function verificarRegistro(world: any, conexion: string | undefined, tabla: string, campo: string, valor: string, t: DataTable) {
  const cond = condiciones(campo, valor);
  const esperados = desdeTabla(t);
  const cumple = (r: any) => r.total === 1 && esperados.every((e) => coincide(r.filas[0]?.[e.campo], e.valor));
  const r = await esperarBusqueda(conexion, tabla, cond, cumple);
  await evidencia(world, `Base de datos: registro de ${tabla}`, r.consulta, r.filas);
  if (r.total === 0) throw new Error(`No existe ningún registro en "${tabla}" donde ${describirCond(cond)}.`);
  if (r.total > 1) throw new Error(`Hay ${r.total} registros en "${tabla}" donde ${describirCond(cond)}; el filtro tiene que identificar uno solo.`);
  const fila = r.filas[0];
  const errores = esperados.filter((e) => !coincide(fila[e.campo], e.valor)).map((e) => {
    if (!(e.campo in fila)) return `el campo "${e.campo}" no existe en "${tabla}"`;
    const real = bd.esSensible(e.campo) ? '****' : JSON.stringify(fila[e.campo]);
    return `"${e.campo}" es ${real} y se esperaba "${e.valor}"`;
  });
  if (errores.length) throw new Error(`Registro de "${tabla}" donde ${describirCond(cond)}: ${errores.join('; ')}.`);
}

Then('el registro de {string} donde {string} es {string} tiene:', async function (tabla: string, campo: string, valor: string, t: DataTable) {
  await verificarRegistro(this, undefined, tabla, campo, valor, t);
});
Then('en la base de datos {string} el registro de {string} donde {string} es {string} tiene:', async function (conexion: string, tabla: string, campo: string, valor: string, t: DataTable) {
  await verificarRegistro(this, conexion, tabla, campo, valor, t);
});

// ------------------------------------------------------------------ consulta libre (solo lectura)
async function consultar(world: any, conexion: string | undefined, texto: string) {
  const q = interpolar(texto.trim());
  const c = bd.config(conexion);
  if (c.motor === 'mongodb') {
    let o: any;
    try { o = JSON.parse(q); } catch { throw new Error('En MongoDB la consulta es un JSON: {"coleccion": "...", "filtro": {...}}'); }
    ultimaConsulta = await bd.mongo(conexion, o);
  } else {
    ultimaConsulta = await bd.sql(conexion, q, []);
  }
  await evidencia(world, `Base de datos: consulta (${ultimaConsulta!.filas.length} filas)`, q, ultimaConsulta!.filas);
}

const consulta = (): Resultado => {
  if (!ultimaConsulta) throw new Error('Todavía no se hizo ninguna consulta a la base de datos en este escenario.');
  return ultimaConsulta;
};

When('consulto en la base de datos:', async function (texto: string) { await consultar(this, undefined, texto); });
When('consulto en la base de datos {string}:', async function (conexion: string, texto: string) { await consultar(this, conexion, texto); });

Then('la consulta devuelve {int} fila(s)', function (n: number) {
  const total = consulta().filas.length;
  if (total !== n) throw new Error(`La consulta devolvió ${total} fila(s) y se esperaban ${n}.`);
});
Then('la consulta devuelve al menos {int} fila(s)', function (n: number) {
  const total = consulta().filas.length;
  if (total < n) throw new Error(`La consulta devolvió ${total} fila(s) y se esperaban al menos ${n}.`);
});
Then('el campo {string} de la consulta es {string}', function (campo: string, valor: string) {
  const fila = consulta().filas[0];
  if (!fila) throw new Error('La consulta no devolvió filas.');
  const esperado = interpolar(valor);
  if (!coincide(fila[campo], esperado)) {
    throw new Error(`"${campo}" es ${bd.esSensible(campo) ? '****' : JSON.stringify(fila[campo])} y se esperaba "${esperado}".`);
  }
});
When('guardo el campo {string} de la consulta como {string}', function (campo: string, nombre: string) {
  const fila = consulta().filas[0];
  if (!fila || !(campo in fila)) throw new Error(`La consulta no tiene el campo "${campo}".`);
  variables[nombre] = fila[campo];
});

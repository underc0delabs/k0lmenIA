#!/usr/bin/env node
// tools/bd/cli.js — consultas a bases de datos para el agente verificador-datos.
//
// Desde herramientas/k0lmena:   npm run bd -- <comando> [opciones]
//
//   conexiones                                 lista las conexiones del .env y las prueba
//   esquema    [--bd X] [--tabla T]            tablas (o colecciones) y columnas de una tabla
//   consultar  [--bd X] --sql "SELECT ..." [--param V]...          SQL de solo lectura
//   consultar  [--bd X] --coleccion C [--operacion find] [--filtro JSON] [--proyeccion JSON]
//              [--orden JSON] [--pipeline JSON] [--campo C]         MongoDB (lectura)
//   existe     [--bd X] --tabla T --donde campo=valor [--donde ...] ¿hay registros? (valor "(nulo)" = NULL)
//   escribir   [--bd X] --sql "UPDATE ..." --confirmar              escritura (requiere DB_X_ESCRITURA=si)
//   escribir   [--bd X] --coleccion C --operacion updateMany --filtro JSON --cambios JSON --confirmar
//
//   --max N           filas a mostrar (default DB_FILAS_MAX o 50)
//   --formato tabla|json|md   (default tabla)
//   Cualquier valor que empiece con @ se lee de un archivo: --sql @consulta.sql --filtro @filtro.json
//
// Las columnas sensibles (password, token, clave, hash, tarjeta, …) se muestran como ****.
'use strict';
const fs = require('fs');
const bd = require('./index');

function leerArgs(argv) {
  const pos = [], o = { param: [], donde: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { pos.push(a); continue; }
    const k = a.slice(2);
    if (k === 'confirmar') { o.confirmar = true; continue; }
    let v = argv[++i];
    if (v === undefined) throw new bd.ErrorBD(`Falta el valor de --${k}.`);
    if (v.startsWith('@') && fs.existsSync(v.slice(1))) v = fs.readFileSync(v.slice(1), 'utf8');
    if (k === 'param' || k === 'donde') o[k].push(v); else o[k] = v;
  }
  return { comando: pos[0], o };
}

const json = (texto, nombre) => {
  if (texto === undefined) return undefined;
  try { return JSON.parse(texto); } catch (e) { throw new bd.ErrorBD(`--${nombre} no es JSON válido: ${e.message}`); }
};

function celda(v) {
  if (v === null || v === undefined) return 'NULL';
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
  return s.length > 60 ? s.slice(0, 57) + '...' : s;
}

function imprimir(titulo, columnas, filas, formato, max, extra = '') {
  const total = filas.length;
  const visibles = bd.enmascarar(filas.slice(0, max));
  if (formato === 'json') {
    console.log(JSON.stringify({ titulo, columnas, filas: visibles, total, truncado: total > max, ...(extra ? { nota: extra } : {}) }, null, 2));
    return;
  }
  const cols = columnas.length ? columnas : [...new Set(visibles.flatMap((f) => Object.keys(f)))];
  console.log(titulo);
  if (!cols.length || !visibles.length) { console.log('(sin filas)'); if (extra) console.log(extra); return; }
  const datos = visibles.map((f) => cols.map((c) => celda(f[c])));
  if (formato === 'md') {
    console.log(`| ${cols.join(' | ')} |\n| ${cols.map(() => '---').join(' | ')} |`);
    datos.forEach((d) => console.log(`| ${d.map((x) => x.replace(/\|/g, '\\|')).join(' | ')} |`));
  } else {
    const anchos = cols.map((c, i) => Math.max(c.length, ...datos.map((d) => d[i].length)));
    const linea = (vals) => vals.map((v, i) => v.padEnd(anchos[i])).join('  ');
    console.log(linea(cols)); console.log(anchos.map((a) => '-'.repeat(a)).join('  '));
    datos.forEach((d) => console.log(linea(d)));
  }
  console.log(`${total > max ? `Mostrando ${max} de ${total} filas` : `${total} fila${total === 1 ? '' : 's'}`}${extra ? ` · ${extra}` : ''}`);
}

async function main() {
  const { comando, o } = leerArgs(process.argv.slice(2));
  const formato = o.formato || 'tabla';
  const max = Number(o.max) || bd.FILAS_MAX();

  switch (comando) {
    case 'conexiones': {
      const filas = [];
      for (const n of bd.nombresConexiones()) {
        try { const r = await bd.probar(n); filas.push({ ...r, estado: `OK (${r.ms} ms)` }); } catch (e) {
          let d = {}; try { d = bd.describir(bd.config(n)); } catch { d = { nombre: n }; }
          filas.push({ ...d, estado: `ERROR: ${e.message}` });
        }
      }
      if (!filas.length) throw new bd.ErrorBD('No hay conexiones: definí DB_CONEXIONES y DB_<NOMBRE>_* en el .env de la raíz.');
      imprimir('Conexiones', ['nombre', 'motor', 'destino', 'escritura', 'produccion', 'estado'], filas.map((f) => ({ ...f, escritura: f.escritura ? 'si' : 'no', produccion: f.produccion ? 'si' : 'no' })), formato, 100);
      break;
    }
    case 'esquema': {
      const r = await bd.esquema(o.bd, o.tabla);
      imprimir(`Esquema · ${r.tipo}`, [], r.filas, formato, 500);
      break;
    }
    case 'consultar':
    case 'escribir': {
      const escribir = comando === 'escribir';
      const opciones = { escribir, confirmado: !!o.confirmar };
      let r;
      if (o.coleccion) {
        r = await bd.mongo(o.bd, {
          coleccion: o.coleccion, operacion: o.operacion || 'find', filtro: json(o.filtro, 'filtro'),
          proyeccion: json(o.proyeccion, 'proyeccion'), orden: json(o.orden, 'orden'), pipeline: json(o.pipeline, 'pipeline'),
          campo: o.campo, documento: json(o.documento, 'documento'), cambios: json(o.cambios, 'cambios'), limite: max + 1,
        }, opciones);
      } else if (o.sql) {
        r = await bd.sql(o.bd, o.sql, o.param, opciones);
      } else {
        throw new bd.ErrorBD('Indicá --sql "..." o --coleccion C.');
      }
      if (r.escritura) console.log(`Escritura confirmada · filas afectadas: ${r.afectadas ?? 0} · ${r.ms} ms`);
      else imprimir(`Resultado (${bd.describir(bd.config(o.bd)).nombre})`, r.columnas, r.filas, formato, max, `${r.ms} ms`);
      break;
    }
    case 'existe': {
      if (!o.tabla || !o.donde.length) throw new bd.ErrorBD('Uso: existe --tabla T --donde campo=valor [--donde campo2=valor2].');
      const condiciones = o.donde.map((d) => {
        const i = d.indexOf('=');
        if (i < 1) throw new bd.ErrorBD(`--donde "${d}" tiene que ser campo=valor.`);
        return { campo: d.slice(0, i).trim(), valor: d.slice(i + 1) };
      });
      const r = await bd.buscar(o.bd, o.tabla, condiciones, Math.min(max, 5));
      console.log(`${r.total > 0 ? 'EXISTE' : 'NO EXISTE'} · ${r.total} registro${r.total === 1 ? '' : 's'} en ${o.tabla} donde ${condiciones.map((c) => `${c.campo} = ${c.valor}`).join(' y ')}`);
      if (r.filas.length) imprimir('Primeros registros', [], r.filas, formato, 5);
      break;
    }
    default:
      console.log('Uso: npm run bd -- <conexiones | esquema | consultar | existe | escribir> [opciones]  (ver tools/bd/cli.js)');
      process.exitCode = comando ? 2 : 0;
  }
}

main()
  .catch((e) => {
    console.error(e instanceof bd.ErrorBD ? `Error: ${e.message}` : `Error de la base de datos: ${e.message}`);
    process.exitCode = 1;
  })
  .finally(() => bd.cerrarTodo());

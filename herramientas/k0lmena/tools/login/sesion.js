// Sesión guardada del navegador (npm run login): dónde se guarda y cuándo se usa.
//
// La comparten las suites web de k0lmena (web/hooks/hook.ts) y el navegador de los agentes
// (scripts/mcp/playwright.js), así que vive en la raíz del repo: .auth/ (gitignored).
//   .auth/sesion.json            la sesión por defecto
//   .auth/sesion-<nombre>.json   una por rol o usuario (npm run login -- --nombre admin)
//
// SESION en el .env decide si se usa:
//   vacío / 0 / no / off   -> no se usa (cada escenario arranca sin sesión)
//   si / on / 1 / true     -> .auth/sesion.json
//   <nombre>               -> .auth/sesion-<nombre>.json
// Sin dependencias: lo carga también el lanzador del MCP, que no tiene node_modules.
const fs = require('fs');
const path = require('path');

// La sesión (.auth/) es del proyecto: ver ../rutas.js.
const { PROYECTO: RAIZ } = require('../rutas');
const CARPETA = path.join(RAIZ, '.auth');
const NOMBRE_VALIDO = /^[\w-]+$/;

const APAGADO = ['', '0', 'no', 'off', 'false'];
const POR_DEFECTO = ['si', 'sí', 'on', '1', 'true', 'yes'];

/** Ruta absoluta del archivo de sesión de <nombre> (o el por defecto, sin nombre). */
function archivoSesion(nombre) {
  if (!nombre) return path.join(CARPETA, 'sesion.json');
  if (!NOMBRE_VALIDO.test(nombre)) throw new Error(`nombre de sesión inválido: "${nombre}" (solo letras, números, - y _)`);
  return path.join(CARPETA, `sesion-${nombre}.json`);
}

/** Qué sesión pide SESION: null si está apagada; si no, { nombre, archivo }. */
function sesionPedida(valor) {
  const v = String(valor ?? '').trim();
  if (APAGADO.includes(v.toLowerCase())) return null;
  const nombre = POR_DEFECTO.includes(v.toLowerCase()) ? '' : v;
  return { nombre, archivo: archivoSesion(nombre) };
}

/**
 * Archivo a usar según SESION, o null si está apagada. Si la pidieron pero el archivo no existe,
 * avisa (una vez) con `avisar` y devuelve null: la corrida sigue sin sesión en vez de cortarse.
 */
function sesionActiva(valor, avisar = () => {}) {
  const pedida = sesionPedida(valor);
  if (!pedida) return null;
  if (!fs.existsSync(pedida.archivo)) {
    const como = pedida.nombre ? `npm run login -- --nombre ${pedida.nombre}` : 'npm run login';
    avisar(`SESION=${String(valor).trim()} pero no existe ${path.relative(RAIZ, pedida.archivo)}: se sigue sin sesión. Guardala con "${como}".`);
    return null;
  }
  return pedida.archivo;
}

module.exports = { RAIZ, CARPETA, archivoSesion, sesionPedida, sesionActiva };

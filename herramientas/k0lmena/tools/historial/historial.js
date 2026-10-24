// Historial de corridas: antes de una corrida nueva, la anterior se MUEVE a <carpeta>/historial/<fecha-hora>/
// con su JSON, su análisis, su informe y su evidencia (capturas, videos, traces…), así su informe se sigue
// abriendo igual y se puede comparar. Se guardan las últimas 5 (4 anteriores + la actual).
//
// Misma lógica que scripts/_historial.py (que además arma la sección "Evolución de las corridas" de los informes).
const fs = require('fs');
const path = require('path');

const MAX_CORRIDAS = Number(process.env.HISTORIAL_CORRIDAS) > 0 ? Number(process.env.HISTORIAL_CORRIDAS) : 5;
const CARPETA = 'historial';

function sello(archivoDatos) {
  let f = null;
  try {
    const d = JSON.parse(fs.readFileSync(archivoDatos, 'utf8'));
    f = (!Array.isArray(d) && (d.marca || d.fecha)) || null;
  } catch { /* JSON ilegible: se usa la fecha del archivo */ }
  if (!f) {
    const m = fs.statSync(archivoDatos).mtime;
    f = new Date(m.getTime() - m.getTimezoneOffset() * 60000).toISOString().slice(0, 19);
  }
  return String(f).replace(/[^0-9A-Za-z-]+/g, '-').slice(0, 19).replace(/^-+|-+$/g, '');
}

function mover(origen, destino) {
  try {
    fs.renameSync(origen, destino);
  } catch (e) {
    if (e.code !== 'EXDEV' && e.code !== 'EPERM' && e.code !== 'EBUSY') throw e;
    fs.cpSync(origen, destino, { recursive: true });
    fs.rmSync(origen, { recursive: true, force: true });
  }
}

// Mueve la corrida anterior (los `nombres` que existan) a historial/<sello>/ y deja solo las últimas.
// archivoDatos: el JSON de la corrida (de él sale la fecha); si no existe, no hay corrida que guardar.
function archivar(carpeta, nombres, archivoDatos, maxCorridas = MAX_CORRIDAS) {
  const datos = path.join(carpeta, archivoDatos);
  if (!fs.existsSync(datos) || fs.statSync(datos).size <= 4) return null; // no hubo corrida ("[]" o vacío)
  const base = path.join(carpeta, CARPETA, sello(datos));
  let destino = base;
  for (let n = 2; fs.existsSync(destino); n++) destino = `${base}-${n}`;
  fs.mkdirSync(destino, { recursive: true });
  // Cada informe HTML va con su versión en inglés (informe.en.html, scripts/_i18n.py) aunque la lista no la nombre.
  const todos = [...new Set(nombres.flatMap((n) => (/\.html$/i.test(n) && !/\.en\.html$/i.test(n) ? [n, n.replace(/\.html$/i, '.en.html')] : [n])))];
  for (const nombre of todos) {
    const src = path.join(carpeta, nombre);
    if (fs.existsSync(src)) mover(src, path.join(destino, nombre));
  }
  podar(carpeta, maxCorridas - 1);
  return destino;
}

function podar(carpeta, guardar) {
  const dir = path.join(carpeta, CARPETA);
  if (!fs.existsSync(dir)) return;
  const corridas = fs.readdirSync(dir, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name).sort();
  for (const viejo of corridas.slice(0, Math.max(0, corridas.length - guardar))) {
    fs.rmSync(path.join(dir, viejo), { recursive: true, force: true });
  }
}

module.exports = { archivar, podar, sello, MAX_CORRIDAS, CARPETA };

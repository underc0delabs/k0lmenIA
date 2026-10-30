#!/usr/bin/env node
// Lanzador de los scripts de Python para los `npm run` de package.json: elige `python` (Windows) o `python3`
// (Mac y Linux), corre el script desde la raíz del repo con los argumentos que vengan después y devuelve su
// código de salida.
//   "doctor": "node scripts/py.js scripts/doctor.py"   →   npm run doctor -- --rapido
const { spawnSync } = require('child_process');
const path = require('path');

const [script, ...args] = process.argv.slice(2);
if (!script) {
  console.error('Uso: node scripts/py.js <script.py> [argumentos]');
  process.exit(2);
}
const raiz = path.resolve(__dirname, '..');
const python = process.platform === 'win32' ? 'python' : 'python3';
const r = spawnSync(python, [path.resolve(raiz, script), ...args], { stdio: 'inherit', cwd: process.cwd() });
if (r.error) {
  console.error(`No pude ejecutar ${python}: ${r.error.message}. ¿Está instalado Python 3 y en el PATH? (npm run doctor)`);
  process.exit(1);
}
process.exit(r.status === null ? 1 : r.status);

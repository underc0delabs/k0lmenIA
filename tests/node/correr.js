// Corre todos los tests de Node del repo (tests/node/*.test.js) con el runner nativo.
// Busca los archivos acá en vez de usar un patrón glob, que `node --test` recién acepta desde Node 21.
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const archivos = fs.readdirSync(__dirname).filter((f) => f.endsWith('.test.js')).map((f) => path.join(__dirname, f));
const r = spawnSync(process.execPath, ['--test', ...archivos], { stdio: 'inherit' });
process.exit(r.status === null ? 1 : r.status);

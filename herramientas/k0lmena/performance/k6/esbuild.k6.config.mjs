// performance/k6/esbuild.k6.config.mjs
// Compila los scripts TypeScript de k6 (performance/k6/http/*.ts) a performance/k6/dist/.
// Uso: node performance/k6/esbuild.k6.config.mjs [script.ts ...]   (sin argumentos: todos)

import { build } from 'esbuild';
import { globby } from 'globby';
import path from 'node:path';
import fs from 'node:fs';

const pedidos = process.argv.slice(2);
const archivos = pedidos.length ? pedidos : await globby('performance/k6/http/*.ts');

const entries = archivos.map((f) => ({
  in: f,
  out: path.join('performance/k6/dist', path.relative('performance/k6', f)).replace(/\.ts$/, '.js'),
}));

for (const e of entries) fs.mkdirSync(path.dirname(e.out), { recursive: true });

// Módulos nativos de k6 (se resuelven en runtime) y librerías remotas de jslib.k6.io
const K6_EXTERNAL = ['k6', 'k6/*', 'https://*'];

await Promise.all(
  entries.map((e) =>
    build({
      entryPoints: [e.in],
      outfile: e.out,
      bundle: true,
      platform: 'neutral',
      format: 'esm',
      target: ['es2020'],
      sourcemap: false,
      logLevel: 'error',
      external: K6_EXTERNAL,
    }),
  ),
);

console.log(`k6: ${entries.length} script(s) compilado(s) en performance/k6/dist/`);

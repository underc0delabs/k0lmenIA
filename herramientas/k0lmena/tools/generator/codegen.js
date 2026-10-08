#!/usr/bin/env node
/**
 * tools/generator/codegen.js
 *
 * Lee BASEURL de tu .env (en la raíz del proyecto)
 * y lanza playwright codegen apuntando a esa URL.
 */

const { execSync } = require('child_process');
require('dotenv').config();  // carga .env desde process.cwd()

// 1️⃣ Obtener la URL desde .env
const url = process.env.BASEURL;
if (!url) {
  console.error('⚠️ ERROR: La variable BASEURL no está definida en tu .env');
  process.exit(1);
}

// 2️⃣ Parámetros de la llamada
const outputPath = 'tools/generator/gen.ts';
const target     = 'javascript';

// 3️⃣ Construir y ejecutar el comando
const cmd = `npx playwright codegen ${url} --target=${target} --output=${outputPath}`;
console.log(`\n⚡️ Ejecutando: ${cmd}\n`);
try {
  execSync(cmd, { stdio: 'inherit' });
} catch (e) {
  console.error('\n❌ Falló la ejecución de Playwright Codegen\n', e.message);
  process.exit(1);
}

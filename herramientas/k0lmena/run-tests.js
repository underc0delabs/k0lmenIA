// Runner de k0lmena: corre las suites sin intervención (y sin agentes).
//
//   npm test                 -> web + api
//   npm test -- web          -> solo web        (también: npm run test:web)
//   npm test -- api          -> solo api
//   npm test -- mobile       -> solo mobile (Appium / emulador / BrowserStack, ver .env)
//   npm test -- all          -> web + api + mobile
//
// Filtrar por tag: TAGS=@HU-001 npm test   (PowerShell: $env:TAGS="@HU-001"; npm test)
// Sale con código != 0 si alguna suite falla, pero siempre corre todas las pedidas.
const { spawnSync } = require('child_process');
// Carga el .env de la raíz de k0lmenIA; las suites (procesos hijos) heredan las variables.
require('./env');

const SUITES = {
  web: 'npx cucumber-js --profile web',
  api: 'npx cucumber-js --profile api',
  mobile: 'npx wdio run mobile/support/wdio.conf.ts',
};

const arg = (process.argv[2] || 'default').toLowerCase();
const plan = {
  default: ['web', 'api'],
  all: ['web', 'api', 'mobile'],
}[arg] || [arg];

const unknown = plan.filter((s) => !SUITES[s]);
if (unknown.length) {
  console.error(`Suite desconocida: ${unknown.join(', ')}. Opciones: web | api | mobile | all`);
  process.exit(2);
}

// Evidencias de la corrida anterior: el reporte solo describe la última, así que se limpian.
const path = require('path');
const fs = require('fs');
const CLEAN = {
  web: ['screenshots', 'traces', 'videos', 'evidencias'].map((d) =>
    path.resolve(__dirname, process.env.REPORT_DIR || 'reports/web', d)
  ),
  mobile: ['html/videos', 'evidencias', 'screenshots'].map((d) => path.join(__dirname, 'reports/mobile', d)),
};

const results = plan.map((suite) => {
  console.log(`\n=== k0lmena: suite ${suite} ===`);
  for (const dir of CLEAN[suite] || []) fs.rmSync(dir, { recursive: true, force: true });
  const { status } = spawnSync(SUITES[suite], { stdio: 'inherit', shell: true });
  return { suite, ok: status === 0 };
});

console.log('\n=== Resumen ===');
for (const r of results) console.log(`${r.suite.padEnd(7)} ${r.ok ? 'OK' : 'FALLÓ'}`);
process.exit(results.every((r) => r.ok) ? 0 : 1);

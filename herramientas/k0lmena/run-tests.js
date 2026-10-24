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
  web: ['screenshots', 'traces', 'videos', 'evidencias', 'dom'].map((d) =>
    path.resolve(__dirname, process.env.REPORT_DIR || 'reports/web', d)
  ),
  mobile: ['html/videos', 'html/evidencias', 'evidencias', 'screenshots'].map((d) => path.join(__dirname, 'reports/mobile', d)),
};

const { archivar } = require('./tools/historial/historial.js');
const dirWeb = path.resolve(__dirname, process.env.REPORT_DIR || 'reports/web');
const HISTORIAL = {
  web: { dir: dirWeb, nombres: ['cucumber-report.json', 'front-report.html', 'index.html', 'features', 'screenshots', 'traces', 'videos', 'evidencias', 'dom'] },
  api: { dir: path.join(__dirname, 'reports/api'), nombres: ['cucumber-report.json', 'api-report.html', 'index.html', 'features'] },
  mobile: { dir: path.join(__dirname, 'reports/mobile'), nombres: ['cucumber-report.json', 'html', 'evidencias', 'screenshots'] },
};

// Evidencia de los tests que pasan: si EVIDENCE no está en el .env, se pregunta (solo en una
// terminal interactiva; en CI o sin terminal queda "captura").
function preguntarEvidencia() {
  if ((process.env.EVIDENCE ?? '').trim()) return Promise.resolve();
  if (!process.stdin.isTTY || process.env.CI || !plan.some((s) => s === 'web' || s === 'mobile')) {
    process.env.EVIDENCE = 'captura';
    return Promise.resolve();
  }
  const rl = require('readline').createInterface({ input: process.stdin, output: process.stdout });
  const texto =
    '\n¿Qué evidencia guardo de los tests que pasan?\n' +
    '  1) Solo captura\n' +
    '  2) Captura + GIF del recorrido (suma ~0,5 s por escenario)\n' +
    'Opción [1]: ';
  return new Promise((resolver) =>
    rl.question(texto, (r) => {
      rl.close();
      process.env.EVIDENCE = r.trim() === '2' ? 'ambos' : 'captura';
      console.log(`Evidencia: ${process.env.EVIDENCE === 'ambos' ? 'captura + GIF' : 'solo captura'}` +
        ' (para no preguntar, fijá EVIDENCE en el .env de la raíz)');
      resolver();
    })
  );
}

// Reporte completo (multiple-cucumber-html-reporter con el tema de k0lmenIA, el de `npm run report:<suite>`):
// se arma solo al terminar cada suite, así el portal de informes enlaza ese y no el HTML básico de Cucumber.
const REPORTES = {
  web: { json: path.join(dirWeb, 'cucumber-report.json'), cmd: 'node reports/web/report-generator.js' },
  api: { json: path.join(__dirname, 'reports/api/cucumber-report.json'), cmd: 'node reports/api/report-generator.js' },
};

function generarReporte(suite) {
  const r = REPORTES[suite];
  if (!r || !fs.existsSync(r.json) || fs.statSync(r.json).size <= 4) return; // sin escenarios no hay reporte
  const { status } = spawnSync(r.cmd, { stdio: 'inherit', shell: true, cwd: __dirname });
  if (status !== 0) console.error(`[k0lmena] No se pudo generar el reporte de ${suite}; queda el básico de Cucumber.`);
}

function correr() {
  const results = plan.map((suite) => {
    console.log(`\n=== k0lmena: suite ${suite} ===`);
    // La corrida anterior (reporte + evidencia) pasa a historial/ (últimas 5) en vez de borrarse.
    const h = HISTORIAL[suite];
    if (h) archivar(h.dir, h.nombres, 'cucumber-report.json');
    for (const dir of CLEAN[suite] || []) fs.rmSync(dir, { recursive: true, force: true });
    const { status } = spawnSync(SUITES[suite], { stdio: 'inherit', shell: true });
    generarReporte(suite);
    return { suite, ok: status === 0 };
  });

  console.log('\n=== Resumen ===');
  for (const r of results) console.log(`${r.suite.padEnd(7)} ${r.ok ? 'OK' : 'FALLÓ'}`);
  process.exit(results.every((r) => r.ok) ? 0 : 1);
}

preguntarEvidencia().then(correr);

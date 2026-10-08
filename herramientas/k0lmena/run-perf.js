// run-perf.js — runner de `npm run perf` (k6 y Artillery, en Windows, Linux, macOS y CI).
//
//   npm run perf                                   lista los scripts disponibles
//   npm run perf -- <script> [perfil] [opciones]
//
//   script   nombre sin extensión: performance/k6/http/<script>.ts o performance/artillery/<script>.yaml
//   perfil   smoke (default) | load | stress | soak | spike
//   --confirmar        no pregunta antes de un perfil con carga (para CI o para el agente,
//                      que ya lo confirmó con la persona)
//   --vus N --duracion 2m   (solo k6) pisan la carga del script en esta corrida
//
// Salida en reports/performance/<herramienta>/: reporte HTML, resumen JSON (chico), resultado
// crudo y log. La consola muestra solo el resumen; el detalle de la herramienta queda en el log.
require('./env');
const fs = require('fs');
const path = require('path');
const { spawn, spawnSync } = require('child_process');
const { generarReporte } = require('./reports/performance/generar-reporte');

const RAIZ = __dirname;
const PERFILES = ['smoke', 'load', 'stress', 'soak', 'spike'];
const DIR_K6 = path.join(RAIZ, 'performance/k6/http');
const DIR_ART = path.join(RAIZ, 'performance/artillery');
const rel = (p) => path.relative(RAIZ, p).split(path.sep).join('/');

function salir(msg, codigo = 2) {
  console.error(msg);
  process.exit(codigo);
}

function listar() {
  const k6 = fs.existsSync(DIR_K6) ? fs.readdirSync(DIR_K6).filter((f) => f.endsWith('.ts')).map((f) => f.slice(0, -3)) : [];
  const art = fs.existsSync(DIR_ART) ? fs.readdirSync(DIR_ART).filter((f) => /\.ya?ml$/.test(f)).map((f) => f.replace(/\.ya?ml$/, '')) : [];
  console.log('Scripts de performance:\n');
  if (!k6.length && !art.length) console.log('  (todavía no hay: los genera el agente performance-mapper)');
  for (const s of k6) console.log(`  k6         ${s}`);
  for (const s of art) console.log(`  artillery  ${s}`);
  console.log(`\nUso: npm run perf -- <script> [${PERFILES.join('|')}] [--confirmar]`);
}

// ------------------------------------------------------------ argumentos
const args = process.argv.slice(2);
const flags = {};
const pos = [];
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--confirmar') flags.confirmar = true;
  else if (a === '--vus' || a === '--duracion') flags[a.slice(2)] = args[++i];
  else pos.push(a);
}
if (!pos.length) {
  listar();
  process.exit(0);
}
const nombre = path.basename(pos[0]).replace(/\.(ts|js|ya?ml)$/, '');
const perfil = (pos[1] || 'smoke').toLowerCase();
if (!PERFILES.includes(perfil)) salir(`Perfil desconocido "${perfil}". Opciones: ${PERFILES.join(', ')}.`);

let herramienta, fuente;
if (fs.existsSync(path.join(DIR_K6, `${nombre}.ts`))) {
  herramienta = 'k6';
  fuente = path.join(DIR_K6, `${nombre}.ts`);
} else {
  const yml = ['yaml', 'yml'].map((e) => path.join(DIR_ART, `${nombre}.${e}`)).find((f) => fs.existsSync(f));
  if (!yml) salir(`No encontré el script "${nombre}" en performance/k6/http/ ni en performance/artillery/. Corré "npm run perf" para ver la lista.`);
  herramienta = 'artillery';
  fuente = yml;
}

// ------------------------------------------------------------ destino (para mostrar y confirmar)
function destino() {
  const texto = fs.readFileSync(fuente, 'utf8');
  if (herramienta === 'artillery') {
    const yaml = require('js-yaml');
    const cfg = (yaml.load(texto) || {}).config || {};
    const envs = cfg.environments || {};
    if (!envs[perfil]) salir(`${rel(fuente)} no define el perfil "${perfil}" (config.environments.${perfil}).`);
    return (envs[perfil] && envs[perfil].target) || cfg.target || '—';
  }
  const destinos = [];
  if (/env\.API_BASEURL/.test(texto) && process.env.API_BASEURL) destinos.push(process.env.API_BASEURL);
  if (/env\.BASEURL/.test(texto) && process.env.BASEURL) destinos.push(process.env.BASEURL);
  if (!destinos.length) destinos.push(...new Set(texto.match(/https?:\/\/[^\s'"`/]+/g) || []));
  return destinos.join(', ') || '—';
}
const target = destino();

function confirmar() {
  if (perfil === 'smoke' || flags.confirmar) return Promise.resolve();
  const aviso = `Perfil "${perfil}" contra ${target}: genera carga real sobre ese sistema.`;
  if (!process.stdin.isTTY || process.env.CI) {
    salir(`${aviso}\nPara correrlo sin terminal interactiva agregá --confirmar (solo con autorización de los dueños del sistema).`);
  }
  const rl = require('readline').createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((ok) =>
    rl.question(`${aviso}\n¿Confirmás? (s/N): `, (r) => {
      rl.close();
      if (!/^s(i|í)?$/i.test(r.trim())) salir('Cancelado.', 1);
      ok();
    })
  );
}

// ------------------------------------------------------------ ejecución
function sello() {
  const d = new Date(), p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

function binarioK6() {
  for (const f of ['tools/k6/k6.exe', 'tools/k6/k6']) if (fs.existsSync(path.join(RAIZ, f))) return path.join(RAIZ, f);
  const r = spawnSync(process.platform === 'win32' ? 'where' : 'which', ['k6'], { encoding: 'utf8' });
  if (r.status === 0 && r.stdout.trim()) return 'k6';
  salir('No encuentro k6. Instalalo con "npm run bootstrap:k6" (queda en tools/k6) o tenelo en el PATH.');
}

function correr(cmd, cmdArgs, env, logFile) {
  return new Promise((resolver) => {
    const log = fs.createWriteStream(logFile);
    const verEnVivo = process.stdout.isTTY && !process.env.CI;
    const hijo = spawn(cmd, cmdArgs, { cwd: RAIZ, env, shell: process.platform === 'win32' && cmd === 'npx' });
    const escribir = (d) => {
      log.write(d);
      if (verEnVivo) process.stdout.write(d);
    };
    hijo.stdout.on('data', escribir);
    hijo.stderr.on('data', escribir);
    hijo.on('error', (e) => {
      log.write(String(e));
      log.end(() => resolver(1));
    });
    hijo.on('close', (codigo) => log.end(() => resolver(codigo ?? 1)));
  });
}

async function main() {
  await confirmar();
  const ts = sello();
  const dir = path.join(RAIZ, 'reports/performance', herramienta);
  fs.mkdirSync(dir, { recursive: true });
  const base = path.join(dir, `${nombre}-${perfil}-${ts}`);
  const crudo = `${base}-crudo.json`;
  const logFile = `${base}.log`;
  const env = { ...process.env, PERFIL: perfil };

  console.log(`Performance: ${nombre} · ${herramienta} · perfil ${perfil} · destino ${target}`);
  console.log(`Log de la herramienta: ${rel(logFile)}`);
  const inicio = Date.now();
  let codigo;

  if (herramienta === 'k6') {
    const k6 = binarioK6();
    const b = spawnSync(process.execPath, ['performance/k6/esbuild.k6.config.mjs', rel(fuente)], { cwd: RAIZ, encoding: 'utf8' });
    if (b.status !== 0) salir(`No compila ${rel(fuente)}:\n${b.stderr || b.stdout}`);
    if (flags.vus) env.PERF_VUS = flags.vus;
    if (flags.duracion) env.PERF_DURACION = flags.duracion;
    env.K0LMENA_PERF_SALIDA = crudo;
    const dist = path.join(RAIZ, 'performance/k6/dist/http', `${nombre}.js`);
    codigo = await correr(k6, ['run', '--no-color', dist], env, logFile);
  } else {
    if (flags.vus || flags.duracion) console.log('Aviso: --vus y --duracion son solo para k6; en Artillery la carga está en las fases del .yaml.');
    const bin = path.join(RAIZ, 'node_modules/artillery/bin/run');
    codigo = await correr(process.execPath, [bin, 'run', rel(fuente), '--environment', perfil, '--output', crudo], { ...env, NO_COLOR: '1' }, logFile);
  }

  const r = generarReporte({ herramienta, script: nombre, perfil, destino: target, crudo, log: logFile, salida: base, codigoSalida: codigo });

  // Resumen corto en consola (es lo que lee el agente).
  const k = r.kpis, l = r.latencia;
  const f = (x, u = '') => (x == null ? '—' : `${Math.round(x * 100) / 100}${u}`);
  console.log(`\nResultado: ${r.veredicto.toUpperCase()} (${Math.round((Date.now() - inicio) / 1000)} s)`);
  if (r.error) console.log(`  ${r.error}`);
  console.log(`  requests ${f(k.requests)} · req/s ${f(k.rps)} · errores ${f(k.error_pct, ' %')}`);
  console.log(`  latencia (${l.fuente}): p50 ${f(l.p50, ' ms')} · p95 ${f(l.p95, ' ms')} · p99 ${f(l.p99, ' ms')} · máx ${f(l.max, ' ms')}`);
  for (const u of r.umbrales) console.log(`  ${u.ok ? 'cumple   ' : 'NO CUMPLE'}  ${u.metrica}: ${u.condicion} (medido ${u.valor})`);
  const errores = Object.entries(r.errores);
  if (errores.length) console.log(`  errores: ${errores.slice(0, 5).map(([e, n]) => `${e} x${n}`).join(' · ')}`);
  console.log(`Reporte: ${rel(r.archivos.html)}`);
  console.log(`Resumen: ${rel(r.archivos.resumen)}`);
  process.exit(r.veredicto === 'cumple' || r.veredicto === 'sin umbrales' ? 0 : 1);
}

main().catch((e) => salir(e.stack || String(e), 1));

// run-perf.js — runner de `npm run perf` (k6, Artillery y JMeter, en Windows, Linux, macOS y CI).
//
//   npm run perf                                   lista los scripts disponibles
//   npm run perf -- <script> [perfil] [opciones]
//
//   script   nombre sin extensión: performance/k6/http/<script>.ts, performance/artillery/<script>.yaml
//            o performance/jmeter/<script>.jmx (+ <script>.json con destino, perfiles y umbrales)
//   perfil   smoke (default) | load | stress | soak | spike
//   --confirmar        no pregunta antes de un perfil con carga (para CI o para el agente,
//                      que ya lo confirmó con la persona)
//   --vus N --duracion 2m   (k6 y JMeter) pisan la carga del script en esta corrida
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
const DIR_JM = path.join(RAIZ, 'performance/jmeter');
const rel = (p) => path.relative(RAIZ, p).split(path.sep).join('/');

function salir(msg, codigo = 2) {
  console.error(msg);
  process.exit(codigo);
}

function listar() {
  const k6 = fs.existsSync(DIR_K6) ? fs.readdirSync(DIR_K6).filter((f) => f.endsWith('.ts')).map((f) => f.slice(0, -3)) : [];
  const art = fs.existsSync(DIR_ART) ? fs.readdirSync(DIR_ART).filter((f) => /\.ya?ml$/.test(f)).map((f) => f.replace(/\.ya?ml$/, '')) : [];
  const jm = fs.existsSync(DIR_JM) ? fs.readdirSync(DIR_JM).filter((f) => f.endsWith('.jmx')).map((f) => f.slice(0, -4)) : [];
  console.log('Scripts de performance:\n');
  if (!k6.length && !art.length && !jm.length) console.log('  (todavía no hay: los genera el agente performance-mapper)');
  for (const s of k6) console.log(`  k6         ${s}`);
  for (const s of art) console.log(`  artillery  ${s}`);
  for (const s of jm) console.log(`  jmeter     ${s}`);
  console.log(`\nUso: npm run perf -- <script> [${PERFILES.join('|')}] [--confirmar]`);
}

// ------------------------------------------------------------ argumentos
const args = process.argv.slice(2);
const flags = {};
const pos = [];
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--confirmar') flags.confirmar = true;
  else if (a === '--vus' || a === '--duracion') {
    const valor = args[++i];
    if (!valor || valor.startsWith('--')) salir(`Falta el valor de ${a} (ej. --vus 20 --duracion 2m).`);
    if (a === '--vus' && !/^[1-9]\d*$/.test(valor)) salir(`--vus tiene que ser un número entero mayor que 0 (recibí "${valor}").`);
    if (a === '--duracion' && !/^\d+\s*[smh]?$/i.test(valor)) salir(`--duracion tiene que ser segundos o con sufijo s, m o h (ej. 90, 2m, 1h); recibí "${valor}".`);
    flags[a.slice(2)] = valor;
  }
  else pos.push(a);
}
if (!pos.length) {
  listar();
  process.exit(0);
}
const nombre = path.basename(pos[0]).replace(/\.(ts|js|ya?ml|jmx)$/, '');
const perfil = (pos[1] || 'smoke').toLowerCase();
if (!PERFILES.includes(perfil)) salir(`Perfil desconocido "${perfil}". Opciones: ${PERFILES.join(', ')}.`);

// Un mismo nombre en dos herramientas es ambiguo: se pide renombrar en lugar de elegir uno en silencio.
const coincidencias = [
  fs.existsSync(path.join(DIR_K6, `${nombre}.ts`)) && 'k6',
  fs.existsSync(path.join(DIR_JM, `${nombre}.jmx`)) && 'jmeter',
  ['yaml', 'yml'].some((e) => fs.existsSync(path.join(DIR_ART, `${nombre}.${e}`))) && 'artillery',
].filter(Boolean);
if (coincidencias.length > 1) {
  salir(`Hay scripts "${nombre}" en ${coincidencias.join(' y ')}: renombrá uno (ej. ${nombre}-${coincidencias[1]}) para que no sea ambiguo.`);
}

let herramienta, fuente;
if (fs.existsSync(path.join(DIR_K6, `${nombre}.ts`))) {
  herramienta = 'k6';
  fuente = path.join(DIR_K6, `${nombre}.ts`);
} else if (fs.existsSync(path.join(DIR_JM, `${nombre}.jmx`))) {
  herramienta = 'jmeter';
  fuente = path.join(DIR_JM, `${nombre}.jmx`);
} else {
  const yml = ['yaml', 'yml'].map((e) => path.join(DIR_ART, `${nombre}.${e}`)).find((f) => fs.existsSync(f));
  if (!yml) salir(`No encontré el script "${nombre}" en performance/k6/http/, performance/artillery/ ni performance/jmeter/. Corré "npm run perf" para ver la lista.`);
  herramienta = 'artillery';
  fuente = yml;
}

// JMeter: la carga de cada perfil, el destino y los umbrales van en <script>.json, al lado del .jmx.
function configJMeter() {
  const archivo = path.join(DIR_JM, `${nombre}.json`);
  if (!fs.existsSync(archivo)) salir(`Falta ${rel(archivo)} (destino, perfiles y umbrales del script de JMeter).`);
  let cfg;
  try {
    cfg = JSON.parse(fs.readFileSync(archivo, 'utf8'));
  } catch (e) {
    salir(`${rel(archivo)} no es un JSON válido: ${e.message}`);
  }
  if (!cfg.perfiles || !cfg.perfiles[perfil]) salir(`${rel(archivo)} no define el perfil "${perfil}" (perfiles.${perfil}).`);
  // destino: el nombre de una variable del .env (ej. API_BASEURL) o una URL.
  const base = /^[A-Z][A-Z0-9_]*$/.test(cfg.destino || '') ? process.env[cfg.destino] : cfg.destino;
  if (!base) salir(`${rel(archivo)}: el destino "${cfg.destino || ''}" está vacío (si es una variable, definila en el .env de la raíz).`);
  return { ...cfg, base: base.replace(/\/+$/, '') };
}
const cfgJM = herramienta === 'jmeter' ? configJMeter() : null;

// ------------------------------------------------------------ destino (para mostrar y confirmar)
function destino() {
  if (herramienta === 'jmeter') return cfgJM.base;
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

// JMeter corre con `java -jar ApacheJMeter.jar` (sin .bat ni shell: las rutas pueden tener espacios).
// El .jtl sale en CSV (el formato por defecto de JMeter). Las propiedades van en un archivo (-q) y no
// como -J: con varios -J el lanzador de Java 8 en Windows se cae antes de arrancar.
function jarJMeter() {
  const candidatos = [];
  if (process.env.JMETER_HOME) candidatos.push(path.join(process.env.JMETER_HOME, 'bin/ApacheJMeter.jar'));
  const dirTools = path.join(RAIZ, 'tools/jmeter');
  if (fs.existsSync(dirTools)) {
    for (const d of fs.readdirSync(dirTools).filter((x) => x.startsWith('apache-jmeter-')).sort().reverse()) {
      candidatos.push(path.join(dirTools, d, 'bin/ApacheJMeter.jar'));
    }
  }
  const jar = candidatos.find((f) => fs.existsSync(f));
  if (!jar) salir('No encuentro JMeter. Instalalo con "npm run bootstrap:jmeter" (queda en tools/jmeter) o definí JMETER_HOME.');
  return jar;
}

function binarioJava() {
  const java = process.env.JAVA_HOME ? path.join(process.env.JAVA_HOME, 'bin', process.platform === 'win32' ? 'java.exe' : 'java') : 'java';
  const r = spawnSync(java, ['-version'], { encoding: 'utf8' });
  if (r.error || r.status !== 0) salir('JMeter necesita Java 8 o superior: instalalo y dejalo en el PATH, o definí JAVA_HOME.');
  return java;
}

// "90", "90s", "5m", "2h" → segundos (para --duracion en JMeter)
function segundos(texto) {
  const m = String(texto).trim().match(/^(\d+)\s*(s|m|h)?$/i);
  if (!m) salir(`Duración inválida "${texto}": usá segundos o un sufijo s, m o h (ej. 90, 2m, 1h).`);
  return Number(m[1]) * { s: 1, m: 60, h: 3600 }[(m[2] || 's').toLowerCase()];
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
  const crudo = `${base}-crudo.${herramienta === 'jmeter' ? 'jtl' : 'json'}`;
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
  } else if (herramienta === 'jmeter') {
    const java = binarioJava();
    const jar = jarJMeter();
    // Cada clave del perfil llega al .jmx como propiedad: ${__P(usuarios,1)}, ${__P(duracion,30)}...
    const props = { ...cfgJM.perfiles[perfil], base_url: cfgJM.base };
    if (flags.vus) props.usuarios = flags.vus;
    if (flags.duracion) props.duracion = segundos(flags.duracion);
    const archivoProps = `${base}.properties`;
    // Formato .properties: la barra invertida es escape y cada propiedad va en una línea.
    const escapar = (v) => String(v).replace(/\\/g, '\\\\').replace(/\r?\n/g, ' ');
    fs.writeFileSync(archivoProps, Object.entries(props).map(([k, v]) => `${k}=${escapar(v)}`).join('\n') + '\n');
    const dashboard = `${base}-dashboard`;
    codigo = await correr(java, [
      '-jar', jar, '-n', '-t', rel(fuente), '-l', rel(crudo), '-j', rel(`${base}-jmeter.log`),
      '-q', rel(archivoProps), '-e', '-o', rel(dashboard),
    ], env, logFile);
    if (fs.existsSync(path.join(dashboard, 'index.html'))) console.log(`Dashboard de JMeter: ${rel(path.join(dashboard, 'index.html'))}`);
  } else {
    if (flags.vus || flags.duracion) console.log('Aviso: --vus y --duracion son solo para k6 y JMeter; en Artillery la carga está en las fases del .yaml.');
    const bin = path.join(RAIZ, 'node_modules/artillery/bin/run');
    codigo = await correr(process.execPath, [bin, 'run', rel(fuente), '--environment', perfil, '--output', crudo], { ...env, NO_COLOR: '1' }, logFile);
  }

  const r = generarReporte({ herramienta, script: nombre, perfil, destino: target, crudo, log: logFile, salida: base, codigoSalida: codigo,
    umbrales: cfgJM && cfgJM.umbrales });

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

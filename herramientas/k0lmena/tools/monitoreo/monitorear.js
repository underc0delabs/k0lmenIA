// Monitoreo sintético: un smoke liviano y de SOLO LECTURA contra un ambiente (producción u otro), pensado
// para correr programado (GitHub Actions, cron o el Programador de tareas de Windows).
//
// Uso (desde la raíz del repo):
//   npm run monitorear -- [--urls https://mi-app.com,https://mi-app.com/login] [--config input/monitoreo.json]
//                         [--nombre produccion] [--texto "Iniciar sesión"] [--timeout-ms 15000] [--lenta-ms 3000]
//                         [--tls-dias 14] [--escenarios] [--avisar-siempre] [--no-avisar] [--corridas 30]
//
// Qué revisa cada corrida:
//   - cada URL (MONITOREO_URLS del .env, --urls o los "checks" de input/monitoreo.json) con GET o HEAD:
//     status esperado (por defecto 2xx), tiempo de respuesta (lenta si pasa --lenta-ms o el max_ms del
//     check), texto que tiene que estar y texto que no tiene que estar;
//   - el certificado TLS de cada host https: avisa si vence en menos de --tls-dias días;
//   - con --escenarios, los escenarios web de k0lmena con el tag @sintetico (o los "tags" del config).
//     TIENEN QUE SER DE SOLO LECTURA: navegar, buscar, mirar. Nada que cree, cambie o borre datos,
//     ni logins con usuarios reales, ni formularios que se envíen: corren contra producción.
//
// Estado de la corrida: Caído (algún check falla), Degradado (lento o certificado por vencer) u OK.
// Compara con la corrida anterior (qué se rompió y qué se recuperó) y SOLO avisa a Slack y Teams
// (scripts/avisar.py) cuando cambia algo, o siempre con --avisar-siempre. MONITOREO_LINK, si está, va como
// link del aviso (por ejemplo, la corrida de GitHub Actions).
//
// Deja output/monitoreo/<nombre>/monitoreo.json e informe-monitoreo.html; las corridas anteriores pasan a
// historial/ (se guardan las últimas --corridas, 30 por defecto, para la disponibilidad). Sale con 1 si
// quedó Caído (útil en CI), 0 si no.
const fs = require('fs');
const path = require('path');
const tls = require('tls');
const { spawnSync } = require('child_process');
const { archivar } = require('../historial/historial.js');

// Datos (output/, input/, .auth/) en el proyecto y scripts de Python en el código de k0lmenIA: ver ../rutas.js.
const { PROYECTO: RAIZ, CODIGO } = require('../rutas');
const K0 = path.resolve(__dirname, '..', '..');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p);
const GENERADOS = ['monitoreo.json', 'informe-monitoreo.html', 'escenarios'];
const METODOS = new Set(['GET', 'HEAD']);

function argumentos(argv) {
  const a = { timeoutMs: 15000, lentaMs: 3000, tlsDias: 14, escenarios: false, avisarSiempre: false, avisar: true, corridas: 30 };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--urls') a.urls = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--config') a.config = v();
    else if (k === '--nombre') a.nombre = v();
    else if (k === '--texto') a.texto = v();
    else if (k === '--timeout-ms') a.timeoutMs = parseInt(v(), 10);
    else if (k === '--lenta-ms') a.lentaMs = parseInt(v(), 10);
    else if (k === '--tls-dias') a.tlsDias = parseInt(v(), 10);
    else if (k === '--corridas') a.corridas = parseInt(v(), 10);
    else if (k === '--escenarios') a.escenarios = true;
    else if (k === '--avisar-siempre') a.avisarSiempre = true;
    else if (k === '--no-avisar') a.avisar = false;
    else if (k === '--salida') a.salida = v();
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (!(a.timeoutMs >= 1000)) throw new Error('--timeout-ms tiene que ser al menos 1000.');
  if (!(a.corridas >= 2 && a.corridas <= 500)) throw new Error('--corridas tiene que estar entre 2 y 500.');
  if (a.nombre && !/^[\w.-]+$/.test(a.nombre)) throw new Error('--nombre solo admite letras, números, punto, guion y guion bajo.');
  return a;
}

// Lista de checks: config (input/monitoreo.json) + --urls / MONITOREO_URLS. Cada uno con id estable.
function armarChecks(config, a, env = process.env) {
  const checks = [];
  for (const c of (config && config.checks) || []) checks.push({ ...c });
  const urls = a.urls || (checks.length ? [] : (env.MONITOREO_URLS || '').split(',').map((x) => x.trim()).filter(Boolean));
  for (const url of urls) checks.push({ url });
  return checks.map((c, i) => {
    if (!c.url || !/^https?:\/\//i.test(c.url)) throw new Error(`El check ${i + 1} no tiene una URL http(s) válida.`);
    const metodo = String(c.metodo || 'GET').toUpperCase();
    if (!METODOS.has(metodo)) throw new Error(`El check ${c.nombre || c.url} usa ${metodo}: el monitoreo es de solo lectura (GET o HEAD).`);
    const u = new URL(c.url);
    return { id: c.id || `${metodo} ${u.host}${u.pathname}${u.search}`, nombre: c.nombre || (u.pathname === '/' ? u.host : u.pathname), url: c.url, metodo,
      status: c.status || null, texto: c.texto ?? a.texto ?? null, no_texto: c.no_texto || null, max_ms: c.max_ms || a.lentaMs };
  });
}

// Evalúa la respuesta de un check: { estado: OK | Lento | Caído, motivo }.
function evaluar(check, r) {
  if (r.error) return { estado: 'Caído', motivo: r.error };
  const esperado = check.status ? [].concat(check.status).map(Number) : null;
  if (esperado ? !esperado.includes(r.status) : !(r.status >= 200 && r.status < 300)) {
    return { estado: 'Caído', motivo: `HTTP ${r.status}${esperado ? ` (se esperaba ${esperado.join(' o ')})` : ''}` };
  }
  if (check.texto && check.metodo !== 'HEAD' && !(r.cuerpo || '').includes(check.texto)) return { estado: 'Caído', motivo: `No aparece el texto "${check.texto}"` };
  if (check.no_texto && (r.cuerpo || '').includes(check.no_texto)) return { estado: 'Caído', motivo: `Aparece el texto "${check.no_texto}"` };
  if (r.ms > check.max_ms) return { estado: 'Lento', motivo: `${r.ms} ms (máximo ${check.max_ms} ms)` };
  return { estado: 'OK', motivo: '' };
}

function diasRestantes(validoHasta, ahora = new Date()) {
  const fin = new Date(validoHasta);
  return Number.isNaN(fin.getTime()) ? null : Math.floor((fin - ahora) / 86400000);
}

function estadoGeneral(resultados) {
  const estados = resultados.map((r) => r.estado);
  if (estados.includes('Caído')) return 'Caído';
  if (estados.some((e) => e === 'Lento' || e === 'Por vencer')) return 'Degradado';
  return 'OK';
}

// Qué cambió desde la corrida anterior: checks que se rompieron, que se recuperaron y nuevos.
function comparar(anterior, actual) {
  const previo = new Map(((anterior && anterior.resultados) || []).map((r) => [r.id, r.estado]));
  const rompio = [];
  const recupero = [];
  for (const r of actual.resultados) {
    const antes = previo.get(r.id);
    if (r.estado === 'Caído' && antes && antes !== 'Caído') rompio.push(r.id);
    else if (r.estado === 'Caído' && !antes && anterior) rompio.push(r.id);
    else if (r.estado !== 'Caído' && antes === 'Caído') recupero.push(r.id);
  }
  return { anterior: anterior ? anterior.estado : null, rompio, recupero, cambio: !anterior || anterior.estado !== actual.estado || rompio.length > 0 || recupero.length > 0 };
}

// Título, texto y nivel del aviso.
function armarAviso(datos) {
  const { estado, nombre, cambios, resultados } = datos;
  const nivel = estado === 'Caído' ? 'error' : estado === 'Degradado' ? 'aviso' : 'ok';
  const caidos = resultados.filter((r) => r.estado === 'Caído');
  let texto;
  if (cambios.recupero.length && !caidos.length) texto = `Se recuperó: ${cambios.recupero.join(', ')}.`;
  else if (caidos.length) texto = `Falla: ${caidos.map((r) => `${r.nombre} (${r.motivo})`).join('; ')}.`;
  else texto = `Todo responde. ${resultados.filter((r) => r.estado !== 'OK').map((r) => `${r.nombre}: ${r.motivo}`).join('; ')}`.trim();
  if (cambios.recupero.length && caidos.length) texto += ` Se recuperó: ${cambios.recupero.join(', ')}.`;
  return { titulo: `Monitoreo ${nombre}: ${estado}`, texto, nivel,
    campos: [['Checks', `${resultados.filter((r) => r.estado !== 'Caído').length}/${resultados.length} OK`], ['Antes', cambios.anterior || '—']] };
}

async function chequear(check, timeoutMs) {
  const control = new AbortController();
  const reloj = setTimeout(() => control.abort(), timeoutMs);
  const inicio = Date.now();
  try {
    const resp = await fetch(check.url, { method: check.metodo, redirect: 'follow', signal: control.signal,
      headers: { 'User-Agent': 'k0lmenIA-monitoreo/1.0', 'Cache-Control': 'no-cache' } });
    const cuerpo = check.metodo === 'HEAD' ? '' : (await resp.text()).slice(0, 2_000_000);
    return { status: resp.status, ms: Date.now() - inicio, cuerpo, url_final: resp.url };
  } catch (e) {
    const causa = e.name === 'AbortError' ? `sin respuesta en ${timeoutMs} ms` : (e.cause && (e.cause.code || e.cause.message)) || e.message;
    return { error: String(causa), ms: Date.now() - inicio };
  } finally {
    clearTimeout(reloj);
  }
}

function certificado(host, port = 443, timeoutMs = 10000) {
  return new Promise((ok) => {
    const s = tls.connect({ host, port, servername: host, timeout: timeoutMs }, () => {
      const c = s.getPeerCertificate();
      s.end();
      ok({ host, vence: c && c.valid_to ? new Date(c.valid_to).toISOString() : null, emisor: c && c.issuer ? c.issuer.O || c.issuer.CN : null });
    });
    s.on('error', (e) => ok({ host, error: e.code || e.message }));
    s.on('timeout', () => { s.destroy(); ok({ host, error: 'sin respuesta' }); });
  });
}

// Escenarios @sintetico de k0lmena (suite web), en su propia carpeta de reportes para no pisar npm test.
function correrEscenarios(tags, carpeta) {
  const dirRel = path.relative(K0, path.join(carpeta, 'escenarios')).split(path.sep).join('/');
  const env = { ...process.env, TAGS: tags, REPORT_DIR: dirRel, EVIDENCE: 'off', VIDEO: 'off', TRACE: 'off', PARALLEL: '' };
  const r = spawnSync('npx cucumber-js --profile web', { cwd: K0, env, shell: true, encoding: 'utf8' });
  const reporte = path.join(carpeta, 'escenarios', 'cucumber-report.json');
  if (!fs.existsSync(reporte)) return [{ id: `escenarios ${tags}`, nombre: `Escenarios ${tags}`, tipo: 'Escenario', estado: 'Caído', motivo: `No se pudieron correr (código ${r.status})` }];
  const salida = [];
  for (const f of JSON.parse(fs.readFileSync(reporte, 'utf8'))) {
    for (const esc of f.elements || []) {
      if (esc.type === 'background') continue;
      const pasos = esc.steps || [];
      const falla = pasos.find((p) => (p.result || {}).status === 'failed');
      const ms = Math.round(pasos.reduce((s, p) => s + ((p.result || {}).duration || 0), 0) / 1e6);
      salida.push({ id: `escenario ${esc.name}`, nombre: esc.name, tipo: 'Escenario', url: f.uri, ms, estado: falla ? 'Caído' : 'OK',
        motivo: falla ? String((falla.result || {}).error_message || 'falló').split('\n')[0].slice(0, 200) : '' });
    }
  }
  return salida;
}

function avisar(aviso, link) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const args = [path.join(CODIGO, 'scripts', 'avisar.py'), '--titulo', aviso.titulo, '--texto', aviso.texto, '--nivel', aviso.nivel,
    '--campos', aviso.campos.map(([k, v]) => `${k}=${String(v).replace(/,/g, ' ')}`).join(',')];
  if (link) args.push('--link', link);
  const r = spawnSync(py, args, { encoding: 'utf8' });
  process.stdout.write(r.stdout || '');
  if (r.status !== 0) console.log(`No se pudo mandar el aviso (${(r.stderr || r.error || '').toString().trim().split('\n').pop()}).`);
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = spawnSync(py, [path.join(CODIGO, 'scripts', 'generar_informe_monitoreo.py'), path.join(carpeta, 'monitoreo.json'),
    path.join(carpeta, 'informe-monitoreo.html')], { encoding: 'utf8' });
  if (r.status !== 0) console.log(`No pude generar el informe HTML: ${(r.stderr || r.error || '').toString().trim().split('\n').pop()}`);
  return r.status === 0;
}

async function main() {
  const a = argumentos(process.argv.slice(2));
  if (a.ayuda) {
    console.log(fs.readFileSync(__filename, 'utf8').split('\n').filter((l) => l.startsWith('//')).map((l) => l.slice(3)).join('\n'));
    return 0;
  }
  const rutaConfig = a.config ? desde(a.config) : path.join(RAIZ, 'input', 'monitoreo.json');
  const config = fs.existsSync(rutaConfig) ? JSON.parse(fs.readFileSync(rutaConfig, 'utf8')) : null;
  if (a.config && !config) throw new Error(`No existe ${a.config}.`);
  const checks = armarChecks(config, a);
  const tags = (config && config.escenarios && config.escenarios.tags) || '@sintetico';
  const escenarios = a.escenarios || Boolean(config && config.escenarios && config.escenarios.correr);
  if (!checks.length && !escenarios) throw new Error('No hay nada para monitorear: definí MONITOREO_URLS en el .env, --urls o input/monitoreo.json.');
  const nombre = a.nombre || (config && config.nombre) || (checks[0] ? new URL(checks[0].url).hostname : 'escenarios');
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'monitoreo', nombre);
  fs.mkdirSync(carpeta, { recursive: true });
  const archivoDatos = path.join(carpeta, 'monitoreo.json');
  const anterior = fs.existsSync(archivoDatos) ? JSON.parse(fs.readFileSync(archivoDatos, 'utf8')) : null;
  archivar(carpeta, GENERADOS, 'monitoreo.json', a.corridas);
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });

  const inicio = new Date();
  console.log(`Monitoreo "${nombre}" · ${checks.length} check(s)${escenarios ? ` + escenarios ${tags}` : ''}`);
  const resultados = [];
  for (const c of checks) {
    const r = await chequear(c, a.timeoutMs);
    const ev = evaluar(c, r);
    resultados.push({ id: c.id, nombre: c.nombre, tipo: 'URL', url: c.url, metodo: c.metodo, status: r.status || null, ms: r.ms, ...ev });
    console.log(`  ${ev.estado.padEnd(6)} ${c.metodo} ${c.url} · ${r.status || '-'} · ${r.ms} ms${ev.motivo ? ` · ${ev.motivo}` : ''}`);
  }
  const hosts = [...new Set(checks.filter((c) => c.url.startsWith('https://')).map((c) => new URL(c.url).host))];
  for (const h of hosts) {
    const [host, port] = h.split(':');
    const cert = await certificado(host, Number(port) || 443);
    const dias = cert.vence ? diasRestantes(cert.vence) : null;
    const estado = cert.error ? 'Caído' : dias < 0 ? 'Caído' : dias < a.tlsDias ? 'Por vencer' : 'OK';
    const motivo = cert.error ? `TLS: ${cert.error}` : dias < 0 ? 'Certificado vencido' : dias < a.tlsDias ? `Vence en ${dias} día(s)` : '';
    resultados.push({ id: `TLS ${h}`, nombre: `Certificado de ${host}`, tipo: 'TLS', url: `https://${h}`, vence: cert.vence, dias_restantes: dias, emisor: cert.emisor, estado, motivo });
    console.log(`  ${estado.padEnd(6)} TLS ${h}${dias != null ? ` · vence en ${dias} días` : ''}${motivo && !dias ? ` · ${motivo}` : ''}`);
  }
  if (escenarios) {
    for (const r of correrEscenarios(tags, carpeta)) {
      resultados.push(r);
      console.log(`  ${r.estado.padEnd(6)} Escenario ${r.nombre}${r.motivo ? ` · ${r.motivo}` : ''}`);
    }
  }

  const datos = { nombre, fecha: inicio.toISOString(), marca: inicio.toISOString().slice(0, 19), duracion_ms: Date.now() - inicio.getTime(),
    estado: estadoGeneral(resultados), resultados };
  datos.cambios = comparar(anterior, datos);
  fs.writeFileSync(archivoDatos, JSON.stringify(datos, null, 2));
  generarInforme(carpeta);
  const rel = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  console.log(`\nEstado: ${datos.estado}${datos.cambios.anterior ? ` (antes: ${datos.cambios.anterior})` : ''}` +
    `${datos.cambios.rompio.length ? ` · se rompió: ${datos.cambios.rompio.join(', ')}` : ''}${datos.cambios.recupero.length ? ` · se recuperó: ${datos.cambios.recupero.join(', ')}` : ''}`);
  console.log(`Informe: ${rel(path.join(carpeta, 'informe-monitoreo.html'))}`);
  // El primer aviso solo si arranca con problemas: un OK sin historia no es novedad.
  const novedad = datos.cambios.cambio && (anterior || datos.estado !== 'OK');
  if (a.avisar && (a.avisarSiempre || novedad)) avisar(armarAviso(datos), process.env.MONITOREO_LINK);
  return datos.estado === 'Caído' ? 1 : 0;
}

if (require.main === module) {
  main().then((c) => process.exit(c)).catch((e) => { console.error(`Error: ${e.message}`); process.exit(2); });
}

module.exports = { argumentos, armarChecks, evaluar, diasRestantes, estadoGeneral, comparar, armarAviso, GENERADOS };

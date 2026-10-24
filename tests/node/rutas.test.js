// Código y datos separados (herramientas/k0lmena/tools/rutas.js): con K0LMENIA_PROYECTO (o como plugin, con
// CLAUDE_PLUGIN_ROOT) el .env, la sesión y las salidas de k0lmena van al proyecto; sin nada, al repo como siempre.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const RAIZ = path.resolve(__dirname, '..', '..');

// Corre un fragmento en un proceso nuevo (las rutas se resuelven al cargar los módulos) y devuelve su JSON.
function enProceso(codigo, env = {}, cwd = RAIZ) {
  const limpio = { ...process.env };
  for (const k of ['K0LMENIA_PROYECTO', 'K0LMENIA_CODIGO', 'CLAUDE_PLUGIN_ROOT', 'K0LMENA_ENV_FILE', 'APP_URL', 'BASEURL', 'SESION']) delete limpio[k];
  const r = spawnSync(process.execPath, ['-e', codigo], { cwd, env: { ...limpio, ...env }, encoding: 'utf8' });
  assert.strictEqual(r.status, 0, r.stderr);
  return JSON.parse(r.stdout);
}

const RUTAS = JSON.stringify(path.join(RAIZ, 'herramientas', 'k0lmena', 'tools', 'rutas.js'));
const SESION = JSON.stringify(path.join(RAIZ, 'herramientas', 'k0lmena', 'tools', 'login', 'sesion.js'));
const ENVJS = JSON.stringify(path.join(RAIZ, 'herramientas', 'k0lmena', 'env.js'));
const LEERENV = JSON.stringify(path.join(RAIZ, 'scripts', 'mcp', 'leer-env.js'));

test('sin variables: proyecto y código son el repo', () => {
  const r = enProceso(`const r = require(${RUTAS}); console.log(JSON.stringify({ p: r.PROYECTO, c: r.CODIGO }))`);
  assert.strictEqual(r.p, RAIZ);
  assert.strictEqual(r.c, RAIZ);
});

test('con K0LMENIA_PROYECTO: .env, sesión y variables del proyecto', () => {
  const proy = fs.mkdtempSync(path.join(os.tmpdir(), 'k0-proyecto-'));
  fs.writeFileSync(path.join(proy, '.env'), 'APP_URL=https://app.proyecto.test\nSESION=si\n');
  fs.mkdirSync(path.join(proy, '.auth'));
  fs.writeFileSync(path.join(proy, '.auth', 'sesion.json'), '{"cookies":[],"origins":[]}');
  const r = enProceso(
    `const r = require(${RUTAS}); require(${ENVJS}); const s = require(${SESION}); const { variable } = require(${LEERENV});
     console.log(JSON.stringify({ p: r.PROYECTO, c: r.CODIGO, app: process.env.APP_URL, leida: variable('APP_URL'),
       auth: s.CARPETA, activa: s.sesionActiva('si', () => {}) }))`,
    { K0LMENIA_PROYECTO: proy });
  assert.strictEqual(r.p, proy);
  assert.strictEqual(r.c, RAIZ); // los scripts de Python siguen en el código
  assert.strictEqual(r.app, 'https://app.proyecto.test'); // env.js cargó el .env del proyecto
  assert.strictEqual(r.leida, 'https://app.proyecto.test'); // y los lanzadores MCP también
  assert.strictEqual(r.auth, path.join(proy, '.auth'));
  assert.strictEqual(r.activa, path.join(proy, '.auth', 'sesion.json'));
});

test('como plugin (CLAUDE_PLUGIN_ROOT): el proyecto es la carpeta actual; K0LMENIA_CODIGO manda para el código', () => {
  const proy = fs.mkdtempSync(path.join(os.tmpdir(), 'k0-plugin-'));
  const r = enProceso(`const r = require(${RUTAS}); console.log(JSON.stringify({ p: r.PROYECTO, c: r.CODIGO }))`,
    { CLAUDE_PLUGIN_ROOT: RAIZ, K0LMENIA_CODIGO: RAIZ }, proy);
  assert.strictEqual(fs.realpathSync(r.p), fs.realpathSync(proy));
  assert.strictEqual(r.c, RAIZ);
});

test('las herramientas de k0lmena toman los datos del proyecto y los scripts del código', () => {
  const dir = path.join(RAIZ, 'herramientas', 'k0lmena', 'tools');
  let revisados = 0;
  for (const carpeta of fs.readdirSync(dir, { withFileTypes: true }).filter((d) => d.isDirectory())) {
    for (const f of fs.readdirSync(path.join(dir, carpeta.name)).filter((x) => x.endsWith('.js'))) {
      const texto = fs.readFileSync(path.join(dir, carpeta.name, f), 'utf8');
      assert.ok(!/path\.resolve\(__dirname, '\.\.', '\.\.', '\.\.', '\.\.'\)/.test(texto), `${carpeta.name}/${f}: la raíz va por ../rutas.js`);
      assert.ok(!/path\.join\(RAIZ, 'scripts'/.test(texto), `${carpeta.name}/${f}: los scripts de Python van con CODIGO`);
      if (texto.includes("require('../rutas')")) revisados++;
    }
  }
  assert.ok(revisados >= 15, `solo ${revisados} herramientas usan ../rutas.js`);
});

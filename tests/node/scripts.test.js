// Tests de los scripts de Node de k0lmenIA (correr: node --test tests/node).
// Solo usan módulos nativos: no hace falta instalar k0lmena.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const RAIZ = path.resolve(__dirname, '..', '..');
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'k0lmenia-'));

test('leer-env: mismas reglas que dotenv y scripts/_env.py', () => {
  const dir = tmp();
  const archivo = path.join(dir, '.env');
  fs.writeFileSync(archivo, '﻿SIMPLE=valor\nexport CON_EXPORT=si\nESPACIOS =  hola   \nCOMENTARIO=abc # no\nCOMILLAS="a # b"\n# OFF=x\n');
  process.env.K0LMENA_ENV_FILE = archivo;
  delete require.cache[require.resolve(path.join(RAIZ, 'scripts/mcp/leer-env.js'))];
  const { variable } = require(path.join(RAIZ, 'scripts/mcp/leer-env.js'));
  assert.equal(variable('SIMPLE'), 'valor');
  assert.equal(variable('CON_EXPORT'), 'si');
  assert.equal(variable('ESPACIOS'), 'hola');
  assert.equal(variable('COMENTARIO'), 'abc');
  assert.equal(variable('COMILLAS'), 'a # b');
  assert.equal(variable('OFF'), '');
  delete process.env.K0LMENA_ENV_FILE;
});

test('lanzar: los servers MCP usan versiones fijas (nunca @latest)', () => {
  const { paqueteFijo, VERSIONES } = require(path.join(RAIZ, 'scripts/mcp/lanzar.js'));
  for (const paquete of Object.keys(VERSIONES)) {
    assert.match(paqueteFijo(paquete), /@\d+\.\d+\.\d+$/);
  }
  process.env.PLAYWRIGHT_MCP_MCP_VERSION = '1.2.3';
  assert.equal(paqueteFijo('@playwright/mcp'), '@playwright/mcp@1.2.3');
  delete process.env.PLAYWRIGHT_MCP_MCP_VERSION;
  const mcp = fs.readFileSync(path.join(RAIZ, '.mcp.json'), 'utf8');
  assert.doesNotMatch(mcp, /@latest/);
});

const { generarReporte } = require(path.join(RAIZ, 'herramientas/k0lmena/reports/performance/generar-reporte.js'));

test('reporte de performance: JMeter (.jtl) con umbrales globales y por muestra', () => {
  const dir = tmp();
  const jtl = path.join(dir, 'crudo.jtl');
  const filas = ['timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect'];
  for (let i = 0; i < 20; i++) filas.push(`${1700000000000 + i * 1000},${100 + i},GET /a,200,OK,t1,text,true,,1,1,2,2,https://x/a,1,0,1`);
  filas.push(`${1700000021000},900,POST /b,500,Error,t1,text,false,"Test failed: code expected to equal\n200",1,1,2,2,https://x/b,1,0,1`);
  fs.writeFileSync(jtl, filas.join('\n'));
  const r = generarReporte({ herramienta: 'jmeter', script: 's', perfil: 'smoke', destino: 'https://x', crudo: jtl, log: '', salida: path.join(dir, 'r'), codigoSalida: 0,
    umbrales: { error_pct: 10, p95: 200, por_muestra: { 'POST /b': { p95: 500 } } } });
  assert.equal(r.kpis.requests, 21);
  assert.equal(r.veredicto, 'no cumple');
  const porNombre = Object.fromEntries(r.umbrales.map((u) => [u.metrica, u.ok]));
  assert.equal(porNombre['% de errores'], true);
  assert.equal(porNombre['POST /b · p95'], false);
  assert.ok(fs.existsSync(path.join(dir, 'r.html')));
  // El mensaje de error multilínea queda en una línea
  assert.ok(Object.keys(r.errores)[0].includes('equal 200'));
});

test('reporte de performance: un resultado truncado se informa como error, sin caerse', () => {
  const dir = tmp();
  const crudo = path.join(dir, 'crudo.json');
  fs.writeFileSync(crudo, '{"metrics": {"http_reqs": ');
  const r = generarReporte({ herramienta: 'k6', script: 's', perfil: 'smoke', destino: '-', crudo, log: '', salida: path.join(dir, 'r'), codigoSalida: 0 });
  assert.equal(r.veredicto, 'error');
});

test('tema oscuro de los reportes de cucumber: fuerza dark y se aplica una sola vez', () => {
  const { temaEnHtml } = require(path.join(RAIZ, 'herramientas/k0lmena/reports/tema-oscuro.js'));
  const original = '<!doctype html><html lang="en"><head><title>x</title></head><body></body></html>';
  const una = temaEnHtml(original);
  assert.match(una, /<html lang="en" class="dark">/);
  assert.match(una, /id="k0lmena-theme"/);
  assert.equal(temaEnHtml(una), una);
});

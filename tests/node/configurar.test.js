// Tests del asistente npm run configurar: escribir el .env sin romperlo y armar el plan según lo elegido.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const RAIZ = path.resolve(__dirname, '..', '..');
const cfg = require(path.join(RAIZ, 'scripts/configurar.js'));
const CATALOGO = JSON.parse(fs.readFileSync(path.join(RAIZ, 'scripts/mcp/catalogo.json'), 'utf8')).conectores;

test('configurar: completa una línea activa, descomenta la comentada o agrega al final', () => {
  let t = '# URL\nAPP_URL=https://vieja.test\n# Token\n# GITHUB_TOKEN=\nOTRA=1\n';
  t = cfg.establecer(t, 'APP_URL', 'https://nueva.test');
  t = cfg.establecer(t, 'GITHUB_TOKEN', 'ghp_123');
  t = cfg.establecer(t, 'NUEVA', 'con espacio');
  assert.equal(t, '# URL\nAPP_URL=https://nueva.test\n# Token\nGITHUB_TOKEN=ghp_123\nOTRA=1\n\n# --- Agregado por npm run configurar ---\nNUEVA="con espacio"\n');
  assert.equal(cfg.leerValor(t, 'GITHUB_TOKEN'), 'ghp_123');
  assert.equal(cfg.leerValor(t, 'NUEVA'), 'con espacio');
  assert.equal(cfg.leerValor('# GITHUB_TOKEN=x\n', 'GITHUB_TOKEN'), '', 'una línea comentada no es un valor');
  assert.equal(cfg.leerValor(cfg.establecer('', 'A', '$x'), 'A'), '$x');
});

test('configurar: el plan junta conectores y datos sin repetir', () => {
  const paso = (id) => cfg.PASOS.find((p) => p.id === id);
  const op = (id, nombre) => paso(id).opciones.find((o) => o.nombre.startsWith(nombre));
  const p = cfg.plan([op('historias', 'Jira'), op('casos', 'Xray Cloud'), op('codigo', 'Sí')]);
  assert.deepEqual(p.conectores, []);
  assert.deepEqual(p.fijos, { GESTION_HERRAMIENTA: 'xray-cloud', REPO_PROVEEDOR: 'local' });
  const claves = p.datos.map((d) => d.clave);
  assert.equal(new Set(claves).size, claves.length, 'cada dato se pide una sola vez');
  assert.ok(claves.includes('JIRA_BASE_URL') && claves.includes('REPO_RUTA_LOCAL'));
  const tmt = cfg.plan([op('casos', 'k0lmenaTMT')]);
  assert.deepEqual(tmt.conectores, ['k0lmena-tmt']);
});

test('configurar: todos los conectores del asistente existen en el catálogo', () => {
  for (const paso of cfg.PASOS) for (const o of paso.opciones) for (const c of o.conectores || []) assert.ok(CATALOGO[c], `${o.nombre} → ${c}`);
});

test('configurar: los datos que pide están documentados en .env.example', () => {
  const ejemplo = fs.readFileSync(path.join(RAIZ, '.env.example'), 'utf8');
  const datos = [...cfg.APP, ...cfg.PASOS.flatMap((p) => p.opciones.flatMap((o) => [...(o.datos || []), ...Object.keys(o.fijos || {}).map((clave) => ({ clave }))]))];
  for (const { clave } of datos) assert.match(ejemplo, new RegExp(`^#? ?${clave}=`, 'm'), clave);
});

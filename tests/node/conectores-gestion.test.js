// Tests de los conectores MCP: headersHelper genérico, activación y catálogo.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const RAIZ = path.resolve(__dirname, '..', '..');
const VARIABLES = /^(LINEAR_API_KEY|MONDAY_API_TOKEN|YOUTRACK_TOKEN|YOUTRACK_URL|ASANA_CLIENT_ID|ASANA_CLIENT_SECRET)$/;

function helper(args, env) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'k0-gestion-'));
  const archivo = path.join(dir, '.env');
  fs.writeFileSync(archivo, Object.entries(env).map(([k, v]) => `${k}=${v}`).join('\n'));
  const limpio = Object.fromEntries(Object.entries(process.env).filter(([k]) => !VARIABLES.test(k)));
  const r = spawnSync(process.execPath, [path.join(RAIZ, 'scripts/mcp/bearer-headers.js'), ...args],
    { encoding: 'utf8', env: { ...limpio, K0LMENA_ENV_FILE: archivo } });
  fs.rmSync(dir, { recursive: true, force: true });
  return r;
}

test('bearer-headers: token como Bearer; opcional sin token deja OAuth; obligatorio sin token corta', () => {
  const ok = helper(['linear', 'LINEAR_API_KEY', '--opcional'], { LINEAR_API_KEY: 'lin_api_prueba' });
  assert.equal(ok.status, 0, ok.stderr);
  assert.deepEqual(JSON.parse(ok.stdout), { Authorization: 'Bearer lin_api_prueba' });
  const oauth = helper(['monday', 'MONDAY_API_TOKEN', '--opcional'], {});
  assert.deepEqual(JSON.parse(oauth.stdout), {});
  const falta = helper(['youtrack', 'YOUTRACK_TOKEN'], {});
  assert.equal(falta.status, 1);
  assert.match(falta.stderr, /youtrack: falta YOUTRACK_TOKEN/);
  assert.equal(helper(['x', 'nombre-invalido'], {}).status, 1);
});

// ---------------------------------------------------------------- catálogo y activación
test('catálogo: cada conector tiene grupo, origen y descripción en inglés, y ningún secreto', () => {
  const { CATALOGO, porGrupo } = require(path.join(RAIZ, 'scripts/mcp/conector.js'));
  for (const n of Object.keys(CATALOGO)) {
    assert.ok(CATALOGO[n].grupo && CATALOGO[n].descripcion_en, `${n}: falta grupo o descripcion_en`);
    assert.ok(['oficial', 'comunitario'].includes(CATALOGO[n].origen), n);
    assert.doesNotMatch(JSON.stringify(CATALOGO[n].servidor), /\|/, `${n}: un | se interpreta como pipe en el shell`);
    assert.doesNotMatch(JSON.stringify(CATALOGO[n]), /Bearer [\w-]|Basic [A-Za-z0-9+/=]{8,}|token=|secret=/, n);
  }
  assert.ok(Object.keys(porGrupo()).includes('Gestión de pruebas'));
});

test('activación: la URL usa la variable del .env o, si falta, el valor por defecto (no depende de que Claude Code expanda :-)', () => {
  const { conVariablesDelEnv } = require(path.join(RAIZ, 'scripts/mcp/conector.js'));
  const previo = process.env.POSTMAN_MCP_URL;
  try {
    delete process.env.POSTMAN_MCP_URL;
    assert.equal(conVariablesDelEnv('${POSTMAN_MCP_URL:-https://mcp.postman.com/minimal}'), 'https://mcp.postman.com/minimal');
    process.env.POSTMAN_MCP_URL = 'https://mcp.eu.postman.com/minimal/';
    assert.equal(conVariablesDelEnv('${POSTMAN_MCP_URL:-https://mcp.postman.com/minimal}'), 'https://mcp.eu.postman.com/minimal');
    assert.equal(conVariablesDelEnv('${VARIABLE_QUE_NO_EXISTE_K0}'), '${VARIABLE_QUE_NO_EXISTE_K0}');
  } finally {
    if (previo === undefined) delete process.env.POSTMAN_MCP_URL; else process.env.POSTMAN_MCP_URL = previo;
  }
});


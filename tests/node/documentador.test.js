// Tests del documentador-proyecto: mapa funcional (k0lmena tools) y conectores de repositorio.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const RAIZ = path.resolve(__dirname, '..', '..');
const mapa = require(path.join(RAIZ, 'herramientas/k0lmena/tools/mapa-funcional/mapear.js'));

// Corre un headersHelper con un .env de prueba y sin las variables del entorno real.
function headers(script, env) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'k0-doc-'));
  const archivo = path.join(dir, '.env');
  fs.writeFileSync(archivo, Object.entries(env).map(([k, v]) => `${k}=${v}`).join('\n'));
  const limpio = Object.fromEntries(Object.entries(process.env).filter(([k]) => !/^(GITHUB|GITLAB)_/.test(k)));
  const r = spawnSync(process.execPath, [path.join(RAIZ, 'scripts/mcp', script)], { encoding: 'utf8', env: { ...limpio, K0LMENA_ENV_FILE: archivo } });
  fs.rmSync(dir, { recursive: true, force: true });
  return r;
}

test('mapa funcional: valida los argumentos', () => {
  assert.deepEqual(mapa.argumentos(['--paginas', 'https://a.com/x, https://a.com/y']).paginas, ['https://a.com/x', 'https://a.com/y']);
  assert.throws(() => mapa.argumentos(['--max-paginas', '0']));
  assert.throws(() => mapa.argumentos(['--profundidad', '9']));
  assert.throws(() => mapa.argumentos(['--otra']));
});

test('mapa funcional: los menús que se repiten en el sitio van una sola vez como navegación global', () => {
  const menu = { nombre: 'Encabezado', items: ['Inicio', 'Productos', 'Contacto'] };
  const paginas = [
    { menus: [menu, { nombre: 'Lateral', items: ['Filtros'] }] },
    { menus: [{ ...menu, items: [...menu.items] }] },
    { menus: [{ ...menu, items: [...menu.items] }] },
  ];
  const globales = mapa.separarMenusGlobales(paginas);
  assert.deepEqual(globales, [menu]);
  assert.deepEqual(paginas[0].menus, [{ nombre: 'Lateral', items: ['Filtros'] }]);
  assert.deepEqual(paginas[1].menus, []);
});

test('mapa funcional: markdown con encabezado para el índice, formularios y restricciones', () => {
  const campo = { nombre: 'email', etiqueta: 'Email *', tipo: 'email', requerido: true, maxlength: 80, minlength: null, min: null, max: null, pattern: null, opciones: null, placeholder: 'tu@mail.com' };
  const md = mapa.aMarkdown({ url: 'https://a.com/', host: 'a.com', fecha: '2026-10-14T10:00:00.000Z', max_paginas: 30, sin_recorrer: true,
    navegacion_global: [{ nombre: 'Encabezado', items: ['Inicio', 'Registro'] }],
    paginas: [
      { url: 'https://a.com/registro', ruta: '/registro', titulo: 'Registro', descripcion: '', encabezados: [{ nivel: 1, texto: 'Crear cuenta' }], menus: [], botones: ['Cancelar'],
        mensajes: ['Todos los campos son obligatorios'], tablas: [], extracto: '', formularios: [{ nombre: 'registro', metodo: 'POST', accion: '/api/registro', campos: [campo], boton: true }] },
      { url: 'https://a.com/caida', ruta: '/caida', error: 'net::ERR_TIMED_OUT' },
    ] });
  assert.match(md, /^---\ntitulo: Mapa funcional del sitio\ntipo: web\nfuentes: https:\/\/a\.com\/\nactualizado: 2026-10-14\n/);
  assert.match(md, /subí --max-paginas/);
  assert.match(md, /- \*\*Encabezado\*\*: Inicio · Registro/);
  assert.match(md, /### Formulario: registro \(POST \/api\/registro\)/);
  assert.match(md, /\| email \| Email \* \| email \| Sí \| máx\. 80 caracteres; placeholder "tu@mail\.com" \|/);
  assert.match(md, /No se pudo abrir: net::ERR_TIMED_OUT/);
  assert.doesNotMatch(md, /\n\n\n/);
});

test('mapa funcional: restricciones de un campo en una línea', () => {
  assert.equal(mapa.restricciones({ min: 18, max: 99, pattern: '\\d+', opciones: [{ valor: '', texto: 'Elegí' }, { valor: 'AR', texto: 'Argentina' }] }),
    'mínimo 18; máximo 99; patrón \\d+; opciones: Elegí, Argentina');
});

test('conector github: token como Bearer, solo lectura y toolsets; sin token corta con un mensaje claro', () => {
  const ok = headers('github-headers.js', { GITHUB_TOKEN: 'ghp_prueba' });
  assert.equal(ok.status, 0, ok.stderr);
  assert.deepEqual(JSON.parse(ok.stdout), { Authorization: 'Bearer ghp_prueba', 'X-MCP-Readonly': 'true', 'X-MCP-Toolsets': 'context,repos,issues,pull_requests' });
  const sin = headers('github-headers.js', {});
  assert.equal(sin.status, 1);
  assert.match(sin.stderr, /falta GITHUB_TOKEN/);
  assert.doesNotMatch(sin.stdout + sin.stderr, /ghp_/);
  assert.equal(headers('github-headers.js', { GITHUB_TOKEN: 'x', GITHUB_TOOLSETS: 'repos;rm' }).status, 1);
});

test('conector gitlab: sin token deja OAuth (solo toolsets); con token agrega el Bearer', () => {
  const oauth = JSON.parse(headers('gitlab-headers.js', {}).stdout);
  assert.deepEqual(oauth, { 'X-Gitlab-Enabled-Mcp-Server-Toolsets': 'meta,core,merge_requests,work_items,repository,wikis' });
  const conToken = JSON.parse(headers('gitlab-headers.js', { GITLAB_TOKEN: 'glpat-prueba', GITLAB_TOOLSETS: 'repository, merge_requests' }).stdout);
  assert.equal(conToken.Authorization, 'Bearer glpat-prueba');
  assert.equal(conToken['X-Gitlab-Enabled-Mcp-Server-Toolsets'], 'repository,merge_requests');
});

test('mapa funcional: compara con el recorrido anterior (pantallas, campos, reglas y botones)', () => {
  const antes = { host: 'a', paginas: [
    { ruta: '/alta', titulo: 'Alta', botones: ['Guardar'], formularios: [{ nombre: 'f', campos: [
      { etiqueta: 'Razón', tipo: 'text', requerido: true, maxlength: 100 }, { etiqueta: 'Fax', tipo: 'text' }] }] },
    { ruta: '/viejo', titulo: 'x' }, { ruta: '/caida', error: 'timeout' }] };
  const ahora = { host: 'a', paginas: [
    { ruta: '/alta', titulo: 'Alta', botones: ['Guardar', 'Borrar'], formularios: [{ nombre: 'f', campos: [
      { etiqueta: 'Razón', tipo: 'text', requerido: true, maxlength: 150 }, { etiqueta: 'Email', tipo: 'email' }] }] },
    { ruta: '/nuevo', titulo: 'y' }] };
  const c = mapa.compararMapas(antes, ahora);
  assert.deepEqual(c.nuevas, ['/nuevo']);
  assert.deepEqual(c.quitadas, ['/viejo']);
  assert.deepEqual(c.paginas[0], { ruta: '/alta', campos_nuevos: ['f › Email'], campos_quitados: ['f › Fax'],
    campos_cambiados: ['f › Razón'], botones_nuevos: ['Borrar'], botones_quitados: [], titulo: null });
  assert.equal(mapa.compararMapas(ahora, ahora).hay, false);
});

test('mapa funcional: markdown con sesión, cambios y locators sugeridos', () => {
  const md = mapa.aMarkdown({ url: 'https://a.com/', host: 'a.com', fecha: '2026-10-23T10:00:00.000Z', max_paginas: 30, sin_recorrer: false,
    con_sesion: 'sesion.json', navegacion_global: [],
    cambios: { desde: '2026-10-01T00:00:00Z', hay: true, nuevas: ['/nuevo'], quitadas: [], paginas: [
      { ruta: '/alta', campos_nuevos: ['f › Email'], campos_quitados: [], campos_cambiados: [], botones_nuevos: [], botones_quitados: [], titulo: null }] },
    paginas: [{ url: 'https://a.com/alta', ruta: '/alta', titulo: 'Alta', descripcion: '', encabezados: [], menus: [], botones: [], mensajes: [],
      tablas: [], extracto: '', formularios: [],
      locators: [{ elemento: 'Guardar', rol: 'button', locator: "getByTestId('guardar')", unico: true },
        { elemento: 'Cancelar', rol: 'button', locator: "getByRole('button', { name: 'Cancelar' })", unico: false }] }] });
  assert.match(md, /\*\*con la sesión iniciada\*\* \(sesion\.json\)/);
  assert.doesNotMatch(md, /Sin sesión:/);
  assert.match(md, /## Cambios desde el recorrido anterior \(2026-10-01\)/);
  assert.match(md, /- Pantallas nuevas: \/nuevo/);
  assert.match(md, /- \/alta: campos nuevos: f › Email/);
  assert.match(md, /### Locators sugeridos/);
  assert.match(md, /\| Guardar \| button \| `getByTestId\('guardar'\)` \| Sí \|/);
  assert.match(md, /\| Cancelar \| button \| .* \| No \|/);
});

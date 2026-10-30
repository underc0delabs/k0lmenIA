// Tests del probador de formularios y el evaluador de UX (k0lmena tools).
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');

const K0 = path.resolve(__dirname, '..', '..', 'herramientas/k0lmena');
const formularios = require(path.join(K0, 'tools/formularios/formularios.js'));
const ux = require(path.join(K0, 'tools/ux/evaluar.js'));

const campo = (extra) => ({ n: 1, nombre: 'x', etiqueta: '', fuente_etiqueta: 'label', tipo: 'text', requerido: false, marca_obligatorio: false,
  maxlength: null, minlength: null, min: null, max: null, step: null, pattern: null, autocomplete: null, placeholder: null, ...extra });

test('formularios: las pruebas dependen del tipo de campo', () => {
  const reglas = (c) => formularios.pruebasPara(campo(c)).map((p) => p.regla);
  assert.deepEqual(reglas({ nombre: 'email', etiqueta: 'Email', requerido: true }).slice(0, 2), ['Obligatorio vacío', 'Solo espacios']);
  assert.ok(reglas({ nombre: 'email', etiqueta: 'Email' }).includes('Email sin @'));
  assert.ok(reglas({ tipo: 'number', min: 18, max: 99 }).includes('Mayor al máximo (99)'));
  assert.ok(reglas({ nombre: 'nombre', etiqueta: 'Nombre' }).includes('Nombre con acentos, ñ y apóstrofe'));
  assert.ok(reglas({ nombre: 'tel', etiqueta: 'Teléfono' }).includes('Teléfono con letras'));
  assert.deepEqual(reglas({ tipo: 'checkbox', requerido: true }), ['Obligatorio sin marcar']);
  assert.deepEqual(reglas({ tipo: 'select', requerido: true, opciones: [{ valor: '' }, { valor: 'AR' }] }), ['Obligatorio sin elegir']);
});

test('formularios: hallazgos de las pruebas y del campo', () => {
  const c = campo({ nombre: 'email', etiqueta: 'Email', requerido: true, pruebas: [
    { regla: 'Email sin @', valor: 'ana', esperado: 'rechaza', resultado: 'acepta', ok: false },
    { regla: 'Email válido', valor: 'ana@test.com', esperado: 'acepta', resultado: 'rechaza', ok: false, mensaje: 'Inválido' },
    { regla: 'Obligatorio vacío', valor: '', esperado: 'rechaza', resultado: 'rechaza', ok: true, fuente: 'navegador', mensaje: 'Please fill out this field.' }] });
  const tipos = formularios.hallazgosDe({ id: 'F-01' }, c).map((h) => `${h.severidad}:${h.tipo}`);
  assert.ok(tipos.includes('Alta:Acepta un valor inválido') && tipos.includes('Alta:Rechaza un valor válido'));
  assert.ok(tipos.includes('Media:Obligatorio') && tipos.includes('Media:Tipo de campo') && tipos.includes('Baja:Mensaje de error'));
});

test('ux: las 10 heurísticas de Nielsen y los grupos de sinónimos', () => {
  assert.equal(Object.keys(ux.HEURISTICAS).length, 10);
  assert.ok(ux.SINONIMOS.some((g) => g.includes('iniciar sesión') && g.includes('login')));
  assert.throws(() => ux.argumentos(['--historia', 'mal']));
});

test('formularios: --enviar-vacio aprieta el botón de ESE formulario, no el primero de la página', () => {
  const llamadas = [];
  const loc = (sel) => ({ locator: (s) => { llamadas.push(s); return loc(s); }, first: () => ({ sel }) });
  const page = { locator: (s) => { llamadas.push(s); return loc(s); } };
  formularios.botonEnvio(page, { campos: [{ n: 7 }, { n: 8 }] });
  assert.equal(llamadas[0], '[data-k0-campo="7"]');
  assert.equal(llamadas[1], 'xpath=ancestor::form[1]');
  assert.ok(llamadas[2].includes('button[type=submit]') && !llamadas[2].startsWith('form '));
});

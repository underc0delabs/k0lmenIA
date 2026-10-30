// Tests de pixel-perfect, cross-browser y el reparador de la automatización (k0lmena tools).
// La comparación de imágenes usa pngjs (dependencia de k0lmena): si no está instalado, esos tests se saltean.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');

const RAIZ = path.resolve(__dirname, '..', '..');
const K0 = path.join(RAIZ, 'herramientas/k0lmena');
const visual = require(path.join(K0, 'tools/visual/comparar.js'));
const pixel = require(path.join(K0, 'tools/pixel-perfect/pixel-perfect.js'));
const cross = require(path.join(K0, 'tools/cross-browser/cross-browser.js'));
const reparar = require(path.join(K0, 'tools/reparador/reparar.js'));

let PNG = null;
try { ({ PNG } = require(require.resolve('pngjs', { paths: [K0] }))); } catch { /* sin k0lmena instalado */ }

const el = (clave, tag, x, y, w = 100, h = 20, estilo = { fondo: '#ffffff', color: '#000000', letra: '16px', peso: '400' }) =>
  ({ clave, tag, texto: clave.split('|')[1] || '', desc: tag, x, y, w, h, estilo });

test('visual: detecta corridos, faltantes, nuevos, textos y estilos cambiados', () => {
  const ref = [el('a|Inicio|1', 'a', 10, 10), el('a|Ayuda|1', 'a', 200, 10), el('h1|Bienvenido|1', 'h1', 10, 60, 300, 40),
    el('button|Comprar|1', 'button', 10, 120)];
  const act = [el('a|Inicio|1', 'a', 50, 10), el('h1|Ofertas|1', 'h1', 10, 60, 300, 40),
    el('button|Comprar|1', 'button', 10, 120, 100, 20, { fondo: '#ff0000', color: '#000000', letra: '16px', peso: '400' }),
    el('div|Promo|1', 'div', 0, 300, 400, 40)];
  const c = visual.compararElementos(ref, act, { tolerancia: 3 });
  assert.equal(c.movidos.length, 1);
  assert.equal(c.movidos[0].dx, 40);
  assert.deepEqual(c.faltantes.map((x) => x.clave), ['a|Ayuda|1']);
  assert.deepEqual(c.cambiados.map((x) => `${x.clave}→${x.actual.clave}`), ['h1|Bienvenido|1→h1|Ofertas|1']);
  assert.deepEqual(c.nuevos.map((x) => x.clave), ['div|Promo|1']);
  assert.equal(c.estilos[0].prop, 'fondo');
  assert.equal(c.estilos[0].a, '#ff0000');
});

test('visual: muchos elementos que se movieron igual son un solo bloque', () => {
  const ref = Array.from({ length: 6 }, (_, i) => el(`p|t${i}|1`, 'p', 10, 100 + i * 30));
  const act = ref.map((x) => ({ ...x, y: x.y + 46 }));
  const c = visual.compararElementos(ref, act);
  assert.equal(c.bloques.length, 1);
  assert.equal(c.bloques[0].dy, 46);
  assert.equal(c.bloques[0].elementos, 6);
  assert.equal(c.movidos.length, 0);
});

test('visual: la diferencia de píxeles y sus regiones', { skip: !PNG && 'pngjs no está instalado' }, () => {
  const lienzo = (pintar) => {
    const p = new PNG({ width: 64, height: 48 });
    p.data.fill(255);
    if (pintar) for (let y = 8; y < 24; y++) for (let x = 8; x < 24; x++) { const o = (y * 64 + x) * 4; p.data[o] = p.data[o + 1] = p.data[o + 2] = 0; }
    return PNG.sync.write(p);
  };
  assert.equal(visual.compararPng(lienzo(false), lienzo(false)).pct, 0);
  const r = visual.compararPng(lienzo(false), lienzo(true));
  assert.equal(r.distintos, 256);
  assert.equal(r.regiones.length, 1);
  const rec = PNG.sync.read(visual.recorteMarcado(lienzo(true), { x: 0, y: 0, w: 40, h: 30 }, { x: 8, y: 8, w: 16, h: 16 }));
  assert.equal(rec.width, 40);
});

test('pixel-perfect: resoluciones, IDs de pantalla y hallazgos con causa', () => {
  assert.deepEqual(pixel.parsearResoluciones('390x844,1366x768').map((r) => r.nombre), ['Mobile', 'Desktop']);
  assert.throws(() => pixel.parsearResoluciones('grande'));
  assert.equal(pixel.idPantalla(1, 'https://x.com/', '390x844'), '01-inicio-390x844');
  const nuevo = el('div|Envío gratis|1', 'div', 0, 54, 1366, 46);
  const desde = el('p|Comprá|1', 'p', 10, 200);
  const p = { pct: 10, regiones: [], alto: 1046, alto_ref: 1000,
    elementos_cmp: { bloques: [{ dx: 0, dy: 46, elementos: 8, desde, caja: {}, ejemplos: [] }], movidos: [], redimensionados: [], cambiados: [],
      faltantes: [], nuevos: [nuevo], estilos: [] } };
  const h = pixel.hallazgosDe(p, { pctMax: 0.2 });
  const bloque = h.find((x) => x.tipo === 'Bloque desplazado');
  assert.match(bloque.titulo, /8 elementos bajaron 46 px/);
  assert.match(bloque.detalle, /Causa probable: apareció “Envío gratis”/);
  assert.ok(h.some((x) => x.tipo === 'Alto de la página'));
});

test('cross-browser: lo que falla solo en algunos navegadores es una diferencia', () => {
  const esc = (estado) => ({ clave: 'f:3', escenario: 'Pagar', uri: 'f', linea: 3, historia: 'HU-1', caso: 'CP-001', estado,
    paso: estado === 'Fallido' ? 'Then ve el ok' : null, error: estado === 'Fallido' ? 'Error: no' : '' });
  const corridas = [{ id: 'chromium-1366x768', escenarios: [esc('Aprobado')] }, { id: 'firefox-1366x768', escenarios: [esc('Fallido')] },
    { id: 'webkit-1366x768', escenarios: [esc('Aprobado')] }];
  const { filas, hallazgos } = cross.analizarSuite(corridas, 'chromium');
  assert.equal(filas[0].clase, 'Diferencia entre navegadores');
  assert.deepEqual(hallazgos[0].fallan, ['firefox-1366x768']);
  assert.match(hallazgos[0].titulo, /falla en Firefox 1366x768/);
  const todos = cross.analizarSuite(corridas.map((c) => ({ ...c, escenarios: [esc('Fallido')] })), 'chromium');
  assert.equal(todos.filas[0].clase, 'Falla en todos');
  assert.equal(cross.sinAnsi('\x1b[2m- hola\x1b[22m'), '- hola');
});

test('reparador: saca el locator del error de Playwright', () => {
  const l = reparar.locatorDelError("locator.click: Timeout 8000ms exceeded.\nCall log:\n  - waiting for getByRole('button', { name: 'Suscribirse' })");
  assert.deepEqual(l.input, { role: 'button', name: 'Suscribirse' });
  assert.deepEqual(reparar.locatorDelError("Locator: getByPlaceholder('tu@email.com')\nExpected: visible").input, { placeholder: 'tu@email.com' });
  assert.deepEqual(reparar.locatorDelError("strict mode violation: getByText('Mate') resolved to 2 elements").input, { text: 'Mate' });
  assert.deepEqual(reparar.locatorDelError("waiting for locator('#btn-pagar')").input, { css: '#btn-pagar' });
  assert.deepEqual(reparar.locatorDelError("getByRole('heading', { name: /ofertas/i, exact: true })").input,
    { role: 'heading', name: { regex: 'ofertas', flags: 'i' }, exact: true });
  assert.equal(reparar.locatorDelError('AssertionError: expected 1 to equal 2'), null);
});

test('reparador: arma el código del locator y lo reemplaza en su línea', () => {
  assert.equal(reparar.codigoDe({ role: 'button', name: "Pagar ahora" }), "{ role: 'button', name: 'Pagar ahora' }");
  assert.equal(reparar.codigoDe({ text: "l'agenda" }), "{ text: 'l\\'agenda' }");
  const r = { locator: { input: { role: 'button', name: 'Suscribirse' } }, ubicacion: { tipo: 'locator' },
    propuesta: { codigo: "{ role: 'button', name: 'Suscribirme' }", input: { role: 'button', name: 'Suscribirme' } } };
  assert.equal(reparar.reemplazarEnLinea("  btn: { role: 'button', name: 'Suscribirse' },", r), "  btn: { role: 'button', name: 'Suscribirme' },");
  const f = { ...r, ubicacion: { tipo: 'feature', valor: 'Cupones' }, propuesta: { input: { role: 'heading', name: 'Promos' } } };
  assert.equal(reparar.reemplazarEnLinea('    Then ve la tarjeta "Cupones"', f), '    Then ve la tarjeta "Promos"');
  const props = reparar.propuestasPara({ tag: 'button', rol: 'button', nombre: 'Agregar', texto: 'Agregar', id: 'agregar-1' });
  assert.deepEqual(props[0], { role: 'button', name: 'Agregar' });
  assert.ok(props.some((p) => p.css === '#agregar-1'));
});

test('pixel-perfect: sin --ocultar se reutilizan las zonas ocultas de la referencia', () => {
  const ref = { config: { ocultar: ['.banner', '.fecha'] } };
  assert.deepEqual(pixel.ocultarEfectivo({ ocultar: [] }, ref), ['.banner', '.fecha']);
  assert.deepEqual(pixel.ocultarEfectivo({ ocultar: ['.otra'] }, ref), ['.otra']);
  assert.deepEqual(pixel.ocultarEfectivo({ ocultar: [] }, null), []);
});

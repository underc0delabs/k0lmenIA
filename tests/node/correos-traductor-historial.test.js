// Tests del verificador de correos, el analista de traducciones y el historial de corridas (k0lmena tools).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const K0 = path.resolve(__dirname, '..', '..', 'herramientas/k0lmena');
const correos = require(path.join(K0, 'tools/correos/correos.js'));
const trad = require(path.join(K0, 'tools/traductor/traductor.js'));
const historial = require(path.join(K0, 'tools/historial/historial.js'));

test('correos: variables sin reemplazar, links a localhost, imágenes y texto plano', () => {
  const m = { Subject: 'Tu pedido {{numero}} está listo', From: { Address: 'a@b.com' }, To: [{ Address: 'ana@test.com' }], Text: '',
    HTML: '<p>Hola undefined</p><img src="/logo.png"><a href="http://localhost:3000/x">Ver</a><a href="https://ok.com/y">Ok</a>' };
  const r = correos.revisar(m, { links: [{ URL: 'https://ok.com/y', StatusCode: 404 }] });
  const tipos = r.hallazgos.map((h) => h.tipo);
  assert.ok(tipos.filter((t) => t === 'Variable sin reemplazar').length >= 2);
  assert.ok(tipos.includes('Texto plano') && tipos.includes('Imágenes'));
  const link = r.hallazgos.filter((h) => h.tipo === 'Link').map((h) => h.titulo).join(' | ');
  assert.match(link, /ambiente local/);
  assert.match(link, /roto \(404\)/);
  assert.equal(correos.consulta({ para: 'ana@test.com', asunto: 'Hola' }), 'to:"ana@test.com" subject:"Hola"');
});

test('correos: expectativas que cumplen, no cumplen y no llegan', () => {
  const c = [{ id: 'M-01', para: ['ana@test.com'], asunto: 'Bienvenida a la tienda', de: 'no-reply@x.com', texto: 'Hola Ana', texto_html: 'Hola Ana',
    links: [{ url: 'https://x.com/confirmar?t=1' }], adjuntos: [{ nombre: 'factura.pdf' }] }];
  const r = correos.evaluarEspera([
    { para: 'ana@test.com', asunto: 'bienvenida', contiene: ['Hola Ana'], links: ['/confirmar'], adjuntos: ['factura'] },
    { para: 'ana@test.com', asunto: 'bienvenida', no_contiene: ['Ana'] },
    { para: 'ana@test.com', asunto: 'Recuperá tu contraseña' }], c);
  assert.deepEqual(r.map((x) => x.estado), ['Cumple', 'No cumple', 'No llegó']);
  const compat = correos.resumirCompat({ Total: { Supported: 71.4 }, Warnings: [{ Title: 'border-radius', Results: [{ Family: 'Outlook', Platform: 'windows', Support: 'no' }] }] });
  assert.equal(compat.pct, 71);
  assert.deepEqual(compat.problemas[0].clientes, ['Outlook (windows)']);
});

test('traductor: detecta el idioma de textos largos y cortos', () => {
  assert.equal(trad.detectarIdioma('Comprá lo que necesites con envío gratis a todo el país'), 'es');
  assert.equal(trad.detectarIdioma('Welcome to the store, find all the products you need'), 'en');
  assert.equal(trad.detectarIdioma('Buscar produtos'), 'pt');
  assert.equal(trad.detectarIdioma('Buscar productos'), 'es');
  assert.equal(trad.detectarIdioma('Hola Ana'), null);
});

test('traductor: claves, codificación, formatos y meses', () => {
  assert.ok(trad.CLAVE.test('checkout.add_to_cart') && trad.CLAVE.test('translation missing: en.home.title'));
  assert.ok(!trad.CLAVE.test('www.example'.toUpperCase()));
  assert.ok(trad.MOJIBAKE.test('EnvÃ­o gratis') && !trad.MOJIBAKE.test('Envío gratis'));
  assert.deepEqual(trad.formatoNumeroRaro('Price: $ 1.234,56', 'en-US'), ['1.234,56']);
  assert.deepEqual(trad.formatoNumeroRaro('Precio: $ 1.234,56', 'es-AR'), []);
  assert.deepEqual(trad.formatoNumeroRaro('Total 1,234.56', 'es-AR'), ['1,234.56']);
  assert.deepEqual(trad.mesesDeOtroIdioma('Deals valid until 15 de octubre', 'en-US'), ['octubre']);
  assert.deepEqual(trad.mesesDeOtroIdioma('Válido hasta el 15 de octubre', 'es-AR'), []);
});

test('traductor: URL de cada idioma y hallazgos de una pantalla', () => {
  const alt = [{ idioma: 'en', url: 'https://x.com/en/' }, { idioma: 'pt-BR', url: 'https://x.com/pt/' }];
  assert.deepEqual(trad.urlEnIdioma('https://x.com/es/', 'en-US', alt, '', 'es'), { url: 'https://x.com/en/', metodo: 'hreflang' });
  assert.equal(trad.urlEnIdioma('https://x.com/es/productos', 'pt', null, 'https://x.com/{idioma_corto}/', 'es').url, 'https://x.com/pt/productos');
  assert.equal(trad.urlEnIdioma('https://x.com/', 'en', null, '?lang={idioma_corto}', 'es').url, 'https://x.com/?lang=en');
  const ref = { lang: 'es', desborde: 0, textos: [{ clave: 'main:1>p:1', texto: 'Envío gratis a todo el país hoy' }] };
  const en = { lang: 'es', desborde: 0, textos: [{ clave: 'main:1>p:1', texto: 'Envío gratis a todo el país hoy', x: 0, y: 0, w: 10, h: 10 },
    { clave: 'main:1>button:1', texto: 'checkout.pay', x: 0, y: 0, w: 10, h: 10 },
    { clave: 'main:1>button:2', texto: 'Add to cart now please', corta: true, x: 0, y: 0, w: 10, h: 10 }] };
  const tipos = trad.hallazgosDePantalla(en, ref, 'en-US', 'es-AR').map((h) => h.tipo);
  assert.ok(tipos.includes('Atributo lang') && tipos.includes('Sin traducir') && tipos.includes('Clave de traducción') && tipos.includes('Texto cortado'));
});

test('historial: guarda la corrida anterior y deja solo las últimas 5', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'k0hist-'));
  for (let i = 1; i <= 7; i++) {
    fs.writeFileSync(path.join(dir, 'datos.json'), JSON.stringify({ marca: `2026101${i}-120000` }));
    fs.mkdirSync(path.join(dir, 'capturas'), { recursive: true });
    fs.writeFileSync(path.join(dir, 'capturas', 'a.png'), 'x');
    const destino = historial.archivar(dir, ['datos.json', 'capturas'], 'datos.json', 5);
    assert.ok(fs.existsSync(path.join(destino, 'capturas', 'a.png')));
    assert.ok(!fs.existsSync(path.join(dir, 'datos.json')));
  }
  const guardadas = fs.readdirSync(path.join(dir, 'historial')).sort();
  assert.equal(guardadas.length, 4);   // 4 anteriores + la actual = 5
  assert.equal(guardadas[0], '20261014-120000');
  fs.writeFileSync(path.join(dir, 'datos.json'), '[]');
  assert.equal(historial.archivar(dir, ['datos.json'], 'datos.json'), null); // un reporte vacío no es una corrida
  fs.rmSync(dir, { recursive: true, force: true });
});

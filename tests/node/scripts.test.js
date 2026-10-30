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

const explorador = require(path.join(RAIZ, 'herramientas/k0lmena/tools/explorador/explorar.js'));

test('explorador: normaliza URLs, valida resoluciones y clasifica links', () => {
  assert.equal(explorador.normalizar('https://x.com/a/#seccion'), 'https://x.com/a');
  assert.equal(explorador.normalizar('https://x.com/'), 'https://x.com/');
  assert.equal(explorador.slug('https://x.com/'), 'inicio');
  assert.equal(explorador.slug('https://x.com/Blog/Post?id=3'), 'blog-post-id-3');
  assert.deepEqual(explorador.parsearResoluciones('360x740, 1366x768').map((r) => r.nombre), ['Mobile', 'Desktop']);
  assert.throws(() => explorador.parsearResoluciones('grande'), /Resolución inválida/);
  assert.equal(explorador.clasificarLink({ status: 200 }), 'ok');
  assert.equal(explorador.clasificarLink({ status: 404 }), 'roto');
  assert.equal(explorador.clasificarLink({ status: 403 }), 'no_verificable');
  assert.equal(explorador.clasificarLink({ status: 0, error: 'timeout' }), 'no_verificable');
  assert.equal(explorador.clasificarLink({ status: 0, error: 'ENOTFOUND', caido: true }), 'roto');
});

test('explorador: arma hallazgos con severidad y agrupa el responsive por página', () => {
  const pagina = { url: 'https://x.com/', status: 200, meta_viewport: 'width=device-width', errores_js: ['boom'], errores_consola: [],
    recursos_fallidos: [{ url: 'https://x.com/a.js', status: 404, tipo: 'script' }], imagenes_rotas: [{ src: 'https://x.com/a.png' }], imagenes_sin_alt: 0 };
  const links = [{ url: 'https://x.com/no', interno: true, status: 404, resultado: 'roto', origenes: ['https://x.com/'] }];
  const fila = (res, ancho) => ({ url: 'https://x.com/', resolucion: res, nombre: 'Mobile', ancho, desborde_horizontal: true, ancho_documento: 500,
    ancho_ventana: ancho, elementos_desbordados: [{ elemento: 'div.tabla', ancho: 500 }], texto_chico: 0, objetivos_tactiles_chicos: 0 });
  const h = explorador.armarHallazgos([pagina], links, [fila('360x740', 360), fila('390x844', 390)]);
  assert.deepEqual(h.map((x) => x.id), h.map((_, i) => `H-${String(i + 1).padStart(2, '0')}`));
  assert.ok(h.every((x, i) => i === 0 || ['Crítica', 'Alta', 'Media', 'Baja'].indexOf(h[i - 1].severidad) <= ['Crítica', 'Alta', 'Media', 'Baja'].indexOf(x.severidad)));
  const resp = h.filter((x) => x.categoria === 'Responsive');
  assert.equal(resp.length, 1);
  assert.deepEqual(resp[0].resoluciones, ['360x740', '390x844']);
  assert.equal(resp[0].severidad, 'Alta');
  for (const cat of ['Error de JavaScript', 'Recurso que falla', 'Imagen rota', 'Link roto']) assert.ok(h.some((x) => x.categoria === cat), cat);
});

test('explorador: cada corrida borra solo lo que generó la anterior', () => {
  const dir = tmp();
  for (const f of ['exploracion.json', 'analisis.json', 'informe-exploratorio.html', 'notas.txt']) fs.writeFileSync(path.join(dir, f), 'x');
  fs.mkdirSync(path.join(dir, 'capturas', 'manual'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'capturas', 'manual', 'ex-01.png'), 'x');
  fs.mkdirSync(path.join(dir, 'videos'));
  explorador.limpiarCarpeta(dir);
  assert.deepEqual(fs.readdirSync(dir), ['notas.txt']);
  explorador.limpiarCarpeta(path.join(dir, 'no-existe')); // sin corrida anterior no falla
});

test('explorador: un problema repetido en varias páginas es un solo hallazgo, con su evidencia', () => {
  const pag = (url) => ({ url, status: 200, meta_viewport: 'x', errores_js: [], errores_consola: [], imagenes_rotas: [], imagenes_sin_alt: 0,
    recursos_fallidos: [{ url: 'https://x.com/estilos.css', status: 404, tipo: 'stylesheet' }], captura: `capturas/paginas/${url.length}.jpg`, tiempo_ms: 500 });
  const h = explorador.armarHallazgos([pag('https://x.com/'), pag('https://x.com/otra')], [], []);
  assert.equal(h.length, 1);
  assert.deepEqual(h[0].paginas, ['https://x.com/', 'https://x.com/otra']);
  assert.ok(h[0].evidencia.startsWith('capturas/paginas/'));
  const lenta = explorador.armarHallazgos([{ ...pag('https://x.com/'), recursos_fallidos: [], tiempo_ms: 7000 }], [], [], { lentaMs: 3000 });
  assert.equal(lenta[0].categoria, 'Rendimiento');
  assert.equal(lenta[0].severidad, 'Media');
  assert.deepEqual(explorador.tiempos([{ tiempo_ms: 1000 }, { tiempo_ms: 3000 }, { error: 'x' }]),
    { carga_promedio_ms: 2000, carga_max_ms: 3000, carga_p90_ms: 3000 });
});

const a11y = require(path.join(RAIZ, 'herramientas/k0lmena/tools/accesibilidad/auditar.js'));

test('accesibilidad: criterios WCAG, nivel y severidad desde los tags de axe', () => {
  assert.deepEqual(a11y.criterios(['cat.color', 'wcag2aa', 'wcag143', 'wcag1410']), ['1.4.3', '1.4.10']);
  assert.equal(a11y.nivelDe(['wcag2a', 'wcag111']), 'A');
  assert.equal(a11y.nivelDe(['wcag21aa']), 'AA');
  assert.equal(a11y.nivelDe(['best-practice']), null);
  assert.equal(a11y.severidad('critical', ['wcag2a', 'wcag111']), 'Crítica');
  assert.equal(a11y.severidad('serious', ['best-practice']), 'Media'); // buena práctica: baja un nivel
  assert.equal(a11y.argumentos(['--nivel', 'aaa']).nivel, 'AAA');
  assert.throws(() => a11y.argumentos(['--nivel', 'B']), /A, AA o AAA/);
});

test('accesibilidad: agrupa por regla entre páginas y suma teclado y reflow', () => {
  const v = { id: 'image-alt', impacto: 'critical', titulo: 'Imágenes sin alt', tags: ['wcag2a', 'wcag111'], total_nodos: 2,
    nodos: [{ selector: 'img', html: '<img>' }, { selector: 'img.b', html: '<img>' }] };
  const pag = (url, extra = {}) => ({ url, violaciones: [v], revisar: [], aprobadas: ['a', 'b', 'c'],
    teclado: { pasos: [{ elemento: 'a', texto: 'Saltar al contenido', visible_indicador: true }], trampa: null }, ...extra });
  const { hallazgos } = a11y.armarHallazgos([
    pag('https://x.com/'),
    pag('https://x.com/b', { teclado: { pasos: [{ elemento: 'a', texto: 'Inicio', visible_indicador: false }], trampa: { elemento: 'input', texto: 'Editor' } },
      reflow: { desborda: true, ancho_documento: 500 } }),
  ]);
  const alt = hallazgos.find((h) => h.regla === 'image-alt');
  assert.deepEqual(alt.paginas, ['https://x.com/', 'https://x.com/b']);
  assert.equal(alt.total_nodos, 4);
  assert.deepEqual(alt.wcag, ['1.1.1']);
  for (const r of ['trampa-de-foco', 'foco-no-visible', 'reflow-320']) assert.ok(hallazgos.some((h) => h.regla === r), r);
  assert.equal(hallazgos[0].severidad, 'Crítica');
  assert.equal(a11y.cumplimiento([{ aprobadas: ['a', 'b', 'c'], violaciones: [v] }]), 75);
});

const rend = require(path.join(RAIZ, 'herramientas/k0lmena/tools/rendimiento/auditar.js'));

test('rendimiento: califica con los umbrales de Google y arma hallazgos y oportunidades', () => {
  assert.equal(rend.calificar('lcp', 2400), 'bueno');
  assert.equal(rend.calificar('lcp', 3000), 'mejorar');
  assert.equal(rend.calificar('cls', 0.3), 'malo');
  assert.throws(() => rend.argumentos(['--dispositivos', 'tablet']), /mobile y\/o desktop/);
  const pagina = (url) => ({ url, dispositivo: 'mobile', metricas: { lcp: { valor: 4500, texto: '4.5 s', estado: 'malo' }, cls: { valor: 0, texto: '0', estado: 'bueno' } },
    oportunidades: [{ id: 'unused-javascript', titulo: 'JS sin usar', ahorro_ms: 1800, ahorro_bytes: 0 }] });
  const { hallazgos, oportunidades } = rend.armarHallazgos([pagina('https://x.com/'), pagina('https://x.com/b'), { url: 'https://x.com/c', dispositivo: 'mobile', error: 'boom' }]);
  assert.equal(oportunidades.length, 1);
  assert.deepEqual(oportunidades[0].paginas, ['https://x.com/', 'https://x.com/b']);
  assert.ok(hallazgos.some((h) => h.categoria === 'Core Web Vitals' && h.severidad === 'Alta'));
  assert.ok(hallazgos.some((h) => h.categoria === 'Oportunidad' && h.severidad === 'Alta'));
  assert.ok(hallazgos.some((h) => h.categoria === 'Error'));
  assert.deepEqual(hallazgos.map((h) => h.id), hallazgos.map((_, i) => `R-${String(i + 1).padStart(2, '0')}`));
});

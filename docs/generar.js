// Regenera los recursos de la documentación de k0lmenIA:
//   docs/assets/img/arquitectura.png  ← docs/diagramas/arquitectura.html
//   docs/assets/img/relaciones.png    ← docs/diagramas/relaciones.html
//   docs/assets/img/uso.png           ← docs/diagramas/uso.html
//   docs/assets/img/puesta-en-marcha.png ← docs/diagramas/puesta-en-marcha.html
//   docs/k0lmenIA-documentacion.pdf   ← docs/index.html (estilos de impresión; no se versiona: lo publica
//                                       el workflow documentacion.yml en el release "docs")
// y lo mismo en inglés:
//   docs/assets/img/en/*.png          ← docs/diagramas/en/*.html
//   docs/k0lmenIA-documentation.pdf   ← docs/en/index.html
//
// Uso, desde la raíz del repo (con k0lmena instalado: usa su Playwright):
//   node docs/generar.js
// La portada se genera aparte, sin encabezado ni pie, y reemplaza a la primera página con pypdf
// (pip install pypdf). Sin pypdf el PDF sale igual, con el pie también en la portada.
const path = require('path');
const { pathToFileURL } = require('url');

const k0lmena = path.resolve(__dirname, '../herramientas/k0lmena');
let chromium;
try {
  ({ chromium } = require(require.resolve('playwright', { paths: [k0lmena] })));
} catch {
  console.error('Falta Playwright: corré "npm install" y "npx playwright install chromium" en herramientas/k0lmena.');
  process.exit(1);
}

// Encabezado o pie del PDF: ocupa todo el margen con el fondo noche (#0E0C09) de k0lmena.
// Los márgenes de @page (docs/assets/estilos.css) son 13 mm arriba y 15 mm abajo. Chromium dibuja la
// plantilla a ~5 mm del borde de la hoja (medido: 5,0 arriba y 5,5 abajo): la parte visible mide el
// margen menos eso, y el fondo se estira 7 mm hacia afuera (arriba en el encabezado, abajo en el pie)
// para llegar al borde sin tapar el contenido.
const BORDE_ARRIBA = 5.0;
const BORDE_ABAJO = 5.5;
const EXTRA = '7mm';
const MARGEN = (contenido, alto, arriba) =>
  '<style>html,body{margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}</style>' +
  `<div style="width:100%;margin:${arriba ? `-${EXTRA} 0 0` : `0 0 -${EXTRA}`};padding:${arriba ? `${EXTRA} 0 0` : `0 0 ${EXTRA}`};background:#0E0C09">` +
  `<div style="height:${alto}">${contenido}</div></div>`;

const url = (archivo) => pathToFileURL(path.join(__dirname, archivo)).href;
const ruta = (archivo) => path.join(__dirname, archivo);

(async () => {
  const navegador = await chromium.launch();

  const IDIOMAS = [
    { carpeta: '', pdf: 'k0lmenIA-documentacion.pdf', pie: 'documentación' },
    { carpeta: 'en/', pdf: 'k0lmenIA-documentation.pdf', pie: 'documentation' },
  ];

  // Diagramas → PNG (2x para que se lean bien en pantallas de alta densidad)
  const lienzo = await navegador.newPage({ viewport: { width: 1900, height: 1200 }, deviceScaleFactor: 2 });
  for (const { carpeta } of IDIOMAS) {
    require('fs').mkdirSync(ruta(`assets/img/${carpeta}`), { recursive: true });
    for (const nombre of ['arquitectura', 'relaciones', 'uso', 'puesta-en-marcha']) {
      await lienzo.goto(url(`diagramas/${carpeta}${nombre}.html`));
      await lienzo.locator('#captura').screenshot({ path: ruta(`assets/img/${carpeta}${nombre}.png`) });
      console.log(`docs/assets/img/${carpeta}${nombre}.png`);
    }
  }

  // Sitio → PDF
  const pdfs = [];
  for (const { carpeta, pdf, pie } of IDIOMAS) {
    const pagina = await navegador.newPage();
    await pagina.goto(url(`${carpeta}index.html`), { waitUntil: 'networkidle' });
    await pagina.emulateMedia({ media: 'print' });
    const final = ruta(pdf);
    const portada = ruta(`.portada-${pdf}`);
    await pagina.pdf({ path: portada, printBackground: true, preferCSSPageSize: true, pageRanges: '1' });
    await pagina.pdf({
      path: final,
      printBackground: true,
      preferCSSPageSize: true,
      displayHeaderFooter: true,
      // Chromium no pinta el fondo de la página en los márgenes de @page (quedan grises): el encabezado
      // y el pie, que se dibujan en esos márgenes, los cubren con el fondo de k0lmena.
      headerTemplate: MARGEN('', `${13 - BORDE_ARRIBA}mm`, true),
      footerTemplate: MARGEN(
        '<div style="height:100%;display:flex;align-items:center;justify-content:space-between;padding:0 15mm;' +
        'font:9px Consolas,\'Cascadia Mono\',monospace;color:#8A8172">' +
        `<span><span style="color:#F9B006">//</span> k0lmenIA · ${pie}</span>` +
        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>', `${15 - BORDE_ABAJO}mm`, false),
    });
    await pagina.close();
    pdfs.push({ pdf, final, portada });
  }
  await navegador.close();

  // Portada sin pie: reemplaza la primera página (pypdf).
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const unir = [
    'import sys',
    'from pypdf import PdfReader, PdfWriter',
    'final, portada = sys.argv[1], sys.argv[2]',
    'w = PdfWriter(clone_from=final)',
    'w.remove_page(0)',
    'w.insert_page(PdfReader(portada).pages[0], 0)',
    'w.write(final)',
  ].join(String.fromCharCode(10));
  for (const { pdf, final, portada } of pdfs) {
    const r = require('child_process').spawnSync(py, ['-c', unir, final, portada], { encoding: 'utf8' });
    if (r.status !== 0) console.log(`(No pude quitar el pie de la portada: ${(r.stderr || r.error || '').toString().trim().split(String.fromCharCode(10)).pop()}. Instalá pypdf.)`);
    require('fs').rmSync(portada, { force: true });
    console.log(`docs/${pdf}`);
  }
})();

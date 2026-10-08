// Regenera los recursos de la documentación de k0lmenIA:
//   docs/assets/img/arquitectura.png  ← docs/diagramas/arquitectura.html
//   docs/assets/img/uso.png           ← docs/diagramas/uso.html
//   docs/k0lmenIA-documentacion.pdf   ← docs/index.html (estilos de impresión)
//
// Uso, desde la raíz del repo (con k0lmena instalado: usa su Playwright):
//   node docs/generar.js
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

const url = (archivo) => pathToFileURL(path.join(__dirname, archivo)).href;
const ruta = (archivo) => path.join(__dirname, archivo);

(async () => {
  const navegador = await chromium.launch();

  // Diagramas → PNG (2x para que se lean bien en pantallas de alta densidad)
  const lienzo = await navegador.newPage({ viewport: { width: 1900, height: 1200 }, deviceScaleFactor: 2 });
  for (const nombre of ['arquitectura', 'uso']) {
    await lienzo.goto(url(`diagramas/${nombre}.html`));
    await lienzo.locator('#captura').screenshot({ path: ruta(`assets/img/${nombre}.png`) });
    console.log(`docs/assets/img/${nombre}.png`);
  }

  // Sitio → PDF
  const pagina = await navegador.newPage();
  await pagina.goto(url('index.html'), { waitUntil: 'networkidle' });
  await pagina.emulateMedia({ media: 'print' });
  await pagina.pdf({
    path: ruta('k0lmenIA-documentacion.pdf'),
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate:
      '<div style="width:100%;font-size:7.5px;color:#7a8699;padding:0 14mm;display:flex;justify-content:space-between;font-family:Segoe UI,sans-serif">' +
      '<span>k0lmenIA · Documentación</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
  });
  console.log('docs/k0lmenIA-documentacion.pdf');
  await navegador.close();
})();

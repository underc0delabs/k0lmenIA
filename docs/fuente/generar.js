// Genera la documentación de docs/ a partir de los HTML de esta carpeta:
//   docs/k0lmenIA-arquitectura.png, docs/k0lmenIA-uso.png y docs/k0lmenIA-documentacion.pdf
//
// Uso (desde la raíz del repo, con k0lmena instalado):
//   node docs/fuente/generar.js
const path = require('path');
const { pathToFileURL } = require('url');

const k0lmena = path.resolve(__dirname, '../../herramientas/k0lmena');
let chromium;
try {
  ({ chromium } = require(require.resolve('playwright', { paths: [k0lmena] })));
} catch {
  console.error('Falta Playwright: corré "npm install" y "npx playwright install chromium" en herramientas/k0lmena.');
  process.exit(1);
}

const fuente = (f) => pathToFileURL(path.join(__dirname, f)).href;
const salida = (f) => path.resolve(__dirname, '..', f);

(async () => {
  const navegador = await chromium.launch();
  const pagina = await navegador.newPage({ viewport: { width: 1900, height: 1200 }, deviceScaleFactor: 2 });

  for (const [html, png] of [['arquitectura.html', 'k0lmenIA-arquitectura.png'], ['uso.html', 'k0lmenIA-uso.png']]) {
    await pagina.goto(fuente(html));
    await pagina.locator('#captura').screenshot({ path: salida(png) });
    console.log(`docs/${png}`);
  }

  await pagina.goto(fuente('documentacion.html'));
  await pagina.pdf({
    path: salida('k0lmenIA-documentacion.pdf'),
    format: 'A4',
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate:
      '<div style="width:100%;font-size:8px;color:#8b97a8;padding:0 14mm;display:flex;justify-content:space-between;font-family:Segoe UI,sans-serif">' +
      '<span>k0lmenIA · Documentación</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
  });
  console.log('docs/k0lmenIA-documentacion.pdf');
  await navegador.close();
})();

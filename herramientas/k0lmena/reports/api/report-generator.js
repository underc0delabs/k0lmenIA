"use strict";
// Reporte HTML de la suite de API (npm run report:api), con el tema oscuro de k0lmenIA.
// multiple-cucumber-html-reporter v4 es solo ESM: se carga con import() dinámico.
const os = require("os");
const path = require("path");
const { opcionesReporte, aplicarTema, esperarHtml, urlSegura } = require("../tema-oscuro");

const DIR = path.resolve(__dirname);

(async () => {
  const reporter = await import("multiple-cucumber-html-reporter");
  await reporter.generate({
    ...opcionesReporte("API"),
    jsonDir: DIR, // Directorio donde está el archivo cucumber-report.json
    reportPath: DIR, // Carpeta donde se generará el reporte HTML
    metadata: {
      browser: { name: "API (axios)", version: "-" },
      device: os.hostname(),
      platform: { name: os.platform(), version: os.release() },
    },
    customData: {
      Proyecto: "k0lmena · API",
      Ejecutado: new Date().toLocaleString("es-AR"),
      "URL base": urlSegura(process.env.API_BASEURL),
    },
  });
  if (!(await esperarHtml(DIR))) console.error('[k0lmena] Aviso: el reporter no terminó de escribir index.html a tiempo; el tema se aplicó a lo que había.');
  console.log(`[k0lmena] Reporte de API con tema oscuro (${aplicarTema(DIR)} páginas).`);
})().catch((e) => {
  console.error("[k0lmena] No se pudo generar el reporte de API:", e);
  process.exitCode = 1;
});

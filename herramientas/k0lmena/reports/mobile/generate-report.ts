// reports/mobile/generate-report.ts — reporte HTML de la suite mobile (npm run report:mobile),
// con el tema oscuro de k0lmenIA.

import { hostname } from 'os';
import { resolve } from 'path';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const { opcionesReporte, aplicarTema, esperarHtml } = require('../tema-oscuro');

// multiple-cucumber-html-reporter v4 es solo ESM: se carga con import() dinámico
// (con new Function para que TypeScript no lo convierta en require).
const loadReporter = new Function('m', 'return import(m)') as (m: string) => Promise<any>;

const salida = resolve(__dirname, 'html');

loadReporter('multiple-cucumber-html-reporter')
  .then(({ generate }) => generate({
    ...opcionesReporte('Mobile'),
    // Directorio donde se encuentra el JSON generado por Cucumber
    jsonDir: resolve(__dirname),
    // Directorio donde se generará el HTML
    reportPath: salida,
    metadata: {
      browser: { name: 'Appium', version: '-' },
      device: process.env.MOBILE_DEVICE_NAME || hostname(),
      platform: {
        name: process.env.MOBILE_PLATFORM || 'Android',
        version: process.env.MOBILE_PLATFORM_VERSION || '-',
      },
    },
    customData: {
      Proyecto: 'k0lmena · Mobile',
      Ejecutado: new Date().toLocaleString('es-AR'),
      Destino: process.env.MOBILE_TARGET || '—',
    },
  }))
  .then(() => esperarHtml(salida))
  .then((listo: boolean) => { if (!listo) console.error('[k0lmena] Aviso: el reporter no terminó de escribir index.html a tiempo.'); })
  .then(() => console.log(`[k0lmena] Reporte mobile con tema oscuro (${aplicarTema(salida)} páginas).`))
  .catch((e: unknown) => {
    console.error('[k0lmena] No se pudo generar el reporte mobile:', e);
    process.exitCode = 1;
  });

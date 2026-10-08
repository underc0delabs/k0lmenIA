// reports/mobile/generate-report.ts

import { resolve } from 'path';

// multiple-cucumber-html-reporter v4 es solo ESM: se carga con import() dinámico
// (con new Function para que TypeScript no lo convierta en require).
const loadReporter = new Function('m', 'return import(m)') as (m: string) => Promise<any>;

loadReporter('multiple-cucumber-html-reporter').then(({ generate }) => generate({
  // Directorio donde se encuentra el JSON generado por Cucumber
  jsonDir: resolve(__dirname),
  // Directorio donde se generará el HTML
  reportPath: resolve(__dirname, 'html'),
  metadata: {
    browser: {
      name: 'Appium',
      version: 'N/A'
    },
    device: 'Android device',
    platform: {
      name: 'Android',
      version: '11.0'  // Actualizá según corresponda
    }
  },
  customData: {
    title: 'Información de la Ejecución',
    data: [
      { label: 'Proyecto', value: 'k0lmena Mobile Automation' },
      { label: 'Ejecutado', value: new Date().toLocaleString() }
    ]
  }
}));

// Carga el .env ÚNICO de k0lmenIA (el de la raíz del repo) para todo k0lmena.
//
// Lo usan run-tests.js, cucumber.js, mobile/support/wdio.conf.ts y los scripts de
// npm (node -r ./env.js). Para usar otro archivo (ej. en CI): K0LMENA_ENV_FILE=ruta/.env
// Las variables ya definidas en el entorno tienen prioridad sobre el archivo.
const path = require('path');

const envFile = process.env.K0LMENA_ENV_FILE
  ? path.resolve(process.env.K0LMENA_ENV_FILE)
  : path.resolve(__dirname, '../../.env');

require('dotenv').config({ path: envFile, quiet: true });

// Compatibilidad con el resto de k0lmenIA: el ejecutor-e2e usa APP_URL.
if (!process.env.BASEURL && process.env.APP_URL) process.env.BASEURL = process.env.APP_URL;

module.exports = { envFile };

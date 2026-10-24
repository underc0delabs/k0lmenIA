// Carga el .env ÚNICO de k0lmenIA (el de la raíz del repo) para todo k0lmena.
//
// Lo usan run-tests.js, cucumber.js, mobile/support/wdio.conf.ts y los scripts de
// npm (node -r ./env.js). Para usar otro archivo (ej. en CI): K0LMENA_ENV_FILE=ruta/.env
// Las variables ya definidas en el entorno tienen prioridad sobre el archivo.
const path = require('path');

// El .env es del proyecto (con k0lmenIA como plugin, el del proyecto del QA): ver tools/rutas.js.
const { PROYECTO } = require('./tools/rutas');
const envFile = process.env.K0LMENA_ENV_FILE
  ? path.resolve(process.env.K0LMENA_ENV_FILE)
  : path.join(PROYECTO, '.env');

// BASEURL definida en la terminal (ej. BASEURL=https://otra npm test) pisa a APP_URL para esa corrida.
const baseurlDeLaTerminal = process.env.BASEURL;

require('dotenv').config({ path: envFile, quiet: true });

// La URL de la app va en un solo lugar: APP_URL. BASEURL (el nombre que usan los steps y las
// herramientas de k0lmena) se arma desde ahí, así las dos valen siempre lo mismo. Un BASEURL viejo
// en el .env solo se usa si APP_URL está vacía.
const url = baseurlDeLaTerminal || process.env.APP_URL || process.env.BASEURL || '';
if (url) {
  process.env.APP_URL = url;
  process.env.BASEURL = url;
}

module.exports = { envFile };

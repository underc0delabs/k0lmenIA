// Dónde están los DATOS del proyecto y dónde el CÓDIGO de k0lmenIA (ver scripts/_proyecto.py).
//
// - PROYECTO (datos): output/, input/, .env, .auth/ y la automatización de herramientas/k0lmena.
//   K0LMENIA_PROYECTO si está definida; si no, y k0lmenIA corre como plugin de Claude Code (CLAUDE_PLUGIN_ROOT),
//   la carpeta actual (el proyecto del QA); si no, la raíz de siempre (el repo clonado).
// - CODIGO: donde están scripts/ (los generadores de informes en Python). K0LMENIA_CODIGO si está definida; si no,
//   la raíz de siempre o, como plugin, la del plugin. Cuando k0lmena vive copiada en el proyecto del QA
//   (`k0lmenia init`), la raíz de siempre es el proyecto y los scripts están en el plugin.
//
// Con el repo clonado, las dos son la misma carpeta: todo sigue como siempre.
const fs = require('fs');
const path = require('path');

// herramientas/k0lmena/tools/ -> la raíz (el repo clonado, o el proyecto si k0lmena está copiada ahí).
const RAIZ_K0 = path.resolve(__dirname, '..', '..', '..');

function proyecto(env = process.env) {
  if (env.K0LMENIA_PROYECTO) return path.resolve(env.K0LMENIA_PROYECTO);
  if (env.CLAUDE_PLUGIN_ROOT) return process.cwd();
  return RAIZ_K0;
}

function codigo(env = process.env) {
  if (env.K0LMENIA_CODIGO) return path.resolve(env.K0LMENIA_CODIGO);
  if (fs.existsSync(path.join(RAIZ_K0, 'scripts'))) return RAIZ_K0;
  if (env.CLAUDE_PLUGIN_ROOT) return path.resolve(env.CLAUDE_PLUGIN_ROOT);
  return RAIZ_K0;
}

module.exports = { PROYECTO: proyecto(), CODIGO: codigo(), proyecto, codigo, RAIZ_K0 };

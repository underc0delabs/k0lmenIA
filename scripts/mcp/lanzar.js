// Lanzamiento común de los servers MCP por stdio (lo usan los scripts de scripts/mcp/).
//
// - Versiones fijas de cada paquete (nada de @latest: un server recibe tokens por el entorno y
//   una versión nueva no revisada no debería recibirlos sin que nadie lo decida). Para subir una
//   versión, cambiala acá (o, para probar, con la variable <PAQUETE>_MCP_VERSION).
// - En Windows npx es un .cmd y necesita shell: se arma la línea a mano con argumentos ya
//   validados (sin espacios ni caracteres que cmd interprete).
// - Al cerrar Claude Code se termina todo el árbol de procesos (en Windows, con taskkill /T),
//   así no quedan servers huérfanos.
const { spawn, spawnSync } = require('child_process');
const path = require('path');

const VERSIONES = {
  '@playwright/mcp': '0.0.83',
  '@smartbear/mcp': '0.42.0',
  'appium-mcp': '1.95.3',
  '@azure-devops/mcp': '2.10.0',
  'mcp-remote': '0.14.3',
};

const RAIZ = path.resolve(__dirname, '..', '..');
const SEGURO = /^[\w@./:=${}-]+$/; // lo que puede ir sin comillas en la línea de cmd

function salirConError(conector, mensaje) {
  console.error(`${conector}: ${mensaje} (ver .env.example y CONECTORES.md).`);
  process.exit(1);
}

/** "paquete@versión" con la versión fija (o la de <PAQUETE>_MCP_VERSION, si se definió). */
function paqueteFijo(paquete) {
  const clave = `${paquete.replace(/^@/, '').replace(/[^\w]+/g, '_').toUpperCase()}_MCP_VERSION`;
  const version = process.env[clave] || VERSIONES[paquete];
  if (!version || !/^[\w.-]+$/.test(version)) throw new Error(`versión inválida para ${paquete}`);
  return `${paquete}@${version}`;
}

/** Lanza `npx -y <paquete fijo> ...args` heredando stdio (el protocolo MCP va por stdout). */
function lanzarNpx(conector, paquete, args, env = process.env) {
  let todos;
  try {
    todos = ['-y', paqueteFijo(paquete), ...args];
  } catch (e) {
    salirConError(conector, e.message);
  }
  const invalido = todos.find((a) => !SEGURO.test(a));
  if (invalido) salirConError(conector, `argumento no permitido: "${invalido}"`);
  const opciones = { stdio: 'inherit', env, cwd: RAIZ };
  const hijo = process.platform === 'win32'
    ? spawn(['npx', ...todos].join(' '), { ...opciones, shell: true })
    : spawn('npx', todos, opciones);
  hijo.on('error', (e) => salirConError(conector, `no se pudo iniciar el server (${e.message})`));
  hijo.on('exit', (codigo) => process.exit(codigo ?? 1));
  const cerrar = () => {
    if (process.platform === 'win32' && hijo.pid) {
      spawnSync('taskkill', ['/PID', String(hijo.pid), '/T', '/F'], { stdio: 'ignore' });
    } else {
      hijo.kill('SIGTERM');
    }
  };
  for (const senal of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.on(senal, () => { cerrar(); process.exit(0); });
  return hijo;
}

module.exports = { lanzarNpx, salirConError, paqueteFijo, VERSIONES, RAIZ };

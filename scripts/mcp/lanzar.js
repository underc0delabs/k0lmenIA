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
};

// Servers de Python (PyPI), con la misma regla de versión fija. Se corren con uvx (o pipx, si no hay uv).
const VERSIONES_PYTHON = {};

const RAIZ = path.resolve(__dirname, '..', '..'); // el código de k0lmenIA
// El server corre en el proyecto (output/, .env y .auth/ del QA; con el repo clonado, la misma carpeta).
const { PROYECTO } = require('../../herramientas/k0lmena/tools/rutas');
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
  const opciones = { stdio: 'inherit', env, cwd: PROYECTO };
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

/** El comando para correr un server de PyPI con versión fija: uvx si está, si no pipx. null si no hay ninguno. */
function comandoPython(paquete, ejecutable, hay = (c) => !spawnSync(c, ['--version'], { stdio: 'ignore' }).error) {
  const clave = `${paquete.replace(/[^\w]+/g, '_').toUpperCase()}_MCP_VERSION`;
  const version = process.env[clave] || VERSIONES_PYTHON[paquete];
  if (!version || !/^[\w.-]+$/.test(version)) throw new Error(`versión inválida para ${paquete}`);
  if (hay('uvx')) return ['uvx', ['--from', `${paquete}==${version}`, ejecutable]];
  if (hay('pipx')) return ['pipx', ['run', '--spec', `${paquete}==${version}`, ejecutable]];
  return null;
}

/** Lanza un server de PyPI (uvx o pipx) heredando stdio, con el mismo cierre que lanzarNpx. */
function lanzarPython(conector, paquete, ejecutable, env = process.env) {
  let cmd;
  try {
    cmd = comandoPython(paquete, ejecutable);
  } catch (e) {
    salirConError(conector, e.message);
  }
  if (!cmd) salirConError(conector, 'hace falta uv (uvx) o pipx para correr este server de Python: https://docs.astral.sh/uv/');
  const [programa, args] = cmd;
  const invalido = args.find((a) => !SEGURO.test(a));
  if (invalido) salirConError(conector, `argumento no permitido: "${invalido}"`);
  const hijo = spawn(programa, args, { stdio: 'inherit', env, cwd: PROYECTO });
  hijo.on('error', (e) => salirConError(conector, `no se pudo iniciar el server (${e.message})`));
  hijo.on('exit', (codigo) => process.exit(codigo ?? 1));
  for (const senal of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
    process.on(senal, () => {
      if (process.platform === 'win32' && hijo.pid) spawnSync('taskkill', ['/PID', String(hijo.pid), '/T', '/F'], { stdio: 'ignore' });
      else hijo.kill('SIGTERM');
      process.exit(0);
    });
  }
  return hijo;
}

module.exports = { lanzarNpx, lanzarPython, comandoPython, salirConError, paqueteFijo, VERSIONES, VERSIONES_PYTHON, RAIZ, PROYECTO };

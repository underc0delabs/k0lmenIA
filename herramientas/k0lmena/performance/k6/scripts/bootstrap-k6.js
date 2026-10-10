// bootstrap-k6.js — `npm run bootstrap:k6`: descarga k6 en tools/k6 (Windows, Linux y macOS).
// Verifica el SHA-256 oficial de la release (fijo para esta versión) antes de extraer.
// Para subir de versión: cambiá VERSION y los hashes, que salen de
// https://github.com/grafana/k6/releases/download/<versión>/k6-<versión>-checksums.txt
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');

const VERSION = 'v2.3.0';
const SHA256 = {
  'linux-amd64.tar.gz': '39c3117b6af817592dcd0ce4242105c0a7af10948c2a425306f0be8f7a8a8ab1',
  'linux-arm64.tar.gz': '5ca3433e8201da72a284aaa241a1bb5fb47f4abb4e384d39410ddd8062f49b90',
  'macos-amd64.zip': 'c83bb16f54f0676afa4ea235fd757f3892d307dbd1bd201450de83af31986654',
  'macos-arm64.zip': 'b2417a3038edc5fe81dc178a889237724b595c5c9cfed875822008e46e862c7d',
  'windows-amd64.zip': '112276d495e5741c968e2bc09ea6196099c1275bd6db9ee0875d173c7148ce43',
};
const DESTINO = path.resolve(__dirname, '../../../tools/k6');

function plataforma() {
  const arch = { x64: 'amd64', arm64: 'arm64' }[process.arch];
  if (process.platform === 'win32') return 'windows-amd64.zip'; // k6 publica Windows solo para amd64
  if (!arch) throw new Error(`arquitectura no soportada: ${process.arch}`);
  return process.platform === 'darwin' ? `macos-${arch}.zip` : `linux-${arch}.tar.gz`;
}

function extraer(archivo, carpeta) {
  // Rutas relativas a cwd: el tar de Git Bash no acepta rutas con "C:".
  const r = archivo.endsWith('.zip') && process.platform === 'win32'
    ? spawnSync('powershell', ['-NoProfile', '-Command', `Expand-Archive -Force -Path '${path.basename(archivo)}' -DestinationPath .`], { cwd: carpeta, stdio: 'inherit' })
    : archivo.endsWith('.zip')
      ? spawnSync('unzip', ['-o', path.basename(archivo)], { cwd: carpeta, stdio: 'inherit' })
      : spawnSync('tar', ['-xzf', path.basename(archivo)], { cwd: carpeta, stdio: 'inherit' });
  if (r.status !== 0) throw new Error('no se pudo extraer el archivo descargado');
}

(async () => {
  const binario = path.join(DESTINO, process.platform === 'win32' ? 'k6.exe' : 'k6');
  if (fs.existsSync(binario)) {
    console.log(`k6 ya está en ${path.relative(process.cwd(), binario)}.`);
    return;
  }
  const sufijo = plataforma();
  const nombre = `k6-${VERSION}-${sufijo}`;
  const url = `https://github.com/grafana/k6/releases/download/${VERSION}/${nombre}`;
  console.log(`Descargando ${url} ...`);
  const r = await fetch(url, { signal: AbortSignal.timeout(300000) });
  if (!r.ok) throw new Error(`HTTP ${r.status} al descargar k6`);
  const datos = Buffer.from(await r.arrayBuffer());
  if (crypto.createHash('sha256').update(datos).digest('hex') !== SHA256[sufijo]) {
    throw new Error('el SHA-256 del archivo descargado no coincide con el publicado por Grafana');
  }
  const temporal = fs.mkdtempSync(path.join(os.tmpdir(), 'k6-'));
  const archivo = path.join(temporal, nombre);
  fs.writeFileSync(archivo, datos);
  console.log('Extrayendo...');
  extraer(archivo, temporal);
  const carpeta = path.join(temporal, nombre.replace(/\.(zip|tar\.gz)$/, ''));
  fs.mkdirSync(DESTINO, { recursive: true });
  fs.copyFileSync(path.join(carpeta, path.basename(binario)), binario);
  if (process.platform !== 'win32') fs.chmodSync(binario, 0o755);
  fs.rmSync(temporal, { recursive: true, force: true });
  console.log(`Listo. Binario en tools/k6/${path.basename(binario)}`);
})().catch((e) => {
  console.error(`No se pudo instalar k6: ${e.message}`);
  process.exit(1);
});

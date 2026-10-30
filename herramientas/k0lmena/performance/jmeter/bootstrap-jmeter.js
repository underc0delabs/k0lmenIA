// bootstrap-jmeter.js — `npm run bootstrap:jmeter`: descarga Apache JMeter en tools/jmeter
// (Windows, Linux y macOS). Verifica el SHA-512 oficial de Apache (fijo para esta versión)
// antes de extraer.
// JMeter necesita Java 8 o superior (el runner lo busca en JAVA_HOME o en el PATH).
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');

const VERSION = '5.6.3';
const NOMBRE = `apache-jmeter-${VERSION}`;
const RUTA = `jmeter/binaries/${NOMBRE}.tgz`;
// El CDN tiene la versión actual; el archivo histórico, todas (y es más lento).
const ESPEJOS_TGZ = [`https://dlcdn.apache.org/${RUTA}`, `https://archive.apache.org/dist/${RUTA}`];
// https://downloads.apache.org/jmeter/binaries/apache-jmeter-5.6.3.tgz.sha512 (al subir de versión, actualizar)
const SHA512 = '5978a1a35edb5a7d428e270564ff49d2b1b257a65e17a759d259a9283fc17093e522fe46f474a043864aea6910683486340706d745fcdf3db1505fd71e689083';
const DESTINO = path.resolve(__dirname, '../../tools/jmeter');

async function bajar(urls) {
  const fallas = [];
  for (const url of urls) {
    try {
      console.log(`Descargando ${url} ...`);
      const r = await fetch(url, { signal: AbortSignal.timeout(300000) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return Buffer.from(await r.arrayBuffer());
    } catch (e) {
      fallas.push(`${url}: ${e.cause?.code || e.message}`);
    }
  }
  throw new Error(`no se pudo descargar:\n  ${fallas.join('\n  ')}`);
}

(async () => {
  if (fs.existsSync(path.join(DESTINO, NOMBRE, 'bin', 'ApacheJMeter.jar'))) {
    console.log(`JMeter ${VERSION} ya está en tools/jmeter/${NOMBRE}.`);
    return;
  }
  fs.mkdirSync(DESTINO, { recursive: true });

  const tgz = await bajar(ESPEJOS_TGZ);
  const real = crypto.createHash('sha512').update(tgz).digest('hex');
  if (real !== SHA512) throw new Error('El SHA-512 del archivo descargado no coincide con el publicado por Apache.');

  const archivo = path.join(DESTINO, 'jmeter.tgz');
  fs.writeFileSync(archivo, tgz);
  console.log('Extrayendo...');
  // Rutas relativas a cwd: el tar de Git Bash no acepta rutas con "C:".
  const t = spawnSync('tar', ['-xzf', 'jmeter.tgz'], { cwd: DESTINO, stdio: 'inherit' });
  fs.rmSync(archivo, { force: true });
  if (t.status !== 0) throw new Error('No se pudo extraer el archivo con tar.');

  const java = spawnSync('java', ['-version'], { encoding: 'utf8' });
  console.log(`Listo. JMeter en tools/jmeter/${NOMBRE}`);
  if (java.status !== 0) console.log('Aviso: no encuentro Java en el PATH. JMeter necesita Java 8 o superior (o definí JAVA_HOME).');
})().catch((e) => {
  console.error(`No se pudo instalar JMeter: ${e.message}`);
  process.exit(1);
});

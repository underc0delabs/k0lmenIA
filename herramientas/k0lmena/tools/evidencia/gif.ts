// tools/evidencia/gif.ts
//
// Evidencia de los escenarios que pasan (web y mobile).
//   EVIDENCE=captura -> captura final (default)
//   EVIDENCE=ambos   -> captura final + GIF del recorrido (una captura por paso)
//   EVIDENCE=off     -> nada
// Si EVIDENCE no está definida, `npm test` lo pregunta al arrancar (ver run-tests.js).

// gifenc y pngjs son JavaScript puro (sin binarios); se cargan con require porque no traen tipos.
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { GIFEncoder, quantize, applyPalette } = require('gifenc');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { PNG } = require('pngjs');

export type ModoEvidencia = 'off' | 'captura' | 'ambos';

export function modoEvidencia(): ModoEvidencia {
  const raw = (process.env.EVIDENCE ?? 'captura').trim().toLowerCase();
  if (['off', '0', 'false', 'no'].includes(raw)) return 'off';
  if (['ambos', 'gif', 'captura+gif'].includes(raw)) return 'ambos';
  return 'captura'; // captura | on | 1 | true | vacío
}

/** Reduce un PNG decodificado a `ancho` px (vecino más cercano: rápido y suficiente para un GIF). */
function reducir(png: { width: number; height: number; data: Buffer }, ancho: number) {
  if (png.width <= ancho) return png;
  const alto = Math.round((png.height * ancho) / png.width);
  const data = Buffer.alloc(ancho * alto * 4);
  for (let y = 0; y < alto; y++) {
    const sy = Math.floor((y * png.height) / alto);
    for (let x = 0; x < ancho; x++) {
      const sx = Math.floor((x * png.width) / ancho);
      png.data.copy(data, (y * ancho + x) * 4, (sy * png.width + sx) * 4, (sy * png.width + sx) * 4 + 4);
    }
  }
  return { width: ancho, height: alto, data };
}

/**
 * Arma un GIF animado con las capturas (PNG) de cada paso.
 * Los cuadros se reducen a `ancho` px; el último queda el doble de tiempo en pantalla.
 */
export function crearGif(capturas: Buffer[], opciones: { ancho?: number; msPorPaso?: number } = {}): Buffer | null {
  const { ancho = 800, msPorPaso = 1000 } = opciones;
  if (capturas.length === 0) return null;
  const gif = GIFEncoder();
  let base: { width: number; height: number } | null = null;
  capturas.forEach((captura, i) => {
    const cuadro = reducir(PNG.sync.read(captura), ancho);
    // Un cuadro con otro tamaño (ej. la pantalla rotó) no entra en el mismo GIF: se descarta.
    if (base && (cuadro.width !== base.width || cuadro.height !== base.height)) return;
    base = base ?? { width: cuadro.width, height: cuadro.height };
    const paleta = quantize(cuadro.data, 256);
    gif.writeFrame(applyPalette(cuadro.data, paleta), cuadro.width, cuadro.height, {
      palette: paleta,
      delay: i === capturas.length - 1 ? msPorPaso * 2 : msPorPaso,
    });
  });
  gif.finish();
  return Buffer.from(gif.bytes());
}

/** Adjunto HTML que muestra el GIF en el reporte (el reporte no renderiza image/gif como imagen). */
export function htmlGif(src: string, titulo: string): string {
  return `<p><strong>${titulo}</strong></p><img src="${src}" style="max-width:100%" alt="${titulo}">` +
    `<p><a href="${src}" download>Descargar GIF</a></p>`;
}

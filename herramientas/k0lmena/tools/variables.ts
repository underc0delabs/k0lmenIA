// tools/variables.ts
//
// Variables de escenario compartidas entre steps (API, base de datos, web).
// Ej.: un step de API guarda el id creado ("guardo el campo "id" de la respuesta como "idUsuario"")
// y un step de base de datos lo usa ("donde "id" es "{idUsuario}"").
// Se reinician antes de cada escenario.
import { After, Before } from '@cucumber/cucumber';
import { randomUUID } from 'crypto';

export const variables: Record<string, unknown> = {};

// Inicio y fin de cada escenario (en el reporte): el analista-logs los cruza con los logs del servidor.
let inicioEscenario = new Date();
After(function () {
  const fin = new Date();
  if (typeof (this as any)?.attach === 'function') {
    return (this as any).attach(`TIEMPO: inicio=${inicioEscenario.toISOString()} fin=${fin.toISOString()}`, 'text/plain');
  }
});

Before(function ({ pickle }) {
  inicioEscenario = new Date();
  for (const k of Object.keys(variables)) delete variables[k];

  // Escenarios que dependen de información que falta (skill investigacion-contexto):
  // tags @falta-info y @FI-XX. Se deja una nota visible en el reporte.
  const tags = (pickle?.tags ?? []).map((t: { name: string }) => t.name.replace(/^@/, ''));
  const ids = tags.filter((t: string) => /^FI-\d+$/i.test(t));
  if (tags.some((t: string) => t.toLowerCase() === 'falta-info') || ids.length) {
    const nota = `FALTA INFORMACIÓN (${ids.join(', ') || 'ver ficha de contexto'}): este escenario depende de datos `
      + 'que no están definidos en la historia ni en sus fuentes. Su resultado puede cambiar cuando se resuelvan. '
      + 'Detalle en output/contexto/.';
    if (typeof (this as any)?.attach === 'function') return (this as any).attach(nota, 'text/plain');
  }
});

// Datos únicos para no chocar con los de una corrida anterior (un email o un nombre que ya existe):
// se generan la primera vez que se usan en el escenario y valen lo mismo hasta que termina, así el
// POST y el GET siguiente usan el mismo valor. Ej.: "email": "qa+{aleatorio}@prueba.com".
const GENERADAS: Record<string, () => string> = {
  uuid: () => randomUUID(),
  aleatorio: () => String(Math.floor(100000 + Math.random() * 900000)),
  timestamp: () => String(Date.now()),
  ahora: () => new Date().toISOString(),
};

/**
 * Reemplaza {nombre} por una variable guardada, por un dato generado ({uuid}, {aleatorio},
 * {timestamp}, {ahora}) o, si no, por la variable de entorno. Lo que no tiene valor queda igual.
 */
export function interpolar(texto: string): string {
  return texto.replace(/\{([A-Za-z_][\w.]*)\}/g, (match, nombre) => {
    if (nombre in variables) return String(variables[nombre]);
    if (nombre in GENERADAS) {
      variables[nombre] = GENERADAS[nombre]();
      return String(variables[nombre]);
    }
    if (process.env[nombre] !== undefined) return String(process.env[nombre]);
    return match;
  });
}

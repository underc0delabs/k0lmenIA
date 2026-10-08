// tools/variables.ts
//
// Variables de escenario compartidas entre steps (API, base de datos, web).
// Ej.: un step de API guarda el id creado ("guardo el campo "id" de la respuesta como "idUsuario"")
// y un step de base de datos lo usa ("donde "id" es "{idUsuario}"").
// Se reinician antes de cada escenario.
import { Before } from '@cucumber/cucumber';

export const variables: Record<string, unknown> = {};

Before(function ({ pickle }) {
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

/** Reemplaza {nombre} por una variable guardada o, si no existe, por la variable de entorno. */
export function interpolar(texto: string): string {
  return texto.replace(/\{([A-Za-z_][\w.]*)\}/g, (match, nombre) => {
    if (nombre in variables) return String(variables[nombre]);
    if (process.env[nombre] !== undefined) return String(process.env[nombre]);
    return match;
  });
}

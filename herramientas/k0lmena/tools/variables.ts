// tools/variables.ts
//
// Variables de escenario compartidas entre steps (API, base de datos, web).
// Ej.: un step de API guarda el id creado ("guardo el campo "id" de la respuesta como "idUsuario"")
// y un step de base de datos lo usa ("donde "id" es "{idUsuario}"").
// Se reinician antes de cada escenario.
import { Before } from '@cucumber/cucumber';

export const variables: Record<string, unknown> = {};

Before(() => {
  for (const k of Object.keys(variables)) delete variables[k];
});

/** Reemplaza {nombre} por una variable guardada o, si no existe, por la variable de entorno. */
export function interpolar(texto: string): string {
  return texto.replace(/\{([A-Za-z_][\w.]*)\}/g, (match, nombre) => {
    if (nombre in variables) return String(variables[nombre]);
    if (process.env[nombre] !== undefined) return String(process.env[nombre]);
    return match;
  });
}

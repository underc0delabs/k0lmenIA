// performance/k6/lib/k0lmena.ts
//
// Base de los scripts k6 de k0lmenIA. Un script define el FLUJO (export default) y la CARGA
// objetivo; el PERFIL se elige al correr (npm run perf -- <script> <perfil>):
//
//   smoke  -> 1 usuario, 30 s: valida que el script funciona (no mide nada)
//   load   -> sube hasta `vus`, los sostiene `duracion` y baja
//   stress -> `vus`, luego 2x y 3x `vus` (busca el punto de quiebre)
//   soak   -> `vus` sostenidos durante `duracionSoak` (fugas de memoria, degradación)
//   spike  -> salto brusco hasta `pico` usuarios y vuelta (picos de tráfico)
//
// Los números (usuarios, duraciones, umbrales) los define la persona: el agente los pregunta.
// PERF_VUS y PERF_DURACION en el entorno pisan `vus` y `duracion` para una corrida puntual.

import http from 'k6/http';

export type Perfil = 'smoke' | 'load' | 'stress' | 'soak' | 'spike';

export interface Carga {
  /** Usuarios virtuales concurrentes objetivo. */
  vus: number;
  /** Tiempo sostenido en `vus` (load y cada escalón de stress), ej. '5m'. */
  duracion: string;
  /** Tiempo de subida y bajada. Default '30s'. */
  rampa?: string;
  /** Duración del soak. Default '30m'. */
  duracionSoak?: string;
  /** Usuarios en el pico del spike. Default 3x `vus`. */
  pico?: number;
  /** Umbrales de k6 (https://grafana.com/docs/k6/latest/using-k6/thresholds/). */
  umbrales?: Record<string, string[]>;
  /** Nombres de los requests (tag `name`) para tener métricas por endpoint en el reporte. */
  endpoints?: string[];
}

export const env = {
  BASEURL: __ENV.BASEURL || '',
  API_BASEURL: __ENV.API_BASEURL || '',
  // Mismo token que la suite de API (API_TOKEN); AUTH_TOKEN queda por compatibilidad.
  TOKEN: __ENV.API_TOKEN || __ENV.AUTH_TOKEN || '',
};

export const perfil = ((__ENV.PERFIL || 'smoke').toLowerCase()) as Perfil;

// Códigos que se desglosan en el reporte (k6 solo exporta submétricas declaradas de antemano).
const CODIGOS = [0, 200, 201, 202, 204, 301, 302, 304, 400, 401, 403, 404, 405, 409, 422, 429, 500, 502, 503, 504];

function etapas(c: Carga) {
  const vus = Number(__ENV.PERF_VUS || c.vus);
  const dur = __ENV.PERF_DURACION || c.duracion;
  const rampa = c.rampa || '30s';
  switch (perfil) {
    case 'smoke':
      return { executor: 'constant-vus', vus: 1, duration: __ENV.PERF_DURACION || '30s' };
    case 'load':
      return { executor: 'ramping-vus', startVUs: 0, stages: [
        { duration: rampa, target: vus }, { duration: dur, target: vus }, { duration: rampa, target: 0 },
      ] };
    case 'stress':
      return { executor: 'ramping-vus', startVUs: 0, stages: [
        { duration: rampa, target: vus }, { duration: dur, target: vus },
        { duration: rampa, target: vus * 2 }, { duration: dur, target: vus * 2 },
        { duration: rampa, target: vus * 3 }, { duration: dur, target: vus * 3 },
        { duration: rampa, target: 0 },
      ] };
    case 'soak':
      return { executor: 'ramping-vus', startVUs: 0, stages: [
        { duration: rampa, target: vus }, { duration: c.duracionSoak || '30m', target: vus }, { duration: rampa, target: 0 },
      ] };
    case 'spike': {
      const pico = c.pico || vus * 3;
      return { executor: 'ramping-vus', startVUs: 0, stages: [
        { duration: rampa, target: vus }, { duration: '1m', target: vus },
        { duration: '10s', target: pico }, { duration: '1m', target: pico },
        { duration: '10s', target: vus }, { duration: '1m', target: vus },
        { duration: rampa, target: 0 },
      ] };
    }
    default:
      throw new Error(`PERFIL desconocido: ${perfil} (smoke | load | stress | soak | spike)`);
  }
}

/** `export const options = opciones({...})` en cada script. */
export function opciones(c: Carga) {
  const thresholds: Record<string, string[]> = { ...(c.umbrales || {}) };
  // Un threshold vacío no evalúa nada: solo hace que k6 exporte esa submétrica al resumen.
  for (const nombre of c.endpoints || []) {
    const clave = `http_req_duration{name:${nombre}}`;
    if (!thresholds[clave]) thresholds[clave] = [];
  }
  for (const codigo of CODIGOS) thresholds[`http_reqs{status:${codigo}}`] = [];
  return {
    scenarios: { [perfil]: etapas(c) },
    thresholds,
    summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max', 'count'],
    tags: { perfil },
  };
}

/** Headers JSON + Authorization (si hay token). */
export function headers(extra: Record<string, string> = {}) {
  const h: Record<string, string> = Object.assign({ 'Content-Type': 'application/json' }, extra);
  if (env.TOKEN) h['Authorization'] = `Bearer ${env.TOKEN}`;
  return h;
}

/**
 * Request con nombre (el nombre agrupa las métricas por endpoint: usá el path con
 * parámetros, ej. 'GET /pet/{id}', no la URL con el ID real).
 */
export function pedir(metodo: string, nombre: string, url: string, body?: unknown, extraHeaders: Record<string, string> = {}) {
  const payload = body === undefined ? null : typeof body === 'string' ? body : JSON.stringify(body);
  return http.request(metodo, url, payload, { headers: headers(extraHeaders), tags: { name: nombre } });
}

/** Guarda el resumen crudo para el reporte de k0lmenIA (lo procesa run-perf.js). */
export function handleSummary(data: unknown) {
  const salida = __ENV.K0LMENA_PERF_SALIDA || 'reports/performance/k6/ultimo.json';
  return { [salida]: JSON.stringify(data) };
}

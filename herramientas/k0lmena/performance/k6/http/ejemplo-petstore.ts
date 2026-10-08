// Ejemplo de script k6 de k0lmenIA (los genera el agente performance-mapper).
// Correr:  npm run perf -- ejemplo-petstore smoke
import { check, group, sleep } from 'k6';
import { env, opciones, pedir } from '../lib/k0lmena';
export { handleSummary } from '../lib/k0lmena';

const BASE = `${env.API_BASEURL || 'https://petstore.swagger.io'}/v2`;

const E = {
  mascotasDisponibles: 'GET /pet/findByStatus',
  inventario: 'GET /store/inventory',
};

export const options = opciones({
  vus: 10,
  duracion: '2m',
  umbrales: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<800', 'p(99)<1500'],
    checks: ['rate>0.99'],
  },
  endpoints: Object.values(E),
});

export default function () {
  group('Consultar catálogo', () => {
    const res = pedir('GET', E.mascotasDisponibles, `${BASE}/pet/findByStatus?status=available`);
    check(res, {
      'mascotas disponibles: status 200': (r) => r.status === 200,
      'mascotas disponibles: devuelve una lista': (r) => Array.isArray(r.json()),
    });
  });
  group('Consultar inventario', () => {
    const res = pedir('GET', E.inventario, `${BASE}/store/inventory`);
    check(res, { 'inventario: status 200': (r) => r.status === 200 });
  });
  sleep(1); // tiempo de pensamiento del usuario
}

// Processor de ejemplo-login.yaml: el flujo de cada usuario virtual.
// Cada test.step() se mide por separado (métrica browser.step.<nombre> en el reporte).
import { goToLogin, loginAs, assertLoggedIn } from './flows/performanceFlows';

export async function loginQARMY(page, _vuContext, _events, test) {
  await test.step('Ingresar al login', async () => {
    await goToLogin(page);
  });
  await test.step('Iniciar sesión', async () => {
    // Credenciales del sitio de práctica; en una app real salen del .env (APP_USER / APP_PASSWORD).
    await loginAs(page, process.env.PERF_USER || 'admin', process.env.PERF_PASSWORD || '123456');
    await assertLoggedIn(page);
  });
}

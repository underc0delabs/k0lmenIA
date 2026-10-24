// --init-page del conector Playwright (scripts/mcp/playwright.js): agrega el header de bypass acordado con el
// equipo de la app (QA_BYPASS_HEADER / QA_BYPASS_TOKEN del .env) SOLO a los requests de los hosts de la app,
// igual que tools/navegador/navegador.js en k0lmena. Nunca a analytics, CDNs ni otros terceros.
// playwright.js le pasa la configuración por el entorno (K0LMENIA_BYPASS_*), ya validada.
export default async ({ page }) => {
  const nombre = (process.env.K0LMENIA_BYPASS_HEADER || '').toLowerCase();
  const valor = process.env.K0LMENIA_BYPASS_TOKEN || '';
  const hosts = (process.env.K0LMENIA_BYPASS_HOSTS || '').split(',').filter(Boolean);
  if (!nombre || !valor || !hosts.length) return;
  const permitido = (host: string) => hosts.some((p) => host === p || host.endsWith(`.${p}`));
  await page.route('**/*', (route) => {
    const req = route.request();
    let host = '';
    try { host = new URL(req.url()).hostname.toLowerCase(); } catch { /* data:, blob: */ }
    if (!permitido(host)) return route.fallback();
    return route.fallback({ headers: { ...req.headers(), [nombre]: valor } });
  });
};

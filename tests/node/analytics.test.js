// Tests de la captura de analytics (k0lmena tools/analytics): proveedores reconocidos y argumentos.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');

const K0 = path.resolve(__dirname, '..', '..', 'herramientas/k0lmena');
const analytics = require(path.join(K0, 'tools/analytics/capturar.js'));

test('analytics: reconoce cada proveedor por su endpoint', () => {
  const casos = {
    'https://region1.google-analytics.com/g/collect?v=2&tid=G-1&en=page_view': 'GA4',
    'https://www.googletagmanager.com/gtm.js?id=GTM-ABC': 'Google Tag Manager',
    'https://www.facebook.com/tr/?id=1&ev=PageView': 'Meta Pixel',
    'https://px.ads.linkedin.com/collect?pid=1': 'LinkedIn Insight',
    'https://analytics.tiktok.com/api/v2/pixel': 'TikTok Pixel',
    'https://googleads.g.doubleclick.net/pagead/viewthroughconversion/1/': 'Google Ads',
    'https://metrics.example.omtrdc.net/b/ss/rsid/1/JS': 'Adobe Analytics',
    'https://api.segment.io/v1/batch': 'Segment',
    'https://api-js.mixpanel.com/track': 'Mixpanel',
    'https://api2.amplitude.com/2/httpapi': 'Amplitude',
    'https://stats.example.com/matomo.php?idsite=1': 'Matomo',
    'https://static.hotjar.com/c/hotjar-1.js': 'Hotjar',
    'https://www.clarity.ms/tag/abc': 'Microsoft Clarity',
  };
  for (const [url, prov] of Object.entries(casos)) assert.equal(analytics.proveedorDe(url), prov, url);
  assert.equal(analytics.proveedorDe('https://cdn.mi-sitio.com/app.js'), null);
});

test('analytics: argumentos y validaciones', () => {
  const a = analytics.argumentos(['--url', 'https://x.com', '--consentimiento', 'rechazar', '--espera', '1000', '--historia', 'HU-001']);
  assert.equal(a.consentimiento, 'rechazar');
  assert.equal(a.espera, 1000);
  assert.throws(() => analytics.argumentos(['--consentimiento', 'quizas']), /aceptar, rechazar o ninguno/);
  assert.throws(() => analytics.argumentos(['--historia', 'abc']), /HU-001/);
  assert.throws(() => analytics.argumentos(['--otra']), /Opción desconocida/);
});

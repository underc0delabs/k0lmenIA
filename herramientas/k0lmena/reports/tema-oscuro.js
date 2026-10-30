// reports/tema-oscuro.js — tema de k0lmenIA para los reportes de multiple-cucumber-html-reporter
// (web, api y mobile). Deja los reportes en modo oscuro fijo, con el estilo de k0lmena.com y la misma
// paleta que el resto de los informes (scripts/_estilos_reporte.py): fondo, tarjetas, bordes y los colores de estado
// que usan sus gráficos (ApexCharts los lee de las variables --status-*).
//
//   const { opcionesReporte, aplicarTema } = require('../tema-oscuro');
//   await reporter.generate({ ...opcionesReporte('Web'), jsonDir, reportPath });
//   aplicarTema(reportPath);
const fs = require('fs');
const path = require('path');
// El .env de la raíz (URL base, navegador, dispositivo…) para los datos del encabezado del reporte.
try {
  require('../env');
} catch {
  // sin dotenv instalado (por ejemplo, en los tests del repo): los datos del encabezado quedan con "—"
}

// Paleta de k0lmena.com (noche, carbón, cera y ámbar) con los colores de datos validados para la
// superficie oscura (CVD y contraste, skill dataviz): los mismos que scripts/_estilos_reporte.py.
const TOKENS = {
  '--background': '#0E0C09',
  '--foreground': '#F4EFE6',
  '--card': '#1A1712',
  '--card-foreground': '#F4EFE6',
  '--popover': '#221E17',
  '--popover-foreground': '#F4EFE6',
  '--primary': '#F9B006',
  '--primary-foreground': '#0E0C09',
  '--secondary': '#221E17',
  '--secondary-foreground': '#F4EFE6',
  '--muted': '#221E17',
  '--muted-foreground': '#8A8172',
  '--accent': '#2E2412',
  '--accent-foreground': '#FFE58A',
  '--destructive': '#FF5A4E',
  '--border': '#2E281F',
  '--input': '#2E281F',
  '--ring': '#F9B006',
  '--chart-1': '#C98500',
  '--chart-2': '#14A895',
  '--chart-3': '#4C8DEB',
  '--chart-4': '#E0702E',
  '--chart-5': '#9085E9',
  // Estados de Cucumber (siempre acompañados del nombre del estado en el reporte)
  '--status-passed': '#5CBF4A',
  '--status-failed': '#FF5A4E',
  '--status-ambiguous': '#FF8A00',
  '--status-undefined': '#FFD60A',
  '--status-pending': '#9085E9',
  '--status-skipped': '#8A8172',
  '--font-sans': '"Inter",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif',
  '--radius': '0.875rem',
};

// Tipografía de k0lmena.com incrustada (scripts/fuentes, licencia OFL): igual sin internet.
const FUENTES = (() => {
  const dir = path.resolve(__dirname, '..', '..', '..', 'scripts', 'fuentes');
  return [['Saira', 'saira.woff2', '500 700'], ['Inter', 'inter.woff2', '400 600'], ['JetBrains Mono', 'jetbrains-mono.woff2', '400 700']]
    .map(([familia, archivo, pesos]) => {
      try {
        return `@font-face{font-family:'${familia}';font-weight:${pesos};font-display:swap;src:url(data:font/woff2;base64,${fs.readFileSync(path.join(dir, archivo)).toString('base64')}) format('woff2')}`;
      } catch {
        return '';
      }
    }).join('');
})();

// Patrón de panal de k0lmena.com (fondo del encabezado).
const PANAL = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='56' height='100'%3E%3Cpath d='M28 66L0 50L0 16L28 0L56 16L56 50L28 66L28 100' fill='none' stroke='%23F9B006' stroke-opacity='.10' stroke-width='1.2'/%3E%3Cpath d='M28 0L28 34L0 50L0 84L28 100L56 84L56 50L28 34' fill='none' stroke='%23F9B006' stroke-opacity='.07' stroke-width='1.2'/%3E%3C/svg%3E\")";

const ESTILO = `
<style id="k0lmena-theme">
${FUENTES}
html.dark,:root.dark{${Object.entries(TOKENS).map(([k, v]) => `${k}:${v}`).join(';')}}
html.dark{color-scheme:dark}
html.dark body{
  background:radial-gradient(760px 420px at 100% -8%,rgba(249,176,6,.12),transparent 62%),
             ${PANAL} 0 0/56px 100px,var(--background) !important;
  background-attachment:fixed !important;font-family:var(--font-sans) !important;-webkit-font-smoothing:antialiased;
}
html.dark main,html.dark .container,html.dark .max-w-7xl,html.dark .max-w-6xl,html.dark .max-w-screen-xl{max-width:1480px !important;margin-left:auto !important;margin-right:auto !important}
html.dark .bg-card{border:1px solid transparent !important;border-radius:14px !important;
  background:linear-gradient(180deg,#1E1A14,#1A1712) padding-box,linear-gradient(180deg,rgba(244,239,230,.12),rgba(244,239,230,.04) 45%,rgba(244,239,230,.06)) border-box !important;
  box-shadow:0 24px 48px -32px rgba(0,0,0,.9) !important}
html.dark h1,html.dark h2,html.dark h3{font-family:"Saira","Inter",ui-sans-serif,system-ui,sans-serif !important;font-weight:700 !important;letter-spacing:-.012em}
html.dark header,html.dark nav{background:rgba(14,12,9,.85) !important;backdrop-filter:blur(10px);border-color:var(--border) !important}
html.dark table{font-variant-numeric:tabular-nums}
html.dark thead th{font-family:"JetBrains Mono",ui-monospace,Consolas,monospace !important;font-size:11px !important;text-transform:lowercase;letter-spacing:.02em;color:var(--muted-foreground) !important;background:rgba(244,239,230,.025)}
html.dark table tbody tr:hover td{background:rgba(249,176,6,.035)}
html.dark code,html.dark pre,html.dark .font-mono{font-family:"JetBrains Mono",ui-monospace,Consolas,monospace !important}
html.dark a{color:#F9B006}
html.dark .apexcharts-tooltip{background:#1A1712 !important;border:1px solid rgba(249,176,6,.38) !important;color:var(--foreground) !important;
  box-shadow:0 14px 34px rgba(0,0,0,.6) !important;border-radius:12px !important}
html.dark .apexcharts-legend-text{color:#CFC7B8 !important}
#theme-toggle{display:none !important}
</style>
<script id="k0lmena-dark">document.documentElement.classList.add('dark');try{localStorage.setItem('theme','dark')}catch(e){}</script>`;

/** URL para mostrar en el reporte, sin usuario ni contraseña (https://user:pass@host → https://host). */
function urlSegura(url) {
  if (!url) return '—';
  try {
    const u = new URL(url);
    u.username = '';
    u.password = '';
    return u.toString().replace(/\/$/, '');
  } catch {
    return '(URL inválida)';
  }
}

/** Opciones comunes para reporter.generate(): título en español y porcentajes en las donas. */
function opcionesReporte(tipo) {
  return {
    pageTitle: `k0lmena · Reporte ${tipo}`,
    reportName: `k0lmena · Reporte de ejecución ${tipo}`,
    displayDuration: true,
    displayChartPercentages: true,
  };
}

function htmls(dir) {
  const salida = [];
  if (!fs.existsSync(dir)) return salida;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) salida.push(...htmls(p));
    else if (e.name.toLowerCase().endsWith('.html')) salida.push(p);
  }
  return salida;
}

/** Inyecta el tema en un HTML (antes de </head>, después de los estilos del reporter). */
function temaEnHtml(html) {
  if (html.includes('id="k0lmena-theme"') || !/<\/head>/i.test(html)) return html;
  // El tema queda fijo en oscuro: se quita el script del reporter que agrega el botón claro/oscuro.
  html = html.replace(/<script[^>]+src=["'][^"']*darkmode\.js[^"']*["'][^>]*>\s*<\/script>\s*/gi, '');
  html = html.replace(/<html([^>]*)>/i, (m, attrs) => (/class=/i.test(attrs)
    ? `<html${attrs.replace(/class=(["'])([^"']*)\1/i, (x, q, c) => `class=${q}${c} dark${q}`)}>`
    : `<html${attrs} class="dark">`));
  return html.replace(/<\/head>/i, `${ESTILO}\n</head>`);
}

/** Aplica el tema a todos los .html de la carpeta del reporte (y subcarpetas). */
function aplicarTema(dir) {
  let n = 0;
  for (const archivo of htmls(dir)) {
    const antes = fs.readFileSync(archivo, 'utf8');
    const despues = temaEnHtml(antes);
    if (despues !== antes) {
      fs.writeFileSync(archivo, despues, 'utf8');
      n++;
    }
  }
  return n;
}

/** Espera a que el reporter termine de escribir los HTML (escribe en segundo plano). */
async function esperarHtml(dir, timeoutMs = 15000) {
  const inicio = Date.now();
  while (Date.now() - inicio < timeoutMs) {
    if (fs.existsSync(path.join(dir, 'index.html'))) return true;
    await new Promise((r) => setTimeout(r, 200));
  }
  return false;
}

module.exports = { opcionesReporte, aplicarTema, temaEnHtml, esperarHtml, urlSegura, TOKENS };

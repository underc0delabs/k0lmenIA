// reports/tema-oscuro.js — tema de k0lmenIA para los reportes de multiple-cucumber-html-reporter
// (web, api y mobile). Deja los reportes en modo oscuro fijo y con la misma paleta que el resto
// de los informes (scripts/_estilos_reporte.py): fondo, tarjetas, bordes y los colores de estado
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

// Paleta validada para la superficie oscura (CVD y contraste, skill dataviz).
const TOKENS = {
  '--background': '#0D1117',
  '--foreground': '#E8ECF2',
  '--card': '#161B22',
  '--card-foreground': '#E8ECF2',
  '--popover': '#161B22',
  '--popover-foreground': '#E8ECF2',
  '--primary': '#3987E5',
  '--primary-foreground': '#FFFFFF',
  '--secondary': '#1C2330',
  '--secondary-foreground': '#E8ECF2',
  '--muted': '#1C2330',
  '--muted-foreground': '#8B95A3',
  '--accent': '#1E2A3D',
  '--accent-foreground': '#C9DDF7',
  '--destructive': '#D03B3B',
  '--border': '#283040',
  '--input': '#283040',
  '--ring': '#3987E5',
  '--chart-1': '#3987E5',
  '--chart-2': '#D95926',
  '--chart-3': '#199E70',
  '--chart-4': '#C98500',
  '--chart-5': '#9085E9',
  // Estados de Cucumber (siempre acompañados del nombre del estado en el reporte)
  '--status-passed': '#0CA30C',
  '--status-failed': '#D03B3B',
  '--status-ambiguous': '#EC835A',
  '--status-undefined': '#FAB219',
  '--status-pending': '#9085E9',
  '--status-skipped': '#8B949E',
  '--font-sans': '"Inter","Segoe UI Variable","Segoe UI",system-ui,-apple-system,Roboto,sans-serif',
  '--radius': '.75rem',
};

const ESTILO = `
<style id="k0lmena-theme">
html.dark,:root.dark{${Object.entries(TOKENS).map(([k, v]) => `${k}:${v}`).join(';')}}
html.dark{color-scheme:dark}
html.dark body{
  background:radial-gradient(1200px 500px at 15% -10%,rgba(57,135,229,.14),transparent 60%),
             radial-gradient(900px 400px at 100% 0%,rgba(144,133,233,.09),transparent 55%),var(--background) !important;
  background-attachment:fixed !important;font-family:var(--font-sans) !important;font-feature-settings:"tnum" 1;
}
html.dark .bg-card{background:linear-gradient(180deg,rgba(255,255,255,.025),transparent 120px),var(--card) !important;
  border:1px solid var(--border) !important;box-shadow:0 12px 32px -18px rgba(0,0,0,.7) !important;border-radius:16px !important}
html.dark header,html.dark nav{background:rgba(13,17,23,.82) !important;backdrop-filter:blur(10px);border-color:var(--border) !important}
html.dark table tbody tr:hover td{background:rgba(255,255,255,.025)}
html.dark code,html.dark pre,html.dark .font-mono{font-family:"JetBrains Mono","Cascadia Code",ui-monospace,Consolas,monospace !important}
html.dark .apexcharts-tooltip{background:#0B0F15 !important;border:1px solid var(--border) !important;color:var(--foreground) !important;
  box-shadow:0 10px 28px rgba(0,0,0,.55) !important;border-radius:10px !important}
html.dark .apexcharts-legend-text{color:#B4BCC8 !important}
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

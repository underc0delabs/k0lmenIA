// reports/performance/generar-reporte.js
//
// Reporte de performance de k0lmenIA (k6, Artillery y JMeter con el mismo formato).
// Lo llama run-perf.js al terminar cada corrida:
//   - normaliza el resultado crudo de la herramienta a un "resumen" común (JSON chico,
//     es lo que lee el agente: no hace falta abrir el crudo ni el log),
//   - arma el dashboard HTML (modo oscuro, autocontenido, sin CDN).
const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------- utilidades
const num = (x) => (typeof x === 'number' && isFinite(x) ? x : null);
const r2 = (x) => (x == null ? null : Math.round(x * 100) / 100);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const sinAnsi = (s) => s.replace(/\x1b\[[0-9;]*m/g, '');

function ms(x) {
  if (x == null) return '—';
  return x >= 1000 ? `${(x / 1000).toFixed(2)} s` : `${x.toFixed(0)} ms`;
}
function duracion(seg) {
  if (seg == null) return '—';
  const total = Math.round(seg); // redondear antes de separar: 239,6 s es "4m 0s", no "3m 60s"
  const m = Math.floor(total / 60), s = total % 60;
  return m ? `${m}m ${s}s` : `${s}s`;
}
function fecha(iso) {
  const d = new Date(iso), p = (n) => String(n).padStart(2, '0');
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
const entero = (x) => (x == null ? '—' : Math.round(x).toLocaleString('es-AR'));

// ---------------------------------------------------------------- k6
function parseSubmetrica(clave) {
  const i = clave.indexOf('{');
  if (i === -1) return null;
  const tags = {};
  for (const par of clave.slice(i + 1, clave.lastIndexOf('}')).split(',')) {
    const j = par.indexOf(':');
    if (j > 0) tags[par.slice(0, j).trim()] = par.slice(j + 1).trim();
  }
  return { metrica: clave.slice(0, i), tags };
}

function checksK6(grupo, salida = []) {
  if (!grupo) return salida;
  const checks = Array.isArray(grupo.checks) ? grupo.checks : Object.values(grupo.checks || {});
  for (const c of checks) salida.push({ nombre: c.name, pasan: c.passes || 0, fallan: c.fails || 0 });
  const grupos = Array.isArray(grupo.groups) ? grupo.groups : Object.values(grupo.groups || {});
  for (const g of grupos) checksK6(g, salida);
  return salida;
}

function desdeK6(data) {
  const m = data.metrics || {};
  const v = (nombre) => (m[nombre] && m[nombre].values) || {};
  const dur = v('http_req_duration');
  const seg = num(data.state && data.state.testRunDurationMs) != null ? data.state.testRunDurationMs / 1000 : null;
  const requests = num(v('http_reqs').count) || 0;

  const umbrales = [];
  const endpoints = [];
  const codigos = {};
  for (const [clave, metrica] of Object.entries(m)) {
    for (const [cond, res] of Object.entries(metrica.thresholds || {})) {
      const mm = cond.match(/^\s*([a-z]+(?:\(\d+(?:\.\d+)?\))?)\s*(<=|>=|<|>|===|==|!=)\s*([\d.]+)\s*$/i);
      let valor = mm ? num(metrica.values[mm[1] === 'p(50)' ? 'med' : mm[1]]) : null;
      if (valor != null && /rate/.test(mm[1])) valor = valor * 100;
      umbrales.push({
        metrica: clave, condicion: cond,
        valor: valor == null ? '—' : /rate/.test(mm && mm[1]) ? `${valor.toFixed(2)} %` : /duration|waiting|time/.test(clave) ? ms(valor) : String(r2(valor)),
        ok: !!res.ok,
      });
    }
    const sub = parseSubmetrica(clave);
    if (!sub) continue;
    if (sub.metrica === 'http_req_duration' && sub.tags.name) {
      const x = metrica.values;
      endpoints.push({ nombre: sub.tags.name, requests: num(x.count), avg: num(x.avg), p95: num(x['p(95)']), p99: num(x['p(99)']), max: num(x.max) });
    }
    if (sub.metrica === 'http_reqs' && sub.tags.status != null && num(metrica.values.count)) {
      codigos[sub.tags.status === '0' ? 'sin respuesta' : sub.tags.status] = metrica.values.count;
    }
  }

  const checks = checksK6(data.root_group);
  const errores = {};
  for (const c of checks) if (c.fallan) errores[`check: ${c.nombre}`] = c.fallan;
  for (const [cod, n] of Object.entries(codigos)) if (cod === 'sin respuesta' || Number(cod) >= 400) errores[`HTTP ${cod}`] = n;

  return {
    duracion_s: seg,
    kpis: {
      requests,
      rps: seg ? requests / seg : num(v('http_reqs').rate),
      error_pct: num(v('http_req_failed').rate) != null ? v('http_req_failed').rate * 100 : null,
      usuarios_max: num(v('vus_max').max) ?? num(v('vus_max').value),
      iteraciones: num(v('iterations').count),
    },
    latencia: {
      fuente: 'http_req_duration (cada request)',
      p50: num(dur.med), p90: num(dur['p(90)']), p95: num(dur['p(95)']), p99: num(dur['p(99)']),
      avg: num(dur.avg), max: num(dur.max),
    },
    umbrales,
    detalle: { titulo: 'Por endpoint', filas: endpoints.sort((a, b) => (b.requests || 0) - (a.requests || 0)) },
    codigos,
    checks,
    errores,
    linea_tiempo: [],
  };
}

// ---------------------------------------------------------------- Artillery
function desdeArtillery(data, log) {
  const a = data.aggregate || {};
  const c = a.counters || {}, s = a.summaries || {};
  const seg = num(a.lastMetricAt) && num(a.firstMetricAt) ? (a.lastMetricAt - a.firstMetricAt) / 1000 : null;
  const requests = c['http.requests'] ?? c['browser.http_requests'] ?? null;
  const creados = c['vusers.created'] || 0, completos = c['vusers.completed'] || 0;
  const fuente = s['http.response_time'] ? 'http.response_time' : s['vusers.session_length'] ? 'vusers.session_length' : null;
  const lat = fuente ? s[fuente] : {};

  // Valor medido de una métrica de Artillery ("http.response_time.p95", "vusers.failed", ...)
  const valorDe = (nombre) => {
    if (c[nombre] != null) return c[nombre];
    const i = nombre.lastIndexOf('.');
    return i > 0 && s[nombre.slice(0, i)] ? num(s[nombre.slice(0, i)][nombre.slice(i + 1)]) : null;
  };
  const umbrales = [];
  for (const linea of sinAnsi(log || '').split(/\r?\n/)) {
    const mm = linea.match(/^\s*(ok|fail):\s*(.+?)\s*$/);
    if (!mm) continue;
    const cond = mm[2];
    const ok = mm[1] === 'ok';
    const errorPct = creados ? `${(((creados - completos) / creados) * 100).toFixed(2)} %` : '—';
    const t = cond.match(/^(.+?)\s*(<=|<)\s*([\d.]+)$/);
    if (/^maxErrorRate|vusers\.created - vusers\.completed/.test(cond)) {
      umbrales.push({ metrica: 'usuarios que no completaron el flujo', condicion: `<= ${t ? t[3] : '?'} %`, valor: errorPct, ok });
    } else if (t) {
      const nombre = t[1].trim(), v = valorDe(nombre);
      const valor = v == null ? '—' : /time|length|step|FCP|LCP|TTFB|FID|INP|CLS/.test(nombre) ? ms(v) : String(r2(v));
      umbrales.push({ metrica: nombre, condicion: `${t[2]} ${t[3]}`, valor, ok });
    } else {
      umbrales.push({ metrica: 'condición', condicion: cond, valor: '—', ok }); // expresiones de config.ensure.conditions
    }
  }

  const filas = Object.entries(s)
    .filter(([n]) => n !== fuente)
    .map(([n, x]) => ({ nombre: n, requests: num(x.count), avg: num(x.mean), p95: num(x.p95), p99: num(x.p99), max: num(x.max) }))
    .sort((x, y) => x.nombre.localeCompare(y.nombre));

  const codigos = {};
  for (const [n, v] of Object.entries(c)) {
    const mm = n.match(/\.codes\.(\d+)$/);
    if (mm) codigos[mm[1]] = (codigos[mm[1]] || 0) + v;
  }
  const errores = {};
  for (const [n, v] of Object.entries(c)) if (n.startsWith('errors.')) errores[n.slice(7)] = v;
  for (const [cod, n] of Object.entries(codigos)) if (Number(cod) >= 400) errores[`HTTP ${cod}`] = n;

  const periodos = (data.intermediate || []).filter((p) => p.counters);
  const linea_tiempo = periodos.map((p, i) => {
    const sig = periodos[i + 1];
    const largo = sig ? (Number(sig.period) - Number(p.period)) / 1000 : 10;
    const req = p.counters['http.requests'] ?? p.counters['browser.http_requests'] ?? p.counters['vusers.created'] ?? 0;
    return {
      t: Number(p.period),
      rps: largo > 0 ? req / largo : null,
      p95: fuente && p.summaries && p.summaries[fuente] ? num(p.summaries[fuente].p95) : null,
      errores: p.counters['vusers.failed'] || 0,
    };
  });

  return {
    duracion_s: seg,
    kpis: {
      requests,
      rps: seg && requests != null ? requests / seg : null,
      error_pct: creados ? ((creados - completos) / creados) * 100 : null,
      usuarios_max: creados,
      iteraciones: completos,
    },
    latencia: {
      fuente: fuente === 'http.response_time' ? 'http.response_time (cada request)' : fuente ? 'vusers.session_length (flujo completo de cada usuario)' : '—',
      p50: num(lat.median ?? lat.p50), p90: num(lat.p90), p95: num(lat.p95), p99: num(lat.p99), avg: num(lat.mean), max: num(lat.max),
    },
    umbrales,
    detalle: { titulo: 'Por paso / métrica', filas },
    codigos,
    checks: [],
    errores,
    linea_tiempo,
  };
}

// ---------------------------------------------------------------- JMeter
// CSV con comillas dobles ("" escapa una comilla), como lo escribe JMeter en el .jtl.
function filasCsv(texto) {
  const filas = [];
  let fila = [], campo = '', comillas = false;
  for (let i = 0; i < texto.length; i++) {
    const ch = texto[i];
    if (comillas) {
      if (ch === '"' && texto[i + 1] === '"') { campo += '"'; i++; }
      else if (ch === '"') comillas = false;
      else campo += ch;
    } else if (ch === '"') comillas = true;
    else if (ch === ',') { fila.push(campo); campo = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && texto[i + 1] === '\n') i++;
      fila.push(campo); campo = '';
      if (fila.length > 1 || fila[0]) filas.push(fila);
      fila = [];
    } else campo += ch;
  }
  if (campo || fila.length) { fila.push(campo); filas.push(fila); }
  return filas;
}

function percentil(ordenados, p) {
  if (!ordenados.length) return null;
  return ordenados[Math.min(ordenados.length - 1, Math.ceil((p / 100) * ordenados.length) - 1)];
}

function estadisticas(tiempos) {
  const o = [...tiempos].sort((a, b) => a - b);
  const suma = o.reduce((s, x) => s + x, 0);
  return { n: o.length, p50: percentil(o, 50), p90: percentil(o, 90), p95: percentil(o, 95), p99: percentil(o, 99), avg: o.length ? suma / o.length : null, max: o.length ? o[o.length - 1] : null };
}

// Umbrales del archivo <script>.json: { error_pct, p50, p90, p95, p99, avg, max, por_muestra: { "<label>": {...} } }
const METRICAS_JM = { error_pct: '% de errores', p50: 'p50', p90: 'p90', p95: 'p95', p99: 'p99', avg: 'promedio', max: 'máximo' };
function umbralesJMeter(def, global, porLabel) {
  const salida = [];
  const evaluar = (limites, est, prefijo) => {
    for (const [clave, limite] of Object.entries(limites || {})) {
      if (!(clave in METRICAS_JM) || typeof limite !== 'number') continue;
      const v = est[clave];
      salida.push({
        metrica: `${prefijo}${METRICAS_JM[clave]}`,
        condicion: clave === 'error_pct' ? `<= ${limite} %` : `<= ${limite} ms`,
        valor: v == null ? '—' : clave === 'error_pct' ? `${v.toFixed(2)} %` : ms(v),
        ok: v != null && v <= limite,
      });
    }
  };
  evaluar(def, global, '');
  for (const [label, limites] of Object.entries((def && def.por_muestra) || {})) {
    const est = porLabel[label];
    if (est) evaluar(limites, est, `${label} · `);
    else salida.push({ metrica: `${label} · (sin muestras)`, condicion: 'la muestra existe', valor: '—', ok: false });
  }
  return salida;
}

function desdeJMeter(texto, defUmbrales) {
  const [enc, ...filas] = filasCsv(texto);
  const col = (n) => enc.indexOf(n);
  const [cTs, cEl, cLb, cCod, cOk, cMsg, cHilos] = ['timeStamp', 'elapsed', 'label', 'responseCode', 'success', 'failureMessage', 'allThreads'].map(col);
  if (cTs < 0 || cEl < 0 || cLb < 0) throw new Error('El .jtl no tiene las columnas timeStamp, elapsed y label (¿se guardó en CSV?).');

  const tiempos = [], porLabel = {}, codigos = {}, errores = {}, baldes = {};
  let inicio = Infinity, fin = 0, fallidas = 0, hilosMax = 0;
  for (const f of filas) {
    const ts = Number(f[cTs]), el = Number(f[cEl]), label = f[cLb];
    if (!isFinite(ts) || !isFinite(el)) continue;
    const ok = cOk < 0 || f[cOk] === 'true';
    tiempos.push(el);
    (porLabel[label] = porLabel[label] || { tiempos: [], fallas: 0 }).tiempos.push(el);
    inicio = Math.min(inicio, ts);
    fin = Math.max(fin, ts + el);
    if (cHilos >= 0) hilosMax = Math.max(hilosMax, Number(f[cHilos]) || 0);
    const cod = cCod >= 0 ? f[cCod] : '';
    const codigo = /^\d{3}$/.test(cod) ? cod : 'sin respuesta';
    codigos[codigo] = (codigos[codigo] || 0) + 1;
    if (!ok) {
      fallidas++;
      porLabel[label].fallas++;
      // Los mensajes de las aserciones de JMeter vienen en varias líneas: se dejan en una.
      const motivo = ((cMsg >= 0 && f[cMsg]) || (codigo === 'sin respuesta' ? `sin respuesta: ${cod}` : `HTTP ${codigo}`))
        .replace(/\s+/g, ' ').trim().slice(0, 160);
      errores[motivo] = (errores[motivo] || 0) + 1;
    }
    const b = Math.floor(ts / 10000) * 10000;
    (baldes[b] = baldes[b] || { tiempos: [], fallas: 0 }).tiempos.push(el);
    if (!ok) baldes[b].fallas++;
  }

  const seg = tiempos.length ? (fin - inicio) / 1000 : null;
  const global = { ...estadisticas(tiempos), error_pct: tiempos.length ? (fallidas / tiempos.length) * 100 : null };
  const estLabel = {};
  for (const [label, x] of Object.entries(porLabel)) estLabel[label] = { ...estadisticas(x.tiempos), error_pct: (x.fallas / x.tiempos.length) * 100 };

  return {
    duracion_s: seg,
    kpis: {
      requests: tiempos.length,
      rps: seg ? tiempos.length / seg : null,
      error_pct: global.error_pct,
      usuarios_max: hilosMax || null,
      iteraciones: fallidas,
    },
    latencia: { fuente: 'elapsed (cada muestra)', p50: global.p50, p90: global.p90, p95: global.p95, p99: global.p99, avg: global.avg, max: global.max },
    umbrales: umbralesJMeter(defUmbrales, global, estLabel),
    detalle: {
      titulo: 'Por muestra (label)',
      filas: Object.entries(estLabel).map(([nombre, e]) => ({ nombre, requests: e.n, avg: e.avg, p95: e.p95, p99: e.p99, max: e.max })).sort((a, b) => b.requests - a.requests),
    },
    codigos,
    checks: [],
    errores,
    linea_tiempo: Object.keys(baldes).map(Number).sort((a, b) => a - b).map((ts) => {
      const x = baldes[ts];
      return { t: ts, rps: x.tiempos.length / 10, p95: estadisticas(x.tiempos).p95, errores: x.fallas };
    }),
  };
}

// ---------------------------------------------------------------- HTML
// Mismo sistema de diseño que los informes de k0lmenIA (scripts/_estilos_reporte.py): estilo de
// k0lmena.com, modo oscuro, paleta categórica y de estado validadas (CVD y contraste), un solo eje por gráfico,
// tooltips al pasar el mouse y el estado siempre con ícono + texto, nunca solo color.
const SERIES = ['#C98500', '#14A895', '#4C8DEB', '#E0702E'];
const ESTADO = { ok: '#5CBF4A', warn: '#FFD60A', serio: '#FF8A00', err: '#FF5A4E', neutro: '#8A8172' };
const SUPERFICIE = '#1E1A14';

// Íconos de línea para los indicadores (24x24, trazo 1.8).
const ICONOS = {
  carga: '<path d="M4 18l5-6 4 3 7-9"/><path d="M15 6h5v5"/>',
  rayo: '<path d="M13 3L5 14h6l-1 7 8-11h-6z"/>',
  warn: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17.2v.1"/>',
  reloj: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  persona: '<circle cx="12" cy="6" r="2.2"/><path d="M5 9.5l7 1.5 7-1.5M12 11v4l-3 5M12 15l3 5"/>',
  lista: '<path d="M9 6h11M9 12h11M9 18h11M4.5 6h.1M4.5 12h.1M4.5 18h.1"/>',
};
const icono = (n) => `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONOS[n] || ICONOS.lista}</svg>`;

// Tipografía de k0lmena.com (Saira, Inter y JetBrains Mono) incrustada (scripts/fuentes, licencia OFL): igual sin internet.
const FUENTES = (() => {
  const dir = path.resolve(__dirname, '..', '..', '..', '..', 'scripts', 'fuentes');
  return [['Saira', 'saira.woff2', '500 700'], ['Inter', 'inter.woff2', '400 600'], ['JetBrains Mono', 'jetbrains-mono.woff2', '400 700']].map(([familia, archivo, pesos]) => {
    try {
      const b64 = fs.readFileSync(path.join(dir, archivo)).toString('base64');
      return `@font-face{font-family:'${familia}';font-weight:${pesos};font-display:swap;src:url(data:font/woff2;base64,${b64}) format('woff2')}`;
    } catch {
      return '';
    }
  }).join('');
})();

const CSS = `*{box-sizing:border-box;margin:0;padding:0}
:root{color-scheme:dark;--bg:#0E0C09;--surface:#1A1712;--surface-2:#1E1A14;--tile:#221E17;--line:rgba(244,239,230,.09);--line-2:rgba(244,239,230,.15);
  --ink:#F4EFE6;--body:#CFC7B8;--muted:#8A8172;--accent:#F9B006;--accent-soft:rgba(249,176,6,.12);--ok:#5CBF4A;--warn:#FFD60A;--err:#FF5A4E;--neutral:#8A8172;
  --neon:linear-gradient(135deg,#FFD60A,#FF8A00);--glow-k0:0 0 0 1px rgba(249,176,6,.35),0 0 32px -6px rgba(249,176,6,.40);
  --display:"Saira","Inter",ui-sans-serif,system-ui,sans-serif;
  --sans:"Inter",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font:14px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
body::before{content:"";position:fixed;inset:0;pointer-events:none;background:radial-gradient(760px 420px at 100% -8%,rgba(249,176,6,.12),transparent 62%),
  url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='56' height='100'%3E%3Cpath d='M28 66L0 50L0 16L28 0L56 16L56 50L28 66L28 100' fill='none' stroke='%23F9B006' stroke-opacity='.10' stroke-width='1.2'/%3E%3Cpath d='M28 0L28 34L0 50L0 84L28 100L56 84L56 50L28 34' fill='none' stroke='%23F9B006' stroke-opacity='.07' stroke-width='1.2'/%3E%3C/svg%3E\") 0 0/56px 100px;-webkit-mask-image:linear-gradient(180deg,#000 0,rgba(0,0,0,.55) 420px,rgba(0,0,0,.18) 900px);
  mask-image:linear-gradient(180deg,#000 0,rgba(0,0,0,.55) 420px,rgba(0,0,0,.18) 900px)}
.app{position:relative;display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh}
.side{position:sticky;top:0;height:100vh;display:flex;flex-direction:column;gap:18px;padding:22px 16px;border-right:1px solid var(--line);
  background:linear-gradient(180deg,rgba(26,23,18,.94),rgba(14,12,9,.94))}
.logo{display:flex;align-items:center;gap:11px;padding:4px 8px 14px;border-bottom:1px solid var(--line)}
.logo i{width:36px;height:34px;clip-path:polygon(25% 3%,75% 3%,100% 50%,75% 97%,25% 97%,0 50%);background:var(--neon);filter:drop-shadow(0 0 10px rgba(249,176,6,.45))}
.logo b{display:block;font-family:var(--display);font-size:16px;font-weight:700;letter-spacing:.02em}.logo span{display:block;font-family:var(--mono);font-size:10.5px;color:var(--accent);text-transform:lowercase;letter-spacing:.04em;font-weight:500}
.nav{flex:1;overflow:auto;display:flex;flex-direction:column;gap:2px}
.nav .t{font-family:var(--mono);font-size:11px;text-transform:lowercase;letter-spacing:.02em;color:var(--accent);font-weight:500;padding:4px 10px 8px}.nav .t::before{content:"// "}
.nav a{display:flex;align-items:center;gap:10px;padding:7px 10px;border-radius:9px;color:var(--body);text-decoration:none;font-size:13px}
.nav a i{width:8px;height:8px;clip-path:polygon(25% 3%,75% 3%,100% 50%,75% 97%,25% 97%,0 50%);background:#2E281F}
.nav a:hover{background:rgba(244,239,230,.04);color:var(--ink)}
.nav a.on{background:var(--accent-soft);color:var(--ink);box-shadow:inset 2px 0 0 var(--accent)}.nav a.on i{background:var(--accent)}
.main{min-width:0;padding:26px 34px 56px}.wrap{max-width:1520px;margin:0 auto}
.eyebrow{display:inline-flex;align-items:center;font-family:var(--mono);font-size:13px;text-transform:lowercase;letter-spacing:.01em;font-weight:500;color:var(--accent)}
.eyebrow::before{content:"// "}
h1{font-family:var(--display);font-size:44px;font-weight:700;letter-spacing:-.012em;line-height:1.05;margin:12px 0 16px}
h2{font-family:var(--display);font-size:18px;font-weight:700;letter-spacing:-.005em}
h2::before{content:"";display:inline-block;width:11px;height:10px;clip-path:polygon(25% 3%,75% 3%,100% 50%,75% 97%,25% 97%,0 50%);margin:0 10px 2px 0;background:var(--neon);vertical-align:middle}
.sub{font-size:12px;color:var(--muted);margin:3px 0 14px}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:rgba(26,23,18,.8);border:1px solid var(--line);border-radius:8px;padding:5px 11px;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:lowercase;letter-spacing:.02em;font-weight:500}
.chip b{color:var(--ink);font-family:var(--sans);font-weight:600;font-size:12.5px;text-transform:none;letter-spacing:0;margin-left:6px}
main.grid{display:grid;gap:18px;grid-template-columns:repeat(12,minmax(0,1fr));margin-top:22px}
.card{position:relative;border-radius:20px;padding:20px 22px 22px;grid-column:span 12;min-width:0;overflow:hidden;scroll-margin-top:20px;border:1px solid transparent;
  background:linear-gradient(180deg,var(--surface-2),var(--surface)) padding-box,linear-gradient(180deg,rgba(244,239,230,.11),rgba(244,239,230,.03) 45%,rgba(244,239,230,.05)) border-box;
  box-shadow:0 24px 48px -32px rgba(0,0,0,.9)}
.c6{grid-column:span 6}
@media(max-width:1100px){.app{grid-template-columns:minmax(0,1fr)}.side{position:sticky;top:0;z-index:5;height:auto;flex-direction:row;align-items:center;padding:10px 14px;border:0;border-bottom:1px solid var(--line)}
  .logo{border:0;padding:0}.logo span{display:none}.nav{flex-direction:row;overflow-x:auto;min-width:0;flex:1 1 0}.nav .t{display:none}.nav a{white-space:nowrap}.c6{grid-column:span 12}.main{padding:20px 16px}}
@media(max-width:760px){h1{font-size:26px}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
.banner{position:relative;display:flex;align-items:center;gap:16px;padding:18px 22px;border-radius:16px;font-weight:600;font-size:16px;border:1px solid transparent;
  background:linear-gradient(100deg,var(--tint),transparent 55%) padding-box,linear-gradient(180deg,#1E1A14,#1A1712) padding-box,linear-gradient(90deg,var(--edge),rgba(244,239,230,.05) 60%) border-box}
.banner .bic{width:40px;height:40px;border-radius:12px;display:grid;place-items:center;font-weight:800;font-size:18px;flex:none}
.banner.ok{--tint:rgba(92,191,74,.16);--edge:rgba(92,191,74,.55)}.banner.ok .bic{background:rgba(92,191,74,.18);color:#7BD36A}
.banner.err{--tint:rgba(255,90,78,.18);--edge:rgba(255,90,78,.6)}.banner.err .bic{background:rgba(255,90,78,.2);color:#FF7B70}
.banner.warn{--tint:rgba(255,214,10,.13);--edge:rgba(255,214,10,.5)}.banner.warn .bic{background:rgba(255,214,10,.16);color:#FFD60A}
.nota{color:var(--muted);margin-top:12px}.nota.err{color:#FF8F85}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-top:18px}
.kpi{position:relative;border-radius:16px;padding:16px 18px;display:flex;flex-direction:column;min-height:132px;overflow:hidden;border:1px solid transparent;
  background:linear-gradient(180deg,#221E17,#1E1A14) padding-box,linear-gradient(180deg,rgba(244,239,230,.1),rgba(244,239,230,.03)) border-box}
.kpi::after{content:"";position:absolute;width:160px;height:160px;right:-60px;top:-80px;border-radius:50%;background:radial-gradient(circle,var(--glow,rgba(249,176,6,.15)),transparent 70%)}
.kpi.ok{--glow:rgba(92,191,74,.16)}.kpi.err{--glow:rgba(255,90,78,.2)}
.kpi .ic{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;color:var(--accent);background:var(--accent-soft);box-shadow:inset 0 0 0 1px rgba(249,176,6,.18)}
.kpi.ok .ic{color:#7BD36A;background:rgba(92,191,74,.13)}.kpi.err .ic{color:#FF7B70;background:rgba(255,90,78,.15)}
.kpi .st{position:absolute;top:16px;right:16px;font-size:10.5px;font-weight:650;text-transform:uppercase;letter-spacing:.08em;padding:3px 8px;border-radius:999px}
.kpi.ok .st{color:#7BD36A;background:rgba(92,191,74,.12)}.kpi.err .st{color:#FF7B70;background:rgba(255,90,78,.14)}
.kpi .et{color:var(--muted);font-size:11.5px;font-weight:550;margin-top:auto;padding-top:14px}
.kpi .v{font-size:30px;font-weight:650;letter-spacing:-.035em;line-height:1.1;margin-top:4px}
.barras{display:flex;flex-direction:column;gap:6px;margin-top:4px}
.barra{display:grid;grid-template-columns:110px 1fr 80px;gap:14px;align-items:center;padding:6px 8px;margin:0 -8px;border-radius:10px}
.barra:hover{background:rgba(244,239,230,.03)}
.barra .et{color:var(--body);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pista{height:12px;background:rgba(244,239,230,.045);border-radius:999px;overflow:hidden}
.relleno{display:block;height:100%;border-radius:999px}
.barra .val{text-align:right;font-weight:620;font-variant-numeric:tabular-nums}
svg{width:100%;height:auto;display:block;overflow:visible}
.axis{font-size:11px;fill:var(--muted);font-variant-numeric:tabular-nums;font-family:var(--sans)}.grid-l{stroke:rgba(244,239,230,.05)}.base{stroke:rgba(244,239,230,.12)}
.valor{font-size:12px;fill:var(--ink);font-weight:620;font-family:var(--sans)}
.hit rect{fill:transparent}.hit .cross{stroke:rgba(244,239,230,.25);opacity:0}.hit:hover .cross{opacity:1}
.hit circle{opacity:0}.hit:hover circle{opacity:1}
.tabla{overflow-x:auto;margin:0 -22px -22px}
table{width:100%;border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums}
th{color:var(--muted);font-size:10.5px;text-transform:uppercase;letter-spacing:.12em;font-weight:650;text-align:left;padding:11px 22px;white-space:nowrap;
  background:rgba(244,239,230,.025);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
td{padding:13px 22px;border-bottom:1px solid var(--line);color:var(--body);white-space:nowrap}
tbody tr:last-child td{border-bottom:0}
td:first-child{white-space:normal;word-break:break-word}
tbody tr:hover td{background:rgba(244,239,230,.025)}
code{font-family:var(--mono);font-size:12.5px;color:var(--ink)}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:3px 10px;border-radius:999px;color:var(--ink)}
.pill.ok{background:rgba(92,191,74,.13);box-shadow:inset 0 0 0 1px rgba(92,191,74,.34)}.pill.ok b{color:var(--ok)}
.pill.err{background:rgba(255,90,78,.13);box-shadow:inset 0 0 0 1px rgba(255,90,78,.38)}.pill.err b{color:var(--err)}
.muted{color:var(--muted)}.vacio{color:#7BD36A}
#tip{position:fixed;z-index:10;pointer-events:none;opacity:0;transition:opacity .12s;background:rgba(26,23,18,.97);border:1px solid var(--line-2);border-radius:12px;padding:9px 12px;
  font-size:12.5px;color:var(--ink);box-shadow:0 18px 40px rgba(0,0,0,.65);white-space:pre-line}#tip.on{opacity:1}
footer{margin:32px auto 0;color:var(--muted);font-size:12px;text-align:center}
@media print{.side{display:none}.app{display:block}}`;

const JS = `(function(){var t=document.createElement('div');t.id='tip';document.body.appendChild(t);
document.addEventListener('mousemove',function(e){var el=e.target.closest('[data-tip]');if(!el){t.className='';return;}
t.textContent=el.getAttribute('data-tip');t.className='on';var w=t.offsetWidth,h=t.offsetHeight;
t.style.left=Math.max(8,Math.min(e.clientX+14,innerWidth-w-8))+'px';t.style.top=(e.clientY-h-12<4?e.clientY+16:e.clientY-h-12)+'px';});
var nav=document.getElementById('nav'),cs=[].slice.call(document.querySelectorAll('main.grid > .card'));
var tt=document.createElement('div');tt.className='t';tt.textContent='En este reporte';nav.appendChild(tt);
cs.forEach(function(c,i){var h=c.querySelector('h2');var txt=h?h.textContent:(i===0?'Resumen':'Sección');c.id='s'+i;
var a=document.createElement('a');a.href='#s'+i;a.innerHTML='<i></i>';a.appendChild(document.createTextNode(txt));nav.appendChild(a);c._a=a;});
if('IntersectionObserver' in window){var vis={};var io=new IntersectionObserver(function(es){es.forEach(function(en){vis[en.target.id]=en.isIntersecting;});
for(var i=0;i<cs.length;i++){if(vis[cs[i].id]){cs.forEach(function(x){x._a.classList.remove('on');});cs[i]._a.classList.add('on');break;}}},{rootMargin:'-10% 0px -60% 0px'});
cs.forEach(function(c){io.observe(c);});}})();`;

function barras(items, fmt) {
  if (!items.length) return '<p class="muted">Sin datos.</p>';
  const max = Math.max(1, ...items.map((i) => i.valor || 0));
  return `<div class="barras">${items.map((i) => `
    <div class="barra" data-tip="${esc(i.etiqueta)}: ${esc(fmt(i.valor))}"><span class="et">${esc(i.etiqueta)}</span>
      <span class="pista"><span class="relleno" style="width:${Math.max(0.8, ((i.valor || 0) / max) * 100).toFixed(1)}%;background:${i.color || SERIES[0]}"></span></span>
      <span class="val">${esc(fmt(i.valor))}</span></div>`).join('')}</div>`;
}

// Máximo "redondo" para 4 líneas de grilla.
function escala(max) {
  if (!(max > 0)) return [1, 0.25];
  const exp = 10 ** Math.floor(Math.log10(max));
  for (const m of [1, 2, 2.5, 5, 10]) if ((m * exp) >= max) return [m * exp, (m * exp) / 4];
  return [max, max / 4];
}

// Curva suave monótona (Fritsch–Carlson): pasa por los puntos sin inventar picos.
function curva(p) {
  const n = p.length;
  if (n < 3) return p.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const m = [];
  for (let i = 0; i < n - 1; i++) m.push((p[i + 1][1] - p[i][1]) / ((p[i + 1][0] - p[i][0]) || 1));
  const t = [m[0]];
  for (let i = 1; i < n - 1; i++) t.push(m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2);
  t.push(m[n - 2]);
  for (let i = 0; i < n - 1; i++) {
    if (m[i] === 0) { t[i] = 0; t[i + 1] = 0; continue; }
    const a = t[i] / m[i], b = t[i + 1] / m[i], s = a * a + b * b;
    if (s > 9) { const k = 3 / Math.sqrt(s); t[i] = k * a * m[i]; t[i + 1] = k * b * m[i]; }
  }
  let d = `M${p[0][0].toFixed(1)},${p[0][1].toFixed(1)}`;
  for (let i = 0; i < n - 1; i++) {
    const h = (p[i + 1][0] - p[i][0]) / 3;
    d += ` C${(p[i][0] + h).toFixed(1)},${(p[i][1] + t[i] * h).toFixed(1)} ${(p[i + 1][0] - h).toFixed(1)},${(p[i + 1][1] - t[i + 1] * h).toFixed(1)} ${p[i + 1][0].toFixed(1)},${p[i + 1][1].toFixed(1)}`;
  }
  return d;
}

let gradientes = 0;
// Línea de una sola serie sobre un eje (curva suave con área en degradado), etiqueta en el máximo
// y el último valor, crosshair y tooltip por intervalo.
function grafLinea(puntos, clave, color, fmt, nombre, W = 700) {
  const pts = puntos.filter((p) => p[clave] != null);
  if (pts.length < 2) return '<p class="muted">Corrida demasiado corta: menos de dos intervalos de 10 s.</p>';
  const H = 260, izq = 58, der = 14, arriba = 22, abajo = 28;
  const [max, paso] = escala(Math.max(...pts.map((p) => p[clave])));
  const t0 = pts[0].t, rango = (pts[pts.length - 1].t - t0) || 1;
  const px = (t) => izq + ((t - t0) / rango) * (W - izq - der);
  const py = (v) => arriba + (H - arriba - abajo) * (1 - v / max);
  let svg = '';
  for (let v = 0; v <= max + 1e-9; v += paso) {
    svg += `<line class="${v === 0 ? 'base' : 'grid-l'}" x1="${izq}" x2="${W - der}" y1="${py(v).toFixed(1)}" y2="${py(v).toFixed(1)}"/>`
      + `<text class="axis" x="${izq - 10}" y="${(py(v) + 4).toFixed(1)}" text-anchor="end">${esc(fmt(v))}</text>`;
  }
  const d = curva(pts.map((p) => [px(p.t), py(p[clave])]));
  const gid = `g${++gradientes}`;
  svg += `<defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".32"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>`
    + `<path d="${d} L${px(pts[pts.length - 1].t).toFixed(1)},${py(0).toFixed(1)} L${px(t0).toFixed(1)},${py(0).toFixed(1)} Z" fill="url(#${gid})"/>`
    + `<path d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
  if (pts.length <= 40) svg += pts.map((p) => `<circle cx="${px(p.t).toFixed(1)}" cy="${py(p[clave]).toFixed(1)}" r="3.5" fill="${color}" stroke="${SUPERFICIE}" stroke-width="2"/>`).join('');
  const iMax = pts.reduce((m, p, i) => (p[clave] > pts[m][clave] ? i : m), 0);
  for (const i of new Set([iMax, pts.length - 1])) {
    svg += `<text class="valor" x="${px(pts[i].t).toFixed(1)}" y="${(py(pts[i][clave]) - 10).toFixed(1)}" text-anchor="middle">${esc(fmt(pts[i][clave]))}</text>`;
  }
  pts.forEach((p, i) => {
    const a = i ? (px(pts[i - 1].t) + px(p.t)) / 2 : px(p.t);
    const b = i < pts.length - 1 ? (px(p.t) + px(pts[i + 1].t)) / 2 : px(p.t);
    svg += `<g class="hit" data-tip="${esc(duracion((p.t - t0) / 1000))}\n${esc(nombre)}: ${esc(fmt(p[clave]))}${p.errores ? `\nerrores: ${p.errores}` : ''}">`
      + `<rect x="${a.toFixed(1)}" y="${arriba}" width="${Math.max(b - a, 1).toFixed(1)}" height="${H - arriba - abajo}"/>`
      + `<line class="cross" x1="${px(p.t).toFixed(1)}" x2="${px(p.t).toFixed(1)}" y1="${arriba}" y2="${H - abajo}"/>`
      + `<circle cx="${px(p.t).toFixed(1)}" cy="${py(p[clave]).toFixed(1)}" r="5.5" fill="${color}" stroke="${SUPERFICIE}" stroke-width="2"/></g>`;
  });
  svg += `<text class="axis" x="${izq}" y="${H - 6}">0 s</text><text class="axis" x="${W - der}" y="${H - 6}" text-anchor="end">${esc(duracion(rango / 1000))}</text>`;
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Evolución de ${esc(nombre)}">${svg}</svg>`;
}

function tabla(encabezados, filas) {
  if (!filas.length) return '<p class="muted">Sin datos.</p>';
  return `<div class="tabla"><table><thead><tr>${encabezados.map((e) => `<th>${esc(e)}</th>`).join('')}</tr></thead>
    <tbody>${filas.map((f) => `<tr>${f.map((c) => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function html(r) {
  const k = r.kpis, l = r.latencia;
  const ver = { cumple: ['ok', '✓', 'Cumple los umbrales'], 'no cumple': ['err', '✕', 'No cumple los umbrales'],
    'sin umbrales': ['warn', '!', 'Sin umbrales definidos'], error: ['err', '✕', 'La corrida terminó con error'] }[r.veredicto];
  const kpi = (et, val, clase = '', ic = 'lista') => `<div class="kpi ${clase}"><div class="ic">${icono(ic)}</div>`
    + `${clase ? `<span class="st">${clase === 'ok' ? '✓ En orden' : '✕ Crítico'}</span>` : ''}<div class="et">${et}</div><div class="v">${val}</div></div>`;
  const colorCodigo = (c) => (c === 'sin respuesta' || Number(c) >= 500 ? ESTADO.err : Number(c) >= 400 ? ESTADO.serio : Number(c) >= 300 ? ESTADO.warn : ESTADO.ok);
  const codigos = Object.entries(r.codigos).map(([c, n]) => ({ etiqueta: c, valor: n, color: colorCodigo(c) }));
  const pill = (ok) => (ok ? '<span class="pill ok"><b>✓</b>Cumple</span>' : '<span class="pill err"><b>✕</b>No cumple</span>');
  const evolucion = r.herramienta === 'k6'
    ? '<section class="card"><h2>Evolución en el tiempo</h2><p class="muted">k6 entrega solo el resumen final; la evolución está disponible en las corridas de Artillery y JMeter.</p></section>'
    : `<section class="card c6"><h2>Throughput</h2><p class="sub">req/s por intervalo de 10 s</p>${grafLinea(r.linea_tiempo, 'rps', SERIES[0], (v) => (v >= 10 ? v.toFixed(0) : v >= 1 ? v.toFixed(1) : v.toFixed(2)), 'req/s')}</section>
  <section class="card c6"><h2>Latencia p95</h2><p class="sub">p95 por intervalo de 10 s</p>${grafLinea(r.linea_tiempo, 'p95', SERIES[1], ms, 'p95')}</section>`;

  return `<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="dark">
<title>Performance · ${esc(r.script)} · ${esc(r.perfil)}</title><style>${FUENTES}${CSS}</style></head><body>
<div class="app"><aside class="side"><div class="logo"><i></i><div><b>k0lmena</b><span>Performance</span></div></div><nav class="nav" id="nav"></nav></aside>
<div class="main"><div class="wrap">
<header>
  <span class="eyebrow">Performance · ${esc(r.perfil)}</span>
  <h1>${esc(r.script)}</h1>
  <div class="chips">
    <span class="chip">Herramienta <b>${esc(r.herramienta)}</b></span><span class="chip">Perfil <b>${esc(r.perfil)}</b></span>
    <span class="chip">Destino <b>${esc(r.destino || '—')}</b></span><span class="chip">Fecha <b>${esc(fecha(r.fecha))}</b></span>
    <span class="chip">Duración <b>${duracion(r.duracion_s)}</b></span>
  </div>
</header>
<main class="grid">
  <section class="card"><div class="banner ${ver[0]}"><span class="bic">${ver[1]}</span>${ver[2]}</div>
    ${r.perfil === 'smoke' ? '<p class="nota">Perfil smoke: carga mínima para validar que el script funciona; no representa la carga objetivo.</p>' : ''}
    ${r.error ? `<p class="nota err">${esc(r.error)}</p>` : ''}
    <div class="kpis">
      ${kpi('Requests', entero(k.requests), '', 'carga')}${kpi('Req/s promedio', k.rps == null ? '—' : k.rps.toFixed(2), '', 'rayo')}
      ${kpi('Errores', k.error_pct == null ? '—' : `${k.error_pct.toFixed(2)} %`, k.error_pct > 0 ? 'err' : 'ok', 'warn')}
      ${kpi('p50', ms(l.p50), '', 'reloj')}${kpi('p95', ms(l.p95), '', 'reloj')}${kpi('p99', ms(l.p99), '', 'reloj')}
      ${kpi(r.herramienta === 'artillery' ? 'Usuarios creados' : 'Usuarios máx.', entero(k.usuarios_max), '', 'persona')}
      ${kpi({ k6: 'Iteraciones', artillery: 'Flujos completos', jmeter: 'Muestras con error' }[r.herramienta], entero(k.iteraciones), '', 'lista')}
    </div>
  </section>
  <section class="card"><h2>Umbrales</h2><p class="sub">criterio de aceptación de la corrida</p>
    ${r.umbrales.length ? tabla(['Métrica', 'Condición', 'Valor medido', 'Resultado'], r.umbrales.map((u) => [`<code>${esc(u.metrica)}</code>`, esc(u.condicion), esc(u.valor), pill(u.ok)])) : '<p class="muted">El script no define umbrales: la corrida no tiene criterio de aceptación.</p>'}
  </section>
  ${evolucion}
  <section class="card c6"><h2>Latencia</h2><p class="sub">${esc(l.fuente)}</p>
    ${barras([{ etiqueta: 'p50', valor: l.p50 }, { etiqueta: 'p90', valor: l.p90 }, { etiqueta: 'p95', valor: l.p95 }, { etiqueta: 'p99', valor: l.p99 }, { etiqueta: 'promedio', valor: l.avg }, { etiqueta: 'máximo', valor: l.max }].filter((b) => b.valor != null), ms)}
  </section>
  <section class="card c6"><h2>Códigos de respuesta</h2><p class="sub">cantidad de respuestas por código HTTP</p>${codigos.length ? barras(codigos, entero) : '<p class="muted">Sin datos de códigos de respuesta.</p>'}</section>
  <section class="card"><h2>${esc(r.detalle.titulo)}</h2><p class="sub">ordenado por cantidad</p>
    ${tabla(['Nombre', 'Cantidad', 'Promedio', 'p95', 'p99', 'Máximo'], r.detalle.filas.map((f) => [`<code>${esc(f.nombre)}</code>`, entero(f.requests), ms(f.avg), ms(f.p95), ms(f.p99), ms(f.max)]))}
  </section>
  ${r.checks.length ? `<section class="card c6"><h2>Checks</h2>${tabla(['Check', 'Pasan', 'Fallan'], r.checks.map((c) => [esc(c.nombre), entero(c.pasan), c.fallan ? `<span class="pill err"><b>✕</b>${entero(c.fallan)}</span>` : '0']))}</section>` : ''}
  <section class="card ${r.checks.length ? 'c6' : ''}"><h2>Errores</h2>
    ${Object.keys(r.errores).length ? tabla(['Error', 'Cantidad'], Object.entries(r.errores).sort((a, b) => b[1] - a[1]).map(([e, n]) => [esc(e), `<span class="pill err"><b>✕</b>${entero(n)}</span>`])) : '<p class="vacio">✓ Sin errores.</p>'}
  </section>
</main>
<footer>k0lmenIA · En esta carpeta: resultado crudo <code>${esc(path.basename(r.archivos.crudo))}</code> · log <code>${esc(path.basename(r.archivos.log))}</code></footer>
</div></div></div><script>${JS}</script>
</body></html>`;
}

// ---------------------------------------------------------------- API
/**
 * @param {object} o { herramienta: 'k6'|'artillery'|'jmeter', script, perfil, destino, crudo, log, salida, codigoSalida,
 *                     umbrales (solo JMeter: los del <script>.json) }
 * @returns {object} resumen (también lo escribe en <salida>.json y el HTML en <salida>.html)
 */
function generarReporte(o) {
  const texto = fs.existsSync(o.crudo) ? fs.readFileSync(o.crudo, 'utf8') : '';
  let crudo = null;
  if (texto.trim()) {
    try {
      crudo = o.herramienta === 'jmeter' ? texto : JSON.parse(texto);
    } catch {
      crudo = null; // resultado truncado (la corrida se cortó): se informa como error, no se cae el reporte
    }
  }
  const log = fs.existsSync(o.log) ? fs.readFileSync(o.log, 'utf8') : '';
  const base = { herramienta: o.herramienta, script: o.script, perfil: o.perfil, destino: o.destino, fecha: new Date().toISOString() };
  let r;
  if (!crudo) {
    r = { ...base, duracion_s: null, kpis: {}, latencia: { fuente: '—' }, umbrales: [], detalle: { titulo: 'Detalle', filas: [] }, codigos: {}, checks: [], errores: {}, linea_tiempo: [],
      error: `La herramienta no generó resultados (código de salida ${o.codigoSalida}). Revisá el log.` };
  } else {
    const desde = { k6: () => desdeK6(crudo), artillery: () => desdeArtillery(crudo, log), jmeter: () => desdeJMeter(crudo, o.umbrales) };
    r = { ...base, ...desde[o.herramienta]() };
  }
  // k6 sale con 99 y Artillery con 1 cuando falla un umbral; cualquier otro código es un error de la corrida.
  // JMeter sale con 0 aunque fallen muestras: los umbrales los evalúa este reporte.
  const fallaUmbral = r.umbrales.some((u) => !u.ok);
  if (!crudo || (o.codigoSalida && !fallaUmbral && ![0, 99].includes(o.codigoSalida))) {
    r.veredicto = 'error';
    r.error = r.error || `La herramienta terminó con código ${o.codigoSalida}. Revisá el log.`;
  } else {
    r.veredicto = !r.umbrales.length ? 'sin umbrales' : fallaUmbral ? 'no cumple' : 'cumple';
  }
  r.archivos = { html: `${o.salida}.html`, resumen: `${o.salida}.json`, crudo: o.crudo, log: o.log };

  fs.mkdirSync(path.dirname(o.salida), { recursive: true });
  fs.writeFileSync(`${o.salida}.json`, JSON.stringify(r, null, 2));
  fs.writeFileSync(`${o.salida}.html`, html(r));
  return r;
}

module.exports = { generarReporte };

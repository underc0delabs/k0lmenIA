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
  const m = Math.floor(seg / 60), s = Math.round(seg % 60);
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
function barras(items, unidad) {
  const max = Math.max(1, ...items.map((i) => i.valor || 0));
  return items.map((i) => `
    <div class="barra"><span class="et">${esc(i.etiqueta)}</span>
      <span class="pista"><span class="relleno ${i.clase || ''}" style="width:${Math.max(1, ((i.valor || 0) / max) * 100).toFixed(1)}%"></span></span>
      <span class="val">${unidad === 'ms' ? ms(i.valor) : entero(i.valor)}</span></div>`).join('');
}

function svgLinea(puntos) {
  if (puntos.length < 2) return '<p class="muted">Sin datos de evolución en el tiempo para esta corrida.</p>';
  const W = 760, H = 220, P = 34;
  const t0 = puntos[0].t, t1 = puntos[puntos.length - 1].t || t0 + 1;
  const x = (t) => P + ((t - t0) / (t1 - t0 || 1)) * (W - 2 * P);
  const serie = (clave, color) => {
    const vals = puntos.map((p) => p[clave]).filter((v) => v != null);
    if (!vals.length) return '';
    const max = Math.max(...vals) || 1;
    const pts = puntos.filter((p) => p[clave] != null).map((p) => `${x(p.t).toFixed(1)},${(H - P - (p[clave] / max) * (H - 2 * P)).toFixed(1)}`).join(' ');
    return `<polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round"/>
      <text x="${W - P}" y="${clave === 'rps' ? 16 : 32}" text-anchor="end" fill="${color}" font-size="12">${clave === 'rps' ? 'req/s' : 'p95'} máx: ${clave === 'rps' ? max.toFixed(1) : ms(max)}</text>`;
  };
  return `<svg viewBox="0 0 ${W} ${H}" class="linea" role="img" aria-label="Evolución de req/s y p95">
    <line x1="${P}" y1="${H - P}" x2="${W - P}" y2="${H - P}" stroke="var(--linea)"/>
    ${serie('rps', 'var(--info)')}${serie('p95', 'var(--warn)')}
    <text x="${P}" y="${H - 10}" fill="var(--muted)" font-size="12">0 s</text>
    <text x="${W - P}" y="${H - 10}" text-anchor="end" fill="var(--muted)" font-size="12">${duracion((t1 - t0) / 1000)}</text>
  </svg>`;
}

function tabla(encabezados, filas) {
  if (!filas.length) return '<p class="muted">Sin datos.</p>';
  return `<div class="tabla"><table><thead><tr>${encabezados.map((e) => `<th>${esc(e)}</th>`).join('')}</tr></thead>
    <tbody>${filas.map((f) => `<tr>${f.map((c) => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function html(r) {
  const k = r.kpis, l = r.latencia;
  const ver = { cumple: ['ok', 'Cumple los umbrales'], 'no cumple': ['err', 'No cumple los umbrales'], 'sin umbrales': ['warn', 'Sin umbrales definidos'], error: ['err', 'La corrida terminó con error'] }[r.veredicto];
  const kpi = (et, val, clase = '') => `<div class="kpi"><div class="et">${et}</div><div class="v ${clase}">${val}</div></div>`;
  const codigos = Object.entries(r.codigos).map(([c, n]) => ({ etiqueta: c, valor: n, clase: c === 'sin respuesta' || Number(c) >= 400 ? 'err' : Number(c) >= 300 ? 'warn' : 'ok' }));

  return `<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Performance · ${esc(r.script)} · ${esc(r.perfil)}</title>
<style>
:root{--bg:#0b0f17;--panel:#121826;--linea:#232c3d;--texto:#e6edf3;--muted:#8b97a8;--ok:#22c55e;--warn:#f59e0b;--err:#ef4444;--info:#60a5fa}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--texto);font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:24px 16px 8px;max-width:1200px;margin:auto}h1{margin:0 0 6px;font-size:22px}h2{font-size:15px;margin:0 0 12px}
.chips{display:flex;flex-wrap:wrap;gap:8px}.chip{background:var(--panel);border:1px solid var(--linea);border-radius:999px;padding:3px 10px;color:var(--muted);font-size:12px}
.chip b{color:var(--texto);font-weight:600}main{max-width:1200px;margin:auto;padding:8px 16px 32px;display:grid;gap:14px;grid-template-columns:repeat(12,1fr)}
.card{background:var(--panel);border:1px solid var(--linea);border-radius:14px;padding:16px;grid-column:span 12;min-width:0}.c6{grid-column:span 6}
@media(max-width:860px){.c6{grid-column:span 12}}
.veredicto{display:flex;align-items:center;gap:12px;font-size:18px;font-weight:700}.punto{width:14px;height:14px;border-radius:50%}
.ok{color:var(--ok)}.err{color:var(--err)}.warn{color:var(--warn)}.bg-ok{background:var(--ok)}.bg-err{background:var(--err)}.bg-warn{background:var(--warn)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}.kpi{background:#0e1420;border:1px solid var(--linea);border-radius:10px;padding:10px 12px}
.kpi .et{color:var(--muted);font-size:12px}.kpi .v{font-size:20px;font-weight:700;font-variant-numeric:tabular-nums}
.barra{display:grid;grid-template-columns:110px 1fr 80px;gap:10px;align-items:center;margin:6px 0}.et{color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pista{background:#0e1420;border-radius:6px;height:12px;overflow:hidden}.relleno{display:block;height:100%;background:var(--info);border-radius:6px}
.relleno.ok{background:var(--ok)}.relleno.err{background:var(--err)}.relleno.warn{background:var(--warn)}.val{text-align:right;font-variant-numeric:tabular-nums}
.tabla{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--linea);white-space:nowrap}
th{color:var(--muted);font-weight:600}td:first-child{white-space:normal;word-break:break-word}.muted{color:var(--muted)}
.linea{width:100%;height:auto}code{background:#0e1420;padding:1px 6px;border-radius:6px}footer{max-width:1200px;margin:auto;padding:0 16px 24px;color:var(--muted);font-size:12px}
</style></head><body>
<header>
  <h1>Performance · ${esc(r.script)}</h1>
  <div class="chips">
    <span class="chip">Herramienta <b>${esc(r.herramienta)}</b></span><span class="chip">Perfil <b>${esc(r.perfil)}</b></span>
    <span class="chip">Destino <b>${esc(r.destino || '—')}</b></span><span class="chip">Fecha <b>${esc(fecha(r.fecha))}</b></span>
    <span class="chip">Duración <b>${duracion(r.duracion_s)}</b></span>
  </div>
</header>
<main>
  <section class="card"><div class="veredicto"><span class="punto bg-${ver[0]}"></span><span class="${ver[0]}">${ver[1]}</span></div>
    ${r.perfil === 'smoke' ? '<p class="muted">Perfil smoke: carga mínima para validar que el script funciona; no representa la carga objetivo.</p>' : ''}
    ${r.error ? `<p class="err">${esc(r.error)}</p>` : ''}
    <div class="kpis" style="margin-top:12px">
      ${kpi('Requests', entero(k.requests))}${kpi('Req/s promedio', k.rps == null ? '—' : k.rps.toFixed(2))}
      ${kpi('Errores', k.error_pct == null ? '—' : `${k.error_pct.toFixed(2)} %`, k.error_pct > 0 ? 'err' : 'ok')}
      ${kpi('p50', ms(l.p50))}${kpi('p95', ms(l.p95))}${kpi('p99', ms(l.p99))}
      ${kpi(r.herramienta === 'artillery' ? 'Usuarios creados' : 'Usuarios máx.', entero(k.usuarios_max))}
      ${kpi({ k6: 'Iteraciones', artillery: 'Flujos completos', jmeter: 'Muestras con error' }[r.herramienta], entero(k.iteraciones))}
    </div>
  </section>
  <section class="card"><h2>Umbrales</h2>
    ${r.umbrales.length ? tabla(['Métrica', 'Condición', 'Valor medido', 'Resultado'], r.umbrales.map((u) => [`<code>${esc(u.metrica)}</code>`, esc(u.condicion), esc(u.valor), u.ok ? '<span class="ok">Cumple</span>' : '<span class="err">No cumple</span>'])) : '<p class="warn">El script no define umbrales: la corrida no tiene criterio de aceptación.</p>'}
  </section>
  <section class="card c6"><h2>Latencia</h2><p class="muted" style="margin-top:-6px">${esc(l.fuente)}</p>
    ${barras([{ etiqueta: 'p50', valor: l.p50 }, { etiqueta: 'p90', valor: l.p90 }, { etiqueta: 'p95', valor: l.p95 }, { etiqueta: 'p99', valor: l.p99 }, { etiqueta: 'promedio', valor: l.avg }, { etiqueta: 'máximo', valor: l.max }].filter((b) => b.valor != null), 'ms')}
  </section>
  <section class="card c6"><h2>Códigos de respuesta</h2>${codigos.length ? barras(codigos) : '<p class="muted">Sin datos de códigos de respuesta.</p>'}</section>
  <section class="card"><h2>Evolución en el tiempo</h2>${r.herramienta === 'k6' ? '<p class="muted">k6 entrega solo el resumen final; la evolución está disponible en las corridas de Artillery y JMeter.</p>' : `<p class="muted" style="margin-top:-6px">Req/s (azul) y p95 de la latencia (naranja), cada una en su propia escala, por intervalo de 10 s.</p>${svgLinea(r.linea_tiempo)}`}</section>
  <section class="card"><h2>${esc(r.detalle.titulo)}</h2>
    ${tabla(['Nombre', 'Cantidad', 'Promedio', 'p95', 'p99', 'Máximo'], r.detalle.filas.map((f) => [`<code>${esc(f.nombre)}</code>`, entero(f.requests), ms(f.avg), ms(f.p95), ms(f.p99), ms(f.max)]))}
  </section>
  ${r.checks.length ? `<section class="card c6"><h2>Checks</h2>${tabla(['Check', 'Pasan', 'Fallan'], r.checks.map((c) => [esc(c.nombre), entero(c.pasan), c.fallan ? `<span class="err">${entero(c.fallan)}</span>` : '0']))}</section>` : ''}
  <section class="card ${r.checks.length ? 'c6' : ''}"><h2>Errores</h2>
    ${Object.keys(r.errores).length ? tabla(['Error', 'Cantidad'], Object.entries(r.errores).sort((a, b) => b[1] - a[1]).map(([e, n]) => [esc(e), `<span class="err">${entero(n)}</span>`])) : '<p class="ok">Sin errores.</p>'}
  </section>
</main>
<footer>k0lmenIA · En esta carpeta: resultado crudo <code>${esc(path.basename(r.archivos.crudo))}</code> · log <code>${esc(path.basename(r.archivos.log))}</code></footer>
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
  const crudo = !texto.trim() ? null : o.herramienta === 'jmeter' ? texto : JSON.parse(texto);
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

// Entregabilidad de los correos (agente verificador-correos): si un mail de la app llega a la bandeja de entrada o
// termina en spam no depende solo del contenido, también del dominio que lo manda.
//
//   - DNS del dominio remitente: SPF (v=spf1, política "all", demasiadas consultas), DMARC (_dmarc: política, reportes,
//     alineación) y la clave DKIM del selector con el que se firmó (selector._domainkey.dominio).
//   - Encabezados del correo recibido: DKIM-Signature (dominio y selector), Authentication-Results / ARC (lo que
//     verificó el servidor que lo recibió), Return-Path y Received (HELO), y la alineación de dominios que pide DMARC.
//   - Puntaje de spam: el de SpamAssassin si Mailpit lo tiene activado; si no, uno heurístico con las causas típicas
//     (asunto en mayúsculas, palabras gatillo, poco texto y mucha imagen, acortadores de links, http, sin texto plano…).
//
// Las funciones de análisis son puras (se testean sin red); las consultas DNS usan el resolver de Node y se pueden
// apagar con --dns no (por ejemplo, sin internet). En un ambiente de pruebas el correo suele salir SIN firmar: la firma la
// pone el proveedor de envío en producción. Por eso la falta de DKIM en el mensaje es "Media" y lo que manda es el DNS.
'use strict';

const dns = require('dns').promises;

// Dominios de segundo nivel compartidos (para el "dominio organizacional" de la alineación DMARC, en modo relajado).
const SEGUNDO_NIVEL = new Set(['com.ar', 'gob.ar', 'org.ar', 'net.ar', 'edu.ar', 'com.br', 'com.mx', 'com.uy', 'com.co', 'com.pe', 'com.py',
  'co.uk', 'org.uk', 'com.au', 'co.nz', 'co.jp', 'com.es', 'com.cl', 'gob.mx', 'gov.uk']);
const PALABRAS_SPAM = ['gratis', 'ganaste', 'ganador', 'premio', 'urgente', 'oferta exclusiva', '100% gratis', 'haga clic aquí', 'hacé clic acá',
  'sin costo', 'dinero fácil', 'oportunidad única', 'última oportunidad', 'free', 'winner', 'act now', 'click here', 'limited time',
  'risk-free', 'guaranteed', '$$$', 'viagra', 'casino', 'crypto'];
const ACORTADORES = /\b(bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly|is\.gd|buff\.ly|cutt\.ly|rebrand\.ly)\b/i;

function dominioDe(direccion) {
  const m = String(direccion || '').toLowerCase().match(/@([a-z0-9.-]+\.[a-z]{2,})\s*>?\s*$/);
  return m ? m[1] : '';
}

function organizacional(dominio) {
  const partes = String(dominio || '').toLowerCase().split('.').filter(Boolean);
  if (partes.length <= 2) return partes.join('.');
  const ultimas2 = partes.slice(-2).join('.');
  return SEGUNDO_NIVEL.has(ultimas2) ? partes.slice(-3).join('.') : ultimas2;
}

// ------------------------------------------------------------------ SPF
function analizarSPF(registros) {
  const spf = (registros || []).filter((r) => /^v=spf1(\s|$)/i.test(r.trim()));
  if (!spf.length) return { estado: 'Falta', registro: null, detalle: 'El dominio no publica un registro SPF.', en: { detalle: 'The domain publishes no SPF record.' } };
  if (spf.length > 1) return { estado: 'Error', registro: spf.join(' | '), detalle: 'Hay más de un registro SPF: los receptores lo toman como error (permerror).', en: { detalle: 'There is more than one SPF record: receivers treat it as an error (permerror).' } };
  const r = spf[0].trim();
  const tokens = r.split(/\s+/).slice(1);
  const all = (tokens.find((t) => /^[-~?+]?all$/i.test(t)) || '').toLowerCase();
  const consultas = tokens.filter((t) => /^[-~?+]?(include:|a(:|$)|mx(:|$)|ptr|exists:|redirect=)/i.test(t)).length;
  const base = { registro: r, all: all || null, consultas };
  if (all === '+all' || all === 'all') return { ...base, estado: 'Inseguro', detalle: '"+all" autoriza a cualquier servidor a mandar en nombre del dominio.', en: { detalle: '"+all" lets any server send on behalf of the domain.' } };
  if (consultas > 10) return { ...base, estado: 'Error', detalle: `${consultas} mecanismos con consultas DNS: el límite es 10 (permerror).`, en: { detalle: `${consultas} mechanisms with DNS lookups: the limit is 10 (permerror).` } };
  if (!all && !tokens.some((t) => /^redirect=/i.test(t))) return { ...base, estado: 'Débil', detalle: 'No termina en "-all" ni "~all": no dice qué hacer con los servidores no autorizados.', en: { detalle: 'It does not end in "-all" or "~all": it does not say what to do with unauthorized servers.' } };
  if (all === '?all') return { ...base, estado: 'Débil', detalle: '"?all" es neutral: no protege contra la suplantación.', en: { detalle: '"?all" is neutral: it does not protect against spoofing.' } };
  return { ...base, estado: 'OK', detalle: all === '-all' ? 'Rechaza a los servidores no autorizados.' : 'Marca como sospechosos a los servidores no autorizados (~all).',
    en: { detalle: all === '-all' ? 'Rejects unauthorized servers.' : 'Marks unauthorized servers as suspicious (~all).' } };
}

// ------------------------------------------------------------------ DMARC
function analizarDMARC(registros) {
  const r = (registros || []).find((x) => /^v=DMARC1/i.test(x.trim()));
  if (!r) return { estado: 'Falta', registro: null, detalle: 'El dominio no publica DMARC (_dmarc): Gmail y Yahoo lo exigen a los remitentes masivos.', en: { detalle: 'The domain publishes no DMARC (_dmarc): Gmail and Yahoo require it from bulk senders.' } };
  const tags = Object.fromEntries(r.split(';').map((p) => p.trim().split('=')).filter((p) => p.length === 2).map(([k, v]) => [k.trim().toLowerCase(), v.trim()]));
  const politica = (tags.p || '').toLowerCase();
  const base = { registro: r.trim(), politica: politica || null, pct: tags.pct ? Number(tags.pct) : 100, rua: tags.rua || null,
    adkim: (tags.adkim || 'r').toLowerCase(), aspf: (tags.aspf || 'r').toLowerCase() };
  if (!['none', 'quarantine', 'reject'].includes(politica)) return { ...base, estado: 'Error', detalle: `Política "p=${tags.p || ''}" inválida.`, en: { detalle: `Invalid "p=${tags.p || ''}" policy.` } };
  if (politica === 'none') return { ...base, estado: 'Débil', detalle: 'p=none solo monitorea: los correos que fallan se entregan igual.', en: { detalle: 'p=none only monitors: failing emails are delivered anyway.' } };
  if (base.pct < 100) return { ...base, estado: 'Débil', detalle: `La política se aplica solo al ${base.pct} % de los correos.`, en: { detalle: `The policy applies to only ${base.pct} % of the emails.` } };
  return { ...base, estado: 'OK', detalle: `p=${politica}${base.rua ? ', con reportes' : ', sin reportes (rua)'}.`, en: { detalle: `p=${politica}${base.rua ? ', with reports' : ', without reports (rua)'}.` } };
}

// ------------------------------------------------------------------ DKIM
function firmasDKIM(encabezados) {
  return (encabezados['DKIM-Signature'] || encabezados['dkim-signature'] || []).map((v) => {
    const t = Object.fromEntries(String(v).replace(/\s+/g, ' ').split(';').map((p) => p.trim().split('=')).filter((p) => p.length >= 2)
      .map(([k, ...rest]) => [k.trim().toLowerCase(), rest.join('=').trim()]));
    return { dominio: (t.d || '').toLowerCase(), selector: t.s || '', algoritmo: t.a || '' };
  }).filter((f) => f.dominio && f.selector);
}

function analizarClaveDKIM(registros) {
  const r = (registros || []).join('');
  if (!r) return { estado: 'Falta', detalle: 'No hay clave DKIM publicada para ese selector.', en: { detalle: 'No DKIM key is published for that selector.' } };
  const p = (r.match(/(?:^|;)\s*p=([^;]*)/i) || [])[1];
  if (p === undefined) return { estado: 'Error', detalle: 'El registro no tiene la clave pública (p=).', en: { detalle: 'The record has no public key (p=).' } };
  if (!p.trim()) return { estado: 'Revocada', detalle: 'La clave está vacía (p=): la firma está revocada.', en: { detalle: 'The key is empty (p=): the signature is revoked.' } };
  // La clave pública RSA en DER pesa ~162 bytes con 1024 bits y ~294 con 2048 (base64: 4 caracteres cada 3 bytes).
  const bytes = Math.floor(p.replace(/\s+/g, '').length * 3 / 4);
  if (/k=ed25519/i.test(r)) return { estado: 'OK', bits: 256, detalle: 'Clave Ed25519 publicada.', en: { detalle: 'Ed25519 key published.' } };
  if (bytes < 200) return { estado: 'Débil', bits: 1024, detalle: 'Clave RSA de 1024 bits o menos: se recomienda 2048.', en: { detalle: 'RSA key of 1024 bits or less: 2048 is recommended.' } };
  return { estado: 'OK', bits: bytes > 400 ? 4096 : 2048, detalle: `Clave RSA de ${bytes > 400 ? '4096' : '2048'} bits publicada.`, en: { detalle: `${bytes > 400 ? '4096' : '2048'}-bit RSA key published.` } };
}

// ------------------------------------------------------------------ encabezados del correo recibido
function analizarAuthResults(encabezados) {
  const valores = [...(encabezados['Authentication-Results'] || []), ...(encabezados['ARC-Authentication-Results'] || [])];
  if (!valores.length) return null;
  const texto = valores.join(' ; ');
  const leer = (mecanismo) => ((texto.match(new RegExp(`\\b${mecanismo}=([a-z]+)`, 'i')) || [])[1] || '').toLowerCase() || null;
  return { spf: leer('spf'), dkim: leer('dkim'), dmarc: leer('dmarc'), crudo: texto.slice(0, 500) };
}

function alineacion(de, firmas, returnPath, dmarc) {
  const org = organizacional(dominioDe(de));
  const estricto = (m) => dmarc && dmarc[m] === 's';
  const dkim = firmas.some((f) => (estricto('adkim') ? f.dominio === dominioDe(de) : organizacional(f.dominio) === org));
  const rp = dominioDe(returnPath);
  const spf = rp ? (estricto('aspf') ? rp === dominioDe(de) : organizacional(rp) === org) : null;
  return { dominio_from: dominioDe(de), dominio_return_path: rp || null, dkim_alineado: firmas.length ? dkim : null, spf_alineado: spf };
}

// ------------------------------------------------------------------ puntaje de spam
function spamHeuristico(m) {
  const reglas = [];
  const sumar = (regla, puntos, detalle, en) => reglas.push({ regla, puntos, detalle, ...(en ? { en: { regla: en[0], detalle: en[1] === undefined ? detalle : en[1] } } : {}) });
  const asunto = m.Subject || '';
  const html = m.HTML || '';
  const texto = (m.Text || '').trim();
  const visible = String(html).replace(/<style[\s\S]*?<\/style>|<script[\s\S]*?<\/script>/gi, ' ').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  const letras = asunto.replace(/[^A-Za-zÁÉÍÓÚÑáéíóúñ]/g, '');
  if (letras.length >= 8 && letras === letras.toUpperCase()) sumar('Asunto en mayúsculas', 1.5, asunto.slice(0, 60), ['Subject in capital letters']);
  if ((asunto.match(/!/g) || []).length >= 2) sumar('Varios signos de exclamación en el asunto', 1, asunto.slice(0, 60), ['Several exclamation marks in the subject']);
  const cuerpo = `${asunto} ${texto} ${visible}`.toLowerCase();
  const gatillos = PALABRAS_SPAM.filter((p) => cuerpo.includes(p));
  if (gatillos.length) sumar('Palabras típicas de spam', Math.min(3, gatillos.length * 0.6), gatillos.slice(0, 5).join(', '), ['Typical spam words']);
  if (html && !texto) sumar('Sin versión de texto plano', 1.2, 'Solo HTML.', ['No plain-text version', 'HTML only.']);
  const imagenes = (html.match(/<img\b/gi) || []).length;
  if (imagenes >= 2 && visible.length < 400) sumar('Mucha imagen y poco texto', 1.5, `${imagenes} imágenes y ${visible.length} caracteres de texto.`, ['Many images and little text', `${imagenes} images and ${visible.length} characters of text.`]);
  const links = [...html.matchAll(/href\s*=\s*["']([^"']+)["']/gi)].map((x) => x[1]);
  if (links.some((l) => ACORTADORES.test(l))) sumar('Links acortados', 1.2, 'Los filtros desconfían de bit.ly y similares.', ['Shortened links', 'Filters distrust bit.ly and similar.']);
  const http = links.filter((l) => /^http:\/\//i.test(l)).length;
  if (http) sumar('Links sin https', Math.min(1.5, http * 0.5), `${http} link(s) http.`, ['Links without https', `${http} http link(s).`]);
  if (Buffer.byteLength(html, 'utf8') > 102 * 1024) sumar('HTML muy pesado', 0.5, 'Más de 102 KB.', ['Very heavy HTML', 'More than 102 KB.']);
  const masivo = /darse de baja|desuscrib|unsubscribe|newsletter|novedades|promo/i.test(cuerpo);
  if (masivo && !(m.ListUnsubscribe && (m.ListUnsubscribe.Header || m.ListUnsubscribe.Links))) {
    sumar('Correo masivo sin List-Unsubscribe', 1.5, 'Gmail y Yahoo lo exigen a los envíos masivos (baja en un clic).', ['Bulk email without List-Unsubscribe', 'Gmail and Yahoo require it for bulk sending (one-click unsubscribe).']);
  }
  const total = Math.round(reglas.reduce((s, r) => s + r.puntos, 0) * 10) / 10;
  return { fuente: 'Heurística', puntaje: total, umbral: 5, es_spam: total >= 5, reglas };
}

function spamDeSpamAssassin(sa) {
  if (!sa || sa.Error || typeof sa.Score !== 'number') return null;
  return { fuente: 'SpamAssassin (Mailpit)', puntaje: Math.round(sa.Score * 10) / 10, umbral: 5, es_spam: Boolean(sa.IsSpam),
    reglas: (sa.Rules || []).filter((r) => r.Score > 0).map((r) => ({ regla: r.Name, puntos: r.Score, detalle: r.Description || '' })) };
}

// ------------------------------------------------------------------ consultas DNS (con caché por dominio)
/** Salida de `nslookup -type=TXT` (Windows, Linux y macOS) → registros TXT (cada uno con sus partes "…" unidas). */
function parsearNslookup(salida) {
  const texto = String(salida || '');
  if (!/text\s*=/i.test(texto)) return [];
  return texto.split(/text\s*=/i).slice(1).map((seg) => {
    const hasta = seg.search(/\n\s*\n\S|\n\S+\s+text\s*=/);
    const bloque = hasta >= 0 ? seg.slice(0, hasta) : seg;
    return [...bloque.matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((m) => m[1].replace(/\\"/g, '"')).join('');
  }).filter(Boolean);
}

function txtPorNslookup(nombre, timeoutMs) {
  const r = require('child_process').spawnSync('nslookup', ['-type=TXT', nombre], { encoding: 'utf8', timeout: timeoutMs, windowsHide: true });
  if (r.error) return { registros: [], error: r.error.code || r.error.message };
  return { registros: parsearNslookup(`${r.stdout || ''}\n${r.stderr || ''}`) };
}

async function txt(nombre, timeoutMs = 5000) {
  try {
    const r = await Promise.race([dns.resolveTxt(nombre), new Promise((_, rej) => setTimeout(() => rej(Object.assign(new Error('timeout'), { code: 'ETIMEOUT' })), timeoutMs))]);
    return { registros: r.map((partes) => partes.join('')) };
  } catch (e) {
    if (['ENODATA', 'ENOTFOUND', 'ENOTIMP'].includes(e.code)) return { registros: [] };
    // El resolver de Node no llega (DNS local, VPN, proxy corporativo): se usa el del sistema.
    return txtPorNslookup(nombre, timeoutMs + 3000);
  }
}

async function dnsDominio(dominio, selectores, cache) {
  if (cache.has(dominio)) {
    const c = cache.get(dominio);
    for (const s of selectores) if (!c.dkim[s]) c.dkim[s] = analizarClaveDKIM((await txt(`${s}._domainkey.${dominio}`)).registros);
    return c;
  }
  const spf = await txt(dominio);
  const dmarc = await txt(`_dmarc.${dominio}`);
  const salida = { dominio, spf: { ...analizarSPF(spf.registros), ...(spf.error ? { error: spf.error } : {}) },
    dmarc: { ...analizarDMARC(dmarc.registros), ...(dmarc.error ? { error: dmarc.error } : {}) }, dkim: {} };
  if (spf.error && dmarc.error) salida.sin_dns = true;
  for (const s of selectores) salida.dkim[s] = analizarClaveDKIM((await txt(`${s}._domainkey.${dominio}`)).registros);
  cache.set(dominio, salida);
  return salida;
}

/** Todo lo de entregabilidad de un correo. encabezados = respuesta de /api/v1/message/{id}/headers de Mailpit. */
function evaluar(m, encabezados, dnsInfo, sa) {
  const firmas = firmasDKIM(encabezados || {});
  const returnPath = ((encabezados || {})['Return-Path'] || [])[0] || '';
  const received = ((encabezados || {}).Received || []);
  const helo = ((received[received.length - 1] || '').match(/from\s+([\w.-]+)/i) || [])[1] || null;
  const html = m.HTML || '';
  const visible = String(html).replace(/<style[\s\S]*?<\/style>|<script[\s\S]*?<\/script>/gi, ' ').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  const ratio = html ? Math.round(visible.length / Math.max(1, html.length) * 100) : null;
  const lu = m.ListUnsubscribe || {};
  return {
    dominio: dominioDe((m.From && (m.From.Address || m.From.address)) || ''),
    dns: dnsInfo || null,
    firmas_dkim: firmas,
    auth_results: analizarAuthResults(encabezados || {}),
    alineacion: alineacion((m.From && (m.From.Address || m.From.address)) || '', firmas, returnPath, dnsInfo && dnsInfo.dmarc),
    helo,
    ratio_texto_html: ratio,
    list_unsubscribe: Boolean(lu.Header || (lu.Links && lu.Links.length)),
    list_unsubscribe_post: Boolean(lu.HeaderPost),
    spam: spamDeSpamAssassin(sa) || spamHeuristico(m),
  };
}

/** Hallazgos de entregabilidad (los del DNS se reportan una sola vez por dominio: ver hallazgosDominio). */
function hallazgosCorreo(ent) {
  const h = [];
  const add = (severidad, titulo, detalle, en) => h.push({ tipo: 'Entregabilidad', severidad, titulo, detalle, ...(en ? { en: { titulo: en[0], detalle: en[1] } } : {}) });
  if (!ent.firmas_dkim.length) add('Media', 'El correo no está firmado con DKIM', 'En el ambiente de pruebas puede ser normal (firma el proveedor en producción): confirmá que en producción se firme con el dominio del remitente.',
    ['The email is not signed with DKIM', 'This can be normal in the test environment (the provider signs in production): confirm production signs with the sender domain.']);
  else if (ent.alineacion.dkim_alineado === false) add('Alta', 'La firma DKIM no está alineada con el remitente', `Firma ${ent.firmas_dkim.map((f) => f.dominio).join(', ')} pero el From es ${ent.dominio}: DMARC falla.`,
    ['The DKIM signature is not aligned with the sender', `Signed by ${ent.firmas_dkim.map((f) => f.dominio).join(', ')} but the From is ${ent.dominio}: DMARC fails.`]);
  const ar = ent.auth_results;
  if (ar) for (const k of ['spf', 'dkim', 'dmarc']) if (ar[k] && !['pass', 'none', 'neutral'].includes(ar[k])) add('Alta', `${k.toUpperCase()} = ${ar[k]} según el servidor que lo recibió`, ar.crudo, [`${k.toUpperCase()} = ${ar[k]} according to the receiving server`, ar.crudo]);
  const s = ent.spam;
  const causas = (r) => r.slice(0, 4).map((x) => x.regla).join(', ');
  const causasEn = (r) => r.slice(0, 4).map((x) => (x.en && x.en.regla) || x.regla).join(', ');
  if (s.es_spam) add('Alta', `Puntaje de spam ${s.puntaje} (umbral ${s.umbral})`, `${s.fuente}: ${causas(s.reglas)}`, [`Spam score ${s.puntaje} (threshold ${s.umbral})`, `${s.fuente}: ${causasEn(s.reglas)}`]);
  else if (s.puntaje >= 3) add('Media', `Puntaje de spam ${s.puntaje}: cerca del umbral (${s.umbral})`, `${s.fuente}: ${causas(s.reglas)}`, [`Spam score ${s.puntaje}: close to the threshold (${s.umbral})`, `${s.fuente}: ${causasEn(s.reglas)}`]);
  if (ent.ratio_texto_html !== null && ent.ratio_texto_html < 10) add('Baja', `Poco texto para tanto HTML (${ent.ratio_texto_html} %)`, 'Los filtros desconfían de los correos con mucho código y poco texto visible.',
    [`Little text for so much HTML (${ent.ratio_texto_html} %)`, 'Filters distrust emails with a lot of code and little visible text.']);
  return h;
}

function hallazgosDominio(d) {
  const h = [];
  if (!d || d.sin_dns) return h;
  const add = (severidad, titulo, detalle, en) => h.push({ tipo: 'Entregabilidad', severidad, titulo, detalle, ...(en ? { en: { titulo: en[0], detalle: en[1] } } : {}) });
  const ESTADO_EN = { Falta: 'missing', Error: 'error', Inseguro: 'insecure', 'Débil': 'weak', Revocada: 'revoked' };
  const detEn = (x) => (x.en && x.en.detalle) || x.detalle;
  const sevSPF = { Falta: 'Alta', Error: 'Alta', Inseguro: 'Crítica', 'Débil': 'Media' };
  if (sevSPF[d.spf.estado]) add(sevSPF[d.spf.estado], `SPF ${d.spf.estado.toLowerCase()} en ${d.dominio}`, d.spf.detalle, [`SPF ${ESTADO_EN[d.spf.estado]} on ${d.dominio}`, detEn(d.spf)]);
  const sevDMARC = { Falta: 'Alta', Error: 'Alta', 'Débil': 'Media' };
  if (sevDMARC[d.dmarc.estado]) add(sevDMARC[d.dmarc.estado], `DMARC ${d.dmarc.estado.toLowerCase()} en ${d.dominio}`, d.dmarc.detalle, [`DMARC ${ESTADO_EN[d.dmarc.estado]} on ${d.dominio}`, detEn(d.dmarc)]);
  else if (d.dmarc.estado === 'OK' && !d.dmarc.rua) add('Baja', `DMARC de ${d.dominio} sin reportes (rua)`, 'Sin reportes no te enterás de quién manda en tu nombre ni de los rechazos.',
    [`DMARC for ${d.dominio} without reports (rua)`, 'Without reports you do not find out who sends on your behalf or about rejections.']);
  for (const [sel, k] of Object.entries(d.dkim || {})) {
    if (k.estado !== 'OK') {
      add(k.estado === 'Débil' ? 'Media' : 'Alta', `Clave DKIM ${k.estado.toLowerCase()} (${sel}._domainkey.${d.dominio})`, k.detalle,
        [`DKIM key ${ESTADO_EN[k.estado] || k.estado} (${sel}._domainkey.${d.dominio})`, detEn(k)]);
    }
  }
  return h;
}

module.exports = { dominioDe, organizacional, analizarSPF, analizarDMARC, firmasDKIM, analizarClaveDKIM, analizarAuthResults, alineacion,
  spamHeuristico, spamDeSpamAssassin, parsearNslookup, dnsDominio, evaluar, hallazgosCorreo, hallazgosDominio };

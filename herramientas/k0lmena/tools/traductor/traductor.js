// Revisión de traducciones e internacionalización (agente analista-traductor).
//
// Uso (desde la raíz del repo):
//   npm run traductor -- [--url https://mi-app.com] [--idiomas es-AR,en-US,pt-BR] [--paginas url1,url2]
//                        [--max-paginas 5] [--profundidad 1] [--resoluciones 1366x768,390x844]
//                        [--url-idioma "https://mi-app.com/{idioma_corto}/"] [--historia HU-001] [--headed]
//
// Recorre cada página en cada idioma (el primero de --idiomas es la referencia) y busca:
//   - textos sin traducir: en otro idioma que el de la página, o iguales a la versión de referencia,
//     también en placeholders, textos alternativos, títulos y aria-label,
//   - claves de traducción a la vista (home.title, MISSING_TRANSLATION, {{ t('...') }}),
//   - caracteres mal codificados (Ã©, â€™, �),
//   - textos cortados o desbordados (las traducciones suelen ser más largas) y scroll horizontal,
//   - formatos de otra región: números (1.234,56 vs 1,234.56) y nombres de meses o días en otro idioma,
//   - el atributo lang del HTML que no coincide con el idioma.
// Cómo cambia de idioma, en este orden: los <link rel="alternate" hreflang> de la página, la plantilla
// --url-idioma (TRADUCTOR_URL_IDIOMA del .env) con {idioma} y {idioma_corto}, o el mismo URL pidiendo el
// idioma al navegador (locale y Accept-Language).
// Captura cada página en cada idioma y resolución, con los problemas marcados.
//
// Deja todo en output/traductor/<HU o host>/ (traductor.json, informe-traductor.html, capturas/ y recortes/);
// la corrida anterior pasa a historial/ (se guardan las últimas 5). Solo navega con GET.
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { normalizar, slug, sello, recorrerScroll, cargar } = require('../explorador/explorar.js');
const { parsearResoluciones, descubrir } = require('../pixel-perfect/pixel-perfect.js');
const visual = require('../visual/comparar.js');
const { archivar } = require('../historial/historial.js');

// Datos (output/, input/, .auth/) en el proyecto y scripts de Python en el código de k0lmenIA: ver ../rutas.js.
const { PROYECTO: RAIZ, CODIGO } = require('../rutas');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p);
const GENERADOS = ['traductor.json', 'analisis.json', 'informe-traductor.html', 'capturas', 'recortes'];
const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };

// Palabras muy frecuentes de cada idioma (para detectar en qué idioma está un texto).
const PALABRAS = {
  es: 'el la los las de del que y en un una por con para es se su sus al lo como más pero ya este esta entre cuando muy sin sobre también hasta hay donde desde todo nos ni otros ese eso esto antes algunos qué unos otro otra tanto esa estos mucho nada poco estar estas algo mi tu ver comprar carrito buscar ingresar cuenta envío envíos precio inicio productos ayuda contacto agregar iniciar sesión registrarse olvidaste contraseña gratis pedido pedidos cerrar volver siguiente anterior enviar mensaje nuestro nuestra usted días hoy semana',
  en: 'the of and to in is you that it was for on are as with they at be this have from or had by but not what all were we when your can there an each which she do how their if will up other about out many then them these so some her would make like into time has two more go see no way could people my than first been who its now find down day did get come made may home search cart sign login account price shipping buy view add free order orders close back next previous send message our week today checkout your products product total welcome store deals valid until rights reserved',
  pt: 'o os a as de do da dos das que e em um uma para com não por mais como mas foi ao ele tem à seu sua ou ser quando muito há nos já está eu também só pelo pela até isso ela entre era depois sem mesmo aos ter seus quem nas esse eles estão você essa nem suas meu minha numa pelos elas qual será nós lhe deles essas esses pelas este dele vocês nosso nossa carrinho entrar conta preço frete comprar buscar início produtos ajuda contato adicionar grátis pedido fechar voltar próximo enviar mensagem semana hoje',
  fr: 'le la les de des du un une et en est que qui dans pour pas sur au avec ce il elle ne se plus par son sa ses ou mais nous vous leur on tout aux été être avoir fait comme bien sans panier compte prix livraison acheter rechercher accueil produits aide contact ajouter gratuit commande fermer retour suivant envoyer',
  it: 'il lo la i gli le di del della dei che e un una per con non è sono si da al alla come più ma anche questo questa tutto ci ne nel nella carrello accedi conto prezzo spedizione acquista cerca prodotti aiuto contatto aggiungi gratis ordine chiudi indietro avanti invia',
  de: 'der die das und ist nicht ein eine zu den von mit sich des auf für im dem es auch an werden aus er hat dass sie nach wird bei einer um am sind noch wie einem über so zum kann nur war warenkorb anmelden konto preis versand kaufen suchen startseite produkte hilfe kontakt hinzufügen kostenlos bestellung schließen zurück weiter senden',
};
const DIC = Object.fromEntries(Object.entries(PALABRAS).map(([k, v]) => [k, new Set(v.split(/\s+/))]));
const MESES = {
  es: 'enero febrero marzo abril mayo junio julio agosto septiembre setiembre octubre noviembre diciembre lunes martes miércoles jueves viernes sábado domingo',
  en: 'january february march april june july august september october november december monday tuesday wednesday thursday friday saturday sunday',
  pt: 'janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro segunda-feira terça-feira quarta-feira quinta-feira sexta-feira sábado domingo',
  fr: 'janvier février mars avril mai juin juillet août septembre octobre novembre décembre lundi mardi mercredi jeudi vendredi samedi dimanche',
  it: 'gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre lunedì martedì mercoledì giovedì venerdì sabato domenica',
  de: 'januar februar märz april mai juni juli august september oktober november dezember montag dienstag mittwoch donnerstag freitag samstag sonntag',
};
const MES = Object.fromEntries(Object.entries(MESES).map(([k, v]) => [k, new Set(v.split(/\s+/))]));
const CLAVE_RE = /^(?:[a-z][a-z0-9_]*\.){1,5}[a-z0-9_]+$|MISSING[_ ]TRANSLATION|translation missing|\[missing "[^"]+" translation\]|\{\{\s*(?:t|\$t|i18n)\s*\(|__\(['"]/i;
// Un dominio (qarmy.ar, tienda.com.ar) no es una clave aunque tenga la misma forma.
const DOMINIO = /\.(com|net|org|edu|gov|io|ar|es|br|mx|cl|uy|co|pe|uk|us|de|fr|it|pt|dev|app|ai|info|biz|tv|me)$/i;
const CLAVE = { test: (t) => CLAVE_RE.test(String(t).trim()) && !DOMINIO.test(String(t).trim()) && !/[A-Z]{2,}\./.test(String(t).trim()) };
const MOJIBAKE = /Ã[\u0080-¿¡-ÿ]|â€[™œ\u009d“”˜]|Â[ ¡-¿]|�/;

function argumentos(argv) {
  const a = { maxPaginas: 5, profundidad: 1, resoluciones: '1366x768,390x844', headed: false,
    idiomas: (process.env.TRADUCTOR_IDIOMAS || '').split(',').map((x) => x.trim()).filter(Boolean), urlIdioma: process.env.TRADUCTOR_URL_IDIOMA || '' };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--idiomas') a.idiomas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--resoluciones') a.resoluciones = v();
    else if (k === '--url-idioma') a.urlIdioma = v();
    else if (k === '--historia') a.historia = v();
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  return a;
}

const corto = (idioma) => String(idioma).toLowerCase().split(/[-_]/)[0];

// ¿En qué idioma está este texto? null si es corto o no hay señales claras.
function detectarIdioma(texto) {
  const palabras = String(texto).toLowerCase().normalize('NFC').match(/[\p{L}]+(?:-[\p{L}]+)?/gu) || [];
  if (palabras.length < 2) return null;
  const puntos = {};
  for (const [k, dic] of Object.entries(DIC)) puntos[k] = palabras.filter((p) => dic.has(p)).length;
  const orden = Object.entries(puntos).sort((x, y) => y[1] - x[1]);
  const [mejor, segundo] = orden;
  // Textos cortos (botones, placeholders): solo si TODAS las palabras son de un único idioma.
  if (palabras.length < 3) return mejor[1] === palabras.length && (!segundo || segundo[1] < mejor[1]) ? mejor[0] : null;
  if (mejor[1] < 2 || mejor[1] < palabras.length * 0.2) return null;
  if (segundo && mejor[1] - segundo[1] < 1) return null; // empate: no se sabe
  return mejor[0];
}

// Número con separadores de otra región: "1.234,56" en inglés o "1,234.56" en español.
function formatoNumeroRaro(texto, idioma) {
  const base = corto(idioma);
  const coma = ['es', 'pt', 'fr', 'it', 'de'].includes(base); // decimal con coma
  const malos = [];
  for (const m of String(texto).matchAll(/\b\d{1,3}(?:([.,])\d{3})+(?:([.,])\d{1,2})?\b/g)) {
    const [num, mil, dec] = m;
    if (dec && mil === dec) continue;
    const decimal = dec || null;
    if (decimal && ((coma && decimal === '.') || (!coma && decimal === ','))) malos.push(num);
    else if (!decimal && ((coma && mil === ',') || (!coma && mil === '.'))) malos.push(num);
  }
  return malos;
}

function mesesDeOtroIdioma(texto, idioma) {
  const base = corto(idioma);
  const palabras = String(texto).toLowerCase().match(/[\p{L}-]+/gu) || [];
  const otros = new Set();
  for (const p of palabras) {
    if (MES[base] && MES[base].has(p)) continue;
    for (const [k, set] of Object.entries(MES)) if (k !== base && set.has(p) && !(MES[base] || new Set()).has(p)) otros.add(p);
  }
  // "mayo"/"marzo"/"agosto" son iguales en varios idiomas: solo cuenta si no es palabra del idioma.
  return [...otros].filter((p) => !(DIC[base] && DIC[base].has(p)));
}

// En la página: textos visibles (con su caja) y si están cortados o desbordados.
function _textosEnPagina() {
  const ruta = (el) => {
    const partes = [];
    for (let n = el; n && n.nodeType === 1 && n !== document.body && partes.length < 6; n = n.parentElement) {
      let i = 1;
      for (let s = n.previousElementSibling; s; s = s.previousElementSibling) if (s.tagName === n.tagName) i++;
      partes.unshift(`${n.tagName.toLowerCase()}:${i}`);
    }
    return partes.join('>');
  };
  const sx = window.scrollX;
  const sy = window.scrollY;
  const salida = [];
  const vistos = new Set();
  const visible = (el) => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return cs.visibility !== 'hidden' && cs.display !== 'none' && Number(cs.opacity) > 0 && r.width > 0 && r.height > 0;
  };
  const caminante = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = caminante.nextNode(); n && salida.length < 1500; n = caminante.nextNode()) {
    const t = n.textContent.replace(/\s+/g, ' ').trim();
    if (t.length < 2 || !/\p{L}/u.test(t)) continue;
    const el = n.parentElement;
    if (!el || ['SCRIPT', 'STYLE', 'NOSCRIPT', 'CODE', 'PRE'].includes(el.tagName) || vistos.has(el) || !visible(el)) continue;
    vistos.add(el);
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const texto = (el.innerText || t).replace(/\s+/g, ' ').trim().slice(0, 300);
    // Cortado: el contenido no entra en su caja y se esconde (overflow) o termina en "…".
    const corta = (el.scrollWidth > el.clientWidth + 2 && ['hidden', 'clip'].includes(cs.overflowX)) || cs.textOverflow === 'ellipsis' && el.scrollWidth > el.clientWidth + 1;
    // Desborda: el texto se sale de su contenedor (sin esconderse).
    const padre = el.parentElement;
    const pr = padre ? padre.getBoundingClientRect() : null;
    const desborda = !corta && pr && cs.whiteSpace.includes('nowrap') && r.right > pr.right + 4;
    salida.push({ clave: ruta(el), tag: el.tagName.toLowerCase(), texto, x: Math.round(r.left + sx), y: Math.round(r.top + sy), w: Math.round(r.width), h: Math.round(r.height),
      corta, desborda: Boolean(desborda) });
  }
  // Textos de atributos que también se traducen.
  for (const el of document.querySelectorAll('[placeholder],[alt],[title],[aria-label]')) {
    if (salida.length >= 1800) break;
    for (const at of ['placeholder', 'alt', 'title', 'aria-label']) {
      const v = (el.getAttribute(at) || '').trim();
      if (v.length < 2 || !/\p{L}/u.test(v)) continue;
      const r = el.getBoundingClientRect();
      salida.push({ clave: `${ruta(el)}@${at}`, tag: el.tagName.toLowerCase(), atributo: at, texto: v.slice(0, 200),
        x: Math.round(r.left + sx), y: Math.round(r.top + sy), w: Math.round(r.width), h: Math.round(r.height) });
    }
  }
  return { lang: document.documentElement.getAttribute('lang') || '', titulo: document.title,
    alternos: [...document.querySelectorAll('link[rel="alternate"][hreflang]')].map((l) => ({ idioma: l.getAttribute('hreflang'), url: l.href })),
    textos: salida, desborde: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    alto: document.documentElement.scrollHeight };
}

// URL de una página en un idioma (y cómo se obtuvo).
function urlEnIdioma(url, idioma, alternos, plantilla, referencia) {
  const alt = (alternos || []).find((x) => x.idioma.toLowerCase() === idioma.toLowerCase())
    || (alternos || []).find((x) => corto(x.idioma) === corto(idioma));
  if (alt) return { url: alt.url, metodo: 'hreflang' };
  if (plantilla) {
    const u = new URL(url);
    const pl = plantilla.replace(/\{idioma\}/g, idioma).replace(/\{idioma_corto\}/g, corto(idioma));
    if (/^https?:/i.test(pl)) return { url: new URL(u.pathname.replace(/^\/[a-z]{2}(-[a-z]{2})?(?=\/|$)/i, '').replace(/^\//, '') + u.search, pl.endsWith('/') ? pl : `${pl}/`).href, metodo: 'plantilla' };
    if (pl.startsWith('?') || pl.startsWith('&')) { const v = new URL(url); const [k, val] = pl.replace(/^[?&]/, '').split('='); v.searchParams.set(k, val); return { url: v.href, metodo: 'plantilla' }; }
  }
  return { url, metodo: idioma === referencia ? 'referencia' : 'navegador' };
}

function hallazgosDePantalla(p, ref, idioma, referencia) {
  const h = [];
  const base = corto(idioma);
  const add = (tipo, severidad, titulo, detalle, t) => h.push({ tipo, severidad, titulo, detalle, texto: t && t.texto, elemento: t && t.clave,
    caja: t && t.w ? { x: t.x, y: t.y, w: t.w, h: t.h } : null });
  if (p.lang && corto(p.lang) !== base) add('Atributo lang', 'Media', `El HTML dice lang="${p.lang}" y la página es ${idioma}`, 'Los lectores de pantalla y los buscadores leen el idioma equivocado.');
  if (!p.lang) add('Atributo lang', 'Baja', 'El HTML no declara el idioma (lang)', 'Sin lang, el lector de pantalla no sabe cómo pronunciar.');
  const refPorClave = new Map((ref ? ref.textos : []).map((t) => [t.clave, t]));
  for (const t of p.textos) {
    if (CLAVE.test(t.texto.trim())) { add('Clave de traducción', 'Alta', `Se ve la clave “${t.texto.slice(0, 60)}”`, 'Falta la traducción de esa clave: la persona ve el nombre interno.', t); continue; }
    if (MOJIBAKE.test(t.texto)) { add('Codificación', 'Alta', `Caracteres mal codificados: “${t.texto.slice(0, 60)}”`, 'El texto se guardó o se sirvió con otra codificación (UTF-8 vs Latin-1).', t); continue; }
    const det = detectarIdioma(t.texto);
    if (det && det !== base) {
      add('Sin traducir', t.atributo ? 'Media' : 'Alta', `${t.atributo ? `${t.atributo}: ` : ''}“${t.texto.slice(0, 70)}” está en ${det}`, `La página es ${idioma} pero este texto está en otro idioma.`, t);
      continue;
    }
    const r = refPorClave.get(t.clave);
    if (idioma !== referencia && r && r.texto === t.texto && (t.texto.match(/\p{L}{3,}/gu) || []).length >= 3 && corto(referencia) !== base) {
      add('Igual que la referencia', 'Media', `${t.atributo ? `${t.atributo}: ` : ''}“${t.texto.slice(0, 70)}” es igual que en ${referencia}`,
        'Probablemente no se tradujo (si es un nombre propio o una marca, descartalo).', t);
    }
    if (t.corta) add('Texto cortado', 'Media', `“${t.texto.slice(0, 60)}” no entra en su lugar y se corta`, `El ${t.tag} es más chico que el texto traducido.`, t);
    else if (t.desborda) add('Texto desbordado', 'Media', `“${t.texto.slice(0, 60)}” se sale de su contenedor`, 'El texto traducido es más largo que el espacio que tiene.', t);
    const nums = formatoNumeroRaro(t.texto, idioma);
    if (nums.length) add('Formato de número', 'Media', `${nums.slice(0, 3).join(', ')} usa el formato de otra región`, `En ${idioma} se escribe ${new Intl.NumberFormat(idioma).format(1234.56)}.`, t);
    const meses = mesesDeOtroIdioma(t.texto, idioma);
    if (meses.length) add('Fecha en otro idioma', 'Media', `“${meses.join(', ')}” no está en ${idioma}`, `La fecha o el día de la semana no se tradujo: “${t.texto.slice(0, 80)}”.`, t);
  }
  if (p.desborde > 4 && (!ref || ref.desborde <= 4)) add('Desborde', 'Media', `La página se sale ${p.desborde} px de ancho en ${idioma}`, 'Aparece scroll horizontal: algún texto traducido no entra.', null);
  return h;
}

// Un mismo problema (el mismo texto) en varias páginas es un solo hallazgo.
function agrupar(hallazgos) {
  const grupos = new Map();
  const salida = [];
  for (const h of hallazgos) {
    const k = `${h.tipo}|${h.idioma}|${h.texto || h.titulo}`;
    const donde = { pagina: h.pagina, url: h.url, resolucion: h.resolucion, recorte: h.recorte, captura: h.captura };
    if (!grupos.has(k)) { const g = { ...h, donde: [] }; grupos.set(k, g); salida.push(g); }
    grupos.get(k).donde.push(donde);
  }
  return salida;
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(CODIGO, 'scripts', 'generar_informe_traductor.py'),
    path.join(carpeta, 'traductor.json'), path.join(carpeta, 'informe-traductor.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_traductor.py <carpeta>/traductor.json <carpeta>/informe-traductor.html`);
    return false;
  }
  return true;
}

async function main() {
  const a = argumentos(process.argv.slice(2));
  if (a.ayuda) {
    console.log(fs.readFileSync(__filename, 'utf8').split('\n').filter((l) => l.startsWith('//')).map((l) => l.slice(3)).join('\n'));
    return;
  }
  const url = a.url || (a.paginas && a.paginas[0]) || process.env.APP_URL || process.env.BASEURL;
  if (!url) throw new Error('No hay URL: pasala con --url o definí APP_URL en el .env de la raíz.');
  if (!/^https?:\/\//i.test(url)) throw new Error(`La URL tiene que empezar con http:// o https:// (recibí "${url}").`);
  const inicio = normalizar(url);
  const host = new URL(inicio).hostname;
  const { chromium } = require('playwright');
  const browser = await navegadorComun.lanzar(chromium, { headless: !a.headed });
  const ctx0 = await browser.newContext();
  const pag0 = await ctx0.newPage();
  await cargar(pag0, inicio).catch(() => {});
  const info0 = await pag0.evaluate(_textosEnPagina).catch(() => ({ alternos: [], lang: '' }));
  // Idiomas: los pedidos o, si no, los que declara el sitio (hreflang), con el de la página primero.
  if (!a.idiomas.length) {
    const decl = [...new Set((info0.alternos || []).map((x) => x.idioma).filter((x) => x && x !== 'x-default'))];
    const propio = info0.lang || (decl[0] || 'es');
    a.idiomas = [propio, ...decl.filter((x) => corto(x) !== corto(propio))];
  }
  if (a.idiomas.length < 2) {
    await browser.close();
    throw new Error(`Solo encontré un idioma (${a.idiomas.join(', ') || 'ninguno'}): pasá los que querés revisar con --idiomas es-AR,en-US (o TRADUCTOR_IDIOMAS en el .env).`);
  }
  const paginas = await descubrir(pag0, inicio, a);
  await ctx0.close();
  const referencia = a.idiomas[0];
  const resoluciones = parsearResoluciones(a.resoluciones);
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'traductor', a.historia || host);
  archivar(carpeta, GENERADOS, 'traductor.json');
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });
  const dirCap = path.join(carpeta, 'capturas');
  const dirRec = path.join(carpeta, 'recortes');
  for (const d of [dirCap, dirRec]) fs.mkdirSync(d, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');
  const relRaiz = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  console.log(`Traducciones: ${paginas.length} página(s) × ${a.idiomas.length} idioma(s) (${a.idiomas.join(', ')}; referencia ${referencia}) × ${resoluciones.length} resolución(es)`);
  console.log(`Salida: ${relRaiz(carpeta)}`);
  const t0 = Date.now();
  const pantallas = [];
  let hallazgos = [];
  for (const [i, u] of paginas.entries()) {
    const idPag = `${String(i + 1).padStart(2, '0')}-${slug(u)}`;
    for (const res of resoluciones) {
      let ref = null;
      for (const idioma of a.idiomas) {
        const ctx = await browser.newContext({ viewport: { width: res.ancho, height: res.alto }, deviceScaleFactor: 1, locale: idioma,
          extraHTTPHeaders: { 'Accept-Language': `${idioma},${corto(idioma)};q=0.9` }, ...(res.ancho < 768 ? { isMobile: true, hasTouch: true } : {}) });
        const page = await ctx.newPage();
        const destino = urlEnIdioma(u, idioma, info0.alternos && i === 0 ? info0.alternos : null, a.urlIdioma, referencia);
        const p = { pagina: idPag, url: u, url_idioma: destino.url, metodo: destino.metodo, idioma, resolucion: res.id };
        process.stdout.write(`[${idioma.padEnd(6)} ${res.id.padEnd(9)}] ${destino.url} `);
        try {
          const { resp } = await cargar(page, destino.url);
          p.status = resp ? resp.status() : 0;
          // Las demás páginas: si declaran hreflang, se sigue ese link (más preciso que la plantilla).
          if (i > 0 && idioma !== referencia) {
            const alt = await page.evaluate(() => [...document.querySelectorAll('link[rel="alternate"][hreflang]')].map((l) => ({ idioma: l.getAttribute('hreflang'), url: l.href })));
            const mejor = urlEnIdioma(u, idioma, alt, a.urlIdioma, referencia);
            if (mejor.metodo === 'hreflang' && mejor.url !== destino.url) { await cargar(page, mejor.url); p.url_idioma = mejor.url; p.metodo = 'hreflang'; }
          }
          await recorrerScroll(page);
          await page.evaluate(() => window.scrollTo(0, 0));
          await visual.estabilizar(page);
          const info = await page.evaluate(_textosEnPagina);
          Object.assign(p, { lang: info.lang, titulo: info.titulo, textos: info.textos.length, desborde: info.desborde });
          const arch = path.join(dirCap, `${idPag}-${idioma}-${res.id}.png`);
          const alto = Math.min(info.alto, 9000);
          await page.screenshot({ path: arch, fullPage: alto === info.alto, ...(alto < info.alto ? { clip: { x: 0, y: 0, width: res.ancho, height: alto } } : {}) });
          p.captura = rel(arch);
          const hs = hallazgosDePantalla(info, ref, idioma, referencia);
          for (const [k, h] of hs.entries()) {
            if (h.caja && h.caja.y < alto) {
              const rec = path.join(dirRec, `${idPag}-${idioma}-${res.id}-${k + 1}.png`);
              fs.writeFileSync(rec, visual.recorteMarcado(arch, visual.ventanaDe([h.caja], 60, 300, 120), h.caja));
              h.recorte = rel(rec);
            }
            hallazgos.push({ ...h, idioma, pagina: idPag, url: p.url_idioma || u, resolucion: res.id, captura: p.captura });
          }
          p.hallazgos = hs.length;
          const sinTrad = hs.filter((h) => h.tipo === 'Sin traducir' || h.tipo === 'Igual que la referencia').length;
          p.traducido_pct = idioma === referencia ? 100 : Math.max(0, Math.round((1 - sinTrad / Math.max(1, info.textos.length)) * 1000) / 10);
          if (idioma === referencia) ref = info;
          console.log(`→ ${hs.length} hallazgo(s)`);
        } catch (e) {
          p.error = String(e.message || e).split('\n')[0].slice(0, 200);
          console.log(`→ error: ${p.error}`);
        }
        pantallas.push(p);
        await ctx.close();
      }
    }
  }
  await browser.close();
  hallazgos = agrupar(hallazgos);
  hallazgos.sort((x, y) => SEV_ORDEN[x.severidad] - SEV_ORDEN[y.severidad] || y.donde.length - x.donde.length);
  hallazgos.forEach((h, i) => { h.id = `T-${String(i + 1).padStart(2, '0')}`; });
  const porIdioma = {};
  for (const idioma of a.idiomas) {
    const ps = pantallas.filter((p) => p.idioma === idioma && p.traducido_pct != null);
    porIdioma[idioma] = { traducido_pct: ps.length ? Math.round(ps.reduce((s, p) => s + p.traducido_pct, 0) / ps.length * 10) / 10 : null,
      hallazgos: hallazgos.filter((h) => h.idioma === idioma).length, metodo: (ps.find((p) => p.metodo) || {}).metodo || null };
  }
  const cuenta = (t) => hallazgos.filter((h) => h.tipo === t).length;
  const resultado = {
    url: inicio, host, historia: a.historia || null, fecha: new Date().toISOString(), marca: sello(), duracion_s: Math.round((Date.now() - t0) / 1000),
    herramienta: `Playwright ${require('playwright/package.json').version}`, idiomas: a.idiomas, referencia, resoluciones: resoluciones.map((r) => r.id),
    resumen: { paginas: paginas.length, idiomas: a.idiomas.length, pantallas: pantallas.length, hallazgos: hallazgos.length,
      sin_traducir: cuenta('Sin traducir') + cuenta('Igual que la referencia'), claves: cuenta('Clave de traducción'), codificacion: cuenta('Codificación'),
      cortados: cuenta('Texto cortado') + cuenta('Texto desbordado') + cuenta('Desborde'), formatos: cuenta('Formato de número') + cuenta('Fecha en otro idioma'),
      lang: cuenta('Atributo lang'), por_idioma: porIdioma,
      por_severidad: Object.fromEntries(['Crítica', 'Alta', 'Media', 'Baja'].map((s) => [s, hallazgos.filter((h) => h.severidad === s).length])) },
    hallazgos, pantallas,
  };
  const salida = path.join(carpeta, 'traductor.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  const r = resultado.resumen;
  console.log(`\nSin traducir: ${r.sin_traducir} · claves a la vista: ${r.claves} · cortados o desbordados: ${r.cortados} · formatos: ${r.formatos} · hallazgos: ${r.hallazgos}`);
  for (const [k, v] of Object.entries(porIdioma)) console.log(`  ${k}: ${v.traducido_pct ?? '—'} % traducido · ${v.hallazgos} hallazgo(s) · ${v.metodo || ''}`);
  console.log(`Datos: ${relRaiz(salida)}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${relRaiz(path.join(carpeta, 'informe-traductor.html'))}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

module.exports = { argumentos, detectarIdioma, formatoNumeroRaro, mesesDeOtroIdioma, urlEnIdioma, hallazgosDePantalla, agrupar, corto, CLAVE, MOJIBAKE, GENERADOS };

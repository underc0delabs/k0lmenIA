// Prueba de validaciones de formularios (agente probador-formularios).
//
// Uso (desde la raíz del repo):
//   npm run formularios -- [--url https://mi-app.com/registro] [--paginas url1,url2] [--max-paginas 6]
//                          [--profundidad 1] [--historia HU-001] [--enviar-vacio] [--headed]
//
// Encuentra los formularios de las páginas y, campo por campo, prueba sus validaciones SIN ENVIAR nada:
// completa un valor, sale del campo y mira si el campo lo rechaza (validación del navegador, aria-invalid o
// un mensaje de error de la aplicación) y qué mensaje muestra. Pruebas según el campo:
//   obligatorio vacío y solo espacios · largo máximo (y si no tiene) · largo mínimo · email con formatos
//   inválidos y uno válido · número con letras, fuera de rango y en los límites · teléfono y URL con texto ·
//   patrón · nombres con acentos, ñ y apóstrofe (tienen que aceptarse) · lista y casilla obligatorias.
// Revisa además: etiqueta del campo, indicación visual de obligatorio, tipo de campo (email como texto),
// autocomplete en nombre, email y teléfono, reglas visibles de la contraseña.
// Con --enviar-vacio (solo con confirmación: si el formulario no valida, se ENVÍA) aprieta el botón de
// enviar con todo vacío y captura qué mensajes muestra.
//
// Deja todo en output/formularios/<HU o host>/ (formularios.json, informe-formularios.html, capturas/); la
// corrida anterior pasa a historial/ (se guardan las últimas 5).
const fs = require('fs');
const path = require('path');
const navegadorComun = require('../navegador/navegador');
const { normalizar, slug, sello, cargar } = require('../explorador/explorar.js');
const { descubrir } = require('../pixel-perfect/pixel-perfect.js');
const visual = require('../visual/comparar.js');
const { archivar } = require('../historial/historial.js');

// Datos (output/, input/, .auth/) en el proyecto y scripts de Python en el código de k0lmenIA: ver ../rutas.js.
const { PROYECTO: RAIZ, CODIGO } = require('../rutas');
const desde = (p) => path.resolve(process.env.INIT_CWD || process.cwd(), p);
const GENERADOS = ['formularios.json', 'analisis.json', 'informe-formularios.html', 'capturas'];
const SEV_ORDEN = { 'Crítica': 0, 'Alta': 1, 'Media': 2, 'Baja': 3 };

function argumentos(argv) {
  const a = { maxPaginas: 6, profundidad: 1, headed: false, enviarVacio: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--url') a.url = v();
    else if (k === '--paginas') a.paginas = v().split(',').map((x) => x.trim()).filter(Boolean);
    else if (k === '--max-paginas') a.maxPaginas = parseInt(v(), 10);
    else if (k === '--profundidad') a.profundidad = parseInt(v(), 10);
    else if (k === '--historia') a.historia = v();
    else if (k === '--enviar-vacio') a.enviarVacio = true;
    else if (k === '--salida') a.salida = v();
    else if (k === '--headed') a.headed = true;
    else if (k === '-h' || k === '--help') a.ayuda = true;
    else throw new Error(`Opción desconocida: ${k}`);
  }
  if (a.historia && !/^[A-Za-z]+-\d+$/.test(a.historia)) throw new Error('--historia tiene que ser un ID como HU-001.');
  return a;
}

// En la página: formularios y sus campos (marca cada campo con data-k0-campo para encontrarlo después).
function _formularios() {
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const etiquetaDe = (c) => {
    const lab = (c.id && document.querySelector(`label[for="${CSS.escape(c.id)}"]`)) || c.closest('label');
    if (lab) return { texto: lab.innerText.replace(/\s+/g, ' ').trim(), fuente: 'label' };
    if (c.getAttribute('aria-label')) return { texto: c.getAttribute('aria-label'), fuente: 'aria-label' };
    const ids = (c.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean);
    if (ids.length) return { texto: ids.map((i) => (document.getElementById(i) || {}).innerText || '').join(' ').trim(), fuente: 'aria-labelledby' };
    if (c.getAttribute('placeholder')) return { texto: c.getAttribute('placeholder'), fuente: 'placeholder' };
    return { texto: '', fuente: null };
  };
  const SEL = 'input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]):not([type=image]):not([type=file]), textarea, select';
  let grupos = [...document.querySelectorAll('form')].filter(visible).map((f) => ({ el: f, campos: [...f.querySelectorAll(SEL)].filter(visible) }));
  const sueltos = [...document.querySelectorAll(SEL)].filter((c) => visible(c) && !c.closest('form'));
  if (sueltos.length >= 2) grupos.push({ el: null, campos: sueltos });
  grupos = grupos.filter((g) => g.campos.length);
  let n = 0;
  return grupos.map((g, i) => {
    const campos = g.campos.map((c) => {
      n++;
      c.setAttribute('data-k0-campo', String(n));
      const et = etiquetaDe(c);
      const tipo = c.tagName === 'SELECT' ? 'select' : c.tagName === 'TEXTAREA' ? 'textarea' : (c.getAttribute('type') || 'text').toLowerCase();
      const req = c.required || c.getAttribute('aria-required') === 'true';
      const marca = /\*|obligatori|requerid|required/i.test(et.texto + ' ' + (c.getAttribute('placeholder') || ''));
      const num = (x) => (c.getAttribute(x) != null && c.getAttribute(x) !== '' ? Number(c.getAttribute(x)) : null);
      const cerca = (c.closest('div, fieldset, p, li') || c.parentElement || document.body).innerText || '';
      return { n, nombre: c.name || c.id || et.texto || `campo ${n}`, etiqueta: et.texto, fuente_etiqueta: et.fuente, tipo, requerido: req, marca_obligatorio: marca,
        maxlength: c.maxLength > 0 ? c.maxLength : null, minlength: c.minLength > 0 ? c.minLength : null, min: num('min'), max: num('max'), step: num('step'),
        pattern: c.getAttribute('pattern'), autocomplete: c.getAttribute('autocomplete'), inputmode: c.getAttribute('inputmode'),
        placeholder: c.getAttribute('placeholder'), opciones: c.tagName === 'SELECT' ? [...c.options].map((o) => ({ valor: o.value, texto: o.text.trim() })) : null,
        reglas_visibles: /\d+\s*(caracteres|characters|dígitos)|mayúscula|número|símbolo/i.test(cerca) };
    });
    const f = g.el;
    const boton = f ? f.querySelector('button[type=submit], input[type=submit], button:not([type])') : null;
    return { indice: i, nombre: (f && (f.getAttribute('name') || f.id || f.getAttribute('aria-label'))) || (f ? `formulario ${i + 1}` : 'campos sin formulario'),
      accion: f ? f.getAttribute('action') : null, metodo: f ? (f.getAttribute('method') || 'get').toUpperCase() : null, campos, boton: Boolean(boton) };
  });
}

// Botón de enviar de ESE formulario (no el primero de la página): se ubica desde su primer campo, que
// _formularios marca con data-k0-campo (la numeración es la misma al recargar la página).
function botonEnvio(page, f) {
  return page.locator(`[data-k0-campo="${f.campos[0].n}"]`).locator('xpath=ancestor::form[1]')
    .locator('button[type=submit], input[type=submit], button:not([type])').first();
}

// Pruebas que corresponden a un campo: [{regla, valor, esperado: 'rechaza'|'acepta'}].
function pruebasPara(c) {
  const p = [];
  const pista = `${c.nombre} ${c.etiqueta} ${c.placeholder || ''} ${c.autocomplete || ''}`.toLowerCase();
  const esEmail = c.tipo === 'email' || /e-?mail|correo/.test(pista);
  const esTel = c.tipo === 'tel' || /tel[eé]fono|celular|phone|whatsapp/.test(pista);
  const esNombre = /nombre|apellido|name/.test(pista) && !esEmail;
  const texto = ['text', 'search', 'textarea', 'password', 'tel', 'url', 'email'].includes(c.tipo);
  if (c.tipo === 'checkbox' || c.tipo === 'radio') {
    if (c.requerido) p.push({ regla: 'Obligatorio sin marcar', valor: null, accion: 'desmarcar', esperado: 'rechaza' });
    return p;
  }
  if (c.tipo === 'select') {
    if (c.requerido && c.opciones && c.opciones.some((o) => o.valor === '')) p.push({ regla: 'Obligatorio sin elegir', valor: '', accion: 'elegir', esperado: 'rechaza' });
    return p;
  }
  if (c.requerido) p.push({ regla: 'Obligatorio vacío', valor: '', esperado: 'rechaza' });
  if (c.requerido && texto) p.push({ regla: 'Solo espacios', valor: '   ', esperado: 'rechaza' });
  if (texto && c.maxlength) p.push({ regla: `Más de ${c.maxlength} caracteres`, valor: 'a'.repeat(c.maxlength + 1), esperado: 'corta' });
  if (c.minlength) p.push({ regla: `Menos de ${c.minlength} caracteres`, valor: 'a'.repeat(Math.max(1, c.minlength - 1)), esperado: 'rechaza' });
  if (esEmail) {
    p.push({ regla: 'Email sin @', valor: 'ana.test.com', esperado: 'rechaza' });
    p.push({ regla: 'Email sin dominio', valor: 'ana@', esperado: 'rechaza' });
    p.push({ regla: 'Email válido', valor: 'ana@test.com', esperado: 'acepta' });
  }
  if (c.tipo === 'number' || c.tipo === 'range') {
    if (c.min != null) { p.push({ regla: `Menor al mínimo (${c.min})`, valor: String(c.min - 1), esperado: 'rechaza' }); p.push({ regla: `En el mínimo (${c.min})`, valor: String(c.min), esperado: 'acepta' }); }
    if (c.max != null) { p.push({ regla: `Mayor al máximo (${c.max})`, valor: String(c.max + 1), esperado: 'rechaza' }); p.push({ regla: `En el máximo (${c.max})`, valor: String(c.max), esperado: 'acepta' }); }
    if (!c.step || Number.isInteger(c.step)) p.push({ regla: 'Con decimales', valor: '1.5', esperado: c.step ? 'rechaza' : 'informa' });
  }
  if (esTel && c.tipo !== 'number') p.push({ regla: 'Teléfono con letras', valor: 'abc-defg', esperado: 'rechaza' });
  if (c.tipo === 'url') p.push({ regla: 'URL inválida', valor: 'no es una url', esperado: 'rechaza' });
  if (c.pattern) p.push({ regla: `No cumple el patrón (${c.pattern.slice(0, 30)})`, valor: '¿?', esperado: 'rechaza' });
  if (esNombre && texto) p.push({ regla: 'Nombre con acentos, ñ y apóstrofe', valor: "José Ñandú O'Brien", esperado: 'acepta' });
  if (texto && !c.maxlength && ['text', 'textarea'].includes(c.tipo)) p.push({ regla: 'Texto muy largo (300 caracteres)', valor: 'a'.repeat(300), esperado: 'informa' });
  return p;
}

// Prueba un valor: lo completa, sale del campo y mira si se rechaza y qué mensaje aparece.
async function probar(page, c, prueba) {
  const sel = `[data-k0-campo="${c.n}"]`;
  const campo = page.locator(sel).first();
  const antes = await page.evaluate(() => [...document.querySelectorAll('[role=alert], [class*=error i], [class*=invalid i], [class*=feedback i], [aria-live]')]
    .map((x) => (x.innerText || '').trim()).join('|'));
  if (prueba.accion === 'desmarcar') await campo.uncheck({ timeout: 3000 }).catch(() => {});
  else if (prueba.accion === 'elegir') await campo.selectOption(prueba.valor, { timeout: 3000 }).catch(() => {});
  else {
    await campo.fill('', { timeout: 3000 }).catch(() => {});
    if (prueba.valor) await campo.pressSequentially(prueba.valor.length > 60 ? prueba.valor.slice(0, 1) : prueba.valor, { timeout: 8000 }).catch(() => {});
    if (prueba.valor && prueba.valor.length > 60) await campo.fill(prueba.valor, { timeout: 3000 }).catch(() => {});
  }
  await campo.press('Tab', { timeout: 3000 }).catch(() => campo.evaluate((e) => e.blur()));
  await page.waitForTimeout(250);
  const r = await page.evaluate(({ s, antes }) => {
    const el = document.querySelector(s);
    const ahora = [...document.querySelectorAll('[role=alert], [class*=error i], [class*=invalid i], [class*=feedback i], [aria-live]')]
      .filter((x) => { const b = x.getBoundingClientRect(); return b.width > 0 && b.height > 0; }).map((x) => (x.innerText || '').trim()).filter(Boolean);
    const nuevos = ahora.filter((t) => !antes.split('|').includes(t));
    // El mensaje de la app que es de ESTE campo: el que referencia (aria-describedby / aria-errormessage) o el
    // que tiene justo después; si no, uno que apareció recién (no el que dejó otro campo).
    const vis = (x) => { const b = x.getBoundingClientRect(); return b.width > 0 && b.height > 0 && (x.innerText || '').trim(); };
    let propio = '';
    for (const at of ['aria-errormessage', 'aria-describedby']) {
      for (const id of (el.getAttribute(at) || '').split(/\s+/).filter(Boolean)) {
        const x = document.getElementById(id);
        if (x && vis(x) && !propio) propio = x.innerText.trim();
      }
    }
    for (let s = el.nextElementSibling, k = 0; s && k < 2 && !propio; s = s.nextElementSibling, k++) {
      if (/^(LABEL|INPUT|SELECT|TEXTAREA|BUTTON)$/.test(s.tagName)) break;
      if (vis(s) && /error|invalid|feedback|help|alert/i.test(`${s.className} ${s.getAttribute('role') || ''}`)) propio = s.innerText.trim();
    }
    const valido = typeof el.checkValidity === 'function' ? el.checkValidity() : true;
    return { valido, mensaje_navegador: el.validationMessage || '', aria_invalid: el.getAttribute('aria-invalid') === 'true',
      mensaje_app: propio || nuevos[0] || '', valor_final: el.type === 'checkbox' ? String(el.checked) : String(el.value) };
  }, { s: sel, antes });
  const rechaza = !r.valido || r.aria_invalid || Boolean(r.mensaje_app && /obligatori|requerid|inv[aá]lid|error|debe|ingres[aá]|complet[aá]|formato|m[ií]nimo|m[aá]ximo|no (es|puede)/i.test(r.mensaje_app));
  let resultado = rechaza ? 'rechaza' : 'acepta';
  if (prueba.esperado === 'corta' && r.valor_final.length <= (c.maxlength || 0)) resultado = 'corta';
  const ok = prueba.esperado === 'informa' ? null : prueba.esperado === 'corta' ? resultado === 'corta' || resultado === 'rechaza' : resultado === prueba.esperado;
  return { regla: prueba.regla, valor: prueba.valor == null ? '(sin marcar)' : prueba.valor.length > 40 ? `${prueba.valor.slice(0, 20)}… (${prueba.valor.length})` : prueba.valor,
    esperado: prueba.esperado, resultado, ok, mensaje: r.mensaje_app || r.mensaje_navegador || '', fuente: r.mensaje_app ? 'aplicación' : r.mensaje_navegador ? 'navegador' : null };
}

function hallazgosDe(f, c) {
  const h = [];
  const add = (severidad, tipo, titulo, detalle) => h.push({ severidad, tipo, titulo, detalle, formulario: f.id, campo: c ? c.nombre : null });
  if (!c) return h;
  const nombre = c.etiqueta || c.nombre;
  if (!c.fuente_etiqueta) add('Media', 'Etiqueta', `“${nombre}” no tiene etiqueta`, 'Sin etiqueta, el lector de pantalla no sabe qué campo es y la persona tampoco cuando lo completa.');
  else if (c.fuente_etiqueta === 'placeholder') add('Baja', 'Etiqueta', `“${nombre}” usa el placeholder como etiqueta`, 'Desaparece al escribir: usá un label visible.');
  if (c.requerido && !c.marca_obligatorio) add('Media', 'Obligatorio', `“${nombre}” es obligatorio y no lo indica`, 'Marcá los obligatorios (asterisco con su explicación o "obligatorio").');
  const pista = `${c.nombre} ${c.etiqueta} ${c.placeholder || ''}`.toLowerCase();
  if (c.tipo === 'text' && /e-?mail|correo/.test(pista)) add('Media', 'Tipo de campo', `“${nombre}” pide un email pero es un campo de texto`, 'Con type="email" el celular muestra el teclado con @ y el navegador valida el formato.');
  if (['text', 'email', 'tel'].includes(c.tipo) && /nombre|name|e-?mail|correo|tel[eé]fono|celular|direcci[oó]n|address/.test(pista) && !c.autocomplete) {
    add('Baja', 'Autocompletar', `“${nombre}” no tiene autocomplete`, 'Con autocomplete (name, email, tel, street-address) el navegador lo completa solo.');
  }
  if (c.tipo === 'password' && !c.minlength && !c.reglas_visibles) add('Baja', 'Contraseña', 'La contraseña no muestra sus reglas', 'Decí antes de escribir cuántos caracteres y qué tiene que tener.');
  for (const p of c.pruebas) {
    if (p.ok === false && p.esperado === 'rechaza') {
      const grave = /Obligatorio|Email/.test(p.regla);
      add(grave ? 'Alta' : 'Media', 'Acepta un valor inválido', `“${nombre}” acepta: ${p.regla}`, `Valor probado: “${p.valor}”. Lo tendría que rechazar con un mensaje claro.`);
    } else if (p.ok === false && p.esperado === 'acepta') {
      add('Alta', 'Rechaza un valor válido', `“${nombre}” rechaza: ${p.regla}`, `Valor probado: “${p.valor}”${p.mensaje ? `; mensaje: “${p.mensaje}”` : ''}. Le impide completar el formulario a personas reales.`);
    } else if (p.ok === false && p.esperado === 'corta') {
      add('Media', 'Largo máximo', `“${nombre}” deja escribir más de ${c.maxlength} caracteres`, 'El largo máximo no se respeta.');
    } else if (p.ok && p.esperado === 'rechaza' && p.fuente === 'navegador') {
      add('Baja', 'Mensaje de error', `“${nombre}”: el mensaje de “${p.regla}” lo pone el navegador`, `Mensaje: “${p.mensaje}”. Es genérico y sale en el idioma del navegador: mostrá uno propio junto al campo.`);
    }
    if (p.regla.startsWith('Texto muy largo') && p.resultado === 'acepta') add('Baja', 'Largo máximo', `“${nombre}” no tiene largo máximo`, 'Acepta 300 caracteres o más: definí un máximo acorde a lo que guarda la base.');
  }
  return h;
}

function generarInforme(carpeta) {
  const py = process.platform === 'win32' ? 'python' : 'python3';
  const r = require('child_process').spawnSync(py, [path.join(CODIGO, 'scripts', 'generar_informe_formularios.py'), path.join(carpeta, 'formularios.json'),
    path.join(carpeta, 'informe-formularios.html')], { encoding: 'utf8' });
  if (r.status !== 0) {
    const motivo = (r.stderr || r.error || '').toString().trim().split(/\r?\n/).pop();
    console.log(`No pude generar el informe HTML (${motivo}). Generalo con: python scripts/generar_informe_formularios.py <carpeta>/formularios.json <carpeta>/informe-formularios.html`);
    return false;
  }
  return true;
}

async function capturaForm(page, f, archivo) {
  const cajas = [];
  for (const c of f.campos) {
    const b = await page.locator(`[data-k0-campo="${c.n}"]`).first().boundingBox().catch(() => null);
    if (b) cajas.push({ x: b.x, y: b.y, w: b.width, h: b.height });
  }
  if (!cajas.length) return false;
  const vp = page.viewportSize();
  const alto = await page.evaluate(() => document.documentElement.scrollHeight);
  const v = visual.ventanaDe(cajas, 90, 360, 200);
  await page.screenshot({ path: archivo, fullPage: true, clip: { x: v.x, y: v.y, width: Math.min(v.w, vp.width - v.x), height: Math.min(v.h, alto - v.y, 2400) } }).catch(() => {});
  return fs.existsSync(archivo);
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
  const carpeta = a.salida ? desde(a.salida) : path.join(RAIZ, 'output', 'formularios', a.historia || host);
  archivar(carpeta, GENERADOS, 'formularios.json');
  for (const n of GENERADOS) fs.rmSync(path.join(carpeta, n), { recursive: true, force: true });
  const dirCap = path.join(carpeta, 'capturas');
  fs.mkdirSync(dirCap, { recursive: true });
  const rel = (p) => path.relative(carpeta, p).split(path.sep).join('/');
  const relRaiz = (p) => path.relative(RAIZ, p).split(path.sep).join('/');
  const { chromium } = require('playwright');
  const browser = await navegadorComun.lanzar(chromium, { headless: !a.headed });
  const t0 = Date.now();
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, locale: process.env.LOCALE || 'es-AR' });
  const page = await ctx.newPage();
  // Nunca se envía nada (salvo --enviar-vacio): cualquier navegación por envío se corta.
  let enviar = false;
  await page.route('**/*', (route) => {
    const rq = route.request();
    if (!enviar && rq.isNavigationRequest() && rq.method() !== 'GET') return route.abort();
    return route.continue();
  });
  const paginas = await descubrir(page, inicio, a);
  console.log(`Formularios: ${paginas.length} página(s) · salida ${relRaiz(carpeta)}`);
  const formularios = [];
  let hallazgos = [];
  for (const [i, u] of paginas.entries()) {
    await cargar(page, u).catch(() => {});
    const fs0 = await page.evaluate(_formularios).catch(() => []);
    process.stdout.write(`[${i + 1}/${paginas.length}] ${u} → ${fs0.length} formulario(s)\n`);
    for (const f of fs0) {
      f.id = `F-${String(formularios.length + 1).padStart(2, '0')}`;
      f.url = u;
      f.pagina = `${String(i + 1).padStart(2, '0')}-${slug(u)}`;
      const antes = path.join(dirCap, `${f.id}-antes.png`);
      if (await capturaForm(page, f, antes)) f.captura = rel(antes);
      for (const c of f.campos) {
        c.pruebas = [];
        for (const pr of pruebasPara(c)) c.pruebas.push(await probar(page, c, pr));
        process.stdout.write(`    ${String(c.etiqueta || c.nombre).slice(0, 30).padEnd(30)} ${c.tipo.padEnd(9)} ${c.pruebas.filter((p) => p.ok === false).length}/${c.pruebas.length} fallan\n`);
      }
      // Estado con errores: cada campo con su primer valor inválido, para ver todos los mensajes juntos.
      for (const c of f.campos) {
        const inval = pruebasPara(c).find((p) => p.esperado === 'rechaza');
        if (inval) await probar(page, c, inval).catch(() => {});
      }
      const errores = path.join(dirCap, `${f.id}-errores.png`);
      if (await capturaForm(page, f, errores)) f.captura_errores = rel(errores);
      if (a.enviarVacio && f.boton) {
        await cargar(page, u).catch(() => {});
        await page.evaluate(_formularios).catch(() => []);
        enviar = true;
        await botonEnvio(page, f).click({ timeout: 5000 }).catch(() => {});
        await page.waitForTimeout(1200);
        enviar = false;
        const env = path.join(dirCap, `${f.id}-envio-vacio.png`);
        await page.screenshot({ path: env, fullPage: true }).catch(() => {});
        if (fs.existsSync(env)) f.captura_envio_vacio = rel(env);
        f.url_despues_de_enviar = page.url();
      }
      f.hallazgos = f.campos.flatMap((c) => hallazgosDe(f, c));
      if (!f.boton && f.nombre !== 'campos sin formulario') f.hallazgos.push({ severidad: 'Baja', tipo: 'Envío', titulo: 'El formulario no tiene un botón de enviar', detalle: 'Sin botón, no queda claro cómo se envía (ni con Enter).', formulario: f.id, campo: null });
      hallazgos.push(...f.hallazgos.map((h) => ({ ...h, url: u, captura: f.captura_errores || f.captura })));
      formularios.push(f);
      await cargar(page, u).catch(() => {});
      await page.evaluate(_formularios).catch(() => []);
    }
  }
  await browser.close();
  hallazgos.sort((x, y) => SEV_ORDEN[x.severidad] - SEV_ORDEN[y.severidad]);
  hallazgos.forEach((h, i) => { h.id = `V-${String(i + 1).padStart(2, '0')}`; });
  const pruebas = formularios.flatMap((f) => f.campos.flatMap((c) => c.pruebas));
  const resultado = {
    url: inicio, host, historia: a.historia || null, fecha: new Date().toISOString(), marca: sello(), duracion_s: Math.round((Date.now() - t0) / 1000),
    herramienta: `Playwright ${require('playwright/package.json').version}`, envio_vacio: a.enviarVacio,
    resumen: { paginas: paginas.length, formularios: formularios.length, campos: formularios.reduce((s, f) => s + f.campos.length, 0), pruebas: pruebas.length,
      pruebas_ok: pruebas.filter((p) => p.ok === true).length, pruebas_fallan: pruebas.filter((p) => p.ok === false).length, hallazgos: hallazgos.length,
      acepta_invalidos: hallazgos.filter((h) => h.tipo === 'Acepta un valor inválido').length, rechaza_validos: hallazgos.filter((h) => h.tipo === 'Rechaza un valor válido').length,
      por_severidad: Object.fromEntries(['Crítica', 'Alta', 'Media', 'Baja'].map((s) => [s, hallazgos.filter((h) => h.severidad === s).length])) },
    hallazgos, formularios,
  };
  const salida = path.join(carpeta, 'formularios.json');
  fs.writeFileSync(salida, JSON.stringify(resultado, null, 2), 'utf8');
  const r = resultado.resumen;
  console.log(`\nFormularios: ${r.formularios} · campos: ${r.campos} · pruebas: ${r.pruebas} (${r.pruebas_fallan} fallan) · hallazgos: ${r.hallazgos}`);
  console.log(`Datos: ${relRaiz(salida)}`);
  if (generarInforme(carpeta)) console.log(`Informe: ${relRaiz(path.join(carpeta, 'informe-formularios.html'))}`);
}

if (require.main === module) {
  main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
}

// extraerFormularios lo reutiliza el mapa funcional (tools/mapa-funcional) del documentador-proyecto.
module.exports = { argumentos, pruebasPara, hallazgosDe, botonEnvio, GENERADOS, extraerFormularios: _formularios };

// tools/correos/correos.steps.ts
//
// Steps de correo para cualquier suite (web y api), contra el buzón de prueba Mailpit (MAILPIT_URL del .env).
// La app del ambiente de pruebas tiene que mandar sus mails por SMTP a Mailpit (ver herramientas/mailpit/README.md).
//
//   Given el buzón de prueba está vacío
//   Then llega un correo a "ana@test.com" con el asunto "Confirmá tu cuenta"
//   Then el correo contiene "Hola Ana"
//   Then el correo no contiene "undefined"
//   Then el correo tiene el adjunto "factura.pdf"
//   When guardo el link del correo que contiene "/confirmar" como "linkConfirmacion"
//
// "llega un correo" espera hasta CORREO_TIMEOUT_S segundos (30 por defecto). El link guardado se usa
// después como {linkConfirmacion} en otros steps (ver tools/variables.ts).
import { Given, Then, When } from '@cucumber/cucumber';
import { interpolar, variables } from '../variables';

const base = () => (process.env.MAILPIT_URL || 'http://localhost:8025').replace(/\/+$/, '');

function cabeceras(): Record<string, string> {
  const h: Record<string, string> = { Accept: 'application/json' };
  if (process.env.MAILPIT_USUARIO) {
    h.Authorization = `Basic ${Buffer.from(`${process.env.MAILPIT_USUARIO}:${process.env.MAILPIT_CLAVE || ''}`).toString('base64')}`;
  }
  return h;
}

async function api(ruta: string, opciones: { metodo?: string; cuerpo?: unknown } = {}): Promise<any> {
  const r = await fetch(`${base()}${ruta}`, {
    method: opciones.metodo || 'GET',
    headers: { ...cabeceras(), ...(opciones.cuerpo ? { 'Content-Type': 'application/json' } : {}) },
    body: opciones.cuerpo ? JSON.stringify(opciones.cuerpo) : undefined,
  }).catch((e) => {
    throw new Error(`No pude conectarme a Mailpit en ${base()} (${e.message}). ¿Está corriendo? Ver herramientas/mailpit/README.md`);
  });
  if (!r.ok) throw new Error(`Mailpit respondió ${r.status} en ${ruta}`);
  const tipo = r.headers.get('content-type') || '';
  return tipo.includes('json') ? r.json() : r.text();
}

const texto = (m: any) => `${m.Subject || ''}\n${m.Text || ''}\n${String(m.HTML || '').replace(/<[^>]+>/g, ' ')}`.replace(/\s+/g, ' ');

function ultimo(): any {
  const m = variables.__correo;
  if (!m) throw new Error('Primero usá "llega un correo a ... con el asunto ...": no hay un correo elegido.');
  return m;
}

Given('el buzón de prueba está vacío', async function () {
  await api('/api/v1/messages', { metodo: 'DELETE', cuerpo: {} });
});

Then('llega un correo a {string} con el asunto {string}', async function (para: string, asunto: string) {
  const destino = interpolar(para);
  const tema = interpolar(asunto);
  const limite = Date.now() + Number(process.env.CORREO_TIMEOUT_S || 30) * 1000;
  const query = encodeURIComponent(`to:"${destino}" subject:"${tema}"`);
  while (Date.now() < limite) {
    const r = await api(`/api/v1/search?query=${query}&limit=5`);
    const m = (r.messages || [])[0];
    if (m) {
      variables.__correo = await api(`/api/v1/message/${m.ID}`);
      if (typeof (this as any)?.attach === 'function') {
        await (this as any).attach(`CORREO: ${m.Subject}\n- Para: ${destino}\n- Ver: ${base()}/view/${m.ID}`, 'text/plain');
      }
      return;
    }
    await new Promise((res) => setTimeout(res, 1500));
  }
  throw new Error(`No llegó ningún correo a ${destino} con el asunto "${tema}" en ${process.env.CORREO_TIMEOUT_S || 30} s.`);
});

Then('el correo contiene {string}', function (t: string) {
  const buscado = interpolar(t);
  if (!texto(ultimo()).toLowerCase().includes(buscado.toLowerCase())) throw new Error(`El correo no contiene "${buscado}".`);
});

Then('el correo no contiene {string}', function (t: string) {
  const buscado = interpolar(t);
  if (texto(ultimo()).toLowerCase().includes(buscado.toLowerCase())) throw new Error(`El correo contiene "${buscado}" y no debería.`);
});

Then('el correo tiene el adjunto {string}', function (nombre: string) {
  const adjuntos = (ultimo().Attachments || []).map((a: any) => String(a.FileName || ''));
  if (!adjuntos.some((a: string) => a.toLowerCase().includes(interpolar(nombre).toLowerCase()))) {
    throw new Error(`El correo no tiene el adjunto "${nombre}" (tiene: ${adjuntos.join(', ') || 'ninguno'}).`);
  }
});

When('guardo el link del correo que contiene {string} como {string}', function (fragmento: string, nombre: string) {
  const m = ultimo();
  const links = [...String(m.HTML || '').matchAll(/href\s*=\s*["']([^"']+)["']/gi)].map((x) => x[1].replace(/&amp;/g, '&'))
    .concat([...String(m.Text || '').matchAll(/https?:\/\/[^\s<>"')]+/g)].map((x) => x[0]));
  const link = links.find((l) => l.includes(interpolar(fragmento)));
  if (!link) throw new Error(`El correo no tiene un link que contenga "${fragmento}".`);
  variables[nombre] = link;
});

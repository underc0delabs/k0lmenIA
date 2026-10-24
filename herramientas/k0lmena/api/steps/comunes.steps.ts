// api/steps/comunes.steps.ts
//
// Steps genéricos de API en español. El agente api-mapper arma los .feature
// usando SOLO estos steps, así no hace falta escribir código por cada endpoint.
//
// URL: API_BASEURL del .env es el server de la spec CON su basePath (ej. https://petstore.swagger.io/v2)
// y los endpoints del .feature son los paths de la spec tal cual ("/pet/{petId}"). Se unen con una
// sola barra; una URL completa en el endpoint se usa como está.
//
// Variables en endpoints, parámetros, headers y bodies: {nombre}
//   - se reemplaza por un valor guardado con "guardo el campo ... como ..."
//   - o por un dato generado para el escenario: {uuid}, {aleatorio}, {timestamp}, {ahora}
//   - o, si no existe, por la variable de entorno del mismo nombre (.env)
//   Una variable que queda sin valor en el endpoint o el body corta el escenario con un mensaje
//   claro (antes se mandaba "{petId}" literal y la API respondía 404).
//
// Autenticación, según el securityScheme de la spec:
//   Bearer (http bearer / JWT)      → el request usa el token de autenticación         (API_TOKEN)
//   apiKey en un header             → el request usa la API key en el header "api_key"  (API_KEY o API_TOKEN)
//   apiKey en la query              → el request usa la API key en el parámetro "key"   (API_KEY o API_TOKEN)
//   http basic                      → el request usa autenticación básica               (API_USER / API_PASSWORD)
//
// Respuestas: el JSON se lee con los enteros grandes (ids int64) como texto, para no perder
// precisión; una respuesta que no es JSON queda como texto.
//
// GraphQL: "envío la consulta GraphQL:" manda {query, variables} por POST al endpoint GraphQL
// (el de "el endpoint GraphQL es ...", o GRAPHQL_URL del .env, o API_BASEURL + /graphql). La query
// va tal cual (sus llaves no se interpolan): los valores dinámicos van en las variables GraphQL,
// que sí aceptan {nombre}.
import '../../env'; // .env único de la raíz de k0lmenIA
import { Given, When, Then, Before, After, DataTable } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import axios, { AxiosResponse, Method } from 'axios';
import { variables, interpolar } from '../../tools/variables';
const http = require('../../tools/api/http');

type Cuerpo = { tipo: 'json'; datos: unknown } | { tipo: 'form'; datos: Record<string, string> };
type Estado = {
  headers: Record<string, string>;
  params: Record<string, string>;
  graphql: { endpoint?: string; variables?: Record<string, unknown> };
  request?: { metodo: string; url: string; params?: Record<string, string>; body?: unknown };
  response?: AxiosResponse;
  ms?: number;
};

let estado: Estado;

Before(() => {
  estado = { headers: {}, params: {}, graphql: {} };
});

const TIMEOUT_MS = Number(process.env.API_TIMEOUT_MS) || 30000;

// Lee un campo con notación de puntos: "data.items.0.id"
const leerCampo = (obj: unknown, ruta: string): unknown =>
  ruta.split('.').reduce<any>((acc, k) => (acc == null ? undefined : acc[k]), obj);

const respuesta = (): AxiosResponse => {
  if (!estado.response) throw new Error('Todavía no se envió ningún request en este escenario.');
  return estado.response;
};

const textoDe = (data: unknown): string => (typeof data === 'string' ? data : JSON.stringify(data) ?? '');

const tieneHeader = (headers: Record<string, string>, nombre: string) =>
  Object.keys(headers).some((k) => k.toLowerCase() === nombre.toLowerCase());

const sinVariablesPendientes = (texto: string, donde: string) => {
  const faltan: string[] = http.variablesSinValor(texto);
  if (faltan.length) {
    throw new Error(`${donde} tiene variables sin valor: ${faltan.map((v) => `{${v}}`).join(', ')}. ` +
      'Guardalas antes con "guardo el campo ... de la respuesta como ..." (en este mismo escenario) o definilas en el .env.');
  }
};

// Filas de una tabla nombre | valor (con o sin la fila de encabezado "nombre | valor").
const filas = (tabla: DataTable): Record<string, string> => {
  const raw = tabla.raw();
  const sinEncabezado = raw.length && /^(nombre|campo|parámetro|parametro|clave)$/i.test(raw[0][0]?.trim() ?? '') ? raw.slice(1) : raw;
  const salida: Record<string, string> = {};
  for (const [k, v] of sinEncabezado) salida[k.trim()] = interpolar(v ?? '');
  return salida;
};

const enviar = async (metodo: string, endpoint: string, cuerpo?: Cuerpo) => {
  const ruta = interpolar(endpoint);
  sinVariablesPendientes(ruta, `El endpoint "${ruta}"`);
  const url: string = http.unirUrl(process.env.API_BASEURL, ruta);
  const headers = { ...estado.headers };
  let data: unknown;
  if (cuerpo?.tipo === 'json') {
    data = cuerpo.datos;
    if (!tieneHeader(headers, 'Content-Type')) headers['Content-Type'] = 'application/json';
  } else if (cuerpo?.tipo === 'form') {
    data = new URLSearchParams(cuerpo.datos).toString();
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
  }
  const params = { ...estado.params };
  const inicio = Date.now();
  estado.request = { metodo: metodo.toUpperCase(), url, params, body: cuerpo?.datos };
  estado.response = await axios.request({
    method: metodo.toUpperCase() as Method,
    url,
    headers,
    params,
    data,
    timeout: TIMEOUT_MS,
    responseType: 'text',
    transformResponse: [(d: string) => http.parsearRespuesta(d)],
    validateStatus: () => true, // los 4xx/5xx se validan en los Then, no tiran excepción
  });
  estado.ms = Date.now() - inicio;
};

const bodyJson = (texto: string) => {
  const t = interpolar(texto);
  sinVariablesPendientes(t, 'El body');
  return http.parsearJson(t, 'El body');
};

// GraphQL: POST con {query, variables, operationName} al endpoint GraphQL.
const urlGraphQL = (): string =>
  http.unirUrl(process.env.API_BASEURL, interpolar(estado.graphql.endpoint ?? process.env.GRAPHQL_URL ?? '/graphql'));

const enviarGraphQL = async (query: string) => {
  const url = urlGraphQL();
  const operacion = /^\s*(?:query|mutation|subscription)\s+([A-Za-z_]\w*)/.exec(query)?.[1];
  const body = { query, variables: estado.graphql.variables ?? {}, ...(operacion ? { operationName: operacion } : {}) };
  const inicio = Date.now();
  estado.request = { metodo: 'POST', url, body };
  estado.response = await axios.request({
    method: 'POST', url, headers: { 'Content-Type': 'application/json', ...estado.headers }, params: { ...estado.params }, data: body,
    timeout: TIMEOUT_MS,
    responseType: 'text',
    transformResponse: [(d: string) => http.parsearRespuesta(d)],
    validateStatus: () => true,
  });
  estado.ms = Date.now() - inicio;
};

const erroresGraphQL = (): Array<{ message?: string; extensions?: Record<string, unknown> }> => {
  const errores = respuesta().data?.errors;
  return Array.isArray(errores) ? errores : [];
};

// Evidencia de cada escenario (pase o falle): último request y su response.
// Las credenciales (Authorization, API keys, cookies) se ocultan para no filtrarlas en el reporte.
After(function () {
  if (!estado?.request) return;
  const res = estado.response;
  const cuerpo = typeof res?.data === 'string' ? res.data : JSON.stringify(res?.data, null, 2) ?? '';
  const params = estado.request.params && Object.keys(estado.request.params).length
    ? `Parámetros: ${JSON.stringify(http.ocultarParametros(estado.request.params))}` : '';
  this.attach(
    [
      `REQUEST\n${estado.request.metodo} ${estado.request.url}`,
      params,
      `Headers: ${JSON.stringify(http.ocultarHeaders(estado.headers))}`,
      estado.request.body !== undefined ? `Body:\n${JSON.stringify(estado.request.body, null, 2)}` : '',
      `\nRESPONSE (${estado.ms} ms)\nStatus: ${res?.status} ${res?.statusText ?? ''}`,
      `Headers: ${JSON.stringify(http.ocultarHeaders(res?.headers ?? {}))}`,
      `Body:\n${cuerpo.length > 20000 ? cuerpo.slice(0, 20000) + '\n... (recortado)' : cuerpo}`,
    ].filter(Boolean).join('\n'),
    'text/plain'
  );
});

/* ---------- Given ---------- */

Given('el request usa el header {string} con valor {string}', (nombre: string, valor: string) => {
  estado.headers[nombre] = interpolar(valor);
});

Given('el request usa el token de autenticación', () => {
  const token = process.env.API_TOKEN;
  if (!token) throw new Error('Falta API_TOKEN en el .env de la raíz de k0lmenIA.');
  estado.headers.Authorization = `Bearer ${token}`;
});

const apiKey = (): string => {
  const clave = process.env.API_KEY || process.env.API_TOKEN;
  if (!clave) throw new Error('Falta API_KEY (o API_TOKEN) en el .env de la raíz de k0lmenIA.');
  return clave;
};

Given('el request usa la API key en el header {string}', (nombre: string) => {
  estado.headers[nombre] = apiKey();
});

Given('el request usa la API key en el parámetro {string}', (nombre: string) => {
  estado.params[nombre] = apiKey();
});

Given('el request usa autenticación básica', () => {
  const usuario = process.env.API_USER;
  const clave = process.env.API_PASSWORD;
  if (!usuario || clave === undefined) throw new Error('Faltan API_USER y API_PASSWORD en el .env de la raíz de k0lmenIA.');
  estado.headers.Authorization = `Basic ${Buffer.from(`${usuario}:${clave}`).toString('base64')}`;
});

Given('el request no envía token de autenticación', () => {
  // Sin ninguna credencial: ni Authorization ni API keys en headers o parámetros.
  for (const k of Object.keys(estado.headers)) if (/^authorization$|api[-_]?key|token/i.test(k)) delete estado.headers[k];
  for (const k of Object.keys(estado.params)) if (/api[-_]?key|token/i.test(k)) delete estado.params[k];
});

Given('el request tiene los parámetros:', (tabla: DataTable) => {
  // Parámetros de query (nombre | valor); se codifican solos (espacios, acentos, &).
  Object.assign(estado.params, filas(tabla));
});

Given('el endpoint GraphQL es {string}', (endpoint: string) => {
  estado.graphql.endpoint = endpoint;
});

Given('las variables GraphQL son:', (json: string) => {
  estado.graphql.variables = http.parsearJson(interpolar(json), 'Las variables GraphQL');
});

/* ---------- When ---------- */

When('envío un {word} a {string}', async (metodo: string, endpoint: string) => {
  await enviar(metodo, endpoint);
});

When('envío un {word} a {string} con el body:', async (metodo: string, endpoint: string, body: string) => {
  await enviar(metodo, endpoint, { tipo: 'json', datos: bodyJson(body) });
});

When('envío un {word} a {string} con el formulario:', async (metodo: string, endpoint: string, tabla: DataTable) => {
  // application/x-www-form-urlencoded (nombre | valor), para los endpoints que en la spec consumen formData.
  await enviar(metodo, endpoint, { tipo: 'form', datos: filas(tabla) });
});

When('envío la consulta GraphQL:', async (query: string) => {
  await enviarGraphQL(query);
});

When('guardo el campo {string} de la respuesta como {string}', (campo: string, nombre: string) => {
  const valor = leerCampo(respuesta().data, campo);
  if (valor === undefined) {
    throw new Error(`La respuesta no tiene el campo "${campo}" para guardarlo como "${nombre}". Respuesta: ${textoDe(respuesta().data).slice(0, 500)}`);
  }
  variables[nombre] = valor;
});

/* ---------- Then ---------- */

Then('el status de la respuesta es {int}', (status: number) => {
  expect(respuesta().status, textoDe(respuesta().data).slice(0, 500)).toBe(status);
});

Then('la respuesta contiene el campo {string}', (campo: string) => {
  expect(leerCampo(respuesta().data, campo), `Falta el campo "${campo}"`).not.toBeUndefined();
});

Then('la respuesta no contiene el campo {string}', (campo: string) => {
  expect(leerCampo(respuesta().data, campo)).toBeUndefined();
});

Then('el campo {string} de la respuesta es {string}', (campo: string, valor: string) => {
  expect(String(leerCampo(respuesta().data, campo))).toBe(interpolar(valor));
});

Then('el campo {string} de la respuesta es el número {float}', (campo: string, valor: number) => {
  expect(Number(leerCampo(respuesta().data, campo))).toBe(valor);
});

Then('el campo {string} de la respuesta es de tipo {string}', (campo: string, tipo: string) => {
  // Acepta los tipos de la spec: integer, number, string, boolean, array, object, null (o en español).
  const v = leerCampo(respuesta().data, campo);
  const { ok, real } = http.tipoDe(v, tipo);
  expect(ok, `El campo "${campo}" es ${real}, no ${tipo}`).toBe(true);
});

Then('la respuesta es una lista', () => {
  expect(Array.isArray(respuesta().data)).toBe(true);
});

Then('la respuesta es una lista con al menos {int} elemento(s)', (min: number) => {
  expect(Array.isArray(respuesta().data)).toBe(true);
  expect(respuesta().data.length).toBeGreaterThanOrEqual(min);
});

const tieneElemento = (lista: unknown, campo: string, valor: string, donde: string) => {
  expect(Array.isArray(lista), `${donde} no es una lista`).toBe(true);
  const buscado = interpolar(valor);
  const hay = (lista as unknown[]).some((x) => String(leerCampo(x, campo)) === buscado);
  expect(hay, `${donde} no tiene ningún elemento con "${campo}" = "${buscado}"`).toBe(true);
};

Then('la respuesta tiene un elemento con {string} igual a {string}', (campo: string, valor: string) => {
  tieneElemento(respuesta().data, campo, valor, 'La respuesta');
});

Then('la lista {string} de la respuesta tiene un elemento con {string} igual a {string}', (lista: string, campo: string, valor: string) => {
  tieneElemento(leerCampo(respuesta().data, lista), campo, valor, `"${lista}"`);
});

Then('la respuesta tiene los campos:', (tabla: DataTable) => {
  // Tabla de una columna con las rutas de los campos obligatorios.
  for (const [campo] of tabla.raw()) {
    expect(leerCampo(respuesta().data, campo), `Falta el campo "${campo}"`).not.toBeUndefined();
  }
});

Then('la respuesta contiene el texto {string}', (texto: string) => {
  expect(textoDe(respuesta().data)).toContain(interpolar(texto));
});

Then('el header {string} de la respuesta contiene {string}', (nombre: string, valor: string) => {
  expect(String(respuesta().headers[nombre.toLowerCase()] ?? '')).toContain(valor);
});

Then('la respuesta llega en menos de {int} ms', (max: number) => {
  expect(estado.ms ?? Infinity).toBeLessThan(max);
});

/* ---------- Then de GraphQL (los campos se leen dentro de "data") ---------- */

Then('la respuesta GraphQL no tiene errores', () => {
  expect(erroresGraphQL().map((e) => e.message), 'La respuesta GraphQL trae errores').toEqual([]);
});

Then('la respuesta GraphQL tiene un error con el mensaje {string}', (mensaje: string) => {
  const mensajes = erroresGraphQL().map((e) => String(e.message ?? ''));
  expect(mensajes.some((m) => m.includes(interpolar(mensaje))), `Errores: ${JSON.stringify(mensajes)}`).toBe(true);
});

Then('la respuesta GraphQL tiene un error con el código {string}', (codigo: string) => {
  const codigos = erroresGraphQL().map((e) => String(e.extensions?.code ?? ''));
  expect(codigos, `Errores: ${JSON.stringify(erroresGraphQL())}`).toContain(codigo);
});

Then('la respuesta GraphQL contiene el campo {string}', (campo: string) => {
  expect(leerCampo(respuesta().data?.data, campo), `Falta data.${campo}`).not.toBeUndefined();
});

Then('el campo GraphQL {string} es {string}', (campo: string, valor: string) => {
  expect(String(leerCampo(respuesta().data?.data, campo))).toBe(interpolar(valor));
});

Then('el campo GraphQL {string} es el número {float}', (campo: string, valor: number) => {
  expect(Number(leerCampo(respuesta().data?.data, campo))).toBe(valor);
});

Then('el campo GraphQL {string} es nulo', (campo: string) => {
  expect(leerCampo(respuesta().data?.data, campo)).toBeNull();
});

Then('el campo GraphQL {string} es una lista con al menos {int} elemento(s)', (campo: string, min: number) => {
  const v = leerCampo(respuesta().data?.data, campo);
  expect(Array.isArray(v), `data.${campo} no es una lista`).toBe(true);
  expect((v as unknown[]).length).toBeGreaterThanOrEqual(min);
});

When('guardo el campo GraphQL {string} como {string}', (campo: string, nombre: string) => {
  variables[nombre] = leerCampo(respuesta().data?.data, campo);
});

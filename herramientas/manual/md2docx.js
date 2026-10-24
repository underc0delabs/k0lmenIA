// Convierte un borrador o versión de un manual de usuario (Markdown) a .docx con el diseño de k0lmena:
// portada oscura (noche + ámbar, logo k0), títulos en Saira, texto en Inter, etiquetas en JetBrains Mono,
// tablas con encabezado oscuro, avisos con borde ámbar e interior claro para que se pueda imprimir.
// Lo llama `python herramientas/manual/manual.py word <md>`, que instala docx e image-size en herramientas/manual/.deps
// y pasa las fuentes de la casa convertidas a TTF (MANUAL_FUENTES) para embeberlas en el documento.
// Uso directo: NODE_PATH=<.deps/node_modules> node md2docx.js <entrada.md> <salida.docx> ["Texto de estado"]
// Variables de entorno: MANUAL_EQUIPO (quién firma, opcional) y MANUAL_FUENTES ({"Saira": "ruta.ttf", ...}).
// Soporta: # título, ## / ### secciones, párrafos, **negrita**, `código`, \* escapado, viñetas anidadas,
// listas numeradas, tablas, imágenes ![alt](ruta), citas (> ⚠️ QA REVIEW …) y bloques de código ```.
const fs = require('fs');
const path = require('path');
const sizeOf = require('image-size');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, ImageRun, AlignmentType, LevelFormat, Footer, Header, PageNumber, TabStopType, VerticalAlign,
  HeightRule, CharacterSet,
} = require('docx');

const [, , mdPath, outPath, STATUS_ARG] = process.argv;
const EQUIPO = (process.env.MANUAL_EQUIPO || '').trim();
const baseDir = path.dirname(path.resolve(mdPath));
const lines = fs.readFileSync(mdPath, 'utf8').split(/\r?\n/);
const VER = (path.basename(mdPath).match(/-(v\d+\.\d+)\.md$/) || [, ''])[1];
const IS_DRAFT = !/^v[1-9]\d*\./.test(VER) && !/[\\/]versiones[\\/]/.test(path.resolve(mdPath));

// Tokens de k0lmena (los mismos de scripts/_estilos_reporte.py)
const C = {
  noche: '0E0C09', carbon: '1A1712', tile: '221E17', linea: '2E281F',
  ink: 'F4EFE6', body: 'CFC7B8', muted: '8A8172', ambar: 'F9B006', ambarOsc: 'C98500',
  ok: '5CBF4A', serio: 'FF8A00',
  // interior claro (papel)
  texto: '2B261E', titulo: '1A1712', borde: 'E4DCCB', zebra: 'FAF7F1', nota: 'FBF6EA', review: 'FFF1E0',
  reviewTxt: 'A65300', codigo: 'F1EBDF',
};
const F = { display: 'Saira', sans: 'Inter', mono: 'JetBrains Mono' };
const PAGE_W = 11906, PAGE_H = 16838, MARGIN = 1134, CONTENT_W = PAGE_W - 2 * MARGIN; // A4, márgenes 2 cm
const STAR = ''; // marcador para que el asterisco escapado no se confunda con la negrita

function runs(text, opts = {}) {
  text = text.replace(/\\\*/g, STAR);
  const star = s => s.split(STAR).join('*');
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: star(text.slice(last, m.index)), ...opts }));
    const t = m[0];
    if (t.startsWith('**')) out.push(new TextRun({ ...opts, text: star(t.slice(2, -2)), bold: true, color: opts.color || C.titulo }));
    else out.push(new TextRun({ text: star(t.slice(1, -1)), font: F.mono, size: 18, color: C.titulo, shading: { type: ShadingType.CLEAR, fill: C.codigo, color: 'auto' } }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: star(text.slice(last)), ...opts }));
  return out;
}

const caja = color => { const b = { style: BorderStyle.SINGLE, size: 4, color }; return { top: b, bottom: b, left: b, right: b }; };
const sinBordes = () => { const b = { style: BorderStyle.NONE, size: 0, color: 'auto' }; return { top: b, bottom: b, left: b, right: b, insideHorizontal: b, insideVertical: b }; };

function image(rel, alt) {
  const ruta = path.resolve(baseDir, rel);
  if (!fs.existsSync(ruta)) {
    console.error(`Aviso: no existe la imagen ${rel}`);
    return [new Paragraph({ children: [new TextRun({ text: `[Falta la imagen ${rel}]`, color: 'C0392B', italics: true })] })];
  }
  const buf = fs.readFileSync(ruta);
  const { width, height } = sizeOf(buf);
  const w = Math.min(600, width), h = Math.round(height * (w / width));
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 40 }, keepNext: true,
      border: caja(C.borde),
      children: [new ImageRun({ type: /\.jpe?g$/i.test(rel) ? 'jpg' : 'png', data: buf, transformation: { width: w, height: h },
        altText: { title: alt, description: alt, name: alt } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 220 },
      children: [new TextRun({ text: alt.toLowerCase(), font: F.mono, size: 15, color: C.muted })] }),
  ];
}

function table(rows) {
  const cells = rows.filter(r => !/^\|[\s:|-]+\|$/.test(r.trim())).map(r => r.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim()));
  const n = cells[0].length;
  const widths = n === 2 ? [Math.round(CONTENT_W * 0.32), 0] : n === 3 ? [2000, 3000, 0] : Array(n).fill(Math.floor(CONTENT_W / n));
  widths[n - 1] = CONTENT_W - widths.slice(0, -1).reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths,
    rows: cells.map((row, i) => new TableRow({
      tableHeader: i === 0,
      children: row.map((c, j) => new TableCell({
        width: { size: widths[j], type: WidthType.DXA }, borders: caja(i === 0 ? C.carbon : C.borde),
        shading: { type: ShadingType.CLEAR, fill: i === 0 ? C.carbon : (i % 2 === 0 ? C.zebra : 'FFFFFF'), color: 'auto' },
        margins: { top: 80, bottom: 80, left: 140, right: 140 },
        children: [new Paragraph({ children: i === 0
          ? [new TextRun({ text: c.replace(/\*\*/g, '').toLowerCase(), font: F.mono, size: 16, color: C.ambar })]
          : runs(c, { size: 19 }) })],
      })),
    })),
  });
}

function quote(block) {
  const isReview = /QA REVIEW/.test(block[0]);
  const side = { style: BorderStyle.SINGLE, size: 24, color: isReview ? C.serio : C.ambar, space: 10 };
  const paras = [];
  for (const raw of block) {
    const t = raw.replace(/^>\s?/, '');
    if (!t.trim()) continue;
    const bullet = /^- /.test(t);
    const text = bullet ? t.slice(2) : t;
    const label = text.match(/^(Motivo|Evidencia|Confirmación requerida[^:]*|Cambios respecto[^:]*):/);
    let children;
    if (isReview && /QA REVIEW/.test(text)) {
      children = [new TextRun({ text: text.replace(/^⚠️?\s*/, '').toLowerCase(), font: F.mono, size: 17, bold: true, color: C.reviewTxt })];
    } else if (label) {
      children = [new TextRun({ text: label[0].toLowerCase() + ' ', font: F.mono, size: 16, color: isReview ? C.reviewTxt : C.ambarOsc }),
        ...runs(text.slice(label[0].length).trim())];
    } else children = runs(text);
    paras.push(new Paragraph({
      children, shading: { type: ShadingType.CLEAR, fill: isReview ? C.review : C.nota, color: 'auto' },
      border: { left: side }, indent: { left: 240, right: 240 }, spacing: { before: 40, after: 40 },
      ...(bullet ? { numbering: { reference: 'bullets', level: 0 } } : {}),
    }));
  }
  paras.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
  return paras;
}

// ------------------------------------------------------------------ cuerpo
const body = [], toc = [];
let stepsInstance = 0, inSteps = false, title = '', nSeccion = 0;
for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  if (!line.trim()) continue;
  if (line.trim().startsWith('```')) {
    const code = []; i++;
    while (i < lines.length && !lines[i].trim().startsWith('```')) code.push(lines[i++].replace(/^ {3}/, ''));
    for (const [k, c] of code.entries()) body.push(new Paragraph({
      shading: { type: ShadingType.CLEAR, fill: C.carbon, color: 'auto' }, indent: { left: 240, right: 240 },
      spacing: { before: k === 0 ? 100 : 0, after: k === code.length - 1 ? 180 : 0 },
      children: [new TextRun({ text: c || ' ', font: F.mono, size: 17, color: C.ink })] }));
    continue;
  }
  if (line.startsWith('>')) {
    const block = []; while (i < lines.length && lines[i].startsWith('>')) block.push(lines[i++]); i--;
    body.push(...quote(block)); continue;
  }
  if (line.startsWith('|')) {
    const rows = []; while (i < lines.length && lines[i].startsWith('|')) rows.push(lines[i++]); i--;
    body.push(table(rows), new Paragraph({ spacing: { after: 160 }, children: [] })); continue;
  }
  const img = line.trim().match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
  if (img) { body.push(...image(img[2], img[1])); continue; }
  let m;
  if ((m = line.match(/^(#{1,3}) (.*)/))) {
    if (m[1].length === 1) { title = m[2].replace(/\*\*/g, ''); continue; }
    inSteps = false;
    if (m[1].length === 2) {
      nSeccion++;
      const num = String(nSeccion).padStart(2, '0');
      toc.push([num, m[2].replace(/\*\*/g, '')]);
      body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [
        new TextRun({ text: `${num}  `, font: F.mono, size: 22, color: C.ambar }), ...runs(m[2], { font: F.display, color: C.titulo })] }));
    } else {
      body.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(m[2], { font: F.display, color: C.ambarOsc }) }));
    }
    continue;
  }
  if ((m = line.match(/^(\s*)[-*] (.*)/))) {
    body.push(new Paragraph({ numbering: { reference: 'bullets', level: Math.min(2, Math.floor(m[1].length / 2)) }, children: runs(m[2]) }));
    continue;
  }
  if ((m = line.match(/^(\s*)\d+\. (.*)/))) {
    if (!inSteps) { stepsInstance++; inSteps = true; }
    body.push(new Paragraph({ numbering: { reference: 'steps', level: 0, instance: stepsInstance }, spacing: { before: 60, after: 60 }, children: runs(m[2]) }));
    continue;
  }
  if (!/^\s/.test(line)) inSteps = false;
  body.push(new Paragraph({ spacing: { after: 140 }, children: runs(line.trim()) }));
}

// ------------------------------------------------------------------ portada (como los informes: noche + ámbar)
const status = STATUS_ARG || (IS_DRAFT ? `Borrador ${VER} · pendiente de revisión (no publicar)` : `Versión ${VER}`);
const footerStatus = STATUS_ARG || (IS_DRAFT ? `borrador ${VER}` : `versión ${VER}`);
const hoy = new Date().toISOString().slice(0, 10);
const meta = [['documento', 'manual de usuario'], ['estado', status], ['fecha', hoy]].concat(EQUIPO ? [['equipo', EQUIPO]] : []);
const portada = new Table({
  width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: [CONTENT_W], borders: sinBordes(),
  rows: [new TableRow({ height: { value: PAGE_H - 2 * MARGIN - 600, rule: HeightRule.ATLEAST }, children: [new TableCell({
    width: { size: CONTENT_W, type: WidthType.DXA }, verticalAlign: VerticalAlign.TOP,
    shading: { type: ShadingType.CLEAR, fill: C.noche, color: 'auto' },
    borders: { top: { style: BorderStyle.NONE, size: 0, color: 'auto' }, left: { style: BorderStyle.NONE, size: 0, color: 'auto' },
      right: { style: BorderStyle.NONE, size: 0, color: 'auto' }, bottom: { style: BorderStyle.SINGLE, size: 24, color: C.ambar } },
    margins: { top: 700, bottom: 700, left: 700, right: 700 },
    children: [
      new Paragraph({ spacing: { after: 4600 }, children: [
        new TextRun({ text: ' k0 ', font: F.display, bold: true, size: 30, color: C.noche, shading: { type: ShadingType.CLEAR, fill: C.ambar, color: 'auto' } }),
        new TextRun({ text: '   K0LMENIA', font: F.display, bold: true, size: 28, color: C.ink }),
      ] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: 'manual de usuario', font: F.mono, size: 18, color: C.ambar })] }),
      new Paragraph({ spacing: { after: 360 }, children: [new TextRun({ text: title || path.basename(mdPath, '.md'), font: F.display, bold: true, size: 64, color: C.ink })] }),
      new Paragraph({ spacing: { after: 480 }, children: [new TextRun({ text: `  ${status}  `, font: F.mono, size: 18, bold: true,
        color: IS_DRAFT && !STATUS_ARG ? C.ambar : C.ok, shading: { type: ShadingType.CLEAR, fill: C.tile, color: 'auto' } })] }),
      ...meta.map(([k, v]) => new Paragraph({ spacing: { after: 60 }, children: [
        new TextRun({ text: `${k}  `, font: F.mono, size: 16, color: C.muted }), new TextRun({ text: v, font: F.sans, size: 19, color: C.body })] })),
      new Paragraph({ spacing: { before: 600 }, children: [new TextRun({ text: 'generado por k0lmenIA · parte de la suite k0lmena', font: F.mono, size: 15, color: C.muted })] }),
    ],
  })] })],
});

const contenido = [
  new Paragraph({ pageBreakBefore: true, spacing: { after: 200 }, children: [new TextRun({ text: 'contenido', font: F.mono, size: 18, color: C.ambar })] }),
  ...toc.map(([num, t]) => new Paragraph({ spacing: { after: 80 }, border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: C.borde, space: 4 } },
    children: [new TextRun({ text: `${num}  `, font: F.mono, size: 20, color: C.ambar }), new TextRun({ text: t, font: F.display, bold: true, size: 24, color: C.titulo })] })),
  new Paragraph({ pageBreakBefore: true, children: [] }),
];

// ------------------------------------------------------------------ fuentes de la casa (embebidas si vienen)
let fonts = [];
try {
  const mapa = JSON.parse(process.env.MANUAL_FUENTES || '{}');
  fonts = Object.entries(mapa).filter(([, ruta]) => fs.existsSync(ruta))
    .map(([name, ruta]) => ({ name, data: fs.readFileSync(ruta), characterSet: CharacterSet.ANSI }));
} catch (e) {
  console.error(`Aviso: no se pudieron embeber las fuentes (${e.message}); Word usará las instaladas.`);
}

const encabezado = new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.borde, space: 6 } },
  children: [new TextRun({ text: 'K0LMENIA', font: F.display, bold: true, size: 16, color: C.titulo }),
    new TextRun({ text: `  ·  ${(title || '').toLowerCase()}`, font: F.mono, size: 14, color: C.ambarOsc })] })] });
const pie = new Footer({ children: [new Paragraph({
  tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }],
  border: { top: { style: BorderStyle.SINGLE, size: 4, color: C.borde, space: 6 } },
  children: [
    new TextRun({ text: `generado por k0lmenIA · ${footerStatus}${EQUIPO ? ' · ' + EQUIPO : ''}`, font: F.mono, size: 14, color: C.muted }),
    new TextRun({ children: ['\tpágina ', PageNumber.CURRENT, ' de ', PageNumber.TOTAL_PAGES], font: F.mono, size: 14, color: C.muted }),
  ] })] });

const doc = new Document({
  creator: EQUIPO || 'k0lmenIA',
  title,
  description: 'Manual de usuario generado con k0lmenIA',
  fonts,
  styles: {
    default: { document: { run: { font: F.sans, size: 21, color: C.texto }, paragraph: { spacing: { line: 300 } } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: F.display, size: 36, bold: true, color: C.titulo },
        paragraph: { spacing: { before: 480, after: 200 }, keepNext: true, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.ambar, space: 6 } } } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: F.display, size: 26, bold: true, color: C.ambarOsc },
        paragraph: { spacing: { before: 300, after: 120 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: 'bullets', levels: [0, 1, 2].map(l => ({ level: l, format: LevelFormat.BULLET, text: ['▪', '–', '·'][l], alignment: AlignmentType.LEFT,
      style: { run: { color: C.ambar }, paragraph: { indent: { left: 640 + 360 * l, hanging: 300 } } } })) },
    { reference: 'steps', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1', alignment: AlignmentType.LEFT,
      style: { run: { font: F.display, bold: true, color: C.ambarOsc, size: 24 }, paragraph: { indent: { left: 640, hanging: 400 } } } }] },
  ] },
  sections: [{
    properties: { titlePage: true, page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    headers: { default: encabezado, first: new Header({ children: [] }) },
    footers: { default: pie, first: new Footer({ children: [] }) },
    children: [portada, ...contenido, ...body],
  }],
});

Packer.toBuffer(doc).then(b => { fs.writeFileSync(outPath, b); console.log('OK', outPath); });

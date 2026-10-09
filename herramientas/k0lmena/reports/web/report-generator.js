"use strict";

// multiple-cucumber-html-reporter v4 es solo ESM: se carga con import() dinámico.
const loadReporter = () => import("multiple-cucumber-html-reporter");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { opcionesReporte, temaEnHtml } = require("../tema-oscuro");

/**
 * Este script vive dentro de reports/web
 */
const REPORT_DIR = path.resolve(__dirname);

(async function main() {
  // 1) Genera el reporte
  // Las páginas de features llevan un id por corrida: se borran las viejas para no acumularlas.
  fs.rmSync(path.join(REPORT_DIR, "features"), { recursive: true, force: true });
  const report = await loadReporter();
  await report.generate({
    ...opcionesReporte("Web"),
    jsonDir: REPORT_DIR,
    reportPath: REPORT_DIR,
    metadata: {
      browser: { name: process.env.BROWSER || "chromium", version: "Playwright" },
      device: os.hostname(),
      platform: { name: os.platform(), version: os.release() },
    },
    customData: {
      Proyecto: "k0lmena · Web",
      Ejecutado: new Date().toLocaleString("es-AR"),
      "URL base": process.env.BASEURL || process.env.APP_URL || "—",
    },
  });

  // 2) Espera a que se creen HTMLs
  await waitForHtmlGeneration(REPORT_DIR);

  // 3) Aplica patches en TODOS los HTML generados
  patchAllHtmlReports(REPORT_DIR);

  console.log(
    "[k0lmena] Reporte web generado con el tema oscuro de k0lmenIA (links de traces corregidos)."
  );
})().catch((e) => {
  console.error("[k0lmena] Report generation/patch failed:", e);
  process.exitCode = 1;
});

/* ----------------------------- Patcher ----------------------------- */

function patchAllHtmlReports(rootDir) {
  const htmlFiles = collectFilesRecursive(rootDir, (p) =>
    p.toLowerCase().endsWith(".html")
  );

  for (const file of htmlFiles) {
    patchSingleHtml(file, rootDir);
  }
}

function patchSingleHtml(filePath, rootDir) {
  let html;
  try {
    html = fs.readFileSync(filePath, "utf8");
  } catch {
    return;
  }

  // Evita doble inyección
  if (html.includes('id="k0lmena-theme"')) return;

  // ✅ FIX 1: Descarga zip (traces) - corrige rutas relativas en páginas dentro de /features/
  html = fixRelativeTraceLinks(html, filePath, rootDir);

  // ✅ FIX 2: Labels (sin tocar estilos)
  // Deben quedar así:
  // + Show Error
  // + Show Info
  // + Download Zip
  // + Screenshot
  html = fixInfoAndZipLabels(html);

  // ✅ FIX 3: modo oscuro fijo con el tema común de k0lmenIA (reports/tema-oscuro.js)
  html = temaEnHtml(html);

  try {
    fs.writeFileSync(filePath, html, "utf8");
  } catch {
    // noop
  }
}

/**
 * ✅ Corrige links como href="traces/archivo.zip" para que apunten bien desde subcarpetas (features/, etc.)
 */
function fixRelativeTraceLinks(html, filePath, rootDir) {
  try {
    const tracesDir = path.join(rootDir, "traces");
    let rel = path.relative(path.dirname(filePath), tracesDir);
    rel = rel.split(path.sep).join("/"); // web slashes
    if (!rel || rel.trim() === "") rel = "traces";
    rel = rel.replace(/\/+$/, "");

    // Reescribe SOLO cuando arranca con "traces/", "videos/" o "evidencias/" (no toca ../ ya correctos)
    const prefix = rel.replace(/traces$/, "");
    // También dentro de adjuntos HTML escapados (data-attachment-content usa &#34; / &quot;).
    html = html.replace(
      /(href|src)=(["']|&#34;|&quot;)(traces|videos|evidencias)\//gi,
      (_m, attr, q, dir) => `${attr}=${q}${prefix}${dir}/`
    );

    return html;
  } catch {
    return html;
  }
}

/**
 * ✅ FIX DEFINITIVO:
 * Parcha SOLO dentro de <ul class="panel_toolbox">...</ul>.
 *
 * Reglas:
 * 1) Si un <a> es claramente de ZIP (atributos con .zip / traces / downloadZip / trace), se etiqueta "+ Download Zip".
 * 2) Si hay patrón en el toolbox: Error -> Info -> Info -> Screenshot, el 3º se fuerza a "+ Download Zip".
 * 3) Se normaliza cualquier "Descargar Zip" / "download zip" a "Download Zip".
 * 4) No se toca CSS/estructura, solo texto.
 */
function fixInfoAndZipLabels(html) {
  return html.replace(
    /<ul\b[^>]*class=(["'])[^"']*panel_toolbox[^"']*\1[^>]*>[\s\S]*?<\/ul>/gi,
    (ul) => patchPanelToolboxUl(ul)
  );
}

function patchPanelToolboxUl(ulHtml) {
  const anchorRe = /<a\b[^>]*>[\s\S]*?<\/a>/gi;

  const anchors = [];
  let m;
  while ((m = anchorRe.exec(ulHtml)) !== null) {
    anchors.push({
      start: m.index,
      end: anchorRe.lastIndex,
      html: m[0],
    });
  }

  if (anchors.length === 0) return ulHtml;

  // Utilidad: tipo por label visible
  const getPlain = (aHtml) =>
    aHtml
      .replace(/<[^>]*>/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();

  const getType = (aHtml) => {
    const p = getPlain(aHtml);
    if (p.includes("+ show error")) return "error";
    if (p.includes("+ screenshot")) return "screenshot";
    if (p.includes("+ download zip") || p.includes("+ descargar zip") || p.includes("+ downloadzip"))
      return "zip";
    if (p.includes("+ show info")) return "info";
    return "other";
  };

  const isZipCandidateByAttrs = (aHtml) => {
    const open = (aHtml.match(/^<a\b[^>]*>/i) || [""])[0].toLowerCase();
    return (
      open.includes(".zip") ||
      open.includes("traces/") ||
      open.includes("trace") || // clave: muchos reports no ponen .zip en href pero sí "trace"/"downloadTrace"
      open.includes("downloadzip") ||
      open.includes("download-zip") ||
      open.includes("zip")
    );
  };

  // 1) Primer pasada: normaliza ZIP por atributos, y normaliza "Descargar Zip" -> "Download Zip"
  let updated = ulHtml;
  for (let i = anchors.length - 1; i >= 0; i--) {
    const a = anchors[i].html;
    const type = getType(a);

    let newA = a;

    // Normaliza cualquier texto "Descargar Zip" o "download zip" a "Download Zip"
    if (/(\+\s*)(descargar\s*zip|download\s*zip|downloadzip)/i.test(newA)) {
      newA = replacePlusLabel(newA, "+ Download Zip");
    }

    // Si por atributos parece ZIP, fuerza "Download Zip"
    if (isZipCandidateByAttrs(newA)) {
      // Incluso si hoy dice Show Info
      if (/(\+\s*)(show\s*info|descargar\s*zip|download\s*zip|downloadzip)/i.test(getPlain(newA))) {
        newA = replacePlusLabel(newA, "+ Download Zip");
      }
    } else {
      // Si NO parece ZIP pero quedó "Download Zip", lo vuelve a Show Info (evita falsos positivos)
      if (type === "zip" && !isZipCandidateByAttrs(newA)) {
        newA = replacePlusLabel(newA, "+ Show Info");
      }
    }

    if (newA !== a) {
      updated = updated.slice(0, anchors[i].start) + newA + updated.slice(anchors[i].end);
    }
  }

  // Re-extrae anchors desde el HTML ya actualizado (porque cambiaron longitudes)
  const anchors2 = [];
  anchorRe.lastIndex = 0;
  while ((m = anchorRe.exec(updated)) !== null) {
    anchors2.push({
      start: m.index,
      end: anchorRe.lastIndex,
      html: m[0],
      type: getType(m[0]),
    });
  }

  // 2) Fallback definitivo por patrón visual:
  // Error -> Info -> Info -> Screenshot  => el 3º es ZIP
  if (anchors2.length >= 4) {
    for (let i = 0; i <= anchors2.length - 4; i++) {
      const a0 = anchors2[i];
      const a1 = anchors2[i + 1];
      const a2 = anchors2[i + 2];
      const a3 = anchors2[i + 3];

      const isPattern =
        a0.type === "error" &&
        a1.type === "info" &&
        a2.type === "info" &&
        a3.type === "screenshot";

      if (isPattern) {
        const target = anchors2[i + 2].html;
        const patched = replacePlusLabel(target, "+ Download Zip");

        if (patched !== target) {
          updated =
            updated.slice(0, anchors2[i + 2].start) +
            patched +
            updated.slice(anchors2[i + 2].end);
        }
        break; // con uno alcanza por toolbox
      }
    }
  }

  return updated;
}

/**
 * Reemplaza SOLO el texto del label "+ ..." manteniendo cualquier HTML interno.
 */
function replacePlusLabel(aTagOrInner, desiredLabel) {
  const desiredNoPlus = desiredLabel.replace(/^\+\s*/i, "");

  // Reemplaza el label si existe (Show Info / Download Zip / Descargar Zip)
  const re = /(\+\s*)(Show\s*Info|Descargar\s*Zip|Download\s*Zip|download\s*zip|downloadzip)/i;

  if (re.test(aTagOrInner)) {
    return aTagOrInner.replace(re, `$1${desiredNoPlus}`);
  }

  // Si no encontró el label, pero hay HTML: agrega al final sin romper nada
  if (/<[^>]+>/.test(aTagOrInner)) {
    return `${aTagOrInner} ${desiredLabel}`;
  }

  return desiredLabel;
}

function collectFilesRecursive(dir, predicate) {
  const out = [];
  let entries = [];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return out;
  }

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      out.push(...collectFilesRecursive(fullPath, predicate));
    } else if (entry.isFile()) {
      if (!predicate || predicate(fullPath)) out.push(fullPath);
    }
  }

  return out;
}

function waitForHtmlGeneration(rootDir, timeoutMs = 15000) {
  const start = Date.now();

  return new Promise((resolve) => {
    const tick = () => {
      const htmlFiles = collectFilesRecursive(rootDir, (p) =>
        p.toLowerCase().endsWith(".html")
      );

      if (htmlFiles.length > 0) return resolve(true);
      if (Date.now() - start >= timeoutMs) return resolve(false);

      setTimeout(tick, 250);
    };

    tick();
  });
}

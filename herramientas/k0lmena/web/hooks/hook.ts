"use strict";
import { config } from "dotenv";
config();
import {
  chromium,
  firefox,
  webkit,
  Browser,
  Page,
  BrowserContext,
} from "playwright";
import {
  BeforeAll,
  Before,
  After,
  AfterAll,
  AfterStep,
  Status,
  ITestCaseHookParameter,
  setDefaultTimeout,
} from "@cucumber/cucumber";
import * as fs from "fs";
import * as path from "path";
import { consumeHealingEvents, flushHealingHistory } from "../utils/autoHealing";
import { crearGif, htmlGif, modoEvidencia } from "../../tools/evidencia/gif";
const { sesionActiva } = require("../../tools/login/sesion");
// Canal (Chrome/Edge), ritmo humano, header de bypass para la app y detección de bloqueos anti-bots.
const navegadorComun = require("../../tools/navegador/navegador");

// Marca que lee scripts/gestion (y el análisis de fallos) para tratar el escenario como Bloqueado, no Fallido.
const MARCA_BLOQUEO = "BLOQUEO ANTI-BOTS";

setDefaultTimeout(60 * 1000);

const nodeLogs: string[] = [];
const originalConsoleLog = console.log;
console.log = function (...args: any[]) {
  nodeLogs.push(args.map(String).join(" "));
  originalConsoleLog.apply(console, args);
};

let browsers: Browser[] = [];
let pages: Page[] = [];
let contexts: BrowserContext[] = [];

const pageLogs = new Map<Page, string[]>();
// Capturas por paso para el GIF del recorrido (solo con EVIDENCE=ambos).
const pageFrames = new Map<Page, Buffer[]>();
const traceState = new Map<
  BrowserContext,
  { started: boolean; stopped: boolean }
>();

function sanitizeFilePart(value: string): string {
  return value
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 120);
}

function toPosix(p: string): string {
  return p.split(path.sep).join("/");
}

function boolFromEnv(name: string, defaultValue: boolean): boolean {
  const raw = (process.env[name] ?? String(defaultValue)).toLowerCase().trim();
  return !["0", "false", "no", "off"].includes(raw);
}

function intFromEnv(name: string, defaultValue: number): number {
  const raw = (process.env[name] ?? "").trim();
  // Vacío o sin definir → el valor por defecto (Number("") es 0: sin esto, el viewport quedaba en 0x0).
  if (!raw) return defaultValue;
  const n = Number(raw);
  return Number.isFinite(n) ? n : defaultValue;
}

function traceMode(): "off" | "on" | "on-failure" {
  const raw = (process.env.TRACE ?? "off").toLowerCase().trim();
  if (raw === "on") return "on";
  if (raw === "on-failure" || raw === "onfailure") return "on-failure";
  return "off";
}

// VIDEO env var: on-failure (default) -> guarda el video solo si el escenario falla
//                on -> guarda siempre | off -> no graba
function videoMode(): "off" | "on" | "on-failure" {
  const raw = (process.env.VIDEO ?? "on-failure").toLowerCase().trim();
  if (raw === "on") return "on";
  if (raw === "off") return "off";
  return "on-failure";
}

function getReportRootAbs(): string {
  const raw = (process.env.REPORT_DIR ?? "reports/web").trim();
  return path.isAbsolute(raw) ? raw : path.join(process.cwd(), raw);
}

async function ensureDirAbs(dirAbs: string): Promise<string> {
  if (!fs.existsSync(dirAbs)) fs.mkdirSync(dirAbs, { recursive: true });
  return dirAbs;
}

function getBrowserLabel(browser: Browser): string {
  const type = (browser as any)?._type?.name?.();
  if (typeof type === "string" && type.length > 0) return type;
  const name = (browser as any)?.browserType?.()?.name?.();
  if (typeof name === "string" && name.length > 0) return name;
  return "browser";
}

function resolveBrowserTypes(): any[] {
  const browserChoice = (process.env.BROWSER ?? "").toLowerCase().trim();
  const map: Record<string, any> = { chromium, firefox, webkit };
  if (browserChoice && map[browserChoice]) return [map[browserChoice]];
  return [chromium, firefox, webkit];
}

function scenarioNameFromWorld(world: any): string {
  return world?.pickle?.name || world?.scenario?.name || "scenario";
}

function attachPageListeners(page: Page) {
  const logs: string[] = [];
  pageLogs.set(page, logs);

  page.on("console", (msg) => {
    logs.push(`[browser console:${msg.type()}] ${msg.text()}`);
  });

  page.on("pageerror", (err) => {
    logs.push(`[pageerror] ${String(err)}`);
  });

  page.on("requestfailed", (req) => {
    const failure = req.failure();
    logs.push(
      `[requestfailed] ${req.method()} ${req.url()}${
        failure?.errorText ? ` -> ${failure.errorText}` : ""
      }`
    );
  });

  page.on("response", (res) => {
    if (res.status() >= 400) {
      logs.push(`[http ${res.status()}] ${res.request().method()} ${res.url()}`);
    }
  });

  page.on("crash", () => {
    logs.push("[crash] La página se crasheó.");
  });
}

async function startTracingIfEnabled(context: BrowserContext) {
  const mode = traceMode();
  if (mode === "off") return;
  await context.tracing.start({
    screenshots: true,
    snapshots: true,
    sources: true,
  });
  traceState.set(context, { started: true, stopped: false });
}

async function stopTracing(context: BrowserContext, savePath?: string) {
  const state = traceState.get(context);
  if (!state?.started || state.stopped) return;
  if (savePath) {
    await context.tracing.stop({ path: savePath }).catch(() => undefined);
  } else {
    await context.tracing.stop().catch(() => undefined);
  }
  state.stopped = true;
  traceState.set(context, state);
}

BeforeAll(async function () {
  const browserTypes = resolveBrowserTypes();
  const headless = boolFromEnv("HEADLESS", true);
  const slowMo = intFromEnv("SLOWMO", 0);

  for (const browserType of browserTypes) {
    const b = await navegadorComun.lanzar(browserType, { headless, slowMo });
    browsers.push(b);
  }
});

// Sesión guardada con npm run login (SESION en el .env). Se resuelve una vez por proceso, así el
// aviso de "no existe el archivo" no se repite en cada escenario.
let sesionResuelta: string | null | undefined;
function archivoSesionActiva(): string | null {
  if (sesionResuelta === undefined) {
    sesionResuelta = sesionActiva(process.env.SESION, (msg: string) => originalConsoleLog(`[sesion] ${msg}`));
  }
  return sesionResuelta ?? null;
}

Before(async function (scenario: ITestCaseHookParameter) {
  nodeLogs.length = 0;

  for (const ctx of contexts) {
    await ctx.close().catch(() => undefined);
  }

  contexts.length = 0;
  pages.length = 0;
  pageLogs.clear();
  pageFrames.clear();
  traceState.clear();

  const viewport = {
    width: intFromEnv("VIEWPORT_WIDTH", 1366),
    height: intFromEnv("VIEWPORT_HEIGHT", 768),
  };

  const locale = (process.env.LOCALE ?? "es-AR").trim();
  const timezoneId = (process.env.TIMEZONE ?? "America/Argentina/Mendoza").trim();

  // Los escenarios @sin-sesion (por ejemplo, los que prueban el propio login) arrancan sin sesión.
  const sinSesion = (scenario?.pickle?.tags ?? []).some((t) => t.name === "@sin-sesion");
  const storageState = sinSesion ? undefined : archivoSesionActiva() ?? undefined;

  for (const browser of browsers) {
    const recordVideo =
      videoMode() === "off"
        ? undefined
        : { dir: path.join(getReportRootAbs(), "videos", ".tmp"), size: viewport };
    const context = await browser.newContext({ viewport, locale, timezoneId, recordVideo, storageState });
    contexts.push(context);

    await startTracingIfEnabled(context);

    const page = await context.newPage();
    page.setDefaultTimeout(60 * 1000);
    page.setDefaultNavigationTimeout(60 * 1000);

    attachPageListeners(page);
    pages.push(page);
  }
});

AfterStep(async function ({ result, pickle }) {
  const healEvents = consumeHealingEvents();
  if (healEvents.length > 0) {
    const lines = healEvents
      .map((e) => {
        const note = e.note ? `\nNote: ${e.note}` : "";
        return `AUTO-HEALING\n- At: ${e.at}\n- Action: ${e.action}\n- Original: ${e.original}\n- Healed with: ${e.healedWith}${note}`;
      })
      .join("\n\n");
    await this.attach(lines, "text/plain");
  }

  if (modoEvidencia() === "ambos" && result?.status === Status.PASSED) {
    for (const page of pages) {
      const frame = await page.screenshot().catch(() => undefined);
      if (frame) pageFrames.set(page, [...(pageFrames.get(page) ?? []), frame]);
    }
  }

  if (!result || result.status !== Status.FAILED) return;

  // ¿Falló porque la app frenó al navegador (desafío, captcha, acceso denegado)? Entonces no es un bug.
  for (const page of pages) {
    const bloqueo =
      (await navegadorComun.detectarEnPagina(page)) ??
      navegadorComun.bloqueos.find((b: { url: string }) => b.url === page.url()) ??
      null;
    if (bloqueo) {
      await this.attach(
        `${MARCA_BLOQUEO}: ${bloqueo.proveedor} (${bloqueo.tipo}) en ${page.url()}
` +
          `El paso falló porque la protección anti-bots de la app frenó al navegador automatizado; no es un bug de la app.
` +
          `Qué hacer: pedí una excepción para QA (QA_BYPASS_HEADER / QA_BYPASS_TOKEN, IP o claves de prueba del captcha) ` +
          `o usá npm run login con SESION en el .env. Guía: ${navegadorComun.GUIA}`,
        "text/plain"
      );
    }
  }

  const reportRoot = getReportRootAbs();
  const screenshotsDir = await ensureDirAbs(path.join(reportRoot, "screenshots"));
  const tracesDir = await ensureDirAbs(path.join(reportRoot, "traces"));

  const scenarioName = sanitizeFilePart(pickle?.name || scenarioNameFromWorld(this as any));
  const timestamp = Date.now();

  for (let i = 0; i < pages.length; i++) {
    const page = pages[i];
    const browserLabel = getBrowserLabel(browsers[i] ?? (browsers[0] as any));

    const screenshot = await page
      .screenshot({ fullPage: true })
      .catch(() => undefined);

    if (screenshot) {
      const fileName = `screenshot-${scenarioName}-${browserLabel}-${timestamp}.png`;
      fs.writeFileSync(path.join(screenshotsDir, fileName), screenshot);
      await this.attach(screenshot, "image/png");
    }

    const url = page.url();
    const title = await page.title().catch(() => "");
    await this.attach(
      `PÁGINA AL FALLAR (${browserLabel})\n- URL: ${url}\n- Título: ${title}`,
      "text/plain"
    );

    // DOM en el momento de la falla: el reparador-automatizacion busca ahí el elemento que el
    // locator no encontró (y propone uno nuevo) sin volver a correr el escenario.
    const html = await page.content().catch(() => undefined);
    if (html) {
      const domDir = await ensureDirAbs(path.join(reportRoot, "dom"));
      const domAbs = path.join(domDir, `dom-${scenarioName}-${browserLabel}-${timestamp}.html`);
      fs.writeFileSync(domAbs, html);
      await this.attach(`DOM: ${toPosix(path.relative(reportRoot, domAbs))}\n- URL: ${url}`, "text/plain");
    }

    const browserSideLogs = pageLogs.get(page) ?? [];
    if (browserSideLogs.length > 0) {
      await this.attach(
        `LOGS DEL NAVEGADOR (${browserLabel}): consola, errores JS, requests fallidos y respuestas HTTP >= 400\n${browserSideLogs.join("\n")}`,
        "text/plain"
      );
    }
  }

  const mode = traceMode();
  if (mode === "on" || mode === "on-failure") {
    for (let i = 0; i < contexts.length; i++) {
      const ctx = contexts[i];
      const browserLabel = getBrowserLabel(browsers[i] ?? (browsers[0] as any));
      const traceAbs = path.join(
        tracesDir,
        `trace-${scenarioName}-${browserLabel}-${timestamp}.zip`
      );

      await stopTracing(ctx, traceAbs);

      const rel = toPosix(path.relative(reportRoot, traceAbs));
      await this.attach(`TRACE: ${rel}`, "text/plain");
      await this.attach(
        `<p><strong>Trace:</strong> <a href="${rel}" download>${path.basename(
          traceAbs
        )}</a></p>`,
        "text/html"
      );
    }
  }

  let errorDetails = "";
  if (result.message) {
    errorDetails += `ERROR\n${result.message}\n`;
  } else if (result.exception) {
    if (result.exception instanceof Error) {
      errorDetails += `Error Exception: ${result.exception.toString()}\n`;
      if ((result.exception as Error).stack) {
        errorDetails += `Stack Trace: ${(result.exception as Error).stack}\n`;
      }
    } else {
      errorDetails += `Error Exception: ${String(result.exception)}\n`;
    }
  }

  if (nodeLogs.length > 0) {
    errorDetails += `Logs de Node:\n${nodeLogs.join("\n")}\n`;
    nodeLogs.length = 0;
  }

  if (errorDetails) {
    await this.attach(errorDetails, "text/plain");
  }
});

After(async function (scenario: ITestCaseHookParameter) {
  const mode = traceMode();
  const failed = scenario?.result?.status === Status.FAILED;
  const reportRoot = getReportRootAbs();
  const scenarioName = sanitizeFilePart(scenario?.pickle?.name || scenarioNameFromWorld(this as any));
  const timestamp = Date.now();

  // Evidencia de un escenario que pasa: captura final (una por test y navegador) y,
  // con EVIDENCE=ambos, también el GIF del recorrido.
  const evidencia = modoEvidencia();
  if (!failed && evidencia === "ambos") {
    const evidenceDir = await ensureDirAbs(path.join(reportRoot, "evidencias"));
    for (let i = 0; i < pages.length; i++) {
      const browserLabel = getBrowserLabel(browsers[i] ?? (browsers[0] as any));
      const gif = crearGif(pageFrames.get(pages[i]) ?? []);
      if (!gif) continue;
      const gifAbs = path.join(evidenceDir, `gif-${scenarioName}-${browserLabel}-${timestamp}.gif`);
      fs.writeFileSync(gifAbs, gif);
      await this.attach(
        htmlGif(toPosix(path.relative(reportRoot, gifAbs)), `Recorrido del escenario (${browserLabel})`),
        "text/html"
      );
    }
  }
  if (!failed && evidencia !== "off") {
    const evidenceDir = await ensureDirAbs(path.join(reportRoot, "evidencias"));
    for (let i = 0; i < pages.length; i++) {
      const browserLabel = getBrowserLabel(browsers[i] ?? (browsers[0] as any));
      const shot = await pages[i].screenshot({ fullPage: true }).catch(() => undefined);
      if (!shot) continue;
      fs.writeFileSync(
        path.join(evidenceDir, `ok-${scenarioName}-${browserLabel}-${timestamp}.png`),
        shot
      );
      await this.attach(shot, "image/png");
    }
  }

  // El video se termina de escribir al cerrar el contexto: guardamos las referencias antes.
  const videos = pages.map((page) => page.video());

  if (mode === "on") {
    for (const ctx of contexts) await stopTracing(ctx, undefined);
  } else if (mode === "on-failure" && !failed) {
    for (const ctx of contexts) await stopTracing(ctx, undefined);
  }

  for (const ctx of contexts) {
    await ctx.close().catch(() => undefined);
  }

  // Video completo de la ejecución: se guarda si el escenario falló (o siempre con VIDEO=on).
  const keepVideo = videoMode() === "on" || (videoMode() === "on-failure" && failed);
  for (let i = 0; i < videos.length; i++) {
    const video = videos[i];
    if (!video) continue;
    if (keepVideo) {
      const browserLabel = getBrowserLabel(browsers[i] ?? (browsers[0] as any));
      const videosDir = await ensureDirAbs(path.join(reportRoot, "videos"));
      const videoAbs = path.join(videosDir, `video-${scenarioName}-${browserLabel}-${timestamp}.webm`);
      const saved = await video.saveAs(videoAbs).then(() => true).catch(() => false);
      if (saved) {
        const rel = toPosix(path.relative(reportRoot, videoAbs));
        await this.attach(
          `<p><strong>Video de la ejecución (${browserLabel}):</strong></p>` +
            `<video controls preload="metadata" style="max-width:100%" src="${rel}"></video>` +
            `<p><a href="${rel}" download>${path.basename(videoAbs)}</a></p>`,
          "text/html"
        );
      }
    }
    await video.delete().catch(() => undefined);
  }

  contexts.length = 0;
  pages.length = 0;
  nodeLogs.length = 0;
  pageLogs.clear();
  pageFrames.clear();
  traceState.clear();
});

AfterAll(async function () {
  const closePromise = Promise.all(
    browsers.map((b) => b.close().catch(() => undefined))
  );
  const flushPromise = flushHealingHistory().catch(() => undefined);
  await Promise.all([closePromise, flushPromise]);
});

export { browsers, pages };

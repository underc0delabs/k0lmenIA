// tools/debug/debugHook.ts
import { BeforeAll, AfterAll, BeforeStep } from '@cucumber/cucumber';
import { chromium, Browser, Page } from 'playwright';

const debugMode = ['1', 'true'].includes((process.env.CUCUMBER_DEBUG || '').toLowerCase());

let browser: Browser;
let page: Page;

BeforeAll(async function () {
  if (!debugMode) return;
  // Lanzamos en modo headful para inspección
  browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  page = await context.newPage();
  // Exponemos la página en el World para usarla en los steps:
  (this as any).page = page;
});

BeforeStep(async function () {
  if (!debugMode) return;
  // Pausamos antes de cada paso para abrir el inspector UI de Playwright
  await page.pause();
});

AfterAll(async function () {
  if (!debugMode) return;
  await browser.close();
});

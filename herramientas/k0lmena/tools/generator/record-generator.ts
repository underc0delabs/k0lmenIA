import * as fs from 'fs/promises';
import * as path from 'path';
import { URL } from 'url';

// Tiempo de espera entre pasos en ms
const STEP_DELAY = 500;

// --- 1) Definición de tipos de acción con soporte de index
interface GotoAction { type: 'goto'; url: string }
interface ClickRoleAction { type: 'clickRole'; role: string; name: string; index?: number; locatorName?: string }
interface ClickRoleInLocatorAction { type: 'clickRoleInLocator'; selector: string; role: string; name: string; index?: number; locatorName?: string; containerLocatorName?: string }
interface FillRoleAction { type: 'fillRole'; role: string; name: string; value: string; locatorName?: string }
interface PressRoleAction { type: 'pressRole'; role: string; name: string; key: string; locatorName?: string }
interface ClickLocatorAction { type: 'clickLocator'; selector: string; index?: number; locatorName?: string }

type Action = GotoAction | ClickRoleAction | ClickRoleInLocatorAction | FillRoleAction | PressRoleAction | ClickLocatorAction;

(async () => {
  const inputPath = path.resolve(__dirname, 'gen.ts');
  const outputDir = path.resolve(__dirname, 'output');
  await fs.mkdir(outputDir, { recursive: true });

  // --- 2) Leer el script generado por Playwright
  const raw = await fs.readFile(inputPath, 'utf8');
  const lines = raw.split(/\r?\n/);

  // --- 3) Parsear líneas en acciones
  const actions: Action[] = [];
  for (const line of lines) {
    let m;
    if (m = line.match(/page\.goto\(['"`](.+?)['"`]\)/)) {
      actions.push({ type: 'goto', url: m[1] });
    } else if (m = line.match(/page\.locator\(['"`](.+?)['"`]\)\.getByRole\(['"`](\w+)['"`],\s*\{\s*name:\s*['"`](.+?)['"`]\s*\}\)\.nth\((\d+)\)\.click/)) {
      actions.push({ type: 'clickRoleInLocator', selector: m[1], role: m[2], name: m[3], index: parseInt(m[4], 10) });
    } else if (m = line.match(/page\.locator\(['"`](.+?)['"`]\)\.getByRole\(['"`](\w+)['"`],\s*\{\s*name:\s*['"`](.+?)['"`]\s*\}\)\.first\(\)\.click/)) {
      actions.push({ type: 'clickRoleInLocator', selector: m[1], role: m[2], name: m[3], index: 0 });
    } else if (m = line.match(/getByRole\(\s*['"`](\w+)['"`],\s*\{\s*name:\s*['"`](.+?)['"`]\s*\}\)\.nth\((\d+)\)\.click/)) {
      actions.push({ type: 'clickRole', role: m[1], name: m[2], index: parseInt(m[3], 10) });
    } else if (m = line.match(/getByRole\(\s*['"`](\w+)['"`],\s*\{\s*name:\s*['"`](.+?)['"`]\s*\}\)\.click/)) {
      actions.push({ type: 'clickRole', role: m[1], name: m[2], index: 0 });
    } else if (m = line.match(/getByRole\(\s*['"`](\w+)['"`],\s*\{\s*name:\s*['"`](.+?)['"`]\s*\}\)\.fill\(\s*['"`](.*?)['"`]\s*\)/)) {
      actions.push({ type: 'fillRole', role: m[1], name: m[2], value: m[3] });
    } else if (m = line.match(/getByRole\(\s*['"`](\w+)['"`],\s*\{\s*name:\s*['"`](.+?)['"`]\s*\}\)\.press\(\s*['"`](.+?)['"`]\s*\)/)) {
      actions.push({ type: 'pressRole', role: m[1], name: m[2], key: m[3] });
    } else if (m = line.match(/page\.locator\(['"`](.+?)['"`]\)\.nth\((\d+)\)\.click/)) {
      actions.push({ type: 'clickLocator', selector: m[1], index: parseInt(m[2], 10) });
    } else if (m = line.match(/page\.locator\(['"`](.+?)['"`]\)\.first\(\)\.click/)) {
      actions.push({ type: 'clickLocator', selector: m[1], index: 0 });
    } else if (m = line.match(/page\.locator\(['"`](.+?)['"`]\)\.click/)) {
      actions.push({ type: 'clickLocator', selector: m[1], index: 0 });
    }
  }

  // --- 4) Generar locators únicos
  const locators: Record<string, string> = {};
  function toLocatorVar(text: string, suffix: string): string {
    const clean = text.replace(/[^\w ]+/g, ' ').trim();
    const words = clean.split(/\s+/).map((w, i) => i === 0 ? w.toLowerCase() : w[0].toUpperCase() + w.slice(1).toLowerCase());
    let base = words.join('') || 'element';
    let name = base + suffix;
    let idx = 1;
    while (locators[name]) name = base + suffix + idx++;
    return name;
  }
  for (const act of actions) {
    if ((act.type === 'clickRole' || act.type === 'pressRole') && !act.locatorName) {
      const v = toLocatorVar(act.name, 'Element');
      locators[v] = act.name;
      act.locatorName = v;
    }
    if (act.type === 'clickRoleInLocator' && !act.containerLocatorName) {
      const c = toLocatorVar(act.selector, 'Container');
      locators[c] = act.selector;
      act.containerLocatorName = c;
      const ch = toLocatorVar(act.name, 'Element');
      locators[ch] = act.name;
      act.locatorName = ch;
    }
    if (act.type === 'fillRole' && !act.locatorName) {
      const v = toLocatorVar(act.name, 'Input');
      locators[v] = act.name;
      act.locatorName = v;
    }
    if (act.type === 'clickLocator' && !act.locatorName) {
      const v = toLocatorVar(act.selector, 'Locator');
      locators[v] = act.selector;
      act.locatorName = v;
    }
  }

  // --- 5) Datos Gherkin
  const gotoAct = actions.find(a => a.type === 'goto') as GotoAction | undefined;
  const url = gotoAct?.url || '';
  const pageName = new URL(url || '').hostname.split('.').slice(-2, -1)[0] || 'Página';
  const featureTitle = `Página de ${pageName.charAt(0).toUpperCase() + pageName.slice(1)}`;

  // --- 6) Generar feature.feature
  const feat: string[] = [];
  feat.push('@Regression');
  feat.push(`Feature: ${featureTitle}`);
  feat.push(`    Scenario: El usuario realiza las acciones grabadas`);
  if (gotoAct) feat.push(`        Given El usuario navega a la ${featureTitle}`);
  const interacts = actions.filter(a => a.type !== 'goto');
  interacts.forEach((act, idx) => {
    const isFirst = idx === 0;
    const isLast = idx === interacts.length - 1;
    const kw = isFirst ? 'When' : isLast ? 'Then' : 'And';
    if (act.type === 'clickRoleInLocator') {
      feat.push(`        ${kw} El usuario clickea el enlace ${locators[act.locatorName!]} dentro de ${locators[act.containerLocatorName!]}`);
    } else if (act.type === 'clickRole') {
      feat.push(`        ${kw} El usuario clickea el enlace ${locators[act.locatorName!]}`);
    } else if (act.type === 'clickLocator') {
      feat.push(`        ${kw} El usuario clickea el elemento ${locators[act.locatorName!]}`);
    } else if (act.type === 'fillRole') {
      feat.push(`        ${kw} El usuario ingresa "${act.value}" en el campo ${locators[act.locatorName!]}`);
    } else if (act.type === 'pressRole') {
      feat.push(`        ${kw} El usuario presiona "${act.key}" en el campo ${locators[act.locatorName!]}`);
    }
  });
  await fs.writeFile(path.join(outputDir, 'feature.feature'), feat.join('\n'));

  // --- 7) Generar locators.ts
  const locLines = Object.entries(locators).map(([k, v]) => `export const ${k} = '${v}';`);
  await fs.writeFile(path.join(outputDir, 'locators.ts'), locLines.join('\n'));

  // --- 8) Generar steps.ts con delay entre pasos
  const steps: string[] = [];
  steps.push(`import { expect } from '@playwright/test';`);
  steps.push(`import { Given, When, Then } from '@cucumber/cucumber';`);
  steps.push(`import { BASEURL } from '../config';`);
  steps.push(`import { pages } from '../hooks/hook';`);
  steps.push(`import * as vals from '../utils/validations';`);
  steps.push(`import { ${Object.keys(locators).join(', ')} } from '../locators/exampleLocators';`);
  steps.push(`import { getByLocator, getElementByRole, pressKey } from '../utils/interactions';`);
  steps.push(`const STEP_DELAY = ${STEP_DELAY};`);
  steps.push('');

  if (gotoAct) {
    steps.push(
      `Given('El usuario navega a la ${featureTitle}', async () => {`,
      `  for (const page of pages) {`,
      `    await page.goto(BASEURL);`,
      `    await page.waitForTimeout(STEP_DELAY);`,
      `  }`,
      `});`,
      ''
    );
  }

  interacts.forEach((act, idx) => {
    const isLast = idx === interacts.length - 1;
    const prefix = isLast ? 'Then' : 'When';

    if (act.type === 'clickRoleInLocator') {
      const i = act.index || 0;
      steps.push(
        `${prefix}('El usuario clickea el enlace ${locators[act.locatorName!]} dentro de ${locators[act.containerLocatorName!]}', async () => {`,
        `  for (const page of pages) {`,
        `    const container = await getByLocator(page, ${act.containerLocatorName!});`,
        `    await container.getByRole('${act.role}', { name: ${act.locatorName!} }).nth(${i}).click();`,
        `    await page.waitForTimeout(STEP_DELAY);`,
        `  }`,
        `});`,
        ''
      );
    } else if (act.type === 'clickRole') {
      const i = act.index || 0;
      steps.push(
        `${prefix}('El usuario clickea el enlace ${locators[act.locatorName!]}', async () => {`,
        `  for (const page of pages) {`,
        `    await page.getByRole('${act.role}', { name: ${act.locatorName!} }).nth(${i}).click();`,
        `    await page.waitForTimeout(STEP_DELAY);`,
        `  }`,
        `});`,
        ''
      );
    } else if (act.type === 'clickLocator') {
      const i = act.index || 0;
      steps.push(
        `${prefix}('El usuario clickea el elemento ${locators[act.locatorName!]}', async () => {`,
        `  for (const page of pages) {`,
        `    await page.locator('${act.selector}').nth(${i}).click();`,
        `    await page.waitForTimeout(STEP_DELAY);`,
        `  }`,
        `});`,
        ''
      );
    } else if (act.type === 'fillRole') {
      steps.push(
        `${prefix}('El usuario ingresa "${act.value}" en el campo ${locators[act.locatorName!]}', async () => {`,
        `  for (const page of pages) {`,
        `    const input = page.getByRole('${act.role}', { name: ${act.locatorName!} });`,
        `    await input.fill('${act.value}');`,
        `    await page.waitForTimeout(STEP_DELAY);`,
        `  }`,
        `});`,
        ''
      );
    } else if (act.type === 'pressRole') {
      steps.push(
        `${prefix}('El usuario presiona "${act.key}" en el campo ${locators[act.locatorName!]}', async () => {`,
        `  for (const page of pages) {`,
        `    const input = page.getByRole('${act.role}', { name: ${act.locatorName!} });`,
        `    await input.press('${act.key}');`,
        `    await page.waitForTimeout(STEP_DELAY);`,
        `  }`,
        `});`,
        ''
      );
    }
  });

  await fs.writeFile(path.join(outputDir, 'steps.ts'), steps.join('\n'));
  console.log('✅ Archivos generados (versión 5) en', outputDir);
})();
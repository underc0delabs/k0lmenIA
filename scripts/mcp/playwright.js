#!/usr/bin/env node
// Lanzador de los conectores MCP playwright y playwright-headless (ver CONECTORES.md).
// Arranca el server oficial de Playwright con la carpeta de evidencias del repo y, si existe el
// .env de la raíz, con --secrets .env: Playwright oculta esos valores (contraseñas, tokens) en
// las respuestas que ve el modelo. Sin .env arranca igual (el server falla si el archivo no existe).
//
// Uso (en .mcp.json): node scripts/mcp/playwright.js [--headless]
const fs = require('fs');
const path = require('path');
const { lanzarNpx, RAIZ } = require('./lanzar');

const args = ['--output-dir', 'output/ejecuciones/evidencia'];
if (process.argv.includes('--headless')) args.push('--headless');
if (fs.existsSync(path.join(RAIZ, '.env'))) args.push('--secrets', '.env');
lanzarNpx('playwright', '@playwright/mcp', args);

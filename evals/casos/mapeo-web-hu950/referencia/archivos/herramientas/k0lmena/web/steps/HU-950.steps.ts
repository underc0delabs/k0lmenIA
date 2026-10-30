import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import { click, fill, findLocator } from '../utils/interactions';
import { loginLocators } from '../locators/HU-950.locators';

const BASE_URL = process.env.BASE_URL ?? '';

Given('que estoy en la página de inicio de sesión', async function () {
  await this.page.goto(`${BASE_URL}/login`);
});

When('ingreso el usuario y la contraseña del ambiente', async function () {
  await fill(this.page, loginLocators.email, process.env.APP_USER ?? '');
  await fill(this.page, loginLocators.password, process.env.APP_PASSWORD ?? '');
});

When('ingreso el usuario del ambiente y la contraseña {string}', async function (clave: string) {
  await fill(this.page, loginLocators.email, process.env.APP_USER ?? '');
  await fill(this.page, loginLocators.password, clave);
});

When('presiono el botón {string}', async function (nombre: string) {
  await click(this.page, { role: 'button', name: nombre });
});

Then('veo el saludo {string}', async function (texto: string) {
  await expect(this.page.getByText(texto)).toBeVisible();
});

Then('veo el mensaje {string}', async function (texto: string) {
  await expect(findLocator(this.page, loginLocators.alerta)).toHaveText(texto);
});

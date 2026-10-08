// mobile/steps/login.steps.ts

import { Given, When, Then } from '@wdio/cucumber-framework';
import { loginLocators } from '../locators/login.locators';

Given(/^la app está abierta$/, async () => {
  await browser.pause(3000);
  const userField = await $(loginLocators.userField);
  await userField.waitForDisplayed({ timeout: 1000 });
});

When(/^el usuario ingresa "(.+)" en el campo usuario$/, async (usuario: string) => {
  const userField = await $(loginLocators.userField);
  await userField.setValue(usuario);
});

When(/^el usuario ingresa "(.+)" en el campo contraseña$/, async (contraseña: string) => {
  const passwordField = await $(loginLocators.passwordField);
  await passwordField.setValue(contraseña);
});

When(/^el usuario presiona el botón de iniciar sesión$/, async () => {
  const loginButton = await $(loginLocators.loginButton);
  await loginButton.click();
});

Then(/^se muestra la pantalla principal$/, async () => {
  const homeScreen = await $(loginLocators.homeScreen);
  await homeScreen.waitForDisplayed({ timeout: 10000 });
});

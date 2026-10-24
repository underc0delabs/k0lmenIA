// mobile/support/wdio.conf.ts
//
// Dónde corre la suite mobile se elige desde el .env, sin tocar este archivo:
//   MOBILE_TARGET=device       -> dispositivo físico por USB con Appium local (default)
//   MOBILE_TARGET=emulator     -> emulador Android / simulador iOS con Appium local
//   MOBILE_TARGET=browserstack -> dispositivo real en BrowserStack
//
// Variables comunes:  MOBILE_PLATFORM (Android | iOS), MOBILE_DEVICE_NAME,
//                     MOBILE_PLATFORM_VERSION, MOBILE_APP (ruta al .apk/.ipa, relativa a mobile/apps/)
// Solo device:        MOBILE_UDID
// Solo BrowserStack:  BROWSERSTACK_USER, BROWSERSTACK_KEY, BROWSERSTACK_APP (bs://...)

import type { Options } from '@wdio/types';
import { resolve, isAbsolute } from 'path';
// .env único de la raíz de k0lmenIA
require('../../env');

const env = (name: string, fallback = '') => (process.env[name] ?? fallback).trim();

const target = env('MOBILE_TARGET', 'device').toLowerCase();
const platform = env('MOBILE_PLATFORM', 'Android');
const isIOS = platform.toLowerCase() === 'ios';
const automationName = isIOS ? 'XCUITest' : 'UiAutomator2';
const appFile = env('MOBILE_APP', 'app.apk');
const appPath = isAbsolute(appFile) ? appFile : resolve(__dirname, '../apps', appFile);
// Los escenarios @bloqueado (pasos que no se pudieron mapear) nunca corren.
const rawTags = env('TAGS');
const tags = rawTags ? `(${rawTags}) and not @bloqueado` : 'not @bloqueado';

const localCapabilities = {
  platformName: platform,
  'appium:automationName': automationName,
  'appium:deviceName': env('MOBILE_DEVICE_NAME', target === 'emulator' ? 'emulator-5554' : '') || undefined,
  'appium:platformVersion': env('MOBILE_PLATFORM_VERSION') || undefined,
  'appium:app': appPath,
  // Solo dispositivo físico: el udid lo da `adb devices`.
  ...(target === 'device' && env('MOBILE_UDID') ? { 'appium:udid': env('MOBILE_UDID') } : {}),
};

const browserstackCapabilities = {
  platformName: platform,
  'appium:automationName': automationName,
  'appium:app': env('BROWSERSTACK_APP'),
  'bstack:options': {
    deviceName: env('MOBILE_DEVICE_NAME', 'Samsung Galaxy S22'),
    osVersion: env('MOBILE_PLATFORM_VERSION', '12.0'),
    projectName: 'k0lmena Mobile',
    buildName: env('BROWSERSTACK_BUILD', 'k0lmenIA'),
    sessionName: 'Mobile Test on BrowserStack',
  },
};

const connection =
  target === 'browserstack'
    ? {
        user: env('BROWSERSTACK_USER'),
        key: env('BROWSERSTACK_KEY'),
        hostname: 'hub.browserstack.com',
        port: 443,
        protocol: 'https' as const,
        services: [['browserstack', {}]] as Options.Testrunner['services'],
      }
    : {
        port: 4723,
        services: ['appium'] as Options.Testrunner['services'],
      };

export const config: Options.Testrunner = {
  runner: 'local',
  ...connection,

  specs: [resolve(__dirname, '../features/**/*.feature')],
  maxInstances: 1,
  logLevel: 'info',
  bail: 0,
  baseUrl: '',
  waitforTimeout: 10000,
  framework: 'cucumber',
  reporters: ['spec'],
  cucumberOpts: {
    require: [
      resolve(__dirname, '../steps/**/*.ts'),
      resolve(__dirname, './hooks.ts'),
      resolve(__dirname, '../../tools/variables.ts'),
      resolve(__dirname, '../../tools/bd/bd.steps.ts'),
    ],
    timeout: 60000,
    failFast: false,
    tags,
    format: [
      'pretty',
      `json:${resolve(__dirname, '../../reports/mobile/cucumber-report.json')}`,
    ],
  },
  autoCompileOpts: {
    tsNodeOpts: {
      transpileOnly: true,
      project: resolve(__dirname, '../../tsconfig.json'),
    },
  },
  capabilities: [target === 'browserstack' ? browserstackCapabilities : localCapabilities],
} as unknown as Options.Testrunner;

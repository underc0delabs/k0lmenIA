// mobile/support/hooks.ts
//
// Evidencias por escenario (como en web):
//  - Pasa  -> captura final de la pantalla.
//  - Falla -> captura, video completo de la ejecución, page source y logs del dispositivo.
// VIDEO=on-failure (default) | on | off   ·   EVIDENCE=on (default) | off

import { Before, After } from '@wdio/cucumber-framework';
import { writeFileSync, mkdirSync } from 'fs';
import { resolve } from 'path';

const reportDir = resolve(__dirname, '../../reports/mobile');
const videoMode = (process.env.VIDEO ?? 'on-failure').trim().toLowerCase();
const evidenceOn = !['0', 'false', 'no', 'off'].includes((process.env.EVIDENCE ?? 'on').trim().toLowerCase());

const dir = (name: string) => {
  const d = resolve(reportDir, name);
  mkdirSync(d, { recursive: true });
  return d;
};
const safe = (s: string) => s.replace(/[<>:"/\\|?*\x00-\x1F]/g, '_').replace(/\s+/g, ' ').trim().slice(0, 100);

let recording = false;

Before(async function () {
  await browser.reloadSession();
  recording = false;
  if (videoMode === 'off') return;
  // UiAutomator2 y XCUITest graban la pantalla; si el destino no lo soporta, se sigue sin video.
  try {
    await browser.startRecordingScreen();
    recording = true;
  } catch (err) {
    console.log('>> No se pudo iniciar la grabación de pantalla:', String(err));
  }
});

After(async function (scenario) {
  const failed = scenario.result?.status !== 'PASSED';
  const name = safe(scenario.pickle?.name ?? 'escenario');
  const ts = Date.now();

  try {
    if (failed || evidenceOn) {
      const shot = await browser.takeScreenshot();
      if (shot) {
        const folder = failed ? 'screenshots' : 'evidencias';
        writeFileSync(resolve(dir(folder), `${failed ? 'error' : 'ok'}-${name}-${ts}.png`), shot, 'base64');
        if (typeof this.attach === 'function') await this.attach(shot, 'image/png');
      }
    }

    if (recording) {
      const video = await browser.stopRecordingScreen();
      if (video && (videoMode === 'on' || failed)) {
        const file = `video-${name}-${ts}.mp4`;
        // Va dentro de html/ para que el reporte (html/features/*.html) lo encuentre en ../videos/.
        writeFileSync(resolve(dir('html/videos'), file), video, 'base64');
        if (typeof this.attach === 'function') {
          await this.attach(
            `<p><strong>Video de la ejecución:</strong></p>` +
              `<video controls preload="metadata" style="max-width:100%" src="../videos/${file}"></video>` +
              `<p><a href="../videos/${file}" download>${file}</a></p>`,
            'text/html'
          );
        }
      }
    }

    if (failed && typeof this.attach === 'function') {
      const source = await browser.getPageSource().catch(() => '');
      if (source) await this.attach(`PAGE SOURCE AL FALLAR\n${source}`, 'text/plain');

      const logType = (await browser.getLogTypes().catch(() => [] as string[])).find((t) => t === 'logcat' || t === 'syslog');
      if (logType) {
        const logs = await browser.getLogs(logType).catch(() => [] as any[]);
        const tail = logs.slice(-300).map((l: any) => `${l.timestamp ?? ''} ${l.level ?? ''} ${l.message ?? ''}`);
        if (tail.length) await this.attach(`LOGS DEL DISPOSITIVO (${logType}, últimas ${tail.length} líneas)\n${tail.join('\n')}`, 'text/plain');
      }
    }
  } catch (err) {
    console.error('>> Error al guardar evidencias:', err);
  }
});

# Monitoreo sintético

`npm run monitorear` corre un smoke **liviano y de solo lectura** contra un ambiente (producción, staging…) y avisa a Slack y Teams **solo cuando algo se rompe o se recupera**.

## Qué revisa

- **URLs** (`MONITOREO_URLS` del `.env`, `--urls` o los `checks` de `input/monitoreo.json`): status esperado (por defecto 2xx), tiempo de respuesta (lento si pasa `--lenta-ms` o el `max_ms` del check), un texto que tiene que estar (`texto`) y uno que no (`no_texto`). Solo `GET` o `HEAD`.
- **Certificado TLS** de cada host `https`: avisa si vence en menos de `--tls-dias` días (14 por defecto).
- **Escenarios de k0lmena** (opcional, `--escenarios` o `"escenarios": {"correr": true}`): los `.feature` web con el tag `@sintetico`.

> Los escenarios `@sintetico` corren contra producción: tienen que ser **de solo lectura** (navegar, buscar, ver). Nada que cree, cambie o borre datos, ni formularios que se envíen, ni usuarios reales. Si un flujo necesita escribir, no es para monitoreo.

Estado de la corrida: **Caído** (algún check falla), **Degradado** (algo lento o un certificado por vencer) u **OK**. Sale con código 1 si quedó Caído.

## Configuración

`input/monitoreo.json` (ver `input/monitoreo.ejemplo.json`):

```json
{
  "nombre": "produccion",
  "checks": [
    { "nombre": "Inicio", "url": "https://mi-app.com/", "texto": "Iniciar sesión", "max_ms": 3000 },
    { "nombre": "Salud", "url": "https://api.mi-app.com/health", "metodo": "HEAD", "status": [200, 204] }
  ],
  "escenarios": { "correr": false, "tags": "@sintetico" }
}
```

Sin archivo, alcanza con `MONITOREO_URLS=https://mi-app.com,https://mi-app.com/login` en el `.env`. Los avisos usan `SLACK_WEBHOOK_URL` y `TEAMS_WEBHOOK_URL` (`scripts/avisar.py`); `MONITOREO_LINK`, si está, va como link del aviso.

## Salida

`output/monitoreo/<nombre>/`: `monitoreo.json`, `informe-monitoreo.html` (estado, qué cambió, checks, tiempos, disponibilidad por check y las corridas) e `historial/` con las últimas 30 corridas (`--corridas`).

## Programarlo

- **GitHub Actions**: `.github/workflows/monitoreo.yml` (viene con el `schedule` comentado; cargá los secrets y descomentalo). Guarda el historial entre corridas con la caché de Actions.
- **Windows (Programador de tareas)**, cada 30 minutos:
  ```powershell
  schtasks /Create /TN "k0lmenIA monitoreo" /SC MINUTE /MO 30 /TR "cmd /c cd /d C:\ruta\a\k0lmenIA && npm run monitorear >> output\monitoreo\monitoreo.log 2>&1"
  ```
- **Linux / macOS (cron)**, cada 30 minutos:
  ```cron
  */30 * * * * cd /ruta/a/k0lmenIA && npm run monitorear >> output/monitoreo/monitoreo.log 2>&1
  ```

La máquina que lo corre tiene que tener el `.env` (o las variables en el entorno), Node y Python.

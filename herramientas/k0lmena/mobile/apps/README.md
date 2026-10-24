# Apps a probar

Poné acá el `.apk` (Android) o `.ipa`/`.app` (iOS) de la app bajo prueba e indicá su nombre en `MOBILE_APP` del `.env` de la raíz de k0lmenIA.

Los binarios **no se versionan** (están en `.gitignore`): cada persona copia su propia app.

Para BrowserStack no hace falta el archivo local: subí la app a BrowserStack y poné el `bs://...` que te devuelve en `BROWSERSTACK_APP`.

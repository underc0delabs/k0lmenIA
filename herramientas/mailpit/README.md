# Mailpit — buzón de prueba para correos

[Mailpit](https://mailpit.axllent.org) (libre, MIT) es un servidor de correo **de prueba**: la aplicación le manda sus mails por SMTP y Mailpit los guarda **sin entregarlos a nadie**. Así se pueden verificar los mails de registro, recuperación de contraseña, pedidos o notificaciones sin usar casillas reales.

Lo usan el agente `verificador-correos` (`npm run correos`) y los steps de correo de k0lmena (`tools/correos/correos.steps.ts`).

## Levantarlo

Con Docker (recomendado):

```bash
docker compose -f herramientas/mailpit/docker-compose.yml up -d
```

O sin Docker: bajá el ejecutable de [github.com/axllent/mailpit/releases](https://github.com/axllent/mailpit/releases) y corré `mailpit`.

- Web y API: http://localhost:8025 (es `MAILPIT_URL` en el `.env` de la raíz).
- SMTP: `localhost:1025`, sin usuario ni TLS.

## Conectar la aplicación

En el **ambiente de pruebas** (nunca en producción), configurá el SMTP de la aplicación así:

| Dato          | Valor                                                                 |
| ------------- | --------------------------------------------------------------------- |
| Servidor SMTP | `localhost` (o la IP o el nombre de la máquina donde corre Mailpit)   |
| Puerto        | `1025`                                                                |
| Usuario/clave | cualquiera (o vacíos)                                                 |
| TLS/SSL       | desactivado                                                           |

Si la aplicación corre en otro servidor, Mailpit tiene que ser accesible desde ahí, y `MAILPIT_URL` tiene que apuntar a esa máquina.

## Usarlo

```bash
npm run correos -- --para ana@test.com --espera input/correos/espera-HU-001.json   # revisa y compara con lo esperado
npm run correos -- --para ana@test.com --esperar 1 --timeout-s 60                 # espera a que llegue después de disparar el envío
npm run correos -- --limpiar-buzon                                               # borra todo el buzón de prueba
```

Steps para los `.feature` de k0lmena (web y api):

```gherkin
Given el buzón de prueba está vacío
Then llega un correo a "ana@test.com" con el asunto "Confirmá tu cuenta"
And el correo contiene "Hola Ana"
And el correo no contiene "undefined"
And el correo tiene el adjunto "factura.pdf"
When guardo el link del correo que contiene "/confirmar" como "linkConfirmacion"
```

Mailpit además revisa la compatibilidad del HTML con los clientes de correo (Outlook, Gmail, Apple Mail…) y los links de cada mensaje: el verificador usa esas dos revisiones.

# Mapeo web · HU-950 Inicio de sesión

Ambiente: staging · headless · a partir de la bitácora input/mapeos/sesion-HU-950-web.md (sin validar con npm test, como se pidió).

| Caso | Paso | Locator | Estado | Nota |
| --- | --- | --- | --- | --- |
| CP-001 | Ingresar email y contraseña | textbox "Email", textbox "Contraseña" | Mapeado | Credenciales desde APP_USER / APP_PASSWORD |
| CP-001 | Presionar Ingresar | button "Ingresar" | Mapeado | |
| CP-001 | Ver el saludo | text "Hola, Ana" | Mapeado | |
| CP-002 | Ver el mensaje de error | alert | Mapeado | Posible bug: la app muestra "Credenciales inválidas" y el caso espera "Usuario o contraseña incorrectos". El Then queda como dice el caso |
| CP-003 | Marcar Recordarme | — | Bloqueado | No existe el checkbox en la pantalla: confirmar si la funcionalidad está en esta versión |
| CP-004 | Intentos fallidos | — | Bloqueado | Falta información FI-01 (cantidad de intentos) y bloquearía la cuenta compartida de staging |

## Para correrlo

`cd herramientas/k0lmena && TAGS=@HU-950 npm run test:web`

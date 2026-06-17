# HU-001 — Inicio de sesión

## Historia

**Como** usuario registrado
**quiero** iniciar sesión con mi email y contraseña
**para** acceder a mi cuenta y a las funcionalidades privadas.

## Criterios de aceptación

- **CA1:** El usuario puede iniciar sesión con email y contraseña válidos y accede a su dashboard.
- **CA2:** Si las credenciales son incorrectas, se muestra un mensaje de error claro y no se permite el acceso.
- **CA3:** Tras 3 intentos fallidos consecutivos, la cuenta se bloquea por 15 minutos.
- **CA4:** El campo email valida el formato (debe contener `@` y un dominio).
- **CA5:** El campo contraseña se muestra oculto y permite mostrar/ocultar su contenido.
- **CA6:** Existe un enlace "¿Olvidaste tu contraseña?" que lleva a la pantalla de recuperación.

## Notas

- Aplica a web y mobile.
- El email es el identificador único del usuario.

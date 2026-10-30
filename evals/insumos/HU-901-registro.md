# HU-901 — Registro de cuenta

**Como** visitante de la tienda
**Quiero** crear una cuenta
**Para** poder comprar y seguir mis pedidos

## Descripción

El formulario de registro pide:

- **Nombre**: obligatorio, entre 2 y 50 caracteres.
- **Email**: obligatorio, con formato válido. No puede haber dos cuentas con el mismo email.
- **Usuario**: obligatorio, entre 4 y 20 caracteres (letras, números y guion bajo).
- **Contraseña**: obligatoria.
- **Fecha de nacimiento**: obligatoria. La edad mínima para registrarse es **18 años**.

Al crear la cuenta se envía un correo de activación.

## Criterios de aceptación

- **CA1** — Con todos los datos válidos se crea la cuenta y se muestra el mensaje "¡Cuenta creada! Revisá tu correo para activarla."
- **CA2** — Si el email ya está registrado, se muestra un mensaje de error y no se crea la cuenta.
- **CA3** — La contraseña tiene que ser segura.
- **CA4** — Solo pueden registrarse personas mayores de 16 años.
- **CA5** — Si el usuario tiene menos de 4 o más de 20 caracteres, se muestra "El usuario debe tener entre 4 y 20 caracteres" y no se crea la cuenta.

## Comentarios (copiados de Jira, PROJ-901)

- **2026-09-01 — Ana Pérez (PO):** "Confirmo que el nombre admite acentos, ñ y apóstrofe (por ejemplo, O'Connor)."
- **2026-09-03 — Leo Gómez (Dev):** "¿El email distingue mayúsculas de minúsculas para detectar duplicados?" *(sin respuesta)*

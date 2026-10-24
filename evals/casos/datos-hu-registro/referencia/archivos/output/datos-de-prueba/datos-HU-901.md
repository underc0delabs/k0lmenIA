# Datos de prueba — HU-901 Registro de cuenta

| # | Nombre | Email | Usuario | Password | Nacimiento | Tipo | Resultado esperado | Falta info |
|---|---|---|---|---|---|---|---|---|
| 1 | María González | maria.gonzalez@test.ar | maria_g | Clave-Prueba-1 | 1990-05-10 | Válido | Aceptado | |
| 2 | Sean O'Connor | sean.oconnor@test.ar | sean_oc | Clave-Prueba-1 | 1988-02-01 | Válido (apóstrofe confirmado por la PO) | Aceptado | |
| 3 | Ana Díaz | ana.diaz@test.ar | abc | Clave-Prueba-1 | 1992-07-15 | De borde (mín−1) | Rechazado: El usuario debe tener entre 4 y 20 caracteres | |
| 4 | Ana Díaz | ana.diaz2@test.ar | abcd | Clave-Prueba-1 | 1992-07-15 | De borde (mín) | Aceptado | |
| 5 | Ana Díaz | ana.diaz3@test.ar | usuario_de_veinte_ch | Clave-Prueba-1 | 1992-07-15 | De borde (máx) | Aceptado | |
| 6 | Ana Díaz | ana.diaz4@test.ar | usuario_de_veintiuno_ | Clave-Prueba-1 | 1992-07-15 | De borde (máx+1) | Rechazado: El usuario debe tener entre 4 y 20 caracteres | |
| 7 | Luis Paz | luis.paz@test.ar | luis_p | Clave-Prueba-1 | (tiene 17 años) | Edad entre 16 y 18 | A confirmar (FI-01) | FI-01 |
| 8 | Luis Paz | luis.paz2@test.ar | luis_p2 | abc | 1990-01-01 | Contraseña sin reglas definidas | A confirmar (FI-02) | FI-02 |

## Falta información

| ID | Qué falta | Dónde se buscó | Filas afectadas | Pregunta para el PO | Estado |
|---|---|---|---|---|---|
| FI-01 | Edad mínima: la descripción dice 18 y el CA4 dice 16 | Historia HU-901 | 7 | ¿La edad mínima es 16 o 18? | Abierto |
| FI-02 | Reglas de la contraseña "segura" (CA3) | Historia HU-901 | 8 | ¿Qué reglas tiene que cumplir? | Abierto |

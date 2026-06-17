# Casos de prueba — HU-001 — Inicio de sesión

## Resumen

```
+--------+--------------------------+----------------------------------------+-------------+
| ID     | Título                   | Resultado esperado                     | Prioridad   |
+========+==========================+========================================+=============+
| CP-003 | Bloqueo de cuenta tras 3 | Tras el 3.º intento la cuenta queda    | Crítica     |
|        | intentos fallidos        | bloqueada 15 min; el intento posterior |             |
|        |                          | se rechaza aun con la contraseña       |             |
|        |                          | correcta.                              |             |
+--------+--------------------------+----------------------------------------+-------------+
| CP-001 | Login con credenciales   | El sistema autentica al usuario y lo   | Alta        |
|        | válidas                  | redirige a su dashboard.               |             |
+--------+--------------------------+----------------------------------------+-------------+
| CP-002 | Login con contraseña     | El sistema no permite el acceso y      | Alta        |
|        | incorrecta               | muestra un mensaje de error claro.     |             |
+--------+--------------------------+----------------------------------------+-------------+
```

## Detalle de los casos

```
+--------+---------------+----------------------+------------------+-------------------+----------------------+----------------------+-----------+-------------+---------------+
| ID #   | Título        | Descripción          | Precondiciones   | Datos de Prueba   | Pasos                | Resultado Esperado   | Estado    | Prioridad   | #Etiquetas    |
+========+===============+======================+==================+===================+======================+======================+===========+=============+===============+
| CP-003 | Bloqueo de    | Verifica que la      | Usuario          | Email: maria.gon  | 1. Acceder al login  | Tras el 3.º intento  | Pendiente | Crítica     | @login        |
|        | cuenta tras 3 | cuenta se bloquee 15 | registrado,      | zalez@test.ar     | 2. Contraseña        | la cuenta queda      |           |             | @seguridad    |
|        | intentos      | minutos tras 3       | cuenta activa y  | Contraseña:       | incorrecta (intento  | bloqueada 15 min; el |           |             | @HU-001 @CA3  |
|        | fallidos      | intentos fallidos    | sin intentos     | Incorrecta123     | 1)                   | intento posterior se |           |             |               |
|        |               | consecutivos (CA3).  | previos.         | (x3)              | 3. Repetir (intento  | rechaza aun con la   |           |             |               |
|        |               |                      |                  |                   | 2)                   | contraseña correcta. |           |             |               |
|        |               |                      |                  |                   | 4. Repetir (intento  |                      |           |             |               |
|        |               |                      |                  |                   | 3)                   |                      |           |             |               |
|        |               |                      |                  |                   | 5. Reintentar con la |                      |           |             |               |
|        |               |                      |                  |                   | correcta             |                      |           |             |               |
+--------+---------------+----------------------+------------------+-------------------+----------------------+----------------------+-----------+-------------+---------------+
| CP-001 | Login con     | Verifica que un      | Usuario          | Email: maria.gon  | 1. Acceder a la      | El sistema autentica | Pendiente | Alta        | @login @smoke |
|        | credenciales  | usuario registrado   | registrado, con  | zalez@test.ar     | pantalla de login    | al usuario y lo      |           |             | @HU-001 @CA1  |
|        | válidas       | pueda iniciar sesión | cuenta activa y  | Contraseña:       | 2. Ingresar el email | redirige a su        |           |             |               |
|        |               | con email y          | no bloqueada.    | Test1234          | registrado           | dashboard.           |           |             |               |
|        |               | contraseña válidos y |                  |                   | 3. Ingresar la       |                      |           |             |               |
|        |               | acceda a su          |                  |                   | contraseña correcta  |                      |           |             |               |
|        |               | dashboard (CA1).     |                  |                   | 4. Presionar         |                      |           |             |               |
|        |               |                      |                  |                   | "Iniciar sesión"     |                      |           |             |               |
+--------+---------------+----------------------+------------------+-------------------+----------------------+----------------------+-----------+-------------+---------------+
| CP-002 | Login con     | Verifica que el      | Usuario          | Email: maria.gon  | 1. Acceder a la      | El sistema no        | Pendiente | Alta        | @login        |
|        | contraseña    | sistema rechace el   | registrado, con  | zalez@test.ar     | pantalla de login    | permite el acceso y  |           |             | @negativo     |
|        | incorrecta    | acceso cuando la     | cuenta activa y  | Contraseña:       | 2. Ingresar el email | muestra un mensaje   |           |             | @HU-001 @CA2  |
|        |               | contraseña no        | no bloqueada.    | Incorrecta123     | registrado           | de error claro.      |           |             |               |
|        |               | coincide (CA2).      |                  |                   | 3. Ingresar una      |                      |           |             |               |
|        |               |                      |                  |                   | contraseña           |                      |           |             |               |
|        |               |                      |                  |                   | incorrecta           |                      |           |             |               |
|        |               |                      |                  |                   | 4. Presionar         |                      |           |             |               |
|        |               |                      |                  |                   | "Iniciar sesión"     |                      |           |             |               |
+--------+---------------+----------------------+------------------+-------------------+----------------------+----------------------+-----------+-------------+---------------+
```


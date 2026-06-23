# Casos de prueba — HU-001 — Inicio de sesión

## Resumen

```
+--------+--------------------------+----------------------------------+-------------+
| ID     | Título                   | Resultado esperado               | Prioridad   |
+========+==========================+==================================+=============+
| CP-003 | Bloqueo de cuenta tras 3 | Tras el 3.º intento la cuenta    | Crítica     |
|        | intentos fallidos        | queda bloqueada 15 min; el       |             |
|        |                          | intento posterior se rechaza aun |             |
|        |                          | con la contraseña correcta.      |             |
+--------+--------------------------+----------------------------------+-------------+
| CP-001 | Login con credenciales   | El sistema autentica al usuario  | Alta        |
|        | válidas                  | y lo redirige a su dashboard.    |             |
+--------+--------------------------+----------------------------------+-------------+
| CP-002 | Login con contraseña     | El sistema no permite el acceso  | Alta        |
|        | incorrecta               | y muestra un mensaje de error    |             |
|        |                          | claro.                           |             |
+--------+--------------------------+----------------------------------+-------------+
```

## Detalle de los casos

```
+--------+---------------+------------------------+------------------+--------------------+--------------------------+----------------------+-------------+--------------+
| ID #   | Título        | Descripción            | Precondiciones   | Datos de Prueba    | Pasos                    | Resultado Esperado   | Prioridad   | #Etiquetas   |
+========+===============+========================+==================+====================+==========================+======================+=============+==============+
| CP-003 | Bloqueo de    | Verifica que la cuenta | Usuario          | Email: maria.gonza | 1. Acceder al login      | Tras el 3.º intento  | Crítica     | @login       |
|        | cuenta tras 3 | se bloquee 15 minutos  | registrado,      | lez@test.ar        | 2. Contraseña incorrecta | la cuenta queda      |             | @seguridad   |
|        | intentos      | tras 3 intentos        | cuenta activa y  | Contraseña:        | (intento 1)              | bloqueada 15 min; el |             | @HU-001 @CA3 |
|        | fallidos      | fallidos consecutivos  | sin intentos     | Incorrecta123 (x3) | 3. Repetir (intento 2)   | intento posterior se |             |              |
|        |               | (CA3).                 | previos.         |                    | 4. Repetir (intento 3)   | rechaza aun con la   |             |              |
|        |               |                        |                  |                    | 5. Reintentar con la     | contraseña correcta. |             |              |
|        |               |                        |                  |                    | correcta                 |                      |             |              |
+--------+---------------+------------------------+------------------+--------------------+--------------------------+----------------------+-------------+--------------+
| CP-001 | Login con     | Verifica que un        | Usuario          | Email: maria.gonza | 1. Acceder a la pantalla | El sistema autentica | Alta        | @login       |
|        | credenciales  | usuario registrado     | registrado, con  | lez@test.ar        | de login                 | al usuario y lo      |             | @smoke       |
|        | válidas       | pueda iniciar sesión   | cuenta activa y  | Contraseña:        | 2. Ingresar el email     | redirige a su        |             | @HU-001 @CA1 |
|        |               | con email y contraseña | no bloqueada.    | Test1234           | registrado               | dashboard.           |             |              |
|        |               | válidos y acceda a su  |                  |                    | 3. Ingresar la           |                      |             |              |
|        |               | dashboard (CA1).       |                  |                    | contraseña correcta      |                      |             |              |
|        |               |                        |                  |                    | 4. Presionar "Iniciar    |                      |             |              |
|        |               |                        |                  |                    | sesión"                  |                      |             |              |
+--------+---------------+------------------------+------------------+--------------------+--------------------------+----------------------+-------------+--------------+
| CP-002 | Login con     | Verifica que el        | Usuario          | Email: maria.gonza | 1. Acceder a la pantalla | El sistema no        | Alta        | @login       |
|        | contraseña    | sistema rechace el     | registrado, con  | lez@test.ar        | de login                 | permite el acceso y  |             | @negativo    |
|        | incorrecta    | acceso cuando la       | cuenta activa y  | Contraseña:        | 2. Ingresar el email     | muestra un mensaje   |             | @HU-001 @CA2 |
|        |               | contraseña no coincide | no bloqueada.    | Incorrecta123      | registrado               | de error claro.      |             |              |
|        |               | (CA2).                 |                  |                    | 3. Ingresar una          |                      |             |              |
|        |               |                        |                  |                    | contraseña incorrecta    |                      |             |              |
|        |               |                        |                  |                    | 4. Presionar "Iniciar    |                      |             |              |
|        |               |                        |                  |                    | sesión"                  |                      |             |              |
+--------+---------------+------------------------+------------------+--------------------+--------------------------+----------------------+-------------+--------------+
```


# Casos de prueba — HU-001 — Inicio de sesión

## Resumen

```
+--------+--------------------------+---------------------------------+-------------+----------+--------------+
| ID     | Título                   | Resultado esperado              | Prioridad   | Tiempo   | Falta info   |
+========+==========================+=================================+=============+==========+==============+
| CP-001 | Bloqueo de cuenta tras 3 | Tras el 3.º intento la cuenta   | Crítica     | 7,5 min  | FI-01,       |
|        | intentos fallidos        | queda bloqueada (duración:      |             |          | FI-02        |
|        |                          | FI-02); el intento posterior se |             |          |              |
|        |                          | rechaza aun con la contraseña   |             |          |              |
|        |                          | correcta.                       |             |          |              |
+--------+--------------------------+---------------------------------+-------------+----------+--------------+
| CP-002 | Login con credenciales   | El sistema autentica al usuario | Alta        | 6 min    |              |
|        | válidas                  | y lo redirige a su dashboard.   |             |          |              |
+--------+--------------------------+---------------------------------+-------------+----------+--------------+
| CP-003 | Login con contraseña     | El sistema no permite el acceso | Alta        | 7 min    |              |
|        | incorrecta               | y muestra un mensaje de error   |             |          |              |
|        |                          | claro.                          |             |          |              |
+--------+--------------------------+---------------------------------+-------------+----------+--------------+
```

**Tiempo estimado de ejecución manual:** 20,5 min en total (fórmula en `plantillas/estimacion-tiempos.md`).

## Detalle de los casos

```
+--------+---------------+------------------------+------------------+--------------------+--------------------------+----------------------+-------------+----------+--------------+
| ID #   | Título        | Descripción            | Precondiciones   | Datos de Prueba    | Pasos                    | Resultado Esperado   | Prioridad   | Tiempo   | #Etiquetas   |
+========+===============+========================+==================+====================+==========================+======================+=============+==========+==============+
| CP-001 | Bloqueo de    | Verifica que la cuenta | Usuario          | Email: maria.gonza | 1. Acceder al login      | Tras el 3.º intento  | Crítica     | 7,5 min  | @login       |
|        | cuenta tras 3 | se bloquee tras 3      | registrado,      | lez@test.ar        | 2. Contraseña incorrecta | la cuenta queda      |             |          | @seguridad   |
|        | intentos      | intentos fallidos      | cuenta activa y  | Contraseña:        | (intento 1)              | bloqueada (duración: |             |          | @HU-001 @CA3 |
|        | fallidos      | consecutivos (CA3).    | sin intentos     | Incorrecta123 (x3) | 3. Repetir (intento 2)   | FI-02); el intento   |             |          | @falta-info  |
|        |               |                        | previos.         |                    | 4. Repetir (intento 3)   | posterior se rechaza |             |          |              |
|        |               |                        |                  |                    | 5. Reintentar con la     | aun con la           |             |          |              |
|        |               |                        |                  |                    | correcta                 | contraseña correcta. |             |          |              |
+--------+---------------+------------------------+------------------+--------------------+--------------------------+----------------------+-------------+----------+--------------+
| CP-002 | Login con     | Verifica que un        | Usuario          | Email: maria.gonza | 1. Acceder a la pantalla | El sistema autentica | Alta        | 6 min    | @login       |
|        | credenciales  | usuario registrado     | registrado, con  | lez@test.ar        | de login                 | al usuario y lo      |             |          | @smoke       |
|        | válidas       | pueda iniciar sesión   | cuenta activa y  | Contraseña:        | 2. Ingresar el email     | redirige a su        |             |          | @HU-001 @CA1 |
|        |               | con email y contraseña | no bloqueada.    | Test1234           | registrado               | dashboard.           |             |          |              |
|        |               | válidos y acceda a su  |                  |                    | 3. Ingresar la           |                      |             |          |              |
|        |               | dashboard (CA1).       |                  |                    | contraseña correcta      |                      |             |          |              |
|        |               |                        |                  |                    | 4. Presionar "Iniciar    |                      |             |          |              |
|        |               |                        |                  |                    | sesión"                  |                      |             |          |              |
+--------+---------------+------------------------+------------------+--------------------+--------------------------+----------------------+-------------+----------+--------------+
| CP-003 | Login con     | Verifica que el        | Usuario          | Email: maria.gonza | 1. Acceder a la pantalla | El sistema no        | Alta        | 7 min    | @login       |
|        | contraseña    | sistema rechace el     | registrado, con  | lez@test.ar        | de login                 | permite el acceso y  |             |          | @negativo    |
|        | incorrecta    | acceso cuando la       | cuenta activa y  | Contraseña:        | 2. Ingresar el email     | muestra un mensaje   |             |          | @HU-001 @CA2 |
|        |               | contraseña no coincide | no bloqueada.    | Incorrecta123      | registrado               | de error claro.      |             |          |              |
|        |               | (CA2).                 |                  |                    | 3. Ingresar una          |                      |             |          |              |
|        |               |                        |                  |                    | contraseña incorrecta    |                      |             |          |              |
|        |               |                        |                  |                    | 4. Presionar "Iniciar    |                      |             |          |              |
|        |               |                        |                  |                    | sesión"                  |                      |             |          |              |
+--------+---------------+------------------------+------------------+--------------------+--------------------------+----------------------+-------------+----------+--------------+
```

## Falta información

Datos que no aparecen en ninguna fuente consultada. Los casos que dependen de ellos llevan la etiqueta `@falta-info`: CP-001 (FI-01, FI-02).

```
+-------+----------------------------------------+-------------------------------+--------------+-----------------------------------+----------+
| ID    | Qué falta                              | Dónde se buscó                | Impacto      | Pregunta para el PO               | Estado   |
+=======+========================================+===============================+==============+===================================+==========+
| FI-01 | Texto del mensaje al quedar la cuenta  | Historia, comentarios, Figma, | CA3 · CP-001 | ¿Cuál es el mensaje exacto al     | Abierto  |
|       | bloqueada                              | Confluence                    |              | bloquearse?                       |          |
+-------+----------------------------------------+-------------------------------+--------------+-----------------------------------+----------+
| FI-02 | Duración del bloqueo (15 o 30 minutos) | Historia, Confluence (se      | CA3 · CP-001 | ¿El bloqueo dura 15 o 30 minutos? | Abierto  |
|       |                                        | contradicen)                  |              |                                   |          |
+-------+----------------------------------------+-------------------------------+--------------+-----------------------------------+----------+
```

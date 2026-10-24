# Cobertura BDD — [HU-XXX — Módulo]

> Informe complementario al archivo `HU-XXX-nombre.feature`.
> Mapea cada criterio de aceptación a los escenarios que lo cubren.
>
> _(Ejemplo orientativo sobre HU-001 — Inicio de sesión.)_

## Resumen

- **Historia:** HU-001 — Inicio de sesión
- **Escenarios generados:** 4
- **Criterios de aceptación cubiertos:** 3 de 3

## Cobertura por criterio

```
+------------+------------------------------------+-----------------------------------------+-----------------------------+
| Criterio   | Descripción                        | Escenarios que lo cubren                | Cobertura                   |
+============+====================================+=========================================+=============================+
| CA1        | Login con credenciales válidas     | CP-001 — Login con credenciales válidas | Cubierto                    |
+------------+------------------------------------+-----------------------------------------+-----------------------------+
| CA2        | Rechazo con credenciales inválidas | CP-002 — Login con email de formato     | Cubierto                    |
|            |                                    | inválido (Scenario Outline); CP-003 —   |                             |
|            |                                    | Login con contraseña incorrecta         |                             |
+------------+------------------------------------+-----------------------------------------+-----------------------------+
| CA3        | Bloqueo tras 3 intentos fallidos   | CP-004 — Bloqueo de cuenta tras 3       | Parcial (falta información) |
|            |                                    | intentos                                |                             |
+------------+------------------------------------+-----------------------------------------+-----------------------------+
```

## Detalle de escenarios por criterio

```
+------------+------------------------------------------+------------------+------------------------------------------+
| Criterio   | Escenario                                | Tipo             | Pasos clave                              |
+============+==========================================+==================+==========================================+
| CA1        | CP-001 — Login con credenciales válidas  | Camino feliz     | Given usuario registrado, When ingresa   |
|            |                                          |                  | credenciales válidas, Then accede al     |
|            |                                          |                  | dashboard                                |
+------------+------------------------------------------+------------------+------------------------------------------+
| CA2        | CP-002 — Login con email de formato      | Negativo         | When ingresa un email sin formato válido |
|            | inválido                                 |                  | (Examples), Then ve el mensaje de        |
|            |                                          |                  | formato inválido                         |
+------------+------------------------------------------+------------------+------------------------------------------+
| CA2        | CP-003 — Login con contraseña incorrecta | Negativo         | When ingresa una contraseña incorrecta,  |
|            |                                          |                  | Then ve el mensaje de error              |
+------------+------------------------------------------+------------------+------------------------------------------+
| CA3        | CP-004 — Bloqueo de cuenta tras 3        | Negativo / borde | Given 2 intentos fallidos previos, When  |
|            | intentos                                 |                  | falla el tercer intento, Then la cuenta  |
|            |                                          |                  | queda bloqueada (duración: FI-02)        |
+------------+------------------------------------------+------------------+------------------------------------------+
```

## Falta información

Datos que no aparecen en ninguna fuente. Los escenarios que dependen de ellos llevan `@falta-info @FI-XX` y el comentario `# FALTA INFORMACIÓN (FI-XX): …` en el `.feature`.

```
+-------+----------------------------------------+------------------------------------------+--------------+-----------------------------------+----------+
| ID    | Qué falta                              | Dónde se buscó                           | Afecta a     | Pregunta para el PO               | Estado   |
+=======+========================================+==========================================+==============+===================================+==========+
| FI-01 | Texto del mensaje al quedar la cuenta  | Historia, comentarios, Figma, Confluence | CA3 · CP-004 | ¿Cuál es el mensaje exacto al     | Abierto  |
|       | bloqueada                              |                                          |              | bloquearse?                       |          |
+-------+----------------------------------------+------------------------------------------+--------------+-----------------------------------+----------+
| FI-02 | Duración del bloqueo (15 o 30 minutos) | Historia, Confluence (se contradicen)    | CA3 · CP-004 | ¿El bloqueo dura 15 o 30 minutos? | Abierto  |
+-------+----------------------------------------+------------------------------------------+--------------+-----------------------------------+----------+
```

## Pendientes / por confirmar

Los `FI-XX` abiertos (marcados con `# FALTA INFORMACIÓN` en el `.feature`) y lo que falte definir antes de automatizar:

- Duración exacta del bloqueo de cuenta tras 3 intentos fallidos (a confirmar con el PO).
- Texto exacto de los mensajes de error.

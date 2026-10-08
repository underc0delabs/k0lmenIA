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
+------------+------------------------------------+-------------------------------------+-------------+
| Criterio   | Descripción                        | Escenarios que lo cubren            | Cobertura   |
+============+====================================+=====================================+=============+
| CA1        | Login con credenciales válidas     | Login con credenciales válidas      | Cubierto    |
+------------+------------------------------------+-------------------------------------+-------------+
| CA2        | Rechazo con credenciales inválidas | Login con datos inválidos (Scenario | Cubierto    |
|            |                                    | Outline)                            |             |
+------------+------------------------------------+-------------------------------------+-------------+
| CA3        | Bloqueo tras 3 intentos fallidos   | Bloqueo de cuenta tras 3 intentos   | Parcial     |
+------------+------------------------------------+-------------------------------------+-------------+
```

## Detalle de escenarios por criterio

```
+------------+-----------------------------------+------------------+------------------------------------------+
| Criterio   | Escenario                         | Tipo             | Pasos clave                              |
+============+===================================+==================+==========================================+
| CA1        | Login con credenciales válidas    | Camino feliz     | Given usuario registrado, When ingresa   |
|            |                                   |                  | credenciales válidas, Then accede al     |
|            |                                   |                  | dashboard                                |
+------------+-----------------------------------+------------------+------------------------------------------+
| CA2        | Login con datos inválidos         | Negativo         | When ingresa email o password inválidos, |
|            |                                   |                  | Then ve el mensaje de error              |
|            |                                   |                  | correspondiente                          |
+------------+-----------------------------------+------------------+------------------------------------------+
| CA3        | Bloqueo de cuenta tras 3 intentos | Negativo / borde | Given 2 intentos fallidos previos, When  |
|            |                                   |                  | falla el tercer intento, Then la cuenta  |
|            |                                   |                  | queda bloqueada 15 minutos               |
+------------+-----------------------------------+------------------+------------------------------------------+
```

## Falta información

Datos que no aparecen en ninguna fuente. Los escenarios que dependen de ellos llevan `@falta-info @FI-XX` y el comentario `# FALTA INFORMACIÓN (FI-XX): …` en el `.feature`.

```
+-------+----------------------------------------+------------------------------------------+-------------------------+-----------------------------------+----------+
| ID    | Qué falta                              | Dónde se buscó                           | Afecta a                | Pregunta para el PO               | Estado   |
+=======+========================================+==========================================+=========================+===================================+==========+
| FI-01 | Texto del mensaje al quedar la cuenta  | Historia, comentarios, Figma, Confluence | CA3 · Bloqueo de cuenta | ¿Cuál es el mensaje exacto al     | Abierto  |
|       | bloqueada                              |                                          |                         | bloquearse?                       |          |
+-------+----------------------------------------+------------------------------------------+-------------------------+-----------------------------------+----------+
| FI-02 | Duración del bloqueo (15 o 30 minutos) | Historia, Confluence (se contradicen)    | CA3 · Bloqueo de cuenta | ¿El bloqueo dura 15 o 30 minutos? | Abierto  |
+-------+----------------------------------------+------------------------------------------+-------------------------+-----------------------------------+----------+
```

## Pendientes / por confirmar

Lo que quedó marcado con `# TODO` en el `.feature` o falta definir antes de automatizar:

- Duración exacta del bloqueo de cuenta tras 3 intentos fallidos (a confirmar con el PO).
- Texto exacto de los mensajes de error.

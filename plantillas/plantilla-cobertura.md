# Cobertura de pruebas — [HU-XXX — Módulo]

> Informe complementario a la planilla de casos `casos-HU-XXX.xlsx`.
> Resume **qué cubren** las pruebas, señala **ambigüedades** y deja **preguntas para el PO**.
>
> _(Ejemplo orientativo sobre HU-001 — Inicio de sesión.)_

## Resumen

- **Historia:** HU-001 — Inicio de sesión
- **Casos generados:** 5 (CP-001 a CP-005)
- **Criterios de aceptación cubiertos:** 3 de 3
- **Tipos de prueba:** positivos (1), negativos (3), de borde (1)

## Cobertura por criterio de aceptación

```
+------------+-----------------------------------+-----------------------+-----------------------------+
| Criterio   | Descripción                       | Casos que lo cubren   | Cobertura                   |
+============+===================================+=======================+=============================+
| CA1        | Login con credenciales válidas    | CP-002                | Cubierto                    |
+------------+-----------------------------------+-----------------------+-----------------------------+
| CA2        | Rechazo con contraseña incorrecta | CP-003                | Cubierto                    |
+------------+-----------------------------------+-----------------------+-----------------------------+
| CA3        | Bloqueo tras 3 intentos fallidos  | CP-001                | Parcial (falta información) |
+------------+-----------------------------------+-----------------------+-----------------------------+
```

## Cobertura por tipo de prueba

- **Positivos:** CP-002 (login con datos válidos).
- **Negativos:** CP-003, CP-004, CP-005.
- **De borde:** CP-001 (bloqueo exactamente en el 3.º intento). Técnica: transición de estados (Activa → Bloqueada al 3.º intento fallido; Bloqueada + contraseña correcta → rechazado).
- **Validaciones de campos:** CP-005 (campos obligatorios).

## Fuera de alcance / no cubierto

- Recuperación de contraseña (no es parte de HU-001).
- Inicio de sesión con redes sociales (no mencionado).

## Falta información

Datos que no aparecen en ninguna fuente (historia, comentarios, subtareas, épica, Confluence, Figma). Los casos que dependen de ellos están resaltados en la planilla y llevan la etiqueta `@falta-info`. Vienen de la ficha `output/contexto/contexto-HU-001.md`.

```
+-------+----------------------------------------+------------------------------------------+--------------+-----------------------------------+----------+
| ID    | Qué falta                              | Dónde se buscó                           | Afecta a     | Pregunta para el PO               | Estado   |
+=======+========================================+==========================================+==============+===================================+==========+
| FI-01 | Texto del mensaje al quedar la cuenta  | Historia, comentarios, Figma, Confluence | CA3 · CP-001 | ¿Cuál es el mensaje exacto al     | Abierto  |
|       | bloqueada                              |                                          |              | bloquearse?                       |          |
+-------+----------------------------------------+------------------------------------------+--------------+-----------------------------------+----------+
| FI-02 | Duración del bloqueo (15 o 30 minutos) | Historia, Confluence (se contradicen)    | CA3 · CP-001 | ¿El bloqueo dura 15 o 30 minutos? | Abierto  |
+-------+----------------------------------------+------------------------------------------+--------------+-----------------------------------+----------+
```

## Ambigüedades detectadas

Puntos de la historia que no están claros o están incompletos. **No se inventaron valores:** donde hizo falta suponer algo, se aclaró el supuesto en `Comentarios` de la planilla y se listó acá.

1. **Duración del bloqueo:** la historia dice "bloqueo temporal" pero no indica cuántos minutos y Confluence dice 15 o 30. _(No se eligió un valor: CP-001 queda ligado a FI-02.)_
2. **Reinicio del contador de intentos:** no se aclara si los 3 intentos se cuentan por sesión, por tiempo, o hasta un login exitoso.
3. **Mensaje de error:** no se especifica el texto exacto que ve el usuario al fallar el login o al bloquearse la cuenta.

## Preguntas para el PO

1. ¿Cuánto dura exactamente el bloqueo de cuenta tras los 3 intentos fallidos?
2. ¿El contador de intentos se reinicia por tiempo, tras un login exitoso, o nunca?
3. ¿Cuál es el mensaje exacto al ingresar credenciales incorrectas? ¿Y al quedar bloqueado?

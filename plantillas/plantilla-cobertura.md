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
+------------+-----------------------------------+-----------------------+-------------+
| Criterio   | Descripción                       | Casos que lo cubren   | Cobertura   |
+============+===================================+=======================+=============+
| CA1        | Login con credenciales válidas    | CP-001                | Cubierto    |
+------------+-----------------------------------+-----------------------+-------------+
| CA2        | Rechazo con contraseña incorrecta | CP-002                | Cubierto    |
+------------+-----------------------------------+-----------------------+-------------+
| CA3        | Bloqueo tras 3 intentos fallidos  | CP-003                | Cubierto    |
+------------+-----------------------------------+-----------------------+-------------+
```

## Cobertura por tipo de prueba

- **Positivos:** CP-001 (login con datos válidos).
- **Negativos:** CP-002, CP-004, CP-005.
- **De borde:** CP-003 (bloqueo exactamente en el 3.º intento).
- **Validaciones de campos:** CP-005 (campos obligatorios).

## Fuera de alcance / no cubierto

- Recuperación de contraseña (no es parte de HU-001).
- Inicio de sesión con redes sociales (no mencionado).

## Ambigüedades detectadas

Puntos de la historia que no están claros o están incompletos. **No se inventaron valores:** donde hizo falta suponer algo, se aclaró el supuesto en `Comentarios` de la planilla y se listó acá.

1. **Duración del bloqueo:** la historia dice "bloqueo temporal" pero no indica cuántos minutos. _(Supuesto usado en CP-003: 15 min, a confirmar.)_
2. **Reinicio del contador de intentos:** no se aclara si los 3 intentos se cuentan por sesión, por tiempo, o hasta un login exitoso.
3. **Mensaje de error:** no se especifica el texto exacto que ve el usuario al fallar el login o al bloquearse la cuenta.

## Preguntas para el PO

1. ¿Cuánto dura exactamente el bloqueo de cuenta tras los 3 intentos fallidos?
2. ¿El contador de intentos se reinicia por tiempo, tras un login exitoso, o nunca?
3. ¿Cuál es el mensaje exacto al ingresar credenciales incorrectas? ¿Y al quedar bloqueado?

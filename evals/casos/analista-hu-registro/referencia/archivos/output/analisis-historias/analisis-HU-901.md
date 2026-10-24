# Análisis de la historia HU-901 — Registro de cuenta

## Resumen

La historia define el alta de una cuenta con nombre, email, usuario, contraseña y fecha de nacimiento. Tiene una contradicción en la edad mínima, un criterio de contraseña sin reglas y un mensaje de error sin definir.

## Evaluación

| Criterio | Claro | Verificable | Observación |
|---|---|---|---|
| CA1 | Sí | Sí | Mensaje de éxito definido |
| CA2 | Parcial | No | El texto del error de email duplicado no está definido (FI-02) |
| CA3 | No | No | "Contraseña segura" sin reglas (FI-03) |
| CA4 | No | No | Contradice la descripción: 16 años en el CA4 y 18 en la descripción (FI-01) |
| CA5 | Sí | Sí | Límites 4 y 20 con el mensaje definido |

## Ambigüedades

- La edad mínima: la descripción dice 18 años y el CA4 dice 16 años (FI-01).
- La contraseña "segura" no define reglas ni requisitos: largo, mayúsculas, números o símbolos (FI-03).
- El CA2 no define el texto del mensaje cuando el email ya está registrado (FI-02).

## Escenarios no contemplados

- El email con mayúsculas: ¿"Ana@Test.com" y "ana@test.com" son el mismo? (pregunta abierta del dev, FI-04).
- Qué pasa si el correo de activación no llega.

## Riesgos

- Que desarrollo implemente 16 y el negocio espere 18: personas menores registradas.
- Que cada equipo interprete distinto la contraseña segura.

## Preguntas

1. ¿La edad mínima es 16 o 18 años?
2. ¿Qué reglas tiene que cumplir una contraseña segura?
3. ¿Cuál es el texto exacto del error cuando el email ya está registrado?
4. ¿El email distingue mayúsculas de minúsculas para detectar duplicados?

## Recomendaciones

- Resolver FI-01 a FI-04 en el refinamiento antes de escribir los casos.

## Falta información

| ID | Qué falta | Pregunta para el PO |
|---|---|---|
| FI-01 | Edad mínima (16 o 18) | ¿Cuál vale? |
| FI-02 | Texto del error de email duplicado | ¿Qué mensaje se muestra? |
| FI-03 | Reglas de la contraseña segura | ¿Qué reglas aplica? |
| FI-04 | Mayúsculas en el email | ¿Distingue mayúsculas? |

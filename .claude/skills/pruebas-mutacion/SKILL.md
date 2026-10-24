---
name: pruebas-mutacion
description: El cómo del mutation testing — mutantes y mutadores, estados (killed, survived, no coverage), mutation score y por qué supera al coverage de líneas, mutantes equivalentes, cómo acotar el costo y herramientas por lenguaje (Stryker, mutmut, PITest, Infection). Lo usa el analista-mutacion; complementa a analista-cobertura.
---

# Mutation testing (calidad de la suite de tests)

El coverage dice **qué código se ejecuta** en los tests; no dice si realmente se **verifica**. El mutation testing lo mide: introduce pequeños cambios (**mutantes**) en el código y, si los tests siguen en verde, ese mutante **sobrevivió** → hay un test que falta o una aserción débil. Es "probar que tus pruebas sirven". Complementa a `analista-cobertura`.

## 1. Mutantes y mutadores

- Un **mutador** cambia algo mínimo: un operador (`+`→`-`, `>`→`>=`), un booleano (`true`→`false`), un límite, un `return`, una condición, o **borra una línea**.
- Cada cambio genera un **mutante**. Se corre la suite contra cada uno.

## 2. Estados y mutation score

- **Killed**: algún test falló → el mutante fue detectado (bien).
- **Survived**: todos los tests pasaron igual → **no detectado** (hay un hueco).
- **No coverage**: el mutante está en código que ningún test ejecuta.
- **Timeout**: el mutante colgó (cuenta como detectado); **Compile error** / **Ignored**: se excluyen del cálculo.
- **Mutation score** = (killed + timeout) / (killed + timeout + survived + no coverage) × 100. Es **mejor señal que el coverage de líneas**.

## 3. Sobrevivientes y equivalentes

- Un **mutante sobreviviente** señala un test faltante o una aserción floja: es lo accionable. Por cada uno, ¿qué caso o assertion lo mataría?
- Un **mutante equivalente** no cambia el comportamiento observable (p. ej. un cambio que igual da el mismo resultado): es un **falso positivo** que se marca como ignorado, no se "arregla". Distinguirlos es el criterio humano clave.

## 4. Costo: cómo acotarlo

- La mutación es **cara** (corre la suite N veces). Para que sea viable:
  - **Incremental**: mutar solo el **diff** (lo que cambió en el PR/rama), no todo el repo.
  - **Por módulo crítico**: enfocá la lógica de negocio/dinero, no el código trivial.
  - Límites de concurrencia y timeout; excluir generado/vendored.
- **Requisito**: la suite tiene que estar **verde y ser rápida** antes de mutar (un test inestable arruina la medición).

## 5. Herramientas por lenguaje

- **JS/TS/C#/Scala**: Stryker (emite el **reporte JSON estándar** que lee `npm run mutacion`).
- **Python**: mutmut o cosmic-ray. **JVM**: PITest. **PHP**: Infection. **Go**: go-mutesting.

## 6. Flujo

1. Confirmá que la suite esté **verde y rápida**.
2. Corré la herramienta de mutación (sobre el diff o un módulo), generá el reporte.
3. Leé el reporte con `npm run mutacion` (`herramientas/mutacion/mutacion.py`): mutation score global y por archivo, sobrevivientes y archivos bajo el umbral.
4. **Triage de sobrevivientes**: separá los equivalentes (ignorar, con motivo) de los reales (test/assertion que falta); priorizá por criticidad del archivo.
5. Recomendá los tests/aserciones concretos que matarían a los sobrevivientes reales.

## 7. Umbrales

- Fijá un **score mínimo** por proyecto/módulo (p. ej. 70-80% en la lógica crítica); no exijas 100% (los equivalentes lo hacen imposible). Útil como gate de PR sobre el diff.

## 8. Bugs/olores típicos que revela

- Tests que ejecutan el código pero **no afirman** nada (coverage alto, score bajo).
- Aserciones débiles (chequean que "no explota" pero no el resultado).
- Ramas/condiciones límite sin test (el mutante de `>`→`>=` sobrevive).
- Manejo de errores sin test (borrar el `throw` sobrevive).

## 9. Preguntas típicas para el equipo

Cuando no está escrito, son `FI-XX`:

- ¿Qué lenguaje/stack de tests y qué herramienta de mutación aplica?
- ¿La suite está verde y es rápida? ¿Hay tests inestables a excluir?
- ¿Mutamos todo, el diff o un módulo crítico? ¿Qué umbral se espera?
- ¿Qué partes del código son las críticas (dinero, seguridad, cálculos)?

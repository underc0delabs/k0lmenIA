# Técnicas de diseño de pruebas — detalle

Referencia ampliada del skill `tecnicas-de-diseno`. Para cada técnica: qué es, cuándo usarla, cómo aplicarla, un ejemplo trabajado y errores comunes.

---

## 1. Clases de equivalencia (Equivalence Partitioning)

**Qué es.** Dividir el universo de entradas posibles en grupos ("clases") que el sistema debería tratar de la misma manera. Si un valor de la clase funciona, se asume que todos los de esa clase funcionan igual, así que se prueba **un representante por clase** en lugar de todos los valores.

**Cuándo.** Entradas con rangos o con categorías; siempre que probar "todos los valores" sea inviable.

**Cómo.**
1. Por cada entrada, identificá las clases **válidas** (lo que el sistema acepta) y las **inválidas** (lo que debe rechazar).
2. Elegí un representante de cada clase.
3. Generá un caso por representante.

**Ejemplo — campo "edad" (acepta 18 a 65).**

```
+------------------------+-----------------+------------+
| Clase                  | Representante   | Esperado   |
+========================+=================+============+
| Válida (18–65)         | 40              | Aceptado   |
+------------------------+-----------------+------------+
| Inválida (menor)       | 15              | Rechazado  |
+------------------------+-----------------+------------+
| Inválida (mayor)       | 70              | Rechazado  |
+------------------------+-----------------+------------+
| Inválida (no numérico) | "abc"           | Rechazado  |
+------------------------+-----------------+------------+
```

Cuatro casos cubren el comportamiento, en lugar de decenas.

**Errores comunes.** Probar solo clases válidas y olvidar las inválidas. Meter en una sola clase cosas que el sistema distingue (ej. "vacío" y "formato inválido" suelen ser clases distintas).

---

## 2. Valores límite (Boundary Value Analysis)

**Qué es.** Los defectos se concentran en los **bordes** de los rangos (errores de `<` vs `<=`, off-by-one). Se prueban los valores en el límite y sus vecinos inmediatos.

**Cuándo.** Siempre que haya un rango numérico, de fechas o de longitud. Complementa a clases de equivalencia.

**Cómo.** Para un rango [mín, máx], probá **mín−1, mín, mín+1** y **máx−1, máx, máx+1**.

**Ejemplo — contraseña de 8 a 16 caracteres.**

```
+------------+---------+------------+
|   Longitud | Punto   | Esperado   |
+============+=========+============+
|          7 | mín−1   | Rechazado  |
+------------+---------+------------+
|          8 | mín     | Aceptado   |
+------------+---------+------------+
|          9 | mín+1   | Aceptado   |
+------------+---------+------------+
|         15 | máx−1   | Aceptado   |
+------------+---------+------------+
|         16 | máx     | Aceptado   |
+------------+---------+------------+
|         17 | máx+1   | Rechazado  |
+------------+---------+------------+
```

**Errores comunes.** Probar solo "adentro" y "afuera" lejos del borde (ej. 5 y 20) y perderse el off-by-one entre 7/8 y 16/17.

---

## 3. Tabla de decisión (Decision Table)

**Qué es.** Una tabla que cruza **condiciones** (entradas) con **acciones** (resultados), con una columna por cada combinación relevante. Hace explícitas las reglas de negocio que dependen de varias condiciones.

**Cuándo.** Cuando el resultado depende de **varias condiciones combinadas** ("si A y B entonces C").

**Cómo.**
1. Listá las condiciones y las acciones.
2. Armá una columna por combinación de condiciones (Sí/No).
3. Definí la acción esperada de cada columna.
4. Cada columna es un caso.

**Ejemplo — descuento: los clientes "premium" tienen 10%; las compras mayores a $10.000 suman 5%.**

```
+---------------------+------+------+------+------+
| Condición / Regla   | R1   | R2   | R3   | R4   |
+=====================+======+======+======+======+
| ¿Es premium?        | No   | No   | Sí   | Sí   |
+---------------------+------+------+------+------+
| ¿Compra > $10.000?  | No   | Sí   | No   | Sí   |
+---------------------+------+------+------+------+
| **Descuento**       | 0%   | 5%   | 10%  | 15%  |
+---------------------+------+------+------+------+
```

Cuatro casos cubren todas las combinaciones.

**Errores comunes.** Omitir combinaciones (probar solo premium + caro y no-premium + barato). No simplificar cuando una condición es indiferente para el resultado.

---

## 4. Transición de estados (State Transition)

**Qué es.** Modelar el sistema como **estados** y **eventos** que lo hacen pasar de uno a otro. Se prueban las transiciones válidas y, sobre todo, las **inválidas** (eventos no permitidos en un estado).

**Cuándo.** Flujos con estados: pedidos, suscripciones, sesiones, bloqueos.

**Cómo.**
1. Listá los estados y los eventos.
2. Mapeá qué evento lleva de qué estado a cuál (y cuáles no están permitidos).
3. Probá cada transición válida y también los intentos de transición inválida.

**Ejemplo — bloqueo de cuenta tras 3 intentos fallidos.**
- Estados: *Activa*, *Bloqueada*.
- *Activa* + 3 logins fallidos → pasa a *Bloqueada*.
- *Activa* + login correcto → sigue *Activa* (el contador de intentos vuelve a 0).
- *Bloqueada* + login correcto → **rechazado**: estando bloqueada no se entra, aunque la clave sea válida (transición inválida).
- *Bloqueada* + espera de N minutos → vuelve a *Activa* (si la regla lo define).

**Errores comunes.** Probar solo el camino que bloquea y no qué pasa **estando** bloqueado. Olvidar el reseteo del contador después de un login exitoso.

---

## 5. Pairwise (combinatoria reducida)

**Qué es.** Cuando hay muchos parámetros independientes, probar **todas** las combinaciones explota. Pairwise cubre **todos los pares** de valores entre parámetros —donde aparece la mayoría de los defectos— con muchísimos menos casos.

**Cuándo.** Varios parámetros independientes con varios valores cada uno (configuraciones, compatibilidad).

**Cómo.** Listá los parámetros y sus valores, y armá un conjunto mínimo de combinaciones que incluya cada par (un valor de A junto a un valor de B) al menos una vez. Hay herramientas que lo generan (PICT, AllPairs).

**Ejemplo — navegador (Chrome, Firefox, Safari) × SO (Windows, macOS) × idioma (ES, EN).**
Todas las combinaciones son 3 × 2 × 2 = 12. Con pairwise se cubren todos los pares en unos 6 casos, manteniendo buena cobertura.

**Errores comunes.** Usar pairwise cuando los parámetros **no** son independientes: si ciertas combinaciones tienen reglas propias, esas van con tabla de decisión.

---

## Cómo combinarlas

Rara vez se usa una sola. Lo típico:

- Por cada campo: **clases de equivalencia** + **valores límite**.
- Si hay reglas combinadas: **tabla de decisión**.
- Si hay flujo con estados: **transición de estados**.
- Si hay muchas configuraciones: **pairwise**.

Y siempre: negativos y bordes, no solo el camino feliz; lo que no esté definido se registra como `FI-XX` (Falta información) con su pregunta al PO.

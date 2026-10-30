---
name: tecnicas-de-diseno
description: Técnicas de diseño de pruebas de caja negra — equivalencia, valores límite, tabla de decisión, transición de estados y pairwise. Úsalo al generar o revisar casos con rangos, condiciones o combinaciones.
---

# Técnicas de diseño de casos de prueba

Estas técnicas ayudan a **cubrir más con menos casos**: derivan los casos relevantes de forma sistemática, sin tirar valores al azar ni repetir lo mismo. Aplicalas al diseñar casos a partir de una historia, una regla de negocio o un endpoint.

## Cómo usarlas (flujo)

1. **Identificá las entradas y sus reglas.** Por cada campo o condición: tipo, rango, formato, obligatoriedad, valores válidos e inválidos, estados posibles.
2. **Elegí la técnica según el tipo de entrada** (guía abajo). Casi siempre se combinan varias.
3. **Derivá los casos** con la técnica.
4. **Sumá siempre negativos y bordes**, no solo el camino feliz.
5. **Eliminá redundancia**: si dos casos prueban exactamente lo mismo, dejá uno.
6. **Lo que no esté definido no se inventa**: registralo como **Falta información** (`FI-XX`, skill `investigacion-contexto`) con su pregunta al PO; si usás un supuesto para escribir el caso, aclaralo ligado a ese `FI-XX`.

## Qué técnica usar

- **Rango numérico o de longitud** (ej. monto 1–9999, contraseña 8–16) → **valores límite** + **clases de equivalencia**.
- **Entradas con categorías o válido/inválido** (ej. tipo de documento, estado civil) → **clases de equivalencia**.
- **Varias condiciones que se combinan y cambian el resultado** (ej. descuento por tipo de cliente + medio de pago) → **tabla de decisión**.
- **Flujo con estados** (ej. pedido: creado → pagado → enviado; o bloqueo de cuenta tras N intentos) → **transición de estados**.
- **Muchos parámetros independientes** (ej. navegador × SO × idioma) → **pairwise** (combinatoria reducida).

## Las técnicas en una línea

- **Clases de equivalencia:** agrupá las entradas que el sistema trata igual y probá **un representante por grupo** (válidos e inválidos).
- **Valores límite:** los errores se esconden en los bordes; probá **el límite y sus vecinos** (mín−1, mín, mín+1 … máx−1, máx, máx+1).
- **Tabla de decisión:** listá condiciones y acciones, y armá una columna por **combinación relevante** de condiciones.
- **Transición de estados:** mapeá estados y eventos, y probá las **transiciones válidas y las inválidas** (eventos no permitidos en cada estado).
- **Pairwise:** en vez de todas las combinaciones, cubrí **todos los pares** de valores; baja muchísimo la cantidad de casos manteniendo buena cobertura.

El detalle de cada técnica, con ejemplos trabajados y errores comunes, está en [`references/tecnicas.md`](references/tecnicas.md).

## Salida

Los casos que derives van en el formato del agente que los genera (planilla `.xlsx` + `.md`, `.feature`, casos de API…), cada uno con su **prioridad** (lo más crítico primero). En el informe de cobertura indicá **siempre** la técnica y los valores derivados por criterio (ej.: "Valores límite, 8–16: 7, 8, 16, 17 → CP-004 a CP-007"), para que se pueda verificar el porqué de cada caso.

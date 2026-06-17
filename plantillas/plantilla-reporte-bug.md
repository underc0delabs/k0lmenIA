# Plantilla — Reporte de bug

> Esta es la plantilla que sigue el agente **`generador-reportes-bug`**.
> Para cambiar el formato de salida, editá esta plantilla: el agente respeta sus campos y su orden.
>
> Formato de salida: **bloque vertical, un reporte por archivo.**
> Regla clave: si falta información, el agente la **marca y la pregunta**, nunca la inventa.

---

**ID:** `BUG-001` — único e identificable.

**Título:** `[Pantalla]` Título descriptivo del error.

**Descripción:**
Comentar brevemente de qué se trata el error, que se entienda cuál es la falla.

**Precondiciones:**
Qué es lo que hay que tener configurado previamente para poder ejecutar los pasos.

**Test Data:**
- Usuario:
- Password:

**Pasos de reproducción:**
1. Paso 1
2. Paso 2
3. Paso 3
4. Paso 4

**Resultado Actual:**
Qué es lo que está pasando ahora.

**Resultado Esperado:**
Cómo debería funcionar la aplicación.

**Evidencia:**
Captura de pantalla, video o log del error.

**Criticidad / Severidad:** `Crítica` · `Alta` · `Media` · `Baja`

**Test Case asociado:** `CP-XXX` (si aplica)

**Versión:** versión de la aplicación (Mobile) — *opcional*

**Browser:** navegador en el que se encontró la falla.

**Ambiente:** ambiente en el que se encontró el error (ej.: testing, staging, producción).

---

> **Nota del agente:** cuando algún dato necesario no esté en la observación original, el reporte incluirá una sección final **"⚠️ Información faltante"** listando qué falta y por qué hace falta, en vez de completarlo con suposiciones.

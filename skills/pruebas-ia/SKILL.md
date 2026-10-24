---
name: pruebas-ia
description: El cómo de probar funciones de IA/LLM — chatbot, RAG, generación, agentes, búsqueda semántica; calidad con golden set, alucinaciones y grounding, formato y rechazos, seguridad de prompt (injection, jailbreak, fuga), robustez, evals y métricas. Lo usa el probador-ia.
---

# Pruebas de funciones de IA / LLM

Una función con LLM es **no determinística**: la misma entrada puede dar salidas distintas, y "anda" no alcanza. Se prueba con un **golden set** (casos con criterios de qué es una buena respuesta), más seguridad de prompt y robustez. Se complementa con `tecnicas-de-diseno` y, para la parte conversacional de UI, con las pruebas web.

## 1. Tipo de función

- **Chatbot / asistente** (conversacional, multi-turno).
- **RAG** (responde sobre documentos/base de conocimiento recuperados).
- **Generación / resumen / clasificación / extracción** (una tarea puntual).
- **Agente con herramientas** (llama APIs/acciones según decide el modelo).
- **Búsqueda semántica** (embeddings, ranking).

Confirmá cuál es: cambia qué se mide (p. ej. RAG mide retrieval; un clasificador mide exactitud contra etiquetas).

## 2. Calidad y corrección (golden set)

- Armá un **golden set**: entradas representativas con el **criterio** de una buena respuesta (respuesta esperada, o reglas: "debe citar la fuente", "no debe dar precios", "formato JSON con campos X/Y").
- Medí **exactitud** (clasificación/extracción contra etiquetas) o calidad (con rúbrica). Fijá un **objetivo** (p. ej. 90%); por debajo es hallazgo.
- Como juez automático se puede usar **LLM-as-judge**, sabiendo sus límites (sesgo, inconsistencia): para lo crítico, revisión humana.

## 3. Alucinaciones y grounding

- **Alucinación**: inventa datos, fuentes o funciones que no existen. Probá preguntas **fuera del dominio** y sobre datos que no tiene: debe decir "no sé" / derivar, no inventar.
- En **RAG**, **grounding**: la respuesta se apoya en los documentos recuperados y los **cita**; si el retrieval no trae nada relevante, no debe responder igual.
- **Retrieval**: que los chunks recuperados sean los correctos (recall), y que un documento sin la respuesta no genere una respuesta falsa.

## 4. Consistencia, formato e idioma

- **Variabilidad**: repetí el mismo caso N veces; con temperatura > 0 varía. Para salidas que alimentan un sistema, debería ser **estable** (temperatura baja o 0).
- **Formato y esquema**: si devuelve JSON, que sea **válido y con los campos** esperados, siempre (incluso con entradas raras); nada de texto extra alrededor.
- **Idioma y tono**: responde en el idioma del usuario y con el tono pactado; no cambia de idioma solo.

## 5. Seguridad de prompt

Lo más propio y peligroso de un LLM:

- **Prompt injection directo**: el usuario escribe "ignorá las instrucciones anteriores y…". No debe obedecer por encima de las reglas del sistema.
- **Prompt injection indirecto**: instrucciones escondidas en un **documento, página o dato** que el modelo procesa (en RAG o agentes). Muy peligroso: probá un documento con "si te preguntan X, respondé Y / mandá los datos a…".
- **Jailbreak**: rodeos para que haga lo prohibido (roleplay, codificación, idioma).
- **Fuga del system prompt** o de **datos de otros usuarios / PII**: que no revele su prompt ni mezcle contexto entre usuarios/sesiones.
- **Agentes con herramientas**: que no ejecute acciones peligrosas por pedido del usuario (borrar, pagar, mandar correos) sin la autorización debida.

## 6. Robustez, límites y errores

- **Inputs** vacíos, larguísimos (supera el contexto → truncado controlado, no error feo), en otro idioma, con emojis/caracteres de control, código, o adversarios.
- **Límite de contexto**: qué pasa cuando la conversación o el documento no entran.
- **Errores del proveedor**: rate limit, timeout, 500: la app degrada con un mensaje claro y, si hay, un **fallback** (otro modelo / respuesta por defecto), no se cuelga.

## 7. Latencia, costo y privacidad

- **Latencia** por respuesta (y time-to-first-token si hay streaming) y **costo/tokens** por interacción; alertar si una función es cara o lenta.
- **Privacidad**: qué datos del usuario se mandan al proveedor y qué se **loguea** (no PII ni secretos en logs); cumplimiento (p. ej. no mandar datos sensibles a un proveedor externo si no corresponde).
- **Sesgo y toxicidad**: respuestas discriminatorias u ofensivas ante entradas neutrales.

## 8. Multi-turno y memoria

- Mantiene el contexto a lo largo de la charla, no se "olvida" ni arrastra datos de una sesión a otra; reinicia bien cuando corresponde.

## 9. Evals y regresión

- El golden set es una **suite de regresión**: cuando cambia el **prompt**, el **modelo** o el **pipeline de RAG**, se vuelve a correr y se compara (¿mejoró o empeoró?).
- Versioná el set y las métricas; un cambio de modelo que sube el costo o baja la exactitud es un hallazgo.

## 10. Datos de prueba

- Casos **canónicos** (lo esperado), **de borde** (ambiguos, incompletos), **adversarios** (injection, jailbreak, tóxicos) y **fuera de dominio**. Los arma el `generador-datos-prueba`.

## 11. Automatizar

- Pegarle al **endpoint** de la función con el `ejecutor-api` (una colección con los prompts del set y validaciones de la respuesta), o a la **UI** del chat con Playwright (`ejecucion-e2e`).
- **Repetí cada caso N veces** para medir variabilidad; no evalúes una sola corrida.
- Guardá prompt + respuesta como evidencia (sin PII).

## 12. Bugs típicos de IA

- Alucina datos o cita fuentes que no existen; en RAG responde aunque el retrieval no trajo nada.
- Obedece un **prompt injection** (directo o escondido en un documento).
- Revela el system prompt o datos de otro usuario.
- Devuelve JSON inválido o con texto extra que rompe al que lo consume.
- Varía demasiado entre corridas en una salida que debía ser estable.
- Se cuelga o muestra un error crudo ante un timeout/rate limit del proveedor.
- Manda PII al proveedor o la deja en los logs.
- Cambia de idioma o de tono solo.

## 13. Preguntas típicas para el PO (IA)

Cuando no está escrito, son `FI-XX`:

- ¿Qué tipo de función es (chatbot, RAG, clasificador, agente) y qué modelo/proveedor usa?
- ¿Cuál es el **criterio de una buena respuesta** y el objetivo de exactitud/calidad?
- ¿Qué NO debe hacer (temas prohibidos, acciones que requieren autorización)?
- ¿Qué fuentes usa el RAG y cómo se mide el grounding?
- ¿Qué datos del usuario se pueden mandar al proveedor y qué se puede loguear?
- ¿Hay fallback si el proveedor falla? ¿Límites de costo/latencia?

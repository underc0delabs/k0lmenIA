---
name: pruebas-ivr
description: El cómo de probar voz, IVR y voicebots telefónicos — árbol de menús (DTMF y ASR), prompts/TTS, flujo de llamada, enrutamiento y colas, transferencias y CTI, telefonía (SIP/VoIP), grabación y cumplimiento, voicebots con NLU y métricas. Lo usa el probador-ivr.
---

# Pruebas de voz / IVR

Un IVR (respuesta de voz interactiva) se prueba **por teléfono**: el usuario escucha prompts y responde con **tonos (DTMF)** o **voz**. Lo que importa es que **no se pierda la llamada**, que el menú lleve a donde debe y que llegue a un humano cuando hace falta. Para la parte de NLU/LLM de un voicebot, se complementa con `pruebas-ia`.

## 1. El árbol de menús

- Mapeá el **árbol completo**: cada opción de cada menú, a dónde lleva, y los submenús. Recorré **todas** las ramas, no solo la principal.
- **DTMF**: cada dígito hace lo que dice; un dígito inválido da el mensaje correcto y reintenta.
- **Reconocimiento de voz (ASR)**: entiende las respuestas esperadas (y sinónimos), con acentos y ruido de fondo; `barge-in` (poder hablar/marcar antes de que termine el prompt).

## 2. Prompts y TTS

- Los **prompts** son claros, en el idioma correcto, sin cortes; el **TTS** pronuncia bien nombres, números y montos.
- La **voz y el tono** son consistentes; los prompts coinciden con las opciones reales (no dicen "marque 3" si el 3 no existe).

## 3. Flujo de llamada y manejo de errores

- **Bienvenida**, menús, y el manejo de **no-input** (el usuario no responde) y **no-match** (responde algo inválido): reintentos (normalmente 3) y luego **salida al operador** o fin cortés, nunca un loop infinito ni colgar de golpe.
- **Timeouts** razonables; **salir al operador** siempre disponible (marcar 0, o decir "operador").
- **Horario de atención**: fuera de hora, mensaje correcto y opción de callback/mensaje.

## 4. Enrutamiento, colas y transferencias

- **ACD/colas**: enruta al skill/cola correcta, con prioridad; **música/mensajes en espera**, posición en la cola, **desborde** cuando no hay agentes y **callback** (devolución de llamada) si existe.
- **Transferencias**: ciega (directa) y consultiva (el agente consulta antes); los **datos de la llamada** (CTI/screen-pop: número, lo que marcó, el cliente identificado) llegan al agente.

## 5. Integración con backend y autenticación

- Consultas por teléfono (saldo, estado de un pedido): el dato que lee el IVR coincide con el backend.
- **Autenticación** por PIN/DNI/voz: intentos, bloqueo, y que no lea datos sensibles en voz alta sin identificar.

## 6. Telefonía y audio

- **SIP/VoIP**: la llamada conecta, buena **calidad de audio** (sin eco, cortes ni robotización), **latencia/jitter** aceptables.
- **DTMF**: que se detecten los tonos (in-band vs. RFC2833/SIP INFO); un problema común es que el IVR no "escuche" los dígitos.
- Cortes y reconexión; qué pasa si el usuario cuelga a mitad.

## 7. Grabación y cumplimiento

- **Consentimiento** de grabación donde la ley lo exige; la grabación realmente se guarda y es recuperable.
- **PCI** en pagos por voz: no grabar el número de tarjeta/CVV (pausar la grabación o usar DTMF enmascarado); sin datos sensibles en logs.

## 8. Voicebots (NLU / LLM)

- Si hay un **voicebot** con NLU/LLM: intents y entidades reconocidos, **fallback** cuando no entiende, **confirmaciones** antes de acciones con efecto, y que no alucine (ver `pruebas-ia` para la parte de IA).

## 9. Métricas

- **Contención** (cuántas llamadas resuelve el IVR sin agente), **abandono** (cuántas cuelgan en el IVR), **tiempo en IVR** y en cola. Un abandono alto en un menú señala un problema.

## 10. Automatizar

- Herramientas de **testing de voz** (Cyara, Hammer, Empirix) hacen llamadas automáticas y validan prompts/DTMF; alternativamente, scripts **SIP** (p. ej. con un softphone/SIPp) y validación de audio. El agente orquesta o documenta estos casos; mucho del testing de IVR es **manual asistido** (llamar y seguir el guion).

## 11. Bugs típicos de IVR

- Opción del menú que lleva a la rama equivocada o a un prompt que no existe.
- No-match/no-input que entra en loop o cuelga sin salir al operador.
- DTMF que no se detecta (tonos ignorados).
- Prompt que menciona opciones que ya no existen o en otro idioma.
- No se puede llegar a un humano.
- Grabación de datos de tarjeta (incumplimiento PCI).
- Transferencia que pierde los datos de la llamada (el agente pregunta todo de nuevo).
- Fuera de horario sin mensaje correcto.

## 12. Preguntas típicas para el PO (IVR)

Cuando no está escrito, son `FI-XX`:

- ¿Tenés el diagrama del árbol del IVR y los prompts esperados?
- ¿El ingreso es por DTMF, por voz (ASR) o ambos? ¿Idiomas?
- ¿Cuántos reintentos antes de salir al operador? ¿Cómo se llega a un humano?
- ¿Qué horarios de atención y qué pasa fuera de hora?
- ¿Hay pagos por teléfono (PCI) o datos sensibles?
- ¿Es un IVR tradicional o un voicebot con NLU/LLM?

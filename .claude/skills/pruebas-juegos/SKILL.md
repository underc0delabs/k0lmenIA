---
name: pruebas-juegos
description: El cómo de probar videojuegos — motores (Unity, Unreal, Godot, HTML5), funcional, compatibilidad, rendimiento (FPS, memoria), guardado, multijugador y red, monetización, audio y a11y, estabilidad y exploratorias de juego. Lo usa el probador-juegos.
---

# Pruebas de videojuegos

Un juego tiene mucho de lo de cualquier software (funcional, rendimiento, compatibilidad), más lo propio: **física, estados de juego, progresión, multijugador y "romper" el mundo** de formas creativas. Lo exploratorio pesa mucho. Para la parte de IA (NPCs con LLM) ver `pruebas-ia`; para el backend online, los skills de API y `pruebas-async`.

## 1. Contexto

- **Motor y plataforma**: Unity, Unreal, Godot, HTML5/web, mobile (iOS/Android), consola, PC. Define cómo se automatiza y qué mirar.
- **Género**: las mecánicas y los casos límite cambian mucho (un RPG vs. un shooter vs. un puzzle).

## 2. Funcional (mecánicas y reglas)

- **Mecánicas**: cada regla del juego funciona (daño, puntaje, cooldowns, inventario, crafteo); casos límite (cero vida, inventario lleno, máximo de nivel).
- **Progresión y misiones**: las misiones se completan y desbloquean lo que deben; sin **soft-locks** (quedar trabado sin poder avanzar) ni secuencias rotas (hacer las cosas en otro orden).
- **Estados del juego**: menú → jugando → pausa → game over → reinicio; transiciones limpias.
- **Físicas y colisiones**: el jugador no atraviesa paredes ni cae fuera del mundo; colisiones correctas; **boundary** del mapa.
- **Controles**: teclado+mouse, gamepad y táctil; que respondan bien y sean remapeables.

## 3. Guardado y persistencia

- **Save/Load**: guardar y cargar restaura el estado exacto; autoguardado; **corrupción** de un save no crashea (maneja el error).
- **Saves en la nube** y sincronización entre dispositivos; **migración** de saves entre versiones del juego.

## 4. Compatibilidad y rendimiento

- **Resoluciones y aspect ratios** (incluida ultrawide), FPS/refresh; UI que no se corta ni se superpone.
- **Rendimiento**: **FPS estable** en las escenas pesadas, **tiempos de carga**, **memoria/leaks** (sesiones largas), **stuttering**, uso de GPU/CPU, **batería/calor** en mobile. Para carga del backend, `performance-mapper`.
- **Plataformas/dispositivos** y **controladores** de la matriz objetivo.

## 5. Multijugador y red

- **Sincronización** entre jugadores (todos ven lo mismo), **latencia/lag** y su compensación (rollback/prediction), **desconexión y reconexión** sin romper la partida, **matchmaking**.
- **Autoridad del servidor y anti-cheat**: el cliente no decide cosas críticas (vida, items, posición) sin validación del servidor; intentos de trampa rechazados.

## 6. Economía y monetización

- **Compras in-app** (sandbox del store), **moneda del juego**, **loot boxes** (probabilidades declaradas), **balance** (no roto ni pay-to-win no intencional), **ads** recompensados.
- Que una compra otorgue lo pagado una sola vez y se restaure ("restore purchases").

## 7. Audio, localización y accesibilidad

- **Audio**: música, efectos y voces se reproducen y mezclan bien; sin cortes.
- **Localización**: textos traducidos, sin desbordes ni claves a la vista (ver `analista-traductor`).
- **Accesibilidad**: remapeo de teclas, subtítulos, modos para daltonismo, escalado de UI.

## 8. Estabilidad y build verification

- **Smoke/BVT por plataforma**: la build arranca, entra a una partida, guarda y sale sin crash.
- **Soak**: dejar el juego corriendo horas (memory leaks, degradación).
- **Crash**: reportar con pasos, logs y, si hay, el crash dump.

## 9. Técnicas propias

- **Exploratorias** (lo más valioso): intentar **romper el mundo** —atravesar geometría, salir del mapa, ejecutar acciones en orden raro, interrumpir cinemáticas, spamear inputs—; **speedrun** para detectar secuencias rotas; estados imposibles.

## 10. Automatizar

- Frameworks del motor (**Unity Test Framework**, **Unreal Automation**, **GAutomator**), **bots** que juegan, **Playwright** para juegos **HTML5**, **Appium** para mobile. Mucho del testing de juegos es **exploratorio manual**; automatizá lo repetitivo (smoke, regresión de mecánicas, carga de red).

## 11. Bugs típicos de juegos

- **Soft-lock**: el jugador queda trabado sin poder avanzar ni volver.
- Atravesar paredes / caer fuera del mundo; colisiones rotas.
- Save corrupto que crashea o progreso perdido al actualizar.
- FPS que se desploma en una escena; memory leak en sesiones largas.
- Desincronización en multijugador; el cliente decide algo crítico (cheat).
- Compra in-app que no otorga el item o lo da dos veces.
- UI cortada en cierto aspect ratio; texto desbordado en otro idioma.
- Secuencia rota al hacer las misiones en otro orden.

## 12. Preguntas típicas para el estudio

Cuando no está escrito, son `FI-XX`:

- ¿Qué motor y qué plataformas/dispositivos objetivo?
- ¿Qué mecánicas y progresión son críticas? ¿Hay un diseño de niveles/misiones?
- ¿Es single o multijugador? ¿Autoridad del servidor y anti-cheat?
- ¿Hay compras in-app, loot boxes o ads? ¿Probabilidades declaradas?
- ¿Qué FPS/tiempos de carga objetivo? ¿Build de QA por plataforma?
- ¿Saves locales, en la nube, y migración entre versiones?

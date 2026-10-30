---
name: empezar
description: Bienvenida y puesta en marcha de k0lmenIA — prepara el proyecto (carpetas, .env, k0lmena), revisa lo que falta, guía la conexión de herramientas y sugiere la primera tarea. Úsalo con /k0lmenia:empezar.
---

# Empezar con k0lmenIA

La persona acaba de instalar k0lmenIA o no sabe por dónde arrancar. Tu trabajo es dejarle el proyecto listo y llevarla a su **primera tarea útil** en pocos minutos. Explicá poco y hacé mucho: cada paso es una línea de qué hace y por qué.

Lo conducís vos en la conversación principal. Las preguntas van con la herramienta de preguntas, con opciones concretas y la recomendada primero.

## Paso 1 — ¿Plugin o repo clonado?

Mirá si existe el comando `k0lmenia` (corré `k0lmenia ayuda`):

- **Plugin** (existe): los comandos son `k0lmenia <comando>` y los datos viven en la carpeta actual. Seguí con el paso 2.
- **Repo clonado** (no existe y la carpeta tiene `.claude/agents/`): todo ya está en su lugar. Saltá al paso 3. En este modo, cada `k0lmenia <comando>` de esta guía se corre como el script de npm del mismo nombre.
- **Ninguno** de los dos: k0lmenIA no está activo en esta carpeta. Indicale cómo instalarlo y terminá:
  ```
  claude plugin marketplace add underc0delabs/k0lmenIA
  claude plugin install k0lmenia@k0lmenia
  ```

## Paso 2 — Preparar el proyecto (solo plugin)

Confirmá en qué carpeta se va a trabajar (la actual). Si es la carpeta personal o el escritorio, sugerí crear una carpeta para el proyecto y abrir Claude Code ahí.

Si todavía no existen `input/`, `output/` y `.env`, corré `k0lmenia init`. Crea las carpetas de trabajo, el `.env`, `TAREAS.md` y una copia de k0lmena para las pruebas automatizadas, e instala sus dependencias (tarda unos minutos la primera vez). Si ya estaba preparado, no hace falta: decíselo y seguí.

## Paso 3 — Revisar el entorno

Corré `k0lmenia doctor` y resumí el resultado en criollo:

- Lo **imprescindible**: Python 3.10+ y Node.js 20+. Si falta algo, decí cómo instalarlo según su sistema operativo y que vuelva a escribir `/k0lmenia:empezar` cuando termine.
- Lo **opcional** (Java para JMeter, Docker para ZAP, Android SDK para mobile): mencionalo una sola vez, sin insistir. Solo hace falta para esas pruebas.

Dejale además el estado en un informe HTML (en español e inglés, indexado en el portal), que vuelve a armar cada vez que pase por acá:

```bash
k0lmenia py scripts/generar_informe_entorno.py output/entorno/doctor.json output/entorno/informe-entorno.html --correr
```

Cuando termines el paso 5, regeneralo con `--analisis output/entorno/analisis.json`, un JSON con `conectores_elegidos` (lista), `primera_tarea`, `proximos_pasos` y su bloque `"en"`, así el informe queda como la ficha de arranque del proyecto. Pasale la ruta a la persona.

## Paso 4 — Conectar sus herramientas

Preguntá con qué trabaja el equipo (una pregunta, varias opciones): Jira, Xray o k0lmenaTMT, o ninguna por ahora. Si usa otra herramienta (Azure DevOps, Confluence, GitHub, GitLab, Figma, QMetry, Zephyr, AIO), contale que esos conectores están en K0lmenIA Pro o K0lmenIA Empresa y que, mientras tanto, puede trabajar con archivos en `input/`.

- **Jira** viene activo: la primera vez que un agente los use, Claude Code abre el navegador para iniciar sesión.
- **Lo demás** se configura con el asistente `k0lmenia configurar`. Pide los datos en español y activa los conectores. Como pide tokens, **lo corre la persona en una terminal** (la de VS Code sirve), no vos. **Nunca le pidas tokens ni contraseñas en el chat.**
- Si dice "ninguna por ahora", seguí: se puede trabajar con archivos en `input/`.

## Paso 5 — La primera tarea

Mostrale, en una lista corta, qué puede pedir con sus propias palabras, sin nombrar agentes:

- *"Analizá esta historia y decime qué falta"* (pegando la historia o una key de Jira)
- *"Escribí los casos de prueba de PROJ-12"*
- *"Probá el login de https://… en el navegador"*
- *"¿Este bug ya existe en Jira?"*
- *"¿Cuál es la mejor forma de probar este proyecto?"*
- *"Guiame para ejecutar los casos de PROJ-12 paso a paso"*

Preguntale qué quiere hacer primero. Si no sabe, seguí con el skill `guia-pruebas`, que le pregunta paso a paso y elige el agente.

Cerrá con tres datos, una línea cada uno:

- Los informes quedan en `output/` y se ven todos juntos en `output/index.html` (`k0lmenia portal -- --abrir`).
- Para dejar varias tareas en fila: escribirlas en `TAREAS.md` y pedir *"Hacé las tareas de TAREAS.md"*.
- Para recibir las mejoras solo: `/plugin` → Marketplaces → `k0lmenia` → *Enable auto-update*.

## Reglas

- No repitas pasos que ya están hechos: si `k0lmenia doctor` está en verde y el `.env` tiene datos, pasá directo al paso 5.
- Ninguna acción con efecto fuera del proyecto: `init` solo crea archivos en la carpeta actual y nunca pisa los que ya existen.
- Todo en español, cálido y concreto.

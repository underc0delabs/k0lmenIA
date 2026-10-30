---
name: base-conocimiento
description: Flujo de la conversación principal para armar y mantener la base de conocimiento de un proyecto (input/documentacion/) — documentar, explorar y actualizar. Úsalo para documentar todo el proyecto.
---

# Base de conocimiento del proyecto (conversación principal)

Este flujo lo maneja la **conversación principal**: encadena agentes que corren como subagentes y le pregunta a la persona lo que haga falta entre un paso y otro (los subagentes no pueden preguntar). Todo lo que se documenta queda en `input/documentacion/` (Markdown con encabezado e índice); los agentes que escriben y automatizan casos lo leen solos con el skill `investigacion-contexto`.

```
documentador-proyecto (barrido + app de punta a punta) ─► input/documentacion/ ─► casos (manuales, BDD) ─► mappers (k0lmena)
                                       INDICE.md + confiabilidad            ▲                         ▲
                                                             cambios-historias.md · cambios.md · cambios de la app
```

La investigación total del proyecto (tableros y wiki) y el manual de usuario verificado en la app están disponibles en K0lmenIA Pro.

## 1. Antes de empezar (preguntale a la persona lo que falte)

- **Alcance**: todo el proyecto, o una épica, release o sprint. Proyecto de Jira y repositorio local (`REPO_RUTA_LOCAL` y `REPO_NOMBRE` del `.env`).
- **Conectores activos** (`npm run conector`): el de Jira (`atlassian`). Si falta, `npm run configurar`.
- **La aplicación**: URL del ambiente de QA (`APP_URL`) y, si tiene login, que la persona corra `npm run login` (inicia sesión **a mano**) y ponga `SESION=si` en el `.env`; si hay roles distintos, una sesión por rol (`npm run login -- --nombre admin`).
- **Costo**: documentar *todo* gasta muchos tokens. Proponé hacerlo por etapas y en lotes (los agentes devuelven el progreso y se continúan).

## 2. Armar la base (una vez)

1. **Detalle de cada historia** → `documentador-proyecto` en **modo barrido**: un dossier por historia con **todos** sus comentarios, subtareas, tareas, tickets vinculados, épica, commits y links; en lotes (si devuelve "quedan N", continualo).
2. **Repositorio y aplicación** → `documentador-proyecto` en **modo proyecto**: reglas, mensajes, estados y permisos, API y el **mapa funcional de punta a punta con la sesión** (`--max-paginas 200 --profundidad 4`, más lo que solo se alcanza con clics), con los **locators sugeridos** de cada pantalla.
3. Mostrale a la persona `input/documentacion/INDICE.md`: qué hay, de dónde sale y qué tan confiable es.

## 3. Escribir los casos con ese contexto

Por historia o por módulo: `generador-casos-manuales` o `generador-casos-bdd` (y el `analista-historias` antes, si la historia es ambigua). Con el skill `investigacion-contexto` leen primero el índice, el dossier y el mapa; lo confirmado va como pasos y resultados esperados, lo dudoso como `FI-XX` (preguntas para el PO), nunca como dato inventado.

## 4. Automatizar

- **Web**: `web-mapper` con los casos (manuales o BDD): parte de los **locators sugeridos** del mapa funcional, los confirma en la app y genera `.feature`, steps y locators de k0lmena. Después corre con `npm test`, sin agentes ni tokens.
- **API**: `api-mapper` (OpenAPI/colección → `.feature` de k0lmena).

## 5. Mantenerla al día (proyectos ágiles)

Los requerimientos cambian en el medio del sprint. La base **no se vuelve a armar**: se actualiza de forma incremental. `.estado.json` guarda qué historias están documentadas, con su fecha y una **huella** de su contenido (título, descripción, criterios, comentarios, subtareas y vínculos); la actualización le pide a Jira **solo** lo modificado desde la última revisión, lee en detalle las historias **nuevas** y las que **cambiaron de contenido**, e ignora las que solo se movieron de columna o se reasignaron.

**Programada** (recomendado): `npm run actualizar-conocimiento -- --programar lunes --con-agente` la deja corriendo cada lunes a las 08:00 en esta máquina (Programador de tareas en Windows; en Mac/Linux da la línea de cron). Cada corrida vuelve a recorrer la app y compara (sin tokens), revisa el código nuevo si hay `REPO_RUTA_LOCAL` (sin tokens), corre el documentador en modo actualizar para las historias (con tope de gasto, `--presupuesto-usd`, 5 por defecto), deja el resumen en `output/conocimiento/` y avisa a Slack/Teams si algo cambió. Sin `--con-agente` no gasta tokens (solo app y código). `--desprogramar` la saca.

**A mano**, la misma rutina: **al empezar cada sprint, antes de escribir casos de una historia que se tocó, y antes de una regresión**:

1. `documentador-proyecto` en **modo actualizar**. Revisa tres cosas y rehace solo lo afectado:
   - **Historias** cambiadas desde la última revisión (y las nuevas) → `cambios-historias.md`, con sus **casos para revisar**.
   - **Código** desde el último commit documentado → `cambios.md`.
   - **Aplicación**: vuelve a correr el mapa funcional y compara (*Cambios desde el recorrido anterior*: pantallas, campos, reglas y botones).
2. Con lo que devuelva: casos para revisar → `revisor-casos` (o regenerarlos con el generador correspondiente). Reparar la automatización que se rompe por cambios de la app está disponible en K0lmenIA Pro.

Contale a la persona qué cambió, qué se rehízo y qué casos quedaron para revisar. Nada se publica en Jira ni en la herramienta de gestión sin su confirmación.

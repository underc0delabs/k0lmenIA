---
name: base-conocimiento
description: Flujo de la conversación principal para armar y mantener la base de conocimiento de un proyecto completo (input/documentacion/) y usarla para escribir y automatizar casos — investigar todo, explorar la plataforma, documentar y la rutina cuando cambian los requerimientos. Úsalo para investigar o documentar todo el proyecto o mantenerlo al día.
---

# Base de conocimiento del proyecto (conversación principal)

Este flujo lo maneja la **conversación principal**: encadena agentes que corren como subagentes y le pregunta a la persona lo que haga falta entre un paso y otro (los subagentes no pueden preguntar). Todo lo que se investiga queda en `input/documentacion/` (Markdown con encabezado e índice), además de los informes HTML/PDF de cada agente; los agentes que escriben y automatizan casos lo leen solos con el skill `investigacion-contexto`.

```
investigador-proyecto (total) ─┐
documentador-proyecto (barrido + app de punta a punta) ─┼─► input/documentacion/ ─► casos (manuales, BDD, API) ─► mappers (k0lmena)
redactor-manual (plataforma) ──┘        INDICE.md + confiabilidad            ▲                         ▲
                                                                     cambios-historias.md · cambios.md · cambios de la app
```

## 1. Antes de empezar (preguntale a la persona lo que falte)

- **Alcance**: todo el proyecto, o una épica, release o tablero (la URL del tablero sirve). Proyecto de Jira o Azure DevOps, espacio de Confluence/Wiki, repositorio (`REPO_*` del `.env`).
- **Conectores activos** (`npm run conector`): el de gestión (`atlassian`, `azure-devops`…), el del repositorio y Figma si hay diseños. Si falta alguno, `npm run configurar`.
- **La aplicación**: URL del ambiente de QA (`APP_URL`) y, si tiene login, que la persona corra `npm run login` (inicia sesión **a mano**) y ponga `SESION=si` en el `.env`; si hay roles distintos, una sesión por rol (`npm run login -- --nombre admin`).
- **Costo**: investigar *todo* gasta muchos tokens. Proponé hacerlo por etapas y en lotes (los agentes devuelven el progreso y se continúan).

## 2. Armar la base (una vez)

1. **Panorama completo** → `investigador-proyecto` con profundidad `total` (*"investigá absolutamente todo el proyecto PROJ"*): árbol completo de épicas, historias y tareas, módulos, flujos, integraciones, decisiones, glosario, dudas y riesgos. Deja el informe HTML/PDF y `input/documentacion/proyecto/investigacion/`.
2. **Detalle de cada historia** → `documentador-proyecto` en **modo barrido** con el mismo alcance: un dossier por historia con **todos** sus comentarios, subtareas, tareas, tickets vinculados, épica, PRs y links; en lotes (si devuelve "quedan N", continualo). Después, **modo proyecto** para el repositorio y la aplicación: reglas, mensajes, estados y permisos, API y el **mapa funcional de punta a punta con la sesión** (`--max-paginas 200 --profundidad 4`, más lo que solo se alcanza con clics), con los **locators sugeridos** de cada pantalla.
3. **Cómo se usa** (opcional, muy útil para casos) → `redactor-manual` en modo **plataforma**: plan por módulos y un manual por módulo, verificado en la app; cada manual deja en `input/documentacion/manual-usuario/` los pasos reales y las **Pistas para probar** (campos, validaciones, mensajes exactos, roles). Las dudas vuelven como `REVIEW-NNN`: preguntáselas a la persona.
4. Mostrale a la persona `input/documentacion/INDICE.md`: qué hay, de dónde sale y qué tan confiable es.

## 3. Escribir los casos con ese contexto

Por historia o por módulo: `generador-casos-manuales`, `generador-casos-bdd` o `generador-casos-api` (y el `analista-historias` antes, si la historia es ambigua). Con el skill `investigacion-contexto` leen primero el índice, el dossier, el manual, la investigación y el mapa; lo confirmado va como pasos y resultados esperados, lo dudoso como `FI-XX` (preguntas para el PO), nunca como dato inventado.

## 4. Automatizar

- **Web**: `web-mapper` con los casos (manuales o BDD): parte de los **locators sugeridos** del mapa funcional y de los manuales, los confirma en la app y genera `.feature`, steps y locators de k0lmena. Después corre con `npm test`, sin agentes ni tokens.
- **API**: `api-mapper` (OpenAPI/colección → `.feature` de k0lmena) o, si la API está en Scalar, `probador-scalar` (colección con tests que corre con Newman).
- **Mobile**: `mobile-mapper`.

## 5. Mantenerla al día (proyectos ágiles)

Los requerimientos cambian en el medio del sprint. La base **no se vuelve a armar**: se actualiza de forma incremental. `.estado.json` guarda qué historias están documentadas, con su fecha y una **huella** de su contenido (título, descripción, criterios, comentarios, subtareas y vínculos); la actualización le pide a la herramienta **solo** lo modificado desde la última revisión, lee en detalle las historias **nuevas** y las que **cambiaron de contenido**, e ignora las que solo se movieron de columna o se reasignaron.

**Programada** (recomendado): `npm run actualizar-conocimiento -- --programar lunes --con-agente` la deja corriendo cada lunes a las 08:00 en esta máquina (Programador de tareas en Windows; en Mac/Linux da la línea de cron). Cada corrida vuelve a recorrer la app y compara (sin tokens), revisa el código nuevo si hay `REPO_RUTA_LOCAL` (sin tokens), corre el documentador en modo actualizar para las historias (con tope de gasto, `--presupuesto-usd`, 5 por defecto), deja el resumen en `output/conocimiento/` y avisa a Slack/Teams si algo cambió. Sin `--con-agente` no gasta tokens (solo app y código). `--desprogramar` la saca.

**A mano**, la misma rutina: **al empezar cada sprint, antes de escribir casos de una historia que se tocó, y antes de una regresión**:

1. `documentador-proyecto` en **modo actualizar**. Revisa tres cosas y rehace solo lo afectado:
   - **Historias** cambiadas desde la última revisión (y las nuevas) → `cambios-historias.md`, con sus **casos para revisar**.
   - **Código** desde el último commit documentado → `cambios.md`.
   - **Aplicación**: vuelve a correr el mapa funcional y compara (*Cambios desde el recorrido anterior*: pantallas, campos, reglas y botones).
2. Con lo que devuelva:
   - casos para revisar → `revisor-casos` (o regenerarlos con el generador correspondiente);
   - pantallas que cambiaron con manual → `redactor-manual` (modo actualizar o solo capturas);
   - automatización que se rompe por la app → `reparador-automatizacion` (y `analista-fallos` para separar bugs de cambios esperados).
3. Cada tanto (por release), `investigador-proyecto` de nuevo: compara contra el relevamiento anterior (ambigüedades nuevas y resueltas) y actualiza `proyecto/investigacion/`.

Contale a la persona qué cambió, qué se rehízo y qué casos quedaron para revisar. Nada se publica en Jira, Azure DevOps ni la herramienta de gestión sin su confirmación.

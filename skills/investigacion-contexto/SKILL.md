---
name: investigacion-contexto
description: El cómo de investigar una historia antes de analizarla, planificarla o automatizarla — documentación, historia en Jira, épica y contratos — y registrar lo que falta (FI-XX) en una ficha.
---

# Investigación de contexto

Antes de suponer, **buscar**. Una historia casi nunca tiene toda la información en su descripción: las decisiones suelen estar en los comentarios, las reglas en la épica o en otras historias, los textos exactos en el código o en la aplicación. Este skill define dónde buscar, en qué orden, y cómo dejar registrado **lo que se encontró** y **lo que falta**.

## 1. ¿Ya hay una ficha?

Buscá `output/contexto/contexto-<HU>.md`. `<HU>` es el `HU-XXX` que usan los casos y reportes; si la historia solo tiene key, usá la key (`contexto-PROJ-12.md`). Antes de crear una ficha, buscá con Grep la key y el `HU-XXX` en `output/contexto/` para no duplicarla, y anotá los dos en el encabezado **Historia**.

- Si existe y la historia **no cambió** desde entonces (compará la fecha de última modificación de la historia —`updated` en Jira; si la historia es un archivo de `input/historias/`, su fecha de modificación— con la fecha de la ficha) y el dossier de `input/documentacion/` no es más nuevo que la ficha, **reusala** y no vuelvas a investigar: ahorra tokens.
- Si cambió, o la persona pide actualizarla, investigá de nuevo y reemplazá la ficha (conservá los `FI-XX` que sigan abiertos, con el mismo ID).

## 2. Primero, la documentación del proyecto

Si existe `input/documentacion/INDICE.md` (lo arma el agente `documentador-proyecto`), leelo **antes** que cualquier otra fuente: dice qué contexto hay, de dónde sale y si está vigente.

- **Dossier de la historia** (`input/documentacion/historias/<HU o key>/dossier.md`): ya trae la historia con sus comentarios, decisiones, vínculos, links, PRs y commits, archivos tocados, pantallas, contradicciones y pistas para probar. Si su `actualizado` es posterior al último cambio de la historia, **usalo como fuente principal** y no vuelvas a recorrer Jira (ahorra tokens); si es anterior, revisá solo lo que cambió después.
- **Documentos del proyecto** (`proyecto/`): abrí solo los que sirvan para la historia — `reglas-de-negocio.md`, `mensajes.md` y `estados-y-permisos.md` (buscá el módulo o el campo, no los leas enteros), `mapa-funcional.md` (los campos y textos reales de la pantalla) y `api/` (contratos).
- **Manual de usuario** (`manual-usuario/<modulo>.md`, si existe: lo deja el agente de manual de usuario de K0lmenIA Pro): cómo se usa la pantalla **verificado en la aplicación** y sus **Pistas para probar**. Lo de **Sin confirmar** va como `FI-XX`, nunca como resultado esperado.
- **Investigación del proyecto** (`proyecto/investigacion/`, si existe: la deja el agente de investigación de K0lmenIA Pro): módulos, flujos, decisiones y glosario. `dudas-y-riesgos.md` son ambigüedades abiertas (`AMB-XX`): si tocan la historia, van como `FI-XX` con su pregunta.
- **¿Sigue vigente?** Antes de usar un documento, mirá `cambios.md` (cambió el código), `cambios-historias.md` (la historia o sus PRs cambiaron después del dossier: requerimientos nuevos) y la sección *Cambios desde el recorrido anterior* de `proyecto/mapa-funcional.md` (cambió la aplicación). Si la historia o sus pantallas figuran ahí, **no uses el dossier o la ficha viejos como verdad**: investigá de nuevo lo que cambió y, en la respuesta, sugerí el modo *actualizar* del `documentador-proyecto` (no lo invoques vos).
- **Confiabilidad** (columna del índice y `estado:` del encabezado): `confirmado` (verificado en la app o aprobado) pesa más que `borrador`, y este más que `investigacion` (tickets y wiki, sin verificar); `sin-confirmar` nunca es un hecho. Si dos fuentes se contradicen (la historia dice una cosa y el manual muestra otra), **no elijas**: es un `FI-XX` con las dos fuentes. La app y el manual describen cómo funciona **hoy**; la historia, lo que se pidió.
- **Citá la fuente original** que figura en el documento (`src/...:línea`, el PR, el comentario), no solo el archivo de `input/documentacion/`.
- Las **Contradicciones y dudas** del dossier se registran como `FI-XX` en la ficha (sección 5).
- Si no hay documentación o está marcada como *Revisar* o *Desactualizado* (cambió el código; ver `input/documentacion/cambios.md`), seguí con las fuentes de la sección 3 y, en la respuesta, sugerí pedirle al `documentador-proyecto` que la arme o la actualice (no lo invoques vos).

## 3. Dónde buscar (en este orden)

```
+-------------------------+------------------------------------------+------------------------------+
| Fuente                  | Qué mirar                                | Cómo                         |
+=========================+==========================================+==============================+
| **Historia en Jira**    | Descripción, criterios de aceptación,    | Conector `atlassian`         |
|                         | estado, prioridad, labels, componentes,  |                              |
|                         | versión, adjuntos (nombres)              |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Comentarios**         | **Todos**, del más viejo al más nuevo.   | Conector `atlassian`         |
|                         | Suelen tener decisiones ("acordamos que  |                              |
|                         | el límite es 50") que reemplazan lo que  |                              |
|                         | dice la descripción                      |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Subtareas**           | Descripción y comentarios de cada una    | Conector `atlassian`         |
|                         | (ej. "Validar email en backend")         |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Épica / padre**       | Descripción y reglas generales de la     | Conector `atlassian`         |
|                         | funcionalidad; **historias hermanas** de |                              |
|                         | la misma épica (solo título y            |                              |
|                         | descripción) para entender el flujo      |                              |
|                         | completo                                 |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Issues vinculados**   | "relates to", "blocks", "is blocked by", | Conector `atlassian`         |
|                         | "duplicates", bugs vinculados (bugs ya   |                              |
|                         | conocidos del flujo)                     |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Contratos de API**    | Swagger/OpenAPI o colecciones de Postman | `curl` / lectura de archivos |
|                         | (URL o `input/api/`): campos,            |                              |
|                         | validaciones, códigos de respuesta       |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Documentación local** | `input/historias/`,                      | Lectura de archivos          |
|                         | `input/documentacion/` (sección 2 y lo   |                              |
|                         | que la persona dejó a mano)              |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Repositorio de la     | Solo si no hay dossier vigente: los      | `git log --grep <key>` y     |
| app**                   | commits con la key de la historia y las  | lectura de archivos en       |
|                         | validaciones o mensajes del código que   | `REPO_RUTA_LOCAL`            |
|                         | tocan (puntual; el recorrido completo es |                              |
|                         | del documentador-proyecto)               |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Trabajo previo**      | `output/analisis-historias/`, casos      | Lectura de archivos          |
|                         | anteriores de la misma historia o de     |                              |
|                         | historias hermanas, `.feature`           |                              |
|                         | existentes en k0lmena                    |                              |
+-------------------------+------------------------------------------+------------------------------+
```

**Si la historia está en otra herramienta de gestión** (Azure DevOps, Linear, ClickUp, monday.com, Asana, Trello, Notion, YouTrack, Shortcut, GitHub o GitLab Issues): leerla por conector está disponible en K0lmenIA Pro. En Light, pedile a la persona que la exporte o la pegue en `input/historias/` y avisá que los comentarios, subtareas y la épica no se pudieron revisar.

Límites para no gastar tokens de más: un solo nivel de profundidad desde la historia (sus vínculos directos, no los vínculos de los vínculos), y de cada fuente extraé solo lo que sirve para probar (reglas, validaciones, textos, estados, permisos, datos). No copies páginas enteras.

**Si un conector no está activo** (por ejemplo, no está `atlassian`), no lo reemplaces con suposiciones: anotá la fuente como **No disponible** en la ficha y seguí con las demás. Si la historia vino pegada en el chat o en `input/`, avisá que los comentarios, subtareas y la épica no se pudieron revisar.

## 4. Cómo interpretar lo que encontrás

- **Comentario vs. descripción**: un comentario más nuevo que registra una **decisión** (de PO, analista o equipo) reemplaza a la descripción. Citá quién y cuándo.
- **Contradicciones**: si dos fuentes dicen cosas distintas y ninguna es una decisión explícita posterior, **no elijas**: registralo como contradicción y como `FI-XX`.
- **La app no es fuente de requisitos**: lo que hace hoy la aplicación sirve como observación, pero no define el resultado esperado.
- **El código tampoco**: una validación o un mensaje del repositorio dice cómo está implementado hoy. Sirve para concretar un dato que la historia deja abierto (el texto exacto de un error, un largo máximo) citándolo como *observado en el código*; si contradice a la historia o a una decisión, es contradicción y `FI-XX`, no el resultado esperado.

## 5. "Falta información" (FI-XX)

Todo dato necesario para probar que **no aparece en ninguna fuente** (o aparece contradictorio) se registra como un ítem `FI-XX`, numerado por historia (`FI-01`, `FI-02`, …):

- **Qué falta**: concreto ("texto del mensaje de error al ingresar un email inválido"), no genérico ("faltan detalles").
- **Dónde se buscó**: las fuentes revisadas, para que nadie repita la búsqueda.
- **Impacto**: qué criterios o casos afecta.
- **Pregunta**: lista para mandarle al PO.
- **Estado**: `Abierto` hasta que alguien lo responda; entonces `Resuelto` con la respuesta y la fuente.

Reglas que valen para todos los agentes:

1. **No inventar**: si un caso depende de un `FI-XX`, se escribe igual pero marcado (ver abajo). Si se usa un supuesto para poder escribirlo, se aclara como supuesto ligado a ese `FI-XX`.
2. **Marcar en cada artefacto**:
   - Casos manuales (JSON de `generar_casos.py`): campo `"falta_info": ["FI-01"]` en el caso y la lista `"falta_informacion"` en la raíz. El script resalta esos casos, suma la etiqueta `@falta-info` y agrega la hoja *Falta información*.
   - Casos BDD y `.feature` de k0lmena: tags `@falta-info @FI-01` en el escenario y un comentario `# FALTA INFORMACIÓN (FI-01): <qué falta>` arriba.
   - Informes de cobertura: sección **Falta información** y, en la tabla por criterio, cobertura `Parcial (falta información)`.
   - Reporte de mapeo: estado `Falta información` en los pasos afectados.
   - Reportes de ejecución e informe de cierre: campo `falta_info` en cada caso y lista `falta_informacion` (ver los scripts).
3. **Reusar los IDs**: el mismo `FI-01` viaja de la ficha a los casos, al `.feature`, a los reportes y a la herramienta de gestión. Así, cuando el PO responde, se sabe qué cambiar.

## 6. La ficha de contexto

Guardala en `output/contexto/contexto-<HU>.md` siguiendo `${CLAUDE_PLUGIN_ROOT}/plantillas/plantilla-contexto.md` y normalizala con `k0lmenia py scripts/formatear_tablas.py`. Secciones: fuentes consultadas (incluidos los documentos de `input/documentacion/` que usaste), resumen de la funcionalidad, reglas y hallazgos por criterio (cada uno con su fuente), decisiones en comentarios, contradicciones y **Falta información**. Respondé a la persona con un resumen corto: fuentes revisadas, hallazgos clave y la lista de `FI-XX` abiertos.

## 7. Versión en inglés (solo a pedido)

La ficha va en español. Si el pedido dice *"Versión en inglés: sí"* (la conversación principal lo pregunta, o `DOCUMENTACION_EN=si` en el `.env`), escribí al lado `contexto-<HU>.en.md` con el mismo contenido traducido (inglés claro de QA; IDs, rutas y citas textuales de las fuentes sin traducir). El HTML de la ficha queda en los dos idiomas, con sus banderitas. Sin ese pedido, no la escribas.

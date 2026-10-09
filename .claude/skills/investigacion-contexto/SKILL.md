---
name: investigacion-contexto
description: Cómo investigar a fondo una historia o funcionalidad antes de analizarla, planificarla, escribir casos o automatizarla — la historia de Jira o de Azure DevOps (Azure Boards) con sus comentarios, subtareas, épica e issues vinculados, las páginas de Confluence relacionadas, los diseños de Figma, contratos de API y documentación local — y cómo registrar lo que falta como "Falta información" (FI-XX) en una ficha de contexto reutilizable. Úsalo en analista-historias, estratega-pruebas, los generadores de casos y los mappers cuando trabajen sobre una historia.
---

# Investigación de contexto

Antes de suponer, **buscar**. Una historia casi nunca tiene toda la información en su descripción: las decisiones suelen estar en los comentarios, las reglas en la épica o en Confluence, los textos exactos en Figma. Este skill define dónde buscar, en qué orden, y cómo dejar registrado **lo que se encontró** y **lo que falta**.

## 1. ¿Ya hay una ficha?

Buscá `output/contexto/contexto-<HU>.md`.

- Si existe y la historia **no cambió** desde entonces (compará el campo `updated` de Jira con la fecha de la ficha), **reusala** y no vuelvas a investigar: ahorra tokens.
- Si cambió, o la persona pide actualizarla, investigá de nuevo y reemplazá la ficha (conservá los `FI-XX` que sigan abiertos, con el mismo ID).

## 2. Dónde buscar (en este orden)

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
| **Confluence**          | Páginas enlazadas desde la historia, la  | Conector `atlassian`         |
|                         | épica o los comentarios; si no hay       |                              |
|                         | enlaces, una búsqueda por el nombre de   |                              |
|                         | la funcionalidad en el espacio del       |                              |
|                         | proyecto (como máximo 5 resultados, leé  |                              |
|                         | solo los relevantes)                     |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Figma**               | Links a diseños en la historia, la épica | Conector `figma`             |
|                         | o los comentarios: textos exactos,       |                              |
|                         | mensajes de error, estados (vacío,       |                              |
|                         | cargando, error), campos obligatorios    |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Contratos de API**    | Swagger/OpenAPI o colecciones de Postman | `curl` / lectura de archivos |
|                         | (URL o `input/api/`): campos,            |                              |
|                         | validaciones, códigos de respuesta       |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Documentación local** | `input/historias/`,                      | Lectura de archivos          |
|                         | `input/documentacion/`                   |                              |
+-------------------------+------------------------------------------+------------------------------+
| **Trabajo previo**      | `output/analisis-historias/`, casos      | Lectura de archivos          |
|                         | anteriores de la misma historia o de     |                              |
|                         | historias hermanas, `.feature`           |                              |
|                         | existentes en k0lmena                    |                              |
+-------------------------+------------------------------------------+------------------------------+
```

**Si la historia está en Azure DevOps** (Azure Boards, conector `azure-devops`), se recorren las mismas fuentes con sus equivalentes: el work item (*User Story* / *Product Backlog Item*) con `wit_work_item` (`get`, campos de descripción y *Acceptance Criteria*), sus comentarios (`list_comments`), las *Tasks* hijas, el padre (*Feature* / *Epic*), los vínculos (*Related*, *Predecessor/Successor*, *Tested By*, bugs) y la **Wiki** del proyecto en lugar de Confluence (`wiki`, `search_wiki`). La fecha de cambio para reusar la ficha es `System.ChangedDate`.

Límites para no gastar tokens de más: un solo nivel de profundidad desde la historia (sus vínculos directos, no los vínculos de los vínculos), y de cada fuente extraé solo lo que sirve para probar (reglas, validaciones, textos, estados, permisos, datos). No copies páginas enteras.

**Si un conector no está activo** (por ejemplo, no hay `atlassian` o `azure-devops`), no lo reemplaces con suposiciones: anotá la fuente como **No disponible** en la ficha y seguí con las demás. Si la historia vino pegada en el chat o en `input/`, avisá que los comentarios, subtareas y la épica no se pudieron revisar.

## 3. Cómo interpretar lo que encontrás

- **Comentario vs. descripción**: un comentario más nuevo que registra una **decisión** (de PO, analista o equipo) reemplaza a la descripción. Citá quién y cuándo.
- **Contradicciones**: si dos fuentes dicen cosas distintas y ninguna es una decisión explícita posterior, **no elijas**: registralo como contradicción y como `FI-XX`.
- **Diseño vs. historia**: los textos de Figma valen como fuente para mensajes y etiquetas; si contradicen la historia, es contradicción.
- **La app no es fuente de requisitos**: lo que hace hoy la aplicación sirve como observación, pero no define el resultado esperado.

## 4. "Falta información" (FI-XX)

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

## 5. La ficha de contexto

Guardala en `output/contexto/contexto-<HU>.md` siguiendo `plantillas/plantilla-contexto.md` y normalizala con `python scripts/formatear_tablas.py`. Secciones: fuentes consultadas, resumen de la funcionalidad, reglas y hallazgos por criterio (cada uno con su fuente), decisiones en comentarios, contradicciones y **Falta información**. Respondé a la persona con un resumen corto: fuentes revisadas, hallazgos clave y la lista de `FI-XX` abiertos.

---
name: relevamiento-proyecto
description: El cómo de relevar un proyecto ENTERO por MCP (no una historia) — barrer Jira, Confluence, Azure DevOps, GitHub, GitLab y las demás herramientas con consultas acotadas, muestrear backlogs grandes, extraer módulos, flujos y decisiones, y detectar ambigüedades y preguntas para el equipo. Lo usa el investigador-proyecto.
---

# Relevamiento de proyecto

El skill `investigacion-contexto` investiga **una historia** a fondo. Este skill releva **un proyecto completo** a lo ancho: qué es el producto, en qué estado está, quién decide, qué está claro y qué no. La meta es que una persona que recién llega entienda el proyecto en una lectura y sepa **qué preguntar**.

Regla de oro: **amplitud primero, profundidad solo donde hace falta.** Un proyecto puede tener miles de issues; no se leen todos. Se lee la estructura (épicas, componentes, wiki, README) completa y el detalle se muestrea con criterio.

## 1. Desde una URL de tablero

Lo más común es que la persona pegue **la URL de un tablero** (board, dashboard, backlog o proyecto). De ahí sacás la herramienta y el proyecto/board, sin pedir nada más:

```
+------------------------------------------------------------------+------------------------------------------------+
| URL (ejemplos)                                                   | De ahí sale                                    |
+==================================================================+================================================+
| .../jira/software/projects/PROJ/boards/12                        | Jira (atlassian), proyecto PROJ, board 12      |
| .../jira/software/c/projects/PROJ/boards/12/backlog              | Jira, proyecto PROJ (backlog)                  |
| .../jira/dashboards/10200                                        | Jira dashboard: leé sus gadgets para el/los    |
|                                                                  | proyecto(s) y filtros                          |
| .../browse/PROJ-123                                              | Jira, proyecto PROJ (issue de entrada)         |
| dev.azure.com/ORG/PROY/_boards/board/t/EQUIPO/Stories           | Azure DevOps, org ORG, proyecto PROY, equipo   |
| dev.azure.com/ORG/PROY/_backlogs/backlog/EQUIPO/Epics           | Azure DevOps, proyecto PROY, nivel Epics       |
| dev.azure.com/ORG/PROY/_sprints/...                              | Azure DevOps, proyecto PROY, iteración         |
| linear.app/EMPRESA/team/ENG/board                                | Linear, team ENG                               |
| trello.com/b/abc123/tablero                                      | Trello, board abc123                           |
| EMPRESA.monday.com/boards/123456                                 | monday.com, board 123456                       |
| app.clickup.com/9999/v/b/li/123                                  | ClickUp, lista/espacio                         |
| notion.so/EMPRESA/Tablero-abc...                                 | Notion, base de datos de ese tablero           |
| github.com/ORG/REPO/projects/4  ·  .../issues                   | GitHub Projects / issues del repo ORG/REPO     |
| gitlab.com/GRUPO/PROY/-/boards                                   | GitLab, proyecto GRUPO/PROY                     |
+------------------------------------------------------------------+------------------------------------------------+
```

Reglas al partir de una URL:
- **Verificá el conector**: si la URL es de Jira y `atlassian` no está activo (o de Azure DevOps y `azure-devops` no está, etc.), no inventes: decí qué activar (`k0lmenia conector -- activar <nombre>`, `CONECTORES.md`) y seguí con lo que sí tengas.
- **Un dashboard** no es un proyecto: leé sus gadgets/filtros para descubrir el o los proyectos, los JQL/consultas guardadas y los board(s) que referencia, y relevá esos.
- **Un board filtrado** (por un JQL, un equipo, una etiqueta) acota el alcance: relevá lo que el board muestra y decilo (el proyecto puede tener más que ese board).
- Si la URL no alcanza para identificar el proyecto (acortada, un SSO de por medio), pedí la key o el nombre del proyecto.

## 2. Alcance del relevamiento

Antes de leer, fijá (del pedido, de la URL o del `.env`):

- **Qué proyecto**: key de Jira (`PROJ`), proyecto de Azure DevOps (`ADO_PROYECTO`), espacio de Confluence, team de Linear, workspace de la herramienta, repositorio (`REPO_PROVEEDOR` + `REPO_NOMBRE`).
- **Ventana de tiempo** para lo "activo": por defecto, los **últimos 90 días** (lo que se movió en ese período) + todo lo que esté abierto.
- **Profundidad**: `rapida` (estructura + muestra chica, ~30 ítems), `normal` (por defecto, ~80 ítems leídos en detalle), `completa` (~200 ítems; solo si la persona lo pide: gasta muchos tokens) o `total` (ver abajo).
- **`total`** (cuando la persona quiere **todo** el proyecto, por ejemplo para documentarlo entero y escribir casos de todo): sin ventana de tiempo y **sin muestreo de la estructura**: listás **todos** los ítems paginando hasta el final (épicas, historias, tareas, subtareas y bugs, con estado, épica, responsable, prioridad, fecha de cambio y cantidad de comentarios) y armás el árbol **completo** en `jerarquia`; el detalle (descripción, criterios, comentarios, links) lo leés de lo crítico, lo ambiguo y lo más discutido, como en `completa`. El detalle **de cada historia** no se hace acá: recomendá en *Próximos pasos* el **modo barrido** del `documentador-proyecto` con el mismo alcance (arma un dossier por historia con todos sus comentarios, subtareas, vínculos y PRs, en lotes, y es incremental). Declarás la cobertura igual: total de ítems listados y cuántos leídos en detalle.
- **Foco opcional**: un módulo, una épica o una release ("relevá solo el módulo de pagos").

Si no hay ninguna herramienta conectada ni material en `input/`, no hay relevamiento posible: devolvé qué conectores activar (`k0lmenia configurar` o `k0lmenia conector -- activar <nombre>`, ver `CONECTORES.md`).

## 3. Orden de lectura

```
+----+------------------------------+-----------------------------------------------+
| #  | Fuente                       | Para qué                                      |
+====+==============================+===============================================+
| 1  | input/documentacion/         | Si el documentador-proyecto ya armó la base,  |
|    | (INDICE.md, proyecto/)       | reusala: no vuelvas a leer lo que ya está     |
|    |                              | vigente. Leé solo lo marcado Revisar o lo que |
|    |                              | no cubre                                      |
+----+------------------------------+-----------------------------------------------+
| 2  | Wiki / Confluence / Notion   | Visión del producto, arquitectura, glosario,  |
|    | (páginas raíz del espacio)   | ambientes, integraciones, decisiones (ADR),   |
|    |                              | onboarding existente                          |
+----+------------------------------+-----------------------------------------------+
| 3  | Épicas / Features            | El mapa de módulos y el estado de cada uno    |
|    | (todas, solo título,         |                                               |
|    | estado, descripción corta)   |                                               |
+----+------------------------------+-----------------------------------------------+
| 4  | Backlog activo (muestra)     | Qué se está haciendo, cómo se escriben las    |
|    |                              | historias, qué criterios faltan               |
+----+------------------------------+-----------------------------------------------+
| 5  | Bugs abiertos (conteo +      | Zonas frágiles del producto, severidades      |
|    | los Críticos/Altos)          |                                               |
+----+------------------------------+-----------------------------------------------+
| 6  | Sprints / iteraciones /      | Ritmo del equipo, próxima entrega, fechas     |
|    | releases / versiones         |                                               |
+----+------------------------------+-----------------------------------------------+
| 7  | Repositorio (README, docs/,  | Stack, cómo se levanta, ambientes, CI,        |
|    | CODEOWNERS, CI, .env.example | quién es dueño de qué. Solo lectura y sin     |
|    | de la app)                   | copiar secretos                               |
+----+------------------------------+-----------------------------------------------+
| 8  | Figma (archivos enlazados    | Pantallas y flujos diseñados vs. lo que dice  |
|    | desde épicas o wiki)         | el backlog                                    |
+----+------------------------------+-----------------------------------------------+
| 9  | Gestión de pruebas (Test     | Qué se prueba hoy, si hay regresión, si hay   |
|    | Plans, Xray, output/)        | automatización                                |
+----+------------------------------+-----------------------------------------------+
```

## 4. Consultas por herramienta (acotadas)

Pedí siempre **solo los campos que necesitás** y con **límite de resultados**. Paginá solo si el conteo lo justifica.

### Jira y Confluence (conector `atlassian`)

- Épicas: `project = PROJ AND issuetype = Epic ORDER BY updated DESC` (todas; campos `summary, status, description` recortada, `fixVersions`).
- Conteos por estado y tipo (sin traer los issues): una búsqueda por cada combinación relevante o el total que devuelve la búsqueda con `maxResults` chico.
- Backlog activo: `project = PROJ AND issuetype in (Story, Task) AND (statusCategory != Done OR updated >= -90d) ORDER BY priority DESC, updated DESC`.
- Bugs abiertos: `project = PROJ AND issuetype = Bug AND statusCategory != Done ORDER BY priority DESC`.
- Historias sin criterios / sin descripción (señales de ambigüedad): `project = PROJ AND issuetype = Story AND statusCategory != Done AND description is EMPTY`.
- Bloqueadas o con dependencias: `project = PROJ AND (status = Blocked OR issueLinkType = "is blocked by") AND statusCategory != Done`.
- Versiones y sprints: las versiones del proyecto (`fixVersions` con su fecha) y el sprint activo (`sprint in openSprints()`).
- Confluence: el árbol del espacio (títulos) y leé las páginas raíz y las que se llamen como *Visión*, *Arquitectura*, *Glosario*, *Ambientes*, *Onboarding*, *Decisiones*, *Reglas de negocio*, *Integraciones*. Una búsqueda CQL por espacio y título (`space = ESP AND title ~ "arquitectura"`), como máximo 15 páginas.

### Azure DevOps (conector `azure-devops`)

- Work items por WIQL (dominio `work-items`): épicas y features (`[System.WorkItemType] IN ('Epic','Feature')`), backlog activo (`[System.State] <> 'Closed' OR [System.ChangedDate] >= @Today - 90`), bugs abiertos ordenados por `Microsoft.VSTS.Common.Severity`.
- Iteraciones y áreas del proyecto (dominio `work`): la iteración actual y las próximas con sus fechas; las **áreas** son a menudo el mejor mapa de módulos.
- Wiki (dominio `wiki`): el árbol de páginas y las páginas clave (mismos títulos que en Confluence).
- Repos (dominio `repositories`): README, `docs/`, pipelines (`azure-pipelines.yml`) y PRs recientes (títulos).
- Test Plans (dominio `test-plans`): planes y suites existentes (solo nombres y conteos).
- Fecha de cambio: `System.ChangedDate`; responsable: `System.AssignedTo` (nombre visible).

### Otras herramientas

Usá las equivalencias de la tabla del skill `investigacion-contexto` (sección *Dónde buscar*): proyecto/ciclo de Linear, listas y espacios de ClickUp, tableros y grupos de monday.com, proyectos y secciones de Asana, listas de Trello, bases de datos de Notion, proyectos de YouTrack, épicas e iteraciones de Shortcut, milestones e issues de GitHub/GitLab. En todas: **la estructura completa, el detalle muestreado**.

### Repositorio (`github`, `gitlab`, `azure-devops`, `atlassian` para Bitbucket)

Solo lectura y solo lo general: `README`, `docs/`, `CONTRIBUTING`, `CODEOWNERS`, archivos de CI, `docker-compose`, `.env.example` de la app (**nombres** de variables, nunca valores), estructura de carpetas de primer y segundo nivel. El recorrido fino de reglas del código es del `documentador-proyecto`.

## 5. Muestreo de backlogs grandes

Con más ítems que la profundidad elegida, leé en detalle (descripción, criterios y comentarios) una muestra **estratificada**:

1. Todo lo **Crítico/Alto** abierto (historias y bugs), hasta un tercio de la muestra.
2. Lo del **sprint o iteración actual** y la próxima release.
3. **Al menos 2 ítems por épica activa** (para que ningún módulo quede ciego).
4. Lo **más comentado** o **más reabierto** (señal de discusión o ambigüedad).
5. El resto, lo más recientemente actualizado.

Del resto, solo conteos (por estado, tipo, épica, prioridad). En el informe, declarás **cuántos ítems hay, cuántos leíste en detalle y con qué criterio**: el lector tiene que saber qué tan representativo es.

### Recorrido profundo (épica → historia → tarea → comentarios → links)

Para cada ítem de la muestra, bajá por la jerarquía y traé lo que sirve para entender y probar:

1. **Épica / feature**: título, estado, descripción, y la lista de **historias** que cuelgan (con su estado). De ahí salen los módulos y su avance (historias hechas / total).
2. **Historia**: descripción, **criterios de aceptación** (o la falta de ellos → vacío), estado, responsable (nombre visible), prioridad, y la lista de **tareas/subtareas** con su estado. Contá las tareas; leé en detalle solo las que aporten reglas.
3. **Tareas / subtareas**: lo técnico que concreta la historia (validación en backend, endpoint, job); de acá salen integraciones y detalles de implementación.
4. **Comentarios** (de la épica, la historia y las tareas): **del más viejo al más nuevo**. Son oro: las decisiones ("acordamos 12 cuotas"), los cambios de criterio y las dudas abiertas viven acá. Un comentario con una **decisión** posterior pisa la descripción (citá quién y cuándo); una discusión sin cerrar es una ambigüedad o un vacío.
5. **Links de referencia**: todo enlace que aparezca en la descripción o los comentarios — Confluence/Wiki, Figma, Google Docs/SharePoint, un repo, un contrato de API, una URL externa. Seguilos **un solo nivel**:
   - Con conector (Confluence, Wiki de Azure DevOps, Figma): abrilos y extraé lo que sirve.
   - Privados sin conector (Google Docs, SharePoint, Notion ajeno): **no** inventes su contenido; anotalos como referencia **Pendiente** con de dónde salen y qué conector/permiso haría falta.
   - Juntá **todos** los links en una lista de referencias (tipo, título, URL, de qué ítem salió, si se leyó): es lo que un QA nuevo va a querer abrir primero.

Esto alimenta la sección **"Épicas, historias y tareas"** del informe (el árbol recorrido, con comentarios y links por ítem) y la de **"Links de referencia"**. Un solo nivel de profundidad desde cada ítem (sus tareas y sus links directos, no los links de los links), y de cada fuente solo lo que sirve para probar: no copies páginas enteras.

## 6. Qué extraer

- **Resumen del producto**: qué es, para quién, qué problema resuelve, en una o dos frases citables.
- **Módulos**: de épicas, áreas, componentes o carpetas del repo; cada uno con su estado (en desarrollo, estable, planificado), su avance (historias hechas / total) y su fuente.
- **Actores y roles** de la aplicación (no del equipo): quién usa qué.
- **Flujos clave** de punta a punta (alta, compra, aprobación…), con las épicas o historias que los implementan.
- **Integraciones**: sistemas externos (pasarelas de pago, CRM, ERP, proveedores de identidad, colas, terceros) con el tipo de integración si está documentado.
- **Ambientes**: dev, QA, staging, producción, con su URL **solo si es pública o está en la documentación** (nunca credenciales).
- **Stack y arquitectura** a grandes rasgos (del repo y la wiki).
- **Equipo y a quién preguntar**: roles (PO, líder técnico, QA lead, diseño) con el **nombre visible** que figura en la herramienta. Nada de emails, teléfonos ni datos personales.
- **Decisiones registradas**: qué se decidió, quién, cuándo y dónde (comentario, ADR, página).
- **Estado del backlog**: totales por estado y tipo, bugs abiertos por severidad, sprint/iteración actual y próximas releases con fecha.
- **Cómo se prueba hoy**: planes de prueba, suites, automatización, qué no se prueba.
- **Glosario**: términos del dominio y siglas, con su definición y fuente.
- **Línea de tiempo**: hitos pasados y próximos (releases, sprints, go-lives).

Cada dato **con su fuente** (`PROJ-12`, `Confluence "Arquitectura"`, `wiki/Ambientes`, `README.md`, `#318`). Lo que no tiene fuente no entra.

## 7. Mapas conceptuales

Para que se entienda **cómo está armado** y **cómo funciona** el proyecto, armá al menos dos mapas (van al campo `mapas` del JSON y se dibujan como diagramas en el informe y en la presentación):

- **Arquitectura**: las piezas del sistema y cómo se conectan — frontend(s), backend/servicios, base(s) de datos, colas, y **sistemas externos** (pasarela de pago, identidad, terceros). Agrupá por capa (`grupo`: Frontend, Backend, Datos, Externos). Sale del repo (README, `docker-compose`, carpetas), la wiki y los diagramas que existan.
- **Cómo funciona**: el **flujo principal** de punta a punta (comprar, dar de alta, aprobar, cobrar), paso a paso, con las ramas importantes (ok / rechazo / reintento). Sale de las épicas, las historias y el mapa funcional.
- Opcional: **módulos / dominio** (el producto y sus módulos y submódulos), útil cuando la arquitectura no está documentada.

Cada mapa es una lista de **nodos** (`id`, `etiqueta`, `grupo`, `nota` corta) y **enlaces** dirigidos (`de`, `a`, `etiqueta` opcional en la flecha). El nodo sin flechas entrantes es la raíz; las columnas y la leyenda se calculan solas. **Armalos solo con lo relevado**: si no hay evidencia de la arquitectura, no la inventes — dejá el mapa de módulos y registrá el vacío como `AMB-XX`.

## 8. Ambigüedades, contradicciones y vacíos

Es la parte más valiosa para un QA nuevo. Clasificá cada hallazgo:

```
+-----------------+------------------------------------------+---------------------------------------------+
| Tipo            | Qué es                                   | Señales para encontrarlo                    |
+=================+==========================================+=============================================+
| Ambigüedad      | Un texto admite más de una lectura       | "rápido", "fácil", "etc.", "y/o", "según    |
|                 |                                          | corresponda", "similar a", "debería",       |
|                 |                                          | "manejar errores", criterios sin números,   |
|                 |                                          | sin actor o sin resultado observable        |
+-----------------+------------------------------------------+---------------------------------------------+
| Contradicción   | Dos fuentes dicen cosas distintas        | Historia vs. épica, descripción vs.         |
|                 |                                          | comentario sin decisión explícita, wiki vs. |
|                 |                                          | backlog, Figma vs. historia, README vs.     |
|                 |                                          | wiki (ambientes, versiones)                 |
+-----------------+------------------------------------------+---------------------------------------------+
| Vacío           | Algo necesario no está en ninguna fuente | Historias sin criterios de aceptación,      |
|                 |                                          | módulos sin documentación, roles sin        |
|                 |                                          | permisos definidos, integraciones sin       |
|                 |                                          | contrato, sin ambientes documentados, sin   |
|                 |                                          | definición de "hecho"                       |
+-----------------+------------------------------------------+---------------------------------------------+
| Desactualizado  | La documentación no refleja el estado    | Páginas sin editar hace más de 6 meses que  |
|                 | actual                                   | describen módulos que siguen cambiando;     |
|                 |                                          | épicas cerradas con historias abiertas;     |
|                 |                                          | releases con fecha pasada y sin cerrar      |
+-----------------+------------------------------------------+---------------------------------------------+
| Dependencia     | Algo bloquea o depende de un tercero o   | Issues "blocked by", integraciones sin      |
|                 | de otra decisión pendiente               | sandbox, decisiones "a definir"             |
+-----------------+------------------------------------------+---------------------------------------------+
```

Para cada uno registrá: **ID** (`AMB-01`, `AMB-02`, …, numeración del relevamiento), **tipo**, **qué** (concreto: *"PROJ-45 dice 'el reembolso es inmediato' y la página 'Reglas de pagos' dice 48 h hábiles"*), **fuentes** (las dos, si es contradicción), **impacto** para probar (`Alta`, `Media`, `Baja`) y la **pregunta** que lo resuelve.

No elijas entre dos fuentes contradictorias ni rellenes un vacío: **se pregunta**. Si una historia concreta queda con un dato faltante, además del `AMB-XX` mencioná que corresponde un `FI-XX` en su ficha (se registra con `investigacion-contexto` cuando alguien trabaje esa historia).

## 9. Preguntas para el equipo

Cada ambigüedad, contradicción o vacío relevante termina en una **pregunta** (`P-01`, `P-02`, …):

- **Concreta y respondible** (*"¿El reembolso con tarjeta es inmediato o tarda hasta 48 h hábiles? (PROJ-45 vs. 'Reglas de pagos')"*), nunca *"¿Cómo funcionan los reembolsos?"*.
- **A quién**: PO, líder técnico, QA lead, diseño, negocio, seguridad, infraestructura (el rol; si la herramienta muestra quién es, su nombre visible).
- **Prioridad** (`Crítica`, `Alta`, `Media`, `Baja`): Crítica si bloquea probar algo de la próxima entrega; Alta si afecta un flujo principal.
- **Por qué importa** y el **AMB-XX** o la historia relacionada.

Además, una lista corta de **preguntas de arranque** que todo QA nuevo debería hacer aunque no salgan de un hallazgo, solo las que la documentación no responda: accesos y ambientes, datos de prueba, definición de hecho, cómo se reportan y priorizan los bugs, qué se automatiza, ventanas de despliegue, quién aprueba una release.

## 10. Riesgos para QA

De lo relevado, los riesgos que afectan cómo probar (no riesgos de negocio genéricos): módulos críticos sin criterios, integraciones sin sandbox, bugs críticos abiertos en un flujo principal, releases cercanas con historias sin definir, ausencia de ambientes de prueba, sin automatización de regresión. Cada uno con nivel (`Alto`, `Medio`, `Bajo`), motivo y mitigación sugerida.

## 11. Fuentes no disponibles

Si un conector no está activo, una página es privada o la búsqueda devuelve error, anotá la fuente como **No accesible** con el motivo y qué haría falta (activar el conector, un permiso, un token). Nunca reemplaces una fuente inaccesible con suposiciones. El informe tiene que dejar claro **qué se leyó y qué no**.

## 12. Higiene

- **Sin secretos ni datos personales**: ni tokens, ni contraseñas, ni emails, ni teléfonos, ni datos de clientes que aparezcan en tickets. Si un ticket los expone, mencioná que el ticket tiene datos sensibles sin copiarlos.
- **Solo lectura**: no comentás, no cambiás estados, no creás nada en ninguna herramienta.
- **Citas cortas**: extraé la regla o la frase, no pegues páginas enteras.
- **Fechas absolutas** (`2026-10-19`), nunca "la semana pasada".

## Referencia del `investigador-proyecto`

El recorrido, qué extraer, los mapas, las ambigüedades (`AMB-XX`), las preguntas (`P-XX`) y los riesgos están en las secciones de arriba. Esto es lo propio del informe.

**Próximos pasos** para el QA que llega, con pedidos reales de este proyecto: `guia-onboarding`, `documentador-proyecto` si falta la base (en **modo barrido** con el mismo alcance si la profundidad fue `total`), `analista-historias` para las historias más ambiguas, `estratega-pruebas` para la próxima release, `consultor-proyecto` para dudas puntuales.

### JSON e informe

`output/investigacion/<proyecto>/investigacion.json` (`<proyecto>`: la key o el nombre en minúsculas, sin acentos y con guiones), con el esquema del encabezado de `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_investigacion.py` y un **resumen** breve y claro. Con `k0lmenia py scripts/generar_informe_investigacion.py output/investigacion/<proyecto>/investigacion.json` quedan en esa carpeta:

- `informe-investigacion.html` (la web completa, con los mapas, buscador y navegación; en español e inglés), `informe-investigacion.md`, `resumen.md` (una carilla) y `presentacion-investigacion.html` (←/→ para pasar diapos; imprime a PDF, una por hoja);
- el relevamiento anterior archivado en `historial/`;
- lo relevado como documentación del proyecto en `input/documentacion/proyecto/investigacion/` (`resumen.md`, `modulos-y-flujos.md`, `backlog.md`, `decisiones-y-glosario.md`, `dudas-y-riesgos.md`, con estado `investigacion` o `sin-confirmar`) y el `INDICE.md` regenerado, para que los agentes que analizan historias y escriben casos lo usen como contexto. Por eso cada dato lleva su **fuente** y nada de datos personales más allá del nombre visible y el rol.

### Antes de entregar

- Cada módulo, regla, decisión, integración y ambiente tiene **fuente**; lo que no la tiene salió del informe o pasó a pregunta.
- Toda contradicción tiene **sus dos fuentes** y una pregunta asociada.
- La **cobertura** está declarada: total de ítems, leídos en detalle y criterio de la muestra.
- Las fuentes **No accesibles** están listadas con qué haría falta.
- No hay **secretos ni datos personales** (emails, teléfonos, tokens, datos de clientes) en el JSON ni en el informe.
- No se escribió, comentó ni cambió nada en ninguna herramienta.
- El JSON es válido y el informe se generó sin error.

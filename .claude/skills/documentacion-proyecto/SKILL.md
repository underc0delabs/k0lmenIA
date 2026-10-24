---
name: documentacion-proyecto
description: Referencia del documentador-proyecto — cómo leer el repositorio por proveedor y qué buscar en el código, el mapa funcional, qué se guarda en input/documentacion/ (encabezado, fuentes, dossier), y los pasos detallados de los modos barrido y actualizar con scripts/cambios_documentacion.py.
---

# Documentación del proyecto — referencia

Material de consulta del agente `documentador-proyecto`. El flujo y las reglas están en el agente; acá, el detalle de cada paso.

## 1. Repositorio de la aplicación (solo lectura)

```
+--------------+--------------------------------+--------------------------------------------------+
| Proveedor    | Conector                       | Herramientas de lectura (las de escritura NO)    |
+==============+================================+==================================================+
| github       | `github` (remoto, modo solo    | contenido de archivos y árbol del repo,          |
|              | lectura)                       | búsqueda de código, commits, pull requests       |
|              |                                | (detalle, archivos, diff, comentarios), issues   |
+--------------+--------------------------------+--------------------------------------------------+
| gitlab       | `gitlab`                       | toolsets `repository`, `merge_requests`,         |
|              |                                | `work_items` y `wikis`                           |
+--------------+--------------------------------+--------------------------------------------------+
| azure-repos  | `azure-devops` (dominio        | `repo_repository`, `repo_file` (`get_content`,   |
|              | `repositories`)                | `list_directory`), `repo_pull_request`,          |
|              |                                | `repo_pull_request_thread`,                      |
|              |                                | `repo_search_commits`, `search_code`             |
+--------------+--------------------------------+--------------------------------------------------+
| bitbucket    | `atlassian` (Bitbucket Cloud,  | `bitbucketRepoContent`, `bitbucketPullRequest`   |
|              | con autenticación por token)   | (`get`, `list`, `comments`, `diff`), commits     |
+--------------+--------------------------------+--------------------------------------------------+
```

- **Nunca uses una herramienta que escriba** (crear o actualizar archivos, ramas, PRs, comentarios, votos, merges), aunque el conector la ofrezca.
- **Con `REPO_RUTA_LOCAL`**, el código se lee de ahí con Grep, Glob y Read (más rápido y sin gastar tokens del conector); PRs y commits se siguen leyendo por el conector. Antes, verificá que sea el mismo repositorio (`git -C <ruta> remote -v`) y anotá la rama y el commit (`git -C <ruta> rev-parse --abbrev-ref HEAD` / `--short HEAD`). No hagas `pull`, `checkout` ni nada que cambie el clon.
- **Leé con método, no todo**: primero el README, la carpeta `docs/` y el árbol de primer y segundo nivel; con eso identificá el stack y los módulos, y después buscá en el código lo que sirve para probar. No abras dependencias (`node_modules`, `vendor`), builds (`dist`, `build`, `target`), archivos minificados, lockfiles ni binarios.

Qué buscar en el código (según el stack; ejemplos, no una lista cerrada):

```
+---------------------------+------------------------------------------------------------------+
| Para documentar           | Dónde suele estar                                                |
+===========================+==================================================================+
| Validaciones y límites    | Esquemas (zod, yup, joi, class-validator, pydantic, Bean         |
|                           | Validation `@NotNull @Size @Pattern`, FluentValidation, Rails    |
|                           | `validates`, Django forms/models), regex, constantes `MAX_`,     |
|                           | `MIN_`, `LIMIT`, `TIMEOUT`                                       |
+---------------------------+------------------------------------------------------------------+
| Mensajes y textos         | Archivos de idioma (`locales/*.json`, `i18n/`,                   |
|                           | `messages*.properties`, `*.po`, `*.resx`), constantes de errores |
+---------------------------+------------------------------------------------------------------+
| Estados y transiciones    | `enum`, campos `status`/`estado`, máquinas de estado, flujos de  |
|                           | aprobación                                                       |
+---------------------------+------------------------------------------------------------------+
| Roles y permisos          | Guards, middlewares, `@PreAuthorize`, policies, configuración    |
|                           | RBAC, menús por rol                                              |
+---------------------------+------------------------------------------------------------------+
| Pantallas y rutas         | Router del front (react-router, Angular routes, `pages/`/`app/`  |
|                           | de Next), controladores                                          |
+---------------------------+------------------------------------------------------------------+
| Contratos de API          | `openapi.(json|yaml)`, `swagger.*`, colecciones de Postman,      |
|                           | controladores y DTOs                                             |
+---------------------------+------------------------------------------------------------------+
| Cálculos y reglas         | Servicios de dominio (precios, impuestos, descuentos, fechas),   |
|                           | feature flags y configuración por ambiente (sin secretos)        |
+---------------------------+------------------------------------------------------------------+
| Comportamiento esperado   | Los tests que ya tiene el repo (unitarios, e2e): sus nombres y   |
|                           | asserts dicen qué se espera                                      |
+---------------------------+------------------------------------------------------------------+
```

**Topes para no gastar tokens de más**: en modo *proyecto*, hasta ~40 archivos de código leídos (los más reveladores de cada módulo); en modo *historia*, hasta ~20 (los que tocaron sus PRs). Si el tope no alcanza, decí qué quedó sin leer y sugerí usar `REPO_RUTA_LOCAL`.

**PRs y commits de una historia**: buscá la key (`PROJ-12`, `AB#1234`, el ID del work item, `ENG-142` de Linear, `sc-123` de Shortcut) en el título, la descripción y la rama de los PRs/MRs y en los mensajes de commit. De cada PR: estado, descripción, comentarios de la revisión (suelen tener decisiones), archivos tocados y, de los relevantes, el diff. Ahí están las reglas y los mensajes **nuevos** que trae la historia.

## 2. Links externos

Juntá los links de la historia, la épica, los comentarios, los PRs y el README, y clasificá cada uno:

- **Con conector activo** (Confluence o Wiki de Azure DevOps, Figma, Jira): leelo con el conector.
- **Públicos** (documentación de un tercero, una página sin login): leelo con WebFetch.
- **Privados sin conector** (Google Docs, SharePoint, Notion, Miro, un Drive): no intentes entrar. Anotalo como **No accesible** con qué conector o qué permiso haría falta.

De cada link leído, extraé solo lo que sirve para probar; no copies páginas enteras.

## 3. La aplicación (mapa funcional rápido)

1. **Recorrido automático** desde la raíz del repo (solo GET, sin enviar formularios):
   ```bash
   npm run mapa-funcional -- --url <url> [--max-paginas 30] [--profundidad 2] [--paginas url1,url2] [--sin-sesion]
   ```
   Deja `input/documentacion/proyecto/mapa-funcional.md` (y su `.json`): navegación global, y por página sus secciones, menús, formularios con cada campo (etiqueta, tipo, obligatorio, largos, mínimos y máximos, patrón, opciones), botones, mensajes visibles, tablas y los **locators sugeridos** de cada elemento interactivo (los que usa el `web-mapper` para automatizar). Si ya había un mapa, agrega **Cambios desde el recorrido anterior** (pantallas nuevas o quitadas, campos y reglas que cambiaron, botones).
   - **Con login**: si `SESION` está en el `.env` (la persona guardó la sesión con `npm run login`, iniciando sesión a mano), recorre **logueado** y cubre las pantallas privadas. Si la app pide login y no hay sesión, decilo en la respuesta y pedí `npm run login` (no escribas credenciales). Para varios roles, una corrida por sesión (`SESION=admin`, `--salida input/documentacion/proyecto/roles/admin/`).
   - **De punta a punta** (modo *proyecto*): `--max-paginas 200 --profundidad 4`. Si `sin_recorrer` quedó en verdadero, corré de nuevo con las secciones que faltan en `--paginas`.
   - En modo *historia*, pasale solo las páginas de la funcionalidad con `--paginas` y `--salida input/documentacion/historias/<HU o key>/`; después agregale `historia: <key>` al encabezado del `mapa-funcional.md` generado, así el índice lo muestra con su historia.
2. **Lo que el recorrido no alcanza** (menús que se abren con clic, pestañas, modales, pasos de un asistente, pantallas de una SPA sin links): con Playwright MCP (`playwright-headless`, que arranca con la misma sesión) navegá hasta cada una y tomá un `browser_snapshot`; anotá sus campos, botones, mensajes y locators en `proyecto/pantallas-adicionales.md` (o en el dossier, en modo *historia*), y las URLs que encuentres pasalas al recorrido con `--paginas`. **No completes ni envíes formularios** y no hagas acciones con efecto. Para el cómo de Playwright MCP, aplicá el skill `ejecucion-e2e`.

Lo que muestra la aplicación es una **observación de cómo funciona hoy**, no un requisito.

## 4. Qué se guarda y dónde

```
input/documentacion/
├── INDICE.md                       el índice (lo arma scripts/indice_documentacion.py)
├── .estado.json                    qué se documentó: commit por repositorio, fuentes de cada documento,
│                                   fecha de cambio de cada historia (scripts/cambios_documentacion.py)
├── cambios.md                      qué cambió desde la última vez: documentos a rehacer y casos a revisar
├── proyecto/
│   ├── resumen.md                  qué es el producto, módulos, roles, glosario, stack, ambientes
│   ├── repositorio.md              repositorios, rama y commit, estructura, módulo → carpetas
│   ├── reglas-de-negocio.md        validaciones, límites y cálculos por módulo
│   ├── mensajes.md                 textos y mensajes de error, éxito y aviso, por pantalla o módulo
│   ├── estados-y-permisos.md       estados y transiciones, roles y qué puede hacer cada uno
│   ├── mapa-funcional.md (+ .json) npm run mapa-funcional
│   └── links.md                    links externos: leído / no accesible y qué aporta
├── api/
│   ├── api.md                      resumen de los contratos: endpoints, auth, códigos de error
│   └── <repo>-openapi.yaml         copia de los contratos encontrados en el repositorio
├── historias/
│   └── <HU o key>/
│       ├── dossier.md              todo lo de una historia o épica
│       └── mapa-funcional.md       (opcional) sus pantallas
├── proyecto/investigacion/         lo deja el investigador-proyecto (tableros, wiki): resumen, módulos y flujos,
│                                   backlog, decisiones y glosario, dudas y riesgos
└── manual-usuario/<modulo>.md      lo deja el redactor-manual: cómo se usa cada pantalla, verificado en la app
```

`proyecto/investigacion/` y `manual-usuario/` **no los escribe el documentador**: son de otros agentes. Se usan como fuente (el manual dice cómo funciona la app hoy; la investigación, qué dicen los tableros) y, si contradicen al código, se anota en *Contradicciones y dudas*.

Cada `.md` empieza con este encabezado (lo lee el índice):

```
---
titulo: Reglas de negocio
tipo: proyecto            (proyecto | repositorio | api | web | historia | links)
historia: PROJ-12 (HU-001)  (solo en los dossiers: la key y, si existe, el HU-XXX local)
fuentes: github mi-empresa/mi-app@main (a1b2c3d), PROJ-12, Confluence "Reglas de pagos"
actualizado: 2026-10-14
---
```

**Cada dato con su fuente**, para que se pueda verificar: `src/pagos/validaciones.ts:42`, `PR #318 (comentario de <autor>, 2026-09-02)`, `PROJ-12 (comentario de <PO>, 2026-08-30)`, la URL de la página. Separá siempre **lo que dice la historia o una decisión** de **lo que hace el código o la aplicación hoy**.

### El dossier de una historia (`historias/<HU o key>/dossier.md`)

La carpeta lleva la key de la herramienta (`PROJ-12`); solo si la historia existe únicamente en `input/historias/`, el `HU-XXX`. En el encabezado `historia:` van los dos, así el índice permite encontrarlo por cualquiera.

- **La historia**: fuente, estado, prioridad, última actualización (`updated` de Jira o `System.ChangedDate` de Azure DevOps), descripción y criterios de aceptación tal como están.
- **Decisiones en comentarios**: quién, cuándo y qué se decidió.
- **Contexto**: épica, historias hermanas (una línea cada una), subtareas, issues y bugs vinculados.
- **Links**: tabla con el link, de qué es, si se leyó (Leído / No accesible / Sin conector) y qué aporta.
- **Implementación en el repositorio**: PRs/MRs y commits (estado, rama, fecha), archivos tocados por módulo y, de ahí, las reglas, validaciones, mensajes, estados y permisos nuevos o cambiados, con `archivo:línea`.
- **Pantallas**: las páginas de la funcionalidad y sus campos (del mapa funcional o del snapshot).
- **API**: endpoints que toca, con método, request, respuestas y errores.
- **Contradicciones y dudas**: fuente contra fuente (la historia dice 50, el código valida 100; un comentario cambia un criterio y el PR no lo refleja). No elijas: describilas. El skill `investigacion-contexto` las convierte en `FI-XX` en la ficha de la historia.
- **Pistas para probar**: los campos, límites, estados, roles y mensajes que los casos tienen que cubrir. Son pistas, no casos.

## 5. Modo barrido (todas las historias de un alcance)

1. **Listá el alcance completo**, paginando hasta el final (no te quedes con la primera página): en Jira, el JQL del alcance (`project = PROJ AND issuetype in (Story, Bug, Task) ORDER BY updated DESC`, o la épica, el sprint, la release o el filtro del tablero); en Azure DevOps, la query WIQL equivalente (`System.ChangedDate`); en las demás herramientas, la tabla de equivalencias de `investigacion-contexto`. De cada ítem, en la **misma consulta** (pedí solo esos campos): `key`, título, tipo, estado, épica, fecha de cambio (`updated` / `System.ChangedDate`) y el **contenido que define el requerimiento**: descripción, criterios de aceptación, cantidad de comentarios y fecha del último, subtareas y vínculos (solo sus keys). Escribilo en `input/documentacion/_alcance.json`: `{"historias": [{"key", "titulo", "actualizado", "contenido": {"titulo", "descripcion", "criterios", "comentarios", "ultimo_comentario", "subtareas", "vinculos"}}]}`. Con el contenido, el script calcula una **huella**: si la historia solo se movió de columna, se reasignó o se etiquetó, la huella no cambia y **no se vuelve a documentar** (ahorra tokens).
2. **Qué falta o cambió** (determinístico):
   ```bash
   python scripts/cambios_documentacion.py historias --actual input/documentacion/_alcance.json
   ```
   Devuelve las **nuevas** (sin dossier), las **cambiadas** (cambió el contenido de la historia o sus PRs después del dossier), las que **solo cambiaron de estado o metadatos** (no se tocan) y las **sin cambios**, y deja `cambios-historias.md`. Solo se leen en detalle las nuevas y las cambiadas: lo ya documentado no se vuelve a recorrer.
3. **Documentá las nuevas y las cambiadas en modo historia**, por lotes de hasta 10 (historia + comentarios + subtareas + tareas + vínculos + épica + PRs + links), registrando cada una apenas la terminás (si el trabajo se corta, se retoma desde ahí): `python scripts/cambios_documentacion.py historia --key <key> --hu <HU> --huella-desde input/documentacion/_alcance.json [--cambio-prs <fecha>] [--modulos …] [--archivos …]`. Si el alcance es grande, **frená en un lote**, regenerá el índice y devolvé el progreso (cuántas quedan) para que la conversación principal te continúe: así no se pierde trabajo si se corta.
4. **Consolidá lo transversal**: las reglas, roles, estados y mensajes que se repiten en varias historias van también a los documentos de `proyecto/` (`reglas-de-negocio.md`, `estados-y-permisos.md`, `mensajes.md`), por módulo, con la historia de la que salen.
5. Al terminar todo el alcance: `python scripts/cambios_documentacion.py historias --actual input/documentacion/_alcance.json --registrar-revision` (la próxima actualización parte de esta fecha) y borrá `_alcance.json`.

## 6. Documentación incremental (modo actualizar, o proyecto con base existente)

En un proyecto ágil los requerimientos cambian en el medio del sprint. La actualización mira **tres** fuentes de cambio:

- **Código**: el paso 1 de abajo (`cambios_documentacion.py cambios`).
- **Historias** (requerimientos): listá **solo** las historias del alcance **cambiadas desde la última revisión** (`updated >= <revision_historias de .estado.json>` en Jira; `System.ChangedDate >= …` en Azure DevOps; las creadas desde entonces también salen), con el mismo formato y contenido que en el modo barrido, escribilas en `_alcance.json` y corré `python scripts/cambios_documentacion.py historias --actual input/documentacion/_alcance.json --registrar-revision`. Rehacé los dossiers de las **cambiadas** y documentá las **nuevas**; `cambios-historias.md` lista sus **casos para revisar**.
- **Aplicación**: volvé a correr `npm run mapa-funcional` con la misma URL y sesión: la sección *Cambios desde el recorrido anterior* dice qué pantallas, campos y botones cambiaron. Rehacé lo afectado (dossiers de esas pantallas) y, si hay manuales en `manual-usuario/` de esas pantallas, listalos en la respuesta para que el `redactor-manual` los actualice.

El estado de lo documentado vive en `input/documentacion/.estado.json` y lo maneja `scripts/cambios_documentacion.py` (determinístico; el agente decide qué rehacer).

1. **¿Qué cambió en el código?** Desde el commit documentado de cada repositorio (`.estado.json` → `repositorios`):
   - Con `REPO_RUTA_LOCAL`:
     ```bash
     python scripts/cambios_documentacion.py cambios --repo <nombre> --git <REPO_RUTA_LOCAL> --marcar
     ```
     (corre `git diff --name-only <commit>..HEAD` en el clon).
   - Con el conector: pedí la comparación de commits del proveedor entre el commit documentado y la punta de la rama (GitHub y GitLab comparan dos commits; en Azure Repos, `repo_search_commits` desde la fecha documentada y los archivos de cada commit; en Bitbucket, los commits de la rama), guardá la lista de archivos en `input/documentacion/_archivos-cambiados.txt` (uno por línea) y corré:
     ```bash
     python scripts/cambios_documentacion.py cambios --repo <nombre> --archivos-desde input/documentacion/_archivos-cambiados.txt --hasta <commit nuevo> --marcar
     ```
   El script escribe `cambios.md` (documentos a rehacer, historias afectadas, **casos existentes para revisar** y archivos que no alimentan ningún documento) y marca esos documentos como *Desactualizado* en el índice. Si no cambió nada, decilo y terminá.
2. **¿Qué cambió en las historias?** Para cada historia de `.estado.json` → `historias`, compará su fecha de cambio actual y la de sus PRs con las guardadas; las que cambiaron se rehacen en modo historia.
3. **Rehacé solo lo afectado**: los documentos de `cambios.md` (leé los archivos cambiados, no todo el repo) y los dossiers de las historias que cambiaron. Los archivos de *Archivos que no alimentan ningún documento* pueden ser código nuevo: revisalos y sumalos al documento que corresponda.
4. **Casos para revisar**: no los cambia el documentador. En la respuesta, listá los casos de `cambios.md` y sugerí pasarlos al `revisor-casos` (o regenerarlos con el generador que corresponda).

**Registrá siempre lo que documentaste** (en la primera corrida y en cada actualización), para que la próxima sea incremental:

```bash
python scripts/cambios_documentacion.py repo --proveedor <github|gitlab|azure-repos|bitbucket> --nombre <repo> --rama <rama> --commit <commit documentado>
python scripts/cambios_documentacion.py registrar --documento proyecto/reglas-de-negocio.md --repo <repo> --fuentes "src/pagos/,src/**/validaciones*.ts" --historias PROJ-12 --modulos pagos
python scripts/cambios_documentacion.py historia --key PROJ-12 --hu HU-001 --cambio-historia <updated> --cambio-prs <fecha del último PR> --modulos pagos --archivos "src/pagos/"
```

Las **fuentes** de cada documento son las carpetas, archivos o patrones del repositorio que leíste para escribirlo (rutas desde la raíz del repo): sé específico, porque de eso depende saber qué rehacer. Registrar un documento le saca la marca de *Desactualizado*. Borrá `_archivos-cambiados.txt` al terminar.

## 7. Cómo habilitar una fuente no disponible

- GitHub o GitLab: completar el bloque *Repositorio de la aplicación* del `.env` y `npm run conector -- activar github` (o `gitlab`), y reiniciar Claude Code.
- Azure Repos: `azure-devops` activo con el dominio `repositories` (viene por defecto) y el PAT con *Code (Read)*.
- Bitbucket Cloud: el conector `atlassian` con `ATLASSIAN_MCP_AUTENTICACION=token` y un API token con permisos de Bitbucket.

Detalle en `CONECTORES.md`.

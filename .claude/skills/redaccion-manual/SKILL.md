---
name: redaccion-manual
description: Cómo crear o actualizar manuales de usuario basados en evidencia, para cualquier tipo de proyecto — de una funcionalidad o de toda la plataforma por módulos — cruzando lo que k0lmenIA ya sabe del proyecto (input/documentacion con dossiers de historias, investigación, mapa funcional, reglas y mensajes; casos de prueba, .feature de k0lmena y la herramienta de gestión configurada), el manual anterior y la aplicación real recorrida con Playwright MCP para verificar flujos y sacar capturas. Matriz de evidencia por fuente (CONFIRMED/REVIEW/BLOCKED), gaps antes de abrir la app, acciones prohibidas en la aplicación, datos de prueba solo con autorización, puntos QA REVIEW (REVIEW-NNN) en el borrador y en qa-review.md, aprobación explícita y checklist antes de la versión final, Markdown + HTML y Word con el diseño de k0lmena, y el conocimiento que queda en input/documentacion/manual-usuario/ para que los demás agentes escriban casos con contexto real. Lo usa el redactor-manual.
---

# Manual de usuario basado en evidencia

Objetivo: documentación **confiable**, para cualquier producto (web, backoffice, e-commerce, ERP, app interna). Todo lo que dice el manual está respaldado por al menos una fuente; lo que no se puede confirmar se marca para revisión humana, nunca se inventa. Y lo que se aprende de la aplicación **no se pierde**: queda en `input/documentacion/manual-usuario/` para que los demás agentes (casos, BDD, automatización) trabajen con contexto real.

Herramienta: `npm run manual -- <comando>` (`herramientas/manual/manual.py`). Carpeta de cada manual: `output/manuales/<slug>/` con `capturas/`, `borradores/`, `revision/` y `versiones/`. Historial de la skill en `CHANGELOG.md` de esta carpeta.

## 0. Quién pregunta y quién trabaja

El `redactor-manual` corre como subagente y **no puede preguntar a mitad del trabajo**. Por eso:

- **La conversación principal** resuelve antes: el alcance (módulo, funcionalidad o flujo, o *toda la plataforma*), el modo (`crear` / `actualizar`), la **URL del ambiente** (nunca producción salvo que la persona lo diga explícitamente), el idioma del manual si no es español, y el **login**: la persona corre `npm run login` (inicia sesión **a mano** en el navegador que se abre) y pone `SESION=si` en el `.env`; así Playwright MCP arranca logueado y nadie escribe credenciales.
- **El agente** trabaja y, si le falta algo o encuentra dudas, termina devolviendo **"Necesito que confirmes"** con las preguntas `REVIEW-NNN` (opciones concretas, recomendación primero).
- Las **respuestas a los REVIEW** y la **aprobación** ("aprobado", "está OK", "generá la versión final") se las pasa la conversación principal al mismo agente. Un "seguí" o "continuá" **no** es aprobación.

## 1. Reglas no negociables

- **Fuentes de solo lectura**: repositorios, herramientas de gestión, tableros y wikis. Nunca crear, editar ni ejecutar nada en ellas.
- **No publicar** en la wiki, el gestor documental ni ningún servicio por iniciativa propia: solo con pedido explícito, y siguiendo el formato de las páginas existentes del proyecto.
- **No guardar credenciales** en ningún archivo (manual, evidencia, capturas con contraseñas a la vista). El login lo hace la persona (`npm run login`).
- **Nunca la versión final** sin aprobación explícita **y** sin el checklist en verde (`npm run manual -- verificar`).
- Al actualizar, **no regenerar todo**: primero detectar qué secciones cambian.
- **No pisar** borradores ni versiones: cada cambio sustancial es una versión nueva (`v0.2`, `v0.3`…; `npm run manual -- estado` dice cuál sigue).

## 2. Proceso

### 2.1 Alcance

Módulo, funcionalidad, flujo(s), versión de la app si existe, modo (`crear` / `actualizar`) y **slug** (kebab-case sin tildes, p. ej. `clientes-alta`). Preparar la carpeta: `npm run manual -- preparar --slug <slug>`. No investigar fuera del alcance salvo para entender el flujo.

**Toda la plataforma**: primero el plan por módulos (ver §9) y después un manual por módulo, de a uno.

### 2.2 Lo que k0lmenIA ya sabe (antes de abrir la app)

En este orden, citando siempre la fuente original:

1. `input/documentacion/INDICE.md` y lo que corresponda al alcance: `proyecto/mapa-funcional.md` (pantallas, menús, formularios y campos), `proyecto/reglas-de-negocio.md`, `proyecto/mensajes.md`, `proyecto/estados-y-permisos.md`, `proyecto/investigacion/` (módulos, flujos, glosario, dudas), los **dossiers** de las historias del módulo (`historias/<key>/dossier.md`, con comentarios y decisiones) y `manual-usuario/` (manuales previos).
2. **Historias y criterios** del módulo (skill `investigacion-contexto` si no hay dossier vigente).
3. **Casos de prueba**: `output/casos-de-prueba/` (manuales y BDD), los `.feature` de `herramientas/k0lmena/` y la **herramienta de gestión** del proyecto, si hay una configurada (solo lectura). Un caso **indica** un flujo; no es prueba definitiva (puede estar desactualizado o usar datos artificiales). Si contradice otra fuente → `REVIEW`. Si te pasan un export `.xlsx` o `.csv` de casos, leelo sin modificarlo (`openpyxl` en modo `read_only`).
4. **El código** (si hay `REPO_RUTA_LOCAL` o el conector del repo): solo labels, textos de pantalla, validaciones y mensajes. Ignorar selectores, waits y detalles técnicos sin valor para el usuario final.
5. **Manual anterior** y material funcional que aporte la persona (notas, capacitaciones, presentaciones): el que indique o el que haya en `input/documentacion/` (`.md`/`.txt` directo; `.pdf` con Read; `.docx` con `python-docx`). Extraer estructura, pasos, términos, capturas, advertencias y prerrequisitos. En `actualizar`, cada sección queda `SIN CAMBIOS` · `ACTUALIZAR` · `NUEVA` · `ELIMINAR (a confirmar)`.

### 2.3 Matriz de evidencia → `revision/evidencia.md`

```markdown
# Matriz de evidencia — <Funcionalidad> (<slug>)

Fecha: <AAAA-MM-DD> · Modo: crear|actualizar · Versión app: <si aplica> · Skill: redaccion-manual 1.0.0

## Fuentes consultadas
- Documentación: input/documentacion/<archivo>
- Historia: PROJ-12 (comentario de <PO>, <fecha>)
- Casos: output/casos-de-prueba/<archivo> (CP-004, paso 2)
- App: <URL> (fecha de verificación)

## Matriz
| Funcionalidad | Documentación | Historia | Casos | App | Estado |
|---|---|---|---|---|---|
| Consultar cliente | Sí | Sí | Sí | Pendiente | REVIEW |
```

Por fuente: `Sí` · `No` · `Parcial` · `Contradice` · `Pendiente`. Estados (solo estos): `CONFIRMED` (verificado en la app, o dos fuentes independientes coinciden sin contradicción y no hace falta captura) · `REVIEW` (una sola fuente, conflicto o nomenclatura sin confirmar) · `BLOCKED` (sin acceso, sin permisos, ambiente caído) · `NOT_APPLICABLE` (fuera de alcance o eliminado, confirmado). Actualizar la matriz después de navegar.

### 2.4 Gaps (antes de abrir la app)

Sección `## Gaps a verificar en la app` en `evidencia.md`, con ítems accionables: ubicación del menú, campos obligatorios, modal de confirmación, mensaje al guardar, cambio de nomenclatura "X" → "Y", captura del listado para el paso 1. **No abrir la app** para lo que ya está confirmado y no necesita captura.

## 3. Navegación (Playwright MCP)

- Navegá solo los **gaps**: `browser_navigate`, `browser_snapshot` (preferido para entender la pantalla), `browser_click`, `browser_type`, `browser_take_screenshot`. **Nada de crawling** (para el panorama general está `npm run mapa-funcional`).
- Si aparece un login o SSO, **no escribas credenciales**: devolvé "Necesito que confirmes" pidiendo `npm run login` con `SESION=si`.
- Las refs del snapshot **cambian** después de seleccionar opciones, abrir diálogos o navegar: volvé a tomar el snapshot antes del siguiente clic. Si la app carga contenido dentro de **iframes**, usá las refs del snapshot en lugar de buscar por texto o rol. Si un control no responde al clic (checkboxes o selects personalizados), probá con el label asociado.
- Leé el texto **exacto** de los mensajes, diálogos y validaciones desde el snapshot para documentarlo tal cual.

**Prohibido** en la app (si un flujo lo requiere, frená y preguntá): eliminar, anular o dar de baja datos; cambiar permisos, roles o usuarios; modificar configuraciones globales; disparar procesos irreversibles o masivos (cierres, envíos, facturación, cobros, sincronizaciones, importaciones, jobs); confirmar un guardado sobre datos reales.

**Permitido**: navegar, abrir formularios, completar campos **sin guardar**, abrir y **cancelar** modales, leer validaciones (p. ej. intentar guardar un formulario vacío si no persiste nada).

**Datos de prueba (solo con autorización explícita en el pedido)**: crear datos propios, nunca tocar los de otros. Nombres reconocibles (`PRUEBA MANUAL QA …`). Documentos y códigos ficticios pero **válidos** para las reglas que valide la app (dígitos verificadores, formatos de identificación fiscal, CBU/IBAN, etc.; si no conocés la regla, preguntala o pedile datos al `generador-datos-prueba`). Registrar lo creado en `qa-review.md`, sección **Datos de prueba creados**, para que el equipo decida si darlo de baja.

## 4. Capturas

- Nombre `NN-descripcion-clara.png` en orden de aparición (`01-listado-clientes.png`); nunca `screenshot1.png` ni timestamps.
- Playwright MCP las guarda en su carpeta de salida: movelas con `npm run manual -- captura --slug <slug> --origen <ruta que devolvió la tool> --nombre 01-listado-clientes.png` (`--reemplazar` solo si la pantalla cambió; decilo en el resumen).
- Solo lo que aporta: acceso, formulario principal, modal o confirmación, resultado. Nada de loaders ni pantallas repetidas.
- Si una pantalla muestra **datos sensibles** (datos personales reales, importes de clientes, credenciales), no la uses: buscá otro registro o avisalo en `qa-review.md`.

## 5. Borrador → `borradores/<slug>-v0.N.md`

Para el **usuario final**, sin jerga técnica (nada de endpoints, selectores, IDs internos, nombres de tests). Términos exactos de la pantalla, en **negrita** para botones, menús y campos. En el idioma que se haya pedido (español por defecto).

```markdown
# <Nombre de la funcionalidad>

## Objetivo
<Para qué sirve, en 1–3 frases.>

## Requisitos previos
<Solo si aplican: permisos, datos previos, configuración.>

## Acceso
<**Menú** › **Submenú** › **Opción**>

## Procedimiento
1. <Paso>
   ![Listado de clientes](../capturas/01-listado-clientes.png)
2. <Paso>

## Resultado esperado
<Qué ve el usuario al terminar.>

## Consideraciones
<Solo si aplican: reglas de negocio, restricciones, casos especiales.>
```

Las imágenes van relativas (`../capturas/…`): sirven desde `borradores/` y desde `versiones/`. En `actualizar`: partir del manual anterior, conservar lo `SIN CAMBIOS` y empezar con un bloque `> Cambios respecto de la versión anterior:` (se quita en la versión final).

Después de cada borrador: `npm run manual -- html <borrador.md>` (HTML autocontenido con el diseño de los informes de k0lmena y las capturas embebidas). **Word** solo si se pide: `npm run manual -- word <borrador.md>` (diseño de k0lmena, fuentes de la casa embebidas; `MANUAL_EQUIPO` del `.env` firma el documento).

## 6. QA REVIEW

Cada incertidumbre se marca **en el borrador**, en el punto exacto:

```markdown
> ⚠️ QA REVIEW (REVIEW-001)
>
> Motivo: los casos indican que Código es obligatorio, pero la historia no lo menciona.
>
> Evidencia: output/casos-de-prueba/<archivo> (CP-004, paso 2) · input/documentacion/historias/PROJ-12/dossier.md
>
> Confirmación requerida: ¿Debe documentarse Código como obligatorio?
```

Y en `revision/qa-review.md`, que tiene **solo** lo que requiere revisión humana:

```markdown
# QA Review — <slug> v0.1

## REVIEW-001

Funcionalidad:
Alta de cliente

Problema:
Los casos indican que Código es obligatorio, pero la historia no lo menciona.

Evidencia:
- Casos: CP-004, paso 2
- Historia: PROJ-12 (no lo menciona)
- App: no verificado / verificado el <fecha>

Confirmación requerida:
Confirmar si debe documentarse como obligatorio.

Estado:
PENDING
```

Estados: `PENDING` · `RESOLVED` (con `Resolución: …` debajo) · `DISCARDED`. Los `REVIEW-NNN` del borrador y de `qa-review.md` coinciden 1 a 1.

**Resolver**: con las respuestas, quitar el bloque ⚠️ del borrador e incorporar lo confirmado, marcar `RESOLVED` con la resolución y actualizar la matriz. Si el cambio es sustancial, nueva versión del borrador.

## 7. Pistas para probar (para los casos)

En `revision/evidencia.md`, una sección `## Pistas para probar` con lo que **no va en el manual** pero sirve para escribir casos: campos con su tipo, obligatoriedad y largos; validaciones y el **texto exacto** de cada mensaje; roles que ven o no cada opción; estados y transiciones; datos que hicieron falta. Solo lo observado o confirmado, con su fuente.

## 8. Conocimiento para los demás agentes

Después de **cada** borrador y de la versión final: `npm run manual -- a-input --slug <slug> --url <ambiente>`. Escribe `input/documentacion/manual-usuario/<slug>.md` (estado `borrador` o `confirmado`), con el manual sin las marcas internas, los `REVIEW` pendientes como **Sin confirmar** y las **Pistas para probar**; y regenera el índice. Así, cuando alguien pida casos de ese módulo, `investigacion-contexto` lo encuentra: lo confirmado como contexto, lo dudoso como `FI-XX`.

## 9. Toda la plataforma

1. Relevá el **menú** con la sesión iniciada (snapshot de la navegación principal) y escribilo en `output/manuales/plataforma/menu.json`: `[{"modulo": "Ventas", "opciones": [{"nombre": "Clientes", "ruta": "/ventas/clientes"}]}]`.
2. `npm run manual -- plataforma --menu output/manuales/plataforma/menu.json` (suma el mapa funcional si existe) → `output/manuales/plataforma/indice.md` con los módulos, su slug y el estado de su manual.
3. Devolvé el plan para que la persona confirme qué módulos entran y en qué orden; después, un manual por módulo con este mismo proceso (cada uno con su carpeta y su `a-input`).

## 10. Checklist y versión final

`npm run manual -- verificar --slug <slug>` tiene que dar `ok: true`: sin `PENDING`, sin bloques QA REVIEW, todas las imágenes existen y ninguna fila de la matriz en `REVIEW`/`BLOCKED` (las `BLOCKED` aceptadas por la persona quedan fuera del texto y pasan a `NOT_APPLICABLE`). Si falla, **no** generar la versión final: informar exactamente qué falta.

Con aprobación explícita y checklist en verde → `versiones/<slug>-v1.0.md` (si existe, preguntar si es `v1.1` o `v2.0`): sin QA REVIEW, sin bloque de cambios, sin notas internas, terminología consistente, Markdown limpio para copiar a la wiki del proyecto. Después: `html`, `word` si se pidió, y `a-input` (queda `confirmado`). Informar la ruta y las imágenes a adjuntar si se publica.

## 11. Solo actualizar capturas

Leer el borrador o la versión, listar las imágenes referenciadas, recapturar solo esas pantallas con los mismos nombres (`--reemplazar`) y registrar en `qa-review.md` cualquier diferencia visible que implique cambiar el texto.

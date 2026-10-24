---
name: pruebas-accesibilidad
description: El cómo de auditar accesibilidad (a11y) en las tres plataformas — web (WCAG 2.2, axe-core, teclado, foco, reflow, ARIA, lectores), mobile (TalkBack/VoiceOver, etiquetas, objetivos táctiles, Appium) y desktop (UI Automation, teclado, alto contraste) — qué se automatiza y qué necesita criterio. Lo usa analista-accesibilidad; lo referencian probador-mobile y probador-desktop.
---

# Accesibilidad (a11y): web, mobile y desktop

La accesibilidad es que **cualquier persona** —con lector de pantalla, solo teclado, baja visión, daltonismo o motricidad reducida— pueda usar el producto. La base es **WCAG 2.2** y sus principios **POUR** (Perceptible, Operable, Comprensible, Robusto); mobile y desktop adaptan esos principios a sus APIs de accesibilidad. Lo automático lo corre una herramienta; lo que necesita criterio humano se revisa a mano.

## 1. Lo común a las tres plataformas (POUR)

- **Perceptible**: todo lo visual tiene alternativa (texto alternativo en imágenes, subtítulos en video), suficiente **contraste**, y la información no depende solo del color.
- **Operable**: todo se puede usar **solo con teclado** (o switch/lector), el **foco es visible** y su orden es lógico, sin **trampas de foco**, objetivos táctiles/clic suficientemente grandes.
- **Comprensible**: etiquetas y mensajes de error claros, comportamiento predecible, idioma declarado.
- **Robusto**: cada control expone su **nombre, rol y estado** a la API de accesibilidad (ARIA en web, labels en mobile, UIA en desktop); lo que no tiene nombre accesible **no se puede usar con un lector ni automatizar**.

## 2. Web (WCAG 2.2)

- **Automático** (axe-core, `k0lmenia accesibilidad`): contraste, roles/ARIA mal usados, imágenes sin alt, formularios sin label, idioma, encabezados; **teclado** (foco no visible, trampas) y **reflow** a 320px.
- **Manual** (con Playwright MCP y `ejecucion-e2e`): orden de encabezados y **landmarks**, menús/modales con teclado y foco atrapado a propósito, mensajes de error asociados al campo, contenido dinámico anunciado (`aria-live`), y una pasada con **lector de pantalla** (NVDA/VoiceOver).
- Nivel objetivo por defecto: **AA**.

## 3. Mobile (Android / iOS)

- **Etiquetas accesibles**: Android `contentDescription` / `labelFor`, iOS `accessibilityLabel`. Un botón de solo ícono sin etiqueta es invisible para TalkBack/VoiceOver (y para Appium).
- **Objetivos táctiles**: mínimo ~**48dp** (Android) / **44pt** (iOS).
- **Escalado de fuente dinámico** (Dynamic Type / tamaño de fuente del sistema grande): el texto crece sin cortarse ni tapar controles.
- **Orden y agrupación** del foco del lector; **alternativas a gestos** complejos (lo que se hace deslizando también por otro medio); **subtítulos** en video.
- **Contraste** y no depender del color.
- Herramientas: **TalkBack** (Android) y **VoiceOver** (iOS) para la revisión manual; **Accessibility Scanner** (Android) y **Accessibility Inspector** (Xcode) para lo automático; con **Appium** se leen los accessibility ids/labels (lo que falta para a11y también falta para automatizar). Se complementa con `pruebas-mobile`.

## 4. Desktop (Windows / UI Automation)

- Cada control expone **Name** y **ControlType** por **UI Automation (UIA)**; un control sin nombre accesible no lo lee NVDA/JAWS/Narrator ni se puede automatizar. La herramienta `${CLAUDE_PLUGIN_ROOT}/herramientas/desktop/controles.py` (`k0lmenia desktop`) ya **marca los controles sin nombre accesible**.
- **Navegación completa por teclado** y orden de tabulación lógico, foco visible, mnemónicos (Alt+letra), Esc/Enter en diálogos.
- **Modo de alto contraste** de Windows y **escalado de texto/DPI**: la app sigue usable, sin texto cortado.
- Revisión con un lector (NVDA es gratis). Se complementa con `pruebas-desktop`.

## 5. Mapeo de WCAG a mobile/desktop

Los criterios de WCAG se trasladan: "texto alternativo" → etiqueta accesible; "teclado" → navegación por teclado (desktop) o lector/switch (mobile); "contraste" y "reflow/zoom" → escalado de fuente y alto contraste; "nombre, rol, valor" → UIA/labels. Usá WCAG como checklist también fuera de la web.

## 6. Cómo priorizar

Por **impacto en el uso**: primero lo que **bloquea** (no se puede completar una tarea con lector o solo teclado: un botón sin nombre, una trampa de foco, un control inalcanzable), después lo que **dificulta** (contraste bajo, foco poco visible, objetivo chico) y por último lo menor. Decí a **quién** afecta cada barrera.

## 7. Qué es automático y qué necesita criterio humano

- **Automático**: contraste, nombres/labels faltantes, roles mal, objetivos chicos, idioma. Lo corre la herramienta por plataforma, sin gastar tokens por pantalla.
- **Criterio humano**: si la etiqueta **tiene sentido**, si el orden de lectura es lógico, si un cambio dinámico se anuncia, si el flujo completo se puede hacer con lector. Eso se revisa a mano.

## 8. Preguntas típicas para el equipo

Cuando no está escrito, son `FI-XX`:

- ¿Qué plataformas (web, Android, iOS, desktop) y qué nivel WCAG objetivo (A/AA/AAA)?
- ¿Hay que soportar lector de pantalla, solo teclado, alto contraste y fuente grande?
- ¿Qué flujos son críticos para auditar de punta a punta con lector?
- ¿Hay una guía de accesibilidad propia o un estándar legal a cumplir?

## 9. Referencia del `analista-accesibilidad`

### Qué hace `k0lmenia accesibilidad` (web)

Trabaja en una carpeta fija, `output/accesibilidad/<HU o host>/`: al arrancar, la corrida anterior pasa a `historial/` (últimas 5, con su evidencia). En cada página:

- **axe-core** con las reglas WCAG 2.2 del nivel pedido y las buenas prácticas, con los textos en español.
- **Teclado**: recorre la página con Tab y detecta elementos que reciben foco **sin indicador visible** (2.4.7), **trampas de foco** (2.1.2) y la falta de un enlace para **saltar al contenido** (2.4.1).
- **Reflow**: a 320px de ancho no tiene que haber scroll horizontal (1.4.10).

Deja `auditoria.json`, el informe, `capturas/paginas/` (cada página con los elementos que fallan marcados en rojo), `capturas/elementos/` (cada elemento que falla y el elemento con foco en los problemas de teclado) y `videos/recorrido.webm`. El informe trae el cumplimiento, los indicadores, gráficos (reglas, principios WCAG, severidad, páginas), los criterios incumplidos con su nombre y nivel, cada hallazgo con sus elementos, captura y corrección, la revisión manual, lo que hay que revisar a mano, la navegación con teclado y el orden del foco, las páginas, el video y las capturas.

### Checklist de la revisión manual (Playwright MCP, `browser_snapshot`)

- **Textos alternativos**: que describan la imagen o su función (axe solo verifica que existan); las decorativas, con `alt=""`.
- **Estructura**: un `h1` por página, encabezados en orden lógico, regiones (`main`, `nav`, `header`, `footer`), títulos de página únicos y descriptivos.
- **Links y botones**: que el texto diga a dónde llevan o qué hacen ("Ver más" o "Click acá" repetidos no sirven).
- **Formularios**: etiqueta visible en cada campo, obligatorios indicados con texto (no solo color o `*`), errores que se identifican en texto, se asocian al campo y se anuncian (`aria-live` o foco al error), con sugerencia de corrección (3.3.1, 3.3.2, 3.3.3).
- **Teclado interactivo**: abrir y cerrar menús, desplegables, pestañas y modales con Enter, Espacio y Esc; el foco entra al modal, no se escapa y vuelve al botón al cerrar; el orden del foco sigue el orden visual (2.4.3).
- **Zoom y color**: al 200 % (`browser_resize` a la mitad del ancho) no se pierde contenido; la información no depende solo del color (1.4.1).
- **Movimiento**: carruseles, videos o animaciones que arrancan solos se pueden pausar (2.2.2).

Por cada problema: captura `<carpeta>/capturas/manual/m-XX.png` (en el análisis, `capturas/manual/m-XX.png`), criterio WCAG, pasos, esperado y obtenido.

### `analisis.json` (web)

`veredicto`, `resumen` (para alguien no técnico: a quién afectan las barreras y qué tan grave es), `areas_revisadas`, `notas` (por ID), `descartados`, `severidades`, `manuales` (`M-01`, … con `titulo`, `severidad`, `wcag`, `pagina`, `pasos`, `esperado`, `obtenido`, `correccion` —qué cambiar en el código—, `evidencia`), `falta_informacion` (`id`, `que_falta`, `pregunta`), `recomendaciones` (acción concreta, por qué y prioridad; agrupá lo que se corrige con un solo cambio, por ejemplo un estilo de foco global) y `proximos_pasos`. El formato completo está en el encabezado de `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_accesibilidad.py`.

### Mobile y desktop: informe genérico

`output/accesibilidad/<HU o app>/analisis.json` con el esquema de `${CLAUDE_PLUGIN_ROOT}/scripts/generar_informe_generico.py` (`titulo`, `eyebrow`: "Accesibilidad", `meta`: plataforma/app, `veredicto`, `pruebas`, `tablas` —controles sin nombre, objetivos chicos—, `hallazgos` con severidad, `recomendaciones`, `falta_informacion`):

```bash
k0lmenia py scripts/generar_informe_generico.py output/accesibilidad/<HU o app>/analisis.json output/accesibilidad/<HU o app>/informe-accesibilidad.html
```

Mobile con el conector **appium** (coordinado con el `probador-mobile`); desktop con `k0lmenia desktop -- --titulo "<regex>"` (marca los controles sin nombre accesible), teclado, alto contraste, escalado de texto/DPI y una pasada con NVDA.

### Severidad

La propone el script según el impacto de axe; se ajusta con criterio (explicado en `notas`):

| Severidad | Cuándo                                                                                          |
| --------- | ----------------------------------------------------------------------------------------------- |
| Crítica   | Impide usar una función a un grupo de personas: trampa de foco, botón o campo sin nombre, imagen que da información sin alternativa |
| Alta      | La dificulta mucho: contraste insuficiente, foco no visible, falta de idioma de la página       |
| Media     | La dificulta: reflow a 320px, orden de foco confuso, buenas prácticas con impacto alto          |
| Baja      | Molestias o buenas prácticas: regiones, orden de encabezados, salto al contenido                 |

Las **buenas prácticas** (reglas de axe sin criterio WCAG) bajan un nivel: no hacen fallar la conformidad, pero se recomiendan.

### Antes de entregar

- El `analisis.json` es JSON válido y el informe se regeneró sin error. El script avisa por consola (`[aviso] analisis.json · …`) los IDs que no existen y las severidades fuera de la escala: corregilos y regenerá.
- Cada ID citado (`notas`, `severidades`, `hallazgos`, `descartados`) existe en el JSON de la herramienta, con su formato (`A-07`, no `A-7`), y las severidades son `Crítica`, `Alta`, `Media` o `Baja`.
- Cada hallazgo manual tiene página, pasos, esperado, obtenido, `correccion` y una captura que existe dentro de la carpeta, con ruta relativa.
- Cada descarte tiene un motivo verificable, y lo que ninguna fuente define va en `falta_informacion`, no en el veredicto.
- No quedan credenciales, tokens ni datos personales en el análisis, el informe ni las capturas.

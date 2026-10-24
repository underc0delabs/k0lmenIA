---
name: pruebas-contenido
description: El cómo de revisar contenido y textos en el idioma principal — typos, ortografía (LanguageTool), placeholders sin reemplazar, Lorem ipsum, claves de i18n a la vista, microcopy y consistencia — extrayendo el texto con Playwright. Lo usa el revisor-contenido; las traducciones son de analista-traductor.
---

# Revisión de contenido y typos

Los **errores de texto** (un typo, un `{{nombre}}` sin reemplazar, "el el", una clave de traducción a la vista) dañan la confianza y se cuelan hasta producción. Esto revisa el contenido en el **idioma principal** del producto; las **traducciones** entre idiomas las cubre el `analista-traductor` (son cosas distintas y complementarias). No juzga estilo ni tono subjetivo, solo lo objetivo y las reglas del proyecto.

## 1. Errores objetivos (typos y relleno)

- **Ortografía y gramática**: con **LanguageTool** (si está instalado, `--lt`) para el idioma del contenido; si no, la heurística cubre lo más grosero.
- **Palabras duplicadas** ("el el", "the the"), **espacios antes de puntuación**, **espacios múltiples**.
- **Placeholders sin reemplazar**: `{{variable}}`, `${var}`, `%s`, `%(nombre)s` a la vista en la UI.
- **Lorem ipsum** y texto de relleno ("asdf", "test test", "xxx") olvidado.
- **Claves de i18n a la vista**: `home.header.title` mostrándose en vez del texto (cruza con `analista-traductor`).
- **Marcadores**: TODO/FIXME/PENDIENTE en el contenido.

## 2. Consistencia de microcopy

- **Términos consistentes**: no mezclar "iniciar sesión" / "loguearse" / "entrar" para la misma acción; "carrito" / "cesta"; mantené un **glosario** del proyecto.
- **Mayúsculas y puntuación**: estilo uniforme en títulos y botones (Title Case vs. mayúscula inicial), sin punto final inconsistente en labels.
- **Botones y labels** claros y accionables ("Guardar cambios" mejor que "OK"); sin textos ambiguos.
- **Mensajes de error** entendibles para una persona (qué pasó y qué hacer), no códigos ni jerga técnica.

## 3. Formato y texto faltante

- **Fechas, números y moneda** en el formato del locale; unidades consistentes.
- **Texto cortado, truncado o vacío** (labels sin contenido, "undefined"/"null" a la vista).

## 4. Automatizar

- Extraé el **texto visible** de cada página con Playwright (snapshot de accesibilidad o el contenido renderizado) y pasalo por `k0lmenia contenido` (`${CLAUDE_PLUGIN_ROOT}/herramientas/contenido/contenido.py`): heurística siempre, y LanguageTool con `--lt` si está.
- Revisá el microcopy y la consistencia de términos a mano o contra el **glosario** del proyecto (si existe; si no, es `FI-XX`).
- Lo que es contenido fijo (no generado) conviene revisarlo una vez por release; lo dinámico, con datos de prueba.

## 5. Bugs típicos de contenido

- `{{nombre}}` / `%s` sin reemplazar a la vista.
- Clave de i18n (`checkout.button.pay`) mostrándose en vez del texto.
- Palabra duplicada o typo en un título o CTA.
- Términos inconsistentes para la misma acción entre pantallas.
- Mensaje de error técnico ("Error 500") mostrado al usuario final.
- Lorem ipsum o "test" olvidado en una página real.
- Botón con texto ambiguo ("OK"/"Click acá") o label vacío.

## 6. Preguntas típicas para el PO (contenido)

Cuando no está escrito, son `FI-XX`:

- ¿Cuál es el idioma principal del contenido?
- ¿Hay un **glosario** o guía de estilo/microcopy del proyecto?
- ¿Title Case o mayúscula inicial en títulos y botones?
- ¿Qué términos son los "oficiales" para acciones clave (login, carrito, etc.)?
- ¿Qué contenido es fijo y qué se genera dinámicamente?

---
name: options
description: Muestra el cuadro comparativo de los planes de k0lmenIA (gratis, Pro y Empresa) y todas las opciones de cada uno — agentes, skills, conectores y gestión de pruebas — con lo que hay instalado en esta PC. Úsalo con /k0lmenia:options o cuando pregunten qué trae cada plan.
---

# Opciones de k0lmenIA: los tres planes

La persona quiere ver qué trae cada plan y en qué se diferencian. Mostralo completo y ordenado; no es una venta.

## Paso 1 — Traer el cuadro

Corré `k0lmenia planes --opciones` (en el repo clonado: `k0lmenia planes -- --opciones`). Devuelve markdown con:

1. **Comparación**: precio, cantidad de agentes, skills y conectores, una fila por capacidad con ✅ o — en cada plan, y la
   fila **En esta PC** (instalado, disponible o sin acceso).
2. **Todas las opciones**: por plan, la tabla de agentes y la de skills (con qué hace cada uno), los conectores y la gestión
   de pruebas. Cada plan incluye todo lo del anterior.

Si tarda o no hay red, usá `k0lmenia planes --opciones --sin-red` (el cuadro sale igual, sin la fila de acceso).

## Paso 2 — Mostrarlo

- Primero la **Comparación**, tal cual (es una tabla markdown).
- Después **Todas las opciones**, completas: todos los agentes y skills de todos los planes. No resumas ni recortes la
  lista: la persona pidió verlas todas. Mantené los nombres de agentes y skills como vienen (en `código`).
- Cerrá con una línea: si tiene acceso a un plan que no instaló, `/k0lmenia:setup` lo instala; si no, el link de compra
  que viene al final del cuadro.

## Paso 3 — Preguntas

Si pregunta por un agente o skill puntual, contestá con su descripción y en qué plan está. Si quiere saber cuál le
conviene para su proyecto, seguí con el skill `setup` (analiza su web y recomienda).

## Reglas

- No inventes agentes, precios ni capacidades: todo sale de `k0lmenia planes --opciones`.
- Todo en español.

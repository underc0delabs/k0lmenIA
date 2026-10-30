---
titulo: Reglas de negocio
tipo: proyecto
fuentes: repo-demo (copia local, sin git)
actualizado: 2026-10-24
confiabilidad: borrador
---

# Reglas de negocio

Lo observado en el código: es lo que funciona hoy, no necesariamente un requisito.

| Regla | Valor | Fuente |
|---|---|---|
| Usuario | entre 4 y 20 caracteres (letras, números y guion bajo) | `src/registro/validaciones.ts:12` |
| Nombre | entre 2 y 50 caracteres | `src/registro/validaciones.ts:8` |
| Edad mínima | 18 años (`EDAD_MINIMA`, declarada pero sin validar en el esquema) | `src/registro/validaciones.ts:20` |
| Cupones | un solo cupón por compra (`MAX_CUPONES_POR_COMPRA = 1`) | `src/pagos/cupones.ts:3` |

La configuración de `config/` tiene credenciales: no se copian a la documentación.

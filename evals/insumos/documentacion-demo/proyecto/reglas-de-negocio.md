---
titulo: Reglas de negocio
tipo: proyecto
fuentes: github demo/tienda@main (a1b2c3d), PROJ-40
actualizado: 2026-10-10
---

# Reglas de negocio

## Registro

- **Usuario**: entre 4 y 20 caracteres; solo letras, números y guion bajo. Fuente: `src/registro/validaciones.ts:12` (observado en el código).
- **Nombre**: entre 2 y 50 caracteres; admite acentos, ñ y apóstrofe. Fuente: `src/registro/validaciones.ts:8`.
- **Edad mínima**: la historia HU-901 dice 18 años en la descripción y 16 en el CA4. El código valida 18 (`src/registro/validaciones.ts:20`). Contradicción sin resolver.

## Carrito y cupones

- **Un solo cupón por compra**: `MAX_CUPONES_POR_COMPRA = 1` (`src/pagos/cupones.ts:3`). Decisión confirmada por la PO en PROJ-40 (comentario de Ana Pérez, 2026-08-10).
- **Envío gratis** desde $50.000 (`src/pagos/envio.ts:5`).

## Pagos

- Medios aceptados: tarjeta de crédito, débito y transferencia (`src/pagos/medios.ts:2`).

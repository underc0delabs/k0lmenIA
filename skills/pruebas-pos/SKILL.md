---
name: pruebas-pos
description: El cómo de probar POS y hardware periférico — venta, caja y arqueo, medios de pago y EMV, periféricos (impresora, cajón, lector, balanza), integración fiscal, modo offline y sincronización, roles y conciliación (cierres X/Z), y resiliencia. Lo usa el probador-pos.
---

# Pruebas de punto de venta (POS) y hardware

Un POS mezcla **software + hardware + dinero + fiscal**, muchas veces **offline**. Lo que más duele: que **la caja no cuadre**, que se **cobre mal** o que una venta se **pierda o duplique** por un corte. Se prueba el flujo completo, los periféricos y los modos de falla. Para la parte de conciliación de dinero y pasarelas, se apoya en `probador-billeteras`.

## 1. Flujo de venta

- **Apertura/cierre de caja** con monto inicial y **arqueo** final (lo contado = lo esperado).
- **Escaneo** de productos (código de barras), **cantidades**, **productos por peso** (balanza), ítems sin código (búsqueda/manual).
- **Descuentos y promociones** (por ítem, por total, 2x1), **impuestos**, **redondeo**.
- **Devoluciones y anulaciones** (con autorización), **suspender/retomar** una venta, cancelar antes de cobrar.
- **La cuenta tiene que cerrar**: subtotal − descuentos + impuestos = total, y el total = lo cobrado; el **vuelto** correcto.

## 2. Medios de pago

- **Efectivo** (vuelto, sin cambio), **tarjeta** (EMV chip, contactless, banda/fallback), **QR/billeteras**, **pago mixto** (parte efectivo, parte tarjeta).
- Resultados: **aprobado, rechazado, sin señal, timeout, cancelado** en el pinpad; **propina**, **cuotas**.
- El pinpad y el POS quedan **consistentes**: si el cobro se aprueba pero el POS no lo registra (o al revés), es un bug grave. Idempotencia ante reintentos (ver `probador-billeteras`).

## 3. Periféricos / hardware

- **Impresora de tickets** y **comandera** (cocina): imprime lo correcto, maneja **sin papel**.
- **Cajón de dinero**: abre cuando corresponde (y solo entonces).
- **Lector de código de barras** 1D/2D; **balanza** (peso y tara); **display al cliente**; lector de huella/identificación del cajero.
- Un periférico **desconectado** a mitad de operación: mensaje claro, no crash.

## 4. Fiscal

- **Impresora/controlador fiscal** o **factura electrónica**: el comprobante se emite con los datos correctos (impuestos, CUIT/RUT/NIF, tipo de comprobante), según el país.
- **Anulación fiscal** y notas de crédito; **redondeo** fiscal; cierre fiscal (Z).

## 5. Offline y sincronización

- **Vender sin internet**: la venta se registra local, encola la transacción y **sincroniza** al reconectar; **no se pierde ni se duplica**.
- **Conciliación**: lo vendido offline aparece una sola vez en el backend; stock y caja cuadran tras sincronizar.

## 6. Inventario y multi-sucursal

- La venta **descuenta stock**; devoluciones lo reponen; stock por **sucursal**; transferencias.

## 7. Roles y autorizaciones

- **Cajero vs. supervisor**: anulaciones, descuentos manuales, apertura de cajón y reimpresiones requieren **autorización**; el cajero no hace lo que no debe.

## 8. Conciliación y reportes

- **Cierre de caja** (X/Z): efectivo contado vs. sistema, por medio de pago; diferencias señaladas. Reportes de ventas del turno.

## 9. Resiliencia (modos de falla)

- **Corte de luz / cierre abrupto** a mitad de una venta: al reiniciar, la venta queda consistente (completa o cancelada, nunca a medias con el cobro hecho y la venta perdida).
- Impresora sin papel, red caída, pinpad desconectado: mensajes claros y recuperación.

## 10. Cómo probar

- En **hardware real** (lo ideal para pinpad, impresora, balanza, cajón) o con **simuladores/SDK** del fabricante y del adquirente (modo de prueba de la pasarela, tarjetas de test). Mucho es **manual asistido**; automatizá la lógica del software (precios, descuentos, cierre) y la sincronización offline.

## 11. Bugs típicos de POS

- **La caja no cuadra** al cierre (redondeo, un medio de pago mal sumado).
- Cobro aprobado en el pinpad pero venta no registrada (o duplicada) → descuadre y reclamo.
- Venta offline que se pierde o se duplica al sincronizar.
- Vuelto o impuesto mal calculado; promoción que no se aplica o se aplica dos veces.
- Comprobante fiscal con datos mal o que no se emite.
- Periférico desconectado que crashea el POS en vez de avisar.
- Anulación/descuento sin pedir autorización de supervisor.
- Stock que no se descuenta o se descuenta de la sucursal equivocada.

## 12. Preguntas típicas para el negocio

Cuando no está escrito, son `FI-XX`:

- ¿Qué hardware (pinpad/adquirente, impresora, balanza, cajón) y hay simuladores/SDK?
- ¿Qué medios de pago y qué pasarela (modo de prueba)?
- ¿Funciona offline? ¿Cómo debe sincronizar y conciliar?
- ¿Qué integración fiscal y de qué país (comprobantes, redondeo, anulación)?
- ¿Qué acciones requieren autorización de supervisor?
- ¿Cómo es el arqueo y el cierre (X/Z) esperado?

---
name: pruebas-documentos
description: El cómo de probar documentos generados (PDF, Excel, CSV, Word) — datos correctos, cálculos, placeholders sin reemplazar, formato/locale, layout, encoding, metadata, seguridad y consistencia con la UI — extrayendo con pypdf/openpyxl. Lo usa el probador-documentos.
---

# Pruebas de documentos generados

Muchas apps generan **PDF/Excel/CSV** (facturas, reportes, estados de cuenta) y casi nunca se prueban: terminan con **datos mal, totales que no cierran o `{{variable}}` sin reemplazar** en producción. Acá se valida el documento como artefacto. Se apoya en la herramienta `documentos` y, para obtenerlo, en los agentes web/API.

## 1. Obtener el documento

- Generalo por el flujo real (descargarlo desde la UI con Playwright, o pedirlo por API con el `ejecutor-api`) con **datos de prueba conocidos**, para poder comparar contra lo esperado.
- Guardá el archivo en la carpeta de salida y pasalo por `npm run documentos` para extraer su contenido.

## 2. Datos y cálculos

- Los **datos** del documento coinciden con la fuente (el pedido, la cuenta, lo que muestra la UI): nombres, montos, fechas, ítems.
- Los **cálculos cierran**: subtotales, impuestos, descuentos y **total**; cantidades × precio; saldos. Un centavo de diferencia es un hallazgo.
- **Consistencia UI ↔ documento**: lo que el usuario vio en pantalla es lo que sale en el PDF.

## 3. Placeholders y plantilla

- **Nada de `{{variable}}`, `${var}`, `%s`, Lorem ipsum, TODO** ni texto de ejemplo sin reemplazar (la herramienta los detecta). Es el bug más común de un documento generado.
- Campos opcionales vacíos no dejan "undefined", "null" ni un hueco raro.

## 4. Formato, locale y encoding

- **Fecha, moneda y números** en el formato e idioma correctos (locale); separadores de miles/decimales del país.
- **Acentos, Unicode y emojis** se ven bien (no "Ã©" ni cuadraditos); idioma del contenido correcto.

## 5. Estructura y layout

- **Páginas** correctas, encabezado/pie en cada una, numeración, saltos de página donde corresponde; **tablas que no se cortan** feo entre páginas.
- **Multipágina** (un reporte largo) y **multi-hoja** (Excel con varias pestañas) completos y en orden.

## 6. Metadata, seguridad y accesibilidad

- **Metadata** del PDF (título, autor, fecha) correcta y sin datos internos filtrados.
- **Seguridad**: si debe ir con **contraseña** o **firma digital**, que la tenga; que no incluya datos sensibles de más.
- **Accesibilidad del PDF** (si aplica): tagged PDF, orden de lectura, texto seleccionable (no una imagen escaneada).

## 7. Automatizar

- `npm run documentos` (`herramientas/documentos/documentos.py`) extrae el **texto y la metadata del PDF** (pypdf) y las **hojas/celdas del Excel** (openpyxl), y marca **placeholders sin reemplazar**.
- Compará el texto/los valores extraídos contra lo esperado (de la fuente o de un documento de referencia aprobado); los totales, recalculalos.
- Datos de prueba con valores "memorables" (montos redondos, nombres únicos) para encontrarlos fácil en el documento.

## 8. Bugs típicos de documentos

- `{{variable}}` o Lorem ipsum sin reemplazar en el documento final.
- Total que no coincide con la suma de los ítems, o impuesto mal calculado.
- Fecha/moneda en el formato equivocado; acentos rotos (encoding).
- Tabla que se corta entre páginas o se desborda; falta el logo/encabezado.
- El PDF muestra datos distintos a la UI.
- PDF que debía ir con contraseña/firma y va sin ella; metadata con datos internos.
- Excel con fórmulas rotas o celdas #REF!; CSV con el separador equivocado.

## 9. Preguntas típicas para el PO (documentos)

Cuando no está escrito, son `FI-XX`:

- ¿Qué documentos genera la app y en qué formato (PDF/Excel/CSV)?
- ¿Cuál es la fuente de la verdad de cada dato y cómo se calculan los totales?
- ¿Qué locale/idioma y formato de fecha/moneda?
- ¿Debe ir con contraseña, firma digital o ser un PDF accesible?
- ¿Hay un documento de referencia aprobado para comparar?

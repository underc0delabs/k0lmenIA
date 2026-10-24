# Documentos

Relevamiento de **solo lectura** de documentos generados (PDF, Excel/CSV) para validarlos en QA. Lo usa el agente `probador-documentos`.

- **`documentos.py`** (`npm run documentos`) — extrae texto y metadata de un **PDF** (pypdf), hojas y celdas de un **Excel** (openpyxl) o filas de un **CSV**, y detecta **placeholders sin reemplazar** (variables de plantilla, Lorem ipsum, TODO) — el bug más común de un documento generado.

```bash
npm run documentos -- --archivo output/.../factura.pdf
npm run documentos -- --archivo reporte.xlsx
```

No modifica el documento. La verificación de que los datos/cálculos y el layout son correctos la hace el `probador-documentos` con este insumo y los datos esperados. Requiere `pypdf` (PDF) y `openpyxl` (Excel), import perezoso.

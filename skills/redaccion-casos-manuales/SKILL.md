---
name: redaccion-casos-manuales
description: Referencia del generador-casos-manuales — columnas de la planilla, esquema del JSON para ${CLAUDE_PLUGIN_ROOT}/scripts/generar_casos.py (con Falta información y versión en inglés), reglas de cada campo, qué genera el script y las secciones del informe de cobertura.
---

# Casos de prueba manuales — referencia

Material de consulta del agente `generador-casos-manuales`. El proceso y las reglas están en el agente.

## 1. Salidas (en `output/casos-de-prueba/manuales/`)

1. **La planilla** `casos-HU-XXX.xlsx` y **los casos en Markdown** `casos-HU-XXX.md`: los genera `${CLAUDE_PLUGIN_ROOT}/scripts/generar_casos.py` en un solo paso, desde el mismo JSON. El `.md` tiene una tabla **Resumen** (ID, Título, Resultado esperado, Prioridad, Tiempo y, si hay, Falta info; ordenada por prioridad) y la **tabla de casos**, una fila por caso; no incluye Estado, Evidencia, Fecha de Ejecución ni Comentarios (sí están en el `.xlsx`, la grilla completa con las 14 columnas). Con varias columnas la tabla del `.md` queda ancha y puede pedir scroll horizontal.
2. **El informe de cobertura** `casos-HU-XXX-cobertura.md` (cobertura + ambigüedades + preguntas para el PO), escrito a mano siguiendo `${CLAUDE_PLUGIN_ROOT}/plantillas/plantilla-cobertura.md`.

Referencias de formato en `${CLAUDE_PLUGIN_ROOT}/plantillas/`: `plantilla-casos-prueba.xlsx` / `plantilla-casos-prueba.md` y `plantilla-cobertura.md`.

## 2. Columnas de los casos (en este orden)

`ID #` · `Título` · `Descripción` · `Precondiciones` · `Datos de Prueba` · `Pasos` · `Resultado Esperado` · `Estado` · `Prioridad` · `Tiempo estimado (min)` · `#Etiquetas` · `Evidencia` · `Fecha de Ejecución` · `Comentarios`

## 3. Esquema del JSON (`output/casos-de-prueba/manuales/_casos-HU-XXX.json`)

```json
{
  "proyecto": "NOMBRE DEL PROYECTO",
  "modulo": "HU-001 — Inicio de sesión",
  "casos": [
    {
      "id": "CP-001", "titulo": "...", "descripcion": "... (ej. CA1)",
      "precondiciones": "...", "datos": "Email: ...\nContraseña: ...",
      "pasos": "1. ...\n2. ...", "resultado": "...",
      "estado": "Pendiente", "prioridad": "Alta",
      "etiquetas": "@login @smoke @HU-001 @CA1",
      "evidencia": "", "fecha_ejecucion": "", "comentarios": "",
      "falta_info": ["FI-01"]
    }
  ],
  "falta_informacion": [
    {"id": "FI-01", "que_falta": "Texto del mensaje al bloquearse la cuenta",
     "donde_se_busco": "Historia, comentarios, Figma, Confluence", "impacto": "CA3",
     "pregunta": "¿Cuál es el mensaje exacto?", "estado": "Abierto"}
  ]
}
```

- En `datos` y `pasos`, separá las líneas con `\n`: el script las acomoda dentro de la celda.
- `falta_info` (por caso) y `falta_informacion` (lista) son opcionales: van solo si hay datos que faltan. Copiá los ítems de la ficha de contexto con el mismo ID. El script resalta esos casos, les suma la etiqueta `@falta-info` y arma la hoja **Falta información**.
- `tiempo_min` (opcional, por caso): manda sobre la fórmula de `${CLAUDE_PLUGIN_ROOT}/scripts/estimacion.py` (`${CLAUDE_PLUGIN_ROOT}/plantillas/estimacion-tiempos.md`) cuando sabés que un caso lleva más (por ejemplo, esperar un proceso de 10 minutos).
- Versión en inglés: un bloque `"en"` por caso (`titulo`, `descripcion`, `precondiciones`, `datos`, `pasos`, `resultado`) y uno general (`modulo`, `falta_informacion`). El script escribe `casos-HU-XXX.en.json` y el HTML bilingüe.

## 4. El script

```bash
k0lmenia py scripts/generar_casos.py output/casos-de-prueba/manuales/_casos-HU-XXX.json output/casos-de-prueba/manuales/casos-HU-XXX.xlsx --limpiar
```

Crea `casos-HU-XXX.xlsx` **y** `casos-HU-XXX.md` (misma ruta, extensión `.md`), con el **tiempo estimado de ejecución manual** de cada caso y el total al pie; reordena los casos por prioridad (Crítica → Alta → Media → Baja); con `--limpiar` borra el JSON temporal; y al terminar arma el informe HTML (español e inglés). Usá `python` o `python3` según el sistema; instala `openpyxl`/`tabulate` solo si faltan (si no puede, pide `pip install -r requirements.txt`). Sin Python no se generan ni el `.xlsx` ni el `.md`: avisalo.

## 5. Reglas de campos

- `id`: `CP-001`, `CP-002`, …
- `estado`: siempre **Pendiente** al generar. Valores: N/A · Pendiente · En ejecución · Aprobado · Fallido · Bloqueado.
- `prioridad`: `Crítica` para flujos críticos de seguridad, `Alta` para flujos principales, `Media`/`Baja` para el resto. Valores: Crítica · Alta · Media · Baja.
- `evidencia` y `fecha_ejecucion` vacíos al generar.
- `comentarios`: notas o supuestos del caso (vacío si no hay).
- `etiquetas`: útiles para filtrar (ej.: `@login`, `@smoke`, `@HU-001`, `@CA1`).

## 6. Informe de cobertura (`casos-HU-XXX-cobertura.md`)

Prosa en Markdown (no la tabla de casos), siguiendo `${CLAUDE_PLUGIN_ROOT}/plantillas/plantilla-cobertura.md`:

- **Resumen:** historia, cantidad de casos, criterios cubiertos, tipos de prueba.
- **Cobertura por criterio de aceptación:** tabla que mapea cada criterio (CA1, CA2, …) a los casos que lo cubren y su estado, como **tabla Markdown normal** (columnas: `Criterio` · `Descripción` · `Casos que lo cubren` · `Cobertura`), sin alinear a mano y **sin emojis** en las celdas. Un criterio que depende de un `FI-XX` va como `Parcial (falta información)`.
- **Cobertura por tipo de prueba:** qué casos son positivos, negativos, de borde y de validación, y **qué técnica** derivó cada grupo con sus valores (ej.: "Valores límite, contraseña 8–16: CP-004 (7), CP-005 (8), CP-006 (16), CP-007 (17)").
- **Fuera de alcance / no cubierto:** lo que la historia no pide o queda explícitamente afuera.
- **Falta información:** tabla con los `FI-XX` (ID · Qué falta · Dónde se buscó · Casos afectados · Pregunta para el PO · Estado).
- **Ambigüedades detectadas:** puntos poco claros o incompletos de la historia, incluido cada supuesto que hubo que hacer (los mismos de `Comentarios`).
- **Preguntas para el PO:** preguntas concretas y accionables para resolver esas ambigüedades.

Al terminar: `k0lmenia py scripts/formatear_tablas.py output/casos-de-prueba/manuales/casos-HU-XXX-cobertura.md`.

---
name: pruebas-datos
description: El cómo de probar datos y pipelines (ETL/ELT, warehouse, batch, streaming) — calidad por dimensiones, reconciliación origen↔destino, esquema y drift, transformaciones, idempotencia y reprocesos, PII y linaje. Lo usa el probador-datos; se apoya en verificador-datos.
---

# Pruebas de datos y pipelines (ETL / calidad de datos)

Acá el producto **son los datos**: lo que importa es que lleguen **completos, correctos y a tiempo** del origen al destino, y que el pipeline sea **repetible** sin duplicar ni perder. Es distinto de probar una app: se prueba con **consultas y reconciliación**, no con clics. Se apoya en el `verificador-datos` (consultas de solo lectura a PostgreSQL, MySQL, SQL Server, MongoDB).

## 1. Dimensiones de calidad de datos

- **Completitud**: no faltan filas ni valores obligatorios (nulos donde no deberían).
- **Unicidad**: sin duplicados por la clave de negocio; la PK es única.
- **Validez**: tipos, formatos, enums, rangos (una fecha no futura, un monto ≥ 0, un email con forma de email).
- **Exactitud**: el valor es el correcto (contra el origen o una fuente de verdad).
- **Consistencia**: coherente entre tablas/sistemas (el total de una tabla = suma del detalle).
- **Integridad referencial**: las FKs existen; sin huérfanos.
- **Frescura (timeliness)**: los datos están actualizados a la ventana esperada (el job del día corrió).
- **Distribución**: la cantidad de filas y los valores están en el rango histórico (una caída al 10% o un pico al 500% es una anomalía).

## 2. Reconciliación origen ↔ destino

- **Conteos**: filas en origen vs. destino (con la lógica de filtrado esperada).
- **Sumas de control**: suma de importes, mínimos/máximos, cantidad de distintos por columna clave.
- **Fila a fila por clave**: para una muestra, cada registro del destino coincide con el origen tras las transformaciones.
- Diferencias esperadas (filtros, deduplicación) deben estar **documentadas**; si no, es `FI-XX`.

## 3. Esquema y contrato de datos

- **Validación de esquema**: tipos, nullabilidad, enums, longitudes; una columna que cambia de tipo rompe aguas abajo.
- **Schema drift**: el origen agrega/saca/renombra una columna; el pipeline debe manejarlo (ignorar, fallar claro) y no cargar basura.
- **Contrato de datos**: si existe, el productor cumple el esquema acordado (ver `pruebas-contratos`).

## 4. Transformaciones

- **Reglas de negocio** aplicadas bien (cálculos, mapeos, categorizaciones), con casos de borde.
- **Deduplicación** y **SCD** (Slowly Changing Dimensions): tipo 1 (sobrescribe) vs. tipo 2 (versiona con fechas de vigencia); verificá que la historia se arme bien.
- **Joins**: que no **inflen** filas (fan-out por una relación 1:N mal) ni las **pierdan** (inner join que descarta sin querer).
- **Zona horaria y formatos**: fechas en UTC vs. local, separadores decimales, encoding; una de las causas más comunes de datos mal.

## 5. Idempotencia, incrementales y late data

- **Idempotencia**: re-correr el pipeline (mismo input) **no duplica** ni cambia el resultado. Probá reprocesar una partición.
- **Incremental vs. full**: una carga incremental no pierde ni duplica respecto de una full; el **watermark** se mueve bien.
- **Late-arriving data**: datos que llegan tarde (de un día anterior) se cargan en la partición correcta, no se pierden.
- **Backfills**: recargar un rango histórico da el mismo resultado y no pisa lo que no debe.

## 6. PII y seguridad

- **PII** enmascarada/anonimizada donde corresponde (en el warehouse de analítica, en ambientes no productivos); sin datos sensibles en claro ni en logs.
- Accesos acotados; no copiar producción a QA sin enmascarar.

## 7. Linaje y orquestación

- **Linaje**: de dónde viene cada campo (para auditar y para impacto de un cambio).
- **Orquestación** (Airflow, dbt, Spark, Dagster): un job que **falla** o **llega tarde** no deja datos a medias; dependencias y reintentos correctos; alertas cuando algo no corre.

## 8. Automatizar

- Consultas de **solo lectura** con el `verificador-datos` (conteos, sumas, duplicados, nulos, huérfanos) en origen y destino.
- **dbt tests** (unique, not_null, relationships, accepted_values) y **Great Expectations / Soda** para expectativas declarativas.
- Reconciliación por **conteos y hashes** de columnas clave; muestreo fila a fila para exactitud.

## 9. Bugs típicos de datos

- Join que infla filas (duplica importes) o inner join que pierde registros.
- Carga incremental que duplica al reprocesar (no idempotente).
- Fechas en zona horaria equivocada; números con el separador decimal mal.
- Nulos en columnas obligatorias; FKs huérfanas.
- Schema drift del origen que carga datos corruptos sin avisar.
- SCD tipo 2 con fechas de vigencia solapadas o huecos.
- Conteos origen≠destino sin una razón documentada.
- PII de producción copiada a QA sin enmascarar.
- Job que falla y deja la tabla a medias (sin transacción/atomicidad).

## 10. Preguntas típicas para el equipo

Cuando no está escrito, son `FI-XX`:

- ¿Cuál es el origen y el destino, y qué transformaciones/filtros se aplican (diferencias esperadas en los conteos)?
- ¿La carga es full o incremental? ¿Cuál es el watermark/clave incremental?
- ¿Cuál es la clave de negocio para detectar duplicados?
- ¿Qué ventana de frescura se espera (cada cuánto corre)?
- ¿Hay SCD? ¿Tipo 1 o 2 por tabla?
- ¿Qué datos son PII y cómo deben enmascararse en QA/analítica?

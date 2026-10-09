---
name: guia-performance
description: Guía paso a paso para planificar una prueba de performance junto con la persona — objetivo y tipo de prueba (smoke, load, stress, soak, spike), herramienta (k6, Artillery + Playwright o JMeter, con una recomendación justificada), ambiente y alcance, usuarios concurrentes, rampa, duración y tiempo de pensamiento (con cálculos sugeridos), umbrales y plan de ejecución — y deja el plan confirmado para el performance-mapper. Úsalo en la conversación principal cuando la persona pida una prueba de performance, carga, estrés, soak o spike, antes de invocar al performance-mapper, y al cierre para armar el informe final.
---

# Guía de performance

La persona no tiene por qué saber de performance: **la guiás**. Le explicás cada decisión en dos o tres líneas, le **sugerís** valores con su porqué y ella confirma o cambia. Nada se aplica sin su confirmación.

**Quién hace qué:** la entrevista la conducís vos en la **conversación principal** (los subagentes no pueden hacerle preguntas a la persona mientras trabajan). Con el plan confirmado, el agente **`performance-mapper`** genera el script, lo valida, corre las pruebas y arma el informe final.

## Cómo preguntar

- **Una etapa por mensaje**, en orden. Usá la herramienta de preguntas con opciones concretas y poné primero la recomendada, marcada "(Recomendado)" y con el motivo. La persona siempre puede escribir otra respuesta.
- **Sugerir no es inventar**: toda sugerencia se presenta como tal ("te sugiero 50 usuarios porque…"), y si la persona la acepta queda registrada en el plan como **supuesto aceptado**. Si un dato hace falta y nadie lo puede definir, queda como `FI-XX` (skill `investigacion-contexto`).
- Si la persona ya dio un dato (en el pedido, la historia o la ficha de contexto), no lo vuelvas a preguntar: confirmalo en el resumen.
- Si la persona dice "decidí vos" o "lo que recomiendes", aplicá tus sugerencias y mostralas todas juntas en el resumen final para que las confirme.

## Etapa 0 — Contexto (sin preguntar)

Antes de la primera pregunta, juntá lo que ya existe:

- Ficha `output/contexto/contexto-<HU>.md` o el skill `investigacion-contexto`: los **requisitos no funcionales** (tiempos de respuesta, usuarios esperados, SLA) suelen estar en la épica, en Confluence o en comentarios.
- Qué se puede medir: colección de Postman, Swagger/OpenAPI, automatización de k0lmena (`herramientas/k0lmena/api` o `web`), un `.jmx` que traiga la persona, o casos de prueba.
- Si hay ejecuciones anteriores en `herramientas/k0lmena/reports/performance/`, sirven de línea base.

## Etapa 1 — Objetivo y tipo de prueba

Preguntá **qué quiere averiguar** y sugerí el tipo de prueba que lo responde:

```
+------------------------------------------+-----------------+------------------------------------------+
| Objetivo de la persona                   | Tipo sugerido   | Qué hace                                 |
+==========================================+=================+==========================================+
| "¿Soporta el uso normal / el pico        | `load`          | Sube hasta la carga objetivo, la         |
| esperado?"                               |                 | sostiene y baja                          |
+------------------------------------------+-----------------+------------------------------------------+
| "¿Hasta dónde aguanta? ¿Dónde se rompe?" | `stress`        | Escalones crecientes (1x, 1,5x, 2x, 3x)  |
|                                          |                 | hasta que se degrada                     |
+------------------------------------------+-----------------+------------------------------------------+
| "¿Se degrada con el tiempo? (memoria,    | `soak`          | Carga moderada durante horas             |
| conexiones)"                             |                 |                                          |
+------------------------------------------+-----------------+------------------------------------------+
| "¿Qué pasa con un pico brusco? (campaña, | `spike`         | Salto de golpe a varias veces la carga y |
| apertura)"                               |                 | vuelta                                   |
+------------------------------------------+-----------------+------------------------------------------+
| "Solo quiero ver que el script funcione" | `smoke`         | 1-2 usuarios, menos de 1 minuto          |
+------------------------------------------+-----------------+------------------------------------------+
```

`smoke` va **siempre primero** (valida el script). Se pueden elegir varios tipos (lo habitual: smoke → load → stress).

## Etapa 2 — Herramienta

Mostrá la comparación y recomendá una según lo que se mide:

```
+----------------------------+---------------------------------------+----------------------------------------+--------------------------------------+
| Herramienta                | Conviene para                         | A favor                                | En contra                            |
+============================+=======================================+========================================+======================================+
| **k6**                     | APIs HTTP                             | Muy liviana: miles de usuarios con una | Solo HTTP/WebSocket/gRPC; no mide la |
|                            |                                       | PC; scripts en TypeScript versionables | experiencia en el navegador          |
+----------------------------+---------------------------------------+----------------------------------------+--------------------------------------+
| **Artillery + Playwright** | Flujos web en el navegador            | Mide lo que ve la persona usuaria      | Cada usuario es un Chromium: 10-20   |
|                            |                                       | (tiempo por paso, Web Vitals)          | simultáneos por PC                   |
+----------------------------+---------------------------------------+----------------------------------------+--------------------------------------+
| **JMeter**                 | APIs HTTP si el equipo ya usa JMeter, | Estándar conocido, muchos protocolos,  | Más pesada (Java); el `.jmx` es XML, |
|                            | hay un `.jmx` para reusar, u otros    | dashboard propio                       | menos legible                        |
|                            | protocolos (JDBC, JMS, SOAP, TCP)     |                                        |                                      |
+----------------------------+---------------------------------------+----------------------------------------+--------------------------------------+
```

Reglas de recomendación: API sin otra condición → **k6**; experiencia en el navegador → **Artillery**; equipo con JMeter, `.jmx` existente u otro protocolo → **JMeter**. Si pide navegador con mucha carga, sugerí combinar: k6 contra los endpoints de esa pantalla + Artillery con pocos usuarios para la experiencia.

Requisitos: k6 → `npm run bootstrap:k6`; JMeter → Java 8+ y `npm run bootstrap:jmeter`; Artillery → `npm install` en `herramientas/k0lmena`.

## Etapa 3 — Ambiente y alcance

- **URL de destino** y confirmación de que **no es producción** (si lo es, autorización explícita de los dueños del sistema; sin esto no se sigue).
- **Qué se mide**: endpoints o pasos del flujo y su **peso** si son varios (ej. 70 % consultas, 30 % altas). Sugerí el mix según el uso real si la persona lo conoce.
- **Datos y efectos**: autenticación (las credenciales van en el `.env` de la raíz, nunca en el chat), si se pueden ejecutar POST/PUT/PATCH/DELETE en ese ambiente, con qué datos y si después hay que limpiarlos.

## Etapa 4 — Carga

Preguntá **usuarios concurrentes**, **rampa**, **duración** y **tiempo de pensamiento**. Si la persona no sabe los usuarios, ayudala a calcularlos:

- **Desde el negocio** (ley de Little): `usuarios concurrentes = transacciones por segundo × (tiempo de respuesta + tiempo de pensamiento)`.
  Ej.: 18.000 logins en la hora pico = 5 por segundo; con 0,5 s de respuesta y 5 s de pensamiento → 5 × 5,5 ≈ **28 usuarios**.
- **Desde analytics**: usuarios activos en la hora pico × fracción que usa esta funcionalidad.
- **Margen**: sugerí probar `load` al pico esperado y `stress` hasta 2-3 veces ese pico.

Valores de referencia para sugerir (siempre como sugerencia):

```
+--------+-------------------------------+-------------------------------------+---------------------------------+
| Tipo   | Usuarios                      | Rampa                               | Duración sostenida              |
+========+===============================+=====================================+=================================+
| smoke  | 1-2                           | —                                   | 30 s a 1 min                    |
+--------+-------------------------------+-------------------------------------+---------------------------------+
| load   | el pico esperado              | 10-20 % de la duración (mín. 1 min) | 10-30 min                       |
+--------+-------------------------------+-------------------------------------+---------------------------------+
| stress | escalones 1x · 1,5x · 2x · 3x | 1-2 min por escalón                 | 5-10 min por escalón            |
+--------+-------------------------------+-------------------------------------+---------------------------------+
| soak   | 70-80 % del pico              | 2-5 min                             | 1-8 h                           |
+--------+-------------------------------+-------------------------------------+---------------------------------+
| spike  | base → 5-10x en menos de 30 s | —                                   | pico 1-3 min y vuelta a la base |
+--------+-------------------------------+-------------------------------------+---------------------------------+
```

- **Tiempo de pensamiento**: 1-5 s entre acciones de una persona real; 0 solo si se quiere medir el máximo de throughput (avisá que no representa usuarios reales).
- **Límites de la máquina**: k6 aguanta miles de usuarios; JMeter, unos cientos por PC (según memoria); Artillery + navegador, 10-20. Si la carga pedida supera eso, avisá que se mediría la PC y no la app, y proponé alternativas (otra herramienta, menos usuarios, generadores distribuidos).

## Etapa 5 — Umbrales (criterio de aceptación)

Primero buscá el requisito (SLA, historia, épica). Si no hay, sugerí valores de referencia **marcados como tales** y registrá que no hay requisito (`FI-XX` con la pregunta para el PO):

```
+-----------------------+--------------------------+
| Qué se mide           | Referencia habitual      |
+=======================+==========================+
| API de consulta       | p95 < 500 ms · p99 < 1 s |
+-----------------------+--------------------------+
| API de alta o proceso | p95 < 1 s · p99 < 2 s    |
+-----------------------+--------------------------+
| Paso de un flujo web  | p95 < 3 s                |
+-----------------------+--------------------------+
| Errores               | < 1 % (0 % en smoke)     |
+-----------------------+--------------------------+
```

Se pueden poner umbrales por endpoint o por paso (ej. el login más exigente que un reporte).

## Etapa 6 — Ejecución

- **Perfiles y orden**: smoke → (load) → (stress / spike) → (soak). Cada corrida con carga se confirma justo antes de lanzarla.
- **Ventana y aviso**: cuándo se puede correr y a quién avisar (equipos de infraestructura o de la app).
- **Monitoreo**: preguntá si hay métricas del servidor (APM, Grafana, CPU, memoria, base de datos). No son obligatorias, pero sin ellas las recomendaciones se basan solo en lo que ve el cliente; si existen, pedí que las miren durante la corrida y compartan lo que vean.

## Etapa 7 — Resumen y confirmación

Escribí el plan en `output/performance/<HU>/plan-performance-<HU>.md` (tablas normalizadas con `python scripts/formatear_tablas.py`) con: objetivo, tipos de prueba, herramienta y por qué, ambiente, alcance y mix, carga por perfil, umbrales, datos y efectos, ventana, monitoreo, **supuestos aceptados** (las sugerencias que la persona aprobó) y `FI-XX` abiertos. Mostrale el resumen y pedí confirmación explícita.

Con el plan confirmado, invocá al **`performance-mapper`** pasándole la ruta del plan. El agente vuelve después del smoke y antes de cada corrida con carga: confirmá con la persona y continuá al agente con lo que diga.

## Al terminar: informe final

Cuando terminan las corridas, el `performance-mapper` arma el **informe de performance** (`scripts/generar_informe_performance.py`): dashboard HTML con el veredicto, el plan acordado, las métricas de cada corrida (tomadas de los resúmenes de `npm run perf`, no transcriptas), gráficos comparativos de latencia, throughput y errores, la evolución en el tiempo, los umbrales, el p95 por endpoint, los errores, los hallazgos, la capacidad observada y las recomendaciones. Presentale a la persona el veredicto, los 3 hallazgos principales, las recomendaciones de prioridad alta y la ruta del informe.

---
name: generador-reporte-cierre
description: Arma el informe de cierre de una ronda de pruebas como dashboard HTML en modo oscuro: resumen ejecutivo, recomendación go/no-go, resultados totales, bugs por severidad, alcance cubierto y pendientes. Úsalo cuando el usuario pida cerrar las pruebas, un informe o reporte de cierre, un resumen ejecutivo de la ronda, o una recomendación de salida (apto / no apto).
---

# Agente: Informe de cierre de pruebas

Armás el **informe de cierre** de una ronda: el resumen ejecutivo que se manda a stakeholders cuando se termina de probar, con una **recomendación de salida** (go / no-go). El entregable es un **dashboard HTML en modo oscuro** con indicadores y gráficos. Se diferencia del agente `generador-reporte-html` (que reporta **una corrida** puntual): este resume **toda la ronda**, suma los bugs y da una conclusión.

## Entradas

- **Resultados de las ejecuciones**: los `output/ejecuciones/_resultados-*.json` de las corridas E2E y de API (se suman los totales: aprobados / fallidos / bloqueados).
- **Bugs**: los reportes de `output/reportes-bug/` (para el conteo por severidad y los críticos/altos abiertos).
- **El plan**, si existe (`output/planes-de-prueba/`): para comparar **alcance ejecutado vs planificado**.
- La persona puede acotar qué incluir (una historia, una release puntual…).

## Proceso

1. Juntá los resultados de las corridas pedidas y sumá los totales (aprobados / fallidos / bloqueados).
2. Revisá los bugs: contá por severidad (Crítica / Alta / Media / Baja) y listá los **críticos o altos abiertos**.
3. Si hay plan, sacá el **alcance planificado** para compararlo con lo ejecutado.
4. Armá el contenido del informe:
   - **Resumen ejecutivo** y **recomendación** (Apto / Apto con observaciones / No apto), con criterio basado en los datos.
   - **Resultados** totales y % de aprobados.
   - **Alcance cubierto** vs planificado.
   - **Bugs** por severidad + los críticos/altos abiertos.
   - **Riesgos y pendientes** (qué quedó sin probar).
   - **Conclusión**.
5. Escribí un JSON con esa estructura (ver el esquema en `scripts/generar_informe_cierre.py`) y generá el HTML:
   ```bash
   python scripts/generar_informe_cierre.py <cierre.json> output/informes-cierre/cierre-<HU>-<fecha>.html
   ```
6. Limpiá el JSON intermedio si no lo necesitás y avisá la ruta del HTML.

## Salida

Un **informe de cierre en HTML** (modo oscuro) en `output/informes-cierre/`, con: el banner de **recomendación** (verde/ámbar/rojo según go / con observaciones / no-go), la **dona** de % aprobados, los KPIs (total, aprobados, fallidos, bloqueados), la **cobertura** (ejecutado vs planificado), el gráfico de **bugs por severidad** y la tabla de críticos abiertos.

## Reglas

- **Solo lo pedido**: cerrá la ronda/alcance que se pide.
- **No inventes** resultados: los números salen de los `_resultados-*.json` y de los bugs reales, no de tu criterio. La recomendación se apoya en esos datos y se explica.
- **Credenciales**: nunca expongas tokens ni credenciales en el informe.
- Es el paso **final**: resume lo que ya se ejecutó y reportó. No ejecuta pruebas.

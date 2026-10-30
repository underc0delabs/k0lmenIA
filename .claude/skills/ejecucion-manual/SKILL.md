---
name: ejecucion-manual
description: "Acompaña al QA mientras ejecuta casos manuales paso a paso: resultados, evidencia, tiempos, bugs e informe."
argument-hint: "[HU-XXX o planilla de casos]"
---

# Ejecución manual acompañada

El QA ejecuta los casos en la aplicación; vos llevás el registro para que no tenga que ir y venir entre la app y la planilla. Mostrás un caso y un paso por vez, preguntás el resultado, guardás la evidencia y el tiempo, y si algo falla redactás el bug en el momento. Lo conducís **vos, en la conversación principal**, porque hay que preguntarle a la persona en cada paso (los subagentes no pueden). Al final, el agente **`asistente-ejecucion-manual`** consolida la sesión y arma el informe.

Todo queda en `output/ejecucion-manual/<HU>/sesion.json` con `scripts/ejecucion_manual.py`: la sesión se puede pausar y retomar (otro día, otra conversación) sin perder nada.

## 1. Antes de arrancar (una sola tanda de preguntas)

- **Qué casos**: el argumento (`/ejecucion-manual HU-012` o una ruta). Buscalos en este orden: `output/casos-de-prueba/manuales/casos-<HU>*.xlsx`, el `.json` de entrada de esa planilla, los `.feature` de la historia, o la herramienta de gestión (pedile al `gestor-pruebas` que los baje). Si hay una sesión en curso para esa historia, ofrecé **retomarla** (recomendado) o empezar de cero.
- **Alcance**: todos, solo los críticos y altos, o una lista (`--solo CP-001,CP-004`).
- **Ambiente, navegador y tester** (para el informe). Si el `.env` tiene `APP_URL`, sugerilo.
- **Evidencia**: si la app está abierta en Playwright MCP, ofrecé sacar la captura vos en cada resultado; si no, que el QA pegue la ruta o la deje en `output/ejecucion-manual/<HU>/capturas/`.

```bash
python scripts/ejecucion_manual.py iniciar --casos <planilla o archivo> --historia HU-XXX --ambiente QA --tester "Nombre" --navegador "Chrome 130"
```

## 2. Caso por caso

Para cada caso (`python scripts/ejecucion_manual.py siguiente --sesion output/ejecucion-manual/<HU>`):

1. Mostrá el **caso**: ID, título, prioridad, precondiciones y tiempo estimado. Corré `empezar --caso CP-XXX` (arranca el reloj).
2. Mostrá **un paso** por vez: acción, datos y resultado esperado, en un bloque corto y claro.
3. Preguntá el resultado con la herramienta de preguntas: **Aprobado** (recomendado si no dice nada), **Fallido**, **Bloqueado**, **N/A**, y una opción para **pausar**.
4. Registralo: `registrar --caso CP-XXX --paso N --resultado …`.
   - **Fallido**: pedí lo que pasó (`--obtenido`), sacá o pedí la captura (`--evidencia`) y ofrecé registrar el bug **ahora** con la plantilla `plantillas/plantilla-reporte-bug.md` (pasos del caso y lo obtenido); el `triador-bugs` busca duplicados antes. La redacción asistida de bugs está disponible en K0lmenIA Pro. El ID del bug va con `--bug BUG-XXX`. Cargarlo en Jira o Azure DevOps solo con confirmación.
   - **Bloqueado**: pedí el motivo (`--motivo`) — ambiente caído, dato que falta, bug previo — y seguí con el próximo caso.
   - **N/A**: anotá por qué en `--comentario`.
5. Cuando el caso se cierra, mostrá en una línea cómo viene la sesión (avance, aprobados, fallidos, tiempo real contra estimado).

Si el QA quiere cortar: `pausar` (las pausas no cuentan en los tiempos). Al volver: `retomar` y `siguiente`.

## 3. Al terminar

1. `python scripts/ejecucion_manual.py estado --sesion …` y mostrá las **inconsistencias** que detecta (un caso Aprobado con un paso Fallido, un Bloqueado sin motivo, un Fallido sin bug ni resultado, casos sin evidencia): que el QA las corrija o las confirme antes de cerrar.
2. Invocá al **`asistente-ejecucion-manual`** con la ruta de la sesión: cierra la sesión, arma los resultados para el informe de ejecución y el informe de la sesión, y te devuelve si hay que publicar.
3. **Publicar** en Xray o k0lmenaTMT: preguntá antes (es una acción con efecto) y pasale la confirmación al agente, que lo hace con el `publicador-resultados`.

## Reglas

- **No inventes resultados**: un caso que el QA no ejecutó queda Pendiente, nunca Aprobado.
- **Sin secretos**: si el QA pega una contraseña o un token en lo obtenido, la herramienta lo redacta; no lo repitas en el chat ni en el bug.
- Una pregunta por paso, corta. Si el QA dice "todo bien hasta el final", registrá los pasos restantes como Aprobados de una vez (confirmándolo).
- Todo en español, cálido y concreto.

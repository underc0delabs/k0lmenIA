# Mutation testing

Lectura de **solo lectura** de un reporte de mutation testing (formato estándar de **Stryker** / mutation-testing-report-schema). La usa el agente `analista-mutacion`.

- **`mutacion.py`** (`npm run mutacion`) — parsea el JSON de Stryker (StrykerJS, Stryker.NET y los que exportan a ese esquema), calcula el **mutation score** global y por archivo, lista los **mutantes sobrevivientes** (los que tus tests no detectaron) y el código **sin cobertura**, y marca los archivos por debajo de un umbral.

```bash
npm run mutacion -- --reporte reports/mutation/mutation.json --umbral 70
```

No corre la mutación: eso lo hace el `analista-mutacion` con la herramienta del proyecto (**Stryker** para JS/TS/C#, **mutmut/cosmic-ray** para Python, **PITest** para JVM, **Infection** para PHP); esta herramienta solo lee el reporte. Sin dependencias (stdlib).

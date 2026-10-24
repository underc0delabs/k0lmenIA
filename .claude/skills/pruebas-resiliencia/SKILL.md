---
name: pruebas-resiliencia
description: Referencia del probador-resiliencia — qué simula y observa npm run resiliencia, cómo revisar sus resultados, la checklist de la exploración manual de fallas, el esquema del analisis.json, el caos server-side con Toxiproxy paso a paso y la checklist antes de entregar.
---

# Resiliencia — referencia

Material de consulta del agente `probador-resiliencia`. El flujo y las reglas están en el agente.

## 1. Qué hace `npm run resiliencia` (caos en el navegador)

```bash
npm run resiliencia -- --url <url> [--paginas url1,url2] [--max-paginas 5] [--profundidad 1] [--escenarios api-500,timeout,lenta,offline,vacia,malformada,estaticos] [--patron-api "/api/"] [--timeout-ms 8000] [--historia HU-001]
```

Escenarios: `api-500`, `api-503`, `api-404`, `timeout`, `lenta`, `offline`, `vacia`, `malformada`, `nulos`, `estaticos` (todos si el pedido no dice cuáles). "La API" son, por defecto, los pedidos `fetch`/`XHR` de la página sin la analítica de terceros; otra convención, con `--patron-api "/api/|/graphql"`.

Para cada página toma la **carga normal** (línea base: texto, elementos, llamadas a la API, errores) y después, en un contexto limpio por escenario, simula la falla, espera `--timeout-ms` y observa: captura, mensajes de error visibles, si quedó en blanco, spinners que siguen girando, mensajes técnicos (`Internal Server Error`, `undefined`, `[object Object]`, trazas), errores de JavaScript nuevos, reintentos (la misma llamada repetida) y si **se recupera** al quitar la falla y recargar. Trabaja en `output/resiliencia/<HU o host>/`: la corrida anterior pasa a `historial/` (últimas 5) y deja `resiliencia.json`, `informe-resiliencia.html` y `capturas/`.

Las respuestas fallidas las arma Playwright: el pedido real ni siquiera llega al servidor (salvo `nulos`, que pide la respuesta real una vez para anularle los campos). No es una prueba de carga.

## 2. Revisión de los resultados

`resiliencia.json` → `hallazgos` y `paginas[].resultados` (no leas todo si no hace falta):

- Mirá las **capturas** (con Read) de los escenarios con hallazgos: una "pantalla en blanco" puede ser un modal de error a pantalla completa (entonces no es blanco), y una "falla silenciosa" puede tener el aviso en un lugar que la heurística no detecta.
- **"No aplica"**: la página no hizo llamadas a la API (o solo telemetría). Si la pantalla sí depende de la API, probá con `--patron-api`.
- Ajustá la severidad según el impacto real (`hallazgos` del análisis con el motivo). Descartá solo con un motivo verificable.

## 3. Checklist de la exploración manual (Playwright MCP)

15–30 minutos sobre los flujos con más riesgo. La falla se simula con las herramientas de red del server, si las tiene (interceptar o bloquear pedidos), o con `browser_evaluate` (por ejemplo, reemplazando `window.fetch` por una función que rechaza):

- **Acciones que llaman a la API** (buscar, filtrar, paginar, agregar al carrito): ¿avisa que falló? ¿se puede reintentar? ¿pierde lo que la persona cargó?
- **Doble envío** (solo con confirmación y en ambiente de prueba): con la API lenta, ¿el botón se deshabilita o se puede apretar dos veces?
- **Volver atrás, recargar, abrir en otra pestaña** en medio de la falla.
- **Sesión vencida**: la API responde 401 a mitad del uso: ¿lleva al login o queda trabada?

Por cada problema, una captura en `<carpeta>/capturas/manual/rm-XX.png` (si Playwright la deja en otro lado —por defecto `output/ejecuciones/evidencia/`—, se mueve con Bash; en el análisis va como `capturas/manual/rm-XX.png`), con pasos, esperado y obtenido.

## 4. `analisis.json`

`veredicto`, `resumen` (para alguien no técnico), `hallazgos` (por `R-XX`: `severidad` y `nota`), `descartados`, `manuales` (`RM-01`, … con `titulo`, `severidad`, `escenario`, `pagina`, `pasos`, `esperado`, `obtenido`, `correccion`, `evidencia`), `falta_informacion` (`id`, `que_falta`, `pregunta`), `recomendaciones` (acción, por qué, prioridad) y `proximos_pasos`. El formato completo está en el encabezado de `scripts/generar_informe_resiliencia.py`.

## 5. Caos server-side (Toxiproxy)

Para ver cómo reacciona el **backend** ante una **dependencia real** lenta o caída (base de datos, API externa, cache, cola), con `herramientas/resiliencia/toxiproxy.py` (`npm run toxiproxy`). **Tiene efecto real**: solo en **QA**, con confirmación, nunca en producción.

1. **Preparación** (del equipo/infra): Toxiproxy corriendo y un **proxy por dependencia** (el servicio apunta al puerto de Toxiproxy, que reenvía a la dependencia real). Si no está configurado, es `FI-XX` o un pedido al equipo. Relevá lo que hay: `npm run toxiproxy -- --accion listar`.
2. **Una falla por vez**, observando el servicio (con el `ejecutor-api` o Playwright sobre un flujo que use esa dependencia):
   - **Latencia**: `npm run toxiproxy -- --accion latencia --proxy db --ms 2000 --jitter 500` → ¿timeouts razonables?, ¿la UI avisa?, ¿reintenta con backoff y no en bucle?
   - **Caída**: `--accion caida --proxy db` → ¿circuit breaker / fallback / mensaje claro, o error técnico y cuelgue?
   - **Lentitud** (ancho de banda): `--accion lento --proxy api --rate 10`.
   - Que no haya **pérdida de datos** ni estados inconsistentes, y que el servicio **se recupere** al restablecer.
3. **Restablecé siempre** al terminar cada escenario y al final:
   ```bash
   npm run toxiproxy -- --accion recuperar --proxy db
   npm run toxiproxy -- --accion reset
   ```
4. Los hallazgos van en el mismo `analisis.json`, como `manuales` (`RM-XX`) con `escenario` = "caos server-side (latencia/caída de <dependencia>)", su esperado/obtenido y la corrección (timeout, retry con backoff, circuit breaker, fallback, degradación elegante).

## 6. Antes de entregar

- El `analisis.json` es JSON válido y el informe se regeneró sin error. El script avisa por consola (`[aviso] analisis.json · …`) los IDs que no existen y las severidades fuera de la escala: corregilos y regenerá.
- Cada ID citado (`notas`, `severidades`, `hallazgos`, `descartados`) existe en el JSON de la herramienta, con su formato (`R-01`, no `R-1`), y las severidades son `Crítica`, `Alta`, `Media` o `Baja`.
- Cada hallazgo manual tiene página, pasos, esperado, obtenido, `correccion` y una captura que existe dentro de la carpeta, con ruta relativa.
- Cada descarte tiene un motivo verificable, y lo que ninguna fuente define va en `falta_informacion`, no en el veredicto.
- No quedan credenciales, tokens ni datos personales en el análisis, el informe ni las capturas.
- Si hubo caos server-side, Toxiproxy quedó con `reset`.

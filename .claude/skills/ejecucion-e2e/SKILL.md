---
name: ejecucion-e2e
description: Cómo ejecutar pruebas end-to-end en el navegador con Playwright MCP de forma robusta — elegir modo headed o headless, ubicar elementos por snapshot de accesibilidad, esperar para evitar flakiness, capturar evidencia y traducir un caso o escenario BDD a acciones de navegador. Úsalo al ejecutar en vivo pruebas web con Playwright MCP (ejecutor-e2e y web-mapper).
---

# Ejecución E2E con Playwright MCP

El "cómo" para ejecutar pruebas en un navegador real con Playwright MCP, de forma confiable y reproducible.

## Modo headed vs headless

Playwright MCP corre el navegador **headed (visible) por defecto**; con `--headless` corre en segundo plano. En este repo hay dos servers en `.mcp.json`:

- **`playwright`** → headed (ves el navegador; ideal para demos y para seguir la corrida).
- **`playwright-headless`** → headless (segundo plano; más rápido, sirve para CI).

Preguntá a la persona cuál quiere y usá las tools del server correspondiente. Todas las acciones (navegar, click, screenshot) funcionan igual en los dos modos.

## Ubicar elementos (sin selectores frágiles)

Playwright MCP expone la página como un **snapshot de accesibilidad**: cada elemento tiene un rol y un nombre accesible (ej. textbox "Email", button "Registrar", combobox "País"). Ubicá los elementos por rol + nombre, no por CSS/XPath frágiles. Eso hace la ejecución más estable ante cambios de UI.

## Esperas (evitar flakiness)

- Antes de actuar, asegurate de que el elemento esté presente y estable.
- Si un elemento no aparece, sacá un **nuevo snapshot** y reintentá con una espera corta antes de declarar fallo. Muchos "fallos" son timing, no bugs.

## Traducir un caso a acciones

- **BDD (`.feature`)**: cada `Given/When/Then` → navegar / completar / click / seleccionar / verificar.
- **Caso manual**: el campo **Pasos** → la secuencia de acciones; **Resultado esperado** → la verificación final.

## Login y credenciales

Si la app bajo prueba pide login, las credenciales **no van en el código ni en el repo**: van en un archivo **`.env`** en la raíz (está en `.gitignore`, no se commitea). Hay una plantilla **`.env.example`** con los nombres de variable; se copia a `.env` y se completan los valores reales:

```bash
cp .env.example .env   # y editás .env con tus datos
```

Variables típicas: `APP_URL`, `APP_USER`, `APP_PASSWORD`. El agente las lee del `.env` (o las recibe en el prompt) y las usa **solo** para loguearse: nunca las escribe en el reporte, el JSON ni las capturas, y nunca las commitea. Usá credenciales de un entorno de **prueba/staging**, no de producción.

**Evitar loguearte en cada corrida (opcional):** Playwright MCP usa por defecto un **perfil persistente**, así que si te logueás una vez en modo headed, la sesión (cookies) suele quedar para las siguientes corridas. Para algo más explícito, podés arrancar el server con `--storage-state <archivo>` apuntando a un estado de sesión guardado (ese archivo también va gitignored).

## Evidencia

- Sacá un screenshot **ante cada fallo** y **uno final**; evitá capturas en cada paso (menos screenshots = más rápido).
- Nombrá cada captura `<fecha-hora>-<id>.png` (ej. `20260618-1432-cp-004.png`, con la misma marca de tiempo de la corrida: así no se pisan entre corridas) y dejala en `output/ejecuciones/evidencia/`. Playwright MCP guarda en su `--output-dir` (en este repo ya apunta ahí); por defecto, sin esa opción, usa `.playwright-mcp/`. Si la captura quedó en otro lado, movela a `evidencia/` con la ruta que devuelve la tool.
- En el reporte, la `evidencia` se referencia **relativa al HTML** (`evidencia/<fecha-hora>-<id>.png`), por eso el reporte y la carpeta `evidencia/` van juntos en `output/ejecuciones/`. (En algunas versiones `--output-dir` puede ignorarse; conviene confirmar que el archivo quedó en `evidencia/`.)

## Reporte

Por cada caso: estado (**Aprobado / Fallido / Bloqueado**) y, ante un fallo, el paso que falló, esperado vs. real, y el link al screenshot.

Al terminar la corrida, el reporte HTML (modo oscuro) se **genera automáticamente** con `scripts/generar_reporte.py`: es el output de la ejecución, no hay que pedirlo. Es **un reporte por corrida** —cubre solo los casos ejecutados— y lleva `<fecha-hora>` en el nombre para no pisar los anteriores.

## Al terminar

- **Cerrá el navegador** con `browser_close` (no dejes la ventana abierta).
- **No dejes basura**: el output son el reporte HTML, el `_resultados-*.json` y las capturas. No guardes snapshots en `.yml`/`.yaml` ni logs `.log` (usá los snapshots en memoria). Si quedó algo suelto en `output/ejecuciones/` o `.playwright-mcp/`, borralo.

## Velocidad y permisos

- El repo trae `.claude/settings.json` que **pre-aprueba los servers** (`enabledMcpjsonServers`) —así Claude Code no pregunta por Playwright **al iniciar el proyecto**— y también sus **tools** (`mcp__playwright__*`), así no pide permiso en cada acción. Si igual aparece un prompt, elegí *Always allow*.
- **Headless** (`playwright-headless`) corre más rápido que headed (no renderiza la ventana).
- **Menos screenshots**: capturá solo ante fallo y al final.
- La versión del server ya está fijada (`scripts/mcp/lanzar.js`), así los arranques son consistentes; la primera vez `npx` lo descarga y después usa la caché.
- **Sé específico** en el pedido (URL, datos, qué validar): menos pasos exploratorios = más rápido.

## Prerrequisitos

- La **app corriendo** (URL accesible).
- Navegadores instalados: `npx playwright install` (en Linux, además `npx playwright install-deps`).

El detalle de las tools de Playwright MCP, tips de robustez y un ejemplo trabajado están en [`references/playwright-mcp.md`](references/playwright-mcp.md).

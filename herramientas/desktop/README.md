# Escritorio (desktop)

Relevamiento de **solo lectura** del árbol de controles de una app de escritorio de Windows con **pywinauto** (UI Automation). Lo usa el agente `probador-desktop` como insumo para ubicar los controles antes de automatizar.

- **`controles.py`** (`npm run desktop`) — se conecta a una app ya abierta por título (regex) o PID, con el backend `uia` (WPF/UWP/WinForms modernos) o `win32` (Win32 clásico), y vuelca el árbol de controles (tipo, nombre, automation id, clase) con un resumen (total, por tipo, cuántos sin nombre accesible). Es el "DOM" de la app.

```bash
npm run desktop -- --titulo "Facturador.*" --salida output/desktop/arbol.json
npm run desktop -- --proceso 1234 --backend win32 --prof 5
```

No hace clics ni cambia nada. Para apps **Electron** automatizá como web (Playwright); esto es para apps **nativas de Windows**. La ejecución de las pruebas la maneja el `probador-desktop` (Appium + WinAppDriver, pywinauto o Playwright para Electron).

**Requisitos**: Windows, `pip install pywinauto`. Para driving con Appium: Appium + Windows Application Driver (WinAppDriver).

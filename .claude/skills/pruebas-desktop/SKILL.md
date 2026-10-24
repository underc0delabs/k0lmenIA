---
name: pruebas-desktop
description: El cómo de probar apps de escritorio de Windows — por tecnología (WinForms, WPF, WinUI, Win32, Electron, Java, Qt) y su herramienta (WinAppDriver, pywinauto, Playwright), el árbol de controles, funcional, instalación, integración con el SO, regresión, rendimiento, seguridad y a11y. Lo usan probador-desktop y los mappers.
---

# Pruebas de aplicaciones de escritorio (Windows)

Una app de escritorio no es una web: vive en el sistema operativo (ventanas, registro, archivos, servicios, permisos) y se automatiza con **UI Automation**, no con un navegador (salvo Electron). Lo primero es saber **con qué tecnología está hecha**, porque define la herramienta.

## 1. Antes de probar

- **Tecnología de la UI**: WinForms, WPF, UWP/WinUI, Win32 clásico, **Electron** (web embebida), **Java** (Swing/SWT) o **Qt**. Cambia el localizador y la herramienta.
- **Versión y build** de la app, **sistema operativo** (Windows 10/11, Server), **arquitectura** (x86/x64/ARM) y **resolución/escalado DPI** (100/125/150/200 %): muchos bugs de layout salen con DPI alto o en pantallas chicas.
- **Instalador** (MSI, EXE, MSIX, ClickOnce, portable) y si requiere **privilegios de administrador (UAC)**.
- **Ambiente de prueba**: una máquina o VM de QA, no la de producción; datos de prueba y una forma de volver al estado inicial (restaurar, reinstalar).

## 2. Herramienta de automatización por tecnología

```
+---------------------------+---------------------------------------------------------------+
| Tecnología                | Cómo se automatiza                                            |
+===========================+===============================================================+
| WinForms / WPF / WinUI    | Appium + WinAppDriver, o pywinauto con backend `uia`          |
| Win32 clásico             | pywinauto backend `win32` (o `uia` si expone UIA)             |
| UWP                       | Appium + WinAppDriver (por el AppId del paquete)              |
| Electron                  | Como web: Playwright/Chromium DevTools (no UI Automation)     |
| Java (Swing/SWT)          | Java Access Bridge (habilitarlo) + UIA, o herramientas Java   |
| Qt                        | UIA si expone accesibilidad; si no, Squish u OCR/imagen       |
+---------------------------+---------------------------------------------------------------+
```

- **Appium + WinAppDriver** (Windows Application Driver) es el camino que va con el Appium que k0lmena ya usa para mobile: driver `windows`, `app` = ruta del ejecutable o AppId. Necesita el **Modo de programador** de Windows y WinAppDriver corriendo.
- **pywinauto** sirve para **relevar** (volcar el árbol de controles de solo lectura, `npm run desktop`) y para manejar la app desde Python.
- **Electron** no se automatiza con UIA: es Chromium; usá Playwright contra su proceso de render.

## 3. Árbol de controles y localizadores

- Los controles se ubican por **AutomationId** (el más estable, si el desarrollador lo puso), **Name** (nombre accesible), **ControlType** (Button, Edit, List…) y **ClassName**.
- **Relevá el árbol** con `herramientas/desktop/controles.py` (`npm run desktop --titulo "<regex>"`): es el "DOM" de la app y muestra qué controles tienen AutomationId y cuáles no tienen nombre accesible (problema para automatizar **y** para accesibilidad).
- Evitá localizar por posición/índice o por coordenadas: se rompen al cambiar el layout o el DPI.

## 4. Pruebas funcionales

- **Ventanas y diálogos**: modales que bloquean la principal, cerrar con la X / Esc / Cancelar, confirmación al salir con cambios sin guardar, ventanas que no quedan fuera de pantalla.
- **Menús y barras**: menú, barra de herramientas, menú contextual (clic derecho), ribbon; ítems habilitados/deshabilitados según el estado.
- **Formularios y validación**: campos obligatorios, formatos (números, fechas, máscaras), límites de longitud, mensajes de error, y que el **foco** vaya al primer campo con error.
- **Teclado**: atajos (Ctrl+S, Ctrl+Z/Y, F1…), **orden de tabulación** lógico, Enter/Esc en diálogos, mnemónicos (Alt+letra).
- **Arrastrar y soltar**, **portapapeles** (copiar/pegar entre la app y otras), y **multi-documento (MDI)** si aplica.
- **Estado y persistencia**: tamaño/posición de la ventana, últimos archivos, preferencias que sobreviven al reinicio.

## 5. Instalación, actualización y smoke

- **Instalación**: instalar limpio, elegir carpeta con espacios/Unicode, con y sin privilegios de admin (UAC), accesos directos y entradas del menú inicio.
- **Primer arranque** (smoke): la app abre sin error, la ventana principal carga y una acción básica funciona.
- **Actualización**: de la versión anterior a la nueva conservando datos y preferencias; **rollback** si falla.
- **Desinstalación**: saca archivos, accesos directos y (lo esperado) claves de registro; qué datos del usuario quedan a propósito.

## 6. Smoke test

Rápido y bloqueante, en la VM de QA:

1. La app abre sin error ni crash y la ventana principal carga.
2. Login (si aplica) con un usuario de prueba.
3. Una acción central del alcance (abrir un documento, crear un registro) funciona.
4. Guardar y reabrir conserva los datos.
5. Cerrar la app no deja el proceso colgado.

## 7. Archivos y datos

- **Abrir/guardar**: cada formato soportado, archivo inexistente, corrupto, de solo lectura, abierto por otro proceso (bloqueo), ruta larga/con Unicode, unidad de red.
- **Permisos del sistema de archivos**: guardar en una carpeta sin permiso da un error claro, no un crash.
- **Autoguardado y recuperación** tras un cierre inesperado.

## 8. Integración con el sistema operativo

- **Registro y configuración**: dónde guarda la config (registro, `%AppData%`, `%ProgramData%`); que no requiera escribir en `Program Files`.
- **Servicios y procesos en segundo plano**, **ícono de bandeja** y **notificaciones**.
- **Multi-monitor y DPI**: mover la ventana entre monitores con distinto escalado sin que se rompa el layout ni los textos se corten.
- **Impresión** y vista previa, si aplica.

## 9. Regresión

- Después de **una nueva versión o un parche**: correr el flujo principal (smoke ampliado), las áreas que toca el cambio y la compatibilidad con los formatos de archivo de versiones anteriores.
- Lo ideal es tenerlo automatizado (Appium/WinAppDriver o pywinauto vía `web-mapper`/mapper y `npm test`) para repetir la regresión sin tokens en cada build.

## 10. Rendimiento

- **Arranque en frío y en caliente**, **uso de memoria y CPU** en reposo y bajo uso, **fugas de memoria** (handles, memoria que crece y no baja tras cerrar documentos).
- **Responsividad de la UI**: que no se congele ("No responde") en operaciones largas; que haya feedback (progreso) y la UI no bloquee el hilo.
- **Archivos grandes** / muchos registros: tiempos de carga y scroll. Medir con el monitor de recursos; para carga, coordinar con `guia-performance`.

## 11. Seguridad

El escaneo y la explotación los hacen el `analista-seguridad` y el `pentester-web` (para la parte de red/servicios); propio del escritorio:

- **Credenciales y secretos**: no guardados en texto plano en archivos, registro ni logs; usar DPAPI/Credential Manager. Tokens que no queden en `%AppData%` legibles.
- **Firma del ejecutable y del instalador** (Authenticode) válida; **actualización segura** (por HTTPS y firmada), no un canal que se pueda suplantar.
- **Privilegios mínimos**: la app no corre como administrador si no lo necesita; no escribe en rutas protegidas.
- **Comunicaciones** con el backend por TLS; certificados validados (no `TrustAll`).
- **Datos sensibles** en memoria y en disco temporal; limpieza al cerrar.

## 12. Accesibilidad

- Los controles tienen **nombre accesible (UIA Name)** y **ControlType** correcto: lo que falta para un lector de pantalla también falta para automatizar (lo marca `controles.py`).
- **Navegación completa por teclado**, foco visible, contraste y que el escalado de texto del SO no corte contenido.

## 13. Automatizar

- **Appium + WinAppDriver**: sesión con `platformName: Windows`, `app` = ruta del .exe o AppId; localizar por AutomationId/Name/ControlType; esperar a que la ventana/el control exista antes de actuar.
- **pywinauto**: backend `uia` (moderno) o `win32` (clásico); `connect(title_re=..., process=...)`, luego `window(...).child_window(auto_id=..., control_type=...)`.
- **Electron**: Playwright contra el proceso de render (es Chromium), no UIA.
- Primero **relevá** el árbol con `controles.py` para elegir localizadores estables; evitá índices y coordenadas.
- Dejá el estado limpio entre escenarios (cerrar diálogos, volver a la pantalla inicial, borrar datos de prueba).

## 14. Bugs típicos de escritorio

- Layout roto o textos cortados con **DPI alto** o en pantallas chicas.
- La app se **congela** ("No responde") en una operación larga sin feedback.
- **Fuga de memoria/handles**: la memoria crece y no baja al cerrar documentos.
- Diálogo modal que no roba el foco o que deja seguir usando la ventana principal.
- Datos o preferencias que se **pierden** al actualizar de versión.
- Error no controlado (crash/stack trace) al abrir un archivo corrupto o sin permiso.
- Controles **sin AutomationId ni nombre accesible**: no se pueden automatizar ni leer con un lector de pantalla.
- La app exige **privilegios de administrador** sin necesidad o escribe en `Program Files`.
- Credenciales guardadas en texto plano en el registro o en `%AppData%`.
- Proceso que **queda colgado** después de cerrar la ventana.

## 15. Preguntas típicas para el PO (escritorio)

Cuando no está escrito, son `FI-XX`:

- ¿Con qué tecnología está hecha la app (WinForms/WPF/UWP/Electron/Java/Qt)?
- ¿Qué versiones de Windows y qué escalados DPI hay que soportar?
- ¿Cómo se instala (MSI/EXE/MSIX/ClickOnce) y requiere admin?
- ¿Dónde guarda la configuración y los datos del usuario?
- ¿Qué formatos de archivo abre/guarda y hay que mantener compatibilidad con versiones viejas?
- ¿Hay backend/servicios con los que se integra y por qué canal?
- ¿La prueba incluye instalación/actualización, rendimiento, seguridad y accesibilidad, o solo funcional?

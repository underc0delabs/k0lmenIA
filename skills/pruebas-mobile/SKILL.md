---
name: pruebas-mobile
description: El cómo de probar apps móviles (Android e iOS) — nativa/híbrida/PWA, instalación y distribución, permisos, interrupciones, conectividad, deep links y push, ciclo de vida, rendimiento, seguridad móvil (MASVS), a11y y compatibilidad, con Appium (MCP). Lo usan probador-mobile y mobile-mapper.
---

# Pruebas de aplicaciones móviles (Android e iOS)

Una app móvil vive en un dispositivo con **ciclo de vida, permisos, interrupciones y conectividad variable** que una web no tiene. Lo primero es saber el **tipo** (nativa, híbrida o web/PWA) y las **plataformas y versiones de OS** a soportar. Se complementa con `tecnicas-de-diseno` y, para automatizar, `automatizacion-k0lmena` (Appium).

## 1. Ambientes y dispositivos

- **Emulador/simulador vs. real**: el emulador sirve para la mayoría; lo **real** es imprescindible para cámara, biometría, push, rendimiento, batería y gestos finos.
- **Matriz de dispositivos**: cubrir por **versión de OS** (una vieja soportada, una actual), **tamaño/densidad** (chico, grande, tablet/foldable) y gama (alta/baja). Pairwise si no se puede todo (`tecnicas-de-diseno`).
- **Granjas** (BrowserStack, Sauce Labs, Firebase Test Lab) para ampliar la matriz sin hardware propio.

## 2. Tipo de app

- **Nativa** (Kotlin/Java, Swift): controles del SO; se automatiza por accessibility id / resource-id.
- **Híbrida** (React Native, Flutter, Ionic/Capacitor, Cordova): mezcla nativo + webview; en la webview se automatiza como web.
- **Web/PWA**: se prueba como web mobile (ver `pruebas-ecommerce`/web), más instalación como PWA, offline y splash.

## 3. Instalación y distribución

- **Android**: APK/**AAB**, firma, `minSdk`/`targetSdk`, instalación por Play Internal Testing o `adb install`; actualización conservando datos; desinstalar.
- **iOS**: IPA, perfiles de aprovisionamiento, **TestFlight**; que no haya *expired provisioning*.
- Primer arranque (onboarding), actualización de una versión a otra (migración de datos), y **downgrade** no soportado sin perder datos avisado.

## 4. Permisos del sistema

- Permisos en **tiempo de ejecución** (cámara, ubicación, notificaciones, archivos, contactos): **otorgar, denegar, "solo esta vez", y revocar desde Ajustes con la app abierta**. La app no debe crashear si se niega: degrada o explica.
- Permisos **excesivos** (pide más de lo que usa) = hallazgo de seguridad/privacidad.

## 5. Interrupciones y ciclo de vida

- **Interrupciones**: llamada entrante, notificación, alarma, **batería baja**, bloqueo de pantalla, split-screen. Al volver, la app retoma el estado sin perder datos del formulario.
- **Ciclo de vida**: mandar a **segundo plano** y volver, **matar** la app y relanzar (restaura sesión/estado esperado), **rotación** (no pierde datos ni recrea mal la pantalla).
- **Gestos y botón atrás** (Android): el back no sale de la app de golpe perdiendo datos; en iOS, el swipe de volver.

## 6. Conectividad

- **Offline**: mensaje claro, cola de acciones y **reintento/sincronización** al volver la red; no se pierde lo cargado.
- **Red lenta/inestable** y **cambio wifi↔datos** a mitad de una operación (p. ej. una compra): timeouts, reintentos idempotentes, sin doble envío.
- **Modo avión** y vuelta.

## 7. Deep links y push

- **Deep links / universal (iOS) / app links (Android)**: abren la pantalla correcta con la app cerrada, en segundo plano y abierta; un link inválido no crashea.
- **Push**: pedir permiso (iOS obligatorio), recibir en **foreground, background y app cerrada**; tocar la notificación lleva al destino correcto (deep link); respeta el opt-out.

## 8. Pantallas, teclado y datos

- **Tamaños/densidades y fuente del sistema grande**: sin textos cortados ni botones tapados; **notch/safe areas** y gestos del borde.
- **Teclado**: tipo correcto (numérico, email), no tapa el campo ni el botón, scroll al foco, "siguiente/listo".
- **Datos**: caché y "borrar datos"/"borrar caché" dejan la app consistente; migración de base al actualizar; nada sensible en logs.

## 9. Smoke test

Rápido y bloqueante, en un dispositivo/emulador de QA:

1. Instala y abre sin crash; onboarding/splash ok.
2. Login (si aplica) con un usuario de prueba.
3. Una acción central del alcance funciona.
4. Segundo plano → volver conserva el estado; rotar no rompe.
5. Sin errores/ANR en el logcat (Android) o la consola (iOS).

## 10. Regresión

- Después de **una nueva build**: smoke ampliado + el flujo principal + lo que toca el cambio, en al menos un Android y un iOS de la matriz. Automatizado con `mobile-mapper` (Appium) y después `k0lmenia test`, sin tokens.
- Revisá **compatibilidad hacia atrás** de los datos locales (una base vieja tras actualizar).

## 11. Rendimiento

- **Arranque** (frío/caliente), **memoria** y **batería**, **jank** (frames caídos, scroll) y **ANR** (Android) / watchdog (iOS); tamaño del APK/IPA.
- Operaciones sobre red con **red lenta** (ver §6). Para carga del backend, `guia-performance` + `performance-mapper`.

## 12. Seguridad móvil

El escaneo/explotación los hacen `analista-seguridad`/`pentester-web` (backend) y la base de OWASP **MASVS**; propio del cliente móvil:

- **Almacenamiento inseguro**: tokens/credenciales/PII en texto plano (SharedPreferences, plist, SQLite sin cifrar, logs); usar Keystore/Keychain.
- **Red**: TLS y, si aplica, **certificate pinning**; no `TrustAll`.
- **Permisos mínimos**, no exportar components/activities de más (Android), deep links sin validar.
- Secretos embebidos en el APK/IPA (claves de API) — hallazgo (se ven decompilando).

## 13. Accesibilidad

- **TalkBack (Android)/VoiceOver (iOS)**: cada control con etiqueta accesible; foco y orden lógicos; lo que no tiene label tampoco se puede automatizar bien.
- **Fuente del sistema grande** y contraste; objetivos táctiles de tamaño suficiente.

## 14. Readiness de tienda

- Metadatos, capturas, ícono, política de privacidad y permisos declarados; que no viole guías de Apple/Google (p. ej. login obligatorio sin "Sign in with Apple" cuando corresponde).

## 15. Automatizar con Appium (mobile-mapper)

- Ubicá por **accessibility id** / resource-id / predicate; evitá XPath frágil y coordenadas.
- Usá el conector **appium** (se activa con `k0lmenia conector`); capabilities por plataforma (Android `uiautomator2`, iOS `xcuitest`).
- Esperá a que el elemento exista; manejá los **diálogos de permisos** del sistema al inicio del escenario (autogrant o aceptarlos explícitamente).
- Dejá el estado limpio entre escenarios (logout, borrar datos si hace falta).
- Para la **webview** de una app híbrida, cambiá de contexto NATIVE_APP ↔ WEBVIEW.

## 16. Bugs típicos de mobile

- Crash al **denegar un permiso** o al revocarlo con la app abierta.
- Se pierde el estado del formulario al **rotar** o al volver de segundo plano.
- Offline sin manejo: pantalla en blanco o datos perdidos; doble envío al reconectar.
- Deep link o push que no abre la pantalla correcta con la app cerrada.
- Texto cortado con **fuente grande** o en pantalla chica; botón tapado por el teclado.
- Token/PII guardado en texto plano o en el logcat.
- ANR/jank en listas largas; arranque lento.
- Migración de datos que rompe al actualizar de versión.
- Permiso pedido que la app no usa.

## 17. Preguntas típicas para el PO (mobile)

Cuando no está escrito, son `FI-XX`:

- ¿Android, iOS o ambos? ¿Qué versiones mínimas de OS y qué dispositivos prioritarios?
- ¿Nativa, híbrida (RN/Flutter/…) o web/PWA?
- ¿Cómo se distribuye para probar (Play Internal, TestFlight, APK directo)?
- ¿Qué permisos usa y para qué? ¿Cuál es el comportamiento esperado si se niegan?
- ¿Hay push y deep links? ¿Qué debe abrir cada uno?
- ¿Qué pasa offline en los flujos clave?
- ¿La prueba incluye rendimiento, seguridad (MASVS) y accesibilidad, o solo funcional?

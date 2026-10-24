---
name: control-onvif
description: El cómo de probar el control ONVIF con onvif-zeep — servicios (device, media, PTZ, eventos), qué consultar (info, perfiles, URIs de stream y snapshot), cómo probar PTZ de forma segura y leer las capacidades de eventos. Lo usa el agente probador-onvif.
---

# Control ONVIF

Guía para probar el **control** de una cámara IP por ONVIF (no el video en sí: eso lo hace el skill `verificacion-streaming` sobre la URI RTSP). Solo cámaras de `ONVIF_HOSTS_AUTORIZADOS`, con credenciales de prueba.

## ONVIF en dos líneas

ONVIF es el estándar que hablan casi todas las cámaras IP. Expone **servicios** SOAP: *device management* (info y capacidades), *media* (perfiles, URIs de stream y snapshot), *PTZ* (mover/zoom) y *events* (movimiento y otras alarmas). Los **perfiles** (Profile S para streaming, Profile T, etc.) agrupan la configuración; cada uno tiene un **token** con el que pedís su stream.

## La librería

`onvif-zeep` (import `from onvif import ONVIFCamera`). La herramienta la instala sola si falta. Conexión:

```python
cam = ONVIFCamera(host, puerto, usuario, password)
dev = cam.create_devicemgmt_service()      # info y capacidades
media = cam.create_media_service()         # perfiles, stream URI, snapshot
ptz = cam.create_ptz_service()             # mover/zoom
ev = cam.create_events_service()           # eventos
```

## Qué probar (y qué significa)

- **GetDeviceInformation**: marca, modelo, firmware, serie. Si falla con credenciales válidas, la cámara no implementa bien ONVIF.
- **GetCapabilities**: qué servicios tiene (PTZ, Events, Media, Imaging). Guía qué más tiene sentido probar.
- **GetProfiles** → por cada perfil, **GetStreamUri** (la URI RTSP) y el token. Sin perfiles no hay streaming por ONVIF: hallazgo Alto.
- **GetSnapshotUri** + descarga: una imagen fija de prueba. Que devuelva una imagen (no un error ni un HTML) confirma el snapshot. La descarga suele pedir auth **digest** (o basic) con las mismas credenciales.
- **Eventos / movimiento**: si hay servicio de eventos, `GetEventProperties` lista los topics (incluida la detección de movimiento). Para ver la detección **en vivo**, el modo `--eventos N` hace una suscripción **pull-point**: `CreatePullPointSubscription`, luego `PullMessages` en una ventana de N segundos, y al final `Unsubscribe`. Mientras corre, hay que **generar movimiento frente a la cámara** (y tener activada su detección). Se busca un `NotificationMessage` cuyo `SimpleItem` de movimiento (`IsMotion`/`State`/`isActive`) venga en `true`; se reportan los topics vistos, los mensajes recibidos y si se detectó movimiento. Si no llega nada, suele ser que la detección no está activada, que la zona/sensibilidad no la disparó, o que la cámara no publica ese topic por ONVIF.
- **PTZ**: `GetPresets` (lista de posiciones guardadas) es de solo lectura. **Mover es una acción con efecto**: solo con confirmación. El patrón seguro es un movimiento mínimo y un frenado inmediato:

```python
ptz.ContinuousMove({"ProfileToken": token, "Velocity": {"PanTilt": {"x": 0.1, "y": 0.0}}})
time.sleep(0.6)
ptz.Stop({"ProfileToken": token, "PanTilt": True, "Zoom": True})
```

Nunca dejes la cámara en movimiento. No cambies presets ni la posición "home".

## Reloj, zona horaria y NTP

- **GetSystemDateAndTime**: da la hora de la cámara (UTC), la zona horaria (`TZ`) y el horario de verano. Compará la hora de la cámara con la hora real para medir la **deriva de reloj**: una deriva grande (aviso sobre 60 s, `ONVIF_DERIVA_RELOJ_AVISO_S`) hace que la hora de las grabaciones y los eventos no sea confiable.
- **GetNTP**: si usa NTP y qué servidores. Sin NTP, el reloj deriva con el tiempo.
- Contra el **estándar del sitio**: `ONVIF_TZ_ESPERADA`, `ONVIF_NTP_ESPERADO` y `ONVIF_FIRMWARE_ESPERADO` permiten flaguear una cámara con zona horaria, NTP o firmware distintos del estándar (o firmware viejo).

## Grabaciones (Recording / Search)

Para verificar que un NVR/cámara graba bien, los servicios **Recording** y **Search** de ONVIF:

- **GetRecordingSummary** (Search): el rango total grabado (`DataFrom`/`DataUntil`) y la cantidad de grabaciones. De ahí salen los **días cubiertos** (para comparar con la retención esperada) y si la última grabación es reciente (si no, puede no estar grabando ahora).
- **GetRecordings** (Recording): cada grabación y sus tracks con su rango, para estimar **huecos**.
- Muchas cámaras no implementan estos servicios por ONVIF: si fallan, se informa que **no está soportado** (no es un fallo de grabación) y se sugiere la API propia del NVR. Esto lo usa el agente `verificador-grabaciones`.

## Seguridad y límites

- **Solo el host autorizado** (`ONVIF_HOSTS_AUTORIZADOS`); no escanees la red ni busques cámaras.
- **Credenciales de prueba** que da la persona; no probar contraseñas por defecto ni fuerza bruta.
- **PTZ y configuración**: mover, solo con confirmación y frenando; **no** cambiar red, usuarios, grabación ni presets.
- **Datos**: no copiar credenciales completas; si aparece alguna expuesta, recomendar rotarla.

## Severidad

- **Crítica**: no conecta por ONVIF (con credenciales válidas).
- **Alta**: falla la info del dispositivo o no expone perfiles/stream.
- **Media**: falla el snapshot o el PTZ declarado.
- **Baja**: un servicio opcional no implementado, o PTZ pedido sin capacidad PTZ.

## Después

Con la URI RTSP de un perfil, el agente `probador-streaming` verifica que ese stream reproduzca bien (códec, resolución, FPS, continuidad, estabilidad).

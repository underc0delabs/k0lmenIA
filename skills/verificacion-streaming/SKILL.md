---
name: verificacion-streaming
description: El cómo de probar streaming y playback con ffprobe/ffmpeg — protocolos (RTSP/ONVIF, RTMP, HLS, DASH, WebRTC, VOD), qué propiedades mirar (códec, resolución, FPS, bitrate, keyframes), cómo leer la continuidad y qué umbrales usar. Lo usa el agente probador-streaming.
---

# Verificación de streaming y playback

Guía para probar que un stream o un video **reproduzca bien**, con ffprobe (metadatos) y ffmpeg (continuidad). No es prueba de carga (eso es el `performance-mapper`) ni seguridad (eso es `analista-seguridad` / `pentester-web`). Solo fuentes de `STREAMING_FUENTES_AUTORIZADAS`.

## Protocolos y cómo se nombran

- **RTSP** (`rtsp://…`): cámaras IP. Usá transporte **TCP** por defecto (más estable que UDP; UDP solo si la persona lo pide). ONVIF es el estándar de control de las cámaras IP: la URL RTSP suele venir de su perfil (Profile S). El control en sí (PTZ, snapshot, eventos) no lo cubre este flujo todavía: queda como `Falta información` o para una extensión.
- **RTMP** (`rtmp://…`): ingesta/salida de transmisión en vivo (OBS, servidores de live).
- **HLS** (`…/index.m3u8`) y **DASH** (`…/manifest.mpd`): streaming adaptativo por HTTP; lo típico de VOD y live en la web. ffprobe lee el manifiesto y la primera representación.
- **WebRTC**: baja latencia en el navegador; si se sirve el stream por HTTP se puede probar la fuente, pero la negociación WebRTC real se valida en el navegador con `ejecutor-e2e`.
- **Archivo / VOD** (`http(s)://…/video.mp4`, o una ruta): playback de un video completo; ahí sí hay `duration`.

## Qué mirar (y qué significa para la persona)

- **Códec de video** (`h264`, `hevc/h265`, `av1`, `vp9`): que sea el esperado y que el reproductor destino lo soporte. HEVC y AV1 no se ven en todos los navegadores.
- **Resolución** (`1920x1080`, …): que coincida con lo contratado/esperado. Menos resolución = imagen más pobre.
- **FPS**: estable y por encima del mínimo (10 por defecto, `STREAMING_FPS_MINIMO`). FPS bajo o variable = video a saltos.
- **Bitrate**: muy bajo = pixelado; muy alto = consumo y buffering. Compará con lo esperado para la resolución.
- **Audio**: presente si corresponde. En cámaras de seguridad suele no haber: eso es esperado (severidad Baja o descartado), no un bug.
- **Keyframes (GOP)**: intervalos muy largos tardan en “enganchar” el stream y en hacer seek. (ffprobe los muestra por frame si se pide; para el MVP se infiere de errores al conectar.)

## Continuidad (la captura de unos segundos)

`ffmpeg` lee `--segundos` a un sink nulo y reporta:

- **frames** leídos, **caídos** (`drop_frames`) y **duplicados** (`dup_frames`): caídos sostenidos (> 5% de los esperados = fps × segundos) = cortes visibles.
- **errores de decodificación**: paquetes corruptos o pérdida de red; cualquiera > 0 merece mirar.
- **latencia de conexión**: cuánto tardó ffprobe en responder (aviso sobre 3 s, `STREAMING_LATENCIA_AVISO_S`).
- **latencia de arranque (TTFF)**: tiempo hasta el **primer frame** decodificado (aviso sobre 4 s, `STREAMING_TTFF_AVISO_S`). Es lo que siente la persona al dar play.

## Estabilidad y reconexión (`--estabilidad N`)

Lee N segundos (soak) con reconexión automática activada (`-reconnect`, aplica a **http/rtmp**; en RTSP no hay reconexión de entrada en ffmpeg) y reporta:

- **interrupciones**: tramos donde el tiempo avanzó pero no entraron frames nuevos (el stream se "congeló").
- **reconexiones**: cuántas veces ffmpeg tuvo que reconectar.

Sirve para live y cámaras que dejás un rato. Una interrupción o reconexión = experiencia cortada: hallazgo Alto/Medio.

**Latencia *glass-to-glass* real** (del hecho físico a la pantalla) necesita un marcador visible frente a la cámara y no se mide sola: queda como `Falta información` o prueba manual. Lo que sí medimos es el TTFF y, en live, el retraso de buffering implícito.

## Carga acotada (`--conexiones N`)

Abre N lecturas en paralelo de la **misma** fuente y reporta cuántas levantan, su FPS promedio y sus errores. Es una prueba de carga **acotada** del servidor de ese stream (por ejemplo, cuántas sesiones RTSP aguanta un NVR). Para la carga de un **sistema completo** (muchos usuarios, rampas, umbrales), el `performance-mapper`.

## Keyframes (GOP)

ffprobe lee ~6 s de frames y mide el **intervalo entre keyframes**. Un intervalo largo (aviso sobre 4 s, `STREAMING_GOP_AVISO_S`) hace que el stream tarde en "enganchar" y que el seek sea tosco.

## Control de la cámara (ONVIF)

PTZ, snapshot, perfiles y eventos/detección de movimiento los prueba el agente `probador-onvif` (skill `control-onvif`), que además devuelve la URI RTSP para verificar el video acá.

## Umbrales (se pisan en el `.env`)

- `STREAMING_FPS_MINIMO` (10 por defecto)
- `STREAMING_LATENCIA_AVISO_S` (3 por defecto)
- `STREAMING_TTFF_AVISO_S` (4 por defecto)
- `STREAMING_GOP_AVISO_S` (4 por defecto)
- Caída de frames de aviso: 5% de los esperados (fijo en el runner).

Los umbrales son un punto de partida: si la persona define otros (por la calidad contratada), esos mandan y se registran como supuesto aceptado.

## Criterio de severidad

- **Crítica**: la fuente no abre o no tiene video.
- **Alta**: FPS por debajo del mínimo, errores de decodificación, frames caídos sostenidos.
- **Media**: resolución no determinable, latencia de conexión alta.
- **Baja**: sin audio cuando podría ser esperado (en cámaras, muchas veces se descarta).

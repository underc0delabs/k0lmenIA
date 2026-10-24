# Streaming (ffprobe/ffmpeg + ONVIF)

Herramientas para QA de video:

- **`probar.py`** — verifica **streaming y playback**: que una fuente levante, sus propiedades (códec, resolución, FPS, bitrate, audio, keyframes/GOP), la latencia de arranque (TTFF), la continuidad (frames caídos, errores), la estabilidad en el tiempo (soak con reconexión) y la carga (N conexiones a la vez). La usa el agente `probador-streaming`.
- **`onvif.py`** — prueba el **control ONVIF** de una cámara IP: información del dispositivo, perfiles y URIs de stream, snapshot, PTZ (opcional) y capacidades de eventos/movimiento. La usa el agente `probador-onvif`.

Cubre cámaras IP (RTSP/ONVIF), transmisiones en vivo (RTMP/HLS/DASH), WebRTC servido por HTTP y VOD/archivo.

## Requisitos

- **ffmpeg** y **ffprobe** en el PATH (para `probar.py`): <https://ffmpeg.org/download.html>
  - Windows: `winget install Gyan.FFmpeg` · Mac: `brew install ffmpeg` · Linux: el paquete `ffmpeg`.
- **onvif-zeep** (para `onvif.py`): se instala sola si falta, o `pip install onvif-zeep`.

## Streaming y playback

```bash
# Básico (propiedades + continuidad):
npm run streaming -- --fuente rtsp://cam.local/stream --historia HU-001 --segundos 10 --confirmar
# Estabilidad (soak de 60 s con reconexión) + carga (10 conexiones a la vez):
npm run streaming -- --fuente https://cdn.mi-app.com/live/index.m3u8 --estabilidad 60 --conexiones 10 --confirmar
```

`--fuente` admite varias separadas por coma. Opciones: `--segundos` (captura de continuidad, 10), `--transporte tcp|udp` (RTSP, tcp por defecto), `--estabilidad N` (soak en segundos), `--conexiones N` (carga acotada), `--confirmar`.

Salida en `output/streaming/<historia o host>/`: `streaming.json`, `informe-streaming.html` (`scripts/generar_informe_streaming.py`) e `historial/` (últimas 5).

## Control ONVIF

```bash
npm run onvif -- --host 192.168.1.50 --puerto 80 --historia HU-001 --confirmar
# Con PTZ (mueve la cámara; exige --confirmar y autorización):
npm run onvif -- --host 192.168.1.50 --ptz --confirmar
```

Credenciales por `--usuario/--password` o `ONVIF_USUARIO`/`ONVIF_PASSWORD` del `.env`. Salida en `output/streaming/onvif-<host o historia>/`: `onvif.json`, `informe-onvif.html`, `snapshot.jpg` e `historial/`.

## Autorización y alcance

- `probar.py`: solo fuentes de `STREAMING_FUENTES_AUTORIZADAS`. `onvif.py`: solo hosts de `ONVIF_HOSTS_AUTORIZADOS`. Solo dispositivos/streams **propios o con autorización por escrito**.
- Son de **solo lectura** (no graban ni retransmiten el video; el snapshot es una imagen de prueba), **salvo el PTZ** de `onvif.py`, que mueve la cámara (mínimo y frenando) y exige `--confirmar`.
- La carga (`--conexiones`) es acotada a una fuente; para carga de un sistema completo, el `performance-mapper`.

Umbrales opcionales (`.env`): `STREAMING_FPS_MINIMO`, `STREAMING_LATENCIA_AVISO_S`, `STREAMING_TTFF_AVISO_S`, `STREAMING_GOP_AVISO_S`.

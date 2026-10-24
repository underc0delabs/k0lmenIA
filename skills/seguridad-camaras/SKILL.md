---
name: seguridad-camaras
description: El cómo del análisis de seguridad pasivo de cámaras IP/NVR — qué puertos revisar, qué servicios son inseguros (Telnet, FTP, HTTP sin TLS, RTSP sin auth), cómo detectar RTSP sin auth con un DESCRIBE inocuo y cómo tratar el firmware y sus CVE. Pasivo y solo CAMARAS_AUTORIZADAS. Lo usa analista-seguridad-camaras.
---

# Seguridad de cámaras (pasivo)

Guía para revisar la exposición de seguridad de cámaras IP y NVR **sin atacar**. Mismo criterio que el escaneo pasivo de ZAP del `analista-seguridad`: solo dispositivos de `CAMARAS_AUTORIZADAS`, nada de fuerza bruta, explotación ni prueba de contraseñas por defecto.

## Qué se revisa

- **Puertos conocidos** (connect TCP, sin payloads): 21 FTP, 22 SSH, 23 Telnet, 80 HTTP, 443 HTTPS, 554 RTSP, 8000/8080/8554/9000, 37777 (Dahua), 34567 (NVR Sofia).
- **Servicios inseguros**:
  - **Telnet (23) o FTP (21) abiertos** → deberían estar deshabilitados (texto plano, credenciales expuestas).
  - **HTTP (80) sin HTTPS (443)** → el panel y las credenciales viajan sin cifrar.
  - **RTSP (554) sin autenticación** → se detecta con un `DESCRIBE` sin credenciales: **200** = responde sin pedir auth (inseguro); **401** = pide auth (correcto). El `DESCRIBE` es inocuo, no es un ataque.
- **Firmware**: si hay credenciales ONVIF, se lee marca/modelo/firmware. **No** hay base de CVEs propia: se **recomienda revisar los CVEs conocidos** de esa versión. No inventes un CVE puntual; si citás uno, que sea verificable.

## Lo que NO se hace

- No se prueban contraseñas (ni las de fábrica), no hay fuerza bruta, no hay DoS ni explotación.
- No se escanean rangos de red ni se buscan cámaras: solo los hosts declarados.
- Si un control bloquea, se **reporta que existe**; no se evade.

## Severidad

- **Alta**: Telnet/FTP abiertos; RTSP sin autenticación.
- **Media**: HTTP sin HTTPS; puertos de administración expuestos a una red no confiable.
- **Baja**: recordatorio de revisar CVEs del firmware; puertos abiertos esperables en la LAN.

## Corrección típica (para las recomendaciones)

Deshabilitar Telnet/FTP, forzar HTTPS y cambiar el panel a TLS, exigir autenticación fuerte en RTSP, actualizar el firmware, y segmentar las cámaras en una VLAN sin salida a internet.

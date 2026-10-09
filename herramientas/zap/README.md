# OWASP ZAP — seguridad web (escaneo pasivo)

[OWASP ZAP](https://www.zaproxy.org/) es el escáner de seguridad web libre y gratuito de referencia. En k0lmenIA se usa en modo **baseline (pasivo)**: recorre el sitio con el spider y analiza las respuestas **sin enviar ataques ni modificar datos**. Lo usa el agente **`analista-seguridad`**, que además analiza los resultados y arma el informe HTML.

Encuentra, entre otras cosas: encabezados de seguridad faltantes (CSP, HSTS, X-Content-Type-Options…), cookies sin `Secure`/`HttpOnly`/`SameSite`, información expuesta (versiones, comentarios, errores), contenido mixto y problemas de caché de datos sensibles.

> [!IMPORTANT]
> Solo se escanean sitios **propios o con autorización por escrito** de sus dueños, declarados en `SEGURIDAD_URLS_AUTORIZADAS`. Un escaneo pasivo **no reemplaza** un escaneo activo autorizado ni una prueba de penetración.

## Requisitos

- **Docker** en ejecución (Docker Desktop en Windows y macOS). La primera vez descarga la imagen oficial `ghcr.io/zaproxy/zaproxy:stable` (unos cientos de MB).
- **Python 3** (el runner y el generador del informe).

## Configuración (`.env` de la raíz)

```bash
SEGURIDAD_URLS_AUTORIZADAS=https://staging.mi-app.com,https://qa.mi-app.com
# ZAP_IMAGEN=ghcr.io/zaproxy/zaproxy:stable     # opcional: otra imagen o versión fija
```

Una URL autorizada cubre sus subrutas (`https://staging.mi-app.com/login`), pero no otros dominios que empiecen igual.

## Uso

Desde la raíz del repo (o pedíselo al agente: *"revisá la seguridad de https://staging.mi-app.com"*):

```bash
python herramientas/zap/escanear.py --url https://staging.mi-app.com --historia HU-001 [--minutos 1] [--confirmar]
```

- `--minutos`: tiempo de recorrido del spider (1 a 10).
- Sin `--confirmar` pide confirmación en la terminal.

Salida en `output/seguridad/<HU o host>/<fecha>/`:

```
zap.json                 resultado de ZAP (lo lee el agente y el informe)
zap-nativo.html          reporte propio de ZAP
zap.log                  log del escaneo
analisis.json            análisis del agente (falsos positivos, notas, recomendaciones)
informe-seguridad.html   informe de k0lmenIA (dashboard, modo oscuro)
```

El informe se puede regenerar con otro análisis:

```bash
python scripts/generar_informe_seguridad.py <carpeta>/zap.json <carpeta>/informe-seguridad.html --url <url> --analisis <carpeta>/analisis.json
```

## Fuentes

- ZAP Baseline Scan: https://www.zaproxy.org/docs/docker/baseline-scan/
- ZAP en Docker: https://www.zaproxy.org/docs/docker/about/

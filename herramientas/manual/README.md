# Manual de usuario

Herramienta del agente `redactor-manual` (skill `redaccion-manual`). Hace lo determinístico del proceso; la redacción, la evidencia y la navegación de la aplicación (Playwright MCP) las hace el agente.

```bash
npm run manual -- preparar --slug clientes-alta          # carpetas del manual y qué versión sigue
npm run manual -- estado --slug clientes-alta            # borradores, versión final, REVIEW pendientes, capturas
npm run manual -- captura --slug clientes-alta --origen <png de Playwright MCP> --nombre 01-listado-clientes.png
npm run manual -- html output/manuales/clientes-alta/borradores/clientes-alta-v0.1.md
npm run manual -- word output/manuales/clientes-alta/borradores/clientes-alta-v0.1.md [--equipo "<quién firma>"]
npm run manual -- verificar --slug clientes-alta         # checklist antes de la versión final (sale con 1 si no pasa)
npm run manual -- a-input --slug clientes-alta --url https://qa.mi-app.com
npm run manual -- plataforma --menu output/manuales/plataforma/menu.json
```

```
+--------------+------------------------------------------+
| Comando      | Qué hace                                 |
+==============+==========================================+
| `preparar`   | Crea `output/manuales/<slug>/` con       |
|              | `capturas/`, `borradores/`, `revision/`  |
|              | y `versiones/` (no pisa nada).           |
+--------------+------------------------------------------+
| `estado`     | Último borrador, el nombre del siguiente |
|              | (`v0.N`), la versión final, los REVIEW y |
|              | las capturas.                            |
+--------------+------------------------------------------+
| `captura`    | Mueve una captura a `capturas/`          |
|              | validando el nombre `NN-                 |
|              | descripcion.png`; no pisa sin            |
|              | `--reemplazar`.                          |
+--------------+------------------------------------------+
| `html`       | HTML autocontenido con el diseño de los  |
|              | informes de k0lmena y las capturas       |
|              | embebidas.                               |
+--------------+------------------------------------------+
| `word`       | `.docx` con el diseño de k0lmena:        |
|              | portada noche + ámbar con el logo,       |
|              | Saira/Inter/JetBrains Mono embebidas.    |
+--------------+------------------------------------------+
| `verificar`  | Sin REVIEW pendientes, sin bloques QA    |
|              | REVIEW, imágenes existentes y matriz sin |
|              | REVIEW/BLOCKED.                          |
+--------------+------------------------------------------+
| `a-input`    | Deja el manual en                        |
|              | `input/documentacion/manual-             |
|              | usuario/<slug>.md` para los demás        |
|              | agentes.                                 |
+--------------+------------------------------------------+
| `plataforma` | Plan del manual de toda la plataforma    |
|              | por módulos (menú relevado + mapa        |
|              | funcional).                              |
+--------------+------------------------------------------+
```

**Word**: la primera vez instala `docx` e `image-size` en `herramientas/manual/.deps/` (no se versiona) y convierte las fuentes de `scripts/fuentes/` a TTF para embeberlas (necesita `fonttools` y `brotli`; si no se pueden instalar, el documento usa las fuentes de la máquina). El interior es claro para que se pueda imprimir; la portada, oscura como los informes. `MANUAL_EQUIPO` en el `.env` firma el documento (opcional).

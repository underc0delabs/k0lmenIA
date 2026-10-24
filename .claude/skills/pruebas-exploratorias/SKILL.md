---
name: pruebas-exploratorias
description: Referencia del explorador-web — qué revisa y deja npm run explorar, la checklist de la exploración manual con Playwright MCP, el esquema del analisis.json, la severidad sugerida por tipo de hallazgo y la checklist antes de entregar.
---

# Pruebas exploratorias web — referencia

Material de consulta del agente `explorador-web`. El flujo y las reglas están en el agente.

## 1. Qué hace `npm run explorar`

```bash
npm run explorar -- --url <url> [--historia HU-001] [--max-paginas 25] [--profundidad 3] [--resoluciones 360x740,390x844,768x1024,1366x768,1920x1080] [--responsive 10] [--externos si] [--video si] [--lenta-ms 3000]
```

Trabaja en una carpeta fija, `output/exploratorias/<HU o host>/`: al arrancar, la corrida anterior pasa a `historial/` (últimas 5, con su evidencia) y el informe muestra qué es nuevo, qué se resolvió y la evolución. Deja:

- `exploracion.json` (los datos) e `informe-exploratorio.html` (el informe, ya generado);
- `capturas/paginas/` (cada página, desktop, página completa) y `capturas/responsive/` (cada página en cada resolución), con los elementos con problemas **marcados en rojo**;
- `videos/` (`recorrido.webm` y uno por resolución; `--video no` para no grabar).

Revisa:

- **Links** internos y externos (rotos vs. *no verificables*: 401/403/429 o timeouts, que suelen ser sitios que bloquean robots).
- **Imágenes** que no cargan, y las imágenes sin `alt`.
- **Errores de JavaScript**, **errores de consola** y **recursos** (scripts, CSS, fetch) que responden 4xx/5xx o no responden.
- **Responsive** en cada resolución: scroll horizontal y qué elemento se sale, texto de menos de 12px y objetivos táctiles de menos de 24px muy juntos (WCAG 2.5.8) en mobile, y la falta de `<meta name="viewport">`.
- **Métricas** de cada página: tiempo de carga, primer byte, DOM listo, requests y peso aproximado; las que tardan más de `--lenta-ms` son hallazgos de rendimiento.

Un mismo problema en varias páginas (un CSS de la plantilla que falta, el menú) queda como **un solo hallazgo** con la lista de páginas. Si avisa que quedaron páginas sin recorrer, va al informe (y se sugiere subir `--max-paginas`).

El informe final trae indicadores, gráficos (páginas y links, hallazgos por severidad y por tipo, tiempos de carga, responsive por resolución), cada hallazgo con su captura, la exploración manual, la matriz de responsive, los videos, las galerías de capturas, los links rotos y el detalle de cada página con sus errores.

## 2. Revisión de los hallazgos automáticos

- **Confirmá los dudosos**: un link externo con 5xx puede ser intermitente; reintentalo y anotalo en `notas`.
- **Descartá** solo con un motivo verificable (por ejemplo, un error de consola de un script de terceros que no afecta la página). Ante la duda, no lo descartes.
- **Mirá las capturas** de responsive (con Read) para confirmar si el desborde se ve o es un elemento oculto, y ajustá la severidad si corresponde (`severidades` + el motivo en `notas`).

## 3. Checklist de la exploración manual (Playwright MCP)

Con una **misión** (charter) y un tiempo acotado (15–30 minutos de trabajo, salvo otro pedido), partiendo de lo que encontró el recorrido y de lo que tiene más riesgo:

- **Navegación**: menú principal y menú mobile (abrir, cerrar, navegar), migas, volver atrás, links del pie, la página 404 (`/una-ruta-que-no-existe`).
- **Formularios** (sin enviar, salvo confirmación): campos obligatorios vacíos, formatos inválidos, valores límite, textos muy largos, caracteres especiales y acentos, espacios al principio y al final, doble clic en el botón.
- **Búsqueda y filtros**: sin resultados, caracteres especiales, búsqueda vacía.
- **Responsive interactivo** (con `browser_resize` a 390x844): que los menús, modales y formularios se puedan usar, no solo que no desborden.
- **Estados y errores**: recargar en medio de un flujo, abrir una URL interna directamente, consola del navegador (`browser_console_messages`) mientras interactuás.

Por cada problema: captura `<carpeta>/capturas/manual/ex-XX.png` (si Playwright la deja en otro lado, se mueve con Bash; en el análisis va como `capturas/manual/ex-XX.png`), pasos, esperado y obtenido.

## 4. `analisis.json`

`veredicto`, `resumen` (para alguien no técnico), `mision`, `duracion_min`, `areas_exploradas`, `notas` (por ID de hallazgo), `descartados`, `severidades`, `exploratorios` (`EX-01`, … con `titulo`, `severidad`, `pagina`, `pasos`, `esperado`, `obtenido`, `correccion`, `evidencia`), `falta_informacion` (`id`, `que_falta`, `pregunta`), `recomendaciones` (acción, por qué y prioridad) y `proximos_pasos`. El formato completo está en el encabezado de `scripts/generar_informe_exploratorio.py`.

## 5. Severidad sugerida

El script propone una severidad; se ajusta con criterio (explicado en `notas`):

| Hallazgo                                                     | Severidad sugerida |
| ------------------------------------------------------------ | ------------------ |
| Página que no abre o responde 5xx                            | Crítica            |
| Página 4xx, link interno roto, imagen rota, error de JS      | Alta               |
| Script o CSS que no carga                                    | Alta               |
| Scroll horizontal en mobile (menos de 768 px)                | Alta               |
| Link externo roto, error de consola, otro recurso que falla  | Media              |
| Scroll horizontal en tablet (768 px) o desktop, sin viewport | Media              |
| Texto chico, objetivos táctiles chicos, imágenes sin alt     | Baja               |
| Página lenta (más de `--lenta-ms`; Media si tarda el doble)  | Baja               |

## 6. Antes de entregar

- El `analisis.json` es JSON válido y el informe se regeneró sin error. El script avisa por consola (`[aviso] analisis.json · …`) los IDs que no existen y las severidades fuera de la escala: corregilos y regenerá.
- Cada ID citado (`notas`, `severidades`, `hallazgos`, `descartados`) existe en el JSON de la herramienta, con su formato (`H-03`, no `H-3`), y las severidades son `Crítica`, `Alta`, `Media` o `Baja`.
- Cada hallazgo manual tiene página, pasos, esperado, obtenido, `correccion` y una captura que existe dentro de la carpeta, con ruta relativa.
- Cada descarte tiene un motivo verificable, y lo que ninguna fuente define va en `falta_informacion`, no en el veredicto.
- No quedan credenciales, tokens ni datos personales en el análisis, el informe ni las capturas.

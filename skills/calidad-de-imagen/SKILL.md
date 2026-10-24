---
name: calidad-de-imagen
description: El cómo de evaluar la calidad de imagen de una cámara — qué mide OpenCV (brillo, Laplaciano, diferencia entre capturas, contra referencia), con qué umbrales, y qué juzgar con visión (lente sucia, encuadre, contraluz, IR). Lo usa el agente calidad-imagen.
---

# Calidad de imagen de cámaras

Guía para evaluar **cómo se ve** una cámara, combinando métricas de OpenCV (lo objetivo) con tu juicio mirando la captura (lo de criterio). La herramienta `${CLAUDE_PLUGIN_ROOT}/herramientas/streaming/calidad_imagen.py` deja la captura en `capturas/` y las métricas en `calidad.json`.

## Lo objetivo (OpenCV, ya calculado)

- **Brillo medio** del gris. Por debajo de ~15 la imagen está prácticamente **negra** (cámara tapada, sin señal, sin IR de noche).
- **Nitidez** = varianza del Laplaciano. Por debajo de ~100 está **desenfocada** (lente sucia, fuera de foco, o niebla). Es relativa a la escena: una pared lisa da baja varianza sin estar borrosa, por eso se confirma con la vista.
- **Congelamiento**: diferencia media entre dos capturas separadas N segundos (`--freeze`). Casi cero = **imagen congelada** (el stream no avanza aunque "reproduzca").
- **Cámara movida**: diferencia media contra una **referencia** (`--referencia`). Alta = el encuadre cambió (alguien la movió) o la escena cambió mucho. Encaja con la idea de `pixel-perfect`: comparar contra una referencia y reportar cuánto cambió.

Umbrales en el runner: `BRILLO_NEGRO=15`, `BLUR_MINIMO=100`, `FREEZE_DIF=1.0`, `MOVIDA_DIF=25`. Son un punto de partida; si la persona define otros por el tipo de escena, esos mandan.

## Lo de criterio (vos, con visión)

Mirá la captura y evaluá lo que una métrica no distingue bien:

- **Lente obstruida o sucia**: manchas, gotas, telaraña, algo tapando parte del cuadro.
- **Cámara movida del encuadre de referencia**: apunta a otro lado, se corrió o giró.
- **Contraluz**: una ventana o foco quema parte de la imagen y no se ve lo importante.
- **Modo IR de noche**: de noche debería verse en blanco y negro con IR; si está oscura o en color ruidoso, el IR no conmutó. **Ojo**: una imagen "oscura" de noche con IR correcto **no** es un defecto — no la marques solo por brillo bajo.

## Cómo decidir

- Un hallazgo automático (negro, desenfoque, congelamiento) es un **candidato**: confirmalo con la captura. Descartá lo esperado (escena lisa, noche con IR).
- Sin una **referencia** o sin saber cómo debería verse (día/noche, encuadre), lo que no puedas afirmar va como `Falta información`, no como defecto.

## Severidad

- **Crítica**: no se pudo capturar imagen de la cámara.
- **Alta**: imagen negra, desenfocada o congelada (confirmada).
- **Media**: cámara movida respecto de la referencia; contraluz que impide ver lo importante.
- **Baja**: IR que no conmuta (si es esperable cierto ruido), suciedad leve.

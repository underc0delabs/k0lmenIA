# Contenido / typos

Revisión de **solo lectura** de contenido y typos de un texto o archivo. La usa el agente `revisor-contenido`.

- **`contenido.py`** (`npm run contenido`) — detecta por heurística (sin diccionario, sin dependencias) los errores objetivos más comunes: placeholders olvidados, Lorem ipsum, palabras duplicadas, claves de i18n a la vista, marcadores TODO, espacios antes de puntuación y espacios múltiples. Con `--lt` corre **LanguageTool** (ortografía/gramática reales) si está instalado.

```bash
npm run contenido -- --archivo pagina.txt --idioma es
npm run contenido -- --texto "el el texto a revisar"
```

No juzga estilo ni tono, solo errores objetivos. Sin dependencias para la heurística; LanguageTool es opcional (`pip install language-tool-python`).

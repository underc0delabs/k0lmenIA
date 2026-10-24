---
name: pruebas-seo
description: El cómo de probar SEO y GEO — técnico (indexabilidad, robots, sitemap, canónicas, redirecciones, hreflang, JSON-LD, Core Web Vitals, render), on-page, y GEO (aparecer en AI Overviews, ChatGPT, Perplexity; contenido citable, E-E-A-T, acceso de crawlers de IA, llms.txt). Lo usa el analista-seo.
---

# Pruebas de SEO y GEO

El SEO es que los **buscadores** encuentren, entiendan e indexen el sitio; el **GEO** (Generative Engine Optimization) es que los **motores con IA** (AI Overviews, ChatGPT, Perplexity, Copilot) lo **citen** en sus respuestas. Comparten mucho (contenido claro, estructurado y con autoridad), pero el GEO suma lo suyo. Se apoya en el `auditor-rendimiento-web` (Core Web Vitals) y `analista-traductor` (hreflang/idiomas).

## 1. Indexabilidad (SEO técnico)

- **robots.txt**: no bloquea lo que debe indexarse; declara el **Sitemap:**. Un `Disallow: /` en producción saca el sitio de Google (bien en staging).
- **sitemap.xml**: existe, es válido, lista las URLs canónicas (no las bloqueadas ni las `noindex`), y está actualizado.
- **meta robots / X-Robots-Tag**: `noindex` donde corresponde (resultados de búsqueda internos, carritos), y **no** en páginas que deben rankear. Un `noindex` olvidado en producción es de los peores bugs de SEO.
- **Códigos de estado y redirecciones**: 200 en lo indexable, **301** (no 302) para redirecciones permanentes, sin cadenas ni loops; una URL vieja redirige, no da 404 ni soft-404.
- **Canónicas** (`rel=canonical`): cada página apunta a su versión canónica; sin canónicas cruzadas ni apuntando a otra página.

## 2. On-page

- **Title** único y descriptivo (~60 car.), **meta description** (~155 car.), un solo **H1**, jerarquía de encabezados coherente.
- **Alt** en las imágenes, **enlaces internos** con anchor útil, sin contenido duplicado ni **canibalización** (dos páginas compitiendo por la misma keyword).
- URLs limpias y estables; parámetros que no generen duplicados indexables.

## 3. Datos estructurados y social

- **Schema.org (JSON-LD)**: el tipo correcto (Product, Article, FAQ, BreadcrumbList, Organization, LocalBusiness…), válido y consistente con lo visible. Habilita rich results **y** ayuda al GEO.
- **Open Graph** y **Twitter Cards** para que el sitio se vea bien al compartirlo (y lo usan algunos motores).

## 4. Internacional

- **hreflang** correcto y recíproco entre idiomas/regiones, con `x-default`; sin apuntar a páginas `noindex` ni rotas (ver `analista-traductor`).

## 5. Rendimiento y renderizado

- **Core Web Vitals** (LCP, CLS, INP) con el `auditor-rendimiento-web`: son factor de ranking y de experiencia.
- **Renderizado**: si el sitio es CSR (JS puro), Google puede verlo vacío; verificá que el contenido clave esté en el HTML inicial (SSR/prerender) o que se renderice bien. El contenido que solo aparece tras interacción no se indexa.
- **Mobile-first**: Google indexa la versión mobile; que tenga el mismo contenido y datos estructurados que desktop.

## 6. GEO (motores generativos / IA)

- **Acceso de los crawlers de IA**: en `robots.txt`, definí si permitís **GPTBot** (OpenAI), **ClaudeBot/anthropic-ai**, **PerplexityBot**, **Google-Extended** (entrenamiento) y **OAI-SearchBot**. Bloquearlos te saca de sus respuestas; permitirlos te hace citable. Es una decisión de negocio: confirmala.
- **Contenido citable**: respuestas **directas y autocontenidas** (un párrafo que responde la pregunta), encabezados en forma de pregunta, listas y tablas, definiciones claras; los motores citan fragmentos, no páginas enteras.
- **Autoridad y E-E-A-T** (experiencia, expertise, autoridad, confianza): autor, fuentes citadas, fecha de actualización, datos verificables. Los motores con IA prefieren fuentes confiables y frescas.
- **Datos estructurados** (FAQ, HowTo, Article): ayudan a la IA a extraer la respuesta.
- **llms.txt** (emergente): un archivo que resume el sitio para los LLM; opcional, pero suma.
- **Frescura**: contenido con fecha y actualizado; lo viejo se cita menos.

## 7. Medir y automatizar

- La herramienta `k0lmenia seo` (`${CLAUDE_PLUGIN_ROOT}/herramientas/seo/seo.py`) trae una URL y chequea title, meta description, canónica, meta robots, Open Graph, JSON-LD, H1, hreflang, robots.txt, sitemap y el acceso de los crawlers de IA.
- Los Core Web Vitals, con el `auditor-rendimiento-web`; el render JS, abriendo la página con Playwright y comparando el HTML inicial con el renderizado.

## 8. Bugs típicos de SEO/GEO

- `noindex` o `Disallow: /` olvidado en producción.
- Canónica apuntando a otra página o a `http` en un sitio `https`.
- Title/description duplicados o vacíos; varios H1 o ninguno.
- Redirecciones 302 donde deberían ser 301; cadenas de redirección; soft-404.
- JSON-LD inválido o que no coincide con lo visible.
- Contenido clave solo en JS que Google no renderiza.
- hreflang no recíproco o a páginas rotas.
- Crawlers de IA bloqueados sin querer (o permitidos cuando el negocio no quería).
- Sitemap con URLs `noindex`, rotas o no canónicas.

## 9. Preguntas típicas para el PO (SEO/GEO)

Cuando no está escrito, son `FI-XX`:

- ¿Qué páginas deben indexarse y cuáles no? ¿Hay un sitemap y quién lo genera?
- ¿El sitio es SSR o CSR? ¿El contenido clave está en el HTML inicial?
- ¿Qué idiomas/regiones y cómo se maneja hreflang?
- ¿Se quiere aparecer en los motores con IA? ¿Se permiten GPTBot/ClaudeBot/PerplexityBot?
- ¿Qué tipos de datos estructurados aplican al contenido?
- ¿Hay keywords objetivo por página (para detectar canibalización)?

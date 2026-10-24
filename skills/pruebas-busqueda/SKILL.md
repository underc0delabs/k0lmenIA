---
name: pruebas-busqueda
description: El cómo de probar búsqueda y relevancia (Elasticsearch, Algolia, Solr, Typesense, Meilisearch, full-text) — ranking, typos, sinónimos, facetas, cero resultados, indexación, seguridad y medición con golden set (precision@k, nDCG, MRR). Lo usa el probador-busqueda.
---

# Pruebas de búsqueda y relevancia

La búsqueda no es "trae algo": es **traer lo correcto, arriba, rápido**. Se prueba con un **golden set** (consultas con el/los resultado(s) esperado(s)) y casos de borde, más la relevancia, los filtros y la indexación. Se complementa con `tecnicas-de-diseno` y, en tiendas, con `pruebas-ecommerce`.

## 1. Relevancia y ranking

- La consulta con intención clara trae el resultado **correcto en las primeras posiciones** (no en la página 3).
- **Boosting**: campos más importantes (título > descripción), y reglas de negocio (destacados, stock, promos) afectan el orden como se espera.
- Consultas de una palabra, varias palabras, frase exacta (comillas) y parciales.

## 2. Tolerancia a errores y lenguaje

- **Typos / fuzzy**: "iphon", "zapatila" encuentran lo correcto (con una distancia de edición razonable).
- **Sinónimos** (celular/móvil, remera/playera) y **stemming/lematización** por idioma (zapato/zapatos, correr/corriendo).
- **Stop words**, **acentos/diacríticos** (café = cafe), mayúsculas/minúsculas.

## 3. Cero resultados y ayudas

- Una consulta sin resultados muestra un **mensaje claro** y, si aplica, **did-you-mean** / sugerencias, no una página vacía ni un error.
- **Autocompletar/typeahead**: sugiere a medida que se escribe, rápido y relevante.

## 4. Facetas, filtros y orden

- Las **facetas** (categoría, precio, marca) filtran bien y se **combinan con la query**; los contadores de cada faceta son correctos; limpiar filtros vuelve al estado base.
- **Paginación** y **orden** (relevancia, precio, fecha) sin perder ni duplicar resultados.

## 5. Indexación y freshness

- Un documento **nuevo aparece** en la búsqueda tras indexar (ojo con el delay de indexación: puede no ser un bug), uno **borrado desaparece**, uno editado refleja el cambio.
- Coincidencia **exacta por SKU/código/ID**; búsqueda por atributos.

## 6. Bordes y seguridad

- Consulta **vacía**, solo espacios, muy larga, con caracteres especiales o comodines; que no rompa ni haga **inyección** en la query (Query DSL injection).
- **Seguridad/permisos**: un usuario no ve en los resultados documentos a los que no tiene acceso (multi-tenant, borradores, privados).

## 7. Rendimiento

- **Latencia** de la búsqueda y del autocompletar bajo consultas típicas y pesadas (muchas facetas); para carga, `performance-mapper`.

## 8. Medir (golden set y métricas)

- Armá un **golden set**: consulta → resultado(s) esperado(s) o criterio ("el primer resultado debe ser X"). Medí **precision@k**, **recall**, y para ranking **nDCG** o **MRR**.
- Es también la **suite de regresión**: cuando se cambian analyzers, sinónimos o boosting, se corre el set y se compara (¿mejoró o empeoró la relevancia?).

## 9. Automatizar

- Golden set contra el **endpoint de búsqueda** con el `ejecutor-api`, o contra la **UI** con Playwright (`ejecucion-e2e`); verificá posición/presencia del esperado, facetas y cero-resultados.
- Datos de prueba: productos/documentos con sinónimos, acentos, typos deliberados y uno sin resultados (`generador-datos-prueba`).

## 10. Bugs típicos de búsqueda

- El resultado obvio no aparece primero (relevancia/boosting mal).
- No tolera typos ni acentos; sinónimos que no funcionan.
- Cero resultados sin mensaje ni sugerencia (pantalla vacía).
- Faceta cuyo contador no coincide con los resultados; combinación query+filtro que rompe.
- Documento borrado que sigue apareciendo (indexación desactualizada).
- Resultados que exponen documentos privados/de otro tenant.
- Autocompletar lento o irrelevante; búsqueda que tumba el backend con una query pesada.

## 11. Preguntas típicas para el PO (búsqueda)

Cuando no está escrito, son `FI-XX`:

- ¿Qué motor de búsqueda (Elasticsearch/OpenSearch, Algolia, Solr, DB full-text)?
- ¿Cuáles son las consultas más importantes y su resultado esperado (para el golden set)?
- ¿Qué boosting/reglas de negocio afectan el orden?
- ¿Hay sinónimos y stemming configurados? ¿En qué idiomas?
- ¿Cuánto tarda la indexación en reflejar un cambio?
- ¿Hay documentos con permisos (privados/multi-tenant) que no deben filtrarse?

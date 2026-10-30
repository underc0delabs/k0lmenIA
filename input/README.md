# input/ — los insumos para los agentes

```
+---------------------+-----------------------------------------+------------------------------------------+
| Carpeta             | Qué va                                  | Nombre sugerido                          |
+=====================+=========================================+==========================================+
| `historias/`        | Historias de usuario con sus criterios  | `HU-001-registro.md`                     |
|                     | de aceptación (`HU-XXX-<tema>.md`)      |                                          |
+---------------------+-----------------------------------------+------------------------------------------+
| `documentacion/`    | Documentación del proyecto: la que arma | `INDICE.md`, `proyecto/`, `api/`,        |
|                     | el documentador-proyecto (repositorio,  | `historias/<HU o key>/dossier.md` (no se |
|                     | historias, links, mapa funcional) y la  | versiona)                                |
|                     | que agregues a mano (actas, PDFs)       |                                          |
+---------------------+-----------------------------------------+------------------------------------------+
| `api/`              | Contratos de API, colecciones y         | incluye `auth-endpoints.md` y            |
|                     | environments de Postman, Bruno (carpeta | `demo.postman_collection.json`, `demo-   |
|                     | con `bruno.json`) o Insomnia (export    | bruno/` y `demo.insomnia.json`           |
|                     | `.json`/`.yaml`), Swagger/OpenAPI y     | (JSONPlaceholder), y una demo GraphQL    |
|                     | schemas GraphQL (`.graphql`)            | (`demo-graphql.postman_collection`)      |
+---------------------+-----------------------------------------+------------------------------------------+
| `bugs/`             | Observaciones sueltas de errores para   | `observacion-<tema>.md`                  |
|                     | convertir en reportes                   |                                          |
+---------------------+-----------------------------------------+------------------------------------------+
| `ejecucion-manual/` | Casos de ejemplo para practicar la      | `casos-HU-950.ejemplo.json`              |
|                     | ejecución manual acompañada             |                                          |
+---------------------+-----------------------------------------+------------------------------------------+
```

Si tu equipo usa Jira, no hace falta copiar las historias acá: pasale a los agentes la key (`PROJ-12`) con el conector activo (ver `CONECTORES.md`).

## Primer uso en cinco minutos

0. (Opcional, recomendado) Pedí *"Documentá el proyecto"*: el `documentador-proyecto` lee el repositorio de la app (`REPO_RUTA_LOCAL` en el `.env`), las historias y la web, y deja el contexto en `documentacion/` para los demás agentes.
1. Guardá una historia en `input/historias/HU-001-<tema>.md`: título, "Como / Quiero / Para" y los criterios de aceptación numerados (`CA1`, `CA2`, …). Para practicar podés usar el formulario "Crear cuenta" del sitio de práctica https://qarmy.ar/practica/automation (el `BASEURL` de `.env.example`).
2. En Claude Code, pedí en orden:
   - *"Analizá la historia HU-001"* → ambigüedades y preguntas para el PO en `output/analisis-historias/`.
   - *"Generá los casos de prueba de HU-001"* → planilla Excel, Markdown y cobertura en `output/casos-de-prueba/manuales/`.
   - *"Pasá HU-001 a BDD"* → `.feature` y cobertura en `output/casos-de-prueba/bdd/`.
   - *"Ejecutá CP-001 de HU-001 contra <URL> en headless"* → reporte HTML con evidencia en `output/ejecuciones/`.
3. Para un bug, guardá tu observación (aunque esté desordenada) en `input/bugs/` y pedí *"Triá el bug de input/bugs/<archivo>"* → duplicados, regresiones y severidad sugerida en `output/triage/`.

La colección `api/demo.postman_collection.json` apunta a JSONPlaceholder (una API pública de prueba): *"Corré la colección demo de input/api"* la ejecuta con Newman y deja su reporte.

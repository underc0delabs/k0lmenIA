# input/ — los insumos para los agentes

```
+------------------+------------------------------------------+---------------------------------------+
| Carpeta          | Qué va                                   | Nombre sugerido                       |
+==================+==========================================+=======================================+
| `historias/`     | Historias de usuario con sus criterios   | `HU-001-registro.md`                  |
|                  | de aceptación (`HU-XXX-<tema>.md`)       |                                       |
+------------------+------------------------------------------+---------------------------------------+
| `documentacion/` | Documentación del proyecto: la que arma  | `INDICE.md`, `proyecto/`, `api/`,     |
|                  | el documentador-proyecto (repositorio,   | `historias/<HU o key>/dossier.md`,    |
|                  | historias, links, mapa funcional), la    | `proyecto/investigacion/`,            |
|                  | del investigador-proyecto (tableros), la | `manual-usuario/` (no se versiona)    |
|                  | del redactor-manual (cómo se usa la app) |                                       |
|                  | y la que agregues a mano (actas, PDFs)   |                                       |
+------------------+------------------------------------------+---------------------------------------+
| `api/`           | Contratos de API, colecciones y          | incluye `auth-endpoints.md` y         |
|                  | environments de Postman, Bruno (carpeta  | `demo.postman_collection.json`,       |
|                  | con `bruno.json`) o Insomnia (export     | `demo-bruno/` y `demo.insomnia.json`  |
|                  | `.json`/`.yaml`), Swagger/OpenAPI y      | (JSONPlaceholder), y una demo GraphQL |
|                  | schemas GraphQL (`.graphql`)             | (`demo-graphql.postman_collection`)   |
+------------------+------------------------------------------+---------------------------------------+
| `bugs/`          | Observaciones sueltas de errores para    | `observacion-<tema>.md`               |
|                  | convertir en reportes                    |                                       |
+------------------+------------------------------------------+---------------------------------------+
| `correos/`       | Lo que tiene que llegar por mail en cada | `espera-HU-001.json`                  |
|                  | caso (verificador-correos)               |                                       |
+------------------+------------------------------------------+---------------------------------------+
| `logs/`          | Logs de la aplicación para el            | `app.log`, `access.log` (no se        |
|                  | analista-logs (no se versionan)          | versionan)                            |
+------------------+------------------------------------------+---------------------------------------+
```

Si tu equipo usa Jira o Azure DevOps, no hace falta copiar las historias acá: pasale a los agentes
la key (`PROJ-12`) o el ID del work item (`1234`) con el conector activo (ver `CONECTORES.md`).

## Primer uso en cinco minutos

0. (Opcional, recomendado) Pedí *"Documentá el proyecto"*: el `documentador-proyecto` lee el repositorio de la app, las historias y la web, y deja el contexto en `documentacion/` para los demás agentes (ver el bloque *Repositorio de la aplicación* del `.env`).
1. Guardá una historia en `input/historias/HU-001-<tema>.md`: título, "Como / Quiero / Para" y los criterios de aceptación numerados (`CA1`, `CA2`, …). Para practicar podés usar el formulario "Crear cuenta" del sitio de práctica https://qarmy.ar/practica/automation (el `BASEURL` de `.env.example`).
2. En Claude Code, pedí en orden:
   - *"Analizá la historia HU-001"* → ambigüedades y preguntas para el PO en `output/analisis-historias/`.
   - *"Generá los casos de prueba de HU-001"* → planilla Excel, Markdown y cobertura en `output/casos-de-prueba/manuales/`.
   - *"Pasá HU-001 a BDD"* → `.feature` y cobertura en `output/casos-de-prueba/bdd/`.
   - *"Ejecutá CP-001 de HU-001 contra <URL> en headless"* → reporte HTML con evidencia en `output/ejecuciones/`.
3. Para un bug, guardá tu observación (aunque esté desordenada) en `input/bugs/` y pedí *"Armá el reporte de bug de input/bugs/<archivo>"* → `output/reportes-bug/BUG-001.md`.

La colección `api/demo.postman_collection.json` apunta a JSONPlaceholder (una API pública de prueba): *"Corré la colección demo de input/api"* la ejecuta con Newman y deja su reporte.

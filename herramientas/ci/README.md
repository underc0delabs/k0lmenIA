# CI

Plantillas para correr las suites de **k0lmena** en el pipeline del equipo, sin agentes ni tokens: instalan k0lmena y Chromium (con sus dependencias), corren las suites, guardan `herramientas/k0lmena/reports/` como artefacto y, si hay ciclo, publican los resultados en Xray o k0lmenaTMT con `scripts/gestion/gestion.py`.

```bash
npm run ci -- listar
npm run ci -- generar --plataforma github                 # → .github/workflows/k0lmena.yml
npm run ci -- generar --plataforma gitlab --suite all     # → .gitlab-ci.yml (web y api)
npm run ci -- generar --plataforma jenkins                # → Jenkinsfile
npm run ci -- generar --plataforma azure --suite api      # → azure-pipelines.yml
npm run ci -- generar --plataforma github --destino C:/proyectos/mi-qa --forzar
```

- **`--suite`**: `web` (por defecto), `api` o `all` (web y api). Mobile necesita un dispositivo o BrowserStack: se suma a mano en `K0LMENA_SUITES`.
- **`--destino`**: la raíz del repo donde va el pipeline (por defecto, este). El pipeline espera la estructura de k0lmenIA (`herramientas/k0lmena`, `scripts/gestion`).
- No pisa un pipeline existente salvo `--forzar`.

## Secretos: el `.env` entero, como secret del pipeline

Las plantillas **no llevan ningún valor**. El `.env` (con `APP_URL`, `GESTION_HERRAMIENTA`, `GESTION_PROYECTO` y los tokens de la herramienta de gestión) se carga como secret y llega por `K0LMENA_ENV_FILE`, que leen k0lmena y `scripts/gestion`:

```
+------------+------------------------------------------------------------+
| Plataforma | Dónde va el .env                                           |
+============+============================================================+
| GitHub     | Secret `K0LMENIA_ENV` (el contenido del archivo)           |
+------------+------------------------------------------------------------+
| GitLab     | Variable `K0LMENA_ENV_FILE` de tipo File, protegida        |
+------------+------------------------------------------------------------+
| Jenkins    | Credencial *Secret file* con id `k0lmenia-env`             |
+------------+------------------------------------------------------------+
| Azure      | Secure file `k0lmenia.env` (Pipelines > Library)           |
+------------+------------------------------------------------------------+
```

## Publicar resultados (opcional)

Si hay **`GESTION_CICLO`** (variable del pipeline, input al correrlo a mano o en el `.env`), después de las suites corre:

```bash
python herramientas/ci/ci.py publicar --suites "web api" [--ciclo PROJ-60] [--traza HU-001] [--dry-run]
```

que, por cada suite con `cucumber-report.json`, hace `gestion.py extraer-resultados` y `publicar-resultados --ciclo`. Los escenarios se asocian a los casos por tag (`@PROJ-45`, o `@CP-001` con la trazabilidad de `--traza`), como en `scripts/gestion/README.md`. Sin ciclo no publica nada.

Si una suite falla, el pipeline igual guarda los reportes y publica, y termina en error.

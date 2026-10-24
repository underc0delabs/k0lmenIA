# Revisión estática de código

Herramientas de **solo lectura** que usa el agente `revisor-codigo` para hacer code review de un repositorio o de un PR/MR.

- **`obtener.py`** (`npm run obtener-codigo`) — trae el código desde **GitHub, GitLab (también self-managed), Bitbucket Cloud, Azure Repos, Gitea/Forgejo/Codeberg**, cualquier URL git/SSH o una carpeta local. Con un PR/MR (o `--base <rama>`) calcula qué cambió contra el merge-base: archivos, líneas nuevas y `cambios.diff`. Deja un manifiesto `origen.json` con el commit y la plantilla de link a cada línea en la web del proveedor.
- **`revision.py`** (`npm run revision-codigo`) — reglas propias por lenguaje (seguridad, performance, confiabilidad, malas prácticas), métricas de mantenibilidad (largo y complejidad de funciones, anidamiento, parámetros, archivos grandes, duplicados), el escáner de secretos de `herramientas/seguridad/sast.py` y, si están instalados, **semgrep**, **ruff** y **bandit**. Deja `revision.json` con sospechas para triagear.

```bash
npm run obtener-codigo -- --origen https://github.com/dueño/repo/pull/123
npm run revision-codigo -- --origen output/revision-codigo/repo-pr-123/origen.json
python scripts/generar_informe_revision_codigo.py output/revision-codigo/repo-pr-123/analisis.json output/revision-codigo/repo-pr-123/informe-revision-codigo.html --markdown output/revision-codigo/repo-pr-123/comentarios-pr.md
```

| Origen                                   | Ejemplo                                                        |
|------------------------------------------|----------------------------------------------------------------|
| Repo / rama (GitHub)                     | `https://github.com/dueño/repo/tree/feature-x`                 |
| PR (GitHub)                              | `https://github.com/dueño/repo/pull/123`                       |
| MR (GitLab)                              | `https://gitlab.com/grupo/sub/proyecto/-/merge_requests/45`    |
| PR (Bitbucket Cloud)                     | `https://bitbucket.org/workspace/repo/pull-requests/7`         |
| PR (Azure Repos)                         | `https://dev.azure.com/org/proyecto/_git/repo/pullrequest/9`   |
| PR (Gitea / Forgejo / Codeberg)          | `https://codeberg.org/dueño/repo/pulls/12`                     |
| Cualquier git                            | `https://git.miempresa.com/equipo/app.git`, `git@host:a/b.git` |
| Carpeta local (con `--base` si es git)   | `C:/proyectos/mi-app`                                          |
| Sin `--origen`                           | `REPO_PROVEEDOR` + `REPO_NOMBRE` (+ `REPO_RAMA`) del `.env`    |

**Repos privados** — token de solo lectura en el `.env`: `GITHUB_TOKEN`, `GITLAB_TOKEN` (`read_repository`/`read_api`), `BITBUCKET_TOKEN` (o `JIRA_API_TOKEN` con permisos de Bitbucket; el email para la API, `BITBUCKET_EMAIL` o `JIRA_EMAIL`), `ADO_PAT` (Code: Read), y `REVISION_GIT_TOKEN` + `REVISION_GIT_USUARIO` para otros hosts (o para pisar los anteriores). Cada token se manda solo a su host, como header HTTP por variables de entorno de git: no queda en la URL, en `.git/config` ni en la salida. Por SSH se usan tus llaves.

**Seguridad** — el código traído es ajeno. No se ejecuta nada del repo: sin hooks, submódulos, LFS, instaladores ni linters que carguen configuración ejecutable (por eso no se corre ESLint). Los symlinks se clonan como texto y no se siguen. Los clones quedan en `output/revision-codigo/` (no se versiona).

**Ruido** — una línea con `k0lmenia: ignorar` se saltea. Se omiten carpetas de dependencias y build, archivos generados y minificados. En archivos de test, la severidad baja un nivel y algunas reglas (console, sleep, TODO) no aplican. Hay un tope de hallazgos por regla y archivo (`recortados_por_tope` en el resumen).

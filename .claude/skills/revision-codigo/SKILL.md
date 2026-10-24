---
name: revision-codigo
description: Cómo hacer una revisión estática de código (code review) — traer el código de GitHub, GitLab, Bitbucket, Azure Repos, Gitea o cualquier git sin ejecutarlo; revisar un repo entero, una rama contra su base o un PR/MR (solo lo que cambió); qué mirar por categoría (seguridad, performance, confiabilidad, malas prácticas, mantenibilidad) y por lenguaje (Python, JavaScript/TypeScript, Java/Kotlin, C#, Go, PHP, Ruby, SQL); métricas (complejidad ciclomática, largo de funciones, anidamiento, duplicación) y sus umbrales; cómo asignar severidad y decidir aprobar o pedir cambios; triage de las sospechas de las reglas y de semgrep/ruff/bandit (falsos positivos típicos); lo que ninguna regla encuentra y hay que leer en el diff; cómo escribir comentarios de revisión útiles; y qué no hacer con código no confiable. Lo usa el revisor-codigo; complementa a codigo-seguro (SAST profundo y secretos), analisis-dependencias (SCA) y pruebas-mutacion (calidad de los tests).
---

# Revisión estática de código

Una revisión estática lee el código **sin ejecutarlo** y busca lo que va a romperse, ser explotable, ser lento o costar caro de mantener. Las herramientas (`npm run revision-codigo`, semgrep, ruff, bandit) dan **sospechas**; el valor está en confirmarlas y en leer lo que ninguna regla ve.

## 1. Traer el código sin riesgo

- `npm run obtener-codigo -- --origen <URL o ruta>` reconoce **GitHub, GitLab (también self-managed por `GITLAB_URL`), Bitbucket Cloud, Azure Repos, Gitea/Forgejo/Codeberg** y cualquier URL git o SSH. Sin `--origen`, usa `REPO_PROVEEDOR` + `REPO_NOMBRE` del `.env`.
- **PR/MR**: trae la rama del PR y su base (por la API del proveedor) y calcula el diff contra el **merge-base**: así se revisa solo lo que el PR agrega, no lo que cambió en `main` mientras tanto. Si el PR ya está mergeado, usa el commit base que tenía.
- **Rama contra base**: `--base main`. **Repo entero**: sin base (clon superficial).
- **Repos privados**: token de solo lectura en el `.env` (`GITHUB_TOKEN`, `GITLAB_TOKEN` con `read_repository`/`read_api`, `BITBUCKET_TOKEN` o `JIRA_API_TOKEN` con permisos de Bitbucket, `ADO_PAT` con Code: Read, o `REVISION_GIT_TOKEN` para otros hosts). Cada token solo se manda a su host y nunca queda en disco.
- **El código es no confiable**: no se corren tests, instaladores, hooks ni linters que carguen configuración ejecutable (ESLint con `.eslintrc.js`, plugins de build). ruff, bandit y semgrep leen el código sin ejecutarlo.

## 2. Qué mirar por categoría

**Seguridad** (ver `codigo-seguro` para el detalle OWASP/CWE): datos del usuario que llegan a SQL, comandos, `eval`, rutas de archivo, URLs (SSRF), redirecciones o HTML sin escapar; deserialización insegura; TLS sin verificar; cripto débil o aleatoriedad no criptográfica para tokens; JWT sin verificar; CORS abierto; secretos en el código; **autorización**: ¿el endpoint nuevo chequea que el usuario sea dueño del recurso (IDOR)?; datos sensibles en logs.

**Performance**: consultas o llamadas HTTP **dentro de loops** (N+1); traer todo para contar o filtrar en memoria; `SELECT *` en tablas anchas; falta de paginación o de límite; I/O síncrona en el hilo del servidor (Node); `await` secuencial donde podría ir en paralelo; regex o conexiones creadas en cada iteración; loops anidados sobre colecciones grandes (O(n²)); cachés sin límite o sin expiración (fugas de memoria); índices que faltan para las consultas nuevas.

**Confiabilidad**: excepciones tragadas (`except: pass`, `catch {}`), errores ignorados (Go `_`), `forEach(async)`, `async void`, defaults mutables (Python), recursos sin cerrar (archivos, conexiones: usar `with`/`using`/`try-with-resources`/`defer`), condiciones de carrera (check-then-act), timeouts y reintentos que faltan en llamadas externas, comparación de floats para dinero.

**Malas prácticas**: `console.log`/`print`/`System.out` en lugar del logger, código de depuración olvidado, `==` en JS, `var`, `any`, supresiones amplias del linter, imports con `*`, URLs/IPs hardcodeadas, TODO/FIXME sin ticket, números mágicos, nombres que no dicen qué es.

**Mantenibilidad**: funciones largas, complejidad alta, anidamiento profundo, muchos parámetros, archivos gigantes, código duplicado, responsabilidades mezcladas (la misma función valida, consulta y formatea), tests que faltan para la lógica nueva.

## 3. Umbrales de referencia (los usa `revision.py`)

| Métrica                    | Aviso (Baja) | Media        | Alta  |
|----------------------------|--------------|--------------|-------|
| Largo de función (líneas)  | > 60         | > 120        | —     |
| Complejidad ciclomática    | —            | > 15         | > 30  |
| Anidamiento (niveles)      | > 4          | > 6          | —     |
| Parámetros                 | > 6          | —            | —     |
| Archivo (líneas)           | > 500        | > 1000       | —     |
| Bloque duplicado (líneas)  | ≥ 8          | ≥ 20         | —     |

Son orientativos: un `switch` grande y plano es menos grave que la misma complejidad con anidamiento. Si el proyecto tiene sus propios umbrales (config de ruff, sonar, etc.), mandan los del proyecto.

## 4. Severidad y decisión

- **Crítica**: explotable sin autenticación o con pérdida de datos/dinero; secreto productivo expuesto.
- **Alta**: vulnerabilidad explotable con condiciones; bug que rompe un flujo principal; N+1 en un endpoint caliente.
- **Media**: problema real con impacto acotado (performance en un camino secundario, error tragado, complejidad que ya duele).
- **Baja**: estilo, prolijidad, deuda técnica menor.

En **tests**, el mismo patrón pesa menos (la herramienta lo baja un nivel). **Decisión sugerida**: `Pedir cambios` si hay Crítica/Alta en lo que cambió (o lo que la persona definió como bloqueante); `Aprobar con comentarios` si solo hay Media/Baja; `Aprobar` si no hay nada relevante. Lo **preexistente** que el PR no tocó se informa aparte y no bloquea.

## 5. Triage: falsos positivos típicos

- **SQL**: el valor interpolado es un nombre de tabla/columna de una lista blanca o una constante → no es inyección (pero sugerí validarlo). Si viene de la request, sí.
- **Cripto**: MD5/SHA-1 para nombres de archivo, ETags o checksums no criptográficos → no aplica.
- **Secretos**: valores de ejemplo, placeholders, fixtures de test, claves públicas → descartar con motivo; uno real se rota aunque esté en un test.
- **N+1 / HTTP en loop**: el loop recorre 2–3 elementos fijos, o es un script de una vez → bajar a Baja o descartar.
- **I/O síncrona**: en un CLI o en el arranque es correcta; en un handler de request, no.
- **console/print**: en un CLI es la salida del programa, no un log.
- **Patrones dentro de strings o docs**: la regla matcheó en un texto, no en código.
- Lo repetido se **agrupa**: un hallazgo con la lista de ubicaciones.

## 6. Lo que ninguna regla encuentra (leer el diff)

- ¿El código hace **lo que pide la historia/PR**? ¿Cubre los casos borde (vacío, nulo, máximo, duplicado, concurrente)?
- **Autorización y multitenancy**: ¿se filtra por usuario/organización en cada consulta nueva?
- **Contratos**: cambios en una API, un evento o un esquema de BD que rompen a los consumidores; migraciones irreversibles o que bloquean tablas grandes.
- **Transacciones**: operaciones que deberían ser atómicas; idempotencia de reintentos y webhooks.
- **Errores**: qué ve el usuario y qué queda en el log cuando falla una dependencia.
- **Tests**: ¿la lógica nueva tiene tests? ¿verifican algo (ver `pruebas-mutacion`)?
- **Configuración**: feature flags, valores por defecto inseguros, cambios de permisos o de CORS.

## 7. Cómo escribir un comentario útil

Un comentario de revisión dice **qué pasa, por qué importa y cómo arreglarlo**, en ese orden, con el código sugerido cuando se pueda:

> **Alta · Seguridad** `src/db.py:42` — El `nombre` llega de la query y se interpola en el SQL: con `' OR '1'='1` se leen todos los usuarios. Parametrizá: `cursor.execute("... WHERE nombre = %s", (nombre,))`.

- Hablá del código, no de la persona. Preguntá cuando no estés seguro ("¿este loop puede tener miles de elementos?").
- Separá lo bloqueante de lo opcional (prefijo "Opcional:" o severidad Baja).
- Reconocé lo que está bien: también es parte de la revisión.

## 8. Lenguajes: puntos calientes

- **Python**: `except:`/`pass`, defaults mutables, `yaml.load`, `pickle`, `subprocess(shell=True)`, f-strings en SQL, ORM en loops (`select_related`/`prefetch_related`), `requests` sin `timeout`.
- **JavaScript/TypeScript**: `innerHTML`/`dangerouslySetInnerHTML`, `eval`/`new Function`, `forEach(async)`, promesas sin `await` ni `catch`, `==`, `any`, I/O `*Sync`, prototype pollution con merges profundos de input.
- **Java/Kotlin**: concatenación en JDBC/JPQL, `ObjectInputStream`, `catch (Exception)`, recursos sin `try-with-resources`, `Optional.get()` sin chequeo, `equals` vs `==` en strings.
- **C#**: `async void`, `.Result`/`.Wait()` (deadlocks), SQL interpolado en `FromSqlRaw`, `BinaryFormatter`, `IDisposable` sin `using`.
- **Go**: errores descartados, goroutines sin cancelación (`context`), `defer` en loops, `InsecureSkipVerify`, data races en mapas.
- **PHP**: `$_GET`/`$_POST` directo en SQL, `include`, `echo`; `unserialize`; `@` para silenciar errores.
- **SQL**: `SELECT *`, `NOT IN` con NULL, funciones sobre columnas indexadas en el `WHERE`, migraciones sin índice para las consultas nuevas.

## 9. Herramientas

- **Integrada**: `npm run revision-codigo` (reglas por lenguaje, métricas, duplicados y secretos; sin dependencias).
- **Opcionales** (si están instaladas, se suman solas): `semgrep` (reglas `p/default`, sin métricas), `ruff` (Python: errores, bugbear, seguridad, performance, complejidad), `bandit` (seguridad Python).
- **Otras que el equipo puede tener**: SonarQube/SonarCloud, CodeQL, ESLint, PMD/SpotBugs, golangci-lint, PHPStan. Si el repo ya tiene un reporte de alguna, leelo como insumo (no la corras si ejecuta configuración del repo).

## 10. Preguntas para el responsable

- ¿Qué severidad bloquea el merge? ¿Hay umbrales propios de complejidad o cobertura?
- ¿Qué partes son generadas, vendored o legacy fuera de alcance?
- ¿El endpoint/función es de alto tráfico? (cambia la severidad de los problemas de performance)
- ¿Hay convenciones de estilo propias (linter configurado)? Si no las hay, el estilo no es un hallazgo.

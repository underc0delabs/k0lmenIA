---
name: analisis-dependencias
description: "El cómo del análisis de dependencias (SCA): manifiestos y lockfiles por ecosistema, CVE/GHSA y CVSS, directas vs. transitivas, reachability, licencias copyleft, SBOM, cadena de suministro y priorización. Lo usa analista-dependencias; complementa a analista-seguridad y pentester-web."
---

# Análisis de dependencias (SCA)

La mayoría del código de un proyecto es de **terceros**. El SCA busca **vulnerabilidades conocidas (CVE)** y problemas de **licencia** en esas dependencias. Es **estático y de solo lectura**: no ejecuta la app ni la ataca (eso es DAST: `analista-seguridad`, `pentester-web`). Se corre sobre el repositorio de la aplicación (`REPO_RUTA_LOCAL`).

## 1. Ecosistemas y lockfiles

- Cada ecosistema tiene su manifiesto y su **lockfile** (la fuente de la verdad de qué versión está instalada): npm/yarn/pnpm (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`), Python (`requirements.txt`, `poetry.lock`), Maven/Gradle, Go (`go.sum`), Ruby (`Gemfile.lock`), PHP (`composer.lock`).
- El análisis se hace contra el **lockfile**, no solo el manifiesto: ahí están las versiones reales, incluidas las transitivas.

## 2. Directas vs. transitivas

- Una **directa** la elegiste vos; una **transitiva** vino arrastrada por otra. La mayoría de los CVE están en transitivas.
- Si la vulnerable es transitiva, el fix puede ser actualizar la **directa** que la trae, o un `override`/`resolution` para forzar la versión parcheada.

## 3. Severidad y priorización

- La severidad viene del **CVSS** (Crítica/Alta/Media/Baja). Pero no todo lo "crítico" es explotable en tu contexto: priorizá por **reachability** (¿el código vulnerable se usa?), si es accesible desde la red, y si hay exploit público.
- **Desactualizado ≠ vulnerable**: un paquete viejo sin CVE no es un bug; actualizarlo es un riesgo aparte (regresión). Reportá vulnerables, no solo viejos.
- **Fix disponible**: lo que se resuelve subiendo a una versión parcheada es prioritario (bajo costo).

## 4. Cadena de suministro

- **Dependency confusion**: un paquete interno con el mismo nombre que uno público puede ser suplantado.
- **Typosquatting**: nombres parecidos a paquetes populares.
- **Paquetes comprometidos** (un mantenedor hackeado, un postinstall malicioso): revisá cambios de mantenedor y scripts de instalación en dependencias nuevas.

## 5. Licencias

- Las licencias **copyleft** (GPL, AGPL, LGPL) pueden obligar a liberar tu código según cómo las uses; las permisivas (MIT, Apache-2.0, BSD) no. Marcá las que necesiten revisión legal, no las decidas vos.

## 6. SBOM

- Un **SBOM** (CycloneDX o SPDX) es el inventario de todo lo que compone el software; útil para auditar y para responder rápido ante un CVE nuevo (¿nos afecta?).

## 7. Herramientas

- `npm audit --json` (Node), `pip-audit` (Python), **`osv-scanner`** (multi-ecosistema, base OSV). La herramienta `k0lmenia dependencias` (`${CLAUDE_PLUGIN_ROOT}/herramientas/seguridad/dependencias.py`) corre las que estén y agrega por severidad.
- Automatizar el seguimiento con **Dependabot** o **Renovate** (PRs de actualización).

## 8. Falsos positivos y riesgo aceptado

- Un CVE puede no aplicar (no usás la función vulnerable, es solo de dev/test). Documentá el **riesgo aceptado** con el motivo y una **fecha de revisión** (como hace el `SECURITY.md` del propio repo), no lo borres y listo.

## 9. Preguntas típicas para el responsable

Cuando no está escrito, son `FI-XX`:

- ¿Cuál es el repositorio y la rama a analizar? ¿Hay lockfile?
- ¿Qué severidad mínima bloquea una release? ¿Hay SLA para parchear críticas?
- ¿Se permiten licencias copyleft? ¿Hay una lista de licencias aprobadas?
- ¿Las dependencias de dev/test entran en el alcance o solo las de producción?
- ¿Existe ya una política de riesgo aceptado o un SBOM?

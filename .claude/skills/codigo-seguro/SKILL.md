---
name: codigo-seguro
description: El cómo del SAST y la búsqueda de secretos — clases de bug en el código (inyección, XSS, deserialización, path traversal, SSRF, cripto débil, control de acceso), OWASP/CWE, semgrep, triage por explotabilidad, detección de secretos y la diferencia SAST vs. DAST. Lo usa analista-codigo-seguro; complementa a analista-seguridad, pentester-web y analisis-dependencias.
---

# Análisis estático de seguridad del código (SAST) y secretos

El SAST busca **bugs de seguridad en el código fuente** sin ejecutarlo, y la búsqueda de secretos encuentra **credenciales que no deberían estar en el repo**. Es estático y de solo lectura; lo que pasa con la app corriendo lo ven el `analista-seguridad` y el `pentester-web` (DAST). Se corre sobre el repositorio de la aplicación (`REPO_RUTA_LOCAL`).

## 1. Qué encuentra el SAST (clases de bug)

Mapeadas al **OWASP Top 10** y a **CWE**:

- **Inyección** (SQL, NoSQL, comandos del SO, LDAP): datos del usuario concatenados en una consulta o comando. Lo más grave y común.
- **XSS**: salida sin escapar en HTML/JS.
- **Deserialización insegura**, **XXE** (XML con entidades externas), **path traversal** (`../`), **SSRF** (URL controlada por el usuario que el servidor consulta).
- **Criptografía**: algoritmos débiles (MD5/SHA1 para contraseñas, DES), claves/IV hardcodeados, aleatoriedad no criptográfica (`Math.random` para tokens).
- **Autenticación y control de acceso** en el código: checks que faltan, comparación de contraseñas no constante.
- **Redirección abierta**, **inyección de logs**, **condiciones de carrera** (TOCTOU).

## 2. Secretos en el código

- Claves de nube (AWS `AKIA…`, Google `AIza…`), tokens (GitHub `ghp_…`, Slack `xox…`), claves privadas (`BEGIN PRIVATE KEY`), claves de pago (`sk_live_…`), JWT, y asignaciones tipo `password=…`, `api_key=…` en config.
- **Un secreto en el repo se considera comprometido**: hay que **rotarlo**, no solo borrarlo — y sacarlo del **histórico de git** (está en commits viejos). Guardarlos en un **vault**/variables de entorno, no en el código.
- La herramienta `npm run sast` (`herramientas/seguridad/sast.py`) trae un escáner de secretos integrado (siempre corre) y **redacta** el valor en la salida; nunca pongas el secreto completo en el informe.

## 3. Triage y priorización

- El SAST genera **falsos positivos**: cada hallazgo se confirma leyendo el código (¿el dato llega realmente sin sanitizar? ¿es código muerto, de test o de ejemplo?). Descartá los FP **con motivo**.
- Priorizá por **explotabilidad** (entrada controlable por el usuario, accesible desde la red) y severidad, no solo por lo que dice la regla.

## 4. Herramientas

- **semgrep** (`semgrep --config auto --json`): reglas por lenguaje y framework; severidad ERROR/WARNING/INFO. Es lo que usa `npm run sast` si está instalado.
- **gitleaks** / **trufflehog**: secretos (incluido el histórico de git).
- **CodeQL**: SAST profundo (GitHub), para análisis más exhaustivo.

## 5. SAST vs. DAST (qué NO ve cada uno)

- El **SAST** ve el código pero no el runtime: no sabe de configuración del servidor, headers, TLS, ni de cadenas de llamadas reales. 
- El **DAST** (ZAP, pentest) ve la app corriendo pero no el código. Se complementan: un hallazgo de SAST se **confirma** con DAST o con una prueba manual (`pentester-web`).

## 6. Preguntas típicas para el responsable

Cuando no está escrito, son `FI-XX`:

- ¿Cuál es el repositorio y la rama? ¿Qué lenguajes/frameworks?
- ¿Qué severidad bloquea una release? ¿Hay un SLA para secretos expuestos?
- ¿Hay partes del código fuera del alcance (generado, vendored, legacy)?
- ¿Usan ya semgrep/CodeQL en CI con alguna config propia?
- ¿Dónde deberían vivir los secretos (vault, variables de entorno, secret manager)?

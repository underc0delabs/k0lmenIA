# Contexto — [HU-XXX — Funcionalidad]

> Ficha de contexto armada antes de analizar, diseñar o automatizar las pruebas (skill `investigacion-contexto`).
> Reúne lo encontrado en todas las fuentes y registra **lo que falta** como `FI-XX`.
>
> _(Ejemplo orientativo sobre HU-001 — Inicio de sesión.)_

- **Historia:** PROJ-12 / HU-001 — Inicio de sesión
- **Actualizada en Jira:** 2026-10-05 14:20 · **Ficha generada:** 2026-10-08 10:15
- **Falta información:** 2 ítems abiertos (FI-01, FI-02)

## Fuentes consultadas

```
+-------------------+------------------------------+------------+----------------------------------------+
| Fuente            | Referencia                   | Estado     | Aporte                                 |
+===================+==============================+============+========================================+
| Historia          | PROJ-12                      | Consultada | Criterios CA1 a CA3                    |
+-------------------+------------------------------+------------+----------------------------------------+
| Comentarios       | 7 comentarios                | Consultada | Decisión sobre el bloqueo (ver abajo)  |
+-------------------+------------------------------+------------+----------------------------------------+
| Subtareas         | PROJ-13, PROJ-14             | Consultada | Validación de formato de email en      |
|                   |                              |            | backend                                |
+-------------------+------------------------------+------------+----------------------------------------+
| Épica             | PROJ-5 Autenticación         | Consultada | Regla de sesión de 30 minutos          |
+-------------------+------------------------------+------------+----------------------------------------+
| Issues vinculados | PROJ-40 (bug)                | Consultada | Bug conocido: el botón se habilita con |
|                   |                              |            | el email vacío                         |
+-------------------+------------------------------+------------+----------------------------------------+
| Confluence        | "Reglas de autenticación"    | Consultada | Política de contraseñas                |
+-------------------+------------------------------+------------+----------------------------------------+
| Figma             | Pantalla Login, frame 12:340 | Consultada | Textos de error de credenciales        |
+-------------------+------------------------------+------------+----------------------------------------+
| Contrato de API   | input/api/auth-endpoints.md  | Consultada | POST /login devuelve 401 y 423         |
+-------------------+------------------------------+------------+----------------------------------------+
```

## Resumen de la funcionalidad

Dos o tres líneas con qué hace la funcionalidad, quién la usa y el flujo principal, según las fuentes.

## Reglas y hallazgos por criterio

```
+------------+--------------------------------------+-----------------------------------------+
| Criterio   | Hallazgo                             | Fuente                                  |
+============+======================================+=========================================+
| CA1        | El login acepta email (no usuario) y | Historia                                |
|            | contraseña                           |                                         |
+------------+--------------------------------------+-----------------------------------------+
| CA2        | Mensaje: "Email o contraseña         | Figma, frame 12:340                     |
|            | incorrectos"                         |                                         |
+------------+--------------------------------------+-----------------------------------------+
| CA3        | Bloqueo tras 3 intentos fallidos     | Comentario de A. Pérez (PO), 2026-10-02 |
|            | consecutivos                         |                                         |
+------------+--------------------------------------+-----------------------------------------+
```

## Decisiones registradas en comentarios

- **2026-10-02 · A. Pérez (PO):** el contador de intentos se reinicia después de un login exitoso. Reemplaza lo que decía la descripción ("por sesión").

## Contradicciones

- La historia dice "bloqueo de 15 minutos" y la página de Confluence "Reglas de autenticación" dice 30 minutos. No hay una decisión posterior → registrado como FI-02.

## Falta información

```
+-------+----------------------------------------+------------------------------------------+---------------------------+------------------------------------------+----------+
| ID    | Qué falta                              | Dónde se buscó                           | Impacto                   | Pregunta para el PO                      | Estado   |
+=======+========================================+==========================================+===========================+==========================================+==========+
| FI-01 | Texto del mensaje al quedar la cuenta  | Historia, comentarios, Figma, Confluence | CA3 · casos de bloqueo    | ¿Cuál es el mensaje exacto al bloquearse | Abierto  |
|       | bloqueada                              |                                          |                           | la cuenta?                               |          |
+-------+----------------------------------------+------------------------------------------+---------------------------+------------------------------------------+----------+
| FI-02 | Duración del bloqueo (15 o 30 minutos) | Historia, Confluence                     | CA3 · casos de desbloqueo | ¿El bloqueo dura 15 o 30 minutos?        | Abierto  |
+-------+----------------------------------------+------------------------------------------+---------------------------+------------------------------------------+----------+
```

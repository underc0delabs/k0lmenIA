# API — Autenticación

**Base URL:** `https://api.qarmy-demo.ar/v1`

---

## POST /auth/login

Inicia sesión y devuelve un token.

**Request body** (JSON):

```json
{
  "email": "string (formato email)",
  "password": "string"
}
```

**Respuestas:**

```
+--------------------+-----------------------------------------------+-----------------------------+
| Status             | Cuerpo                                        | Cuándo                      |
+====================+===============================================+=============================+
| `200 OK`           | `{ "token": "string (JWT)", "expiresIn": 1800 | Credenciales válidas        |
|                    | }`                                            |                             |
+--------------------+-----------------------------------------------+-----------------------------+
| `400 Bad Request`  | `{ "error": "Email o contraseña con formato   | Body mal formado            |
|                    | inválido" }`                                  |                             |
+--------------------+-----------------------------------------------+-----------------------------+
| `401 Unauthorized` | `{ "error": "Credenciales incorrectas" }`     | Email/password no coinciden |
+--------------------+-----------------------------------------------+-----------------------------+
| `423 Locked`       | `{ "error": "Cuenta bloqueada por intentos    | 3 intentos fallidos         |
|                    | fallidos" }`                                  |                             |
+--------------------+-----------------------------------------------+-----------------------------+
```

---

## POST /auth/forgot-password

Solicita el envío de un enlace de recuperación.

**Request body** (JSON):

```json
{ "email": "string" }
```

**Respuestas:**

```
+-------------------+------------------------------------------------+----------------------------------------+
| Status            | Cuerpo                                         | Cuándo                                 |
+===================+================================================+========================================+
| `200 OK`          | `{ "message": "Si el email existe, se envió un | Siempre (no revela si el email existe) |
|                   | enlace" }`                                     |                                        |
+-------------------+------------------------------------------------+----------------------------------------+
| `400 Bad Request` | `{ "error": "Email con formato inválido" }`    | Email mal formado                      |
+-------------------+------------------------------------------------+----------------------------------------+
```

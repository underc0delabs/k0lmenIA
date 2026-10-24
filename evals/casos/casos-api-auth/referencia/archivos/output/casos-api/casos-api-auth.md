# Casos de API — autenticación (input/api/auth-endpoints.md)

| ID | Endpoint | Escenario | Código esperado |
|---|---|---|---|
| CP-API-001 | POST /auth/login | Credenciales válidas | 200 |
| CP-API-002 | POST /auth/login | Contraseña incorrecta | 401 |
| CP-API-003 | POST /auth/login | Body sin email | 400 |
| CP-API-004 | POST /auth/login | Email con formato inválido | 400 |
| CP-API-005 | POST /auth/login | Tercer intento fallido: la cuenta se bloquea | 423 |
| CP-API-006 | POST /auth/login | Login con la cuenta bloqueada | 423 |
| CP-API-007 | POST /auth/forgot-password | Email registrado | 200 |
| CP-API-008 | POST /auth/forgot-password | Email inexistente: misma respuesta, no revela si existe | 200 |
| CP-API-009 | POST /auth/forgot-password | Body vacío | 400 |

## CP-API-001 — Login válido

```json
{"email": "qa@test.com", "password": "Clave-Prueba-1"}
```

Respuesta esperada: 200 con el token.

## CP-API-005 — Bloqueo después de 3 intentos

Tres intentos fallidos seguidos bloquean la cuenta; el tercero responde 423.

```json
{"email": "qa@test.com", "password": "incorrecta"}
```

## CP-API-008 — Email inexistente

La respuesta es la misma que con un email registrado: no revela si el email existe.

```json
{"email": "no-registrado@test.com"}
```

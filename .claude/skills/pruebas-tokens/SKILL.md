---
name: pruebas-tokens
description: El cómo de probar tokens de auth (JWT, OAuth/OIDC, sesión, API keys) y la tokenización de pagos (PCI) — ciclo de vida, validación de firma y claims, ataques típicos (alg none, replay, scope ampliado) y manejo seguro. Lo usan probador-billeteras, pentester-web, probador-salesforce y quien pruebe login, sesiones o APIs autenticadas.
---

# Pruebas de tokens

"Token" abarca cosas distintas que se prueban distinto: **tokens de autenticación/autorización** (JWT, OAuth, sesión, API key) y **tokens de pago** (la tokenización de una tarjeta). Este skill cubre las dos, siempre sobre ambientes **propios o autorizados** y **sin datos reales**.

Regla transversal: **un token es un secreto**. No lo pegues entero en informes, capturas, logs ni en el chat; mostrá como mucho los primeros caracteres (`eyJ…`) y recomendá rotar cualquiera que aparezca expuesto. Los tokens de prueba van en el `.env` (gitignored), nunca commiteados.

## 1. JWT (JSON Web Token)

Un JWT tiene tres partes `header.payload.signature` en base64url. El header y el payload **se leen sin la clave** (no están cifrados, solo firmados): nunca metas datos sensibles en el payload.

Qué verificar:
- **Firma**: el servidor **rechaza** un token con la firma cambiada o ausente. Cambiá un byte de la firma y esperá 401.
- **`alg: none`**: tomá un token válido, poné `"alg":"none"` en el header, borrá la firma y probá: si lo acepta, es crítico (bypass total).
- **Confusión de algoritmo** (RS256 → HS256): si el server usa RSA (clave pública conocida), probar firmar un token HS256 usando la clave pública como secreto; si valida, es crítico.
- **Firma débil (HS256)**: si el secreto es corto o común, es fuerza bruta offline. No lo ejecutes salvo pentest autorizado; sí señalá el riesgo si el secreto se ve débil o está en el repo.
- **Claims**:
  - `exp` (expiración): un token vencido se rechaza; probá justo después de `exp`. ¿Hay tolerancia de reloj exagerada?
  - `nbf` / `iat`: token del futuro, token sin `iat`.
  - `iss` / `aud`: ¿valida emisor y audiencia? Un token de otro cliente/tenant no debería servir.
  - `sub` / `roles` / `scope`: cambiá el `sub` por otro usuario o agregá un rol/scope: si no revalida contra la firma, es escalamiento (IDOR por claim).
- **`kid`**: inyección por el `kid` (path traversal, SQL) para que valide con una clave que controlás; `jku`/`x5u` apuntando a un JWKS propio.
- **Expiración y refresh**: el access token dura poco; el refresh token rota al usarse (rotación) y se **invalida el anterior**. Reusar un refresh ya canjeado debe fallar y, idealmente, revocar la familia (detección de robo).
- **Logout y revocación**: después de cerrar sesión, el access token viejo no debería funcionar hasta su `exp` (si el server mantiene lista de revocados) — si no la mantiene, dejá constancia del riesgo.

## 2. OAuth 2.0 / OIDC

- **Flujo**: para apps y SPA, **Authorization Code + PKCE**; *implicit* y *password grant* están desaconsejados. Señalá si se usan.
- **`state`**: presente, aleatorio y verificado a la vuelta (anti-CSRF del login). Sin `state`, es vulnerable.
- **`redirect_uri`**: validación **exacta** (no por prefijo ni comodín). Probá un `redirect_uri` no registrado, uno con `@`, con `#`, con subdominio o path extra: deben rechazarse (open redirect / robo de código).
- **PKCE**: `code_verifier` obligatorio; un code sin verifier o con verifier equivocado se rechaza. El `code` es de un solo uso y expira rápido; reusarlo falla.
- **Scopes**: pedí un scope de más y verificá que el token no lo reciba; probá usar un token para un recurso fuera de su scope (debe dar 403).
- **Tokens**: dónde quedan (ver sección 4), expiración, refresh con rotación (sección 1). Para server-to-server, **Client Credentials** o **JWT bearer**.

## 3. Tokens de sesión y API keys

- **Sesión (cookie)**: la cookie de sesión lleva `HttpOnly`, `Secure` y `SameSite` adecuado; el ID es largo y aleatorio (no secuencial ni predecible). **Se renueva al iniciar sesión** (anti session-fixation: un ID previo no debe quedar válido autenticado). Expira por inactividad y por tiempo absoluto; logout la invalida **en el servidor** (no solo borra la cookie). Dos logins no deberían compartir el mismo token.
- **API keys**: viajan por header (`Authorization`), nunca en la URL (quedan en logs e historial); se pueden **rotar y revocar**; tienen scope/permisos acotados; hay rate limit. Una key revocada deja de funcionar al instante.
- **Fijación y reenvío (replay)**: un token capturado no debería servir desde otra IP/sesión si hay binding; probá reusarlo. Para operaciones sensibles, además, idempotencia (ver el skill `pruebas-billeteras`).

## 4. Manejo seguro (dónde se guarda y cómo viaja)

- **Transporte**: siempre HTTPS; el token nunca en la **URL** ni en parámetros de query; en el header `Authorization: Bearer` o en cookie segura.
- **Almacenamiento en el cliente**: `localStorage` es accesible por JavaScript (expuesto a XSS); para web, cookie `HttpOnly` es más segura para la sesión. Señalá tokens largos en `localStorage`.
- **Logs y errores**: el token no debe aparecer en logs de servidor, APM, mensajes de error ni analytics. Revisá respuestas de error y `analista-logs`.
- **Caché**: respuestas con token no cacheables (`Cache-Control: no-store`).
- **Exposición**: buscá tokens o secretos en el repo, en el bundle del frontend, en `.env.example` con valores reales, en archivos de Postman commiteados.

## 5. Tokenización de medios de pago (PCI-DSS)

Tokenizar = reemplazar el **PAN** (número de tarjeta) por un **token** que no sirve fuera de su contexto, para no guardar ni transmitir la tarjeta real.

- **Nunca uses tarjetas reales.** Usá las **tarjetas de prueba del proveedor** (Stripe, Mercado Pago, Adyen, PayPal, Braintree, etc.; cada uno publica sus números de test y su ambiente sandbox). Si aparece un PAN real en datos o logs, es un incidente: reportalo sin copiarlo.
- **El PAN no debe tocar tu backend**: con los SDK/iframe del proveedor (Stripe Elements, Checkout, campos hospedados), la tarjeta va del navegador al proveedor y vuelve un token. Verificá que tu servidor reciba **el token, no el PAN/CVV**.
- **El token no es la tarjeta**: no se puede "destokenizar" del lado del comercio; es de un solo proveedor y, a veces, de un solo comercio o uso.
- **Qué probar**: tokenizar una tarjeta de prueba y cobrar con el token; token inválido/vencido; reuso de un token de un solo uso; token de otro comercio (no debe servir); importes límite; moneda; 3-D Secure (SCA) cuando aplica; el PAN enmascarado se muestra como `**** 4242` y nunca completo; CVV **no se guarda** (PCI lo prohíbe).
- **Datos que nunca se guardan**: CVV/CVC, el PAN completo salvo cifrado y con alcance PCI, la banda/chip. Si la app los guarda o loguea, es hallazgo crítico.
- **Webhooks de pago**: la confirmación real llega por **webhook firmado** del proveedor; verificá la firma (no confíes en el `return_url`), idempotencia (el proveedor reintenta) y que un webhook falsificado se rechace.

## 6. Herramientas en k0lmenIA

- Diseñar los casos: `generador-casos-api` (incluye casos de autorización y de token). Ejecutar contra la API: `ejecutor-api` (Newman) con el token y la URL del `.env`. Automatizar: `api-mapper`.
- Decodificar un JWT para inspeccionar sus claims: hacelo **offline** (el header y el payload son base64url); no mandes el token a un decodificador online (se filtra).
- La parte activa (forjar tokens, `alg:none`, fuerza bruta) es de **pentest autorizado**: va con el `pentester-web`, solo con `PENTEST_AUTORIZADO=si` y sobre un sitio propio o con permiso escrito. Sin esa autorización, el análisis se queda en lo pasivo: revisar la configuración, los claims, el transporte y el almacenamiento.

## 7. Reglas

- **Solo ambientes propios o autorizados.** Forjar o atacar tokens de un sistema de terceros sin permiso no se hace.
- **Sin datos reales**: tarjetas de prueba del proveedor, usuarios de prueba, ambiente sandbox.
- **Los tokens son secretos**: del `.env`, nunca en el chat ni en el informe; los que aparezcan, recomendá rotarlos y mostralos truncados.
- Lo esperado sale de la historia, el estándar (RFC 7519 para JWT, OAuth 2.1, OWASP ASVS cap. 3 de sesiones) o la documentación del proveedor: si no está definido, es `Falta información`, no un supuesto.

---
name: setup
description: Setup inicial de k0lmenIA — pide la web principal del proyecto, la recorre, recomienda qué agentes y plugins (Pro, Empresa) le sirven, muestra checks para activar los planes a los que tiene acceso, los instala y configura k0lmenaTMT. Úsalo con /k0lmenia:setup o cuando pregunten qué plan les conviene.
---

# Setup de k0lmenIA: tu proyecto, tus planes y tus plugins

k0lmenIA se instala por partes: el **core** (`k0lmenia`, gratis) y, encima, un plugin por plan pago: **Pro**
(`k0lmenia-pro`) y **Empresa** (`k0lmenia-empresa`, que suma Pro). Cada plan pago vive en un repo privado de GitHub: quien
tiene acceso de lectura a ese repo puede instalarlo. Tu trabajo: entender qué proyecto prueba la persona, recomendarle qué
usar y dejarle activados los plugins que le corresponden.

Lo conducís vos en la conversación principal. Las preguntas van con la herramienta de preguntas.

## Paso 1 — La web principal

Pedí la URL de la web principal del proyecto que van a probar (una pregunta, texto libre). Si no tiene web (una API, una
app mobile, un sistema interno sin acceso), pedile que lo describa en una línea y saltá al paso 3 con eso.

## Paso 2 — Recorrerla

1. Corré `k0lmenia planes --recomendar <url> --json`. Lee la página principal (una sola petición, sin enviar nada) y
   devuelve las `senales` que vio (tienda, plataforma, login, pagos, chat, analytics, idiomas, video, app, SAP,
   Salesforce, cabeceras de seguridad…), los agentes `recomendados` con su `motivo` y `plan`, `por_plan`, el
   `plan_sugerido` y el estado de cada plan (`planes`: instalado, disponible, bloqueado o desconocido).
2. Si tenés el navegador de Playwright (`k0lmenia:playwright-headless`), abrí la URL y mirá la página como la ve una
   persona: qué hace el producto, si hay login, registro, carrito, búsqueda, formularios importantes, chat o app. Si la
   página lo bloquea o pide login, no insistas: alcanza con lo del punto 1. **Solo mirás**: no completes formularios, no
   inicies sesión y no hagas clic en nada que cambie datos.
3. Si `error` vino con algo (no se pudo leer), decíselo en una línea y seguí con lo que describa la persona.

## Paso 3 — Recomendar

En pocas líneas, en este orden:

- **Qué es su proyecto** (una línea, con lo que viste).
- **Lo que ya puede usar con el core**: los recomendados del plan gratis, con el motivo de cada uno.
- **Lo que suma cada plan pago para este proyecto**: los recomendados de Pro y de Empresa, con su motivo (no la lista
  completa del plan; para eso está `/k0lmenia:options`).
- **Plan sugerido**: `plan_sugerido`, y por qué en una línea.

## Paso 4 — Activar plugins (checks)

Mostrá una sola pregunta de **selección múltiple** ("¿Qué plugins activo?") con una opción por plan **disponible** (tiene
acceso y no está instalado). Marcá como recomendada la del plan sugerido. Cada opción dice qué suma para este proyecto.

- Los planes **instalados** no van como opción: decí que ya están activos (✅).
- Los planes **bloqueados** (sin acceso) no van como opción: listalos aparte con 🔒, su precio, qué sumarían para este
  proyecto y el link de `compra`.
- Si **no hay ninguno disponible**, no hagas la pregunta. Si además `github.credenciales` es `false` o el acceso salió
  `desconocido`, puede que sí tenga acceso pero falten las credenciales de GitHub en la PC. Explicale que lo resuelva en
  una terminal (lo corre la persona, no vos) y que vuelva a escribir `/k0lmenia:setup`:
  ```
  gh auth login
  gh auth setup-git
  ```
  Si ya pagó y sigue bloqueado, que le pase su usuario de GitHub (`github.usuario`) a Underc0de.

Por cada plan marcado, corré `k0lmenia planes --instalar <pro|empresa>` (Empresa ya trae Pro: si marcó los dos, alcanza
con Empresa). Instala el plugin desde el marketplace `k0lmenia` con sus dependencias. Si falla por permisos, volvé a la
explicación de credenciales. Nunca instales un plan que la persona no marcó.

Al terminar: que escriba `/reload-plugins` (o reinicie Claude Code) para ver los agentes nuevos, y que active la
actualización automática en `/plugin` → Marketplaces → `k0lmenia` → *Enable auto-update*.

## Paso 5 — k0lmenaTMT

k0lmenaTMT viene en todos los planes. Si `tmt.configurado` es `false` (en `k0lmenia planes --json --sin-red`), preguntá si
el equipo usa k0lmenaTMT para gestionar sus pruebas:

- **Sí**: la URL y el token se cargan en el `.env` (`K0LMENA_TMT_URL` y `K0LMENA_TMT_TOKEN`) con `k0lmenia configurar`, que
  lo corre **la persona en una terminal**. Nunca le pidas el token en el chat. Después, con su sí, corré
  `k0lmenia conector activar k0lmena-tmt` y decile que reinicie Claude Code.
- **No**: seguí. Xray funciona sin conector, por API.

## Paso 6 — Cierre

Una línea con lo que quedó activo y dos pedidos de ejemplo para **su** web, con sus propias palabras (por ejemplo,
*"Probá el checkout de https://… con una tarjeta de prueba"*). Si es la primera vez en esta carpeta, seguí con el skill
`empezar`. Para ver todo lo que trae cada plan: `/k0lmenia:options`.

## Reglas

- Mostrá los planes bloqueados una sola vez y sin insistir: es información, no una venta.
- Si la persona pide algo de un plan que no tiene, decile en qué plan está y que `/k0lmenia:setup` le muestra cómo
  sumarlo. No lo intentes con otro agente que no corresponde.
- Ninguna acción con efecto sin confirmación: instalar un plugin y activar un conector se confirman antes.
- En la web de la persona solo se mira: nada de formularios, login ni acciones.
- Todo en español, concreto.

---
name: setup
description: Setup inicial de k0lmenIA — pide la web principal del proyecto, la recorre, recomienda qué agentes le sirven (del core y de Pro), ofrece instalar Pro completo o solo los paquetes que necesita (seguridad, performance…) si tiene acceso, y configura k0lmenaTMT. Úsalo con /k0lmenia:setup o cuando pregunten qué plan les conviene.
---

# Setup de k0lmenIA: tu proyecto, tus planes y tus plugins

k0lmenIA se instala por partes: el **core** (`k0lmenia`, gratis) y, encima, el plugin privado **Pro**
(`k0lmenia-pro`). Pro vive en un repo privado de GitHub: quien tiene acceso de lectura a ese repo puede instalarlo. Tu
trabajo: entender qué proyecto prueba la persona, recomendarle qué usar y dejarle activado Pro si le corresponde.

Lo conducís vos en la conversación principal. Las preguntas van con la herramienta de preguntas.

## Paso 1 — La web principal

Pedí la URL de la web principal del proyecto que van a probar (una pregunta, texto libre). Si no tiene web (una API, una
app mobile, un sistema interno sin acceso), pedile que lo describa en una línea y saltá al paso 3 con eso.

## Paso 2 — Recorrerla

1. Corré `k0lmenia planes --recomendar <url> --json`. Lee la página principal (una sola petición, sin enviar nada) y
   devuelve las `senales` que vio (tienda, plataforma, login, pagos, chat, analytics, idiomas, video, app, SAP,
   Salesforce, cabeceras de seguridad…), los agentes `recomendados` con su `motivo`, `plan` y (los de Pro) `paquete`,
   `por_plan`, el `plan_sugerido`, los `paquetes_sugeridos` de Pro y el estado de cada plan (`planes`: instalado,
   disponible, bloqueado o desconocido; Pro trae además sus `paquetes`, cada uno con `instalado`).
2. Si tenés el navegador de Playwright (`k0lmenia:playwright-headless`), abrí la URL y mirá la página como la ve una
   persona: qué hace el producto, si hay login, registro, carrito, búsqueda, formularios importantes, chat o app. Si la
   página lo bloquea o pide login, no insistas: alcanza con lo del punto 1. **Solo mirás**: no completes formularios, no
   inicies sesión y no hagas clic en nada que cambie datos.
3. Si `error` vino con algo (no se pudo leer), decíselo en una línea y seguí con lo que describa la persona.

## Paso 3 — Recomendar

En pocas líneas, en este orden:

- **Qué es su proyecto** (una línea, con lo que viste).
- **Lo que ya puede usar con el core**: los recomendados del plan gratis, con el motivo de cada uno.
- **Solo si Pro está instalado o disponible** (`por_plan` lo trae): lo que suma Pro para este proyecto, agrupado por
  paquete, con su motivo (no la lista completa; para eso está `/k0lmenia:options`), y qué paquetes le sirven
  (`paquetes_sugeridos`), en una línea.

Pro es privado y no se vende: si la persona no lo tiene ni tiene acceso, **no lo menciones**.

## Paso 4 — Activar Pro (completo o por paquetes)

Pro se instala **completo** (todos los paquetes) o **por paquetes** (solo los que necesita: seguridad, performance…; cada
paquete suma la base de Pro sola). Según el estado de Pro en `planes`:

- **Disponible**, o **instalado** con paquetes que faltan (`completo` en `false`): una pregunta, "¿Qué instalo de
  K0lmenIA Pro?", con estas opciones:
  1. **Solo lo que te sirve** (recomendada si hay `paquetes_sugeridos`): nombrá esos paquetes y qué suma cada uno.
  2. **Todo Pro**: todos los paquetes.
  3. **Elijo los paquetes**: mostrá la lista de paquetes que faltan (id y en una línea qué trae) y que la persona
     escriba cuáles quiere.
  4. **Nada por ahora**.
  No ofrezcas los paquetes que ya están instalados (decí cuáles ya tiene, con ✅).
- **Instalado completo** (`completo` en `true`): no preguntes; decí que ya tiene todo Pro (✅).
- **Bloqueado** (sin acceso): no preguntes ni lo menciones; seguí con el paso 5.
- **Desconocido** (no se pudo revisar el acceso, por ejemplo con `github.credenciales` en `false`): no lo ofrezcas. Solo
  si la persona dice que le dieron acceso a Pro, explicale que cargue sus credenciales de GitHub en una terminal (lo
  corre la persona, no vos) y que vuelva a escribir `/k0lmenia:setup`:
  ```
  gh auth login
  gh auth setup-git
  ```
  Si sigue sin acceso, que le pase su usuario de GitHub (`github.usuario`) a quien le dio acceso.

Según lo que eligió, corré `k0lmenia planes --instalar pro` (todo) o `k0lmenia planes --instalar <id> <id>…` (los
paquetes elegidos, por ejemplo `--instalar seguridad performance`). Instala desde el marketplace `k0lmenia` con sus
dependencias. Si falla por permisos, volvé a la explicación de credenciales. Nunca instales nada que no eligió.

Si más adelante pide algo de un paquete que no tiene (un agente que sugiere seguir con otro de otro paquete, por ejemplo),
decile en qué paquete está y ofrecé instalarlo con `k0lmenia planes --instalar <id>`.

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

- Nada está a la venta: no hables de precios, compras ni planes a los que la persona no tiene acceso.
- Si la persona pide algo que no está en lo que tiene instalado, decile que no está incluido en su versión y ofrecé lo
  que sí se puede hacer. No lo intentes con otro agente que no corresponde.
- Ninguna acción con efecto sin confirmación: instalar un plugin y activar un conector se confirman antes.
- En la web de la persona solo se mira: nada de formularios, login ni acciones.
- Todo en español, concreto.

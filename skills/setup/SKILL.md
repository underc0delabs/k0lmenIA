---
name: setup
description: Muestra qué plan de k0lmenIA tiene la persona, a qué planes tiene acceso (Pro, Empresa) y qué suma cada uno, instala los que le corresponden y configura k0lmenaTMT. Úsalo con /k0lmenia:setup o cuando pregunte por los planes.
---

# Setup de k0lmenIA: planes y plugins

k0lmenIA se instala por partes: el **core** (`k0lmenia`, gratis) y, encima, un plugin por plan pago: **Pro**
(`k0lmenia-pro`) y **Empresa** (`k0lmenia-empresa`, que suma Pro). Cada plan pago vive en un repo privado de GitHub: quien
tiene acceso de lectura a ese repo puede instalarlo. Tu trabajo es mostrarle a la persona qué tiene, qué puede instalar ya
y qué sumaría cada plan, e instalar lo que elija.

Lo conducís vos en la conversación principal. Las preguntas van con la herramienta de preguntas, con la opción
recomendada primero.

## Paso 1 — Revisar el acceso

Corré `k0lmenia planes --json`. Para cada plan trae: `instalado`, `acceso` (`si`, `no` o `desconocido`), `precio`,
`resumen`, los conteos de agentes y skills, los `conectores`, las herramientas de `gestion` y unos `destacados`. En
`github` dice si hay credenciales de GitHub en la PC y con qué usuario.

## Paso 2 — Mostrarlo

Una tabla corta, un plan por fila, en este orden:

| Estado | Qué significa |
|---|---|
| ✅ instalado | ya lo tiene |
| ⬇️ disponible | tiene acceso y no lo instaló: ofrecé instalarlo |
| 🔒 bloqueado | no tiene acceso: mostrá el precio, el resumen y 4 o 5 destacados, y el link de `compra` |

Si `acceso` es `desconocido` o todos los pagos salen bloqueados y `github.credenciales` es `false`, puede que sí tenga
acceso pero falten las credenciales de GitHub en la PC. Explicale que lo resuelva en una terminal (lo corre la persona,
no vos):

```
gh auth login
gh auth setup-git
```

y que vuelva a escribir `/k0lmenia:setup`. Si ya pagó y sigue bloqueado, que le pase su usuario de GitHub (el de
`github.usuario`) a Underc0de.

## Paso 3 — Instalar lo disponible

Si hay planes disponibles, preguntá cuáles instalar (Empresa ya trae Pro: si tiene acceso a Empresa, ofrecé ese). Con el
sí de la persona, corré por cada uno:

```
k0lmenia planes --instalar <pro|empresa>
```

Instala el plugin del plan desde el marketplace `k0lmenia` (y sus dependencias). Al terminar, decile que escriba
`/reload-plugins` (o que reinicie Claude Code) para que aparezcan los agentes nuevos, y que active la actualización
automática en `/plugin` → Marketplaces → `k0lmenia` → *Enable auto-update*.

Si la instalación falla por permisos, volvé al paso 2 (credenciales). Nunca instales un plan sin el sí de la persona.

## Paso 4 — k0lmenaTMT

k0lmenaTMT viene en todos los planes. Si `tmt.configurado` es `false`, preguntá si el equipo usa k0lmenaTMT para
gestionar sus pruebas:

- **Sí**: el token se carga en el `.env` (`K0LMENA_TMT_URL` y `K0LMENA_TMT_TOKEN`) con `k0lmenia configurar`, que lo corre
  **la persona en una terminal**. Nunca le pidas el token en el chat. Después, con su sí, corré
  `k0lmenia conector activar k0lmena-tmt` y decile que reinicie Claude Code.
- **No**: seguí. Xray funciona sin conector, por API.

## Paso 5 — Cierre

Una línea con lo que quedó instalado y otra con qué puede pedir ahora (si instaló un plan, dos ejemplos de lo que suma,
con sus propias palabras y sin nombrar agentes). Si es la primera vez que usa k0lmenIA en esta carpeta, seguí con el
skill `empezar`.

## Reglas

- Mostrá los planes bloqueados una sola vez y sin insistir: es información, no una venta.
- Si la persona pide algo que es de un plan que no tiene, decile en qué plan está y que `/k0lmenia:setup` le muestra cómo
  sumarlo. No lo intentes con otro agente que no corresponde.
- Ninguna acción con efecto sin confirmación: instalar un plugin y activar un conector se confirman antes.
- Todo en español, concreto.

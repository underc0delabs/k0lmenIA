---
name: pruebas-billeteras
description: El cómo de probar billeteras y medios de pago — ledger de doble entrada, estados de transacción, idempotencia, doble gasto, conciliación, KYC/AML, webhooks firmados y 3-D Secure/SCA. Usa el skill pruebas-tokens para la seguridad de tokens. Lo usan probador-billeteras y los generadores de casos cuando hay dinero.
---

# Pruebas de billeteras virtuales y pagos

Cuando una app maneja **dinero**, un bug no es una molestia: es plata que aparece o desaparece. La regla madre es **la plata no se crea ni se destruye**: toda operación conserva el total del sistema. Todo lo de tokens y tokenización de tarjetas está en el skill `pruebas-tokens`.

**Siempre en ambiente de prueba / sandbox, con dinero y tarjetas de prueba. Nunca movimientos reales ni datos reales de personas.**

## 1. Saldo y libro mayor (ledger)

Una billetera seria no guarda "un número de saldo" que se suma y resta: lleva un **libro mayor de doble entrada** (cada movimiento es un asiento con débito y crédito que suman cero) y el saldo es la **suma de los asientos**. Qué verificar:

- **Invariante de conservación**: antes y después de cualquier operación entre cuentas, la suma de todos los saldos del sistema (incluidas las cuentas internas: pasarela, comisiones, suspenso) es la misma. Un P2P de A a B: A baja X, B sube X, total igual.
- **Saldo = suma del ledger**: el saldo que muestra la app coincide con la suma de los movimientos. Si hay un campo de saldo "cacheado", que no se desincronice (verificalo con el `verificador-datos` por SQL de solo lectura).
- **Sin saldos negativos** salvo que el producto lo permita (línea de crédito): intentar gastar más de lo disponible se rechaza.
- **Fondos en tránsito / retenciones (holds)**: un pago autorizado pero no capturado retiene saldo; el disponible baja aunque el contable no. Probá disponible vs. contable.
- **Precisión**: el dinero se guarda en **enteros de la unidad mínima** (centavos) o decimal exacto, **nunca en float** (0.1 + 0.2 ≠ 0.3). Probá importes que exponen redondeo: dividir, porcentajes de comisión, conversión de moneda. El redondeo tiene una regla definida (a favor de quién) y se aplica siempre igual.

## 2. Transacciones y sus estados

Operaciones típicas: **carga/top-up** (entra dinero), **retiro/cash-out**, **P2P** (entre usuarios), **pago** a un comercio, **reversa/refund**, **contracargo/chargeback**.

- **Máquina de estados**: `pendiente → autorizada → capturada/completada`, con ramas `rechazada`, `expirada`, `revertida`, `en disputa`. Probá cada transición válida y, sobre todo, las **inválidas**: capturar algo ya revertido, revertir algo pendiente, pagar dos veces la misma orden. Un estado final no cambia.
- **Autorización vs. captura**: una autorización puede capturarse parcial o expirar sin capturar (libera el hold). Probá captura parcial, doble captura y captura después de expirar.
- **Reversa/refund**: total y parcial; no se reembolsa más de lo cobrado; el refund vuelve al mismo medio; refund de un pago ya reembolsado falla.
- **Comisiones e impuestos**: se calculan sobre el monto correcto, se asientan en la cuenta correcta y se reflejan en lo que recibe cada parte.

## 3. Idempotencia y reintentos

En pagos, la red falla: el cliente reintenta y no debe cobrar dos veces.

- **Clave de idempotencia**: la operación de cobro/transferencia acepta una `Idempotency-Key`; repetir la **misma** request con la misma clave devuelve el **mismo** resultado sin ejecutar de nuevo (un solo asiento). Probá: mandá la misma request 2-3 veces con la misma clave → un solo movimiento; con claves distintas → se procesa cada una.
- **Timeout y respuesta perdida**: simulá que la respuesta se pierde después de ejecutar (el `probador-resiliencia` ayuda); el reintento no debe duplicar.
- **Webhooks**: el proveedor reintenta el webhook; procesarlo dos veces no debe acreditar dos veces (idempotencia por ID de evento). Verificá la firma del webhook (ver `pruebas-tokens`).

## 4. Concurrencia y doble gasto

- **Doble gasto**: con saldo para **una** operación, disparar **dos en paralelo** (dos retiros, un retiro y un pago) → una sola prospera, la otra se rechaza por fondos; nunca las dos. Es la prueba estrella: se hace con requests concurrentes (no secuenciales).
- **Condiciones de carrera**: aplicar dos veces el mismo cupón, canjear dos veces un voucher, usar el mismo código de un solo uso; registrar dos operaciones sobre el mismo hold.
- **Bloqueos**: el sistema serializa por cuenta (lock optimista/pesimista); un deadlock o un `lock timeout` bajo carga es un hallazgo. La carga real la arma el `performance-mapper`; acá, concurrencia acotada para detectar el doble gasto.
- **Consistencia eventual**: si el acreditado es asíncrono (cola), definí la ventana esperada y verificá que al final cuadre; que un fallo a mitad no deje dinero en el limbo (saga/compensación).

## 5. Límites, cupos y reglas de negocio

- **Límites**: por operación, diarios, mensuales, por saldo máximo de la billetera (muchas e-money tienen tope regulatorio), por cantidad de operaciones. Probá justo en el límite, uno arriba y acumulando durante el período.
- **Mínimos**: monto mínimo de carga/retiro; cero y negativos rechazados.
- **Cuentas no verificadas**: una billetera sin KYC completo suele tener límites más bajos o no poder retirar. Probá qué puede hacer cada nivel de verificación.
- **Expiración de fondos / promociones**: saldo promocional que vence o no se puede retirar, separado del saldo real.

## 6. KYC / AML y antifraude

- **KYC (onboarding)**: alta con documento, validación de identidad, estados (pendiente, aprobado, rechazado, requiere revisión); qué habilita cada estado. Datos de prueba, nunca documentos reales.
- **AML**: operaciones que deberían **marcarse** (montos altos, fraccionamiento/structuring, destinos de riesgo, velocidad inusual) generan alerta o retención; verificá que la regla dispare y que la operación quede retenida, no completada.
- **Antifraude**: dispositivo nuevo, IP de otro país, muchos intentos, tarjeta probada en varias cuentas (card testing) → fricción (OTP, bloqueo). No generes patrones de fraude reales contra terceros; probá contra el sandbox.
- **Listas y sanciones**: un beneficiario en lista debe bloquearse (si el producto lo contempla).

## 7. Conciliación

- **Contra el proveedor de pagos**: lo que la billetera registra tiene que cuadrar con lo que informa la pasarela (Stripe, Mercado Pago, Adyen…). Tomá el reporte/settlement del sandbox y comparalo con los movimientos de la billetera: montos, comisiones, fechas, estados; buscá diferencias, duplicados y faltantes.
- **Cuentas de suspenso**: dinero en estados intermedios (autorizado, en disputa, pendiente de liquidación) debe estar en una cuenta de suspenso y resolverse; nada queda huérfano.
- **Contracargos**: un chargeback del sandbox debita al comercio, cambia el estado y concilia.

## 8. Dinero en la interfaz

- **Formato**: separador de miles y decimales según la configuración regional; símbolo de moneda correcto; signo de débito/crédito claro; el `analista-traductor` ayuda con formatos por idioma.
- **Consistencia**: el mismo importe se ve igual en el listado, el detalle, el comprobante, el correo (`verificador-correos`) y el PDF. El comprobante no se puede alterar.
- **Estados a la vista**: la persona entiende si un pago está pendiente, completado o rechazado; un pago pendiente no se muestra como completado.
- **Resiliencia**: si la pasarela cae o tarda, la interfaz no deja a la persona sin saber si pagó o no (doble clic en "Pagar" no cobra dos veces → idempotencia del front también). Lo cubre el `probador-resiliencia`.

## 9. Bugs típicos del dinero (para buscarlos a propósito)

- Redondeo que "gana" centavos en cada operación (salami).
- Doble acreditación por reintento o webhook repetido (falta idempotencia).
- Saldo negativo o gasto por encima del disponible por condición de carrera.
- Importe o moneda que cambian entre pantallas o entre front y back.
- Refund mayor al cobro, o doble refund.
- Comisión calculada sobre el monto equivocado o asentada en la cuenta equivocada.
- Transacción que queda "pendiente" para siempre (sin timeout ni compensación).
- Límite que se puede superar con operaciones en paralelo.
- CVV o PAN guardados/logueados (ver `pruebas-tokens`).

## 10. Herramientas en k0lmenIA

- Casos de la API de pagos/billetera: `generador-casos-api` (positivos, negativos, autorización, idempotencia). Correrlos: `ejecutor-api` (Newman); automatizarlos y correr lo concurrente: `api-mapper` / k0lmena. Carga y estrés: `performance-mapper`.
- Verificar saldos y asientos en la base: `verificador-datos` (SQL de **solo lectura**; nunca ajustar saldos a mano para "arreglar" una prueba).
- Resiliencia (pasarela caída, respuesta perdida, doble clic): `probador-resiliencia`. Correos y comprobantes: `verificador-correos`. Seguridad de tokens y webhooks: skill `pruebas-tokens` y, para la parte activa autorizada, `pentester-web`.

## 11. Reglas

- **Solo sandbox**, con **dinero y tarjetas de prueba** del proveedor; nunca movimientos ni datos reales.
- **No “arregles” datos**: no edites saldos ni estados en la base para que una prueba pase; eso oculta el bug.
- Lo esperado (límites, comisiones, redondeo, qué habilita cada nivel de KYC) sale de la historia, las reglas de negocio o la regulación aplicable: si no está definido, es `Falta información`, no un supuesto.
- **Sin datos personales ni secretos** en informes y capturas; importes y tarjetas, siempre de prueba.

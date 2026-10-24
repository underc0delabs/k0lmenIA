---
name: pruebas-soap
description: El cómo de probar servicios SOAP — el WSDL, el sobre (Envelope/Header/Body), SOAPAction, 1.1 vs. 1.2, el XSD, SOAP Faults, namespaces, WS-Security, mustUnderstand y compatibilidad del contrato — armando el sobre y enviándolo con el ejecutor-api. Lo usa el probador-soap; complementa a los agentes de API.
---

# Pruebas de servicios SOAP

SOAP es un contrato **fuerte y basado en XML**: el **WSDL** define exactamente las operaciones, los tipos y los errores. A diferencia de REST, casi todo se valida contra el **esquema (XSD)**, y los errores de negocio viajan como **SOAP Faults**, no como códigos HTTP. Se complementa con `tecnicas-de-diseno` y con los agentes de API para la parte de transporte.

## 1. El WSDL

- Define **operaciones** (portType/binding), sus **mensajes** de entrada/salida, el **endpoint** (address location) y el **SOAPAction** de cada operación.
- La herramienta `npm run soap` (`herramientas/soap/wsdl.py`) lo relevа: servicio, endpoint, versión (1.1/1.2) y operaciones, y genera un **sobre de ejemplo** por operación.
- Un WSDL que no carga, con tipos rotos o endpoints que apuntan a otro ambiente, es un hallazgo antes de probar.

## 2. El sobre SOAP

- **Envelope → Header + Body**. El Body lleva la operación y sus parámetros; el Header, metadatos (seguridad, direccionamiento).
- **SOAP 1.1 vs. 1.2**: cambia el namespace del Envelope, el content-type (`text/xml` vs. `application/soap+xml`) y cómo se manda el SOAPAction. Confirmá la versión.
- **Namespaces y prefijos**: tienen que coincidir con el WSDL; un namespace mal puesto hace fallar la operación aunque el XML "se vea bien".

## 3. Validación contra el esquema (XSD)

- El **request** debe cumplir el XSD: tipos correctos, campos obligatorios (minOccurs), `nillable`, enumeraciones, longitudes, orden de los elementos (sequence).
- Probá con **valores inválidos** (tipo equivocado, fuera de rango, campo obligatorio ausente, enumeración inexistente, fecha mal): el servicio debe rechazar con un Fault claro, no con un 500 genérico.
- El **response** también debe cumplir el esquema; un response que no valida es un bug del servicio.

## 4. SOAP Faults (manejo de errores)

- Los errores van como **Fault**: en 1.1 `faultcode`/`faultstring`/`detail`; en 1.2 `Code`/`Reason`/`Detail`.
- Cada error de negocio esperado (no encontrado, no autorizado, validación) debe devolver un **Fault con el código y el detalle correctos**, no un HTTP 500 pelado ni un 200 con un mensaje de error escondido.
- Probá la diferencia entre **fault de cliente** (datos mal) y **de servidor** (error interno).

## 5. Seguridad (WS-Security)

- **WS-Security UsernameToken** (usuario/clave en el header, con nonce y timestamp), **firma** (XML Signature) y **cifrado** (XML Encryption).
- **Timestamp/nonce** contra replay: un mensaje viejo o repetido debe rechazarse.
- `mustUnderstand="1"` en un header: si el servicio no lo entiende, debe fallar, no ignorarlo.
- **Transporte**: TLS; credenciales no en la URL; un endpoint sin seguridad que debería tenerla es hallazgo.

## 6. Tipos, arrays y adjuntos

- **Arrays/colecciones** (maxOccurs), objetos anidados, tipos complejos y `xsi:nil`; bordes: lista vacía, un elemento, muchos.
- **MTOM/attachments** si maneja archivos binarios.

## 7. Contrato y compatibilidad

- **Versionado**: un cambio en el WSDL/XSD no debe romper a los clientes viejos (agregar un campo opcional está bien; sacar uno o cambiar un tipo rompe).
- **Idempotencia**: reenviar la misma operación de escritura, ¿duplica? (sobre todo sin WS-ReliableMessaging).

## 8. Automatizar

- Relevá el WSDL con `npm run soap`, tomá el sobre de ejemplo, completá los parámetros y **envialo por HTTP POST** con el `ejecutor-api` (una colección de Postman/Newman con el XML en el body, el `Content-Type` correcto y el header `SOAPAction`).
- Validá la respuesta: que sea el XML esperado, que cumpla el esquema y que los Faults aparezcan cuando corresponde. Para suites grandes, SoapUI es una alternativa.
- Datos de prueba: un valor válido, uno inválido por tipo, uno con un obligatorio ausente, uno que dispare cada Fault.

## 9. Bugs típicos de SOAP

- Error de negocio devuelto como **HTTP 500** o como 200 con mensaje, en vez de un **SOAP Fault** bien formado.
- Request válido rechazado por un **namespace/prefijo** mal, o por el orden de los elementos (sequence).
- El servicio **no valida** el request contra el XSD y procesa datos inválidos.
- `mustUnderstand` ignorado; timestamp/nonce sin chequear (replay).
- Un response que **no cumple** su propio esquema.
- Endpoint del WSDL apuntando a otro ambiente; WSDL que no carga.
- Operación de escritura **no idempotente** que duplica al reenviar.

## 10. Preguntas típicas para el PO (SOAP)

Cuando no está escrito, son `FI-XX`:

- ¿Dónde está el WSDL y cuál es el endpoint de QA? ¿SOAP 1.1 o 1.2?
- ¿Qué seguridad usa (WS-Security UsernameToken, firma, solo TLS)?
- ¿Qué operaciones entran en el alcance y cuáles tienen efecto (escritura)?
- ¿Qué Faults define cada operación y cuándo deben dispararse?
- ¿Hay versionado del contrato y clientes viejos a mantener compatibles?

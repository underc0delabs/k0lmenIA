---
name: pruebas-sap
description: El cómo de probar SAP — SAP GUI (Scripting API) y Fiori/UI5 (OData), mandantes y transportes, S/4HANA vs. ECC, autorizaciones y roles (PFCG, SoD), procesos end-to-end (O2C, P2P, R2R), jobs e IDocs, rendimiento y seguridad. Lo usan probador-sap y los mappers.
---

# Pruebas en SAP

SAP se prueba en **dos frentes**: el **SAP GUI for Windows** (las transacciones clásicas por código, los "T-codes") y **Fiori/UI5** (las apps web del launchpad). Casi todo proceso de negocio cruza los dos, autorizaciones y datos maestros. Se prueba siempre contra un **mandante (client) de QA**, nunca productivo.

## 1. Ambientes y mandantes

- Un sistema SAP tiene un **SID** (p. ej. `DQ1`) y varios **mandantes** (clients, p. ej. 100). El paisaje típico es **DEV → QAS → PRD** y los cambios viajan por **transportes (TR)**. Se prueba en QAS (o un mandante de QA), con datos de prueba.
- **S/4HANA vs. ECC**: en S/4HANA el back-office tiene mucho Fiori y cambian tablas y transacciones (p. ej. el modelo de datos de finanzas, materiales de 40 caracteres). Confirmá la versión: cambia qué y cómo se prueba.
- **Cuándo se dispara una regresión**: después de **importar un transporte**, aplicar un **support package**, un **upgrade** o una **conversión a S/4HANA**. Ahí se corre la regresión de los procesos críticos (§9).
- El **número de transporte** y el mandante son parte de la trazabilidad del bug.

## 2. SAP GUI for Windows

- Se navega por **T-codes** en el campo de comandos (`/n<tcode>` para ir, `/o<tcode>` para una sesión nueva). Las transacciones clave dependen del módulo (SD, MM, FI/CO, PP, HCM…).
- **Mensajes de la barra de estado**: SAP responde con mensajes de tipo **S** (éxito), **W** (warning), **E** (error) y **A** (abort). El tipo y el número del mensaje (p. ej. `VL 561`) son la verificación objetiva de un paso.
- **Variantes de transacción y layouts**: una misma transacción puede verse distinta por variante, layout de ALV o parametrización del usuario; probá con la variante que usa el negocio.
- **SAP GUI Scripting** (la API de automatización por COM) requiere estar habilitado en el **servidor** (RZ11 `sapgui/user_scripting = TRUE`) y en el **cliente** (Opciones → Accesibilidad y scripting). La herramienta `k0lmenia sap` (`${CLAUDE_PLUGIN_ROOT}/herramientas/sap/sap_gui.py`) releva en solo lectura el sistema, el mandante, el usuario y la transacción de las sesiones abiertas.
- El **Script Recording & Playback** del propio SAP GUI genera un script base; el agente lo adapta. Los **ids de los campos** del GUI (`wnd[0]/usr/ctxt...`) son estables entre corridas pero cambian entre versiones de la transacción.

## 3. Fiori / UI5

- El **Fiori Launchpad** muestra **tiles** agrupados en **catálogos** y **grupos**, asignados por rol. Un tile que no aparece suele ser un tema de rol/catálogo, no un bug de la app.
- Las apps Fiori son **UI5** (web) y consumen **servicios OData** (`/sap/opu/odata/...` o `/sap/opu/odata4/...`). Se automatizan como web con Playwright; los servicios OData, con el `ejecutor-api` (metadata `$metadata`, `$filter`, `$expand`, `$batch`).
- Tipos de app: **transaccionales** (crear/editar), **analíticas** (KPIs, Smart Business) y **listas de hechos**. Los **Smart Controls** (SmartTable, SmartFilterBar) generan campos según los metadatos de OData.
- **Launchpad y navegación cruzada**: una app navega a otra por *semantic object + action*; probá que el enlace lleve con el parámetro correcto.

## 4. Autorizaciones y roles

- Los permisos se arman con **roles (PFCG)** compuestos de **objetos de autorización** (p. ej. `V_VBAK_VKO` con actividad 01/02/03). Los usuarios (**SU01**) tienen roles.
- **SU53** muestra el último fallo de autorización del usuario: es la evidencia de "me faltó un permiso". **SUIM** busca quién tiene qué.
- Probá **por rol**: que cada rol pueda hacer lo que le toca y **no** lo que no (acceso por T-code y por objeto; en Fiori, qué tiles ve). Un rol de QA no debería traer permisos de más.
- **Segregación de funciones (SoD)**: combinaciones peligrosas (p. ej. crear un proveedor **y** pagarle) no deberían recaer en un mismo usuario. Es un hallazgo de seguridad.

## 5. Procesos de negocio (de punta a punta)

Lo que más valor tiene es el proceso completo, no la transacción suelta:

- **Order to Cash (O2C/SD)**: pedido de ventas (VA01) → entrega (VL01N) → picking/WM → factura (VF01) → contabilización. Verificá stock, precios, impuestos y los documentos contables.
- **Procure to Pay (P2P/MM)**: solicitud de pedido (ME51N) → pedido (ME21N) → entrada de mercadería (MIGO) → factura (MIRO) → pago (F110). Tres vías: pedido, recepción y factura.
- **Record to Report (R2R/FI-CO)**: asientos, cierres, conciliaciones, reportes.
- Cada paso deja un **documento** (número de documento) y afecta stock, contabilidad o ambos; la cuenta tiene que cerrar entre módulos.

## 6. Datos maestros y de prueba

- **Datos maestros**: materiales (MM01), clientes/proveedores (Business Partner, BP), cuentas, centros, organizaciones de ventas/compras. Un dato maestro incompleto frena el proceso aguas abajo.
- Usá datos de prueba del **mandante de QA** (prefijo `QA-` donde se pueda) y anotá los documentos creados para rastrearlos.
- **Fechas y períodos contables**: muchos errores salen por período cerrado o fecha fuera de rango.

## 7. Procesos de fondo e interfaces

- **Jobs de fondo (SM37)**: que se programen, corran y terminen sin cancelar; revisá el log (spool).
- **IDocs (WE02/WE05)**: estado 53 (ok), 51 (error de aplicación), 02/30 (no enviado); reprocesamiento (BD87).
- **Colas qRFC/tRFC (SMQ1/SMQ2, SM58)**: entradas atascadas = interfaces que no procesaron.
- **BAPIs y RFC**: si el flujo llama una BAPI, probá commit/rollback y el manejo de errores.

## 8. Smoke test

Rápido y bloqueante, en el mandante de QA:

1. Login al SAP GUI y a Fiori con un usuario de prueba.
2. Abrir una transacción clave del alcance (p. ej. VA03 en modo visualización) sin dump.
3. El launchpad de Fiori carga y los tiles del rol aparecen.
4. SAP GUI Scripting está habilitado (si se va a automatizar el GUI).
5. No hay **dumps ST22** recientes del usuario ni errores a la vista.

## 9. Regresión

- Después de un **transporte, support package, upgrade o conversión a S/4HANA**: correr los **procesos críticos** de punta a punta (O2C y P2P como mínimo), las transacciones y apps que toca el cambio, y los reportes clave, verificando los documentos y los importes.
- Lo ideal es tenerlo automatizado (SAP GUI Scripting para el GUI y Playwright para Fiori, vía `web-mapper` y `k0lmenia test`), para repetir la regresión sin tokens después de cada transporte.
- Revisá **dumps nuevos (ST22)** y **mensajes de error** tras el cambio.

## 10. Rendimiento

- **Tiempos de respuesta** por transacción y por app Fiori; **ST03** (workload del sistema), **ST05** (SQL trace), **SAT/SE30** (trace de ABAP) y **SM50/SM66** (procesos de trabajo) muestran dónde se va el tiempo.
- En **Fiori**, además, los CWV y la latencia de los servicios OData (`auditor-rendimiento-web` y, para carga, `performance-mapper` con `guia-performance`).
- Ojo con reportes/listados que traen millones de filas sin filtro y con jobs que se pisan en el horario pico.

## 11. Seguridad

El escaneo y la explotación los hacen el `analista-seguridad` y el `pentester-web`; propio de SAP:

- **Roles de mínimo privilegio** y **segregación de funciones (SoD)**: combinaciones peligrosas separadas.
- **SAP GUI Scripting**: habilitarlo baja una barrera de seguridad; en productivo suele restringirse. Confirmá que en QA es intencional.
- **RFC y usuarios de comunicación/servicio**: con permisos acotados, no `SAP_ALL`; destinos RFC (SM59) sin credenciales de más.
- **Usuarios estándar** (SAP*, DDIC) con contraseña por defecto = hallazgo.
- **PII y datos sensibles** en pantallas, descargas (listas a Excel) y logs; **enmascarado** donde corresponda.
- En **Fiori/OData**: que un servicio no exponga datos sin autorización y que no haya IDOR por el id de la entidad.

## 12. Automatizar

- **SAP GUI**: con la **Scripting API** (COM) desde Python (`win32com`) o el lenguaje que use k0lmena; navegá por ids de campo (`wnd[0]/usr/...`), mandá el T-code por el campo de comandos y verificá el **tipo y número del mensaje** de la barra de estado, no solo el texto.
- **Fiori**: con Playwright MCP (skill `ejecucion-e2e`); esperá las respuestas OData antes de leer la UI; los ids de UI5 son largos y cambian, ubicá por rol y texto.
- **OData**: con el `ejecutor-api` (colección sobre `/sap/opu/odata/...`, con `$metadata`, `$filter`, `$batch` y CSRF token).
- Probá siempre sobre el **mandante de QA**; nunca automatices escritura contra productivo.

## 13. Bugs típicos de SAP

- Un **dump ST22** (error de runtime ABAP) al ejecutar una transacción tras un transporte.
- Falta de **autorización** (SU53) en un rol que debería poder hacer el paso.
- El proceso frena por un **dato maestro** incompleto o un **período contable** cerrado.
- Importes o impuestos que no cierran entre SD, MM y FI.
- Un **IDoc en 51** o una **cola RFC atascada**: la interfaz no procesó.
- Un **job** que cancela o no se programa.
- En **Fiori**, un **tile que no aparece** por catálogo/rol, o una app que falla por un servicio OData sin autorización.
- **SoD**: un usuario que puede crear proveedor y pagarle.
- Variante de transacción distinta a la del negocio que oculta campos obligatorios.

## 14. Preguntas típicas para el PO (SAP)

Cuando no está escrito, son `FI-XX`:

- ¿Es S/4HANA o ECC? ¿Qué release?
- ¿Qué procesos entran en el alcance (O2C, P2P, R2R…) y hasta qué paso?
- ¿Sobre qué sistema y mandante se prueba (nunca productivo)? ¿Con qué usuarios y roles?
- ¿El GUI Scripting está habilitado en QA para automatizar?
- ¿Qué apps Fiori y qué servicios OData están en el alcance?
- ¿Qué datos maestros de prueba hay y quién los crea?
- ¿La prueba cubre autorizaciones/SoD, rendimiento o solo funcional?

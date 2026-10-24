---
name: pruebas-salesforce
description: El cómo de probar Salesforce (Sales, Service, Experience, CPQ) — sandboxes, acceso (perfiles, permission sets, OWD, sharing, FLS), automatización (validaciones, flows, Apex, límites de gobierno, bulk 200), datos, UI Lightning con Playwright, tests de Apex y releases. Lo usan probador-salesforce y los mappers.
---

# Pruebas en Salesforce

Salesforce no es "una web más": casi todo lo que hay que probar es **configuración** (quién ve qué, qué se valida, qué se automatiza) y cambia por **perfil**, **record type** y **datos**. Este skill dice qué mirar y cómo probarlo sin romper nada.

## 1. Ambientes: nunca en producción

```
+-----------------+------------------------------+----------------------------------------------+
| Org             | Datos                        | Para qué                                     |
+=================+==============================+==============================================+
| Developer /     | Sin datos (solo metadata)    | Pruebas de configuración y Apex con datos de |
| Developer Pro   |                              | prueba propios                               |
+-----------------+------------------------------+----------------------------------------------+
| Partial Copy    | Muestra de producción        | QA funcional e integración                   |
+-----------------+------------------------------+----------------------------------------------+
| Full            | Copia completa de producción | UAT, performance, ensayo de release (ojo:    |
|                 |                              | puede tener datos personales reales)         |
+-----------------+------------------------------+----------------------------------------------+
| Scratch org     | Vacía, efímera               | Desarrollo y CI                              |
+-----------------+------------------------------+----------------------------------------------+
| Producción      | Reales                       | **No se prueba.** Solo lectura y con permiso |
|                 |                              | explícito                                    |
+-----------------+------------------------------+----------------------------------------------+
```

- El login de sandbox es por `https://test.salesforce.com` (o el My Domain `--<sandbox>.sandbox.my.salesforce.com`). Si una URL no dice `sandbox`, `test` o `scratch`, **verificá** que no sea producción (`Organization.IsSandbox`).
- Después de un **refresh** del sandbox: los datos vuelven a los de producción (o vacíos), los usuarios de prueba pueden perder permisos y la **entrega de correo queda en "Solo correo del sistema"** (Setup → Deliverability). Si un correo no llega en sandbox, revisá eso antes de reportar un bug.
- En un **Full** o **Partial Copy** puede haber datos personales reales: no los copies en reportes ni capturas (enmascará o recortá). Si la org usa **Data Mask**, preguntá si se aplicó.

## 2. Acceso: lo que más se rompe

El acceso se evalúa en capas; un usuario ve un dato solo si **todas** lo permiten:

1. **Objeto** (CRUD: leer, crear, editar, borrar, ver todo, modificar todo) — perfil + permission sets + permission set groups.
2. **Campo** (FLS: visible / solo lectura) — mismo origen. Un campo oculto por FLS **no aparece** en la página, en reportes ni en la API para ese usuario.
3. **Registro** — OWD (acceso por defecto: `Private`, `Read`, `ReadWrite`, `ControlledByParent`), jerarquía de roles, sharing rules (por dueño o por criterio), equipos (de cuenta/oportunidad), sharing manual, Apex managed sharing, territorios.
4. **Interfaz** — page layouts y Dynamic Forms por perfil/record type, Lightning App Builder (visibilidad de componentes), botones y acciones por layout, pestañas y apps visibles.

Cómo probarlo:
- **Un usuario de prueba por perfil relevante** (no uses tu admin para probar permisos: el admin ve todo). Pedí que existan o que se creen en el sandbox (eso es una acción con efecto: se confirma).
- Matriz **perfil × objeto × acción** y **perfil × campo sensible** (sueldos, documentos, datos de tarjeta, notas internas). El `probador-permisos` arma la matriz rol × ruta; acá se completa con lo propio de Salesforce (FLS y sharing).
- Sharing: con un usuario que **no es dueño** ni está arriba en la jerarquía, intentar ver/editar un registro ajeno, por la interfaz, por URL directa (`/lightning/r/<Objeto>/<Id>/view`), por búsqueda global, por reportes y por la API.
- **Login As** (Iniciar sesión como) solo si el admin lo habilitó y te lo autorizaron; si no, usuarios de prueba con su propia sesión.
- Experience Cloud (portales): el **usuario invitado** (guest) y los usuarios externos tienen su propio OWD externo y sharing sets; es una fuente clásica de exposición de datos. Probá sin sesión qué ve el invitado.

## 3. Automatización: validaciones, flows y Apex

**Orden de ejecución al guardar** (simplificado): reglas de validación de sistema → before-save flows → before triggers → reglas de validación custom → duplicados → guardado → after triggers → assignment/auto-response → (workflow/process builder legados) → after-save flows → roll-ups → commit → acciones post-commit (correos, eventos, `@future`/queueable). Consecuencias para probar:
- Un **before-save flow** puede cambiar un valor antes de que lo vea la validación: probá el efecto combinado, no cada pieza aislada.
- Las acciones **asíncronas** (correos, `@future`, queueable, platform events, flows programados) no están al terminar el guardado: **esperá y reconsultá** (polling con tope), no fijes un "esperar 5 segundos".
- Varios **triggers en el mismo objeto** no tienen orden garantizado: si hay más de uno, probá combinaciones.

**Reglas de validación**: por cada regla activa, un caso que la **rompe** (mensaje exacto y en qué campo aparece, o arriba del formulario) y uno que la **cumple** justo en el borde. Probalas también por **API e importación** (las integraciones también las disparan) y con el **usuario de integración** (a veces se excluye por perfil: confirmá si es intencional).

**Flows**: por cada flow activo, cada camino de decisión; los disparados por registro, en creación, edición y (si aplica) borrado; los de pantalla, con datos válidos e inválidos, y el botón *Anterior*; los programados, con su condición de entrada. **Process Builder y Workflow Rules están retirados** (fin de soporte 2025-12-31): si siguen activos, es un riesgo y su migración a Flow necesita regresión.

**Límites de gobierno** (por transacción, Apex síncrono): 100 consultas SOQL, 150 DML, 50.000 filas consultadas, 10.000 filas en DML, 10 s de CPU, 6 MB de heap (asíncrono: 200 SOQL, 60 s de CPU, 12 MB). Se rompen con **volumen**, no con un registro:
- **Bulk de 200**: insertar/actualizar 200 registros de una vez (Data Loader, `sf data import`, la API Bulk o una lista con edición masiva) es la prueba que encuentra SOQL o DML dentro de un `for`. Es una carga de datos: se confirma y solo en sandbox.
- Errores típicos: `System.LimitException: Too many SOQL queries: 101`, `Apex CPU time limit exceeded`, `UNABLE_TO_LOCK_ROW` (concurrencia), `FIELD_CUSTOM_VALIDATION_EXCEPTION` (una regla bloqueó), `INSUFFICIENT_ACCESS_OR_READONLY` (sharing), `ENTITY_IS_LOCKED` (en aprobación).

**Tests de Apex**: Salesforce exige **75 % de cobertura** en toda la org para desplegar a producción y que cada trigger tenga algo de cobertura. Cobertura alta no es calidad: mirá que los tests **afirmen** algo (`System.assert*`) y no usen `SeeAllData=true`. Correrlos (`sf apex run test --test-level RunLocalTests --code-coverage`) no deja datos, pero consume límites asíncronos: en sandbox y con confirmación.

## 4. Datos

- **Record types**: cada uno puede tener su layout, sus valores de picklist y sus validaciones. Probá cada flujo con **cada record type** y el record type por defecto de cada perfil.
- **Picklists**: dependientes (controlador → dependiente), valores inactivos que siguen en registros viejos, **API name vs. etiqueta** (las integraciones mandan el API name; la interfaz muestra la etiqueta, traducida si hay Translation Workbench).
- **Relaciones**: lookup (opcional, sin borrado en cascada) vs. master-detail (obligatorio, borrado en cascada, sharing heredado, roll-ups). Borrar un padre en master-detail borra los hijos: probalo **solo** con datos propios.
- **Duplicados**: reglas y matching rules (bloquear o avisar), también por API e importación.
- **Multimoneda** y **zona horaria**: montos con la moneda del registro vs. la corporativa, tasas fechadas; fechas/horas se guardan en UTC y se muestran en la zona del **usuario** (un caso clásico: un `Date` que cambia de día para usuarios en otra zona).
- **Fórmulas y roll-ups**: recalculan en lectura (fórmulas) o al guardar el hijo (roll-ups); probá el borde (nulos, división por cero, redondeo).
- **Datos de prueba**: creados por vos y marcados (un prefijo `QA-` en el nombre), sin datos personales reales. Verificá en la base con SOQL de **solo lectura** (`sf data query` o la herramienta `run_soql_query` del conector `salesforce`), nunca modificando registros por la API para "acomodar" una prueba.

## 5. Interfaz Lightning con Playwright

- **Shadow DOM**: los componentes LWC encapsulan su DOM. Playwright atraviesa el shadow DOM con `getByRole`, `getByLabel`, `getByText` y CSS (no con XPath). Preferí siempre rol + nombre accesible (`getByRole('button', { name: 'Guardar' })`, `getByLabel('Nombre de la cuenta')`).
- **IDs dinámicos**: `input-123`, `combobox-456` cambian en cada carga: **nunca** los uses como locator. Tampoco las clases `slds-*` solas (son de estilo, se repiten).
- **Esperas**: esperá que desaparezca el spinner (`lightning-spinner`) y que aparezca el **toast** de confirmación (`role="status"` / `role="alert"` con el texto esperado) antes de seguir; las related lists y los componentes se cargan perezosamente al hacer scroll.
- **Combobox y lookups**: el picklist de Lightning no es un `<select>`: click en el combobox → opción por rol `option`. Los lookups buscan al tipear: esperá el resultado y elegilo por su texto.
- **Navegación**: preferí la URL directa (`/lightning/o/Account/new`, `/lightning/r/Account/<Id>/view`) a recorrer menús. En apps de consola, cada registro abre una **pestaña** (subtab): cerrá las que abriste.
- **Login**: con MFA, no automatices el login; usá la sesión guardada (`k0lmenia login` en k0lmena) del usuario de prueba. Cada perfil, su propia sesión guardada.
- **Idioma y formato**: la interfaz depende del idioma y la configuración regional del **usuario**; fijalos en los usuarios de prueba para que los textos esperados no cambien.
- **Classic**: si la org todavía usa Salesforce Classic para algún perfil, es otra interfaz: probala aparte o confirmá que no se usa.

## 6. APIs e integraciones

- APIs: REST (`/services/data/vXX.X/`), SOAP, **Bulk API 2.0** (volumen), Composite (varias operaciones en una), GraphQL, Streaming (**Platform Events**, **Change Data Capture**). El usuario de integración tiene su propio perfil: probá con **ese** usuario, no con un admin.
- Autenticación: Connected App / External Client App con OAuth (JWT bearer para integraciones de servidor). Los tokens van en el `.env`, nunca en el chat (ver el skill `pruebas-tokens`).
- Callouts salientes: **Named Credentials**; en sandbox deben apuntar a los **sandboxes** de los terceros (verificalo: un sandbox llamando a la pasarela de pagos de producción es un incidente).
- Integraciones típicas: ERP, pasarela de pagos, firma digital, middleware (MuleSoft), marketing (Marketing Cloud, Account Engagement). Por cada una: alta, modificación, error del tercero (timeout, 500), reintento e idempotencia (no duplicar el registro si el tercero reintenta).
- Para diseñar los casos de API usá `generador-casos-api`; para correrlos, `ejecutor-api`; para automatizarlos, `api-mapper`.

## 7. Releases y regresión

- Salesforce publica **tres releases al año** (Spring, Summer, Winter). Unas semanas antes, los **sandboxes de preview** reciben la nueva versión: es la ventana para correr la regresión y detectar cambios de comportamiento antes que producción.
- **Release Updates** (actualizaciones críticas) se activan solas en una fecha: listalas y probalas activadas en sandbox.
- Despliegues propios: `sf project deploy validate` (check-only) corre los tests sin desplegar; un deploy que falla por cobertura o por un test es un hallazgo. El QA **no despliega**: lo pide.
- Regresión mínima por release: login por perfil, los flujos principales (lead → conversión → oportunidad → cierre; caso → asignación → resolución), las validaciones y flows tocados, las integraciones y los reportes/dashboards clave.

## 8. Por nube (chequeos rápidos)

- **Sales Cloud**: conversión de lead (mapeo de campos, duplicados), etapas de oportunidad y probabilidad, productos y listas de precios, forecasting, cotizaciones.
- **Service Cloud**: creación de casos por canal (email-to-case, web-to-case, chat), reglas de asignación y escalamiento, entitlements y milestones (tiempos de SLA en horario hábil), Omni-Channel, base de conocimiento.
- **Experience Cloud**: usuario invitado, registro y login de externos, sharing sets, qué ve cada tipo de licencia, SEO y páginas públicas.
- **CPQ / Revenue Cloud**: reglas de precio y producto, descuentos por volumen, aprobaciones, generación del documento de cotización, redondeos.
- **Reportes y dashboards**: el resultado depende del usuario que lo ve (o del "running user" fijo del dashboard): probá con perfiles distintos y verificá que no expongan datos por un running user con más acceso.

## 9. Bugs típicos de Salesforce (para no confundirlos)

- *"El campo no aparece"* → FLS o layout del perfil/record type, no un bug de la página.
- *"No llega el correo"* → deliverability del sandbox, plantilla con campos sin acceso, o es asíncrono.
- *"Funciona con un registro y falla con 200"* → límites de gobierno: **es** un bug (de Apex o del flow).
- *"Falla a veces"* → `UNABLE_TO_LOCK_ROW` (dos procesos sobre el mismo registro), recálculo de sharing o asincronía.
- *"El dato es otro en la API"* → API name vs. etiqueta, moneda, zona horaria.
- *"Al admin le anda"* → el admin tiene *Modify All Data*: reproducilo con el perfil real.

## 10. Reglas

- **Solo sandboxes autorizados** (`SALESFORCE_ORGS_AUTORIZADAS`), nunca producción salvo lectura con permiso explícito.
- **Nada de metadata**: no despliegues, no cambies configuración (validaciones, flows, perfiles, sharing), no asignes permisos. Si para probar hace falta un cambio, se **pide** al admin.
- **Crear o modificar datos** (por interfaz, API o importación) es una acción con efecto: se confirma, se hace con datos `QA-` propios y en sandbox.
- **Sin datos personales ni secretos** en informes, capturas o casos.

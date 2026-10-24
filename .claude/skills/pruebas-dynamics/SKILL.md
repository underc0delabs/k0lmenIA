---
name: pruebas-dynamics
description: El cómo de probar Dynamics 365 y otros CRM/ERP de bajo código — entornos y soluciones, seguridad (roles, unidades de negocio, column security), lógica (business rules, flows, plugins, BPF, roll-ups), formularios, la Web API de Dataverse y procesos end-to-end. Lo usa el probador-dynamics.
---

# Pruebas de Microsoft Dynamics 365 (y otros CRM/ERP)

Dynamics 365 es una plataforma **de bajo código sobre Dataverse**: casi todo (tablas, reglas, flujos, formularios, roles) se **configura**, y ahí están los bugs. Se prueba en un **entorno no productivo (sandbox)**, por rol, siguiendo los procesos de negocio. El mismo enfoque vale para otros CRM/ERP; Salesforce y SAP ya tienen sus propios skills (`pruebas-salesforce`, `pruebas-sap`).

## 1. Entornos y soluciones

- **Dataverse** es la base. Se prueba en un **sandbox** (copia), nunca en producción.
- Los cambios viajan como **soluciones** (managed/unmanaged): verificá que una solución importada no rompa nada y que las dependencias estén.
- Confirmá la **app** (model-driven o Canvas/Power App) y los módulos en alcance (Sales, Customer Service, Field Service, Finance & Operations…).

## 2. Seguridad y acceso

- **Roles de seguridad** + **unidades de negocio** + **equipos**: definen qué ve y hace cada usuario, con alcance (propio, unidad de negocio, toda la organización).
- **Column (field) security** para campos sensibles.
- Probá **por rol**: que cada uno pueda hacer lo suyo y **no** lo ajeno (crear/leer/editar/borrar por tabla, y por registro según el alcance); acceso directo por URL a un registro de otra unidad.

## 3. Modelo de datos

- **Tablas/entidades**, columnas (tipos, requeridas, choices/option sets), **relaciones** (1:N, N:N) y comportamientos de borrado en cascada.
- **Duplicados** (reglas de detección), **auditoría** (qué cambios se registran).

## 4. Lógica de negocio

- **Business rules** (en el formulario: mostrar/ocultar, requerir, calcular), **reglas de validación**.
- **Business Process Flows** (las etapas guiadas de un proceso): que avancen según las condiciones.
- **Power Automate flows**, **plugins** y **workflows** (lógica en el servidor): que se disparen en el evento correcto, una sola vez, y con el resultado esperado; orden de ejecución.
- **Cálculos y roll-ups** (campos calculados y de acumulación): que den el valor correcto y se actualicen cuando deben.

## 5. Formularios, vistas y apps

- **Formularios** por tabla y por rol (campos visibles/requeridos), **vistas** (filtros, columnas, orden), **tableros**.
- **Canvas/Power Apps**: fórmulas (Power Fx), conexión a datos, comportamiento offline si aplica.

## 6. API de Dataverse (relevamiento de solo lectura)

- La **Web API** (OData v4) permite relevar tablas, columnas y metadata en solo lectura; **FetchXML** para consultas. Útil para entender el modelo antes de probar; sin escrituras.

## 7. Procesos de negocio (punta a punta)

- **Sales**: lead → calificar → oportunidad → cotización → pedido → factura; precios y listas de precios, descuentos.
- **Customer Service**: caso → cola → asignación → **SLA** (que el reloj corra y escale) → resolución; derechos (entitlements).
- **Field Service / Finance & Operations** según el alcance.
- Cada proceso cruza roles, lógica y datos: que el estado y los campos cierren en cada etapa.

## 8. Automatizar

- La UI model-driven y las Canvas Apps se prueban en el navegador con **Playwright** (por rol); ubicá por rol/nombre accesible (los IDs generados cambian).
- El modelo y los datos, con la **Web API** de Dataverse en lectura; los correos/notificaciones con el `verificador-correos`; los permisos con el `probador-permisos`.

## 9. Otros CRM/ERP

El patrón se repite: **entorno no productivo**, **roles/perfiles**, **lógica de negocio** (reglas, flujos, triggers), **procesos end-to-end** y **API de lectura** para relevar. Aplica a Oracle, NetSuite, Zoho, Odoo, HubSpot y similares (Salesforce y SAP tienen skill propio). Confirmá cuál es y adaptá los nombres de los artefactos.

## 10. Bugs típicos de Dynamics/CRM-ERP

- Un rol que ve o edita registros que no debería (alcance mal configurado).
- Una business rule o un plugin que no se dispara, o se dispara dos veces.
- Business Process Flow que avanza sin cumplir la condición de la etapa.
- Roll-up o campo calculado que no se actualiza.
- SLA que no corre o no escala.
- Solución importada que rompe un formulario o deja dependencias faltantes.
- Regla de duplicados que no detecta (o bloquea de más).
- Campo con column security visible para quien no debería.

## 11. Preguntas típicas para el PO (Dynamics/CRM-ERP)

Cuando no está escrito, son `FI-XX`:

- ¿Qué CRM/ERP y qué módulos entran (Sales, Customer Service, F&O…)?
- ¿Sobre qué entorno/sandbox se prueba (nunca producción)? ¿Con qué roles?
- ¿Qué procesos de negocio de punta a punta hay que cubrir?
- ¿Qué lógica es crítica (plugins, flows, BPF, roll-ups) y cuándo debe dispararse?
- ¿Hay SLAs y cómo deben comportarse?
- ¿Model-driven, Canvas App o portal?

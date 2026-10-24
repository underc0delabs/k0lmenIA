# Salesforce (CLI sf)

Herramienta de QA para orgs de Salesforce. La usa el agente `probador-salesforce`.

- **`inventario.py`** — releva en **solo lectura** una org **autorizada** (sandbox): la organización (sandbox vs. producción), perfiles y usuarios activos por perfil, permission sets, record types, reglas de validación, flows (y los Process Builder que quedaron activos), triggers de Apex, cobertura de Apex, modelo de sharing (OWD) de los objetos, reglas de duplicados, procesos de aprobación y límites de la org. Calcula hallazgos (cobertura < 75 %, Process Builder activos, varios triggers por objeto, OWD abiertos, reglas inactivas, límites casi agotados) y sugerencias de prueba (un negativo por validación, bulk de 200 por trigger, flows por camino, acceso por perfil, record types). Con `--apex` corre además los tests de Apex locales con cobertura. Deja `salesforce.json` e `informe-salesforce.html` (`scripts/generar_informe_salesforce.py`) en `output/salesforce/<historia o alias>/`.

## Requisitos

- **Salesforce CLI (`sf`)** en el PATH: `npm install --global @salesforce/cli` (el `npm run doctor` avisa si falta).
- La org **autorizada localmente** antes de usarla:
  ```bash
  sf org login web --alias mi-sandbox-qa --instance-url https://test.salesforce.com
  ```

## Uso

```bash
# Inventario de solo lectura:
npm run salesforce -- --org mi-sandbox-qa --historia HU-010 --confirmar
# Objetos puntuales para el modelo de sharing:
npm run salesforce -- --org mi-sandbox-qa --objetos Account,Opportunity,Pedido__c --confirmar
# Además, correr los tests de Apex con cobertura (solo en sandbox):
npm run salesforce -- --org mi-sandbox-qa --apex --confirmar
```

## Autorización y alcance

- **Solo orgs de `SALESFORCE_ORGS_AUTORIZADAS`** del `.env` (alias separados por coma). `SALESFORCE_ORG` es la org por defecto.
- **Nunca producción**: la herramienta detecta `Organization.IsSandbox` y corta. Relevar una org de producción en solo lectura exige `--permitir-produccion` **y** autorización explícita; aun así, sin `--apex`.
- Es de **solo lectura**: las consultas SOQL van por archivo a `sf data query`. **No** crea, edita ni borra registros, metadata, usuarios ni permisos. Correr los tests de Apex (`--apex`) no deja datos pero consume límites asíncronos; por eso se confirma.

El conector MCP **`salesforce`** (SOQL de solo lectura y `run_apex_test`) lo activa cada persona con `npm run conector -- activar salesforce`.

# SAP

Relevamiento de **solo lectura** de una sesión de SAP GUI for Windows por la **Scripting API** (COM). Lo usa el agente `probador-sap` como smoke/relevamiento antes de automatizar los flujos.

- **`sap_gui.py`** (`npm run sap`) — se conecta al SAP GUI ya abierto, lista conexiones y sesiones, y de cada una el sistema (SID), mandante, usuario, idioma, transacción y programa actuales, más métricas (round trips, tiempo de respuesta). Confirma que el Scripting esté habilitado y a qué sistema estás conectado.

```bash
npm run sap -- --salida output/sap/relevamiento.json
```

Solo lectura: no ejecuta transacciones ni cambia datos. La automatización de los flujos (SAP GUI Scripting, Playwright para Fiori, OData con el ejecutor-api) la arma el `probador-sap`.

**Requisitos**: Windows, SAP GUI for Windows, `pip install pywin32`, y el Scripting habilitado en el servidor (RZ11 `sapgui/user_scripting = TRUE`) y en el cliente (Opciones → Accesibilidad y scripting → Scripting). Siempre contra un **mandante de QA**, nunca productivo.

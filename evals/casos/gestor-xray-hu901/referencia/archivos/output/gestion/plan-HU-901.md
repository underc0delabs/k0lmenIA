# Plan de subida a Xray Cloud · HU-901

Corrida **en seco** (`--dry-run`): no se creó nada en Xray ni en Jira y no se escribió la trazabilidad.

- Proyecto: PROJ · Herramienta: xray-cloud
- Carpeta: `HU-901 Registro` (se crea)
- Historia de Jira: PROJ-12 (cada caso se vincula como *Test*)
- Trazabilidad: `output/gestion/HU-901-xray-cloud.json` (se escribe al ejecutar de verdad)

| Caso | Título | Tiempo | Etiquetas |
|---|---|---|---|
| CP-001 | Registro con todos los datos válidos | 5,5 min | positivo, regresion |
| CP-002 | Largo del usuario en los límites | 5,5 min | borde, regresion |
| CP-003 | Email con formato inválido | 5 min | negativo, regresion |
| CP-004 | Nombre con apóstrofe | 4,5 min | positivo, regresion |
| CP-005 | Email ya registrado | 5,5 min | negativo, falta-info, FI-01 |
| CP-006 | Persona de 17 años | 4,5 min | borde, falta-info, FI-02 |
| CP-007 | Contraseña débil | 4,5 min | negativo, falta-info, FI-03 |

Total estimado (scripts/estimacion.py): 35 min.

CP-005, CP-006 y CP-007 dependen de FI-01, FI-02 y FI-03: se suben con la etiqueta `falta-info` y quedan fuera de la regresión hasta que se respondan.

## Para ejecutarlo

Con tu confirmación corro el mismo comando sin `--dry-run`:

```bash
python scripts/gestion/gestion.py subir-casos --origen output/casos-de-prueba/bdd/HU-901-registro.feature --carpeta "HU-901 Registro" --historia PROJ-12 --traza HU-901
```

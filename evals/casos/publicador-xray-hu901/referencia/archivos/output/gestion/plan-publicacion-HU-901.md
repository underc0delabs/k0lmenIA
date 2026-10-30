# Plan de publicación en Xray Cloud · HU-901

Probado **en seco** (`--dry-run`): todavía no se publicó nada en Xray.

- Resultados extraídos: `output/gestion/resultados-20261029-1000.json` (5 escenarios: 4 aprobados, 1 fallido)
- Ciclo propuesto: **PROJ-60** "HU-901 · Sprint 15 · Regresión" (el último de `output/gestion/HU-901-xray-cloud.json`)
- Trazabilidad: HU-901

| Caso | Key | Estado | Nota |
|---|---|---|---|
| CP-001 | PROJ-50 | Aprobado | |
| CP-003 | PROJ-52 | Fallido | AssertionError: se esperaba 'Email inválido' y se vio 'Error inesperado' |
| CP-005 | PROJ-54 | Aprobado | Con la reserva de FI-01: el resultado puede cambiar cuando se resuelva |

## Escenarios que no se publican

- **Smoke de la home**: no tiene tag `@CP-XXX` ni key, y su título no coincide con ningún caso de la trazabilidad. No lo asigno a CP-001 por aproximación: si es ese caso, agregale el tag `@CP-001` (y `@HU-901`) al escenario o confirmame la key.
- **Login con credenciales válidas**: es de otra historia (HU-900); se publica aparte con su trazabilidad.

## Para publicar

Con tu confirmación del ciclo:

```bash
python scripts/gestion/gestion.py publicar-resultados --ciclo PROJ-60 --resultados output/gestion/resultados-20261029-1000.json --traza HU-901
```

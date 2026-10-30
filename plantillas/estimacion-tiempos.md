# Tiempo estimado de ejecución manual

Cada caso de prueba (manual o BDD) lleva un **tiempo estimado de ejecución manual**: cuánto tarda una persona que conoce la aplicación en ejecutarlo de punta a punta, con el ambiente listo. Lo calcula `scripts/estimacion.py` y aparece en:

- la planilla de casos (`generar_casos.py`): columna **Tiempo estimado (min)**, con el total al pie, y en el `.md`;
- la herramienta de gestión al subir los casos (`gestion.py subir-casos`): en la descripción de cada caso y, si la herramienta lo tiene, en su campo de tiempo —**Original Estimate** de Jira en Xray Cloud y Server/DC, **estimatedTime** en QTM4J y Zephyr Scale, **estimatedEffort** en AIO Tests—; para Azure DevOps viaja en el JSON de `para_azure_devops.py` y como etiqueta;
- el revisor de casos (`revisor-casos`).

## La fórmula

```
tiempo del caso = (preparación + Σ tiempo de cada paso + registro) × factor     → redondeado hacia arriba a 0,5 min (mínimo 1)

tiempo de un paso = acción + datos + verificación
```

```
+--------------+------------------------------------------+
| Parte        | Cómo se calcula                          |
+==============+==========================================+
| Acción       | Según el verbo del paso (tabla de abajo) |
+--------------+------------------------------------------+
| Datos        | 0,15 min por cada dato extra del paso    |
|              | (más allá de los campos que ya se        |
|              | contaron)                                |
+--------------+------------------------------------------+
| Verificación | 0,5 min si el paso tiene resultado       |
|              | esperado (o es un Then), + 0,25 por cada |
|              | verificación extra (hasta 4)             |
+--------------+------------------------------------------+
| Preparación  | 1 min (abrir el ambiente y leer el caso) |
|              | + 0,5 por precondición (hasta 3) + 2 si  |
|              | hay que crear datos o usuarios           |
+--------------+------------------------------------------+
| Registro     | 0,5 min (marcar el resultado y guardar   |
|              | la evidencia) + 0,1 por paso             |
+--------------+------------------------------------------+
| Factor       | 1,1 para casos negativos o de borde (hay |
|              | que observar con más cuidado); 1 para el |
|              | resto. `ESTIMACION_FACTOR` del `.env`    |
|              | multiplica todo (por ejemplo 1,3 para    |
|              | alguien que recién conoce la aplicación) |
+--------------+------------------------------------------+
```

```
+-----------------------------------+---------------+------------------------------------------+
| Acción del paso (verbo)           | Minutos       | Ejemplos                                 |
+===================================+===============+==========================================+
| Navegar                           | 0,5           | ir a, abrir, acceder, entrar a la        |
|                                   |               | sección                                  |
+-----------------------------------+---------------+------------------------------------------+
| Clic o seleccionar                | 0,25          | hacer clic, presionar, seleccionar,      |
|                                   |               | marcar, guardar                          |
+-----------------------------------+---------------+------------------------------------------+
| Completar campos                  | 0,3 por campo | completar, escribir, ingresar el email y |
|                                   |               | la clave                                 |
+-----------------------------------+---------------+------------------------------------------+
| Iniciar sesión                    | 1             | iniciar sesión, loguearse con su usuario |
+-----------------------------------+---------------+------------------------------------------+
| Subir o descargar un archivo      | 1             | adjuntar, subir una imagen, descargar,   |
|                                   |               | exportar                                 |
+-----------------------------------+---------------+------------------------------------------+
| Esperar un correo, SMS o proceso  | 2             | esperar, recibir el correo, revisar la   |
|                                   |               | bandeja                                  |
+-----------------------------------+---------------+------------------------------------------+
| Consultar la base, una API o logs | 2             | consultar la base de datos, llamar al    |
|                                   |               | endpoint                                 |
+-----------------------------------+---------------+------------------------------------------+
| Leer o recorrer                   | 0,5           | desplazarse, revisar, leer el detalle    |
+-----------------------------------+---------------+------------------------------------------+
| Cualquier otra acción             | 0,5           |                                          |
+-----------------------------------+---------------+------------------------------------------+
```

Ejemplo: *"Inicio de sesión con contraseña incorrecta"* (1 precondición; pasos: ir a la página de login, completar el email y la contraseña con 2 datos, hacer clic en Ingresar con 2 verificaciones) = (preparación 1,5 + pasos 0,5 + 0,6 + 1,25 + registro 0,8) × 1,1 = 5,12 → **5,5 min** (redondeado hacia arriba a 0,5). El último paso suma 0,25 del clic + 0,5 de la primera verificación + 0,5 de las dos extra que tiene el resultado esperado.

## Ajustarlo

- **Un caso puntual**: escribí el tiempo en la columna *Tiempo estimado (min)* de la planilla (o `"tiempo_min"` en el JSON de `generar_casos.py`): ese valor manda sobre la fórmula y los pasos se reparten en proporción.
- **Todo el equipo**: `ESTIMACION_FACTOR` en el `.env` (1 por defecto).
- **Sin campo nativo en la herramienta de gestión**: `GESTION_TIEMPO_NATIVO=0` (el tiempo queda solo en la descripción). Si la herramienta rechaza el campo (por ejemplo, un proyecto de Jira sin time tracking), el caso se crea igual, sin él.
- **Ver la estimación de una planilla**: `python scripts/estimacion.py output/casos-de-prueba/manuales/casos-HU-001.xlsx`.

Es una estimación para planificar, no una medición: compará con lo que tardan las ejecuciones reales y ajustá el factor.

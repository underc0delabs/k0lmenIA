"""Interfaz común de los adaptadores de herramientas de gestión de pruebas.

Cada herramienta (Xray Cloud, Xray Server/DC, QTM4J, AIO Tests) implementa estas
operaciones con su API oficial. El CLI (gestion.py) y los agentes solo usan esta interfaz.

Convenciones:
- Un "caso" es el dict que devuelve lectores.leer_casos (id, titulo, descripcion,
  precondiciones, prioridad, etiquetas, tipo manual|cucumber, pasos, gherkin).
- Las keys que se devuelven son las visibles en la herramienta (PROJ-45, PROJ-TC-12...).
- estado normalizado: aprobado | fallido | bloqueado | pendiente | en_ejecucion.
"""


import os


def con_tiempo(texto, caso):
    """Agrega a la descripción el tiempo estimado de ejecución manual (scripts/estimacion.py)."""
    e = caso.get("estimacion")
    if not e:
        return texto
    linea = f"Tiempo estimado de ejecución manual: {e['texto']} (k0lmenIA)"
    return f"{texto}\n\n{linea}".strip() if texto else linea


def tiempo_nativo():
    """GESTION_TIEMPO_NATIVO=0 desactiva el campo nativo de tiempo (Original Estimate, estimatedTime…)."""
    return os.environ.get("GESTION_TIEMPO_NATIVO", "1").strip() != "0"


def intentar_con_tiempo(crear, con, sin):
    """Crea con el campo de tiempo; si la herramienta lo rechaza (campo inexistente, fuera de la pantalla
    o con otro formato), crea sin él. El tiempo sigue en la descripción."""
    from comun import ErrorGestion
    if con is sin:
        return crear(sin)
    try:
        return crear(con)
    except ErrorGestion:
        return crear(sin)


def jira_duracion(minutos):
    """Original Estimate de Jira ("7m", "1h 15m")."""
    import math
    m = int(math.ceil(minutos))
    h, r = divmod(m, 60)
    return " ".join(x for x in (f"{h}h" if h else "", f"{r}m" if r else "") if x) or "1m"


def hhmm(minutos):
    import math
    m = int(math.ceil(minutos))
    return f"{m // 60:02d}:{m % 60:02d}"


def titulo_remoto(caso, largo=250):
    """'CP-001 - Título' (o solo el título si el caso no tiene ID propio, ej. un escenario sin @CP-XXX)."""
    titulo = caso["titulo"] if caso["id"] == caso["titulo"] else f'{caso["id"]} - {caso["titulo"]}'
    return titulo[:largo]


class Adaptador:
    nombre = "base"
    #: tamaño máximo de un adjunto en bytes (None = sin límite conocido)
    limite_adjunto = None

    def __init__(self, proyecto, dry_run=False):
        self.proyecto = proyecto
        self.dry_run = dry_run

    # --- Repositorio de casos -------------------------------------------------
    def crear_carpeta(self, ruta):
        """Crea la carpeta (y sus padres) si no existe. Devuelve su id."""
        raise NotImplementedError

    def crear_caso(self, caso, carpeta_id, carpeta_ruta):
        """Crea el caso dentro de la carpeta. Devuelve {"key": ..., "id": ...}."""
        raise NotImplementedError

    def vincular_caso_historia(self, caso, historia):
        """Vincula el caso (dict con key/id) a la historia de Jira (ej. PROJ-12)."""
        raise NotImplementedError

    # --- Ciclos ---------------------------------------------------------------
    def crear_ciclo(self, nombre, descripcion="", carpeta_ruta=None):
        """Crea el ciclo (Test Execution en Xray, Test Cycle en QTM4J/AIO). Devuelve {"key", "id"}."""
        raise NotImplementedError

    def vincular_ciclo_historia(self, ciclo, historia):
        raise NotImplementedError

    def agregar_casos_ciclo(self, ciclo, casos):
        """ciclo y casos: dicts con key/id."""
        raise NotImplementedError

    # --- Resultados -----------------------------------------------------------
    def registrar_resultado(self, ciclo, caso, estado, comentario, evidencias):
        """Carga el estado del caso en el ciclo, el comentario y adjunta las evidencias
        (lista de rutas). Devuelve la lista de evidencias que no se pudieron subir."""
        raise NotImplementedError

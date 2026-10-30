"""Etiquetas estándar de un caso de prueba: las mismas en la planilla, en el .feature y en la herramienta de gestión.

Cada caso lleva, en este orden:
- la historia: HU-XXX y, si se subió con --historia, su key en Jira (PROJ-12);
- el módulo: modulo-<nombre> (modulo-registro, modulo-inicio-de-sesion);
- la prioridad: critica, alta, media o baja (la de la columna Prioridad o el tag del escenario);
- el tipo de ejecución: smoke si el caso es smoke (o crítico) y regresion si entra en la regresión (todos, salvo los
  que dependen de información que falta o están bloqueados);
- y después las demás (positivo, negativo, borde, CA1, falta-info, FI-01…).

Las etiquetas van sin @ y en minúscula (Cucumber distingue mayúsculas: TAGS=@smoke no encuentra @Smoke); las keys
(HU-001, PROJ-12, CA1, FI-01, CP-001) quedan como están.
"""
import re
import unicodedata

PRIORIDADES = {"critica": "critica", "crítica": "critica", "alta": "alta", "media": "media", "baja": "baja"}
SMOKE = {"smoke"}
REGRESION = {"regresion", "regresión", "regression"}
FUERA_DE_REGRESION = {"falta-info", "bloqueado"}
_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9]*-\d+$|^CA\d+$", re.I)
_HU = re.compile(r"^HU-\d+$", re.I)


def slug(texto):
    """'Inicio de sesión' -> 'inicio-de-sesion'."""
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")


def separar_modulo(texto):
    """'HU-001 — Inicio de sesión' -> ('HU-001', 'Inicio de sesión'); 'Registro' -> (None, 'Registro')."""
    texto = str(texto or "").strip()
    m = re.match(r"^(HU-\d+)\s*(?:[—–:|-]\s*)?(.*)$", texto, re.I)
    if m:
        return m.group(1).upper(), m.group(2).strip()
    return None, texto


def _normal(e):
    e = str(e).strip().lstrip("@")
    return e if _KEY.match(e) else e.lower()


def lista(etiquetas):
    """'@login @smoke, @HU-001' o ['@login', 'smoke'] -> ['login', 'smoke', 'HU-001']."""
    if isinstance(etiquetas, str):
        etiquetas = re.split(r"[\s,]+", etiquetas)
    return [_normal(e) for e in etiquetas or [] if str(e).strip().lstrip("@")]


def estandar(etiquetas, prioridad=None, modulo=None, historias=()):
    """Las etiquetas del caso ordenadas y completas (ver el docstring del módulo).

    prioridad: la de la columna Prioridad (manda sobre un tag de prioridad distinto).
    modulo:    nombre del módulo ('Inicio de sesión' o 'HU-001 — Inicio de sesión'); si el caso ya trae un
               modulo-<x>, se respeta.
    historias: HU-XXX y keys de Jira que el caso tiene que llevar (se suman a las que ya tenga).
    """
    resto = lista(etiquetas)
    hu_del_modulo, nombre_modulo = separar_modulo(modulo)
    claves = [h for h in resto if _HU.match(h)]
    claves += [_normal(h) for h in [hu_del_modulo, *historias] if h]
    claves = list(dict.fromkeys(h.upper() if _HU.match(h) else h for h in claves))
    mods = [e for e in resto if e.startswith("modulo-")]
    if not mods and slug(nombre_modulo):
        mods = [f"modulo-{slug(nombre_modulo)}"]
    tags_prioridad = [PRIORIDADES[e] for e in resto if e in PRIORIDADES]
    prio = PRIORIDADES.get(str(prioridad or "").strip().lower()) or (tags_prioridad[0] if tags_prioridad else None)
    es_smoke = any(e in SMOKE for e in resto) or prio == "critica"
    fuera = any(e in FUERA_DE_REGRESION for e in resto)
    tipo = (["smoke"] if es_smoke else []) + (["regresion"] if not fuera else [])
    usadas = {e.upper() for e in claves} | set(mods) | set(PRIORIDADES) | SMOKE | REGRESION
    otras = [e for e in resto if e.upper() not in usadas and e not in usadas]
    return list(dict.fromkeys(claves + mods + ([prio] if prio else []) + tipo + otras))


def como_texto(etiquetas):
    """['HU-001', 'smoke'] -> '@HU-001 @smoke' (la columna #Etiquetas de la planilla y los tags de un .feature)."""
    return " ".join(f"@{e}" for e in etiquetas)

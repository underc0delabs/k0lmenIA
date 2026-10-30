"""Días y husos horarios para programar tareas (cron de GitHub Actions, Programador de tareas de Windows, crontab)."""
import re
from datetime import datetime, timedelta, timezone

DIAS = {"lun": ("MON", 1), "mar": ("TUE", 2), "mie": ("WED", 3), "mié": ("WED", 3), "jue": ("THU", 4), "vie": ("FRI", 5),
        "sab": ("SAT", 6), "sáb": ("SAT", 6), "dom": ("SUN", 0)}


# Respaldo cuando zoneinfo no tiene la base de husos (Windows sin el paquete tzdata): zonas sin horario de verano.
HUSOS_FIJOS = {"America/Argentina/Buenos_Aires": -3, "America/Montevideo": -3, "America/Sao_Paulo": -3, "America/Bogota": -5,
               "America/Lima": -5, "America/Mexico_City": -6, "America/Guatemala": -6, "America/Caracas": -4, "America/La_Paz": -4,
               "America/Panama": -5, "America/Guayaquil": -5, "UTC": 0}


def huso(zona, referencia=None):
    """tzinfo de la zona: la de zoneinfo si está; si no, un huso fijo conocido o 'UTC-03:00'."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(zona)
    except Exception:
        pass
    m = re.match(r"^UTC([+-])(\d{1,2})(?::?(\d{2}))?$", zona.strip(), re.I)
    if m:
        horas = int(m.group(2)) + int(m.group(3) or 0) / 60
        return timezone(timedelta(hours=horas if m.group(1) == "+" else -horas))
    if zona in HUSOS_FIJOS:
        return timezone(timedelta(hours=HUSOS_FIJOS[zona]))
    raise SystemExit(f'No conozco la zona "{zona}" sin la base de husos: instalá tzdata (pip install tzdata) o usá "UTC-03:00".')


def cron_utc(hora, dias="lun-vie", zona="America/Argentina/Buenos_Aires", referencia=None):
    """'09:00' lun-vie en la zona → expresión cron de GitHub Actions (UTC), corriendo los días si cruza la medianoche."""
    h, m = (int(x) for x in hora.split(":"))
    ref = referencia or datetime.now()
    local = datetime(ref.year, ref.month, ref.day, h, m, tzinfo=huso(zona, ref))
    utc = local.astimezone(timezone.utc)
    corrimiento = (utc.date() - local.date()).days
    nums = sorted(((DIAS[d][1] + corrimiento) % 7) for d in _dias(dias))
    return f"{utc.minute} {utc.hour} * * {','.join(str(n) for n in nums)}"


def _dias(texto):
    t = (texto or "lun-vie").lower().replace(" ", "")
    orden = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
    norm = lambda x: x.replace("é", "e").replace("á", "a")  # noqa: E731
    if t in ("todos", "diario", "lun-dom"):
        return orden
    if "-" in t and "," not in t:
        a, b = (norm(x) for x in t.split("-"))
        return orden[orden.index(a):orden.index(b) + 1]
    return [norm(x) for x in t.split(",") if x]

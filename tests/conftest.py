"""Configuración común de los tests de k0lmenIA: los scripts se importan desde scripts/ y scripts/gestion/."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (RAIZ / "scripts", RAIZ / "scripts" / "gestion"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

# Los informes que arman los tests (también en subprocesos) no tocan el portal output/index.html.
import os  # noqa: E402

os.environ["K0LMENIA_PORTAL"] = "0"


# ------------------------------------------------------------------ traducciones (modo estricto, lo usa el CI)
# Con K0LMENIA_I18N_ESTRICTO=1, cada texto que quede en español en la versión en inglés de los informes que arman
# los tests se audita (scripts/_i18n.py). Al final se compara con tests/i18n_base.txt (el contenido de ejemplo de
# los tests, que es legítimamente español): si aparece algo nuevo, es interfaz sin traducir y la corrida falla.
# Para actualizar la base cuando se agregan fixtures: K0LMENIA_I18N_ESTRICTO=actualizar python -m pytest tests -q
BASE_I18N = RAIZ / "tests" / "i18n_base.txt"
_AUDITORIA = RAIZ / ".pytest_cache" / "i18n-auditoria.txt"


def pytest_sessionstart(session):
    if os.environ.get("K0LMENIA_I18N_ESTRICTO"):
        _AUDITORIA.parent.mkdir(parents=True, exist_ok=True)
        _AUDITORIA.write_text("", encoding="utf-8")
        os.environ["K0LMENIA_I18N_AUDITORIA"] = str(_AUDITORIA)  # también la heredan los subprocesos


def pytest_sessionfinish(session, exitstatus):
    modo = os.environ.get("K0LMENIA_I18N_ESTRICTO")
    if not modo or not _AUDITORIA.exists():
        return
    vistas = {x.strip() for x in _AUDITORIA.read_text(encoding="utf-8").splitlines() if x.strip()}
    if modo == "actualizar":
        BASE_I18N.write_text("\n".join(sorted(vistas)) + "\n", encoding="utf-8")
        print(f"\n[i18n] base actualizada: {len(vistas)} textos de ejemplo en {BASE_I18N.name}")
        return
    base = set(BASE_I18N.read_text(encoding="utf-8").splitlines()) if BASE_I18N.exists() else set()
    nuevas = sorted(vistas - base)
    if nuevas:
        print("\n[i18n] Textos en español en la versión en inglés de los informes que no están en el diccionario")
        print("       (scripts/i18n/en/*.json). Si son interfaz, traducilos; si son datos de ejemplo de un test nuevo,")
        print("       actualizá la base con K0LMENIA_I18N_ESTRICTO=actualizar:")
        for x in nuevas[:60]:
            print(f"         - {x}")
        session.exitstatus = 1

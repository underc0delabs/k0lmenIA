"""Índice de input/documentacion/ (agente documentador-proyecto)."""
import datetime as dt
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import indice_documentacion as indice  # noqa: E402


def _md(ruta, encabezado, cuerpo="# Título del archivo\n"):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    front = "".join(f"{k}: {v}\n" for k, v in encabezado.items())
    ruta.write_text((f"---\n{front}---\n" if encabezado else "") + cuerpo, encoding="utf-8")


def test_lee_el_encabezado_y_tolera_bom():
    assert indice.leer_encabezado("﻿---\ntitulo: Reglas\ntipo: proyecto\n---\n# x") == {"titulo": "Reglas", "tipo": "proyecto"}
    assert indice.leer_encabezado("# Sin encabezado") == {}


def test_documentos_por_tipo_con_historia_y_agregados_a_mano(tmp_path):
    _md(tmp_path / "proyecto" / "reglas-de-negocio.md", {"titulo": "Reglas", "tipo": "proyecto", "fuentes": "github a/b", "actualizado": "2026-01-10"})
    _md(tmp_path / "historias" / "PROJ-12" / "dossier.md", {"titulo": "Dossier PROJ-12", "tipo": "historia", "historia": "PROJ-12", "actualizado": "2026-10-01"})
    _md(tmp_path / "proyecto" / "mapa-funcional.md", {"titulo": "Mapa", "tipo": "web", "actualizado": "2026-10-01"})
    (tmp_path / "proyecto" / "mapa-funcional.json").write_text("{}", encoding="utf-8")  # datos del .md: no se lista aparte
    _md(tmp_path / "manual-usuario.md", {}, "# Manual de usuario\n")
    (tmp_path / "acta.pdf").write_bytes(b"%PDF")
    _md(tmp_path / "_borrador.md", {"tipo": "proyecto"})  # los temporales con _ no se listan
    (tmp_path / "INDICE.md").write_text("viejo", encoding="utf-8")

    docs = indice.documentos(tmp_path)
    assert [d["ruta"] for d in docs] == [
        "proyecto/reglas-de-negocio.md", "proyecto/mapa-funcional.md", "historias/PROJ-12/dossier.md", "acta.pdf", "manual-usuario.md"]
    manual = docs[-1]
    assert manual["tipo"] == "manual" and manual["titulo"] == "Manual de usuario"

    texto = indice.armar_indice(docs, dt.date(2026, 10, 14), dias=30)
    assert "5 documento(s) · 1 para revisar" in texto
    assert "| `proyecto/reglas-de-negocio.md` | Reglas | github a/b | 2026-01-10 | Revisar |" in texto
    assert "| `historias/PROJ-12/dossier.md` | Dossier PROJ-12 | PROJ-12 | - | 2026-10-01 | Vigente |" in texto
    assert texto.index("## Proyecto") < texto.index("## Aplicación web") < texto.index("## Historias") < texto.index("## Agregado a mano")


def test_sin_documentacion_lo_dice(tmp_path):
    assert "Todavía no hay documentación" in indice.armar_indice([], dt.date(2026, 10, 14), 30)


def test_main_escribe_el_indice_con_tablas_alineadas(tmp_path, capsys):
    _md(tmp_path / "proyecto" / "resumen.md", {"titulo": "Resumen", "tipo": "proyecto", "actualizado": dt.date.today().isoformat()})
    assert indice.main(["--carpeta", str(tmp_path)]) == 0
    texto = (tmp_path / "INDICE.md").read_text(encoding="utf-8")
    assert "+====" in texto and "Resumen" in texto  # formatear_tablas.py la pasó a ASCII
    assert "1 documento(s)" in capsys.readouterr().out


def test_la_documentacion_generada_no_se_versiona():
    reglas = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert "/input/documentacion/*" in reglas and "!/input/documentacion/.gitkeep" in reglas
    assert os.path.exists(RAIZ / "input" / "documentacion" / ".gitkeep")


def test_indice_muestra_confiabilidad(tmp_path):
    indice.escribir_documento(tmp_path / "manual-usuario" / "a.md", "Manual — A", "manual-usuario", "# A\n", estado="confirmado",
                              fuentes="app")
    indice.escribir_documento(tmp_path / "proyecto" / "r.md", "Reglas", "proyecto", "# R\n")
    texto = indice.armar_indice(indice.documentos(tmp_path), dt.date.today(), 30)
    assert "| Documento | Título | Confiabilidad | Fuentes | Actualizado | Estado |" in texto
    assert "| `manual-usuario/a.md` | Manual — A | confirmado | app |" in texto
    assert "| Documento | Título | Fuentes | Actualizado | Estado |" in texto  # sin confiabilidad, sin columna

"""Manual de usuario (redactor-manual): versiones, revisión, checklist, HTML, conocimiento a input y plan de la plataforma."""
import base64
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "herramientas" / "manual"))
sys.path.insert(0, str(RAIZ / "scripts"))

import manual  # noqa: E402
import indice_documentacion as indice  # noqa: E402

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

BORRADOR = """# Alta de proveedores

> Cambios respecto de la versión anterior:
> - Nuevo campo Código

## Objetivo
Dar de alta un proveedor.

## Procedimiento
1. Ingresá a **Proveedores**.
   ![Listado de proveedores](../capturas/01-listado-proveedores.png)
2. Completá **Razón social** y hacé clic en **Guardar**.
   - Si falta, aparece **Campo obligatorio**.

> ⚠️ QA REVIEW (REVIEW-001)
>
> Motivo: no está claro si Código es obligatorio.
>
> Confirmación requerida: ¿Es obligatorio?

## Resultado esperado
Aparece **Proveedor guardado correctamente**.

| Campo | Obligatorio |
|---|---|
| Razón social | Sí |
"""

QA_REVIEW = """# QA Review — proveedores-alta v0.1

## REVIEW-001

Funcionalidad:
Alta de proveedor

Problema:
Los casos indican que Código es obligatorio,
pero la historia no lo menciona.

Confirmación requerida:
Confirmar si es obligatorio.

Estado:
PENDING

## REVIEW-002

Funcionalidad: Listado
Problema: nombre del menú
Estado: RESOLVED
Resolución: es "Proveedores"
"""

EVIDENCIA = """# Matriz
| Funcionalidad | App | Estado |
|---|---|---|
| Alta | Sí | CONFIRMED |
| Código obligatorio | Pendiente | REVIEW |

## Pistas para probar
- Razón social: obligatoria, máximo 100 caracteres.
"""


@pytest.fixture
def man(tmp_path):
    base = tmp_path / "out"
    manual.preparar("proveedores-alta", base)
    c = base / "proveedores-alta"
    (c / "capturas" / "01-listado-proveedores.png").write_bytes(PNG)
    (c / "borradores" / "proveedores-alta-v0.1.md").write_text(BORRADOR, encoding="utf-8")
    (c / "revision" / "qa-review.md").write_text(QA_REVIEW, encoding="utf-8")
    (c / "revision" / "evidencia.md").write_text(EVIDENCIA, encoding="utf-8")
    return base


def test_slug_y_versiones(tmp_path, man):
    with pytest.raises(ValueError):
        manual.carpeta("Alta Proveedores")
    est = manual.estado_manual("proveedores-alta", man)
    assert est["ultimo_borrador"].endswith("proveedores-alta-v0.1.md")
    assert est["borrador_siguiente"].endswith("proveedores-alta-v0.2.md") and est["version_final"] is None
    assert est["reviews"] == {"pendientes": ["REVIEW-001"], "resueltos": 1, "descartados": 0}
    (man / "proveedores-alta" / "borradores" / "proveedores-alta-v0.10.md").write_text("# x", encoding="utf-8")
    assert manual.estado_manual("proveedores-alta", man)["borrador_siguiente"].endswith("v0.11.md")  # 10 > 9, no orden de texto


def test_leer_reviews_formatos(man):
    r = manual.leer_reviews(man / "proveedores-alta" / "revision" / "qa-review.md")
    assert [x["id"] for x in r] == ["REVIEW-001", "REVIEW-002"]
    assert r[0]["estado"] == "PENDING" and r[0]["problema"] == "Los casos indican que Código es obligatorio, pero la historia no lo menciona."
    assert r[0]["confirmacion"] == "Confirmar si es obligatorio."
    assert r[1]["estado"] == "RESOLVED" and r[1]["funcionalidad"] == "Listado" and r[1]["resolucion"] == 'es "Proveedores"'


def test_verificar_bloquea_y_despues_pasa(man):
    v = manual.verificar("proveedores-alta", base=man)
    texto = " ".join(v["problemas"])
    assert not v["ok"] and "REVIEW-001" in texto and "QA REVIEW" in texto and "Código obligatorio (REVIEW)" in texto
    c = man / "proveedores-alta"
    (c / "revision" / "qa-review.md").write_text(QA_REVIEW.replace("PENDING", "RESOLVED"), encoding="utf-8")
    (c / "revision" / "evidencia.md").write_text(EVIDENCIA.replace("| REVIEW |", "| CONFIRMED |"), encoding="utf-8")
    limpio = manual.quitar_internos(BORRADOR)
    (c / "borradores" / "proveedores-alta-v0.2.md").write_text(limpio, encoding="utf-8")
    v = manual.verificar("proveedores-alta", base=man)
    assert v["ok"] and v["problemas"] == [] and v["borrador"].endswith("v0.2.md")
    (c / "capturas" / "01-listado-proveedores.png").unlink()
    assert "Imágenes que no existen" in " ".join(manual.verificar("proveedores-alta", base=man)["problemas"])


def test_quitar_internos():
    limpio = manual.quitar_internos(BORRADOR)
    assert "QA REVIEW" not in limpio and "Cambios respecto" not in limpio
    assert "## Resultado esperado" in limpio and "![Listado de proveedores]" in limpio
    assert [b[0] for b in manual.bloques_review(BORRADOR)] == ["REVIEW-001"]


def test_html_autocontenido(man):
    md = man / "proveedores-alta" / "borradores" / "proveedores-alta-v0.1.md"
    html = manual.a_html(md).read_text(encoding="utf-8")
    assert "<title>Alta de proveedores — k0lmenIA</title>" in html and "Borrador v0.1" in html
    assert '<span class="mk">k0</span>' in html and "#0E0C09" in html and "@font-face" in html  # diseño de la casa
    assert 'src="data:image/png;base64,' in html and "<figcaption>Listado de proveedores</figcaption>" in html
    assert '<blockquote class="review">' in html and "<strong>Proveedores</strong>" in html
    assert "<ol>" in html and "<ul>" in html and "<table>" in html and "<th>Campo</th>" in html
    sin = manual.a_html(md, md.with_name("x.html"), embebido=False).read_text(encoding="utf-8")
    assert 'src="../capturas/01-listado-proveedores.png"' in sin


def test_a_input_borrador_y_confirmado(man, tmp_path):
    destino = tmp_path / "doc"
    ruta = manual.a_input("proveedores-alta", base=man, destino=destino, url="https://qa.app")
    texto = ruta.read_text(encoding="utf-8")
    meta = indice.leer_encabezado(texto)
    assert meta["tipo"] == "manual-usuario" and meta["estado"] == "borrador" and "app https://qa.app" in meta["fuentes"]
    assert "QA REVIEW" not in texto and "Cambios respecto" not in texto
    assert "## Sin confirmar" in texto and "REVIEW-001" in texto and "REVIEW-002" not in texto
    assert "## Pistas para probar" in texto and "máximo 100 caracteres" in texto
    assert "capturas/01-listado-proveedores.png" in texto and "../capturas" not in texto
    assert texto.count("# Alta de proveedores") == 1
    assert "Manual de usuario (cómo se usa la aplicación)" in (destino / "INDICE.md").read_text(encoding="utf-8")
    # La versión aprobada pasa a confirmado
    c = man / "proveedores-alta"
    (c / "versiones" / "proveedores-alta-v1.0.md").write_text(manual.quitar_internos(BORRADOR), encoding="utf-8")
    (c / "revision" / "qa-review.md").write_text(QA_REVIEW.replace("PENDING", "RESOLVED"), encoding="utf-8")
    texto = manual.a_input("proveedores-alta", base=man, destino=destino).read_text(encoding="utf-8")
    assert "estado: confirmado" in texto and "## Sin confirmar" not in texto


def test_captura_valida_nombre_y_no_pisa(man, tmp_path):
    origen = tmp_path / "page-2026.png"
    origen.write_bytes(PNG)
    with pytest.raises(ValueError):
        manual.guardar_captura("proveedores-alta", origen, "screenshot1.png", base=man)
    r = manual.guardar_captura("proveedores-alta", origen, "02-nuevo-proveedor.png", base=man)
    assert r["reemplazada"] is False and not origen.exists()
    origen.write_bytes(PNG)
    with pytest.raises(ValueError):
        manual.guardar_captura("proveedores-alta", origen, "02-nuevo-proveedor.png", base=man)
    assert manual.guardar_captura("proveedores-alta", origen, "02-nuevo-proveedor.png", reemplazar=True, base=man)["reemplazada"]


def test_plataforma_menu_y_mapa(man, tmp_path):
    menu = tmp_path / "menu.json"
    menu.write_text(json.dumps([{"modulo": "Compras", "opciones": [{"nombre": "Proveedores", "ruta": "/compras/proveedores"}]},
                                {"modulo": "Proveedores alta", "opciones": []}]), encoding="utf-8")
    mapa = tmp_path / "mapa.json"
    mapa.write_text(json.dumps({"paginas": [{"ruta": "/compras/ordenes", "titulo": "Órdenes", "formularios": [{"campos": []}]},
                                            {"ruta": "/ayuda", "titulo": "Ayuda"}, {"ruta": "/x", "error": "404"}]}), encoding="utf-8")
    plan = manual.plataforma(mapa, menu, man)
    mods = {m["slug"]: m for m in plan["modulos"]}
    assert set(mods) == {"compras", "proveedores-alta", "ayuda"}
    assert len(mods["compras"]["paginas"]) == 2 and mods["compras"]["formularios"] == 1
    assert mods["proveedores-alta"]["manual"] == "borrador" and mods["ayuda"]["manual"] == "pendiente"
    assert "+====" in (man / "plataforma" / "indice.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        manual.plataforma(tmp_path / "no.json", None, man)


def test_indice_muestra_confiabilidad(tmp_path):
    indice.escribir_documento(tmp_path / "manual-usuario" / "a.md", "Manual — A", "manual-usuario", "# A\n", estado="confirmado",
                              fuentes="app")
    indice.escribir_documento(tmp_path / "proyecto" / "r.md", "Reglas", "proyecto", "# R\n")
    import datetime as dt
    texto = indice.armar_indice(indice.documentos(tmp_path), dt.date.today(), 30)
    assert "| Documento | Título | Confiabilidad | Fuentes | Actualizado | Estado |" in texto
    assert "| `manual-usuario/a.md` | Manual — A | confirmado | app |" in texto
    assert "| Documento | Título | Fuentes | Actualizado | Estado |" in texto  # sin confiabilidad, sin columna

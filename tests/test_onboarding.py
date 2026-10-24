"""Plan de onboarding (agente guia-onboarding)."""
import json

import generar_onboarding as onb
from _i18n import ruta_en, ruta_es  # noqa: E402

PLAN = {
    "persona": "Ana Pérez", "rol": "QA manual", "proyecto": "Tienda", "fecha": "2026-10-14",
    "resumen": "Tienda online con checkout y backoffice.",
    "producto": {"modulos": [{"nombre": "Checkout", "descripcion": "Pago con tarjeta", "fuente": "proyecto/resumen.md"}],
                 "roles": [{"rol": "Comprador", "puede": "comprar"}],
                 "flujos": [{"nombre": "Comprar", "pantallas": "Carrito → Pago", "fuente": "mapa-funcional.md"}],
                 "glosario": [{"termino": "SKU", "definicion": "código de producto"}]},
    "entorno": [{"que": "Doctor", "estado": "falta", "detalle": "No existe .env", "accion": "cp .env.example .env"}],
    "agentes": [{"agente": "generador-casos-manuales", "para_que": "casos", "pedido": "Generá los casos de PROJ-12"}],
    "plan": [{"cuando": "Día 1", "tarea": "Correr el doctor", "hecho_cuando": "0 faltantes", "agente": "npm run doctor"}],
    "preguntas": [{"id": "FI-01", "pregunta": "¿Límite de cuotas?", "a_quien": "PO", "por_que": "no está en la historia"}],
    "checklist": ["Tener el .env completo", "Correr npm test"],
    "faltantes": ["No hay mapa funcional."],
}


def test_html_y_md(tmp_path):
    archivo = tmp_path / "plan.json"
    archivo.write_text(json.dumps(PLAN, ensure_ascii=False), encoding="utf-8")
    assert onb.main([str(archivo), "--salida", str(tmp_path / "o")]) == 0
    html = ruta_es(tmp_path / "o" / "plan-onboarding.html").read_text(encoding="utf-8")
    assert "Onboarding · Ana Pérez" in html and "Generá los casos de PROJ-12" in html and "FI-01" in html
    en = ruta_en(tmp_path / "o" / "plan-onboarding.html").read_text(encoding="utf-8")
    assert 'lang="en"' in en and "Plan for the first weeks" in en and "' of '+cajas.length" in en
    assert html.count('type="checkbox"') == 2 and "localStorage" in html and "1 pendiente(s)" in html
    md = (tmp_path / "o" / "plan-onboarding.md").read_text(encoding="utf-8")
    assert "- [ ] Correr npm test" in md and "Checkout" in md and "> No hay mapa funcional." in md


def test_slug_y_validacion(tmp_path):
    assert onb.slug("Ana Pérez") == "ana-perez"
    archivo = tmp_path / "x.json"
    archivo.write_text("{}", encoding="utf-8")
    import pytest
    with pytest.raises(SystemExit):
        onb.main([str(archivo)])

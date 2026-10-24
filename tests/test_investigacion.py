"""Informe del relevamiento de un proyecto (agente investigador-proyecto)."""
import json

import pytest

import generar_informe_investigacion as inv

RELEVAMIENTO = {
    "proyecto": "Tienda online", "clave": "PROJ", "fecha": "2026-10-19", "profundidad": "normal", "para": "QA manual",
    "tablero": "https://mi-empresa.atlassian.net/jira/software/projects/PROJ/boards/12",
    "resumen": "Tienda online con checkout, billetera y backoffice.",
    "cobertura": {"total_items": 400, "leidos": 80, "criterio": "Críticos abiertos y sprint actual",
                  "epicas": 2, "historias": 3, "tareas": 7, "comentarios": 20},
    "jerarquia": [{"epica": {"id": "PROJ-3", "titulo": "Checkout", "estado": "En curso", "url": "https://x/PROJ-3"},
                   "historias": [{"id": "PROJ-12", "titulo": "Pago con tarjeta", "estado": "En curso", "responsable": "Ana",
                                  "tareas": 4, "comentarios": 7, "links": ["Confluence 'Reglas de pagos'"],
                                  "nota": "decisión: cuotas hasta 12", "url": "https://x/PROJ-12"}]}],
    "referencias": [{"tipo": "Confluence", "titulo": "Reglas de pagos", "url": "https://x/wiki/pagos", "origen": "PROJ-12 (comentario)", "leido": True}],
    "mapas": [{"titulo": "Arquitectura", "tipo": "arquitectura", "descripcion": "Capas y externos.",
               "nodos": [{"id": "web", "etiqueta": "Front web", "grupo": "Frontend"},
                         {"id": "api", "etiqueta": "API", "grupo": "Backend", "nota": "REST"},
                         {"id": "db", "etiqueta": "PostgreSQL", "grupo": "Datos"}],
               "enlaces": [{"de": "web", "a": "api", "etiqueta": "HTTPS"}, {"de": "api", "a": "db"}]},
              {"titulo": "Cómo funciona", "tipo": "flujo",
               "nodos": [{"id": "s1", "etiqueta": "Carrito"}, {"id": "s2", "etiqueta": "Pago"}, {"id": "s3", "etiqueta": "Confirma"}],
               "enlaces": [{"de": "s1", "a": "s2"}, {"de": "s2", "a": "s3"}, {"de": "s3", "a": "s2", "etiqueta": "reintenta"}]}],
    "fuentes": [{"fuente": "Jira PROJ", "tipo": "Gestión", "alcance": "épicas y backlog", "estado": "leida"},
                {"fuente": "Figma", "tipo": "Diseño", "estado": "no_accesible", "motivo": "conector figma no activo"}],
    "modulos": [{"nombre": "Checkout", "descripcion": "Pago con tarjeta", "estado": "En desarrollo",
                 "avance": {"hechas": 6, "total": 8}, "fuente": "PROJ-3"}],
    "actores": [{"rol": "Comprador", "puede": "comprar", "fuente": "PROJ-3"}],
    "flujos": [{"nombre": "Comprar", "pasos": "Carrito → Pago", "items": "PROJ-12", "fuente": "PROJ-3"}],
    "integraciones": [{"sistema": "Mercado Pago", "para_que": "cobros", "tipo": "API REST", "fuente": "wiki/Integraciones"}],
    "ambientes": [{"nombre": "QA", "url": "https://qa.tienda.com", "para_que": "pruebas", "fuente": "wiki/Ambientes"}],
    "backlog": {"por_estado": {"Por hacer": 40, "Hecho": 300}, "bugs_por_severidad": {"Crítica": 2, "Baja": 4},
                "sprint_actual": {"nombre": "Sprint 14", "inicio": "2026-10-13", "fin": "2026-10-24", "items": 18},
                "releases": [{"nombre": "2.4", "fecha": "2026-11-05", "estado": "Planificada", "fuente": "Jira"}]},
    "ambiguedades": [{"id": "AMB-01", "tipo": "Contradicción", "que": "Reembolso inmediato vs. 48 h hábiles",
                      "fuentes": ["PROJ-45", "Confluence 'Reglas de pagos'"], "impacto": "Alta", "pregunta": "P-01"}],
    "preguntas": [{"id": "P-01", "pregunta": "¿El reembolso es inmediato o tarda 48 h?", "a_quien": "PO", "prioridad": "Crítica",
                   "por_que": "bloquea los casos de reembolso", "relacionado": "AMB-01"}],
    "preguntas_arranque": ["¿Cómo se piden datos de prueba en QA?"],
    "riesgos": [{"riesgo": "Sin sandbox de pagos", "nivel": "Alto", "motivo": "no hay ambiente", "mitigacion": "pedirlo"}],
    "glosario": [{"termino": "SKU", "definicion": "código de producto", "fuente": "wiki/Glosario"}],
    "proximos_pasos": [{"paso": "Onboarding", "agente": "guia-onboarding", "pedido": "Armá el onboarding de Ana"}],
    "faltantes": ["No hay conector de Figma."],
}


def _escribir(carpeta, datos):
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / "investigacion.json"
    archivo.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return archivo


def test_html_y_md(tmp_path):
    archivo = _escribir(tmp_path / "proj", RELEVAMIENTO)
    assert inv.main([str(archivo), "--input", str(tmp_path / "doc")]) == 0
    html = (tmp_path / "proj" / "informe-investigacion.html").read_text(encoding="utf-8")
    assert "Relevamiento de Tienda online" in html
    assert "AMB-01" in html and "P-01" in html and "Reembolso inmediato" in html
    assert "PROJ-45 <b>vs.</b> Confluence" in html  # las dos fuentes de la contradicción, juntas
    assert "No accesible" in html and "1/2" in html and "6/8 · 75 %" in html
    assert "Cambios desde el relevamiento anterior" not in html  # es el primero
    # Recorrido del tablero: épicas/historias/tareas, con links clickeables
    assert "Épicas, historias y tareas" in html and "Links de referencia" in html
    assert "Backlog recorrido" in html and "Relevado desde el tablero" in html
    assert 'href="https://x/PROJ-12"' in html and "Reglas de pagos" in html and "cuotas hasta 12" in html
    md = (tmp_path / "proj" / "informe-investigacion.md").read_text(encoding="utf-8")
    assert "Tienda online" in md and "PROJ-45 vs. Confluence" in md and "> No hay conector de Figma." in md
    assert "## Épicas, historias y tareas" in md and "## Links de referencia" in md
    assert "[Reglas de pagos](https://x/wiki/pagos)" in md and "Recorrido del tablero: 2 épica" in md
    assert len(list((tmp_path / "proj" / "historial").iterdir())) == 1
    # Mapas conceptuales (SVG) en el informe
    assert html.count('class="mapa"') == 2 and "<svg viewBox" in html and "Arquitectura" in html and "Cómo funciona" in html
    assert "back" in html  # la arista de vuelta (reintenta) va punteada
    # Resumen breve
    resumen = (tmp_path / "proj" / "resumen.md").read_text(encoding="utf-8")
    assert "# Tienda online — resumen" in resumen and "Las 3 preguntas más urgentes" in resumen and "reembolso" in resumen.lower()
    # Presentación autocontenida
    pres = (tmp_path / "proj" / "presentacion-investigacion.html").read_text(encoding="utf-8")
    assert pres.startswith("<!doctype html>") and "De un vistazo" in pres and "Arquitectura" in pres
    assert pres.count('<section class="s"') >= 5 and "imprimí a PDF" in pres
    # Lo relevado queda como documentación del proyecto para los demás agentes, con el encabezado del índice
    doc = tmp_path / "doc" / "proyecto" / "investigacion"
    assert sorted(p.name for p in doc.iterdir()) == ["backlog.md", "decisiones-y-glosario.md", "dudas-y-riesgos.md",
                                                     "modulos-y-flujos.md", "resumen.md"]
    backlog = (doc / "backlog.md").read_text(encoding="utf-8")
    assert backlog.startswith("---\ntitulo: Épicas, historias y releases — Tienda online\ntipo: investigacion\nestado: investigacion\n")
    assert "PROJ-12" in backlog and "cuotas hasta 12" in backlog and "+====" in backlog  # tablas alineadas
    dudas = (doc / "dudas-y-riesgos.md").read_text(encoding="utf-8")
    assert "estado: sin-confirmar" in dudas and "AMB-01" in dudas and "FI-XX" in dudas
    indice = (tmp_path / "doc" / "INDICE.md").read_text(encoding="utf-8")
    assert "Investigación del proyecto" in indice and "sin-confirmar" in indice


def test_compara_con_el_relevamiento_anterior(tmp_path):
    carpeta = tmp_path / "proj"
    assert inv.main([str(_escribir(carpeta, RELEVAMIENTO)), "--sin-input"]) == 0
    nuevo = json.loads(json.dumps(RELEVAMIENTO))
    nuevo["ambiguedades"] = [{"id": "AMB-01", "tipo": "Vacío", "que": "No hay criterios para el cupón", "impacto": "Media"}]
    nuevo["preguntas"] = [{"id": "P-01", "pregunta": "¿El cupón se acumula con otras promos?", "prioridad": "Alta"}]
    import time
    time.sleep(1.1)  # el historial se nombra por segundo
    assert inv.main([str(_escribir(carpeta, nuevo)), "--sin-input"]) == 0
    html = (carpeta / "informe-investigacion.html").read_text(encoding="utf-8")
    assert "Cambios desde el relevamiento anterior" in html
    assert "No hay criterios para el cupón" in html and "Reembolso inmediato vs. 48 h hábiles" in html  # nueva y resuelta
    assert "Resuelta" in html and "Nueva" in html


def test_avisa_inconsistencias(capsys):
    d = {"proyecto": "X",
         "ambiguedades": [{"id": "AMB-01", "tipo": "Contradicción", "que": "a", "fuentes": ["solo una"], "pregunta": "P-09"},
                          {"id": "AMB-01", "tipo": "Rara", "que": "b", "impacto": "Altísima"}],
         "preguntas": [{"id": "P-01", "pregunta": "?", "prioridad": "Urgente"}],
         "fuentes": [{"fuente": "Jira", "estado": "leído"}]}
    avisos = inv.validar(d)
    texto = " ".join(avisos)
    assert "IDs repetidos AMB-01" in texto and "dos fuentes" in texto and "P-09" in texto
    assert "'Rara'" in texto and "'Altísima'" in texto and "'Urgente'" in texto and "'leído'" in texto
    assert "[aviso]" in capsys.readouterr().err


def test_requiere_proyecto(tmp_path):
    archivo = tmp_path / "x.json"
    archivo.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit):
        inv.main([str(archivo), "--sin-input"])


def test_historial_se_poda(tmp_path):
    for i in range(7):
        (tmp_path / "historial" / f"2026-10-0{i + 1}-000000").mkdir(parents=True)
    inv.guardar_historial(tmp_path, [], maximo=5)
    assert len(list((tmp_path / "historial").iterdir())) == 5

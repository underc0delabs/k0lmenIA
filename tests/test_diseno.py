"""Sistema de diseño de los reportes: barra lateral con índice, grilla bento, fuentes incrustadas y tablas interactivas."""
import _estilos_reporte as est


def test_pagina_con_indice_fuentes_y_buscador():
    body = (est.section("Resumen", "<p>x</p>") + est.two_col(est.section("Uno", "a"), est.section("Dos", "b"))
            + est.section("Resumen", "<p>y</p>", ancho=4))
    html = est.page("Informe", "Prueba", est.meta([("Historia", "HU-001")]), body)
    assert 'class="side"' in html and 'id="nav"' in html and 'id="buscar"' in html
    assert html.count('data-nav="Resumen"') == 2 and 'id="s-resumen"' in html and 'id="s-resumen-2"' in html  # ids únicos
    assert "grid-column:span 4" in html
    assert "@font-face" in html and "font/woff2;base64," in html  # Saira, Inter y JetBrains Mono incrustadas: se ve igual sin internet
    assert "https://" not in html.split("<body>")[0]  # nada se carga de internet


def test_indicadores_con_progreso_sparkline_y_estado_con_texto():
    k = est.kpi_tiles([("Aprobados", 14, "ok", "78 %", "", {"pct": 78}), ("Carga", "1,2 s", "", "", "reloj", {"serie": [3, 5, 2, 6]}),
                       ("Fallidos", 3, "bad")])
    assert 'style="width:78%"' in k and "<svg" in k and "✕ Crítico" in k and "✓ En orden" in k


def test_graficos_nuevos():
    assert "stroke-dasharray" in est.gauge(82, "puntaje")
    assert "linearGradient" in est.column_chart([("A", 3), ("B", 5)])
    assert est.sparkline([1]) == ""
    panel = est.donut_panel([(3, est.OK, "OK"), (1, est.CRITICO, "Mal")], 75, "ok")
    assert 'class="p"' in panel and "75 %" in panel


def test_evidencia_relativa_absoluta_y_faltante(tmp_path):
    import generar_reporte
    (tmp_path / "evidencia").mkdir()
    (tmp_path / "evidencia" / "cp-001.png").write_bytes(b"x")
    assert est.resolver_evidencia("evidencia/cp-001.png", tmp_path) == ("evidencia/cp-001.png", True)
    assert est.resolver_evidencia(str(tmp_path / "evidencia" / "cp-001.png"), tmp_path) == ("evidencia/cp-001.png", True)
    assert est.resolver_evidencia("evidencia/no.png", tmp_path)[1] is False
    html = generar_reporte.build_html({"casos": [
        {"id": "CP-001", "titulo": "a", "estado": "Aprobado", "evidencia": "evidencia/cp-001.png"},
        {"id": "CP-002", "titulo": "b", "estado": "Fallido", "evidencia": "evidencia/no.png"}]}, tmp_path)
    assert 'class="lb thumb s" href="evidencia/cp-001.png"' in html and "! Evidencia no encontrada" in html
    assert "id='lb'" in html or "lb.id='lb'" in html  # el visor es común a todos los reportes

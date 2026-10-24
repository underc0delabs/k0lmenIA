"""Métricas de uso de tokens: atribución por agente, deduplicación, costos y privacidad."""
import json

import metricas_tokens as mt


def _respuesta(mid, modelo, entrada, salida, lectura=0, escritura=0, ts="2026-10-14T12:00:00Z", herramientas=(), texto="secreto"):
    contenido = [{"type": "text", "text": texto}] + [{"type": "tool_use", "name": h, "input": {}} for h in herramientas]
    return json.dumps({"type": "assistant", "timestamp": ts, "message": {
        "id": mid, "model": modelo, "content": contenido,
        "usage": {"input_tokens": entrada, "output_tokens": salida, "cache_read_input_tokens": lectura,
                  "cache_creation_input_tokens": escritura, "cache_creation": {"ephemeral_5m_input_tokens": escritura}}}})


def _proyecto(tmp_path):
    base = tmp_path / "projects" / "E--repo"
    sub = base / "s1" / "subagents"
    sub.mkdir(parents=True)
    # la misma respuesta aparece en dos líneas (una por bloque): se cuenta una vez
    (base / "s1.jsonl").write_text("\n".join([
        json.dumps({"type": "user", "message": {"content": "hola"}}),
        _respuesta("m1", "claude-opus-5-5", 1000, 100, lectura=9000, herramientas=["Bash"]),
        _respuesta("m1", "claude-opus-5-5", 1000, 100, lectura=9000, herramientas=["Read"]),
        _respuesta("m2", "modelo-nuevo-x", 10, 10, ts="2026-10-13T10:00:00Z"),
    ]), encoding="utf-8")
    (sub / "agent-a1.jsonl").write_text(_respuesta("m3", "claude-sonnet-5-5", 2000, 500, escritura=4000), encoding="utf-8")
    (sub / "agent-a1.meta.json").write_text(json.dumps({"agentType": "generador-casos-manuales"}), encoding="utf-8")
    return base


def test_atribuye_deduplica_y_calcula_costos(tmp_path):
    regs = mt.recolectar(_proyecto(tmp_path))
    assert len(regs) == 3
    d = mt.agregar(regs)
    agentes = {a["agente"]: a for a in d["agentes"]}
    assert set(agentes) == {mt.PRINCIPAL, "generador-casos-manuales"}
    principal = agentes[mt.PRINCIPAL]
    assert principal["llamadas"] == 2 and principal["sin_precio"] == 1 and sorted(principal["herramientas"]) == ["Bash", "Read"]
    # Opus 5.5: 1000 × $4 + 100 × $20 + 9000 × $0.20 por millón
    assert abs(principal["costo_usd"] - (1000 * 4 + 100 * 20 + 9000 * 0.20) / 1e6) < 1e-9
    # Sonnet 5.5 con escritura de caché a 5 minutos (×1,25 la entrada)
    gen = agentes["generador-casos-manuales"]
    assert abs(gen["costo_usd"] - (2000 * 2 + 500 * 10 + 4000 * 2.5) / 1e6) < 1e-9
    assert d["resumen"]["sin_precio"] == 1 and any(o["tipo"] == "Sin precio" for o in d["oportunidades"])


def test_filtra_por_fecha_y_no_guarda_texto(tmp_path):
    from datetime import date
    regs = mt.recolectar(_proyecto(tmp_path), desde=date(2026, 10, 14))
    assert {r["modelo"] for r in regs} == {"claude-opus-5-5", "claude-sonnet-5-5"}
    assert "secreto" not in json.dumps(mt.agregar(regs))


def test_carpeta_del_proyecto_o_de_una_carpeta_padre(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    raiz = tmp_path / "E" / "repo"
    raiz.mkdir(parents=True)
    padre = str((tmp_path / "E").resolve())
    for c in (chr(92), "/", ":"):
        padre = padre.replace(c, "-")
    (tmp_path / "projects" / padre).mkdir(parents=True)
    assert mt.carpeta_transcripciones(raiz).name == padre


def test_cli_e_informe_y_candidatos(tmp_path, capsys):
    base = _proyecto(tmp_path)
    sub = base / "s1" / "subagents"
    for i in range(2, 7):
        (sub / f"agent-a{i}.jsonl").write_text(_respuesta(f"x{i}", "claude-sonnet-5-5", 100, 10), encoding="utf-8")
        (sub / f"agent-a{i}.meta.json").write_text(json.dumps({"agentType": "ejecutor-e2e"}), encoding="utf-8")
    salida = tmp_path / "out"
    assert mt.main(["--carpeta", str(base), "--salida", str(salida), "--nombre", "t"]) == 0
    d = json.loads((salida / "metricas.json").read_text(encoding="utf-8"))
    assert any(o["tipo"] == "Candidato a automatizar" and o["agente"] == "ejecutor-e2e" for o in d["oportunidades"])
    html = (salida / "informe-metricas.html").read_text(encoding="utf-8")
    assert "Costo por agente" in html and "secreto" not in html
    en = (salida / "informe-metricas.en.html").read_text(encoding="utf-8")
    assert "Cost per agent" in en and "Automation candidate" in en and "secreto" not in en


def test_sin_transcripciones_lo_dice(tmp_path, capsys):
    assert mt.main(["--carpeta", str(tmp_path / "no-existe"), "--salida", str(tmp_path / "o")]) == 0
    assert "No encuentro las transcripciones" in (tmp_path / "o" / "informe-metricas.html").read_text(encoding="utf-8")


def test_tablero_suma_uso_de_tokens(tmp_path):
    import tablero_calidad as tablero
    from pathlib import Path
    d = tmp_path / "output" / "metricas-tokens" / "general"
    d.mkdir(parents=True)
    (d / "metricas.json").write_text(json.dumps({"periodo": "x", "resumen": {"llamadas": 3, "costo_usd": 1.5, "pct_cache": 80},
                                                 "agentes": [{"agente": "analista-historias"}]}), encoding="utf-8")
    real = tablero.RAIZ
    try:
        tablero.usar_raiz(tmp_path)
        ex = tablero.extras()
    finally:
        tablero.usar_raiz(Path(real))
    assert ex["tokens"] == [{"nombre": "general", "periodo": "x", "costo_usd": 1.5, "pct_cache": 80, "agente_top": "analista-historias"}]

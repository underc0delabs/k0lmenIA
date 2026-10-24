# Seguridad estática (SCA y SAST)

Análisis de seguridad **estático y de solo lectura** del repositorio de la aplicación. Complementa el análisis **dinámico** (OWASP ZAP) de `herramientas/zap/`, que lo usan `analista-seguridad` y `pentester-web`.

- **`dependencias.py`** (`npm run dependencias`) — **SCA**: detecta los ecosistemas del proyecto (Node, Python, Java, Go, Ruby, PHP) y corre los escáneres disponibles (`npm audit`, `pip-audit`, `osv-scanner`) para listar vulnerabilidades conocidas (CVE) agregadas por severidad. Lo usa el `analista-dependencias`.
- **`sast.py`** (`npm run sast`) — **SAST + secretos**: trae un escáner de secretos integrado (en Python puro, siempre corre; redacta el valor) y, si está, corre `semgrep` para hallazgos de código (inyección, XSS, cripto, etc.). Lo usa el `analista-codigo-seguro`.

```bash
npm run dependencias -- --ruta C:/proyectos/mi-app --salida output/dependencias/mi-app/sca.json
npm run sast         -- --ruta C:/proyectos/mi-app --salida output/sast/mi-app/sast.json
```

Ambos son de **solo lectura**: no ejecutan ni modifican el proyecto, no instalan ni actualizan nada. Los informes HTML los arman `scripts/generar_informe_dependencias.py` y `scripts/generar_informe_sast.py` a partir del `analisis.json` que triagea el agente.

**Requisitos (opcionales)**: `npm` (Node), `pip install pip-audit` (Python), `osv-scanner` (multi-ecosistema) y `semgrep` (SAST). Si falta alguno, la herramienta lo avisa y sigue con lo que haya; el escáner de secretos no necesita nada. El `npm run doctor` chequea cuáles están.

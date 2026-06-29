# 🪖 Agentes k0lmena

**Agentes de QA para Claude Code** que aceleran las tareas del día a día del testing manual: analizar historias, escribir casos de prueba (manuales, BDD y de API), generar datos de prueba, redactar reportes de bug, ejecutar pruebas end-to-end en el navegador y armar reportes de resultados en HTML — todo en español.

> Pensado para QAs manuales. No hace falta saber programar: se trabaja conversando con Claude Code dentro de VS Code.

🌐 Web: https://qarmy.ar

▶️ YouTube: https://www.youtube.com/@QARMY-UC?sub_confirmation=1

💬 Canal de WhatsApp: https://whatsapp.com/channel/0029VaSzkgD1CYoTmiX8Uv26

---

## ¿Qué es esto?

Un repositorio con un equipo de **agentes especializados** en QA. Vos ponés un insumo (una historia, una observación de bug, un contrato de API) en la carpeta `input/`, le pedís a Claude Code lo que necesitás, y el agente correspondiente genera el artefacto en la carpeta `output/`.

Los **casos de prueba** se generan como planilla **Excel** (`.xlsx`), acompañada de un **informe de cobertura** en Markdown con ambigüedades y preguntas para el PO. El formato del reporte de bug lo definís editando su plantilla. Y si querés, esos casos se pueden **ejecutar en un navegador real** (con Playwright MCP) para obtener un **reporte de resultados en HTML**.

```
input/ → [ agente de QA ] → output/
                ↑
        plantillas/ + scripts/   (formato)
```

### Agentes disponibles

| Agente | Qué hace |
|--------|----------|
| 🔍 **Analista de historias** | Analiza historias y criterios de aceptación; detecta ambigüedades y arma preguntas de refinamiento |
| 🗺️ **Estratega de pruebas** | Arma el plan/estrategia (alcance, riesgos, tipos de prueba, criterios) como dashboard HTML en modo oscuro |
| 📝 **Casos manuales** | Genera los casos en Excel (.xlsx) y Markdown (.md), + un informe de cobertura (.md) con ambigüedades y preguntas para el PO |
| 🥒 **Casos BDD** | Genera escenarios en Gherkin (keywords en inglés, contenido en español) + un informe de cobertura por criterio (.md) |
| 🐞 **Reportes de bug** | Convierte notas sueltas en reportes profesionales, siguiendo tu plantilla |
| 🎲 **Datos de prueba** | Genera datos realistas (Markdown o CSV) |
| 🔌 **Casos de API** | Genera casos de prueba de API a partir de un contrato |
| ▶️ **Ejecutor E2E** | Ejecuta los casos/escenarios pedidos en un navegador real con Playwright MCP (headed o headless) y genera el reporte de la corrida con evidencia |
| 🧪 **Ejecutor de API** | Ejecuta una colección de Postman con Newman contra la API y genera el reporte de la corrida |
| 📊 **Reporte HTML** | Arma el reporte HTML (dashboard en modo oscuro) de una ejecución a partir de sus resultados |
| 🏁 **Informe de cierre** | Resume toda la ronda (resultados, bugs, recomendación go/no-go) en un dashboard HTML en modo oscuro |

---

## Requisitos

- **Claude Code** instalado.
- Una cuenta de Claude (plan **Pro**, **Max**, **Team** o **Enterprise**) o acceso por **API** de Anthropic. El plan gratuito no incluye Claude Code.
- **VS Code** (recomendado, aunque Claude Code corre en cualquier terminal).
- Para instalar por npm: **Node.js 18 o superior**.
- **Python 3** — lo usan los scripts que dan formato a las salidas: `scripts/generar_casos.py` (planilla `.xlsx` y `.md` de casos) y `scripts/formatear_tablas.py` (alinea las tablas de los `.md`). Instalan `openpyxl`/`tabulate` solo si faltan, o las instalás vos con `pip install -r requirements.txt`.
- **Para ejecutar pruebas E2E** (opcional): los navegadores de Playwright, que se instalan una sola vez con `npx playwright install` (en Linux, además `npx playwright install-deps`). Requiere Node.js.
- **Para ejecutar pruebas de API** (opcional): **Newman**, la CLI de Postman: `npm install -g newman` (requiere Node.js).

---

## Instalación

### 1. Instalar Claude Code

**Opción recomendada (instalador nativo, sin dependencias):**

- macOS / Linux:
  ```bash
  curl -fsSL https://claude.ai/install.sh | bash
  ```
- Windows (PowerShell): seguí la guía oficial en https://docs.claude.com/en/docs/claude-code/overview

**Alternativa con npm** (requiere Node.js 18+):
```bash
npm install -g @anthropic-ai/claude-code
```
> No uses `sudo`. Si te da un error de permisos, configurá un directorio global propio de npm (`~/.npm-global`).

Verificá la instalación:
```bash
claude --version
```

### 2. Clonar este repositorio

```bash
git clone https://github.com/QARMY/agentes-k0lmena.git
cd agentes-k0lmena
```

> Si hiciste un fork, reemplazá la URL por la de tu repositorio.

(Opcional) instalá las dependencias de los scripts de una:
```bash
pip install -r requirements.txt
```

### 3. Abrir en VS Code y lanzar Claude Code

```bash
code .
```
Abrí la terminal integrada de VS Code (no hace falta una extensión aparte) y ejecutá:
```bash
claude
```
La primera vez te va a pedir autenticarte en el navegador. Listo: Claude Code ya reconoce los agentes de la carpeta `.claude/agents/`.

### 4. (Opcional) Preparar la ejecución (E2E y API)

Solo si vas a **ejecutar** pruebas (no únicamente generarlas).

Para **E2E en el navegador**, instalá los navegadores de Playwright una vez:
```bash
npx playwright install
```
> En Linux puede pedirte además `npx playwright install-deps`.

Para **pruebas de API**, instalá Newman (la CLI de Postman):
```bash
npm install -g newman
```

Si la app/API que vas a probar pide **login o token**, copiá la plantilla de variables y completá tus datos (el `.env` no se sube al repo):
```bash
cp .env.example .env
```
Editá `.env` con la URL y las credenciales (`APP_URL`, `APP_USER`, `APP_PASSWORD`, `API_TOKEN`). Los agentes las leen de ahí; nunca las commitean.

---

## Cómo se usa

1. Poné tu insumo en la carpeta de `input/` que corresponda (hay un ejemplo en cada una para arrancar).
2. Pedile a Claude Code lo que necesites, en lenguaje natural. Él elige el agente adecuado.
3. Revisá el resultado en `output/`.

**Ejemplos de lo que podés pedir:**

- *"Analizá la historia HU-001 y decime qué ambigüedades tiene."*
- *"Armá el plan de pruebas de HU-001."* → genera el plan en HTML (modo oscuro) en `output/planes-de-prueba/`
- *"Generá los casos de prueba de HU-001."* → arma `casos-HU-001.xlsx`, `casos-HU-001.md` y `casos-HU-001-cobertura.md`
- *"Pasá la historia HU-001 a escenarios BDD."* → arma `HU-001-registro.feature` + `HU-001-cobertura.md`
- *"Tomá la observación de `input/bugs/` y armá el reporte de bug."*
- *"Generá datos de prueba para el formulario de registro."*
- *"Generá los casos de prueba de la API de autenticación."*
- *"Ejecutá SOLO el escenario de registro válido de HU-001 contra https://tu-app.com."* → corre la prueba en el navegador y genera el reporte HTML de esa corrida en `output/ejecuciones/`
- *"Ejecutá la colección de API de `input/api/` contra https://tu-api.com."* → corre la colección con Newman y genera el reporte HTML en `output/ejecuciones/`
- *"Armá el informe de cierre de las pruebas de HU-001."* → resume la ronda en un informe HTML (modo oscuro) en `output/informes-cierre/`

> 💡 El formato del **reporte de bug** lo definís en `plantillas/plantilla-reporte-bug.md`. Los **casos de prueba** salen como planilla Excel (referencia `plantillas/plantilla-casos-prueba.xlsx`, la arma `scripts/generar_casos.py`) más un informe de cobertura (referencia `plantillas/plantilla-cobertura.md`).

---

## Estructura del repositorio

```
agentes-k0lmena/
├── CLAUDE.md              # Contexto y estándares del proyecto (Claude Code lo lee siempre)
├── README.md
├── ARQUITECTURA.md        # Cómo está pensado el repo para crecer (agentes/skills/MCP/herramientas/scripts)
├── requirements.txt       # Dependencias de Python (openpyxl, tabulate)
├── .mcp.json              # Conexiones MCP activas (Playwright headed + headless)
├── .mcp.json.example      # Plantilla para más conexiones (Jira, Xray, etc.)
├── .env.example           # Plantilla de variables/credenciales (copiar a .env, que no se versiona)
├── .claude/
│   ├── agents/            # Los agentes de QA (el "quién")
│   └── skills/            # Skills (el "cómo"): técnicas de diseño + ejecución E2E y de API
├── herramientas/          # Herramientas externas de testing (Newman para API; JMeter/k6 a futuro)
├── plantillas/            # Referencias de formato (bug + casos .xlsx + cobertura .md)
├── scripts/               # Utilidades internas en Python (casos, reporte HTML, conversor Newman, plan e informe de cierre)
├── input/                 # Tus insumos (con un ejemplo en cada carpeta; incluye una colección de API en input/api/)
└── output/                # Lo que generan los agentes (ejecuciones, planes-de-prueba, informes-cierre…)
```

> 🧱 ¿Querés entender cómo está armado el repo o sumarle un skill / un server MCP a futuro? Mirá [`ARQUITECTURA.md`](ARQUITECTURA.md).

---

## Cómo agregar un agente nuevo

El proyecto está pensado para crecer. Para sumar un agente:

1. Creá un archivo en `.claude/agents/` (ej.: `mi-agente.md`).
2. Agregale el frontmatter con `name`, `description` y `tools`. La `description` es clave: es lo que usa Claude Code para saber cuándo invocarlo.
3. Escribí el cuerpo (rol, entradas, proceso, salida y reglas), en español.
4. Si genera un artefacto con formato propio, sumá su plantilla en `plantillas/` (o su script en `scripts/`) y su carpeta en `output/`.
5. Si genera tablas en un `.md`, hacelas pasar por `scripts/formatear_tablas.py` para que queden alineadas (es el estándar del repo).

Tomá los agentes existentes como referencia de estilo.

## Licencia

Licencia **MIT** — © 2026 **QARMY**. Podés usarlo, modificarlo y compartirlo libremente; se entrega sin garantías.

---

Hecho con 🪖 por la comunidad de **Underc0de**

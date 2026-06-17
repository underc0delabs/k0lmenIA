# 🪖 Agentes QARMY

**Agentes de QA para Claude Code** que aceleran las tareas del día a día del testing manual: analizar historias, escribir casos de prueba (manuales, BDD y de API), generar datos de prueba y redactar reportes de bug profesionales — todo en español.

> Pensado para QAs manuales. No hace falta saber programar: se trabaja conversando con Claude Code dentro de VS Code.

🌐 Web: https://qarmy.ar
▶️ YouTube: https://www.youtube.com/@QARMY-UC?sub_confirmation=1
💬 Canal de WhatsApp: https://whatsapp.com/channel/0029VaSzkgD1CYoTmiX8Uv26

---

## ¿Qué es esto?

Un repositorio con un equipo de **agentes especializados** en QA. Vos ponés un insumo (una historia, una observación de bug, un contrato de API) en la carpeta `input/`, le pedís a Claude Code lo que necesitás, y el agente correspondiente genera el artefacto en la carpeta `output/`.

Los **casos de prueba** se generan como planilla **Excel** (`.xlsx`), acompañada de un **informe de cobertura** en Markdown con ambigüedades y preguntas para el PO. El formato del reporte de bug lo definís editando su plantilla.

```
input/ → [ agente de QA ] → output/
                ↑
        plantillas/ + scripts/   (formato)
```

### Agentes disponibles

| Agente | Qué hace |
|--------|----------|
| 🔍 **Analista de historias** | Analiza historias y criterios de aceptación; detecta ambigüedades y arma preguntas de refinamiento |
| 📝 **Casos manuales** | Genera los casos en Excel (.xlsx) y Markdown (.md), + un informe de cobertura (.md) con ambigüedades y preguntas para el PO |
| 🥒 **Casos BDD** | Genera escenarios en Gherkin (keywords en inglés, contenido en español) + un informe de cobertura por criterio (.md) |
| 🐞 **Reportes de bug** | Convierte notas sueltas en reportes profesionales, siguiendo tu plantilla |
| 🎲 **Datos de prueba** | Genera datos realistas (Markdown o CSV) |
| 🔌 **Casos de API** | Genera casos de prueba de API a partir de un contrato |

---

## Requisitos

- **Claude Code** instalado.
- Una cuenta de Claude (plan **Pro**, **Max**, **Team** o **Enterprise**) o acceso por **API** de Anthropic. El plan gratuito no incluye Claude Code.
- **VS Code** (recomendado, aunque Claude Code corre en cualquier terminal).
- Para instalar por npm: **Node.js 18 o superior**.
- **Python 3** — lo usan los scripts que dan formato a las salidas: `scripts/generar_casos.py` (planilla `.xlsx` y `.md` de casos) y `scripts/formatear_tablas.py` (alinea las tablas de los `.md`). Instalan `openpyxl`/`tabulate` solo si faltan.

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
git clone https://github.com/QARMY/agentes-qarmy.git
cd agentes-qarmy
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

---

## Cómo se usa

1. Poné tu insumo en la carpeta de `input/` que corresponda (hay un ejemplo en cada una para arrancar).
2. Pedile a Claude Code lo que necesites, en lenguaje natural. Él elige el agente adecuado.
3. Revisá el resultado en `output/`.

**Ejemplos de lo que podés pedir:**

- *"Analizá la historia HU-001 y decime qué ambigüedades tiene."*
- *"Generá los casos de prueba de HU-001."* → arma `casos-HU-001.xlsx`, `casos-HU-001.md` y `casos-HU-001-cobertura.md`
- *"Pasá la historia HU-001 a escenarios BDD."* → arma `HU-001-login.feature` + `HU-001-cobertura.md`
- *"Tomá la observación de `input/bugs/` y armá el reporte de bug."*
- *"Generá datos de prueba para el formulario de login."*
- *"Generá los casos de prueba de la API de autenticación."*

> 💡 El formato del **reporte de bug** lo definís en `plantillas/plantilla-reporte-bug.md`. Los **casos de prueba** salen como planilla Excel (referencia `plantillas/plantilla-casos-prueba.xlsx`, la arma `scripts/generar_casos.py`) más un informe de cobertura (referencia `plantillas/plantilla-cobertura.md`).

---

## Estructura del repositorio

```
agentes-qarmy/
├── CLAUDE.md              # Contexto y estándares del proyecto (Claude Code lo lee siempre)
├── README.md
├── .claude/agents/        # Los agentes de QA
├── plantillas/            # Referencias de formato (bug + casos .xlsx + cobertura .md)
├── scripts/               # Scripts de formato (casos .xlsx/.md + normalizador de tablas)
├── input/                 # Tus insumos (con un ejemplo en cada carpeta)
└── output/                # Lo que generan los agentes
```

---

## Cómo contribuir

¿Querés sumar un agente nuevo a la comunidad?

1. Creá un archivo en `.claude/agents/` (ej.: `mi-agente.md`).
2. Agregale el frontmatter con `name`, `description` y `tools`. La `description` es clave: es lo que usa Claude Code para saber cuándo invocarlo.
3. Escribí el cuerpo (rol, entradas, proceso, salida y reglas), en español.
4. Si genera un artefacto con formato propio, sumá su plantilla en `plantillas/` (o su script en `scripts/`) y su carpeta en `output/`.
5. Abrí un Pull Request.

Tomá los agentes existentes como referencia de estilo.

---

Hecho con 🪖 por la comunidad **QARMY** · https://qarmy.ar

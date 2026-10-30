# k0lmenIA — plugin de Claude Code

Agentes de QA en español para Claude Code. Esta rama (`plugin`) la arma sola el repo
[underc0delabs/k0lmenIA](https://github.com/underc0delabs/k0lmenIA) en cada cambio: no se edita a mano.

## Instalar

Desde una terminal (una sola vez por persona):

```
claude plugin marketplace add underc0delabs/k0lmenIA
claude plugin install k0lmenia@k0lmenia
```

O adentro de Claude Code: `/plugin marketplace add underc0delabs/k0lmenIA` y `/plugin install k0lmenia@k0lmenia`.

Después abrí Claude Code en la carpeta de tu proyecto y escribí **`/k0lmenia:empezar`**: prepara el proyecto, revisa
que esté todo instalado, te ayuda a conectar tus herramientas y te sugiere por dónde arrancar.

(Si lo instalaste antes con `underc0delabs/k0lmenIA#plugin`, sigue funcionando igual.)

## Qué instala y dónde

El código (agentes, skills, scripts y herramientas) queda en la caché de Claude Code. En tu proyecto, `k0lmenia init` (o
`/k0lmenia:empezar`) deja lo tuyo: `input/` con los mismos ejemplos que el repo, `output/` con los informes y el portal, el
`.env`, `TAREAS.md`, tu copia de k0lmena y, en `.claude/settings.json`, los mismos permisos que el repo clonado. Nunca pisa
un archivo que ya existe. Es lo mismo que clonar el repo; solo no viajan la web y el PDF (están online), los tests del repo
y los evals de los agentes.

## Actualizar

Cada cambio en el repo se publica solo en esta rama. Para recibirlo:

- **Automático** (recomendado): `/plugin` → Marketplaces → `k0lmenia` → *Enable auto-update*. Una sola vez por persona.
- **A mano**: `/plugin marketplace update k0lmenia`.

Eso actualiza agentes, skills, scripts y herramientas. El framework de automatización (`herramientas/k0lmena/` de tu
proyecto) se actualiza con `k0lmenia actualizar`; Claude te avisa al iniciar la sesión cuando hay una versión nueva.
Tus pruebas (features, steps, locators) no se tocan, y si modificaste un archivo del framework, la versión nueva queda
al lado como `.nuevo` para que la compares. Tus datos (`input/`, `output/`, `.env`) viven en tu proyecto y no se tocan.

Para todo el equipo, en el `.claude/settings.json` del proyecto:

```json
{
  "extraKnownMarketplaces": {"k0lmenia": {"source": {"source": "github", "repo": "underc0delabs/k0lmenIA"}}},
  "enabledPlugins": {"k0lmenia@k0lmenia": true}
}
```

Cada persona lo instala una vez con `claude plugin install k0lmenia@k0lmenia --scope project`.

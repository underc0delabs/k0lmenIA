# k0lmenIA — plugin de Claude Code

Agentes de QA en español para Claude Code. Esta rama (`plugin`) la arma sola el repo
[underc0delabs/k0lmenIA](https://github.com/underc0delabs/k0lmenIA) en cada cambio: no se edita a mano.

## Instalar

En Claude Code:

```
/plugin marketplace add underc0delabs/k0lmenIA#plugin
/plugin install k0lmenia@k0lmenia
```

Después, en la carpeta de tu proyecto: `k0lmenia init` (crea `input/`, `output/`, el `.env` y copia k0lmena para tus
pruebas automatizadas) y `k0lmenia doctor` (revisa que esté todo).

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
  "extraKnownMarketplaces": {"k0lmenia": {"source": {"source": "github", "repo": "underc0delabs/k0lmenIA", "ref": "plugin"}}},
  "enabledPlugins": {"k0lmenia@k0lmenia": true}
}
```

Cada persona lo instala una vez con `claude plugin install k0lmenia@k0lmenia --scope project`.

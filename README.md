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

`/plugin marketplace update k0lmenia` (o activá la actualización automática en `/plugin` → Marketplaces). Tus datos
(`input/`, `output/`, `.env`, tus pruebas en `herramientas/k0lmena/`) viven en tu proyecto y no se tocan.

Para todo el equipo, en el `.claude/settings.json` del proyecto:

```json
{
  "extraKnownMarketplaces": {"k0lmenia": {"source": {"source": "github", "repo": "underc0delabs/k0lmenIA", "ref": "plugin"}}},
  "enabledPlugins": {"k0lmenia@k0lmenia": true}
}
```

Cada persona lo instala una vez con `claude plugin install k0lmenia@k0lmenia --scope project`.

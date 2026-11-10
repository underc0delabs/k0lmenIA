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

## Planes

El core es gratis. **K0lmenIA Pro** y **K0lmenIA Empresa** se suman como plugins aparte (`k0lmenia-pro` y
`k0lmenia-empresa`) para quien tiene acceso a su repo. **`/k0lmenia:setup`** te muestra qué plan tenés, a cuáles tenés
acceso y qué suma cada uno, e instala los que te corresponden. Desde una terminal: `k0lmenia planes`.

## Qué instala y dónde

El código (agentes, skills, scripts y herramientas) queda en la caché de Claude Code. En tu proyecto, `k0lmenia init` (o
`/k0lmenia:empezar`) deja lo tuyo: `input/` con los mismos ejemplos que el repo, `output/` con los informes y el portal, el
`.env`, `TAREAS.md`, tu copia de k0lmena y, en `.claude/settings.json`, los mismos permisos que el repo clonado. Nunca pisa
un archivo que ya existe.

## Actualizar

- **Automático** (recomendado): `/plugin` → Marketplaces → `k0lmenia` → *Enable auto-update*. Una sola vez por persona.
- **A mano**: `/plugin marketplace update k0lmenia`.

El framework de automatización (`herramientas/k0lmena/` de tu proyecto) se actualiza con `k0lmenia actualizar`; Claude te
avisa al iniciar la sesión cuando hay una versión nueva. Tus pruebas y tus datos (`input/`, `output/`, `.env`) no se tocan.

Para todo el equipo, en el `.claude/settings.json` del proyecto:

```json
{
  "extraKnownMarketplaces": {"k0lmenia": {"source": {"source": "github", "repo": "underc0delabs/k0lmenIA"}}},
  "enabledPlugins": {"k0lmenia@k0lmenia": true}
}
```

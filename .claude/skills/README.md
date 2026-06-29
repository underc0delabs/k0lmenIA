# Skills

Los **skills** son conocimiento empaquetado que Claude Code carga **on-demand** (solo cuando hace falta, sin pesar en el contexto si no se usan). Sirven para encapsular el "cómo" de una capacidad reutilizable que varios agentes pueden aprovechar.

## Skills disponibles

- **`tecnicas-de-diseno/`** — técnicas formales de diseño de casos de caja negra (clases de equivalencia, valores límite, tabla de decisión, transición de estados, pairwise). Sirve para derivar casos más completos al generar pruebas manuales, BDD o de API.
- **`ejecucion-e2e/`** — cómo ejecutar pruebas E2E en el navegador con Playwright MCP (modo headed/headless, ubicar elementos por accesibilidad, esperas para evitar flakiness, evidencia). Lo usa el agente `ejecutor-e2e`.
- **`ejecucion-api/`** — cómo ejecutar pruebas de API con Newman (la CLI de Postman): correr una colección, escribir validaciones, manejar base_url y token, e interpretar los resultados. Lo usa el agente `ejecutor-api`.

## Cómo agregar uno

Creá una carpeta en `.claude/skills/` con un `SKILL.md` adentro:

```
.claude/skills/
└── mi-skill/
    ├── SKILL.md          # obligatorio: frontmatter (name, description) + instrucciones
    ├── references/       # opcional: detalle que se carga solo si hace falta
    └── scripts/          # opcional: scripts que el skill ejecuta
```

El `description` del frontmatter es lo que usa Claude Code para decidir cuándo cargar el skill. Más detalle en [`../../ARQUITECTURA.md`](../../ARQUITECTURA.md).

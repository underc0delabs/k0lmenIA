// Cucumber configuration (dynamic).
//
// Migrated from cucumber.json to JavaScript so the parallelism can be toggled
// from the environment (.env). The profile shape is otherwise identical.
//
// PARALLEL env var:
//   (empty) | 0 | 1 | false | off | no  -> sequential (single process)
//   on | true | yes                     -> auto (one worker per CPU core)
//   N (>1)                              -> N parallel workers
require('./env'); // .env único de la raíz de k0lmenIA

const resolveParallel = () => {
  const raw = (process.env.PARALLEL ?? '').trim().toLowerCase();
  if (!raw || ['0', '1', 'false', 'off', 'no'].includes(raw)) return 0;
  if (['on', 'true', 'yes', 'auto'].includes(raw)) {
    // "auto": use the number of logical CPUs (min 2).
    const cpus = require('os').cpus()?.length || 2;
    return Math.max(2, cpus);
  }
  const n = Number(raw);
  return Number.isFinite(n) && n > 1 ? Math.floor(n) : 0;
};

const parallel = resolveParallel();

// TAGS env var: filtra escenarios por tag (ej. TAGS=@HU-001). Vacío = todos.
// Los escenarios marcados @bloqueado (pasos que no se pudieron mapear) nunca corren.
const rawTags = (process.env.TAGS ?? '').trim();
const tags = rawTags ? `(${rawTags}) and not @bloqueado` : 'not @bloqueado';

// Steps compartidos por todas las suites: variables de escenario y verificaciones de base de datos.
const pasosComunes = ['tools/variables.ts', 'tools/bd/bd.steps.ts'];

const common = {
  requireModule: ['ts-node/register'],
  timeout: 60000,
  tags,
  formatOptions: {
    snippetInterface: 'async-await',
  },
};

module.exports = {
  web: {
    ...common,
    retry: 1,
    paths: ['web/features/*.feature'],
    require: ['web/steps/*.ts', ...pasosComunes],
    parallel,
    format: [
      ['html', 'reports/web/front-report.html'],
      'summary',
      'progress-bar',
      'json:reports/web/cucumber-report.json',
    ],
  },

  api: {
    ...common,
    paths: ['api/features/*.feature'],
    require: ['api/steps/*.ts', ...pasosComunes],
    parallel,
    format: [
      ['html', 'reports/api/api-report.html'],
      'summary',
      'progress-bar',
      'json:reports/api/cucumber-report.json',
    ],
  },

  // Debug always runs sequentially so breakpoints / logs are readable.
  debug: {
    ...common,
    paths: ['web/features/*.feature'],
    require: ['tools/debug/debugHook.ts', 'web/steps/*.ts', ...pasosComunes],
    parallel: 0,
    format: [
      ['html', 'reports/web/front-report-debug.html'],
      'summary',
      'progress-bar',
      'json:reports/web/cucumber-report-debug.json',
    ],
  },
};

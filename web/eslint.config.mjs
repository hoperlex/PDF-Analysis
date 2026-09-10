import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';

/**
 * FSD boundary rules for `web/`.
 *
 * Layer order, strictly downward: app / _app -> _pages -> widgets -> features ->
 * entities -> shared. A layer may import the layers below it and nothing else, and it
 * may only reach a sibling slice through that slice's public API — `@/entities/project`,
 * never `@/entities/project/model/store`.
 *
 * Raw HTTP exists in exactly one place: `src/shared/api/**`. Everywhere else `fetch`,
 * `XMLHttpRequest` and any HTTP library are restricted identifiers, so a slice that
 * wants to talk to the API has to go through the generated client.
 *
 * The fixtures under `tests/guards/fixtures/**` deliberately violate these rules. They
 * are ignored by the default run and linted on purpose by the boundary guard test,
 * which asserts that ESLint goes red on them.
 */

const LAYER_BELOW = {
  _pages: ['widgets', 'features', 'entities', 'shared'],
  widgets: ['features', 'entities', 'shared'],
  features: ['entities', 'shared'],
  entities: ['shared'],
  shared: [],
};

const ALL_LAYERS = ['_app', '_pages', 'widgets', 'features', 'entities', 'shared'];

/** Build the `no-restricted-imports` patterns that forbid every upward import. */
function upwardBans(layer) {
  const allowed = new Set(LAYER_BELOW[layer]);
  return ALL_LAYERS.filter((other) => other !== layer && !allowed.has(other)).map(
    (other) => ({
      group: [`@/${other}`, `@/${other}/*`, `@/${other}/**`],
      message:
        `FSD boundary: \`${layer}\` may not import \`${other}\`. Imports run downward ` +
        `only: app/_app -> _pages -> widgets -> features -> entities -> shared.`,
    }),
  );
}

/** Forbid reaching past a slice's public API, e.g. `@/entities/project/model/x`. */
const DEEP_IMPORT_BANS = ['_pages', 'widgets', 'features', 'entities'].map((layer) => ({
  group: [`@/${layer}/*/*`, `@/${layer}/*/**`],
  message:
    `FSD boundary: import the slice public API \`@/${layer}/<slice>\`, not a path inside ` +
    `it. A deep import couples you to another owner's internals.`,
}));

const HTTP_BANS = [
  {
    group: ['axios', 'axios/*', 'got', 'node-fetch', 'superagent', 'ky'],
    message:
      'Transport boundary: HTTP lives only in `src/shared/api`. Import the generated ' +
      'client instead of an HTTP library.',
  },
];

const RESTRICTED_HTTP_GLOBALS = [
  {
    name: 'fetch',
    message:
      'Transport boundary: raw `fetch` is allowed only inside `src/shared/api`. Use the ' +
      'generated client.',
  },
  {
    name: 'XMLHttpRequest',
    message: 'Transport boundary: raw `XMLHttpRequest` is never allowed in this app.',
  },
];

export default tseslint.config(
  {
    ignores: [
      '.next/**',
      'node_modules/**',
      'next-env.d.ts',
      'tests/guards/fixtures/**',
      'src/shared/api/generated/**',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      eqeqeq: ['error', 'always'],
      'no-console': ['error', { allow: ['warn', 'error'] }],
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
    },
  },
  // Every layer: no deep imports, no HTTP library.
  {
    files: ['src/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': [
        'error',
        { patterns: [...DEEP_IMPORT_BANS, ...HTTP_BANS] },
      ],
      'no-restricted-globals': ['error', ...RESTRICTED_HTTP_GLOBALS],
    },
  },
  // Per-layer upward bans, layered on top of the shared pattern list.
  ...Object.keys(LAYER_BELOW).map((layer) => ({
    files: [`src/${layer}/**/*.{ts,tsx}`],
    rules: {
      'no-restricted-imports': [
        'error',
        { patterns: [...DEEP_IMPORT_BANS, ...HTTP_BANS, ...upwardBans(layer)] },
      ],
    },
  })),
  // `src/shared/api/**` is the one place raw HTTP is legal.
  {
    files: ['src/shared/api/**/*.ts'],
    rules: { 'no-restricted-globals': 'off' },
  },
  // Node-side tooling and tests.
  {
    files: ['scripts/**/*.mjs', 'tests/**/*.ts', '*.config.{ts,mjs}'],
    languageOptions: { globals: { ...globals.node } },
    rules: {
      'no-console': 'off',
      'no-restricted-globals': 'off',
    },
  },
);

import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    // Guards shell out to ESLint; give them room without being generous.
    testTimeout: 120_000,
    hookTimeout: 120_000,
    // A single fork keeps the reported order stable and keeps two suites from racing on
    // the same temp directories.
    pool: 'forks',
    poolOptions: { forks: { singleFork: true } },
  },
});

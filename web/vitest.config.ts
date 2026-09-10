import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    // Guards shell out to `node` and `eslint`; give them room without being generous.
    testTimeout: 120_000,
    hookTimeout: 120_000,
    // Determinism probes write into their own temp directories; running them in
    // parallel is safe, but a single fork keeps the reported order stable.
    pool: 'forks',
    poolOptions: { forks: { singleFork: true } },
  },
});

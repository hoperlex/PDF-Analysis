import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

export default defineConfig({
  // tsconfig sets jsx: "preserve", which is correct for Next: it hands JSX to the Next
  // compiler untouched. vitest's esbuild reads the same tsconfig and takes "preserve" as
  // the CLASSIC runtime, so it emits React.createElement against a React binding nothing
  // imports, and every shared/ui component throws "React is not defined" the moment a
  // test invokes it. B8 diagnosed it; B7 hit the same wall from the other side and
  // reported it as "no component is render-tested". Pinning the automatic runtime here
  // changes only how the test transform emits JSX - the Next build still reads
  // jsx: "preserve" from tsconfig and is unaffected.
  esbuild: { jsx: 'automatic' },

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

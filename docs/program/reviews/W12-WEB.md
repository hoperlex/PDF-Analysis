# `W12-WEB` — mutation sweep of `web/src`

Session `W12-WEB`, wave 12 stage A. Tests only; no product code changed.

- **HEAD on arrival**: `3ebe34dbdeda5873e51c8067d227a4c41e28a025` (`merge: two tests-only
  streams for wave 12 stage A`), worktree `/root/w12web`, branch `agent/w12-web` off
  `origin/dev`.
- **Started**: 2026-09-17 11:29:45 +05:00.
- Baseline before any work: `npx vitest run` in `web/` → **289 passed / 24 files**.

## 1. The harness

`make mutation-copy` has no vitest equivalent, and the brief is right that one should not
be pretended. The obstacle is not the alias — it is that the web suite reaches `web/src`
by **two different routes**, and a harness that only redirects one of them produces
silent false greens:

1. `tests/unit/**` and `tests/contract/csv-columns` import through the `@` alias that
   `web/vitest.config.ts` maps to `./src`.
2. `tests/guards/**` and two contract suites read `web/src` **as text**, resolving their
   root from `tests/guards/lib/repo.ts`:
   `WEB_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..','..','..')`.

A path-alias-only harness (copy `src`, point `@` at the copy) leaves route 2 reading the
*pristine* tree. That is exactly failure mode 4 in the dispatch, and I hit it: the first
prototype had `@` resolving to `/root/w12web-mut/src` while `WEB_ROOT` still pointed at
`/root/w12web/web`. Every source-scanning guard would have been green against a tree that
still had the defect.

### Mechanism actually used

A **full copy of the web tree plus the authorities the suites read**, rebuilt from the
worktree before every single mutation (`/root/w12web-mut/rebuild.sh`):

```
/root/w12web-mut/repo/web/{src,tests,scripts,openapi,package.json,package-lock.json,
                           .nvmrc,.npmrc,FRONTEND_LOCK.json,eslint.config.mjs,
                           tsconfig.json,vitest.config.ts,next.config.mjs,docs}
/root/w12web-mut/repo/web/node_modules  -> symlink to /root/w12web/web/node_modules
/root/w12web-mut/repo/contracts/api/v1/openapi.json
/root/w12web-mut/repo/docs/program/P02_SEAMS.md
```

vitest runs with `cwd=/root/w12web-mut/repo/web` and the tree's **own committed**
`vitest.config.ts`, so the `@` alias resolves relative to the copy and `import.meta.url`
inside `tests/guards/lib/repo.ts` resolves into the copy as well. Both routes move
together. No tracked file in `/root/w12web` is ever edited.

### Evidence the mutated tree is the one under test

The vitest equivalent of printing `auditmanager.__file__`. A probe suite
(`/root/w12web-mut/provenance.probe.test.ts`, copied into the mutation tree at
`tests/probe/` by `rebuild.sh`; **not** committed to the repository, because it must fail
outside the harness) proves both routes at runtime:

- **Route 1 (import)** — it calls `assertNever` from `@/shared/lib/assert-never`, catches
  the throw and reads the module's own frame out of the V8 stack:

  ```
  PROVENANCE module frame: at assertNever (/root/w12web-mut/repo/web/src/shared/lib/assert-never.ts:10:9)
  ```

  The stack frame is emitted by the loader, not by anything the test declares, so it is
  the imported module reporting its own file — `__file__`'s exact analogue.

- **Route 2 (source scan)** — it imports `WEB_ROOT` and `REPO_ROOT` from the *suite's own*
  `tests/guards/lib/repo.ts`, the same bindings every scanning guard uses:

  ```
  PROVENANCE WEB_ROOT: /root/w12web-mut/repo/web REPO_ROOT: /root/w12web-mut/repo
  ```

Both probe assertions compare against `process.env.MUT_WEB_ROOT`, supplied by the driver,
so the probe **fails** if either route leaks back to `/root/w12web`. Every row of the
table below was produced by a run in which both probe assertions passed.

### Baseline of the unmutated copy

The copy with no mutation applied: **291 passed** — the repository's 289, plus the 2 probe
assertions. The copy mechanism reddens nothing by itself.

### Driver

`/root/w12web-mut/mut.py <label> <path> <old> <new>` rebuilds the copy, applies exactly
one textual substitution, refuses to continue if the literal is absent or ambiguous,
**prints the before/after line so the mutation is read back for meaning**, then runs the
suite and names the failing tests by full test name.

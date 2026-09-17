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

## 2. The sweep

Every row below is one single-substitution mutation of the copied tree, applied and run on
its own from a freshly rebuilt copy. `KILLED` names the tests that went red; `SURVIVED`
means the whole suite stayed green; `TIMEOUT` means no test went red and the suite never
finished (see §2.1).

### 2.1 Batch 1 — `run-presentation.ts` and `run-state.ts`

| # | Mutation | Result | What refused |
|---|---|---|---|
| RP-01 | `PROVIDER_MODE_UNKNOWN` sentinel becomes `'live'` | KILLED | `run/provider-mode` — *renders unknown for an absent, null, empty or unrecognised value*, *offers the badge only the two qualifiers it declares*, *covers exactly the contract value set…*, *says an unknown provenance is not treated as live* |
| RP-02 | unrecognised provider mode passes through unnarrowed | KILLED | `run/provider-mode` — *renders unknown for an absent, null, empty or unrecognised value* |
| RP-03 | `badgeProviderMode` passes `unknown` to the badge | KILLED | `run/provider-mode` — *offers the badge only the two qualifiers it declares* |
| RP-04 | the `recorded` caption claims live-call evidence | KILLED | `run/provider-mode` — *says a recorded run is not evidence of a live provider call* |
| RP-05 | `interruptedReason` stops treating `''` as absent | KILLED | `run/provider-mode` — *treats an empty or null reason as no reason* |
| RP-06 | `isRunAnimating` ignores the interrupted reason | KILLED | `run/provider-mode` — *stops on a non-terminal reading that carries an OD-10 interrupted reason* |
| RP-07 | `isRunAnimating` keeps animating a terminal run | KILLED | `run/provider-mode` — *stops on every terminal state* |
| RP-08 | a `partial` run is classified as `published` | KILLED | `run/vocabulary` — *gives published, partial and failed three different outcome kinds*, *reports the recorded degradation set on a partial run* |
| RP-09 | a failed run drops its `terminal_reason` | KILLED | `run/vocabulary` — *reports the terminal reason on a failed run* |
| **RP-10** | **a failed run drops its `interrupted` reason** | **SURVIVED** | — |
| RP-11 | `PC01_STAGE_IDS` order swapped | KILLED | `run/stage-rows` ×2, `run/vocabulary` ×1 |
| RP-12 | `PC01_STAGE_IDS` loses `text_analysis` | KILLED | `run/stage-rows` ×4 |
| RP-13 | `stageRows` marks scheduled stages unexpected | KILLED | `run/stage-rows` — *always produce four rows…* |
| RP-14 | `stageRows` drops unscheduled stages the run reported | KILLED | `run/stage-rows` — *appends it after the four, flagged as unexpected* |
| RP-15 | `stageRows` invents `succeeded` for an unreported stage | KILLED | `run/stage-rows` ×2 |
| **RS-01** | **`TERMINAL_RUN_STATES` loses `cancelled`** | **TIMEOUT** | nothing red; the suite hangs |
| RS-02 | `EXPORTABLE_RUN_STATES` admits `failed` | KILLED | `review/provider-mode`, `run/provider-mode` |
| RS-03 | `EXPORTABLE_RUN_STATES` drops `partial` | KILLED | `export/export-panel` and others |
| **RS-04** | **`stageCarriesError` always returns `false`** | **SURVIVED** | — |
| **RS-05** | **`isTerminalRunState` always returns `false`** | **TIMEOUT** | nothing red; the suite hangs |

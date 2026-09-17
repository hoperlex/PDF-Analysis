# W16-WEB — closing D-1.5, the named exception to PC-01's certification

**Session** `W16-WEB`. **Branch** `agent/w16-web`, from `origin/dev`.
**HEAD on arrival** `315de258306053b0b6ba73529a34fe0a50794a29` — `merge: the clean-lane
breaker, and the two infra lines W15-AUTH stopped at`.

Owns `web/**` and this file. Touched `web/tests/**` and this file, and nothing else: no
`src/`, no `contracts/`, no `infra/`, no `Makefile`. **`web/FRONTEND_LOCK.json` is
unchanged**, as are `web/package.json` and `web/package-lock.json` — no dependency was
added and no generated file was touched.

## 1. The answer in one paragraph

`D-1.5` said ten mutations inside the unreached region all survived. **Six of those ten
are now killed.** The four survivors are argued in §5: three are unreddenable by
construction and were already known to be, and the fourth is an effect-only adapter whose
loop is guarded elsewhere. Reachability went from 34 modules unreached to **0**, but that
is the weaker of the two numbers and it is not the answer to this row — twelve further
mutations, written against the new tests and listed in §4.2, were run to show the new
tests constrain rather than merely reach. **12 of 12 killed.** Frontend suite 498 → 592;
`make gate` exit **0**.

## 2. Reachability, measured rather than inherited

### 2.1 The figure the dispatch carried, and the figure the script actually prints

`DEBT_REGISTER.md` D-1.5 and my dispatch both state `110 76 34` — 34 of 110 modules,
1 352 of 7 604 lines, 18%. Running `W12-WEB` §11's script unchanged at my base:

```
cd /root/w16web/web && python3 -    # W12-WEB.md §11, verbatim
114 79 35
```

So the inherited triple is stale in every one of its three numbers, as the dispatch
warned. `web/src` is **8 273** lines now, not 7 604, and the unreached lines are 1 448,
not 1 352.

### 2.2 The script itself is wrong, and that is the more useful finding

`114 79 35` is not right either. The one module that appears to have entered the region
since wave 12 is `src/app/bff/v1/[...path]/route.ts`, `W15-AUTH`'s BFF handler — and it
**is** reached, by `web/tests/unit/api/server-credential.test.ts:97`:

```ts
const { GET } = await import('@/app/bff/v1/[...path]/route');
```

`W12-WEB`'s import pattern is

```python
re.findall(r"""(?:from|import)\s+['"]([^'"]+)['"]""", txt)
```

which demands whitespace between the keyword and the quote. A dynamic `import(` has a
parenthesis there, so **the script cannot see a dynamic import at all**, and it has been
under-reporting reachability for two waves. Adding the dynamic form:

```python
DYNAMIC = re.compile(r"""(?:import|require)\s*\(\s*['"]([^'"]+)['"]\s*\)""")
```

| tree | W12 script (static only) | corrected (static + dynamic) |
|---|---|---|
| `315de25`, my base | `114 79 35`, 1 448 lines | **`114 80 34`, 1 352 lines** |
| `188cacc`, after this work | `114 114 0`, 0 lines | **`114 114 0`, 0 lines** |

Script: `/root/w16web-mut/reach2.py`, run from `web/`; it prints both rows so the two
methods are comparable in one command.

The corrected base figure is **34 modules, 1 352 lines** — the same 34 modules and the
same 1 352 lines `W12-WEB` listed at `3ebe34d`. The set is identical, module for module.

### 2.3 What that means for D-1.5's wording and for W15-AUTH §8.4

- **`W15-AUTH` §8.4 is correct and my dispatch's suspicion of it was the stale premise.**
  §8.4 claims "nothing this wave adds falls inside the unswept region". Measured: of the
  four modules `W15-AUTH` added, three are statically reached and the fourth is reached
  dynamically. The unswept region did not move. The dispatch told me to treat §8.4 as a
  claim rather than a measurement, which was right advice that happened to vindicate it.
- **D-1.5's percentage is stale.** 1 352 of 8 273 lines is **16.3%**, not 18%, and the
  denominator of modules is 114, not 110. The set is unchanged; the tree around it grew.
- `DEBT_REGISTER.md` is not mine to edit. The row's `Check:` line should point at a
  script that can see a dynamic import, or the next session to run it will re-derive
  `114 79 35` and conclude the region grew when it did not.

## 3. What was reached

Five new files, 94 new tests, no new dependency. `renderToStaticMarkup` over a
`QueryClientProvider`, exactly as `W12-WEB` §10 predicted — that prediction was checked
before anything was written on it, and it holds.

| file | reaches | tests |
|---|---|---|
| `web/tests/unit/screens/harness.ts` | the provider/seeding machinery, all of it | — |
| `web/tests/unit/screens/run-progress.test.ts` | `run-progress.tsx` (231 lines) | 41 |
| `web/tests/unit/screens/widgets.test.ts` | `upload-panel.tsx`, `project-list.tsx` | 13 |
| `web/tests/unit/screens/forms-and-pages.test.ts` | the three write forms, the four route screens, `app-frame.tsx` | 19 |
| `web/tests/unit/screens/routes.test.ts` | the five `app/**` route files, `layout.tsx`, the BFF handler | 14 |
| `web/tests/guards/upload-precheck-wiring.guard.test.ts` | the upload form's pre-check wiring | 7 |

Two things the harness needed that were not obvious, both now documented in the file that
needed them:

1. **A seeded query error renders as a spinner unless `retryOnMount: false`.** React
   Query computes an *optimistic* result for an unmounted observer, and `fetchState()`
   forces `status: 'pending'` and clears `error` whenever the query has no data and a
   fetch would start on mount. One server pass is always an unmounted observer. Without
   this, every error branch in the suite would have silently asserted against a loading
   state — a test that reaches a module and constrains nothing, which is the exact failure
   this row is about.
2. **`ProjectDetailPage` calls `useRouter()` before anything else** and throws "invariant
   expected app router to be mounted" with no provider above it. `AppRouterContext` from
   `next/dist/shared/lib/app-router-context.shared-runtime` is what Next's own provider
   publishes; it is imported in one place, and it is a deep import into `next/dist`, which
   is said out loud in the file rather than left for a reader to find.

**The route files earn their tests.** Four of the five are delegation-only and look like
nothing worth testing. That is the shape of the bug they can hold: a route that handed
`project_uid` to a prop named `runId` type-checks (both are `string`), renders a screen
that asks the server about the wrong thing, and is invisible to every component test,
because the component received exactly what it was asked for. `W-01` and `W-02` in §4.2
are that mutation, and both are red.

## 4. Mutations: killed and survived

### 4.1 `W12-WEB`'s ten, re-run

`/root/w16web-mut/sweep.py /root/w12web-mut/b8.json` — one substitution per mutation, read
back from disk, whole frontend suite, reverted and re-read. Log
`/root/w16web-logs/b8-rerun.log`. Tree verified clean afterwards.

| # | mutation | wave 12 | **wave 16** |
|---|---|---|---|
| U-01 | `run-progress` stops rendering `terminal_reason` | SURVIVED | **KILLED** |
| U-02 | `run-progress` keeps the activity indicator on a stopped run | SURVIVED | **KILLED** |
| U-03 | `run-progress` offers the review link for every run | SURVIVED | **KILLED** |
| U-04 | the upload form stops pre-checking the chosen file | SURVIVED | **KILLED** (guard, §5.2) |
| U-05 | the upload form submits a file the pre-check refused | SURVIVED | **KILLED** (guard, §5.2) |
| U-06 | the upload intent key is re-minted on every render | SURVIVED | SURVIVED |
| U-07 | the create-project intent key is re-minted on every render | SURVIVED | SURVIVED |
| U-08 | the start-run intent key is re-minted on every render | SURVIVED | SURVIVED |
| U-09 | the upload panel stops stating the envelope before the picker | SURVIVED | **KILLED** |
| U-10 | the run-status hook stops seeding from the cache in its effect | SURVIVED | SURVIVED |

**6 killed, 4 survived, 0 hung. Ten ran; none was inapplicable.**

`U-01` is the one D-1.5 named. It is red on three different catalog codes, and separately
red on the assertion that no *other* reason appears, so a mutation that prints any
constant — `redacted`, or the first code the suite happens to use — is red rather than
green.

### 4.2 Twelve more, written against the new tests

A suite that kills someone else's mutations has not shown that *its own* new assertions
can fail. `/root/w16web-mut/w16.json`, same harness, log `/root/w16web-logs/w16-sweep.log`:

| # | mutation | result |
|---|---|---|
| W-01 | the run route crosses its two parameters | KILLED |
| W-02 | the review route crosses its two parameters | KILLED |
| W-03 | the layout nests the frame outside the query provider | KILLED |
| W-04 | the unconfigured BFF answers 500 instead of 401 | KILLED |
| W-05 | the unconfigured BFF names the environment variable on the wire | KILLED |
| W-06 | the BFF drops a verb, making one operation unroutable | KILLED |
| W-07 | the project detail page weakens the address check | KILLED |
| W-08 | `run-progress` pins the provider-mode sentence to `live` | KILLED |
| W-09 | the project list renders a genuinely empty page as rows | KILLED |
| W-10 | the project list offers the next page with no cursor | KILLED |
| W-11 | the upload form drops the `accept` filter from the picker | KILLED |
| W-12 | the start-run control offers a provider-mode selector | KILLED |

**12 of 12 killed.** Each was checked against the failing test names in the log to confirm
it was reddened by the assertion written for it and not by a lint guard firing on the
mutated text; every one of the twelve was. `W-04`, `W-05` and `W-06` additionally reddened
`W15-AUTH`'s own `server-credential.test.ts` — which is how the dynamic-import hole in §2.2
was found.

`W-08` is worth naming separately: it is criterion 4's other half. The provider mode is
rendered twice, and the assertion counts both occurrences, so a screen that pinned the
sentence to `live` while leaving the badge correct is red.

## 5. The four survivors, argued

### 5.1 U-06, U-07, U-08 — unreddenable **by construction**, and already known to be

`W12-WEB` §5.2 made this argument and it is correct. The rule is *the key is stable across
renders and changes when the signature changes*, held in a `useRef`. It needs two render
passes of the same component instance. `renderToStaticMarkup` performs one pass and
discards the instance, so `useRef` is fresh on every call and a hook that re-mints on every
render is **indistinguishable from one that does not** — not hard to detect, but
definitionally invisible. A second pass needs `react-dom/client` against a DOM or
`react-test-renderer`; `vitest.config.ts` pins `environment: 'node'`, `node_modules`
carries no `jsdom`, `happy-dom`, `@testing-library/*` or `react-test-renderer`, and
`FRONTEND_LOCK.json` seals the dependency set.

The three modules are now *reached* — the forms import them — which is precisely why
reachability is the weaker number. Reaching them changed nothing about these three.

**The rule is guarded in its pure form**, as `W12-WEB` said: `resolveIntentKey` in
`entities/expert-decision/model/intent.ts` holds the same rule as a function, and
`tests/unit/decisions/intent.test.ts` reddens on it. The three hooks are hand-copies, and
each file says so: *"Duplicated from the other two write features. It belongs in
`shared/lib`, which a Gate B session may not write to."* So the rule has one tested
statement and three untestable duplicates. **That is a product observation, not a testing
gap**, and the repair is to move the rule to `shared/lib` and have the three call it — one
statement, already guarded, three call sites a render test can see. That is the right fix
and it is an edit to `web/src`, which I did not make: it is not a test, and D-1.5 is a
testing row. Recommended as a follow-up.

### 5.2 U-04 and U-05 — reddened by a guard, not by a render, and the difference is stated

Both live inside closures only an event fires: `choose` runs on the picker's `change`,
`send` on submit. One static pass renders the resting form and cannot press anything on
it. **`W12-WEB` §10 is wrong about these two.** It says seven of the ten are "ordinary
components `renderToStaticMarkup` can render exactly as this suite already renders the
evidence viewer". That is true of *rendering the components* and false of *these two
mutations*, which are not in the rendered output at any state a single pass can produce.
Of the seven it listed, four fell to render tests (U-01, U-02, U-03, U-09) and three did
not (U-04, U-05, U-10).

`web/tests/guards/upload-precheck-wiring.guard.test.ts` is the `tests/guards` pattern the
`transport-boundary` and `server-credential` guards already use: scan the real source with
comments and string literals stripped, then prove the scanner fires by applying
`W12-WEB`'s own `b8.json` substitutions **in memory, byte for byte**. The fixture *is* the
mutation, so the guard is shown to fire on exactly what it exists to catch rather than on
a resemblance to it, and it asserts the substitution still applies to today's source, so a
refactor that moved the code takes the guard red instead of silently testing nothing.

**What it proves and what it does not.** It proves the two statements are present and
wired to the right values. It does **not** execute them. It is weaker than the render
tests beside it and is not offered as equivalent. It is here because the alternative was
not a better test but no test, on the two survivors that decide whether a file the browser
already refused can be sent. The render half is taken as far as it goes in
`forms-and-pages.test.ts`: the submit button carries `disabled` before a file is chosen,
and the picker carries `accept="application/pdf"` (`W-11`).

Rows U-04 and U-05 are marked KILLED above because the mutation reddens the suite, which
is what the column measures. A reader deciding how much that is worth should read this
paragraph, not the table.

### 5.3 U-10 — genuinely unguarded, and the smallest of the four

The substitution removes the **effect-time** cache read in
`entities/audit-run/api/use-run-status.ts`. `renderToStaticMarkup` never runs effects.

Note the label drift: D-1.5 renders U-10 as "the run-status hook stops seeding from the
cache", and the hook seeds twice — once in a `useState` initialiser and once inside the
effect. **The initialiser is now constrained**: `run-progress.test.ts` asserts a seeded
cache renders a real reading and an empty one renders the loading state, and a mutation of
that line is red. `b8.json`'s U-10 is the *other* seed, whose only job is to stop the loop
before it starts when the cached reading is already terminal.

What is lost if it breaks: a run that has already finished is polled once before the loop
notices the terminal state and stops. **A wasted request, not a wrong screen** — no state,
no mode and no reason is rendered differently, which is why no assertion in this suite can
see it. The loop itself, `pollRunStatus`, is fully guarded in `tests/unit/run/polling.test.ts`
with the frozen 2 s / ×1.5 / 15 s schedule. I judged a source guard here to be worth less
than its brittleness and did not write one; that is a judgement, and the argument is above
so it can be disagreed with.

## 6. What was deliberately left

Reachability is 114/114, so nothing is left *unreached*. Left **unconstrained**, on
purpose:

- **The three intent-key hooks** — §5.1. Invisible to any renderer this tree may contain.
- **The effect-time seed in `use-run-status.ts`** — §5.3.
- **Every `useMutation` failure branch** in the three write forms. A mutation's error lives
  on a `MutationObserver` that `useMutation` creates fresh on each render, with nothing in
  the `QueryClient` to seed — unlike a query, whose cache entry the harness can fault. So
  `UnsupportedState` vs `ErrorState`, the retry offer and the correlation-id line are not
  reached on these three screens. The *classifiers* that decide all of it —
  `classifyUploadFailure`, `classifyCreateProjectFailure`, `classifyRunFailure` — are fully
  guarded as functions in `tests/unit/projects` and `tests/unit/run`, and the same
  presentation components are render-tested through `ProjectList`, whose failure is a query
  and therefore seedable. What is unguarded is the wiring between the two on three screens.
  Stated, not closed.
- **`features/export-run/model/download-sink.ts`** — outside this row, and `W12-WEB` §5.1's
  argument still holds: three DOM statements behind an interface whose tested half is
  `deliverDownload`.

## 7. Other things found false or wrong

1. **The dispatch's `110 76 34`** — stale. §2.1.
2. **The reachability script misses dynamic imports** — §2.2. It has been under-reporting
   for two waves and is the `Check:` command on D-1.5.
3. **`W15-AUTH` §8.4 is right**, and the dispatch's doubt about it was the wrong premise to
   carry. §2.3.
4. **`W12-WEB` §10's "seven … `renderToStaticMarkup` can reach"** — four of the seven.
   §5.2.
5. **D-1.5's 18%** — 16.3% of a tree that grew. §2.3.
6. **`analysis_provider_unavailable` is not an error code.** The first draft of
   `run-progress.test.ts` used it as a `terminal_reason` and `tsc` refused it: the frozen
   catalog has 21 codes and that is not one of them. This is D-1.6's failure mode exactly —
   `checksum_mismatch`, a plausible-sounding name that no catalog carries — reproduced
   independently, by me, six rows below where the register warns about it. The catalog is
   worth reading rather than reconstructing from memory; `tsc` caught this one only because
   `terminal_reason` is typed as `ErrorCode`, and prose has no `tsc`.

## 8. The gate

Instance `gate-w16a`, `POSTGRES_PORT=55770`, `S3_API_PORT=59370`, `S3_CONSOLE_PORT=59371`,
`POSTGRES_DB=audit_w16a`, bucket `auditmanager-gate-w16a`. Run twice: at `188cacc`, and again at the tip `e73fce7` so the recorded
gate is the gate of the commit a reviewer reads. Both on a **clean, fully committed
tree** — `git status --porcelain` empty before the run, as
`tests/integration/foundation/conftest.py:542` requires.

```
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12   -> bootstrap OK, exit 0
make gate                                              -> GATE OK,     exit 0
```

The exit code was captured on its own line from `$?` after a redirect, never through a
pipe: `make gate > gate.log 2>&1; echo "GATE_EXIT=$?"`. A `| tail` would have reported
tail's status.

| component | expected by the dispatch | measured |
|---|---|---|
| battery | 1726 passed / 5 skipped / 168 subtests | **1726 passed, 5 skipped, 168 subtests** in 217.42 s |
| foundation | 35 | **35 passed** in 32.90 s |
| frontend | 498 at base | **592 passed / 44 files** |
| whitespace | — | clean |

`GATE_EXIT=0` on both runs. Full logs `/root/w16web-logs/gate.log` (at `188cacc`) and
`/root/w16web-logs/gate-final.log` (at `e73fce7`, the figures above); `npm run typecheck` and
`npm run lint` both exit 0, logs beside it.

The battery figure is unchanged, as it must be: nothing outside `web/tests` and this file
was touched. The frontend figure is 498 + 94.

## 9. Reproducing this

```
/root/w16web-mut/reach2.py     # both reachability methods, one command, run from web/
/root/w16web-mut/sweep.py      # one substitution per mutation, read back, run, revert
/root/w16web-mut/w16.json      # §4.2's twelve, as data
/root/w12web-mut/b8.json       # W12-WEB's ten, re-run unchanged
/root/w16web-logs/             # gate, b8-rerun, w16-sweep, typecheck, lint, bootstrap
```

Outside the worktree on purpose, for `W12-WEB` §11's reason: a committed copy of `web/src`
is a second tree a later session can mistake for the real one.

## 10. Elapsed

Start `2026-09-18T04:03:03+05:00` (worktree created), second gate green `04:32`.
**~30 minutes**
wall-clock, on a host at 92% disk with two other wave-16 lanes live. No subagent was
dispatched at any point: `make gate` copies the working tree, and a fan-out during a
measurement is how this programme has corrupted sandbox runs before.

Branch `agent/w16-web`, 8 commits, changing `web/tests/**` and this file only. Not pushed,
not tagged, not merged.

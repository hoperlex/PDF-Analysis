# Task DEV-WEB-REDS-01 — two vitest reds on the clean integration tip

task_id: DEV-WEB-REDS-01
status: completed in development candidate

## Outcome

The two frontend unit reds measured on `integration/ar-close-1026` (2026-10-26: 2 failed, 2845 passed, 186 files) are green because the tests now say what is true, not less: the `/analysis-settings` route test pins the exact full list of reads the screen registers (profile registry plus the AR v3 beta group review, the latter disabled without a `group_id` and enabled for exactly the group in the address) and the not-found answer for a malformed `group_id`; the contrast census renders the loaded six-scope group review, so the two colour-bearing rules that state alone carries are reached and measured against both palettes. No `web/src/**` file changed.

## Depends on

- `AR-V3-BETA-GROUP-REVIEW-SCREEN-01` — completed; added the group review panel to `/analysis-settings` and its query key.
- `W59-ANALYSIS-SETTINGS-01` — completed; graduated the screen and the R-66 test that pinned its single read.
- `DEV-CONTRACT-REDS-01` — completed; the integration tip this lane starts from.

## Frozen inputs

- domain contract: not touched
- API contract: `1.4.0` (shared contract; not touched)
- analysis/comparison/event contract: not touched
- migration head: `0032_ar_v3_run_group` (not touched)
- base commit: `0555a1209eff5db2134543c7b48d8d2423625944` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: web/tests/unit/styles/screens.ts
- enumerator_owner: DEV-WEB-REDS-01
- totality_query: `npm --prefix web test -- --run tests/unit/styles/contrast.test.ts -t "names every colour-bearing rule"`

The set is the contrast census' rendered screens, not a product screen set: one entry, `ArV3BetaReview six scopes loaded`, is added. The totality query passes only when every colour-bearing rule of every stylesheet is reached by some rendered screen or carries a justified entry in `UNREACHED_BY_ANY_SCREEN`; that list is unchanged.

## Captured premise evidence

- premise: the two reds, and the reads the settings screen registers, are as dispatched

### P-01 — the R-66 test pins one read; the screen registers two

- captured_at: 2026-10-26
- command: `git show 0555a120:web/tests/unit/qa_w50/r66-navigation.test.ts > web/tests/unit/qa_w50/zz-base.test.ts && npm --prefix web test -- --run tests/unit/qa_w50/zz-base.test.ts` (the file at the base commit, copied beside the lane's tests and removed after the run)
- captured_output:
  ```text
     × R-66: the stubs have graduated, and each keeps its ruled row and place > /analysis-settings graduated (W59-ANALYSIS-SETTINGS-01): its ruled row and place are kept, and it reads the profile registry 72ms
       → expected [ [ 'analysis', 'profiles' ], …(1) ] to deeply equal [ [ 'analysis', 'profiles' ] ]
  AssertionError: expected [ [ 'analysis', 'profiles' ], …(1) ] to deeply equal [ [ 'analysis', 'profiles' ] ]
        Tests  1 failed | 15 passed (16)
  ```
- interpretation: the unchanged test fails on the second registered read and nothing else in the file; it does not say which read is the second.

### P-02 — the census reaches no element of two rules in the group review module

- captured_at: 2026-10-26
- command: `npm --prefix web test -- --run tests/unit/styles/contrast.test.ts` (base tree, only `r66-navigation.test.ts` modified)
- captured_output:
  ```text
     × the census is taken over rendered screens, not over a list > names every colour-bearing rule that NO rendered screen reaches 1158ms
       → these rules declare a colour and NO screen in `screens.ts` renders an element they match, so their contrast is not measured by anything. Render the screen that carries them. If one truly cannot be rendered, add it to UNREACHED_BY_ANY_SCREEN with the reason — and an entry whose reason is only "it is not rendered" is the defect being laundered.: expected [ '._member_7c8115 details', …(1) ] to deeply equal []
  + [
  +   "._member_7c8115 details",
  +   "._quote_7c8115",
  + ]
   Test Files  1 failed (1)
        Tests  1 failed | 19 passed (20)
  ```
- interpretation: exactly two selectors of `web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.module.css` are unreached; every other test of the file, including the pair-threshold and `R-33` border checks, passed.

### P-03 — which reads the route registers, per address

- captured_at: 2026-10-26
- command: `a temporary vitest case (removed) that imported web/src/app/analysis-settings/page.tsx, rendered its element with renderScreen and printed queryKey, options.enabled and fetchStatus for each query in the cache, for no group_id, a valid group_id and two malformed ones`
- captured_output:
  ```text
  {} [{"key":["analysis","profiles"],"state":"idle","status":"pending"},{"key":["runs","ar-v3-group-review",""],"enabled":false,"state":"idle","status":"pending"}]
  {"group_id":"arg_01M2545JSD15ETSNNV904X991K"} [{"key":["analysis","profiles"],"state":"idle","status":"pending"},{"key":["runs","ar-v3-group-review","arg_01M2545JSD15ETSNNV904X991K"],"enabled":true,"state":"idle","status":"pending"}]
  bad "arg_bad" NEXT_HTTP_ERROR_FALLBACK;404
  bad ["arg_01M2545JSD15ETSNNV904X991K","x"] NEXT_HTTP_ERROR_FALLBACK;404
  ```
- interpretation: without a `group_id` the review is registered under the empty address with `enabled: false` (it asks the server nothing); with a valid one it is enabled for that group; a malformed or repeated value is refused by the route before any render. The profile registry carries no `enabled` option, i.e. it is enabled.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/tests/unit/qa_w50/r66-navigation.test.ts`
- `web/tests/unit/styles/screens.ts`
- `web/tests/unit/styles/contrast.test.ts`
- `web/tests/unit/analysis-settings/**`
- `docs/program/tasks/DEV-WEB-REDS-01.md`
- `docs/program/DEV-WEB-REDS-01.md`

## Forbidden hotspots

All of `web/src/**`, `contracts/**`, `src/**`, `db/**`, `infra/**`, `Makefile`, root dependency/lock files, `web/FRONTEND_LOCK.json`, global styles, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, `origin/main`, tags and the deployment host.

## Non-goals

No change to the screen, the widget, its stylesheet or the query key. No weaker assertion: neither `UNREACHED_BY_ANY_SCREEN` nor any threshold is touched. No full frontend suite, gate or live journey (`R-135`).

## Deliverables

- `r66-navigation.test.ts`: the `/analysis-settings` case asserts the exact list of reads with their `enabled` flag, plus two companion cases (valid `group_id`; malformed `group_id` answers not-found).
- `screens.ts`: the loaded group review rendered in the census.
- `analysis-settings/ar-v3-beta-review-fixtures.ts`: the group review fixture, shared by the panel's test and the census; `ar-v3-beta-review.test.ts` imports it.
- This task file and `docs/program/DEV-WEB-REDS-01.md`.

## Required tests

- command: `npm --prefix web test -- --run tests/unit/qa_w50/r66-navigation.test.ts tests/unit/styles tests/unit/analysis-settings`
- expected: 8 files, 104 passed
- command: `npm --prefix web run lint -- --quiet` and `npm --prefix web run typecheck`
- expected: both exit 0
- command: `npm --prefix web test -- --run tests/guards/screen-set.guard.test.ts tests/guards/screen-claims-about-the-system.guard.test.ts tests/guards/lazy-boundary.guard.test.ts`
- expected: the three guards that read `screens()` pass (41 tests)

## Integration contract

Test-only change. The integrator can rely on: the two measured reds are green; the census now holds one more screen (its screen and pair counts only grow, so `lazy-boundary.guard` `(b)` still holds); no source, contract or stylesheet differs from the base. The integrator re-runs the full vitest suite (not run here, `R-135`).

## Failure/idempotency/security cases

- A third read on the settings screen, or the loss of either read, reddens the list.
- The review read becoming enabled without a valid group, or the route accepting a malformed `group_id`, reddens its own case.
- Removing the loaded-review seed (or the entry) from the census re-creates the P-02 red.
- No network, no provider, no database: static rendering only.

## Rollback / feature flag

Not applicable: test-only. Forward-revert the lane commits.

## Handoff

- changed files: see `docs/program/DEV-WEB-REDS-01.md`
- commands/results: see the same report
- known limits: the widget's borders use `var(--am-border, currentColor)` and `--am-border` is defined in no stylesheet, so the census produces no border pair for them (true of eight modules; see the report)
- integration notes: merge after `DEV-CONTRACT-REDS-01`; re-run the whole vitest suite once

# Task AR-V3-BETA-PACK-STATUS-WEB-FIX-01 — repair four findings in the pack status panel and the six-check start

task_id: AR-V3-BETA-PACK-STATUS-WEB-FIX-01
status: completed in development candidate

## Outcome
An independent judge read `AR-V3-BETA-PACK-STATUS-WEB-01` and reported four findings. Each was re-proved below with a real run before it was fixed, and all four reproduced. After this task: (1) the pack panel's markup carries no more than the first twelve characters of the pack digest, in any attribute, for any role; (2) a six-check start that has been sent cannot lose its navigation or its idempotency key when the pack status stops being readable under it; (3) a status whose profile or prompt-bundle ID breaks the contract's pattern is a contract fault, never an installed pack; (4) a retry under the same key, and a different key for a different version, are pinned by tests that go red when the key is minted afresh. No contract, backend or generated-client change.

## Depends on
- `AR-V3-BETA-PACK-STATUS-WEB-01` — completed; the panel, `useArV3PackStatus`, the six-check control and the run list this task repairs.
- `AR-V3-BETA-PACK-STATUS-API-01` — completed; shared contract `1.5.0`, the `AnalysisProfileId` and `PromptBundleId` patterns.

## Frozen inputs
- shared domain/API/analysis/events contract: `1.5.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged; `VERSION` `0.8.0`, unchanged
- base commit: `809d5c733a92e62a6979103c5771b546d1217c03` (tip of `integration/ar-close-1026`)

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: all four findings are present at the base commit

### P-01 — finding 1: the panel puts the whole digest in a title attribute
- captured_at: 2026-10-26
- command: `git grep -n 'title={pack.packSha256}' 809d5c733a92e62a6979103c5771b546d1217c03 -- web/src/widgets/ar-v3-beta-pack`
- captured_output:
  ```text
  809d5c733a92e62a6979103c5771b546d1217c03:web/src/widgets/ar-v3-beta-pack/ui/ar-v3-beta-pack.tsx:54:          <code title={pack.packSha256}>{packDigestShown(pack.packSha256)}</code>
  ```
- interpretation: the source passes the full digest as a `title`. The run below shows it reaches the markup: a throw-away test (`renderScreen` over `ArV3BetaPack` with the installed fixture and a real 64-hex digest, deleted afterwards) printed `F1 contains full 64-char digest: true` and the fragment `<code title="6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f">6d53674f688f…</code>`. The old test at `ar-v3-beta-pack-status.test.ts:164` pinned `title="${REAL_DIGEST}"`, so it asserted the defect.

### P-02 — finding 2: a failed pack re-read under a start in flight loses the navigation and the key
- captured_at: 2026-10-26
- command: `cd web && npx vitest run tests/unit/analysis-settings/run-list-ar-v3-live.test.ts` (the new stateful test file, run against the UNFIXED source; the three tests below are the ones that moved from red to green with the fix)
- captured_output:
  ```text
     ✓ the harness itself can see what these tests rely on > draws the control on an installed pack and presses it 31ms
     ✓ the harness itself can see what these tests rely on > draws nothing in its place once the pack read has failed 16ms
     × a start in flight when the pack status stops being readable > keeps the control mounted and still opens the started group 20ms
       → the control was unmounted under a request in flight: expected '<div class="am-state am-state--neutra…' to contain 'data-ar-v3-group-start'
     × a start in flight when the pack status stops being readable > draws nothing again once the request has settled and the pack is still unreadable 19ms
       → expected [] to deeply equal [ Array(1) ]
     × a start in flight when the pack status stops being readable > sends the SAME key when the control comes back after the request failed unseen 24ms
       → a new key would make a second group of six runs: expected 'ik_bf671ad0-2798-48f7-a9b8-fbef8ddbb3…' to be 'ik_67f8c5d6-8678-4c2f-b6a1-92ae69189d…' // Object.is equality
     ✓ the key of one intent > is the same on a retry after a failure, and on a second press 16ms
     ✓ the key of one intent > is a different one for a different version 13ms
   Test Files  1 failed (1)
        Tests  3 failed | 4 passed (7)
  ```
- interpretation: the mechanism is as the judge described. Source at the base: `run-list.tsx:61` `packInstalled = pack.phase === 'read' && ...`, `run-list.tsx:70` draws the control only when `packInstalled`, and `start-ar-v3-group-control.tsx:117` holds the key in `useIntentKey` inside the control. The first red shows the control gone under a pending request; the second shows the accepted group never opened (the per-call `onSuccess` died with the observer); the third shows a second press after the control returned sending a different key. The last two green tests are the missing tests of finding 4 and pass on unfixed code because there the control is never unmounted in their scenarios.

### P-03 — finding 3: `installed` accepts any non-empty profile and bundle ID
- captured_at: 2026-10-26
- command: `python3 -c "import json;s=json.load(open('contracts/api/v1/openapi.json'))['components']['schemas'];print(s['AnalysisProfileId']['pattern']);print(s['PromptBundleId']['pattern'])"` together with `git grep -n 'isNonEmptyString(profileId)' 809d5c733a92e62a6979103c5771b546d1217c03 -- web/src/entities/audit-run/model/ar-v3-pack-status.ts`
- captured_output:
  ```text
  ^ap_[0-9A-HJKMNP-TV-Z]{26}$
  ^pb_[0-9A-HJKMNP-TV-Z]{26}$
  809d5c733a92e62a6979103c5771b546d1217c03:web/src/entities/audit-run/model/ar-v3-pack-status.ts:92:  if (!isNonEmptyString(profileId) || !isNonEmptyString(bundleId)) return fault('missing_member');
  ```
- interpretation: the contract has patterns; the reader checks only non-emptiness. A throw-away test calling `readArV3PackStatus` on the installed fixture with one ID replaced read `"installed"` for every one of: `"x"` as profile, a profile with a leading space, with a trailing newline, in lower case, `"x"` as bundle, a bundle with a leading space, with a trailing newline, in lower case, and the bundle ID in the profile slot (nine of nine).

### P-04 — finding 4: nothing tests that a retry reuses its key
- captured_at: 2026-10-26
- command: `cd web && sed -i 's|const idempotencyKey = useIntentKey(`start-ar-v3-group:${versionUid}`);|const idempotencyKey = newIdempotencyKey();|; s|^import { routes, useIntentKey } from .@/shared/lib.;|import { routes } from "@/shared/lib";\nimport { newIdempotencyKey } from "@/shared/api";|' src/features/start-ar-v3-group/ui/start-ar-v3-group-control.tsx && npm test -- --run tests/unit/analysis-settings tests/unit/screens` (the control file restored with `git checkout` afterwards)
- captured_output:
  ```text
   ✓ tests/unit/analysis-settings/ar-v3-group-start-command.test.ts (4 tests) 2ms
   ✓ tests/unit/screens/run-list-ar-v3-started.test.ts (3 tests) 3ms
   Test Files  21 passed (21)
        Tests  394 passed (394)
  ```
- interpretation: with the control minting a fresh key on every render, all 394 tests of the two directories that cover it stay green. The mutation survives, so the claim of the finding holds; the existing control test even asserted only `idempotencyKey.length > 8`.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `web/src/entities/audit-run/model/ar-v3-pack-status.ts`
- `web/src/entities/audit-run/api/use-ar-v3-pack-status.ts`
- `web/src/entities/audit-run/index.ts`
- `web/src/widgets/ar-v3-beta-pack/**`
- `web/src/features/start-ar-v3-group/**`
- `web/src/widgets/run-list/ui/run-list.tsx`
- `web/tests/unit/analysis-settings/**`
- `web/tests/unit/screens/**`
- `web/tests/guards/rendered-language.guard.test.ts`
- `docs/program/tasks/AR-V3-BETA-PACK-STATUS-WEB-FIX-01.md`
- `docs/program/AR-V3-BETA-PACK-STATUS-WEB-FIX-01.md`

## Forbidden hotspots
- `contracts/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `web/package.json`, `web/package-lock.json`
- `src/**`, `db/**`, `infra/**`, `Makefile`, global styles, the composition root (`web/src/_app/providers.tsx`, `src/auditmanager/bootstrap/**`)
- `web/src/shared/lib/**` (the shared `useIntentKey` is unchanged and unneeded: the key is held by the run list, not by a module-scope store), `web/tests/unit/styles/**`
- `docs/program/CURRENT_STATE.md`, `docs/program/RELEASES.md`, `docs/program/DEBT_REGISTER.md`, `release-notes/**`, `VERSION`
- `origin/main`, tags and the deployment host

## Non-goals
- A key that survives leaving the version page, or a module-scope key store (see the design and its limits below).
- Any change to what the control says or to its refusals; `StartArV3GroupView` and the sentences are untouched.
- Any change to `StartRunControl` or to the single-run start.
- Role gating, polling, or showing the group on the version page.

## Deliverables
- Finding 1: `<code title=...>` removed from the installed panel; the rule is stated in the panel comment and at `packDigestShown` (no more than twelve characters of the digest anywhere in the markup); the old `title` assertion removed; tests that measure the longest run of the digest in the panel and in the whole settings screen and require exactly twelve.
- Finding 2, design. The run list holds what must outlive the control, through a new feature hook `useArV3GroupStartIntent(versionUid)` (`features/start-ar-v3-group/model/use-ar-v3-group-start-intent.ts`): (a) `idempotencyKey`, minted by `useIntentKey` inside the run list, so it lives as long as the list does and changes with the version, not with the control; (b) `inFlight`, read from the mutation cache with `useIsMutating` (the mutation now carries `START_AR_V3_GROUP_MUTATION_KEY`; the filter also matches the version in the variables). The cache keeps a mutation until it settles whether or not anything observes it, so no callback or lifted state is needed and no component has to report its own pending state. The run list draws the control when `packInstalled || startIntent.inFlight`; the control takes the intent as a required prop, sends exactly that key (it no longer calls `useIntentKey`) and disables its button when `mutation.isPending || intent.inFlight`. A pending mutation keeps its observer, so the per-call `onSuccess` that opens the group still runs. The shared `useIntentKey` and `shared/lib` are untouched.
- Finding 2, tests: `web/tests/unit/analysis-settings/run-list-ar-v3-live.test.ts` mounts the real run list, control and mutation with only the generated operations and the router replaced, and moves the pack status under a request in flight; `live-render.ts` is the minimal stateful renderer it needs (see Integration contract).
- Finding 3: `ANALYSIS_PROFILE_ID` and `PROMPT_BUNDLE_ID` patterns copied from the contract; a failing one is the new fault reason `bad_identifier`; fifteen malformed-ID cases (`"x"`, leading and trailing space, trailing newline, lower case, one character short or long, a letter Crockford omits, the other kind's prefix) in the classification table, and a test that the well-formed fixture IDs are read unchanged.
- Finding 4: two live tests, a retry and a second press after failures send the same key as the first; a changed version sends a different key. The control test now requires the key it was handed.
- The task note `docs/program/AR-V3-BETA-PACK-STATUS-WEB-FIX-01.md`.

## Verification
- `npm --prefix web run lint -- --quiet`
- `npm --prefix web run typecheck`
- `npm --prefix web test -- --run tests/unit/analysis-settings tests/unit/screens tests/unit/styles tests/guards tests/unit/qa_w50` (bounded; no full suite, R-135)
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/AR-V3-BETA-PACK-STATUS-WEB-FIX-01.md',encoding='utf-8').read())))"` must print `[]`
- Every new test shown red under a quoted mutation (see the result note). No live journey, no full suite, no `make gate`.

## Integration contract
Observable behaviour of the run list and the panel after this task:
- The installed panel's markup contains at most twelve characters of the pack digest, shown as `<twelve>…`; the full digest is on the in-memory reading only.
- A status whose `analysis_profile_id` does not match `^ap_[0-9A-HJKMNP-TV-Z]{26}$` or whose `prompt_bundle_id` does not match `^pb_[0-9A-HJKMNP-TV-Z]{26}$` reads as a fault (`bad_identifier`), is drawn as the contract-fault panel and offers no start.
- The six-check control is drawn when the pack reads as installed, and also while a start for the same version is pending, whatever the pack status does meanwhile. An accepted start always opens `/analysis-settings?group_id=<id>`. Once nothing is pending and the pack is not installed the control is gone again, with nothing in its place.
- The idempotency key for `startArV3BetaGroup` is held by the run list: the same for every press and retry while the list is mounted for one version, a new one when the version changes.
- `StartArV3GroupControl` has a required `intent: ArV3GroupStartIntent` prop (breaking for any other caller; the run list is the only one in the tree). `StartArV3GroupView` and the census (`tests/unit/styles/screens.ts`) are unchanged.
- New public names in `@/features/start-ar-v3-group`: `useArV3GroupStartIntent`, type `ArV3GroupStartIntent`. New fault reason `bad_identifier` in `ArV3PackFaultReason`.
- Test instrument: `web/tests/unit/analysis-settings/live-render.ts` renders with `react-dom/client` into a hand-written node tree (no DOM library, no dependency, `FRONTEND_LOCK.json` untouched). It runs state, effects and a press that calls the element's `onClick`; it has no layout, event path or focus. It lives under `analysis-settings` because a file under `tests/unit/screens/` that names the query provider is counted as a screen-wide consumer by the D-97 guard and must use `renderScreen`.

## Failure/idempotency/security cases
- A start sent, then the pack re-read fails, then the answer is lost (network): the control disappears once the request has settled, the panel in «Настройки анализа» carries the pack error, and the next press after the pack is readable again sends the SAME key, so the server replays the first outcome instead of making a second group.
- A start sent, then the pack re-read fails, then the answer is a 202: the group opens.
- A page opened while an earlier request for the same version is still pending draws the control with its button disabled.
- The digest: no role sees more than twelve characters of it in the DOM; the full value is never put in an attribute.
- A malformed ID in a status is never drawn: neither as installed nor as an empty state.

## Rollback / feature flag
Forward-revert the commit. No flag, no migration, no data; the server operations are untouched.

## Handoff
- changed files: see the result note
- commands/results: see the result note
- known limits: (1) the pending flag reaches React one TanStack notification (a zero-delay timer) after the press, so a pack re-read that fails inside that window can still take the control off the page; the key is held by the list, so the next press replays the same request, but the navigation of that one start is lost. (2) The key lives as long as the run list; leaving the version page and entering it again is a new intent with a new key, covered only for a request still pending (the button is disabled then). (3) A failure of a start that settles while the pack is unreadable is not shown, because the control is gone by then; it is not retried silently either. (4) No stand, pack or browser: the stateful tests use a hand-written DOM, not a browser.
- integration notes: merge after `AR-V3-BETA-PACK-STATUS-WEB-01`; no other lane touches these paths. Nothing to re-run on a database lane.

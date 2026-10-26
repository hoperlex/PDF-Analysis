# Task AR-V3-BETA-PACK-STATUS-WEB-FIX-02 — four findings of judge J8 on the previous web fix

task_id: AR-V3-BETA-PACK-STATUS-WEB-FIX-02
status: completed in development candidate

## Outcome
Judge J8 read `AR-V3-BETA-PACK-STATUS-WEB-FIX-01` and reported four findings. Each was re-proved below with a real test run (red before, green after); all four reproduced. After this task: (1) a six-check start that has been sent still opens its group, and still shows its refusal, when the run list around it turns into its loading or error state; (2) the live test instrument refuses a click on a disabled button, as a browser does, and says so; (3) the digest bound is measured case-insensitively and through separators, so a digest printed in upper case, in groups or split across elements is caught; (4) the intent hook answers for the version it is given, and a list that changes version carries nothing of the previous one. Web-only: no contract, backend, generated-client or shared-library change.

## Depends on
- `AR-V3-BETA-PACK-STATUS-WEB-FIX-01` — completed; `useArV3GroupStartIntent`, the run list's start control and `live-render.ts` that this task repairs.
- `AR-V3-BETA-PACK-STATUS-WEB-01` — completed; the panel and the six-check control.

## Frozen inputs
- shared domain/API/analysis/events contract: `1.5.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged; `VERSION` `0.8.1`, unchanged
- base commit: `4e6b0b4d4eeb4fc93d5209db248ed773bf7c3318`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: all four findings reproduce at the base commit

### P-01 — finding 1: the run list's loading and error states unmount the start control and drop its observer
- captured_at: 2026-10-26
- command: `cd web && npx vitest run tests/unit/analysis-settings/run-list-ar-v3-live.test.ts`
- captured_output:
  ```text
     × a start in flight when the run list itself stops showing the list > keeps the control and still opens the started group while the next page loads 19ms
       → the control was unmounted under a request in flight: expected '<div class="am-state am-state--neutra…' to contain 'data-ar-v3-group-start'
     × a start in flight when the run list itself stops showing the list > keeps the control and still opens the started group while the list failed to re-read 13ms
       → the control was unmounted under a request in flight: expected '<div class="am-state am-state--error"…' to contain 'data-ar-v3-group-start'
     × a start in flight when the run list itself stops showing the list > shows the refusal, and retries under the same key, when the page comes back after a failed start 17ms
       → the control came back with no sign of the failed start: expected '<div data-run-count="1"><ul class="am…' to contain 'data-ar-v3-group-failure'
     × a start in flight when the run list itself stops showing the list > opens a group accepted while the list was loading even when it is back by then 18ms
       → expected [] to deeply equal [ Array(1) ]
     ✓ a fresh visit draws no six-check control while the list is not showing > draws none while the list is loading, whatever the pack status is 13ms
     ✓ a fresh visit draws no six-check control while the list is not showing > draws none while the list has failed, whatever the pack status is 16ms
     ✓ a fresh visit draws no six-check control while the list is not showing > draws none once a start has settled and the list is loading again 12ms
   Test Files  1 failed (1)
        Tests  4 failed | 11 passed (15)
  ```
- interpretation: Command context (the new tests of this task, run against the UNFIXED `run-list.tsx` and control; the source returns before the control at `run-list.tsx:94` `if (query.isPending) return <LoadingState …/>` and `:96` `if (query.isError) {`). the judge's mechanism holds, and one case is worse than the finding says. The fourth test presses the start, lets the next page load and come back BEFORE the answer arrives: the control is back on the page, yet the 202 opens nothing, because the control that comes back is a new instance with a new mutation observer and TanStack drops a per-call `onSuccess` with the observer that was given it. A control kept mounted only in the loading and error branches would not fix that (it too is a different instance in each branch); the observer has to be held by the component that stays mounted through every branch. The three green tests are the fresh-visit rule (c) and pass on the unfixed code, as they must: no pack and no start means no control.

### P-02 — finding 2: `press` calls `onClick` on a disabled button
- captured_at: 2026-10-26
- command: `cd web && npx vitest run tests/unit/analysis-settings/zz-throwaway.test.ts`
- captured_output:
  ```text
  THROWAWAY button disabled in markup: true | startArV3BetaGroup calls after a second press: 2
       Tests  1 passed (1)
  ```
- interpretation: Command context (a throw-away file, deleted afterwards: mounts the run list, presses the six-check button once with a never-answered request, then presses it again; `live-render.ts` unfixed). the button is disabled in the markup and the second press still reached `startArV3BetaGroup`. React dispatches no click to a disabled button, so a test could press a button the page had disabled and pass. Source at the base: `live-render.ts:228` `const onClick = propsOf(found[0] as FakeNode).onClick;` and `:231` `onClick({ type: 'click', … })`, with no check of `disabled`.

### P-03 — finding 3: the digest measure sees only contiguous, case-sensitive runs
- captured_at: 2026-10-26
- command: `node -e "const D='6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f';function old(m,d){for(let l=d.length;l>0;l--)for(let s=0;s+l<=d.length;s++)if(m.includes(d.slice(s,s+l)))return l;return 0}const G=D.match(/.{8}/g);const c={upper:D.toUpperCase(),groupsSpace:G.join(' '),groupsHyphen:G.join('-'),zws:G.join('​'),upperGrouped:G.map(x=>x.toUpperCase()).join(' ')};for(const [k,v] of Object.entries(c))console.log(k,old('<code>'+v+'</code>',D))"`
- captured_output:
  ```text
  upper 6
  groupsSpace 8
  groupsHyphen 8
  zws 8
  upperGrouped 5
  ```
- interpretation: Command context (the body of `longestDigestRun` at `ar-v3-beta-pack-status.test.ts:156` as it was at the base, on a whole 64-character digest printed five ways). a complete digest measures 5 to 8 characters, under the bound of twelve. End to end: with the panel changed to carry `<span hidden>` and the whole digest upper-cased in groups of eight, the ORIGINAL test file of the base (14 tests) stays green, which is the hole; the new file fails with `expected 64 to be 12` (see the mutation table).

### P-04 — finding 4: `useIsMutating` keeps the previous version's answer until a cache event
- captured_at: 2026-10-26
- command: `cd web && npx vitest run tests/unit/analysis-settings/run-list-ar-v3-live.test.ts`
- captured_output:
  ```text
     × a start pending for one version says nothing about another > keeps the other version's button enabled when the list switches version 10ms
       → the other version shows a start it never sent: expected '<div class="am-state am-state--neutra…' not to match /<button[^>]*disabled=""[^>]*>З…/button>
     × a start pending for one version says nothing about another > the intent hook recomputes inFlight for the version it is given, not only on a cache event 8ms
       → the hook still answers for the first version: expected 'B:true' to be 'B:false' // Object.is equality
  ```
- interpretation: Command context (the two tests of this task that change the version under a pending start, against the UNFIXED hook and run list; `use-ar-v3-group-start-intent.ts:43` `const pending = useIsMutating({`). the judge's reading of TanStack is right (`useMutationState` computes its result once, keeps `optionsRef` current in an effect, and recomputes only inside the cache subscription: `node_modules/@tanstack/react-query/src/useMutationState.ts:74` and `:79`). The existing "different key for a different version" test could not see it: its start for the first version was refused, so nothing was pending. The new tests keep the first start pending.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `web/src/widgets/run-list/ui/run-list.tsx`
- `web/src/features/start-ar-v3-group/**`
- `web/tests/unit/analysis-settings/**`
- `docs/program/tasks/AR-V3-BETA-PACK-STATUS-WEB-FIX-02.md`
- `docs/program/AR-V3-BETA-PACK-STATUS-WEB-FIX-02.md`

## Forbidden hotspots
- `contracts/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `web/package.json`, `web/package-lock.json`
- `src/**`, `db/**`, `infra/**`, `Makefile`, global styles, the composition root (`web/src/_app/providers.tsx`, `src/auditmanager/bootstrap/**`)
- `web/src/shared/**` (the shared `useIntentKey` is unchanged), `web/tests/unit/screens/**`, `web/tests/unit/styles/**`
- `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, `release-notes/**`, `VERSION`
- `origin/main`, tags and the deployment host

## Non-goals
- A key that survives leaving the version page; the pending flag's last timing window (see the limits).
- Any change to what the control says or to its refusals; `StartArV3GroupView`, the sentences and the census are untouched.
- Any change to `StartRunControl`, to the single-run start, or to the pack panel.

## Deliverables
- Finding 1, design. The start's mutation observer is held by the component that stays mounted through every branch of the list, not by the control. `useArV3GroupStartIntent(versionUid)` now also calls `useStartArV3Group()` and returns it as `mutation`; `StartArV3GroupControl` sends and reads through `intent.mutation` and no longer calls the hook itself. The per-call `onSuccess` that opens the group therefore runs while the list shows its loading state, its error state or the list, and a refusal that arrived while no control was drawn is on the observer when the control comes back. The run list (`VersionRunList`) also draws the control under its loading and error messages while `startIntent.inFlight`, so a user who pressed «Дальше» still sees the request on its way; with no start in flight those branches draw exactly what they drew before, and a fresh visit with the pack not installed draws no control (the rule «no pack, no control» is unchanged). The router stays out of the list: `StartArV3Group` still reads it, and the callback it passes closes over the router object. Why not the brief's literal "keep the control mounted in the pending and error branches": the control is a different instance in each branch, so a control drawn there would not own the observer that sent the request (P-01, fourth test).
- Finding 2: `LiveRender.press` returns `Promise<boolean>`: `false`, with nothing called, when the button carries `disabled`; `true` when the click was delivered. New `live-render.test.ts` (4 tests). New live tests: a second press on a pending start returns `false` and sends no request; a start that is never answered keeps the button disabled through a pack re-read, a re-render and a list refetch; the button is enabled and takes a press once the request was refused. No existing test pressed a disabled button: all 8 stateful tests of the previous lane passed against the new `press` before any assertion of this task was added to them.
- Finding 3: `longestDigestRun` lower-cases both sides, removes white space, `-`, `_`, `:`, zero-width space, non-joiner, joiner, word joiner, byte-order mark and soft hyphen when they sit between two hex characters, and measures twice: over the markup as written and over its text with the tags taken out (a digest cut into sibling elements). Fixtures: twenty ways of printing a whole digest (case, groups, each separator, mixed separators, a zero-width space after every character, sibling elements, a `title`, a `data-` attribute) each measure 64; the twelve-character form measures 12 in either case; ordinary markup (dates, class names, an id) measures under 6.
- Finding 4: (a) the hook reads `inFlight` with `useSyncExternalStore` over `queryClient.getMutationCache()`: the snapshot is `findAll({ mutationKey, status: 'pending', predicate: version })` evaluated for the version given on this render, and the subscription is the cache's, so a changed version is answered at once. (b) `RunList` renders `VersionRunList` with `key={versionUid}`, so the cursor, the key and the observer (whose `isPending` and answer belong to the previous version) are one version's. Production is unchanged: Next remounts the page on a `[version_uid]` change. Tests: the existing "different key" test now asserts that the other version's button is enabled and no request is named; a start pending for one version leaves the other's button enabled and presses; a probe component shows the hook's answer for A, B and A again.
- Both notes: this note's task file and the result note `docs/program/AR-V3-BETA-PACK-STATUS-WEB-FIX-02.md`.

## Verification
- `npm --prefix web run lint -- --quiet`
- `npm --prefix web run typecheck`
- `npm --prefix web test -- --run tests/unit/analysis-settings tests/unit/screens tests/unit/styles tests/guards tests/unit/qa_w50` (bounded; no full suite, R-135)
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/AR-V3-BETA-PACK-STATUS-WEB-FIX-02.md',encoding='utf-8').read())))"` must print `[]`
- Every new guard shown red under a quoted mutation (see the result note). No live journey, no full suite, no `make gate`.

## Integration contract
Observable behaviour after this task:
- A six-check start that has been sent opens `/analysis-settings?group_id=<id>` on a 202 whatever the list shows at that moment: the list, its loading state (after «Дальше»), its error state, or the empty state. A refusal is drawn when the control is next drawn, with «Повторить с тем же ключом», and the retry sends the same key.
- While a start is pending the run list's loading and error states carry the control (disabled button, «запрос на шесть проверок») under their own message. With no pending start they carry nothing more. Once nothing is pending and the pack is not installed there is no control.
- `ArV3GroupStartIntent` has a third member, `mutation`; `StartArV3GroupControl` reads and sends through `intent.mutation` (it no longer calls `useStartArV3Group`). The run list is the only caller of both.
- `RunList` keeps its name and props; internally it is keyed by the version.
- Test instrument: `LiveRender.press` resolves `boolean`; callers that ignored the old `void` are unaffected.

## Failure/idempotency/security cases
- A start sent, «Дальше» pressed, the 202 arrives while the next page loads: the group opens.
- A start sent, «Дальше» pressed, the request is refused while the next page loads, the page returns: the refusal is drawn with its retry; the retry sends the first press's key.
- A start sent, the list's re-read fails, the 202 arrives: the group opens.
- A page opened for a version with no pack and no pending start, list loading or failed: no control, no «шесть проверок».
- A start pending for version A never disables the control of version B.

## Rollback / feature flag
Forward-revert the commits. No flag, no migration, no data; the server operations are untouched.

## Handoff
- changed files: see the result note
- commands/results: see the result note
- known limits: see the result note
- integration notes: merge after `AR-V3-BETA-PACK-STATUS-WEB-FIX-01`; no other lane touches these paths. Nothing to re-run on a database lane.

# Task WEB-HISTORY-SEVERITY-FAULT-01 — fail closed on unknown decision severity

task_id: WEB-HISTORY-SEVERITY-FAULT-01

## Outcome

The decision history hides its complete event list and shows one explicit fault if any event has a severity outside the sealed vocabulary. Valid and absent severities retain their existing display.

## Depends on

- `WEB-REVIEW-FOLLOWUPS-01` — completed; introduced severity in the history and its focused test.
- `WEB-HOOKS-PER-FINDING-01` — completed; covered severity rendering in the language guard.

## Frozen inputs

- domain contract: `1.2.0`;
- API contract: `1.2.0` and existing generated `SEVERITY_VALUES`;
- analysis/comparison/event contract: current `DecisionEvent.severity` is optional and closed vocabulary;
- migration head: `0032_ar_v3_run_group`;
- base commit: `b8a3c67d200773f6bc1697118ac5255acb5fb555`;
- version: `0.8.0`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the history validates event type and verdict but does not validate severity before rendering the ledger.

### P-01 — the history guard omits severity

- captured_at: 2026-10-23
- command: `rg -n 'hasKnownVocabulary|eventTypes.includes|verdicts.includes|data-history-fault' web/src/widgets/decision-history/ui/decision-history.tsx`
- captured_output:
  ```text
  62:function hasKnownVocabulary(event: DecisionEvent): boolean {
  66:    eventTypes.includes(event.event_type) &&
  67:    (event.verdict === null || event.verdict === undefined || verdicts.includes(event.verdict))
  83:  if (events.some((event) => !hasKnownVocabulary(event))) {
  85:      <section className="am-history" data-history-fault="closed-vocabulary">
  ```
- interpretation: event type and verdict already hide the ledger; severity does not yet enter that check.

### P-02 — the old test explicitly permits a partial ledger

- captured_at: 2026-10-23
- command: `rg -n 'badge.s fault|other event is still there|data-event-count' web/tests/unit/review/history-and-kb-severity.test.ts`
- captured_output:
  ```text
  181:  it('shows a value outside the closed set as the badge’s fault, not as a blank or as a word', () => {
  191:    // The other event is still there: one bad severity does not hide the ledger.
  192:    expect(markup).toContain('data-event-count="2"');
  ```
- interpretation: the test pins the behavior being replaced only for history; the knowledge base remains separate.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/src/widgets/decision-history/ui/decision-history.tsx`
- `web/tests/unit/review/history-and-kb-severity.test.ts`
- `docs/program/DEBT_REGISTER.md`
- `docs/program/tasks/WEB-HISTORY-SEVERITY-FAULT-01.md`
- `docs/program/WEB-HISTORY-SEVERITY-FAULT-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and lock files, composition root, global styles, generated client, other UI and tests.

## Non-goals

- Producing `merged_observations` in the v2 pipeline; changing knowledge-base policy or severity vocabulary; publishing to `origin/main`.

## Deliverables

- History guard and focused regression; D-201 narrowed to its remaining producer; completion report.

## Required tests

- `npm --prefix web test -- --run --no-cache tests/unit/review/history-and-kb-severity.test.ts tests/unit/review/viewer-and-panels.test.ts` — expected green after a failing-first regression.
- `npm --prefix web run typecheck` and `npm --prefix web run lint -- --quiet` — expected green.
- `git diff --check` and exact allowed-path check — expected green.

## Integration contract

Every event is validated before ordering or rendering. A single unknown severity (including malformed `null`) hides all events with `data-history-fault="closed-vocabulary"`; missing severity and known values retain existing behavior. No API, schema or migration changes. Publish only a checked fast-forward to `origin/dev`.

## Failure/idempotency/security cases

- One malformed event cannot leak a partial ledger or the raw unknown member. No write or external side effect; repeated renders are identical.

## Rollback / feature flag

- Revert the commit. No flag; the change tightens an existing fault behavior.

## Handoff

- changed files, commands/results, known limits and integration notes: `docs/program/WEB-HISTORY-SEVERITY-FAULT-01.md`.

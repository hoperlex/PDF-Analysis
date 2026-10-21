# Task W56A-INT-RECORDED-V2-CHAIN-PREP-01 — recorded AR v2 publication chain

task_id: W56A-INT-RECORDED-V2-CHAIN-PREP-01

## Outcome

A caller can pass one recorded model response and its pinned PDF text layer
through the existing parser, grounding, deterministic merge and transactional
publisher without selecting a provider or changing the run executor.

## Depends on

- `W56A-INT-RESPONSE-PIPELINE-PREP-01` — completed pure response pipeline;
- `W56A-INT-V2-PUBLICATION-PREP-01` — completed publisher at `9e3ec73e`;
- `W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01` — completed analysis seam.

## Frozen inputs

- base commit and `origin/dev`: `9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/public.py`
- enumerator_owner: `W56A-INT-RECORDED-V2-CHAIN-PREP-01`
- totality_query: `sed -n '80,170p' src/auditmanager/analysis/public.py`

## Captured premise evidence

- premise: the response pipeline and publisher are present, but no recorded-only
  function binds them and the public analysis seam lacks their input types.

### P-01 — exact base and boundary

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && rg -n 'finish_response|publish_v2_merge_plan' src/auditmanager/{analysis,findings}`
- captured_output:
  ```text
  9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d
  9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d
  src/auditmanager/findings/v2_publication.py:161:def publish_v2_merge_plan(
  src/auditmanager/analysis/profiles/ar_v2/response_pipeline.py:32:def finish_response(
  ```
- interpretation: an additive recorded chain can be tested without executor or provider activation.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/findings/v2_recorded.py`
- `tests/integration/findings/test_v2_recorded_chain.py`
- `docs/program/tasks/W56A-INT-RECORDED-V2-CHAIN-PREP-01.md`
- `docs/program/W56A-INT-RECORDED-V2-CHAIN-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, root dependency/lock files,
composition root, global styles, run executor, existing v1 publication,
historical fixtures, corpus, `CURRENT_STATE.md`, refs and tags.

## Non-goals

No model call, live mode, stage registry change, run state transition,
runtime wiring, diagnostic DB row, DB acceptance, full gate or beta claim.

## Deliverables

Recorded-only chain, public input exports, focused recorded tests, task and
result report.

## Required tests

- focused no-DB tests for accepted/rejected/invalid/truncated cases;
- Python compilation, direct governance, frozen hashes, whitespace and exact
  owned-path proof;
- PostgreSQL and full `make gate` deferred under R-135.

## Integration contract

The later executor may use this function only for an explicitly recorded AR v2
run with a pinned text layer and caller-owned transaction. The function calls
`finish_response`, then `plan_v2_merge_publication`, then
`publish_v2_merge_plan` in that order. It refuses live context before opening
a savepoint. Runtime authority, outer commit, run idempotency and diagnostic
persistence remain with later owned tasks.

## Failure/idempotency/security cases

An invalid response or grounding/merge failure writes no rows. A database
refusal rolls back the publisher savepoint. Replays need caller-enforced run
idempotency; no model proposal becomes an expert decision.

## Rollback / feature flag

Remove the additive chain and public exports before runtime wiring. No flag or
migration is introduced.

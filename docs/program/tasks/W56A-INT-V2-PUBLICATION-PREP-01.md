# Task W56A-INT-V2-PUBLICATION-PREP-01 — prepare transactional AR v2 finding publication

task_id: W56A-INT-V2-PUBLICATION-PREP-01

## Outcome

An additive publisher accepts only a typed `MergePublicationPlan` as finding content. In one caller-owned savepoint it allocates one finding UID per merge group, writes every grounded member and its PDF evidence with proposed severity, then binds the canonical observation. A fake-session test verifies SQL order, parameters, rollback and error mapping without claiming PostgreSQL acceptance.

## Depends on

- `W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01` — completed typed and validated merge-publication plan.

## Frozen inputs

- base commit and `origin/dev`: `3a9b64c0796e6d61ad33a6c9f87ff842525712f6`;
- W56 plan §A3.3 SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the four owned paths are additive on the exact base and the migration supplies a nullable canonical FK.

### P-01 — base and additive paths

- captured_at: 2026-10-15
- command: `git rev-parse origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/findings/v2_publication.py tests/integration/findings/test_v2_publication_sql.py docs/program/tasks/W56A-INT-V2-PUBLICATION-PREP-01.md docs/program/W56A-INT-V2-PUBLICATION-PREP-01.md`
- captured_output:
  ```text
  3a9b64c0796e6d61ad33a6c9f87ff842525712f6
  ```
- interpretation: no owned path exists at the base; the task does not mutate v1 publication.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/findings/v2_publication.py`
- `tests/integration/findings/test_v2_publication_sql.py`
- `docs/program/tasks/W56A-INT-V2-PUBLICATION-PREP-01.md`
- `docs/program/W56A-INT-V2-PUBLICATION-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing publication and merge modules, executor, API, composition root, root dependencies/locks, global styles, `CURRENT_STATE.md`, Git refs, tags, `origin/dev` and `origin/main`.

## Non-goals

No runtime routing, provider call, DB acceptance, schema or contract change, decision write, rejected diagnostic row, v1 behavior change, complete gate or beta claim.

## Deliverables

Additive transactional publisher, focused fake-session tests, task file and result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/findings/test_v2_publication_sql.py` — pass;
- Python compilation, direct task governance, whitespace and exact owned-path proof — pass;
- PostgreSQL integration and complete `make gate` deferred under `R-135` and absent isolated database.

## Integration contract

`publish_v2_merge_plan(session, *, plan, context)` takes a `MergePublicationPlan` and typed provenance context. The caller must pass the output of `plan_v2_merge_publication` after `finish_response`; a hand-built dataclass does not prove merge-rule consistency or PDF grounding. The caller owns the outer transaction and commits or aborts it. One savepoint encloses all groups. Returned group and member identities retain dense and source ordinals. Rejected proposals retain diagnostics in the result only and allocate no identity. This module is not a public/runtime export.

## Failure/idempotency/security cases

Wrong plan type, structurally invalid group, malformed provenance identity or provider mode fails before an ID is allocated. A database refusal rolls back all v2 writes to the savepoint and maps SQLSTATE through the shared catalog. Retry after rollback allocates fresh opaque IDs; the caller must enforce run-level idempotency. No model proposal is an expert decision.

## Rollback / feature flag

Remove the additive module and test before runtime wiring; no data rollback or feature flag is needed.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: integrate only after separately granted runtime wiring and PostgreSQL acceptance.

# Task W56A-INT-EVALUATION-GLOBAL-IDENTITY-01 — check published IDs across seeded runs

task_id: W56A-INT-EVALUATION-GLOBAL-IDENTITY-01

## Outcome

The offline AR v2 evaluation bridge refuses a repeated published finding UID or
observation ID across different seeded runs, while a complete series with
distinct IDs keeps the same evidence score.

## Depends on

- `W56A-INT-EVALUATION-BRIDGE-PREP-01` — completed offline scoring bridge;
- `W56A-INT-V2-PUBLICATION-PREP-01` — completed publication result shape.

## Frozen inputs

- base commit: `7b56cb451946d250b1030f61150a4979dbcfc157`
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- seeded manifest SHA-256 `95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7`;
- API contract SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0023_norm_citations`; the existing finding and observation IDs are global primary keys.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the bridge checks publication IDs only within a single run although both are global database keys.

### P-01 — current check scope

- captured_at: 2026-10-16
- command: `rg -n 'finding_ids:|observation_ids:|for run in runs:|_check_publication\(' tools/evaluation/bridge.py`
- captured_output:
  ```text
  160:def _check_publication(plan: object, publication: object, run_id: str) -> None:
  171:    finding_ids: set[str] = set()
  172:    observation_ids: set[str] = set()
  213:    for run in runs:
  227:            _check_publication(run.plan, run.publication, run.run_id)
  ```
- interpretation: two valid per-run projections can reuse the same published IDs without bridge rejection.

### P-02 — database identity scope

- captured_at: 2026-10-16
- command: `rg -n 'finding_uid.*PRIMARY KEY|finding_observation_id text PRIMARY KEY|every run allocates fresh finding_uid' db/migrations/versions/20260910_0002_pc01_schema.py`
- captured_output:
  ```text
  888:            finding_uid     text PRIMARY KEY,
  909:        "no cross-run matching: every run allocates fresh finding_uid values, which is "
  917:            finding_observation_id text PRIMARY KEY,
  ```
- interpretation: the repository treats both published IDs as global, and each run allocates fresh finding IDs.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tools/evaluation/bridge.py`
- `tests/contract/evaluation/test_bridge.py`
- `docs/program/tasks/W56A-INT-EVALUATION-GLOBAL-IDENTITY-01.md`
- `docs/program/W56A-INT-EVALUATION-GLOBAL-IDENTITY-01.md`

## Forbidden hotspots

Existing fixture bytes and manifest, matcher, runtime publisher, recordings,
baseline, `contracts/**`, migrations, provider lock, root dependencies and lock,
composition root, global styles, `CURRENT_STATE.md`, Git refs and tags.

## Non-goals

No real recorded run, source-byte custody proof, quality baseline or threshold,
provider call, database write, contract or migration change, beta verdict or
served activation.

## Deliverables

One aggregate identity check in the pure bridge; focused duplicate-finding,
duplicate-observation and globally unique-series tests; this task and report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/evaluation/test_bridge.py tests/contract/evaluation/test_matcher_core.py` — pass;
- `../../../.venv/bin/python -m py_compile tools/evaluation/bridge.py tests/contract/evaluation/test_bridge.py` — pass;
- direct `governance_findings` check on this task, `git diff --check` and exact owned-path proof — pass;
- full `make gate` deferred under R-135.

## Integration contract

`score_seeded_plans` checks one shared finding-ID set and one shared
observation-ID set across every supplied `V2PublicationResult`. It raises the
existing `publication_identity_invalid` error on a duplicate within or across
run results. Runs without a supplied publication remain allowed for pure plan
scoring, as before. No output schema or API changes.

## Failure/idempotency/security cases

Identical IDs in two distinct bundle runs fail even when every per-run group,
canonical member and evidence quote is valid. Repeated pure inputs yield the
same result. Publication IDs cannot become bundle or source identity.

## Rollback / feature flag

Revert the four owned files before an evaluation harness consumes this check.
No persistent data or flag is involved.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: integrate the source commit on the exact checked base and retain the
  separate recorded source-custody and measured-baseline requirements.

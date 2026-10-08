# Task W52-DEBT-CODE-128F11 — name the text stage version at the analysis boundary

task_id: W52-DEBT-CODE-128F11

## Outcome

The analysis public module exports the text stage's version as `TEXT_STAGE_VERSION`.
The runs executor imports that precise name, and a focused contract test prevents a
return to the context-wide `STAGE_VERSION` name.

## Depends on

- `W52-INT-128F2-02` — integrated and published at
  `8af9fdd508ed3982677ee82e67b1822b505fe7d1`.

## Frozen inputs

- Exact base `8af9fdd508ed3982677ee82e67b1822b505fe7d1`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-128 F-11 in `reviews/W48-JUDGE-Z.md`; proposed W52 plan at
  `2b45a11ec558df1452a4822149e54d2fe0ddb57e` slots F-11 to DEBT-CODE.
- Owner direction 2026-10-08: proceed without approval; only basic tests and lint;
  stand, QA and full gate remain D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: one text-stage version is exported under a context-wide name and immediately
  re-aliased by its only cross-context importer.

### P-01 — exact base and import sites

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n 'STAGE_VERSION|TEXT_STAGE_VERSION' src/auditmanager/analysis/public.py src/auditmanager/runs/executor.py`
- captured_output:
  ```text
  8af9fdd508ed3982677ee82e67b1822b505fe7d1
  src/auditmanager/runs/executor.py:99:from auditmanager.analysis.public import STAGE_VERSION as TEXT_STAGE_VERSION
  src/auditmanager/runs/executor.py:388:        stage_version=TEXT_STAGE_VERSION,
  src/auditmanager/analysis/public.py:64:from auditmanager.analysis.text.stage import STAGE_VERSION
  src/auditmanager/analysis/public.py:90:    "STAGE_VERSION",
  ```
- interpretation: F-11 is a naming issue at the public seam, with one known importer;
  the text stage's internal constant and its value are unchanged.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/executor.py`
- `tests/contract/architecture/test_analysis_public_stage_version.py`
- `docs/program/W52-DEBT-CODE-128F11.md`

## Forbidden hotspots

Every other path, especially `contracts/**`, migration head, dependencies/locks,
`src/auditmanager/analysis/text/stage.py`, API and bootstrap composition roots,
global styles and D-128 F-1/F-10.

## Non-goals

No stage version bump, wire change, D-128 closure, W52 freeze, QA, stand, full gate,
release, tag or `origin/main` publication.

## Deliverables

- Precisely named public export and one consumer import; runtime version value unchanged.
- A focused contract test proving the exported value and rejecting the broad name.

## Required tests

- `.venv/bin/python -m pytest -q tests/contract/architecture/test_analysis_public_stage_version.py tests/contract/architecture/test_alr05_boundaries.py`
- Python compilation/import smoke check, frontend lint and `git diff --check`; no stand
  or full gate.

## Integration contract

Hand back a clean branch from the exact dispatch SHA with only allowed paths. The
integrator may publish this code preparation to `origin/dev` after exact remote-ref
and fast-forward verification. D-128 remains open for F-1/F-10 and validation.

## Failure/idempotency/security cases

An importer asking for the old public name must fail visibly; no silent alias remains.
Importing runs still resolves the same text-stage version. Repeated imports are stable.

## Rollback / feature flag

Revert the code commit. No runtime feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.

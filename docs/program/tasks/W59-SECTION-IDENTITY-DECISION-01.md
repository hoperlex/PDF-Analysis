# Task W59-SECTION-IDENTITY-DECISION-01 — decide version-bound section identity

task_id: W59-SECTION-IDENTITY-DECISION-01

## Outcome

One reviewable pre-seal decision names the opaque identities and version,
stage, expert-confirmation, current-head and ACL rules that W59 SECTION-SEAL
must implement. It explains the same identity boundary for W59 version
comparison, W62 П/Р comparison and W63 Form 7 without granting code changes.

## Depends on

- `W59-INT-SECTION-SUGGESTION-PREP-01` — completed 15-code suggestion input.
- `W59-INT-SECTION-ROUTE-PREP-01` — completed version-bound route guard.
- `W59-INT-CONFIRMATION-PREP-01` — completed expert-choice policy.
- `W59-INT-VERSION-PAIR-READ-01` — completed exact same-set/order reader.
- `W59-INT-PROFILE-READINESS-GAP-01` — completed profile and seal gap report.

## Frozen inputs

- base commit: `08055ca094a9c3e4676a5907a0b3020f0bee4fb8` (`origin/dev`);
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis stage registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- roadmap SHA-256: `e7e73b21996c1c6f37f7b3f5cb741b7d50054dcd7751b3a401ed7fba514a7be5`;
- glossary SHA-256: `87e3d7701f96808546ffa4823352af5984330d9d45b572a4ed59b993c3fd8431`;
- migration head: `0022_findings_v2`; roadmap S-1–S-6/C-1–C-4 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W59 has pure suggestion, confirmation and route preparation, while
  the current 14-code API and immutable version schema cannot yet encode a
  version-bound expert decision or П/Р stage.

### P-01 — preparatory tasks at the exact base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD docs/program/tasks | rg 'W59-INT-(CONFIRMATION|PROFILE-READINESS-GAP|SECTION-ROUTE|SECTION-SUGGESTION|VERSION-PAIR-READ)'`
- captured_output:
  ```text
  docs/program/tasks/W59-INT-CONFIRMATION-PREP-01.md
  docs/program/tasks/W59-INT-PROFILE-READINESS-GAP-01.md
  docs/program/tasks/W59-INT-SECTION-ROUTE-PREP-01.md
  docs/program/tasks/W59-INT-SECTION-SUGGESTION-PREP-01.md
  docs/program/tasks/W59-INT-VERSION-PAIR-READ-01.md
  ```
- interpretation: this is a design input before the separately granted
  SECTION-SEAL; these tasks do not own a shared contract or migration.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W59-SECTION-IDENTITY-DECISION-01.md`
- `docs/program/W59-SECTION-IDENTITY-DECISION-01.md`

## Forbidden hotspots

`contracts/**`, migrations, all `src/**` and tests, existing docs/task files,
`CURRENT_STATE.md`, root dependencies/locks, composition root, global styles,
production configuration, recordings, Docker, refs and tags.

## Non-goals

No W58 close, API/domain/error/stage reseal, physical DB design or migration,
run-start or upload behavior change, new ObjectUid, executable profile,
provider call, project ACL or beta acceptance. No historical version receives
an inferred stage or confirmed section in this task.

## Deliverables

This formal task and the paired identity-decision report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program/test_wave_governance.py` — pass;
- direct governance findings on this task — empty;
- frozen SHA readback, `git diff --check` and exact two-path proof — pass;
- no runtime, DB, Docker, network or complete gate under R-135.

## Integration contract

The later W59 SECTION-SEAL owner may use this identity decision as an input,
but must freeze again from the completed W58-code close, name one owner for the
API contract and migration head, and prove upgrade and runtime refusals. If
the later freeze changes this design, it records the replacement decision;
this document alone cannot authorize publication or infer stored facts.

## Failure/idempotency/security cases

Legacy `document.section`, a filename suggestion, a version ordinal or
`document.current_version_uid` cannot authenticate a section, stage or actor.
Missing/foreign version, wrong project/set, absent stage, absent confirmation
or unavailable profile must refuse at the eventual run boundary. Re-reading
this report has no side effect.

## Rollback / feature flag

Remove the two Markdown files if a later freeze supersedes them. No behavior,
schema, data rollback or feature flag exists in this task.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: W58-code close, then one fresh W59 SECTION-SEAL freeze and owner.

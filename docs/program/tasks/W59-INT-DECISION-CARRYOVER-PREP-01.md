# Task W59-INT-DECISION-CARRYOVER-PREP-01 — pure confirmed carryover plan

task_id: W59-INT-DECISION-CARRYOVER-PREP-01

## Outcome

A deterministic policy offers the current prior-version expert verdict for an
explicitly matched target finding and produces a plan only for an expert's exact
single or bulk selection. It refuses stale, ambiguous and already-decided
targets; it appends no decision event.

## Depends on

- `W59-INT-VERSION-RAW-TEXT-PREP-01` — completed immutable raw evidence seam.
- `W59-INT-CONFIRMATION-PREP-01` — completed version-bound expert-choice pattern.

## Frozen inputs

- base commit: `238363272716c005760ec14ce7eae0f500abda4a`
- API contract SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- roadmap SHA-256: `e7e73b21996c1c6f37f7b3f5cb741b7d50054dcd7751b3a401ed7fba514a7be5`;
- ADR-0010 SHA-256: `fd8694dd76dab2c0e5c7d1aea713d8d60538da573b11b9ad5807ae8b7f195d27`;
- ADR-0013 SHA-256: `a5d8a88e1a7b531ea00cd383a7aa00f691cada0a1c118e807b48c1949eaab410`;
- migration head: `0022_findings_v2`; R-135, roadmap C-4.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: roadmap C-4 requires expert confirmation, while the completed
  comparison package had no persisted carryover path at this task's freeze.

### P-01 — approved rule and missing implementation

- captured_at: 2026-10-15
- command: `rg -n 'C-4|VERSION-COMPARE' docs/program/dispatch/ROADMAP-TO-BETA.md docs/program/dispatch/CODE-FIRST-SCOPE-W58-W63.md && git ls-tree -r --name-only HEAD src/auditmanager/comparison`
- captured_output:
  ```text
  docs/program/dispatch/ROADMAP-TO-BETA.md:451:| C-4 | decision carryover | **with confirmation**: a matched finding is offered its previous decision marked «из версии N»; the expert confirms singly or in bulk; fixed findings are marked resolved |
  docs/program/dispatch/CODE-FIRST-SCOPE-W58-W63.md:19:| W59 / VERSION-COMPARE | Версии комплекта: pairing, детерминированный raw text diff, AI summary, matching findings, подтверждаемое наследование решений. | AI не изменяет raw evidence; перенос только после подтверждения; fixed findings помечены resolved. | SECTION-SEAL merge; один comparison owner. |
  src/auditmanager/comparison/README.md
  src/auditmanager/comparison/raw_text.py
  ```
- interpretation: C-4 specifies explicit confirmation but not matching,
  persisted revision/authorization, event provenance or resolved-state schema.
  This task implements a pure conservative plan only.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/W59-INT-DECISION-CARRYOVER-PREP-01.md at `e61fc457`
- addendum_path: docs/program/PROGRAM-GOVERNANCE-REPAIR-01.md

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/decision_carryover.py`
- `tests/integration/comparison/test_decision_carryover.py`
- `docs/program/tasks/W59-INT-DECISION-CARRYOVER-PREP-01.md`
- `docs/program/W59-INT-DECISION-CARRYOVER-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing comparison/decision/section files,
routers, API/UI, runtime workers, storage, analysis profiles, provider lock,
root dependencies/locks, composition root, global styles, `CURRENT_STATE.md`,
refs, tags and Docker resources.

## Non-goals

No automatic finding matching, fixed-finding resolution rule, sheet matching,
AI synthesis, persisted offer or authorization, ledger append, API/DB/S3 wiring,
contract reseal, full gate or beta claim. A source version UID is provenance;
its display number is not identity.

## Deliverables

Pure offer/confirmation plan, addressable tests and result report.

## Required tests

- `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_decision_carryover.py` — pass when the host has an available RAM/CPU window;
- `.venv/bin/python -m compileall -q src/auditmanager/comparison/decision_carryover.py tests/integration/comparison/test_decision_carryover.py` — pass;
- `git diff --check` and exact changed-path proof — pass;
- no Docker/DB/network/full gate under this task.

## Integration contract

The W59 comparison owner must load authoritative same-set version order,
approved finding matches and immutable evidence in a transaction. Source
current verdict and target event counts must be re-read at confirmation. The
service must authenticate an expert, bind a persisted offer to its exact
revision, then append a new event to the target finding with provenance to the
source decision and an idempotent command key. Neither a client-constructed
input nor this plan grants authority. The owner separately defines how fixed
findings are established and marked resolved.

## Failure/idempotency/security cases

Invalid IDs, equal versions/findings, bad evidence digest, non-current source
verdict, prior target event, duplicate or stale selection and non-expert actor
refuse. One plan per target; no partial bulk result. Repeating identical pure
inputs returns equal outputs. A future unique DB key and append-only ledger
enforce persistent idempotency.

## Rollback / feature flag

Delete the additive module before runtime wiring. No data rollback or feature
flag because no production behavior is connected.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: SECTION-SEAL and the W59 comparison owner define persisted matching,
  source provenance, resolved-state semantics and API/DB transaction before
  calling this policy.

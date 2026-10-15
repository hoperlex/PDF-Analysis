# Task W59-INT-VERSION-RAW-TEXT-PREP-01 — deterministic version text evidence

task_id: W59-INT-VERSION-RAW-TEXT-PREP-01

## Outcome

A pure comparison function accepts explicit approved SheetLink pairs for two
immutable VersionUid values and emits bounded, reproducible raw line changes.
It refuses ambiguous, mismatched or oversized inputs. No AI result can mutate
the returned evidence.

## Depends on

- `W59-INT-SECTION-ROUTE-PREP-01` — complete on `origin/dev` before this task.

## Frozen inputs

- base commit: `5a51721a745a7bfc5c85cc4594625fa53cbce523`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis stage registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- comparison v1 area SHA-256: `3c07e1692fa611c55e6de74ba73006a9244512e2b4ed06c77944b204610f2c0f`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- migration head: `0022_findings_v2`;
- ADR-0013 and roadmap §10.4 C-1–C-4; R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the comparison boundary has no implementation at the frozen base.

### P-01 — comparison implementation absent at base

- captured_at: 2026-10-15
- command: `git ls-tree -r --name-only HEAD src/auditmanager/comparison`
- captured_output:
  ```text
  src/auditmanager/comparison/README.md
  ```
- interpretation: the comparison directory had only its README at the base;
  this task adds a pure module and no runtime route.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/raw_text.py`
- `tests/integration/comparison/test_raw_text.py`
- `docs/program/tasks/W59-INT-VERSION-RAW-TEXT-PREP-01.md`
- `docs/program/W59-INT-VERSION-RAW-TEXT-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, storage/public APIs, routers, analysis profiles,
section seal, runtime workers, existing comparison README, composition root,
root dependencies/locks, global styles, `CURRENT_STATE.md`, tags and refs.

## Non-goals

No automatic sheet matching, approval persistence/authorization, set membership
or stage policy, finding matching, decision carryover, AI summary, graphic
comparison, API/DB/S3 wiring, full gate or beta claim. Explicit page numbers
are coordinates inside immutable versions, never sheet identity; the catalog
has ComparisonId and SheetLinkId but no SheetUid.

## Deliverables

Pure raw text evidence module, focused recorded fixtures/tests and result
report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_raw_text.py` — pass;
- `../../../.venv/bin/python -m compileall -q src/auditmanager/comparison/raw_text.py` — pass;
- direct task governance, `git diff --check` and changed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

The later SECTION-SEAL owner supplies authoritative approved links, confirms
both versions belong to the same set and are ordered as intended, and stores a
write-once raw artifact keyed by its checksum. AI synthesis is a separate
derived artifact keyed to that checksum. The pure function does not accept
suggestions as authority and does not allocate IDs.

## Failure/idempotency/security cases

Invalid IDs, stale link revision, mixed comparisons/versions, duplicate links
or page use, missing page text, and size ceilings refuse before evidence is
returned. Replaying the same input yields equal evidence and checksum.

## Rollback / feature flag

Remove the additive module before runtime wiring. No data rollback or flag.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: SECTION-SEAL and the version comparison owner must own DB/API/AI and
  the full comparison workflow.

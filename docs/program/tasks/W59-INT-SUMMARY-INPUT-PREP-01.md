# Task W59-INT-SUMMARY-INPUT-PREP-01 — bounded version-summary input

task_id: W59-INT-SUMMARY-INPUT-PREP-01

## Outcome

A pure W59 module prepares bounded, deterministic changed-line input for a
future AI version summary from one exactly reverified raw evidence seal. It
retains the ordered version pair, approval revision and every approved sheet's
evidence digest. It neither generates a summary nor changes raw evidence.

## Depends on

- `W59-INT-VERSION-RAW-TEXT-PREP-01` — completed raw text evidence.
- `W59-INT-VERSION-PAIR-READ-01` — completed ordered pair reader.
- `W59-INT-RAW-EVIDENCE-SEAL-PREP-01` — completed exact raw seal.

## Frozen inputs

- base commit: `445efc5db8556ef5a5e13fa680f9f49eb9783954` (`origin/dev`);
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis stage registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- roadmap SHA-256: `e7e73b21996c1c6f37f7b3f5cb741b7d50054dcd7751b3a401ed7fba514a7be5`;
- migration head: `0022_findings_v2`; roadmap C-2 and ALR-22/23; R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: exact raw comparison evidence is sealed, but no bounded input for a
  separate AI summary exists at the frozen base.

### P-01 — comparison boundary at the frozen base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only origin/dev src/auditmanager/comparison`
- captured_output:
  ```text
  src/auditmanager/comparison/README.md
  src/auditmanager/comparison/decision_carryover.py
  src/auditmanager/comparison/finding_match_suggestions.py
  src/auditmanager/comparison/raw_evidence_seal.py
  src/auditmanager/comparison/raw_text.py
  src/auditmanager/comparison/version_reader.py
  ```
- interpretation: the additive input module has no existing implementation or
  shared file to edit; the raw seal is the authoritative integrity input.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/summary_input.py`
- `tests/integration/comparison/test_summary_input.py`
- `docs/program/tasks/W59-INT-SUMMARY-INPUT-PREP-01.md`
- `docs/program/W59-INT-SUMMARY-INPUT-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing comparison modules, sections and
profiles, public boundaries, routers, API/UI, workers, storage, provider lock,
root dependencies/locks, composition root, global styles, `CURRENT_STATE.md`,
refs, tags and Docker resources.

## Non-goals

No sheet approval or authorization, DB/Blob/source read, AI call, prompt
profile, summary/classification output, derived artifact persistence, finding
match or carryover, stage comparison, runtime wiring, full gate or beta claim.

## Deliverables

One additive pure module, focused refusal tests and a result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_summary_input.py tests/integration/comparison/test_raw_evidence_seal.py tests/integration/comparison/test_raw_text.py` — pass when host load permits;
- `../../../.venv/bin/python -m compileall -q src/auditmanager/comparison/summary_input.py tests/integration/comparison/test_summary_input.py` — pass;
- direct task governance, frozen-input SHA readback, `git diff --check` and
  exact changed-path proof — pass;
- no Docker, live DB, network or complete gate under R-135.

## Integration contract

The W59 comparison owner reads an authoritative pair and approved sheet links
in one consistent transaction, creates and stores immutable raw differences,
then passes that pair, all differences and their exact seal to this function.
The output is a deterministic, bounded input value with digest provenance,
not an approved comparison or AI result. A later owner must store any AI
summary as its own versioned derived artifact referencing the raw seal; it
must never overwrite or republish raw differences under that identity.

## Failure/idempotency/security cases

Mixed pairs, revisions, forged seals/diffs or noncanonical input refuse before
return. Every approved sheet remains represented even when unchanged; only
changed lines enter the proposed text. Oversized content refuses in full,
without truncating or dropping a sheet. Reordering the same raw diffs returns
identical output. No side effects or model calls occur.

## Rollback / feature flag

Remove the additive module before runtime wiring. No data rollback or flag.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: comparison owner completes SECTION-SEAL-dependent approval, raw and
  derived artifact custody, provider profile and runtime integration.

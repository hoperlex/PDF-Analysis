# Task W59-INT-RAW-EVIDENCE-SEAL-PREP-01 — seal exact version text evidence

task_id: W59-INT-RAW-EVIDENCE-SEAL-PREP-01

## Outcome

A pure verifier recomputes every approved page's raw text difference and
produces one deterministic checksum for the ordered version pair, approval
revision and complete page evidence. A future separate AI summary can name
this checksum without changing the raw evidence.

## Depends on

- `W59-INT-VERSION-RAW-TEXT-PREP-01` — completed deterministic page diff;
- `W59-INT-VERSION-PAIR-READ-01` — completed exact same-set/order reader.

## Frozen inputs

- base commit: `5e71a8c7451862cd0419722375a2c932c9b3928a`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis stage registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- roadmap SHA-256: `e7e73b21996c1c6f37f7b3f5cb741b7d50054dcd7751b3a401ed7fba514a7be5`;
- ADR-0013 SHA-256: `a5d8a88e1a7b531ea00cd383a7aa00f691cada0a1c118e807b48c1949eaab410`;
- migration head: `0022_findings_v2`; R-135; roadmap C-2 and ALR-23.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the approved raw page diff and ordered pair reader exist, but no
  cross-page checksum binds both versions and the approval revision for a
  separately derived AI artifact.

### P-01 — existing comparison boundary at exact base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD src/auditmanager/comparison`
- captured_output:
  ```text
  src/auditmanager/comparison/README.md
  src/auditmanager/comparison/decision_carryover.py
  src/auditmanager/comparison/raw_text.py
  src/auditmanager/comparison/version_reader.py
  ```
- interpretation: no existing comparison seal module is present at the base;
  this inventory does not establish runtime approval or artifact persistence.

### P-02 — derived artifact must retain raw provenance

- captured_at: 2026-10-16
- command: `rg -n '^\| ALR-23 ' docs/architecture/ARCHITECTURE_LINT_RULES.md`
- captured_output:
  ```text
  97:| ALR-23 | AI output stays a separate versioned derived artifact that references the source checksum; it is never republished under the identity of the raw evidence. | `review` | `error` | `Reviewer records: the AI review artifact has its own id and revision and names the raw diff checksum it was derived from.` | `Reviewer records: the AI summary is written into the diff artifact record so consumers reading raw evidence receive synthesis.` |
  ```
- interpretation: the seal gives a whole-comparison source checksum; the
  future owner still must persist distinct raw and derived artifact identities.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/raw_evidence_seal.py`
- `tests/integration/comparison/test_raw_evidence_seal.py`
- `docs/program/tasks/W59-INT-RAW-EVIDENCE-SEAL-PREP-01.md`
- `docs/program/W59-INT-RAW-EVIDENCE-SEAL-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing comparison modules, public boundaries,
routers, API/UI, workers, analysis profiles, storage, root dependencies/locks,
composition root, global styles, `CURRENT_STATE.md`, refs, tags and Docker.

## Non-goals

No sheet suggestion, authorization or approval persistence; no DB/Blob/source
read, AI generation, finding match, stage comparison, runtime wiring, full gate
or beta claim. A digest proves exact supplied bytes, not expert approval.

## Deliverables

One additive pure seal module, focused tests and this task/result pair.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_raw_evidence_seal.py tests/integration/comparison/test_raw_text.py tests/integration/comparison/test_version_reader.py` — pass;
- Python compilation, direct task governance, frozen SHA values, whitespace,
  `git diff --check` and exact owned-path proof — pass;
- no Docker, live DB, network or complete gate under R-135.

## Integration contract

The W59 comparison owner reads the authoritative pair and approved SheetLink
revision under a consistent transaction, runs `diff_approved_pairs`, then
`seal_raw_version_evidence`, and persists those raw page artifacts write-once.
The separate AI artifact references `seal_sha256` and has its own identity and
revision. The owner must verify approval, transaction consistency and artifact
custody; the seal itself cannot confer them.

## Failure/idempotency/security cases

Malformed comparison identity, missing diffs, mixed versions/revisions,
out-of-range/duplicate pages, forged lines or per-page checksum, and oversized
evidence refuse before a seal is returned. Input order has no effect on the
checksum. Version byte checksums and all page evidence participate in the seal.

## Rollback / feature flag

Remove the additive module before runtime wiring. No active behavior or data
migration changes; no feature flag required.

## Handoff

- changed paths/checks/limits: accompanying result report;
- contracts: none;
- next: comparison owner adds persisted approved links and separate raw/derived
  artifact custody after SECTION-SEAL.

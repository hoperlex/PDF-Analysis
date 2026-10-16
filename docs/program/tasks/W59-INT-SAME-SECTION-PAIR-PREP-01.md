# Task W59-INT-SAME-SECTION-PAIR-PREP-01 — check supplied version classifications

task_id: W59-INT-SAME-SECTION-PAIR-PREP-01

## Outcome

An unserved pure W59 comparison preflight accepts an already checked ordered
pair only when separately supplied classifications name each exact VersionUid
and agree on explicit P/R project stage and confirmed section code. It refuses
missing, foreign or mismatched facts before any raw comparison can use them.

## Depends on

- `W59-INT-VERSION-PAIR-READ-01` — completed ordered same-set version reader.
- `W59-INT-CONFIRMATION-PREP-01` — completed version-bound expert choice shape.
- `W59-SECTION-IDENTITY-DECISION-01` — completed W59 same-stage/section ruling.

## Frozen inputs

- base commit: `8c39b9e0dfd63da7d32d1a848e609ae2dd437a01`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- code-first scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- W59 section identity decision SHA-256: `6b0e8abf399833b1339dbc99586941ee7bf758b22b6778b30c50ec0a2b2a1788`;
- ordered version reader SHA-256: `1a1a6047a12350e0150a3d4366f22fa5d0bd5c9820c7428e6eabe6a806784964`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `VERSION=0.6.0`, R-135 intermediate-code checks.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W59's accepted identity decision requires matching version-bound
  stage and confirmed section for ordinary version comparison, but the
  completed version reader supplies only same-set/order/PDF facts.

### P-01 — accepted same-classification rule and absent pure guard

- captured_at: 2026-10-16
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/comparison tests/integration/comparison | rg 'version_reader|section|classification' && rg -n 'same explicit|same.*stage|same.*section' docs/program/W59-SECTION-IDENTITY-DECISION-01.md`
- captured_output:
  ```text
  8c39b9e0dfd63da7d32d1a848e609ae2dd437a01
  src/auditmanager/comparison/version_reader.py
  tests/integration/comparison/test_version_reader.py
  18:| Confirmed section | One expert-confirmed code from the complete 15-code catalogue is bound to one `VersionUid`, with confirming `UserUid` and auditable provenance. The same code on another version needs its own confirmation. No filename, text suggestion or legacy `document.section` is a confirmation. |
  60:  set and, for the version-comparison lane, have the same explicit `P` or `R`
  110:   not move; new version is unclassified. Compare explicit same-set/same-stage
  ```
- interpretation: the rule is approved, while this base has no pure
  comparison-stage compatibility guard. This does not establish a persisted
  source read or permit SECTION-SEAL/runtime wiring.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/version_section_pair.py`
- `tests/integration/comparison/test_version_section_pair.py`
- `docs/program/tasks/W59-INT-SAME-SECTION-PAIR-PREP-01.md`
- `docs/program/W59-INT-SAME-SECTION-PAIR-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing comparison/section modules, public
facades, run/API/UI/router code, analysis profiles, DB/S3 adapters, root
dependencies/locks, composition root, global styles, `CURRENT_STATE.md`,
remote refs, tags and Docker.

## Non-goals

No SECTION-SEAL, new section enum, profile activation, classification or
confirmation persistence, authority/ACL proof, W62 P-versus-R comparison,
AI summary, raw evidence write, served route, full gate or beta claim.

## Deliverables

One additive pure comparison guard, focused positive/refusal tests, this task
and its result report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_version_section_pair.py tests/integration/comparison/test_version_reader.py tests/integration/sections/test_staged_routing.py` — pass;
- Python compilation, full offline comparison suite, direct task governance,
  ALR-05 architecture, frozen SHA readback, exact-path handoff and
  `git diff --check` — pass;
- no Docker, DB/S3, network, provider or full gate under R-135.

## Integration contract

The future W59 comparison owner calls `read_ordered_version_pair` and reads
both versions' saved P/R stages and expert section confirmations in one
consistent authorized transaction. It passes exact version-bound values to
this pure guard before approved links or raw text are used. The guard returns
only a same-stage/same-section tuple for ordinary version comparison; it
cannot prove that supplied classifications came from storage. Only the later
SECTION-SEAL owner may wire a public/served path. The sealed fifteen-code
registry, not this guard's syntax check, decides whether a section exists.

## Failure/idempotency/security cases

Malformed or same/reversed pair, missing or foreign VersionUid, absent P/R or
section, stage mismatch (including P versus R), section mismatch (including
PS versus PB) all refuse. No inference from filename, legacy document section,
version ordinal or current-head pointer. Repetition gives equal immutable
output without I/O or side effects.

## Rollback / feature flag

Remove the new pure module before activation. No served/persisted behavior
changes; no feature flag or data rollback is needed.

## Handoff

- changed files/checks/risks: accompanying result report;
- contracts: unchanged;
- next: integrate after dev65 while keeping it unserved; future SECTION-SEAL
  and comparison owner supplies authorized persisted classifications.

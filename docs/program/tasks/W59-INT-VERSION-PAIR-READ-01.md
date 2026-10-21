# Task W59-INT-VERSION-PAIR-READ-01 — read exact ordered versions of one set

task_id: W59-INT-VERSION-PAIR-READ-01

## Outcome

A SELECT-only preflight verifies caller-named project, logical set (`Document`),
source VersionUid and target VersionUid against two published immutable rows,
then proves source-before-target order from per-document version ordinals.
It returns exact source metadata for a later approved sheet-pair raw diff;
no filename, title or page label is used as identity.

## Depends on

- `W59-INT-VERSION-RAW-TEXT-PREP-01` — completed approved-pair raw text seam;
- `CODE-FIRST-SCOPE-01` — completed W59 code-scope record.

## Frozen inputs

- base commit: `248179be684395170311c8c2fea604ddea165bb5`;
- source branch: `integration/code-first-entry`;
- domain identifiers SHA-256 `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- W58–W63 scope SHA-256 `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- roadmap SHA-256 `e7e73b21996c1c6f37f7b3f5cb741b7d50054dcd7751b3a401ed7fba514a7be5`;
- ADR-0013 SHA-256 `a5d8a88e1a7b531ea00cd383a7aa00f691cada0a1c118e807b48c1949eaab410`;
- migration head `0022_findings_v2`; glossary `Document`, migration `0002` document/version constraints and immutability guard; R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the glossary's logical document is a drawing set whose identity
  persists across versions; the DB stores each version's document FK and a
  unique ordinal per document. The comparison boundary has no reader yet.

### P-01 — same-set/order facts exist in frozen schema

- captured_at: 2026-10-15
- command: `rg -n 'Document \| логическая документация|document_uid     text NOT NULL REFERENCES document|version_ordinal  integer NOT NULL|UNIQUE \(document_uid, version_ordinal\)|"document_version",' docs/architecture/GLOSSARY.md db/migrations/versions/20260910_0002_pc01_schema.py`
- captured_output:
  ```text
  db/migrations/versions/20260910_0002_pc01_schema.py:460:            document_uid     text NOT NULL REFERENCES document (document_uid),
  db/migrations/versions/20260910_0002_pc01_schema.py:461:            version_ordinal  integer NOT NULL,
  db/migrations/versions/20260910_0002_pc01_schema.py:483:                UNIQUE (document_uid, version_ordinal),
  db/migrations/versions/20260910_0002_pc01_schema.py:1257:        "document_version",
  docs/architecture/GLOSSARY.md:8:| Document | логическая документация/чертёжный комплект | identity persists across versions |
  ```
- interpretation: a shared `document_uid` proves membership in one logical
  set and the ordinal orders its published versions; the ordinal is not an
  identity. The immutable-row trigger applies to `document_version`. The
  parent `document.project_uid` is current membership, not proven immutable.

### P-02 — new reader paths absent at frozen base

- captured_at: 2026-10-15
- command: `git rev-parse 248179be684395170311c8c2fea604ddea165bb5 && git ls-tree -r --name-only 248179be684395170311c8c2fea604ddea165bb5 src/auditmanager/comparison/version_reader.py tests/integration/comparison/test_version_reader.py docs/program/tasks/W59-INT-VERSION-PAIR-READ-01.md docs/program/W59-INT-VERSION-PAIR-READ-01.md`
- captured_output:
  ```text
  248179be684395170311c8c2fea604ddea165bb5
  ```
- interpretation: these four exact additive paths were absent; no existing
  version preflight proves the caller's set and ordered pair.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/version_reader.py`
- `tests/integration/comparison/test_version_reader.py`
- `docs/program/tasks/W59-INT-VERSION-PAIR-READ-01.md`
- `docs/program/W59-INT-VERSION-PAIR-READ-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing comparison/decision/document modules,
public boundaries, routers, API/UI, runtime workers, analysis profiles,
provider lock, root dependencies/locks, composition root, global styles,
`CURRENT_STATE.md`, refs, tags and Docker resources.

## Non-goals

No sheet suggestion or approval, comparison ID allocation, page text/Blob
read, AI, finding match, expert decision, DB write, authorization, API,
stage-policy reseal, full gate or beta claim. The reader proves current
project membership at its SELECT snapshot; schema does not freeze the
`document.project_uid` column for all future time.

## Deliverables

Additive SELECT-only version-pair reader, focused fake-session tests, task and
result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_version_reader.py` — pass;
- Python compilation, direct governance, frozen hashes, whitespace,
  `git diff --check` and exact owned-path proof — pass;
- no Docker, live DB or complete `make gate` under R-135.

## Integration contract

The later W59 comparison owner supplies exact ProjectUid, DocumentUid and
source/target VersionUid values; no display ordinal is accepted as identity.
The owner runs this reader under a consistent transaction before loading
approved SheetLink revisions and immutable source text. The one SELECT joins
both version rows to their logical set and current project, requires exactly
the two requested published versions, and returns their immutable checksum,
size, page count, media type and ordinals only if source ordinal is lower.
Approval/authorization and same transaction across subsequent reads remain
with the caller.

## Failure/idempotency/security cases

Malformed or equal caller IDs fail before SQL. Missing, duplicate, foreign,
unpublished, wrong-project/set or reversed rows fail without a partial pair.
Invalid stored digests and media facts also fail. Repeating the same SELECT
snapshot yields equal value objects; no side effect, fallback or inference.

## Rollback / feature flag

Remove the additive reader before runtime wiring. No active behavior or data
migration changes, so no feature flag is required.

## Handoff

- changed paths/checks/limits: accompanying report;
- contracts: none;
- next: comparison owner must supply authorized approved links and retain a
  consistent transaction through source reads and raw artifact publication.

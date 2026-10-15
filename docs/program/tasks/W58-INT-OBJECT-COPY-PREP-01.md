# Task W58-INT-OBJECT-COPY-PREP-01 — seal an offline S3 object mirror

task_id: W58-INT-OBJECT-COPY-PREP-01

## Outcome

An operator can seal and later recheck a separately mirrored, objects-only
directory against the W54 copy key's `inventory.tsv`. The check refuses a
missing, extra, changed, malformed or symlinked object, and records a SHA-256
for every payload. Focused tests prove safe repeated verification and a
write-once manifest. This is bounded W58 recovery-code preparation; it does
not close W58 or qualify a backup.

## Depends on

- `W54-STAND-COPY-01` — completed DB dump, S3 inventory and local restore-test mechanism.

## Frozen inputs

- base commit and local `origin/dev`: `5a51721a745a7bfc5c85cc4594625fa53cbce523`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- `copy-serve.sh` SHA-256: `998442c31a583831d3dd941e81cb7ef039045a2212a25bfb47c8ce14bbfa4f86`;
- `pull-copy.sh` SHA-256: `7e44d3f6f3126d8b758f85e031cc9a8bacb69023b5ac02f9616b60b397e341da`;
- `restore-test.sh` SHA-256: `2151a9264fe3ae457d9e4bda55275b37be608aed10362d381dc1503c792c30d1`;
- migration head: `0022_findings_v2`; R-135 defers full local gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the W54 pull contains a DB dump and object inventory but no S3 payload bytes.

### P-01 — one-off copy lists objects but does not fetch their bytes

- captured_at: 2026-10-15
- command: `sed -n '10,15p' infra/deploy/pull-copy.sh`
- captured_output:
  ```text
  # `fetch <STAMP> record|db|inventory`:
  #
  #   record.json    the copy record; its stamp must be <STAMP> and it must be a full copy
  #                  with its dump and inventory taken
  #   db.dump        must have the size and SHA-256 the record names
  #   inventory.tsv  must have the count, bytes and SHA-256 the record names
  ```
- interpretation: the current copy proves DB restoration and records a bucket
  listing, but it contains no S3 object payloads. The new tool checks a mirror
  obtained separately; it does not create one.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/object_copy.py`
- `tests/integration/recovery/test_object_copy.py`
- `docs/program/tasks/W58-INT-OBJECT-COPY-PREP-01.md`
- `docs/program/W58-INT-OBJECT-COPY-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency and lock files;
- `src/auditmanager/storage/**`, `src/auditmanager/norms/**`, `infra/deploy/**`;
- composition root, API/router, global styles, and other agents' corpus,
  section and comparison paths;
- `.local/norms/**`, working stand, Git refs/tags and `origin/main`.

## Non-goals

- No S3 transfer or readback, DB restore, recovery drill, operating RPO,
  backup scheduling, production activation or corpus publication.
- No claim that an ETag is a content digest or that this mirror is current
  after the writers resume.

## Deliverables

- Offline `seal` and `verify` CLI plus pure inventory parser and manifest checker.
- Focused tests and a report with exact limitations and integration steps.

## Required tests

- `../../../.venv/bin/python -m pytest tests/integration/recovery/test_object_copy.py -q -p no:cacheprovider` — all focused cases pass.
- `../../../.venv/bin/python -m py_compile scripts/recovery/object_copy.py` — syntax passes.
- `git diff --check` — no whitespace errors.
- Full gate and DB/S3 drill deferred under R-135 and the absent W58 freeze.

## Integration contract

After an owner-approved W54 `dump-db` → `inventory-s3` → `pull-copy` →
`restore-test` sequence, a later W58 transport may mirror every bucket object
into a private objects-only directory while writers remain stopped. This CLI
then seals `inventory.tsv` plus that mirror, writing `objects.json` beside the
private inventory; `verify` must pass again immediately before restore. A
future W58 owner must bind this seal to the W54 copy record and prove S3
readback, DB-to-Blob reference integrity, full restore and safe retry on
isolated data before making a backup claim.

## Failure/idempotency/security cases

- Exact keys and sizes from sorted inventory; SHA-256 over local bytes; any
  missing, extra, symlinked, unsafe or changed object refuses.
- Same sealed bytes repeat without modification; a different existing seal
  refuses, including a concurrent creation. Manifest mode is private.
- Object keys are transport locators, never domain identities.
- Mirror and inventory must be frozen together from seal through restore.

## Rollback / feature flag

No application behavior changes or feature flag. Remove the offline script
and its report if the later W58 transport adopts a different artifact shape.

## Handoff

- changed files: see `docs/program/W58-INT-OBJECT-COPY-PREP-01.md`;
- commands/results: see the same report;
- known limits: no live transfer/readback/restore;
- integration notes: retain as preparatory code until a separate W58 freeze.

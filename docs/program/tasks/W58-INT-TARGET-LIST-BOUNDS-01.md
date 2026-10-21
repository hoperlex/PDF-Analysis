# Task W58-INT-TARGET-LIST-BOUNDS-01 — bound isolated target listing

task_id: W58-INT-TARGET-LIST-BOUNDS-01

## Outcome

The unactivated W58 isolated target restore refuses a listing that exceeds
the sealed object count or keeps returning new continuation tokens beyond a
bounded number of pages. Valid one-object pages still allow exact readback.

## Depends on

- `W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01` — completed sealed target copy.
- `W58-INT-TARGET-RETRY-METADATA-01` — completed target retry metadata guard.
- `CFB-INT-DEV-PUBLISH-65` — completed published development predecessor.

## Frozen inputs

- base commit: `8c39b9e0dfd63da7d32d1a848e609ae2dd437a01`
- source SHA-256 `ef4de9fc117f32111472e01fb449a41b97ac2c036dee059afda0f426486674fa`;
- test SHA-256 `cd650a89191cac3aab66199642c95697077b9f3bd9fb406dcb1b04b69a8e6aec`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`; R-135 defers the complete beta gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the listing detects a repeated continuation token, but new unique
  tokens can keep it running; a hostile page can also add arbitrary rows
  beyond the known sealed count.

### P-01 — unbounded target listing

- captured_at: 2026-10-16
- command: `rg -n '^def _target_listing|^def restore_sealed_objects|_target_listing\\(client' scripts/recovery/target_object_restore.py`
- captured_output:
  ```text
  97:def _target_listing(client: TargetObjectClient, bucket: str) -> dict[str, int]:
  171:def restore_sealed_objects(
  199:        before = _target_listing(client, target_bucket)
  228:    after = _target_listing(client, target_bucket)
  234:    if _target_listing(client, target_bucket) != after:
  ```
- interpretation: every target listing knows the expected sealed object set
  in its caller, but the helper receives no count limit. This does not prove
  an actual hostile S3 endpoint or live recovery failure.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01.md`
- addendum_path: `docs/program/W58-INT-TARGET-LIST-BOUNDS-01.md`

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/target_object_restore.py`
- `tests/integration/recovery/test_target_object_restore.py`
- `docs/program/tasks/W58-INT-TARGET-LIST-BOUNDS-01.md`
- `docs/program/W58-INT-TARGET-LIST-BOUNDS-01.md`

## Forbidden hotspots

Other `scripts/recovery/**`, `src/**`, `contracts/**`, migrations, `infra/**`,
root dependency/lock files, composition root, global styles,
`CURRENT_STATE.md`, corpus data, service resources, refs and tags.

## Non-goals

No live S3 request, production target identity, DB restore, source writer
quiescence, atomic bucket snapshot, W58 drill or beta acceptance.

## Deliverables

Three count-bounded target listings, bounded-refusal regressions, passing
normal paginated retry tests, this task and result addendum.

## Required tests

- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/recovery/test_target_object_restore.py tests/integration/recovery/test_source_object_mirror.py tests/integration/recovery/test_object_copy.py` — pass.
- Programme governance, owned Python compilation, frozen SHA-256 readback,
  exact four-path handoff and `git diff --check` — pass.
- No Docker, PostgreSQL/S3, provider or full gate under R-135.

## Integration contract

Each target listing gets the exact sealed object count. It refuses a page
that would make the target set larger than that count and refuses after at
most count+1 page requests, while retaining unique-token, key, size and
final exact-set checks. A target with one key per page remains valid. No
upload starts until the initial bounded listing passes; later listings can
refuse a changed target after partial upload.

## Failure/idempotency/security cases

Fresh unique tokens with empty truncated pages and oversized listings
refuse finitely. A changed target after upload still refuses. An empty seal
allows one empty nontruncated page; one foreign key refuses. Repeated runs
with stable valid bytes retain the same result.

## Rollback / feature flag

Revert the four owned paths before activating the operator drill. No served
behavior or persisted schema changes; no runtime flag or data rollback.

## Handoff

- changed files/checks/contracts/limits: paired result addendum;
- next: integrate a source commit into a separate `origin/dev` slot after
  exact path review; this task has no push authority.

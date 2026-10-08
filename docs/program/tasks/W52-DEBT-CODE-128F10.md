# Task W52-DEBT-CODE-128F10 — make reconciliation categories truthful

task_id: W52-DEBT-CODE-128F10

## Outcome

The ingest reconciliation report exposes only categories that `Reconciler.report()` can
produce. A Blob without a manifest or analysis intent is called unattributed regardless
of its age; the report never claims it is an action-ready orphan.

## Depends on

- `W52-INT-128F1-01` — published at
  `bd7cb62a70e758c4b88c44e8e664ddfb90977cb3`.

## Frozen inputs

- Exact base `bd7cb62a70e758c4b88c44e8e664ddfb90977cb3`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-128 F-10 in `reviews/W48-JUDGE-Z.md`; proposed W52 plan at `2b45a11` assigns
  F-10 to a separate DEBT-CODE slot. No W52 freeze or contract reseal is claimed.
- Owner direction 2026-10-08: proceed without approval; only basic tests and lint;
  QA, stand and full gate remain D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the report has two unpopulated fields and misnames an unattributed row as legacy.

### P-01 — exact base and report construction

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; rg -n 'class (OrphanObject|LegacyUnattributedBlob|ReconciliationReport)|orphan_objects:|unpublished_records:|legacy_unattributed_blobs:|return ReconciliationReport' src/auditmanager/ingest/reconciliation.py`
- captured_output:
  ```text
  bd7cb62a70e758c4b88c44e8e664ddfb90977cb3
  166:class OrphanObject:
  176:class LegacyUnattributedBlob:
  236:class ReconciliationReport:
  239:    orphan_objects: tuple[OrphanObject, ...] = ()
  240:    unpublished_records: tuple[OrphanObject, ...] = ()
  241:    legacy_unattributed_blobs: tuple[LegacyUnattributedBlob, ...] = ()
  436:        return ReconciliationReport(
  ```
- interpretation: `report()` populates only the third category; the review proves the
  `legacy` label also covers a newer interrupted document upload.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/ingest/reconciliation.py`
- `src/auditmanager/ingest/__init__.py`
- `tests/integration/ingest/test_reconciliation.py`
- `tests/integration/ingest/test_reconciliation_rules_with_no_guard.py`
- `tests/integration/runs/test_durable_effect_boundaries.py`
- `tests/unit/ingest/test_reconciliation_report.py`
- `docs/program/W52-DEBT-CODE-128F10.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, dependencies/locks, routers,
composition root, global styles and the separate D-133/W56 tasks.

## Non-goals

No new age/provenance inference, automatic Blob rejection, store listing, wire API
change, D-128 closure without integration, W52 freeze, QA, stand, full gate, tag or
`origin/main` publication.

## Deliverables

- Replace the stale report categories with `unattributed_blobs: tuple[UnattributedBlob]`;
  preserve Blob identity, recorded state, digest, size and presence.
- Update the report summary and consumers, and state explicitly that old and new
  document uploads can enter this category without Attempt authority.
- A pure unit regression test for the public report shape and conservative summary.

## Required tests

- Focused pure unit test and Python syntax compilation; basic repository lint/check if
  available; `git diff --check`. Database integration tests remain deferred with QA.

## Integration contract

Hand back a clean branch from the exact dispatch SHA with only allowed paths. The
integrator may publish this internal Python report correction to `origin/dev` after
exact remote-ref and fast-forward verification. No wire contract is resealed.

## Failure/idempotency/security cases

Unattributed rows are never described as proven old or safe to delete. `is_clean` must
be false when one exists; an empty report remains clean. The rejection path retains
its current refusal without Attempt authority. Repeated reports use the same categories.

## Rollback / feature flag

Revert the code commit. No runtime feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.

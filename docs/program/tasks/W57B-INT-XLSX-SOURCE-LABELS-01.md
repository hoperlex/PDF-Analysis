# Task W57B-INT-XLSX-SOURCE-LABELS-01 — bind XLSX page labels to version input

task_id: W57B-INT-XLSX-SOURCE-LABELS-01

## Outcome

A SELECT-only source reader returns page labels from the pinned version's stored
portal block list after matching its immutable manifest, available blob
metadata and actual bytes. Pages without an unambiguous portal label refuse.

## Depends on

- `W57B-INT-XLSX-PACKAGE-PREP-01` — completed caller-supplied XLSX package seam.
- `W57B-INT-XLSX-READ-PREP-01` — completed finding reader requiring labels.

## Frozen inputs

- base commit: `62a9e23dd44cdd7d9373e69413ce6ad27e508d3d`
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §B3.5.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  portal block schema SHA-256 `b4e286219614dbcb892d95b40beef4ae89408650dfb27ebf6ecd399e611ede2a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- migration head `0022_findings_v2`; no head movement.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `source.structured_companion` has a version-bound manifest and
  `page_label` per portal block; finding evidence has page numbers only. There
  is no persisted finding citation source at this head.

### P-01 — additive task paths

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/exports/xlsx/source_labels.py tests/integration/exports/test_xlsx_source_labels.py docs/program/tasks/W57B-INT-XLSX-SOURCE-LABELS-01.md docs/program/W57B-INT-XLSX-SOURCE-LABELS-01.md`
- captured_output:
  ```text
  62a9e23dd44cdd7d9373e69413ce6ad27e508d3d
  ```
- interpretation: the four paths are additive at this base.

### P-02 — actual source and missing citation storage

- captured_at: 2026-10-15
- command: `rg -n 'source.structured_companion|page_label: int|page_number      integer' src/auditmanager/ingest/bundle_members.py src/auditmanager/analysis/geometry/portal.py db/migrations/versions/20260910_0002_pc01_schema.py`
- captured_output:
  ```text
  db/migrations/versions/20260910_0002_pc01_schema.py:990:            page_number      integer NOT NULL,
  src/auditmanager/ingest/bundle_members.py:11:``_blocks.json``           ``source.structured_companion``    ``source_structured_..``    application/json
  src/auditmanager/analysis/geometry/portal.py:71:    page_label: int
  ```
- interpretation: labels can be derived from the stored companion only for pages whose blocks agree; this does not establish any citation mapping.

### P-03 — citation storage absent in existing finding schema and 0022

- captured_at: 2026-10-15
- command: `rg -n 'citation' db/migrations/versions`
- captured_output: empty (exit 1).
- interpretation: migrations through head 0022 have no persisted citation relation. This task cannot assert that an explicit empty XLSX citation tuple is verified.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/exports/xlsx/source_labels.py`
- `tests/integration/exports/test_xlsx_source_labels.py`
- `docs/program/tasks/W57B-INT-XLSX-SOURCE-LABELS-01.md`
- `docs/program/W57B-INT-XLSX-SOURCE-LABELS-01.md`

## Forbidden hotspots

Existing XLSX read/projection/package/writer, CSV, routers, contracts,
migrations, composition root, root dependencies/locks, global styles, corpus,
`CURRENT_STATE.md`, W56A paths, tags and remote refs.

## Non-goals

No citation mapping or normative assertion, no S3 implementation, no export
authorization, no route, no fallback from page number, no live DB, full gate,
release or beta acceptance.

## Deliverables

SELECT-only source binder, focused fake-session and portal-byte tests, source
gap report and exact changed-path proof.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_source_labels.py tests/integration/exports/test_xlsx_package.py` — pass when host load permits;
- Python compilation, direct task governance, whitespace and exact path proof — pass;
- no `make gate` under R-135.

## Integration contract

`read_verified_page_labels(session, version_uid, read_blob=...)` uses the
caller's consistent transaction to SELECT the version, its
`source.structured_companion` manifest and available blob metadata. It calls
the injected, caller-owned storage read exactly once with the selected opaque
blob ID, verifies bytes against both metadata declarations, then projects
only label-related fields from the pinned portal schema. It returns immutable page-number to
display-label mapping and a version/blob/digest source reference. A missing
version returns `None`; an unlabelled or ambiguous page refuses. The result can
fill `ExportSources.page_labels` and `page_label_source_ref` only for that same
version. The caller still verifies run version, export policy and citations.

## Failure/idempotency/security cases

Missing companion, unavailable blob, inconsistent digest/size/media type,
unreadable or changed bytes, malformed layout, absent or conflicting page
labels refuse. No inferred label; no SQL writes or commit. Repeated immutable
inputs yield equal values.

## Rollback / feature flag

Remove the additive resolver and test before runtime wiring; no data rollback
or feature flag is needed.

## Handoff

- changed files/checks/limits: see report;
- contracts: none;
- next: W57b seal/API owner must wire a verified citation source and run-policy
  check before any XLSX export is exposed.

# W57B-INT-XLSX-SOURCE-LABELS-01 — version-bound page labels

## Result

`read_verified_page_labels` selects the exact published document version, its
`source.structured_companion` manifest entry and the associated available blob
metadata. It refuses a missing or mismatched binding before a storage read.
The caller-owned storage reader is invoked once; returned bytes must match the
manifest and blob size and SHA-256. A purpose-specific reader checks the
pinned portal schema version, page indices and block labels. The resolver requires one consistent label from
blocks for every PDF page; it never substitutes the page number for a missing
label. It returns a read-only mapping and a version/blob/digest reference.

The result is usable as the XLSX package's `page_labels` and
`page_label_source_ref` after the sealed caller matches the same `version_uid`
to the run. The code is SELECT-only, owns no transaction and does not access
S3 directly.

## Citation source gap

At migration head `0022_findings_v2`, `finding_evidence` stores page numbers and
project evidence but there is no persisted per-finding normative citation
relation. The W57a pure citation guard can produce grounded candidates, but
neither it nor the current XLSX package proves their durable finding mapping.
This task did not invent a citation source or reinterpret an explicit empty
tuple as verified absence. XLSX remains without API/runtime exposure; the
W57b seal must supply and verify `citations_by_finding` separately.

## Checks

- `nice -n 19 ionice -c3 ../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_source_labels.py tests/integration/exports/test_xlsx_package.py` — **33 passed**.
- `../../../.venv/bin/python -m compileall -q src/auditmanager/exports/xlsx/source_labels.py tests/integration/exports/test_xlsx_source_labels.py` — pass.
- Direct `governance_findings` on the task — `[]`; the strict task parser accepts
  the exact base SHA and four additive paths. Whitespace check — pass.
- No full gate, live DB/S3 read, spreadsheet application probe or API policy
  test was run under R-135.

The tests cover intact bytes, immutable returned labels, absent version,
wrong manifest version or role, unavailable or mismatched blob, changed or
unreadable bytes, invalid portal shape, unlabeled pages and conflicting labels.
The fake session rejects SQL other than SELECT.

## Changed files

- `src/auditmanager/exports/xlsx/source_labels.py`
- `tests/integration/exports/test_xlsx_source_labels.py`
- `docs/program/tasks/W57B-INT-XLSX-SOURCE-LABELS-01.md`
- `docs/program/W57B-INT-XLSX-SOURCE-LABELS-01.md`

These four additive paths are the task allowlist. This task did not modify the
other W56A agent's visible files or any existing XLSX, contract, migration,
composition, root dependency, style, corpus, tag or remote path. No commit or
push was made.

## Integration and limitations

The caller supplies a consistent read transaction, a blob reader that uses
the selected opaque blob ID, and a run/version match. A bare PDF, a portal
bundle page without a block, or any conflicting portal labels refuses. This
deliberate coverage limit can block XLSX export for otherwise valid versions;
it needs an authoritative full-page display-label source before wider use.
No contracts changed. Removing the additive files before runtime wiring is
the rollback; no data migration or feature flag is needed.

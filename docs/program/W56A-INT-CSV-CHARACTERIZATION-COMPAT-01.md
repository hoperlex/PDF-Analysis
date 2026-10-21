# W56A-INT-CSV-CHARACTERIZATION-COMPAT-01 — historical CSV compatibility

## Result

The wave-13 CSV characterization compares record 12 to the current W56a
nineteen-column export through a narrow in-memory projection. It verifies the
immutable source's SHA-256, pre-token length, BOM, CRLF, exact seventeen-column
header and five data rows, then appends `severity,severity_proposed` to the
header and two empty cells to each row. All original CSV bytes remain in order.
The projection is used by the main record comparison and the O1 permutation
and mutation probes. No historical record or runtime producer was edited.

The decoded tokenized historical body is 3973 bytes. Its `length` metadata is
the original pre-token 4409-byte response. The projection adds 27 ASCII
header bytes and 10 delimiters over five rows, yielding 4010 tokenized bytes
and a derived pre-token length of **4446**. This arithmetic has not been
confirmed against a live PostgreSQL characterization journey.

## Changed files

- `tests/characterization/w13_baseline/test_response_baseline.py`
- `docs/program/tasks/W56A-INT-CSV-CHARACTERIZATION-COMPAT-01.md`
- `docs/program/W56A-INT-CSV-CHARACTERIZATION-COMPAT-01.md`

## Checks

- `../../../.venv/bin/python -m pytest -q tests/characterization/w13_baseline/test_response_baseline.py -k csv_compat`: **2 passed, 61 deselected**. The pure probes check both appended fields are empty and catch legacy-byte, BOM, CRLF, extra-column and nonempty-severity mutations.
- `../../../.venv/bin/python -m compileall -q tests/characterization/w13_baseline/test_response_baseline.py`: passed.
- Direct `governance_findings` for the exact task: empty set.
- `git diff --check`: passed.
- Frozen W56 plan, API, error catalog, analysis registry and provider lock hashes match the task. Migration head remains `0022_findings_v2`.

## Contracts and limits

No `contracts/**`, migration, serializer, query, composition root, root
dependency/lock file, global style or historical record was changed. This is
test-only compatibility for the additive W56a CSV surface; it neither grants
runtime v2 activation nor establishes a beta acceptance result. The full
characterization suite needs the DB-backed journey and is pending under
`R-135`; the two new pure probes do not establish live byte identity.

## Integration instruction

Keep `records/12-exportRunCsv.success.json` unchanged. On isolated PostgreSQL
migrated through 0022, run the full characterization file and inspect record
12 for exact projected bytes, including both empty severity cells. If it
differs, diagnose the producer and the separately owned CSV pins before
changing this projection. Include this task's three paths in the integration
allowlist; no Git ref, checkpoint or tag was changed by this lane.

## Ownership proof

This lane edited only the three exact paths in its task. The record-12 file
and `journey.py` are absent from its diff, as are all forbidden hotspots.

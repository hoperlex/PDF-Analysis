# W59-INT-VERSION-RAW-TEXT-PREP-01 — development result

Added a pure, bounded raw text comparison for explicit approved SheetLink
pairs. It binds every result to opaque ComparisonId, SheetLinkId and two
VersionUid values, the approval revision and page coordinates within those
versions. It preserves exact line endings and Unicode text, records all
equal/change spans, and hashes both inputs and the canonical evidence body.
The frozen output contains tuples only. Pair order does not alter output.

The function refuses a missing, duplicated, mixed-version or stale-revision
link, missing page text and input above explicit limits (32 pairs, 200,000
characters or 1,000 lines per page, 2,000,000 characters or 4,000 lines per
call). There is no implicit sheet matching and no filename/page number used
as entity identity. The page number is only a coordinate within VersionUid.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_raw_text.py`: **14 passed**.
- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/architecture/test_analysis_public_stage_version.py`: **1 passed**.
- `../../../.venv/bin/python -m compileall -q src/auditmanager/comparison/raw_text.py tests/integration/comparison/test_raw_text.py`: passed.
- Direct task governance: `[]`.
- Mutating the matcher to report every line as equal made
  `test_exact_text_and_provenance_are_immutable_and_repeatable` fail as
  expected; the mutation was in one Python process and did not edit files.
- `git diff --check`: passed for tracked changes; each untracked owned file
  passed `git diff --no-index --check /dev/null <file>` with no whitespace
  diagnostics. The integrator should repeat staged `git diff --check`.
- Ruff was unavailable in this worktree's venv, so no Ruff result is claimed.
- Full local gate deferred under R-135.

## Contracts, limits and integration

No contract, migration, API, active comparison route, DB, S3, AI, finding or
decision behavior changed. `ApprovedSheetPair` is a pure input shape: this
module cannot authenticate the approving expert, prove that a link was stored,
prove same-set membership or choose the version order. SECTION-SEAL and the
comparison owner must supply authoritative approved links, persist immutable
raw evidence keyed by checksum, keep AI summaries in a separate derived layer
and build finding matching plus confirmed decision carryover. For large sets,
the owner must define a revision-aware paging/chunk policy rather than silently
truncating this function's input. The provisional pair shape must be checked
against the future W59 comparison seal.

Changed files: `src/auditmanager/comparison/raw_text.py`,
`tests/integration/comparison/test_raw_text.py`, this report and
`docs/program/tasks/W59-INT-VERSION-RAW-TEXT-PREP-01.md`. They are exactly the
task's allowed paths. Forbidden hotspots and refs were not touched by this
lane. Rollback removes these additive files before runtime wiring; no data
rollback or flag is needed.

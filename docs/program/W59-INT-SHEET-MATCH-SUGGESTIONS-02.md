# W59-INT-SHEET-MATCH-SUGGESTIONS-02 — result

An unserved pure module proposes unique exact full-page text pairs from a
complete ordered-version page snapshot. Moved pages match. Changed, blank and
duplicated page text abstains. The candidate carries version and comparison
identity, page coordinates, source text SHA-256 and a digest that binds both
version PDF checksums. No `SheetLinkId` or approval is created.

## Changed files

- `src/auditmanager/comparison/sheet_match_suggestions.py`
- `tests/integration/comparison/test_sheet_match_suggestions.py`
- `docs/program/tasks/W59-INT-SHEET-MATCH-SUGGESTIONS-02.md`
- this report.

## Checks

- Focused sheet, raw-text and finding-match suite: **39 passed** in 0.50 s.
- Python compilation, frozen checksums, owned-file whitespace, `git diff
  --check` and direct task handoff: see final handoff evidence.
- No Docker, live DB/S3, network or complete gate under R-135.

## Contracts and limitations

No contract, migration, existing module, public boundary, router, API/UI,
worker, dependency, composition root, global style, `CURRENT_STATE.md` or ref
changed. The caller must supply authoritative complete page text; this pure
function cannot prove DB/Blob custody. Textless, changed or duplicate pages
require expert pairing. Suggestions never supersede approved links.

## Integration instruction

Integrate only the four new paths. After W59 SECTION-SEAL, the comparison
owner can load the complete immutable page snapshots, show candidates for
explicit expert review, persist approved SheetLinks separately, and then
produce raw differences from those approved links. No suggestion may be
treated as a link, a finding match or a decision.

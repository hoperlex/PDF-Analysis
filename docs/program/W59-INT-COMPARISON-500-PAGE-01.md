# W59-INT-COMPARISON-500-PAGE-01 — result addendum

W55b admits 500-page versions, but the W59 comparison reader, sheet candidate,
raw evidence seal and finding-match guard still refused more than 30 pages.
They now share `MAX_VERSION_PAGES=500`. The complete text snapshot uses
W55b's 200,000-character page and 20,000,000-character document ceilings.
UTF-8 hashing holds one page's encoded text at a time. A synthetic 500-page,
text-rich pair over the old 2 MB budget produces 500 moved-sheet candidates.

## Changed files

- `src/auditmanager/comparison/{version_reader,sheet_match_suggestions,raw_evidence_seal,finding_match_suggestions}.py`;
- matching tests in `tests/integration/comparison/` for those four modules;
- `docs/program/tasks/W59-INT-COMPARISON-500-PAGE-01.md`;
- this report.

## Checks

- Complete focused comparison suite: **95 passed** in 0.55 s.
- Python compilation, frozen hashes, exact owned paths, whitespace and direct
  task handoff: see final local evidence.
- No Docker, live DB/S3, network or complete gate under R-135.

## Contracts and limitations

No contract, migration, served route, API/UI, storage, profile, root dependency,
composition root, global style, `CURRENT_STATE.md` or ref changed. This is an
unserved preflight and pure-policy correction. `raw_text.MAX_PAIRS=32` and its
2,000,000-character raw-diff budget still limit one approved comparison
revision. A 500-page version is accepted, but a full 500-link raw comparison
requires a separate budget/persistence decision. Complete authoritative
page-text custody and approval are still absent.

## Integration instruction

Integrate after `W59-INT-SHEET-MATCH-SUGGESTIONS-02`; its base is that exact
commit. Review all ten owned paths together so reader, candidate, seal and
finding-match limits stay aligned. Do not activate a public comparison or
assume candidates are approved links. The previous task/report remain the
historical record at their own SHA; this addendum explains the correction.

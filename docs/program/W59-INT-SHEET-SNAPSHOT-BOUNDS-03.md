# W59-INT-SHEET-SNAPSHOT-BOUNDS-03 — result addendum

The unserved exact sheet suggestion now checks each page's 200,000-character
ceiling and the snapshot's 20,000,000-character ceiling before allocating its
UTF-8 encoding. The maximum ordinary Unicode page encoding is therefore
800,000 bytes as claimed by the earlier 500-page comparison task. Matching,
output order and digest construction are unchanged.

## Changed files

- `src/auditmanager/comparison/sheet_match_suggestions.py` — move both
  character checks before `encode`;
- `tests/integration/comparison/test_sheet_match_suggestions.py` — source and
  target page refusal before encoding, aggregate crossing-page refusal, and
  frozen exact-limit digest regression;
- `docs/program/tasks/W59-INT-SHEET-SNAPSHOT-BOUNDS-03.md` — source freeze;
- this addendum.

## Checks

- The two refusal tests failed on the base implementation because their
  oversized `str` subclass reached `encode`; the exact-boundary test passed.
- Complete focused comparison suite after the fix: **99 passed** (see final
  local evidence for the exact command and observed count).
- Python compilation, frozen hashes, exact owned paths, whitespace and direct
  task governance: see final local evidence.
- No Docker, DB/S3, network or full gate under R-135.

## Contracts and limits

No contract, migration, served route, API/UI, storage, profile, root
dependency, composition root, global style, `CURRENT_STATE.md` or ref changed.
For a valid 100-page snapshot with exactly 20,000,000 characters on each
version and a 200,000-character Cyrillic page, the candidate retains
`page_text_sha256=e125e459ef1f20607b55f5e1430a143b7a3d7ada463cb6c56b7ec9953a4c44d7`
and `suggestion_sha256=dd38eb7c61170ad2fa8ef3c8e3b2d7ef1917d63b0d2c224ec726935950cb9d00`.
The caller still must supply complete authoritative page text and obtain
expert approved links separately. The 32-pair raw diff ceiling is untouched.

## Integration instruction

Integrate after `W59-INT-COMPARISON-500-PAGE-01`; review all four owned paths
together. This source commit is an unserved memory-bound correction, not an
approval, runtime activation or beta acceptance.

# W59-INT-FINDING-MATCH-SUGGESTIONS-01 — conservative finding candidates

## Result

`suggest_exact_finding_matches` maps source quote pages only through caller
supplied approved SheetLinks, compares the exact category and NFC/whitespace
normalized issue text and quote content, and proposes a pair only when that
key is unique on both versions. A page can move between versions. A changed
issue, missing link or duplicated issue yields no suggestion, and no absent
finding is marked fixed. Each suggestion has a SHA-256 over the exact source
and target observation values, comparison/revision and link identities.

## Changed files

- `src/auditmanager/comparison/finding_match_suggestions.py`;
- `tests/integration/comparison/test_finding_match_suggestions.py`;
- `docs/program/tasks/W59-INT-FINDING-MATCH-SUGGESTIONS-01.md`;
- this report.

## Checks

- Focused W59 matching, carryover and raw seal suite: **36 passed** in 1.60 s.
- Python compilation, direct task governance `[]`, frozen SHA-256 values,
  owned-file whitespace, `git diff --check` and exact changed-path proof:
  passed.
- No Docker, live DB, network or full gate under R-135.

## Contracts and limitations

No contract, migration, existing module, public boundary, router/API/UI,
worker, dependency, composition root, global style, `CURRENT_STATE.md` or ref
changed. Suggestions are conservative: semantically equal issues with changed
wording or quote do not match. The caller still must prove the pair, sheet
approval and complete run snapshots; this function cannot authorize or
persist matches, carry decisions or mark an absent issue resolved.

## Integration instruction

Integrate only the four new paths. The W59 owner may display these digest
bound suggestions for expert review, persist approved matches with explicit
revision and provenance, and then re-read current decisions before calling
the separate confirmed carryover policy. Never use a suggestion as a decision
or a proof that an unmatched source finding has been fixed.

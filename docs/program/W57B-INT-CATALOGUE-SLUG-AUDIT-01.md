# W57B-INT-CATALOGUE-SLUG-AUDIT-01 — source designation coverage

## Result

The pinned local 674-document corpus manifest was scanned read-only. The
previous pure W57b parser recognized **588** slugs and left **86** unparsed.
Adding the explicit ГОСТ IEC/ISO and ГОСТ Р ИСО/МЭК subseries recognizes 29
more, for **617 parsed and 57 unparsed**. Subseries remain distinct from
ordinary numeric ГОСТ designations, and extraction keeps raw occurrence
offsets. The family vocabulary version is
`norm-reference-families-prep-v2`.

The remaining 57 slugs are saved only as the local, unreviewed candidate
`/root/projects/PDF-Analysis/.local/norms/reference-unparsed-candidate.json`
(7,848 bytes; SHA-256
`202d3f8b22003a9a2a2505043a27af42130cb805a3a2e9874e4e15f7b7c6c37d`).
Its source manifest SHA-256 is
`160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`.
It is a review input, not a runtime allowlist or proof of a promoted snapshot.

| Remaining source type | Count |
| --- | ---: |
| Приказ | 20 |
| МДС | 7 |
| Постановление, Решение | 6 each |
| Письмо | 3 |
| Правила, Статья | 2 each |
| Градостроительный, Здания, Изменение, Инструкция, Информационное, Методика, ПЭУ, Поправка, РД, Распоряжение, Справочная | 1 each |

## Checks

- `tests/integration/norms/references/test_reference_resolution.py`: **23 passed**.
- Exact read-only manifest scan: 674 = 617 parsed + 57 candidate; candidate
  bytes and SHA-256 recorded above.
- Python compilation, direct task governance, frozen contract hashes and
  whitespace check: passed.
- Full `make gate` deferred under R-135. No source checksum sweep, database,
  embedding or stand operation ran; available RAM stayed below W54's heavy
  step floor during this task.

## Contracts and limits

No API/domain/analysis contract, migration, provider lock, root dependency,
composition root or global style changed. The local manifest is source
metadata, not a qualified snapshot. The 57 exceptions need an owner decision
against the eventual promoted catalogue, and the SQL/Python token twin still
needs its database equality sweep at the W57b gate. Unparsed forms are not
silently treated as absent from the corpus.

## Integration instruction

Carry the candidate's exact digest into the later catalogue review. For each
remaining slug, either extend a named family with tests or approve its
unparsed status. Re-run the scan on the actual promoted catalogue and refuse
if its source digest or document set differs. Then bind the reviewed list to
the W57b stage's pinned catalogue; do not load the local candidate as policy.

## Ownership proof

Only the three named reference parser/vocabulary files, their focused test,
this task/report and `CURRENT_STATE.md` were changed in Git. The ignored
candidate is the sole local output. Source corpus files, manifest,
`contracts/**`, migrations, provider lock, root dependencies/locks,
composition root, global styles, stand and `origin/main` were untouched.

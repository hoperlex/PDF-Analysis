# W56A-MATCHER-CORE-PREP-01 — offline matcher handoff

**Base:** `origin/dev=68b6f81f241e00192b52bf0a2cc4351897f06c3c`.
The committed synthetic manifest remains at SHA-256
`95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7`.

## Result

`tools/evaluation/matcher.py` implements the mechanical PC-02 §11 rule:
same bundle, category and page, with a predicted quotation containing or
contained by a seeded quotation. Every observation member of a merged group
is considered. It counts each seeded issue/control once, reports 21-case
recall and seven-control false-positive pressure, per-category figures,
unmatched groups and one-group-to-many-issue over-merge. It never matches by
finding UID, invents no baseline, and does not invoke a provider.

## Changed files and checks

- New `tools/evaluation/{__init__,matcher}.py`.
- New `tests/contract/evaluation/test_matcher_core.py`.
- New task and this report under `docs/program/`.
- Focused pytest: **15 passed**, including empty-prediction zero recall,
  any-member match, substring in both directions, same-document/category/page
  boundaries, control hit, over-merge, duplicate prediction and malformed
  ground-truth refusals.
- Python compilation and `git diff --check`: passed. No full local gate,
  recorded run, paid call or service-backed acceptance ran.

## Integration and limits

Merge this exact commit through a dedicated dev integration task. HARNESS
later adapts actual recorded findings, supplies the baseline and enforces
the measured threshold; the matcher alone is not a quality verdict. The
source manifest, API/domain/stage contracts, migration, model lock,
runtime executor, web, root dependencies, global styles, `origin/main` and
tags are untouched. The two-gateway model identity block remains.

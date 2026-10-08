# W52-DEBT-CODE-129F3 — executor handoff

Task: `docs/program/tasks/W52-DEBT-CODE-129F3.md`. Exact code base:
`2f82396d60ca32630584471292d36317c9d226bf`; dispatch commit `d605acb`.
This repairs D-129 Y F-3 only.

`name_label` now selects one uppercase letter from an expanding Unicode mapping.
The accepted initials `ß`, `ŉ` and `ǰ` yield `S`, `N` and `J`, so a 60-character
surname with two initials stays at the frozen 66-character API bound. A character
with no uppercase mapping keeps its original glyph, preserving existing behaviour
while still fitting the bound.

Changed files: `src/auditmanager/access/models.py`,
`tests/integration/access/test_account_names.py`, and this report. The focused
`TestTheLabel` selection passed **11/11** tests; Python compilation, frontend lint
and `git diff --check` passed. No database fixture or temporary stand was used.
Broader QA and full gate remain D-139/D-140.

No contract, migration, dependency/lock, router, composition root or global style
changed. The Unicode code point used as an initial can lose a combining mark when its
uppercase mapping expands, as with `ǰ` → `J`; it remains a truthful one-letter initial
within the existing contract. Integrator may merge this clean branch to `origin/dev`
after exact ancestry and basic checks. Revert the code commit to roll back; no flag.

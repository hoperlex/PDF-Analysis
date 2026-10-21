# W56A-RULE-01 — owner rulings and W56a check/review alignment

**Base:** `8c5a109bd98302b64fb47b364d4c639ff63c0eda` (`integration/w55b`, still under
acceptance). **Branch:** `agent/w56a-rule-01`. **Task:** `tasks/W56A-RULE-01.md`.

## 1. Result and changed files

The H-1…H-10 answers already given in `dispatch/ROADMAP-TO-BETA.md` §10.14 are recorded as
`R-129`…`R-134`. W56a's plan now names those rulings and follows `R-124` (one whole-wave judge,
then FIX) and `R-126` (backend database suites in the final gate). The owner's 2026-10-14
instruction lets this document-only task run while W55b acceptance continues; W56a freeze and
implementation still depend on `W55B-INT-CLOSE`.

Changed paths:

- `AGENTS.md` — §8 scoped overrides for `R-102` and `R-126`.
- `docs/program/OWNER_RULINGS_2026-09-17.md` — §3.35, `R-129`…`R-134`.
- `docs/program/dispatch/W56-PLAN.md` — numbered ruling references, review/check sequence,
  and an explicit note that the older estimate needs revision at the freeze.
- `docs/program/tasks/W56A-RULE-01.md` — this task's grant and frozen inputs.
- `docs/program/W56A-RULE-01.md` — this report.

## 2. Checks and results

On the branch above, from its worktree:

| Command | Result |
| --- | --- |
| `git diff --check` | exit 0 |
| `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | exit 0, 77 passed in 53.71 s |
| `rg -n 'R-Z[1-6]|W56A-QA-01|W56A-JUDGE-[XY]|W56A-NOTES-JUDGE' docs/program/dispatch/W56-PLAN.md` | exit 1, no live references |
| `sha256sum contracts/api/v1/openapi.json contracts/domain/v1/error-codes.json contracts/analysis/v1/stage-registry.json` | same three digests as the task's frozen inputs |

The first test invocation used `tests/contract/test_doc_prose_facts.py`, which does not exist;
pytest exited 4 before collecting anything. The task command was corrected to the actual
`tests/contract/api_v1/` path and the 77 tests above passed. No gate is owed for these
document-only changes.

## 3. Contracts, limitations and rollback

No API, domain, analysis or migration contract changed. The migration head remains
`0021_portal_bundles`. These rulings authorise later W56a work; they do not implement it.

The W55b acceptance may add owner rulings after this branch's base. If it takes any of
`R-129`…`R-134`, renumber this section and every W56a reference before merge. The W56a
freeze must also re-estimate the plan after `R-124` and re-sweep its code and contract pins
against the accepted W55b tree. Rollback before freeze is a revert of this document commit;
there is no runtime state to restore.

## 4. Integrator handoff and hotspot proof

Rebase onto `W55B-INT-CLOSE`; confirm the next free ruling number; run the document checks
again; then use the recorded rulings as frozen inputs to `W56A-FREEZE-01`. Do not dispatch
SEAL, GENERATOR or Stage B from this branch alone.

`git diff --name-only 8c5a109bd98302b64fb47b364d4c639ff63c0eda` and `git status --short`
show only the five paths in §1. `contracts/**`, `db/migrations/**`, root dependencies and
lockfiles, composition roots, global styles, the W55b worktrees, refs and the stand were
untouched. The `AGENTS.md` and owner-ruling edits are the explicitly owned integration slot
in `tasks/W56A-RULE-01.md`.

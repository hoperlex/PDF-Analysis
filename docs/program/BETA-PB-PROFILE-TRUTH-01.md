# BETA-PB-PROFILE-TRUTH-01 — beta UI fixtures follow the served ПБ profile

Task: `docs/program/tasks/BETA-PB-PROFILE-TRUTH-01.md`; base `d1487c75fb80a02689c1ce3f08570448591b3c40`.

## Result

The normal «Настройки анализа» and rendered-language fixtures now carry all fifteen registered profiles. ПБ appears as an authored `draft` with `source: null` and an expert-review label. All fifteen normal classification options are executable. A synthetic server response missing ГП still exercises both profile-less refusal presentations. `CURRENT_STATE.md` now reflects the 14 non-AR synthetic recorded profiles; none is expert accepted by those recordings.

## Changed files

- `web/tests/unit/analysis-settings/analysis-settings.test.ts`: ПБ draft and explicit missing-ГП case.
- `web/tests/guards/rendered-language.guard.test.ts`: truthful normal profiles/options and a synthetic missing-ГП confirmed state.
- `web/tests/unit/sections/classification-panel.test.ts`, `classification-correction.test.ts`: remove stale comments about the shared fixture.
- `docs/program/CURRENT_STATE.md`: current registry and recording status.
- The task and this result note.

## Checks

- Byte comparison of `web/package.json` and `web/package-lock.json` with the gate worktree: equal. A temporary ignored `web/node_modules` symlink allowed the checks without installing packages; it was removed afterward.
- Modified TypeScript parsed with zero syntax diagnostics in all four files.
- `tests/contract/api_v1/test_doc_prose_facts.py`: **44 passed**.
- Four focused rendered suites: **101 passed, 1 failed**. All 18 analysis-settings and all 58 section tests pass. The only failure is the global rendered-language branch ratchet: it names four missing AR v3 group review states added by the previous screen task. This is unrelated to ПБ and is the next task's owned guard/UI repair.
- `npm --prefix web run typecheck`: fails on the earlier AR v3 stage union and group-review request `signal` type; these are the next task's owned source repair.
- `git diff --check`: pass.

## Contracts, risks and integration

No contract, API, registry, migration, generated file, served UI or feature flag changed. The ПБ profile remains a draft and its synthetic recording is not acceptance evidence. The next task must repair the two type errors and seed the four reachable group-review branches in the language matrix, then rerun both checks before development publication.

Only the task's allowed files changed. Forbidden hotspots were untouched. Keep this commit in the development candidate and do not update `origin/main`.

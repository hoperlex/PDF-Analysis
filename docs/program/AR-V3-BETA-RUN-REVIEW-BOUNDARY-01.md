# AR-V3-BETA-RUN-REVIEW-BOUNDARY-01 — v3 review stays separate from canonical findings

Task: `docs/program/tasks/AR-V3-BETA-RUN-REVIEW-BOUNDARY-01.md`; base `289f1eb0182029dd53d7eae3407ee85ca55f1ec0`.

## Result

The generic Run page detects the exact AR v3 beta profile and does not offer the canonical «Разобрать находки» link for its `published` or `partial` terminal. A successful v3 Run says that a preliminary normative review was saved, that canonical findings are not published, and that every topic and quote needs expert review. A partial v3 Run does not claim a complete verified result. The page directs the reviewer to «Настройки анализа» to enter the group ID; it does not invent a group ID from the Run ID. Legacy `published` and `partial` Runs retain their canonical review entry point.

## Changed files

- `web/src/entities/audit-run/model/run-presentation.ts`: the canonical review gate excludes the exact v3 beta profile.
- `web/src/widgets/run-progress/ui/run-progress.tsx`: distinct review-only terminal copy and no canonical link or finding count for v3.
- `web/tests/unit/run/provider-mode.test.ts`, `web/tests/unit/screens/run-progress.test.ts`: exact-profile positive and negative cases on rendered output.
- `web/tests/guards/rendered-language.guard.test.ts`: a published v3 Run state reaches the new copy; no branch waiver.
- `docs/program/CURRENT_STATE.md`, the task and this result note.

## Checks

- `npm --prefix web run typecheck`: **pass**.
- Provider-mode, Run-progress and rendered-language guard suites: **125 passed**.
- `npm --prefix web run lint -- --quiet`: **pass**.
- `tests/contract/api_v1/test_doc_prose_facts.py`: **44 passed**.
- `git diff --check` and task handoff: **pass** on the exact committed diff.
- Temporary ignored `web/node_modules` link to byte-matching installed dependencies was removed after testing. No dependency or lockfile was changed.

## Contracts, risks and integration

No contract, migration, generated client, provider or pack changed. The separate group-review screen requires the group ID returned at start; `RunStatus` does not carry that identity, so this slice can point to the screen but cannot deep-link from one Run. The v3 profile remains review-only; no finding or expert decision is published by this UI. A future API could expose a safe group link if the product needs direct navigation.

Only task allowed paths changed; forbidden hotspots were untouched. Integrate the exact checked tree into `origin/dev` only. Full `make gate`, approved pack and live stand acceptance remain open under `R-135`; `origin/main` remains unchanged.

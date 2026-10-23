# WEB-HISTORY-SEVERITY-FAULT-01 — decision history closes on unknown severity

Task: `docs/program/tasks/WEB-HISTORY-SEVERITY-FAULT-01.md`. Base: `b8a3c67d200773f6bc1697118ac5255acb5fb555` (`origin/dev`).

## Result

`DecisionHistory` checks every event's severity against the generated closed set before ordering or rendering. One unknown member, including a malformed `null`, shows the existing closed-vocabulary history fault and hides every event. The fault text now identifies severity as one possible cause. Known severities and omitted severities keep their previous rendering. The knowledge base keeps its own badge fault policy.

`D-201` is narrowed to the remaining v2 `merged_observations` producer. The verdict/comment hook isolation and language guard were completed in `WEB-HOOKS-PER-FINDING-01`; this task completes the history part.

## Evidence

- Failing first: the revised history test failed on the base code, with the unknown `urgent` member and the second event visible in a two-event ledger (1 red, 28 green).
- Focused history and adjacent widget tests after the fix: 55/55 passed. Final combined history/widget/language-guard run after the malformed-`null` case: 82/82 passed (3 files).
- Typecheck and lint with `--quiet`: both exit 0.
- `git diff --check`: exit 0.
- Task governance checker: no findings (`[]`).

## Contracts and integration

No schema, contract, migration, route, vocabulary, dependency, lockfile, composition root or global style changed. The browser may rely on `data-history-fault="closed-vocabulary"` and on no event content rendering when any decision severity is unknown. Revert this task's commit to roll back; no flag is needed.

## Limits

The v2 `merged_observations` producer remains absent; a real served run has not been shown to supply those observations. This UI correction neither activates v2 nor v3 execution. `origin/main` and deployment are outside this task.

## Handoff

Changed paths are the history widget, its focused test, the D-201 row, this report and its task file. All lie in the task allowlist. The integrator can fast-forward the checked commit to `origin/dev`; no additional consumer change is needed.

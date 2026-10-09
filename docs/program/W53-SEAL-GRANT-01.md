# W53-SEAL-GRANT-01 — historical custody task is read-only

The W53 plan and first SEAL task grant named
`docs/program/tasks/NORM-CUSTODY-01.md` as an editable custody-design path.
Direct inspection on the frozen Stage-A base showed that this is a completed
historical task with a handoff and test record. The task template's
historical-evidence rule requires a new addendum rather than rewriting it.

The exact replacement grant is
`docs/program/NORM-CUSTODY-W53-ADDENDUM.md` (new), alongside the already
granted `NORM_CORPUS_CUSTODY.md`, decision backlog and ADR addendum.
`docs/program/tasks/NORM-CUSTODY-01.md` is forbidden and must remain bytewise
unchanged. No other SEAL path or behavior grant changes. The agent may use
`git show <this-grant-sha>:docs/program/tasks/W53-SEAL-01.md` to read the
updated task without rebasing its in-progress branch.

This is a docs-only repair grant. The integrator checks the agent's changed
paths and the historical task's unchanged blob before accepting SEAL.

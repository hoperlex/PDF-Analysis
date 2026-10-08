# W52-RULE-01 — owner rulings recorded

The owner confirmed all three W52 §4 deviations directly on 2026-10-08:
hand-written expected facts with separately maintained live prose; serial
full-gate acceleration without `pytest-xdist` while R-70 light acceptance
continues; and unchanged `contract_version` until beta freeze. The earlier
roadmap answers V-1…V-10, P-2 and W-1 support the remaining wording.

`OWNER_RULINGS_2026-09-17.md` now records R-71 through R-74. The W52 plan
uses those numbers, and the roadmap's W52 A5/A6 rows and D-120's pending
decision status are reconciled. This is the ruling step only: W52 has no
freeze SHA, task grants, gate, QA or release verdict. D-120's accepted-risk
closure remains for `W52-INT-CLOSE` as the plan assigns it.

Checks on the seven-path documentation candidate: each of R-71…R-74 has
exactly one ruling heading; no `R-V1`…`R-V4` remains in the W52 plan;
`git diff --cached --check` passed; the focused programme governance and
prose/surface suite passed **93 tests**. No full `make gate` or live check
was run under the owner's W52 code-only deferral.

The contract set is unchanged: domain candidate revision 9 / 29 identities,
API 27 paths / 34 operations / 77 schemas, 23 error codes and Alembic head
`0015_accounts_roles_registration`. The freeze must remeasure all of these
on its own base; the preflight figures are advisory.

Changed tracked files: this report and task; `OWNER_RULINGS_2026-09-17.md`;
`dispatch/W52-PLAN.md`, `dispatch/ROADMAP-TO-BETA.md`;
`CURRENT_STATE.md`, `DEBT_REGISTER.md`. No contract, migration,
dependency/lock, composition root, global style, product code/test or
deployment path changed. After checks and exact remote ancestry, the
integrator may fast-forward only `origin/dev`. No `origin/main` authority.

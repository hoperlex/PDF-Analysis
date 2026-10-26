# EXEC-PAR-DECISION-01 — the decisions behind parallel runs on chosen executors

Written 2026-10-26 on `f6ee66ee`. This is the decision record of
[`dispatch/EXEC-PARALLEL-RUNS-PLAN.md`](dispatch/EXEC-PARALLEL-RUNS-PLAN.md); read that for the
facts of the tree. The owner answered by direct poll (`AskUserQuestion`) on 2026-10-26. The
integrator records them as numbered rulings; no ruling number is invented here.

| # | Question | Owner's answer | Effect |
| --- | --- | --- | --- |
| 1 | What is wanted? | Checks of **different documents** run at the same time, each on an executor chosen **explicitly in the UI**. (A first reading, a cross-check of one fragment on several executors, was wrong and is dropped.) | one run, one executor, chosen at run start |
| 2 | How many runs at once? | **4 worker slots.** The default stays `1`; `AUDITMANAGER_WORKER_SLOTS=4` turns it on. | supersedes the slot count of `R-146j` («один воркер без SLO») when the setting is raised; `1` is the rollback |
| 3 | Runs at once on one executor | **One.** A second run for a busy executor waits in the queue and does not hold a slot. | per-connection limit `L = 1` in the claim |
| 4 | What next? | Implement the slices. | `EXEC-PAR-START-01`, `EXEC-PAR-QUEUE-01`, then `EXEC-PAR-WEB-01` |

Decided by the plan and not contradicted (the owner may reopen them):

- An explicit executor choice **never falls back** to the standby or to another executor: an
  unusable choice refuses the start with a typed `dependency_unavailable`.
- A run that makes no choice behaves exactly as today (the global route, the standby rule).
- «Повторить прогон» keeps the original run's executor; if it is no longer usable the repeat is
  refused, not redirected.
- The AR v3 group (`EXEC-PAR-V3-01`) is not in the first release.

Consequences for the slots (`AGENTS.md` §3): the contract slot is `EXEC-PAR-START-01`'s, the
composition-root slot is `EXEC-PAR-QUEUE-01`'s, and `EXEC-PAR-WEB-01` owns the web paths and starts
after `EXEC-PAR-START-01` is integrated, because it consumes the regenerated client.

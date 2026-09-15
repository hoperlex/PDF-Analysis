# Wave 2 — burn down the debt the expert sessions would otherwise pay for

Base `ff39cb6b2d5539ef26791b7247a875505df003a0`. Three parallel implementation sessions, then one independent QA, serial.

## Why this wave, and why now

`P4-BHV-01` puts 3–5 experts in front of this stack. Expert time is the scarcest resource
the programme has, and `OD-18` has not yet named the people. **This wave does not shorten
the path to PC-02** — that path is owner-blocked on `OD-17` and `OD-18` — it removes three
taxes the expert sessions would otherwise pay, and it runs in parallel with recruitment.

Each item is something the measuring session recorded and deliberately did not repair:

1. **An 18% attempt-failure rate with no retry in the executor.** `P4-RUN-01` saw three of
   seventeen attempts fail `dependency_unavailable` at ~133 s and retried by hand in its own
   harness. `P4_CLOSURE.md` §6: "A retry policy for `dependency_unavailable` belongs in the
   run executor, not in each caller… that is not a licence for every caller to invent its
   own." An expert watching a 133-second failure is the worst place to discover this.
2. **`model_call.status` cannot record `truncated`,** which `B3`'s provenance emits. The
   ledger PC-02 will cite therefore mis-files a real outcome class as `failed`.
3. **The query surface declares `cursor`, `limit`, `category` and `verdict` and implements
   none.** An expert working fourteen documents' findings meets this immediately.

A fourth, cheap and recommended by the same session: record the provider's **output-token
count** beside the finding count, so a later reader can tell "read it and found nothing"
from "returned after ten tokens". `PC02-C01` and `PC02-C07` returned after 10; `PC02-C09`
reasoned for 530 and still published nothing.

## Why three sessions and not one

The path sets are disjoint and the migration head has exactly one writer:

| Session | Owns | Migration head |
|---|---|---|
| `W2-RUN` | `src/auditmanager/runs/**`, `tests/integration/runs/**` | no |
| `W2-PROV` | `db/migrations/**`, `src/auditmanager/analysis/text/provenance.py`, the stage metrics it writes, `tools/validation/ledger_report.py`, their tests | **yes, sole writer** |
| `W2-API` | `contracts/api/v1/**`, `src/auditmanager/api/**`, `web/src/shared/api/generated/**`, their tests | no |

`W2-QA` runs after all three are merged, authored none of them, and repairs none of them.

## Order and gates

`W2-RUN`, `W2-PROV` and `W2-API` dispatch together from the base above. The integrator
merges in the order they return, running the full battery after each. `W2-QA` dispatches
only from the convergence commit, once all three are in.

`W2-PROV` changes behaviour PC-01 certified, so the PC-01 record is bound to `6d3c0f3` and
this wave does not amend it. If the owner wants PC-01 re-certified on the new tree, that is
a fresh `C2` run and a separate decision.

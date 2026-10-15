# W56a model-probe spend ledger

**Opened before live calls, 2026-10-15.** Owner ceiling: $5 for all W56a live
activity (`R-29`, `R-134`). This ledger records the model identity probes only;
later W56a calls must add their own entries and recompute the remaining budget.

## Pre-call projection

Four tiny calls are planned: configured and default on each of two distinct
gateways. Each uses a synthetic, one-sentence prompt and `max_tokens=16`.
Reserve **$0.25** for all four, far below the $5 wave ceiling. The configured
model's locked maximum for 100 input and 16 output tokens is $0.0009 at the
Opus $5/$25 per million-token rates. The default model is unknown; a response
whose actual cost exceeds the remaining reserve stops further calls and requires
reprojection. The reserve is a cap for this probe sequence, not an asserted price.
Before any call, the selected-model rate check is fixed at **20% relative or
$0.00002 absolute, whichever is larger**, comparing reported `usage.cost` with
the lock's input/output-token calculation. A missing cost or usage count fails.

| Call | Gateway role | Selection | Status | Reported cost, USD |
| --- | --- | --- | --- | ---: |
| 1 | stand | explicit locked model | completed; identity/rate FAIL | 0.0000046 |
| 2 | stand | default/stub | stopped after call 1 | — |
| 3 | recording | explicit locked model | stopped; access unresolved | — |
| 4 | recording | default/stub | stopped; access unresolved | — |

Actual probe total: **$0.0000046** from one reported response. Remaining wave
ceiling by this ledger: **$4.9999954**. No retry or default call was made after
the explicit-model failure. The gateway reported 14 input and 16 output tokens;
at the locked Opus $5/$25 rates that would cost $0.00047, about 102 times the
reported amount. The response named a different concrete model. This is a stop,
not a rounding difference.
No private URL, token or customer content belongs in this ledger.

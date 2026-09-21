# W25-COST — `metrics["cost_basis"]` describes the figure beside it

**Session** `W25-COST`. **Branch** `agent/w25-cost`, from `origin/dev` = `fea3794`.
**Lane** `gate-w25b`. Carries out owner ruling `R-14`
(`docs/program/OWNER_RULINGS_2026-09-17.md` §3.8), the design call `DEBT_REGISTER.md`
**`D-15`** was opened for and `W18-SEAL` deliberately declined to inherit.

| | before | after |
|---|---|---|
| `metrics["cost_basis"]` | the **last response's** provenance | an aggregate over **every** contribution to `metrics["cost_usd"]` |
| where the rule lives | an expression repeated in two metric dicts | `CostMeter.cost_basis`, read by both |
| gate | 1932 / 5 / 168, foundation 35, frontend 706 (48 files) | **1942 / 5 / 168, 35, 706 (48)**, exit **0** |
| characterization records | 36, none carrying `metrics["cost_basis"]` | **36, byte-identical, none moved** |
| contracts | untouched | **untouched** — `contracts/**` is `W25-SEAL`'s |

## 1. What was measured on arrival, and where the brief is wrong

The brief and `D-15` both say the defect is reached like this: *"a run whose first attempt
replayed and whose second reported a cost publishes a two-attempt sum wearing one attempt's
provenance."* **That run cannot happen, and the tree says so in three places.**

A retry is taken only for `dependency_unavailable` — `RETRYABLE_STAGE_ERRORS` holds exactly
that one code, and `RetryPolicy.__post_init__` refuses to construct over any code the frozen
catalog does not mark retryable. Every site that raises it
(`recorded.py:100`, `proxy.py:121,282,287`, `live.py:51,106`) raises it **from inside
`adapter.complete()`** — before `cost_meter.charge(...)`, which `run_text_analysis` reaches
only once the response is in hand. So an attempt that is retried charged **nothing**, and an
attempt that charged is never retried: every error reachable after the charge
(`cost_budget_exceeded`, `analysis_failed` from a truncated reply or from
`assert_consistent_mode`) is `retryable: false`.

The suite already asserts this without naming it —
`tests/integration/p02_journey/test_retry_provenance_seam.py` pins
`control_meter.call_count == 1` after a **three-attempt** run, with the comment *"a three-
attempt run charges once"*. A run therefore makes at most one **charged** model call, its
`model_call` row count is at most one, and a retry alone can never make the sum and the last
response disagree.

**The defect is real and the mechanism is a different one.** `metrics["cost_usd"]` is
`round(cost_meter.spent_usd, 8)` — the meter's *whole* spend, not this call's cost — while
`metrics["cost_basis"]` was `response.reported_cost_usd is not None` — this call alone. The
two describe different quantities whenever the meter carries more than one contribution, and
the meter is a per-**run** object handed to every attempt on purpose (`OD-03`: a retry must
not buy a fresh ceiling). Two ways to reach that state exist today:

1. **a meter opened carrying spend.** `execute_run`'s own docstring: *"A caller may supply one
   already carrying spend — nothing in the deployment does, and a test does, to place a run
   mid-budget."* `tests/integration/runs/test_retry_policy.py` hands it `spent_usd=0.90` and
   asserts the persisted `metrics["cost_usd"] == 1.40`. That row said **`measured`**, over a
   figure 0.90 of which nobody priced.
2. **one meter, two calls into the stage.** The accumulation the executor performs across
   attempts, reached directly.

So: `D-15`'s **measurement** of the two expressions is exact, its **story about how a run
gets there** is not, and the same wrong story is quoted verbatim in the `permitted_change`
prose of five characterization records. The consequence for scope is small — the repair is
the one `R-14` ruled either way — but the consequence for a reader is not: nothing in the
deployment can currently produce a wrong `metrics["cost_basis"]`, and this repair is
therefore a **structural guarantee about a figure that accumulates**, not a fix to an
observable production defect. It is worth having for exactly the reason `R-14` gives: the two
places now say the same thing.

## 2. The rule, and where it lives

`CostMeter` gains one counter, one derived property, and no new argument:

* `unpriced_contributions` — `init=False`. `charge()` increments it when
  `reported_cost_usd is None`, **beside** the `spent_usd` and `call_count` increments and
  **before** the ceiling check, so the call that broke the budget counts in all three. This is
  `W18-SEAL`'s NULL-is-unmeasured care one layer earlier: `None` here is the same absence that
  becomes a NULL `cost_micros` on the row, caught before a `sum` can skip it silently.
* `__post_init__` counts a non-zero **opening balance** as one unpriced contribution. Spend a
  meter did not charge has no provenance at all, and `measured` is the flattering reading of
  "no provenance recorded" — `D-3` is this programme's record of what that costs.
* `cost_basis` — `measured` only when at least one call was charged and **every** contribution
  reported a cost; `estimated` otherwise, including the meter that has charged nothing. That
  last case cannot reach the metrics (both emit sites run after a charge), and is stated
  rather than left to the coincidence.

Both metric dicts in `analysis/text/stage.py` — the success path and the budget-overrun path —
now read `cost_meter.cost_basis`. **`_record` still reads the response**, and that is not an
inconsistency left behind: the record's figure is *that call's* cost and the metric's figure is
*the run's*, so `model_calls[0].cost_basis == "measured"` beside
`metrics["cost_basis"] == "estimated"` is two correct answers about two different numbers.

**One divergence from `RunStatus.cost_basis` is pre-existing and deliberate, and I did not
change it.** On the overrun path the `model_call` row is written `cost_basis="estimated"`
because the figure stored on it is the pin's own computation, not the reported one — the
module says so at the call site. The meter, meanwhile, charged the *reported* figure. So a run
that overran on a priced call can persist a row reading `estimated` while its metrics read
`measured`. Both are true of their own number. Changing the row is `RunStatus`'s side of the
seam and a non-goal here.

## 3. The discriminating case, and how it was built without sleeping

**No retry is staged and nothing sleeps** — and per §1 a retry could not have produced this
case anyway. The mechanism is the accumulation itself, which is deterministic and needs no
failure, no clock and no gate to reach.

* **At the stage** (`tests/integration/analysis/test_stage_status_and_cost_rules.py`): one
  `CostMeter` handed to two `run_text_analysis` calls — the same object for the same reason
  `_run_text_analysis_stage` hands one to every attempt. First call replays (no reported
  cost, charged 0.01 from the pins), second reports 0.02. `metrics["cost_usd"]` is 0.03;
  `metrics["cost_basis"]` must be `estimated`. **Both orders** are asserted, because a rule
  keyed on the last response passes one of the two by luck. A third test charges two
  *priced* calls and requires `measured`, so hard-wiring `estimated` reddens. A fourth drives
  the **overrun** dict by the same rule, and a fifth opens the meter at 0.90.
* **Through `execute_run`** (`tests/integration/runs/test_retry_policy.py`): the discriminating
  **pair**, against real PostgreSQL, real MinIO and the committed recording. Same outage
  script both halves — `_ScriptedProvider(outages=1, reported_cost_usd=0.50)`, whose wait is
  `sleep=lambda _seconds: None` as the rest of that file already does. A fresh meter persists
  `cost_usd 0.50 / measured`; a meter opened at 0.90 persists `cost_usd 1.40 / estimated`.

**Shown able to fail.** `src/` was copied to a scratch directory, the two changed modules
reverted there to their state at `76925da` (contracts, docs, fixtures, db and tools
symlinked, as `make mutation-copy` does), and the new tests run from the worktree with
`-o pythonpath=<copy>/src`. No tracked file was edited to produce the red.

```
8 failed, 31 passed
tests/integration/runs/test_retry_policy.py::test_a_persisted_sum_that_spans_unpriced_spend_is_not_called_measured
E  AssertionError: 1.40 is published as measured while 0.90 of it was priced by nobody
E  assert 'measured' == 'estimated'
tests/integration/analysis/…::test_the_metrics_basis_is_estimated_when_an_earlier_charge_reported_nothing
E  assert 'measured' == 'estimated'
```

The pre-fix run's **control halves stayed green** — the fresh-meter row still read `measured`,
and the single-call success and overrun tests `W11-FIX` left behind never moved — so the red is
the rule and not the harness.

## 4. Characterization records

**Measured, not assumed: zero of the 36 records carry `metrics["cost_basis"]`.** Five carry a
`cost_basis`, and all five are `RunStatus.cost_basis` — `W18-SEAL`'s property, over the
`model_call` rows, untouched here. The four hits for `cost_usd` are all inside the
`permitted_change` **prose** of those same records, not in a response body: no API surface
publishes `stage_result.metrics`.

So **no record moved**, the byte-for-byte comparison passes unchanged, and `PERMITTED_EXCEPTIONS`
is not extended. `W20-CODE` refused to write a `permitted_change` for a change that did not
happen; this is the same refusal.

One consequence for a later reader: the `permitted_change` prose in records 04, 05, 06, 07 and
34 says *"that pair is D-15, it is unrepaired"*. It **was** unrepaired when that text was
written and it is the record of a past decision, so it is left exactly as it is. The two stale
comments that were **not** evidence — `runs/repository.py`'s `_COST_SUMMARY` note and
`RunCost`'s docstring, both asserting the stage still describes the last response — are
corrected, comment-only.

## 5. What a consumer sees differently

A consumer reading `stage_result.metrics["cost_basis"]`:

* **for every run the deployment can currently produce, nothing changes.** One charged call per
  run, so the sum is that call and the old expression and the new rule agree — including the
  replayed run (`estimated`), the priced run (`measured`) and the budget-overrun run
  (`measured`, as before: the meter charged the reported figure).
* **for a run whose meter carried spend it did not price, the word changes from `measured` to
  `estimated`.** The number does not change. No key is added, removed or re-typed, the value
  stays one of the same two strings, and `contracts/analysis/v1/stage-result.schema.json`
  admits it as it did before.
* the direction of the change is one-way and unflattering: it can turn `measured` into
  `estimated` and never the reverse. A reader who trusted the old word over a multi-
  contribution sum was being told something nobody had measured.

`RunStatus.cost_basis`, the CSV, the API bodies and the frontend are untouched.

## 6. Gate

`make gate` on the lane `gate-w25b` (POSTGRES_PORT 55970, S3 59570/59571, `audit_w25b`,
bucket `auditmanager-gate-w25b`), provisioned with
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` and `npm --prefix web ci`, both exit 0.
Output redirected to a file and the status read from `$?`, never through a pipe:

```
battery   1942 passed, 5 skipped, 168 subtests   (base 1932 + the 10 tests above)
foundation 35 passed
frontend  706 passed in 48 files
GATE OK: battery, foundation, frontend and whitespace all pass
GATE EXIT=0
```

No tag, no checkpoint, nothing pushed to `main`, no image built.

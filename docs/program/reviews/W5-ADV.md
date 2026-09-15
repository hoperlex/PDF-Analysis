# `W5-ADV` — adversarial QA of what waves 2 and 3 changed

Session `W5-ADV`, 2026-09-15. Worktree `/root/w5adv`, branch `agent/w5-adv`, instance
`gate-w5a` (55570 / 59170 / 59171, database `audit_w5a`, bucket `auditmanager-gate-w5a`).
`W5-CERT` was live on 55560 / 59160 / 59161 throughout; I never addressed those ports.

I authored none of waves 2 or 3 and I repaired nothing. Four guards added, 793 → 797.
Five mutations run: four red, one green-and-then-reddened.

## 0. `HEAD` on arrival

`beaa7f732bcb0c87f612db82c0159e785247a5a9`, on `planning/prototype-roadmap`.

The brief names `ef5b8bf6cbef240fe6b63043455545fb4bdf12b8` as the base and says that being
one or two commits ahead is harmless if the difference touches only
`docs/program/dispatch/**`. It does:

```
$ git diff ef5b8bf..HEAD --stat
 docs/program/dispatch/W5-ADV.md  | 12 +++++++-----
 docs/program/dispatch/W5-CERT.md | 14 ++++++++------
 2 files changed, 15 insertions(+), 11 deletions(-)
```

So the provisioning defect the brief predicted did **not** fire: the harness had not seeded
me from `origin/main` at `6d3c0f3`. I built the worktree from `origin/dev` anyway, as
instructed, and it landed on the same commit.

## 1. Commands, with exit codes

| Command | Exit |
|---|---|
| `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | 0 |
| `make foundation` — 35 passed | 0 |
| `.venv/bin/pytest tests --ignore=tests/contract --ignore=tests/checkpoint` (baseline) | 1, then 0 — see below |
| `.venv/bin/pytest tests --ignore=tests/contract --ignore=tests/checkpoint` (final) — **797 passed, 5 skipped, 116 subtests**, 200.09 s | 0 |
| `git diff --check` | 0 |
| `make check-db` (after the migration round trip) | 0 |

The baseline run reported `793 passed, 5 skipped, 1 error, 116 subtests` and exit 1. The
error was **mine**: I created a probe file inside `tests/` while the battery was running,
and the session-scoped autouse `checkout_is_unchanged` fixture in
`tests/integration/foundation/conftest.py` failed the session at teardown, naming the
untracked file. The guard did exactly its job, and `OPERATING_CONSTRAINTS.md` §8 — freeze
the tree before the battery — is the rule I broke. The passing counts were unaffected:
**793 passed / 5 skipped / 116 subtests**, as the brief predicted.

The final battery ran on a frozen, committed tree (`git status --porcelain -uall` empty).

## 2. The seam: `terminal_reason` on the exhausted-budget path

**Answer: the run row says `dependency_unavailable`, it is correct, and — contrary to the
brief — it was already asserted.**

The brief's premise is that `test_terminal_reason_names_the_cause.py` "reaches the
unreachable-provider case by a different route", leaving `audit_run.terminal_reason`
unasserted after an exhausted budget. **That is false.** Its fixture builds a
`RecordedAdapter` over an empty directory. That adapter raises `dependency_unavailable`,
which `RETRYABLE_STAGE_ERRORS` marks retryable, so the run it drives is retried to
exhaustion. It is not a different route; it is *the* route.

Measured, with a counting wrapper around that exact adapter:

```
provider calls   : 3          (== ATTEMPT_BUDGET)
waits            : [2.0, 8.0] (== BACKOFF_SECONDS, in order)
result.attempts  : 3
stage metrics    : attempts 3, attempt_budget 3, attempt_budget_exhausted True,
                   retried_on_error_code 'dependency_unavailable'
stage error      : dependency_unavailable
run row          : state 'failed', terminal_reason 'dependency_unavailable',
                   degradation_set ['text_analysis']
```

The behaviour is right. What was missing is not the assertion but the *statement of the
route*: nothing said that the wave-3 guard depends on `dependency_unavailable` staying
retryable. Make it non-retryable, or move the empty-recordings failure onto another code,
and that suite silently becomes a single-attempt test while still claiming to cover the
unreachable provider. Two guards now hold it (§3).

Mechanism, for the record: with all four `PC01_STAGES` persisted, `execute_run` builds
`stage_errors` from the stage rows and `_reason_for(['text_analysis'], …)` finds a single
distinct catalog code. I also checked the failure mode that would bypass this — if a
required stage had no row at all, `execute_run` takes the `missing` branch and hard-codes
`analysis_failed`. It does not fire here: `text_analysis` is the last required stage, so
its failure leaves no later required stage unwritten.

I also confirmed `audit_run`'s CHECK on `terminal_reason` is exactly the 20-member catalog,
not a subset — so `_reason_for`'s catalog validation cannot be defeated by a code that is
in the catalog but illegal in the column.

## 3. Guards written, each mutated red and green

Mutations were applied to a copy of `src/` at `/root/w5adv-mut` with `contracts/`, `docs/`
and `fixtures/` symlinked, run as `pytest -o pythonpath=/root/w5adv-mut/src`.
`auditmanager.__file__` was asserted to resolve to
`/root/w5adv-mut/src/auditmanager/__init__.py` before any mutation was trusted. **No
tracked file was edited to produce any mutation**; after every revert, `diff -r` showed the
copy's sources identical to the worktree's.

### `tests/integration/runs/test_exhausted_budget_run_row.py` (2 guards)

- `test_the_recorded_adapter_over_an_empty_directory_exhausts_the_budget` — the route.
- `test_an_exhausted_budget_names_the_transport_failure_on_the_run_row` — the run row,
  driven by a *scripted* never-reachable provider, so this and the wave-3 guard reach the
  same reason through two different adapters.

| Mutation | Result |
|---|---|
| A — `findings/terminal.py::_reason_for` returns `analysis_failed` unconditionally | run-row guard **RED** (`'analysis_failed' == 'dependency_unavailable'`); route guard **green** |
| B — `runs/retry.py::RetryPolicy.has_budget_for` returns `attempt <= 1` | **both RED** (`1 == 3`) |

Mutation A is the discrimination I wanted: the loop is untouched and only the reason is
wrong, and exactly the guard that claims the reason fails.

On B I predicted the run-row guard would stay green and **I was wrong**. It reddens, but on
its *precondition* (`adapter.calls == ATTEMPT_BUDGET`), not on its claim: with retries
disabled the run never reaches the exhausted path, so the guard refuses to report a verdict
about a journey the run did not take. That is the precondition working, and it is a
different thing from failing on the claim. The wrong prediction is recorded in the module
docstring rather than quietly corrected.

### `tests/integration/exports/test_tiebreaker_is_load_bearing.py` (2 guards)

- `test_the_tie_is_real_and_the_two_orders_can_differ` — discriminating precondition.
- `test_the_listing_and_the_export_agree_when_many_observations_share_one_finding`.

| Mutation | Result |
|---|---|
| M2 — drop `o.finding_observation_id` from `_PUBLISHED_FINDINGS`'s `ORDER BY` | claim **RED 5/5**; precondition green 5/5. Reverted: **green 5/5** |

See §4.

**A guard of mine that was wrong before it shipped.** The precondition originally asserted
the physical heap order via `ORDER BY ctid`, expecting the exact reverse of the sorted
order. It passed 5/5 on the clean tree and then flaked on one of three runs under M2. Heap
placement depends on free space left by earlier transactions; it is not a property this
suite may rest on, and a flaky precondition is worse than none. It now asserts what the
guard actually needs — that ordering by the finding alone and ordering by the full key
family *can* return different sequences — using two raw-SQL queries, so it keeps its
meaning while the guard beside it is red. Green 5/5 clean, green 5/5 under M2.

## 4. Verdict on the integrator's two green mutations

### M2 — **I disagree. It is reddenable, and I have reddened it.**

`W3_CLOSURE.md` §1 says:

> M2 cannot be reddened and this is worth stating plainly: dropping the tiebreaker makes
> the order *unspecified* rather than *wrong*, and PostgreSQL happens to return the rows
> the expected way on this data. A test that passed today would be resting on the planner,
> not on a property.

That is true of the data in play, and only of it.
`test_two_observations_under_one_finding_still_order_deterministically` ties exactly **two**
rows, and at two rows PostgreSQL's sort does not visibly reorder a tie. I reproduced the
integrator's result: M2 against the whole existing `tests/integration/exports` suite is
28 passed, green, including that guard.

Tie **twenty** observations under one `finding_uid`, inserted in descending identifier order,
and the two surfaces disagree:

```
listing: 0019, 0016, 0017, 0018, 0000, 0001, ... 0015
export:  0000, 0001, 0002, 0003, 0004, ...       0019
```

Reproducible: red 5/5 under M2, green 5/5 reverted. The order under M2 is not merely
unspecified — it is observably different from the CSV's, which is the disagreement D1 was
repaired to prevent.

The "resting on the planner" objection is a good one and deserves an answer rather than a
brush-past. It applies to a test that pins a *literal* expected sequence. My guard pins no
sequence: it compares two live queries and asserts they agree, which is the property
`api/routers/findings.py::_finding_sort_key` states in prose. If the planner changes, both
sides may move; what may not happen is that they move differently, and only a total order
on both sides guarantees that. So a green result is not a bet on the planner, and a red one
is proof that without the tiebreaker the two surfaces *can* disagree — which is all a
mutation needs to show.

Nothing in `src/` changed. The repair D1 shipped was correct; what was wrong was the
conclusion that it could not be guarded.

### M3 — **I agree with the result, and the stated reason is wrong in a way worth fixing.**

`W3_CLOSURE.md` says "M3 is defensive against a future non-C collation; it guards nothing
today." The first half is right, the second is right, but the implied premise — that the
database is effectively C today — is not. `audit_w5a`'s collation is **`en_US.utf8`**, so
`COLLATE "C"` is an active override, not a no-op.

The actual reason M3 cannot be reddened is stronger and is a schema fact, not luck. Both
identifier columns are CHECK-constrained:

```
ck_finding_finding_uid_format      CHECK (finding_uid ~ '^fnd_[0-9A-HJKMNP-TV-Z]{26}$')
ck_finding_observation_id_format   CHECK (finding_observation_id ~ '^fobs_[0-9A-HJKMNP-TV-Z]{26}$')
```

Digits and uppercase only, behind a constant ASCII prefix. Over all 1024 ordered pairs of
that 32-character alphabet, `C` and `en_US.utf8` disagree **zero** times:

```sql
SELECT count(*) FROM pairs
WHERE (('fnd_'||a) COLLATE "C"           < ('fnd_'||b) COLLATE "C")
   <> (('fnd_'||a) COLLATE "en_US.utf8"  < ('fnd_'||b) COLLATE "en_US.utf8");
-- 0
```

So M3 is unreddenable **by construction**, and it will stay that way for exactly as long as
that CHECK holds. `COLLATE "C"` is defensive against a widening of the identifier alphabet
(lowercase, or punctuation), not against a change of database collation — the collation is
already non-C. Worth recording because the closure's version invites someone to delete the
`COLLATE` on the grounds that the database is C. It is not.

## 5. Migrations `0004` and `0005`, forward and backward, against a populated database

Run against `audit_w5a` carrying committed rows — 62 `audit_run`, 232 `stage_result`, 54
`model_call` (50 `succeeded`, **4 `truncated`**), 142 `finding`, 142 `finding_observation`.
Six rows carry `parameters.call_status = 'truncated'`, so the population holds both the
post-`0005` shape and two rows in the legacy pre-`0005` shape.

`head → 0004 → 0003 → head` all exited 0. No data lost, no constraint violated on
re-validation; `make check-db` is green afterwards and the database is back at
`0005_truncated_call_status`. The round trip is sound. Two findings fall out of it (§6.2,
§6.3).

## 6. Defects found, left unrepaired

### 6.1 `attempt_budget_exhausted` is `true` on runs that succeeded

**Owner: `src/auditmanager/runs/retry.py`, `AttemptSummary.budget_exhausted`.**

```python
@property
def budget_exhausted(self) -> bool:
    return self.attempts >= self.attempt_budget
```

It counts attempts *used* and never asks whether the last one failed. A run whose provider
was unreachable twice and answered on the third attempt **publishes**, and its stage row
records `attempt_budget_exhausted: true`. Measured:

```
outages=2 → calls 3, attempts 3, terminal 'published'
metrics: attempts 3, attempt_budget 3, attempt_budget_exhausted True
run row: state 'published', terminal_reason None
```

The metric name says the budget ran out. For this run it did not: the budget was fully
*used* and the run succeeded. Anything counting exhausted budgets — the natural query for
"how many runs died because the provider never came back", which is exactly the kind of
figure `AttemptSummary.metrics`'s own docstring exists to keep computable — will include
published runs.

The existing suite cannot catch it: `test_an_unreachable_provider_is_retried_and_the_run
_still_publishes` asserts `attempt_budget_exhausted is False`, but at `attempts == 2`,
below the budget. The success-on-the-last-attempt case is untested.

`budget_exhausted`'s own docstring ("`True` when the last attempt was the last one the
budget allowed") accurately describes the code; it is the persisted metric *name* that
overstates. Either the property should also require the final attempt to have failed, or
the metric should be named `attempt_budget_fully_used`. That is an owner's call, not mine.

**No guard added,** deliberately. The correct assertion (`False` on a published run) is red
against the current tree, and I may not ship a red gate or repair the tree I am measuring.

### 6.2 `0004`'s downgrade silently destroys cost provenance, unrepairably

**Owner: `db/migrations/versions/20260914_0004_cost_basis.py`.**

`downgrade()` is `DROP COLUMN cost_basis`. A later `upgrade()` re-adds it as
`NOT NULL DEFAULT 'estimated'`, so every row comes back labelled `estimated`. On a database
holding `measured` rows — any proxied or live run — a `0004` down/up cycle relabels them as
derived. That is precisely the outcome `0004`'s own column comment forbids:

> The default is estimated because every row written before this column existed was
> derived: a backfill claiming otherwise would invent provenance for calls nobody measured.

After a downgrade the rows *were* measured, and the re-upgrade asserts they were not.

It cannot be corrected afterwards. `model_call` carries `trg_model_call_immutable`;
I confirmed it directly:

```
UPDATE model_call SET cost_basis='measured' WHERE status='truncated'
→ state_transition_not_allowed: model_call is immutable once written; UPDATE is refused
```

So the mislabelling is permanent in the one table the programme treats as evidence.

My round trip did **not** exhibit the loss, and I want to be exact about why: all 54 rows in
`audit_w5a` were already `estimated`, because nothing in the offline suite produces a
`measured` call. The defect is latent here and would fire on a database that has run the
proxy. Reported rather than demonstrated.

### 6.3 `0005`'s stated reason for safe validation has expired

**Owner: `db/migrations/versions/20260915_0005_truncated_call_status.py` (docstring).**

> Both constraints are therefore satisfied vacuously by every row in every existing
> database: no row anywhere has `status = 'truncated'` yet, because until this revision the
> executor could not write one. Validation is immediate and no table is rewritten.

True when authored, false the moment the revision shipped and the executor began writing
the value. `audit_w5a` holds 4 such rows today. Re-applying `0005` — after a downgrade, or
on any database restored to `0004` — now validates two CHECKs against real data and *can*
fail. It did not fail here (4/4 truncated rows carry a `response_sha256`, 0/4 carry an
`error_code`), so the migration is correct; what is wrong is the recorded justification. A
reader relying on it would conclude that re-applying `0005` cannot fail on data. It can.

### 6.4 The wave-3 guard sleeps the pinned backoff for real, twice per battery

**Owner: `tests/integration/runs/test_terminal_reason_names_the_cause.py`.**

`_run_against` calls `execute_run` without the `sleep` injection point the executor
provides. Since the fixture takes the exhausted-budget route (§2), each instantiation sleeps
`2.0 + 8.0 = 10 s` of wall clock. `unreachable_provider_run` is function-scoped and feeds
two tests, so every gate run spends **~20 s** — about 10% of the 200 s battery — asleep,
proving nothing that `sleep=lambda _: None` would not prove. `Sleep` exists on `execute_run`
for exactly this reason and its docstring says so: "a test must be able to assert *that* the
pinned backoff was taken without spending it."

This one sits inside a path I own (`tests/integration/runs/**`). I left it alone anyway: the
brief says I repair nothing, and a session that edits the tree it is measuring cannot be
cited for the measurement. It is a one-line change for whoever owns the repair.

## 7. Things in the brief that turned out to be false

1. **The seam.** "Nothing asserts `audit_run.terminal_reason` on the exhausted path… the
   wave-3 guard reaches the unreachable-provider case by a different route." Both halves are
   wrong: it is the same route, and the run row was already asserted on it. §2. This is the
   brief's central claim and it was built from reading the tests, which the brief itself
   flags as "still a claim" — correctly.
2. **The provisioning defect did not fire.** The brief says "it will fire" and that `HEAD`
   would be `6d3c0f3`. It was `beaa7f7`, on the right line. §0.
3. **`W3_CLOSURE.md` §1's M2 verdict**, which the brief asks me to judge: reddenable. §4.
4. **`W3_CLOSURE.md` §1's M3 reasoning**, same: the conclusion holds, the reason given does
   not. The database is `en_US.utf8`, not C. §4.
5. Trivia: the brief calls itself 185 lines; it is 187. `git diff 6d3c0f3..ef5b8bf -- src/ db/`
   is "915 lines" only if that means insertions — the full stat is 915 insertions and 80
   deletions across 14 files. `runs/retry.py` is exactly 260 lines, as stated.

Premises I checked that **held**: `ATTEMPT_BUDGET = 3` and `BACKOFF_SECONDS = (2.0, 8.0)`;
`analysis_failed` not retryable and `dependency_unavailable` retryable in the frozen catalog;
`audit_run.terminal_reason` CHECK-constrained to exactly the 20-member catalog;
`truncated` written through unmapped since `0005`; the baseline gate counts; `make foundation`
35 passed; all three of my ports free.

## 8. On the cost ceiling, idempotency, and `truncated` downstream

Read and not faulted, so that the absence of a finding is on the record rather than implied:

- **Cost ceiling across attempts.** `execute_run` builds one `CostMeter` from
  `config.run_cost_ceiling_usd` and threads it through every attempt; a retry cannot buy a
  fresh budget. Guarded by `test_the_cost_ceiling_binds_across_attempts_not_per_attempt`,
  which has both halves of the discrimination (spent-0.90 halts, spent-0.00 publishes).
- **Idempotency under retry.** The retry is a loop inside one execution. The run's
  `command_id` and `frozen_input_digest` are unchanged across it, no second command is
  issued, and `model_call_id` is `ModelCallId.new()` per attempt, so attempts neither
  collide on the primary key nor orphan a suffixed key. `P4_CLOSURE.md` §1's
  "provably identical input" property still holds in code: everything the provider does not
  touch — the required-input check and all three artifact reads — happens once, above the
  loop.
- **`truncated` downstream.** `tools/validation/ledger_report.py` handles all three shapes:
  the post-`0005` column, the legacy `(succeeded, parameters.call_status='truncated')` pair,
  and an unknown value, which it reports as `unknown` rather than silently as success. I
  found nothing downstream that still treats `truncated` as a clean success. The one
  asymmetry is documented and intentional: `truncated` carries no `error_code`, because
  `GATE_B1_CLOSURE.md` §4 item 6 is an open owner decision.

## 9. How this meets `W5-CERT`

Of the four defects, §6.1 is the only one plausibly visible through the twelve journey
operations, and only to an operator who reads `stage_result.metrics` on a published run —
which is not one of the §8 criteria. §6.2 and §6.3 are migration-level and invisible to the
journey. §6.4 is a test-suite cost. So I do not think any of these is a gap in `W5-CERT`'s
certification, and its verdict is not weakened by this report.

The one result that bears on re-certification is §4's M2: listing order is observable in the
artifacts PC-01 scored, and it is now guarded rather than merely repaired.

## 10. Elapsed

18:48 → 19:09 local, **~21 minutes** wall clock.

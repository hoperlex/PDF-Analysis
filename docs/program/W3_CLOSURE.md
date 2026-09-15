# Wave 3 closure: two defects W2-QA found, repaired and proved

Written 2026-09-15 by the integrator. Convergence at `848255f`, base `e3503a0`; the gate is
green: **793 passed, 5 skipped, 116 subtests** under the canonical battery, `make foundation`
35 passed, `git diff --check` clean, working tree unchanged by the battery.

No dispatched sessions. Wave 3 was led personally, in one worktree (`/root/w3`, branch
`agent/w3`, instance `gate-w3`, ports 55550/59150/59151, database `audit_w3`), because the
two items were small, adjacent and both in code paths `W2-QA` had just read. Splitting them
across sessions would have cost more in briefing than in execution — and, per §2 of the wave-2
closure, my briefs are the part of dispatch that has been going wrong.

Ten guards added, 783 → 793. Seven mutations run, five red, two reported green.

## 1. D1 — the listing and the CSV disagreed about order

`W2-QA` found that `_PUBLISHED_FINDINGS` ordered by a single key while the CSV export it
claims to mirror orders by a key *family*. Two findings sharing a first key came back in
whatever order the database chose, so the UI listing and the downloaded CSV could present
the same run's findings in different sequences — with nothing in either artifact admitting
it.

Repaired in `src/auditmanager/findings/queries.py` by aligning two `ORDER BY` clauses to the
CSV's canonical key family. `_DIAGNOSTICS` (`WHERE o.finding_uid IS NULL`) and
`finding_by_uid` (`LIMIT 1`) were deliberately left alone: neither shares the CSV's key, and
changing them would have been change without a claim behind it.

Guarded by `tests/integration/exports/test_listing_order_matches_the_export.py`, which
opens with `test_the_case_really_does_discriminate` — a test that the *fixture* can tell the
two orders apart, so the guard cannot pass by never exercising the case.

| Mutation | Result |
|---|---|
| M1 restore the single-key order | **RED** |
| M4 reverse the tiebreaker | **RED** |
| M2 drop the tiebreaker entirely | green here — **wrong; `W5-ADV` reddened it, see below** |
| M3 drop `COLLATE "C"` | green — **reported; the reason given below was wrong** |

> **Corrected 2026-09-15 after `W5-ADV`, and both corrections verified independently by the
> integrator before being recorded here.** The two paragraphs below are kept as written,
> struck through, because what I concluded from them is the useful part.

~~M2 cannot be reddened and this is worth stating plainly: dropping the tiebreaker makes the
order *unspecified* rather than *wrong*, and PostgreSQL happens to return the rows the
expected way on this data. A test that passed today would be resting on the planner, not on
a property.~~

**Wrong, and wrong in a way worth naming: I generalised "unreddenable" from a two-row
case.** `W5-ADV` reddened M2 with **20 observations tied under one `finding_uid`**, inserted
in descending id order — the listing returns `0019, 0016, 0017, 0018, 0000…` while the CSV
returns `0000…0019`. Reproduced by me on a copy at `/root/w3-m2` with imports proven under
the copy: **red 3 of 3 under M2, green on revert.**

The "resting on the planner" objection does not survive either, and the reason is a lesson
about how to write this kind of guard: `W5-ADV`'s test **pins no sequence**. It runs the two
live queries and compares them, so only a total order on *both* sides can keep them
agreeing. My mutation was fine; my test design was what could not discriminate.

~~M3 is defensive against a future non-C collation; it guards nothing today.~~

**The result stands, the stated reason was false.** The database collation is **`en_US.utf8`**,
not C — `datcollate` measured, and `finding_observation_id` carries no column collation, so
it inherits it. `COLLATE "C"` is therefore an *active override* today, not a no-op waiting
for a future change.

The real reason M3 cannot be reddened is a CHECK constraint: ids are pinned to the Crockford
alphabet `[0-9A-HJKMNP-TV-Z]` behind a constant prefix, and over all **1024 pairs** of that
alphabet C and `en_US.utf8` disagree **zero** times (measured). So M3 is unreddenable *by
construction*, and the `COLLATE` is load-bearing insurance against the id alphabet ever
widening — not against a collation change.

This matters practically: my original wording invites a later reader to delete `COLLATE "C"`
on the grounds that the database is already C. It is not.

## 2. The run row flattened every failure into `analysis_failed`

Any failed run recorded `analysis_failed` whatever killed it. The frozen catalog marks
`analysis_failed` **not retryable** and `dependency_unavailable` **retryable**, so an
operator reading a run row could not tell a model that answered badly from a provider that
never answered — precisely the distinction the retry policy `W2-RUN` shipped depends on.

`select_terminal` now takes each stage's error code and returns it as the terminal reason
when the failed stages agree on one. `execute_run` builds that mapping from the stage rows
and stops being the thing that names a cause; the gate remains the only decider, which
`test_terminal_selection_is_delegated` still enforces structurally.

Two rules keep the widening honest:

- stages that failed for **different** reasons keep `analysis_failed`. One reason cannot
  represent two causes, so naming one would be a guess; the stage rows carry all of them.
- a code **outside the frozen 20-member catalog** is dropped. `audit_run.terminal_reason` is
  CHECK-constrained to the catalog, so passing an invented code through would convert a
  failed run into a database error — a worse failure than the one being reported.

Each rule has its own unit guard, because a live run cannot easily produce either.

| Mutation | Result |
|---|---|
| M5 helper always returns `analysis_failed` (the pre-wave behaviour) | **RED** ×2 |
| M6 drop the single-distinct-code rule | **RED** |
| M7 drop the catalog validation | **RED** |

Each reddened exactly the guard claiming to cover it. The control
`test_a_real_analysis_failure_still_reads_as_one` stayed green under all three — it should,
since `analysis_failed` is the right answer in that case, and a control that reddens under
every mutation is not discriminating between them.

All seven mutations ran on a copy at `/root/w3-mut` with `contracts/`, `docs/` and
`fixtures/` symlinked, `pytest -o pythonpath=/root/w3-mut/src`, and `auditmanager.__file__`
asserted to resolve under the copy before any mutation was applied.

## 3. One test needed updating, and the update was made to earn its keep

Widening `select_terminal` broke `test_terminal_selection_is_delegated`, whose gate double
pins the signature. That is the test doing its job, not a regression — but a signature-only
edit would have left the new half of the delegation contract unguarded. The double now also
asserts that the executor hands the gate an error code for every stage it hands a status,
so a future executor that quietly stopped forwarding codes would fail here rather than
silently revert §2 to `analysis_failed` for everything.

## 4. Version fixation

`origin/dev` advances to `848255f`. **`origin/main` stays at `6d3c0f3`**, and deliberately:
`6d3c0f3` is the PC-01 acceptance, and wave 3 changes behaviour PC-01 certified —
`terminal_reason` values and listing order are both observable in the artifacts PC-01 scored.
Re-certification is the owner's decision, not the integrator's, so main does not move until
PC-01 is re-run. This is the same rule `VERSION_FIXATION.md` states and the reason PC-01
carries no tag.

## 5. Still owner-blocked

Unchanged by this wave, and none of it is mine to decide:

- **OD-17** — the next corpus shape. Precision evidence is saturated; more documents of the
  same shape buy nothing.
- **OD-18** — three to five named experts with committed slots.
- The **21st error code**, if the catalog is to grow.

Wave 4 cannot be planned past these without inventing the answers.

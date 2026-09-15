# Wave 6 closure: the five defects wave 5 was not allowed to fix

Written 2026-09-15 by the integrator. Convergence at `338b45e`, base `8f418e9`; the gate is
green: **803 passed, 5 skipped, 116 subtests**, `make foundation` 35 passed, `git diff
--check` clean, working tree unchanged by the battery.

797 → 803: six guards, one per repair plus the two the mutations demanded.

Led personally. `W5-ADV` and `W5-CERT` found these and could not repair them — that rule is
what makes their findings citable — and repairing is not certifying, so authorship is no
obstacle here.

## 1. What was repaired

| Defect | Tree | Repair |
|---|---|---|
| `W5ADV-D1` | `src/` | `budget_exhausted` asks the last attempt's outcome instead of comparing counts |
| `W5CERT-DEF-2` | `src/` | the environment is resolved once and governs the whole wiring; `Application` exposes `provider_config` |
| `W5ADV-D2` | `db/` | `0004`'s downgrade refuses while any measured cost would be lost |
| `W5ADV-D3` | `db/` | `0005`'s justification marked expired rather than rewritten |
| `W5ADV-D4` | `tests/` | the wave-3 guard injects `sleep`: 21.6 s → 1.5 s |

Every repair was mutation-proved, on copies outside the worktree with
`auditmanager.__file__` confirmed under the copy. Six mutations, **all red**, plus one that
started green and is the subject of §2.

## 2. A mutation that reddened nothing, and what it was hiding

M9 — drop the budget check from `budget_exhausted` and keep only "the last attempt failed" —
stayed **green**.

That is the *other* direction of the same defect. A run refused a second attempt because its
error code is not retryable fails on attempt 1 of 3, and under M9 would report its budget
exhausted. Nothing said otherwise: the test for that case asserted `attempts` and
`retried_on_error_code` and stopped short of this field.

One assertion added to the test that already set the scenario up, and **M9 now reddens**. So
the field is guarded in both directions rather than only the one `W5-ADV` found. Reporting
exhaustion for a run that published and reporting it for a run that was never allowed a
second try are opposite errors with identical effect on a count.

## 3. The convergence QA had blessed the defect as an expectation

Two of `W2-QA`'s seam tests pinned `attempt_budget_exhausted is True` on runs that answered
on their third attempt and **published**.

So `W5ADV-D1` was not an unguarded field. It was a field guarded *wrongly*, by the
independent convergence pass, which is why it survived waves 2 through 5 with three sessions
reading that code. **A wrong expectation is worse than no expectation**: it converts a later
correction into an apparent regression and argues against the repair.

Neither test lost anything. The first is about the seam — both authors' metrics surviving on
one row — and the key is informative either way. The second is named for telling a first-try
run from a third-try one, and that is carried by `attempts` and `retried_on_error_code` two
lines above; this field never discriminated between them.

This is the sharpest argument yet for the adversarial role. `W2-QA` was independent, careful
and thorough, and it still wrote down the wrong number — because it was reading the
implementation to learn what to expect. Only a session asked to *attack* the code rather
than describe it found the difference.

## 4. W5ADV-D2, reproduced rather than accepted

`W5-ADV` reported that a downgrade/upgrade round trip relabels measured costs. I reproduced
it end to end rather than taking the report: a copy of `db/migrations` with the refusal
removed, run against a database seeded with one `measured` call, and the value came back
**`estimated`** — with `trg_model_call_immutable` refusing the UPDATE that would put it
right.

The real migration, on identical input: exit 1, *"refusing to drop model_call.cost_basis: 1
row(s) record a measured cost and dropping the column loses that permanently"*, and the row
untouched. That A/B is the guard's red and green.

The fix is **refusal, not preservation**. The information genuinely cannot survive a column
drop, so the honest behaviour is to stop and make an operator decide what happens to the
measurements rather than decide for them by discarding.

## 5. Three mistakes of my own, in the test written to protect a migration

Recorded because all three were the same mistake, and it is the one I have spent four
closures attributing to other people's briefs.

- `document.title` — the column is `display_title`. I also seeded a `command_record` nothing
  needed, since `audit_run.command_id` is nullable.
- Readable filler ids — every id is CHECK-constrained to Crockford base32, which has no `I`,
  `L`, `O` or `U`. `ap_downgrade_guard` could never have been valid.
- A leaked `engine.connect()` — it held a lock and `ALTER TABLE` waited on it for the full
  180 s alembic timeout. **The test written to protect the migration was what blocked it.**

Each time I had written from an assumption about the schema instead of reading it. The
comment on the connection line says so in place, so the next person adding a migration test
does not spend the same three minutes.

That is the fifth recorded instance of this failure mode — `W2_CLOSURE.md` §2 (two briefs),
`W4_CLOSURE.md` §3 (an obsolete register), `W5-PLAN.md` (my own dispatch brief), and now my
own test. The pattern is not carelessness about *documents*. It is trusting a remembered
shape over a readable one, and it does not care whether the shape is a record or a schema.

## 6. Version fixation

`origin/dev` advances to the wave-6 merge. **`origin/main` stays at `8f418e9`.**

`main` moved to the certified tree hours ago, and wave 6 changes `src/` and `db/` — the
first behaviour change since. `W5-CERT` certified `beaa7f7`; that certification does not
extend to this. The re-certification debt reopens here, deliberately and with one wave's
worth of changes in it rather than five.

None of the five repairs is journey-visible, so nothing suggests the ten criteria have
stopped holding. That is an expectation, not a measurement, and the difference is the whole
reason `W5-CERT` existed.

## 7. Still owner-blocked

- **`OD-18`** — three to five named experts with committed slots. `P4-BHV-01` waits on this
  alone.
- **`OD-17`** — the next corpus shape; PC-02's precision evidence is saturated.
- **The 21st error code.**
- **Whether to re-certify PC-01 again** now that wave 6 has changed behaviour. The `W5-CERT`
  brief is reusable as written; only its base commit changes.

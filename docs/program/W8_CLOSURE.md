# Wave 8 closure: three guards that did not guard

Written 2026-09-16 by the integrator. Convergence at `0a12ca1`, base `972602d`.
**`make gate` → `GATE OK`**: foundation 35, battery **811 passed** / 5 skipped / 116
subtests, frontend 289, whitespace clean. 803 → 811.

Led personally. All three items are things `W6-CERT` named *in passing* while certifying
something else, and correctly did not repair — a session that repairs the tree it measures
cannot be cited for the measurement. None is a defect in behaviour. All three are places
where the evidence said less than it appeared to.

## 1. A cross-check the twelve operations cannot reach

`runs/executor.py` compares the run row's declared provider mode against the adapter's.
`W6-CERT` removed it and the whole criterion-4 suite stayed green, because `adapters.py`
refuses a request for an unprovided mode *before* a run row exists.

**Reproduced before writing anything**: with the branch disabled on an isolated copy,
`tests/e2e/pc01` is 49 passed / 5 skipped, unchanged.

It is worth keeping and it is reachable — through `execute_run`, which is where it lives.
`adapters.py` compares a *request* against a *deployment*; this compares a persisted *row*
against the object about to write under it, and a composition that wired the wrong adapter
is refused here and nowhere else. Three tests now reach it there, including that nothing is
written before the refusal: a check firing after the stages ran would leave rows claiming a
provenance nothing produced.

The comment is corrected too. It said the refusal "happens one level above it, which is
here", implying this was the refusing site.

**M13** — disable the branch: **RED** on both claims, precondition green, and
`tests/e2e/pc01` still 49 passed. The guard reddens exactly where the existing suite does
not, which is the whole point of writing it.

## 2. My first attempt at the race proved nothing, and the mutations said so

`W6-CERT` nulled `CommandRepository.begin`'s pre-read and criterion 9 stayed green: the
safety is the `UNIQUE` constraint and the recovery that reads the winner back after the
insert collides. The pre-read is an optimisation. **That recovery had no test** — every
existing `idempotency_key_stale` case is about an *abandoned* key, a different branch.

I first ordered two real sessions by commit, assuming a pre-read issued after the winner
commits would miss. **Under `READ COMMITTED` it does not**: each statement sees fresh data,
so every call took the pre-read path. Five tests passed and **both mutations stayed green**.
I had written tests for the line that had just been shown not to be load-bearing.

This is worth recording as it happened. The tests looked right, the fixture was real, the
scenario was named correctly, and the only thing that revealed the gap was the mutation
discipline. Without it I would have committed five green tests over an unguarded branch and
called wave 8 done.

The stale read is now arranged directly, by a subclass whose first `find` returns `None`
while the winner's row is really committed. A simulation of the *timing window*, not of the
collision: the insert is real, the `UNIQUE` violation is the database's, the read-back is
production code, and a helper asserts the recovery actually ran so a future change that
reopens the pre-read path fails here rather than passing quietly. Threads would reproduce
the window authentically and flakily — it is microseconds wide, and a test that passes
because it lost a race is not evidence.

Four guards over what the collision really does: the winner still running gives the loser a
typed retryable refusal; the winner finished replays its outcome; the SAVEPOINT is why the
loser can be answered at all rather than handed an aborted transaction; the fingerprint
check stops a different payload receiving the winner's result.

| Mutation | Result |
|---|---|
| M14 drop the recovery | **RED** ×3 |
| M15 drop the SAVEPOINT | **RED** ×3 |
| M16 drop the fingerprint comparison | **RED** on exactly the payload test |

Both preconditions stay green under all three.

## 3. A tautology in the live precision measurement

`assert isinstance(flagged, list)` — and `flagged` is built as a list two lines above. It
was the only assertion in the live controls test, which is why `W6-CERT` had to confirm
"0 of 6" from the published evidence by hand.

The intent was right and is kept: a flagged control is a precision result, not a gate.
What was missing is that **"0 of 6 flagged" and "compared against nothing" produce the same
number.** So the measurement's preconditions are asserted rather than its result — there
were controls, there was published text, and anything flagged is a real control id — and
the print now carries the denominator and the size of the comparison set.

Shown to discriminate without a live run: against an empty manifest and against a run that
published nothing, the old assertion passes and each new one fails; an honest zero passes
both. Proving a live-path assertion cost nothing.

## 4. The recurring mistake, twice more, and what is different about it now

Twice in this wave I wrote from an assumption instead of reading: `finding` has no `run_id`
of its own (it is reached through `finding_observation`), and `CommandRepository` is not
called `CommandStore`. Both were caught in seconds by the thing failing.

That is now the **seventh and eighth** instances across eight waves. What is different is
where they land. In waves 2 through 7 the assumption reached a *brief* or a *record*, where
nothing fails and it survives for waves. Here it reached code, and code answers immediately.

The lesson is not "stop assuming" — eight waves say that instruction does not take. It is
that **an assumption is cheap where something executes and expensive where nothing does**,
which is an argument for pushing claims into executable form wherever they can go. That is
what `make gate` did for the gate in wave 7, and what §1–3 of this wave did for three
claims that were sitting in prose and in tautologies.

## 5. Version fixation

`origin/dev` advances to the wave-8 merge. **`origin/main` stays at `8f418e9`.**

Wave 8 changed **no `src/` behaviour** — one comment in `executor.py` and nothing else
outside `tests/`. So the certification `W6-CERT` gave `c0d7daf` still describes this tree's
behaviour exactly, and `main` can advance to carry it whenever the owner says so. That
decision has now been pending across three waves; it is not blocking anything, and it is
still not the integrator's.

## 6. Still owner-blocked

- **`OD-18`** — three to five named experts with committed slots. `P4-BHV-01` waits on this
  alone.
- **`OD-17`** — the next corpus shape; PC-02's precision evidence is saturated.
- **The 21st error code.**
- **Whether `origin/main` advances** to `c0d7daf` or later.

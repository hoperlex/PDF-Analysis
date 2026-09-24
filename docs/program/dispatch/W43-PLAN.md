# Wave 43 — the screens the owner ruled and nobody built, in two stages with a judge on each

**Ruled by the owner 2026-09-24: parallel execution, and _at least one judge per stage of the
wave_.** This file says what the stages are and what each judge is for, because a judge briefed
as "check the work" checks nothing.

## Why these screens, and why now

`R-23` sorted ten legacy screens. **Two of its answers are still unbuilt and neither is blocked
by anything**: the stage-comparison skeleton, and the front-end preparation for blocks,
optimisation, logs and workers. `W42` was meant to carry them and became the fix wave instead,
when the owner redirected it after the poll.

Everything else in `R-23` is either done (the knowledge base, wave 38), deferred by the owner
(dashboard `D-63`, queue, work schedule), or waiting on users (dispatcher). And the two things
that would otherwise lead — `R-1`'s host and `D-70`'s provider key — are the owner's and have
not arrived. **Nine addresses exist today**; this wave adds five.

## The measurement this wave is, whether or not anyone intends it

`WAVE_PLAN_42_45.md` said of wave 42: *"the first wave that will test wave 41's repair on screens
written after it."* **Wave 42 did not write a screen, so wave 43 is that wave.**

Wave 41 made the language guard's coverage an assertion derived from the contract, and wave 42
made every border meet 3:1 and widened the contrast census to 49 screens. **Five new screens are
the first honest test of both.** If a new screen can be added and neither instrument notices, the
repairs were local and the rows should reopen. **That question belongs to the judge, not to the
streams**, because a stream that knows it is being measured on coverage will seed its own screens.

## Stage A — build, in parallel

| stream | lane | owns | carries |
|---|---|---|---|
| `W43-COMPARE` | `gate-w43a` | its own routes and widgets under `web/src` | the stage-comparison skeleton |
| `W43-PREP` | `gate-w43b` | its own four routes, `web/src/_app/app-frame.tsx` | blocks, optimisation, logs, workers |

Neither touches `contracts/**`, `src/auditmanager/**`, `db/**` or `web/FRONTEND_LOCK.json`. **This
wave changes no contract.** The ownership boundary between them is named in each brief.

## Stage A's judge — `W43-JUDGE-A`, before the merge

Runs on **both branches**, before the integrator merges either. **It repairs nothing.**

Its subject is not "is the code good". It is the five questions this programme has paid for:

1. **Do the instruments reach the new screens?** Drive the language guard and the contrast census
   against them. A new screen that neither reaches is `D-69` reopening, and the judge says so.
2. **Are the data-shape notes true?** `W43-PREP`'s third deliverable is a written claim about what
   each future screen would show, checked against the contract. **A false note is worse than no
   note**, because the next wave budgets against it.
3. **Is any number on these screens invented?** The addendum's fourth rule is *no invented
   numbers*: an empty screen is more honest than a plausible one.
4. **Does any stub claim something false about the system?** `R-18`: a finished application does
   not explain its own transport, and a stub that promises what the programme has not decided to
   build is a promise nobody made.
5. **Does each new guard bite?** Mutate them. A guard added with a screen and never shown to fail
   is the thing seven consecutive waves were spent learning about.

## Stage B — integration

The integrator merges both branches, runs **one** `make gate` on the merged tree, and reads the
verdict from the `GATE OK` line in the log.

## Stage B's judge — `W43-JUDGE-B`, after the gate

Runs on the **merged, gated tree**. **It repairs nothing.** Its subject is what a merge and a
green gate cannot tell you:

1. **Did the merge lose a test?** Two branches editing `web/src` and `web/tests` can drop one
   silently. The count is `1032 in 72 files` at `alpha-w42`; it must have risen by the streams'
   own additions and not by less.
2. **Does the browser journey still pass?** `make gate`'s frontend battery cannot see the journey
   — that is a recorded property of this programme, not a suspicion.
3. **Are the five new addresses reachable on the deployed stand**, and do they render in Russian
   with borders that meet 3:1? The stand is at `127.0.0.1:31500` in `recorded` mode.
4. **Do the two stage-A judge's findings still hold after the merge?** A finding repaired in one
   branch can be reintroduced by the other.

## Lanes

`gate-w43a`, `gate-w43b`, and `gate-w43j` for both judges in turn. Recorded in `PORT_REGISTRY.md`
in the commit that dispatches this wave.

## What this wave does not touch

`contracts/**` · `db/migrations/**` · `src/auditmanager/**` · `infra/**` · `web/FRONTEND_LOCK.json`.
The surface stays **15 paths / 18 operations / 51 schemas** and the migration head stays
`0010_run_terminal_detail`.

# Waves 45–48, planned 2026-09-24

**Successor to `WAVE_PLAN_42_45.md`.** Written into the tree because a session that restarts
loses its plan, and this programme has lost one that way.

## What is true at `alpha-w44` (`d6ebe3a`), measured

`make gate` → **`GATE OK`**: battery **2466**, foundation **35**, frontend **1110 in 78 files**.
All four refs equal; the stand is deployed and `verify-deployed.sh` reports it byte-identical.
Contract **15 paths / 18 operations / 51 schemas**, migration head **`0010`**, catalog **22 codes**.

**Twelve rows open. Five of them are the owner's** — `D-56`, `D-63`, `D-70`, `D-75`, `D-91` —
and one of those, `D-70`, blocks every path that needs a model.

## The constraint that shapes this plan, stated first

**`R-1`'s host has not arrived and `D-70`'s provider key has not arrived.** Together they block:
a live analysis, the owner's manual pass, `R-9`'s corpus work, `R-34`/`R-35`'s re-recognition,
and `PA-01` criteria 1 and 2 — which have read *cannot be established* through **four**
certifications.

**So these waves are chosen to be the work that is not waiting on either**, and to make the
host wave short when it comes rather than to substitute for it.

## W45 — the blocks screen made real, and the readiness that shortens the host wave

> **This section replaced a plan for a second section vertical (ПОС), written and committed
> an hour earlier and withdrawn before any stream saw it.** Two facts in the tree forbid it and
> I had not read either: `PROTOTYPE_PROFILE.md` §7.2 lists *"disciplines other than the single
> AR validation profile"* under **Deferred**, and `analysis/text/profile.py`'s own docstring says
> *"a second profile is a scope change"*. `R-25` also sequenced the thirteen sections **after the
> first deploy**, which is `R-1` and the owner's. **Building ПОС now would have reordered the
> owner's sequencing and taken a deferred scope decision on their behalf** — `D-96`'s exact
> shape, caught by the check it asks for, one step before four sessions were dispatched on it.

| stream | subject |
|---|---|
| `W45-BLOCKS` | the `/blocks` screen stops being a stub, **using data the pipeline already produces** |
| `W45-READY` | `D-80`'s `.dockerignore` **verified by a real build**, `D-79`'s repair so the gate reads `docs/`, and a deploy rehearsal from a clean clone |

**Why blocks is buildable today when almost nothing else is.** `W43-PREP`'s data-shape note —
the deliverable a stream would have skipped — found that *"there is no geometry to draw"* was
false: `analysis/stages/page_geometry_extraction.py:226` writes a real `bbox {x0,y0,x1,y1}` in
points, top-left origin, **one per text line**, with its unit and origin beside it. What is
missing is **an operation that returns it**.

**And that stage needs no provider.** It is one of the four in `PC01_STAGES` and carries no
adapter, no model and no provider reference, so it runs in `recorded` mode exactly as in `live`.
**`D-70` does not block this**, which is what makes it the right work while the key is missing.

It is a reseal — an operation, its client, the mirror and `FRONTEND_LOCK.json` — and under
`R-29` the shape is the integrator's to pick. `R-23` ruled the screen wanted and said each is
wired *"as its vertical lands"*; a deterministic read is that vertical landing.

**`W45-READY` is the wave's leverage.** Every hour it spends is an hour the host wave does not,
and the host wave is the only thing that moves a `PA-01` criterion.

## W46 — the logs read operation, or the debt wave

The second of the three reseals `W43-PREP` put on paper: an execution journal a reviewer can
read. **Its note needs re-reading first** — `audit_event` is never written by `src/`; what exists
is `stage_result`, `model_call`, `contract_state_transition` and `command_record`, so the
operation's subject is a decision before it is a schema.

If that decision is not ready, W46 becomes the debt wave and W47 moves up.

## W47 — the debt wave, on cadence

`D-97` (six renderer copies against one contract), `D-87`, `D-89`'s rule, `D-96`'s discipline,
`D-74`, and whatever W45 and W46 leave. Named now so it is not invented at the end.

## W48 — the host wave if it has arrived, and otherwise the optimisation view

**The thirteen section verticals are not in this plan at all**, and that is deliberate: `R-25`
placed them after the first deploy, and `PROTOTYPE_PROFILE.md` §7.2 defers a second discipline.
**They start when the owner's host does.**

**The host wave pre-empts whichever wave it lands in.** It does not queue.

## Judging, per the owner's standing instruction

Every wave: **parallel streams, one judge at the close of each sub-stage, and two or more judges
cross-judging at the close — before the final testing.** Wave 44 is the evidence that the order
matters: its cross-judges found **five false greens in the integrator's own repairs**, including
a credential guard that admitted a fallback on the next line, and they were repaired **before**
the final gate rather than after a tag, which is what wave 43 had to do.

**And the cross-examination is not a formality.** In wave 44 each judge *strengthened* the
other's findings with measurements the other had not taken, and one narrowed its own finding in
the process.
